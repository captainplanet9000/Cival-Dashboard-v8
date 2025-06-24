import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, call # Added call for checking multiple calls
import asyncio

from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.models.event_bus_models import Event

@pytest_asyncio.fixture
async def event_bus() -> EventBusService:
    """Provides a fresh instance of EventBusService for each test."""
    return EventBusService()

# --- Tests for subscribe ---
@pytest.mark.asyncio
async def test_subscribe_single_callback(event_bus: EventBusService):
    event_type = "TestEvent"
    mock_callback = AsyncMock()

    await event_bus.subscribe(event_type, mock_callback)

    assert event_type in event_bus._subscribers
    assert len(event_bus._subscribers[event_type]) == 1
    assert event_bus._subscribers[event_type][0] == mock_callback

@pytest.mark.asyncio
async def test_subscribe_multiple_callbacks_same_event(event_bus: EventBusService):
    event_type = "TestEventMultiple"
    mock_callback1 = AsyncMock()
    mock_callback2 = AsyncMock()

    await event_bus.subscribe(event_type, mock_callback1)
    await event_bus.subscribe(event_type, mock_callback2)

    assert len(event_bus._subscribers[event_type]) == 2
    assert mock_callback1 in event_bus._subscribers[event_type]
    assert mock_callback2 in event_bus._subscribers[event_type]

@pytest.mark.asyncio
async def test_subscribe_different_event_types(event_bus: EventBusService):
    event_type1 = "EventType1"
    event_type2 = "EventType2"
    mock_callback1 = AsyncMock()
    mock_callback2 = AsyncMock()

    await event_bus.subscribe(event_type1, mock_callback1)
    await event_bus.subscribe(event_type2, mock_callback2)

    assert len(event_bus._subscribers[event_type1]) == 1
    assert event_bus._subscribers[event_type1][0] == mock_callback1
    assert len(event_bus._subscribers[event_type2]) == 1
    assert event_bus._subscribers[event_type2][0] == mock_callback2

@pytest.mark.asyncio
async def test_subscribe_non_async_callback_logs_warning(event_bus: EventBusService):
    event_type = "NonAsyncTest"
    def sync_callback(event: Event): # Sync callback
        pass

    with patch.object(event_bus.logger, 'warning') as mock_log_warning:
        await event_bus.subscribe(event_type, sync_callback) # type: ignore
        # The service logs a warning but still adds it. The publish method will handle it.
        mock_log_warning.assert_called_once()
        assert "not an async function" in mock_log_warning.call_args[0][0]

    assert event_type in event_bus._subscribers
    assert len(event_bus._subscribers[event_type]) == 1


# --- Tests for publish ---
@pytest.mark.asyncio
async def test_publish_no_subscribers(event_bus: EventBusService):
    event = Event(publisher_agent_id="agent1", message_type="UnheardEvent", payload={})
    # No exception should be raised, and it should log that no subscribers were found
    with patch.object(event_bus.logger, 'debug') as mock_log_debug:
        await event_bus.publish(event)
        mock_log_debug.assert_any_call(f"No subscribers for event type '{event.message_type}'. Event ID {event.event_id} not dispatched to any callback.")

@pytest.mark.asyncio
async def test_publish_to_single_subscriber(event_bus: EventBusService):
    event_type = "SingleSubEvent"
    mock_callback = AsyncMock()
    await event_bus.subscribe(event_type, mock_callback)

    event_data = {"key": "value"}
    event = Event(publisher_agent_id="agent2", message_type=event_type, payload=event_data)
    await event_bus.publish(event)

    mock_callback.assert_called_once_with(event)

@pytest.mark.asyncio
async def test_publish_to_multiple_subscribers(event_bus: EventBusService):
    event_type = "MultiSubEvent"
    mock_callback1 = AsyncMock()
    mock_callback2 = AsyncMock()
    await event_bus.subscribe(event_type, mock_callback1)
    await event_bus.subscribe(event_type, mock_callback2)

    event = Event(publisher_agent_id="agent3", message_type=event_type, payload={})
    await event_bus.publish(event)

    mock_callback1.assert_called_once_with(event)
    mock_callback2.assert_called_once_with(event)

@pytest.mark.asyncio
async def test_publish_only_to_correct_event_type_subscribers(event_bus: EventBusService):
    event_type_A = "EventA"
    event_type_B = "EventB"
    mock_callback_A = AsyncMock()
    mock_callback_B = AsyncMock()

    await event_bus.subscribe(event_type_A, mock_callback_A)
    await event_bus.subscribe(event_type_B, mock_callback_B)

    event_A_instance = Event(publisher_agent_id="agentA", message_type=event_type_A, payload={})
    await event_bus.publish(event_A_instance)

    mock_callback_A.assert_called_once_with(event_A_instance)
    mock_callback_B.assert_not_called()

@pytest.mark.asyncio
async def test_publish_handles_subscriber_exception(event_bus: EventBusService):
    event_type = "ErrorEvent"
    mock_callback_good1 = AsyncMock()
    mock_callback_bad = AsyncMock(side_effect=ValueError("Subscriber error!"))
    mock_callback_good2 = AsyncMock()

    await event_bus.subscribe(event_type, mock_callback_good1)
    await event_bus.subscribe(event_type, mock_callback_bad)
    await event_bus.subscribe(event_type, mock_callback_good2)

    event = Event(publisher_agent_id="agentError", message_type=event_type, payload={})

    with patch.object(event_bus.logger, 'error') as mock_log_error:
        await event_bus.publish(event)

        mock_callback_good1.assert_called_once_with(event)
        mock_callback_bad.assert_called_once_with(event)
        mock_callback_good2.assert_called_once_with(event)

        # Check that an error was logged
        mock_log_error.assert_called_once()
        args, _ = mock_log_error.call_args
        assert "Error in subscriber" in args[0]
        assert "Subscriber error!" in str(args[1]) # The exception instance

@pytest.mark.asyncio
async def test_publish_with_non_async_subscriber_is_skipped(event_bus: EventBusService):
    event_type = "MixedSubscribers"

    async def async_cb(event: Event): pass
    def sync_cb(event: Event): pass # Not an async def

    mock_async_cb = AsyncMock(wraps=async_cb) # To check calls
    # We can't easily mock sync_cb to check calls if it's not called via await,
    # but we can check logs.

    await event_bus.subscribe(event_type, mock_async_cb)
    await event_bus.subscribe(event_type, sync_cb) # type: ignore

    event = Event(publisher_agent_id="agentMixed", message_type=event_type, payload={})

    with patch.object(event_bus.logger, 'error') as mock_log_error:
        await event_bus.publish(event)

        mock_async_cb.assert_called_once_with(event)
        # Check that an error was logged for the sync callback
        mock_log_error.assert_called_once()
        args, _ = mock_log_error.call_args
        assert "is not an async function as expected. Skipping." in args[0]

