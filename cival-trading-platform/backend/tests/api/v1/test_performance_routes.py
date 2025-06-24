import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

from python_ai_services.models.performance_models import PerformanceMetrics
from python_ai_services.services.performance_calculation_service import PerformanceCalculationService
from python_ai_services.api.v1.performance_routes import router as performance_router, get_performance_calculation_service

# Create a minimal FastAPI app for testing this specific router
app = FastAPI()
app.include_router(performance_router, prefix="/api/v1")

# Mock service instance
mock_service_perf = MagicMock(spec=PerformanceCalculationService)

# Override the dependency for testing
def override_get_performance_calculation_service():
    return mock_service_perf

app.dependency_overrides[get_performance_calculation_service] = override_get_performance_calculation_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_mock_service():
    """Reset the mock service before each test."""
    mock_service_perf.reset_mock()

# --- Helper to create sample data ---
def _create_sample_performance_metrics(agent_id: str) -> PerformanceMetrics:
    return PerformanceMetrics(
        agent_id=agent_id,
        calculation_timestamp=datetime.now(timezone.utc),
        total_trades=10,
        winning_trades=5,
        losing_trades=3,
        neutral_trades=2,
        win_rate=0.625, # 5 / (5+3)
        loss_rate=0.375, # 3 / (5+3)
        total_net_pnl=150.0,
        gross_profit=300.0,
        gross_loss=150.0,
        average_win_amount=60.0,
        average_loss_amount=50.0,
        profit_factor=2.0,
        notes="Sample metrics"
    )

# --- Test Cases ---

def test_get_agent_performance_metrics_success():
    agent_id = "agent_perf_1"
    mock_metrics = _create_sample_performance_metrics(agent_id)
    mock_service_perf.calculate_performance_metrics = AsyncMock(return_value=mock_metrics)

    response = client.get(f"/api/v1/agents/{agent_id}/performance")

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["agent_id"] == agent_id
    assert response_json["total_trades"] == 10
    assert response_json["profit_factor"] == 2.0
    mock_service_perf.calculate_performance_metrics.assert_called_once_with(agent_id)

def test_get_agent_performance_metrics_failure_to_fetch():
    agent_id = "agent_perf_fetch_fail"
    # Simulate service returning metrics object with specific note indicating fetch failure
    mock_metrics_fetch_fail = PerformanceMetrics(
        agent_id=agent_id,
        notes="Failed to fetch trade history: DB error"
    )
    mock_service_perf.calculate_performance_metrics = AsyncMock(return_value=mock_metrics_fetch_fail)

    response = client.get(f"/api/v1/agents/{agent_id}/performance")

    assert response.status_code == 503 # As per route logic for this specific note
    assert "Could not calculate performance" in response.json()["detail"]
    assert "Failed to fetch trade history: DB error" in response.json()["detail"]
    mock_service_perf.calculate_performance_metrics.assert_called_once_with(agent_id)

def test_get_agent_performance_metrics_no_history():
    agent_id = "agent_perf_no_history"
    # Simulate service returning metrics object with note for no history
    mock_metrics_no_history = PerformanceMetrics(
        agent_id=agent_id,
        notes="No trade history available for calculation."
        # Other fields would be defaults (0s, Nones)
    )
    mock_service_perf.calculate_performance_metrics = AsyncMock(return_value=mock_metrics_no_history)

    response = client.get(f"/api/v1/agents/{agent_id}/performance")

    assert response.status_code == 200 # Route allows this through
    response_json = response.json()
    assert response_json["agent_id"] == agent_id
    assert response_json["total_trades"] == 0
    assert "No trade history available" in response_json["notes"]
    mock_service_perf.calculate_performance_metrics.assert_called_once_with(agent_id)


def test_get_agent_performance_metrics_unexpected_error():
    agent_id = "agent_perf_unexpected_error"
    mock_service_perf.calculate_performance_metrics = AsyncMock(side_effect=Exception("Unexpected internal error"))

    response = client.get(f"/api/v1/agents/{agent_id}/performance")

    assert response.status_code == 500
    assert "Unexpected internal error" in response.json()["detail"]
    mock_service_perf.calculate_performance_metrics.assert_called_once_with(agent_id)

