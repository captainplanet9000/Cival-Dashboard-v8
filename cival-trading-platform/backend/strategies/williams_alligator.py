import pandas as pd
import numpy as np
import vectorbt as vbt
from logging import getLogger
from typing import Optional, Tuple

try:
    from openbb import obb
except ImportError:
    obb = None

logger = getLogger(__name__)

# Default parameters for Williams Alligator
DEFAULT_JAW_PERIOD = 13
DEFAULT_JAW_OFFSET = 8
DEFAULT_TEETH_PERIOD = 8
DEFAULT_TEETH_OFFSET = 5
DEFAULT_LIPS_PERIOD = 5
DEFAULT_LIPS_OFFSET = 3

def calculate_smma(series: pd.Series, period: int) -> pd.Series:
    """Helper to calculate Smoothed Moving Average (SMMA) / Running Moving Average (RMA)."""
    # Using ewm with alpha = 1/period is a common way to calculate SMMA.
    # adjust=False is important for it to behave like a traditional SMMA/RMA.
    return series.ewm(alpha=1/period, adjust=False).mean()

def get_williams_alligator_signals(
    symbol: str,
    start_date: str,
    end_date: str,
    jaw_period: int = DEFAULT_JAW_PERIOD, jaw_offset: int = DEFAULT_JAW_OFFSET,
    teeth_period: int = DEFAULT_TEETH_PERIOD, teeth_offset: int = DEFAULT_TEETH_OFFSET,
    lips_period: int = DEFAULT_LIPS_PERIOD, lips_offset: int = DEFAULT_LIPS_OFFSET,
    data_provider: str = "yfinance"
) -> Optional[pd.DataFrame]:
    logger.info(f"Generating Williams Alligator signals for {symbol} from {start_date} to {end_date} using provider {data_provider}")

    if obb is None:
        logger.error("OpenBB SDK not available. Cannot fetch data for Williams Alligator strategy.")
        return None

    try:
        data_obb = obb.equity.price.historical(
            symbol=symbol, start_date=start_date, end_date=end_date, provider=data_provider, interval="1d"
        )
        if not data_obb or not hasattr(data_obb, 'to_df'):
            logger.warning(f"No data or unexpected data object returned for {symbol} from {start_date} to {end_date} by provider {data_provider}")
            return None

        price_data = data_obb.to_df()
        if price_data.empty:
            logger.warning(f"No data returned (empty DataFrame) for {symbol} from {start_date} to {end_date} by provider {data_provider}")
            return None

        rename_map = {}
        for col_map_from, col_map_to in {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}.items():
            if col_map_from in price_data.columns:
                rename_map[col_map_from] = col_map_to
            elif col_map_to in price_data.columns:
                pass
            else:
                title_case_col = col_map_from.title()
                if title_case_col in price_data.columns:
                     rename_map[title_case_col] = col_map_to
        price_data.rename(columns=rename_map, inplace=True)

        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in price_data.columns for col in required_cols):
            logger.error(f"DataFrame for {symbol} is missing one or more required columns: {required_cols}. Available: {price_data.columns.tolist()}")
            return None

        price_data = price_data[required_cols].copy()

        # Use median price (High+Low)/2 for Alligator calculations
        median_price = (price_data['High'] + price_data['Low']) / 2

        jaw_line_unshifted = calculate_smma(median_price, jaw_period)
        teeth_line_unshifted = calculate_smma(median_price, teeth_period)
        lips_line_unshifted = calculate_smma(median_price, lips_period)

        price_data['jaw'] = jaw_line_unshifted.shift(jaw_offset)
        price_data['teeth'] = teeth_line_unshifted.shift(teeth_offset)
        price_data['lips'] = lips_line_unshifted.shift(lips_offset)

        price_data.dropna(inplace=True)

        if price_data.empty:
            logger.warning(f"Data became empty after Alligator calculations for {symbol}. Insufficient history for periods/offsets.")
            return None

        price_data['entries'] = False
        price_data['exits'] = False

        is_bullish_aligned = (price_data['lips'] > price_data['teeth']) & (price_data['teeth'] > price_data['jaw'])
        # is_bearish_aligned = (price_data['lips'] < price_data['teeth']) & (price_data['teeth'] < price_data['jaw']) # For short signals

        # Long entry: Previous state was not bullishly aligned, current state is.
        price_data.loc[is_bullish_aligned & ~is_bullish_aligned.shift(1).fillna(False), 'entries'] = True

        # Exit long: Bullish alignment is lost (e.g., Lips cross below Teeth)
        # A more robust exit might be when lips cross below teeth, or teeth cross below jaw.
        # Simple version: if it's no longer bullishly aligned but was on the previous bar.
        price_data.loc[~is_bullish_aligned & is_bullish_aligned.shift(1).fillna(False), 'exits'] = True

        price_data.loc[price_data['entries'], 'exits'] = False

        logger.info(f"Generated {price_data['entries'].sum()} entry signals and {price_data['exits'].sum()} exit signals for {symbol}.")
        return price_data

    except Exception as e:
        logger.error(f"Error generating Williams Alligator signals for {symbol}: {e}", exc_info=True)
        return None

def run_williams_alligator_backtest(
    price_data_with_signals: pd.DataFrame,
    init_cash: float = 100000,
    size: float = 0.10,
    commission_pct: float = 0.001,
    freq: str = 'D'
) -> Optional[vbt.Portfolio.StatsEntry]:
    if price_data_with_signals is None or not all(col in price_data_with_signals for col in ['Close', 'entries', 'exits']):
        logger.error("Price data with signals is missing required 'Close', 'entries', or 'exits' columns.")
        return None
    if price_data_with_signals['entries'].sum() == 0:
        logger.warning("No entry signals found. Backtest will show no trades.")

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
        logger.info("Williams Alligator backtest portfolio created successfully.")
        return portfolio.stats()
    except Exception as e:
        logger.error(f"Error running Williams Alligator vectorbt backtest: {e}", exc_info=True)
        return None

# Example Usage (commented out):
# if __name__ == '__main__':
#     symbol_to_test = "AAPL"
#     start_date_test = "2020-01-01"
#     end_date_test = "2023-12-31"
#     logger.info(f"--- Running Williams Alligator Example for {symbol_to_test} ---")
#     signals_df = get_williams_alligator_signals(symbol_to_test, start_date_test, end_date_test)
#     if signals_df is not None and not signals_df.empty:
#         print("\nSignals DataFrame head:")
#         print(signals_df[['Close', 'jaw', 'teeth', 'lips', 'entries', 'exits']].head(20))
#         print(f"\nTotal Entry Signals: {signals_df['entries'].sum()}")
#         print(f"Total Exit Signals: {signals_df['exits'].sum()}")
#         stats = run_williams_alligator_backtest(signals_df)
#         if stats is not None:
#             print("\nBacktest Stats:")
#             print(stats)
#             # Plotting example:
#             # try:
#             #    signals_df[['Close', 'jaw', 'teeth', 'lips']].vbt.plot(
#             #        trace_kwargs=dict(name='Close'),
#             #        fig=None # Pass a figure if you want to add to an existing one
#             #    ).add_trace( # Example for plotting signals
#             #        go.Scatter(y=signals_df.loc[signals_df['entries'], 'Close'], mode='markers', marker_symbol='triangle-up', marker_color='green', name='Entry'),
#             #        row=1, col=1
#             #    ).add_trace(
#             #        go.Scatter(y=signals_df.loc[signals_df['exits'], 'Close'], mode='markers', marker_symbol='triangle-down', marker_color='red', name='Exit'),
#             #        row=1, col=1
#             #    ).show()
#             # except Exception as plot_e:
#             #    print(f"Plotting failed (might require graphical environment or Plotly setup): {plot_e}")
#     else:
#         logger.warning("Could not generate Williams Alligator signals.")
#     logger.info(f"--- End of Williams Alligator Example for {symbol_to_test} ---")
