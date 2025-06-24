from ..services.agent_management_service import AgentManagementService
from ..services.trading_coordinator import TradingCoordinator
from ..services.hyperliquid_execution_service import HyperliquidExecutionService
from ..services.simulated_trade_executor import SimulatedTradeExecutor
from ..models.agent_models import AgentConfigOutput
from ..models.api_models import TradingAnalysisCrewRequest
from ..utils.google_sdk_bridge import GoogleSDKBridge
from ..utils.a2a_protocol import A2AProtocol
from .trade_history_service import TradeHistoryService
from .risk_manager_service import RiskManagerService
from .market_data_service import MarketDataService
from .event_bus_service import EventBusService
from .darvas_box_service import DarvasBoxTechnicalService
from .williams_alligator_service import WilliamsAlligatorTechnicalService
from .market_condition_classifier_service import MarketConditionClassifierService
from .portfolio_optimizer_service import PortfolioOptimizerService
from .portfolio_optimizer_service import PortfolioOptimizerService
from .news_analysis_service import NewsAnalysisService
# Use the new factories
from ..core.factories import get_hyperliquid_execution_service_instance, get_dex_execution_service_instance
from typing import Optional, Any, Dict, List
from .dex_execution_service import DEXExecutionService
from .learning_data_logger_service import LearningDataLoggerService # Added
from .portfolio_snapshot_service import PortfolioSnapshotService # Added
from .trading_data_service import TradingDataService # Ensure TradingDataService is imported for portfolio_summary
from loguru import logger
import asyncio
from unittest.mock import MagicMock

class AgentOrchestratorService:
    def __init__(
        self,
        agent_management_service: AgentManagementService,
        trade_history_service: TradeHistoryService,
        risk_manager_service: RiskManagerService,
        market_data_service: MarketDataService, # Added
        event_bus_service: EventBusService, # Added, ensure type is correct
        google_bridge: Optional[GoogleSDKBridge] = None,
        a2a_protocol: Optional[A2AProtocol] = None,
        simulated_trade_executor: Optional[SimulatedTradeExecutor] = None,
        learning_logger_service: Optional[LearningDataLoggerService] = None, # Added
        portfolio_snapshot_service: Optional[PortfolioSnapshotService] = None, # Added
        trading_data_service: Optional[TradingDataService] = None # Added for portfolio_summary
    ):
        self.agent_management_service = agent_management_service
        self.trade_history_service = trade_history_service
        self.risk_manager_service = risk_manager_service
        self.market_data_service = market_data_service
        self.event_bus_service = event_bus_service
        self.learning_logger_service = learning_logger_service
        self.portfolio_snapshot_service = portfolio_snapshot_service # Store it
        self.trading_data_service = trading_data_service # Store it
        self.google_bridge = google_bridge if google_bridge else MagicMock(spec=GoogleSDKBridge)
        self.a2a_protocol = a2a_protocol if a2a_protocol else MagicMock(spec=A2AProtocol)
        self.simulated_trade_executor = simulated_trade_executor if simulated_trade_executor else MagicMock(spec=SimulatedTradeExecutor)

        logger.info("AgentOrchestratorService initialized.")
        if self.learning_logger_service: logger.info("LearningDataLoggerService: Available.")
        else: logger.warning("LearningDataLoggerService: Not Available. Learning logs may be skipped by some agents.")
        if self.portfolio_snapshot_service: logger.info("PortfolioSnapshotService: Available.")
        else: logger.warning("PortfolioSnapshotService: Not Available. Portfolio snapshots will not be recorded by orchestrator.")
        if self.trading_data_service: logger.info("TradingDataService: Available for portfolio summaries.")
        else: logger.warning("TradingDataService: Not Available. Portfolio summaries for snapshots will not be fetched by orchestrator.")


    async def _get_trading_coordinator_for_agent(self, agent_config: AgentConfigOutput) -> Optional[TradingCoordinator]:
        logger.debug(f"Orchestrator: Getting TradingCoordinator for agent: {agent_config.agent_id} ({agent_config.name}), provider: {agent_config.execution_provider}")
        hles_instance: Optional[HyperliquidExecutionService] = None
        dex_instance: Optional[DEXExecutionService] = None # Renamed for clarity and consistency

        if agent_config.execution_provider == "hyperliquid":
            hles_instance = get_hyperliquid_execution_service_instance(agent_config)
            if not hles_instance:
                logger.error(f"Orchestrator: Failed to get HyperliquidExecutionService for agent {agent_config.agent_id}.")
                return None
        elif agent_config.execution_provider == "dex":
            dex_instance = get_dex_execution_service_instance(agent_config) # Use the correct factory
            if not dex_instance:
                logger.error(f"Orchestrator: Failed to get DEXExecutionService for agent {agent_config.agent_id}.")
                return None

        if agent_config.execution_provider == "paper" and not self.simulated_trade_executor:
             logger.error(f"Orchestrator: Agent {agent_config.agent_id} configured for paper trading, but SimulatedTradeExecutor not available.")
             return None

        try:
            coordinator = TradingCoordinator(
                agent_id=agent_config.agent_id,
                agent_management_service=self.agent_management_service,
                risk_manager_service=self.risk_manager_service,
                google_bridge=self.google_bridge,
                a2a_protocol=self.a2a_protocol,
                simulated_trade_executor=self.simulated_trade_executor,
                hyperliquid_execution_service=hles_instance,
                dex_execution_service=dex_instance, # Pass the created dex_instance
                trade_history_service=self.trade_history_service,
                event_bus_service=self.event_bus_service
            )
            await coordinator.set_trade_execution_mode(agent_config.execution_provider) # type: ignore
            await coordinator.setup_event_subscriptions()
            logger.debug(f"Orchestrator: TradingCoordinator instantiated and subscriptions set up for agent {agent_config.agent_id} in '{agent_config.execution_provider}' mode.")
            return coordinator
        except Exception as e:
            logger.error(f"Orchestrator: Failed to instantiate or set up TradingCoordinator for agent {agent_config.agent_id}: {e}", exc_info=True)
            return None

    async def run_single_agent_cycle(self, agent_id: str):
        logger.info(f"Starting single agent cycle for agent_id: {agent_id}")
        agent_config = await self.agent_management_service.get_agent(agent_id)

        if not agent_config:
            logger.warning(f"Agent {agent_id} not found by AgentManagementService. Skipping cycle.")
            return
        if not agent_config.is_active:
            logger.info(f"Agent {agent_id} ({agent_config.name}) is not active. Skipping cycle.")
            return

        logger.info(f"Running cycle for active agent: {agent_config.name} (ID: {agent_id}), Type: {agent_config.agent_type}")

        if agent_config.agent_type == "DarvasBoxTechnicalAgent":
            if not self.market_data_service or not self.event_bus_service:
                logger.error(f"MarketDataService or EventBusService not available for DarvasBoxTechnicalAgent {agent_id}. Skipping cycle.")
                await self.agent_management_service.update_agent_heartbeat(agent_id)
                return

            darvas_service = DarvasBoxTechnicalService(
                agent_config=agent_config,
                event_bus=self.event_bus_service,
                market_data_service=self.market_data_service,
                learning_logger_service=self.learning_logger_service # Pass logger
            )
            if not agent_config.strategy.watched_symbols:
                logger.warning(f"DarvasBoxAgent {agent_id} ({agent_config.name}) has no watched_symbols configured. No analysis will be run.")
            else:
                for symbol in agent_config.strategy.watched_symbols:
                    try:
                        await darvas_service.analyze_symbol_and_generate_signal(symbol)
                    except Exception as e:
                        logger.error(f"Error during DarvasBox analysis for agent {agent_id}, symbol {symbol}: {e}", exc_info=True)

            await self.agent_management_service.update_agent_heartbeat(agent_id)
            logger.info(f"DarvasBoxTechnicalAgent cycle finished for agent_id: {agent_id}")
            return

        elif agent_config.agent_type == "WilliamsAlligatorTechnicalAgent":
            if not self.market_data_service or not self.event_bus_service:
                logger.error(f"MarketDataService or EventBusService not available for WilliamsAlligatorTechnicalAgent {agent_id}. Skipping cycle.")
                await self.agent_management_service.update_agent_heartbeat(agent_id)
                return

            wa_service = WilliamsAlligatorTechnicalService(
                agent_config=agent_config,
                event_bus=self.event_bus_service,
                market_data_service=self.market_data_service,
                learning_logger_service=self.learning_logger_service # Pass logger
            )
            if not agent_config.strategy.watched_symbols:
                logger.warning(f"WilliamsAlligatorAgent {agent_id} ({agent_config.name}) has no watched_symbols configured. No analysis will be run.")
            else:
                for symbol in agent_config.strategy.watched_symbols:
                    try:
                        await wa_service.analyze_symbol_and_generate_signal(symbol)
                    except Exception as e:
                        logger.error(f"Error during WilliamsAlligator analysis for agent {agent_id}, symbol {symbol}: {e}", exc_info=True)

            await self.agent_management_service.update_agent_heartbeat(agent_id)
            logger.info(f"WilliamsAlligatorTechnicalAgent cycle finished for agent_id: {agent_id}")
            return

        elif agent_config.agent_type == "MarketConditionClassifierAgent":
            if not self.market_data_service or not self.event_bus_service:
                logger.error(f"Orchestrator: MarketDataService or EventBusService not configured. Cannot run MarketConditionClassifierAgent {agent_id}.")
                await self.agent_management_service.update_agent_heartbeat(agent_id) # Still update heartbeat
                return

            mcc_service = MarketConditionClassifierService(
                agent_config=agent_config,
                event_bus=self.event_bus_service,
                market_data_service=self.market_data_service,
                learning_logger_service=self.learning_logger_service # Pass logger
            )
            if not agent_config.strategy.watched_symbols:
                logger.warning(f"MarketConditionClassifierAgent {agent_id} ({agent_config.name}) has no watched_symbols configured. No analysis will be run.")
            else:
                for symbol in agent_config.strategy.watched_symbols:
                    try:
                        await mcc_service.analyze_symbol_and_publish_condition(symbol)
                    except Exception as e:
                        logger.error(f"Error during MarketConditionClassifier analysis for agent {agent_id}, symbol {symbol}: {e}", exc_info=True)

            await self.agent_management_service.update_agent_heartbeat(agent_id)
            logger.info(f"MarketConditionClassifierAgent cycle finished for agent_id: {agent_id}")
            return

        elif agent_config.agent_type == "PortfolioOptimizerAgent":
            # This agent is primarily event-driven via its EventBus subscriptions.
            # The orchestrator's role for this agent type is mainly to keep its heartbeat updated.
            # Actual logic (`on_market_condition_event`) is triggered by EventBus.
            # Subscription setup is assumed to be handled when the agent/service is activated/initialized elsewhere.
            # (e.g., in main.py or if AgentManagementService.start_agent was enhanced)

            # For this subtask, we'll ensure the orchestrator can recognize it and heartbeat it.
            # If it had periodic review tasks not triggered by events, they could be called here.
            # Example:
            # po_service = PortfolioOptimizerService(
            #     agent_config=agent_config,
            #     agent_management_service=self.agent_management_service,
            #     event_bus=self.event_bus_service
            # )
            # await po_service.perform_periodic_review() # If such a method existed

            logger.debug(f"PortfolioOptimizerAgent {agent_id} cycle: Is event-driven. Updating heartbeat.")
            await self.agent_management_service.update_agent_heartbeat(agent_id)
            logger.info(f"PortfolioOptimizerAgent cycle finished for agent_id: {agent_id}")
            return

        elif agent_config.agent_type == "NewsAnalysisAgent":
            if not self.event_bus_service: # MarketDataService not directly used by NewsAnalysisService itself if it only fetches external RSS
                logger.error(f"Orchestrator: EventBusService not configured. Cannot run NewsAnalysisAgent {agent_id}.")
                await self.agent_management_service.update_agent_heartbeat(agent_id)
                return

            news_service = NewsAnalysisService(
                agent_config=agent_config,
                event_bus=self.event_bus_service,
                learning_logger_service=self.learning_logger_service # Pass logger
            )
            try:
                # This agent type might not iterate symbols, but rather fetches all its configured feeds.
                # If it needs to iterate symbols (e.g. to filter news or focus analysis), that logic is in NewsAnalysisService.
                await news_service.fetch_and_analyze_feeds()
            except Exception as e:
                logger.error(f"Error during NewsAnalysisAgent cycle for agent {agent_id}: {e}", exc_info=True)

            await self.agent_management_service.update_agent_heartbeat(agent_id)
            logger.info(f"NewsAnalysisAgent cycle finished for agent_id: {agent_id}")
            return


        elif agent_config.agent_type == "RenkoTechnicalAgent":
            if not all([self.market_data_service, self.event_bus_service]):
                logger.error(f"Orchestrator: Missing critical services for RenkoTechnicalAgent {agent_id}.")
                await self.agent_management_service.update_agent_heartbeat(agent_id)
                return
            from .renko_technical_service import RenkoTechnicalService # Local import

            renko_service = RenkoTechnicalService(
                agent_config=agent_config,
                event_bus=self.event_bus_service,
                market_data_service=self.market_data_service,
                learning_logger=self.learning_logger_service # Pass logger
            )
            if agent_config.strategy.watched_symbols:
                for symbol in agent_config.strategy.watched_symbols:
                    try:
                        await renko_service.analyze_symbol_and_generate_signal(symbol)
                    except Exception as e:
                        logger.error(f"Error during Renko analysis for agent {agent_id}, symbol {symbol}: {e}", exc_info=True)
            else:
                logger.warning(f"RenkoTechnicalAgent {agent_id} has no watched_symbols configured.")
            await self.agent_management_service.update_agent_heartbeat(agent_id)
            logger.info(f"RenkoTechnicalAgent cycle finished for agent_id: {agent_id}")
            return

        elif agent_config.agent_type == "HeikinAshiTechnicalAgent":
            if not all([self.market_data_service, self.event_bus_service]):
                logger.error(f"Orchestrator: Missing critical services for HeikinAshiTechnicalAgent {agent_id}.")
                await self.agent_management_service.update_agent_heartbeat(agent_id)
                return
            from .heikin_ashi_service import HeikinAshiTechnicalService # Local import

            heikin_ashi_service = HeikinAshiTechnicalService(
                agent_config=agent_config,
                event_bus=self.event_bus_service,
                market_data_service=self.market_data_service,
                # learning_logger=self.learning_logger_service # Pass logger if service accepts
            )
            if agent_config.strategy.watched_symbols:
                for symbol in agent_config.strategy.watched_symbols:
                    try:
                        await heikin_ashi_service.analyze_symbol_and_generate_signal(symbol)
                    except Exception as e:
                        logger.error(f"Error during Heikin Ashi analysis for agent {agent_id}, symbol {symbol}: {e}", exc_info=True)
            else:
                logger.warning(f"HeikinAshiTechnicalAgent {agent_id} has no watched_symbols configured.")
            await self.agent_management_service.update_agent_heartbeat(agent_id)
            logger.info(f"HeikinAshiTechnicalAgent cycle finished for agent_id: {agent_id}")
            return

        # Default handling for other agent types (e.g., "GenericAgent" or those using TradingCoordinator)
        # This block should be the last one for agent_type checks.
        else: # Fallback for GenericAgent or any other type that uses TradingCoordinator
            trading_coordinator = await self._get_trading_coordinator_for_agent(agent_config)
            if not trading_coordinator:
                logger.error(f"Failed to get TradingCoordinator for agent {agent_id} (type: {agent_config.agent_type}). Skipping analysis cycle.")
            else:
                symbols_to_watch = agent_config.strategy.watched_symbols
                if not symbols_to_watch:
                    logger.info(f"Agent {agent_id} ({agent_config.name}, type: {agent_config.agent_type}) has no watched_symbols defined. No analysis will be run by TC.")
                else:
                    for symbol in symbols_to_watch:
                        event_description = agent_config.strategy.default_market_event_description.format(symbol=symbol)
                        additional_context = agent_config.strategy.default_additional_context

                        crew_request = TradingAnalysisCrewRequest(
                            symbol=symbol,
                            market_event_description=event_description,
                            additional_context=additional_context,
                            user_id=agent_id
                        )
                        logger.info(f"Initiating TradingCoordinator-based analysis for agent {agent_id} on symbol {symbol}.")
                        try:
                            analysis_result = await trading_coordinator.analyze_trading_opportunity(crew_request)
                            logger.info(f"TradingCoordinator analysis completed for agent {agent_id}, symbol {symbol}. Result snippet: {str(analysis_result)[:200]}")
                        except Exception as e:
                            logger.error(f"Error during TradingCoordinator analysis for agent {agent_id}, symbol {symbol}: {e}", exc_info=True)

        # Record portfolio snapshot for agents that might have traded or whose portfolio value could change
        # Exclude agents that only provide analysis or manage others, unless their own state is tracked.
        non_trading_agent_types = ["NewsAnalysisAgent", "PortfolioOptimizerAgent", "MarketConditionClassifierAgent"]
        if agent_config.agent_type not in non_trading_agent_types:
            if self.trading_data_service and self.portfolio_snapshot_service:
                try:
                    logger.debug(f"Orchestrator: Attempting to fetch portfolio summary for snapshot - Agent {agent_id}")
                    # Ensure trading_data_service is available on self if not passed to __init__ or if it's optional
                    if not self.trading_data_service:
                         logger.error("Orchestrator: TradingDataService not available, cannot fetch portfolio summary for snapshot.")
                    else:
                        portfolio_summary = await self.trading_data_service.get_portfolio_summary(agent_id)
                        if portfolio_summary and isinstance(portfolio_summary.account_value_usd, float):
                            logger.debug(f"Orchestrator: Recording snapshot for agent {agent_id}, equity: {portfolio_summary.account_value_usd}")
                            await self.portfolio_snapshot_service.record_snapshot(
                                agent_id=agent_id,
                                total_equity_usd=portfolio_summary.account_value_usd
                                # Timestamp will be auto-generated by snapshot service
                            )
                        elif portfolio_summary:
                            logger.warning(f"Orchestrator: account_value_usd is not a float for agent {agent_id}, cannot record snapshot. Value: {portfolio_summary.account_value_usd}")
                        else:
                            logger.warning(f"Orchestrator: Portfolio summary not available for agent {agent_id}, cannot record snapshot.")
                except Exception as e_snap:
                    logger.error(f"Orchestrator: Error during portfolio snapshot for agent {agent_id}: {e_snap}", exc_info=True)
            else:
                logger.warning(f"Orchestrator: TradingDataService or PortfolioSnapshotService not available for agent {agent_id}. Skipping portfolio snapshot.")

        await self.agent_management_service.update_agent_heartbeat(agent_id)
        logger.info(f"Agent cycle finished for agent_id: {agent_id}")


    async def run_all_active_agents_once(self):
        logger.info("Starting run_all_active_agents_once cycle.")
        all_agents = await self.agent_management_service.get_agents() # Use updated name
        active_agents = [agent for agent in all_agents if agent.is_active]

        if not active_agents:
            logger.info("No active agents found to run.")
            return

        logger.info(f"Found {len(active_agents)} active agents to run.")

        tasks = [self.run_single_agent_cycle(agent.agent_id) for agent in active_agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for agent, result in zip(active_agents, results):
            if isinstance(result, Exception):
                logger.error(f"Exception during agent cycle for {agent.agent_id} ({agent.name}): {result}", exc_info=result)
            else:
                logger.info(f"Successfully completed agent cycle for {agent.agent_id} ({agent.name}).")
        logger.info("Finished run_all_active_agents_once cycle.")

