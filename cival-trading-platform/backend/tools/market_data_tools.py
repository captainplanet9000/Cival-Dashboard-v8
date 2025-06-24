from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from loguru import logger
import json
import pandas as pd
import numpy as np # For mock data generation if service call fails or for the stub path

# Attempt to import the 'tool' decorator from crewai_tools
try:
    from crewai_tools import tool
except ImportError:
    logger.warning("crewai_tools.tool not found. Using a placeholder decorator '@tool_stub'.")
    def tool_stub(name: str, args_schema: Optional[Any] = None, description: Optional[str] = None):
        def decorator(func):
            func.tool_name = name
            func.args_schema = args_schema
            func.description = description
            logger.debug(f"Tool stub '{name}' registered with args_schema: {args_schema}, desc: {description}")
            return func
        return decorator
    tool = tool_stub

# Import MarketDataService and the global services registry
# This direct import is a simplification for this subtask.
# In a production CrewAI setup, tools often get dependencies injected or use a service locator.
try:
    from ..services.market_data_service import MarketDataService
    from ..main import services as app_services # Accessing the global 'services' dict from main.py
    SERVICE_ACCESS_METHOD = "app_services_dict"
except ImportError:
    logger.warning("Could not import MarketDataService or app_services from ..services/..main. Tool will rely on mock data only.")
    MarketDataService = None
    app_services = None
    SERVICE_ACCESS_METHOD = "mock_only"


class FetchMarketDataArgs(BaseModel):
    """
    Input arguments for the Fetch Market Data Tool.
    Specifies the symbol, timeframe, and historical data range for market data retrieval.
    """
    symbol: str = Field(..., description="The trading symbol to fetch market data for (e.g., 'BTC-USD', 'AAPL').")
    timeframe: str = Field(..., description="The timeframe for the data (e.g., '1h', '4h', '1d'). Common values might be '1min', '5min', '15min', '1h', '4h', '1d', '1w'.")
    historical_days: int = Field(default=30, description="Number of past days of historical data to fetch.", gt=0)


@tool("Fetch Market Data Tool", args_schema=FetchMarketDataArgs, description="Fetches historical OHLCV market data for a given financial symbol and timeframe. Includes simulated current price.")
async def fetch_market_data_tool(symbol: str, timeframe: str, historical_days: int = 30) -> str:
    """
    Fetches historical OHLCV market data for a specified trading symbol and timeframe.
    This tool attempts to use the MarketDataService. If unavailable or if an error occurs,
    it falls back to generating mock data.

    Args:
        symbol: The trading symbol (e.g., 'BTC-USD', 'AAPL').
        timeframe: The timeframe for the data (e.g., '1h', '1d'). Corresponds to 'interval' in MarketDataService.
        historical_days: Number of past days of historical OHLCV data to retrieve.

    Returns:
        A JSON string representing a dictionary with market data including:
        'symbol', 'timeframe', 'requested_historical_days', 'limit_calculated' (number of candles),
        'data' (a list of OHLCV records), and 'current_price_simulated'.
        Returns an error JSON if the service call fails and mock generation also fails.
    """
    logger.info(f"TOOL: Fetching market data for {symbol}, timeframe {timeframe}, last {historical_days} days.")

    limit = historical_days # Default for '1d'
    if 'h' in timeframe:
        try:
            hours = int(timeframe.replace('h', ''))
            if hours > 0 and 24 % hours == 0:
                limit = historical_days * (24 // hours)
            else: # Default to 24 candles per day if timeframe is unusual, e.g. 5h
                limit = historical_days * 24
                logger.warning(f"Uncommon hour timeframe '{timeframe}', defaulting limit calculation to 24 periods per day.")
        except ValueError:
            limit = historical_days * 24 # Default to 1h if parse fails for hour format
            logger.warning(f"Could not parse hour timeframe '{timeframe}', defaulting limit calculation to 24 periods per day.")
    elif 'min' in timeframe:
        try:
            minutes = int(timeframe.replace('min', ''))
            if minutes > 0 and (60*24) % minutes == 0 :
                 limit = historical_days * ( (24 * 60) // minutes)
            else: # Default to a large number of 1-min candles per day if unusual
                limit = historical_days * 24 * 60
                logger.warning(f"Uncommon minute timeframe '{timeframe}', defaulting limit calculation to 1440 periods per day.")
        except ValueError:
            limit = historical_days * 24 * 60 # Default to 1min if parse fails
            logger.warning(f"Could not parse minute timeframe '{timeframe}', defaulting limit calculation to 1440 periods per day.")

    logger.debug(f"Calculated limit: {limit} candles for {historical_days} days with timeframe {timeframe}.")

    data_to_return: List[Dict[str, Any]] = []
    data_source_status: str = "unknown"
    current_price: Optional[float] = None

    market_data_service: Optional[MarketDataService] = None
    if SERVICE_ACCESS_METHOD == "app_services_dict" and app_services:
        market_data_service = app_services.get("market_data_service")

    if market_data_service:
        try:
            logger.info(f"TOOL: Calling MarketDataService.get_historical_data(symbol='{symbol}', interval='{timeframe}', limit={limit})")
            actual_call_result = await market_data_service.get_historical_data(
                symbol=symbol,
                interval=timeframe,
                limit=limit
            )
            if actual_call_result: # Not None and not empty list
                data_to_return = actual_call_result
                data_source_status = "service_success"
                logger.info(f"Successfully retrieved {len(data_to_return)} data points from MarketDataService for {symbol}.")
            else: # Service returned None or empty list
                logger.warning(f"MarketDataService returned no data for {symbol}, {timeframe}. Falling back to mock data.")
                data_to_return = _generate_mock_ohlcv_data(symbol, timeframe, limit)
                data_source_status = "service_no_data_mock_fallback"
        except Exception as e:
            logger.error(f"Error calling MarketDataService for {symbol}, {timeframe}: {e}. Falling back to mock data.")
            data_to_return = _generate_mock_ohlcv_data(symbol, timeframe, limit)
            data_source_status = "service_error_mock_fallback"
    else:
        logger.warning(f"MarketDataService not available (SERVICE_ACCESS_METHOD: {SERVICE_ACCESS_METHOD}). Falling back to mock data.")
        # Limit calculation is already done above, so it's available here too.
        data_to_return = _generate_mock_ohlcv_data(symbol, timeframe, limit)
        data_source_status = "service_unavailable_mock_fallback"

    if data_to_return and isinstance(data_to_return[-1], dict) and 'close' in data_to_return[-1]:
        current_price = data_to_return[-1]['close']

    output_payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "historical_days": historical_days, # Renamed from requested_historical_days for consistency
        "limit_calculated": limit,
        "data_source_status": data_source_status,
        "current_price_simulated": current_price,
        "data_points_returned": len(data_to_return),
        "data": data_to_return
    }

    try:
        return json.dumps(output_payload, default=str)
    except (TypeError, OverflowError) as e:
        logger.error(f"TOOL: Error serializing market data to JSON for {symbol}: {e}")
        return json.dumps({
            "error": "Failed to serialize market data.",
            "details": str(e),
            "symbol": symbol,
            "timeframe": timeframe,
            "data_source_status": data_source_status # Include status even in serialization error
        })

def _calculate_limit_for_tool(historical_days: int, timeframe: str) -> int:
    """
    Calculates the number of data points (limit) based on historical days and timeframe.
    (This function was implicitly part of the main tool logic before)
    """
    limit = historical_days
    if 'h' in timeframe:
        try:
            hours = int(timeframe.replace('h', ''))
            if hours > 0 and 24 % hours == 0:
                limit = historical_days * (24 // hours)
            else:
                limit = historical_days * 24
        except ValueError:
            limit = historical_days * 24
    elif 'min' in timeframe:
        try:
            minutes = int(timeframe.replace('min', ''))
            if minutes > 0 and (60*24) % minutes == 0 :
                 limit = historical_days * ( (24 * 60) // minutes)
            else:
                limit = historical_days * 24 * 60
        except ValueError:
            limit = historical_days * 24 * 60
    return limit

def _symbol_to_int_for_mock(symbol_str: str) -> int:
    """Helper to generate somewhat consistent integer from symbol string for mock data."""
    val = 0
    for char in symbol_str:
        val += ord(char)
    return val % 100

def _generate_mock_ohlcv_data(symbol: str, timeframe: str, limit: int) -> List[Dict[str, Any]]:
    """
    Generates mock OHLCV data for a given symbol, timeframe, and limit.
    """
    logger.info(f"Generating mock OHLCV data for {symbol}, timeframe {timeframe}, limit {limit}.")
    mock_ohlcv_data: List[Dict[str, Any]] = []
    # Use a consistent base price modifier based on symbol to make mock data somewhat unique per symbol
    base_price = 150.0 + _symbol_to_int_for_mock(symbol)

    # Determine the timedelta based on timeframe more accurately
    if 'h' in timeframe:
        td_unit = pd.Timedelta(hours=int(timeframe.replace('h', '') or '1'))
    elif 'min' in timeframe:
        td_unit = pd.Timedelta(minutes=int(timeframe.replace('min', '') or '1'))
    elif 'd' in timeframe:
        td_unit = pd.Timedelta(days=int(timeframe.replace('d', '') or '1'))
    else: # Default to daily if timeframe is not recognized
        td_unit = pd.Timedelta(days=1)
        logger.warning(f"Unrecognized timeframe '{timeframe}' for mock data generation, defaulting to daily steps.")

    # Start date for mock data generation so it ends near 'today'
    current_dt = pd.Timestamp.utcnow().normalize() - pd.Timedelta(days=1) * (limit * td_unit.total_seconds() // (24*3600)) # Approximate start
    current_dt = current_dt.replace(hour=0, minute=0, second=0, microsecond=0) # Normalize start time

    for i in range(limit):
        current_dt += td_unit # Increment by the timeframe unit

        # Ensure open, high, low, close are in logical order
        open_price = round(base_price + np.random.randn() * 2, 2)
        price_var = np.random.rand() * 5
        high_price = round(max(open_price, open_price + price_var), 2)
        low_price = round(min(open_price, open_price - price_var), 2)
        close_price = round(np.random.uniform(low_price, high_price), 2)

        volume = int(10000 + np.random.rand() * 5000 * (1 + 0.1 * (i % 5))) # Some volume variation
        base_price = close_price # Next candle's open is based on this close (simplified)

        mock_ohlcv_data.append({
            "timestamp": current_dt.isoformat().replace("+00:00", "Z"),
            # "symbol": symbol, # Standard OHLCV from exchanges often don't repeat symbol in each record
            "open": open_price, "high": high_price, "low": low_price, "close": close_price, "volume": volume
        })
    return mock_ohlcv_data

async def main_async_example():
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), colorize=True, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="INFO")

    # This example assumes app_services might be populated if run within a broader context.
    # For standalone tool test, it will likely use mock data.
    logger.info(f"Service access method for tool: {SERVICE_ACCESS_METHOD}")

    # Temporarily set up a mock service if not available, for example demonstration
    original_app_services = app_services
    if SERVICE_ACCESS_METHOD == "app_services_dict" and (app_services is None or "market_data_service" not in app_services):
        logger.warning("app_services is None or MarketDataService not found. Using a temporary mock for example.")

        class MockMarketDataServiceForExample: # Renamed to avoid conflict
            async def get_historical_data(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
                logger.info(f"MOCK MarketDataServiceForExample called: get_historical_data for {symbol}, {interval}, {limit}")
                if symbol == "REALSERVICE_TEST": # Simulate actual service data
                    return [{"timestamp": (pd.Timestamp.utcnow() - pd.Timedelta(days=1)).isoformat(), "open": 100, "high": 102, "low": 99, "close": 101, "volume": 5000}]
                return [] # Simulate service returning no data for other symbols

        global app_services # Allow modification of global for this example context
        app_services = {"market_data_service": MockMarketDataServiceForExample()} # type: ignore
        logger.info("Using a temporary mock MarketDataService for this example run.")

    # Example 1: Service returns data
    args_real_service = FetchMarketDataArgs(symbol="REALSERVICE_TEST", timeframe="1d", historical_days=1)
    json_output_real = await fetch_market_data_tool(**args_real_service.model_dump())
    logger.info(f"Fetch Market Data Tool Output (REALSERVICE_TEST, 1d, 1 day - service success):\n{json.dumps(json.loads(json_output_real), indent=2, default=str)}")

    # Example 2: Service returns no data, fallback to mock
    args_service_no_data = FetchMarketDataArgs(symbol="NO_DATA_SYM", timeframe="1h", historical_days=1)
    json_output_no_data = await fetch_market_data_tool(**args_service_no_data.model_dump())
    logger.info(f"Fetch Market Data Tool Output (NO_DATA_SYM, 1h, 1 day - service_no_data_mock_fallback):\n{json.dumps(json.loads(json_output_no_data), indent=2, default=str)}")

    # Example 3: Service error (requires modifying the mock service to raise an error, or setting service to None)
    if app_services and "market_data_service" in app_services:
        app_services["market_data_service"] = None # Simulate service becoming unavailable
        logger.info("Simulating MarketDataService becoming unavailable for next call.")
    args_service_error = FetchMarketDataArgs(symbol="ERROR_SYM", timeframe="1d", historical_days=2)
    json_output_error = await fetch_market_data_tool(**args_service_error.model_dump())
    logger.info(f"Fetch Market Data Tool Output (ERROR_SYM, 1d, 2 days - service_unavailable_mock_fallback):\n{json.dumps(json.loads(json_output_error), indent=2, default=str)}")

    # Restore original app_services if it was changed
    if SERVICE_ACCESS_METHOD == "app_services_dict":
        app_services = original_app_services
        logger.info("Restored original app_services.")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main_async_example())
