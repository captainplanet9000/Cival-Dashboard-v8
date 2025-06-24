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

# Default parameters for Heikin Ashi
DEFAULT_TREND_CONFIRMATION_CANDLES = 3 # Number of consecutive HA candles to confirm trend
DEFAULT_EXIT_CHANGE_CANDLES = 1 # Number of HA candles changing color/type for potential exit

def calculate_heikin_ashi_candles(ohlc_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Heikin Ashi OHLC values from a standard OHLC DataFrame.
    Input DataFrame must have 'Open', 'High', 'Low', 'Close' columns.
    """
    if not all(col in ohlc_df.columns for col in ['Open', 'High', 'Low', 'Close']):
        logger.error("Input DataFrame for HA calculation must contain 'Open', 'High', 'Low', 'Close' columns.")
        # Consider raising ValueError or returning empty DataFrame if used as a public utility
        # For internal use here, assume the caller (get_heikin_ashi_signals) ensures this.
        # However, adding a safeguard:
        raise ValueError("Input DataFrame for HA calculation must contain 'Open', 'High', 'Low', 'Close' columns.")


    ha_df = pd.DataFrame(index=ohlc_df.index)

    # HA Close: (Open + High + Low + Close) / 4
    ha_df['ha_close'] = (ohlc_df['Open'] + ohlc_df['High'] + ohlc_df['Low'] + ohlc_df['Close']) / 4.0

    # HA Open: (Previous HA Open + Previous HA Close) / 2
    ha_df['ha_open'] = np.nan # Initialize column
    if not ohlc_df.empty:
        ha_df.loc[ha_df.index[0], 'ha_open'] = (ohlc_df['Open'].iloc[0] + ohlc_df['Close'].iloc[0]) / 2.0
        for i in range(1, len(ohlc_df)):
            ha_df.loc[ha_df.index[i], 'ha_open'] = (ha_df['ha_open'].iloc[i-1] + ha_df['ha_close'].iloc[i-1]) / 2.0

    # HA High: Max(Original High, HA Open, HA Close)
    # Ensure ha_open and ha_close are not NaN for max/min calculation; they should be filled by this point.
    ha_df['ha_high'] = ha_df[['ha_open', 'ha_close']].join(ohlc_df['High']).max(axis=1)

    # HA Low: Min(Original Low, HA Open, HA Close)
    ha_df['ha_low'] = ha_df[['ha_open', 'ha_close']].join(ohlc_df['Low']).min(axis=1)

    return ha_df[['ha_open', 'ha_high', 'ha_low', 'ha_close']].copy()


def get_heikin_ashi_signals(
    symbol: str,
    start_date: str,
    end_date: str,
    trend_confirmation_candles: int = DEFAULT_TREND_CONFIRMATION_CANDLES,
    exit_change_candles: int = DEFAULT_EXIT_CHANGE_CANDLES, # Number of opposite color candles for exit
    data_provider: str = "yfinance"
) -> Optional[pd.DataFrame]:
    logger.info(f"Generating Heikin Ashi signals for {symbol} from {start_date} to {end_date} using provider {data_provider}")

    if obb is None:
        logger.error("OpenBB SDK not available. Cannot fetch data for Heikin Ashi strategy.")
        return None

    try:
        data_obb = obb.equity.price.historical(
            symbol=symbol, start_date=start_date, end_date=end_date, provider=data_provider, interval="1d"
        )
        if not data_obb or not hasattr(data_obb, 'to_df'):
            logger.warning(f"No data or unexpected data object returned for {symbol} from {start_date} to {end_date}")
            return None
        price_data = data_obb.to_df()
        if price_data.empty:
            logger.warning(f"No data returned (empty DataFrame) for {symbol} from {start_date} to {end_date}")
            return None

        rename_map = {}
        for col_map_from, col_map_to in {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}.items():
            if col_map_from in price_data.columns: rename_map[col_map_from] = col_map_to
            elif col_map_to not in price_data.columns and col_map_from.title() in price_data.columns: rename_map[col_map_from.title()] = col_map_to
        price_data.rename(columns=rename_map, inplace=True)

        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in price_data.columns for col in required_cols):
            logger.error(f"DataFrame for {symbol} is missing required columns {required_cols}. Available: {price_data.columns.tolist()}")
            return None

        # Keep original OHLC for backtesting close price and other potential uses
        original_ohlcv = price_data[required_cols].copy()

        ha_candles = calculate_heikin_ashi_candles(original_ohlcv[['Open', 'High', 'Low', 'Close']])

        price_data = original_ohlcv.join(ha_candles) # Join HA candles to the original data
        price_data.dropna(subset=['ha_open', 'ha_close', 'ha_high', 'ha_low'], inplace=True) # Remove NaNs from initial HA calculation

        if price_data.empty:
            logger.warning(f"Data became empty after Heikin Ashi calculations for {symbol}. Insufficient data for HA generation.")
            return None

    except Exception as e:
        logger.error(f"Failed to fetch or process data for {symbol}: {e}", exc_info=True)
        return None

    price_data['entries'] = False
    price_data['exits'] = False

    # Define tolerance for shadow checks to handle floating point inaccuracies
    tolerance = 1e-5 # A small number, adjust based on price scale if necessary
    price_data['ha_green'] = price_data['ha_close'] > price_data['ha_open']
    price_data['ha_red'] = price_data['ha_close'] < price_data['ha_open']
    # No lower shadow (strong uptrend): ha_open is very close to ha_low
    price_data['ha_no_lower_shadow'] = abs(price_data['ha_open'] - price_data['ha_low']) < tolerance
    # No upper shadow (strong downtrend): ha_open is very close to ha_high
    # price_data['ha_no_upper_shadow'] = abs(price_data['ha_open'] - price_data['ha_high']) < tolerance # For shorting

    # Long Entry: N consecutive green HA candles, ideally with no lower shadows
    buy_condition = price_data['ha_green'] & price_data['ha_no_lower_shadow']
    entry_signal_active = buy_condition.rolling(window=trend_confirmation_candles, min_periods=trend_confirmation_candles).apply(lambda x: x.all(), raw=True).fillna(0).astype(bool)

    # Trigger entry on the bar *after* the confirmation
    # Shift signals by 1 to enter on the open of the next bar after confirmation
    shifted_entry_signal = entry_signal_active.shift(1).fillna(False)
    price_data.loc[shifted_entry_signal & ~shifted_entry_signal.shift(1).fillna(False), 'entries'] = True


    # Long Exit: N consecutive red HA candles (signifying trend change)
    sell_condition = price_data['ha_red']
    exit_signal_active = sell_condition.rolling(window=exit_change_candles, min_periods=exit_change_candles).apply(lambda x: x.all(), raw=True).fillna(0).astype(bool)

    # Trigger exit on the bar *after* exit confirmation
    shifted_exit_signal = exit_signal_active.shift(1).fillna(False)
    # Only exit if an entry signal was active previously (conceptual: must be in a trade)
    # This simplified logic doesn't track actual position state, vectorbt handles that.
    # We are providing signals. If an entry signal was active, and now an exit condition is met.
    # This requires a state machine or more complex logic to ensure we only exit if in a position.
    # For vectorbt, providing entry and exit signals separately is fine.
    price_data.loc[shifted_exit_signal, 'exits'] = True

    # Ensure no exit on the same bar as entry
    price_data.loc[price_data['entries'], 'exits'] = False

    # Ensure Close and Volume are present for backtesting (they should be from original_ohlcv join)
    if 'Close' not in price_data.columns and 'Close' in original_ohlcv.columns:
        price_data['Close'] = original_ohlcv['Close']
    if 'Volume' not in price_data.columns and 'Volume' in original_ohlcv.columns:
        price_data['Volume'] = original_ohlcv['Volume']
    price_data.dropna(subset=['Close'], inplace=True)


    logger.info(f"Generated {price_data['entries'].sum()} entry signals and {price_data['exits'].sum()} exit signals for {symbol}.")
    return price_data


def run_heikin_ashi_backtest(
    price_data_with_signals: pd.DataFrame,
    init_cash: float = 100000,
    size: float = 0.10,
    commission_pct: float = 0.001,
    freq: str = 'D'
) -> Optional[vbt.Portfolio.StatsEntry]:
    if price_data_with_signals is None or not all(col in price_data_with_signals for col in ['Close', 'entries', 'exits']):
        logger.error("Price data is missing required 'Close', 'entries', or 'exits' columns for Heikin Ashi backtest.")
        return None
    if price_data_with_signals['entries'].sum() == 0:
        logger.warning("No entry signals found for Heikin Ashi. Backtest will show no trades.")

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
        logger.info("Heikin Ashi backtest portfolio created successfully.")
        return portfolio.stats()
    except Exception as e:
        logger.error(f"Error running Heikin Ashi vectorbt backtest: {e}", exc_info=True)
        return None

# Example Usage (commented out):
# if __name__ == '__main__':
#     symbol_to_test = "MSFT"
#     start_date_test = "2022-01-01"
#     end_date_test = "2023-12-31"
#     logger.info(f"--- Running Heikin Ashi Example for {symbol_to_test} ---")
#     signals_df = get_heikin_ashi_signals(symbol_to_test, start_date_test, end_date_test,
#                                          trend_confirmation_candles=3, exit_change_candles=1)
#     if signals_df is not None and not signals_df.empty:
#         print("\nSignals DataFrame head (showing HA and original close):")
#         # Display relevant columns for verification
#         print(signals_df[['Close', 'ha_open', 'ha_high', 'ha_low', 'ha_close', 'ha_green', 'ha_no_lower_shadow', 'entries', 'exits']].head(30))
#         print(f"\nTotal Entry Signals: {signals_df['entries'].sum()}")
#         print(f"Total Exit Signals: {signals_df['exits'].sum()}")
#
#         stats = run_heikin_ashi_backtest(signals_df, freq='D') # Ensure freq matches data
#         if stats is not None:
#             print("\nBacktest Stats:")
#             print(stats)
#
#         # Plotting example (requires plotly and graphical environment)
#         # import plotly.graph_objects as go
#         # try:
#         #     fig = signals_df[['Close']].vbt.plot(trace_kwargs=dict(name='Original Close'))
#         #     fig.add_candlestick(
#         #         x=signals_df.index,
#         #         open=signals_df['ha_open'],
#         #         high=signals_df['ha_high'],
#         #         low=signals_df['ha_low'],
#         #         close=signals_df['ha_close'],
#         #         name="Heikin Ashi"
#         #     )
#         #     entry_points = signals_df[signals_df['entries']]
#         #     exit_points = signals_df[signals_df['exits']]
#         #     fig.add_trace(go.Scatter(x=entry_points.index, y=entry_points['Close'], mode='markers',
#         #                              marker=dict(symbol='triangle-up', color='green', size=10), name='Entry'))
#         #     fig.add_trace(go.Scatter(x=exit_points.index, y=exit_points['Close'], mode='markers',
#         #                              marker=dict(symbol='triangle-down', color='red', size=10), name='Exit'))
#         #     fig.show()
#         # except Exception as plot_e:
#         #     print(f"Plotting failed: {plot_e}")
#
#     else:
#         logger.warning("Could not generate Heikin Ashi signals.")
#     logger.info(f"--- End of Heikin Ashi Example for {symbol_to_test} ---")
