from typing import Dict, List, Optional, Any, Tuple
from loguru import logger
import json
from datetime import datetime
import asyncio
import numpy as np
import uuid


# Supabase client import
try:
    from supabase import create_client, Client as SupabaseClient
    from supabase.lib.client_options import ClientOptions
    # from supabase.lib.errors import APIError as SupabaseAPIError # More specific error if needed
except ImportError:
    logger.warning("supabase-py components not found. Supabase functionality will be stubbed or may fail if used.")
    SupabaseClient = None
    ClientOptions = None
    # SupabaseAPIError = None

# Redis client import
try:
    import redis.asyncio as aioredis
except ImportError:
    logger.warning("redis.asyncio (aioredis) not found. Redis functionality will not be available.")
    aioredis = None

# Model imports
try:
    from ..models.crew_models import TaskStatus # For using enum values
except ImportError:
    logger.warning("TaskStatus enum not found from ..models.crew_models. Using string literals for status.")
    class TaskStatus: # Basic placeholder
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"


AsyncRedis = Any


class AgentPersistenceService:
    """
    Service dedicated to direct interactions with data persistence layers (Supabase and Redis)
    for agent-related data, including states, memories, and checkpoints.
    """
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None, redis_url: Optional[str] = None):
        self.supabase_url: Optional[str] = supabase_url
        self.supabase_key: Optional[str] = supabase_key
        self.redis_url: Optional[str] = redis_url

        self.supabase_client: Optional[SupabaseClient] = None
        self.redis_client: Optional[AsyncRedis] = None
        logger.info("AgentPersistenceService initialized (clients not yet connected).")

    async def connect_clients(self):
        # Supabase connection
        if self.supabase_url and self.supabase_key and not self.supabase_client and SupabaseClient and ClientOptions:
            try:
                logger.info(f"Attempting to create Supabase client for URL: {self.supabase_url[:20]}...")
                options = ClientOptions(postgrest_client_timeout=10, storage_client_timeout=10)
                self.supabase_client = create_client(self.supabase_url, self.supabase_key, options=options)
                logger.info("Successfully created Supabase client.")
            except Exception as e:
                logger.error(f"Failed to create Supabase client: {e}")
                self.supabase_client = None
        elif not SupabaseClient and self.supabase_url:
             logger.warning("Supabase URL is configured, but 'supabase-py' library is not available.")
        elif (self.supabase_url or self.supabase_key) and not (self.supabase_url and self.supabase_key):
            logger.error("Supabase URL or Key not fully configured. Both are required. Supabase client cannot be initialized.")
            self.supabase_client = None

        # Redis connection (Redis Cloud)
        if self.redis_url and not self.redis_client and aioredis:
            try:
                logger.info(f"Connecting to Redis Cloud...")
                # Redis Cloud requires decode_responses=True for string operations
                self.redis_client = await aioredis.from_url(self.redis_url, decode_responses=True)
                await self.redis_client.ping()
                logger.info("Successfully connected to Redis Cloud and ping successful.")
            except aioredis.RedisError as e:
                logger.error(f"Failed to connect to Redis Cloud: {e}")
                self.redis_client = None
            except Exception as e:
                logger.error(f"An unexpected error occurred during Redis connection: {e}")
                self.redis_client = None
        elif not aioredis and self.redis_url:
            logger.warning("Redis URL is configured, but 'redis.asyncio' library is not available.")

        if self.supabase_client and self.redis_client:
            logger.info("Supabase client created and Redis client connected.")
        elif self.supabase_client:
            logger.info("Supabase client created. Redis not configured or failed to connect.")
        elif self.redis_client:
            logger.info("Redis client connected. Supabase not configured or failed to connect/create.")
        else:
            logger.warning("Neither Supabase nor Redis clients are configured/connected/created.")

    async def close_clients(self):
        if self.redis_client:
            logger.info("Closing Redis connection...")
            try:
                await self.redis_client.close()
                logger.info("Redis connection closed.")
            except aioredis.RedisError as e:
                logger.error(f"Error closing Redis connection: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during Redis close: {e}")
            finally:
                self.redis_client = None
        if self.supabase_client:
            logger.info("Supabase client conceptually 'closed' (typically no explicit close needed for REST client).")
            self.supabase_client = None
        logger.info("Client connections are now considered closed.")

    # ... [Existing Redis and Agent State/Memory/Checkpoint Supabase methods remain here] ...
    async def save_realtime_state_to_redis(self, agent_id: str, state_data: Dict, ttl_seconds: int = 3600) -> bool:
        if not self.redis_client:
            logger.error(f"Redis client not available. Cannot save state for agent '{agent_id}'.")
            return False
        key = f"agent_realtime_state:{agent_id}"
        try:
            serialized_state = json.dumps(state_data)
            await self.redis_client.setex(key, ttl_seconds, serialized_state)
            logger.info(f"Saved real-time state for agent '{agent_id}' to Redis. Key: '{key}', TTL: {ttl_seconds}s.")
            return True
        except json.JSONEncodeError as e:
            logger.error(f"Failed to serialize state for agent '{agent_id}' for Redis: {e}")
            return False
        except aioredis.RedisError as e: # pyright: ignore [reportUnboundVariable]
            logger.error(f"Redis error saving state for agent '{agent_id}': {e}") # type: ignore
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving state to Redis for agent '{agent_id}': {e}")
            return False

    async def get_realtime_state_from_redis(self, agent_id: str) -> Optional[Dict]:
        if not self.redis_client:
            logger.error(f"Redis client not available. Cannot get state for agent '{agent_id}'.")
            return None
        key = f"agent_realtime_state:{agent_id}"
        try:
            serialized_state = await self.redis_client.get(key)
            if serialized_state:
                logger.debug(f"Cache hit from Redis for real-time state of agent '{agent_id}'. Key: '{key}'")
                # With decode_responses=True, Redis returns strings directly
                if isinstance(serialized_state, str):
                    return json.loads(serialized_state)
                elif isinstance(serialized_state, bytes):
                    return json.loads(serialized_state.decode('utf-8'))
                else:
                    return serialized_state
            else:
                logger.debug(f"Cache miss from Redis for real-time state of agent '{agent_id}'. Key: '{key}'")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize state from Redis for agent '{agent_id}': {e}. Key: '{key}'. Cache entry might be corrupt.")
            return None
        except aioredis.RedisError as e: # pyright: ignore [reportUnboundVariable]
            logger.error(f"Redis error getting state for agent '{agent_id}': {e}") # type: ignore
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting state from Redis for agent '{agent_id}': {e}. Key: '{key}'")
            return None

    async def delete_realtime_state_from_redis(self, agent_id: str) -> bool:
        if not self.redis_client:
            logger.error(f"Redis client not available. Cannot delete state for agent '{agent_id}'.")
            return False
        key = f"agent_realtime_state:{agent_id}"
        try:
            result = await self.redis_client.delete(key)
            if result > 0:
                logger.info(f"Deleted real-time state for agent '{agent_id}' from Redis. Key: '{key}'.")
            else:
                logger.info(f"No real-time state found in Redis for agent '{agent_id}' to delete. Key: '{key}'.")
            return True
        except aioredis.RedisError as e: # pyright: ignore [reportUnboundVariable]
            logger.error(f"Redis error deleting state for agent '{agent_id}': {e}") # type: ignore
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting state from Redis for agent '{agent_id}': {e}. Key: '{key}'")
            return False

    async def save_agent_state_to_supabase(self, agent_id: str, strategy_type: str, state: Dict, memory_references: Optional[List[str]] = None) -> Optional[Dict]:
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot save state for agent '{agent_id}'.")
            return None
        record_to_upsert = {
            "agent_id": agent_id, "strategy_type": strategy_type,
            "state": state, "memory_references": memory_references or []
        }
        try:
            logger.info(f"Attempting to save/update agent state for '{agent_id}' to Supabase.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_states")
                .upsert(record_to_upsert, on_conflict="agent_id")
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully saved/updated agent state for '{agent_id}' to Supabase.")
                return response.data[0]
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error saving state for '{agent_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return None
            else:
                logger.warning(f"Supabase returned no data and no error for save_agent_state '{agent_id}'. Response: {response}")
                return None
        except Exception as e:
            logger.exception(f"Supabase client error saving state for agent '{agent_id}': {e}")
            return None

    async def get_agent_state_from_supabase(self, agent_id: str) -> Optional[Dict]:
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot get state for agent '{agent_id}'.")
            return None
        try:
            logger.info(f"Attempting to retrieve agent state for '{agent_id}' from Supabase.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_states")
                .select("*")
                .eq("agent_id", agent_id)
                .limit(1)
                .maybe_single()
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully retrieved agent state for '{agent_id}' from Supabase.")
                return response.data
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error getting state for '{agent_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return None
            else:
                logger.info(f"No agent state found in Supabase for '{agent_id}'.")
                return None
        except Exception as e:
            logger.exception(f"Supabase client error getting state for agent '{agent_id}': {e}")
            return None

    async def delete_agent_state_from_supabase(self, agent_id: str) -> bool:
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot delete state for agent '{agent_id}'.")
            return False
        try:
            logger.info(f"Attempting to delete agent state for '{agent_id}' from Supabase.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_states")
                .delete()
                .eq("agent_id", agent_id)
                .execute
            )
            if hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error deleting state for '{agent_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return False
            logger.info(f"Delete operation for agent state '{agent_id}' completed. Data (if any): {response.data}")
            return True
        except Exception as e:
            logger.exception(f"Supabase client error deleting state for agent '{agent_id}': {e}")
            return False

    async def save_agent_memory_to_supabase(self, agent_id: str, content: str, embedding: List[float], metadata: Optional[Dict] = None) -> Optional[Dict]:
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot save memory for agent '{agent_id}'.")
            return None
        record_to_insert = {
            "agent_id": agent_id, "content": content,
            "embedding": embedding, "metadata": metadata or {}
        }
        try:
            logger.info(f"Attempting to save agent memory for '{agent_id}' to Supabase.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_memories")
                .insert(record_to_insert)
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully saved agent memory for '{agent_id}' to Supabase.")
                return response.data[0]
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error saving memory for '{agent_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return None
            else:
                logger.warning(f"Supabase returned no data and no error for save_agent_memory '{agent_id}'.")
                return None
        except Exception as e:
            logger.exception(f"Supabase client error saving memory for agent '{agent_id}': {e}")
            return None

    async def search_agent_memories_in_supabase(self, agent_id: str, query_embedding: List[float], top_k: int = 5, match_threshold: Optional[float] = None) -> List[Dict]:
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot search memories for agent '{agent_id}'.")
            return []
        rpc_params: Dict[str, Any] = {
            "agent_id_filter": agent_id,
            "query_embedding": query_embedding,
            "match_count": top_k
        }
        if match_threshold is not None:
            rpc_params["match_threshold"] = match_threshold
        rpc_function_name = "match_agent_memories"
        try:
            logger.info(f"Attempting to search memories for '{agent_id}' via RPC '{rpc_function_name}'.")
            response = await asyncio.to_thread(
                self.supabase_client.rpc(rpc_function_name, rpc_params)
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully retrieved {len(response.data)} memories for agent '{agent_id}'.")
                return response.data
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase RPC error searching memories for '{agent_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return []
            else:
                logger.info(f"No memories found or Supabase RPC returned no data for '{agent_id}'.")
                return []
        except Exception as e:
            logger.exception(f"Supabase client error searching memories for agent '{agent_id}': {e}")
            return []

    async def save_agent_checkpoint_to_supabase(self, agent_id: str, state: Dict,
                                                strategy_type: Optional[str] = None,
                                                memory_references: Optional[List[str]] = None,
                                                metadata: Optional[Dict] = None) -> Optional[Dict]:
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot save checkpoint for agent '{agent_id}'.")
            return None
        checkpoint_id = str(uuid.uuid4())
        current_metadata = metadata.copy() if metadata else {}
        if strategy_type: current_metadata['strategy_type'] = strategy_type
        if memory_references: current_metadata['memory_references'] = memory_references
        record_to_insert = {
            "checkpoint_id": checkpoint_id, "agent_id": agent_id,
            "state_snapshot": state, "metadata": current_metadata
        }
        try:
            logger.info(f"Attempting to save agent checkpoint for '{agent_id}' to Supabase.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_checkpoints")
                .insert(record_to_insert)
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully saved agent checkpoint for '{agent_id}', ID: {checkpoint_id}.")
                return response.data[0]
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error saving checkpoint for '{agent_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return None
            else:
                logger.warning(f"Supabase returned no data and no error for save_agent_checkpoint '{agent_id}'.")
                return None
        except Exception as e:
            logger.exception(f"Supabase client error saving checkpoint for agent '{agent_id}': {e}")
            return None

    async def get_agent_checkpoint_from_supabase(self, checkpoint_id: str) -> Optional[Dict]:
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot get checkpoint '{checkpoint_id}'.")
            return None
        try:
            logger.info(f"Attempting to retrieve agent checkpoint '{checkpoint_id}' from Supabase.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_checkpoints")
                .select("*")
                .eq("checkpoint_id", checkpoint_id)
                .maybe_single()
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully retrieved agent checkpoint '{checkpoint_id}'.")
                return response.data
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error getting checkpoint '{checkpoint_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return None
            else:
                logger.info(f"No agent checkpoint found in Supabase for ID '{checkpoint_id}'.")
                return None
        except Exception as e:
            logger.exception(f"Supabase client error getting checkpoint '{checkpoint_id}': {e}")
            return None

    async def list_agent_checkpoints_from_supabase(self, agent_id: str, limit: int = 10) -> List[Dict]:
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot list checkpoints for agent '{agent_id}'.")
            return []
        try:
            logger.info(f"Attempting to list last {limit} checkpoints for agent '{agent_id}' from Supabase.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_checkpoints")
                .select("checkpoint_id, agent_id, created_at, metadata")
                .eq("agent_id", agent_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully retrieved {len(response.data)} checkpoints for agent '{agent_id}'.")
                return response.data
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error listing checkpoints for '{agent_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return []
            else:
                logger.info(f"No checkpoints found or Supabase returned no data for agent '{agent_id}'.")
                return []
        except Exception as e:
            logger.exception(f"Supabase client error listing checkpoints for agent '{agent_id}': {e}")
            return []

    # --- AgentTask CRUD Methods ---

    async def create_agent_task(self, crew_id: str, inputs: Dict, task_id_str: Optional[str] = None, status: str = TaskStatus.PENDING.value, logs_summary: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Creates a new agent task record in the `agent_tasks` table."""
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot create agent task for crew '{crew_id}'.")
            return None

        record_to_insert = {
            "crew_id": crew_id,
            "inputs": inputs,
            "status": status,
            "start_time": datetime.utcnow().isoformat() # Explicitly set, DB default also exists
        }
        if task_id_str: # If task_id is client-generated (e.g. from Pydantic default_factory)
            record_to_insert["task_id"] = task_id_str
        if logs_summary is not None:
            record_to_insert["logs_summary"] = logs_summary

        try:
            logger.info(f"Attempting to create agent task for crew '{crew_id}'. Inputs: {str(inputs)[:100]}")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_tasks")
                .insert(record_to_insert)
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully created agent task for crew '{crew_id}'. Task ID: {response.data[0].get('task_id')}")
                return response.data[0]
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error creating agent task for crew '{crew_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return None
            else:
                logger.warning(f"Supabase returned no data and no error for create_agent_task for crew '{crew_id}'.")
                return None
        except Exception as e:
            logger.exception(f"Supabase client error creating agent task for crew '{crew_id}': {e}")
            return None

    async def update_agent_task_status(self, task_id: str, status: str, error_message: Optional[str] = None) -> Optional[Dict]:
        """Updates the status and optionally an error message for an agent task."""
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot update status for task '{task_id}'.")
            return None

        update_payload: Dict[str, Any] = {"status": status}
        # DB trigger handles updated_at, but explicit set is fine.
        # Let DB handle updated_at to avoid potential clock skew issues if not strictly needed here.

        current_time_iso = datetime.utcnow().isoformat()
        if error_message is not None:
            update_payload["error_message"] = error_message

        # The DDL for agent_tasks has start_time DEFAULT now().
        # Only update end_time when task reaches a terminal state.
        if status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
            update_payload["end_time"] = current_time_iso

        try:
            logger.info(f"Attempting to update status for task '{task_id}' to '{status}'.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_tasks")
                .update(update_payload)
                .eq("task_id", task_id)
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully updated status for task '{task_id}'.")
                return response.data[0]
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error updating task status for '{task_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return None
            else: # No data and no error might mean record not found or no change needed for update
                logger.warning(f"Supabase returned no data and no error for update_agent_task_status on task '{task_id}'. May indicate task not found or no change.")
                # To confirm if it was found, a select might be needed, or rely on returned data length.
                # For now, assume if no error, it's operationally fine.
                return None # Or return a specific dict indicating no update occurred if needed
        except Exception as e:
            logger.exception(f"Supabase client error updating task status for '{task_id}': {e}")
            return None

    async def update_agent_task_result(self, task_id: str, output: Any, status: str = TaskStatus.COMPLETED.value, logs_summary: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Updates the output, status, end_time, and optionally logs summary for an agent task."""
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot update result for task '{task_id}'.")
            return None

        current_time_iso = datetime.utcnow().isoformat()
        update_payload: Dict[str, Any] = {
            "output": output, # Should be JSON serializable
            "status": status,
            "end_time": current_time_iso,
            # "updated_at": current_time_iso # Let DB trigger handle updated_at
        }
        if logs_summary is not None:
            update_payload["logs_summary"] = logs_summary

        try:
            logger.info(f"Attempting to update result for task '{task_id}'. Status: {status}.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_tasks")
                .update(update_payload)
                .eq("task_id", task_id)
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully updated result for task '{task_id}'.")
                return response.data[0]
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error updating task result for '{task_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return None
            else:
                logger.warning(f"Supabase returned no data and no error for update_agent_task_result on task '{task_id}'. May indicate task not found.")
                return None
        except Exception as e:
            logger.exception(f"Supabase client error updating task result for '{task_id}': {e}")
            return None

    async def get_agent_task(self, task_id: str) -> Optional[Dict]:
        """Retrieves a specific agent task by its ID from `agent_tasks` table."""
        if not self.supabase_client:
            logger.error(f"Supabase client not available. Cannot get task '{task_id}'.")
            return None
        try:
            logger.info(f"Attempting to retrieve task '{task_id}'.")
            response = await asyncio.to_thread(
                self.supabase_client.table("agent_tasks")
                .select("*")
                .eq("task_id", task_id)
                .maybe_single() # Returns one record or None
                .execute
            )
            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully retrieved task '{task_id}'.")
                return response.data
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error getting task '{task_id}': {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return None
            else: # No data and no error means not found by maybe_single()
                logger.info(f"No task found for ID '{task_id}'.")
                return None
        except Exception as e:
            logger.exception(f"Supabase client error getting task '{task_id}': {e}")
            return None

    async def list_agent_tasks(self, crew_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Lists agent tasks from `agent_tasks`, optionally filtered by crew_id and/or status, ordered by start_time descending."""
        if not self.supabase_client:
            logger.error("Supabase client not available. Cannot list agent tasks.")
            return []
        try:
            logger.info(f"Listing agent tasks. Filters: crew_id='{crew_id}', status='{status}', limit={limit}.")
            query = self.supabase_client.table("agent_tasks").select("*").order("start_time", desc=True).limit(limit)
            if crew_id:
                query = query.eq("crew_id", crew_id)
            if status:
                query = query.eq("status", status)

            response = await asyncio.to_thread(query.execute)

            if hasattr(response, 'data') and response.data:
                logger.info(f"Successfully retrieved {len(response.data)} tasks.")
                return response.data
            elif hasattr(response, 'error') and response.error:
                logger.error(f"Supabase API error listing tasks: {response.error.message} (Code: {response.error.code if hasattr(response.error, 'code') else 'N/A'})")
                return []
            else: # No data and no error means empty result set matching criteria
                logger.info("No tasks found matching criteria or Supabase returned no data.")
                return []
        except Exception as e:
            logger.exception(f"Supabase client error listing tasks: {e}")
            return []

    async def list_and_count_agent_tasks_paginated(
        self,
        crew_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        start_date_from: Optional[datetime] = None,
        start_date_to: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lists agent tasks with pagination and filtering, and provides a total count
        for the filtered query. Returns raw dictionaries from the database.
        """
        if not self.supabase_client:
            logger.error("Supabase client not available. Cannot list agent tasks.")
            return ([], 0)

        total_count = 0
        tasks_list: List[Dict[str, Any]] = []

        try:
            # Count Query
            query_builder_count = self.supabase_client.table("agent_tasks").select("task_id", count="exact")
            if crew_id:
                query_builder_count = query_builder_count.eq("crew_id", crew_id)
            if status:
                query_builder_count = query_builder_count.eq("status", status.value) # Use enum value
            if start_date_from:
                query_builder_count = query_builder_count.gte("start_time", start_date_from.isoformat())
            if start_date_to:
                query_builder_count = query_builder_count.lte("start_time", start_date_to.isoformat())

            logger.debug(f"Executing count query for agent_tasks with filters: crew_id={crew_id}, status={status}, from={start_date_from}, to={start_date_to}")
            count_response = await asyncio.to_thread(query_builder_count.execute)

            if hasattr(count_response, 'count') and count_response.count is not None:
                total_count = count_response.count
                logger.info(f"Total tasks matching filters: {total_count}")
            elif hasattr(count_response, 'error') and count_response.error:
                logger.error(f"Supabase API error during count query for agent_tasks: {count_response.error.message}")
                # Return 0,0 and let the caller decide how to handle partial failure
                return ([], 0)
            else:
                logger.warning("Supabase count query for agent_tasks returned no count and no error.")


            # Data Query (only if there's a potential count, or always try if desired)
            if total_count > 0 or offset == 0 : # Only query data if there's something to query or it's the first page
                query_builder_data = self.supabase_client.table("agent_tasks").select("*")
                if crew_id:
                    query_builder_data = query_builder_data.eq("crew_id", crew_id)
                if status:
                    query_builder_data = query_builder_data.eq("status", status.value)
                if start_date_from:
                    query_builder_data = query_builder_data.gte("start_time", start_date_from.isoformat())
                if start_date_to:
                    query_builder_data = query_builder_data.lte("start_time", start_date_to.isoformat())

                query_builder_data = query_builder_data.order("start_time", desc=True).range(offset, offset + limit - 1)

                logger.debug(f"Executing data query for agent_tasks with filters and pagination: offset={offset}, limit={limit}")
                response = await asyncio.to_thread(query_builder_data.execute)

                if hasattr(response, 'data') and response.data is not None:
                    tasks_list = response.data
                    logger.info(f"Retrieved {len(tasks_list)} tasks for the current page.")
                elif hasattr(response, 'error') and response.error:
                    logger.error(f"Supabase API error during data query for agent_tasks: {response.error.message}")
                    # tasks_list remains empty, total_count might be from earlier
                else:
                    logger.info("No tasks found for the current page or Supabase returned no data.")

            return (tasks_list, total_count)

        except Exception as e:
            logger.exception(f"Supabase client error in list_and_count_agent_tasks_paginated: {e}")
            return ([], 0)


# Appended by subtask worker: (This should remain at the end of the file)
AGENT_STATE_MANAGER_REFACTORING_PLAN = """
=== AgentStateManager Refactoring Plan ===

The existing `AgentStateManager` (in `agent_state_manager.py`) will be refactored to use this `AgentPersistenceService`.

Key changes to `AgentStateManager`:
1.  `__init__(self, persistence_service: AgentPersistenceService)`:
    *   It will receive an instance of `AgentPersistenceService`.
    *   The `db_connection_string` and `base_url` (for httpx) will be removed.
2.  `async get_agent_state(self, agent_id: str) -> Dict`:
    *   Priority: In-memory cache (`self.in_memory_cache`).
    *   Then: `await self.persistence_service.get_realtime_state_from_redis(agent_id)`. If found, update in-memory cache and return.
    *   Then: `await self.persistence_service.get_agent_state_from_supabase(agent_id)`. If found, update in-memory and Redis cache, then return.
    *   If not found anywhere, return default empty state and cache it.
3.  `async update_agent_state(self, agent_id: str, state: Dict, strategy_type: str = "unknown", memory_references: Optional[List[str]] = None) -> Dict`:
    *   Persist to Supabase: `updated_record = await self.persistence_service.save_agent_state_to_supabase(agent_id, strategy_type, state, memory_references)`.
    *   Persist/update Redis: `await self.persistence_service.save_realtime_state_to_redis(agent_id, state, ttl)`. (TTL needs to be defined/configured).
    *   Update in-memory cache: `self.in_memory_cache[agent_id] = updated_record` (or use the returned state from Supabase which includes `updated_at`).
    *   Return the updated state/record.
4.  `update_state_field`: Will use the refactored `get_agent_state` and `update_agent_state`.
5.  `delete_agent_state`: Will call `await self.persistence_service.delete_agent_state_from_supabase(agent_id)` and `await self.persistence_service.delete_realtime_state_from_redis(agent_id)`, then clear in-memory cache.
6.  `save_trading_decision`: The aspect of this method that *updates agent state with decision history* will use the refactored `get_agent_state` and `update_agent_state`. The part that POSTs to `/decisions` (if it's a separate log like an audit trail) might remain an HTTP call or be refactored if decisions are also purely DB-driven via `AgentPersistenceService`. For now, focus on the state persistence aspect.
7.  `create_agent_checkpoint`: Will call `current_state = await self.get_agent_state(agent_id)` and then `await self.persistence_service.save_agent_checkpoint_to_supabase(agent_id, current_state.get("state", {}), metadata)`.
8.  `restore_agent_checkpoint`: Will call `checkpoint_data = await self.persistence_service.get_agent_checkpoint_from_supabase(checkpoint_id)`. If found, it will use the state from `checkpoint_data` to call the refactored `update_agent_state` to make it the current active state.

This refactoring will centralize direct database/Redis interaction within `AgentPersistenceService`, making `AgentStateManager` a higher-level orchestrator of state access and caching.
"""
