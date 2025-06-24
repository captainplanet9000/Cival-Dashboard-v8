import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from python_ai_services.services.heikin_ashi_service import HeikinAshiTechnicalService
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig
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

def create_ha_agent_config(
    agent_id: str = "ha_test_agent",
    trend_sma_period: int = 20,
    signal_confirmation_candles: int = 2,
    stop_loss_atr_multiplier: float = 1.5,
    atr_period_for_sl: int = 14,
    watched_symbols: Optional[List[str]] = None
) -> AgentConfigOutput:
    ha_params = AgentStrategyConfig.HeikinAshiParams(
        trend_sma_period=trend_sma_period,
        signal_confirmation_candles=signal_confirmation_candles,
        stop_loss_atr_multiplier=stop_loss_atr_multiplier,
        atr_period_for_sl=atr_period_for_sl
    )
    return AgentConfigOutput(
        agent_id=agent_id, name=f"TestHeikinAshiAgent_{agent_id}", agent_type="HeikinAshiTechnicalAgent",
        strategy=AgentStrategyConfig(
            strategy_name="HeikinAshiStrategy",
            heikin_ashi_params=ha_params,
            watched_symbols=watched_symbols if watched_symbols else ["BTC/USD"]
        ),
        risk_config=MagicMock(), execution_provider="paper"
    )

@pytest_asyncio.fixture
def ha_service(mock_event_bus: MagicMock, mock_market_data_service: MagicMock) -> HeikinAshiTechnicalService:
    default_config = create_ha_agent_config()
    return HeikinAshiTechnicalService(
        agent_config=default_config,
        event_bus=mock_event_bus,
        market_data_service=mock_market_data_service
    )

# --- Helper for Kline Data ---
def generate_ohlc_df(prices_data: List[Dict[str, float]], start_timestamp_ms: int, interval_ms: int = 60000 * 60 * 24) -> pd.DataFrame:
    data_for_df = []
    for i, p_data in enumerate(prices_data):
        ts = start_timestamp_ms + i * interval_ms
        data_for_df.append({
            "timestamp": ts, "open": p_data["open"], "high": p_data["high"],
            "low": p_data["low"], "close": p_data["close"], "volume": p_data.get("volume", 100 + i)
        })
    return pd.DataFrame(data_for_df)

# --- Tests for _calculate_heikin_ashi_candles ---
def test_calculate_ha_candles_empty_df(ha_service: HeikinAshiTechnicalService):
    empty_df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close'])
    ha_df = ha_service._calculate_heikin_ashi_candles(empty_df)
    assert ha_df.empty
    assert list(ha_df.columns) == ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'timestamp']


def test_calculate_ha_candles_basic_calculation(ha_service: HeikinAshiTechnicalService):
    # Data from a known example: https://school.stockcharts.com/doku.php?id=chart_analysis:heikin_ashi
    # Day Open High Low Close | HA-Close HA-Open HA-High HA-Low
    # 1   20.00 20.20 19.80 20.04 | 20.01    20.02    20.20   19.80
    # 2   20.04 20.08 19.75 19.83 | 19.925   20.015   20.08   19.75
    # 3   19.83 20.05 19.82 20.01 | 19.9275  19.97    20.05   19.82
    data = [
        {"timestamp": 1000, "open": 20.00, "high": 20.20, "low": 19.80, "close": 20.04},
        {"timestamp": 2000, "open": 20.04, "high": 20.08, "low": 19.75, "close": 19.83},
        {"timestamp": 3000, "open": 19.83, "high": 20.05, "low": 19.82, "close": 20.01},
    ]
    klines_df = pd.DataFrame(data)
    ha_df = ha_service._calculate_heikin_ashi_candles(klines_df)

    assert len(ha_df) == 3
    # Day 1
    assert pytest.approx(ha_df['ha_close'].iloc[0]) == (20.00 + 20.20 + 19.80 + 20.04) / 4 # 20.01
    assert pytest.approx(ha_df['ha_open'].iloc[0]) == (20.00 + 20.04) / 2 # 20.02
    assert pytest.approx(ha_df['ha_high'].iloc[0]) == max(ha_df['ha_open'].iloc[0], ha_df['ha_close'].iloc[0], klines_df['high'].iloc[0]) # max(20.02, 20.01, 20.20) = 20.20
    assert pytest.approx(ha_df['ha_low'].iloc[0]) == min(ha_df['ha_open'].iloc[0], ha_df['ha_close'].iloc[0], klines_df['low'].iloc[0])   # min(20.02, 20.01, 19.80) = 19.80
    # Day 2
    assert pytest.approx(ha_df['ha_close'].iloc[1]) == (20.04 + 20.08 + 19.75 + 19.83) / 4 # 19.925
    assert pytest.approx(ha_df['ha_open'].iloc[1]) == (ha_df['ha_open'].iloc[0] + ha_df['ha_close'].iloc[0]) / 2 # (20.02 + 20.01)/2 = 20.015
    assert pytest.approx(ha_df['ha_high'].iloc[1]) == max(ha_df['ha_open'].iloc[1], ha_df['ha_close'].iloc[1], klines_df['high'].iloc[1]) # max(20.015, 19.925, 20.08) = 20.08
    assert pytest.approx(ha_df['ha_low'].iloc[1]) == min(ha_df['ha_open'].iloc[1], ha_df['ha_close'].iloc[1], klines_df['low'].iloc[1])   # min(20.015, 19.925, 19.75) = 19.75

# --- Tests for _calculate_atr (can reuse from Renko if identical, or test specifically) ---
@pytest.mark.asyncio
async def test_ha_calculate_atr_sufficient_data(ha_service: HeikinAshiTechnicalService):
    # Use a known ATR example if possible, or verify calculation properties
    raw_klines = [
        {'timestamp': 1, 'open': 10, 'high': 12, 'low': 9, 'close': 11}, # TR = 3
        {'timestamp': 2, 'open': 11, 'high': 13, 'low': 10, 'close': 12}, # TR = 3 (max(3, abs(13-11), abs(10-11)))
        {'timestamp': 3, 'open': 12, 'high': 14, 'low': 11, 'close': 13}, # TR = 3
    ] * 5 # Repeat for 15 days to have enough for period 14
    klines_df = pd.DataFrame(raw_klines)
    atr = await ha_service._calculate_atr(klines_df, period=14)
    assert atr is not None
    assert atr > 0
    # Example: if all TRs are 3, ATR should be 3
    assert pytest.approx(atr) == 3.0

# --- Tests for analyze_symbol_and_generate_signal ---
@pytest.mark.asyncio
async def test_analyze_not_enough_data(ha_service: HeikinAshiTechnicalService, mock_market_data_service: MagicMock):
    mock_market_data_service.get_historical_klines.return_value = generate_ohlc_df([{"open":10,"high":11,"low":9,"close":10}]*5, 0) # Only 5 klines
    await ha_service.analyze_symbol_and_generate_signal("TEST/USD")
    ha_service.event_bus.publish.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_ha_buy_signal(ha_service: HeikinAshiTechnicalService, mock_market_data_service: MagicMock, mock_event_bus: MagicMock):
    # Setup: 1 non-strong green HA, then 2 strong green HA, HA_close > HA_SMA
    # Actual prices for ATR SL calculation
    prices_data = [
        # Initial data for ATR and SMA buildup
        *([{"open": 100, "high": 101, "low": 99, "close": 100}] * (ha_service.params.trend_sma_period + 2)), # Approx 22 days
        # Candle before signal sequence (e.g., a doji or small body green)
        {"open": 100, "high": 101, "low": 99, "close": 100.5}, # HA might be: open=100, close=100.125, high=101, low=99 (Not strong green)
        # Signal sequence (2 strong green candles by default)
        {"open": 101, "high": 103, "low": 101, "close": 103},   # HA: open=100.06, close=102, high=103, low=100.06 (Strong green)
        {"open": 103, "high": 105, "low": 103, "close": 105},   # HA: open=101.03, close=104, high=105, low=101.03 (Strong green) - Signal candle
    ]
    klines_df_raw = generate_ohlc_df(prices_data, 0)
    mock_market_data_service.get_historical_klines.return_value = klines_df_raw.to_dict(orient='records')

    await ha_service.analyze_symbol_and_generate_signal("TEST/USD")

    mock_event_bus.publish.assert_called_once()
    event_arg: Event = mock_event_bus.publish.call_args[0][0]
    assert event_arg.message_type == "TradeSignalEvent"
    payload = TradeSignalEventPayload(**event_arg.payload)
    assert payload.symbol == "TEST/USD"
    assert payload.action == "buy"
    assert payload.price_target == pytest.approx(105.0) # Last actual close
    assert payload.stop_loss is not None # ATR should be calculable
    assert payload.stop_loss < payload.price_target

@pytest.mark.asyncio
async def test_analyze_ha_sell_signal(ha_service: HeikinAshiTechnicalService, mock_market_data_service: MagicMock, mock_event_bus: MagicMock):
    # Setup: 1 non-strong red HA, then 2 strong red HA, HA_close < HA_SMA
    prices_data = [
        *([{"open": 105, "high": 106, "low": 104, "close": 105}] * (ha_service.params.trend_sma_period + 2)),
        {"open": 105, "high": 105.5, "low": 104, "close": 104.5}, # HA might be: open=105, close=104.75, high=105.5, low=104 (Not strong red)
        {"open": 104, "high": 104, "low": 102, "close": 102},   # HA: open=104.875, close=103, high=104.875, low=102 (Strong red)
        {"open": 102, "high": 102, "low": 100, "close": 100},   # HA: open=103.9375, close=101, high=103.9375, low=100 (Strong red) - Signal candle
    ]
    klines_df_raw = generate_ohlc_df(prices_data, 0)
    mock_market_data_service.get_historical_klines.return_value = klines_df_raw.to_dict(orient='records')

    await ha_service.analyze_symbol_and_generate_signal("TEST/USD")

    mock_event_bus.publish.assert_called_once()
    event_arg: Event = mock_event_bus.publish.call_args[0][0]
    payload = TradeSignalEventPayload(**event_arg.payload)
    assert payload.action == "sell"
    assert payload.price_target == pytest.approx(100.0) # Last actual close
    assert payload.stop_loss is not None
    assert payload.stop_loss > payload.price_target

@pytest.mark.asyncio
async def test_analyze_no_signal_choppy_market(ha_service: HeikinAshiTechnicalService, mock_market_data_service: MagicMock, mock_event_bus: MagicMock):
    prices_data = [
        {"open": 100, "high": 101, "low": 99, "close": 100.5}, # Green
        {"open": 100.5, "high": 101, "low": 99, "close": 99.5}, # Red
        {"open": 99.5, "high": 101, "low": 99, "close": 100.2}, # Green
        {"open": 100.2, "high": 101, "low": 99, "close": 99.8}, # Red
    ] * ( (ha_service.params.trend_sma_period + 2) // 4 + 1) # Ensure enough data
    klines_df_raw = generate_ohlc_df(prices_data, 0)
    mock_market_data_service.get_historical_klines.return_value = klines_df_raw.to_dict(orient='records')

    await ha_service.analyze_symbol_and_generate_signal("TEST/USD")
    mock_event_bus.publish.assert_not_called()

# Add more tests:
# - ATR calculation for SL returns None (SL should be None)
# - Kline data has NaNs or missing columns (graceful handling)
