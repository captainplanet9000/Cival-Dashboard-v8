import pytest
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

from python_ai_services.strategies.renko import run_renko, _calculate_atr, _calculate_renko_bricks
from python_ai_services.models.strategy_models import RenkoConfig, RenkoBrickSizeMethod
from python_ai_services.types.trading_types import TradeAction # For signal type assertion

# Helper function to create OHLCV DataFrames for tests
def create_ohlcv_df(
    dates: List[str],
    opens: Optional[List[float]] = None,
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
    closes: Optional[List[float]] = None,
    volumes: Optional[List[int]] = None,
    use_close_for_all_prices: bool = False
) -> pd.DataFrame:
    if use_close_for_all_prices and closes is not None:
        opens = highs = lows = closes

    data_dict: Dict[str, Any] = {'Close': closes if closes else []}
    # Ensure all required columns are present for ATR calculation if highs/lows/closes are None initially
    default_series = [0.0] * len(dates) if dates else []
    data_dict['High'] = highs if highs is not None else (closes if closes is not None else default_series)
    data_dict['Low'] = lows if lows is not None else (closes if closes is not None else default_series)
    data_dict['Open'] = opens if opens is not None else (closes if closes is not None else default_series)
    data_dict['Close'] = closes if closes is not None else default_series # Should always be present

    if volumes: data_dict['Volume'] = volumes
    else: data_dict['Volume'] = [100] * len(dates) # Default volume if not provided

    return pd.DataFrame(data_dict, index=pd.to_datetime(dates))

# --- Fixtures ---
@pytest.fixture
def atr_renko_config_default() -> RenkoConfig:
    return RenkoConfig(brick_size_method=RenkoBrickSizeMethod.ATR, atr_period=14, price_source_column="close")

@pytest.fixture
def fixed_renko_config_default() -> RenkoConfig:
    return RenkoConfig(brick_size_method=RenkoBrickSizeMethod.FIXED, brick_size_value=1.0, price_source_column="close")

# --- Tests for _calculate_atr ---
def test_calculate_atr_basic():
    dates = pd.date_range(start="2023-01-01", periods=20, freq="D")
    high_data = np.array([10, 11, 10, 12, 13, 11, 12, 14, 13, 12, 15, 16, 14, 13, 12, 14, 15, 16, 17, 18.0])
    low_data  = np.array([ 9, 10,  9, 10, 11, 10, 10, 12, 11, 11, 13, 14, 12, 11, 10, 12, 13, 14, 15, 16.0])
    close_data= np.array([9.5,10.5,9.5,11.5,12.5,10.5,11.5,13.5,12.5,11.5,14.5,15.5,13.5,12.5,11.5,13.5,14.5,15.5,16.5,17.5])
    df = create_ohlcv_df(dates.strftime("%Y-%m-%d").tolist(), highs=high_data.tolist(), lows=low_data.tolist(), closes=close_data.tolist())

    atr_period = 5
    atr_series = _calculate_atr(df['high'], df['low'], df['close'], period=atr_period)

    assert isinstance(atr_series, pd.Series)
    assert atr_series.name == f"ATR_{atr_period}"
    assert atr_series.iloc[:atr_period].isnull().all()
    assert pd.notna(atr_series.iloc[atr_period])

    # TR values (from index 1, index 0 is effectively NaN for TR):
    # H-L: [1,1,1,2,2,1,2,2,2,1,2,2,2,2,2,2,2,2,2]
    # abs(H-Cp): [1.5,0.5,2.5,1.5,2.5,1.5,2.5,0.5,1.5,2.5,1.5,2.5,1.5,2.5,1.5,1.5,1.5,1.5]
    # abs(L-Cp): [0.5,1.5,0.5,0.5,0.5,1.5,0.5,1.5,0.5,1.5,0.5,1.5,0.5,1.5,0.5,1.5,0.5,1.5]
    # TR_calc: [1.5, 1.5, 2.5, 2.0, 2.5, 2.0, 2.5, 2.0, 1.5, 2.5, 2.0, 2.5, 2.0, 2.5, 2.0, 2.0, 2.0, 2.0] (len 19)
    # First ATR (ATR[5]) = mean(TR[1]..TR[5]) = (1.5+1.5+2.5+2.0+2.5)/5 = 10/5 = 2.0
    # ATR[6] = (ATR[5]*(5-1) + TR[6])/5. TR[6] (for day idx 6) is 2.0
    # ATR[6] = (2.0*4 + 2.0)/5 = (8+2)/5 = 10/5 = 2.0
    assert abs(atr_series.iloc[atr_period] - 2.0) < 0.001
    assert abs(atr_series.iloc[atr_period+1] - 2.0) < 0.001

def test_calculate_atr_short_series():
    dates = pd.date_range(start="2023-01-01", periods=5)
    closes = [10,11,12,11,10]
    df = create_ohlcv_df(dates.strftime("%Y-%m-%d").tolist(), closes=closes, use_close_for_all_prices=True)
    atr = _calculate_atr(df['high'], df['low'], df['close'], 14) # Period longer than series
    assert atr.isnull().all()

# --- Tests for _calculate_renko_bricks ---
def test_renko_bricks_upward_trend(fixed_renko_config_default: RenkoConfig):
    config = fixed_renko_config_default
    prices = pd.Series([10.0, 10.5, 11.2, 10.8, 12.3, 13.0, 12.5, 13.8, 14.2],
                       index=pd.to_datetime([f"2023-01-0{i}" for i in range(1,10)]))
    bricks_df = _calculate_renko_bricks(prices, config.brick_size_value) # type: ignore
    assert bricks_df['brick_type'].tolist() == ['up', 'up', 'up', 'up']
    assert bricks_df['open'].tolist() == [10.0, 11.0, 12.0, 13.0]
    assert bricks_df['close'].tolist() == [11.0, 12.0, 13.0, 14.0]

def test_renko_bricks_downward_trend(fixed_renko_config_default: RenkoConfig):
    config = fixed_renko_config_default
    prices = pd.Series([15.0, 14.5, 13.8, 14.2, 12.7, 12.0, 12.5, 11.2, 10.9],
                       index=pd.to_datetime([f"2023-01-0{i}" for i in range(1,10)]))
    bricks_df = _calculate_renko_bricks(prices, config.brick_size_value) # type: ignore
    assert bricks_df['brick_type'].tolist() == ['down', 'down', 'down', 'down']

def test_renko_bricks_reversal_up_to_down(fixed_renko_config_default: RenkoConfig):
    config = fixed_renko_config_default
    prices = pd.Series([10, 10.5, 11.1, 11.5, 12.2, 11.8, 10.8, 9.9, 8.7],
                       index=pd.to_datetime([f"2023-01-{str(i).zfill(2)}" for i in range(1,10)]))
    bricks_df = _calculate_renko_bricks(prices, config.brick_size_value) # type: ignore
    assert bricks_df['brick_type'].tolist() == ['up', 'up', 'down', 'down', 'down']
    assert bricks_df['open'].tolist() == [10.0, 11.0, 12.0, 11.0, 10.0]
    assert bricks_df['close'].tolist() == [11.0, 12.0, 11.0, 10.0, 9.0]

def test_renko_bricks_no_movement_less_than_brick_size(fixed_renko_config_default: RenkoConfig):
    config = fixed_renko_config_default
    prices = pd.Series([10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9],
                       index=pd.to_datetime([f"2023-01-{str(i).zfill(2)}" for i in range(1,11)]))
    bricks_df = _calculate_renko_bricks(prices, config.brick_size_value) # type: ignore
    assert bricks_df.empty # No full brick movement

# --- Tests for run_renko ---
@pytest.mark.parametrize("price_data, expected_brick_count, min_actionable_signals", [
    ([100, 101, 102, 103, 104, 105], 5, 1),
    ([100, 99, 98, 97, 96, 95], 5, 1),
    ([100, 100.1, 100.2, 100.3, 100.4], 0, 0),
])
def test_run_renko_fixed_brick_scenarios(fixed_renko_config_default: RenkoConfig, price_data, expected_brick_count, min_actionable_signals):
    config = fixed_renko_config_default
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, len(price_data) + 1)]
    df = create_ohlcv_df(dates, closes=price_data, use_close_for_all_prices=True)

    results = run_renko(df, config)
    assert results["brick_size_used"] == config.brick_size_value
    assert len(results["renko_bricks"]) == expected_brick_count
    actionable_signals = [s for s in results["signals"] if s["type"] != "HOLD"]
    assert len(actionable_signals) >= min_actionable_signals

@patch('python_ai_services.strategies.renko._calculate_atr')
def test_run_renko_atr_brick_size(mock_calc_atr: MagicMock, atr_renko_config_default: RenkoConfig):
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 31)]
    closes = [100 + np.sin(i/5)*5 + i*0.1 for i in range(30)]
    df = create_ohlcv_df(dates, closes=closes, use_close_for_all_prices=True)

    mock_atr_value = 2.34
    mock_calc_atr.return_value = pd.Series([np.nan]*(atr_renko_config_default.atr_period) + [mock_atr_value]*(len(df)-atr_renko_config_default.atr_period), index=df.index)

    results = run_renko(df, atr_renko_config_default)
    assert results["brick_size_used"] == mock_atr_value
    mock_calc_atr.assert_called_once()

def test_run_renko_output_structure(fixed_renko_config_default: RenkoConfig):
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 10)]
    closes = [10,11,12,13,14,13,12,11,10]
    df = create_ohlcv_df(dates, closes=closes, use_close_for_all_prices=True)
    results = run_renko(df, fixed_renko_config_default)

    assert "signals" in results and isinstance(results["signals"], list)
    assert "renko_bricks" in results and isinstance(results["renko_bricks"], pd.DataFrame)
    assert "brick_size_used" in results and isinstance(results["brick_size_used"], float)
    if not results["renko_bricks"].empty:
        assert all(col in results["renko_bricks"].columns for col in ['timestamp', 'brick_type', 'open', 'close'])

def test_run_renko_insufficient_data_for_atr(atr_renko_config_default: RenkoConfig):
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, atr_renko_config_default.atr_period)] # Data < ATR period
    closes = [100+i for i in range(len(dates))]
    df = create_ohlcv_df(dates, closes=closes, use_close_for_all_prices=True)
    results = run_renko(df, atr_renko_config_default) # Should use fallback brick size
    assert len(results["signals"]) == 0 # Likely no signals with fallback on tiny data
    assert results["brick_size_used"] > 0 # Check fallback was applied
    assert results["renko_bricks"].empty # Not enough data to form bricks even with fallback sometimes

def test_run_renko_price_source_hlc3(fixed_renko_config_default: RenkoConfig):
    dates = [f"2023-01-{str(i).zfill(2)}" for i in range(1, 10)]
    config = fixed_renko_config_default
    config.price_source_column = "hlc3" # type: ignore
    # Create data where close is flat but hlc3 moves
    df = create_ohlcv_df(
        dates,
        opens=[10,11,12,11,10, 9,10,11,10],
        highs=[12,13,14,13,12,11,12,13,12],
        lows= [ 8, 9,10, 9, 8, 7, 8, 9, 8],
        closes=[10,10,10,10,10,10,10,10,10], # Flat close
        volumes=[100]*9
    )
    df_hlc3 = df.copy()
    df_hlc3['hlc3'] = (df['high'] + df['low'] + df['close']) / 3

    # Mock _calculate_renko_bricks to check the series passed
    with patch('python_ai_services.strategies.renko._calculate_renko_bricks', return_value=pd.DataFrame()) as mock_calc_bricks:
        run_renko(df_hlc3, config)
        mock_calc_bricks.assert_called_once()
        passed_series = mock_calc_bricks.call_args[0][0]
        pd.testing.assert_series_equal(passed_series, df_hlc3['hlc3'], check_names=False)

def test_run_renko_signal_buy_after_two_up_bricks(fixed_renko_config_default: RenkoConfig):
    config = fixed_renko_config_default
    config.brick_size_value = 1.0
    # Prices: 10 (base) -> 11.1 (1st up brick [10,11]) -> 12.1 (2nd up brick [11,12] -> BUY)
    dates = ["2023-01-01", "2023-01-02", "2023-01-03"]
    closes = [10.0, 11.1, 12.1]
    df = create_ohlcv_df(dates, closes=closes, use_close_for_all_prices=True)
    results = run_renko(df, config)
    buy_signals = [s for s in results["signals"] if s["type"] == TradeAction.BUY.value] # Use .value for enum comparison
    assert len(buy_signals) == 1
    assert buy_signals[0]["price"] == 12.0 # Signal at close of 2nd up brick
    assert buy_signals[0]["brick_type"] == "up"
    assert "Two consecutive 'up' bricks" in buy_signals[0]["reason"]

