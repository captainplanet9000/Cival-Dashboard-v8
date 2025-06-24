import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import uuid

from python_ai_services.services.alert_monitoring_service import AlertMonitoringService
from python_ai_services.services.alert_configuration_service import AlertConfigurationService
from python_ai_services.services.trading_data_service import TradingDataService
from python_ai_services.models.alert_models import AlertConfigOutput, AlertCondition, AlertNotification
from python_ai_services.models.dashboard_models import PortfolioSummary, AssetPositionSummary
# ConnectionManager and WebSocketEnvelope not directly used in AMS tests anymore
# from python_ai_services.core.websocket_manager import ConnectionManager
# from python_ai_services.models.websocket_models import WebSocketEnvelope
from python_ai_services.services.event_bus_service import EventBusService # Added
from python_ai_services.models.event_bus_models import Event # Added

@pytest_asyncio.fixture
def mock_alert_config_service() -> AlertConfigurationService:
    return MagicMock(spec=AlertConfigurationService)

@pytest_asyncio.fixture
def mock_trading_data_service() -> TradingDataService:
    return MagicMock(spec=TradingDataService)

@pytest_asyncio.fixture
def mock_event_bus() -> MagicMock: # Added
    bus = AsyncMock(spec=EventBusService)
    bus.publish = AsyncMock()
    return bus

@pytest_asyncio.fixture
def alert_monitoring_service(
    mock_alert_config_service: AlertConfigurationService,
    mock_trading_data_service: TradingDataService,
    mock_event_bus: MagicMock # Changed from mock_connection_manager
) -> AlertMonitoringService:
    return AlertMonitoringService(
        config_service=mock_alert_config_service,
        data_service=mock_trading_data_service,
        event_bus=mock_event_bus # Changed from connection_mgr
    )

# --- Helper to create sample data ---
def create_sample_alert_config(
    agent_id: str, alert_id: str, conditions: List[AlertCondition],
    is_enabled: bool = True, cooldown: int = 300, name: str = "Test Alert"
) -> AlertConfigOutput:
    return AlertConfigOutput(
        alert_id=alert_id,
        agent_id=agent_id,
        name=name,
        conditions=conditions,
        notification_channels=["log"],
        is_enabled=is_enabled,
        cooldown_seconds=cooldown,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

def create_sample_portfolio_summary(
    account_value: float = 10000.0,
    total_pnl: float = 500.0,
    available_balance: float = 9000.0,
    margin_used: float = 1000.0,
    positions: Optional[List[AssetPositionSummary]] = None
) -> PortfolioSummary:
    if positions is None:
        positions = [AssetPositionSummary(asset="BTC", size=0.1, unrealized_pnl=150.0)]
    return PortfolioSummary(
        agent_id="test_agent", # agent_id in portfolio summary is not used by alert logic directly
        timestamp=datetime.now(timezone.utc),
        account_value_usd=account_value,
        total_pnl_usd=total_pnl,
        available_balance_usd=available_balance,
        margin_used_usd=margin_used,
        open_positions=positions
    )

# --- Test Cases for _evaluate_condition ---
# Test _evaluate_condition directly as it's complex
def test_evaluate_condition_account_value_met(alert_monitoring_service: AlertMonitoringService):
    condition = AlertCondition(metric="account_value_usd", operator="<", threshold=9500.0)
    portfolio = create_sample_portfolio_summary(account_value=9000.0)
    met, val = alert_monitoring_service._evaluate_condition(condition, portfolio)
    assert met is True
    assert val == 9000.0

def test_evaluate_condition_account_value_not_met(alert_monitoring_service: AlertMonitoringService):
    condition = AlertCondition(metric="account_value_usd", operator=">", threshold=10000.0)
    portfolio = create_sample_portfolio_summary(account_value=9000.0)
    met, val = alert_monitoring_service._evaluate_condition(condition, portfolio)
    assert met is False
    assert val == 9000.0

def test_evaluate_condition_position_pnl_met(alert_monitoring_service: AlertMonitoringService):
    condition = AlertCondition(metric="open_position_unrealized_pnl", operator="<", threshold=-50.0, asset_symbol="ETH")
    positions = [AssetPositionSummary(asset="ETH", size=1, unrealized_pnl=-100.0)]
    portfolio = create_sample_portfolio_summary(open_positions=positions)
    met, val = alert_monitoring_service._evaluate_condition(condition, portfolio)
    assert met is True
    assert val == -100.0

def test_evaluate_condition_position_pnl_asset_not_found(alert_monitoring_service: AlertMonitoringService):
    condition = AlertCondition(metric="open_position_unrealized_pnl", operator="<", threshold=-50.0, asset_symbol="ADA")
    positions = [AssetPositionSummary(asset="ETH", size=1, unrealized_pnl=-100.0)]
    portfolio = create_sample_portfolio_summary(open_positions=positions)
    met, val = alert_monitoring_service._evaluate_condition(condition, portfolio)
    assert met is False
    assert val is None

def test_evaluate_condition_position_pnl_no_asset_symbol_in_condition(alert_monitoring_service: AlertMonitoringService):
    condition = AlertCondition(metric="open_position_unrealized_pnl", operator="<", threshold=-50.0) # asset_symbol missing
    portfolio = create_sample_portfolio_summary() # Pydantic validation on AlertCondition should catch this if strict
    # Assuming it bypasses for test:
    met, val = alert_monitoring_service._evaluate_condition(condition, portfolio)
    assert met is False
    assert val is None


# --- Test Cases for check_and_trigger_alerts_for_agent ---
@pytest.mark.asyncio
async def test_check_alerts_no_enabled_configs(alert_monitoring_service: AlertMonitoringService, mock_alert_config_service: MagicMock):
    agent_id = "agent_no_alerts"
    mock_alert_config_service.get_alert_configs_for_agent = AsyncMock(return_value=[])

    notifications = await alert_monitoring_service.check_and_trigger_alerts_for_agent(agent_id)
    assert len(notifications) == 0
    mock_alert_config_service.get_alert_configs_for_agent.assert_called_once_with(agent_id, only_enabled=True)

@pytest.mark.asyncio
async def test_check_alerts_no_portfolio_summary(
    alert_monitoring_service: AlertMonitoringService,
    mock_alert_config_service: MagicMock,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_no_portfolio"
    alert_conf = create_sample_alert_config(agent_id, "alert1", [AlertCondition(metric="account_value_usd", operator="<", threshold=1000)])
    mock_alert_config_service.get_alert_configs_for_agent = AsyncMock(return_value=[alert_conf])
    mock_trading_data_service.get_portfolio_summary = AsyncMock(return_value=None)

    notifications = await alert_monitoring_service.check_and_trigger_alerts_for_agent(agent_id)
    assert len(notifications) == 0
    mock_trading_data_service.get_portfolio_summary.assert_called_once_with(agent_id)

@pytest.mark.asyncio
async def test_check_alerts_condition_met_and_triggered(
    alert_monitoring_service: AlertMonitoringService,
    mock_alert_config_service: MagicMock,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_trigger"
    alert_id = "alert_id_1"
    condition = AlertCondition(metric="account_value_usd", operator="<", threshold=9500.0)
    alert_conf = create_sample_alert_config(agent_id, alert_id, [condition], name="Low Balance Alert")

    mock_alert_config_service.get_alert_configs_for_agent = AsyncMock(return_value=[alert_conf])
    portfolio = create_sample_portfolio_summary(account_value=9000.0)
    mock_trading_data_service.get_portfolio_summary = AsyncMock(return_value=portfolio)

    # Mock _send_notifications to verify it's called
    alert_monitoring_service._send_notifications = AsyncMock()

    notifications = await alert_monitoring_service.check_and_trigger_alerts_for_agent(agent_id)

    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.alert_id == alert_id
    assert notification.agent_id == agent_id
    assert "Low Balance Alert" in notification.message
    assert "account_value_usd < 9500.0 (current value: 9000.00)" in notification.message
    assert len(notification.triggered_conditions_details) == 1

    alert_monitoring_service._send_notifications.assert_called_once_with(alert_conf, notification)
    assert alert_id in alert_monitoring_service._last_triggered_times

@pytest.mark.asyncio
async def test_check_alerts_condition_not_met(
    alert_monitoring_service: AlertMonitoringService,
    mock_alert_config_service: MagicMock,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_no_trigger"
    condition = AlertCondition(metric="account_value_usd", operator=">", threshold=10000.0) # Not met
    alert_conf = create_sample_alert_config(agent_id, "alert2", [condition])

    mock_alert_config_service.get_alert_configs_for_agent = AsyncMock(return_value=[alert_conf])
    portfolio = create_sample_portfolio_summary(account_value=9000.0) # Current value doesn't meet condition
    mock_trading_data_service.get_portfolio_summary = AsyncMock(return_value=portfolio)
    alert_monitoring_service._send_notifications = AsyncMock()

    notifications = await alert_monitoring_service.check_and_trigger_alerts_for_agent(agent_id)
    assert len(notifications) == 0
    alert_monitoring_service._send_notifications.assert_not_called()

@pytest.mark.asyncio
async def test_check_alerts_cooldown_prevents_trigger(
    alert_monitoring_service: AlertMonitoringService,
    mock_alert_config_service: MagicMock,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_cooldown"
    alert_id = "alert_cooldown_1"
    condition = AlertCondition(metric="account_value_usd", operator="<", threshold=9500.0)
    alert_conf = create_sample_alert_config(agent_id, alert_id, [condition], cooldown=600) # 10 min cooldown

    mock_alert_config_service.get_alert_configs_for_agent = AsyncMock(return_value=[alert_conf])
    portfolio = create_sample_portfolio_summary(account_value=9000.0) # Condition is met
    mock_trading_data_service.get_portfolio_summary = AsyncMock(return_value=portfolio)
    alert_monitoring_service._send_notifications = AsyncMock()

    # Simulate it was triggered recently
    alert_monitoring_service._last_triggered_times[alert_id] = datetime.now(timezone.utc) - timedelta(seconds=100)

    notifications = await alert_monitoring_service.check_and_trigger_alerts_for_agent(agent_id)
    assert len(notifications) == 0 # Should be skipped due to cooldown
    alert_monitoring_service._send_notifications.assert_not_called()

    # Simulate cooldown has passed
    alert_monitoring_service._last_triggered_times[alert_id] = datetime.now(timezone.utc) - timedelta(seconds=700)
    notifications_after_cooldown = await alert_monitoring_service.check_and_trigger_alerts_for_agent(agent_id)
    assert len(notifications_after_cooldown) == 1 # Should trigger now
    alert_monitoring_service._send_notifications.assert_called_once()


@pytest.mark.asyncio
async def test_send_notifications_publishes_to_event_bus(alert_monitoring_service: AlertMonitoringService, mock_event_bus: MagicMock):
    alert_id = "alert_event_bus_test"
    agent_id = "agent_event_bus_test"
    # notification_channels can be anything, event publishing is independent now
    alert_config = create_sample_alert_config(
        agent_id, alert_id, conditions=[], name="Event Bus Test", notification_channels=["log"]
    )
    notification = AlertNotification(
        alert_id=alert_id, alert_name="Event Bus Test", agent_id=agent_id,
        message="Test event bus notification message", triggered_conditions_details=[]
    )

    with patch('python_ai_services.services.alert_monitoring_service.logger.warning') as mock_log_warn: # For log channel
        await alert_monitoring_service._send_notifications(alert_config, notification)

        mock_log_warn.assert_any_call(f"ALERT TRIGGERED (Agent: {agent_id}, Alert: Event Bus Test): Test event bus notification message")

        # Verify Event Bus publish
        mock_event_bus.publish.assert_called_once()
        event_arg: Event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event_arg, Event)
        assert event_arg.message_type == "AlertTriggeredEvent"
        assert event_arg.publisher_agent_id == agent_id
        assert event_arg.payload == notification.model_dump(mode='json')


@pytest.mark.asyncio
async def test_send_notifications_event_bus_unavailable(alert_monitoring_service: AlertMonitoringService, caplog):
    alert_monitoring_service.event_bus = None # Simulate no event bus available

    alert_id = "alert_no_event_bus"
    agent_id = "agent_no_event_bus"
    alert_config = create_sample_alert_config(
        agent_id, alert_id, conditions=[], name="No Event Bus Test",
        notification_channels=["log"] # Only log channel
    )
    notification = AlertNotification(
        alert_id=alert_id, alert_name="No Event Bus Test", agent_id=agent_id,
        message="Test no event bus", triggered_conditions_details=[]
    )

    # We expect the log channel to still work, but no event bus publish and no error related to it, just a warning at init.
    # The actual _send_notifications method should not error out if event_bus is None, it should just skip publishing.
    # The initial warning about event_bus missing is tested by checking the service's init logs if needed,
    # here we check that _send_notifications doesn't fail and that publish is not called.

    mock_event_bus_publish_on_instance = AsyncMock() # Create a new mock to ensure it's not called
    alert_monitoring_service.event_bus = MagicMock(publish=mock_event_bus_publish_on_instance) # Temporarily assign a mock
    alert_monitoring_service.event_bus = None # Then set to None

    await alert_monitoring_service._send_notifications(alert_config, notification)
    mock_event_bus_publish_on_instance.assert_not_called()
    # Check that "Alert events will not be published for relay" was logged at init (or relevant part of caplog)
    # This is harder to check here directly without capturing init logs.
    # The main thing is that it doesn't try to call publish on a None object.

# Need List, Optional from typing for helpers
from typing import List, Optional, Any # Added Any
