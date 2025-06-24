from ..models.agent_models import AgentConfigOutput, AgentStrategyConfig
from ..models.event_bus_models import Event, MarketConditionEventPayload
from ..services.event_bus_service import EventBusService
from ..services.market_data_service import MarketDataService
from .learning_data_logger_service import LearningDataLoggerService # Added
from ..models.learning_models import LearningLogEntry # Added
from typing import List, Dict, Any, Optional, Literal # Added Literal for regime
import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime, timezone

class MarketConditionClassifierService:
    def __init__(
        self,
        agent_config: AgentConfigOutput,
        event_bus: EventBusService,
        market_data_service: MarketDataService,
        learning_logger_service: Optional[LearningDataLoggerService] = None # Added
    ):
        self.agent_config = agent_config
        self.event_bus = event_bus
        self.market_data_service = market_data_service
        self.learning_logger_service = learning_logger_service # Store it

        if self.agent_config.strategy.market_condition_classifier_params:
            self.params = self.agent_config.strategy.market_condition_classifier_params
        else:
            logger.warning(f"MCC ({self.agent_config.agent_id}): market_condition_classifier_params not found. Using defaults.")
            self.params = AgentStrategyConfig.MarketConditionClassifierParams()

        if self.learning_logger_service:
            logger.info(f"MCC ({self.agent_config.agent_id}): LearningDataLoggerService: Available")
        else:
            logger.warning(f"MCC ({self.agent_config.agent_id}): LearningDataLoggerService: Not Available. Learning logs will be skipped.")

    async def _log_learning_event(
        self,
        event_type: str,
        data_snapshot: Dict,
        outcome: Optional[Dict] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        if self.learning_logger_service:
            entry = LearningLogEntry(
                primary_agent_id=self.agent_config.agent_id,
                source_service=self.__class__.__name__,
                event_type=event_type,
                data_snapshot=data_snapshot,
                outcome_or_result=outcome,
                notes=notes,
                tags=tags if tags else []
            )
            await self.learning_logger_service.log_entry(entry)

    def _calculate_sma(self, data: List[float], period: int) -> pd.Series:
        if not data or len(data) < period:
            return pd.Series([None] * len(data) if data else [], dtype=float) # Return Series of Nones
        series = pd.Series(data, dtype=float)
        # Ensure result has same index as input series for easier alignment if needed, though not strictly here.
        return series.rolling(window=period, min_periods=period).mean()

    def _calculate_adx_proxy(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> Optional[float]:
        # Simplified ADX placeholder: uses relative volatility / range std dev as proxy
        if len(closes) < period or period <= 1: return None

        df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
        # True Range calculation (simplified)
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        tr = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]

        # Directional Movement (very simplified proxy)
        # Compare current high/low with previous high/low
        delta_high = (pd.Series(highs) - pd.Series(highs).shift(1)).abs()
        delta_low = (pd.Series(lows) - pd.Series(lows).shift(1)).abs()
        # This is not DM+ or DM- but a simple measure of price expansion
        avg_expansion = (delta_high + delta_low).rolling(window=period).mean().iloc[-1] / 2

        if atr is None or pd.isna(atr) or atr == 0: return 0.0
        if avg_expansion is None or pd.isna(avg_expansion): return 0.0

        # ADX proxy: ratio of directional expansion to true range (volatility)
        # This is a conceptual proxy, NOT a real ADX.
        # A real ADX is much more involved (smoothed DM+/DM-, DX, then ADX).
        # For this placeholder, let's use a simple volatility-normalized range.
        max_h = pd.Series(highs[-period:]).max()
        min_l = pd.Series(lows[-period:]).min()
        price_range = max_h - min_l

        if atr == 0: adx_proxy_val = 50.0 if price_range > 0 else 0.0 # Arbitrary: if volatile but no ATR, still "trending"
        else: adx_proxy_val = (price_range / atr) * 25 # Scaled to be somewhat ADX-like (0-100 range)

        logger.debug(f"MCC ({self.agent_config.agent_id}): Simplified ADX proxy: {adx_proxy_val:.2f} (Range: {price_range:.2f}, ATR-like: {atr:.2f})")
        return round(adx_proxy_val, 2)


    def _calculate_bollinger_bands(self, data: List[float], period: int, stddev: float) -> Dict[str, Optional[float]]:
        if len(data) < period:
            return {"upper": None, "middle": None, "lower": None, "width": None}

        series = pd.Series(data, dtype=float)
        middle_series = series.rolling(window=period, min_periods=period).mean()
        std_dev_series = series.rolling(window=period, min_periods=period).std()

        if middle_series.empty or std_dev_series.empty:
             return {"upper": None, "middle": None, "lower": None, "width": None}

        middle = middle_series.iloc[-1]
        std_dev_val = std_dev_series.iloc[-1]

        if pd.isna(middle) or pd.isna(std_dev_val):
            return {"upper": None, "middle": middle if pd.notna(middle) else None, "lower": None, "width": None}

        upper = middle + (std_dev_val * stddev)
        lower = middle - (std_dev_val * stddev)
        width = ((upper - lower) / middle) if middle != 0 else 0.0 # Avoid division by zero
        return {"upper": upper, "middle": middle, "lower": lower, "width": width}

    async def analyze_symbol_and_publish_condition(self, symbol: str):
        params = self.params
        logger.info(f"MCC ({self.agent_config.agent_id}): Analyzing {symbol} with ADX p:{params.adx_period}, MA({params.ma_short_period},{params.ma_long_period}), BB({params.bbands_period},{params.bbands_stddev})")

        # Fetch enough data for longest lookback requirement of any indicator
        num_klines = max(params.adx_period, params.ma_long_period, params.bbands_period) + 50 # Generous buffer

        klines = await self.market_data_service.get_historical_klines(symbol, limit=num_klines)

        if len(klines) < max(params.ma_long_period, params.adx_period, params.bbands_period): # Basic check
            logger.warning(f"MCC ({self.agent_config.agent_id}): Not enough data for {symbol} for all indicators. Need at least {max(params.ma_long_period, params.adx_period, params.bbands_period)}, got {len(klines)}.")
            return

        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]

        adx_value = self._calculate_adx_proxy(highs, lows, closes, params.adx_period)

        ma_short_series = self._calculate_sma(closes, params.ma_short_period)
        ma_long_series = self._calculate_sma(closes, params.ma_long_period)

        ma_short_slope = 0.0
        # Need at least 2 non-NaN values from the SMA series to calculate slope
        ma_short_dropna = ma_short_series.dropna()
        if len(ma_short_dropna) >= 2:
            y_short = ma_short_dropna.values[-2:] # Last two available SMA values
            x_short = np.arange(len(y_short))
            ma_short_slope = np.polyfit(x_short, y_short, 1)[0]

        ma_short_current = ma_short_series.iloc[-1] if not ma_short_series.empty and pd.notna(ma_short_series.iloc[-1]) else None
        ma_long_current = ma_long_series.iloc[-1] if not ma_long_series.empty and pd.notna(ma_long_series.iloc[-1]) else None

        bbands = self._calculate_bollinger_bands(closes, params.bbands_period, params.bbands_stddev)
        bb_width = bbands.get("width")

        regime: Literal["trending_up", "trending_down", "ranging", "volatile", "undetermined"] = "undetermined"
        confidence = 0.5
        supporting_data: Dict[str, Any] = {
            "adx_proxy": round(adx_value,2) if adx_value is not None else None,
            "ma_short_slope": round(ma_short_slope, 5) if ma_short_slope is not None else None,
            "bb_width": round(bb_width,4) if bb_width is not None else None,
            "ma_short": round(ma_short_current,2) if ma_short_current is not None else None,
            "ma_long": round(ma_long_current,2) if ma_long_current is not None else None,
        }

        # Simplified Logic
        is_trending_by_adx = adx_value is not None and adx_value > params.adx_trend_threshold

        if ma_short_current is not None and ma_long_current is not None: # Ensure MAs are calculated
            if is_trending_by_adx:
                if ma_short_slope > params.ma_slope_threshold and ma_short_current > ma_long_current:
                    regime = "trending_up"; confidence = 0.7
                elif ma_short_slope < -params.ma_slope_threshold and ma_short_current < ma_long_current:
                    regime = "trending_down"; confidence = 0.7
                elif bb_width is not None and bb_width > params.bbands_width_volatility_threshold: # ADX trend but MAs not aligned -> volatile
                    regime = "volatile"; confidence = 0.65
                else: # ADX trend but MAs not aligned, not clearly volatile -> perhaps ranging within a trend
                    regime = "ranging"; confidence = 0.6
            else: # Not trending by ADX
                if bb_width is not None:
                    if bb_width < params.bbands_width_ranging_threshold:
                        regime = "ranging"; confidence = 0.7
                    elif bb_width > params.bbands_width_volatility_threshold:
                        regime = "volatile"; confidence = 0.6
                    else: # ADX low, BB width moderate
                        regime = "undetermined"; confidence = 0.55
                else: # No BB width, ADX low
                    regime = "undetermined"
        else: # MAs not available
            logger.warning(f"MCC ({self.agent_config.agent_id}): MAs not fully calculated for {symbol}. Regime undetermined.")
            regime = "undetermined"

        logger.info(f"MCC ({self.agent_config.agent_id}): {symbol} classified as '{regime}'. Confidence: {confidence:.2f}. Data: {supporting_data}")

        payload = MarketConditionEventPayload(
            symbol=symbol, regime=regime, confidence_score=confidence, supporting_data=supporting_data
        )

        await self._log_learning_event(
            event_type="MarketConditionClassified",
            data_snapshot=payload.model_dump(), # Log the payload being published
            notes=f"Market condition classified for {symbol}.",
            tags=["market_condition_classifier", regime]
        )

        event = Event(
            publisher_agent_id=self.agent_config.agent_id,
            message_type="MarketConditionEvent",
            payload=payload.model_dump()
        )
        await self.event_bus.publish(event)

