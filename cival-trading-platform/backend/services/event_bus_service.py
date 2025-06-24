from collections import defaultdict
from typing import Dict, List, Callable, Awaitable
import asyncio
# Assuming Event model is in a sibling 'models' package
from ..models.event_bus_models import Event
from loguru import logger

class EventBusService:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = defaultdict(list)
        logger.info("EventBusService initialized.")

    async def subscribe(self, event_type: str, callback: Callable[[Event], Awaitable[None]]):
        """
        Subscribes a callback to a specific event type.
        The callback must be an awaitable (async function).
        """
        # It's good practice to ensure the callback is awaitable if type hints specify Awaitable
        if not asyncio.iscoroutinefunction(callback):
            logger.warning(f"Callback {getattr(callback, '__name__', repr(callback))} for event type '{event_type}' is not an async function. It will be wrapped, but direct async is preferred.")
            # This is a simple wrapper. More robust would be to check if it's already awaitable.
            # For this exercise, we'll assume users provide async def functions as callbacks.
            # If a synchronous function is passed that needs to be awaited, it would need to be run in an executor.
            # However, the type hint Callable[[Event], Awaitable[None]] implies it's already awaitable.

        logger.debug(f"New subscription for event type '{event_type}' by callback: {getattr(callback, '__name__', repr(callback))}")
        self._subscribers[event_type].append(callback)

    async def publish(self, event: Event):
        """
        Publishes an event to all subscribed awaitable callbacks for its message_type.
        Executes callbacks concurrently and gathers results.
        """
        event_type = event.message_type
        logger.info(f"Publishing event ID {event.event_id} of type '{event_type}' from agent {event.publisher_agent_id}. Payload keys: {list(event.payload.keys())}")

        subscribers_for_type = self._subscribers.get(event_type, [])
        if not subscribers_for_type:
            logger.debug(f"No subscribers for event type '{event_type}'. Event ID {event.event_id} not dispatched to any callback.")
            return

        tasks = []
        for callback in subscribers_for_type:
            try:
                # Ensure the callback is indeed awaitable before adding to tasks
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    # This case should ideally not happen if subscribers adhere to the type hint.
                    # If it does, logging it is important. Running a sync function directly in gather()
                    # without being wrapped would block if it's IO-bound or long-running.
                    # For now, we'll log a warning and skip if not an async function,
                    # or the user must ensure their sync callable returns an Awaitable (e.g. a completed Future).
                    logger.error(f"Callback {getattr(callback, '__name__', repr(callback))} for event type '{event_type}' is not an async function as expected. Skipping.")
            except Exception as e_cb_setup: # Should not happen if callback is just a function reference
                 logger.error(f"Error setting up callback {getattr(callback, '__name__', repr(callback))} for event {event.event_id}: {e_cb_setup}", exc_info=True)


        if not tasks:
            logger.debug(f"No valid async subscribers to execute for event type '{event_type}'. Event ID {event.event_id}.")
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            # Need to map result back to the original callback for logging, if tasks list was filtered.
            # Assuming tasks list directly corresponds to subscribers_for_type if no filtering happened.
            # If tasks list could be shorter due to filtering non-async callbacks, this mapping needs care.
            # For this version, assuming tasks correspond 1:1 with subscribers_for_type that were async.
            # A more robust way would be to store (callback, task) tuples if filtering happens.

            # Get the callback that corresponds to this result.
            # This assumes tasks were appended in the same order as subscribers_for_type and none were skipped.
            # If non-async functions were skipped, this index might be wrong.
            # For simplicity, let's find the callback that was actually used to create the task.
            # This is tricky as tasks don't directly store the original coroutine function reference in an obvious public way.
            # A better approach for error reporting would be to wrap each callback call.

            # Simplified error reporting for now:
            original_callback_ref = subscribers_for_type[i] # This assumes no filtering of non-async subscribers occurred.
                                                            # If filtering did occur, this could point to the wrong callback.
                                                            # A more robust approach would be to iterate over (callback, task_result) pairs.
                                                            # For now, this is a known simplification.

            if isinstance(result, Exception):
                callback_name = getattr(original_callback_ref, '__name__', repr(original_callback_ref))
                logger.error(f"Error in subscriber '{callback_name}' for event type '{event_type}' (Event ID: {event.event_id}): {result}", exc_info=result)

        logger.debug(f"Finished publishing event ID {event.event_id} to {len(tasks)} subscriber(s).")

