from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from loguru import logger
import json
import pandas as pd
from datetime import datetime # For StrategyApplicationResult timestamp
from unittest import mock # For example usage of async tool

# Attempt to import the 'tool' decorator from crewai_tools
try:
    from crewai_tools import tool
except ImportError:
    logger.warning("crewai_tools.tool not found. Using a placeholder decorator '@tool_stub'.")
    def tool_stub(name: str, args_schema: Optional[Any] = None, description: Optional[str] = None):
        def decorator(func):
            func.tool_name = name
            func.args_schema = args_schema
            func.description = description
            logger.debug(f"Tool stub '{name}' registered with args_schema: {args_schema}, desc: {description}")
            return func
        return decorator
    tool = tool_stub

# Relative imports for models and strategy logic
try:
    from ..models.strategy_models import DarvasBoxConfig, WilliamsAlligatorConfig, HeikinAshiConfig, ElliottWaveConfig
    from ..models.crew_models import StrategyApplicationResult
    from ..types.trading_types import TradeAction
    from ..strategies.darvas_box import run_darvas_box
    from ..strategies.williams_alligator import run_williams_alligator
    from ..strategies.heikin_ashi import run_heikin_ashi
    from ..strategies.elliott_wave import run_elliott_wave
except ImportError as e:
    logger.critical(f"Failed to import necessary modules for strategy_application_tools: {e}. Tool may not function correctly.")
    # Define placeholders if imports fail, mainly for subtask execution context
    class DarvasBoxConfig(BaseModel): pass
    class WilliamsAlligatorConfig(BaseModel): pass
    class HeikinAshiConfig(BaseModel): pass
    class ElliottWaveConfig(BaseModel): pass # Added placeholder
    class StrategyApplicationResult(BaseModel): pass
    class TradeAction: BUY="BUY"; SELL="SELL"; HOLD="HOLD" # Basic placeholder
    def run_darvas_box(df, config): return {"signals": [], "boxes": []}
    def run_williams_alligator(df, config): return {"signals": [], "indicator_data": pd.DataFrame()}
    def run_heikin_ashi(df, config): return {"signals": [], "heikin_ashi_data": pd.DataFrame()}
    def run_elliott_wave(df, config): return {"signals": [], "identified_patterns": [], "analysis_summary": "Placeholder EW run"}


class ApplyDarvasBoxArgs(BaseModel):
    """
    Input arguments for the Apply Darvas Box Strategy Tool.
    """
    processed_market_data_json: str = Field(..., description="JSON string containing market data. Expected to have 'ohlcv_with_ta' key with a list of OHLCV records (output from run_technical_analysis_tool), and 'symbol'.")
    darvas_config: Dict[str, Any] = Field(..., description="Dictionary of parameters to configure the DarvasBoxConfig (e.g., lookback_period_highs, min_box_duration).")


@tool("Apply Darvas Box Strategy Tool", args_schema=ApplyDarvasBoxArgs, description="Applies the Darvas Box trading strategy to the provided market data using specified configurations, and returns a structured strategy application result including trading advice.")
def apply_darvas_box_tool(processed_market_data_json: str, darvas_config: Dict[str, Any]) -> str:
    """
    Applies the Darvas Box trading strategy to market data.

    Args:
        processed_market_data_json: JSON string from run_technical_analysis_tool.
                                    Expected to have 'ohlcv_with_ta' (list of OHLCV records)
                                    and 'symbol'.
        darvas_config: A dictionary of parameters to instantiate DarvasBoxConfig.

    Returns:
        A JSON string representing a `StrategyApplicationResult`.
    """
    logger.info(f"TOOL: Applying Darvas Box Strategy. Config: {darvas_config}")

    try:
        validated_darvas_config = DarvasBoxConfig(**darvas_config)
    except PydanticValidationError as e:
        logger.error(f"TOOL: Invalid DarvasBoxConfig provided: {e}")
        return json.dumps({"error": "Invalid Darvas Box configuration.", "details": e.errors()})

    try:
        market_data_dict = json.loads(processed_market_data_json)
        ohlcv_records = market_data_dict.get('ohlcv_with_ta')
        symbol = market_data_dict.get('symbol')

        if not symbol:
            logger.error("TOOL: 'symbol' missing in processed_market_data_json.")
            return json.dumps({"error": "'symbol' missing in processed market data."})
        if not isinstance(ohlcv_records, list) or not ohlcv_records:
            logger.error("TOOL: 'ohlcv_with_ta' field in processed_market_data_json is missing, not a list, or empty.")
            return json.dumps({"error": "Market data 'ohlcv_with_ta' field is invalid or empty."})

        df = pd.DataFrame(ohlcv_records)
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col.lower() in [c.lower() for c in df.columns] for col in required_cols):
            logger.error(f"TOOL: Market data DataFrame missing required OHLCV columns. Expected: {required_cols}, Found: {list(df.columns)}")
            return json.dumps({"error": "Market data DataFrame missing required OHLCV columns."})

        df.columns = [col.lower() for col in df.columns]
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=numeric_cols)
        if df.empty:
            logger.warning(f"TOOL: DataFrame for {symbol} became empty after numeric conversion and NA drop.")
            return json.dumps({"error": "Market data resulted in empty dataset after cleaning."})

    except json.JSONDecodeError as e:
        logger.error(f"TOOL: Invalid JSON format in processed_market_data_json: {e}")
        return json.dumps({"error": "Invalid JSON format for market data.", "details": str(e)})
    except Exception as e:
        logger.error(f"TOOL: Error processing market data for Darvas Box: {e}")
        return json.dumps({"error": "Error processing market data.", "details": str(e)})

    try:
        logger.info(f"TOOL: Running Darvas Box core logic for {symbol} with {len(df)} records.")
        strategy_output = run_darvas_box(df, validated_darvas_config)
    except Exception as e:
        logger.exception(f"TOOL: Error during run_darvas_box execution for {symbol}: {e}")
        return json.dumps({"error": "Error during Darvas Box strategy execution.", "details": str(e)})

    advice = TradeAction.HOLD
    confidence = 0.5
    target_price = None
    stop_loss = None
    take_profit = None
    rationale = f"No actionable Darvas Box BUY signal generated for {symbol} with the current configuration."
    # Include a preview of the input data and the identified boxes in additional_data
    additional_data = {
        "boxes_found": strategy_output.get("boxes", []),
        "input_ohlcv_preview": ohlcv_records[:5] # Preview first 5 records of the input
    }

    if strategy_output.get("signals"):
        last_signal = strategy_output["signals"][-1]
        if last_signal.get("type") == "BUY":
            advice = TradeAction.BUY
            confidence = 0.70
            box_top = last_signal.get("box_top")
            box_bottom = last_signal.get("box_bottom")
            if box_top is not None and box_bottom is not None:
                box_height = box_top - box_bottom
                target_price = round(box_top + box_height * 1.5, 2)
                stop_loss = last_signal.get("stop_loss")
                take_profit = round(box_top + box_height * 2.0, 2)

            rationale = (
                f"Darvas Box strategy generated a BUY signal for {symbol} on {pd.to_datetime(last_signal.get('date')).strftime('%Y-%m-%d')} " # Ensure date is string
                f"at price {last_signal.get('price'):.2f}. Box range: {box_bottom:.2f} - {box_top:.2f}. "
                f"Stop-loss set at {stop_loss:.2f}."
            )
            additional_data["last_signal_details"] = last_signal
    else:
        logger.info(f"TOOL: No BUY signals from Darvas Box for {symbol}.")

    result_model = StrategyApplicationResult(
        symbol=symbol, strategy_name="DarvasBoxStrategy", advice=advice,
        confidence_score=confidence, target_price=target_price, stop_loss=stop_loss,
        take_profit=take_profit, rationale=rationale, additional_data=additional_data,
        timestamp=datetime.utcnow()
    )
    try:
        return result_model.model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"TOOL: Error serializing StrategyApplicationResult to JSON for {symbol}: {e}")
        return json.dumps({"error": "Failed to serialize strategy result.", "details": str(e)})


class ApplyWilliamsAlligatorArgs(BaseModel):
    """
    Input arguments for the Apply Williams Alligator Strategy Tool.
    """
    processed_market_data_json: str = Field(..., description="JSON string from run_technical_analysis_tool. Expected to have 'symbol' and 'ohlcv_with_ta' (list of OHLCV records).")
    alligator_config: Dict[str, Any] = Field(..., description="Dictionary of parameters for WilliamsAlligatorConfig.")


@tool("Apply Williams Alligator Strategy Tool", args_schema=ApplyWilliamsAlligatorArgs, description="Applies the Williams Alligator strategy to market data and returns a strategy application result.")
def apply_williams_alligator_tool(processed_market_data_json: str, alligator_config: Dict[str, Any]) -> str:
    """
    Applies the Williams Alligator trading strategy to market data.

    Args:
        processed_market_data_json: JSON string from run_technical_analysis_tool.
                                    Expected to have 'ohlcv_with_ta' (list of OHLCV records)
                                    and 'symbol'.
        alligator_config: A dictionary of parameters to instantiate WilliamsAlligatorConfig.

    Returns:
        A JSON string representing a `StrategyApplicationResult`.
    """
    logger.info(f"TOOL: Applying Williams Alligator Strategy. Config: {alligator_config}")

    try:
        validated_alligator_config = WilliamsAlligatorConfig(**alligator_config)
    except PydanticValidationError as e:
        logger.error(f"TOOL: Invalid WilliamsAlligatorConfig provided: {e}")
        return json.dumps({"error": "Invalid Williams Alligator configuration.", "details": e.errors()})

    try:
        market_data_dict = json.loads(processed_market_data_json)
        ohlcv_records = market_data_dict.get('ohlcv_with_ta')
        symbol = market_data_dict.get('symbol')

        if not symbol:
            logger.error("TOOL: 'symbol' missing in processed_market_data_json.")
            return json.dumps({"error": "'symbol' missing in processed market data."})
        if not isinstance(ohlcv_records, list) or not ohlcv_records:
            logger.error("TOOL: 'ohlcv_with_ta' field in processed_market_data_json is missing, not a list, or empty.")
            return json.dumps({"error": "Market data 'ohlcv_with_ta' field is invalid or empty."})

        df = pd.DataFrame(ohlcv_records)
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume'] # Base columns needed
        # Williams Alligator itself might only use 'close' or 'hlc3' depending on config, but good to have all.
        if not all(col.lower() in [c.lower() for c in df.columns] for col in required_cols):
            logger.error(f"TOOL: Market data DataFrame missing required OHLCV columns. Expected: {required_cols}, Found: {list(df.columns)}")
            return json.dumps({"error": "Market data DataFrame missing required OHLCV columns."})

        df.columns = [col.lower() for col in df.columns]
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=numeric_cols) # Drop rows where essential numeric conversion failed for safety
        if df.empty:
            logger.warning(f"TOOL: DataFrame for {symbol} (Alligator) became empty after numeric conversion and NA drop.")
            return json.dumps({"error": "Market data for Alligator resulted in empty dataset after cleaning."})

    except json.JSONDecodeError as e:
        logger.error(f"TOOL: Invalid JSON format in processed_market_data_json (Alligator): {e}")
        return json.dumps({"error": "Invalid JSON format for market data (Alligator).", "details": str(e)})
    except Exception as e:
        logger.error(f"TOOL: Error processing market data for Williams Alligator: {e}")
        return json.dumps({"error": "Error processing market data (Alligator).", "details": str(e)})

    try:
        logger.info(f"TOOL: Running Williams Alligator core logic for {symbol} with {len(df)} records.")
        strategy_output = run_williams_alligator(df, validated_alligator_config)
    except Exception as e:
        logger.exception(f"TOOL: Error during run_williams_alligator execution for {symbol}: {e}")
        return json.dumps({"error": "Error during Williams Alligator strategy execution.", "details": str(e)})

    advice = TradeAction.HOLD
    confidence = 0.5
    target_price, stop_loss, take_profit = None, None, None
    rationale = f"Williams Alligator indicates no clear entry/exit signal for {symbol}; lines may be intertwined or trend unclear."

    # Process the last signal if any
    signals = strategy_output.get("signals", [])
    last_actionable_signal = None
    if signals:
        for signal in reversed(signals): # Find the most recent BUY or SELL
            if signal.get("type") == TradeAction.BUY.value or signal.get("type") == TradeAction.SELL.value:
                last_actionable_signal = signal
                break
        if not last_actionable_signal and signals[-1].get("type") == TradeAction.HOLD.value: # If last is HOLD
             rationale = signals[-1].get("reason", rationale) # Use HOLD reason from strategy

    if last_actionable_signal:
        signal_type_str = last_actionable_signal.get("type")
        # Safely convert string to TradeAction enum member
        try:
            advice = TradeAction(signal_type_str) # Convert string like "BUY" to TradeAction.BUY
        except ValueError:
            logger.warning(f"TOOL: Unknown signal type '{signal_type_str}' from Alligator strategy. Defaulting to HOLD.")
            advice = TradeAction.HOLD

        confidence = 0.65 # Mock confidence for any Alligator signal
        rationale = last_actionable_signal.get("reason", f"Williams Alligator signal: {advice.value}")

        # Conceptual stop-loss/take-profit based on Alligator lines from signal
        # This is highly conceptual as actual SL/TP would depend on more rules.
        price_at_signal = last_actionable_signal.get("price")
        jaw = last_actionable_signal.get("jaw")
        teeth = last_actionable_signal.get("teeth")
        lips = last_actionable_signal.get("lips")

        if advice == TradeAction.BUY and price_at_signal and jaw:
            stop_loss = round(min(jaw, teeth, lips) * 0.99, 2) # Stop below jaw (example)
            target_price = round(price_at_signal * 1.05, 2) # Simplistic target
        elif advice == TradeAction.SELL and price_at_signal and jaw:
            stop_loss = round(max(jaw, teeth, lips) * 1.01, 2) # Stop above jaw (example)
            target_price = round(price_at_signal * 0.95, 2) # Simplistic target

    indicator_data_df = strategy_output.get("indicator_data")
    additional_data_payload = {}
    if isinstance(indicator_data_df, pd.DataFrame) and not indicator_data_df.empty:
        # Serialize a sample of the indicator data
        df_sample = indicator_data_df[['open', 'high', 'low', 'close', 'volume', 'jaw', 'teeth', 'lips']].tail(5).copy()
        if isinstance(df_sample.index, pd.DatetimeIndex):
            df_sample.index = df_sample.index.map(lambda ts: ts.isoformat())
        additional_data_payload["indicator_data_preview"] = df_sample.reset_index().to_dict(orient='records')


    result_model = StrategyApplicationResult(
        symbol=symbol, strategy_name="WilliamsAlligatorStrategy", advice=advice,
        confidence_score=confidence, target_price=target_price, stop_loss=stop_loss,
        take_profit=take_profit, rationale=rationale, additional_data=additional_data_payload,
        timestamp=datetime.utcnow()
    )
    try:
        return result_model.model_dump_json(indent=2, exclude_none=True)
    except Exception as e:
        logger.error(f"TOOL: Error serializing StrategyApplicationResult for Alligator ({symbol}): {e}")
        return json.dumps({"error": "Failed to serialize Alligator strategy result.", "details": str(e)})


if __name__ == '__main__':
    from python_ai_services.tools.market_data_tools import fetch_market_data_tool, FetchMarketDataArgs
    from python_ai_services.tools.technical_analysis_tools import run_technical_analysis_tool, RunTechnicalAnalysisArgs
    import asyncio

    logger.remove()
    logger.add(lambda msg: print(msg, end=''), colorize=True, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="INFO")

    async def get_processed_market_data_for_test(symbol="MSFT", days=100):
        # Patch app_services for fetch_market_data_tool to use its mock path
        # This mock needs to be in scope if market_data_tools is not using its internal fallback
        # For this example, assume fetch_market_data_tool's internal mock is active if service not found
        market_args = FetchMarketDataArgs(symbol=symbol, timeframe="1d", historical_days=days)

        # In a real test setup, you might mock app_services globally for the tool module
        # For this __main__, we rely on fetch_market_data_tool's internal fallback if service not found
        market_data_json_str = await fetch_market_data_tool(**market_args.dict())

        ta_args = RunTechnicalAnalysisArgs(market_data_json=market_data_json_str, volume_sma_period=20)
        return run_technical_analysis_tool(**ta_args.dict())

    # Darvas Box Example (keeping it for context)
    # ... (Darvas Box __main__ example remains unchanged) ...
    logger.info("\n === Darvas Box Example (from previous __main__) ===")
    processed_market_data_json_for_darvas = asyncio.run(get_processed_market_data_for_test(symbol="AAPL", days=60))
    darvas_config_params = {
        "lookback_period_highs": 50, "box_definition_period": 10,
        "volume_increase_factor": 1.2, "min_box_duration": 3,
        "stop_loss_percent_from_bottom": 2.0, "box_range_tolerance_percent": 1.0
    }
    tool_args_darvas = ApplyDarvasBoxArgs(
        processed_market_data_json=processed_market_data_json_for_darvas,
        darvas_config=darvas_config_params
    )
    strategy_result_json_darvas = apply_darvas_box_tool(**tool_args_darvas.dict())
    logger.info(f"Apply Darvas Box Strategy Tool Output:\n{json.dumps(json.loads(strategy_result_json_darvas), indent=2)}")


    # Williams Alligator Example
    logger.info("\n\n--- Williams Alligator Strategy Tool Example ---")
    processed_market_data_json_for_alligator = asyncio.run(get_processed_market_data_for_test(symbol="MSFT", days=100))

    alligator_config_params = {
        "jaw_period": 13, "jaw_shift": 8,
        "teeth_period": 8, "teeth_shift": 5,
        "lips_period": 5, "lips_shift": 3,
        "price_source_column": "close"
    }
    tool_args_alligator = ApplyWilliamsAlligatorArgs(
        processed_market_data_json=processed_market_data_json_for_alligator,
        alligator_config=alligator_config_params
    )
    strategy_result_json_alligator = apply_williams_alligator_tool(**tool_args_alligator.dict())
    logger.info(f"Apply Williams Alligator Strategy Tool Output:\n{json.dumps(json.loads(strategy_result_json_alligator), indent=2)}")

    # Example with invalid Alligator config
    invalid_alligator_config = {"jaw_period": -5} # Invalid value
    tool_args_invalid_alligator_cfg = ApplyWilliamsAlligatorArgs(
        processed_market_data_json=processed_market_data_json_for_alligator,
        alligator_config=invalid_alligator_config
    )
    error_output_alligator_cfg = apply_williams_alligator_tool(**tool_args_invalid_alligator_cfg.dict())
    logger.info(f"Apply Williams Alligator Strategy Tool Output (Invalid Config):\n{json.dumps(json.loads(error_output_alligator_cfg), indent=2)}")


class ApplyHeikinAshiArgs(BaseModel):
    """
    Arguments for the Apply Heikin Ashi Strategy Tool.
    """
    processed_market_data_json: str = Field(..., description="JSON string from run_technical_analysis_tool. Expected to have 'symbol' and 'ohlcv_with_ta' (list of OHLCV records).")
    heikin_ashi_config: Dict[str, Any] = Field(..., description="Dictionary of parameters for HeikinAshiConfig.")


@tool("Apply Heikin Ashi Strategy Tool", args_schema=ApplyHeikinAshiArgs, description="Applies the Heikin Ashi strategy to market data and returns a strategy application result.")
def apply_heikin_ashi_tool(processed_market_data_json: str, heikin_ashi_config: Dict[str, Any]) -> str:
    """
    Applies the Heikin Ashi trading strategy to market data.

    Args:
        processed_market_data_json: JSON string from run_technical_analysis_tool.
                                    Expected to have 'ohlcv_with_ta' (list of OHLCV records)
                                    and 'symbol'.
        heikin_ashi_config: A dictionary of parameters to instantiate HeikinAshiConfig.

    Returns:
        A JSON string representing a `StrategyApplicationResult`.
    """
    logger.info(f"TOOL: Applying Heikin Ashi Strategy. Config: {heikin_ashi_config}")

    try:
        validated_ha_config = HeikinAshiConfig(**heikin_ashi_config)
    except PydanticValidationError as e:
        logger.error(f"TOOL: Invalid HeikinAshiConfig provided: {e}")
        return json.dumps({"error": "Invalid Heikin Ashi configuration.", "details": e.errors()})

    try:
        market_data_dict = json.loads(processed_market_data_json)
        ohlcv_records = market_data_dict.get('ohlcv_with_ta')
        symbol = market_data_dict.get('symbol')

        if not symbol:
            logger.error("TOOL: 'symbol' missing in processed_market_data_json (Heikin Ashi).")
            return json.dumps({"error": "'symbol' missing in processed market data for Heikin Ashi."})
        if not isinstance(ohlcv_records, list) or not ohlcv_records:
            logger.error("TOOL: 'ohlcv_with_ta' field in processed_market_data_json (Heikin Ashi) is missing, not a list, or empty.")
            return json.dumps({"error": "Market data 'ohlcv_with_ta' field is invalid or empty for Heikin Ashi."})

        df = pd.DataFrame(ohlcv_records)
        # Heikin Ashi requires Open, High, Low, Close. Volume might be used by underlying TA or context.
        required_cols = ['timestamp', 'open', 'high', 'low', 'close']
        if not all(col.lower() in [c.lower() for c in df.columns] for col in required_cols):
            logger.error(f"TOOL: Market data DataFrame missing required OHLC columns for Heikin Ashi. Expected: {required_cols}, Found: {list(df.columns)}")
            return json.dumps({"error": "Market data DataFrame missing required OHLC columns for Heikin Ashi."})

        df.columns = [col.lower() for col in df.columns]
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

        numeric_cols = ['open', 'high', 'low', 'close'] # Volume not directly used by HA calculation itself
        if 'volume' in df.columns: # include volume if present for completeness
             numeric_cols.append('volume')

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=['open', 'high', 'low', 'close']) # HA calculation needs these specifically
        if df.empty:
            logger.warning(f"TOOL: DataFrame for {symbol} (Heikin Ashi) became empty after numeric conversion and NA drop.")
            return json.dumps({"error": "Market data for Heikin Ashi resulted in empty dataset after cleaning."})

    except json.JSONDecodeError as e:
        logger.error(f"TOOL: Invalid JSON format in processed_market_data_json (Heikin Ashi): {e}")
        return json.dumps({"error": "Invalid JSON format for market data (Heikin Ashi).", "details": str(e)})
    except Exception as e:
        logger.error(f"TOOL: Error processing market data for Heikin Ashi: {e}")
        return json.dumps({"error": "Error processing market data (Heikin Ashi).", "details": str(e)})

    try:
        logger.info(f"TOOL: Running Heikin Ashi core logic for {symbol} with {len(df)} records.")
        strategy_output = run_heikin_ashi(df.copy(), validated_ha_config) # Pass copy to avoid modifying original df if run_heikin_ashi does in-place changes
    except Exception as e:
        logger.exception(f"TOOL: Error during run_heikin_ashi execution for {symbol}: {e}")
        return json.dumps({"error": "Error during Heikin Ashi strategy execution.", "details": str(e)})

    advice = TradeAction.HOLD
    confidence = 0.5
    target_price, stop_loss, take_profit = None, None, None
    rationale = f"Heikin Ashi strategy indicates no definitive signal for {symbol}."

    signals = strategy_output.get("signals", [])
    last_actionable_signal = None

    if signals:
        for signal_info in reversed(signals): # Find the most recent BUY or SELL
            if signal_info.get("type") in [TradeAction.BUY.value, TradeAction.SELL.value]:
                last_actionable_signal = signal_info
                break
        if not last_actionable_signal and signals[-1].get("type") == TradeAction.HOLD.value: # If last is HOLD
             rationale = signals[-1].get("reason", rationale)

    if last_actionable_signal:
        signal_type_str = last_actionable_signal.get("type")
        try:
            advice = TradeAction(signal_type_str)
        except ValueError:
            logger.warning(f"TOOL: Unknown signal type '{signal_type_str}' from Heikin Ashi strategy. Defaulting to HOLD.")
            advice = TradeAction.HOLD

        confidence = 0.60 # Default confidence for HA signal
        rationale = last_actionable_signal.get("reason", f"Heikin Ashi signal: {advice.value}")
        price_at_signal = last_actionable_signal.get("price") # This would be the HA close or actual close at signal time

        if price_at_signal:
            # Conceptual SL/TP: HA candles often show trend strength.
            # SL could be based on previous HA candle's low/high or a fixed percentage.
            # TP could be based on a risk/reward ratio or other indicators.
            # For this example, let's use a simple percentage.
            percentage_change = 0.02 # 2% for SL/TP
            if advice == TradeAction.BUY:
                stop_loss = round(price_at_signal * (1 - percentage_change), 2)
                target_price = round(price_at_signal * (1 + percentage_change * 1.5), 2) # 1.5 R:R
            elif advice == TradeAction.SELL:
                stop_loss = round(price_at_signal * (1 + percentage_change), 2)
                target_price = round(price_at_signal * (1 - percentage_change * 1.5), 2)

    ha_data_df = strategy_output.get("heikin_ashi_data")
    additional_data_payload = {}
    if isinstance(ha_data_df, pd.DataFrame) and not ha_data_df.empty:
        # Serialize a sample of the Heikin Ashi data (original OHLC + HA candles)
        # Ensure 'timestamp' is in a serializable format if it's an index
        df_sample = ha_data_df.tail(10).copy() # Take last 10 records
        if isinstance(df_sample.index, pd.DatetimeIndex):
             df_sample.index = df_sample.index.map(lambda ts: ts.isoformat())
        additional_data_payload["heikin_ashi_data_preview"] = df_sample.reset_index().to_dict(orient='records')

    result_model = StrategyApplicationResult(
        symbol=symbol, strategy_name="HeikinAshiStrategy", advice=advice,
        confidence_score=confidence, target_price=target_price, stop_loss=stop_loss,
        take_profit=take_profit, rationale=rationale, additional_data=additional_data_payload,
        timestamp=datetime.utcnow()
    )

    try:
        return result_model.model_dump_json(indent=2, exclude_none=True)
    except Exception as e:
        logger.error(f"TOOL: Error serializing StrategyApplicationResult for Heikin Ashi ({symbol}): {e}")
        return json.dumps({"error": "Failed to serialize Heikin Ashi strategy result.", "details": str(e)})


    # --- Heikin Ashi Strategy Tool Example ---
    logger.info("\n\n--- Heikin Ashi Strategy Tool Example ---")
    processed_market_data_json_for_ha = asyncio.run(get_processed_market_data_for_test(symbol="GOOGL", days=120))

    ha_config_params = {
        "heikin_ashi_smoothing_period": 1, # Example: no extra smoothing beyond HA calculation itself
        "trend_confirmation_candles": 2,
        "signal_strength_threshold": 0.6 # Example custom threshold if strategy uses it
    }
    tool_args_ha = ApplyHeikinAshiArgs(
        processed_market_data_json=processed_market_data_json_for_ha,
        heikin_ashi_config=ha_config_params
    )
    strategy_result_json_ha = apply_heikin_ashi_tool(**tool_args_ha.dict())
    logger.info(f"Apply Heikin Ashi Strategy Tool Output:\n{json.dumps(json.loads(strategy_result_json_ha), indent=2)}")

    # Example with invalid Heikin Ashi config
    invalid_ha_config = {"heikin_ashi_smoothing_period": -1} # Invalid value
    tool_args_invalid_ha_cfg = ApplyHeikinAshiArgs(
        processed_market_data_json=processed_market_data_json_for_ha,
        heikin_ashi_config=invalid_ha_config
    )
    error_output_ha_cfg = apply_heikin_ashi_tool(**tool_args_invalid_ha_cfg.dict())
    logger.info(f"Apply Heikin Ashi Strategy Tool Output (Invalid Config):\n{json.dumps(json.loads(error_output_ha_cfg), indent=2)}")


class ApplyElliottWaveArgs(BaseModel):
    """
    Arguments for the Apply Elliott Wave Strategy Tool.
    """
    processed_market_data_json: str = Field(..., description="JSON string from run_technical_analysis_tool. Expected to have 'symbol' and 'ohlcv_with_ta' (list of OHLCV records).")
    elliott_wave_config: Dict[str, Any] = Field(..., description="Dictionary of parameters for ElliottWaveConfig.")


@tool("Apply Elliott Wave Strategy Tool (Stub)", args_schema=ApplyElliottWaveArgs, description="Applies the (stubbed) Elliott Wave analysis to market data and returns a strategy application result.")
def apply_elliott_wave_tool(processed_market_data_json: str, elliott_wave_config: Dict[str, Any]) -> str:
    """
    Applies the (stubbed) Elliott Wave analysis to market data.

    Args:
        processed_market_data_json: JSON string from run_technical_analysis_tool.
                                    Expected to have 'ohlcv_with_ta' (list of OHLCV records)
                                    and 'symbol'.
        elliott_wave_config: A dictionary of parameters to instantiate ElliottWaveConfig.

    Returns:
        A JSON string representing a `StrategyApplicationResult`.
    """
    logger.info(f"TOOL: Applying Elliott Wave Strategy (Stub). Config: {elliott_wave_config}")

    try:
        validated_ew_config = ElliottWaveConfig(**elliott_wave_config)
    except PydanticValidationError as e:
        logger.error(f"TOOL: Invalid ElliottWaveConfig provided: {e}")
        return json.dumps({"error": "Invalid Elliott Wave configuration.", "details": e.errors()})

    try:
        market_data_dict = json.loads(processed_market_data_json)
        ohlcv_records = market_data_dict.get('ohlcv_with_ta')
        symbol = market_data_dict.get('symbol')

        if not symbol:
            logger.error("TOOL: 'symbol' missing in processed_market_data_json (Elliott Wave).")
            return json.dumps({"error": "'symbol' missing in processed market data for Elliott Wave."})
        if not isinstance(ohlcv_records, list) or not ohlcv_records:
            logger.error("TOOL: 'ohlcv_with_ta' field in processed_market_data_json (Elliott Wave) is missing, not a list, or empty.")
            return json.dumps({"error": "Market data 'ohlcv_with_ta' field is invalid or empty for Elliott Wave."})

        df = pd.DataFrame(ohlcv_records)
        # Elliott Wave stub might use 'open', 'high', 'low', 'close' depending on its price_source_column.
        # Ensure timestamp is present and other essential columns for general processing.
        required_cols_check = ['timestamp', 'open', 'high', 'low', 'close'] # Check for these basic columns
        if not all(col.lower() in [c.lower() for c in df.columns] for col in required_cols_check):
            logger.error(f"TOOL: Market data DataFrame missing some standard OHLC columns for Elliott Wave. Expected at least: {required_cols_check}, Found: {list(df.columns)}")
            return json.dumps({"error": "Market data DataFrame missing some standard OHLC columns for Elliott Wave."})

        df.columns = [col.lower() for col in df.columns]
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

        # Convert all potential price source columns to numeric, and volume too
        numeric_cols = ['open', 'high', 'low', 'close']
        if validated_ew_config.price_source_column.lower() not in numeric_cols:
             # If hlc3 or something else, it would be calculated, but for stub, assume it's one of OHLC.
             if validated_ew_config.price_source_column.lower() in df.columns:
                numeric_cols.append(validated_ew_config.price_source_column.lower())
             else:
                logger.error(f"TOOL: Configured price_source_column '{validated_ew_config.price_source_column}' not found in market data columns: {list(df.columns)}")
                return json.dumps({"error": f"Configured price_source_column '{validated_ew_config.price_source_column}' not found in market data."})


        if 'volume' in df.columns: numeric_cols.append('volume')

        for col in numeric_cols:
            if col in df.columns: # Ensure column exists before trying to convert
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Drop rows if the specific price_source_column used by the strategy is NaN after conversion
        df = df.dropna(subset=[validated_ew_config.price_source_column.lower()])
        if df.empty:
            logger.warning(f"TOOL: DataFrame for {symbol} (Elliott Wave) became empty after numeric conversion and NA drop on price_source_column '{validated_ew_config.price_source_column}'.")
            return json.dumps({"error": f"Market data for Elliott Wave resulted in empty dataset after cleaning based on '{validated_ew_config.price_source_column}'."})

    except json.JSONDecodeError as e:
        logger.error(f"TOOL: Invalid JSON format in processed_market_data_json (Elliott Wave): {e}")
        return json.dumps({"error": "Invalid JSON format for market data (Elliott Wave).", "details": str(e)})
    except Exception as e: # Catch-all for other processing errors
        logger.error(f"TOOL: Error processing market data for Elliott Wave: {e}")
        return json.dumps({"error": "Error processing market data (Elliott Wave).", "details": str(e)})

    try:
        logger.info(f"TOOL: Running Elliott Wave (Stub) core logic for {symbol} with {len(df)} records.")
        # Pass a copy of df to strategy function if it might modify it
        strategy_output = run_elliott_wave(df.copy(), validated_ew_config)
    except Exception as e:
        logger.exception(f"TOOL: Error during run_elliott_wave (Stub) execution for {symbol}: {e}")
        return json.dumps({"error": "Error during Elliott Wave (Stub) strategy execution.", "details": str(e)})

    advice = TradeAction.HOLD
    confidence = 0.1 # Very low confidence for a stub
    rationale = strategy_output.get("analysis_summary", "Elliott Wave stub executed, no specific signal.")
    target_price, stop_loss, take_profit = None, None, None # Stubs typically don't provide these

    signals = strategy_output.get("signals", [])
    if signals and isinstance(signals, list) and len(signals) > 0:
        first_signal = signals[0]
        try:
            # The stub might return "CONSIDER_BUY_STUB" etc. which are not valid TradeAction members
            # So, we map them or default to HOLD
            raw_signal_type = first_signal.get("type", "HOLD").upper()
            if "BUY" in raw_signal_type:
                advice = TradeAction.BUY
            elif "SELL" in raw_signal_type:
                advice = TradeAction.SELL
            else:
                advice = TradeAction.HOLD

            # If it was a direct TradeAction enum value, this would also work:
            # advice = TradeAction(first_signal.get("type", TradeAction.HOLD.value))
        except ValueError: # If first_signal["type"] is not a valid TradeAction member
            logger.warning(f"TOOL: Elliott Wave stub signal type '{first_signal.get('type')}' not a valid TradeAction. Defaulting to HOLD.")
            advice = TradeAction.HOLD

        rationale = f"{strategy_output.get('analysis_summary', '')} Signal: {first_signal.get('reason', 'N/A')}"
        confidence = 0.3 # Slightly higher if stub produced some kind of directional signal
        # Price from signal might be useful for rationale, but not for actual trading from stub
        # price_at_signal = first_signal.get("price")

    additional_data = {
        "identified_patterns": strategy_output.get("identified_patterns", []),
        "analysis_summary_from_strategy": strategy_output.get("analysis_summary", "N/A")
    }

    result_model = StrategyApplicationResult(
        symbol=symbol,
        strategy_name="ElliottWaveStrategy_Stub",
        advice=advice,
        confidence_score=confidence,
        target_price=target_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        rationale=rationale,
        additional_data=additional_data,
        timestamp=datetime.utcnow()
    )

    try:
        return result_model.model_dump_json(indent=2, exclude_none=True)
    except Exception as e:
        logger.error(f"TOOL: Error serializing StrategyApplicationResult for Elliott Wave ({symbol}): {e}")
        return json.dumps({"error": "Failed to serialize Elliott Wave strategy result.", "details": str(e)})


    # --- Elliott Wave Strategy Tool Example (Stub) ---
    logger.info("\n\n--- Elliott Wave Strategy Tool Example (Stub) ---")
    processed_market_data_json_for_ew = asyncio.run(get_processed_market_data_for_test(symbol="EWAVE", days=150))

    ew_config_params = {
        "price_source_column": "close",
        "zigzag_threshold_percent": 5.0,
        "wave2_max_retracement_w1": 0.786,
        "wave3_min_extension_w1": 1.618,
        "wave4_max_retracement_w3": 0.5,
        "wave4_overlap_w1_allowed": False,
        "wave5_min_equality_w1_or_extension_w1w3": 0.618,
        "waveB_max_retracement_wA": 0.786,
        "waveC_min_equality_wA_or_extension_wA": 1.0,
        "max_waves_to_identify": 3
    }
    tool_args_ew = ApplyElliottWaveArgs(
        processed_market_data_json=processed_market_data_json_for_ew,
        elliott_wave_config=ew_config_params
    )
    strategy_result_json_ew = apply_elliott_wave_tool(**tool_args_ew.dict())
    logger.info(f"Apply Elliott Wave Strategy Tool (Stub) Output:\n{json.dumps(json.loads(strategy_result_json_ew), indent=2, default=str)}")

    # Example with invalid Elliott Wave config
    invalid_ew_config = {"zigzag_threshold_percent": -5.0} # Invalid value
    tool_args_invalid_ew_cfg = ApplyElliottWaveArgs(
        processed_market_data_json=processed_market_data_json_for_ew,
        elliott_wave_config=invalid_ew_config
    )
    error_output_ew_cfg = apply_elliott_wave_tool(**tool_args_invalid_ew_cfg.dict())
    logger.info(f"Apply Elliott Wave Strategy Tool (Stub) Output (Invalid Config):\n{json.dumps(json.loads(error_output_ew_cfg), indent=2, default=str)}")

