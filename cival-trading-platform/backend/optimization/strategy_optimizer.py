import pandas as pd
import numpy as np
import itertools
from typing import Dict, Any, List, Callable, Optional
from logging import getLogger
import vectorbt as vbt # For StatsEntry type hint if needed, and for backtesting

# Assuming strategies and their parameter models are importable
# This might require careful path management or ensuring python-ai-services is in PYTHONPATH
from ..strategies.darvas_box import get_darvas_signals as get_darvas_signals_func, run_darvas_backtest as run_darvas_backtest_func
# from ..models.strategy_models import DarvasBoxParams # Import Pydantic model if used for validation or defaults
# For now, param_model is for future use, so direct model import might not be strictly needed yet.

logger = getLogger(__name__)

class StrategyOptimizerError(Exception):
    """Custom exception for strategy optimizer errors."""
    pass

class StrategyOptimizer:
    def __init__(self, strategy_name: str,
                 signal_func: Callable, # Requires symbol, start_date, end_date, **params
                 backtest_func: Callable, # Requires price_data_with_signals, init_cash, etc.
                 param_model: Optional[Any] = None, # Pydantic model for strategy params (e.g. DarvasBoxParams)
                 data_fetch_func: Optional[Callable] = None): # Optional: if signal_func doesn't fetch data
        """
        Initializes the StrategyOptimizer.

        Args:
            strategy_name (str): Name of the strategy to optimize.
            signal_func (Callable): Function that takes symbol, start_date, end_date, and strategy parameters,
                                    returns a Tuple[pd.DataFrame with signals, Optional[pd.DataFrame for plotting]].
            backtest_func (Callable): Function that takes price data with signals and runs a backtest,
                                      returning performance stats (e.g., vectorbt Portfolio.stats()).
            param_model (Optional[Any]): The Pydantic model for the strategy's parameters.
                                         (Currently for informational/future use).
            data_fetch_func (Optional[Callable]): Function to fetch historical data. Not used if signal_func
                                                  handles its own data fetching (as current strategies do).
        """
        self.strategy_name = strategy_name
        self.signal_func = signal_func
        self.backtest_func = backtest_func
        self.param_model = param_model # For future use (e.g. deriving default grid)
        self.data_fetch_func = data_fetch_func # For strategies not fetching their own data
        logger.info(f"StrategyOptimizer initialized for strategy: {self.strategy_name}")

    def _generate_param_combinations(self, param_grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Generates all possible parameter combinations from a grid.
        """
        if not param_grid:
            return [{}]

        keys = param_grid.keys()
        values = param_grid.values()
        # Check for empty lists in values, which would lead to no combinations
        if any(not v_list for v_list in values):
            logger.warning("Empty list found in param_grid values. This will result in no combinations for that parameter.")
            # Filter out keys with empty lists for itertools.product
            valid_grid = {k: v for k, v in param_grid.items() if v}
            if not valid_grid: return [{}] # If all lists were empty or grid became empty
            keys = valid_grid.keys()
            values = valid_grid.values()

        combinations = list(itertools.product(*values))

        param_combinations = [dict(zip(keys, combo)) for combo in combinations]
        return param_combinations

    def run_grid_search(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        param_grid: Dict[str, List[Any]],
        optimization_metric: str = "Sharpe Ratio",
        init_cash: float = 100000,
        commission_pct: float = 0.001,
        # Pass other fixed args required by signal_func or backtest_func if any
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        logger.info(f"Starting grid search for {self.strategy_name} on {symbol} ({start_date} to {end_date})")
        logger.debug(f"Parameter grid: {param_grid}")
        logger.info(f"Optimizing for: {optimization_metric}")

        param_combinations = self._generate_param_combinations(param_grid)
        if not param_combinations:
            logger.warning("No parameter combinations generated. Check param_grid structure and values.")
            return {"error": "No parameter combinations generated.", "all_run_results": []}

        best_performance = -np.inf
        best_params = None
        best_stats_dict = None # Store stats as dict for easier JSON later

        results_summary = []

        for i, params in enumerate(param_combinations):
            logger.info(f"Testing combination {i+1}/{len(param_combinations)}: {params}")
            current_metric_value = -np.inf # Default for this run
            stats_for_run = None
            error_for_run = None

            try:
                # Merge fixed kwargs into current params for the signal function
                signal_func_params = {**params, **kwargs.get("signal_func_kwargs", {})}

                # Signal function is expected to return: (signals_df, shapes_df or None)
                price_data_with_signals, _ = self.signal_func(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    **signal_func_params
                )

                if price_data_with_signals is None or price_data_with_signals.empty:
                    logger.warning(f"No signal data generated for params: {params}. Skipping.")
                    error_for_run = "No signal data"
                elif price_data_with_signals['entries'].sum() == 0:
                    logger.warning(f"No entry signals for params: {params}. Assigning poor performance.")
                    # No error, but no trades, so metric remains -np.inf
                else:
                    backtest_func_params = {**kwargs.get("backtest_func_kwargs", {})}
                    stats_vbt = self.backtest_func( # vectorbt stats object
                        price_data_with_signals=price_data_with_signals,
                        init_cash=init_cash,
                        commission_pct=commission_pct,
                        **backtest_func_params
                    )

                    if stats_vbt is None:
                        logger.warning(f"Backtest failed for params: {params}.")
                        error_for_run = "Backtest failed"
                    elif not isinstance(stats_vbt, pd.Series) and not isinstance(stats_vbt, dict):
                        # Assuming stats_vbt is a vectorbt StatsEntry which is Series-like or Dict-like
                        logger.warning(f"Backtest stats for params: {params} is not a Series or Dict. Type: {type(stats_vbt)}")
                        error_for_run = "Non-standard stats format"
                    elif optimization_metric not in stats_vbt:
                        logger.warning(f"Metric '{optimization_metric}' not found in stats for params: {params}. Available: {list(stats_vbt.keys())}")
                        error_for_run = f"Metric '{optimization_metric}' not found"
                    else:
                        current_metric_value = stats_vbt[optimization_metric]
                        if pd.isna(current_metric_value):
                            logger.warning(f"Metric '{optimization_metric}' is NaN for params: {params}. Treating as poor performance.")
                            current_metric_value = -np.inf
                        stats_for_run = dict(stats_vbt) # Convert to dict for storing

                if current_metric_value > best_performance:
                    best_performance = current_metric_value
                    best_params = params
                    best_stats_dict = stats_for_run
                    logger.info(f"New best performance: {optimization_metric} = {best_performance:.4f} with params: {best_params}")

            except Exception as e:
                logger.error(f"Error during optimization run with params {params}: {e}", exc_info=True)
                error_for_run = str(e)

            results_summary.append({
                "params": params,
                "metric_value": current_metric_value if current_metric_value != -np.inf else "N/A",
                "error": error_for_run,
                # "full_stats_preview": {k: v for k, v in stats_for_run.items() if k in ['Total Return [%]', 'Sharpe Ratio', 'Sortino Ratio', 'Win Rate [%]', 'Total Trades']} if stats_for_run else None
            })


        if best_params is not None:
            logger.info(f"Grid search completed for {self.strategy_name} on {symbol}.")
            logger.info(f"Best parameters found: {best_params}")
            logger.info(f"Best {optimization_metric}: {best_performance:.4f}")
            return {
                "strategy_name": self.strategy_name,
                "symbol": symbol,
                "best_parameters": best_params,
                "optimized_metric": optimization_metric,
                "best_metric_value": best_performance if best_performance != -np.inf else None, # Return None if still -np.inf
                "best_stats": best_stats_dict,
                "all_run_results": results_summary
            }
        else:
            logger.warning(f"Grid search for {self.strategy_name} on {symbol} did not find any successful parameter combination yielding positive performance improvement.")
            return {"error": "No successful parameter combination found or performance did not improve.", "all_run_results": results_summary}

# Example of how to use it (conceptual, would be in a script or service)
# if __name__ == "__main__":
#     # This example assumes DarvasBox strategy functions are correctly imported and work.
#     # Also assumes OpenBB is available and configured.
#
#     # Note: Keys in param_grid MUST match the parameter names of the signal_func
#     # (e.g., get_darvas_signals_func parameters like 'lookback_period', 'min_box_duration')
#     darvas_param_grid = {
#         "lookback_period": [20, 30],    # Matches 'lookback_period' in get_darvas_signals
#         "min_box_duration": [3, 5],     # Matches 'min_box_duration'
#         "volume_factor": [1.5, 2.0],
#         "breakout_confirmation_bars": [0, 1], # Matches 'breakout_confirmation_bars'
#         # "stop_loss_atr_multiplier": [1.5, 2.0], # Matches 'stop_loss_atr_multiplier'
#         # "atr_period": [10, 14] # Matches 'atr_period'
#     }
#
#     # For DarvasBox, data_fetch_func is not needed as get_darvas_signals_func handles it.
#     # param_model can be DarvasBoxParams from strategy_models.py if we want to use it.
#     # from ..models.strategy_models import DarvasBoxParams
#
#     optimizer = StrategyOptimizer(
#         strategy_name="DarvasBox",
#         signal_func=get_darvas_signals_func,
#         backtest_func=run_darvas_backtest_func,
#         # param_model=DarvasBoxParams
#     )
#
#     results = optimizer.run_grid_search(
#         symbol="AAPL",
#         start_date="2023-01-01", # Use a longer period for meaningful optimization
#         end_date="2023-06-30",
#         param_grid=darvas_param_grid,
#         optimization_metric="Sharpe Ratio", # Ensure this matches key in vbt stats
#         # Example of passing fixed kwargs to signal_func if needed:
#         # signal_func_kwargs={"data_provider": "fmp"}
#     )
#
#     if results and "error" not in results:
#         print("\n--- Optimization Results ---")
#         print(f"Strategy: {results['strategy_name']} for Symbol: {results['symbol']}")
#         print(f"Optimized for: {results['optimized_metric']}")
#         print(f"Best Parameters: {results['best_parameters']}")
#         print(f"Best Metric Value: {results['best_metric_value']:.4f if results['best_metric_value'] is not None else 'N/A'}")
#         print("\nFull Best Stats:")
#         if results['best_stats']:
#             for key, value in results['best_stats'].items():
#                 print(f"  {key}: {value}")
#         # print("\nAll Run Results:")
#         # for run in results.get("all_run_results", []):
#         #     print(f"  Params: {run['params']}, Metric: {run['metric_value']}, Error: {run.get('error')}")
#     elif results:
#         print(f"\nOptimization Error: {results['error']}")
#         # print("\nAll Run Results (even with error):")
#         # for run in results.get("all_run_results", []):
#         #     print(f"  Params: {run['params']}, Metric: {run['metric_value']}, Error: {run.get('error')}")
#     else:
#         print("Optimization returned no results object.")
