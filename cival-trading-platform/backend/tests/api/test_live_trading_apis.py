import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
import uuid
from datetime import datetime, timezone
from typing import List

# Application instance from main.py
from python_ai_services.main import app

# Models to be returned by endpoints or used in tests
from python_ai_services.models.auth_models import AuthenticatedUser
from python_ai_services.models.hyperliquid_models import (
    HyperliquidAccountSnapshot,
    HyperliquidAssetPosition,
    HyperliquidOpenOrderItem,
    HyperliquidOrderStatusInfo
)

# Service and its error that will be mocked
from python_ai_services.services.hyperliquid_execution_service import HyperliquidExecutionService, HyperliquidExecutionServiceError

# Dependency injectors that will be overridden
from python_ai_services.main import get_hyperliquid_execution_service, get_current_active_user

# --- Test Client Fixture ---
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# --- Mock Fixture for AuthenticatedUser ---
@pytest.fixture
def mock_auth_user():
    return AuthenticatedUser(id=uuid.uuid4(), email="live@example.com", roles=["user"])

# --- Mock Fixture for HyperliquidExecutionService ---
@pytest_asyncio.fixture
async def mock_hl_service():
    service = MagicMock(spec=HyperliquidExecutionService)
    service.get_detailed_account_summary = AsyncMock()
    service.get_all_open_orders = AsyncMock()
    service.get_order_status = AsyncMock()
    # Mock the wallet_address attribute that's accessed by endpoints
    service.wallet_address = "0xTestWalletAddressForService"
    return service

# Helper for dependency overrides
def setup_dependencies(mock_user, mock_service_instance=None, service_unavailable=False):
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    if service_unavailable:
        app.dependency_overrides[get_hyperliquid_execution_service] = \
            lambda: (_ for _ in ()).throw(HTTPException(status_code=503, detail="Hyperliquid service not available or not configured."))
    elif mock_service_instance:
        app.dependency_overrides[get_hyperliquid_execution_service] = lambda: mock_service_instance
    else: # Default mock if specific instance not provided but service should be "available"
        app.dependency_overrides[get_hyperliquid_execution_service] = lambda: MagicMock(spec=HyperliquidExecutionService)


# === Tests for GET /api/v1/live/hyperliquid/account-summary ===

def test_get_account_summary_success(client: TestClient, mock_auth_user: AuthenticatedUser, mock_hl_service: MagicMock):
    sample_snapshot = HyperliquidAccountSnapshot(
        time=int(datetime.now(timezone.utc).timestamp() * 1000),
        totalRawUsd="12345.67",
        parsed_positions=[
            HyperliquidAssetPosition(asset="ETH", szi="1.0", entry_px="2000", unrealized_pnl="100", margin_used="200")
        ],
        parsed_open_orders=[]
    )
    mock_hl_service.get_detailed_account_summary.return_value = sample_snapshot
    setup_dependencies(mock_auth_user, mock_hl_service)

    response = client.get("/api/v1/live/hyperliquid/account-summary")

    assert response.status_code == 200
    assert response.json()["total_account_value_usd"] == "12345.67" # totalRawUsd alias
    assert len(response.json()["parsed_positions"]) == 1
    mock_hl_service.get_detailed_account_summary.assert_called_once_with(user_address=mock_hl_service.wallet_address)
    app.dependency_overrides.clear()

def test_get_account_summary_not_found(client: TestClient, mock_auth_user: AuthenticatedUser, mock_hl_service: MagicMock):
    mock_hl_service.get_detailed_account_summary.return_value = None
    setup_dependencies(mock_auth_user, mock_hl_service)

    response = client.get("/api/v1/live/hyperliquid/account-summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "Account summary data not found."
    app.dependency_overrides.clear()

def test_get_account_summary_service_error(client: TestClient, mock_auth_user: AuthenticatedUser, mock_hl_service: MagicMock):
    mock_hl_service.get_detailed_account_summary.side_effect = HyperliquidExecutionServiceError("HL Service Down")
    setup_dependencies(mock_auth_user, mock_hl_service)

    response = client.get("/api/v1/live/hyperliquid/account-summary")

    assert response.status_code == 500
    assert response.json()["detail"] == "HL Service Down"
    app.dependency_overrides.clear()

def test_get_account_summary_service_unavailable(client: TestClient, mock_auth_user: AuthenticatedUser):
    setup_dependencies(mock_auth_user, service_unavailable=True)

    response = client.get("/api/v1/live/hyperliquid/account-summary")

    assert response.status_code == 503
    assert response.json()["detail"] == "Hyperliquid service not available or not configured."
    app.dependency_overrides.clear()


# === Tests for GET /api/v1/live/hyperliquid/open-orders ===

def test_get_open_orders_success(client: TestClient, mock_auth_user: AuthenticatedUser, mock_hl_service: MagicMock):
    sample_open_order = HyperliquidOpenOrderItem(
        oid=123, asset="BTC", side="b", limit_px="30000", sz="0.1",
        timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
        raw_order_data={"cloid": str(uuid.uuid4())}
    )
    mock_hl_service.get_all_open_orders.return_value = [sample_open_order]
    setup_dependencies(mock_auth_user, mock_hl_service)

    response = client.get("/api/v1/live/hyperliquid/open-orders")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["oid"] == 123
    assert response_data[0]["asset"] == "BTC"
    mock_hl_service.get_all_open_orders.assert_called_once_with(user_address=mock_hl_service.wallet_address)
    app.dependency_overrides.clear()

def test_get_open_orders_service_error(client: TestClient, mock_auth_user: AuthenticatedUser, mock_hl_service: MagicMock):
    mock_hl_service.get_all_open_orders.side_effect = HyperliquidExecutionServiceError("Failed to fetch open orders")
    setup_dependencies(mock_auth_user, mock_hl_service)

    response = client.get("/api/v1/live/hyperliquid/open-orders")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to fetch open orders"
    app.dependency_overrides.clear()


# === Tests for GET /api/v1/live/hyperliquid/orders/{order_id}/status ===

def test_get_order_status_success(client: TestClient, mock_auth_user: AuthenticatedUser, mock_hl_service: MagicMock):
    order_id_to_check = 789012
    sample_order_status = HyperliquidOrderStatusInfo(
        order={"oid": order_id_to_check, "asset": "ETH", "side": "s", "limitPx": "2100", "sz": "0.5"},
        status="filled",
        fills=[{"px": "2100.50", "qty": "0.5", "fee": "1.05", "time": int(datetime.now(timezone.utc).timestamp() * 1000)}]
    )
    mock_hl_service.get_order_status.return_value = sample_order_status
    setup_dependencies(mock_auth_user, mock_hl_service)

    response = client.get(f"/api/v1/live/hyperliquid/orders/{order_id_to_check}/status")

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["order"]["oid"] == order_id_to_check
    assert response_data["status"] == "filled"
    mock_hl_service.get_order_status.assert_called_once_with(user_address=mock_hl_service.wallet_address, oid=order_id_to_check)
    app.dependency_overrides.clear()

def test_get_order_status_order_not_found(client: TestClient, mock_auth_user: AuthenticatedUser, mock_hl_service: MagicMock):
    order_id_to_check = 111222
    mock_hl_service.get_order_status.side_effect = HyperliquidExecutionServiceError("Order not found")
    setup_dependencies(mock_auth_user, mock_hl_service)

    response = client.get(f"/api/v1/live/hyperliquid/orders/{order_id_to_check}/status")

    assert response.status_code == 404
    assert response.json()["detail"] == f"Order OID {order_id_to_check} not found."
    app.dependency_overrides.clear()

def test_get_order_status_other_service_error(client: TestClient, mock_auth_user: AuthenticatedUser, mock_hl_service: MagicMock):
    order_id_to_check = 333444
    mock_hl_service.get_order_status.side_effect = HyperliquidExecutionServiceError("HL API timeout")
    setup_dependencies(mock_auth_user, mock_hl_service)

    response = client.get(f"/api/v1/live/hyperliquid/orders/{order_id_to_check}/status")

    assert response.status_code == 500
    assert response.json()["detail"] == "HL API timeout"
    app.dependency_overrides.clear()

