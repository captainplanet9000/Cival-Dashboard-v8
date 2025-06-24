import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock # AsyncMock for async service methods
from datetime import datetime, timezone, timedelta # Added timedelta
import uuid
from typing import List, Optional # Added List, Optional

from python_ai_services.models.dashboard_models import PortfolioSummary, TradeLogItem, OrderLogItem, AssetPositionSummary, PortfolioSnapshotOutput # Added PortfolioSnapshotOutput
from python_ai_services.services.trading_data_service import TradingDataService
from python_ai_services.services.portfolio_snapshot_service import PortfolioSnapshotService # Added
# Import the dependency provider function from the routes file
from python_ai_services.api.v1.dashboard_data_routes import router as dashboard_data_router, get_trading_data_service, get_portfolio_snapshot_service_instance # Added get_portfolio_snapshot_service_instance
from fastapi import Query # Added Query

# Create a minimal FastAPI app for testing this specific router
app = FastAPI()
app.include_router(dashboard_data_router, prefix="/api/v1")

# Mock service instance that will be used by the router's dependency override
mock_service_tds = MagicMock(spec=TradingDataService)

# Override the dependency for testing
def override_get_trading_data_service():
    return mock_service_tds

app.dependency_overrides[get_trading_data_service] = override_get_trading_data_service

# Mock and override for PortfolioSnapshotService
mock_service_pss = MagicMock(spec=PortfolioSnapshotService)
def override_get_portfolio_snapshot_service():
    return mock_service_pss
app.dependency_overrides[get_portfolio_snapshot_service_instance] = override_get_portfolio_snapshot_service


client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_mock_service():
    """Reset the mock service before each test."""
    mock_service_tds.reset_mock()

# --- Helper to create sample data ---
def _create_sample_portfolio_summary(agent_id: str) -> PortfolioSummary:
    return PortfolioSummary(
        agent_id=agent_id,
        timestamp=datetime.now(timezone.utc),
        account_value_usd=10000.0,
        total_pnl_usd=500.0,
        available_balance_usd=9000.0,
        margin_used_usd=1000.0,
        open_positions=[AssetPositionSummary(asset="BTC", size=0.1, entry_price=50000.0)]
    )

def _create_sample_trade_log_item(agent_id: str) -> TradeLogItem:
    return TradeLogItem(
        trade_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        agent_id=agent_id,
        asset="ETH",
        side="buy",
        order_type="market",
        quantity=1.0,
        price=3000.0,
        total_value=3000.0
    )

def _create_sample_order_log_item(agent_id: str, status: str = "open") -> OrderLogItem:
    return OrderLogItem(
        order_id=str(uuid.uuid4()),
        agent_id=agent_id,
        timestamp=datetime.now(timezone.utc),
        asset="SOL",
        side="sell",
        order_type="limit",
        quantity=10.0,
        limit_price=150.0,
        status=status
    )

# --- Test Cases ---

def test_get_agent_portfolio_summary_found():
    agent_id = "agent123"
    mock_summary = _create_sample_portfolio_summary(agent_id)
    mock_service_tds.get_portfolio_summary = AsyncMock(return_value=mock_summary)

    response = client.get(f"/api/v1/agents/{agent_id}/portfolio/summary")

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["agent_id"] == agent_id
    assert response_json["account_value_usd"] == 10000.0
    mock_service_tds.get_portfolio_summary.assert_called_once_with(agent_id)

def test_get_agent_portfolio_summary_not_found():
    agent_id = "agent_unknown"
    mock_service_tds.get_portfolio_summary = AsyncMock(return_value=None)

    response = client.get(f"/api/v1/agents/{agent_id}/portfolio/summary")

    assert response.status_code == 404
    assert "not available" in response.json()["detail"]
    mock_service_tds.get_portfolio_summary.assert_called_once_with(agent_id)


def test_get_agent_trade_history():
    agent_id = "agent_th"
    mock_trades = [_create_sample_trade_log_item(agent_id) for _ in range(2)]
    mock_service_tds.get_trade_history = AsyncMock(return_value=mock_trades)

    response = client.get(f"/api/v1/agents/{agent_id}/portfolio/trade-history?limit=5&offset=0")

    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 2
    assert response_json[0]["agent_id"] == agent_id
    mock_service_tds.get_trade_history.assert_called_once_with(agent_id, 5, 0)

def test_get_agent_trade_history_invalid_limit():
    agent_id = "agent_th_limit"
    response_over_limit = client.get(f"/api/v1/agents/{agent_id}/portfolio/trade-history?limit=1000&offset=0")
    assert response_over_limit.status_code == 400
    assert "Limit must be between 1 and 500" in response_over_limit.json()["detail"]

    response_under_limit = client.get(f"/api/v1/agents/{agent_id}/portfolio/trade-history?limit=0&offset=0")
    assert response_under_limit.status_code == 400
    assert "Limit must be between 1 and 500" in response_under_limit.json()["detail"]

    mock_service_tds.get_trade_history.assert_not_called()


def test_get_agent_open_orders():
    agent_id = "agent_oo"
    mock_orders = [_create_sample_order_log_item(agent_id, status="open") for _ in range(1)]
    mock_service_tds.get_open_orders = AsyncMock(return_value=mock_orders)

    response = client.get(f"/api/v1/agents/{agent_id}/orders/open")

    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 1
    assert response_json[0]["agent_id"] == agent_id
    assert response_json[0]["status"] == "open"
    mock_service_tds.get_open_orders.assert_called_once_with(agent_id)

def test_get_agent_order_history():
    agent_id = "agent_oh"
    mock_orders = [_create_sample_order_log_item(agent_id, status="filled") for _ in range(3)]
    mock_service_tds.get_order_history = AsyncMock(return_value=mock_orders)

    response = client.get(f"/api/v1/agents/{agent_id}/orders/history?limit=10&offset=0")

    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 3
    assert response_json[0]["agent_id"] == agent_id
    assert response_json[0]["status"] == "filled"
    mock_service_tds.get_order_history.assert_called_once_with(agent_id, 10, 0)


# --- Tests for /agents/{agent_id}/portfolio/equity-curve ---

def _create_sample_portfolio_snapshot_output(agent_id: str, equity: float, offset_days: int = 0) -> PortfolioSnapshotOutput:
    return PortfolioSnapshotOutput(
        agent_id=agent_id,
        timestamp=datetime.now(timezone.utc) - timedelta(days=offset_days),
        total_equity_usd=equity
    )

def test_get_agent_equity_curve_success():
    agent_id = "agent_equity_test"
    mock_snapshots = [
        _create_sample_portfolio_snapshot_output(agent_id, 10000.0, 2),
        _create_sample_portfolio_snapshot_output(agent_id, 10100.0, 1),
        _create_sample_portfolio_snapshot_output(agent_id, 10050.0, 0)
    ]
    mock_service_pss.get_historical_snapshots = AsyncMock(return_value=mock_snapshots)

    start_time_iso = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    end_time_iso = datetime.now(timezone.utc).isoformat()

    response = client.get(
        f"/api/v1/agents/{agent_id}/portfolio/equity-curve",
        params={"start_time": start_time_iso, "end_time": end_time_iso, "limit": 10, "sort_ascending": "true"}
    )
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 3
    assert response_json[0]["agent_id"] == agent_id
    assert response_json[0]["total_equity_usd"] == 10000.0

    mock_service_pss.get_historical_snapshots.assert_called_once()
    call_args = mock_service_pss.get_historical_snapshots.call_args[1] # kwargs
    assert call_args['agent_id'] == agent_id
    assert isinstance(call_args['start_time'], datetime)
    assert isinstance(call_args['end_time'], datetime)
    assert call_args['limit'] == 10
    assert call_args['sort_ascending'] is True


def test_get_agent_equity_curve_no_snapshots():
    agent_id = "agent_no_equity_data"
    mock_service_pss.get_historical_snapshots = AsyncMock(return_value=[])

    response = client.get(f"/api/v1/agents/{agent_id}/portfolio/equity-curve")
    assert response.status_code == 200
    assert response.json() == []
    mock_service_pss.get_historical_snapshots.assert_called_once_with(
        agent_id=agent_id, start_time=None, end_time=None, limit=1000, sort_ascending=True # Default limit, sort_ascending from route
    )

def test_get_agent_equity_curve_service_error():
    agent_id = "agent_equity_error"
    mock_service_pss.get_historical_snapshots = AsyncMock(side_effect=Exception("Database connection failed"))

    response = client.get(f"/api/v1/agents/{agent_id}/portfolio/equity-curve")
    assert response.status_code == 500
    assert "Failed to retrieve equity curve: Database connection failed" in response.json()["detail"]

def test_get_agent_equity_curve_invalid_limit_param():
    agent_id = "agent_equity_limit_fail"
    # Test value less than ge=1
    response_low = client.get(f"/api/v1/agents/{agent_id}/portfolio/equity-curve?limit=0")
    assert response_low.status_code == 422 # Unprocessable Entity for Pydantic/FastAPI validation

    # Test value greater than le=10000 (as defined in the new endpoint)
    response_high = client.get(f"/api/v1/agents/{agent_id}/portfolio/equity-curve?limit=10001")
    assert response_high.status_code == 422

    mock_service_pss.get_historical_snapshots.assert_not_called() # Should not be called if params fail validation
