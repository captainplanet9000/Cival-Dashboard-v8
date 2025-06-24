from ..models.agent_models import AgentConfigOutput, AgentStrategyConfig
from ..models.event_bus_models import Event, TradeSignalEventPayload
from ..services.event_bus_service import EventBusService
from ..services.market_data_service import MarketDataService
from .learning_data_logger_service import LearningDataLoggerService # Added
from ..models.learning_models import LearningLogEntry # Added
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime, timezone

class DarvasBoxTechnicalService:
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

        if self.agent_config.strategy.darvas_params:
            self.params = self.agent_config.strategy.darvas_params
        else:
            logger.warning(f"DarvasBox ({self.agent_config.agent_id}): darvas_params not found. Using defaults.")
            self.params = AgentStrategyConfig.DarvasStrategyParams()

        if self.learning_logger_service:
            logger.info(f"DarvasBox ({self.agent_config.agent_id}): LearningDataLoggerService: Available")
        else:
            logger.warning(f"DarvasBox ({self.agent_config.agent_id}): LearningDataLoggerService: Not Available. Learning logs will be skipped.")

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

    async def analyze_symbol_and_generate_signal(self, symbol: str):
        logger.info(f"DarvasBox ({self.agent_config.agent_id}): Analyzing {symbol} with params: Lookback={self.params.lookback_period}, BoxMinRange%={self.params.box_range_min_percentage*100}%, SL%FromBoxBottom={self.params.stop_loss_percentage_from_box_bottom*100}%")

        # Need lookback_period for historical box + 1 current candle for breakout check
        klines_to_fetch = self.params.lookback_period + self.params.breakout_confirmation_periods

        klines = await self.market_data_service.get_historical_klines(
            symbol, limit=klines_to_fetch
        )

        if len(klines) < klines_to_fetch:
            logger.warning(f"DarvasBox ({self.agent_config.agent_id}): Not enough data for {symbol} (need {klines_to_fetch}, got {len(klines)}).")
            return

        # Current candle(s) for breakout confirmation
        # For breakout_confirmation_periods = 1, current_candle is klines[-1]
        # If breakout_confirmation_periods > 1, we'd need to check multiple recent candles.
        # Simplified: check only the latest candle against the box formed by prior candles.
        current_candle = klines[-1]
        # Historical klines used to determine the box
        historical_klines_for_box = klines[-(self.params.lookback_period + self.params.breakout_confirmation_periods) : -self.params.breakout_confirmation_periods]


        if not historical_klines_for_box: # Should be caught by len(klines) check earlier
            logger.warning(f"DarvasBox ({self.agent_config.agent_id}): No historical klines for box formation for {symbol} after slicing.")
            return

        # Simplified Darvas: Box top is the highest high of the lookback period.
        # Box bottom is the lowest low *after* the high that established the box top,
        # or more simply, the lowest low within the box formation period if that high is recent.
        # For this version: Box top = max high of historical_klines_for_box.
        # Box bottom = min low of historical_klines_for_box.

        box_top = max(k['high'] for k in historical_klines_for_box)
        box_bottom = min(k['low'] for k in historical_klines_for_box)

        current_price = current_candle['close'] # Using close of current candle for breakout signal

        logger.debug(f"DarvasBox ({self.agent_config.agent_id}): Symbol: {symbol}, Current Price: {current_price}, Box Top: {box_top}, Box Bottom: {box_bottom}")

        # Buy signal: Current price breaks (and closes, for this simplified version) above box_top
        # breakout_confirmation_periods=1 means we just check the last candle.
        # A more robust check might ensure price stays above for 'breakout_confirmation_periods' candles.
        if current_price > box_top:
            # Optional: check box_range_min_percentage
            if self.params.box_range_min_percentage > 0 and box_top > 0: # box_top > 0 to avoid division by zero
                box_range_percentage = (box_top - box_bottom) / box_top
                if box_range_percentage < self.params.box_range_min_percentage:
                    logger.info(f"DarvasBox ({self.agent_config.agent_id}): Box range {box_range_percentage*100:.2f}% for {symbol} is below minimum {self.params.box_range_min_percentage*100:.2f}%. Signal skipped.")
                    return

            stop_loss_price = box_bottom * (1 - self.params.stop_loss_percentage_from_box_bottom)

            signal_payload = TradeSignalEventPayload(
                symbol=symbol,
                action="buy",
                quantity=None, # Quantity decision typically by portfolio management based on risk
                price_target=current_price, # Signal to enter at current breakout price
                stop_loss=round(stop_loss_price, 2), # Example rounding, adapt to asset precision
                strategy_name=f"DarvasBox_L{self.params.lookback_period}",
                confidence=0.75
            )

            await self._log_learning_event(
                event_type="SignalGenerated",
                data_snapshot=signal_payload.model_dump(),
                notes=f"Darvas Box signal for {symbol}. Box: [{box_bottom} - {box_top}]",
                tags=["darvas_box", signal_payload.action]
            )

            event = Event(
                publisher_agent_id=self.agent_config.agent_id,
                message_type="TradeSignalEvent",
                payload=signal_payload.model_dump()
            )
            await self.event_bus.publish(event)
            logger.success(f"DarvasBox ({self.agent_config.agent_id}): Published BUY signal for {symbol} at {current_price}. SL: {stop_loss_price:.2f}. Box: [{box_bottom} - {box_top}]")
        else:
            logger.info(f"DarvasBox ({self.agent_config.agent_id}): No breakout signal for {symbol}. Current price {current_price} not above box top {box_top}.")
            await self._log_learning_event(
                event_type="SignalEvaluation",
                data_snapshot={"symbol": symbol, "current_price": current_price, "box_top": box_top, "box_bottom": box_bottom, "params": self.params.model_dump()},
                outcome={"signal_generated": False},
                notes=f"No Darvas Box breakout for {symbol}.",
                tags=["darvas_box", "no_signal"]
            )
