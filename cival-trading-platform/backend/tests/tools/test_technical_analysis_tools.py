import pytest
import json
import pandas as pd # For creating test input data
from typing import Dict, Any

from python_ai_services.tools.technical_analysis_tools import run_technical_analysis_tool, RunTechnicalAnalysisArgs
from python_ai_services.tools.market_data_tools import fetch_market_data_tool, FetchMarketDataArgs # For sample input

import pytest_asyncio # To handle async fixtures/tests if needed for helpers

# --- Helper to get sample market data JSON string ---
# This helper now needs to be async because fetch_market_data_tool is async
@pytest_asyncio.fixture
async def sample_market_data_json_fixture():
    """Provides a sample market_data_json string using the async fetch_market_data_tool."""
    # Mock app_services for fetch_market_data_tool if it's not using its own fallback
    # For simplicity, assume fetch_market_data_tool's fallback to mock data is sufficient here,
    # or that app_services is available in the test environment for it.
    # If testing fetch_market_data_tool's actual service call, its own tests cover that.
    # Here, we just need its output format.
    days = 25 # Ensure enough data for default SMA period
    market_args = FetchMarketDataArgs(symbol="TEST/TA", timeframe="1d", historical_days=days)
    # Patch app_services specifically for this helper's call to fetch_market_data_tool
    # to ensure it uses mock data and doesn't try to make real service calls.
    with mock.patch('python_ai_services.tools.market_data_tools.app_services', {"market_data_service": None}):
        json_str = await fetch_market_data_tool(**market_args.dict())
    return json_str

# --- Tests for run_technical_analysis_tool ---

@pytest.mark.asyncio # Mark test as async because the fixture is async
async def test_run_technical_analysis_tool_success(sample_market_data_json_fixture: str):
    """Test run_technical_analysis_tool with valid market_data_json."""
    market_json_str = sample_market_data_json_fixture # Use the awaited fixture

    result_json = run_technical_analysis_tool(market_data_json=market_json_str, volume_sma_period=20)

    assert isinstance(result_json, str)
    data = json.loads(result_json)

    assert "error" not in data, f"Tool returned an error: {data.get('error')}"
    assert "symbol" in data
    assert data["symbol"] == "TEST/TA" # From fixture
    assert "timeframe" in data
    assert data["timeframe"] == "1d" # From fixture
    assert "summary" in data
    assert "ohlcv_with_ta" in data
    assert isinstance(data["ohlcv_with_ta"], list)
    assert "columns_available" in data
    assert isinstance(data["columns_available"], list)
    assert "volume_sma" in data["columns_available"]
    assert "timestamp" in data["columns_available"] # Ensure timestamp is a column after reset_index

    if data["ohlcv_with_ta"]:
        # Convert back to DataFrame to check structure and content
        df_out = pd.DataFrame(data["ohlcv_with_ta"])
        assert not df_out.empty

        # Verify timestamp format (should be string ISO)
        assert isinstance(df_out["timestamp"].iloc[0], str)
        try:
            pd.to_datetime(df_out["timestamp"].iloc[0]) # Check if it's a valid ISO string
        except ValueError:
            pytest.fail("Timestamp in ohlcv_with_ta is not a valid ISO string.")

        original_data_points = json.loads(market_json_str).get("data_points_returned")
        assert len(df_out) == original_data_points

        required_original_cols = ['open', 'high', 'low', 'close', 'volume'] # Timestamp is now a column
        for col in required_original_cols:
            assert col in df_out.columns
        assert "volume_sma" in df_out.columns

        # Check if SMA actually has values (not all None, as np.nan becomes None in JSON)
        # if period is met and volume data was present
        volume_data_in_input = json.loads(market_json_str).get("data", [])
        # Check if any volume data was non-zero or non-NA in the input to expect a non-None SMA
        has_volume = any(record.get("volume") is not None and record.get("volume") > 0 for record in volume_data_in_input)

        if len(df_out) >= 20 and has_volume: # volume_sma_period is 20 by default in tool
             # Check that not all SMA values are None if calculation was expected
            assert any(sma_val is not None for sma_val in df_out["volume_sma"]), "Volume SMA is all None, expected some values."
        elif "volume_sma" in df_out.columns:
            # If not enough data or no volume, all SMA values might be None
            assert all(sma_val is None for sma_val in df_out["volume_sma"]), "Volume SMA has values where None was expected (insufficient data or no volume)."


def test_run_technical_analysis_tool_invalid_json_input():
    """Test with a malformed JSON string."""
    malformed_json = '{"symbol": "BADJSON", "data": "this is not a list... oops'
    result_json = run_technical_analysis_tool(market_data_json=malformed_json)
    data = json.loads(result_json)
    assert "error" in data
    assert "Invalid JSON format" in data["error"]

def test_run_technical_analysis_tool_missing_data_key():
    """Test with valid JSON but missing the 'data' key."""
    missing_data_key_json = json.dumps({"symbol": "NODATA", "timeframe": "1d"}) # 'data' key is missing
    result_json = run_technical_analysis_tool(market_data_json=missing_data_key_json)
    data = json.loads(result_json)
    assert "error" in data
    assert "'data' field in market_data_json is missing or not a list" in data["error"]

def test_run_technical_analysis_tool_empty_data_list():
    """Test with 'data' key present but the list is empty."""
    empty_data_list_json = json.dumps({"symbol": "EMPTYDATA", "timeframe": "1d", "data": []})
    result_json = run_technical_analysis_tool(market_data_json=empty_data_list_json)
    data = json.loads(result_json)
    assert "error" not in data
    assert data["summary"] == "No OHLCV data provided to analyze."
    assert "ohlcv_with_ta" in data and len(data["ohlcv_with_ta"]) == 0
    assert "columns_available" in data # Should report available columns, even if empty

def test_run_technical_analysis_tool_dataframe_conversion_error():
    """Test with data where essential numeric conversion fails for all rows."""
    bad_ohlcv_data_json = json.dumps({
        "symbol": "BADDATATYPE", "timeframe": "1d",
        "data": [{"timestamp": "2023-01-01T00:00:00Z", "open": "bad", "high": "data", "low": "for", "close": "numeric", "volume": "conversion"}]
    })
    result_json = run_technical_analysis_tool(market_data_json=bad_ohlcv_data_json)
    data = json.loads(result_json)
    assert "error" not in data # Graceful handling by returning summary
    assert "Data for essential OHLCV columns was not numeric" in data["summary"]
    assert "ohlcv_with_ta" in data and len(data["ohlcv_with_ta"]) == 0

def test_run_technical_analysis_tool_missing_ohlcv_columns_in_records():
    """Test with 'data' records missing essential OHLCV columns."""
    market_data_missing_cols = {
        "symbol": "MISSINGCOLS", "timeframe": "1h", "data_source_status": "mock", "limit_calculated": 5,
        "data": [
            {"timestamp": "2023-01-01T00:00:00Z", "open": 100, "high": 102}, # Missing low, close, volume
            {"timestamp": "2023-01-01T01:00:00Z", "open": 101, "high": 103, "low": 99, "close": 102, "volume": 500}
        ]
    }
    result_json = run_technical_analysis_tool(market_data_json=json.dumps(market_data_missing_cols))
    data = json.loads(result_json)
    assert "error" in data
    assert "DataFrame missing required OHLCV columns" in data["error"]

def test_run_technical_analysis_tool_args_schema():
    """Test that the tool has the correct args_schema linked."""
    if hasattr(run_technical_analysis_tool, 'args_schema'):
        assert run_technical_analysis_tool.args_schema == RunTechnicalAnalysisArgs
    elif hasattr(run_technical_analysis_tool, '_crew_tool_input_schema'):
         assert run_technical_analysis_tool._crew_tool_input_schema == RunTechnicalAnalysisArgs
    else:
        pytest.skip("Tool schema attribute not found, decorator might be a simple stub or crewai internal changed.")

