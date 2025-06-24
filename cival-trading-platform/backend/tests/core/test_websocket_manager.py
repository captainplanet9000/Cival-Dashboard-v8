import pytest
import pytest_asyncio # For async fixtures if needed, though manager methods are mostly sync for connect/disconnect
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio # For testing broadcast

from fastapi import WebSocketDisconnect # Import for simulating disconnect
# Adjust path based on your project structure
from python_ai_services.core.websocket_manager import ConnectionManager
from python_ai_services.models.websocket_models import WebSocketEnvelope


@pytest.fixture
def manager() -> ConnectionManager:
    """Returns a fresh ConnectionManager instance for each test."""
    return ConnectionManager()

@pytest.fixture
def mock_websocket() -> MagicMock:
    """Returns a MagicMock for a WebSocket connection."""
    ws = MagicMock(spec=WebSocket) # Use MagicMock for sync methods like accept
    ws.accept = AsyncMock() # accept is async
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    # Add receive_text if ConnectionManager starts listening for client messages
    # ws.receive_text = AsyncMock()
    return ws

# --- Test ConnectionManager.connect ---
@pytest.mark.asyncio
async def test_connect_adds_client(manager: ConnectionManager, mock_websocket: MagicMock):
    client_id = "client1"
    await manager.connect(mock_websocket, client_id)
    assert client_id in manager.active_connections
    assert manager.active_connections[client_id] == mock_websocket
    mock_websocket.accept.assert_called_once()

# --- Test ConnectionManager.disconnect ---
@pytest.mark.asyncio
async def test_disconnect_removes_client(manager: ConnectionManager, mock_websocket: MagicMock):
    client_id = "client1"
    await manager.connect(mock_websocket, client_id) # Connect first

    manager.disconnect(client_id, mock_websocket)
    assert client_id not in manager.active_connections

@pytest.mark.asyncio
async def test_disconnect_unknown_client(manager: ConnectionManager, caplog):
    manager.disconnect("unknown_client_id")
    assert "Attempted to disconnect unknown or already disconnected client_id: unknown_client_id" in caplog.text

@pytest.mark.asyncio
async def test_disconnect_specific_websocket_instance(manager: ConnectionManager, mock_websocket: MagicMock):
    # This test is more relevant if multiple WebSockets per client_id are supported.
    # For the current simple dict, it behaves like normal disconnect.
    client_id = "client_multi_ws"
    await manager.connect(mock_websocket, client_id)
    manager.disconnect(client_id, mock_websocket) # Pass the websocket instance
    assert client_id not in manager.active_connections


# --- Test ConnectionManager.send_to_client ---
@pytest.mark.asyncio
async def test_send_to_client_sends_message(manager: ConnectionManager, mock_websocket: MagicMock):
    client_id = "client_send"
    await manager.connect(mock_websocket, client_id)

    message_payload = WebSocketEnvelope(event_type="TEST_EVENT", payload={"data": "test_data"})
    await manager.send_to_client(client_id, message_payload)

    mock_websocket.send_text.assert_called_once_with(message_payload.model_dump_json())

@pytest.mark.asyncio
async def test_send_to_client_unknown_client(manager: ConnectionManager, caplog):
    message_payload = WebSocketEnvelope(event_type="TEST_EVENT", payload={"data": "test_data"})
    await manager.send_to_client("unknown_client_for_send", message_payload)
    assert f"No active WebSocket connection for client_id 'unknown_client_for_send'" in caplog.text

@pytest.mark.asyncio
async def test_send_to_client_handles_exception_and_disconnects(manager: ConnectionManager, mock_websocket: MagicMock, caplog):
    client_id = "client_send_fail"
    await manager.connect(mock_websocket, client_id)

    mock_websocket.send_text.side_effect = Exception("Connection closed") # Simulate send error

    message_payload = WebSocketEnvelope(event_type="FAIL_EVENT", payload={"error": True})
    await manager.send_to_client(client_id, message_payload)

    assert f"Error sending WebSocket message to client '{client_id}': Connection closed" in caplog.text
    assert client_id not in manager.active_connections # Client should be disconnected

# --- Test ConnectionManager.broadcast_to_all ---
@pytest.mark.asyncio
async def test_broadcast_to_all_sends_to_multiple_clients(manager: ConnectionManager):
    client1_ws = MagicMock(spec=WebSocket); client1_ws.send_text = AsyncMock()
    client2_ws = MagicMock(spec=WebSocket); client2_ws.send_text = AsyncMock()

    # Connect clients (accept is not called by manager.connect if ws is already MagicMock)
    # To be precise, we should ensure accept is called if it's part of the connect contract.
    # For these mocks, accept() is part of mock_websocket fixture, but not these direct MagicMocks.
    # Let's assume they are "accepted" for this test's purpose.
    manager.active_connections["clientB1"] = client1_ws
    manager.active_connections["clientB2"] = client2_ws

    message_payload = WebSocketEnvelope(event_type="BROADCAST_EVENT", payload={"global": "update"})
    message_json = message_payload.model_dump_json()

    await manager.broadcast_to_all(message_payload)

    client1_ws.send_text.assert_called_once_with(message_json)
    client2_ws.send_text.assert_called_once_with(message_json)

@pytest.mark.asyncio
async def test_broadcast_to_all_no_clients(manager: ConnectionManager, caplog):
    message_payload = WebSocketEnvelope(event_type="BROADCAST_NO_CLIENTS", payload={})
    await manager.broadcast_to_all(message_payload)
    assert "No active WebSocket clients to broadcast to." in caplog.text

@pytest.mark.asyncio
async def test_broadcast_to_all_handles_send_exceptions_and_disconnects(manager: ConnectionManager, caplog):
    client_ok_ws = MagicMock(spec=WebSocket); client_ok_ws.send_text = AsyncMock()
    client_fail_ws = MagicMock(spec=WebSocket); client_fail_ws.send_text = AsyncMock(side_effect=Exception("Failed to send to this one"))

    manager.active_connections["client_ok"] = client_ok_ws
    manager.active_connections["client_fail"] = client_fail_ws

    message_payload = WebSocketEnvelope(event_type="BROADCAST_MIXED", payload={"status": "mixed_results"})
    message_json = message_payload.model_dump_json()

    await manager.broadcast_to_all(message_payload)

    client_ok_ws.send_text.assert_called_once_with(message_json)
    client_fail_ws.send_text.assert_called_once_with(message_json) # Attempt was made

    assert "client_ok" in manager.active_connections # Should remain connected
    assert "client_fail" not in manager.active_connections # Should be disconnected
    assert "Error sending during broadcast to client 'client_fail': Failed to send to this one" in caplog.text
    assert "Broadcast to client 'client_fail' failed with exception: Failed to send to this one" in caplog.text

# --- Test ConnectionManager as a Singleton ---
# (This is more of an integration aspect, but can be conceptually checked)
def test_connection_manager_singleton_instance_exists():
    # Attempt to import the singleton instance directly
    try:
        from python_ai_services.core.websocket_manager import connection_manager as global_manager_instance
        assert isinstance(global_manager_instance, ConnectionManager)
    except ImportError:
        pytest.fail("Could not import global connection_manager instance from core.websocket_manager")

