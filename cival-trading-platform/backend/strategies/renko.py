import pandas as pd
import numpy as np
import vectorbt as vbt
from logging import getLogger
from typing import Optional, Tuple, Literal

try:
    from openbb import obb
except ImportError:
    obb = None

logger = getLogger(__name__)

# Default parameters for Renko
DEFAULT_RENKO_BRICK_SIZE_MODE: Literal["fixed", "atr"] = "atr"
DEFAULT_RENKO_ATR_PERIOD = 14
DEFAULT_RENKO_FIXED_BRICK_SIZE = None # Must be set if mode is 'fixed'

def calculate_renko_bricks(
    price_series: pd.Series,
    brick_size: float # Brick size must be pre-calculated and positive
) -> pd.DataFrame:
    """
    Calculates Renko bricks from a price series using a pre-defined brick size.
    Returns a DataFrame with 'open', 'high', 'low', 'close' of each Renko brick,
    and 'type' (1 for up brick, -1 for down brick). Brick timestamps match the
    original price series bar that completed the brick.
    """
    if price_series.empty:
        logger.warning("Input price_series is empty for Renko calculation.")
        return pd.DataFrame()
    if brick_size <= 0:
        logger.error(f"Brick size must be positive. Got: {brick_size}")
        raise ValueError("Brick size must be positive.")

    renko_bricks_list = []
    # Initial reference price: first price in the series.
    # Renko bricks traditionally start from a level that's a multiple of the brick size,
    # or simply from the first price, and the first brick forms after a move of `brick_size`.
    # For this implementation, we'll use the first price as the initial reference point (last_brick_close).
    # The first actual brick will be plotted once the price moves `brick_size` away from this.

    # More robust: start with the first price as the effective 'close' of a hypothetical zeroth brick.
    last_brick_close = price_series.iloc[0]
    brick_type = 0 # 0: no direction yet, 1: up, -1: down

    for timestamp, current_price in price_series.items():
        if brick_type == 0: # Determining direction for the very first brick
            if current_price >= last_brick_close + brick_size:
                brick_type = 1
                num_bricks = int((current_price - last_brick_close) / brick_size)
                for i in range(num_bricks):
                    brick_open = last_brick_close + i * brick_size
                    brick_close = brick_open + brick_size
                    renko_bricks_list.append({'timestamp': timestamp, 'open': brick_open, 'high': brick_close,
                                         'low': brick_open, 'close': brick_close, 'type': 1})
                last_brick_close = brick_close # Update to the close of the last formed brick
            elif current_price <= last_brick_close - brick_size:
                brick_type = -1
                num_bricks = int((last_brick_close - current_price) / brick_size)
                for i in range(num_bricks):
                    brick_open = last_brick_close - i * brick_size
                    brick_close = brick_open - brick_size
                    renko_bricks_list.append({'timestamp': timestamp, 'open': brick_open, 'high': brick_open,
                                         'low': brick_close, 'close': brick_close, 'type': -1})
                last_brick_close = brick_close
            # If no brick formed yet, last_brick_close remains the initial price.
            # If a brick did form, last_brick_close is updated.
            continue # Move to next price point

        # Subsequent bricks after the first one has formed
        if brick_type == 1: # Last brick was UP
            if current_price >= last_brick_close + brick_size: # New UP brick(s)
                num_bricks = int((current_price - last_brick_close) / brick_size)
                for _ in range(num_bricks):
                    brick_open = last_brick_close
                    brick_close = last_brick_close + brick_size
                    renko_bricks_list.append({'timestamp': timestamp, 'open': brick_open, 'high': brick_close,
                                         'low': brick_open, 'close': brick_close, 'type': 1})
                    last_brick_close = brick_close
            elif current_price <= last_brick_close - 2 * brick_size: # Reversal to DOWN brick(s)
                brick_type = -1
                # First reversal brick opens one level down from previous close of the up brick
                brick_open = last_brick_close - brick_size
                brick_close = brick_open - brick_size
                renko_bricks_list.append({'timestamp': timestamp, 'open': brick_open, 'high': brick_open,
                                     'low': brick_close, 'close': brick_close, 'type': -1})
                last_brick_close = brick_close
                # Check for further down bricks if the drop was large enough
                num_additional_bricks = int(np.floor((last_brick_close - current_price) / brick_size)) # Use floor for additional bricks
                for _ in range(num_additional_bricks):
                    brick_open = last_brick_close
                    brick_close = last_brick_close - brick_size
                    renko_bricks_list.append({'timestamp': timestamp, 'open': brick_open, 'high': brick_open,
                                         'low': brick_close, 'close': brick_close, 'type': -1})
                    last_brick_close = brick_close

        elif brick_type == -1: # Last brick was DOWN
            if current_price <= last_brick_close - brick_size: # New DOWN brick(s)
                num_bricks = int((last_brick_close - current_price) / brick_size)
                for _ in range(num_bricks):
                    brick_open = last_brick_close
                    brick_close = last_brick_close - brick_size
                    renko_bricks_list.append({'timestamp': timestamp, 'open': brick_open, 'high': brick_open,
                                         'low': brick_close, 'close': brick_close, 'type': -1})
                    last_brick_close = brick_close
            elif current_price >= last_brick_close + 2 * brick_size: # Reversal to UP brick(s)
                brick_type = 1
                brick_open = last_brick_close + brick_size
                brick_close = brick_open + brick_size
                renko_bricks_list.append({'timestamp': timestamp, 'open': brick_open, 'high': brick_close,
                                     'low': brick_open, 'close': brick_close, 'type': 1})
                last_brick_close = brick_close
                num_additional_bricks = int(np.floor((current_price - last_brick_close) / brick_size)) # Use floor
                for _ in range(num_additional_bricks):
                    brick_open = last_brick_close
                    brick_close = last_brick_close + brick_size
                    renko_bricks_list.append({'timestamp': timestamp, 'open': brick_open, 'high': brick_close,
                                         'low': brick_open, 'close': brick_close, 'type': 1})
                    last_brick_close = brick_close

    if not renko_bricks_list:
        return pd.DataFrame()
    return pd.DataFrame(renko_bricks_list).set_index('timestamp')


def get_renko_signals(
    symbol: str,
    start_date: str,
    end_date: str,
    brick_size_mode: Literal["fixed", "atr"] = DEFAULT_RENKO_BRICK_SIZE_MODE,
    brick_size_value: Optional[float] = None,
    atr_period: int = DEFAULT_RENKO_ATR_PERIOD,
    data_provider: str = "yfinance"
) -> Optional[pd.DataFrame]:
    logger.info(f"Generating Renko signals for {symbol} from {start_date} to {end_date}, mode: {brick_size_mode}")

    if obb is None:
        logger.error("OpenBB SDK not available.")
        return None

    try:
        price_obb = obb.equity.price.historical(symbol=symbol, start_date=start_date, end_date=end_date, provider=data_provider, interval="1d")
        if not price_obb or not hasattr(price_obb, 'to_df'):
            logger.warning(f"No data or unexpected data object returned for {symbol}")
            return None
        price_df_orig = price_obb.to_df()
        if price_df_orig.empty:
            logger.warning(f"No data for {symbol} from {start_date} to {end_date}")
            return None

        rename_map = {}
        for col_map_from, col_map_to in {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}.items():
            if col_map_from in price_df_orig.columns: rename_map[col_map_from] = col_map_to
            elif col_map_to not in price_df_orig.columns and col_map_from.title() in price_df_orig.columns: rename_map[col_map_from.title()] = col_map_to
        price_df_orig.rename(columns=rename_map, inplace=True)

        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume'] # Ensure these are present after rename
        if not all(col in price_df_orig.columns for col in required_cols):
            logger.error(f"DataFrame for {symbol} is missing required OHLCV columns. Available: {price_df_orig.columns.tolist()}")
            return None
        price_df_orig = price_df_orig[required_cols].copy()

        close_prices = price_df_orig['Close']
        if close_prices.empty:
            logger.warning(f"Close price series is empty for {symbol}")
            return None

        current_brick_size = 0.0
        if brick_size_mode == "atr":
            if brick_size_value is not None:
                current_brick_size = brick_size_value
                logger.info(f"Using provided ATR value as brick size: {current_brick_size}")
            else:
                atr_series = vbt.ATR.run(price_df_orig['High'], price_df_orig['Low'], price_df_orig['Close'], window=atr_period, ewm=False).atr # Use SMA for ATR
                if atr_series.empty or np.isnan(atr_series.iloc[-1]) or atr_series.iloc[-1] == 0:
                    logger.error(f"ATR calculation failed or resulted in zero/NaN for {symbol}. Cannot use ATR mode.")
                    return None
                current_brick_size = round(atr_series.iloc[-1], 8) # Round ATR to sensible precision
                logger.info(f"Calculated ATR({atr_period}) for brick size: {current_brick_size}")
        elif brick_size_mode == "fixed":
            if brick_size_value is None or brick_size_value <= 0:
                logger.error("Fixed brick size must be positive and provided for 'fixed' mode.")
                return None
            current_brick_size = brick_size_value
        else:
            logger.error(f"Invalid brick_size_mode: {brick_size_mode}")
            return None

        if current_brick_size <= 0: # Should be caught above, but defense
            logger.error(f"Calculated or provided brick size is not positive: {current_brick_size}")
            return None

        renko_df = calculate_renko_bricks(close_prices, brick_size=current_brick_size)
        if renko_df.empty:
            logger.warning(f"No Renko bricks generated for {symbol}. Original data will be returned without signals.")
            price_df_orig['entries'] = False
            price_df_orig['exits'] = False
            return price_df_orig

        # Merge Renko brick type with original DataFrame
        # Need to align timestamps carefully. Renko bricks are timestamped with the original bar that COMPLETED them.
        # We want to make decisions on the NEXT bar's open after a Renko signal.
        price_df_orig['renko_type'] = renko_df['type'].reindex(price_df_orig.index, method=None) # Get type for bars that completed a brick
        price_df_orig['renko_type'].ffill(inplace=True) # Carry forward the type of the last completed brick
        price_df_orig.fillna({'renko_type': 0}, inplace=True) # Bars before first brick have type 0

        price_df_orig['entries'] = False
        price_df_orig['exits'] = False

        renko_type_shifted = price_df_orig['renko_type'].shift(1).fillna(0)

        # Entry: Current brick is UP (1) and previous brick was DOWN (-1)
        price_df_orig.loc[(price_df_orig['renko_type'] == 1) & (renko_type_shifted == -1), 'entries'] = True
        # Exit (or Short Entry): Current brick is DOWN (-1) and previous brick was UP (1)
        price_df_orig.loc[(price_df_orig['renko_type'] == -1) & (renko_type_shifted == 1), 'exits'] = True

        price_df_orig.loc[price_df_orig['entries'], 'exits'] = False

        logger.info(f"Generated {price_df_orig['entries'].sum()} Renko entry signals and {price_df_orig['exits'].sum()} exit signals for {symbol}.")
        return price_df_orig

    except Exception as e:
        logger.error(f"Error generating Renko signals for {symbol}: {e}", exc_info=True)
        return None

def run_renko_backtest(
    price_data_with_signals: pd.DataFrame,
    init_cash: float = 100000,
    size: float = 0.10,
    commission_pct: float = 0.001,
    freq: str = 'D'
) -> Optional[vbt.Portfolio.StatsEntry]:
    if price_data_with_signals is None or not all(col in price_data_with_signals for col in ['Close', 'entries', 'exits']):
        logger.error("Price data is missing required 'Close', 'entries', or 'exits' columns for Renko backtest.")
        return None
    if price_data_with_signals['entries'].sum() == 0 and price_data_with_signals['exits'].sum() == 0 :
        logger.warning("No entry or exit signals found for Renko. Backtest will show no trades.")

    try:
        portfolio = vbt.Portfolio.from_signals(
            close=price_data_with_signals['Close'],
            entries=price_data_with_signals['entries'],
            exits=price_data_with_signals['exits'],
            init_cash=init_cash,
            size=size,
            size_type='percentequity',
            fees=commission_pct,
            freq=freq
        )
        logger.info("Renko backtest portfolio created successfully.")
        return portfolio.stats()
    except Exception as e:
        logger.error(f"Error running Renko vectorbt backtest: {e}", exc_info=True)
        return None

# Example Usage (commented out):
# if __name__ == '__main__':
#     symbol_to_test = "BTC-USD"
#     start_date_test = "2023-01-01" # Shorter period for faster testing
#     end_date_test = "2023-06-30"
#     logger.info(f"--- Running Renko Example for {symbol_to_test} ---")
#
#     # Test with fixed brick size
#     # signals_df_fixed = get_renko_signals(symbol_to_test, start_date_test, end_date_test,
#     #                                   brick_size_mode="fixed", brick_size_value=500.0) # Brick size for BTC
#     # if signals_df_fixed is not None and not signals_df_fixed.empty:
#     #     print("\nSignals DataFrame with Renko info (Fixed Brick Size):")
#     #     print(signals_df_fixed[signals_df_fixed['entries'] | signals_df_fixed['exits']][['Close', 'renko_type', 'entries', 'exits']].head(10))
#     #     stats_fixed = run_renko_backtest(signals_df_fixed, freq='D')
#     #     if stats_fixed: print("\nBacktest Stats (Fixed Brick):\n", stats_fixed)
#     # else:
#     #     logger.warning("Could not generate Renko signals with fixed brick size.")
#
#     # Test with ATR brick size (function calculates ATR internally)
#     signals_df_atr = get_renko_signals(symbol_to_test, start_date_test, end_date_test,
#                                        brick_size_mode="atr", atr_period=14)
#     if signals_df_atr is not None and not signals_df_atr.empty:
#         print("\nSignals DataFrame with Renko info (ATR Brick Size):")
#         print(signals_df_atr[signals_df_atr['entries'] | signals_df_atr['exits']][['Close', 'renko_type', 'entries', 'exits']].head(10))
#         stats_atr = run_renko_backtest(signals_df_atr, freq='D')
#         if stats_atr: print("\nBacktest Stats (ATR Brick):\n", stats_atr)
#     else:
#         logger.warning("Could not generate Renko signals with ATR brick size.")
#
#     logger.info(f"--- End of Renko Example for {symbol_to_test} ---")
