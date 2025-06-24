import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Assuming main.py or where your FastAPI app is defined
# This path might need adjustment based on actual project structure
from python_ai_services.main import app # Import your FastAPI app instance
from python_ai_services.models.simulation_models import BacktestRequest, BacktestResult, EquityDataPoint
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig # For creating snapshot
from python_ai_services.services.simulation_service import SimulationService, SimulationServiceError # For mocking and error type

# --- Test Client Fixture ---
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# --- Helper Functions ---
def create_valid_backtest_request_dict(with_snapshot: bool = True) -> dict:
    if with_snapshot:
        # Create a minimal AgentConfigOutput snapshot
        snapshot = AgentConfigOutput(
            agent_id="snap_agent", name="Snapshot Agent", agent_type="DarvasBoxTechnicalAgent",
            strategy=AgentStrategyConfig(strategy_name="darvas_test"),
            risk_config=AgentRiskConfig(max_capital_allocation_usd=1000, risk_per_trade_percentage=0.01)
        ).model_dump(mode='json') # Use mode='json' for Pydantic v2 if needed, or just .dict() for v1

        return {
            "agent_config_snapshot": snapshot,
            "symbol": "TEST/USD",
            "start_date_iso": "2023-01-01T00:00:00Z",
            "end_date_iso": "2023-01-31T23:59:59Z",
            "initial_capital": 10000.0,
            "simulated_fees_percentage": 0.001,
            "simulated_slippage_percentage": 0.0005
        }
    else: # Use agent_id_to_simulate
        return {
            "agent_id_to_simulate": "existing_agent_id_123",
            "symbol": "TEST/USD",
            "start_date_iso": "2023-01-01T00:00:00Z",
            "end_date_iso": "2023-01-31T23:59:59Z",
            "initial_capital": 10000.0
            # Optional fields will use defaults
        }

def create_mock_backtest_result(request_dict: dict) -> BacktestResult:
    # Create a BacktestRequest model from the dict to embed in the result
    req_model = BacktestRequest(**request_dict)
    return BacktestResult(
        request_params=req_model,
        final_capital=11000.0,
        total_pnl=1000.0,
        total_pnl_percentage=10.0,
        total_trades=5,
        winning_trades=3,
        losing_trades=2,
        win_rate=60.0,
        equity_curve=[EquityDataPoint(timestamp=datetime.now(timezone.utc), equity=10500.0)] # Simplified
    )

# --- API Endpoint Tests ---

@patch('python_ai_services.api.v1.simulation_routes.SimulationService.run_backtest', new_callable=AsyncMock)
@patch('python_ai_services.api.v1.simulation_routes.AgentManagementService') # Mock AMS used in endpoint
@patch('python_ai_services.api.v1.simulation_routes.MarketDataService') # Mock MDS used in endpoint
def test_run_backtest_endpoint_success_with_snapshot(
    mock_mds_constructor: MagicMock, mock_ams_constructor: MagicMock,
    mock_run_backtest: AsyncMock, client: TestClient
):
    # Mock AMS instance methods if it gets created and used
    mock_ams_instance = AsyncMock()
    mock_ams_instance._load_existing_statuses_from_db = AsyncMock()
    mock_ams_constructor.return_value = mock_ams_instance

    request_payload = create_valid_backtest_request_dict(with_snapshot=True)
    mock_result = create_mock_backtest_result(request_payload)
    mock_run_backtest.return_value = mock_result

    response = client.post("/api/v1/simulations/backtest", json=request_payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total_pnl"] == mock_result.total_pnl
    assert response_data["request_params"]["symbol"] == request_payload["symbol"]
    mock_run_backtest.assert_called_once()
    # Assert that the BacktestRequest model was passed to the service
    call_args = mock_run_backtest.call_args[0][0]
    assert isinstance(call_args, BacktestRequest)
    assert call_args.symbol == request_payload["symbol"]
    assert call_args.agent_config_snapshot is not None
    assert call_args.agent_config_snapshot.agent_id == request_payload["agent_config_snapshot"]["agent_id"]


@patch('python_ai_services.api.v1.simulation_routes.SimulationService.run_backtest', new_callable=AsyncMock)
@patch('python_ai_services.api.v1.simulation_routes.AgentManagementService')
@patch('python_ai_services.api.v1.simulation_routes.MarketDataService')
def test_run_backtest_endpoint_success_with_agent_id(
    mock_mds_constructor: MagicMock, mock_ams_constructor: MagicMock,
    mock_run_backtest: AsyncMock, client: TestClient
):
    mock_ams_instance = AsyncMock()
    mock_ams_instance._load_existing_statuses_from_db = AsyncMock() # Mock the async method
    mock_ams_constructor.return_value = mock_ams_instance # AMS constructor returns our mock

    request_payload = create_valid_backtest_request_dict(with_snapshot=False)
    mock_result = create_mock_backtest_result(request_payload)
    mock_run_backtest.return_value = mock_result

    response = client.post("/api/v1/simulations/backtest", json=request_payload)

    assert response.status_code == 200
    mock_ams_constructor.assert_called_once() # AMS should be instantiated if agent_id is passed
    # await mock_ams_instance._load_existing_statuses_from_db.assert_called_once() # Check if it was awaited
    # This assertion for await is tricky with AsyncMock directly. Usually, check side effects or if method itself is awaitable.
    # For now, ensuring AMS constructor was called is a good step.

    mock_run_backtest.assert_called_once()
    call_args = mock_run_backtest.call_args[0][0]
    assert isinstance(call_args, BacktestRequest)
    assert call_args.agent_id_to_simulate == request_payload["agent_id_to_simulate"]


@patch('python_ai_services.api.v1.simulation_routes.SimulationService.run_backtest', new_callable=AsyncMock)
@patch('python_ai_services.api.v1.simulation_routes.AgentManagementService')
@patch('python_ai_services.api.v1.simulation_routes.MarketDataService')
def test_run_backtest_endpoint_value_error(
    mock_mds: MagicMock, mock_ams: MagicMock,
    mock_run_backtest: AsyncMock, client: TestClient
):
    request_payload = create_valid_backtest_request_dict()
    mock_run_backtest.side_effect = ValueError("Invalid date range")

    response = client.post("/api/v1/simulations/backtest", json=request_payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid date range"


@patch('python_ai_services.api.v1.simulation_routes.SimulationService.run_backtest', new_callable=AsyncMock)
@patch('python_ai_services.api.v1.simulation_routes.AgentManagementService')
@patch('python_ai_services.api.v1.simulation_routes.MarketDataService')
def test_run_backtest_endpoint_simulation_service_error(
    mock_mds: MagicMock, mock_ams: MagicMock,
    mock_run_backtest: AsyncMock, client: TestClient
):
    request_payload = create_valid_backtest_request_dict()
    mock_run_backtest.side_effect = SimulationServiceError("Something went wrong in simulation")

    response = client.post("/api/v1/simulations/backtest", json=request_payload)

    assert response.status_code == 500
    assert response.json()["detail"] == "Something went wrong in simulation"


@patch('python_ai_services.api.v1.simulation_routes.SimulationService.run_backtest', new_callable=AsyncMock)
@patch('python_ai_services.api.v1.simulation_routes.AgentManagementService')
@patch('python_ai_services.api.v1.simulation_routes.MarketDataService')
def test_run_backtest_endpoint_unexpected_error(
    mock_mds: MagicMock, mock_ams: MagicMock,
    mock_run_backtest: AsyncMock, client: TestClient
):
    request_payload = create_valid_backtest_request_dict()
    mock_run_backtest.side_effect = Exception("Totally unexpected")

    response = client.post("/api/v1/simulations/backtest", json=request_payload)

    assert response.status_code == 500
    assert "Internal server error during backtest: Totally unexpected" in response.json()["detail"]

# Need to import datetime and timezone for create_mock_backtest_result
from datetime import datetime, timezone
