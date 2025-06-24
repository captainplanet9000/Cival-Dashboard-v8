from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from loguru import logger

from ..models.alert_models import AlertConfigOutput, AlertCondition, AlertNotification
from ..models.dashboard_models import PortfolioSummary, AssetPositionSummary # For type hinting
# WebSocketEnvelope no longer directly used here, EventBus + Relay will handle it.
# from ..models.websocket_models import WebSocketEnvelope
from .alert_configuration_service import AlertConfigurationService
from .trading_data_service import TradingDataService
# connection_manager no longer directly used here
# from ..core.websocket_manager import connection_manager as global_connection_manager
from ..services.event_bus_service import EventBusService # Added
from ..models.event_bus_models import Event # Added
import operator as op_module # For comparing values based on operator string

class AlertMonitoringService:
    def __init__(
        self,
        config_service: AlertConfigurationService,
        data_service: TradingDataService,
        event_bus: Optional[EventBusService] = None # Added event_bus
        # connection_mgr: Optional[Any] = None # Removed direct connection_mgr
    ):
        self.config_service = config_service
        self.data_service = data_service
        self.event_bus = event_bus # Store it
        self._last_triggered_times: Dict[str, datetime] = {} # Key: alert_id
        logger.info("AlertMonitoringService initialized.")
        if self.event_bus:
            logger.info("AlertMonitoringService: EventBusService available for publishing alert events.")
        else:
            logger.warning("AlertMonitoringService: EventBusService not available. Alert events will not be published for relay.")

    def _evaluate_condition(self, condition: AlertCondition, portfolio_summary: PortfolioSummary) -> (bool, Optional[Any]):
        """
        Evaluates a single alert condition against the portfolio summary.
        Returns a tuple: (condition_met, current_value_for_logging)
        """
        current_value: Optional[float] = None

        if condition.metric == "account_value_usd":
            current_value = portfolio_summary.account_value_usd
        elif condition.metric == "total_pnl_usd":
            current_value = portfolio_summary.total_pnl_usd
        elif condition.metric == "available_balance_usd":
            current_value = portfolio_summary.available_balance_usd
        elif condition.metric == "margin_used_usd":
            current_value = portfolio_summary.margin_used_usd
        elif condition.metric == "open_position_unrealized_pnl":
            if not condition.asset_symbol:
                logger.warning(f"Asset symbol missing for open_position_unrealized_pnl metric in condition: {condition.model_dump_json()}")
                return False, None

            position_found = False
            for pos in portfolio_summary.open_positions:
                if pos.asset == condition.asset_symbol:
                    current_value = pos.unrealized_pnl
                    position_found = True
                    break
            if not position_found:
                logger.debug(f"Asset {condition.asset_symbol} not found in open positions for alert check.")
                # Depending on desired behavior, could treat as condition not met, or value is 0/None
                return False, None # Or current_value = 0.0 if that's preferred for non-existent positions

        if current_value is None:
            logger.debug(f"Metric {condition.metric} resulted in None value, condition not met.")
            return False, None

        ops = {
            "<": op_module.lt, "<=": op_module.le,
            ">": op_module.gt, ">=": op_module.ge,
            "==": op_module.eq
        }
        if condition.operator not in ops:
            logger.error(f"Unsupported operator '{condition.operator}' in condition.")
            return False, current_value

        return ops[condition.operator](current_value, condition.threshold), current_value


    async def _send_notifications(self, alert_config: AlertConfigOutput, notification: AlertNotification):
        logger.info(f"Sending notifications for alert '{alert_config.name}' (ID: {alert_config.alert_id}) for agent {alert_config.agent_id}")
        for channel in alert_config.notification_channels:
            if channel == "log":
                logger.warning(f"ALERT TRIGGERED (Agent: {notification.agent_id}, Alert: {notification.alert_name}): {notification.message}")
            elif channel == "email_placeholder":
                if alert_config.target_email:
                    logger.info(f"Placeholder: Would send email to {alert_config.target_email}: {notification.message}")
                else:
                    logger.error(f"Cannot send email for alert {alert_config.alert_id}: target_email not set.")
            elif channel == "webhook_placeholder":
                if alert_config.target_webhook_url:
                    logger.info(f"Placeholder: Would POST to {alert_config.target_webhook_url} with payload: {notification.model_dump_json()}")
                else:
                    logger.error(f"Cannot send webhook for alert {alert_config.alert_id}: target_webhook_url not set.")
            # The "websocket" channel is now implicitly handled by publishing to EventBus
            # if WebSocketRelayService is subscribed to "AlertTriggeredEvent".
            # No direct ConnectionManager interaction here anymore.
            # If a channel named "websocket" is still in config, it might just mean "make this available for websocket relay"
            # which is achieved by publishing to event bus.
            else: # Log other configured channels as unknown if not handled above.
                 if channel != "websocket": # Avoid warning if "websocket" is just a marker now
                    logger.warning(f"Unknown or unhandled notification channel '{channel}' for alert {alert_config.alert_id}.")

        # After handling traditional notifications, publish to Event Bus for other consumers (like WebSocketRelay)
        if self.event_bus:
            try:
                event_payload_dict = notification.model_dump(mode='json') # mode='json' for datetime
                await self.event_bus.publish(Event(
                    publisher_agent_id=alert_config.agent_id, # Or a system ID like "AlertMonitoringService"
                    message_type="AlertTriggeredEvent",
                    payload=event_payload_dict
                ))
                logger.info(f"Published AlertTriggeredEvent for alert '{alert_config.name}', agent {alert_config.agent_id}")
            except Exception as e_event:
                logger.error(f"Error publishing AlertTriggeredEvent for alert {alert_config.alert_id}: {e_event}", exc_info=True)


    async def check_and_trigger_alerts_for_agent(self, agent_id: str) -> List[AlertNotification]:
        logger.debug(f"Checking alerts for agent_id: {agent_id}")
        now = datetime.now(timezone.utc)
        triggered_notifications: List[AlertNotification] = []

        enabled_alert_configs = await self.config_service.get_alert_configs_for_agent(agent_id, only_enabled=True)
        if not enabled_alert_configs:
            logger.debug(f"No enabled alert configurations found for agent {agent_id}.")
            return []

        portfolio_summary = await self.data_service.get_portfolio_summary(agent_id)
        if not portfolio_summary:
            logger.warning(f"Could not retrieve portfolio summary for agent {agent_id}. Skipping alert checks.")
            return []

        for alert_config in enabled_alert_configs:
            # Check cooldown
            last_triggered = self._last_triggered_times.get(alert_config.alert_id)
            if last_triggered and (now - last_triggered) < timedelta(seconds=alert_config.cooldown_seconds):
                logger.debug(f"Alert {alert_config.name} (ID: {alert_config.alert_id}) is in cooldown. Skipping.")
                continue

            all_conditions_met = True
            triggered_conditions_details_log: List[Dict[str, Any]] = []

            if not alert_config.conditions: # Should not happen if validation is good, but handle defensively
                logger.warning(f"Alert config {alert_config.name} (ID: {alert_config.alert_id}) has no conditions. Skipping.")
                continue

            for condition in alert_config.conditions:
                condition_met, current_value = self._evaluate_condition(condition, portfolio_summary)
                if condition_met:
                    triggered_conditions_details_log.append({
                        "metric": condition.metric,
                        "operator": condition.operator,
                        "threshold": condition.threshold,
                        "current_value": current_value,
                        "asset_symbol": condition.asset_symbol
                    })
                else: # AND logic: if any condition is false, the alert doesn't trigger
                    all_conditions_met = False
                    break

            if all_conditions_met:
                logger.info(f"All conditions met for alert '{alert_config.name}' (ID: {alert_config.alert_id}) for agent {agent_id}.")

                # Construct message
                message_parts = [f"Alert '{alert_config.name}' triggered for agent {agent_id}."]
                for detail in triggered_conditions_details_log:
                    msg_part = f"Condition: {detail['metric']}"
                    if detail['asset_symbol']:
                        msg_part += f" ({detail['asset_symbol']})"
                    msg_part += f" {detail['operator']} {detail['threshold']} (current value: {detail['current_value']:.2f})"
                    message_parts.append(msg_part)

                notification_message = " ".join(message_parts)

                notification = AlertNotification(
                    alert_id=alert_config.alert_id,
                    alert_name=alert_config.name,
                    agent_id=agent_id,
                    message=notification_message,
                    triggered_conditions_details=triggered_conditions_details_log
                )

                await self._send_notifications(alert_config, notification)
                self._last_triggered_times[alert_config.alert_id] = now
                triggered_notifications.append(notification)
            else:
                logger.debug(f"Not all conditions met for alert '{alert_config.name}' (ID: {alert_config.alert_id}) for agent {agent_id}.")

        return triggered_notifications

