import pytest
from fastapi.testing import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4, UUID
from datetime import datetime, timedelta, timezone

# Adjust import to bring in the 'app' instance from your main application file
# This path might need adjustment based on your project structure
from python_ai_services.main import app

# Import Pydantic models used in request/response validation
from python_ai_services.models.crew_models import AgentTask, TaskStatus # For full AgentTask and enum
from python_ai_services.models.monitoring_models import (
    AgentTaskSummary, TaskListResponse,
    AgentMemoryStats,
    SystemHealthSummary, DependencyStatus
)

# Path for patching app_services in monitoring_routes
APP_SERVICES_PATCH_PATH = "python_ai_services.api.v1.monitoring_routes.app_services"
# Path for patching get_deep_health_logic helper if testing /system/health independently of its direct logic
DEEP_HEALTH_LOGIC_PATCH_PATH = "python_ai_services.api.v1.monitoring_routes.get_deep_health_logic"

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

# --- Tests for GET /api/v1/monitoring/tasks ---
@patch(APP_SERVICES_PATCH_PATH, new_callable=MagicMock)
def test_list_tasks_success_no_filters(mock_app_services: MagicMock, client: TestClient):
    mock_persistence_service = AsyncMock()
    mock_app_services.get.return_value = mock_persistence_service

    raw_task_data = [
        {"task_id": str(uuid4()), "crew_id": "crew_A", "status": "COMPLETED",
         "start_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
         "end_time": datetime.now(timezone.utc).isoformat(),
         "inputs": {"symbol": "BTC/USD"}, "error_message": None},
        {"task_id": str(uuid4()), "crew_id": "crew_B", "status": "RUNNING",
         "start_time": datetime.now(timezone.utc).isoformat(),
         "inputs": {"symbol": "ETH/USD"}, "error_message": None}
    ]
    mock_persistence_service.list_and_count_agent_tasks_paginated = AsyncMock(return_value=(raw_task_data, 2))

    response = client.get("/api/v1/monitoring/tasks", params={"limit": 10, "offset": 0})

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert len(data["tasks"]) == 2
    assert data["tasks"][0]["crew_id"] == "crew_A"
    assert data["tasks"][0]["status"] == TaskStatus.COMPLETED.value
    assert "duration_ms" in data["tasks"][0]
    assert data["tasks"][0]["input_summary"] == {"symbol": "BTC/USD"}
    mock_persistence_service.list_and_count_agent_tasks_paginated.assert_called_once_with(
        crew_id=None, status=None, start_date_from=None, start_date_to=None, limit=10, offset=0
    )

@patch(APP_SERVICES_PATCH_PATH, new_callable=MagicMock)
def test_list_tasks_with_filters(mock_app_services: MagicMock, client: TestClient):
    mock_persistence_service = AsyncMock()
    mock_app_services.get.return_value = mock_persistence_service
    mock_persistence_service.list_and_count_agent_tasks_paginated = AsyncMock(return_value=([], 0))

    dt_from = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    dt_to = datetime.now(timezone.utc).isoformat()

    client.get("/api/v1/monitoring/tasks", params={
        "crew_id": "test_crew", "status": "FAILED",
        "start_date_from": dt_from, "start_date_to": dt_to,
        "limit": 5, "offset": 10
    })

    mock_persistence_service.list_and_count_agent_tasks_paginated.assert_called_once_with(
        crew_id="test_crew", status=TaskStatus.FAILED,
        start_date_from=datetime.fromisoformat(dt_from),
        start_date_to=datetime.fromisoformat(dt_to),
        limit=5, offset=10
    )

@patch(APP_SERVICES_PATCH_PATH, new_callable=MagicMock)
def test_list_tasks_persistence_service_unavailable(mock_app_services: MagicMock, client: TestClient):
    mock_app_services.get.return_value = None # Simulate service not available
    response = client.get("/api/v1/monitoring/tasks")
    assert response.status_code == 503
    assert "AgentPersistenceService not available" in response.json()["detail"]

# --- Tests for GET /api/v1/monitoring/tasks/{task_id} ---
@patch(APP_SERVICES_PATCH_PATH, new_callable=MagicMock)
def test_get_task_details_success(mock_app_services: MagicMock, client: TestClient):
    mock_persistence_service = AsyncMock()
    mock_app_services.get.return_value = mock_persistence_service

    task_uuid = uuid4()
    # Ensure this mock data matches the AgentTask Pydantic model structure
    mock_task_data = {
        "task_id": str(task_uuid), "crew_id": "crew_X", "status": "COMPLETED",
        "start_time": datetime.utcnow().isoformat(), "end_time": datetime.utcnow().isoformat(),
        "inputs": {"detail": "input"}, "output": {"detail": "output"},
        "error_message": None, "logs_summary": []
    }
    mock_persistence_service.get_agent_task.return_value = mock_task_data

    response = client.get(f"/api/v1/monitoring/tasks/{task_uuid}")

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == str(task_uuid)
    assert data["crew_id"] == "crew_X"
    mock_persistence_service.get_agent_task.assert_called_once_with(str(task_uuid))

@patch(APP_SERVICES_PATCH_PATH, new_callable=MagicMock)
def test_get_task_details_not_found(mock_app_services: MagicMock, client: TestClient):
    mock_persistence_service = AsyncMock()
    mock_app_services.get.return_value = mock_persistence_service
    mock_persistence_service.get_agent_task.return_value = None # Simulate task not found

    task_uuid = uuid4()
    response = client.get(f"/api/v1/monitoring/tasks/{task_uuid}")

    assert response.status_code == 404
    assert f"Task with ID '{task_uuid}' not found" in response.json()["detail"]

# --- Tests for GET /api/v1/monitoring/agents/{app_agent_id}/memory/stats ---
@patch(APP_SERVICES_PATCH_PATH, new_callable=MagicMock)
def test_get_agent_memory_stats_success(mock_app_services: MagicMock, client: TestClient):
    mock_memory_service = AsyncMock()
    mock_app_services.get.return_value = mock_memory_service

    app_agent_id = "test_agent_123"
    stats_data = {
        "app_agent_id": app_agent_id, "memories_stored_count": 10,
        "memories_recalled_count": 5, "last_activity_timestamp": datetime.utcnow().isoformat()
    }
    # AgentMemoryStats model is used by the service method for its return, so mock that structure
    mock_memory_service.get_agent_memory_stats.return_value = AgentMemoryStats(**stats_data)

    response = client.get(f"/api/v1/monitoring/agents/{app_agent_id}/memory/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["app_agent_id"] == app_agent_id
    assert data["memories_stored_count"] == 10
    mock_memory_service.get_agent_memory_stats.assert_called_once_with(app_agent_id)

@patch(APP_SERVICES_PATCH_PATH, new_callable=MagicMock)
def test_get_agent_memory_stats_not_found(mock_app_services: MagicMock, client: TestClient):
    mock_memory_service = AsyncMock()
    mock_app_services.get.return_value = mock_memory_service
    mock_memory_service.get_agent_memory_stats.return_value = None

    app_agent_id = "unknown_agent"
    response = client.get(f"/api/v1/monitoring/agents/{app_agent_id}/memory/stats")

    assert response.status_code == 404
    assert f"Memory stats not found for agent '{app_agent_id}'" in response.json()["detail"]

# --- Tests for GET /api/v1/monitoring/system/health ---
@patch(DEEP_HEALTH_LOGIC_PATCH_PATH, new_callable=AsyncMock)
def test_get_system_health_summary_success(mock_get_deep_health: AsyncMock, client: TestClient):
    mock_deep_health_output = {
        "overall_status": "degraded",
        "dependencies": [
            {"name": "redis_cache", "status": "connected"},
            {"name": "agent_persistence_supabase_client", "status": "not_connected_or_configured", "error": "Config missing"},
        ]
    }
    mock_get_deep_health.return_value = mock_deep_health_output

    response = client.get("/api/v1/monitoring/system/health")

    assert response.status_code == 200 # Even if degraded, endpoint itself is fine
    data = response.json()

    assert data["overall_status"] == "degraded"
    assert len(data["service_statuses"]) == 2
    assert data["service_statuses"][0]["name"] == "redis_cache"
    assert data["service_statuses"][0]["status"] == "connected"
    assert data["service_statuses"][1]["name"] == "agent_persistence_supabase_client"
    assert data["service_statuses"][1]["status"] == "not_connected_or_configured"
    assert data["service_statuses"][1]["details"] == "Config missing"

    mock_get_deep_health.assert_called_once()

