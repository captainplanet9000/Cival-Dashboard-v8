import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, call # Added call
from datetime import datetime, timezone
import uuid

from python_ai_services.services.websocket_relay_service import WebSocketRelayService
from python_ai_services.core.websocket_manager import ConnectionManager
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.models.event_bus_models import Event
from python_ai_services.models.websocket_models import WebSocketEnvelope
# Import payload types for creating test events
from python_ai_services.models.trade_history_models import TradeFillData
from python_ai_services.models.alert_models import AlertNotification
from python_ai_services.models.dashboard_models import PortfolioSnapshotOutput


@pytest_asyncio.fixture
def mock_connection_manager() -> MagicMock:
    manager = MagicMock(spec=ConnectionManager)
    manager.send_to_client = AsyncMock()
    manager.broadcast_json = AsyncMock() # If WebSocketMessage is used directly for broadcast
    manager.broadcast_to_all = AsyncMock() # If WebSocketEnvelope is used for broadcast
    return manager

@pytest_asyncio.fixture
def mock_event_bus() -> MagicMock:
    bus = MagicMock(spec=EventBusService)
    bus.subscribe = AsyncMock()
    return bus

@pytest_asyncio.fixture
def websocket_relay_service(mock_connection_manager: MagicMock, mock_event_bus: MagicMock) -> WebSocketRelayService:
    return WebSocketRelayService(connection_manager=mock_connection_manager, event_bus=mock_event_bus)

# --- Test Cases ---

@pytest.mark.asyncio
async def test_setup_subscriptions(websocket_relay_service: WebSocketRelayService, mock_event_bus: MagicMock):
    await websocket_relay_service.setup_subscriptions()

    expected_calls = [
        call("NewFillRecordedEvent", websocket_relay_service.on_new_fill_recorded),
        call("AlertTriggeredEvent", websocket_relay_service.on_alert_triggered),
        call("PortfolioSnapshotTakenEvent", websocket_relay_service.on_portfolio_snapshot_taken)
    ]
    mock_event_bus.subscribe.assert_has_calls(expected_calls, any_order=True)
    assert mock_event_bus.subscribe.call_count == 3

@pytest.mark.asyncio
async def test_on_new_fill_recorded(websocket_relay_service: WebSocketRelayService, mock_connection_manager: MagicMock):
    agent_id = "agent_fill_test"
    fill_payload_dict = TradeFillData( # Create with Pydantic then dump for exact match if needed
        fill_id=str(uuid.uuid4()), agent_id=agent_id, asset="BTC/USD", side="buy", quantity=0.1,
        price=50000, timestamp=datetime.now(timezone.utc), fee=5.0
    ).model_dump(mode='json')

    event = Event(
        publisher_agent_id=agent_id,
        message_type="NewFillRecordedEvent",
        payload=fill_payload_dict
    )

    await websocket_relay_service.on_new_fill_recorded(event)

    mock_connection_manager.send_to_client.assert_called_once()
    call_args = mock_connection_manager.send_to_client.call_args[0]
    assert call_args[0] == agent_id # client_id to send to

    ws_envelope: WebSocketEnvelope = call_args[1]
    assert ws_envelope.event_type == "NEW_FILL"
    assert ws_envelope.agent_id == agent_id
    assert ws_envelope.payload == fill_payload_dict

@pytest.mark.asyncio
async def test_on_new_fill_recorded_no_agent_id(websocket_relay_service: WebSocketRelayService, mock_connection_manager: MagicMock, caplog):
    fill_payload_dict = {"fill_id": "fill_no_agent", "asset": "ETH/USD"} # Missing agent_id in payload
    event = Event(
        publisher_agent_id=None, # No publisher_agent_id
        message_type="NewFillRecordedEvent",
        payload=fill_payload_dict
    )
    await websocket_relay_service.on_new_fill_recorded(event)
    mock_connection_manager.send_to_client.assert_not_called()
    assert "Skipping NewFillRecordedEvent relay as agent_id is missing" in caplog.text


@pytest.mark.asyncio
async def test_on_alert_triggered_with_agent_id(websocket_relay_service: WebSocketRelayService, mock_connection_manager: MagicMock):
    agent_id = "agent_alert_test"
    alert_payload_dict = AlertNotification(
        alert_id="alert1", alert_name="Test Alert", agent_id=agent_id,
        message="This is a test alert", triggered_at=datetime.now(timezone.utc)
    ).model_dump(mode='json')

    event = Event(
        publisher_agent_id=agent_id,
        message_type="AlertTriggeredEvent",
        payload=alert_payload_dict
    )

    await websocket_relay_service.on_alert_triggered(event)

    mock_connection_manager.send_to_client.assert_called_once()
    call_args = mock_connection_manager.send_to_client.call_args[0]
    assert call_args[0] == agent_id

    ws_envelope: WebSocketEnvelope = call_args[1]
    assert ws_envelope.event_type == "ALERT_TRIGGERED"
    assert ws_envelope.agent_id == agent_id
    assert ws_envelope.payload == alert_payload_dict
    mock_connection_manager.broadcast_to_all.assert_not_called()


@pytest.mark.asyncio
async def test_on_alert_triggered_no_agent_id_broadcasts(websocket_relay_service: WebSocketRelayService, mock_connection_manager: MagicMock, caplog):
    alert_payload_dict = {"alert_name": "System Alert", "message": "System wide broadcast"} # Missing agent_id
    event = Event(
        publisher_agent_id=None, # No specific agent publisher
        message_type="AlertTriggeredEvent",
        payload=alert_payload_dict
    )

    await websocket_relay_service.on_alert_triggered(event)

    mock_connection_manager.send_to_client.assert_not_called()
    mock_connection_manager.broadcast_to_all.assert_called_once()
    ws_envelope: WebSocketEnvelope = mock_connection_manager.broadcast_to_all.call_args[0][0]
    assert ws_envelope.event_type == "ALERT_TRIGGERED"
    assert ws_envelope.agent_id is None # No specific agent for broadcast
    assert ws_envelope.payload == alert_payload_dict
    assert "AlertTriggeredEvent has no specific agent_id, broadcasting to all clients." in caplog.text


@pytest.mark.asyncio
async def test_on_portfolio_snapshot_taken(websocket_relay_service: WebSocketRelayService, mock_connection_manager: MagicMock):
    agent_id = "agent_snapshot_test"
    snapshot_payload_dict = PortfolioSnapshotOutput(
        agent_id=agent_id, timestamp=datetime.now(timezone.utc), total_equity_usd=12345.67
    ).model_dump(mode='json')

    event = Event(
        publisher_agent_id=agent_id,
        message_type="PortfolioSnapshotTakenEvent",
        payload=snapshot_payload_dict
    )

    await websocket_relay_service.on_portfolio_snapshot_taken(event)

    mock_connection_manager.send_to_client.assert_called_once()
    call_args = mock_connection_manager.send_to_client.call_args[0]
    assert call_args[0] == agent_id

    ws_envelope: WebSocketEnvelope = call_args[1]
    assert ws_envelope.event_type == "PORTFOLIO_SNAPSHOT"
    assert ws_envelope.agent_id == agent_id
    assert ws_envelope.payload == snapshot_payload_dict

@pytest.mark.asyncio
async def test_on_portfolio_snapshot_taken_no_agent_id(websocket_relay_service: WebSocketRelayService, mock_connection_manager: MagicMock, caplog):
    snapshot_payload_dict = {"timestamp": datetime.now(timezone.utc).isoformat(), "total_equity_usd": 500} # Missing agent_id
    event = Event(
        publisher_agent_id=None,
        message_type="PortfolioSnapshotTakenEvent",
        payload=snapshot_payload_dict
    )
    await websocket_relay_service.on_portfolio_snapshot_taken(event)
    mock_connection_manager.send_to_client.assert_not_called()
    assert "Skipping PortfolioSnapshotTakenEvent relay as agent_id is missing" in caplog.text

@pytest.mark.asyncio
async def test_event_handler_invalid_payload_type(websocket_relay_service: WebSocketRelayService, mock_connection_manager: MagicMock, caplog):
    event_invalid_payload = Event(
        publisher_agent_id="agent_x",
        message_type="NewFillRecordedEvent", # Expects dict
        payload="this is a string, not a dict"
    )
    await websocket_relay_service.on_new_fill_recorded(event_invalid_payload)
    mock_connection_manager.send_to_client.assert_not_called()
    assert "Invalid payload type for NewFillRecordedEvent: <class 'str'>. Expected dict." in caplog.text
