import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from datetime import datetime, date, timezone, timedelta # Ensure timedelta is imported
import uuid
from typing import List, Dict, Any, Optional

# Models and Services to test/mock
from python_ai_services.services.strategy_visualization_service import StrategyVisualizationService, StrategyVisualizationServiceError
from python_ai_services.services.strategy_config_service import StrategyConfigService # For mocking
from python_ai_services.models.strategy_models import StrategyConfig, DarvasBoxParams, StrategyTimeframe # Example
from python_ai_services.models.visualization_models import StrategyVisualizationRequest, StrategyVisualizationDataResponse, OHLCVBar, IndicatorDataPoint, SignalDataPoint
from python_ai_services.models.trading_history_models import TradeRecord, TradeSide, OrderType, OrderStatus # Assuming OrderType, OrderStatus enums

# --- Fixtures ---

@pytest_asyncio.fixture
async def mock_supabase_client_viz(): # viz for Visualization service tests
    client = MagicMock()
    # Mock for fetching trading_history
    trade_history_mock_execute = AsyncMock()
    # Adjust the chain of returns to match the actual Supabase client usage in the service
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.lt.return_value.order.return_value.execute = trade_history_mock_execute
    return client

@pytest_asyncio.fixture
async def mock_strategy_config_service_viz():
    service = MagicMock(spec=StrategyConfigService)
    service.get_strategy_config = AsyncMock()
    return service

@pytest_asyncio.fixture
async def visualization_service(mock_supabase_client_viz, mock_strategy_config_service_viz):
    return StrategyVisualizationService(
        supabase_client=mock_supabase_client_viz,
        strategy_config_service=mock_strategy_config_service_viz
    )

# --- Sample Data ---
def get_sample_price_df(start_date_dt: datetime, num_days: int) -> pd.DataFrame:
    dates = pd.to_datetime([start_date_dt + timedelta(days=i) for i in range(num_days)], utc=True)
    # Ensure the index name is 'timestamp' or None, as some pandas versions might create 'None'
    # and others might require it to be explicitly named if operations depend on it.
    # For iterrows, it doesn't strictly matter, but for joins it might.
    # The service code converts index to_pydatetime(), so a DatetimeIndex is key.
    return pd.DataFrame({
        'Open': [100.0 + i for i in range(num_days)],
        'High': [102.0 + i for i in range(num_days)],
        'Low': [98.0 + i for i in range(num_days)],
        'Close': [101.0 + i for i in range(num_days)],
        'Volume': [1000.0 + i * 10 for i in range(num_days)]
    }, index=dates)

def get_sample_signals_df(price_df: pd.DataFrame) -> pd.DataFrame:
    signals = price_df.copy() # Start with a copy to keep OHLCV for signal generation context
    signals['SMA_20'] = price_df['Close'].rolling(window=min(20, len(price_df))).mean().fillna(0) # fillna for simplicity in test
    signals['entries'] = False
    signals['exits'] = False
    if len(signals) > 1:
        signals.loc[signals.index[1], 'entries'] = True
    if len(signals) > 3:
        signals.loc[signals.index[3], 'exits'] = True
    return signals

# --- Tests for get_strategy_visualization_data ---

@pytest.mark.asyncio
@patch('python_ai_services.services.strategy_visualization_service.get_historical_price_data_tool')
@patch('python_ai_services.services.strategy_visualization_service.importlib.import_module')
async def test_get_strategy_visualization_data_success(
    mock_import_module: MagicMock, # Type hint for clarity
    mock_get_historical_data: MagicMock, # Type hint
    visualization_service: StrategyVisualizationService,
    mock_strategy_config_service_viz: MagicMock,
    mock_supabase_client_viz: MagicMock
):
    # Arrange
    user_id = uuid.uuid4()
    strategy_config_id = uuid.uuid4()
    start_date_obj = date(2023, 1, 1)
    end_date_obj = date(2023, 1, 10) # Results in 10 data points if start_datetime is day 1

    request = StrategyVisualizationRequest(
        strategy_config_id=strategy_config_id, user_id=user_id,
        start_date=start_date_obj, end_date=end_date_obj
    )

    # Mock StrategyConfig - user_id is not part of StrategyConfig Pydantic model directly.
    # The service's get_strategy_config method takes user_id for ownership check.
    mock_config = StrategyConfig(
        strategy_id=strategy_config_id, strategy_name="Test Darvas", strategy_type="DarvasBox",
        symbols=["AAPL"], timeframe=StrategyTimeframe("1d"), parameters=DarvasBoxParams()
        # user_id would be on the DB record, not necessarily the Pydantic model unless adapted
    )
    mock_strategy_config_service_viz.get_strategy_config.return_value = mock_config

    start_datetime = datetime.combine(start_date_obj, datetime.min.time(), tzinfo=timezone.utc)
    # Ensure num_days results in data up to and including end_date_obj
    num_days = (end_date_obj - start_date_obj).days + 1
    price_df = get_sample_price_df(start_datetime, num_days)
    # Access the .func attribute if get_historical_price_data_tool is a patched Tool object
    # If it's patched as a direct function, just .return_value
    if hasattr(mock_get_historical_data, 'func'):
        mock_get_historical_data.func.return_value = price_df
    else:
        mock_get_historical_data.return_value = price_df


    signals_df = get_sample_signals_df(price_df.copy())

    mock_strategy_module = MagicMock()
    # Service uses strategy_module_name_map.get("DarvasBox") -> "darvas_box"
    # and then constructs signal_func_name = f"get_{mapped_module_name}_signals"
    mock_strategy_module.get_darvas_box_signals = MagicMock(return_value=(signals_df, None)) # Func returns (df, shapes)
    mock_import_module.return_value = mock_strategy_module

    mock_trades_db_response = AsyncMock() # This should be the return value of .execute()
    mock_trades_db_response.data = [
        TradeRecord(trade_id=uuid.uuid4(), user_id=user_id, symbol="AAPL", side=TradeSide.BUY, order_type=OrderType.MARKET, status=OrderStatus.FILLED, quantity_ordered=10.0, quantity_filled=10.0, price=101.0, created_at=price_df.index[1].to_pydatetime().replace(tzinfo=timezone.utc), updated_at=price_df.index[1].to_pydatetime().replace(tzinfo=timezone.utc), order_id=str(uuid.uuid4())).model_dump()
    ]
    # Corrected mock chain for Supabase:
    mock_supabase_client_viz.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.lt.return_value.order.return_value.execute = mock_trades_db_response


    # Act
    result = await visualization_service.get_strategy_visualization_data(request)

    # Assert
    assert result is not None
    assert isinstance(result, StrategyVisualizationDataResponse)
    assert result.strategy_config_id == strategy_config_id
    assert result.symbol_visualized == "AAPL"
    assert len(result.ohlcv_data) == num_days # Should match number of days
    assert result.ohlcv_data[0].open == 100.0

    assert "SMA_20" in result.indicator_data
    # Exact length can vary due to rolling window NaNs. Check if list is non-empty if SMA_20 is expected.
    assert len(result.indicator_data["SMA_20"]) <= num_days
    if num_days >=1: # Check first point if data exists
         assert isinstance(result.indicator_data["SMA_20"][0], IndicatorDataPoint)


    assert len(result.entry_signals) == 1
    assert result.entry_signals[0].signal_type == "entry_long"
    assert len(result.exit_signals) == 1
    assert result.exit_signals[0].signal_type == "exit_long"

    assert result.paper_trades is not None
    assert len(result.paper_trades) == 1
    assert result.paper_trades[0].price == 101.0

    mock_strategy_config_service_viz.get_strategy_config.assert_called_once_with(strategy_config_id, user_id)

    if hasattr(mock_get_historical_data, 'func'):
         mock_get_historical_data.func.assert_called_once()
    else:
         mock_get_historical_data.assert_called_once()

    mock_import_module.assert_called_once_with("python_ai_services.strategies.darvas_box")
    mock_strategy_module.get_darvas_box_signals.assert_called_once()


@pytest.mark.asyncio
@patch('python_ai_services.services.strategy_visualization_service.get_historical_price_data_tool')
async def test_get_strategy_visualization_data_config_not_found(
    mock_get_historical_data: MagicMock,
    visualization_service: StrategyVisualizationService,
    mock_strategy_config_service_viz: MagicMock
):
    mock_strategy_config_service_viz.get_strategy_config.return_value = None
    request = StrategyVisualizationRequest(
        strategy_config_id=uuid.uuid4(), user_id=uuid.uuid4(),
        start_date=date(2023,1,1), end_date=date(2023,1,10)
    )
    with pytest.raises(StrategyVisualizationServiceError, match="not found for user"):
        await visualization_service.get_strategy_visualization_data(request)

@pytest.mark.asyncio
@patch('python_ai_services.services.strategy_visualization_service.get_historical_price_data_tool')
async def test_get_strategy_visualization_data_no_price_data(
    mock_get_historical_data: MagicMock,
    visualization_service: StrategyVisualizationService,
    mock_strategy_config_service_viz: MagicMock
):
    mock_config_id = uuid.uuid4()
    mock_user_id = uuid.uuid4()
    mock_config = StrategyConfig(strategy_id=mock_config_id, strategy_name="Test", strategy_type="DarvasBox", symbols=["FAIL"], timeframe=StrategyTimeframe("1d"), parameters=DarvasBoxParams())
    mock_strategy_config_service_viz.get_strategy_config.return_value = mock_config

    if hasattr(mock_get_historical_data, 'func'):
        mock_get_historical_data.func.return_value = None # Simulate price data fetch failure
    else:
        mock_get_historical_data.return_value = None


    request = StrategyVisualizationRequest(
        strategy_config_id=mock_config.strategy_id, user_id=mock_user_id, # Use the mock_user_id here
        start_date=date(2023,1,1), end_date=date(2023,1,10)
    )
    with pytest.raises(StrategyVisualizationServiceError, match="Could not fetch price data"):
        await visualization_service.get_strategy_visualization_data(request)

# TODO: Add tests for:
# - Strategy with no symbols (service should raise error, test this)
# - Signal function import error (ModuleNotFoundError, AttributeError)
# - Signal function returning None or empty DataFrame for signals
# - No paper trades found (should return empty list for paper_trades, not error)
# - Different strategy types to test the dynamic import map (if more are added to map in service)
# - Error during paper trade fetching from Supabase
# - Test case where signals_df has no 'entries' or 'exits' columns.
# - Test case where price_df is empty after fetching. (Covered by "Could not fetch price data" if None, but also for empty DataFrame)
# - Test indicator extraction logic with more complex scenarios (e.g. multi-value indicators, all NaNs)
# - Test OHLCVBar creation with missing Volume data.
