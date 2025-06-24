import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Optional, Any, Dict
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException # Added import
from fastapi.testclient import TestClient
from python_ai_services.main import app

# Import Pydantic models for response validation and mock data creation
from python_ai_services.models.monitoring_models import (
    AgentTaskSummary, TaskListResponse, DependencyStatus, SystemHealthSummary
)
# Import services and exceptions for type hinting and mocking
from python_ai_services.services.agent_task_service import AgentTaskService
from python_ai_services.services.memory_service import MemoryService, MemoryInitializationError
from supabase import Client as SupabaseClient # For type hinting app.state.supabase_client

# Import the actual dependency callables from main.py to use as keys for overrides
from python_ai_services.main import get_agent_task_service, get_memory_service_for_monitoring, get_supabase_client


# --- Test Client Fixture ---
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# --- Mock Service Fixtures ---
@pytest.fixture
def mock_agent_task_service_override(): # Renamed to avoid conflict if a class is named this
    service = MagicMock(spec=AgentTaskService)
    service.get_task_summaries = MagicMock() # Sync method
    return service

@pytest.fixture
def mock_memory_service_override(): # Renamed
    service = MagicMock(spec=MemoryService)
    service.get_agent_memory_stats = AsyncMock() # Async method
    return service

# --- Monitoring API Tests ---

def test_get_tasks_summary_success(client: TestClient, mock_agent_task_service_override: MagicMock):
    mock_ats = mock_agent_task_service_override
    task_id = uuid4()
    # Create Pydantic models for the expected data
    expected_task_summary = AgentTaskSummary(
        task_id=str(task_id),
        status="COMPLETED",
        agent_name="TestAgent",
        crew_name="TestCrew",
        timestamp=datetime.now(timezone.utc).isoformat(),
        duration_ms=100.0,
        result_summary="Done",
        error_message=None
    )
    expected_response_model = TaskListResponse(
        tasks=[expected_task_summary],
        total_tasks=1,
        page=1,
        page_size=1
    )
    mock_ats.get_task_summaries.return_value = expected_response_model

    app.dependency_overrides[get_agent_task_service] = lambda: mock_ats
    response = client.get("/api/v1/monitoring/tasks?page=1&page_size=1")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    # FastAPI automatically calls .dict() on Pydantic model responses
    # For comparison, ensure both are dicts, and timestamps match format.
    response_json = response.json()
    expected_dict = expected_response_model.dict()
    # Timestamps can have slight precision differences if not careful,
    # but here they are generated then used, so should be exact.
    assert response_json == expected_dict
    mock_ats.get_task_summaries.assert_called_once_with(1, 1, None)


def test_get_tasks_summary_service_error(client: TestClient, mock_agent_task_service_override: MagicMock):
    mock_ats = mock_agent_task_service_override
    mock_ats.get_task_summaries.side_effect = Exception("Service layer error")

    app.dependency_overrides[get_agent_task_service] = lambda: mock_ats
    response = client.get("/api/v1/monitoring/tasks")
    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert "Failed to fetch task summaries: Service layer error" in response.json()["detail"]


def test_get_dependencies_health_all_operational(client: TestClient, mock_memory_service_override: MagicMock):
    # Store original app.state values if they exist
    original_supabase_client = getattr(app.state, 'supabase_client', None)
    original_redis_client = getattr(app.state, 'redis_cache_client', None)

    app.state.supabase_client = MagicMock(spec=SupabaseClient)
    app.state.redis_cache_client = MagicMock()
    app.state.redis_cache_client.ping = AsyncMock(return_value=True)

    app.dependency_overrides[get_memory_service_for_monitoring] = lambda: mock_memory_service_override

    response = client.get("/api/v1/monitoring/health/dependencies")
    app.dependency_overrides.clear()

    # Restore original app.state values
    app.state.supabase_client = original_supabase_client
    app.state.redis_cache_client = original_redis_client


    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["name"] == "Supabase (PostgreSQL)"; assert data[0]["status"] == "operational"
    assert data[1]["name"] == "Redis"; assert data[1]["status"] == "operational"
    assert data[2]["name"] == "MemGPT (via MemoryService)"; assert data[2]["status"] == "operational"
    app.state.redis_cache_client.ping.assert_called_once()


def test_get_dependencies_health_redis_fails(client: TestClient, mock_memory_service_override: MagicMock):
    original_supabase_client = getattr(app.state, 'supabase_client', None)
    original_redis_client = getattr(app.state, 'redis_cache_client', None)

    app.state.supabase_client = MagicMock(spec=SupabaseClient)
    app.state.redis_cache_client = MagicMock()
    app.state.redis_cache_client.ping = AsyncMock(side_effect=Exception("Redis connection failed"))

    app.dependency_overrides[get_memory_service_for_monitoring] = lambda: mock_memory_service_override

    response = client.get("/api/v1/monitoring/health/dependencies")
    app.dependency_overrides.clear()
    app.state.supabase_client = original_supabase_client
    app.state.redis_cache_client = original_redis_client

    assert response.status_code == 200
    data = response.json()
    assert data[1]["name"] == "Redis"; assert data[1]["status"] == "unavailable"
    assert "Failed to connect to Redis: Redis connection failed" in data[1]["details"]


def test_get_dependencies_health_memory_service_fails_init(client: TestClient):
    original_supabase_client = getattr(app.state, 'supabase_client', None)
    original_redis_client = getattr(app.state, 'redis_cache_client', None)
    app.state.supabase_client = MagicMock(spec=SupabaseClient)
    app.state.redis_cache_client = MagicMock()
    app.state.redis_cache_client.ping = AsyncMock(return_value=True)

    # Make the get_memory_service_for_monitoring dependency raise an HTTPException like in main.py
    mock_failing_ms_dependency = MagicMock(side_effect=HTTPException(status_code=503, detail="MS Init Failed from test"))
    app.dependency_overrides[get_memory_service_for_monitoring] = mock_failing_ms_dependency

    response = client.get("/api/v1/monitoring/health/dependencies")
    app.dependency_overrides.clear()
    app.state.supabase_client = original_supabase_client
    app.state.redis_cache_client = original_redis_client

    assert response.status_code == 200 # Endpoint itself succeeds
    data = response.json()
    assert data[2]["name"] == "MemGPT (via MemoryService)"
    assert data[2]["status"] == "unavailable"
    assert "MS Init Failed from test" in data[2]["details"]


def test_get_system_health_all_ok(client: TestClient, mock_memory_service_override: MagicMock):
    original_supabase_client = getattr(app.state, 'supabase_client', None)
    original_redis_client = getattr(app.state, 'redis_cache_client', None)
    app.state.supabase_client = MagicMock(spec=SupabaseClient)
    app.state.redis_cache_client = MagicMock()
    app.state.redis_cache_client.ping = AsyncMock(return_value=True)

    app.dependency_overrides[get_memory_service_for_monitoring] = lambda: mock_memory_service_override

    response = client.get("/api/v1/monitoring/health/system")
    app.dependency_overrides.clear()
    app.state.supabase_client = original_supabase_client
    app.state.redis_cache_client = original_redis_client

    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "healthy"
    assert len(data["dependencies"]) == 3


def test_get_system_health_one_dependency_fails(client: TestClient, mock_memory_service_override: MagicMock):
    original_supabase_client = getattr(app.state, 'supabase_client', None)
    original_redis_client = getattr(app.state, 'redis_cache_client', None)
    app.state.supabase_client = MagicMock(spec=SupabaseClient)
    app.state.redis_cache_client = MagicMock()
    app.state.redis_cache_client.ping = AsyncMock(side_effect=Exception("Redis down"))

    app.dependency_overrides[get_memory_service_for_monitoring] = lambda: mock_memory_service_override

    response = client.get("/api/v1/monitoring/health/system")
    app.dependency_overrides.clear()
    app.state.supabase_client = original_supabase_client
    app.state.redis_cache_client = original_redis_client

    assert response.status_code == 200
    data = response.json()
    # Based on logic in main.py, if redis is "unavailable", overall_status becomes "critical"
    assert data["overall_status"] == "critical"
    assert data["dependencies"][1]["status"] == "unavailable"


def test_get_memory_stats_success(client: TestClient, mock_memory_service_override: MagicMock):
    mock_ms = mock_memory_service_override
    expected_stats_payload = {"memgpt_agent_name": "test_agent", "total_memories": 100}
    mock_ms.get_agent_memory_stats.return_value = {
        "status": "success", "message": "Stats retrieved", "stats": expected_stats_payload
    }

    app.dependency_overrides[get_memory_service_for_monitoring] = lambda: mock_ms
    response = client.get("/api/v1/monitoring/memory/stats")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["stats"] == expected_stats_payload
    mock_ms.get_agent_memory_stats.assert_called_once()


def test_get_memory_stats_service_returns_error_status(client: TestClient, mock_memory_service_override: MagicMock):
    mock_ms = mock_memory_service_override
    mock_ms.get_agent_memory_stats.return_value = {
        "status": "error", "message": "MemGPT not ready", "stats": None
    }
    app.dependency_overrides[get_memory_service_for_monitoring] = lambda: mock_ms
    response = client.get("/api/v1/monitoring/memory/stats")
    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "MemGPT not ready" in response.json()["detail"]


def test_get_memory_stats_service_dependency_raises_init_error(client: TestClient):
    # This tests when get_memory_service_for_monitoring itself raises an exception
    failing_dependency_mock = MagicMock(side_effect=HTTPException(status_code=503, detail="MS Dependency Init Failed"))
    app.dependency_overrides[get_memory_service_for_monitoring] = failing_dependency_mock

    response = client.get("/api/v1/monitoring/memory/stats")
    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "MS Dependency Init Failed" in response.json()["detail"]

# Final check on overall_status logic for test_get_system_health_one_dependency_fails
# The main.py logic is:
# overall_status = "healthy"
# for dep_status in dependency_statuses:
#     if dep_status.status not in ["operational", "not_checked"]:
#         overall_status = "warning"
#         if dep_status.status in ["unavailable", "error", "misconfigured"]:
#             overall_status = "critical"
#             break
# If Redis is "unavailable", overall_status should indeed be "critical".
# The test test_get_system_health_one_dependency_fails correctly reflects this.
# Looks good.
