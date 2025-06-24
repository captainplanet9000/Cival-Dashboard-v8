from ..models.agent_models import AgentConfigOutput, AgentStrategyConfig
from ..models.event_bus_models import Event, TradeSignalEventPayload
from ..services.event_bus_service import EventBusService
from ..services.market_data_service import MarketDataService
from .learning_data_logger_service import LearningDataLoggerService # Added
from ..models.learning_models import LearningLogEntry # Added
from typing import List, Dict, Any, Optional
import pandas as pd
from loguru import logger
from datetime import datetime, timezone

class WilliamsAlligatorTechnicalService:
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

        if self.agent_config.strategy.williams_alligator_params:
            self.params = self.agent_config.strategy.williams_alligator_params
        else:
            logger.warning(f"WA ({self.agent_config.agent_id}): williams_alligator_params not found. Using defaults.")
            self.params = AgentStrategyConfig.WilliamsAlligatorParams()

        if self.learning_logger_service:
            logger.info(f"WA ({self.agent_config.agent_id}): LearningDataLoggerService: Available")
        else:
            logger.warning(f"WA ({self.agent_config.agent_id}): LearningDataLoggerService: Not Available. Learning logs will be skipped.")

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

    def _calculate_sma(self, data: List[float], period: int) -> List[Optional[float]]:
        if not data or len(data) < period: # Added check for empty data
            # Return list of Nones matching data length if data is too short, or empty list if data is empty
            return [None] * len(data) if data else []
        series = pd.Series(data, dtype=float) # Ensure dtype is float for pd operations
        sma = series.rolling(window=period, min_periods=period).mean().tolist() # min_periods=period ensures full period for SMA
        # The result of rolling().mean() will have NaNs at the beginning.
        # Pandas tolist() will convert these NaNs to None if the dtype was object, or keep as float NaN.
        # We want Optional[float], so replacing float NaN with None.
        return [val if pd.notna(val) else None for val in sma]


    async def analyze_symbol_and_generate_signal(self, symbol: str):
        logger.info(f"WilliamsAlligator ({self.agent_config.agent_id}): Analyzing {symbol} with params: Jaw({self.params.jaw_period},{self.params.jaw_shift}), Teeth({self.params.teeth_period},{self.params.teeth_shift}), Lips({self.params.lips_period},{self.params.lips_shift})")

        # Determine max period and max shift to fetch enough data
        max_period = max(self.params.jaw_period, self.params.teeth_period, self.params.lips_period)
        max_shift = max(self.params.jaw_shift, self.params.teeth_shift, self.params.lips_shift)
        # Need at least max_period data points for the SMA calculation,
        # then max_shift additional points to be able to look back for the shifted value,
        # and then 2 more points (current and previous) for crossover detection.
        required_data_points = max_period + max_shift + 2

        klines = await self.market_data_service.get_historical_klines(
            symbol, limit=required_data_points
        )

        if len(klines) < required_data_points:
            logger.warning(f"WA ({self.agent_config.agent_id}): Not enough kline data for {symbol} (need {required_data_points}, got {len(klines)}).")
            return

        closes = [k['close'] for k in klines]
        current_price = closes[-1] # Latest close price

        # Calculate SMAs on the 'closes' series
        jaw_sma_unshifted = self._calculate_sma(closes, self.params.jaw_period)
        teeth_sma_unshifted = self._calculate_sma(closes, self.params.teeth_period)
        lips_sma_unshifted = self._calculate_sma(closes, self.params.lips_period)

        # Conceptual shift: access elements from [series_length - 1 - shift] for current, and [series_length - 2 - shift] for previous.
        # Ensure indices are valid after conceptual shift.
        # Current values (latest available shifted)
        idx_jaw_current = len(jaw_sma_unshifted) - 1 - self.params.jaw_shift
        idx_teeth_current = len(teeth_sma_unshifted) - 1 - self.params.teeth_shift
        idx_lips_current = len(lips_sma_unshifted) - 1 - self.params.lips_shift

        # Previous values (one period before current shifted)
        idx_jaw_prev = idx_jaw_current - 1
        idx_teeth_prev = idx_teeth_current - 1
        idx_lips_prev = idx_lips_current - 1

        # Check if all indices are valid (>=0)
        if not (idx_jaw_prev >=0 and idx_teeth_prev >=0 and idx_lips_prev >=0):
            logger.warning(f"WA ({self.agent_config.agent_id}): Not enough data points to get previous shifted SMA values for {symbol}.")
            return

        jaw_current = jaw_sma_unshifted[idx_jaw_current]
        teeth_current = teeth_sma_unshifted[idx_teeth_current]
        lips_current = lips_sma_unshifted[idx_lips_current]

        jaw_prev = jaw_sma_unshifted[idx_jaw_prev]
        teeth_prev = teeth_sma_unshifted[idx_teeth_prev]
        lips_prev = lips_sma_unshifted[idx_lips_prev]

        if None in [jaw_current, teeth_current, lips_current, jaw_prev, teeth_prev, lips_prev]:
            logger.debug(f"WA ({self.agent_config.agent_id}): SMA values not fully calculated (contains None) for {symbol}. Required: {required_data_points}, JawSMA len: {len(jaw_sma_unshifted)}")
            return

        logger.debug(f"WA ({self.agent_config.agent_id}) {symbol}: Price:{current_price:.2f} | Lips:{lips_current:.2f}(Prev:{lips_prev:.2f}) Teeth:{teeth_current:.2f}(Prev:{teeth_prev:.2f}) Jaw:{jaw_current:.2f}(Prev:{jaw_prev:.2f})")

        action = None
        # Bullish Crossover and Alignment: Lips > Teeth > Jaw
        is_lips_crossed_teeth_up = (lips_prev <= teeth_prev) and (lips_current > teeth_current) # type: ignore
        is_teeth_crossed_jaw_up = (teeth_prev <= jaw_prev) and (teeth_current > jaw_current) # type: ignore
        is_lines_bullish_ordered = lips_current > teeth_current and teeth_current > jaw_current # type: ignore

        # More robust: Check if lines are ordered AND a recent crossover occurred for lips over teeth
        if is_lines_bullish_ordered and is_lips_crossed_teeth_up and current_price > max(lips_current, teeth_current, jaw_current): # type: ignore
            action = "buy"
            logger.info(f"WA ({self.agent_config.agent_id}): BUY signal for {symbol} at {current_price:.2f}. Lines bullishly ordered and lips crossed teeth up.")

        # Bearish Crossover and Alignment: Lips < Teeth < Jaw
        is_lips_crossed_teeth_down = (lips_prev >= teeth_prev) and (lips_current < teeth_current) # type: ignore
        is_teeth_crossed_jaw_down = (teeth_prev >= jaw_prev) and (teeth_current < jaw_current) # type: ignore
        is_lines_bearish_ordered = lips_current < teeth_current and teeth_current < jaw_current # type: ignore

        if is_lines_bearish_ordered and is_lips_crossed_teeth_down and current_price < min(lips_current, teeth_current, jaw_current): # type: ignore
            action = "sell"
            logger.info(f"WA ({self.agent_config.agent_id}): SELL signal for {symbol} at {current_price:.2f}. Lines bearishly ordered and lips crossed teeth down.")

        if action:
            sl_price = None
            if action == "buy" and jaw_current is not None:
                sl_price = jaw_current * (1 - 0.02) # Example: 2% below Jaw as SL
            elif action == "sell" and jaw_current is not None:
                sl_price = jaw_current * (1 + 0.02) # Example: 2% above Jaw as SL

            signal_payload = TradeSignalEventPayload(
                symbol=symbol,
                action=action,
                quantity=None,
                price_target=round(current_price, 2), # Use current price as target for market entry
                stop_loss=round(sl_price, 2) if sl_price is not None else None,
                strategy_name=f"WilliamsAlligator_J{self.params.jaw_period}T{self.params.teeth_period}L{self.params.lips_period}",
                confidence=0.65
            )

            await self._log_learning_event(
                event_type="SignalGenerated",
                data_snapshot=signal_payload.model_dump(),
                notes=f"Williams Alligator signal for {symbol}. Lines: Lips({lips_current:.2f}), Teeth({teeth_current:.2f}), Jaw({jaw_current:.2f})",
                tags=["williams_alligator", signal_payload.action]
            )

            event = Event(
                publisher_agent_id=self.agent_config.agent_id,
                message_type="TradeSignalEvent",
                payload=signal_payload.model_dump()
            )
            await self.event_bus.publish(event)
            logger.success(f"WA ({self.agent_config.agent_id}): Published {action.upper()} signal for {symbol} at {current_price:.2f}. SL: {sl_price:.2f if sl_price else 'N/A'}")
        else:
            logger.info(f"WA ({self.agent_config.agent_id}): No actionable signal for {symbol} based on Williams Alligator conditions.")
            current_values_snapshot = {
                "symbol": symbol, "current_price": current_price,
                "lips_current": lips_current, "lips_prev": lips_prev,
                "teeth_current": teeth_current, "teeth_prev": teeth_prev,
                "jaw_current": jaw_current, "jaw_prev": jaw_prev,
                "params": self.params.model_dump()
            }
            # Only log if all values were available for a decision to be made (i.e., not None)
            if None not in [lips_current, teeth_current, jaw_current, lips_prev, teeth_prev, jaw_prev]:
                await self._log_learning_event(
                    event_type="SignalEvaluation",
                    data_snapshot=current_values_snapshot,
                    outcome={"signal_generated": False},
                    notes=f"No Williams Alligator signal for {symbol}.",
                    tags=["williams_alligator", "no_signal"]
                )

