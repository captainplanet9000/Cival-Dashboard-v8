from ..core.websocket_manager import ConnectionManager
from ..services.event_bus_service import EventBusService
from ..models.event_bus_models import Event
# Import Pydantic models for type clarity on payloads, though they arrive as dicts
from ..models.trade_history_models import TradeFillData
from ..models.alert_models import AlertNotification
from ..models.dashboard_models import PortfolioSnapshotOutput
from ..models.websocket_models import WebSocketEnvelope # Using WebSocketEnvelope as defined previously
from loguru import logger
from typing import Optional # For optional agent_id in event payload

class WebSocketRelayService:
    def __init__(self, connection_manager: ConnectionManager, event_bus: EventBusService):
        self.connection_manager = connection_manager
        self.event_bus = event_bus
        logger.info("WebSocketRelayService initialized.")

    async def setup_subscriptions(self):
        """
        Subscribes this relay service to relevant internal events on the event bus.
        """
        await self.event_bus.subscribe("NewFillRecordedEvent", self.on_new_fill_recorded)
        await self.event_bus.subscribe("AlertTriggeredEvent", self.on_alert_triggered)
        await self.event_bus.subscribe("PortfolioSnapshotTakenEvent", self.on_portfolio_snapshot_taken)
        logger.info("WebSocketRelayService: Subscribed to NewFillRecordedEvent, AlertTriggeredEvent, and PortfolioSnapshotTakenEvent.")

    async def _get_agent_id_from_event(self, event: Event) -> Optional[str]:
        """Helper to consistently extract agent_id from event or its payload."""
        agent_id = event.publisher_agent_id
        if not agent_id and isinstance(event.payload, dict):
            agent_id = event.payload.get('agent_id')

        if not agent_id:
             logger.warning(f"WebSocketRelay: Could not determine agent_id for event type {event.message_type}. Event ID: {event.event_id}. Cannot target specific client.")
        return agent_id

    async def on_new_fill_recorded(self, event: Event):
        if not isinstance(event.payload, dict):
            logger.error(f"WebSocketRelay: Invalid payload type for NewFillRecordedEvent: {type(event.payload)}. Expected dict.")
            return

        agent_id = await self._get_agent_id_from_event(event)
        if not agent_id:
            # Decide behavior: broadcast? skip? For fills, agent-specific is typical.
            logger.warning(f"WebSocketRelay: Skipping NewFillRecordedEvent relay as agent_id is missing. Event ID: {event.event_id}")
            return

        logger.debug(f"WebSocketRelay: Relaying NewFillRecordedEvent for agent {agent_id}. Fill ID: {event.payload.get('fill_id')}")

        ws_envelope = WebSocketEnvelope(
            event_type="NEW_FILL",
            agent_id=agent_id, # For client-side routing if dashboard handles multiple agents
            payload=event.payload # event.payload is already the dict of TradeFillData
        )
        await self.connection_manager.send_to_client(agent_id, ws_envelope)

    async def on_alert_triggered(self, event: Event):
        if not isinstance(event.payload, dict):
            logger.error(f"WebSocketRelay: Invalid payload type for AlertTriggeredEvent: {type(event.payload)}. Expected dict.")
            return

        agent_id = await self._get_agent_id_from_event(event)
        # For alerts, if agent_id is missing, we might choose to broadcast or handle differently.
        # The current ConnectionManager.send_to_client will simply not send if agent_id is None.
        # If a broadcast is desired for alerts without a specific agent_id, that logic would be here.

        logger.debug(f"WebSocketRelay: Relaying AlertTriggeredEvent for agent {agent_id or 'N/A'}. Alert Name: {event.payload.get('alert_name')}")

        ws_envelope = WebSocketEnvelope(
            event_type="ALERT_TRIGGERED",
            agent_id=agent_id, # Can be None if alert is system-wide and broadcast is used
            payload=event.payload # event.payload is already dict of AlertNotification
        )

        if agent_id:
            await self.connection_manager.send_to_client(agent_id, ws_envelope)
        else:
            # Example: If agent_id is None, broadcast to all connected dashboard clients
            logger.info("WebSocketRelay: AlertTriggeredEvent has no specific agent_id, broadcasting to all clients.")
            await self.connection_manager.broadcast_to_all(ws_envelope)


    async def on_portfolio_snapshot_taken(self, event: Event):
        if not isinstance(event.payload, dict):
            logger.error(f"WebSocketRelay: Invalid payload type for PortfolioSnapshotTakenEvent: {type(event.payload)}. Expected dict.")
            return

        agent_id = await self._get_agent_id_from_event(event)
        if not agent_id:
            logger.warning(f"WebSocketRelay: Skipping PortfolioSnapshotTakenEvent relay as agent_id is missing. Event ID: {event.event_id}")
            return

        logger.debug(f"WebSocketRelay: Relaying PortfolioSnapshotTakenEvent for agent {agent_id}. Timestamp: {event.payload.get('timestamp')}")

        ws_envelope = WebSocketEnvelope(
            event_type="PORTFOLIO_SNAPSHOT",
            agent_id=agent_id,
            payload=event.payload # event.payload is already dict of PortfolioSnapshotOutput
        )
        await self.connection_manager.send_to_client(agent_id, ws_envelope)
