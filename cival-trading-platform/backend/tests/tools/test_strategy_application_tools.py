import pytest
import json
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

# Adjust import path based on test execution context
from python_ai_services.tools.strategy_application_tools import (
    apply_darvas_box_tool, ApplyDarvasBoxArgs,
    apply_williams_alligator_tool, ApplyWilliamsAlligatorArgs,
    apply_renko_tool, ApplyRenkoArgs,
    apply_heikin_ashi_tool, ApplyHeikinAshiArgs,
    apply_elliott_wave_tool, ApplyElliottWaveArgs
)
from python_ai_services.models.strategy_models import (
    DarvasBoxConfig,
    WilliamsAlligatorConfig,
    RenkoConfig, RenkoBrickSizeMethod,
    HeikinAshiConfig,
    ElliottWaveConfig
)
from python_ai_services.models.crew_models import StrategyApplicationResult
from python_ai_services.types.trading_types import TradeAction

# Helper to get sample market data JSON string
def get_sample_processed_market_data_json(symbol="TEST/SYM", days=60, add_volume_sma=True) -> str:
    """
    Generates a sample processed_market_data_json string, mimicking
    the output of run_technical_analysis_tool.
    The OHLCV records in 'ohlcv_with_ta' should NOT have 'symbol' field each.
    """
    ohlcv_records = []
    base_price = 100.0
    current_dt = pd.Timestamp("2023-01-01T00:00:00Z")
    volumes = []

    for i in range(days):
        current_dt += pd.Timedelta(days=1)
        price_movement = i * 0.1
        if i > days * 0.66: price_movement -= (i - days * 0.66) * 0.3
        elif i > days * 0.33: price_movement += (i - days * 0.33) * 0.2

        open_price = round(base_price + price_movement, 2)
        high_price = round(open_price + (2 + (i % 3)), 2)
        low_price = round(open_price - (2 + (i % 2)), 2)
        close_price = round((open_price + high_price + low_price + open_price) / 4, 2)
        volume = 1000 + (i * 10) + (5000 if i == days - (days // 4) else 0)

        volumes.append(volume)
        ohlcv_records.append({
            "timestamp": current_dt.isoformat(),
            "open": open_price, "high": high_price, "low": low_price,
            "close": close_price, "volume": volume
        })

    columns_available = ["timestamp", "open", "high", "low", "close", "volume"]
    if add_volume_sma and days >= 20:
        temp_df = pd.DataFrame(ohlcv_records)
        temp_df['volume'] = pd.to_numeric(temp_df['volume'], errors='coerce')
        sma_min_periods = min(20, len(temp_df['volume'].dropna()))
        if sma_min_periods > 0 and sma_min_periods <= 20:
            temp_df['volume_sma'] = temp_df['volume'].rolling(window=20, min_periods=sma_min_periods).mean().round(2)
            for i, record in enumerate(ohlcv_records):
                sma_val = temp_df.loc[i, 'volume_sma'] if 'volume_sma' in temp_df.columns else None
                record['volume_sma'] = None if pd.isna(sma_val) else sma_val
            if 'volume_sma' not in columns_available: columns_available.append("volume_sma")
        else:
            for record in ohlcv_records: record['volume_sma'] = None

    return json.dumps({
        "symbol": symbol,
        "timeframe": "1d",
        "summary": f"Technical analysis complete for {symbol}. DataFrame includes {len(ohlcv_records)} records.",
        "ohlcv_with_ta": ohlcv_records,
        "columns_available": columns_available
    })

# --- Tests for apply_darvas_box_tool ---
@pytest.fixture
def sample_darvas_config_dict() -> Dict[str, Any]:
    return DarvasBoxConfig().model_dump()

@patch('python_ai_services.tools.strategy_application_tools.run_darvas_box')
def test_apply_darvas_box_tool_success_buy_signal(mock_run_darvas: MagicMock, sample_darvas_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="DB_BUY", days=60)
    sample_darvas_config_dict["lookback_period_highs"] = 30
    mock_darvas_output = {
        "signals": [{"date": pd.Timestamp("2023-03-01T00:00:00Z"), "type": "BUY", "price": 115.0, "box_top": 112.0, "box_bottom": 107.0, "stop_loss": 105.93}],
        "boxes": [{"start_date": pd.Timestamp("2023-02-01T00:00:00Z"), "top": 112.0, "bottom": 107.0, "breakout_date": pd.Timestamp("2023-03-01T00:00:00Z")}]
    }
    mock_run_darvas.return_value = mock_darvas_output
    result_json = apply_darvas_box_tool(processed_market_data_json=market_json_str, darvas_config=sample_darvas_config_dict)
    data = json.loads(result_json)

    assert "error" not in data, f"Tool returned an error: {data.get('error')}"

    mock_run_darvas.assert_called_once()
    # Check the DataFrame passed to the mocked run_darvas_box
    call_args = mock_run_darvas.call_args
    passed_df = call_args[0][0]
    assert isinstance(passed_df, pd.DataFrame)
    assert isinstance(passed_df.index, pd.DatetimeIndex)
    assert not passed_df.empty
    # Check for essential columns Darvas Box needs
    expected_cols_for_strategy = ['open', 'high', 'low', 'close', 'volume']
    for col in expected_cols_for_strategy:
        assert col in passed_df.columns
        assert pd.api.types.is_numeric_dtype(passed_df[col])

    assert isinstance(call_args[0][1], DarvasBoxConfig) # Check config type

    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.advice == TradeAction.BUY
    assert parsed_result.additional_data["boxes_found"][0]["top"] == 112.0
    assert "input_ohlcv_preview" in parsed_result.additional_data
    assert len(parsed_result.additional_data["input_ohlcv_preview"]) <= 5


@patch('python_ai_services.tools.strategy_application_tools.run_darvas_box')
def test_apply_darvas_box_tool_no_signal_hold(mock_run_darvas: MagicMock, sample_darvas_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="DB_HOLD", days=60)
    mock_run_darvas.return_value = {"signals": [], "boxes": []}

    result_json = apply_darvas_box_tool(processed_market_data_json=market_json_str, darvas_config=sample_darvas_config_dict)
    data = json.loads(result_json)
    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.advice == TradeAction.HOLD
    assert "input_ohlcv_preview" in parsed_result.additional_data

def test_apply_darvas_box_tool_invalid_darvas_config():
    market_json_str = get_sample_processed_market_data_json() # Valid market data
    invalid_config = {"lookback_period_highs": -5, "this_is_extra": "bad"} # Invalid and extra field

    result_json = apply_darvas_box_tool(processed_market_data_json=market_json_str, darvas_config=invalid_config)
    data = json.loads(result_json)
    assert "error" in data
    assert "Invalid Darvas Box configuration" in data["error"]
    assert "details" in data
    # Pydantic v2+ error format for .errors() is a list of dicts
    assert any("lookback_period_highs" in e.get("loc", ()) for e in data["details"])
    assert any("extra_forbidden" in e.get("type", "") and "this_is_extra" in str(e.get("loc",())) for e in data["details"])


def test_apply_darvas_box_tool_malformed_market_json():
    malformed_json_str = '{"symbol": "MALFORMED", "ohlcv_with_ta": [{}, ...' # Incomplete JSON
    result_json = apply_darvas_box_tool(processed_market_data_json=malformed_json_str, darvas_config={"lookback_period_highs":10})
    data = json.loads(result_json)
    assert "error" in data
    assert "Invalid JSON format for market data" in data["error"]

def test_apply_darvas_box_tool_missing_key_in_market_json():
    # Valid JSON, but missing 'ohlcv_with_ta' key
    market_data = json.loads(get_sample_processed_market_data_json())
    del market_data['ohlcv_with_ta']
    missing_key_json_str = json.dumps(market_data)

    result_json = apply_darvas_box_tool(processed_market_data_json=missing_key_json_str, darvas_config={"lookback_period_highs":10})
    data = json.loads(result_json)
    assert "error" in data
    assert "Market data 'ohlcv_with_ta' field is invalid or empty" in data["error"]

def test_apply_darvas_box_tool_records_missing_columns():
    """Test when ohlcv_with_ta records are missing essential columns like 'close' or 'volume'."""
    market_data = json.loads(get_sample_processed_market_data_json(days=5)) # Use full structure
    # Corrupt one of the records
    if market_data['ohlcv_with_ta']:
        del market_data['ohlcv_with_ta'][0]['close'] # Remove 'close' from the first record
        if 'volume' in market_data['ohlcv_with_ta'][1]:
             del market_data['ohlcv_with_ta'][1]['volume'] # Remove 'volume' from the second record

    corrupted_records_json_str = json.dumps(market_data)
    sample_config = DarvasBoxConfig().model_dump()

    result_json = apply_darvas_box_tool(processed_market_data_json=corrupted_records_json_str, darvas_config=sample_config)
    data = json.loads(result_json)
    assert "error" in data
    assert "Market data DataFrame missing required OHLCV columns" in data["error"]


@patch('python_ai_services.tools.strategy_application_tools.run_darvas_box')
def test_apply_darvas_box_tool_strategy_execution_fails(mock_run_darvas: MagicMock, sample_darvas_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json()
    mock_run_darvas.side_effect = Exception("Core strategy error!")
    result_json = apply_darvas_box_tool(processed_market_data_json=market_json_str, darvas_config=sample_darvas_config_dict)
    data = json.loads(result_json)
    assert "error" in data and "Error during Darvas Box strategy execution" in data["error"]

# --- Tests for apply_williams_alligator_tool ---
@pytest.fixture
def sample_alligator_config_dict() -> Dict[str, Any]:
    return WilliamsAlligatorConfig().model_dump()

@patch('python_ai_services.tools.strategy_application_tools.run_williams_alligator')
def test_apply_williams_alligator_tool_success_signal(mock_run_alligator: MagicMock, sample_alligator_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="ALLI_TEST", days=60)
    mock_signal_date = pd.Timestamp("2023-03-01T00:00:00Z")
    indicator_preview_df_data = [{"timestamp": mock_signal_date.isoformat(), "close": 115.0, "lips": 114.0, "teeth": 113.0, "jaw": 112.0}]
    mock_alligator_output = {
        "signals": [{"date": mock_signal_date, "type": "BUY", "price": 115.0, "reason": "Alligator bullish crossover", "lips": 114.0, "teeth": 113.0, "jaw": 112.0}],
        "indicator_data": pd.DataFrame(indicator_preview_df_data).set_index("timestamp")
    }
    mock_run_alligator.return_value = mock_alligator_output
    result_json = apply_williams_alligator_tool(processed_market_data_json=market_json_str, alligator_config=sample_alligator_config_dict)
    data = json.loads(result_json)
    assert "error" not in data
    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.advice == TradeAction.BUY

# ... (other Alligator tests remain unchanged) ...
@patch('python_ai_services.tools.strategy_application_tools.run_williams_alligator')
def test_apply_williams_alligator_tool_no_signal_hold(mock_run_alligator: MagicMock, sample_alligator_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="ALLI_HOLD", days=60)
    mock_run_alligator.return_value = {"signals": [], "indicator_data": pd.DataFrame()}
    result_json = apply_williams_alligator_tool(processed_market_data_json=market_json_str, alligator_config=sample_alligator_config_dict)
    data = json.loads(result_json)
    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.advice == TradeAction.HOLD

def test_apply_williams_alligator_tool_invalid_config():
    market_json_str = get_sample_processed_market_data_json()
    invalid_config = {"jaw_period": -5}
    result_json = apply_williams_alligator_tool(processed_market_data_json=market_json_str, alligator_config=invalid_config)
    data = json.loads(result_json)
    assert "error" in data and "Invalid Williams Alligator configuration" in data["error"]

@patch('python_ai_services.tools.strategy_application_tools.run_williams_alligator')
def test_apply_williams_alligator_tool_strategy_execution_fails(mock_run_alligator: MagicMock, sample_alligator_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json()
    mock_run_alligator.side_effect = Exception("Core Alligator error!")
    result_json = apply_williams_alligator_tool(processed_market_data_json=market_json_str, alligator_config=sample_alligator_config_dict)
    data = json.loads(result_json)
    assert "error" in data and "Error during Williams Alligator strategy execution" in data["error"]

# --- Tests for apply_renko_tool ---

@pytest.fixture
def sample_renko_config_dict_fixed() -> Dict[str, Any]:
    return RenkoConfig(brick_size_method=RenkoBrickSizeMethod.FIXED, brick_size_value=1.0).model_dump()

@pytest.fixture
def sample_renko_config_dict_atr() -> Dict[str, Any]:
    return RenkoConfig(brick_size_method=RenkoBrickSizeMethod.ATR, atr_period=14).model_dump()

@patch('python_ai_services.tools.strategy_application_tools.run_renko')
def test_apply_renko_tool_success_signal(mock_run_renko: MagicMock, sample_renko_config_dict_fixed: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="RENKO_TEST", days=60)
    mock_signal_date = pd.Timestamp("2023-03-01T00:00:00Z")
    mock_renko_output = {
        "signals": [{"date": mock_signal_date, "type": "BUY", "price": 105.0, "reason": "Renko reversal: Two consecutive 'up' bricks.", "brick_type": "up"}],
        "renko_bricks": pd.DataFrame({"timestamp": [mock_signal_date.isoformat()], "brick_type": ["up"], "open": [104.0], "close": [105.0]}).set_index("timestamp"),
        "brick_size_used": 1.0
    }
    mock_run_renko.return_value = mock_renko_output

    result_json = apply_renko_tool(processed_market_data_json=market_json_str, renko_config=sample_renko_config_dict_fixed)
    data = json.loads(result_json)
    assert "error" not in data

    mock_run_renko.assert_called_once()
    call_args = mock_run_renko.call_args
    assert isinstance(call_args[0][0], pd.DataFrame)
    assert isinstance(call_args[0][1], RenkoConfig)

    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.symbol == "RENKO_TEST"
    assert parsed_result.strategy_name == "RenkoStrategy"
    assert parsed_result.advice == TradeAction.BUY
    assert "Renko reversal" in parsed_result.rationale
    assert "renko_bricks_preview" in parsed_result.additional_data
    assert parsed_result.additional_data["brick_size_used"] == 1.0
    if parsed_result.additional_data["renko_bricks_preview"]:
        assert "brick_type" in parsed_result.additional_data["renko_bricks_preview"][0]

@patch('python_ai_services.tools.strategy_application_tools.run_renko')
def test_apply_renko_tool_no_signal_hold(mock_run_renko: MagicMock, sample_renko_config_dict_fixed: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="RENKO_HOLD", days=60)
    mock_run_renko.return_value = {"signals": [], "renko_bricks": pd.DataFrame(), "brick_size_used": 1.0}

    result_json = apply_renko_tool(processed_market_data_json=market_json_str, renko_config=sample_renko_config_dict_fixed)
    data = json.loads(result_json)
    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.advice == TradeAction.HOLD
    assert "No clear Renko entry/exit signal" in parsed_result.rationale

def test_apply_renko_tool_invalid_config():
    market_json_str = get_sample_processed_market_data_json()
    invalid_config = {"brick_size_method": "fixed", "brick_size_value": -1.0} # Invalid brick_size_value

    result_json = apply_renko_tool(processed_market_data_json=market_json_str, renko_config=invalid_config)
    data = json.loads(result_json)
    assert "error" in data
    assert "Invalid RenkoConfig" in data["error"] # Pydantic validation error

@patch('python_ai_services.tools.strategy_application_tools.run_renko')
def test_apply_renko_tool_strategy_execution_fails(mock_run_renko: MagicMock, sample_renko_config_dict_fixed: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json()
    mock_run_renko.side_effect = Exception("Core Renko error!")

    result_json = apply_renko_tool(processed_market_data_json=market_json_str, renko_config=sample_renko_config_dict_fixed)
    data = json.loads(result_json)
    assert "error" in data
    assert "Error executing Renko strategy" in data["error"]
    assert "Core Renko error!" in data["details"]

# --- Tests for apply_heikin_ashi_tool ---

@pytest.fixture
def sample_ha_config_dict() -> Dict[str, Any]:
    """Returns a sample valid Heikin Ashi configuration dictionary."""
    return HeikinAshiConfig(heikin_ashi_smoothing_period=1, trend_confirmation_candles=2).model_dump()

@patch('python_ai_services.tools.strategy_application_tools.run_heikin_ashi')
def test_apply_heikin_ashi_tool_success_signal(mock_run_ha: MagicMock, sample_ha_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="HA_BUY", days=70)
    mock_signal_date = pd.Timestamp("2023-03-10T00:00:00Z")
    # Sample HA data should include original OHLC and HA OHLC
    ha_df_data = [{"timestamp": mock_signal_date.isoformat(),
                   "open": 120.0, "high": 122.0, "low": 119.0, "close": 121.0, # Original
                   "ha_open": 120.5, "ha_high": 122.5, "ha_low": 120.0, "ha_close": 122.0}] # HA
    mock_ha_output = {
        "signals": [{"date": mock_signal_date, "type": "BUY", "price": 122.0, "reason": "Heikin Ashi bullish trend confirmation"}],
        "heikin_ashi_data": pd.DataFrame(ha_df_data).set_index("timestamp")
    }
    mock_run_ha.return_value = mock_ha_output

    result_json = apply_heikin_ashi_tool(processed_market_data_json=market_json_str, heikin_ashi_config=sample_ha_config_dict)
    data = json.loads(result_json)

    assert "error" not in data, f"Tool returned error: {data.get('error')}"
    mock_run_ha.assert_called_once()

    call_args = mock_run_ha.call_args
    assert isinstance(call_args[0][0], pd.DataFrame) # Check DataFrame passed
    assert isinstance(call_args[0][1], HeikinAshiConfig) # Check HeikinAshiConfig instance passed

    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.symbol == "HA_BUY"
    assert parsed_result.strategy_name == "HeikinAshiStrategy"
    assert parsed_result.advice == TradeAction.BUY
    assert "bullish trend confirmation" in parsed_result.rationale
    assert "heikin_ashi_data_preview" in parsed_result.additional_data
    if parsed_result.additional_data["heikin_ashi_data_preview"]:
        assert "ha_close" in parsed_result.additional_data["heikin_ashi_data_preview"][0]

@patch('python_ai_services.tools.strategy_application_tools.run_heikin_ashi')
def test_apply_heikin_ashi_tool_no_signal_hold(mock_run_ha: MagicMock, sample_ha_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="HA_HOLD", days=70)
    mock_run_ha.return_value = {"signals": [], "heikin_ashi_data": pd.DataFrame()} # No signals

    result_json = apply_heikin_ashi_tool(processed_market_data_json=market_json_str, heikin_ashi_config=sample_ha_config_dict)
    data = json.loads(result_json)
    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.advice == TradeAction.HOLD
    assert "No definitive signal" in parsed_result.rationale

def test_apply_heikin_ashi_tool_invalid_config(sample_ha_config_dict: Dict[str, Any]): # Reusing fixture for market data
    market_json_str = get_sample_processed_market_data_json()
    # Intentionally make config invalid, e.g., by using a negative value for a period
    invalid_ha_config = {"heikin_ashi_smoothing_period": -1, "trend_confirmation_candles": "abc"}

    result_json = apply_heikin_ashi_tool(processed_market_data_json=market_json_str, heikin_ashi_config=invalid_ha_config)
    data = json.loads(result_json)
    assert "error" in data
    assert "Invalid Heikin Ashi configuration" in data["error"]

def test_apply_heikin_ashi_tool_invalid_market_data(sample_ha_config_dict: Dict[str, Any]):
    # Test with malformed JSON (e.g., not a JSON string)
    malformed_market_json = "this is not json"
    result_json = apply_heikin_ashi_tool(processed_market_data_json=malformed_market_json, heikin_ashi_config=sample_ha_config_dict)
    data = json.loads(result_json)
    assert "error" in data
    assert "Invalid JSON format for market data" in data["error"]

    # Test with JSON missing 'ohlcv_with_ta'
    missing_key_json = json.dumps({"symbol": "HA_TEST", "summary": "Data missing key"})
    result_json = apply_heikin_ashi_tool(processed_market_data_json=missing_key_json, heikin_ashi_config=sample_ha_config_dict)
    data = json.loads(result_json)
    assert "error" in data
    assert "Market data 'ohlcv_with_ta' field is invalid or empty" in data["error"]

@patch('python_ai_services.tools.strategy_application_tools.run_heikin_ashi')
def test_apply_heikin_ashi_tool_strategy_execution_fails(mock_run_ha: MagicMock, sample_ha_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json()
    mock_run_ha.side_effect = Exception("Core Heikin Ashi strategy error!")

    result_json = apply_heikin_ashi_tool(processed_market_data_json=market_json_str, heikin_ashi_config=sample_ha_config_dict)
    data = json.loads(result_json)
    assert "error" in data
    assert "Error during Heikin Ashi strategy execution" in data["error"]
    assert "Core Heikin Ashi strategy error!" in data["details"]


def test_all_tools_args_schema_linkage():
    tools_to_check = [
        apply_darvas_box_tool,
        apply_williams_alligator_tool,
        apply_renko_tool,
        apply_heikin_ashi_tool # Added Heikin Ashi
    ]
    arg_schemas = [
        ApplyDarvasBoxArgs,
        ApplyWilliamsAlligatorArgs,
        ApplyRenkoArgs,
        ApplyHeikinAshiArgs # Added Heikin Ashi
    ]
    for tool_func, schema_class in zip(tools_to_check, arg_schemas):
        schema_attr = getattr(tool_func, 'args_schema', None)
        if schema_attr is None and hasattr(tool_func, 'tool'):
             schema_attr = getattr(tool_func.tool, 'args_schema', None)
        if schema_attr is None and hasattr(tool_func, '_crew_tool_input_schema'):
            schema_attr = tool_func._crew_tool_input_schema

        if schema_attr:
            assert schema_attr == schema_class
        else:
            # This condition might be hit if the tool decorator isn't applied in a way this test expects
            # or if the tool is a native CrewAI tool that doesn't use 'args_schema' in the same way.
            pytest.fail(f"Tool schema attribute not found or not matching for {tool_func.__name__} using common patterns. Tool object: {tool_func}")

# --- Tests for apply_elliott_wave_tool ---

@pytest.fixture
def sample_ew_config_dict() -> Dict[str, Any]:
    """Returns a sample valid Elliott Wave configuration dictionary."""
    return ElliottWaveConfig().model_dump()

@patch('python_ai_services.tools.strategy_application_tools.run_elliott_wave')
def test_apply_elliott_wave_tool_success_stub_signal(mock_run_ew: MagicMock, sample_ew_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="EW_STUB", days=80)
    mock_signal_date = pd.Timestamp("2023-03-20T00:00:00Z") # Ensure this is within sample_df range

    # Ensure the mock output from run_elliott_wave_stub is structured as the tool expects
    mock_strategy_output = {
        "signals": [{"date": mock_signal_date, "type": "HOLD", "price": 110.0, "reason": "Elliott Wave analysis stub - further detailed analysis required."}],
        "identified_patterns": [{"pattern_type": "stub_3_wave_sequence_placeholder", "swings_identified": []}],
        "analysis_summary": "Elliott Wave analysis is currently a STUB implementation."
    }
    mock_run_ew.return_value = mock_strategy_output

    result_json = apply_elliott_wave_tool(processed_market_data_json=market_json_str, elliott_wave_config=sample_ew_config_dict)
    data = json.loads(result_json)

    assert "error" not in data, f"Tool returned error: {data.get('error')}"
    mock_run_ew.assert_called_once()

    call_args = mock_run_ew.call_args
    assert isinstance(call_args[0][0], pd.DataFrame) # Check DataFrame
    assert isinstance(call_args[0][1], ElliottWaveConfig) # Check ElliottWaveConfig instance

    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.symbol == "EW_STUB"
    assert parsed_result.strategy_name == "ElliottWaveStrategy_Stub"
    assert parsed_result.advice == TradeAction.HOLD # Default from stub
    assert "Elliott Wave analysis is currently a STUB implementation." in parsed_result.rationale
    assert parsed_result.confidence_score == 0.1 # Default low confidence for HOLD
    assert "identified_patterns" in parsed_result.additional_data
    assert parsed_result.additional_data["identified_patterns"][0]["pattern_type"] == "stub_3_wave_sequence_placeholder"
    assert "analysis_summary_from_strategy" in parsed_result.additional_data
    assert "STUB implementation" in parsed_result.additional_data["analysis_summary_from_strategy"]

@patch('python_ai_services.tools.strategy_application_tools.run_elliott_wave')
def test_apply_elliott_wave_tool_stub_with_mocked_simple_buy_signal(mock_run_ew: MagicMock, sample_ew_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json(symbol="EW_BUY_STUB", days=80)
    mock_signal_date = pd.Timestamp("2023-03-20T00:00:00Z")

    mock_strategy_output = {
        "signals": [{"date": mock_signal_date, "type": "CONSIDER_BUY_STUB", "price": 112.0, "reason": "Stub: Last identified swing was a low."}],
        "identified_patterns": [],
        "analysis_summary": "Elliott Wave stub with a conceptual buy signal."
    }
    mock_run_ew.return_value = mock_strategy_output

    result_json = apply_elliott_wave_tool(processed_market_data_json=market_json_str, elliott_wave_config=sample_ew_config_dict)
    data = json.loads(result_json)

    assert "error" not in data
    parsed_result = StrategyApplicationResult(**data)
    assert parsed_result.advice == TradeAction.BUY # Tool should map "CONSIDER_BUY_STUB"
    assert "Stub: Last identified swing was a low." in parsed_result.rationale
    assert parsed_result.confidence_score == 0.3 # Slightly higher for a directional stub signal

def test_apply_elliott_wave_tool_invalid_config(sample_ew_config_dict: Dict[str, Any]): # Using sample_ew_config_dict just as a valid base to corrupt for market_json
    market_json_str = get_sample_processed_market_data_json()
    invalid_ew_config = {"zigzag_threshold_percent": -5.0} # Invalid value for zigzag

    result_json = apply_elliott_wave_tool(processed_market_data_json=market_json_str, elliott_wave_config=invalid_ew_config)
    data = json.loads(result_json)
    assert "error" in data
    assert "Invalid Elliott Wave configuration" in data["error"]
    # Example check for Pydantic error detail structure if needed
    assert "details" in data
    assert isinstance(data["details"], list)
    assert any("zigzag_threshold_percent" in detail.get("loc", ()) for detail in data["details"])


@patch('python_ai_services.tools.strategy_application_tools.run_elliott_wave')
def test_apply_elliott_wave_tool_strategy_execution_fails(mock_run_ew: MagicMock, sample_ew_config_dict: Dict[str, Any]):
    market_json_str = get_sample_processed_market_data_json()
    mock_run_ew.side_effect = Exception("Core Elliott Wave (Stub) error!")

    result_json = apply_elliott_wave_tool(processed_market_data_json=market_json_str, elliott_wave_config=sample_ew_config_dict)
    data = json.loads(result_json)
    assert "error" in data
    assert "Error during Elliott Wave (Stub) strategy execution" in data["error"]
    assert "Core Elliott Wave (Stub) error!" in data["details"]

def test_all_tools_args_schema_linkage():
    tools_to_check = [
        apply_darvas_box_tool,
        apply_williams_alligator_tool,
        apply_renko_tool,
        apply_heikin_ashi_tool,
        apply_elliott_wave_tool # Added Elliott Wave
    ]
    arg_schemas = [
        ApplyDarvasBoxArgs,
        ApplyWilliamsAlligatorArgs,
        ApplyRenkoArgs,
        ApplyHeikinAshiArgs,
        ApplyElliottWaveArgs # Added Elliott Wave
    ]
    for tool_func, schema_class in zip(tools_to_check, arg_schemas):
        schema_attr = getattr(tool_func, 'args_schema', None)
        if schema_attr is None and hasattr(tool_func, 'tool'):
             schema_attr = getattr(tool_func.tool, 'args_schema', None)
        if schema_attr is None and hasattr(tool_func, '_crew_tool_input_schema'):
            schema_attr = tool_func._crew_tool_input_schema

        if schema_attr:
            assert schema_attr == schema_class
        else:
            # This condition might be hit if the tool decorator isn't applied in a way this test expects
            # or if the tool is a native CrewAI tool that doesn't use 'args_schema' in the same way.
            pytest.fail(f"Tool schema attribute not found or not matching for {tool_func.__name__} using common patterns. Tool object: {tool_func}")

