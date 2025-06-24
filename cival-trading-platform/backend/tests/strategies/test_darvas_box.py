import pytest
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

# Adjust imports based on how pytest will discover the modules.
# Assuming 'python-ai-services' is in PYTHONPATH or tests are run from a project root.
from python_ai_services.strategies.darvas_box import run_darvas_box, _find_new_high
from python_ai_services.models.strategy_models import DarvasBoxConfig

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
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=pd.to_datetime(dates))

# --- Default Config for Tests ---
@pytest.fixture
def default_darvas_config() -> DarvasBoxConfig:
    """Provides a default DarvasBoxConfig for tests."""
    return DarvasBoxConfig(
        lookback_period_highs=50, # Default to a reasonable period for tests
        box_definition_period=10,
        volume_increase_factor=1.5,
        box_range_tolerance_percent=1.0,
        min_box_duration=3,
        stop_loss_percent_from_bottom=2.0
    )

# --- Tests for _find_new_high Helper Function ---

def test_find_new_high_basic():
    series = pd.Series([10, 12, 11, 13, 12, 14, 13]) # New highs at idx 1, 3, 5
    lookback = 3
    expected = pd.Series([False, True, False, True, False, True, False])
    pd.testing.assert_series_equal(_find_new_high(series, lookback), expected, check_dtype=False)

    series_short_lookback = pd.Series([10,9,8,12]) # new high at 12 (idx 3)
    lookback_short = 2
    expected_short = pd.Series([False, False, False, True])
    pd.testing.assert_series_equal(_find_new_high(series_short_lookback, lookback_short), expected_short, check_dtype=False)


def test_find_new_high_no_new_highs():
    series = pd.Series([15, 14, 13, 12, 11])
    lookback = 3
    expected = pd.Series([False, False, False, False, False])
    pd.testing.assert_series_equal(_find_new_high(series, lookback), expected, check_dtype=False)

    series_flat = pd.Series([10, 10, 10, 10, 10])
    expected_flat = pd.Series([False, False, False, False, False])
    pd.testing.assert_series_equal(_find_new_high(series_flat, lookback), expected_flat, check_dtype=False)

def test_find_new_high_with_full_lookback_match():
    # New high if it's higher than ALL previous 'lookback' days.
    series = pd.Series([10, 11, 12, 13, 12, 13.5]) # High at index 3 (13), index 5 (13.5)
    lookback = 3 # Compares with s[0:3] for s[3], s[1:4] for s[4] etc. after shift
                 # s[3]=13 > max(s[0],s[1],s[2]) = 12 -> True
                 # s[4]=12 not > max(s[1],s[2],s[3]) = 13 -> False
                 # s[5]=13.5 > max(s[2],s[3],s[4]) = 13 -> True
    expected = pd.Series([False, False, False, True, False, True])
    pd.testing.assert_series_equal(_find_new_high(series, lookback), expected, check_dtype=False)

def test_find_new_high_edge_cases():
    # Empty series
    series_empty = pd.Series([], dtype=float)
    expected_empty = pd.Series([], dtype=bool) # pd.Series([], dtype='bool') # Pandas >= 1.0.0
    pd.testing.assert_series_equal(_find_new_high(series_empty, 3), expected_empty, check_dtype=False)

    # Series shorter than lookback
    series_short = pd.Series([10, 11])
    lookback = 3
    expected_short = pd.Series([False, False]) # No new highs possible if series < lookback
    pd.testing.assert_series_equal(_find_new_high(series_short, lookback), expected_short, check_dtype=False)

    # Lookback is 1
    series_lookback_1 = pd.Series([10, 9, 11, 10, 12]) # Highs at 11, 12
    lookback_1 = 1
    # s[0]=10, shift(1) is NaN, 10 > NaN is False
    # s[1]=9, shift(1) is 10, 9 > 10 is False
    # s[2]=11, shift(1) is 9, 11 > 9 is True
    # s[3]=10, shift(1) is 11, 10 > 11 is False
    # s[4]=12, shift(1) is 10, 12 > 10 is True
    expected_lookback_1 = pd.Series([False, False, True, False, True])
    pd.testing.assert_series_equal(_find_new_high(series_lookback_1, lookback_1), expected_lookback_1, check_dtype=False)

    # Lookback is 0 or negative (should return all False as per implementation)
    series_any = pd.Series([10,11,12])
    expected_zero_lookback = pd.Series([False,False,False])
    pd.testing.assert_series_equal(_find_new_high(series_any, 0), expected_zero_lookback, check_dtype=False)
    pd.testing.assert_series_equal(_find_new_high(series_any, -1), expected_zero_lookback, check_dtype=False)


# --- Tests for run_darvas_box Main Function ---

def test_run_darvas_box_no_signals_flat_data(default_darvas_config):
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 20)]
    prices = [100.0] * 19
    volumes = [1000] * 19
    df = create_ohlcv_df(dates, prices, prices, prices, prices, volumes)

    results = run_darvas_box(df, default_darvas_config)
    assert len(results["signals"]) == 0
    assert len(results["boxes"]) == 0

def test_run_darvas_box_insufficient_data(default_darvas_config):
    # Data shorter than lookback_period_highs
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 5)]
    prices = [100.0, 101.0, 102.0, 103.0]
    volumes = [1000] * 4
    df = create_ohlcv_df(dates, prices, prices, prices, prices, volumes)

    config = default_darvas_config
    config.lookback_period_highs = 10 # Ensure lookback is greater than data length

    results = run_darvas_box(df, config)
    assert len(results["signals"]) == 0
    assert len(results["boxes"]) == 0

def test_run_darvas_box_successful_box_and_buy_signal(default_darvas_config):
    # Crafted data:
    # Day 0-4: Rising trend (to ensure enough data for lookback)
    # Day 5: New High (112) -> Establishes Box Top
    # Day 6-8: Price stays below Box Top (112), Lows establish Box Bottom (107) and hold for 3 days
    # Day 9: Breakout above Box Top (112) with high volume
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 15)] # 14 days
    data = { # Index from 0 to 13 for easier mapping
        'Open':  [100, 101, 102, 103, 104, 108, 110, 108, 107, 109, 108, 107, 108, 112], # Day 13 (idx 13) opens at breakout
        'High':  [101, 102, 103, 104, 105, 112, # Day 5 (idx 5): New High, Box Top = 112
                  110, 109, 108, 110, 109, 108, 109, 113], # Day 13 (idx 13): Breakout High
        'Low':   [99,  100, 101, 102, 103, 107, # Day 5 (idx 5): Low = 107
                  108, 107, 107, 107, # Day 7,8,9 (idx 7,8,9): Lows hold at 107. Box Bottom = 107. min_box_duration=3 met by day 9.
                  106, 106, 107, 112],
        'Close': [100, 101, 102, 103, 104, 111, # Day 5 (idx 5): Close
                  109, 108, 107.5, 108, # prices stay within box [107-112]
                  107, 107, 108, 112.5],# Day 13 (idx 13): Breakout Close
        'Volume':[100, 100, 100, 100, 100, 100,
                  100, 100, 100, 100, # Avg volume in box (idx 6-12) is low (100)
                  100, 100, 100, 300] # High volume on breakout (idx 13)
    }
    df = create_ohlcv_df(dates, data['Open'], data['High'], data['Low'], data['Close'], data['Volume'])

    config = DarvasBoxConfig(
        lookback_period_highs=5, # New high on day 5 (idx 5) value 112
        box_definition_period=10, # Max days to form box
        volume_increase_factor=1.5,
        min_box_duration=3, # Min days bottom must hold
        stop_loss_percent_from_bottom=1.0,
        box_range_tolerance_percent=0.5 # Tight tolerance
    )

    results = run_darvas_box(df, config)

    assert len(results["signals"]) == 1
    signal = results["signals"][0]
    assert signal["type"] == "BUY"
    assert signal["date"] == pd.Timestamp(dates[13]) # Breakout date
    assert signal["price"] == 112.5 # Breakout close price
    assert signal["box_top"] == 112.0
    assert signal["box_bottom"] == 107.0
    assert signal["stop_loss"] == round(107.0 * (1 - 0.01), 2) # 107 * 0.99 = 105.93

    assert len(results["boxes"]) == 1
    box = results["boxes"][0]
    assert box["start_date"] == pd.Timestamp(dates[5]) # Date box top was set
    assert box["end_date"] == pd.Timestamp(dates[12]) # Day before breakout
    assert box["top"] == 112.0
    assert box["bottom"] == 107.0
    assert box["breakout_date"] == pd.Timestamp(dates[13])

def test_run_darvas_box_breakout_no_volume(default_darvas_config: DarvasBoxConfig):
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 15)]
    data = { # Same data as successful_box_and_buy_signal, but volume on breakout is low
        'Open':  [100,101,102,103,104,108,110,108,107,109,108,107,108,112],
        'High':  [101,102,103,104,105,112,110,109,108,110,109,108,109,113],
        'Low':   [99,100,101,102,103,107,108,107,107,107,106,106,107,112],
        'Close': [100,101,102,103,104,111,109,108,107.5,108,107,107,108,112.5],
        'Volume':[100,100,100,100,100,100,100,100,100,100,100,100,100, 110] # LOW volume on breakout
    }
    df = create_ohlcv_df(dates, data['Open'], data['High'], data['Low'], data['Close'], data['Volume'])
    config = DarvasBoxConfig(lookback_period_highs=5, min_box_duration=3, volume_increase_factor=1.5)

    results = run_darvas_box(df, config)
    assert len(results["signals"]) == 0 # No signal due to low volume
    # A box might still be recorded if the breakout attempt is logged, or not if it resets.
    # Current logic: if breakout fails volume, no box is recorded for that attempt.
    # To test if a box was formed *before* the failed breakout, would need more complex assertions
    # or modification of run_darvas_box to log "attempted breakouts" or "defined boxes before breakout".
    # For now, we expect no "completed" breakout box.
    found_box_for_breakout_attempt = False
    for box_rec in results["boxes"]:
        if box_rec["top"] == 112.0 and box_rec["breakout_date"] is not None:
            found_box_for_breakout_attempt = True
            break
    assert not found_box_for_breakout_attempt


def test_run_darvas_box_top_violated_during_formation(default_darvas_config: DarvasBoxConfig):
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 10)]
    data = { # New high, then top is violated before bottom is confirmed
        'Open':  [100,101,102,103,104,108,110,113,110],
        'High':  [101,102,103,104,105,112, # Day 5 (idx 5): New High, Box Top = 112
                  110, # Day 6 (idx 6): Stays below top
                  114, # Day 7 (idx 7): Violates top 112 (114 > 112 * (1+tolerance if any))
                  111],
        'Low':   [99,100,101,102,103,107,108,111,109],
        'Close': [100,101,102,103,104,111,109,113,110],
        'Volume':[100,100,100,100,100,100,100,100,100]
    }
    df = create_ohlcv_df(dates, data['Open'], data['High'], data['Low'], data['Close'], data['Volume'])
    config = DarvasBoxConfig(lookback_period_highs=5, min_box_duration=3, box_range_tolerance_percent=0.1) # Very tight tolerance

    results = run_darvas_box(df, config)
    assert len(results["signals"]) == 0
    assert len(results["boxes"]) == 0 # Box formation should have been reset

def test_run_darvas_box_parameter_sensitivity_min_duration(default_darvas_config: DarvasBoxConfig):
    # Same data as successful_box_and_buy_signal, but breakout happens before min_box_duration met
    # For this, we need the bottom to be tested for fewer than min_box_duration days
    # Original data: Box Bottom (107) holds for Day 7,8,9 (idx 7,8,9) -> 3 days
    # Breakout on Day 13 (idx 13)
    # If min_box_duration is 4, this should fail. If 3, it passes.

    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 15)]
    data = {
        'Open':  [100,101,102,103,104,108,110,108,107,109,108,107,108,112],
        'High':  [101,102,103,104,105,112,110,109,108,110,109,108,109,113],
        'Low':   [99,100,101,102,103,107,108,107,107,107,106,106,107,112],
        'Close': [100,101,102,103,104,111,109,108,107.5,108,107,107,108,112.5],
        'Volume':[100,100,100,100,100,100,100,100,100,100,100,100,100,300]
    }
    df = create_ohlcv_df(dates, data['Open'], data['High'], data['Low'], data['Close'], data['Volume'])

    config_strict_duration = DarvasBoxConfig(
        lookback_period_highs=5,
        min_box_duration=4, # Increased duration
        volume_increase_factor=1.5,
        box_definition_period=10,
        stop_loss_percent_from_bottom=1.0,
        box_range_tolerance_percent=0.5
    )
    results_strict = run_darvas_box(df, config_strict_duration)
    assert len(results_strict["signals"]) == 0 # Fails because bottom held for 3 days (idx 7,8,9) but min_box_duration is 4

    config_pass_duration = DarvasBoxConfig(
        lookback_period_highs=5,
        min_box_duration=3, # Original duration
        volume_increase_factor=1.5,
        box_definition_period=10,
        stop_loss_percent_from_bottom=1.0,
        box_range_tolerance_percent=0.5
    )
    results_pass = run_darvas_box(df, config_pass_duration)
    assert len(results_pass["signals"]) == 1 # Should pass with min_box_duration=3


# Add more tests:
# - test_run_darvas_box_multiple_boxes_and_signals (requires more complex data setup)
# - test_run_darvas_box_box_definition_period_timeout
# - test_run_darvas_box_bottom_violation_after_confirmation (box breaks down, no signal)
