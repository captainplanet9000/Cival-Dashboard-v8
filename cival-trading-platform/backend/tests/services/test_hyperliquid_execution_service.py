import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, PropertyMock
import os
import uuid
from typing import Dict, Any

import datetime as dt # Alias for clarity if datetime is used extensively
from datetime import timezone # Explicitly import timezone if not covered by dt

# Service and models to test
from python_ai_services.services.hyperliquid_execution_service import HyperliquidExecutionService, HyperliquidExecutionServiceError
from python_ai_services.models.hyperliquid_models import (
    HyperliquidAccountSnapshot, HyperliquidPlaceOrderParams, HyperliquidOrderResponseData,
    HyperliquidOrderStatusInfo, HyperliquidAssetPosition, HyperliquidOpenOrderItem # Added new models
)

# Mocked SDK components (assuming these are the classes used)
# These will be patched where they are imported in the service file.
# from hyperliquid.info import Info
# from hyperliquid.exchange import Exchange
# from hyperliquid.utils import constants # HL_CONSTANTS is an alias in service
# from eth_account import Account

# --- Constants for Testing ---
TEST_WALLET_ADDRESS = "0x0367C313f106A301207009ad699b816c5E8336e8"
TEST_PRIVATE_KEY = "0xde89f6b9febfddd494176bebac48610c8a5f34a8a1228251e206df22e6f2da16" # Test key
# Note: HL_CONSTANTS.MAINNET_API_URL and HL_CONSTANTS.TESTNET_API_URL are used in service
# We will mock HL_CONSTANTS directly if specific URL values are needed beyond what service already uses.

# --- Fixtures ---
@pytest_asyncio.fixture
def mock_hl_constants():
    """Mocks the hyperliquid.utils.constants module used by the service."""
    with patch('python_ai_services.services.hyperliquid_execution_service.HL_CONSTANTS') as MockConstants:
        MockConstants.MAINNET_API_URL = "https://api.hyperliquid.xyz"  # Ensure this is set for tests
        MockConstants.TESTNET_API_URL = "https://api.hyperliquid-testnet.xyz" # Ensure this is set for tests
        yield MockConstants

@pytest_asyncio.fixture
def mock_hyperliquid_sdk_info(mock_hl_constants): # Depends on mock_hl_constants to ensure URLs are patched
    """Mocks the hyperliquid.info.Info class."""
    with patch('python_ai_services.services.hyperliquid_execution_service.Info') as MockInfo:
        instance = MockInfo.return_value
        instance.user_state = MagicMock()
        instance.order_status = MagicMock()
        yield MockInfo

@pytest_asyncio.fixture
def mock_hyperliquid_sdk_exchange(mock_hl_constants): # Depends on mock_hl_constants
    """Mocks the hyperliquid.exchange.Exchange class."""
    with patch('python_ai_services.services.hyperliquid_execution_service.Exchange') as MockExchange:
        instance = MockExchange.return_value
        instance.order = MagicMock()
        instance.cancel = MagicMock()
        yield MockExchange

@pytest_asyncio.fixture
def mock_eth_account():
    """Mocks eth_account.Account."""
    with patch('python_ai_services.services.hyperliquid_execution_service.Account') as MockAccount:
        mock_account_instance = MockAccount.from_key.return_value
        type(mock_account_instance).address = PropertyMock(return_value=TEST_WALLET_ADDRESS)
        yield MockAccount


# --- Tests for __init__ ---
# Use all relevant fixtures for __init__ tests. mock_hl_constants is used by other fixtures.
@pytest.mark.usefixtures("mock_hyperliquid_sdk_info", "mock_hyperliquid_sdk_exchange", "mock_eth_account", "mock_hl_constants")
def test_hyperliquid_service_init_mainnet_success(
    mock_eth_account: MagicMock,
    mock_hyperliquid_sdk_info: MagicMock,
    mock_hyperliquid_sdk_exchange: MagicMock,
    mock_hl_constants: MagicMock
):
    service = HyperliquidExecutionService(
        wallet_address=TEST_WALLET_ADDRESS, # Pass the test wallet address
        private_key=TEST_PRIVATE_KEY,
        network_mode="mainnet"
    )
    mock_eth_account.from_key.assert_called_once_with(TEST_PRIVATE_KEY)
    assert service.wallet_address == TEST_WALLET_ADDRESS
    mock_hyperliquid_sdk_info.assert_called_once_with(mock_hl_constants.MAINNET_API_URL, skip_ws=True)
    mock_hyperliquid_sdk_exchange.assert_called_once_with(mock_eth_account.from_key.return_value, mock_hl_constants.MAINNET_API_URL)
    assert service.info_client is not None
    assert service.exchange_client is not None

@pytest.mark.usefixtures("mock_hyperliquid_sdk_info", "mock_hyperliquid_sdk_exchange", "mock_eth_account", "mock_hl_constants")
def test_hyperliquid_service_init_testnet_with_url_override(
    mock_eth_account: MagicMock,
    mock_hyperliquid_sdk_info: MagicMock,
    mock_hyperliquid_sdk_exchange: MagicMock,
    mock_hl_constants: MagicMock # Though HL_CONSTANTS is mocked, api_url override means it's not used for URL selection
):
    custom_testnet_url = "https://custom.api.hyperliquid-testnet.xyz"
    service = HyperliquidExecutionService(
        wallet_address=TEST_WALLET_ADDRESS,
        private_key=TEST_PRIVATE_KEY,
        api_url=custom_testnet_url,
        network_mode="testnet"
    )
    mock_hyperliquid_sdk_info.assert_called_once_with(custom_testnet_url, skip_ws=True)
    mock_hyperliquid_sdk_exchange.assert_called_once_with(mock_eth_account.from_key.return_value, custom_testnet_url)

@pytest.mark.usefixtures("mock_hl_constants") # Constants needed for URL fallbacks if not for Info/Exchange mocks
def test_hyperliquid_service_init_invalid_private_key(mock_eth_account: MagicMock): # Only mock_eth_account needed here
    mock_eth_account.from_key.side_effect = ValueError("Test invalid key")
    with pytest.raises(HyperliquidExecutionServiceError, match="Invalid private key: Test invalid key"):
        HyperliquidExecutionService(wallet_address=TEST_WALLET_ADDRESS, private_key="invalid_key")

# Patch Info, Exchange, Account, and HL_CONSTANTS to None to simulate them not being importable
@patch('python_ai_services.services.hyperliquid_execution_service.Info', None)
@patch('python_ai_services.services.hyperliquid_execution_service.Exchange', None)
@patch('python_ai_services.services.hyperliquid_execution_service.Account', None)
@patch('python_ai_services.services.hyperliquid_execution_service.HL_CONSTANTS', None)
def test_hyperliquid_service_init_sdk_not_installed_fully(MockInfo, MockExchange, MockAccount, MockHL_CONSTANTS):
    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid SDK or eth_account not installed/imported correctly."):
        HyperliquidExecutionService(wallet_address=TEST_WALLET_ADDRESS, private_key=TEST_PRIVATE_KEY)


# --- Tests for get_user_state ---
@pytest.mark.asyncio
# We patch __init__ to None to prevent it from running its SDK setup logic,
# allowing us to manually set up the mocks for info_client for this specific test.
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_user_state_success():
    service = HyperliquidExecutionService("addr", "key")

    service.info_client = MagicMock()
    service.info_client.user_state = MagicMock(return_value={"totalRawUsd": "10000.00", "assetPositions": []})
    service.wallet_address = TEST_WALLET_ADDRESS

    user_state = await service.get_user_state(TEST_WALLET_ADDRESS)

    assert user_state == {"totalRawUsd": "10000.00", "assetPositions": []}
    service.info_client.user_state.assert_called_once_with(TEST_WALLET_ADDRESS)


@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_user_state_sdk_exception():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    service.info_client.user_state = MagicMock(side_effect=Exception("SDK API Error"))
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Failed to fetch user state: SDK API Error"):
        await service.get_user_state(TEST_WALLET_ADDRESS)

# --- Placeholders for other method tests ---
# test_cancel_order, test_get_order_status,
# test_get_detailed_account_summary, test_get_all_open_positions, test_get_all_open_orders

# --- Tests for place_order ---

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None) # Bypass __init__
async def test_place_order_success(mock_hl_init_bypass): # param name should be different from fixture if not used
    # Arrange
    service = HyperliquidExecutionService("addr", "key") # Args don't matter
    service.exchange_client = MagicMock() # Mock the exchange client instance

    order_params_data = HyperliquidPlaceOrderParams(
        asset="ETH", is_buy=True, sz=0.01, limit_px=2000.0,
        order_type={"limit": {"tif": "Gtc"}},
        cloid=uuid.uuid4()
    )

    # Expected SDK response structure for a successful order placement
    sdk_success_response = {
        "status": "ok",
        "response": {
            "type": "order",
            "data": {
                "statuses": [{"resting": {"oid": 12345}}]
            }
        }
    }
    service.exchange_client.order = MagicMock(return_value=sdk_success_response)
    service.wallet_address = TEST_WALLET_ADDRESS # Set if needed by any internal logic, though not directly by place_order mock

    # Act
    response_model = await service.place_order(order_params_data)

    # Assert
    service.exchange_client.order.assert_called_once_with(
        coin=order_params_data.asset,
        is_buy=order_params_data.is_buy,
        sz=order_params_data.sz,
        limit_px=order_params_data.limit_px,
        order_type_info=order_params_data.order_type,
        reduce_only=order_params_data.reduce_only, # Should be False by default in Pydantic model
        cloid=order_params_data.cloid
    )
    assert isinstance(response_model, HyperliquidOrderResponseData)
    assert response_model.status == "resting" # Extracted from statuses[0] key
    assert response_model.oid == 12345
    assert response_model.order_type_info == order_params_data.order_type
    # simulated_fills field is removed


# Test for market order still makes sense to ensure it's processed, just no simulated_fills
@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None) # Bypass __init__
async def test_place_market_order_processed_correctly(mock_hl_init_bypass): # Renamed test
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()

    order_params_market = HyperliquidPlaceOrderParams(
        asset="ETH", is_buy=True, sz=0.01, limit_px=0,
        order_type={"market": {"tif": "Ioc"}},
    )

    sdk_market_response = { # Could be 'filled' or just 'ok' if market order status is generic
        "status": "ok",
        "response": {
            "type": "order",
            "data": {"statuses": [{"filled": {"oid": 54321, "totalSz": "0.01", "avgPx": "2001.0"}}]}
        }
    }
    service.exchange_client.order = MagicMock(return_value=sdk_market_response)

    response_model = await service.place_order(order_params_market)

    assert isinstance(response_model, HyperliquidOrderResponseData)
    assert response_model.status == "filled" # Or "ok" depending on what SDK returns and how it's parsed
    assert response_model.oid == 54321
    # No assertion for simulated_fills here


@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_place_order_sdk_returns_error_status(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    order_params_data = HyperliquidPlaceOrderParams(asset="BTC", is_buy=False, sz=0.1, limit_px=30000.0, order_type={"limit": {"tif": "Alo"}})

    sdk_error_response = {"status": "error", "error": "Insufficient margin"}
    service.exchange_client.order = MagicMock(return_value=sdk_error_response)
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid API error: Insufficient margin"):
        await service.place_order(order_params_data)
    service.exchange_client.order.assert_called_once()

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_place_order_sdk_unexpected_response_no_statuses(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    order_params_data = HyperliquidPlaceOrderParams(asset="SOL", is_buy=True, sz=1.0, limit_px=50.0, order_type={"limit": {"tif": "Ioc"}})

    sdk_unexpected_response = {"status": "ok", "response": {"type": "order", "data": {"statuses": []}}} # Empty statuses
    service.exchange_client.order = MagicMock(return_value=sdk_unexpected_response)
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Order placement ok, but no status details in response."):
        await service.place_order(order_params_data)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_place_order_sdk_raises_exception(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    order_params_data = HyperliquidPlaceOrderParams(asset="ETH", is_buy=True, sz=0.01, limit_px=2000.0, order_type={"limit": {"tif": "Gtc"}})

    service.exchange_client.order = MagicMock(side_effect=Exception("Network timeout"))
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Failed to place order: Network timeout"):
        await service.place_order(order_params_data)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_place_order_exchange_client_not_initialized(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = None # Simulate client not being initialized
    order_params_data = HyperliquidPlaceOrderParams(asset="ETH", is_buy=True, sz=0.01, limit_px=2000.0, order_type={"limit": {"tif": "Gtc"}})
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid Exchange client not initialized."):
        await service.place_order(order_params_data)

# --- Tests for cancel_order ---

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None) # Bypass __init__
async def test_cancel_order_success(mock_hl_init_bypass):
    # Arrange
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()

    asset = "ETH"
    oid_to_cancel = 12345

    sdk_success_response = {"status": "ok", "response": {"type": "cancel", "data": {"statuses": ["success"]}}}
    service.exchange_client.cancel = MagicMock(return_value=sdk_success_response)
    service.wallet_address = TEST_WALLET_ADDRESS


    # Act
    response_dict = await service.cancel_order(asset, oid_to_cancel)

    # Assert
    service.exchange_client.cancel.assert_called_once_with(coin=asset, oid=oid_to_cancel)
    assert response_dict == sdk_success_response

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_cancel_order_sdk_returns_error_status(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    sdk_error_response = {"status": "error", "error": "Order already filled"}
    service.exchange_client.cancel = MagicMock(return_value=sdk_error_response)
    service.wallet_address = TEST_WALLET_ADDRESS


    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid API error on cancel: Order already filled"):
        await service.cancel_order("BTC", 54321)
    service.exchange_client.cancel.assert_called_once()

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_cancel_order_sdk_unexpected_response(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    sdk_unexpected_response = {"result": "cancelled_maybe"} # Does not match expected structure
    service.exchange_client.cancel = MagicMock(return_value=sdk_unexpected_response)
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Unexpected response from Hyperliquid SDK on cancel."):
        await service.cancel_order("SOL", 7890)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_cancel_order_sdk_raises_exception(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    service.exchange_client.cancel = MagicMock(side_effect=Exception("Network timeout on cancel"))
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Failed to cancel order: Network timeout on cancel"):
        await service.cancel_order("ETH", 111)

# --- Tests for get_order_status ---

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None) # Bypass __init__
async def test_get_order_status_success(mock_hl_init_bypass):
    # Arrange
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock() # Mock the info client instance

    user_address = TEST_WALLET_ADDRESS
    oid_to_check = 56789

    mock_order_detail = {"oid": oid_to_check, "asset": "BTC", "side": "b", "limitPx": "30000.0", "sz": "0.1"}
    sdk_success_response = {
        "order": mock_order_detail,
        "status": "open", # Or "filled", "canceled" etc.
        "fills": [{"price": "30000.0", "qty": "0.05", "time": 1678886400000}] # Example fill
    }
    service.info_client.order_status = MagicMock(return_value=sdk_success_response)
    service.wallet_address = TEST_WALLET_ADDRESS


    # Act
    response_model = await service.get_order_status(user_address, oid_to_check)

    # Assert
    service.info_client.order_status.assert_called_once_with(user=user_address, oid=oid_to_check)
    assert isinstance(response_model, HyperliquidOrderStatusInfo)
    assert response_model.order == mock_order_detail
    assert response_model.status == "open"
    assert len(response_model.fills) == 1
    assert response_model.fills[0]["qty"] == "0.05"

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_order_status_sdk_returns_error_message(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    sdk_error_response = {"error": "Order not found"} # Hyperliquid specific error format
    service.info_client.order_status = MagicMock(return_value=sdk_error_response)
    service.wallet_address = TEST_WALLET_ADDRESS


    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid API error: Order not found"):
        await service.get_order_status(TEST_WALLET_ADDRESS, 123)
    service.info_client.order_status.assert_called_once()

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_order_status_sdk_unexpected_response(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    sdk_unexpected_response = {"info": "some_info_but_not_order_status"}
    service.info_client.order_status = MagicMock(return_value=sdk_unexpected_response)
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Unexpected response structure for order status."):
        await service.get_order_status(TEST_WALLET_ADDRESS, 456)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_order_status_sdk_raises_exception(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    service.info_client.order_status = MagicMock(side_effect=Exception("Info API Network Error"))
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Failed to fetch order status: Info API Network Error"):
        await service.get_order_status(TEST_WALLET_ADDRESS, 789)

# --- Tests for get_detailed_account_summary, get_all_open_positions, get_all_open_orders ---

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None) # Bypass __init__
async def test_get_detailed_account_summary_success(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS

    # Mock the get_user_state method for these tests
    mock_raw_user_state = {
        "time": int(dt.datetime.now(timezone.utc).timestamp() * 1000),
        "crossMarginSummary": {
            "totalRawUsd": "12345.67",
            "totalNtlPos": "100.50", # Example PnL
        },
        "assetPositions": [
            {
                "asset": "ETH",
                "position": {"szi": "1.5", "entryPx": "2000.0", "unrealizedPnl": "50.25", "marginUsed": "300.0"}
            },
            { # Position with zero size, should be filtered out by service logic
                "asset": "BTC",
                "position": {"szi": "0", "entryPx": "30000.0", "unrealizedPnl": "0", "marginUsed": "0"}
            }
        ],
        "openOrders": [
            {"oid": 1, "coin": "ETH", "side": "b", "limitPx": "1900.0", "sz": "0.5", "timestamp": int(dt.datetime.now(timezone.utc).timestamp() * 1000 - 5000)},
            {"oid": 2, "coin": "BTC", "side": "s", "limitPx": "31000.0", "sz": "0.01", "timestamp": int(dt.datetime.now(timezone.utc).timestamp() * 1000 - 10000)},
            {"oid": 3, "coin": "SOL", "side": "b", "limitPx": "40.0", "sz": "10"}, # Missing timestamp, should be skipped by parser
        ]
    }
    service.get_user_state = MagicMock(return_value=mock_raw_user_state)

    summary = await service.get_detailed_account_summary(TEST_WALLET_ADDRESS)

    assert isinstance(summary, HyperliquidAccountSnapshot)
    assert summary.total_account_value_usd == "12345.67"
    assert summary.total_pnl_usd_str == "100.50"

    assert len(summary.parsed_positions) == 1 # BTC position with szi="0" should be filtered
    assert summary.parsed_positions[0].asset == "ETH"
    assert summary.parsed_positions[0].szi == "1.5"
    assert summary.parsed_positions[0].size_float == 1.5

    assert len(summary.parsed_open_orders) == 2 # SOL order missing timestamp should be filtered
    assert summary.parsed_open_orders[0].oid == 1
    assert summary.parsed_open_orders[0].asset == "ETH"
    assert summary.parsed_open_orders[1].oid == 2
    assert summary.parsed_open_orders[1].asset == "BTC"

    service.get_user_state.assert_called_once_with(TEST_WALLET_ADDRESS)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_detailed_account_summary_empty_state(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    mock_empty_user_state = {
        "time": int(dt.datetime.now(timezone.utc).timestamp() * 1000),
        "crossMarginSummary": {"totalRawUsd": "0", "totalNtlPos": "0"},
        "assetPositions": [],
        "openOrders": []
    }
    service.get_user_state = MagicMock(return_value=mock_empty_user_state)

    summary = await service.get_detailed_account_summary(TEST_WALLET_ADDRESS)

    assert isinstance(summary, HyperliquidAccountSnapshot)
    assert summary.total_account_value_usd == "0"
    assert len(summary.parsed_positions) == 0
    assert len(summary.parsed_open_orders) == 0

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_detailed_account_summary_no_user_state(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    service.get_user_state = MagicMock(return_value=None) # Simulate get_user_state returning None

    summary = await service.get_detailed_account_summary(TEST_WALLET_ADDRESS)
    assert summary is None

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_detailed_account_summary_parsing_error(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    # Malformed state that might cause Pydantic validation error or key error
    mock_malformed_user_state = {"time": "not_an_int", "crossMarginSummary": {}}
    service.get_user_state = MagicMock(return_value=mock_malformed_user_state)

    with pytest.raises(HyperliquidExecutionServiceError, match="Failed to parse account snapshot:"):
        await service.get_detailed_account_summary(TEST_WALLET_ADDRESS)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_all_open_positions_delegates_to_summary(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS

    mock_position = HyperliquidAssetPosition(asset="ETH", szi="1.0", entry_px="2000", unrealized_pnl="10", margin_used="200")
    mock_snapshot = HyperliquidAccountSnapshot(
        time=123, totalRawUsd="1000",
        parsed_positions=[mock_position], parsed_open_orders=[]
    )
    # Patch get_detailed_account_summary directly on the instance for this test
    service.get_detailed_account_summary = MagicMock(return_value=mock_snapshot)

    positions = await service.get_all_open_positions(TEST_WALLET_ADDRESS)

    assert len(positions) == 1
    assert positions[0].asset == "ETH"
    service.get_detailed_account_summary.assert_called_once_with(TEST_WALLET_ADDRESS)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_all_open_orders_delegates_to_summary(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS

    mock_order_item = HyperliquidOpenOrderItem(
        oid=1, asset="BTC", side="b", limit_px="30000", sz="0.01",
        timestamp=int(dt.datetime.now(timezone.utc).timestamp() * 1000),
        raw_order_data={}
    )
    mock_snapshot = HyperliquidAccountSnapshot(
        time=123, totalRawUsd="1000",
        parsed_positions=[], parsed_open_orders=[mock_order_item]
    )
    service.get_detailed_account_summary = MagicMock(return_value=mock_snapshot)

    orders = await service.get_all_open_orders(TEST_WALLET_ADDRESS)

    assert len(orders) == 1
    assert orders[0].asset == "BTC"
    service.get_detailed_account_summary.assert_called_once_with(TEST_WALLET_ADDRESS)

# --- Tests for get_asset_contexts ---

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_contexts_success():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    mock_contexts = [{"name": "ETH", "maxLeverage": 20}, {"name": "BTC", "maxLeverage": 10}]
    service.info_client.meta = MagicMock(return_value=mock_contexts)

    contexts = await service.get_asset_contexts()

    assert contexts == mock_contexts
    service.info_client.meta.assert_called_once()

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_contexts_sdk_returns_none():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    service.info_client.meta = MagicMock(return_value=None)

    contexts = await service.get_asset_contexts()

    assert contexts == [] # Service method should convert None to empty list
    service.info_client.meta.assert_called_once()

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_contexts_sdk_error():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    service.info_client.meta = MagicMock(side_effect=Exception("SDK Network Error"))

    with pytest.raises(HyperliquidExecutionServiceError, match="Failed to fetch asset contexts: SDK Network Error"):
        await service.get_asset_contexts()

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_contexts_client_not_initialized():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = None

    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid Info client not initialized."):
        await service.get_asset_contexts()

# --- Tests for get_funding_history ---

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_funding_history_success():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    mock_history = [{"coin": "ETH", "time": 1234567890, "usdc": "0.5"}]
    service.info_client.funding_history = MagicMock(return_value=mock_history)
    user_address = "0xUser1"
    start_time = 1234500000
    end_time = 1234600000

    history = await service.get_funding_history(user_address, start_time, end_time)

    assert history == mock_history
    service.info_client.funding_history.assert_called_once_with(user_address, start_time, end_time)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_funding_history_sdk_returns_non_list():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    service.info_client.funding_history = MagicMock(return_value={"error": "unexpected response"}) # Non-list
    user_address = "0xUser1"
    start_time = 1234500000

    history = await service.get_funding_history(user_address, start_time)
    assert history == [] # Service method should convert non-list to empty list
    service.info_client.funding_history.assert_called_once()


@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_funding_history_sdk_error():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    service.info_client.funding_history = MagicMock(side_effect=Exception("SDK Funding Error"))
    user_address = "0xUser1"
    start_time = 1234500000

    with pytest.raises(HyperliquidExecutionServiceError, match="Failed to fetch funding history: SDK Funding Error"):
        await service.get_funding_history(user_address, start_time)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_funding_history_client_not_initialized():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = None
    user_address = "0xUser1"
    start_time = 1234500000

    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid Info client not initialized."):
        await service.get_funding_history(user_address, start_time)


# --- Tests for get_account_margin_summary ---
from python_ai_services.models.hyperliquid_models import HyperliquidMarginSummary # Ensure imported

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_account_margin_summary_success_cross():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS # Crucial for this method
    mock_margin_data = {"accountValue": "1000", "totalRawUsd": "1000", "totalNtlPos": "100", "totalMarginUsed": "50"}
    mock_user_state = {"crossMarginSummary": mock_margin_data}
    # Patch get_user_state directly on the instance for this test
    service.get_user_state = MagicMock(return_value=mock_user_state)
    # Mock info_client just to satisfy the initial check in the method
    service.info_client = MagicMock()


    summary = await service.get_account_margin_summary()

    assert isinstance(summary, HyperliquidMarginSummary)
    assert summary.account_value == "1000"
    assert summary.total_margin_used == "50"
    service.get_user_state.assert_called_once_with(TEST_WALLET_ADDRESS)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_account_margin_summary_success_spot_fallback():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    mock_margin_data = {"accountValue": "900", "totalRawUsd": "900", "totalNtlPos": "90", "totalMarginUsed": "40"}
    # No crossMarginSummary, only spotMarginSummary
    mock_user_state = {"spotMarginSummary": mock_margin_data}
    service.get_user_state = MagicMock(return_value=mock_user_state)
    service.info_client = MagicMock()


    summary = await service.get_account_margin_summary()

    assert isinstance(summary, HyperliquidMarginSummary)
    assert summary.account_value == "900"
    service.get_user_state.assert_called_once_with(TEST_WALLET_ADDRESS)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_account_margin_summary_no_margin_data():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    mock_user_state = {} # No margin summary data
    service.get_user_state = MagicMock(return_value=mock_user_state)
    service.info_client = MagicMock()


    summary = await service.get_account_margin_summary()
    assert summary is None

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_account_margin_summary_get_user_state_returns_none():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    service.get_user_state = MagicMock(return_value=None) # get_user_state fails
    service.info_client = MagicMock()


    summary = await service.get_account_margin_summary()
    assert summary is None


@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_account_margin_summary_sdk_error_via_get_user_state():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    # Simulate get_user_state raising an error (as if info_client.user_state failed)
    service.get_user_state = MagicMock(side_effect=HyperliquidExecutionServiceError("SDK Error from user_state"))
    service.info_client = MagicMock() # Still need this for the initial check

    with pytest.raises(HyperliquidExecutionServiceError, match="SDK Error from user_state"):
        await service.get_account_margin_summary()

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_account_margin_summary_client_not_initialized():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = None
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid Info client not initialized."):
        await service.get_account_margin_summary()

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_account_margin_summary_malformed_data():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    # Missing 'totalRawUsd', which is required by HyperliquidMarginSummary
    mock_margin_data = {"accountValue": "1000", "totalNtlPos": "100", "totalMarginUsed": "50"}
    mock_user_state = {"crossMarginSummary": mock_margin_data}
    service.get_user_state = MagicMock(return_value=mock_user_state)
    service.info_client = MagicMock()

    # Pydantic validation error will be wrapped by HyperliquidExecutionServiceError
    with pytest.raises(HyperliquidExecutionServiceError, match="Margin summary data is incomplete. Missing: totalRawUsd"):
        await service.get_account_margin_summary()


# --- Tests for get_asset_leverage ---

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_leverage_success():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    asset_symbol = "ETH"
    mock_leverage_info = {"type": "cross", "value": 20}
    mock_user_state = {
        "assetPositions": [
            {"asset": "BTC", "position": {"leverage": {"type": "isolated", "value": 10}}},
            {"asset": "ETH", "position": {"leverage": mock_leverage_info}}
        ]
    }
    service.get_user_state = MagicMock(return_value=mock_user_state)
    service.info_client = MagicMock()

    leverage = await service.get_asset_leverage(asset_symbol)

    assert leverage == mock_leverage_info
    service.get_user_state.assert_called_once_with(TEST_WALLET_ADDRESS)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_leverage_asset_not_found():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    mock_user_state = {"assetPositions": [{"asset": "BTC", "position": {"leverage": {"type": "isolated", "value": 10}}}]}
    service.get_user_state = MagicMock(return_value=mock_user_state)
    service.info_client = MagicMock()

    leverage = await service.get_asset_leverage("NONEXISTENT_ASSET")
    assert leverage is None

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_leverage_no_leverage_info():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    mock_user_state = {"assetPositions": [{"asset": "ETH", "position": {}}]} # No leverage key
    service.get_user_state = MagicMock(return_value=mock_user_state)
    service.info_client = MagicMock()

    leverage = await service.get_asset_leverage("ETH")
    assert leverage is None

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_leverage_no_asset_positions():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    mock_user_state = {} # No assetPositions key
    service.get_user_state = MagicMock(return_value=mock_user_state)
    service.info_client = MagicMock()

    leverage = await service.get_asset_leverage("ETH")
    assert leverage is None

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_leverage_user_address_override():
    service = HyperliquidExecutionService("addr", "key")
    # service.wallet_address is not used if user_address is provided
    custom_address = "0xCustomUser"
    mock_leverage_info = {"type": "cross", "value": 5}
    mock_user_state = {"assetPositions": [{"asset": "ETH", "position": {"leverage": mock_leverage_info}}]}
    service.get_user_state = MagicMock(return_value=mock_user_state)
    service.info_client = MagicMock()

    leverage = await service.get_asset_leverage("ETH", user_address=custom_address)
    assert leverage == mock_leverage_info
    service.get_user_state.assert_called_once_with(custom_address)


@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_leverage_sdk_error():
    service = HyperliquidExecutionService("addr", "key")
    service.wallet_address = TEST_WALLET_ADDRESS
    service.get_user_state = MagicMock(side_effect=HyperliquidExecutionServiceError("SDK Error"))
    service.info_client = MagicMock()

    with pytest.raises(HyperliquidExecutionServiceError, match="SDK Error"):
        await service.get_asset_leverage("ETH")

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_asset_leverage_client_not_initialized():
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = None
    service.wallet_address = TEST_WALLET_ADDRESS

    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid Info client not initialized."):
        await service.get_asset_leverage("ETH")


# --- Tests for set_asset_leverage ---

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_set_asset_leverage_success():
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    asset_symbol = "ETH"
    leverage = 20
    is_cross_margin = True
    sdk_response = {"status": "ok", "response": {"type": "updateLeverage", "data": "Successfully updated margin"}}
    service.exchange_client.update_leverage = MagicMock(return_value=sdk_response)

    response = await service.set_asset_leverage(asset_symbol, leverage, is_cross_margin)

    assert response == sdk_response
    service.exchange_client.update_leverage.assert_called_once_with(
        coin=asset_symbol, is_cross_margin=is_cross_margin, leverage=leverage
    )

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_set_asset_leverage_success_new_response_format():
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    asset_symbol = "BTC"
    leverage = 10
    is_cross_margin = False
    # Example of the newer list-based success response for data field
    sdk_response_new_format = {
        "status": "ok",
        "response": {
            "type": "updateLeverage",
            "data": [{"name": "BTC", "cross": False, "leverage": 10}]
        }
    }
    service.exchange_client.update_leverage = MagicMock(return_value=sdk_response_new_format)

    response = await service.set_asset_leverage(asset_symbol, leverage, is_cross_margin)

    assert response == sdk_response_new_format
    service.exchange_client.update_leverage.assert_called_once_with(
        coin=asset_symbol, is_cross_margin=is_cross_margin, leverage=leverage
    )


@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_set_asset_leverage_sdk_returns_error_status():
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    sdk_error_response = {"status": "error", "error": "Leverage too high"}
    service.exchange_client.update_leverage = MagicMock(return_value=sdk_error_response)

    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid API error on set_leverage: Leverage too high"):
        await service.set_asset_leverage("ETH", 100, True)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_set_asset_leverage_sdk_raises_exception():
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock()
    service.exchange_client.update_leverage = MagicMock(side_effect=Exception("SDK Update Error"))

    with pytest.raises(HyperliquidExecutionServiceError, match="Failed to set asset leverage: SDK Update Error"):
        await service.set_asset_leverage("ETH", 10, True)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_set_asset_leverage_client_not_initialized():
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = None

    with pytest.raises(HyperliquidExecutionServiceError, match="Hyperliquid Exchange client not initialized."):
        await service.set_asset_leverage("ETH", 10, True)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_set_asset_leverage_invalid_leverage_value():
    service = HyperliquidExecutionService("addr", "key")
    service.exchange_client = MagicMock() # Needs to be mocked even if not called

    with pytest.raises(HyperliquidExecutionServiceError, match="Invalid leverage value provided."):
        await service.set_asset_leverage("ETH", 0, True) # Leverage 0 is invalid

    with pytest.raises(HyperliquidExecutionServiceError, match="Invalid leverage value provided."):
        await service.set_asset_leverage("ETH", -5, True) # Negative leverage

    # Check that it's not called if validation fails
    service.exchange_client.update_leverage.assert_not_called()


# --- Tests for get_fills_for_order ---

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_fills_for_order_success(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    user_address = "0xUser"
    oid = 123
    mock_fills_data = [{"px": "2000", "qty": "0.1", "time": 1678886400000}, {"px": "2001", "qty": "0.2", "time": 1678886400001}]
    sdk_response = {"order": {}, "status": "filled", "fills": mock_fills_data}
    service.info_client.order_status = MagicMock(return_value=sdk_response)

    fills = await service.get_fills_for_order(user_address, oid)

    assert fills == mock_fills_data
    service.info_client.order_status.assert_called_once_with(user=user_address, oid=oid)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_fills_for_order_no_fills_in_response(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    # Scenario 1: "fills" key present but list is empty
    sdk_response_empty_fills = {"order": {}, "status": "open", "fills": []}
    service.info_client.order_status = MagicMock(return_value=sdk_response_empty_fills)
    fills = await service.get_fills_for_order("user", 124)
    assert fills == []
    # Scenario 2: "fills" key is missing
    sdk_response_missing_fills_key = {"order": {}, "status": "open"}
    service.info_client.order_status = MagicMock(return_value=sdk_response_missing_fills_key)
    fills_missing = await service.get_fills_for_order("user", 125)
    assert fills_missing == []
     # Scenario 3: "fills" is not a list
    sdk_response_fills_not_list = {"order": {}, "status": "open", "fills": "not_a_list"}
    service.info_client.order_status = MagicMock(return_value=sdk_response_fills_not_list)
    fills_not_list = await service.get_fills_for_order("user", 126)
    assert fills_not_list == []


@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_fills_for_order_api_error_response(mock_hl_init_bypass, caplog):
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    sdk_api_error_response = {"error": "Order not found or archived"}
    service.info_client.order_status = MagicMock(return_value=sdk_api_error_response)

    fills = await service.get_fills_for_order("user", 127)
    assert fills == []
    assert "API error when fetching order status for fills (OID 127): Order not found or archived" in caplog.text


@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_fills_for_order_unexpected_response_structure(mock_hl_init_bypass, caplog):
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    sdk_unexpected_response = {"data": "some_other_format"} # Does not contain 'fills' or 'error'
    service.info_client.order_status = MagicMock(return_value=sdk_unexpected_response)

    fills = await service.get_fills_for_order("user", 128)
    assert fills == []
    assert "Unexpected response structure or no fills found for OID 128" in caplog.text

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_fills_for_order_sdk_call_raises_exception(mock_hl_init_bypass):
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = MagicMock()
    service.info_client.order_status = MagicMock(side_effect=Exception("SDK network failure"))

    with pytest.raises(HyperliquidExecutionServiceError, match="Failed to fetch fills for order 129: SDK network failure"):
        await service.get_fills_for_order("user", 129)

@pytest.mark.asyncio
@patch.object(HyperliquidExecutionService, '__init__', lambda self, *args, **kwargs: None)
async def test_get_fills_for_order_info_client_not_initialized(mock_hl_init_bypass, caplog):
    service = HyperliquidExecutionService("addr", "key")
    service.info_client = None # Simulate client not initialized

    fills = await service.get_fills_for_order("user", 130)
    assert fills == []
    assert "Hyperliquid Info client not initialized. Cannot fetch fills." in caplog.text
