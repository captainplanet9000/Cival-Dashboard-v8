import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from python_ai_services.services.agent_orchestrator_service import AgentOrchestratorService
from python_ai_services.services.agent_management_service import AgentManagementService
from python_ai_services.services.trading_coordinator import TradingCoordinator
from python_ai_services.services.hyperliquid_execution_service import HyperliquidExecutionService
from python_ai_services.services.dex_execution_service import DEXExecutionService # Added
from python_ai_services.services.simulated_trade_executor import SimulatedTradeExecutor
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig
from python_ai_services.models.api_models import TradingAnalysisCrewRequest
from python_ai_services.utils.google_sdk_bridge import GoogleSDKBridge
from python_ai_services.utils.a2a_protocol import A2AProtocol
from python_ai_services.services.trade_history_service import TradeHistoryService
from python_ai_services.services.risk_manager_service import RiskManagerService
from python_ai_services.services.market_data_service import MarketDataService
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.services.trading_data_service import TradingDataService # Added
from python_ai_services.services.portfolio_snapshot_service import PortfolioSnapshotService # Added
from python_ai_services.models.dashboard_models import PortfolioSummary # Added for mocking
from typing import Optional, List, Dict, Any


@pytest_asyncio.fixture
def mock_agent_service() -> AgentManagementService:
    return AsyncMock(spec=AgentManagementService)

@pytest_asyncio.fixture
def mock_google_bridge() -> GoogleSDKBridge:
    return MagicMock(spec=GoogleSDKBridge)

@pytest_asyncio.fixture
def mock_a2a_protocol() -> A2AProtocol:
    return MagicMock(spec=A2AProtocol)

@pytest_asyncio.fixture
def mock_simulated_trade_executor() -> SimulatedTradeExecutor:
    return MagicMock(spec=SimulatedTradeExecutor)

@pytest_asyncio.fixture
def mock_trade_history_service() -> TradeHistoryService:
    return AsyncMock(spec=TradeHistoryService)

@pytest_asyncio.fixture
def mock_risk_manager_service() -> RiskManagerService:
    return AsyncMock(spec=RiskManagerService)

@pytest_asyncio.fixture
def mock_event_bus_service() -> EventBusService:
    return AsyncMock(spec=EventBusService)

@pytest_asyncio.fixture
def mock_market_data_service() -> MarketDataService:
    return AsyncMock(spec=MarketDataService)

@pytest_asyncio.fixture # Added
def mock_trading_data_service() -> TradingDataService:
    return AsyncMock(spec=TradingDataService)

@pytest_asyncio.fixture # Added
def mock_portfolio_snapshot_service() -> PortfolioSnapshotService:
    return AsyncMock(spec=PortfolioSnapshotService)

@pytest_asyncio.fixture
def orchestrator_service(
    mock_agent_service: AgentManagementService,
    mock_google_bridge: GoogleSDKBridge,
    mock_a2a_protocol: A2AProtocol,
    mock_simulated_trade_executor: SimulatedTradeExecutor,
    mock_trade_history_service: TradeHistoryService,
    mock_risk_manager_service: RiskManagerService,
    mock_event_bus_service: EventBusService,
    mock_market_data_service: MarketDataService,
    mock_trading_data_service: TradingDataService, # Added
    mock_portfolio_snapshot_service: PortfolioSnapshotService # Added
) -> AgentOrchestratorService:
    return AgentOrchestratorService(
        agent_management_service=mock_agent_service,
        trade_history_service=mock_trade_history_service,
        risk_manager_service=mock_risk_manager_service,
        market_data_service=mock_market_data_service,
        event_bus_service=mock_event_bus_service,
        google_bridge=mock_google_bridge,
        a2a_protocol=mock_a2a_protocol,
        simulated_trade_executor=mock_simulated_trade_executor,
        # learning_logger_service is already part of the service's __init__ from a previous step,
        # so it should be added here if not already present from that step. Assuming it is.
        # learning_logger_service=AsyncMock(spec=LearningDataLoggerService),
        trading_data_service=mock_trading_data_service, # Pass it
        portfolio_snapshot_service=mock_portfolio_snapshot_service # Pass it
    )

# Updated Helper to create sample AgentConfigOutput
def create_sample_agent_config(
    agent_id: str,
    is_active: bool = True,
    provider: str = "paper",
    symbols: Optional[List[str]] = None,
    agent_type_override: Optional[str] = None,
    dex_config_override: Optional[Dict[str, Any]] = None
) -> AgentConfigOutput:
    if symbols is None:
        symbols = ["BTC/USD", "ETH/USD"]

    hl_config = None
    if provider == "hyperliquid":
        hl_config = {
            "wallet_address": f"0xWallet{agent_id}",
            "private_key_env_var_name": f"PRIV_KEY_{agent_id.upper()}",
            "network_mode": "testnet"
        }

    dex_conf = None
    if provider == "dex":
        dex_conf = dex_config_override if dex_config_override else {
            "wallet_address": "0xDexWallet", "private_key_env_var_name": "DEX_PK_VAR",
            "rpc_url_env_var_name": "RPC_URL_VAR", "dex_router_address": "0xDexRouter"
        }

    strategy = AgentStrategyConfig(
        strategy_name="test_strat",
        parameters={},
        watched_symbols=symbols,
        default_market_event_description="Market event for {symbol}",
        default_additional_context={"source": "orchestrator"}
    )

    agent_type_to_use = agent_type_override if agent_type_override else "GenericAgent"
    if agent_type_to_use == "DarvasBoxTechnicalAgent":
        strategy.darvas_params = AgentStrategyConfig.DarvasStrategyParams()
    elif agent_type_to_use == "WilliamsAlligatorTechnicalAgent":
        strategy.williams_alligator_params = AgentStrategyConfig.WilliamsAlligatorParams()
    elif agent_type_to_use == "MarketConditionClassifierAgent":
        strategy.market_condition_classifier_params = AgentStrategyConfig.MarketConditionClassifierParams()
    elif agent_type_to_use == "PortfolioOptimizerAgent":
        strategy.portfolio_optimizer_params = AgentStrategyConfig.PortfolioOptimizerParams(rules=[])
    elif agent_type_to_use == "NewsAnalysisAgent":
        strategy.news_analysis_params = AgentStrategyConfig.NewsAnalysisParams()

    return AgentConfigOutput(
        agent_id=agent_id, name=f"Agent {agent_id}", is_active=is_active,
        agent_type=agent_type_to_use, strategy=strategy,
        risk_config=AgentRiskConfig(max_capital_allocation_usd=1000, risk_per_trade_percentage=0.01),
        execution_provider=provider, #type: ignore
        hyperliquid_config=hl_config,
        dex_config=dex_conf
    )

# --- Tests for _get_trading_coordinator_for_agent ---
@pytest.mark.asyncio
async def test_get_trading_coordinator_paper_agent(orchestrator_service: AgentOrchestratorService, mock_simulated_trade_executor: MagicMock):
    agent_config = create_sample_agent_config("paper_agent", provider="paper")
    with patch('python_ai_services.services.agent_orchestrator_service.TradingCoordinator') as MockTradingCoordinator:
        mock_tc_instance = AsyncMock(spec=TradingCoordinator)
        mock_tc_instance.set_trade_execution_mode = AsyncMock()
        mock_tc_instance.setup_event_subscriptions = AsyncMock()
        MockTradingCoordinator.return_value = mock_tc_instance
        coordinator = await orchestrator_service._get_trading_coordinator_for_agent(agent_config)
        assert coordinator is not None
        MockTradingCoordinator.assert_called_once_with(
            agent_id=agent_config.agent_id,
            agent_management_service=orchestrator_service.agent_management_service,
            risk_manager_service=orchestrator_service.risk_manager_service,
            google_bridge=orchestrator_service.google_bridge,
            a2a_protocol=orchestrator_service.a2a_protocol,
            simulated_trade_executor=mock_simulated_trade_executor,
            hyperliquid_execution_service=None,
            dex_execution_service=None, # Ensure DEX service is None here
            trade_history_service=orchestrator_service.trade_history_service,
            event_bus_service=orchestrator_service.event_bus_service
        )
        mock_tc_instance.set_trade_execution_mode.assert_called_once_with("paper")
        mock_tc_instance.setup_event_subscriptions.assert_called_once()


@pytest.mark.asyncio
@patch('python_ai_services.services.agent_orchestrator_service.get_hyperliquid_execution_service_instance')
async def test_get_trading_coordinator_hyperliquid_agent_success(
    mock_get_hles_instance: MagicMock, orchestrator_service: AgentOrchestratorService
):
    agent_config = create_sample_agent_config("hl_agent", provider="hyperliquid")
    mock_hles_instance = MagicMock(spec=HyperliquidExecutionService)
    mock_get_hles_instance.return_value = mock_hles_instance
    with patch('python_ai_services.services.agent_orchestrator_service.TradingCoordinator') as MockTradingCoordinator:
        mock_tc_instance = AsyncMock(spec=TradingCoordinator)
        mock_tc_instance.set_trade_execution_mode = AsyncMock()
        mock_tc_instance.setup_event_subscriptions = AsyncMock()
        MockTradingCoordinator.return_value = mock_tc_instance
        coordinator = await orchestrator_service._get_trading_coordinator_for_agent(agent_config)
        assert coordinator is not None
        mock_get_hles_instance.assert_called_once_with(agent_config)
        MockTradingCoordinator.assert_called_once_with(
            agent_id=agent_config.agent_id,
            agent_management_service=orchestrator_service.agent_management_service,
            risk_manager_service=orchestrator_service.risk_manager_service,
            google_bridge=orchestrator_service.google_bridge,
            a2a_protocol=orchestrator_service.a2a_protocol,
            simulated_trade_executor=orchestrator_service.simulated_trade_executor,
            hyperliquid_execution_service=mock_hles_instance,
            dex_execution_service=None,
            trade_history_service=orchestrator_service.trade_history_service,
            event_bus_service=orchestrator_service.event_bus_service
        )
        mock_tc_instance.set_trade_execution_mode.assert_called_once_with("hyperliquid")
        mock_tc_instance.setup_event_subscriptions.assert_called_once()

@patch('python_ai_services.services.agent_orchestrator_service.get_hyperliquid_execution_service_instance')
async def test_get_trading_coordinator_hyperliquid_factory_returns_none(
    mock_get_hles_instance: MagicMock, orchestrator_service: AgentOrchestratorService
):
    mock_get_hles_instance.return_value = None
    agent_config = create_sample_agent_config("hl_agent_factory_fail", provider="hyperliquid")
    coordinator = await orchestrator_service._get_trading_coordinator_for_agent(agent_config)
    assert coordinator is None
    mock_get_hles_instance.assert_called_once_with(agent_config)

@patch('python_ai_services.services.agent_orchestrator_service.get_dex_execution_service_instance')
async def test_get_trading_coordinator_dex_agent_success(
    mock_get_dex_instance: MagicMock, orchestrator_service: AgentOrchestratorService
):
    agent_config = create_sample_agent_config("dex_agent_1", provider="dex")
    mock_dex_instance = MagicMock(spec=DEXExecutionService)
    mock_get_dex_instance.return_value = mock_dex_instance
    with patch('python_ai_services.services.agent_orchestrator_service.TradingCoordinator') as MockTradingCoordinator:
        mock_tc_instance = AsyncMock(spec=TradingCoordinator)
        mock_tc_instance.set_trade_execution_mode = AsyncMock()
        mock_tc_instance.setup_event_subscriptions = AsyncMock()
        MockTradingCoordinator.return_value = mock_tc_instance
        coordinator = await orchestrator_service._get_trading_coordinator_for_agent(agent_config)
        assert coordinator is not None
        mock_get_dex_instance.assert_called_once_with(agent_config)
        MockTradingCoordinator.assert_called_once_with(
            agent_id=agent_config.agent_id,
            agent_management_service=orchestrator_service.agent_management_service,
            risk_manager_service=orchestrator_service.risk_manager_service,
            google_bridge=orchestrator_service.google_bridge,
            a2a_protocol=orchestrator_service.a2a_protocol,
            simulated_trade_executor=orchestrator_service.simulated_trade_executor,
            hyperliquid_execution_service=None,
            dex_execution_service=mock_dex_instance,
            trade_history_service=orchestrator_service.trade_history_service,
            event_bus_service=orchestrator_service.event_bus_service
        )
        mock_tc_instance.set_trade_execution_mode.assert_called_once_with("dex")
        mock_tc_instance.setup_event_subscriptions.assert_called_once()

# --- Tests for run_single_agent_cycle ---
@pytest.mark.asyncio
async def test_run_single_agent_cycle_agent_not_found(orchestrator_service: AgentOrchestratorService, mock_agent_service: MagicMock):
    mock_agent_service.get_agent = AsyncMock(return_value=None)
    await orchestrator_service.run_single_agent_cycle("unknown_agent")
    mock_agent_service.get_agent.assert_called_once_with("unknown_agent")
    mock_agent_service.update_agent_heartbeat.assert_not_called()

@pytest.mark.asyncio
async def test_run_single_agent_cycle_agent_not_active(orchestrator_service: AgentOrchestratorService, mock_agent_service: MagicMock):
    agent_id = "inactive_agent"
    agent_config = create_sample_agent_config(agent_id, is_active=False)
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)
    await orchestrator_service.run_single_agent_cycle(agent_id)
    mock_agent_service.update_agent_heartbeat.assert_not_called()

@pytest.mark.asyncio
async def test_run_single_agent_cycle_tc_setup_fails(orchestrator_service: AgentOrchestratorService, mock_agent_service: MagicMock):
    agent_id = "agent_tc_fail"
    agent_config = create_sample_agent_config(agent_id, provider="hyperliquid")
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)
    with patch('python_ai_services.services.agent_orchestrator_service.get_hyperliquid_execution_service_instance', return_value=None) as mock_hl_factory_call:
        await orchestrator_service.run_single_agent_cycle(agent_id)
    if agent_config.execution_provider == "hyperliquid": # Ensure factory was called for HL agent
        mock_hl_factory_call.assert_called_once_with(agent_config)
    mock_agent_service.update_agent_heartbeat.assert_called_once_with(agent_id)


@pytest.mark.asyncio
async def test_run_single_agent_cycle_generic_agent_no_watched_symbols(orchestrator_service: AgentOrchestratorService, mock_agent_service: MagicMock):
    agent_id = "generic_agent_no_symbols"
    agent_config = create_sample_agent_config(agent_id, symbols=[], agent_type_override="GenericAgent")
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)
    mock_tc = AsyncMock(spec=TradingCoordinator)
    mock_tc.analyze_trading_opportunity = AsyncMock()
    orchestrator_service._get_trading_coordinator_for_agent = AsyncMock(return_value=mock_tc)
    await orchestrator_service.run_single_agent_cycle(agent_id)
    mock_tc.analyze_trading_opportunity.assert_not_called()
    mock_agent_service.update_agent_heartbeat.assert_called_once_with(agent_id)

@pytest.mark.asyncio
async def test_run_single_agent_cycle_generic_agent_success_with_symbols(orchestrator_service: AgentOrchestratorService, mock_agent_service: MagicMock):
    agent_id = "generic_agent_with_symbols"
    symbols = ["BTC/USD", "ETH/USD"]
    agent_config = create_sample_agent_config(agent_id, symbols=symbols, agent_type_override="GenericAgent")
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)
    mock_tc = AsyncMock(spec=TradingCoordinator)
    mock_tc.analyze_trading_opportunity = AsyncMock(return_value={"decision": "buy"})
    orchestrator_service._get_trading_coordinator_for_agent = AsyncMock(return_value=mock_tc)

    # Mock portfolio summary for snapshot recording
    mock_portfolio_summary = PortfolioSummary(
        agent_id=agent_id, timestamp=datetime.now(timezone.utc),
        account_value_usd=10000.0, total_pnl_usd=100.0, open_positions=[]
    )
    orchestrator_service.trading_data_service.get_portfolio_summary = AsyncMock(return_value=mock_portfolio_summary)
    orchestrator_service.portfolio_snapshot_service.record_snapshot = AsyncMock()

    await orchestrator_service.run_single_agent_cycle(agent_id)

    assert mock_tc.analyze_trading_opportunity.call_count == len(symbols)
    first_call_args = mock_tc.analyze_trading_opportunity.call_args_list[0][0][0]
    assert isinstance(first_call_args, TradingAnalysisCrewRequest)
    assert first_call_args.symbol == symbols[0]
    mock_agent_service.update_agent_heartbeat.assert_called_once_with(agent_id)
    # Verify snapshot recording for GenericAgent (trading agent)
    orchestrator_service.trading_data_service.get_portfolio_summary.assert_called_once_with(agent_id)
    orchestrator_service.portfolio_snapshot_service.record_snapshot.assert_called_once_with(
        agent_id=agent_id, total_equity_usd=10000.0
    )

@pytest.mark.asyncio
@patch('python_ai_services.services.agent_orchestrator_service.DarvasBoxTechnicalService')
@patch('python_ai_services.services.agent_orchestrator_service.WilliamsAlligatorTechnicalService')
@patch('python_ai_services.services.agent_orchestrator_service.MarketConditionClassifierService')
@patch('python_ai_services.services.agent_orchestrator_service.NewsAnalysisService')
@patch('python_ai_services.services.agent_orchestrator_service.RenkoTechnicalService')
@patch('python_ai_services.services.agent_orchestrator_service.HeikinAshiTechnicalService') # Added HeikinAshi
@patch('python_ai_services.services.agent_orchestrator_service.PortfolioOptimizerService')
async def test_run_single_agent_cycle_specialized_agents_and_snapshot(
    MockPortfolioOptimizer: MagicMock,
    MockHeikinAshiService: MagicMock, # Added HeikinAshi
    MockRenkoService: MagicMock,
    MockNewsService: MagicMock,
    MockMCCService: MagicMock,
    MockWATService: MagicMock,
    MockDarvasService: MagicMock,
    orchestrator_service: AgentOrchestratorService,
    mock_agent_service: MagicMock,
    mock_market_data_service: MagicMock,
    mock_event_bus_service: MagicMock
):
    agent_types_and_mocks = {
        "DarvasBoxTechnicalAgent": MockDarvasService,
        "WilliamsAlligatorTechnicalAgent": MockWATService,
        "MarketConditionClassifierAgent": MockMCCService, # Non-trading
        "NewsAnalysisAgent": MockNewsService,             # Non-trading
        "RenkoTechnicalAgent": MockRenkoService,
        "HeikinAshiTechnicalAgent": MockHeikinAshiService, # Added HeikinAshi
        "PortfolioOptimizerAgent": MockPortfolioOptimizer # Non-trading
    }

    non_trading_agent_types = ["NewsAnalysisAgent", "PortfolioOptimizerAgent", "MarketConditionClassifierAgent"]

    for agent_type, MockService in agent_types_and_mocks.items():
        agent_id = f"{agent_type}_test_id_snap"
        symbols = ["TEST/SYM1", "TEST/SYM2"]
        agent_config = create_sample_agent_config(agent_id, symbols=symbols, agent_type_override=agent_type)
        if agent_type == "RenkoTechnicalAgent":
            agent_config.strategy.renko_params = AgentStrategyConfig.RenkoParams()
        elif agent_type == "HeikinAshiTechnicalAgent": # Added HeikinAshi
            agent_config.strategy.heikin_ashi_params = AgentStrategyConfig.HeikinAshiParams()

        mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

        mock_service_instance = AsyncMock()
        # Setup specific method mocks for each service type
        if agent_type == "NewsAnalysisAgent":
            mock_service_instance.fetch_and_analyze_feeds = AsyncMock()
        elif agent_type == "MarketConditionClassifierAgent":
            mock_service_instance.analyze_symbol_and_publish_condition = AsyncMock()
        elif agent_type == "PortfolioOptimizerAgent":
            # PO Service doesn't have a primary "run_cycle" method called by orchestrator, it's event driven
            # So, no specific method call to mock here for its main logic triggered by run_single_agent_cycle
            pass
        else: # Darvas, Williams, Renko
            mock_service_instance.analyze_symbol_and_generate_signal = AsyncMock()

        MockService.return_value = mock_service_instance

        # Mock portfolio summary for snapshot recording if it's a trading agent
        if agent_type not in non_trading_agent_types:
            mock_portfolio_summary = PortfolioSummary(
                agent_id=agent_id, timestamp=datetime.now(timezone.utc),
                account_value_usd=12345.0, total_pnl_usd=2345.0, open_positions=[]
            )
            orchestrator_service.trading_data_service.get_portfolio_summary = AsyncMock(return_value=mock_portfolio_summary)
        orchestrator_service.portfolio_snapshot_service.record_snapshot = AsyncMock() # Reset for each agent type

        # Call the cycle
        await orchestrator_service.run_single_agent_cycle(agent_id)

        # Assertions for service instantiation (common parts)
        if agent_type != "PortfolioOptimizerAgent": # PO Service is not instantiated in cycle by default
             expected_constructor_args = { "agent_config": agent_config, "event_bus": mock_event_bus_service }
             if agent_type not in ["NewsAnalysisAgent"]: # NewsAnalysis doesn't take MDS
                 expected_constructor_args["market_data_service"] = mock_market_data_service
             # All these services now accept learning_logger_service (optional)
             expected_constructor_args["learning_logger_service"] = orchestrator_service.learning_logger_service
             if agent_type == "RenkoTechnicalAgent":
                 expected_constructor_args["learning_logger"] = orchestrator_service.learning_logger_service
                 if "learning_logger_service" in expected_constructor_args: del expected_constructor_args["learning_logger_service"]
             # HeikinAshiTechnicalService __init__ from Step 2 did not have learning_logger.
             # If it were added, similar logic to Renko would apply for param name.
             # Based on current HeikinAshi service, learning_logger_service is not passed.
             # Self-correction: The orchestrator *does* pass learning_logger_service to HA if available,
             # but HA service init must accept it. Assuming HA service was updated to accept 'learning_logger_service' or 'learning_logger'.
             # The current orchestrator passes 'learning_logger' to Renko, and 'learning_logger_service' to others.
             # Let's assume HeikinAshi service (if it were to use it) would expect 'learning_logger_service' like Darvas/WA.
             # The prompt's HA service did not include it. The current orchestrator code for HA also doesn't pass it.
             # So, no change needed here for HA regarding learning_logger unless HA service is updated.
             # The provided orchestrator code for HA call:
             # heikin_ashi_service = HeikinAshiTechnicalService(..., # learning_logger=self.learning_logger_service) -> This was commented out.
             # So, for now, `learning_logger_service` is not in expected_constructor_args for HeikinAshi.
             if agent_type == "HeikinAshiTechnicalAgent" and "learning_logger_service" in expected_constructor_args:
                # If HA service was updated to take it like Darvas/Williams, this would be true.
                # Based on current definition of HA service from prompt, it does not take it.
                # The orchestrator code I generated for HA in this same subtask also *omitted* it.
                # So, this test should reflect that it's NOT passed to HA service.
                del expected_constructor_args["learning_logger_service"]


             MockService.assert_called_once_with(**expected_constructor_args)

        # Assertions for method calls on the service instance
        if agent_type == "NewsAnalysisAgent":
            mock_service_instance.fetch_and_analyze_feeds.assert_called_once()
        elif agent_type == "MarketConditionClassifierAgent":
            assert mock_service_instance.analyze_symbol_and_publish_condition.call_count == len(symbols)
        elif agent_type not in ["PortfolioOptimizerAgent"]: # PO doesn't have this
            assert mock_service_instance.analyze_symbol_and_generate_signal.call_count == len(symbols)

        # Assertions for snapshot recording
        if agent_type not in non_trading_agent_types:
            orchestrator_service.trading_data_service.get_portfolio_summary.assert_called_once_with(agent_id)
            orchestrator_service.portfolio_snapshot_service.record_snapshot.assert_called_once_with(
                agent_id=agent_id, total_equity_usd=12345.0
            )
        else: # For non-trading types, these should not be called
            orchestrator_service.trading_data_service.get_portfolio_summary.assert_not_called()
            orchestrator_service.portfolio_snapshot_service.record_snapshot.assert_not_called()

        mock_agent_service.update_agent_heartbeat.assert_called_once_with(agent_id)

        # Reset mocks for the next iteration of the loop
        MockService.reset_mock()
        mock_agent_service.reset_mock()
        orchestrator_service.trading_data_service.get_portfolio_summary.reset_mock()
        orchestrator_service.portfolio_snapshot_service.record_snapshot.reset_mock()


@pytest.mark.asyncio
@patch('python_ai_services.services.agent_orchestrator_service.NewsAnalysisService')
async def test_run_single_agent_cycle_news_analysis_agent_success(
    MockNewsService: MagicMock,
    orchestrator_service: AgentOrchestratorService,
    mock_agent_service: MagicMock,
    mock_event_bus_service: MagicMock
):
    agent_id = "news_agent_1"
    agent_config = create_sample_agent_config(agent_id, agent_type_override="NewsAnalysisAgent")
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)
    mock_news_instance = AsyncMock()
    mock_news_instance.fetch_and_analyze_feeds = AsyncMock()
    MockNewsService.return_value = mock_news_instance
    orchestrator_service._get_trading_coordinator_for_agent = AsyncMock()
    await orchestrator_service.run_single_agent_cycle(agent_id)
    MockNewsService.assert_called_once_with(
        agent_config=agent_config,
        event_bus=mock_event_bus_service
    )
    mock_news_instance.fetch_and_analyze_feeds.assert_called_once()
    orchestrator_service._get_trading_coordinator_for_agent.assert_not_called()
    mock_agent_service.update_agent_heartbeat.assert_called_once_with(agent_id)


# --- Tests for run_all_active_agents_once ---
@pytest.mark.asyncio
async def test_run_all_active_agents_once_no_active_agents(orchestrator_service: AgentOrchestratorService, mock_agent_service: MagicMock):
    mock_agent_service.get_agents = AsyncMock(return_value=[
        create_sample_agent_config("agent1", is_active=False),
        create_sample_agent_config("agent2", is_active=False)
    ])
    orchestrator_service.run_single_agent_cycle = AsyncMock()
    await orchestrator_service.run_all_active_agents_once()
    orchestrator_service.run_single_agent_cycle.assert_not_called()

@pytest.mark.asyncio
async def test_run_all_active_agents_once_multiple_active(orchestrator_service: AgentOrchestratorService, mock_agent_service: MagicMock):
    agent1_config = create_sample_agent_config("agent1_active", is_active=True)
    agent2_config = create_sample_agent_config("agent2_inactive", is_active=False)
    agent3_config = create_sample_agent_config("agent3_active", is_active=True)
    mock_agent_service.get_agents = AsyncMock(return_value=[agent1_config, agent2_config, agent3_config])
    orchestrator_service.run_single_agent_cycle = AsyncMock()
    await orchestrator_service.run_all_active_agents_once()
    assert orchestrator_service.run_single_agent_cycle.call_count == 2
    calls = orchestrator_service.run_single_agent_cycle.call_args_list
    called_agent_ids = {call[0][0] for call in calls}
    assert agent1_config.agent_id in called_agent_ids
    assert agent3_config.agent_id in called_agent_ids
    assert agent2_config.agent_id not in called_agent_ids

@pytest.mark.asyncio
async def test_run_all_active_agents_one_cycle_fails(orchestrator_service: AgentOrchestratorService, mock_agent_service: MagicMock):
    agent1_config = create_sample_agent_config("agent1_ok_cycle", is_active=True)
    agent2_config = create_sample_agent_config("agent2_fail_cycle", is_active=True)
    mock_agent_service.get_agents = AsyncMock(return_value=[agent1_config, agent2_config])
    async def side_effect_for_run_cycle(agent_id_param):
        if agent_id_param == "agent2_fail_cycle":
            raise ValueError("Simulated cycle failure")
        return f"Success for {agent_id_param}"
    orchestrator_service.run_single_agent_cycle = AsyncMock(side_effect=side_effect_for_run_cycle)
    await orchestrator_service.run_all_active_agents_once()
    assert orchestrator_service.run_single_agent_cycle.call_count == 2

from typing import Optional, List, Dict, Any # Ensure all type hints are imported
