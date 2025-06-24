from ..models.agent_models import AgentConfigOutput, AgentStrategyConfig # RenkoParams is nested in AgentStrategyConfig
from ..models.event_bus_models import Event, TradeSignalEventPayload
from ..models.learning_models import LearningLogEntry
from ..services.event_bus_service import EventBusService
from ..services.market_data_service import MarketDataService
from ..services.learning_data_logger_service import LearningDataLoggerService
from typing import List, Dict, Any, Optional, Literal, Tuple # Added Literal and Tuple
import pandas as pd
import numpy as np # For NaN checks
from loguru import logger
from datetime import datetime, timezone

class RenkoTechnicalService:
    def __init__(
        self,
        agent_config: AgentConfigOutput,
        event_bus: EventBusService,
        market_data_service: MarketDataService,
        learning_logger: Optional[LearningDataLoggerService] = None # Kept learning_logger
    ):
        self.agent_config = agent_config
        self.event_bus = event_bus
        self.market_data_service = market_data_service
        self.learning_logger = learning_logger

        if self.agent_config.strategy.renko_params:
            self.params = self.agent_config.strategy.renko_params
        else:
            logger.warning(f"RenkoSvc ({self.agent_config.agent_id}): renko_params not found. Using defaults.")
            # Ensure RenkoParams class is accessed correctly from AgentStrategyConfig
            self.params = AgentStrategyConfig.RenkoParams()

        if self.learning_logger: # Kept
            logger.info(f"RenkoSvc ({self.agent_config.agent_id}): LearningDataLoggerService: Available")
        else:
            logger.warning(f"RenkoSvc ({self.agent_config.agent_id}): LearningDataLoggerService: Not Available.")

    async def _log_learning_event(self, event_type: str, data: Dict, outcome: Optional[Dict] = None, notes: Optional[str] = None, tags: Optional[List[str]] = None): # Kept
        if self.learning_logger:
            entry = LearningLogEntry(
                primary_agent_id=self.agent_config.agent_id,
                source_service=self.__class__.__name__,
                event_type=event_type,
                data_snapshot=data,
                outcome_or_result=outcome,
                notes=notes,
                tags=tags if tags else []
            )
            await self.learning_logger.log_entry(entry)

    async def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> Optional[float]: # As per prompt
        if not highs or not lows or not closes:
            logger.warning(f"Renko ({self.agent_config.agent_id}): ATR calculation received empty high/low/close lists.")
            return None
        if len(closes) < period + 1:
            logger.debug(f"Renko ({self.agent_config.agent_id}): Not enough data ({len(closes)} points) for ATR period {period + 1}.")
            return None

        df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
        df['tr1'] = abs(df['high'] - df['low'])
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df[['tr1', 'tr2', 'tr3']] = df[['tr1', 'tr2', 'tr3']].fillna(0) # Fill NaN before max

        df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        atr_series = df['true_range'].rolling(window=period).mean() # Using SMA as per prompt

        if atr_series.empty or pd.isna(atr_series.iloc[-1]):
            logger.warning(f"Renko ({self.agent_config.agent_id}): ATR calculation resulted in NaN or empty series.")
            return None

        atr_value = atr_series.iloc[-1]
        return atr_value if pd.notna(atr_value) and atr_value > 1e-9 else None # Epsilon check

    def _calculate_renko_bricks( # Simplified version from prompt
        self,
        timestamps: List[int],
        prices: List[float],
        brick_size: float
    ) -> List[Dict[str, Any]]:
        if not prices or brick_size <= 1e-9:
            logger.warning(f"Renko ({self.agent_config.agent_id}): Cannot calculate Renko. No prices or invalid brick size ({brick_size}).")
            return []

        bricks: List[Dict[str, Any]] = []
        if not prices: return []

        last_brick_close = prices[0]

        for i in range(1, len(prices)):
            price = prices[i]
            timestamp_ms = timestamps[i]

            price_diff = price - last_brick_close

            if abs(price_diff) >= brick_size:
                num_bricks = int(abs(price_diff) / brick_size)
                brick_type = "up" if price_diff > 0 else "down"

                for _ in range(num_bricks):
                    brick_open = last_brick_close
                    if brick_type == "up":
                        brick_close = brick_open + brick_size
                    else: # down
                        brick_close = brick_open - brick_size

                    bricks.append({
                        "type": brick_type,
                        "open": round(brick_open, 5),
                        "close": round(brick_close, 5),
                        "timestamp": timestamp_ms
                    })
                    last_brick_close = brick_close
        return bricks

    async def analyze_symbol_and_generate_signal(self, symbol: str):
        logger.info(f"RenkoSvc ({self.agent_config.agent_id}): Analyzing {symbol} with params: {self.params.model_dump_json()}") # Use RenkoParams from init

        # Using updated field names from Pydantic model
        atr_calc_relevant_period = self.params.atr_period if self.params.brick_size_mode == 'atr' else 20 # Default if fixed but need ATR for something else
        num_klines_fetch = max(200, atr_calc_relevant_period + 100)

        klines_raw = await self.market_data_service.get_historical_klines(symbol, limit=num_klines_fetch)

        if not klines_raw or len(klines_raw) < 2: # Min 2 for price change
            logger.warning(f"RenkoSvc ({self.agent_config.agent_id}): Not enough data for {symbol} (got {len(klines_raw)}).")
            await self._log_learning_event("SignalEvaluation", {"symbol": symbol, "reason": "Insufficient kline data"}, outcome={"signal_generated": False})
            return

        klines = []
        for k_raw in klines_raw:
            try:
                klines.append({
                    'timestamp': int(k_raw['timestamp']),
                    'open': float(k_raw['open']), 'high': float(k_raw['high']),
                    'low': float(k_raw['low']), 'close': float(k_raw['close']),
                    'volume': float(k_raw['volume'])
                })
            except (TypeError, ValueError, KeyError) as e:
                logger.warning(f"RenkoSvc ({self.agent_config.agent_id}): Skipping kline for {symbol} due to parsing error: {e}. Raw: {k_raw}")
                continue

        if len(klines) < max(2, self.params.atr_period + 1 if self.params.brick_size_mode == 'atr' else 2): # Min data for ATR or fixed
            logger.warning(f"RenkoSvc ({self.agent_config.agent_id}): Not enough valid kline data for {symbol} after parsing.")
            await self._log_learning_event("SignalEvaluation", {"symbol": symbol, "reason": "Insufficient valid kline data after parsing"}, outcome={"signal_generated": False})
            return

        closes = [k['close'] for k in klines]
        timestamps_ms = [k['timestamp'] for k in klines]

        brick_s: Optional[float] = None
        # Using self.params with updated field names
        if self.params.brick_size_mode == "fixed":
            if self.params.brick_size_value_fixed is None or self.params.brick_size_value_fixed <= 1e-9:
                logger.error(f"RenkoSvc ({self.agent_config.agent_id}): Fixed brick size not configured or invalid for {symbol}.")
                await self._log_learning_event("ProcessingError", {"symbol": symbol, "reason": "Invalid fixed brick size"}, outcome={"signal_generated": False})
                return
            brick_s = self.params.brick_size_value_fixed
        elif self.params.brick_size_mode == "atr":
            highs = [k['high'] for k in klines]
            lows = [k['low'] for k in klines]
            atr_val = await self._calculate_atr(highs, lows, closes, self.params.atr_period)
            if atr_val is None or atr_val <= 1e-9:
                logger.warning(f"RenkoSvc ({self.agent_config.agent_id}): Valid ATR for {symbol} is {atr_val}. Cannot determine brick size.")
                await self._log_learning_event("ProcessingError", {"symbol": symbol, "reason": f"Invalid ATR value {atr_val}"}, outcome={"signal_generated": False})
                return
            brick_s = atr_val

        if brick_s is None:
            logger.error(f"RenkoSvc ({self.agent_config.agent_id}): Brick size could not be determined for {symbol}.")
            await self._log_learning_event("ProcessingError", {"symbol": symbol, "reason": "Brick size determination failed"}, outcome={"signal_generated": False})
            return

        logger.debug(f"RenkoSvc ({self.agent_config.agent_id}): Using brick size {brick_s:.5f} for {symbol}")
        renko_bricks = self._calculate_renko_bricks(timestamps_ms, closes, brick_s) # Pass timestamps_ms

        # Using self.params.signal_confirmation_bricks
        if len(renko_bricks) < self.params.signal_confirmation_bricks:
            logger.debug(f"RenkoSvc ({self.agent_config.agent_id}): Not enough Renko bricks ({len(renko_bricks)}) for signal on {symbol} (need {self.params.signal_confirmation_bricks}).")
            await self._log_learning_event("SignalEvaluation", {"symbol": symbol, "brick_size": brick_s, "bricks_generated": len(renko_bricks), "required_bricks": self.params.signal_confirmation_bricks}, outcome={"signal_generated": False}, notes="Not enough bricks for signal.")
            return

        last_n_bricks = renko_bricks[-self.params.signal_confirmation_bricks:]
        action: Optional[Literal["buy", "sell"]] = None

        first_brick_type_in_sequence = last_n_bricks[0]["type"]
        all_same_type_in_sequence = all(b["type"] == first_brick_type_in_sequence for b in last_n_bricks)

        if all_same_type_in_sequence:
            brick_before_sequence_index = len(renko_bricks) - self.params.signal_confirmation_bricks - 1
            if brick_before_sequence_index >= 0:
                if renko_bricks[brick_before_sequence_index]["type"] != first_brick_type_in_sequence:
                    action = "buy" if first_brick_type_in_sequence == "up" else "sell"
            else:
                action = "buy" if first_brick_type_in_sequence == "up" else "sell"

        log_data_snapshot = {"symbol": symbol, "brick_size": brick_s, "last_n_bricks_for_signal": last_n_bricks, "params": self.params.model_dump()}

        if action:
            entry_price = closes[-1] # Current market price for entry
            sl_price: Optional[float] = None

            # SL logic using stop_loss_bricks_away from the first brick of the signal sequence
            if self.params.stop_loss_bricks_away and self.params.stop_loss_bricks_away > 0:
                first_signal_brick = renko_bricks[-self.params.signal_confirmation_bricks]
                if action == "buy": # Up bricks, SL is below
                    sl_price = first_signal_brick["open"] # As per prompt's simple SL logic
                else: # Sell signal (down bricks), SL is above
                    sl_price = first_signal_brick["open"] # As per prompt's simple SL logic
                sl_price = round(sl_price, 5) if sl_price is not None else None

            signal_payload = TradeSignalEventPayload(
                symbol=symbol, action=action, quantity=None,
                price_target=round(entry_price, 5),
                stop_loss=sl_price,
                strategy_name=f"Renko_B{brick_s:.4f}_C{self.params.signal_confirmation_bricks}", # Use updated param name
                confidence=0.70 # Example confidence
            )
            event_data = Event(
                publisher_agent_id=self.agent_config.agent_id,
                message_type="TradeSignalEvent", payload=signal_payload.model_dump()
            )
            await self.event_bus.publish(event_data)
            await self._log_learning_event("SignalGenerated", data=log_data_snapshot, outcome=signal_payload.model_dump(), tags=["renko", action])
            logger.success(f"RenkoSvc ({self.agent_config.agent_id}): Published {action.upper()} signal for {symbol} at {entry_price:.4f}. SL: {sl_price if sl_price is not None else 'N/A'}")
        else:
            await self._log_learning_event("SignalEvaluation", data=log_data_snapshot, outcome={"signal_generated": False}, notes="No Renko signal based on consecutive bricks.", tags=["renko", "no_signal"])
            logger.info(f"RenkoSvc ({self.agent_config.agent_id}): No signal for {symbol} based on last {self.params.signal_confirmation_bricks} bricks.")

