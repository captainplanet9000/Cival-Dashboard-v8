import pytest
import pytest_asyncio # For async fixtures
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from datetime import datetime, timezone, timedelta
import uuid

# Models and Services to test
from python_ai_services.services.simulated_trade_executor import SimulatedTradeExecutor
from python_ai_services.models.paper_trading_models import PaperTradeOrder, PaperTradeFill
from python_ai_services.models.trading_history_models import TradeSide, OrderType as PaperOrderType, OrderStatus as PaperOrderStatus
from python_ai_services.services.event_service import EventService # For mocking event_service instance
from python_ai_services.models.event_models import AlertEvent, AlertLevel # For asserting alert content

# --- Fixtures ---

@pytest_asyncio.fixture
async def mock_supabase_client_ste(): # STE for SimulatedTradeExecutor
    """Mocks the Supabase client."""
    client = MagicMock()
    # No specific table/method mocks needed here as we test STE methods that use helpers,
    # or those helpers (like _get_market_data_for_fill) will be mocked directly.
    return client

@pytest_asyncio.fixture
async def mock_event_service_ste():
    """Mocks the EventService."""
    service = MagicMock(spec=EventService) # Use spec for more accurate mocking
    service.publish_event = AsyncMock()
    return service

@pytest_asyncio.fixture
async def trade_executor(mock_supabase_client_ste: MagicMock, mock_event_service_ste: MagicMock):
    """Provides an instance of SimulatedTradeExecutor with mocked dependencies."""
    # Patch 'create_client' in the module where SimulatedTradeExecutor will import it from.
    with patch('python_ai_services.services.simulated_trade_executor.create_client', return_value=mock_supabase_client_ste):
        executor = SimulatedTradeExecutor(
            supabase_url="dummy_url", # These are passed but create_client is mocked
            supabase_key="dummy_key",
            event_service=mock_event_service_ste # Inject mocked EventService
        )
    return executor

# --- Tests for submit_paper_order ---

@pytest.mark.asyncio
async def test_submit_paper_order_market_buy_fills_at_next_open(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    # Arrange
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    order_request_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    paper_order = PaperTradeOrder(
        order_id=order_id,
        user_id=user_id,
        symbol="AAPL",
        side=TradeSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=10,
        order_request_timestamp=order_request_time
    )

    mock_market_df = pd.DataFrame({
        'Open': [150.00, 150.50],
        'High': [150.80, 151.00], 'Low': [149.90, 150.25],
        'Close': [150.30, 150.75], 'Volume': [1000, 1200]
    }, index=pd.to_datetime([
        order_request_time + timedelta(minutes=1),
        order_request_time + timedelta(minutes=2)
    ], utc=True)) # Ensure index is pd.DatetimeIndex and UTC

    # Mock the helper method directly on the instance
    trade_executor._get_market_data_for_fill = AsyncMock(return_value=mock_market_df)

    # Act
    updated_order, fills = await trade_executor.submit_paper_order(paper_order, simulated_commission_pct=0.001)

    # Assert
    trade_executor._get_market_data_for_fill.assert_called_once_with("AAPL", order_request_time.replace(tzinfo=timezone.utc)) # Ensure UTC

    assert updated_order.status == PaperOrderStatus.FILLED
    assert len(fills) == 1
    fill = fills[0]
    assert fill.order_id == order_id
    assert fill.price == 150.00
    assert fill.quantity == 10
    assert fill.fill_timestamp == mock_market_df.index[0].to_pydatetime().replace(tzinfo=timezone.utc)
    expected_commission = round(10 * 150.00 * 0.001, 4)
    assert fill.commission == expected_commission
    assert "Simulated fill" in updated_order.notes

    mock_event_service_ste.publish_event.assert_called_once()
    alert_arg = mock_event_service_ste.publish_event.call_args[0][0]
    assert isinstance(alert_arg, AlertEvent)
    assert alert_arg.alert_level == AlertLevel.INFO
    assert "FILLED" in alert_arg.message


@pytest.mark.asyncio
async def test_submit_paper_order_market_sell_fills_at_next_open(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    order_request_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    paper_order = PaperTradeOrder(
        order_id=order_id, user_id=user_id, symbol="TSLA",
        side=TradeSide.SELL, order_type=PaperOrderType.MARKET, quantity=5,
        order_request_timestamp=order_request_time
    )
    mock_market_df = pd.DataFrame({
        'Open': [200.00], 'High': [201.00], 'Low': [199.00], 'Close': [200.50], 'Volume': [500]
    }, index=pd.to_datetime([order_request_time + timedelta(minutes=1)], utc=True))
    trade_executor._get_market_data_for_fill = AsyncMock(return_value=mock_market_df)

    updated_order, fills = await trade_executor.submit_paper_order(paper_order, simulated_commission_pct=0.0)

    assert updated_order.status == PaperOrderStatus.FILLED
    assert len(fills) == 1
    fill = fills[0]
    assert fill.price == 200.00
    assert fill.quantity == 5
    assert fill.commission == 0.0
    mock_event_service_ste.publish_event.assert_called_once()


@pytest.mark.asyncio
async def test_submit_paper_order_no_market_data(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    order_request_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    paper_order = PaperTradeOrder(user_id=uuid.uuid4(), symbol="NVDA", side=TradeSide.BUY, order_type=PaperOrderType.MARKET, quantity=1, order_request_timestamp=order_request_time)

    trade_executor._get_market_data_for_fill = AsyncMock(return_value=None)

    updated_order, fills = await trade_executor.submit_paper_order(paper_order)

    assert updated_order.status == PaperOrderStatus.REJECTED
    assert "No market data available" in updated_order.notes
    assert len(fills) == 0

    # Alert for rejection should NOT be published by submit_paper_order if no market data, as it returns early
    # The updated submit_paper_order in previous step *does* publish rejection alerts.
    mock_event_service_ste.publish_event.assert_called_once()
    alert_arg = mock_event_service_ste.publish_event.call_args[0][0]
    assert isinstance(alert_arg, AlertEvent)
    assert alert_arg.alert_level == AlertLevel.WARNING

# --- Tests for calculate_paper_portfolio_valuation ---

@pytest.mark.asyncio
async def test_calculate_paper_portfolio_valuation_no_positions(trade_executor: SimulatedTradeExecutor):
    user_id = uuid.uuid4()
    cash_balance = 10000.0

    # Mock the Supabase call to return no positions
    mock_supabase_execute = AsyncMock()
    mock_supabase_execute.return_value = MagicMock(data=[]) # Ensure .data is an empty list
    trade_executor.supabase.table.return_value.select.return_value.eq.return_value.execute = mock_supabase_execute

    result = await trade_executor.calculate_paper_portfolio_valuation(user_id, cash_balance)

    assert result["user_id"] == str(user_id)
    assert result["current_cash_balance"] == cash_balance
    assert result["total_positions_market_value"] == 0.0
    assert result["total_unrealized_pnl"] == 0.0
    assert result["total_portfolio_value"] == cash_balance
    assert len(result["open_positions"]) == 0
    # Verify the DB call for fetching positions
    trade_executor.supabase.table.return_value.select.return_value.eq.assert_called_once_with("user_id", str(user_id))

@pytest.mark.asyncio
async def test_calculate_paper_portfolio_valuation_one_long_position_profit(trade_executor: SimulatedTradeExecutor):
    user_id = uuid.uuid4()
    cash_balance = 10000.0
    pos_id = uuid.uuid4()

    # Simulate data returned from Supabase for one position
    # Ensure PaperPosition is available for constructing mock data
    from python_ai_services.models.paper_trading_models import PaperPosition

    positions_db_data = [{
        "position_id": str(pos_id), "user_id": str(user_id), "symbol": "AAPL",
        "quantity": 10.0, "average_entry_price": 150.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_modified_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {}
    }]
    mock_supabase_execute = AsyncMock()
    mock_supabase_execute.return_value = MagicMock(data=positions_db_data)
    trade_executor.supabase.table.return_value.select.return_value.eq.return_value.execute = mock_supabase_execute

    trade_executor.get_current_market_price = AsyncMock(return_value=160.0)

    result = await trade_executor.calculate_paper_portfolio_valuation(user_id, cash_balance)

    trade_executor.get_current_market_price.assert_called_once_with("AAPL")
    assert result["total_positions_market_value"] == 1600.0
    assert result["total_unrealized_pnl"] == 100.0
    assert result["total_portfolio_value"] == 11600.0
    assert len(result["open_positions"]) == 1
    assert result["open_positions"][0]["symbol"] == "AAPL"
    assert result["open_positions"][0]["unrealized_pnl"] == 100.0
    assert result["open_positions"][0]["current_market_value"] == 1600.0
    assert result["open_positions"][0]["current_market_price"] == 160.0


@pytest.mark.asyncio
async def test_calculate_paper_portfolio_valuation_one_short_position_loss(trade_executor: SimulatedTradeExecutor):
    user_id = uuid.uuid4()
    cash_balance = 10000.0
    from python_ai_services.models.paper_trading_models import PaperPosition
    positions_db_data = [{
        "position_id": str(uuid.uuid4()), "user_id": str(user_id), "symbol": "TSLA",
        "quantity": -5.0, "average_entry_price": 200.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_modified_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {}
    }]
    mock_supabase_execute = AsyncMock()
    mock_supabase_execute.return_value = MagicMock(data=positions_db_data)
    trade_executor.supabase.table.return_value.select.return_value.eq.return_value.execute = mock_supabase_execute

    trade_executor.get_current_market_price = AsyncMock(return_value=210.0)

    result = await trade_executor.calculate_paper_portfolio_valuation(user_id, cash_balance)

    trade_executor.get_current_market_price.assert_called_once_with("TSLA")
    assert result["total_positions_market_value"] == -1050.0
    assert result["total_unrealized_pnl"] == -50.0
    assert result["total_portfolio_value"] == 8950.0

    assert len(result["open_positions"]) == 1
    assert result["open_positions"][0]["symbol"] == "TSLA"
    assert result["open_positions"][0]["unrealized_pnl"] == -50.0

@pytest.mark.asyncio
async def test_calculate_paper_portfolio_valuation_multiple_positions(trade_executor: SimulatedTradeExecutor):
    user_id = uuid.uuid4()
    cash_balance = 10000.0
    from python_ai_services.models.paper_trading_models import PaperPosition
    positions_db_data = [
        {"position_id": str(uuid.uuid4()), "user_id": str(user_id), "symbol": "AAPL", "quantity": 10.0, "average_entry_price": 150.0, "created_at": datetime.now(timezone.utc).isoformat(), "last_modified_at": datetime.now(timezone.utc).isoformat(), "metadata": {}},
        {"position_id": str(uuid.uuid4()), "user_id": str(user_id), "symbol": "TSLA", "quantity": -5.0, "average_entry_price": 200.0, "created_at": datetime.now(timezone.utc).isoformat(), "last_modified_at": datetime.now(timezone.utc).isoformat(), "metadata": {}}
    ]
    mock_supabase_execute = AsyncMock()
    mock_supabase_execute.return_value = MagicMock(data=positions_db_data)
    trade_executor.supabase.table.return_value.select.return_value.eq.return_value.execute = mock_supabase_execute

    async def mock_price_func(symbol):
        if symbol == "AAPL": return 160.0
        if symbol == "TSLA": return 190.0
        return None
    trade_executor.get_current_market_price = AsyncMock(side_effect=mock_price_func)

    result = await trade_executor.calculate_paper_portfolio_valuation(user_id, cash_balance)

    assert trade_executor.get_current_market_price.call_count == 2
    assert result["total_positions_market_value"] == round(1600.0 - 950.0, 2)
    assert result["total_unrealized_pnl"] == round(100.0 + 50.0, 2)
    assert result["total_portfolio_value"] == round(10000.0 + 650.0, 2)
    assert len(result["open_positions"]) == 2

@pytest.mark.asyncio
async def test_calculate_paper_portfolio_valuation_price_fetch_fails_for_one_asset(trade_executor: SimulatedTradeExecutor):
    user_id = uuid.uuid4()
    cash_balance = 10000.0
    from python_ai_services.models.paper_trading_models import PaperPosition
    positions_db_data = [
        {"position_id": str(uuid.uuid4()), "user_id": str(user_id), "symbol": "AAPL", "quantity": 10.0, "average_entry_price": 150.0, "created_at": datetime.now(timezone.utc).isoformat(), "last_modified_at": datetime.now(timezone.utc).isoformat(), "metadata": {}},
        {"position_id": str(uuid.uuid4()), "user_id": str(user_id), "symbol": "UNKNOWN", "quantity": 5.0, "average_entry_price": 50.0, "created_at": datetime.now(timezone.utc).isoformat(), "last_modified_at": datetime.now(timezone.utc).isoformat(), "metadata": {}}
    ]
    mock_supabase_execute = AsyncMock()
    mock_supabase_execute.return_value = MagicMock(data=positions_db_data)
    trade_executor.supabase.table.return_value.select.return_value.eq.return_value.execute = mock_supabase_execute

    async def mock_price_func_partial_fail(symbol):
        if symbol == "AAPL": return 160.0
        if symbol == "UNKNOWN": return None
        return None
    trade_executor.get_current_market_price = AsyncMock(side_effect=mock_price_func_partial_fail)

    result = await trade_executor.calculate_paper_portfolio_valuation(user_id, cash_balance)

    assert result["total_positions_market_value"] == 1600.0
    assert result["total_unrealized_pnl"] == 100.0
    assert result["total_portfolio_value"] == 11600.0
    assert len(result["open_positions"]) == 2
    assert result["open_positions"][0]["symbol"] == "AAPL"
    assert result["open_positions"][0]["current_market_price"] == 160.0
    assert result["open_positions"][1]["symbol"] == "UNKNOWN"
    assert result["open_positions"][1]["current_market_price"] is None
    assert result["open_positions"][1]["current_market_value"] is None
    assert result["open_positions"][1]["unrealized_pnl"] is None

# --- Tests for run_historical_paper_backtest ---

@pytest.mark.asyncio
@patch('python_ai_services.services.simulated_trade_executor.get_historical_price_data_tool') # Mock the tool
async def test_run_historical_paper_backtest_simple_buy_and_hold(
    mock_get_historical_data_tool, # Patched object
    trade_executor: SimulatedTradeExecutor # Fixture
):
    # Arrange
    user_id = uuid.uuid4()
    symbol = "TESTSYM_BH" # Buy and Hold
    start_date_str = "2023-01-01"
    end_date_str = "2023-01-10" # 10 days of data
    initial_cash = 100000.0
    trade_quantity = 10.0

    price_dates = pd.to_datetime([f"2023-01-{i:02d}" for i in range(1, 11)], utc=True)
    mock_prices_df = pd.DataFrame({
        'Open': [100.0 + i for i in range(10)],
        'High': [102.0 + i for i in range(10)],
        'Low': [98.0 + i for i in range(10)],
        'Close': [101.0 + i for i in range(10)],
        'Volume': [1000.0 + i * 10 for i in range(10)]
    }, index=price_dates)
    mock_get_historical_data_tool.return_value = mock_prices_df

    # Must import PaperPosition for the mock return of apply_fill_to_position
    from python_ai_services.models.paper_trading_models import PaperPosition
    from python_ai_services.models.trading_history_models import TradeRecord # For _log_paper_trade_to_history mock
    from unittest.mock import ANY # For cash assertion

    async def mock_strategy_signals_buy_hold(symbol, start_date, end_date, data_provider, **kwargs): # Added data_provider
        idx = pd.to_datetime([f"2023-01-{i:02d}" for i in range(1, 11)], utc=True)
        signals = pd.DataFrame(index=idx)
        signals['entries'] = False
        signals['exits'] = False
        if not signals.empty:
            signals.loc[signals.index[0], 'entries'] = True
        return signals, None

    strategy_params = {}

    entry_order_id = uuid.uuid4()
    mock_filled_order_entry = PaperTradeOrder(
        order_id=entry_order_id, user_id=user_id, symbol=symbol, side=TradeSide.BUY,
        order_type=PaperOrderType.MARKET, quantity=trade_quantity,
        order_request_timestamp=price_dates[0].to_pydatetime(), # Use python datetime
        status=PaperOrderStatus.FILLED,
        notes="Simulated fill for entry by mock"
    )
    entry_fill_price = mock_prices_df['Open'].iloc[0]
    mock_fill_entry = PaperTradeFill(
        order_id=entry_order_id, user_id=user_id, symbol=symbol, side=TradeSide.BUY,
        fill_timestamp=price_dates[0].to_pydatetime(), price=entry_fill_price, quantity=trade_quantity,
        commission=round(entry_fill_price * trade_quantity * 0.001, 4)
    )

    # submit_paper_order is called once for entry
    # It needs to be an AsyncMock because it's awaited
    trade_executor.submit_paper_order = AsyncMock(return_value=(mock_filled_order_entry, [mock_fill_entry]))

    new_pos_after_entry = PaperPosition(
        user_id=user_id, symbol=symbol, quantity=trade_quantity, average_entry_price=entry_fill_price,
        position_id=uuid.uuid4(), created_at=price_dates[0].to_pydatetime(), last_modified_at=price_dates[0].to_pydatetime()
    )
    trade_executor.apply_fill_to_position = AsyncMock(return_value=new_pos_after_entry)

    trade_executor._log_paper_trade_to_history = AsyncMock(return_value=MagicMock(spec=TradeRecord))

    final_market_price = mock_prices_df['Close'].iloc[-1]
    market_value_of_pos = trade_quantity * final_market_price
    unrealized_pnl = (final_market_price - entry_fill_price) * trade_quantity
    cash_after_buy = initial_cash - (entry_fill_price * trade_quantity) - mock_fill_entry.commission
    final_portfolio_val = cash_after_buy + market_value_of_pos

    final_valuation_mock_data = {
        "user_id": str(user_id), "current_cash_balance": round(cash_after_buy, 2),
        "total_positions_market_value": round(market_value_of_pos, 2),
        "total_unrealized_pnl": round(unrealized_pnl, 2),
        "total_portfolio_value": round(final_portfolio_val, 2),
        "open_positions": [{
            "symbol": symbol, "quantity": trade_quantity, "average_entry_price": entry_fill_price,
            "current_market_price": final_market_price,
            "current_market_value": round(market_value_of_pos, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "position_id": str(new_pos_after_entry.position_id) # Match type from service
        }]
    }
    trade_executor.calculate_paper_portfolio_valuation = AsyncMock(return_value=final_valuation_mock_data)

    # Act
    result = await trade_executor.run_historical_paper_backtest(
        user_id, mock_strategy_signals_buy_hold, strategy_params,
        symbol, start_date_str, end_date_str, initial_cash, trade_quantity
    )

    # Assert
    mock_get_historical_data_tool.assert_called_once_with(symbol, start_date_str, end_date_str, interval="1d", provider="yfinance")
    trade_executor.submit_paper_order.assert_called_once()
    trade_executor.apply_fill_to_position.assert_called_once_with(mock_fill_entry)
    trade_executor._log_paper_trade_to_history.assert_called_once()
    trade_executor.calculate_paper_portfolio_valuation.assert_called_once_with(user_id, ANY)

    assert result["strategy_name"] == "mock_strategy_signals_buy_hold"
    assert result["initial_cash"] == initial_cash
    assert result["final_portfolio_value"] == round(final_portfolio_val, 2)
    assert result["net_profit"] == round(final_portfolio_val - initial_cash, 2)
    assert len(result["final_open_positions"]) == 1
    assert result["final_open_positions"][0]["symbol"] == symbol
    assert result["final_open_positions"][0]["quantity"] == trade_quantity

@pytest.mark.asyncio
@patch('python_ai_services.services.simulated_trade_executor.get_historical_price_data_tool')
async def test_run_historical_paper_backtest_no_signals_generated(
    mock_get_historical_data_tool,
    trade_executor: SimulatedTradeExecutor
):
    user_id = uuid.uuid4()
    symbol = "NOSIG"
    start_date_str="2023-01-01"; end_date_str="2023-01-03"; initial_cash=10000.0

    mock_prices = pd.DataFrame({'Open': [10,11,12], 'Close': [10,11,12], 'High':[10,11,12], 'Low':[10,11,12]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'], utc=True))
    mock_get_historical_data_tool.return_value = mock_prices

    async def mock_no_signals_strategy(symbol, start_date, end_date, data_provider, **kwargs): # Added data_provider
        idx = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'], utc=True)
        signals = pd.DataFrame(index=idx); signals['entries'] = False; signals['exits'] = False
        return signals, None

    final_val_data = {"total_portfolio_value": initial_cash, "net_profit": 0.0, "final_open_positions": [], "open_positions": [],
                      "current_cash_balance": initial_cash, "total_positions_market_value": 0.0, "total_unrealized_pnl":0.0}
    trade_executor.calculate_paper_portfolio_valuation = AsyncMock(return_value=final_val_data)
    trade_executor.submit_paper_order = AsyncMock()
    trade_executor.apply_fill_to_position = AsyncMock()
    trade_executor._log_paper_trade_to_history = AsyncMock()


    result = await trade_executor.run_historical_paper_backtest(
        user_id, mock_no_signals_strategy, {}, symbol, start_date_str, end_date_str, initial_cash, 1.0
    )

    trade_executor.submit_paper_order.assert_not_called()
    trade_executor.apply_fill_to_position.assert_not_called()
    trade_executor._log_paper_trade_to_history.assert_not_called()
    assert result["net_profit"] == 0.0
    assert result["final_portfolio_value"] == initial_cash


# --- Tests for calculate_realized_pnl_for_trades (Placeholder) ---

@pytest.mark.asyncio
async def test_calculate_realized_pnl_for_trades_placeholder(trade_executor: SimulatedTradeExecutor):
    user_id = uuid.uuid4()

    result = await trade_executor.calculate_realized_pnl_for_trades(user_id=user_id)

    assert result["user_id"] == str(user_id)
    assert result["total_realized_pnl"] == 0.00
    assert "Placeholder - Full P&L logic not yet implemented" in result["calculation_status"]
    assert result["filters_applied"]["trade_ids"] == "All applicable"

@pytest.mark.asyncio
async def test_calculate_realized_pnl_for_trades_with_filters_placeholder(trade_executor: SimulatedTradeExecutor):
    user_id = uuid.uuid4()
    trade_ids_filter = [uuid.uuid4(), uuid.uuid4()]
    symbol_filter = "AAPL"
    start_date_filter = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date_filter = datetime(2023, 12, 31, tzinfo=timezone.utc)

    result = await trade_executor.calculate_realized_pnl_for_trades(
        user_id=user_id,
        trade_ids=trade_ids_filter,
        symbol_filter=symbol_filter,
        start_date_filter=start_date_filter,
        end_date_filter=end_date_filter
    )

    assert result["user_id"] == str(user_id)
    assert result["total_realized_pnl"] == 0.00
    assert "Placeholder - Full P&L logic not yet implemented" in result["calculation_status"]
    assert result["filters_applied"]["trade_ids"] == [str(tid) for tid in trade_ids_filter]
    assert result["filters_applied"]["symbol"] == symbol_filter
    assert result["filters_applied"]["start_date"] == start_date_filter.isoformat()
    assert result["filters_applied"]["end_date"] == end_date_filter.isoformat()


# --- Tests for apply_fill_to_position ---

@pytest.mark.asyncio
async def test_apply_fill_to_position_opens_new_long_position(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock): # Added mock_event_service_ste
    user_id = uuid.uuid4()
    fill = PaperTradeFill(
        user_id=user_id, symbol="AAPL", side=TradeSide.BUY,
        quantity=10, price=150.0, order_id=uuid.uuid4(), fill_timestamp=datetime.now(timezone.utc)
    )

    trade_executor._get_paper_position = AsyncMock(return_value=None)
    trade_executor._create_paper_position = AsyncMock(side_effect=lambda pos: pos)
    # mock_event_service_ste.publish_event = AsyncMock() # Already mocked by fixture if needed for position events

    result_position = await trade_executor.apply_fill_to_position(fill)

    trade_executor._get_paper_position.assert_called_once_with(user_id, "AAPL")
    trade_executor._create_paper_position.assert_called_once()
    created_pos_arg = trade_executor._create_paper_position.call_args[0][0]

    assert isinstance(created_pos_arg, PaperPosition) # Ensure PaperPosition is imported
    assert created_pos_arg.user_id == user_id
    assert created_pos_arg.symbol == "AAPL"
    assert created_pos_arg.quantity == 10
    assert created_pos_arg.average_entry_price == 150.0
    assert result_position is not None
    assert result_position.quantity == 10
    # No alert is published by _create_paper_position itself in current design
    mock_event_service_ste.publish_event.assert_not_called()


@pytest.mark.asyncio
async def test_apply_fill_to_position_opens_new_short_position(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    fill = PaperTradeFill(
        user_id=user_id, symbol="TSLA", side=TradeSide.SELL,
        quantity=5, price=200.0, order_id=uuid.uuid4(), fill_timestamp=datetime.now(timezone.utc)
    )
    trade_executor._get_paper_position = AsyncMock(return_value=None)
    trade_executor._create_paper_position = AsyncMock(side_effect=lambda pos: pos)

    result_position = await trade_executor.apply_fill_to_position(fill)

    created_pos_arg = trade_executor._create_paper_position.call_args[0][0]
    assert created_pos_arg.quantity == -5
    assert created_pos_arg.average_entry_price == 200.0
    assert result_position.quantity == -5
    mock_event_service_ste.publish_event.assert_not_called()


@pytest.mark.asyncio
async def test_apply_fill_to_position_adds_to_existing_long(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    # Ensure PaperPosition is imported for this
    from python_ai_services.models.paper_trading_models import PaperPosition
    existing_pos = PaperPosition(
        position_id=uuid.uuid4(), user_id=user_id, symbol="MSFT", quantity=10, average_entry_price=250.0
    )
    fill = PaperTradeFill(
        user_id=user_id, symbol="MSFT", side=TradeSide.BUY,
        quantity=5, price=260.0, order_id=uuid.uuid4(), fill_timestamp=datetime.now(timezone.utc)
    )
    trade_executor._get_paper_position = AsyncMock(return_value=existing_pos)
    trade_executor._update_paper_position_record = AsyncMock(side_effect=lambda pos: pos)

    result_position = await trade_executor.apply_fill_to_position(fill)

    expected_new_qty = 15.0
    expected_avg_price = ((10 * 250.0) + (5 * 260.0)) / 15.0

    updated_pos_arg = trade_executor._update_paper_position_record.call_args[0][0]
    assert updated_pos_arg.quantity == expected_new_qty
    assert round(updated_pos_arg.average_entry_price, 6) == round(expected_avg_price, 6)
    assert result_position.quantity == expected_new_qty
    mock_event_service_ste.publish_event.assert_not_called()

@pytest.mark.asyncio
async def test_apply_fill_to_position_reduces_existing_long_not_closing(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    from python_ai_services.models.paper_trading_models import PaperPosition
    existing_pos = PaperPosition(
        position_id=uuid.uuid4(), user_id=user_id, symbol="GOOG", quantity=20, average_entry_price=120.0
    )
    fill = PaperTradeFill(
        user_id=user_id, symbol="GOOG", side=TradeSide.SELL,
        quantity=5, price=125.0, order_id=uuid.uuid4(), fill_timestamp=datetime.now(timezone.utc)
    )
    trade_executor._get_paper_position = AsyncMock(return_value=existing_pos)
    trade_executor._update_paper_position_record = AsyncMock(side_effect=lambda pos: pos)

    result_position = await trade_executor.apply_fill_to_position(fill)

    updated_pos_arg = trade_executor._update_paper_position_record.call_args[0][0]
    assert updated_pos_arg.quantity == 15
    assert updated_pos_arg.average_entry_price == 120.0
    assert result_position.quantity == 15
    mock_event_service_ste.publish_event.assert_not_called()


@pytest.mark.asyncio
async def test_apply_fill_to_position_closes_long_position_exactly(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    pos_id = uuid.uuid4()
    from python_ai_services.models.paper_trading_models import PaperPosition
    existing_pos = PaperPosition(
        position_id=pos_id, user_id=user_id, symbol="AMZN", quantity=10, average_entry_price=100.0
    )
    fill = PaperTradeFill(
        user_id=user_id, symbol="AMZN", side=TradeSide.SELL,
        quantity=10, price=110.0, order_id=uuid.uuid4(), fill_timestamp=datetime.now(timezone.utc)
    )
    trade_executor._get_paper_position = AsyncMock(return_value=existing_pos)
    trade_executor._delete_paper_position = AsyncMock(return_value=None)
    # mock_event_service_ste fixture already mocks publish_event as AsyncMock

    result_position = await trade_executor.apply_fill_to_position(fill)

    trade_executor._delete_paper_position.assert_called_once_with(pos_id)
    assert result_position is None
    mock_event_service_ste.publish_event.assert_called_once()
    alert_arg = mock_event_service_ste.publish_event.call_args[0][0]
    assert isinstance(alert_arg, AlertEvent)
    assert alert_arg.alert_level == AlertLevel.INFO
    assert "Paper position CLOSED" in alert_arg.message


@pytest.mark.asyncio
async def test_apply_fill_to_position_flips_long_to_short(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    from python_ai_services.models.paper_trading_models import PaperPosition
    existing_pos = PaperPosition(
        position_id=uuid.uuid4(), user_id=user_id, symbol="NFLX", quantity=5, average_entry_price=300.0
    )
    fill = PaperTradeFill(
        user_id=user_id, symbol="NFLX", side=TradeSide.SELL,
        quantity=15, price=310.0, order_id=uuid.uuid4(), fill_timestamp=datetime.now(timezone.utc)
    )
    trade_executor._get_paper_position = AsyncMock(return_value=existing_pos)
    trade_executor._update_paper_position_record = AsyncMock(side_effect=lambda pos: pos)
    # Position flip involves closing one side and opening another.
    # Current logic: one alert for "close", then new position is created/updated.
    # If _delete is called (it shouldn't for flip, only exact close), then alert.
    # If it's a flip, it goes to _update_paper_position_record. No separate "flip" alert.
    trade_executor._delete_paper_position = AsyncMock() # Ensure it's mocked if we want to assert not_called


    result_position = await trade_executor.apply_fill_to_position(fill)

    updated_pos_arg = trade_executor._update_paper_position_record.call_args[0][0]
    assert updated_pos_arg.quantity == -10
    assert updated_pos_arg.average_entry_price == 310.0
    assert result_position.quantity == -10
    trade_executor._delete_paper_position.assert_not_called()
    mock_event_service_ste.publish_event.assert_not_called() # No "close" alert if it's a flip, new logic implies this


@pytest.mark.asyncio
async def test_apply_fill_to_position_adds_to_existing_short(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    from python_ai_services.models.paper_trading_models import PaperPosition
    existing_pos = PaperPosition(
        position_id=uuid.uuid4(), user_id=user_id, symbol="META", quantity=-10, average_entry_price=180.0
    )
    fill = PaperTradeFill(
        user_id=user_id, symbol="META", side=TradeSide.SELL,
        quantity=5, price=175.0, order_id=uuid.uuid4(), fill_timestamp=datetime.now(timezone.utc)
    )
    trade_executor._get_paper_position = AsyncMock(return_value=existing_pos)
    trade_executor._update_paper_position_record = AsyncMock(side_effect=lambda pos: pos)

    result_position = await trade_executor.apply_fill_to_position(fill)

    expected_new_qty = -15.0
    expected_avg_price = ((-10 * 180.0) + (-5 * 175.0)) / -15.0

    updated_pos_arg = trade_executor._update_paper_position_record.call_args[0][0]
    assert updated_pos_arg.quantity == expected_new_qty
    assert round(updated_pos_arg.average_entry_price, 6) == round(expected_avg_price, 6)
    assert result_position.quantity == expected_new_qty
    mock_event_service_ste.publish_event.assert_not_called()
    assert "REJECTED" in alert_arg.message


@pytest.mark.asyncio
async def test_submit_paper_order_no_market_data_after_order_time(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    order_request_time = datetime.now(timezone.utc)
    paper_order = PaperTradeOrder(user_id=uuid.uuid4(), symbol="AMD", side=TradeSide.BUY, order_type=PaperOrderType.MARKET, quantity=2, order_request_timestamp=order_request_time)

    mock_market_df = pd.DataFrame({
        'Open': [50.00], 'High': [51.00], 'Low': [49.00], 'Close': [50.50], 'Volume': [200]
    }, index=pd.to_datetime([order_request_time - timedelta(minutes=5)], utc=True)) # Data ends before order time
    trade_executor._get_market_data_for_fill = AsyncMock(return_value=mock_market_df)

    updated_order, fills = await trade_executor.submit_paper_order(paper_order)

    assert updated_order.status == PaperOrderStatus.REJECTED
    assert "No market data found after order time" in updated_order.notes
    assert len(fills) == 0
    mock_event_service_ste.publish_event.assert_called_once()
    alert_arg = mock_event_service_ste.publish_event.call_args[0][0]
    assert isinstance(alert_arg, AlertEvent)
    assert alert_arg.alert_level == AlertLevel.WARNING
    assert "REJECTED" in alert_arg.message


@pytest.mark.asyncio
async def test_submit_paper_order_limit_buy_fills(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    order_request_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    limit_price = 150.00

    paper_order = PaperTradeOrder(
        order_id=order_id, user_id=user_id, symbol="MSFT",
        side=TradeSide.BUY, order_type=PaperOrderType.LIMIT, quantity=10,
        limit_price=limit_price, order_request_timestamp=order_request_time
    )

    mock_market_df = pd.DataFrame({
        'Open':  [151.00, 150.50, 149.80],
        'High':  [151.50, 150.80, 150.20],
        'Low':   [150.60, 149.90, 149.50],
        'Close': [150.70, 150.00, 149.90]
    }, index=pd.to_datetime([
        order_request_time + timedelta(minutes=1),
        order_request_time + timedelta(minutes=2),
        order_request_time + timedelta(minutes=3)
    ], utc=True))
    trade_executor._get_market_data_for_fill = AsyncMock(return_value=mock_market_df)
    # mock_event_service_ste is already part of the trade_executor fixture

    updated_order, fills = await trade_executor.submit_paper_order(paper_order)

    assert updated_order.status == PaperOrderStatus.FILLED
    assert len(fills) == 1
    fill = fills[0]
    assert fill.price == limit_price
    assert fill.quantity == 10
    assert fill.fill_timestamp == mock_market_df.index[1].to_pydatetime().replace(tzinfo=timezone.utc)
    mock_event_service_ste.publish_event.assert_called_once()
    alert_arg = mock_event_service_ste.publish_event.call_args[0][0]
    assert alert_arg.alert_level == AlertLevel.INFO

@pytest.mark.asyncio
async def test_submit_paper_order_limit_sell_fills(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    order_request_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    limit_price = 200.00

    paper_order = PaperTradeOrder(
        order_id=order_id, user_id=user_id, symbol="GOOG",
        side=TradeSide.SELL, order_type=PaperOrderType.LIMIT, quantity=5,
        limit_price=limit_price, order_request_timestamp=order_request_time
    )
    mock_market_df = pd.DataFrame({
        'Open':  [198.50, 199.00, 200.50],
        'High':  [199.20, 200.10, 201.00],
        'Low':   [198.00, 198.80, 199.80],
        'Close': [199.00, 199.50, 200.80]
    }, index=pd.to_datetime([
        order_request_time + timedelta(minutes=1),
        order_request_time + timedelta(minutes=2),
        order_request_time + timedelta(minutes=3)
    ], utc=True))
    trade_executor._get_market_data_for_fill = AsyncMock(return_value=mock_market_df)

    updated_order, fills = await trade_executor.submit_paper_order(paper_order)

    assert updated_order.status == PaperOrderStatus.FILLED
    assert len(fills) == 1
    fill = fills[0]
    assert fill.price == limit_price
    assert fill.quantity == 5
    assert fill.fill_timestamp == mock_market_df.index[1].to_pydatetime().replace(tzinfo=timezone.utc)
    mock_event_service_ste.publish_event.assert_called_once()
    alert_arg = mock_event_service_ste.publish_event.call_args[0][0]
    assert alert_arg.alert_level == AlertLevel.INFO


@pytest.mark.asyncio
async def test_submit_paper_order_limit_buy_not_filled(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    order_request_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    limit_price = 145.00

    paper_order = PaperTradeOrder(
        order_id=order_id, user_id=user_id, symbol="MSFT",
        side=TradeSide.BUY, order_type=PaperOrderType.LIMIT, quantity=10,
        limit_price=limit_price, order_request_timestamp=order_request_time
    )
    mock_market_df = pd.DataFrame({
        'Open':  [151.00, 150.50], 'High':  [151.50, 150.80],
        'Low':   [150.60, 149.90], 'Close': [150.70, 150.00]
    }, index=pd.to_datetime([
        order_request_time + timedelta(minutes=1),
        order_request_time + timedelta(minutes=2)
    ], utc=True))
    trade_executor._get_market_data_for_fill = AsyncMock(return_value=mock_market_df)

    updated_order, fills = await trade_executor.submit_paper_order(paper_order)

    assert updated_order.status == PaperOrderStatus.NEW
    assert "Limit price not reached" in updated_order.notes
    assert len(fills) == 0
    mock_event_service_ste.publish_event.assert_not_called()

@pytest.mark.asyncio
async def test_submit_paper_order_limit_order_missing_price(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    order_request_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    paper_order = PaperTradeOrder(
        order_id=order_id, user_id=user_id, symbol="AMZN",
        side=TradeSide.BUY, order_type=PaperOrderType.LIMIT, quantity=2,
        limit_price=None,
        order_request_timestamp=order_request_time
    )
    trade_executor._get_market_data_for_fill = AsyncMock(return_value=pd.DataFrame({'Open':[100.00]}, index=[pd.to_datetime(order_request_time + timedelta(minutes=1), utc=True)]))

    updated_order, fills = await trade_executor.submit_paper_order(paper_order)

    assert updated_order.status == PaperOrderStatus.REJECTED
    assert "Limit price not set" in updated_order.notes
    assert len(fills) == 0
    mock_event_service_ste.publish_event.assert_called_once()
    alert_arg = mock_event_service_ste.publish_event.call_args[0][0]
    assert alert_arg.alert_level == AlertLevel.WARNING


@pytest.mark.asyncio
async def test_submit_paper_order_unsupported_type(trade_executor: SimulatedTradeExecutor, mock_event_service_ste: MagicMock):
    user_id = uuid.uuid4()
    order_id = uuid.uuid4()
    order_request_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    paper_order = PaperTradeOrder(
        order_id=order_id, user_id=user_id, symbol="TSLA",
        side=TradeSide.BUY,
        order_type=PaperOrderType.STOP_LIMIT,
        quantity=1,
        limit_price=200.0, stop_price=199.0,
        order_request_timestamp=order_request_time
    )
    trade_executor._get_market_data_for_fill = AsyncMock(return_value=pd.DataFrame({'Open':[190.00]}, index=[pd.to_datetime(order_request_time + timedelta(minutes=1), utc=True)]))

    updated_order, fills = await trade_executor.submit_paper_order(paper_order)

    assert updated_order.status == PaperOrderStatus.REJECTED
    assert "not supported by simulator" in updated_order.notes
    assert len(fills) == 0
    mock_event_service_ste.publish_event.assert_called_once()
    alert_arg = mock_event_service_ste.publish_event.call_args[0][0]
    assert alert_arg.alert_level == AlertLevel.WARNING


# --- Tests for get_open_paper_orders ---

@pytest.mark.asyncio
async def test_get_open_paper_orders_success(trade_executor: SimulatedTradeExecutor, mock_supabase_client_ste: MagicMock):
    user_id = uuid.uuid4()
    # Ensure PaperOrderType and PaperOrderStatus are used when creating PaperTradeOrder instances if those are the enums defined in that model
    # However, TradeRecord uses TradingHistoryOrderStatus and TradingHistoryOrderType from trading_history_models.
    # The service method get_open_paper_orders returns List[TradeRecord].
    # So, mock_order_data should be List[Dict] that can be parsed into TradeRecord.
    # Also, ensure all required fields for TradeRecord are present in the mock data.
    from python_ai_services.models.trading_history_models import TradeRecord, TradeSide, OrderType as TradingHistoryOrderType, OrderStatus as TradingHistoryOrderStatus

    mock_order_data = [
        {"user_id": str(user_id), "order_id": str(uuid.uuid4()), "symbol": "AAPL", "side": TradeSide.BUY.value, "order_type": TradingHistoryOrderType.MARKET.value, "status": TradingHistoryOrderStatus.NEW.value, "quantity_ordered": 10.0, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(), "exchange": "PAPER_BACKTEST", "trade_id": str(uuid.uuid4()), "quantity_filled": 0.0},
        {"user_id": str(user_id), "order_id": str(uuid.uuid4()), "symbol": "MSFT", "side": TradeSide.SELL.value, "order_type": TradingHistoryOrderType.LIMIT.value, "status": TradingHistoryOrderStatus.PARTIALLY_FILLED.value, "quantity_ordered": 5.0, "quantity_filled": 2.0, "limit_price": 300.0, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(), "exchange": "PAPER_BACKTEST", "trade_id": str(uuid.uuid4())}
    ]

    mock_execute = AsyncMock(return_value=MagicMock(data=mock_order_data, error=None))
    # .table("trading_history").select("*").eq("user_id",...).in_("status",...).eq("exchange",...).order(...).execute()
    mock_supabase_client_ste.table.return_value.select.return_value.eq.return_value.in_.return_value.eq.return_value.order.return_value.execute = mock_execute

    result = await trade_executor.get_open_paper_orders(user_id)

    assert len(result) == 2
    assert isinstance(result[0], TradeRecord)
    assert result[0].symbol == "AAPL"
    assert result[1].symbol == "MSFT"

    mock_supabase_client_ste.table.assert_called_with("trading_history")
    open_statuses = [
        TradingHistoryOrderStatus.NEW.value,
        TradingHistoryOrderStatus.PARTIALLY_FILLED.value,
        TradingHistoryOrderStatus.PENDING_CANCEL.value
    ]
    mock_supabase_client_ste.table.return_value.select.return_value.eq.return_value.in_.assert_called_with("status", open_statuses)
    mock_supabase_client_ste.table.return_value.select.return_value.eq.return_value.in_.return_value.eq.assert_called_with("exchange", "PAPER_BACKTEST")


@pytest.mark.asyncio
async def test_get_open_paper_orders_no_orders_found(trade_executor: SimulatedTradeExecutor, mock_supabase_client_ste: MagicMock):
    user_id = uuid.uuid4()
    mock_execute = AsyncMock(return_value=MagicMock(data=[], error=None))
    mock_supabase_client_ste.table.return_value.select.return_value.eq.return_value.in_.return_value.eq.return_value.order.return_value.execute = mock_execute

    result = await trade_executor.get_open_paper_orders(user_id)
    assert len(result) == 0

# --- Tests for cancel_paper_order ---

@pytest.mark.asyncio
async def test_cancel_paper_order_success(trade_executor: SimulatedTradeExecutor, mock_supabase_client_ste: MagicMock):
    user_id = uuid.uuid4()
    order_id_to_cancel = uuid.uuid4()
    from python_ai_services.models.trading_history_models import TradeSide, OrderType as TradingHistoryOrderType, OrderStatus as TradingHistoryOrderStatus
    from python_ai_services.models.paper_trading_models import PaperTradeOrder, PaperOrderStatus
    from python_ai_services.models.event_models import AlertEvent, AlertLevel


    original_trade_record_data = {
        "id": str(uuid.uuid4()),
        "user_id": str(user_id), "order_id": str(order_id_to_cancel),
        "symbol": "GOOG", "side": TradeSide.BUY.value, "order_type": TradingHistoryOrderType.LIMIT.value,
        "status": TradingHistoryOrderStatus.NEW.value, "quantity_ordered": 10.0, "limit_price": 150.0,
        "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(),
        "exchange": "PAPER_BACKTEST", "metadata": {"time_in_force": "GTC"}, "quantity_filled": 0.0 # ensure all fields for TradeRecord
    }
    mock_fetch_execute = AsyncMock(return_value=MagicMock(data=original_trade_record_data, error=None))
    mock_supabase_client_ste.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = mock_fetch_execute

    updated_trade_record_data = {**original_trade_record_data, "status": TradingHistoryOrderStatus.CANCELED.value, "notes": " [User Canceled]"}
    mock_update_execute = AsyncMock(return_value=MagicMock(data=[updated_trade_record_data], error=None))
    mock_supabase_client_ste.table.return_value.update.return_value.eq.return_value.select.return_value.execute = mock_update_execute

    if trade_executor.event_service:
        trade_executor.event_service.publish_event = AsyncMock()

    result_order = await trade_executor.cancel_paper_order(user_id, order_id_to_cancel)

    assert isinstance(result_order, PaperTradeOrder)
    assert result_order.order_id == order_id_to_cancel
    assert result_order.status == PaperOrderStatus.CANCELED
    assert "User Canceled" in result_order.notes

    update_payload = mock_supabase_client_ste.table.return_value.update.call_args[0][0]
    assert update_payload["status"] == TradingHistoryOrderStatus.CANCELED.value

    if trade_executor.event_service:
        trade_executor.event_service.publish_event.assert_called_once()
        alert_arg = trade_executor.event_service.publish_event.call_args[0][0]
        assert isinstance(alert_arg, AlertEvent)
        assert alert_arg.alert_level == AlertLevel.INFO
        assert "CANCELED" in alert_arg.message


@pytest.mark.asyncio
async def test_cancel_paper_order_not_found(trade_executor: SimulatedTradeExecutor, mock_supabase_client_ste: MagicMock):
    user_id = uuid.uuid4()
    order_id_to_cancel = uuid.uuid4()
    mock_fetch_execute = AsyncMock(return_value=MagicMock(data=None, error=None))
    mock_supabase_client_ste.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = mock_fetch_execute

    with pytest.raises(ValueError, match=f"Paper order {order_id_to_cancel} not found or does not belong to user."):
        await trade_executor.cancel_paper_order(user_id, order_id_to_cancel)


@pytest.mark.asyncio
async def test_cancel_paper_order_not_cancellable_status(trade_executor: SimulatedTradeExecutor, mock_supabase_client_ste: MagicMock):
    user_id = uuid.uuid4()
    order_id_to_cancel = uuid.uuid4()
    from python_ai_services.models.trading_history_models import TradeSide, OrderType as TradingHistoryOrderType, OrderStatus as TradingHistoryOrderStatus

    original_trade_record_data = {
        "id": str(uuid.uuid4()), "user_id": str(user_id), "order_id": str(order_id_to_cancel),
        "symbol": "GOOG", "side": TradeSide.BUY.value, "order_type": TradingHistoryOrderType.MARKET.value,
        "status": TradingHistoryOrderStatus.FILLED.value,
        "quantity_ordered": 10.0, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(),
        "exchange": "PAPER_BACKTEST", "quantity_filled": 10.0
    }
    mock_fetch_execute = AsyncMock(return_value=MagicMock(data=original_trade_record_data, error=None))
    mock_supabase_client_ste.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = mock_fetch_execute

    with pytest.raises(ValueError, match=f"Order {order_id_to_cancel} cannot be canceled. Current status: FILLED"):
        await trade_executor.cancel_paper_order(user_id, order_id_to_cancel)
