import pytest
import pandas as pd
import numpy as np
from typing import List, Dict, Any

# Adjust import path based on test execution context
from python_ai_services.strategies.williams_alligator import run_williams_alligator, _calculate_smma
from python_ai_services.models.strategy_models import WilliamsAlligatorConfig

# Helper function to create OHLCV DataFrames for tests
def create_ohlcv_df(
    dates: List[str],
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    volumes: List[int]
) -> pd.DataFrame:
    """Creates a Pandas DataFrame for OHLCV data with a DatetimeIndex."""
    return pd.DataFrame({
        'Open': opens, # Ensure initial columns are capitalized as per function expectation before lowercasing
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=pd.to_datetime(dates))

# --- Default Config for Tests ---
@pytest.fixture
def default_alligator_config() -> WilliamsAlligatorConfig:
    """Provides a default WilliamsAlligatorConfig for tests."""
    return WilliamsAlligatorConfig() # Uses all default values from the Pydantic model

@pytest.fixture
def short_period_alligator_config() -> WilliamsAlligatorConfig:
    """A config with shorter periods for easier testing with less data."""
    return WilliamsAlligatorConfig(
        jaw_period=5, jaw_shift=3,
        teeth_period=3, teeth_shift=2,
        lips_period=2, lips_shift=1,
        price_source_column="close"
    )

# --- Tests for _calculate_smma Helper Function ---

def test_calculate_smma_basic():
    series = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])
    period = 3
    # Manual calculation:
    # SMA[2] = (10+11+12)/3 = 11.0
    # SMMA[3] = (11.0 * 2 + 13.0) / 3 = (22+13)/3 = 35/3 = 11.666666
    # SMMA[4] = (11.666666 * 2 + 14.0) / 3 = (23.333333 + 14)/3 = 37.333333/3 = 12.444444
    # SMMA[5] = (12.444444 * 2 + 15.0) / 3 = (24.888888 + 15)/3 = 39.888888/3 = 13.296296
    expected_values = [np.nan, np.nan, 11.0, 11.666666666666666, 12.444444444444445, 13.296296296296297]
    expected = pd.Series(expected_values, name=f"SMMA_{period}")
    result = _calculate_smma(series, period)
    pd.testing.assert_series_equal(result, expected, check_dtype=True)

def test_calculate_smma_handles_initial_nans():
    series = pd.Series([np.nan, np.nan, 10.0, 11.0, 12.0, 13.0])
    period = 3
    # SMA[4] = (10+11+12)/3 = 11.0
    # SMMA[5] = (11.0 * 2 + 13.0) / 3 = 11.666666
    expected_values = [np.nan, np.nan, np.nan, np.nan, 11.0, 11.666666666666666]
    expected = pd.Series(expected_values, name=f"SMMA_{period}")
    result = _calculate_smma(series, period)
    pd.testing.assert_series_equal(result, expected, check_dtype=True)

def test_calculate_smma_series_shorter_than_period():
    series = pd.Series([10.0, 11.0])
    period = 3
    expected = pd.Series([np.nan, np.nan], name=f"SMMA_{period}")
    result = _calculate_smma(series, period)
    pd.testing.assert_series_equal(result, expected, check_dtype=True)

def test_calculate_smma_all_nans_input():
    series = pd.Series([np.nan, np.nan, np.nan, np.nan])
    period = 3
    expected = pd.Series([np.nan, np.nan, np.nan, np.nan], name=f"SMMA_{period}")
    result = _calculate_smma(series, period)
    pd.testing.assert_series_equal(result, expected, check_dtype=True)

def test_calculate_smma_with_intermittent_nans():
    series = pd.Series([10.0, 11.0, 12.0, np.nan, 14.0, 15.0])
    period = 3
    # SMA[2] = 11.0
    # SMMA[3] = (11.0 * 2 + np.nan) / 3 -> This logic needs care. Current SMMA propagates NaN.
    # If series.iloc[i] is NaN, smma.iloc[i] becomes NaN.
    # If smma.iloc[i-1] is NaN, smma.iloc[i] becomes NaN.
    expected_values = [np.nan, np.nan, 11.0, np.nan, np.nan, np.nan]
    # Let's trace:
    # smma[2] = 11.0
    # smma[3] = (smma[2]*2 + series[3]=nan) / 3 = nan
    # smma[4] = (smma[3]=nan*2 + series[4]=14.0) / 3 = nan
    # smma[5] = (smma[4]=nan*2 + series[5]=15.0) / 3 = nan
    expected = pd.Series(expected_values, name=f"SMMA_{period}")
    result = _calculate_smma(series, period)
    pd.testing.assert_series_equal(result, expected, check_dtype=True)


# --- Tests for run_williams_alligator Main Function ---

def test_alligator_indicator_calculation(short_period_alligator_config: WilliamsAlligatorConfig):
    dates = pd.date_range(start="2023-01-01", periods=20, freq="D").strftime("%Y-%m-%d").tolist()
    closes = [10,11,12,13,14,15,16,17,18,19,20,19,18,17,16,15,14,13,12,11]
    df_input = create_ohlcv_df(dates, closes, closes, closes, closes, [100]*20) # Using close for O,H,L for simplicity

    config = short_period_alligator_config # Lips(2,1), Teeth(3,2), Jaw(5,3)

    results = run_williams_alligator(df_input, config)
    indicator_df = results["indicator_data"]

    assert "jaw" in indicator_df.columns
    assert "teeth" in indicator_df.columns
    assert "lips" in indicator_df.columns

    # Check for NaNs at the beginning due to SMMA and shifting
    # Max shift is jaw_shift=3. Max period for SMMA is jaw_period=5.
    # So, first (5-1)+3 = 7 values for jaw should be NaN.
    # Lips: (2-1)+1 = 2 NaNs. Teeth: (3-1)+2 = 4 NaNs.
    assert indicator_df['lips'].iloc[:config.lips_period-1+config.lips_shift].isnull().all()
    assert indicator_df['teeth'].iloc[:config.teeth_period-1+config.teeth_shift].isnull().all()
    assert indicator_df['jaw'].iloc[:config.jaw_period-1+config.jaw_shift].isnull().all()

    # Check a few specific values manually if possible, or rely on SMMA tests
    # For example, lips (period=2, shift=1)
    # price_source = df_input['Close']
    # smma_lips_no_shift_period2 = _calculate_smma(price_source, 2) -> [n, 10.5, 11.5, 12.5, ...]
    # lips = smma_lips_no_shift_period2.shift(1) -> [n, n, 10.5, 11.5, ...]
    # So, indicator_df['lips'].iloc[2] should be (closes[0]+closes[1])/2 = (10+11)/2 = 10.5
    # But this is before shifting.
    # After shifting by 1: indicator_df['lips'].iloc[2] is smma_lips_no_shift_period2.iloc[1] = 10.5
    # The way _calculate_smma is written, smma_lips_no_shift_period2.iloc[1] is the first SMMA value
    # smma_lips_no_shift_period2.iloc[1] = (closes.iloc[0] + closes.iloc[1])/2 = 10.5
    # lips.iloc[1+1] = smma_lips_no_shift_period2.iloc[1] -> lips.iloc[2] = 10.5
    if not indicator_df['lips'].iloc[config.lips_period-1+config.lips_shift:].isnull().all(): # Check if any non-NaN
        assert pd.notna(indicator_df['lips'].iloc[config.lips_period-1+config.lips_shift])


def test_alligator_buy_signal_on_bullish_crossover(short_period_alligator_config: WilliamsAlligatorConfig):
    # Data: initial tangle/bearish, then bullish crossover and spread
    # Lips (2,1), Teeth (3,2), Jaw (5,3)
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 21)] # 20 days
    # Initial state: Jaw > Teeth > Lips (Bearish or tangled)
    # Then transition to Lips > Teeth > Jaw (Bullish)
    closes = ([15,14,13,12,11] + # Initial bearish separation for SMMA history (Jaw highest)
              [10,10,10,10,10] + # Sleep / Tangle
              [11,12,13,14,15] + # Lips starts crossing
              [16,17,18,19,20])  # Bullish spread: Lips > Teeth > Jaw
    df = create_ohlcv_df(dates, closes, closes, closes, closes, [1000]*20)

    results = run_williams_alligator(df, short_period_alligator_config)
    signals = results["signals"]

    buy_signals = [s for s in signals if s["type"] == "BUY" and "bullish crossover" in s["reason"]]
    assert len(buy_signals) >= 1, "Should generate at least one BUY signal on bullish crossover"
    if buy_signals:
        first_buy_signal = buy_signals[0]
        # Assertions on the first buy signal's properties can be added here
        # e.g., assert first_buy_signal['price'] is df.loc[first_buy_signal['date']]['close']

def test_alligator_sell_signal_on_bearish_crossover(short_period_alligator_config: WilliamsAlligatorConfig):
    # Data: initial tangle/bullish, then bearish crossover and spread
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 21)]
    closes = ([10,11,12,13,14] + # Initial bullish separation
              [15,15,15,15,15] + # Sleep / Tangle
              [14,13,12,11,10] + # Lips starts crossing down
              [9,8,7,6,5])       # Bearish spread
    df = create_ohlcv_df(dates, closes, closes, closes, closes, [1000]*20)

    results = run_williams_alligator(df, short_period_alligator_config)
    signals = results["signals"]

    sell_signals = [s for s in signals if s["type"] == "SELL" and "bearish crossover" in s["reason"]]
    assert len(sell_signals) >= 1, "Should generate at least one SELL signal on bearish crossover"

def test_alligator_hold_when_sleeping(short_period_alligator_config: WilliamsAlligatorConfig):
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 21)]
    closes = [10, 10.1, 10, 10.2, 10.1, 10, 9.9, 10, 10.1, 10.2, # Choppy, tangled
              10.3, 10.2, 10.1, 10, 9.9, 9.8, 9.9, 10, 10.1, 10]
    df = create_ohlcv_df(dates, closes, [c+0.2 for c in closes], [c-0.2 for c in closes], closes, [1000]*20)

    results = run_williams_alligator(df, short_period_alligator_config)
    signals = results["signals"]

    # In "sleeping" phase, expect mostly HOLD signals or fewer BUY/SELL
    # The exact number of HOLDs depends on the strictness of crossover conditions.
    # If there are any BUY/SELL, they should be quickly followed by exits or counter-signals if it's truly tangled.
    # For this test, let's assert that there isn't a persistent BUY or SELL trend.
    non_hold_signals = [s for s in signals if s["type"] != "HOLD"]
    if non_hold_signals:
        # If there are buy/sell signals, check if they are somewhat balanced or quickly reversed
        # This is a qualitative check for "sleeping" behavior
        action_sequence = [s['type'] for s in non_hold_signals]
        # A very simple check: not too many consecutive signals of the same type without reversal
        # Example: No more than 2 consecutive BUYs without a SELL, or vice-versa
        consecutive_buys = 0
        consecutive_sells = 0
        for action in action_sequence:
            if action == "BUY":
                consecutive_buys +=1
                consecutive_sells = 0
            elif action == "SELL":
                consecutive_sells += 1
                consecutive_buys = 0
            assert consecutive_buys < 3, "Too many consecutive BUYs in tangled market"
            assert consecutive_sells < 3, "Too many consecutive SELLs in tangled market"
    # Or, more simply, assert that the number of BUY/SELL signals is low relative to HOLDs or data length
    assert len(non_hold_signals) < len(df) / 2 , "Too many non-HOLD signals in a supposedly tangled market"


def test_alligator_no_signals_insufficient_data(default_alligator_config: WilliamsAlligatorConfig):
    # Default config: jaw (13,8), teeth (8,5), lips (5,3)
    # Max lookback needed for lines: (13-1)+8 = 20 for jaw. Need at least 21 data points for first value.
    # Need 22 for signal generation (current + previous).
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 15)] # Only 14 data points
    closes = [100 + i for i in range(14)]
    df = create_ohlcv_df(dates, closes, closes, closes, closes, [100]*14)

    results = run_williams_alligator(df, default_alligator_config)
    assert len(results["signals"]) == 0
    assert results["indicator_data"]['jaw'].isnull().all() # Alligator lines should be mostly NaN

# Further tests to consider:
# - test_alligator_exit_long_on_bearish_signal
# - test_alligator_exit_short_on_bullish_signal
# - test_alligator_price_source_hlc3 (verifying SMMA calculation uses hlc3)
# - test_alligator_handles_initial_nans_in_indicators_for_signals (ensure no signals if lines are NaN)

