import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from python_ai_services.services.renko_technical_service import RenkoTechnicalService
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig
# AgentStrategyConfig.RenkoParams will be used directly
from python_ai_services.models.event_bus_models import Event, TradeSignalEventPayload
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.services.market_data_service import MarketDataService

# --- Fixtures ---
@pytest_asyncio.fixture
def mock_event_bus() -> MagicMock:
    return AsyncMock(spec=EventBusService)

@pytest_asyncio.fixture
def mock_market_data_service() -> MagicMock:
    service = AsyncMock(spec=MarketDataService)
    service.get_historical_klines = AsyncMock()
    return service

def create_renko_agent_config(
    agent_id: str = "renko_test_agent",
    brick_size_mode: str = "atr",
    fixed_brick_size: Optional[float] = None,
    atr_period: int = 14,
    signal_confirmation_bricks: int = 2,
    stop_loss_bricks_away: Optional[int] = 2,
    watched_symbols: Optional[List[str]] = None
) -> AgentConfigOutput:
    renko_params = AgentStrategyConfig.RenkoParams(
        brick_size_mode=brick_size_mode, # type: ignore
        brick_size_value_fixed=fixed_brick_size,
        atr_period=atr_period,
        signal_confirmation_bricks=signal_confirmation_bricks,
        stop_loss_bricks_away=stop_loss_bricks_away
    )
    return AgentConfigOutput(
        agent_id=agent_id, name=f"TestRenkoAgent_{agent_id}", agent_type="RenkoTechnicalAgent",
        strategy=AgentStrategyConfig(
            strategy_name="RenkoStrategy",
            renko_params=renko_params,
            watched_symbols=watched_symbols if watched_symbols else ["BTC/USD"]
        ),
        # Dummy risk/execution config as RenkoService doesn't use them directly
        risk_config=MagicMock(),
        execution_provider="paper"
    )

@pytest_asyncio.fixture
def renko_service(mock_event_bus: MagicMock, mock_market_data_service: MagicMock) -> RenkoTechnicalService:
    default_config = create_renko_agent_config()
    return RenkoTechnicalService(
        agent_config=default_config,
        event_bus=mock_event_bus,
        market_data_service=mock_market_data_service
        # learning_logger can be None for these tests unless specifically testing logging
    )

# --- Helper for Kline Data ---
def generate_klines(prices: List[float], start_timestamp_ms: int, interval_ms: int = 60000 * 60 * 24) -> List[Dict[str, Any]]:
    klines = []
    for i, price in enumerate(prices):
        ts = start_timestamp_ms + i * interval_ms
        klines.append({
            "timestamp": ts, "open": price, "high": price + 1,
            "low": price -1, "close": price, "volume": 100 + i
        })
    return klines

# --- Tests for _calculate_atr ---
@pytest.mark.asyncio
async def test_calculate_atr_sufficient_data(renko_service: RenkoTechnicalService):
    closes = [10, 11, 10.5, 12, 11.5, 13, 12.5, 14, 13.5, 15, 14.5, 16, 15.5, 17, 16.5] # 15 points
    highs = [p + 0.5 for p in closes]
    lows = [p - 0.5 for p in closes]
    atr = await renko_service._calculate_atr(highs, lows, closes, period=14)
    assert atr is not None
    assert atr > 0

@pytest.mark.asyncio
async def test_calculate_atr_insufficient_data(renko_service: RenkoTechnicalService):
    closes = [10, 11, 12] # 3 points
    highs = [11, 12, 13]
    lows = [9, 10, 11]
    atr = await renko_service._calculate_atr(highs, lows, closes, period=14)
    assert atr is None

@pytest.mark.asyncio
async def test_calculate_atr_empty_data(renko_service: RenkoTechnicalService):
    atr = await renko_service._calculate_atr([], [], [], period=14)
    assert atr is None

# --- Tests for _calculate_renko_bricks ---
def test_calculate_renko_bricks_no_prices(renko_service: RenkoTechnicalService):
    bricks = renko_service._calculate_renko_bricks([], [], 1.0)
    assert bricks == []

def test_calculate_renko_bricks_invalid_brick_size(renko_service: RenkoTechnicalService):
    prices = [100, 101, 102]
    timestamps = [1000, 2000, 3000]
    bricks = renko_service._calculate_renko_bricks(timestamps, prices, 0)
    assert bricks == []
    bricks_neg = renko_service._calculate_renko_bricks(timestamps, prices, -1.0)
    assert bricks_neg == []

def test_calculate_renko_bricks_upward_trend(renko_service: RenkoTechnicalService):
    prices = [100, 101, 102, 103, 104, 105]
    timestamps = [i * 1000 for i in range(len(prices))]
    brick_size = 1.0
    bricks = renko_service._calculate_renko_bricks(timestamps, prices, brick_size)
    assert len(bricks) == 5
    for i, brick in enumerate(bricks):
        assert brick["type"] == "up"
        assert brick["open"] == pytest.approx(100.0 + i * brick_size)
        assert brick["close"] == pytest.approx(100.0 + (i + 1) * brick_size)
        assert brick["timestamp"] == timestamps[i+1] # Timestamp of candle that formed the brick

def test_calculate_renko_bricks_downward_trend(renko_service: RenkoTechnicalService):
    prices = [100, 99, 98, 97, 96, 95]
    timestamps = [i * 1000 for i in range(len(prices))]
    brick_size = 1.0
    bricks = renko_service._calculate_renko_bricks(timestamps, prices, brick_size)
    assert len(bricks) == 5
    for i, brick in enumerate(bricks):
        assert brick["type"] == "down"
        assert brick["open"] == pytest.approx(100.0 - i * brick_size)
        assert brick["close"] == pytest.approx(100.0 - (i + 1) * brick_size)
        assert brick["timestamp"] == timestamps[i+1]

def test_calculate_renko_bricks_mixed_trend_simple_reversal(renko_service: RenkoTechnicalService):
    # Simpler brick logic: forms new brick type if price moves brick_size from last brick's close
    prices =       [100, 101, 102, 101, 100, 99]
    timestamps =   [  0,1000,2000,3000,4000,5000]
    brick_size = 1.0
    bricks = renko_service._calculate_renko_bricks(timestamps, prices, brick_size)

    # Expected:
    # 1. Price moves 100 -> 101: brick [100, 101] type up, ts 1000
    # 2. Price moves 101 -> 102: brick [101, 102] type up, ts 2000
    # 3. Price moves 102 -> 101: no new brick (not enough movement for reversal from 102)
    # 4. Price moves 101 -> 100: brick [101, 100] type down, ts 4000 (diff from 102 is -2, so 2 bricks [102,101], [101,100] if from last_brick_close=102)
    #    With prompt's logic: last_brick_close=102. Price 101. diff = -1. Brick: [102,101] down. last_brick_close=101. ts 3000.
    #                        Next price 100. diff = -1 from 101. Brick: [101,100] down. last_brick_close=100. ts 4000.
    #                        Next price 99. diff = -1 from 100. Brick: [100,99] down. last_brick_close=99. ts 5000.

    assert len(bricks) == 5
    assert bricks[0] == {"type": "up", "open": 100.0, "close": 101.0, "timestamp": 1000}
    assert bricks[1] == {"type": "up", "open": 101.0, "close": 102.0, "timestamp": 2000}
    assert bricks[2] == {"type": "down", "open": 102.0, "close": 101.0, "timestamp": 3000} # Reversal brick
    assert bricks[3] == {"type": "down", "open": 101.0, "close": 100.0, "timestamp": 4000}
    assert bricks[4] == {"type": "down", "open": 100.0, "close": 99.0, "timestamp": 5000}

# --- Tests for analyze_symbol_and_generate_signal ---
@pytest.mark.asyncio
async def test_analyze_no_klines(renko_service: RenkoTechnicalService, mock_market_data_service: MagicMock):
    mock_market_data_service.get_historical_klines.return_value = []
    await renko_service.analyze_symbol_and_generate_signal("BTC/USD")
    renko_service.event_bus.publish.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_atr_calculation_fails(renko_service: RenkoTechnicalService, mock_market_data_service: MagicMock):
    # Configured for ATR brick size
    renko_service.params.brick_size_mode = "atr"
    # Return klines that are insufficient for ATR (e.g., less than atr_period)
    klines = generate_klines([100, 101], 0)
    mock_market_data_service.get_historical_klines.return_value = klines

    # Mock _calculate_atr to return None
    with patch.object(renko_service, '_calculate_atr', new_callable=AsyncMock) as mock_calc_atr:
        mock_calc_atr.return_value = None
        await renko_service.analyze_symbol_and_generate_signal("BTC/USD")
        renko_service.event_bus.publish.assert_not_called()
        mock_calc_atr.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_fixed_brick_size_invalid_config(renko_service: RenkoTechnicalService, mock_market_data_service: MagicMock):
    # Configure for fixed brick size but set it to None or zero
    renko_service.params.brick_size_mode = "fixed"
    renko_service.params.brick_size_value_fixed = None

    klines = generate_klines([100, 101, 102, 103], 0)
    mock_market_data_service.get_historical_klines.return_value = klines

    await renko_service.analyze_symbol_and_generate_signal("BTC/USD")
    renko_service.event_bus.publish.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_not_enough_renko_bricks_for_signal(renko_service: RenkoTechnicalService, mock_market_data_service: MagicMock):
    renko_service.params.brick_size_mode = "fixed"
    renko_service.params.brick_size_value_fixed = 1.0
    renko_service.params.signal_confirmation_bricks = 3 # Need 3 bricks for signal

    # Prices will generate only 1 brick: 100 -> 101
    prices = [100, 101.5] # Only one brick [100, 101]
    klines = generate_klines(prices, 0)
    mock_market_data_service.get_historical_klines.return_value = klines

    await renko_service.analyze_symbol_and_generate_signal("BTC/USD")
    renko_service.event_bus.publish.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_buy_signal_generated(renko_service: RenkoTechnicalService, mock_market_data_service: MagicMock, mock_event_bus: MagicMock):
    renko_service.params.brick_size_mode = "fixed"
    renko_service.params.brick_size_value_fixed = 1.0
    renko_service.params.signal_confirmation_bricks = 2
    renko_service.params.stop_loss_bricks_away = 1 # SL at open of first signal brick

    # Prices: ..., 99 (down), 100 (up), 101 (up) -> BUY signal
    prices = [100, 99, 100.5, 101.5] # Generates bricks: [100,99] down, [99,100] up, [100,101] up
    # Last kline close is 101.5
    klines = generate_klines(prices, datetime.now(timezone.utc).timestamp() * 1000 - 4 * (24*60*60*1000))
    mock_market_data_service.get_historical_klines.return_value = klines

    await renko_service.analyze_symbol_and_generate_signal("TEST/USD")

    mock_event_bus.publish.assert_called_once()
    event_arg: Event = mock_event_bus.publish.call_args[0][0]
    assert event_arg.message_type == "TradeSignalEvent"
    payload: TradeSignalEventPayload = TradeSignalEventPayload(**event_arg.payload)
    assert payload.symbol == "TEST/USD"
    assert payload.action == "buy"
    assert payload.price_target == pytest.approx(101.5) # Last close price
    # First signal brick is [99,100] up. SL is its open.
    assert payload.stop_loss == pytest.approx(99.0)
    assert payload.strategy_name == f"Renko_B{1.0:.4f}_C2"

@pytest.mark.asyncio
async def test_analyze_sell_signal_generated(renko_service: RenkoTechnicalService, mock_market_data_service: MagicMock, mock_event_bus: MagicMock):
    renko_service.params.brick_size_mode = "fixed"
    renko_service.params.brick_size_value_fixed = 1.0
    renko_service.params.signal_confirmation_bricks = 2
    renko_service.params.stop_loss_bricks_away = 1

    # Prices: ..., 101 (up), 100 (down), 99 (down) -> SELL signal
    prices = [100, 101, 99.5, 98.5] # Bricks: [100,101] up, [101,100] down, [100,99] down
    # Last kline close is 98.5
    klines = generate_klines(prices, datetime.now(timezone.utc).timestamp() * 1000 - 4 * (24*60*60*1000))
    mock_market_data_service.get_historical_klines.return_value = klines

    await renko_service.analyze_symbol_and_generate_signal("TEST/USD")

    mock_event_bus.publish.assert_called_once()
    event_arg: Event = mock_event_bus.publish.call_args[0][0]
    payload = TradeSignalEventPayload(**event_arg.payload)
    assert payload.action == "sell"
    assert payload.price_target == pytest.approx(98.5)
    # First signal brick is [101,100] down. SL is its open.
    assert payload.stop_loss == pytest.approx(101.0)
