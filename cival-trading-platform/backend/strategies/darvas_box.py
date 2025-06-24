import pandas as pd
import numpy as np
import vectorbt as vbt
from logging import getLogger
from typing import Optional, Tuple, List

# Attempt to import OpenBB; if not available, this strategy can't fetch data.
try:
    from openbb import obb
except ImportError:
    obb = None # Allows module to load but data fetching will fail.

logger = getLogger(__name__)

# Default parameters for Darvas Box
DEFAULT_LOOKBACK_PERIOD_DAYS = 20
DEFAULT_BOX_BREAKOUT_CONFIRMATION_BARS = 1
DEFAULT_MIN_BOX_DURATION_DAYS = 3
DEFAULT_VOLUME_INCREASE_FACTOR = 1.5
DEFAULT_STOP_LOSS_ATR_MULTIPLIER = 2.0
DEFAULT_ATR_PERIOD = 14

def get_darvas_signals(
    symbol: str,
    start_date: str,
    end_date: str,
    lookback_period: int = DEFAULT_LOOKBACK_PERIOD_DAYS,
    min_box_duration: int = DEFAULT_MIN_BOX_DURATION_DAYS,
    volume_factor: float = DEFAULT_VOLUME_INCREASE_FACTOR,
    breakout_confirmation_bars: int = DEFAULT_BOX_BREAKOUT_CONFIRMATION_BARS,
    stop_loss_atr_multiplier: float = DEFAULT_STOP_LOSS_ATR_MULTIPLIER,
    atr_period: int = DEFAULT_ATR_PERIOD,
    data_provider: str = "yfinance" # Allow provider to be specified
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    logger.info(f"Generating Darvas Box signals for {symbol} from {start_date} to {end_date} using {data_provider}")

    if obb is None:
        logger.error("OpenBB SDK not available. Cannot fetch data for Darvas Box strategy.")
        return None, None

    try:
        data_obb = obb.equity.price.historical(
            symbol=symbol, start_date=start_date, end_date=end_date, provider=data_provider, interval="1d" # Darvas is typically daily
        )
        if not data_obb or not hasattr(data_obb, 'to_df'):
            logger.warning(f"No data or unexpected data object returned for {symbol} from {start_date} to {end_date}")
            return None, None

        price_data = data_obb.to_df()
        if price_data.empty:
            logger.warning(f"No data returned (empty DataFrame) for {symbol} from {start_date} to {end_date}")
            return None, None

        # Ensure standard column names, case-insensitive match from OpenBB common outputs
        rename_map = {}
        for col_map_from, col_map_to in {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}.items():
            if col_map_from in price_data.columns:
                rename_map[col_map_from] = col_map_to
            elif col_map_to in price_data.columns: # Already in correct format
                pass
            else: # Try title case as another common variant from some providers
                title_case_col = col_map_from.title()
                if title_case_col in price_data.columns:
                     rename_map[title_case_col] = col_map_to

        price_data.rename(columns=rename_map, inplace=True)

        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in price_data.columns for col in required_cols):
            logger.error(f"DataFrame for {symbol} is missing one or more required columns after renaming: {required_cols}. Available: {price_data.columns.tolist()}")
            return None, None

        price_data = price_data[required_cols].copy()

    except Exception as e:
        logger.error(f"Failed to fetch or process data for {symbol} using OpenBB: {e}", exc_info=True)
        return None, None

    price_data['box_top'] = np.nan
    price_data['box_bottom'] = np.nan
    price_data['entries'] = False
    price_data['exits'] = False

    try:
        atr_indicator = vbt.ATR.run(price_data['High'], price_data['Low'], price_data['Close'], window=atr_period, ewm=False) # Use SMA for ATR as per some conventions
        price_data['atr'] = atr_indicator.atr.values
    except Exception as e:
        logger.warning(f"Could not calculate ATR for {symbol}, possibly insufficient data (min length {atr_period}): {e}. Stop-loss features might be impaired.")
        price_data['atr'] = np.nan

    avg_volume = price_data['Volume'].rolling(window=lookback_period, min_periods=1).mean()

    in_box = False
    box_start_index = -1
    current_box_top = np.nan
    current_box_bottom = np.nan
    entry_box_bottom_for_stop = np.nan

    plot_shapes_data = []

    for i in range(lookback_period, len(price_data)):
        current_high = price_data['High'].iloc[i]
        current_low = price_data['Low'].iloc[i]
        current_close = price_data['Close'].iloc[i]
        current_volume = price_data['Volume'].iloc[i]

        if not in_box:
            # Potential new box: current high is a new N-day high (lookback_period)
            if current_high >= price_data['High'].iloc[i-lookback_period:i].max():
                current_box_top = current_high
                current_box_bottom = current_low # Initial bottom is the low of this bar
                in_box = True
                box_start_index = i
                logger.debug(f"{price_data.index[i]}: Potential box started. Top: {current_box_top:.2f}, Temp Bottom: {current_box_bottom:.2f}")

        if in_box:
            price_data.loc[price_data.index[i], 'box_top'] = current_box_top # Tentative top

            if current_high > current_box_top:
                current_box_top = current_high
                current_box_bottom = current_low
                box_start_index = i
                price_data.loc[price_data.index[i], 'box_top'] = current_box_top
                price_data.loc[price_data.index[i], 'box_bottom'] = np.nan # Mark bottom as needing reconfirmation
                logger.debug(f"{price_data.index[i]}: Box top elevated to {current_box_top:.2f}, bottom reset to {current_box_bottom:.2f}, duration reset.")
            elif current_low < current_box_bottom:
                logger.debug(f"{price_data.index[i]}: Price {current_low:.2f} broke below current temp box bottom {current_box_bottom:.2f}. Box invalidated.")
                if box_start_index != -1 : # Check if box_start_index was valid
                     plot_shapes_data.append(dict(x0=price_data.index[box_start_index], x1=price_data.index[i], y0=current_box_bottom, y1=current_box_top, fillcolor="rgba(255,0,0,0.1)", line_color="red", name="Invalidated Box Attempt"))
                in_box = False
                current_box_top, current_box_bottom, entry_box_bottom_for_stop = np.nan, np.nan, np.nan
            else: # Price stays within current_box_top and current_box_bottom
                price_data.loc[price_data.index[i], 'box_bottom'] = current_box_bottom # Confirmed bottom for this bar
                box_duration_bars = i - box_start_index + 1 # Number of bars since box top was set/reset

                if box_duration_bars >= min_box_duration: # Box has matured
                    # Check for breakout BUY condition
                    confirmed_breakout = True # Assume true, then check confirmation bars
                    if breakout_confirmation_bars > 0:
                        # Ensure all relevant close prices are above current_box_top for confirmation period
                        # The confirmation period starts from the bar *after* the breakout bar up to `i`.
                        # A simpler way: current bar closes above, and previous N-1 bars (if breakout_confirmation_bars > 1) also closed above.
                        # For now, let's use: current close breaks out, and if confirmation >0, prior bars also support this.
                        # The loop below checks from i-breakout_confirmation_bars+1 up to i (inclusive)
                        # A more standard way: breakout bar at `j`, then check `j+1` to `j+confirmation_bars`.
                        # The current logic is: if current bar `i` is a breakout, check `i` and `i-1`...`i-conf+1`.

                        # If current bar is the breakout candidate:
                        if current_close > current_box_top:
                            if breakout_confirmation_bars > 0 : # If 0, current bar breakout is enough
                                start_confirm_idx = max(box_start_index, i - breakout_confirmation_bars + 1)
                                if not (price_data['Close'].iloc[start_confirm_idx : i+1] > current_box_top).all():
                                    confirmed_breakout = False
                        else: # Current bar is not breaking out
                            confirmed_breakout = False

                    if confirmed_breakout and current_volume > avg_volume.iloc[i-1] * volume_factor:
                        logger.info(f"{price_data.index[i]}: BUY signal. Breakout above {current_box_top:.2f} (confirmed bottom {current_box_bottom:.2f}) with volume.")
                        price_data.loc[price_data.index[i], 'entries'] = True
                        entry_box_bottom_for_stop = current_box_bottom

                        plot_shapes_data.append(dict(x0=price_data.index[box_start_index], x1=price_data.index[i], y0=current_box_bottom, y1=current_box_top, fillcolor="rgba(0,255,0,0.2)", line_color="green", name="Entry Box"))

                        in_box = False
                        current_box_top, current_box_bottom = np.nan, np.nan

        # Apply stop-loss logic if a position was entered
        # This simple logic assumes only one position is active at a time.
        if not np.isnan(entry_box_bottom_for_stop) and not price_data['entries'].iloc[i]: # If in an active trade (stop is set) AND not an entry bar
             if not np.isnan(price_data['atr'].iloc[i]): # Ensure ATR is available
                stop_price_level = entry_box_bottom_for_stop - (price_data['atr'].iloc[i] * stop_loss_atr_multiplier)
                if current_low < stop_price_level:
                    logger.info(f"{price_data.index[i]}: SELL (Stop-Loss) signal. Price {current_low:.2f} below stop {stop_price_level:.2f} (EntryBoxBottom: {entry_box_bottom_for_stop:.2f}, ATR: {price_data['atr'].iloc[i]:.2f})")
                    price_data.loc[price_data.index[i], 'exits'] = True
                    entry_box_bottom_for_stop = np.nan # Reset stop as position is exited

    # Fill forward box_top and box_bottom for plotting continuity if needed
    # price_data['box_top'].ffill(inplace=True)
    # price_data['box_bottom'].ffill(inplace=True) # Careful with ffill on bottom if it's reset to NaN often

    plot_shapes_df = pd.DataFrame(plot_shapes_data) if plot_shapes_data else pd.DataFrame() # Ensure DataFrame, even if empty
    return price_data, plot_shapes_df

def run_darvas_backtest(
    price_data_with_signals: pd.DataFrame,
    init_cash: float = 100000,
    size: float = 0.10, # Percentage of equity per trade
    commission_pct: float = 0.001,
    freq: str = 'D' # Ensure frequency matches data
) -> Optional[vbt.Portfolio.StatsEntry]:
    if price_data_with_signals is None or not all(col in price_data_with_signals for col in ['Close', 'entries', 'exits']):
        logger.error("Price data with signals is missing, or 'Close', 'entries'/'exits' columns not found.")
        return None
    if price_data_with_signals['entries'].sum() == 0:
        logger.warning("No entry signals found. Backtest will show no trades.")
        # Return empty stats or specific indicator for no trades
        # For now, let vectorbt handle this; it usually returns stats with Total Trades = 0.

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
        logger.info("Vectorbt backtest portfolio created successfully.")
        return portfolio.stats()
    except Exception as e:
        logger.error(f"Error running vectorbt backtest: {e}", exc_info=True)
        return None

# Example usage:
# if __name__ == '__main__':
#     signals_df, shapes_df = get_darvas_signals("MSFT", "2022-01-01", "2023-12-31", data_provider="yfinance")
#     if signals_df is not None:
#         print("\nSignals (Entries/Exits):")
#         print(signals_df[signals_df['entries'] | signals_df['exits']][['Close', 'entries', 'exits', 'box_top', 'box_bottom', 'atr']])
#
#         print("\nBacktest Stats:")
#         stats = run_darvas_backtest(signals_df, freq='D') # Assuming daily data
#         if stats is not None:
#             print(stats)
#         else:
#             print("Could not generate backtest stats.")
#
#         # To plot with vectorbt (interactive, requires plotly and a graphical environment):
#         # try:
#         #     price_plot = signals_df['Close'].vbt.plot(trace_kwargs=dict(name='Close'))
#         #     if not shapes_df.empty:
#         #          price_plot.add_shapes(shapes_df.to_dict(orient='records'))
#         #     price_plot.show()
#         # except Exception as e:
#         #     print(f"Plotting failed (might require graphical environment or Plotly setup): {e}")
#     else:
#         print("Could not generate Darvas signals.")
