from supabase import Client as SupabaseClient
from logging import getLogger
from typing import Optional, Dict, Any, Callable, List
from datetime import date, datetime, timezone, timedelta # Ensure timedelta is imported
import pandas as pd
import importlib # For dynamically importing strategy functions

from ..models.strategy_models import StrategyConfig
from ..models.visualization_models import StrategyVisualizationRequest, StrategyVisualizationDataResponse, OHLCVBar, IndicatorDataPoint, SignalDataPoint
from ..models.trading_history_models import TradeRecord, TradeSide # For fetching paper trades
from ..services.strategy_config_service import StrategyConfigService # To get strategy config
from ..tools.market_data_tools import get_historical_price_data_tool # To get OHLCV

logger = getLogger(__name__)

class StrategyVisualizationServiceError(Exception):
    pass

class StrategyVisualizationService:
    def __init__(self, supabase_client: SupabaseClient, strategy_config_service: StrategyConfigService):
        self.supabase = supabase_client
        self.strategy_config_service = strategy_config_service
        logger.info("StrategyVisualizationService initialized.")

    async def get_strategy_visualization_data(self, request: StrategyVisualizationRequest) -> StrategyVisualizationDataResponse:
        logger.info(f"Fetching visualization data for strategy: {request.strategy_config_id}, user: {request.user_id}")

        # 1. Fetch Strategy Configuration
        config = await self.strategy_config_service.get_strategy_config(request.strategy_config_id, request.user_id)
        if not config:
            raise StrategyVisualizationServiceError(f"Strategy config {request.strategy_config_id} not found for user.")
        if not config.symbols:
            raise StrategyVisualizationServiceError(f"Strategy config {request.strategy_config_id} has no symbols defined.")

        symbol_to_visualize = config.symbols[0] # For now, visualize the first symbol

        # 2. Fetch OHLCV Data
        start_date_str = request.start_date.isoformat()
        end_date_str = request.end_date.isoformat()

        # Assuming get_historical_price_data_tool returns a Pandas DataFrame
        # with DatetimeIndex and columns 'Open', 'High', 'Low', 'Close', 'Volume'.
        price_data_result = get_historical_price_data_tool.func( # Accessing the underlying function for direct call
            symbol=symbol_to_visualize,
            start_date=start_date_str,
            end_date=end_date_str
            # interval=config.timeframe # TODO: Map StrategyTimeframe to OpenBB interval string
        )

        if isinstance(price_data_result, str) or price_data_result is None: # Error string or None
             raise StrategyVisualizationServiceError(f"Could not fetch price data for {symbol_to_visualize}: {price_data_result if price_data_result else 'No data returned'}")

        price_df = price_data_result # Assuming it's a DataFrame if not error/None

        if price_df.empty:
            raise StrategyVisualizationServiceError(f"Price data for {symbol_to_visualize} is empty for the period.")

        ohlcv_bars = [OHLCVBar(timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc), # Ensure UTC
                               open=row['Open'], high=row['High'], low=row['Low'],
                               close=row['Close'], volume=row.get('Volume'))
                      for idx, row in price_df.iterrows()]

        # 3. Get Strategy Signals & Indicator Data
        entry_signals_list: List[SignalDataPoint] = []
        exit_signals_list: List[SignalDataPoint] = []
        indicator_data_dict: Dict[str, List[IndicatorDataPoint]] = {}
        module_path = "" # Initialize for logging in case of early failure
        signal_func_name = "" # Initialize for logging

        try:
            strategy_module_name_map = {
                "DarvasBox": "darvas_box",
                "WilliamsAlligator": "williams_alligator",
                "HeikinAshi": "heikin_ashi",
                "Renko": "renko",
                "SMACrossover": "sma_crossover", # Corrected from SMACrossover to sma_crossover
                "ElliottWave": "elliott_wave"
            }
            mapped_module_name = strategy_module_name_map.get(config.strategy_type)
            if not mapped_module_name:
                raise StrategyVisualizationServiceError(f"No module mapping for strategy type: {config.strategy_type}")

            module_path = f"python_ai_services.strategies.{mapped_module_name}"
            strategy_module = importlib.import_module(module_path)
            signal_func_name = f"get_{mapped_module_name}_signals"
            signal_func = getattr(strategy_module, signal_func_name)

            strategy_params = config.parameters.model_dump(exclude_none=True) if config.parameters else {}

            # Call the signal function. Assume it returns a DataFrame (signals_df)
            # and optionally other items (like shapes for plotting, ignored here).
            signal_func_output = signal_func(
                symbol=symbol_to_visualize,
                start_date=start_date_str,
                end_date=end_date_str,
                **strategy_params
            )

            signals_df = None
            if isinstance(signal_func_output, tuple) and len(signal_func_output) > 0:
                if isinstance(signal_func_output[0], pd.DataFrame):
                    signals_df = signal_func_output[0]
                # Potentially handle other elements if needed, e.g., signal_func_output[1] for shapes
            elif isinstance(signal_func_output, pd.DataFrame):
                signals_df = signal_func_output

            if signals_df is not None and not signals_df.empty:
                # Ensure signals_df index is datetime
                if not isinstance(signals_df.index, pd.DatetimeIndex):
                    signals_df.index = pd.to_datetime(signals_df.index)

                for idx, row in signals_df.iterrows():
                    ts = idx.to_pydatetime().replace(tzinfo=timezone.utc)
                    price_at_sig = row['Close']
                    if row.get('entries') == True: # Some strategies use 1/-1, others True/False
                        entry_signals_list.append(SignalDataPoint(timestamp=ts, price_at_signal=price_at_sig, signal_type="entry_long"))
                    elif row.get('entries') == 1: # Handle numeric signals
                         entry_signals_list.append(SignalDataPoint(timestamp=ts, price_at_signal=price_at_sig, signal_type="entry_long"))

                    if row.get('exits') == True:
                        exit_signals_list.append(SignalDataPoint(timestamp=ts, price_at_signal=price_at_sig, signal_type="exit_long"))
                    elif row.get('exits') == -1: # Handle numeric signals
                        exit_signals_list.append(SignalDataPoint(timestamp=ts, price_at_signal=price_at_sig, signal_type="exit_long"))

                # Heuristic for indicator columns - needs refinement based on actual strategy outputs
                excluded_cols = ['Open','High','Low','Close','Volume','entries','exits','signal', 'signals', # common signal names
                                 'renko_type','renko_close','box_top','box_bottom', 'atr',
                                 'swing_points', 'wave_label', 'wave_pattern',
                                 'ha_open', 'ha_high', 'ha_low', 'ha_close', 'ha_green', 'ha_red',
                                 'ha_no_lower_shadow', 'ha_no_upper_shadow']
                indicator_cols = [col for col in signals_df.columns if col not in excluded_cols and col.lower() not in excluded_cols]

                for ind_col in indicator_cols:
                    indicator_data_dict[ind_col] = []
                    for idx, value in signals_df[ind_col].items():
                        ts = idx.to_pydatetime().replace(tzinfo=timezone.utc)
                        if isinstance(value, dict):
                             indicator_data_dict[ind_col].append(IndicatorDataPoint(timestamp=ts, values={k: (float(v) if pd.notna(v) else None) for k,v in value.items()}))
                        elif pd.notna(value):
                             indicator_data_dict[ind_col].append(IndicatorDataPoint(timestamp=ts, value=float(value)))
            else:
                logger.info(f"No signals or indicator data returned from {signal_func_name} for {symbol_to_visualize}")


        except ModuleNotFoundError:
            logger.error(f"Strategy module for type {config.strategy_type} (expected at {module_path}) not found.", exc_info=True)
        except AttributeError:
            logger.error(f"Signal function {signal_func_name} not found in module {module_path}.", exc_info=True)
        except Exception as e:
            logger.error(f"Error generating signals/indicators for {config.strategy_type} ({symbol_to_visualize}): {e}", exc_info=True)

        # 4. Fetch Paper Trades
        paper_trades_list: List[TradeRecord] = []
        try:
            # Ensure dates are in ISO format strings for Supabase query
            start_iso = request.start_date.isoformat()
            # For end_date, Supabase range is typically exclusive for timestamp 'lte',
            # so if we want to include the whole end_date, we go to the start of the next day.
            end_iso = (request.end_date + timedelta(days=1)).isoformat()

            trade_history_response = self.supabase.table("trading_history") \
                .select("*") \
                .eq("user_id", str(request.user_id)) \
                .eq("strategy_id", str(request.strategy_config_id)) \
                .gte("created_at", start_iso) \
                .lt("created_at", end_iso) \
                .order("created_at", desc=False) \
                .execute()

            if trade_history_response.data:
                paper_trades_list = [TradeRecord(**trade) for trade in trade_history_response.data]
        except Exception as e:
            logger.error(f"Error fetching paper trades for visualization (strategy {request.strategy_config_id}): {e}", exc_info=True)

        return StrategyVisualizationDataResponse(
            strategy_config_id=request.strategy_config_id,
            symbol_visualized=symbol_to_visualize,
            period_start_date=request.start_date,
            period_end_date=request.end_date,
            ohlcv_data=ohlcv_bars,
            indicator_data=indicator_data_dict,
            entry_signals=entry_signals_list,
            exit_signals=exit_signals_list,
            paper_trades=paper_trades_list
        )
