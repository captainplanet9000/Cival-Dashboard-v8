"""
Agent State Manager for persistent storage of agent trading states
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio # For asyncio.Lock
from loguru import logger

# Assuming AgentPersistenceService is in the same package directory
from .agent_persistence_service import AgentPersistenceService


class AgentStateManager:
    """
    Service for managing agent states with multiple layers of caching and persistence.
    Orchestrates state retrieval and updates using AgentPersistenceService.
    """
    
    def __init__(self, persistence_service: AgentPersistenceService, redis_realtime_ttl_seconds: int = 3600):
        self.persistence_service: AgentPersistenceService = persistence_service
        self.redis_realtime_ttl_seconds: int = redis_realtime_ttl_seconds
        self.in_memory_cache: Dict[str, Dict] = {}
        self.lock: asyncio.Lock = asyncio.Lock()
        logger.info("AgentStateManager initialized with AgentPersistenceService.")
    
    async def get_agent_state(self, agent_id: str) -> Dict:
        """
        Retrieve the agent's state, checking in-memory cache, then Redis, then Supabase.
        Returns a dictionary representing the agent's state record from Supabase,
        or a default structure if not found.
        The structure returned is expected to be the full record as stored in/retrieved from Supabase.
        """
        logger.debug(f"Getting state for agent: {agent_id}")
        
        # 1. Check in-memory cache first
        if agent_id in self.in_memory_cache:
            logger.debug(f"In-memory cache hit for agent: {agent_id}")
            return self.in_memory_cache[agent_id]
        
        # 2. Check Redis
        try:
            redis_full_record = await self.persistence_service.get_realtime_state_from_redis(agent_id)
            if redis_full_record is not None:
                logger.debug(f"Redis cache hit for agent: {agent_id}.")
                self.in_memory_cache[agent_id] = redis_full_record
                return redis_full_record
        except Exception as e:
            logger.error(f"Error accessing Redis for agent {agent_id} during get_agent_state: {e}. Proceeding to Supabase.")

        # 3. Check Supabase (persistent state)
        try:
            supabase_record = await self.persistence_service.get_agent_state_from_supabase(agent_id)
            if supabase_record is not None:
                logger.debug(f"Supabase data found for agent: {agent_id}.")
                self.in_memory_cache[agent_id] = supabase_record
                await self.persistence_service.save_realtime_state_to_redis(
                    agent_id,
                    supabase_record,
                    self.redis_realtime_ttl_seconds
                )
                return supabase_record
        except Exception as e:
            logger.critical(f"CRITICAL: Supabase query failed for {agent_id} during get_agent_state. State is unknown. Error: {e}")

        # 4. Not found in any layer or Supabase failed, return default empty state and cache it (in-memory only for default)
        logger.warning(f"No state found for agent {agent_id} in any persistence layer or Supabase failed. Returning default empty state.")
        empty_state_record = {
            "agent_id": agent_id,
            "state": {},
            "strategy_type": "default",
            "memory_references": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "source": "new_default"
        }
        self.in_memory_cache[agent_id] = empty_state_record
        return empty_state_record
    
    async def update_agent_state(
        self,
        agent_id: str,
        state: Dict,
        strategy_type: str = "unknown",
        memory_references: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Update the agent's state in Supabase (as source of truth), then update Redis and in-memory cache.
        Returns the persisted state record from Supabase, or None on failure.
        """
        logger.info(f"Updating state for agent: {agent_id}. Strategy type: {strategy_type}. State preview: {str(state)[:100]}...")
        
        async with self.lock:
            try:
                updated_supa_record = await self.persistence_service.save_agent_state_to_supabase(
                    agent_id, strategy_type, state, memory_references
                )
                
                if not updated_supa_record:
                    logger.error(f"Failed to save state to Supabase for agent {agent_id}. Aborting update.")
                    return None

                redis_success = await self.persistence_service.save_realtime_state_to_redis(
                    agent_id, updated_supa_record, self.redis_realtime_ttl_seconds
                )
                if not redis_success:
                    logger.warning(f"Failed to save state to Redis for agent {agent_id}, but Supabase save was successful.")

                self.in_memory_cache[agent_id] = updated_supa_record

                logger.info(f"Successfully updated state for agent: {agent_id}.")
                return updated_supa_record
                    
            except Exception as e:
                logger.exception(f"Unexpected error updating agent state for {agent_id}: {e}")
                return None
    
    async def update_state_field(self, agent_id: str, field: str, value: Any) -> Optional[Dict]:
        """Update a specific field in the agent's 'state' dictionary."""
        logger.info(f"Attempting to update field '{field}' for agent: {agent_id}.")
        
        try:
            current_full_record = await self.get_agent_state(agent_id)
            
            state_dict_to_modify = current_full_record.get("state", {}).copy()
            strategy_type = current_full_record.get("strategy_type", "unknown_on_field_update")
            memory_references = current_full_record.get("memory_references")

            state_dict_to_modify[field] = value
            
            logger.debug(f"Calling update_agent_state for field update on agent {agent_id}.")
            return await self.update_agent_state(
                agent_id,
                state_dict_to_modify,
                strategy_type=strategy_type,
                memory_references=memory_references
            )
            
        except Exception as e:
            logger.exception(f"Error updating state field '{field}' for agent {agent_id}: {e}")
            return None
    
    async def delete_agent_state(self, agent_id: str) -> bool:
        """Delete the agent's state from all persistence layers and caches."""
        logger.info(f"Attempting to delete state for agent: {agent_id}.")
        
        async with self.lock:
            try:
                supa_deleted = await self.persistence_service.delete_agent_state_from_supabase(agent_id)
                redis_op_success = await self.persistence_service.delete_realtime_state_from_redis(agent_id)

                if agent_id in self.in_memory_cache:
                    del self.in_memory_cache[agent_id]
                    logger.debug(f"Removed agent {agent_id} from in-memory cache.")

                if supa_deleted:
                    logger.info(f"Deletion process run for agent {agent_id}. Supabase main delete success: {supa_deleted}. Redis op success: {redis_op_success}.")
                else:
                    logger.warning(f"Supabase deletion failed or record not found for agent {agent_id}. Redis op success: {redis_op_success}.")
                return supa_deleted
                    
            except Exception as e:
                logger.exception(f"Unexpected error deleting agent state for {agent_id}: {e}")
                return False
    
    async def save_trading_decision(self, agent_id: str, decision: Dict) -> Optional[Dict]:
        """
        Updates the agent's state with the new trading decision in its history.
        Note: The original httpx call to log decisions to an external endpoint has been removed.
        If such functionality is required, it should be handled by a dedicated service or explicitly
        called by the orchestrating code that uses AgentStateManager.
        """
        logger.info(f"Attempting to update agent state with trading decision for agent: {agent_id}")
        
        try:
            await self._update_decision_history(agent_id, decision)
            logger.info(f"Successfully updated decision history in state for agent {agent_id}.")
            return {"status": "decision_history_updated_in_state", "agent_id": agent_id, "decision_timestamp": decision.get("timestamp")}
        except Exception as e:
            logger.exception(f"Failed to save trading decision to agent state for {agent_id}: {e}")
            raise
            
    async def _update_decision_history(self, agent_id: str, decision: Dict):
        """Helper to update decision history in agent's 'state' dictionary."""
        logger.debug(f"Updating decision history for agent {agent_id}.")
        current_full_record = await self.get_agent_state(agent_id)

        state_dict_to_modify = current_full_record.get("state", {}).copy()
        strategy_type = current_full_record.get("strategy_type", "decision_history_update")
        memory_references = current_full_record.get("memory_references")

        if "decisionHistory" not in state_dict_to_modify:
            state_dict_to_modify["decisionHistory"] = []

        if "timestamp" not in decision:
            decision["timestamp"] = datetime.utcnow().isoformat()

        max_history = 50
        state_dict_to_modify["decisionHistory"] = [decision] + state_dict_to_modify["decisionHistory"][:max_history-1]

        updated_record = await self.update_agent_state(
            agent_id,
            state_dict_to_modify,
            strategy_type=strategy_type,
            memory_references=memory_references
        )
        if not updated_record:
             raise Exception(f"Failed to save updated decision history for agent {agent_id} via update_agent_state.")
        else:
            logger.debug(f"Decision history updated and saved for agent {agent_id}.")
            
    async def create_agent_checkpoint(self, agent_id: str, metadata: Optional[Dict] = None) -> Optional[Dict]:
        """Create a checkpoint of the agent's current 'state' dictionary using AgentPersistenceService."""
        logger.info(f"Creating checkpoint for agent: {agent_id} with metadata: {metadata}")
        
        try:
            current_state_record = await self.get_agent_state(agent_id)
            state_to_checkpoint = current_state_record.get("state", {})
            
            if metadata is None: metadata = {}
            if "strategy_type" not in metadata and current_state_record.get("strategy_type"):
                metadata["strategy_type"] = current_state_record.get("strategy_type")
            
            checkpoint_result = await self.persistence_service.save_agent_checkpoint_to_supabase(
                agent_id,
                state_to_checkpoint,
                metadata
            )

            if checkpoint_result:
                logger.info(f"Successfully created checkpoint for agent: {agent_id}. ID: {checkpoint_result.get('checkpoint_id')}")
                return checkpoint_result
            else:
                logger.error(f"Failed to save checkpoint to Supabase for agent {agent_id}.")
                return None
                
        except Exception as e:
            logger.exception(f"Error creating agent checkpoint for {agent_id}: {e}")
            return None
    
    async def restore_agent_checkpoint(self, agent_id: str, checkpoint_id: str) -> Optional[Dict]:
        """Restore an agent's state from a checkpoint using AgentPersistenceService."""
        logger.info(f"Attempting to restore checkpoint {checkpoint_id} for agent: {agent_id}")
        
        try:
            checkpoint_data = await self.persistence_service.get_agent_checkpoint_from_supabase(checkpoint_id)

            if not checkpoint_data:
                logger.error(f"Checkpoint {checkpoint_id} not found.")
                return None

            if checkpoint_data.get("agent_id") != agent_id:
                logger.error(f"Checkpoint {checkpoint_id} agent_id mismatch. Expected {agent_id}, found {checkpoint_data.get('agent_id')}.")
                return None

            state_to_restore = checkpoint_data.get("state")

            if state_to_restore is None:
                logger.error(f"Checkpoint {checkpoint_id} for agent {agent_id} does not contain a valid 'state' field in its data.")
                return None

            metadata_from_checkpoint = checkpoint_data.get("metadata", {})
            strategy_type_from_checkpoint = metadata_from_checkpoint.get("strategy_type", "restored_from_checkpoint")

            logger.info(f"Attempting to update agent {agent_id} state from checkpoint {checkpoint_id}.")
            updated_state_record = await self.update_agent_state(
                agent_id,
                state_to_restore,
                strategy_type=strategy_type_from_checkpoint
            )

            if updated_state_record:
                logger.info(f"Successfully restored state for agent {agent_id} from checkpoint {checkpoint_id}.")
                return updated_state_record
            else:
                logger.error(f"Failed to update agent state after restoring checkpoint {checkpoint_id} for agent {agent_id}.")
                return None
                
        except Exception as e:
            logger.exception(f"Error restoring agent checkpoint for {agent_id} from {checkpoint_id}: {e}")
            return None