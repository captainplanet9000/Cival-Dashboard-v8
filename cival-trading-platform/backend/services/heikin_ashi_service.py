from ..models.agent_models import AgentConfigOutput, AgentStrategyConfig # For HeikinAshiParams
from ..models.event_bus_models import Event, TradeSignalEventPayload
from ..services.event_bus_service import EventBusService
from ..services.market_data_service import MarketDataService
from typing import List, Dict, Any, Optional, Literal # Added Literal
import pandas as pd
import numpy as np # For pd.notna checks if needed
from loguru import logger
from datetime import datetime, timezone # Ensure timezone for Event

class HeikinAshiTechnicalService:
    def __init__(
        self,
        agent_config: AgentConfigOutput,
        event_bus: EventBusService,
        market_data_service: MarketDataService
        # learning_logger: Optional[LearningDataLoggerService] = None # If adding learning logger
    ):
        self.agent_config = agent_config
        self.event_bus = event_bus
        self.market_data_service = market_data_service

        if self.agent_config.strategy.heikin_ashi_params:
            self.params = self.agent_config.strategy.heikin_ashi_params
        else:
            logger.warning(f"HeikinAshiSvc ({self.agent_config.agent_id}): HeikinAshiParams not found. Using defaults.")
            self.params = AgentStrategyConfig.HeikinAshiParams() # Use defaults from model definition
        # self.learning_logger = learning_logger # If adding

    def _calculate_heikin_ashi_candles(self, klines_df: pd.DataFrame) -> pd.DataFrame:
        if klines_df.empty:
            return pd.DataFrame(columns=['ha_open', 'ha_high', 'ha_low', 'ha_close', 'timestamp'])

        ha_df = pd.DataFrame(index=klines_df.index)

        # Ensure original columns are numeric
        for col in ['open', 'high', 'low', 'close']:
            klines_df[col] = pd.to_numeric(klines_df[col], errors='coerce')

        ha_df['ha_close'] = (klines_df['open'] + klines_df['high'] + klines_df['low'] + klines_df['close']) / 4

        # Calculate HA Open
        ha_df['ha_open'] = 0.0 # Initialize column with a float type
        if len(klines_df) > 0: # Check if DataFrame is not empty
            ha_df.iloc[0, ha_df.columns.get_loc('ha_open')] = (klines_df['open'].iloc[0] + klines_df['close'].iloc[0]) / 2
            for i in range(1, len(klines_df)):
                ha_df.iloc[i, ha_df.columns.get_loc('ha_open')] = \
                    (ha_df['ha_open'].iloc[i-1] + ha_df['ha_close'].iloc[i-1]) / 2

        # Calculate HA High and HA Low
        # Create a temporary DataFrame for klines_df['high'] and klines_df['low'] to join
        temp_high_low_df = pd.DataFrame({
            'orig_high': klines_df['high'],
            'orig_low': klines_df['low']
        }, index=klines_df.index)

        ha_df['ha_high'] = ha_df[['ha_open', 'ha_close']].join(temp_high_low_df['orig_high']).max(axis=1)
        ha_df['ha_low'] = ha_df[['ha_open', 'ha_close']].join(temp_high_low_df['orig_low']).min(axis=1)

        if 'timestamp' in klines_df.columns: # Carry over timestamp if it exists
             ha_df['timestamp'] = klines_df['timestamp']

        return ha_df[['timestamp', 'ha_open', 'ha_high', 'ha_low', 'ha_close']] if 'timestamp' in ha_df else ha_df[['ha_open', 'ha_high', 'ha_low', 'ha_close']]


    async def _calculate_atr(self, klines_df: pd.DataFrame, period: int) -> Optional[float]:
        if len(klines_df) < period + 1:
            logger.debug(f"HA Svc ({self.agent_config.agent_id}): Not enough data for ATR period {period+1}. Have {len(klines_df)} candles.")
            return None

        # Ensure columns are numeric
        for col in ['high', 'low', 'close']:
            klines_df[col] = pd.to_numeric(klines_df[col], errors='coerce')

        df = klines_df.copy()
        df['tr1'] = abs(df['high'] - df['low'])
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df[['tr1', 'tr2', 'tr3']] = df[['tr1', 'tr2', 'tr3']].fillna(0) # Fill NaNs for robust max

        df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        atr_series = df['true_range'].rolling(window=period, min_periods=period).mean()

        if atr_series.empty or pd.isna(atr_series.iloc[-1]):
            logger.warning(f"HA Svc ({self.agent_config.agent_id}): ATR calculation resulted in NaN or empty series.")
            return None

        atr_value = atr_series.iloc[-1]
        return atr_value if pd.notna(atr_value) and atr_value > 1e-9 else None


    async def analyze_symbol_and_generate_signal(self, symbol: str):
        logger.info(f"HeikinAshiSvc ({self.agent_config.agent_id}): Analyzing {symbol} with params: {self.params.model_dump_json()}")

        # Fetch enough klines for longest lookback (trend_sma_period or atr_period_for_sl) + signal candles + buffer
        required_klines = max(self.params.trend_sma_period, self.params.atr_period_for_sl) + self.params.signal_confirmation_candles + 50 # Buffer

        raw_klines_list = await self.market_data_service.get_historical_klines(symbol, limit=required_klines)

        if not raw_klines_list or len(raw_klines_list) < max(self.params.trend_sma_period, self.params.atr_period_for_sl) + self.params.signal_confirmation_candles :
            logger.warning(f"HA Svc ({self.agent_config.agent_id}): Not enough kline data for {symbol} (fetched {len(raw_klines_list)}).")
            return

        klines_df = pd.DataFrame(raw_klines_list)
        # Ensure required columns exist and are numeric
        required_cols = ['timestamp', 'open', 'high', 'low', 'close']
        if not all(col in klines_df.columns for col in required_cols):
            logger.error(f"HA Svc ({self.agent_config.agent_id}): Kline data for {symbol} is missing one or more required columns: {required_cols}.")
            return
        try:
            for col in ['open', 'high', 'low', 'close']:
                klines_df[col] = pd.to_numeric(klines_df[col])
            klines_df['timestamp'] = pd.to_numeric(klines_df['timestamp'])
        except ValueError as e:
            logger.error(f"HA Svc ({self.agent_config.agent_id}): Error converting kline data to numeric for {symbol}: {e}")
            return


        ha_candles_df = self._calculate_heikin_ashi_candles(klines_df)
        if len(ha_candles_df) < max(self.params.trend_sma_period, self.params.signal_confirmation_candles + 1):
            logger.debug(f"HA Svc ({self.agent_config.agent_id}): Not enough HA candles ({len(ha_candles_df)}) for analysis on {symbol}.")
            return

        ha_candles_df['ha_sma_trend'] = ha_candles_df['ha_close'].rolling(window=self.params.trend_sma_period).mean()

        # Need enough data for signal_confirmation_candles + one candle before sequence + SMA period
        if len(ha_candles_df) < self.params.trend_sma_period + self.params.signal_confirmation_candles: # Ensure SMA is available for last candle in sequence
             logger.debug(f"HA Svc ({self.agent_config.agent_id}): Not enough HA candles with SMA for analysis on {symbol}.")
             return


        last_n_ha_candles = ha_candles_df.iloc[-self.params.signal_confirmation_candles:]
        candle_before_sequence_index = -self.params.signal_confirmation_candles - 1
        if len(ha_candles_df) <= self.params.signal_confirmation_candles: # Not enough history for "candle_before_sequence"
            logger.debug(f"HA Svc ({self.agent_config.agent_id}): Not enough HA history for candle_before_sequence on {symbol}.")
            return
        candle_before_sequence = ha_candles_df.iloc[candle_before_sequence_index]

        current_ha_candle = last_n_ha_candles.iloc[-1]
        current_ha_sma = current_ha_candle['ha_sma_trend']

        action: Optional[Literal["buy", "sell"]] = None # type: ignore

        # Buy Signal Logic: N strong green candles, after a non-strong-green candle, and HA close above HA SMA trend
        all_green_strong_sequence = True
        for _, candle in last_n_ha_candles.iterrows():
            if not (candle['ha_close'] > candle['ha_open'] and candle['ha_open'] == candle['ha_low']): # Green & no lower wick
                all_green_strong_sequence = False
                break

        if all_green_strong_sequence:
            prev_candle_not_strong_green = not (candle_before_sequence['ha_close'] > candle_before_sequence['ha_open'] and \
                                                candle_before_sequence['ha_open'] == candle_before_sequence['ha_low'])
            if prev_candle_not_strong_green and pd.notna(current_ha_sma) and current_ha_candle['ha_close'] > current_ha_sma:
                action = "buy"

        # Sell Signal Logic: N strong red candles, after a non-strong-red candle, and HA close below HA SMA trend
        if not action: # Only check for sell if no buy signal
            all_red_strong_sequence = True
            for _, candle in last_n_ha_candles.iterrows():
                if not (candle['ha_close'] < candle['ha_open'] and candle['ha_open'] == candle['ha_high']): # Red & no upper wick
                    all_red_strong_sequence = False
                    break

            if all_red_strong_sequence:
                prev_candle_not_strong_red = not (candle_before_sequence['ha_close'] < candle_before_sequence['ha_open'] and \
                                                  candle_before_sequence['ha_open'] == candle_before_sequence['ha_high'])
                if prev_candle_not_strong_red and pd.notna(current_ha_sma) and current_ha_candle['ha_close'] < current_ha_sma:
                    action = "sell"

        if action:
            current_actual_price = klines_df['close'].iloc[-1]
            # Use original klines_df for ATR calculation for SL based on actual price volatility
            atr = await self._calculate_atr(klines_df, self.params.atr_period_for_sl)
            sl_price: Optional[float] = None

            if atr is not None and atr > 1e-9: # Epsilon check for ATR
                if action == "buy":
                    sl_price = current_actual_price - (atr * self.params.stop_loss_atr_multiplier)
                else: # sell
                    sl_price = current_actual_price + (atr * self.params.stop_loss_atr_multiplier)
            else:
                logger.warning(f"HA Svc ({self.agent_config.agent_id}): ATR for SL is None or zero ({atr}) for {symbol}. SL not set.")

            # Round SL price to a reasonable number of decimal places (e.g., 4 or asset-specific)
            sl_price_rounded = round(sl_price, 4) if sl_price is not None else None


            signal_payload = TradeSignalEventPayload(
                symbol=symbol, action=action, quantity=None, # Quantity decided downstream
                price_target=round(current_actual_price, 4), # Signal at current market price
                stop_loss=sl_price_rounded,
                strategy_name=f"HeikinAshi_SMA{self.params.trend_sma_period}_Conf{self.params.signal_confirmation_candles}",
                confidence=0.75 # Example confidence, can be refined
            )
            event = Event(
                publisher_agent_id=self.agent_config.agent_id,
                message_type="TradeSignalEvent", payload=signal_payload.model_dump()
            )
            await self.event_bus.publish(event)
            logger.success(f"HeikinAshiSvc ({self.agent_config.agent_id}): Published {action.upper()} signal for {symbol} at {current_actual_price:.4f}. SL: {sl_price_rounded if sl_price_rounded else 'N/A'}")
        else:
            logger.info(f"HeikinAshiSvc ({self.agent_config.agent_id}): No signal generated for {symbol}.")
