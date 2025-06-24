from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pandas as pd
from loguru import logger
import uuid

from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig
from python_ai_services.models.market_data_models import Kline
from python_ai_services.models.event_bus_models import Event, TradeSignalEventPayload, MarketInsightEventPayload
from python_ai_services.services.market_data_service import MarketDataService, MarketDataServiceError
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.services.learning_data_logger_service import LearningDataLoggerService
from python_ai_services.models.learning_models import LearningLogEntry

class SMACrossoverTechnicalServiceError(Exception):
    pass

class SMACrossoverTechnicalService:
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

        if not self.agent_config.strategy.sma_crossover_params:
            logger.warning(f"SMACrossoverService (agent: {self.agent_config.agent_id}): Missing sma_crossover_params. Using defaults.")
            self.params = AgentStrategyConfig.SMACrossoverParams()
        else:
            self.params = self.agent_config.strategy.sma_crossover_params

        logger.info(f"SMACrossoverTechnicalService initialized for agent {self.agent_config.agent_id}.")

    async def _log_learning_event(self, event_type: str, data_snapshot: Dict, outcome: Optional[Dict] = None, notes: Optional[str] = None):
        if self.learning_logger_service:
            entry = LearningLogEntry(
                primary_agent_id=self.agent_config.agent_id,
                source_service=self.__class__.__name__,
                event_type=event_type,
                data_snapshot=data_snapshot,
                outcome_or_result=outcome,
                notes=notes,
                tags=["sma_crossover", event_type.lower()]
            )
            await self.learning_logger_service.log_entry(entry)

    def _calculate_sma(self, series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window=window).mean()

    def _calculate_ema(self, series: pd.Series, window: int) -> pd.Series:
        return series.ewm(span=window, adjust=False).mean()

    async def analyze_symbol_and_generate_signal(self, symbol: str, interval: str = "1h", lookback_days: int = 60):
        agent_id_log = self.agent_config.agent_id # For cleaner log lines
        logger.info(f"SMACrossoverService (agent: {agent_id_log}): Starting analysis for {symbol}.")

        try:
            end_time = datetime.now(timezone.utc)
            # Ensure enough data for the longest MA plus a few prior periods for comparison
            required_data_points = self.params.long_window + 5
            # Estimate days needed based on interval (very rough, assumes 24/7 market)
            if "m" in interval: # minutes
                days_per_point = (int(interval.replace("m","")) / (60*24))
            elif "h" in interval: # hours
                days_per_point = int(interval.replace("h","")) / 24
            elif "d" in interval: # days
                days_per_point = int(interval.replace("d",""))
            else: # default to 1 day per point if interval is unknown format
                days_per_point = 1

            # Calculate lookback days needed for required_data_points
            # Add a buffer to ensure enough data points after potential gaps or non-trading days.
            calculated_lookback_days = int(required_data_points * days_per_point) + 15 # Buffer of 15 days
            final_lookback_days = max(lookback_days, calculated_lookback_days, self.params.long_window + 5) # Ensure at least long_window + 5 days

            start_time = end_time - timedelta(days=final_lookback_days)

            klines_pydantic = await self.market_data_service.get_historical_klines(
                symbol=symbol, interval=interval, start_time=start_time, end_time=end_time
            )

            if not klines_pydantic or len(klines_pydantic) < self.params.long_window:
                logger.warning(f"SMACrossover (agent: {agent_id_log}): Not enough kline data for {symbol} (need {self.params.long_window}, got {len(klines_pydantic)}).")
                await self._log_learning_event("NotEnoughData", {"symbol": symbol, "kline_count": len(klines_pydantic)})
                return

            klines_data = [{"timestamp": k.timestamp, "close": k.close} for k in klines_pydantic]
            df = pd.DataFrame(klines_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')

            calc_ma = self._calculate_sma if self.params.sma_type == "SMA" else self._calculate_ema
            df['short_ma'] = calc_ma(df['close'], self.params.short_window)
            df['long_ma'] = calc_ma(df['close'], self.params.long_window)

            df = df.dropna()
            if len(df) < 2:
                logger.info(f"SMACrossover (agent: {agent_id_log}): Not enough data points after MA for {symbol}.")
                await self._log_learning_event("NotEnoughDataAfterMA", {"symbol": symbol, "df_len": len(df)})
                return

            prev_short = df['short_ma'].iloc[-2]
            prev_long = df['long_ma'].iloc[-2]
            curr_short = df['short_ma'].iloc[-1]
            curr_long = df['long_ma'].iloc[-1]
            current_price = df['close'].iloc[-1]
            signal_action: Optional[Literal["buy", "sell"]] = None
            confidence = 0.6

            if prev_short <= prev_long and curr_short > curr_long:
                signal_action = "buy"
                logger.info(f"SMACrossover (agent: {agent_id_log}): BUY signal for {symbol}.")
            elif prev_short >= prev_long and curr_short < curr_long:
                signal_action = "sell"
                logger.info(f"SMACrossover (agent: {agent_id_log}): SELL signal for {symbol}.")

            if signal_action:
                event_payload = TradeSignalEventPayload(
                    agent_id=self.agent_config.agent_id, symbol=symbol, signal_type=signal_action,
                    price_at_signal=float(current_price), confidence_score=confidence,
                    strategy_name=self.agent_config.strategy.strategy_name or "SMACrossover",
                    details={
                        "short_ma_value": float(curr_short), "long_ma_value": float(curr_long),
                        "short_window": self.params.short_window, "long_window": self.params.long_window,
                        "sma_type": self.params.sma_type, "interval": interval,
                        "kline_timestamp": df.index[-1].isoformat()
                    }
                )
                await self.event_bus_service.publish(Event(
                    message_type="TradeSignalEvent", payload=event_payload.model_dump(),
                    publisher_agent_id=self.agent_config.agent_id, event_id=str(uuid.uuid4())
                ))
                await self._log_learning_event("TradeSignalPublished", event_payload.model_dump())
            else:
                logger.info(f"SMACrossover (agent: {agent_id_log}): No crossover signal for {symbol}.")
                await self._log_learning_event("NoSignal", {"symbol": symbol, "short_ma": curr_short, "long_ma": curr_long})

        except MarketDataServiceError as e:
            logger.error(f"SMACrossover (agent: {agent_id_log}): MarketDataServiceError for {symbol}: {e}", exc_info=True)
            await self._log_learning_event("MarketDataError", {"symbol": symbol, "error": str(e)})
        except Exception as e:
            logger.error(f"SMACrossover (agent: {agent_id_log}): Unexpected error for {symbol}: {e}", exc_info=True)
            await self._log_learning_event("UnexpectedAnalysisError", {"symbol": symbol, "error": str(e)})
