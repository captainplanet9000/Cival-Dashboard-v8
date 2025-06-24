import asyncio
import os
import uuid
import json # For saving results to JSON
from datetime import datetime, timezone # For timestamped output directory
from dotenv import load_dotenv
from decimal import Decimal # Not directly used here but often in dependent modules
from logging import getLogger, basicConfig, INFO

# Configure basic logging for the script
basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# Assuming the script is run from a context where 'python_ai_services' is importable
# e.g., from the root of the project, or PYTHONPATH is set.
# This might require path adjustments if run directly from the 'scripts' directory.
try:
    from python_ai_services.services.simulated_trade_executor import SimulatedTradeExecutor
    from python_ai_services.strategies import (
        get_darvas_signals,
        get_williams_alligator_signals,
        get_heikin_ashi_signals,
        get_renko_signals,
        get_sma_crossover_signals,
        get_elliott_wave_signals # This is a stub, will likely show no trades
    )
    # Import parameter models to help define default params if needed, though not strictly necessary for this script
    from python_ai_services.models.strategy_models import (
        DarvasBoxParams, WilliamsAlligatorParams, HeikinAshiParams, RenkoParams # ElliottWaveParams not used as it's a stub
    )
except ImportError as e:
    logger.error(f"ImportError: {e}. Ensure PYTHONPATH is set correctly or run from project root.")
    logger.error("Example: PYTHONPATH=$PYTHONPATH:/path/to/your/project python python-ai-services/scripts/run_all_paper_backtests.py")
    exit(1)


async def main():
    # Load environment variables (SUPABASE_URL, SUPABASE_KEY)
    # Assumes .env file is in python-ai-services directory or project root
    # For script, let's assume .env is one level up from 'scripts' (i.e., in 'python-ai-services')
    env_path_scripts = os.path.join(os.path.dirname(__file__), '..', '.env')
    if not os.path.exists(env_path_scripts): # Fallback to current dir .env or project root .env
        env_path_scripts = os.path.join(os.path.dirname(__file__), '..', '..', '.env') # If scripts is in python-ai-services/scripts

    if os.path.exists(env_path_scripts):
        load_dotenv(dotenv_path=env_path_scripts)
        logger.info(f"Loaded .env file from: {env_path_scripts}")
    else:
        logger.warning(f".env file not found at {env_path_scripts} or parent. Supabase credentials must be in environment.")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment variables or .env file.")
        return

    # Initialize SimulatedTradeExecutor. EventService is optional and not critical for this script's output.
    try:
        # EventService is optional for SimulatedTradeExecutor, so passing None is fine if alerts aren't the focus here.
        trade_executor = SimulatedTradeExecutor(supabase_url=supabase_url, supabase_key=supabase_key, event_service=None)
    except ValueError as e:
        logger.error(f"Failed to initialize SimulatedTradeExecutor: {e}")
        return

    # Define common backtest parameters
    user_id = uuid.uuid4() # Dummy user for this backtest run
    symbol = "AAPL"       # Common symbol for testing
    start_date = "2022-01-01"
    end_date = "2022-12-31" # 1 year of data
    initial_cash = 100000.0
    trade_quantity = 10.0   # Fixed quantity for paper trades in this script

    strategies_to_test = [
        {
            "name": "Darvas Box",
            "signal_func": get_darvas_signals,
            "params": DarvasBoxParams().model_dump() # Use default params from Pydantic model
        },
        {
            "name": "Williams Alligator",
            "signal_func": get_williams_alligator_signals,
            "params": WilliamsAlligatorParams().model_dump()
        },
        {
            "name": "Heikin Ashi",
            "signal_func": get_heikin_ashi_signals,
            "params": HeikinAshiParams().model_dump()
        },
        {
            "name": "Renko (ATR based)",
            "signal_func": get_renko_signals,
            # RenkoParams needs brick_size_mode, and brick_size_value if fixed, or atr_period if atr.
            # get_renko_signals defaults to ATR mode and calculates ATR if brick_size_value is not given.
            "params": RenkoParams(brick_size_mode="atr", atr_period=14).model_dump()
        },
        {
            "name": "SMA Crossover (20/50)",
            "signal_func": get_sma_crossover_signals,
            "params": {"short_window": 20, "long_window": 50} # Matches function signature
        },
        {
            "name": "Elliott Wave (Stub)",
            "signal_func": get_elliott_wave_signals,
            "params": {} # Stub takes default swing_order
        },
    ]

    logger.info(f"--- Starting Batch Paper Backtest for User {user_id} ---")
    logger.info(f"Symbol: {symbol}, Period: {start_date} to {end_date}, Initial Cash: ${initial_cash:,.2f}\n")

    # Define and create output directory for results
    # Place it in python-ai-services/backtest_results/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.dirname(script_dir) # This should be python-ai-services
    backtest_results_output_dir = os.path.join(project_root_dir, 'backtest_results', datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
    os.makedirs(backtest_results_output_dir, exist_ok=True)
    logger.info(f"Saving backtest results to: {backtest_results_output_dir}")

    all_results_summary_list = [] # Keep this for overall summary if needed

    for strategy_test_config in strategies_to_test:
        strategy_name = strategy_test_config["name"]
        signal_func = strategy_test_config["signal_func"]
        params = strategy_test_config["params"]

        logger.info(f"--- Running Backtest for: {strategy_name} ---")
        logger.info(f"Parameters: {params}")

        try:
            performance_summary = await trade_executor.run_historical_paper_backtest(
                user_id=user_id,
                strategy_signal_func=signal_func,
                strategy_params=params,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash,
                trade_quantity=trade_quantity
            )

            logger.info(f"--- Results for {strategy_name} ---")
            if performance_summary.get("error"):
                logger.error(f"Error: {performance_summary['error']}")
            else:
                logger.info(f"  Initial Cash: ${performance_summary.get('initial_cash', 0):,.2f}")
                logger.info(f"  Final Portfolio Value: ${performance_summary.get('final_portfolio_value', 0):,.2f}")
                logger.info(f"  Net Profit: ${performance_summary.get('net_profit', 0):,.2f}")
                logger.info(f"  Final Cash: ${performance_summary.get('final_cash', 0):,.2f}")
                logger.info(f"  Final Unrealized P&L: ${performance_summary.get('total_unrealized_pnl_final', 0):,.2f}")
                num_trades_logged = performance_summary.get('logged_trades_count', 'N/A')
                logger.info(f"  Trades Logged: {num_trades_logged}")
                if performance_summary.get("final_open_positions"):
                    logger.info("  Final Open Positions:")
                    for pos in performance_summary["final_open_positions"]:
                        logger.info(f"    - {pos['symbol']}: Qty {pos['quantity']}, AvgPrice ${pos['average_entry_price']:.2f}, MktVal ${pos.get('current_market_value',0):.2f}, UnP&L ${pos.get('unrealized_pnl',0):.2f}")

            # Save detailed results to JSON file
            if performance_summary: # Ensure there's something to save
                # Sanitize strategy_name and symbol for filename
                safe_strategy_name = strategy_name.replace(' ', '_').replace('/', '_')
                safe_symbol = symbol.replace('/', '_')
                results_filename = f"{safe_strategy_name}_{safe_symbol}_{start_date}_to_{end_date}.json"
                full_results_path = os.path.join(backtest_results_output_dir, results_filename)

                try:
                    with open(full_results_path, 'w') as f:
                        # The summary from run_historical_paper_backtest is already a Dict[str, Any]
                        # with basic types, lists, and dicts.
                        json.dump(performance_summary, f, indent=4, default=str) # default=str for datetimes or other non-serializable
                    logger.info(f"Saved detailed results for {strategy_name} to: {full_results_path}")
                except Exception as e_json:
                    logger.error(f"Error saving results to JSON for {strategy_name}: {e_json}", exc_info=True)

            all_results_summary_list.append({"strategy": strategy_name, "summary": performance_summary})
            logger.info("---------------------------------------\n")

        except Exception as e:
            logger.error(f"Critical error running backtest for {strategy_name}: {e}", exc_info=True)
            all_results_summary_list.append({"strategy": strategy_name, "summary": {"error": str(e)}})
            logger.info("---------------------------------------\n")

    logger.info("--- All Batch Paper Backtests Completed ---")
    # Optionally, print a summary table of all_results_summary_list or save to a file.

if __name__ == "__main__":
    # Ensure .env is loaded from python-ai-services directory if running script directly
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dotenv_path_main = os.path.join(project_root, '.env')
    if os.path.exists(dotenv_path_main):
        load_dotenv(dotenv_path=dotenv_path_main, override=True)
        logger.info(f"Loaded .env from project root for direct script run: {dotenv_path_main}")
    else:
        logger.warning(f"Project root .env not found at {dotenv_path_main} for direct script run.")


    asyncio.run(main())
