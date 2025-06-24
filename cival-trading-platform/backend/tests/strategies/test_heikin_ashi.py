import pytest
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

from python_ai_services.strategies.heikin_ashi import run_heikin_ashi, _calculate_heikin_ashi_candles
from python_ai_services.models.strategy_models import HeikinAshiConfig
from python_ai_services.types.trading_types import TradeAction

# Helper function to create OHLCV DataFrames for tests
def create_ohlcv_df(
    dates: List[str],
    opens: Optional[List[float]] = None,
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
    closes: Optional[List[float]] = None,
    volumes: Optional[List[int]] = None, # Added volumes for completeness
    use_close_for_all_prices: bool = False
) -> pd.DataFrame:
    if use_close_for_all_prices and closes is not None:
        opens = highs = lows = closes

    data_dict: Dict[str, Any] = {'Close': closes if closes else []}
    default_series = [0.0] * len(dates) if dates else []
    data_dict['High'] = highs if highs is not None else (closes if closes is not None else default_series)
    data_dict['Low'] = lows if lows is not None else (closes if closes is not None else default_series)
    data_dict['Open'] = opens if opens is not None else (closes if closes is not None else default_series)
    data_dict['Close'] = closes if closes is not None else default_series
    data_dict['Volume'] = volumes if volumes is not None else ([100] * len(dates))

    return pd.DataFrame(data_dict, index=pd.to_datetime(dates))

# --- Fixtures ---
@pytest.fixture
def default_ha_config() -> HeikinAshiConfig:
    """Provides a default HeikinAshiConfig for tests."""
    return HeikinAshiConfig()

@pytest.fixture
def ha_config_min_trend_2() -> HeikinAshiConfig:
    """HA Config with min_trend_candles = 2 for easier testing."""
    return HeikinAshiConfig(min_trend_candles=2, small_wick_threshold_percent=20.0)


# --- Tests for _calculate_heikin_ashi_candles ---

def test_calculate_ha_candles_basic():
    dates = ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"]
    df_input = create_ohlcv_df(
        dates,
        opens= [100, 102, 101, 103],
        highs= [105, 106, 104, 107],
        lows=  [98,  100, 99,  101],
        closes=[102, 101, 103, 105]
    )
    ha_df = _calculate_heikin_ashi_candles(df_input)

    assert all(col in ha_df.columns for col in ['ha_open', 'ha_high', 'ha_low', 'ha_close'])
    assert len(ha_df) == len(df_input)
    pd.testing.assert_index_equal(ha_df.index, df_input.index)

    # Manual calculation for first few candles:
    # Candle 0 (2023-01-01): O=100, H=105, L=98, C=102
    # HA_Close[0] = (100+105+98+102)/4 = 405/4 = 101.25
    # HA_Open[0] = (100+102)/2 = 101.0
    # HA_High[0] = max(105, 101.0, 101.25) = 105.0
    # HA_Low[0]  = min(98, 101.0, 101.25) = 98.0
    assert abs(ha_df['ha_close'].iloc[0] - 101.25) < 0.01
    assert abs(ha_df['ha_open'].iloc[0] - 101.0) < 0.01
    assert abs(ha_df['ha_high'].iloc[0] - 105.0) < 0.01
    assert abs(ha_df['ha_low'].iloc[0] - 98.0) < 0.01

    # Candle 1 (2023-01-02): O=102, H=106, L=100, C=101
    # HA_Close[1] = (102+106+100+101)/4 = 409/4 = 102.25
    # HA_Open[1] = (HA_Open[0] + HA_Close[0])/2 = (101.0 + 101.25)/2 = 101.125
    # HA_High[1] = max(106, 101.125, 102.25) = 106.0
    # HA_Low[1]  = min(100, 101.125, 102.25) = 100.0
    assert abs(ha_df['ha_close'].iloc[1] - 102.25) < 0.01
    assert abs(ha_df['ha_open'].iloc[1] - 101.125) < 0.01
    assert abs(ha_df['ha_high'].iloc[1] - 106.0) < 0.01
    assert abs(ha_df['ha_low'].iloc[1] - 100.0) < 0.01

def test_calculate_ha_candles_empty_input():
    df_input = pd.DataFrame(columns=['open', 'high', 'low', 'close'])
    df_input.index = pd.to_datetime(df_input.index)
    ha_df = _calculate_heikin_ashi_candles(df_input)
    assert ha_df.empty
    assert all(col in ha_df.columns for col in ['ha_open', 'ha_high', 'ha_low', 'ha_close'])

# --- Tests for run_heikin_ashi Main Function ---

def test_ha_indicator_data_output_no_smoothing(default_ha_config: HeikinAshiConfig):
    dates = ["2023-01-01", "2023-01-02", "2023-01-03"]
    df_input = create_ohlcv_df(dates, closes=[10,11,12], use_close_for_all_prices=True)
    results = run_heikin_ashi(df_input, default_ha_config)

    assert "heikin_ashi_data" in results
    ha_data_df = results["heikin_ashi_data"]
    assert isinstance(ha_data_df, pd.DataFrame)
    assert all(col in ha_data_df.columns for col in ['ha_open', 'ha_high', 'ha_low', 'ha_close'])
    assert not any(col.startswith('smoothed_') for col in ha_data_df.columns)

def test_ha_indicator_data_output_with_smoothing(default_ha_config: HeikinAshiConfig):
    dates = ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]
    df_input = create_ohlcv_df(dates, closes=[10,11,12,13,14], use_close_for_all_prices=True)
    config = default_ha_config
    config.price_smoothing_period = 3

    results = run_heikin_ashi(df_input, config)
    ha_data_df = results["heikin_ashi_data"]
    assert all(col in ha_data_df.columns for col in ['smoothed_ha_open', 'smoothed_ha_high', 'smoothed_ha_low', 'smoothed_ha_close'])
    # Check if smoothed values are different from raw HA values (they should be after some periods)
    assert pd.notna(ha_data_df['smoothed_ha_close'].iloc[-1])
    if len(ha_data_df) > config.price_smoothing_period:
         assert ha_data_df['ha_close'].iloc[-1] != ha_data_df['smoothed_ha_close'].iloc[-1]


def test_ha_buy_signal_strong_bullish_trend(ha_config_min_trend_2: HeikinAshiConfig):
    # 2 green HA candles with no lower wicks needed for BUY
    dates = ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"]
    # Data crafted to produce strong green HA candles
    df_input = create_ohlcv_df(
        dates,
        opens= [10, 11, 12, 13],
        highs= [12, 13, 14, 15], # Ensure HA_High = HA_Close
        lows=  [10, 11, 12, 13],  # Ensure HA_Low = HA_Open
        closes=[12, 13, 14, 15]  # Ensures HA_Close > HA_Open
    ) # This data makes HA_Open = HA_Low, HA_Close = HA_High => No wicks

    results = run_heikin_ashi(df_input, ha_config_min_trend_2)
    signals = results["signals"]
    buy_signals = [s for s in signals if s["type"] == TradeAction.BUY.value] # Use .value for enum if imported

    assert len(buy_signals) > 0
    # First BUY should be on the 2nd green candle (index 1, if HA starts at 0)
    # _calculate_ha_candles: HA_C[0]=(10+12+10+12)/4=11, HA_O[0]=(10+12)/2=11. HA_H=12, HA_L=10. (Doji, but used for next HA_O)
    # HA_C[1]=(11+13+11+13)/4=12, HA_O[1]=(11+11)/2=11. HA_H=13, HA_L=11 (Green, no lower wick)
    # HA_C[2]=(12+14+12+14)/4=13, HA_O[2]=(11+12)/2=11.5. HA_H=14, HA_L=11.5 (Green, no lower wick) -> BUY at close of C[2]
    # This depends on how start_signal_generation_idx and min_trend_candles interact.
    # If min_trend_candles=2, we check candles at i and i-1.
    # First possible i is start_signal_generation_idx = first_valid_ha_idx + 1 (for 2 candles)
    # If first_valid_ha_idx is 0 (assuming enough data for HA calc), then i starts at 1.
    # Signal at index 2 (3rd day) if candle 1 and 2 meet criteria.
    if buy_signals:
         assert buy_signals[0]['date'] == pd.Timestamp(dates[2]) # Signal on the close of the 2nd confirming HA candle
         assert "consecutive green HA candles" in buy_signals[0]['reason']


def test_ha_sell_signal_strong_bearish_trend(ha_config_min_trend_2: HeikinAshiConfig):
    dates = ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"]
    df_input = create_ohlcv_df(
        dates,
        opens= [15, 14, 13, 12],
        highs= [15, 14, 13, 12], # HA_High = HA_Open
        lows=  [13, 12, 11, 10],  # HA_Low = HA_Close
        closes=[13, 12, 11, 10]  # HA_Close < HA_Open
    ) # This data makes HA_Open = HA_High, HA_Close = HA_Low => No upper wicks for red candles
    results = run_heikin_ashi(df_input, ha_config_min_trend_2)
    signals = results["signals"]
    sell_signals = [s for s in signals if s["type"] == TradeAction.SELL.value]
    assert len(sell_signals) > 0
    if sell_signals:
        assert sell_signals[0]['date'] == pd.Timestamp(dates[2]) # Signal on the 2nd confirming red HA candle
        assert "consecutive red HA candles" in sell_signals[0]['reason']

def test_ha_no_signals_insufficient_data(default_ha_config: HeikinAshiConfig):
    dates = ["2023-01-01", "2023-01-02"] # Only 2 data points
    df = create_ohlcv_df(dates, closes=[10,11], use_close_for_all_prices=True)
    results = run_heikin_ashi(df, default_ha_config) # Default min_trend_candles = 3
    assert len(results["signals"]) == 0

# TODO: More tests:
# - test_ha_exit_long_on_red_candle
# - test_ha_exit_long_on_weak_green_candle
# - test_ha_hold_in_strong_bullish_trend_after_buy
# - test_ha_small_wick_threshold_impact
