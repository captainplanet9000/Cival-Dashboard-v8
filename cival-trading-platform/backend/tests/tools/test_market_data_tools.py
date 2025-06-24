import pytest
import pytest_asyncio # For async tests
import json
from typing import Dict, Any, List, Optional
from unittest import mock # For patching app_services
from unittest.mock import AsyncMock, MagicMock # For mocking async methods

# Adjust import path based on test execution context
from python_ai_services.tools.market_data_tools import fetch_market_data_tool, FetchMarketDataArgs
# Import MarketDataService to mock its instance type
from python_ai_services.services.market_data_service import MarketDataService

# Path for patching app_services in the context of the tool's module
APP_SERVICES_PATH = "python_ai_services.tools.market_data_tools.app_services"

# --- Tests for fetch_market_data_tool (Refactored for Async and Service Call) ---

@pytest.mark.asyncio
async def test_fetch_market_data_tool_success_service_call():
    """Test fetch_market_data_tool successfully calls MarketDataService."""
    symbol = "TEST/USD"
    timeframe = "1d"
    historical_days = 7
    expected_limit = 7 # For 1d timeframe, limit = historical_days

    mock_service_data = [{"timestamp": "2023-01-01T00:00:00Z", "close": 100}]

    mock_mds_instance = AsyncMock(spec=MarketDataService)
    mock_mds_instance.get_historical_data = AsyncMock(return_value=mock_service_data)

    mock_app_services = {"market_data_service": mock_mds_instance}

    with mock.patch(APP_SERVICES_PATH, mock_app_services):
        result_json = await fetch_market_data_tool(symbol=symbol, timeframe=timeframe, historical_days=historical_days)

    assert isinstance(result_json, str)
    data = json.loads(result_json)

    mock_mds_instance.get_historical_data.assert_called_once_with(symbol=symbol, interval=timeframe, limit=expected_limit)
    assert data["symbol"] == symbol
    assert data["timeframe"] == timeframe
    assert data["historical_days"] == historical_days # Field name updated in tool
    assert data["limit_calculated"] == expected_limit
    assert data["data_source_status"] == "service_success"
    assert data["data_points_returned"] == len(mock_service_data)
    assert data["data"] == mock_service_data
    assert data["current_price_simulated"] == mock_service_data[-1]["close"]

@pytest.mark.asyncio
async def test_fetch_market_data_tool_service_unavailable_uses_mock():
    """Test tool falls back to mock data if MarketDataService is not in app_services."""
    symbol = "MOCK/USD"
    timeframe = "1h"
    historical_days = 1
    expected_limit = 24 # 1 day * 24 hours

    # Simulate app_services not containing market_data_service
    with mock.patch(APP_SERVICES_PATH, {}) as mock_empty_services:
        result_json = await fetch_market_data_tool(symbol=symbol, timeframe=timeframe, historical_days=historical_days)

    data = json.loads(result_json)
    assert data["data_source_status"] == "service_unavailable_mock_fallback"
    assert data["symbol"] == symbol
    assert data["limit_calculated"] == expected_limit
    assert len(data["data"]) == expected_limit
    assert data["current_price_simulated"] == data["data"][-1]["close"] # from mock
    # Mock data from _generate_mock_ohlcv_data does not include 'symbol' in each record anymore.
    # assert data["data"][0].get("symbol") == symbol # This check is removed/modified

@pytest.mark.asyncio
async def test_fetch_market_data_tool_service_returns_no_data_uses_mock():
    """Test tool falls back to mock data if service returns None or empty list."""
    symbol = "NODATA/SRV"
    timeframe = "1d"
    historical_days = 3

    mock_mds_instance = AsyncMock(spec=MarketDataService)
    mock_mds_instance.get_historical_data = AsyncMock(return_value=[]) # Simulate empty list
    mock_app_services = {"market_data_service": mock_mds_instance}

    with mock.patch(APP_SERVICES_PATH, mock_app_services):
        result_json = await fetch_market_data_tool(symbol=symbol, timeframe=timeframe, historical_days=historical_days)

    data = json.loads(result_json)
    assert data["data_source_status"] == "service_no_data_mock_fallback"
    assert data["symbol"] == symbol
    assert data["limit_calculated"] == historical_days # For 1d
    assert len(data["data"]) == historical_days
    assert data["current_price_simulated"] == data["data"][-1]["close"] # from mock

@pytest.mark.asyncio
async def test_fetch_market_data_tool_service_raises_exception_uses_mock():
    """Test tool falls back to mock data if service call raises an exception."""
    symbol = "EXCEPT/SRV"
    timeframe = "4h"
    historical_days = 2

    mock_mds_instance = AsyncMock(spec=MarketDataService)
    mock_mds_instance.get_historical_data = AsyncMock(side_effect=Exception("Service network error"))
    mock_app_services = {"market_data_service": mock_mds_instance}

    with mock.patch(APP_SERVICES_PATH, mock_app_services):
        result_json = await fetch_market_data_tool(symbol=symbol, timeframe=timeframe, historical_days=historical_days)

    data = json.loads(result_json)
    assert data["data_source_status"] == "service_error_mock_fallback"
    assert data["symbol"] == symbol
    assert data["limit_calculated"] == 2 * (24 // 4) # 2 days, 4h timeframe
    assert len(data["data"]) > 0
    assert data["current_price_simulated"] == data["data"][-1]["close"] # from mock

@pytest.mark.asyncio
@pytest.mark.parametrize("timeframe, days, expected_limit", [
    ("1d", 10, 10),
    ("1h", 1, 24),
    ("4h", 2, 12), # 2 days * (24/4) candles
    ("30min", 1, 48), # 1 day * (24*60/30) candles
    ("5h", 1, 24), # Falls back to 24 per day due to uneven division
])
async def test_fetch_market_data_tool_limit_calculation(timeframe, days, expected_limit):
    """Test limit calculation for various timeframes."""
    symbol = f"LIMIT/{timeframe}"

    mock_service_data = [{"timestamp": "2023-01-01T00:00:00Z", "close": 100}]*expected_limit
    mock_mds_instance = AsyncMock(spec=MarketDataService)
    mock_mds_instance.get_historical_data = AsyncMock(return_value=mock_service_data)
    mock_app_services = {"market_data_service": mock_mds_instance}

    with mock.patch(APP_SERVICES_PATH, mock_app_services):
        result_json = await fetch_market_data_tool(symbol=symbol, timeframe=timeframe, historical_days=days)

    data = json.loads(result_json)
    mock_mds_instance.get_historical_data.assert_called_once_with(symbol=symbol, interval=timeframe, limit=expected_limit)
    assert data["limit_calculated"] == expected_limit
    assert data["data_points_returned"] == expected_limit
    assert len(data["data"]) == expected_limit


def test_fetch_market_data_tool_args_schema(): # This test remains sync as it checks a class attribute
    """Test that the tool has the correct args_schema linked."""
    if hasattr(fetch_market_data_tool, 'args_schema'):
        assert fetch_market_data_tool.args_schema == FetchMarketDataArgs
    elif hasattr(fetch_market_data_tool, '_crew_tool_input_schema'):
         assert fetch_market_data_tool._crew_tool_input_schema == FetchMarketDataArgs
    else:
        pytest.skip("Tool schema attribute not found, decorator might be a simple stub or crewai internal changed.")

@pytest.mark.asyncio
async def test_fetch_market_data_tool_default_days_with_service_call():
    """Test default historical_days is used when calling via schema with service."""
    symbol = "DEFAULT/DAYS"
    timeframe = "1d"
    args_model = FetchMarketDataArgs(symbol=symbol, timeframe=timeframe) # historical_days uses Pydantic default (30)
    expected_limit = 30 # Default days for 1d timeframe

    mock_service_data = [{"timestamp": "2023-01-01T00:00:00Z", "close": 100}] * expected_limit
    mock_mds_instance = AsyncMock(spec=MarketDataService)
    mock_mds_instance.get_historical_data = AsyncMock(return_value=mock_service_data)
    mock_app_services = {"market_data_service": mock_mds_instance}

    with mock.patch(APP_SERVICES_PATH, mock_app_services):
        # Call tool using values from Pydantic model after instantiation
        result_json = await fetch_market_data_tool(
            symbol=args_model.symbol,
            timeframe=args_model.timeframe,
            historical_days=args_model.historical_days # This will be 30
        )

    data = json.loads(result_json)
    mock_mds_instance.get_historical_data.assert_called_once_with(symbol=symbol, interval=timeframe, limit=expected_limit)
    assert data["historical_days"] == 30 # Field name updated
    assert data["limit_calculated"] == expected_limit
    assert data["data_points_returned"] == expected_limit
