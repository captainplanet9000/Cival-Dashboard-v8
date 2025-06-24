import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, call
from typing import List, Dict, Any, Optional

from python_ai_services.services.portfolio_optimizer_service import PortfolioOptimizerService
from python_ai_services.services.agent_management_service import AgentManagementService
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.models.agent_models import (
    AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig,
    AgentUpdateRequest
)
# PortfolioOptimizerParams and PortfolioOptimizerRule are nested in AgentStrategyConfig
from python_ai_services.models.event_bus_models import Event, MarketConditionEventPayload, NewsArticleEventPayload # Added
from datetime import datetime, timezone

# --- Fixtures ---
@pytest_asyncio.fixture
def mock_agent_management_service() -> AgentManagementService:
    service = AsyncMock(spec=AgentManagementService)
    service.get_agent = AsyncMock()
    service.get_agents = AsyncMock()
    service.update_agent = AsyncMock()
    return service

@pytest_asyncio.fixture
def mock_event_bus() -> EventBusService:
    service = AsyncMock(spec=EventBusService)
    service.subscribe = AsyncMock()
    service.publish = AsyncMock() # Though PO service doesn't publish in this design
    return service

# Helper to create AgentConfigOutput for PortfolioOptimizerAgent
def create_optimizer_agent_config(
    agent_id: str,
    rules: List[AgentStrategyConfig.PortfolioOptimizerRule]
) -> AgentConfigOutput:
    return AgentConfigOutput(
        agent_id=agent_id, name=f"Optimizer_{agent_id}", agent_type="PortfolioOptimizerAgent",
        strategy=AgentStrategyConfig(
            strategy_name="PortfolioOptimizerStrategy",
            portfolio_optimizer_params=AgentStrategyConfig.PortfolioOptimizerParams(rules=rules)
        ),
        risk_config=AgentRiskConfig(max_capital_allocation_usd=0, risk_per_trade_percentage=0), # Not used by PO
        is_active=True, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )

# Helper to create AgentConfigOutput for a target agent
def create_target_agent_config(
    agent_id: str, agent_type: str = "GenericAgent",
    is_active: bool = True, op_params: Optional[Dict[str, Any]] = None,
    watched_symbols: Optional[List[str]] = None
) -> AgentConfigOutput:
    return AgentConfigOutput(
        agent_id=agent_id, name=f"Target_{agent_id}", agent_type=agent_type,
        strategy=AgentStrategyConfig(
            strategy_name="some_strat",
            parameters={},
            watched_symbols=watched_symbols if watched_symbols is not None else []
        ),
        risk_config=AgentRiskConfig(max_capital_allocation_usd=1000, risk_per_trade_percentage=0.01),
        is_active=is_active, operational_parameters=op_params if op_params else {},
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )

# --- Test Cases ---
@pytest.mark.asyncio
async def test_portfolio_optimizer_init_and_subscriptions(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    rule = AgentStrategyConfig.PortfolioOptimizerRule(rule_name="Test Rule")
    agent_config = create_optimizer_agent_config("optimizer1", rules=[rule])

    optimizer_service = PortfolioOptimizerService(
        agent_config=agent_config,
        agent_management_service=mock_agent_management_service,
        event_bus=mock_event_bus
    )
    assert optimizer_service.params.rules[0].rule_name == "Test Rule"

    await optimizer_service.setup_subscriptions()
    # Check for both subscriptions
    expected_calls = [
        call("MarketConditionEvent", optimizer_service.on_market_condition_event),
        call("NewsArticleEvent", optimizer_service.on_news_article_event)
    ]
    mock_event_bus.subscribe.assert_has_calls(expected_calls, any_order=True)
    assert mock_event_bus.subscribe.call_count == 2
    # Check logger message (optional, if logger is mocked and important)
    # For example, if logger was passed in and mocked:
    # mock_logger.info.assert_any_call(f"PortfolioOptimizerService ({agent_config.agent_id}): Subscribed to MarketConditionEvent and NewsArticleEvent.")


@pytest.mark.asyncio
async def test_optimizer_init_no_params(mock_agent_management_service, mock_event_bus):
    agent_config_no_params = AgentConfigOutput(
        agent_id="opt_no_params", name="OptimizerNoParams", agent_type="PortfolioOptimizerAgent",
        strategy=AgentStrategyConfig(strategy_name="PortfolioOptimizerStrategy"), # portfolio_optimizer_params is None
        risk_config=AgentRiskConfig(max_capital_allocation_usd=0, risk_per_trade_percentage=0)
    )
    service = PortfolioOptimizerService(agent_config_no_params, mock_agent_management_service, mock_event_bus)
    assert service.params.rules == [] # Should default to empty rules

@pytest.mark.asyncio
async def test_on_market_condition_event_no_matching_rule(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    rules = [AgentStrategyConfig.PortfolioOptimizerRule(if_market_regime="trending_up")]
    agent_config = create_optimizer_agent_config("optimizer_no_match", rules=rules)
    optimizer_service = PortfolioOptimizerService(agent_config, mock_agent_management_service, mock_event_bus)

    event_payload = MarketConditionEventPayload(symbol="BTC/USD", regime="ranging")
    event = Event(publisher_agent_id="mcc1", message_type="MarketConditionEvent", payload=event_payload.model_dump())

    await optimizer_service.on_market_condition_event(event)
    mock_agent_management_service.update_agent.assert_not_called()

@pytest.mark.asyncio
async def test_on_market_condition_event_applies_rule_target_id(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    target_agent_id = "target_agent_for_id_rule"
    rule = AgentStrategyConfig.PortfolioOptimizerRule(
        rule_name="ActivateAgentOnTrendingUp",
        if_market_regime="trending_up",
        target_agent_id=target_agent_id,
        set_is_active=True,
        set_operational_parameters={"risk_factor": 0.5}
    )
    optimizer_config = create_optimizer_agent_config("optimizer_id_target", rules=[rule])

    target_agent_initial_config = create_target_agent_config(target_agent_id, is_active=False, op_params={"risk_factor": 1.0, "another_param": "value"})
    mock_agent_management_service.get_agent = AsyncMock(return_value=target_agent_initial_config)

    optimizer_service = PortfolioOptimizerService(optimizer_config, mock_agent_management_service, mock_event_bus)

    event_payload = MarketConditionEventPayload(symbol="ETH/USD", regime="trending_up")
    event = Event(publisher_agent_id="mcc1", message_type="MarketConditionEvent", payload=event_payload.model_dump())

    await optimizer_service.on_market_condition_event(event)

    mock_agent_management_service.update_agent.assert_called_once()
    call_args = mock_agent_management_service.update_agent.call_args[1] # Get kwargs
    assert call_args['agent_id'] == target_agent_id
    update_request: AgentUpdateRequest = call_args['update_data']
    assert update_request.is_active is True
    assert update_request.operational_parameters == {"risk_factor": 0.5, "another_param": "value"} # Merged

@pytest.mark.asyncio
async def test_on_market_condition_event_applies_rule_target_type(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    target_type = "TradingAgentTypeX"
    rule = AgentStrategyConfig.PortfolioOptimizerRule(
        rule_name="DeactivateTypeXRanging",
        if_market_regime="ranging",
        target_agent_type=target_type,
        set_is_active=False
    )
    optimizer_config = create_optimizer_agent_config("optimizer_type_target", rules=[rule])

    target_agent1 = create_target_agent_config("target1", agent_type=target_type, is_active=True)
    target_agent2 = create_target_agent_config("target2", agent_type="OtherType", is_active=True) # Should not be affected
    target_agent3 = create_target_agent_config("target3", agent_type=target_type, is_active=True)
    # Optimizer itself should not be targeted even if it matches type
    optimizer_self_as_target_type = create_optimizer_agent_config("optimizer_type_target", rules=[])

    mock_agent_management_service.get_agents = AsyncMock(return_value=[
        target_agent1, target_agent2, target_agent3, optimizer_self_as_target_type
    ])

    optimizer_service = PortfolioOptimizerService(optimizer_config, mock_agent_management_service, mock_event_bus)

    event_payload = MarketConditionEventPayload(symbol="BTC/USD", regime="ranging")
    event = Event(publisher_agent_id="mcc1", message_type="MarketConditionEvent", payload=event_payload.model_dump())

    await optimizer_service.on_market_condition_event(event)

    assert mock_agent_management_service.update_agent.call_count == 2
    # Check that update_agent was called for target1 and target3 with is_active=False
    expected_update_payload = AgentUpdateRequest(is_active=False)

    # Create a list of calls to check against
    calls_made = mock_agent_management_service.update_agent.call_args_list

    # Check call for target_agent1
    assert any(
        c.kwargs['agent_id'] == target_agent1.agent_id and
        c.kwargs['update_data'].model_dump(exclude_none=True) == expected_update_payload.model_dump(exclude_none=True)
        for c in calls_made
    )
    # Check call for target_agent3
    assert any(
        c.kwargs['agent_id'] == target_agent3.agent_id and
        c.kwargs['update_data'].model_dump(exclude_none=True) == expected_update_payload.model_dump(exclude_none=True)
        for c in calls_made
    )


@pytest.mark.asyncio
async def test_on_market_condition_event_no_actual_change(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    target_agent_id = "target_no_change"
    rule = AgentStrategyConfig.PortfolioOptimizerRule(
        rule_name="NoChangeRule", if_market_regime="trending_up",
        target_agent_id=target_agent_id, set_is_active=True # Target is already active
    )
    optimizer_config = create_optimizer_agent_config("optimizer_no_change", rules=[rule])
    target_agent_config = create_target_agent_config(target_agent_id, is_active=True) # Already active
    mock_agent_management_service.get_agent = AsyncMock(return_value=target_agent_config)

    optimizer_service = PortfolioOptimizerService(optimizer_config, mock_agent_management_service, mock_event_bus)
    event_payload = MarketConditionEventPayload(symbol="ANY/USD", regime="trending_up")
    event = Event(publisher_agent_id="mcc1", message_type="MarketConditionEvent", payload=event_payload.model_dump())

    await optimizer_service.on_market_condition_event(event)
    mock_agent_management_service.update_agent.assert_not_called()


@pytest.mark.asyncio
async def test_on_market_condition_event_invalid_payload(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    optimizer_config = create_optimizer_agent_config("optimizer_bad_payload", rules=[AgentStrategyConfig.PortfolioOptimizerRule(if_market_regime="trending_up")])
    optimizer_service = PortfolioOptimizerService(optimizer_config, mock_agent_management_service, mock_event_bus)

    invalid_payload_event = Event(publisher_agent_id="mcc1", message_type="MarketConditionEvent", payload={"wrong_field": "data"})

    with patch.object(optimizer_service.logger, 'error') as mock_log_error:
        await optimizer_service.on_market_condition_event(invalid_payload_event)
        mock_log_error.assert_called_once()
        assert "Failed to parse MarketConditionEventPayload" in mock_log_error.call_args[0][0]

    mock_agent_management_service.update_agent.assert_not_called()


# --- Tests for on_news_article_event ---

@pytest.mark.asyncio
async def test_on_news_article_event_no_matching_sentiment_rule(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    rules = [AgentStrategyConfig.PortfolioOptimizerRule(if_news_sentiment_is="positive")]
    optimizer_config = create_optimizer_agent_config("opt_news_no_match", rules=rules)
    optimizer_service = PortfolioOptimizerService(optimizer_config, mock_agent_management_service, mock_event_bus)
    optimizer_service._apply_rule_to_targets = AsyncMock() # Mock to check if called

    news_payload = NewsArticleEventPayload(
        article_id="news1", title="Great News", sentiment_label="neutral", # Different sentiment
        mentioned_symbols=["SYM1", "SYM2"]
    )
    event = Event(publisher_agent_id="news_agent", message_type="NewsArticleEvent", payload=news_payload.model_dump())

    await optimizer_service.on_news_article_event(event)
    optimizer_service._apply_rule_to_targets.assert_not_called()


@pytest.mark.asyncio
async def test_on_news_article_event_applies_rule_no_symbol_filter_in_event(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    target_agent_id = "target_for_news_any_sym"
    rule = AgentStrategyConfig.PortfolioOptimizerRule(
        rule_name="ActivateOnPositiveNews", if_news_sentiment_is="positive",
        target_agent_id=target_agent_id, set_is_active=True
    )
    optimizer_config = create_optimizer_agent_config("opt_news_no_sym_event", rules=[rule])

    target_agent_conf = create_target_agent_config(target_agent_id, is_active=False, watched_symbols=["TARGET_SYM"])
    mock_agent_management_service.get_agent = AsyncMock(return_value=target_agent_conf)

    optimizer_service = PortfolioOptimizerService(optimizer_config, mock_agent_management_service, mock_event_bus)
    # _apply_rule_to_targets will be called, and it will call update_agent
    optimizer_service._apply_rule_to_targets = AsyncMock(wraps=optimizer_service._apply_rule_to_targets) # Wrap to spy & execute

    news_payload = NewsArticleEventPayload(
        article_id="news2", title="Market is Up!", sentiment_label="positive",
        mentioned_symbols=[] # Event mentions no specific symbols
    )
    event = Event(publisher_agent_id="news_agent", message_type="NewsArticleEvent", payload=news_payload.model_dump())

    await optimizer_service.on_news_article_event(event)

    optimizer_service._apply_rule_to_targets.assert_called_once()
    mock_agent_management_service.update_agent.assert_called_once()
    updated_agent_id = mock_agent_management_service.update_agent.call_args[1]['agent_id']
    update_data: AgentUpdateRequest = mock_agent_management_service.update_agent.call_args[1]['update_data']
    assert updated_agent_id == target_agent_id
    assert update_data.is_active is True


@pytest.mark.asyncio
async def test_on_news_article_event_applies_rule_with_symbol_intersection(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    target_agent_type = "NewsReactiveTrader"
    rule = AgentStrategyConfig.PortfolioOptimizerRule(
        rule_name="BoostOnNegativeNewsForWatchedSymbol", if_news_sentiment_is="negative",
        target_agent_type=target_agent_type, set_operational_parameters={"aggression": 1.5}
    )
    optimizer_config = create_optimizer_agent_config("opt_news_sym_match", rules=[rule])

    # Agent 1 watches SYM1 (will be matched)
    target1_conf = create_target_agent_config("target1_news", agent_type=target_agent_type, watched_symbols=["SYM1", "OTHER"], op_params={"aggression": 1.0})
    # Agent 2 watches SYM3 (will not be matched)
    target2_conf = create_target_agent_config("target2_news", agent_type=target_agent_type, watched_symbols=["SYM3"], op_params={"aggression": 1.0})
    # Agent 3 of different type (will not be matched by type)
    target3_conf = create_target_agent_config("target3_other_type", agent_type="OtherTrader", watched_symbols=["SYM1"])

    mock_agent_management_service.get_agents = AsyncMock(return_value=[target1_conf, target2_conf, target3_conf])

    optimizer_service = PortfolioOptimizerService(optimizer_config, mock_agent_management_service, mock_event_bus)
    optimizer_service._apply_rule_to_targets = AsyncMock(wraps=optimizer_service._apply_rule_to_targets)

    news_payload = NewsArticleEventPayload(
        article_id="news3", title="SYM1 Plummets!", sentiment_label="negative",
        mentioned_symbols=["SYM1", "SYM2"] # SYM1 is mentioned and watched by target1
    )
    event = Event(publisher_agent_id="news_agent", message_type="NewsArticleEvent", payload=news_payload.model_dump())

    await optimizer_service.on_news_article_event(event)

    optimizer_service._apply_rule_to_targets.assert_called_once()
    mock_agent_management_service.update_agent.assert_called_once() # Only target1 should be updated

    updated_agent_id = mock_agent_management_service.update_agent.call_args[1]['agent_id']
    update_data: AgentUpdateRequest = mock_agent_management_service.update_agent.call_args[1]['update_data']
    assert updated_agent_id == target1_conf.agent_id
    assert update_data.operational_parameters == {"aggression": 1.5}


@pytest.mark.asyncio
async def test_on_news_article_event_no_symbol_intersection(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    target_agent_type = "NewsReactiveTrader"
    rule = AgentStrategyConfig.PortfolioOptimizerRule(
        rule_name="BoostOnPositiveNews", if_news_sentiment_is="positive",
        target_agent_type=target_agent_type, set_operational_parameters={"mode": "active_buy"}
    )
    optimizer_config = create_optimizer_agent_config("opt_news_no_sym_intersect", rules=[rule])

    # Target agent watches only OTHER_SYM
    target_agent_conf = create_target_agent_config("target_news_no_match", agent_type=target_agent_type, watched_symbols=["OTHER_SYM"])
    mock_agent_management_service.get_agents = AsyncMock(return_value=[target_agent_conf])

    optimizer_service = PortfolioOptimizerService(optimizer_config, mock_agent_management_service, mock_event_bus)
    optimizer_service._apply_rule_to_targets = AsyncMock(wraps=optimizer_service._apply_rule_to_targets)

    news_payload = NewsArticleEventPayload(
        article_id="news4", title="SYM1 and SYM2 Surge", sentiment_label="positive",
        mentioned_symbols=["SYM1", "SYM2"] # Target agent does not watch these
    )
    event = Event(publisher_agent_id="news_agent", message_type="NewsArticleEvent", payload=news_payload.model_dump())

    await optimizer_service.on_news_article_event(event)

    # _apply_rule_to_targets is called because a rule matches the sentiment
    optimizer_service._apply_rule_to_targets.assert_called_once()
    # But no agent update should happen because the symbol intersection fails
    mock_agent_management_service.update_agent.assert_not_called()


@pytest.mark.asyncio
async def test_on_news_article_event_invalid_payload(
    mock_agent_management_service: MagicMock, mock_event_bus: MagicMock
):
    optimizer_config = create_optimizer_agent_config("opt_news_bad_payload", rules=[AgentStrategyConfig.PortfolioOptimizerRule(if_news_sentiment_is="positive")])
    optimizer_service = PortfolioOptimizerService(optimizer_config, mock_agent_management_service, mock_event_bus)

    invalid_payload_event = Event(publisher_agent_id="news_agent", message_type="NewsArticleEvent", payload={"bad_data": True})

    with patch.object(optimizer_service.logger, 'error') as mock_log_error:
        await optimizer_service.on_news_article_event(invalid_payload_event)
        mock_log_error.assert_called_once()
        assert "Failed to parse NewsArticleEventPayload" in mock_log_error.call_args[0][0]

    mock_agent_management_service.update_agent.assert_not_called()

# Ensure all type hints are imported
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone
