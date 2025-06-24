import json
from typing import Optional
import redis.asyncio as aioredis # Ensure this matches the type in main.py
from logging import getLogger

# Assuming BaseEvent and other specific event types are importable
# from ..models.event_models import BaseEvent # This might cause circular import if models also import services.
# For now, expect event to be a Pydantic BaseModel that can be .model_dump_json()'d.
from pydantic import BaseModel # Use as a type hint for event if BaseEvent is problematic here.

logger = getLogger(__name__)

class EventServiceError(Exception):
    """Base exception for EventService errors."""
    pass

class EventService:
    def __init__(self, redis_client: aioredis.Redis, default_channel: str = "agent_events"):
        """
        Initializes the EventService.

        Args:
            redis_client: An initialized asyncio Redis client instance.
            default_channel: The default Redis channel to publish events to.
        """
        if redis_client is None:
            # This is a critical misconfiguration.
            # While we log an error, operations will fail.
            # Consider if this should raise an error immediately or if the service
            # can exist in a "disabled" state if no redis client is provided.
            # For now, it will log and then fail on publish_event.
            logger.error("EventService initialized with a None Redis client. Event publishing will fail.")
        self.redis_client = redis_client
        self.default_channel = default_channel
        logger.info(f"EventService initialized. Default publish channel: '{self.default_channel}'. Redis client is {'set' if redis_client else 'None'}.")

    async def publish_event(self, event: BaseModel, channel: Optional[str] = None) -> None:
        """
        Serializes a Pydantic event model to JSON and publishes it to a Redis channel.
        """
        if self.redis_client is None:
            logger.error("Cannot publish event: Redis client is not available in EventService.")
            # This makes the misconfiguration at init time a hard failure at runtime.
            raise EventServiceError("Redis client not available. Cannot publish event.")

        target_channel = channel if channel else self.default_channel

        try:
            # Ensure the event is a Pydantic model to have .model_dump_json()
            if not isinstance(event, BaseModel):
                logger.error(f"Invalid event type: {type(event)}. Event must be a Pydantic BaseModel.")
                raise EventServiceError(f"Event must be a Pydantic BaseModel, got {type(event)}.")

            # For Pydantic v2, model_dump_json() is the method.
            # For Pydantic v1, it was .json().
            # Assuming Pydantic v2 based on common modern usage.
            event_json = event.model_dump_json()

            await self.redis_client.publish(target_channel, event_json)

            # For logging, try to get event_type and event_id if they exist
            event_type_str = getattr(event, 'event_type', 'UnknownEventType')
            event_id_str = str(getattr(event, 'event_id', 'UnknownEventID')) # Ensure event_id is string for logging

            logger.debug(f"Successfully published event to Redis channel '{target_channel}': Type='{event_type_str}', ID='{event_id_str}'")
        except AttributeError as e:
            # This might happen if model_dump_json() is not available (e.g. not a Pydantic model, or wrong Pydantic version)
            logger.error(f"Failed to serialize event: {e}. Ensure event is a Pydantic v2 model. Event data (partial): {str(event)[:200]}", exc_info=True)
            raise EventServiceError(f"Failed to serialize event: {e}")
        except aioredis.RedisError as e:
            logger.error(f"Redis error publishing event to channel '{target_channel}': {e}", exc_info=True)
            raise EventServiceError(f"Redis error publishing event: {e}")
        except Exception as e:
            logger.error(f"Unexpected error publishing event to channel '{target_channel}': {e}", exc_info=True)
            raise EventServiceError(f"Unexpected error publishing event: {e}")
