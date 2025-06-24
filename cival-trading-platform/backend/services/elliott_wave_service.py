from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta # Added timedelta
from decimal import Decimal
from loguru import logger

from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig # ElliottWaveParams is nested here
from python_ai_services.models.market_data_models import Kline
from python_ai_services.models.event_bus_models import Event, TradeSignalEventPayload, MarketInsightEventPayload
from python_ai_services.services.market_data_service import MarketDataService, MarketDataServiceError
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.services.learning_data_logger_service import LearningDataLoggerService
from python_ai_services.models.learning_models import LearningLogEntry
import uuid # For event IDs

class ElliottWaveTechnicalServiceError(Exception):
    pass

class ElliottWaveTechnicalService:
    def __init__(
        self,
        agent_config: AgentConfigOutput,
        market_data_service: MarketDataService,
        event_bus_service: EventBusService,
        learning_logger_service: Optional[LearningDataLoggerService] = None,
    ):
        self.agent_config = agent_config
        self.market_data_service = market_data_service
        self.event_bus_service = event_bus_service
        self.learning_logger_service = learning_logger_service

        if not self.agent_config.strategy.elliott_wave_params:
            logger.warning(f"ElliottWaveTechService (agent: {self.agent_config.agent_id}): Missing elliott_wave_params. Using defaults.")
            self.params = AgentStrategyConfig.ElliottWaveParams() # Use defaults
        else:
            self.params = self.agent_config.strategy.elliott_wave_params

        logger.info(f"ElliottWaveTechnicalService initialized for agent {self.agent_config.agent_id}.")

    async def _log_learning_event(self, event_type: str, data_snapshot: Dict, outcome: Optional[Dict] = None, notes: Optional[str] = None):
        if self.learning_logger_service:
            entry = LearningLogEntry(
                primary_agent_id=self.agent_config.agent_id,
                source_service=self.__class__.__name__,
                event_type=event_type,
                data_snapshot=data_snapshot,
                outcome_or_result=outcome,
                notes=notes,
                tags=["elliott_wave", event_type.lower()]
            )
            await self.learning_logger_service.log_entry(entry)

    async def _find_significant_moves(self, klines: List[Kline], min_candles: int, min_change_pct: float) -> List[Dict[str, Any]]:
        if len(klines) < min_candles:
            return []
        significant_moves = []
        i = 0
        while i < len(klines):
            start_index = i
            start_price = Decimal(str(klines[i].close))
            # Upward move
            j = i + 1
            move_found_in_direction = False
            while j < len(klines):
                current_price = Decimal(str(klines[j].close))
                if start_price == Decimal(0): price_change_pct = Decimal(0) if current_price == Decimal(0) else Decimal(100)
                else: price_change_pct = ((current_price - start_price) / start_price) * 100

                if price_change_pct >= min_change_pct and (j - start_index + 1) >= min_candles:
                    significant_moves.append({"start_idx": start_index, "end_idx": j, "type": "up", "start_price": start_price, "end_price": current_price, "length_candles": j - start_index + 1})
                    i = j
                    move_found_in_direction = True
                    break
                if current_price < start_price and (j - start_index + 1) >= min_candles // 2: # Allow some reversal if part of a complex W1
                    i = j
                    break
                j += 1
            if move_found_in_direction: continue # Restart search from end of found move
            if j == len(klines) and not move_found_in_direction : i = j

            # Downward move
            start_price = Decimal(str(klines[i].close)) if i < len(klines) else Decimal(0) # Ensure i is valid
            if i >= len(klines): break # End of klines
            j = i + 1
            move_found_in_direction = False
            while j < len(klines):
                current_price = Decimal(str(klines[j].close))
                if start_price == Decimal(0): price_change_pct = Decimal(0) if current_price == Decimal(0) else Decimal(100)
                else: price_change_pct = ((start_price - current_price) / start_price) * 100

                if price_change_pct >= min_change_pct and (j - start_index + 1) >= min_candles:
                    significant_moves.append({"start_idx": start_index, "end_idx": j, "type": "down", "start_price": start_price, "end_price": current_price, "length_candles": j - start_index + 1})
                    i = j
                    move_found_in_direction = True
                    break
                if current_price > start_price and (j - start_index + 1) >= min_candles // 2:
                    i = j
                    break
                j += 1
            if move_found_in_direction: continue
            if j == len(klines) and not move_found_in_direction : i = j

            if start_index == i : i+=1
        return significant_moves

    async def analyze_symbol(self, symbol: str, klines: List[Kline]):
        agent_id_log = self.agent_config.agent_id
        if not klines or len(klines) < self.params.impulse_wave_min_candles * 2:
            logger.debug(f"EW (agent: {agent_id_log}): Not enough kline data for {symbol}.")
            return

        await self._log_learning_event("AnalysisStarted", {"symbol": symbol, "kline_count": len(klines), "params": self.params.model_dump()})
        potential_wave1s = await self._find_significant_moves(klines, self.params.impulse_wave_min_candles, self.params.impulse_wave_min_total_change_pct)

        if not potential_wave1s:
            logger.info(f"EW (agent: {agent_id_log}): No significant initial moves (potential Wave 1s) found for {symbol}.")
            await self._log_learning_event("NoWave1Candidates", {"symbol": symbol})
            return

        last_potential_w1 = potential_wave1s[-1]
        w1_start_price = last_potential_w1["start_price"]
        w1_end_price = last_potential_w1["end_price"]
        w1_end_idx = last_potential_w1["end_idx"]
        w1_type = last_potential_w1["type"]

        wave1_details = {
            "type": w1_type, "start_price": float(w1_start_price), "end_price": float(w1_end_price),
            "start_idx": last_potential_w1["start_idx"], "end_idx": w1_end_idx,
            "start_time": klines[last_potential_w1["start_idx"]].timestamp.isoformat(),
            "end_time": klines[w1_end_idx].timestamp.isoformat()
        }
        logger.info(f"EW (agent: {agent_id_log}): Identified potential Wave 1 for {symbol}.")

        if w1_end_idx < len(klines) - 1:
            klines_after_w1 = klines[w1_end_idx + 1:]
            if not klines_after_w1: return # No data after W1 for W2 analysis

            wave1_length = abs(w1_end_price - w1_start_price)
            if wave1_length == Decimal(0): return # Avoid division by zero if wave1 is flat

            for fib_level in self.params.correction_fib_levels:
                target_correction_price = Decimal(0)
                met_condition = False
                if w1_type == "up":
                    target_correction_price = w1_end_price - (wave1_length * Decimal(str(fib_level)))
                    min_price_in_correction = min([Decimal(str(k.low)) for k in klines_after_w1[:10]]) if klines_after_w1 else w1_end_price
                    if min_price_in_correction <= target_correction_price: met_condition = True

                elif w1_type == "down":
                    target_correction_price = w1_end_price + (wave1_length * Decimal(str(fib_level)))
                    max_price_in_correction = max([Decimal(str(k.high)) for k in klines_after_w1[:10]]) if klines_after_w1 else w1_end_price
                    if max_price_in_correction >= target_correction_price: met_condition = True

                if met_condition:
                    insight_msg = f"Potential Wave 2 correction for {symbol} after Wave 1 ({w1_type}) ending at {float(w1_end_price):.2f}. Price retraced near {fib_level*100:.1f}% level."
                    logger.info(f"EW (agent: {agent_id_log}): {insight_msg}")
                    event_payload = MarketInsightEventPayload(
                        agent_id=self.agent_config.agent_id, symbol=symbol,
                        insight_type="ElliottWave_Potential_W2_Correction", content=insight_msg,
                        confidence_score=0.4,
                        metadata={"wave1": wave1_details, "fib_level": fib_level, "target_correction_price": float(target_correction_price)}
                    )
                    await self.event_bus_service.publish(Event(message_type="MarketInsightEvent", payload=event_payload.model_dump(), publisher_agent_id=self.agent_config.agent_id, event_id=str(uuid.uuid4())))
                    await self._log_learning_event("PotentialWave2Insight", event_payload.model_dump(), notes=f"Fib level {fib_level} considered.")
                    break
        else:
            logger.info(f"EW (agent: {agent_id_log}): Potential Wave 1 for {symbol} is the most recent pattern.")
            await self._log_learning_event("Wave1IsLastPattern", {"symbol": symbol, "wave1_details": wave1_details})

    async def run_analysis_for_symbol(self, symbol: str, interval: str = "1h", lookback_days: int = 90):
        agent_id_log = self.agent_config.agent_id
        logger.info(f"ElliottWaveTechService (agent: {agent_id_log}): Starting analysis for {symbol}.")
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=lookback_days)

            klines = await self.market_data_service.get_historical_klines(
                symbol=symbol, interval=interval, start_time=start_time, end_time=end_time
            )
            if klines:
                await self.analyze_symbol(symbol, klines)
            else:
                logger.warning(f"EW (agent: {agent_id_log}): No kline data for {symbol}.")
                await self._log_learning_event("NoDataReceived", {"symbol": symbol})
        except MarketDataServiceError as e:
            logger.error(f"EW (agent: {agent_id_log}): MarketDataServiceError for {symbol}: {e}", exc_info=True)
            await self._log_learning_event("MarketDataError", {"symbol": symbol, "error": str(e)})
        except Exception as e:
            logger.error(f"EW (agent: {agent_id_log}): Unexpected error for {symbol}: {e}", exc_info=True)
            await self._log_learning_event("UnexpectedAnalysisError", {"symbol": symbol, "error": str(e)})
