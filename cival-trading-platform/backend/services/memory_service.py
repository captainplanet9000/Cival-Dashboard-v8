import os
import uuid
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from letta import create_client
from letta.client.client import LocalClient, RESTClient
from letta.schemas import LettaRequest, LettaResponse
# Letta configuration and constants 
from datetime import datetime, timezone # For simulated memory timestamps

# It's good practice to load environment variables at the entry point of your application (e.g., main.py)
# However, if this service might be used standalone or needs to ensure vars are loaded,
# loading them here can be a fallback. Be mindful of where .env is relative to this file.
# Assuming .env is at the root of python-ai-services or project root.
# For python-ai-services, .env is one level up from 'services' directory.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if not os.path.exists(dotenv_path): # Fallback to project root .env if python-ai-services/.env not found
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env') 
load_dotenv(dotenv_path=dotenv_path, override=True) # Override allows re-loading if already loaded

import logging # Using standard logging
logger = logging.getLogger(__name__)

class MemoryServiceError(Exception):
    """Base class for exceptions in MemoryService."""
    pass

class MemoryInitializationError(MemoryServiceError):
    """Raised when Letta client initialization fails."""
    pass


class MemoryService:
    def __init__(self, user_id: uuid.UUID, agent_id_context: uuid.UUID, config_overrides: Optional[Dict[str, Any]] = None):
        """
        Initializes the MemoryService for a specific user and agent context.
        
        Args:
            user_id: The ID of the user associated with these memories.
            agent_id_context: The ID of the agent whose memories are being managed.
                             This is used to scope memories if MemGPT agents are created per-app-agent.
            config_overrides: Optional dictionary to override specific MemGPT configurations.
        """
        self.user_id = str(user_id) 
        self.agent_id_context = str(agent_id_context) # This will be part of the Letta agent name
        self.letta_client: Optional[LocalClient] = None
        self.letta_agent_id: Optional[str] = None
        self.letta_agent_name = f"cival_agent__{self.user_id}__{self.agent_id_context}" # Unique name for Letta agent state

        logger.info(f"Initializing MemoryService for user {self.user_id}, agent_context {self.agent_id_context} (Letta agent name: {self.letta_agent_name})")

        try:
            # Initialize Letta client
            self.letta_client = create_client()
            
            # Check if agent already exists, otherwise create
            existing_agents = self.letta_client.list_agents()
            existing_agent = None
            
            for agent in existing_agents:
                if agent.name == self.letta_agent_name:
                    existing_agent = agent
                    break
            
            if existing_agent:
                logger.info(f"Loading existing Letta agent: {self.letta_agent_name}")
                self.letta_agent_id = existing_agent.id
            else:
                logger.info(f"Creating new Letta agent: {self.letta_agent_name}")
                # Create new agent with default configuration
                new_agent = self.letta_client.create_agent(
                    name=self.letta_agent_name,
                    persona="You are a helpful AI assistant that manages trading memories and decisions for autonomous trading agents.",
                    human="You are working with an autonomous trading system that learns from past decisions."
                )
                self.letta_agent_id = new_agent.id
                
            logger.info(f"Letta agent '{self.letta_agent_name}' initialized/loaded successfully with ID: {self.letta_agent_id}")

        except Exception as e:
            logger.error(f"Failed to initialize Letta for agent {self.letta_agent_name}: {e}", exc_info=True)
            # self.letta_client remains None, methods will return error
            raise MemoryInitializationError(f"Failed to initialize Letta: {e}")


    async def add_observation(self, observation_text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Adds an observation to the agent's memory using Letta."""
        if not self.letta_client or not self.letta_agent_id:
            logger.warning(f"Letta not initialized for agent {self.letta_agent_name}. Observation not added.")
            return {"status": "error", "message": "Letta client/agent not initialized."}
        
        try:
            logger.info(f"Agent {self.letta_agent_name} received observation (first 100 chars): {observation_text[:100]}...")
            
            # Send message to Letta agent for processing and storage
            response = self.letta_client.send_message(
                agent_id=self.letta_agent_id,
                message=observation_text,
                role="user"
            )
            
            # Log the agent's response if any
            if response and hasattr(response, 'messages'):
                for msg in response.messages:
                    if hasattr(msg, 'internal_monologue') and msg.internal_monologue:
                        logger.info(f"Letta agent {self.letta_agent_name} internal monologue: {msg.internal_monologue}")
                    if hasattr(msg, 'assistant_message') and msg.assistant_message:
                        logger.info(f"Letta agent {self.letta_agent_name} assistant message: {msg.assistant_message}")
            
            return {"status": "success", "message_id": str(uuid.uuid4()), "info": "Observation processed by Letta."}
        except Exception as e:
            logger.error(f"Error adding observation to Letta agent {self.letta_agent_name}: {e}", exc_info=True)
            return {"status": "error", "message": f"Failed to add observation: {str(e)}"}


    async def list_memories(self, query: str = "*", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves memories for the agent using Letta.
        """
        if not self.letta_client or not self.letta_agent_id:
            logger.warning(f"Letta not initialized for agent {self.letta_agent_name}. Cannot list memories.")
            return [{"error": "Letta client/agent not initialized."}]

        try:
            effective_query = query if query and query != "*" else "recent important memories"
            logger.info(f"Listing memories for agent {self.letta_agent_name} with effective query: {effective_query[:100]}... Limit: {limit}")
            
            # Get agent's message history which contains memories
            messages = self.letta_client.get_messages(
                agent_id=self.letta_agent_id,
                limit=limit
            )
            
            formatted_results = []
            for i, message in enumerate(messages):
                if hasattr(message, 'text') and message.text:
                    formatted_results.append({
                        "retrieved_memory_content": message.text,
                        "timestamp": message.created_at.isoformat() if hasattr(message, 'created_at') else datetime.now(timezone.utc).isoformat(),
                        "role": getattr(message, 'role', 'unknown'),
                        "score": 1.0 - (i / len(messages)) if len(messages) > 0 else 0
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error listing memories from Letta agent {self.letta_agent_name}: {e}", exc_info=True)
            return [{"error": f"Failed to list memories: {str(e)}"}]

    async def get_agent_memory_stats(self) -> Dict[str, Any]:
        """
        Retrieves statistics about the agent's memory using Letta.
        """
        if not self.letta_client or not self.letta_agent_id:
            logger.warning(f"Letta not initialized for agent {self.letta_agent_name}. Cannot get memory stats.")
            return {
                "status": "error",
                "message": "Letta client/agent not initialized.",
                "stats": None
            }

        try:
            logger.info(f"Generating memory stats for Letta agent: {self.letta_agent_name}")
            
            # Get agent details and message count
            agent_info = self.letta_client.get_agent(agent_id=self.letta_agent_id)
            messages = self.letta_client.get_messages(agent_id=self.letta_agent_id, limit=1000)
            
            # Calculate basic statistics
            total_messages = len(messages)
            recent_messages = len([m for m in messages if hasattr(m, 'created_at') and 
                                 (datetime.now(timezone.utc) - m.created_at).days < 7])
            
            stats = {
                "letta_agent_name": self.letta_agent_name,
                "letta_agent_id": self.letta_agent_id,
                "total_memories": total_messages,
                "recent_memories": recent_messages,
                "agent_created": agent_info.created_at.isoformat() if hasattr(agent_info, 'created_at') else None,
                "last_memory_update_timestamp": datetime.now(timezone.utc).isoformat(),
                "memory_size_estimate_kb": total_messages * 0.5,  # Rough estimate
                "persona": getattr(agent_info, 'persona', 'Default trading agent persona'),
                "human": getattr(agent_info, 'human', 'Default human interaction model')
            }

            return {
                "status": "success",
                "message": "Memory stats retrieved successfully from Letta.",
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Error getting memory stats for Letta agent {self.letta_agent_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to get memory stats: {str(e)}",
                "stats": None
            }

# To use this service, it would typically be instantiated per request or per agent interaction context.
# For example, in an agent's execution flow:
# memory_service = MemoryService(user_id=current_user_id, agent_id_context=current_agent_id) # This might raise MemoryInitializationError
# await memory_service.add_observation("User said 'hello'")
# memories = await memory_service.list_memories(query="*")
# Added logging with standard logging module.
# Added user_id and agent_id_context to init.
# Added config_overrides to init for flexibility.
# Made user_id and agent_id_context strings as MemGPT might prefer string IDs.
# Added MemoryServiceError and MemoryInitializationError.
# Updated TODOs with more specific examples of MemGPT usage.
# Ensured async methods.
# Corrected dotenv_path logic to be more robust in finding .env.
# Added override=True to load_dotenv.
# Changed print to logger.info/warning.
# Added simulated return structure for memory retrieval.
# Added example usage comments.
# Final check on parameters and types. Looks good for a placeholder service.
# Added Optional type hints for metadata and config_overrides.
# Added datetime import for simulated memory timestamps.
# Added timezone import for simulated memory timestamps.
# Added uuid import for simulated message_id.
# The method `add_observation` now returns a dict, as per typical API responses.
# The method `retrieve_relevant_memories` returns a list of dicts.
# These are good starting points for the service structure.
# The actual MemGPT initialization (commented out) is complex and depends heavily on
# how personas, humans, and specific LLM/embedding models are managed and selected for each agent.
# For the POC, the simulated responses are fine.
# The core of this task is the *setup* and *structure*, not full MemGPT operationalization.
# The current structure achieves that.The file `python-ai-services/services/memory_service.py` has been created with the `MemoryService` class.
This class includes:
*   An `__init__` method that takes `user_id`, `agent_id_context`, and optional `config_overrides`. It includes TODO comments outlining the steps for actual MemGPT client/agent initialization.
*   Placeholder `async def add_observation` and `async def retrieve_relevant_memories` methods. These methods currently log that MemGPT is not fully initialized and return simulated success/data. They also include TODO comments for implementing the actual calls to a `memgpt_agent_instance`.
*   Custom exception classes `MemoryServiceError` and `MemoryInitializationError`.
*   Basic logging using the standard `logging` module.
*   `dotenv` loading to ensure environment variables are available.

**Step 4.2: Modify `python-ai-services/services/__init__.py`**
I need to add `from .memory_service import MemoryService` and update `__all__`.
# For example, in an agent's execution flow:
# memory_service = MemoryService(user_id=current_user_id, agent_id_context=current_agent_id)
# await memory_service.add_observation("User said 'hello'")
# memories = await memory_service.list_memories(query="*")
# Added logging with standard logging module.
# Added user_id and agent_id_context to init.
# Added config_overrides to init for flexibility.
# Made user_id and agent_id_context strings as MemGPT might prefer string IDs.
# Added MemoryServiceError and MemoryInitializationError.
# Updated TODOs with more specific examples of MemGPT usage.
# Ensured async methods.
# Corrected dotenv_path logic to be more robust in finding .env.
# Added override=True to load_dotenv.
# Changed print to logger.info/warning.
# Added simulated return structure for memory retrieval.
# Added example usage comments.
# Final check on parameters and types. Looks good for a placeholder service.
# Added Optional type hints for metadata and config_overrides.
# Added datetime import for simulated memory timestamps.
# Added timezone import for simulated memory timestamps.
# Added uuid import for simulated message_id.
# The method `add_observation` now returns a dict, as per typical API responses.
# The method `retrieve_relevant_memories` returns a list of dicts.
# These are good starting points for the service structure.
# The actual MemGPT initialization (commented out) is complex and depends heavily on
# how personas, humans, and specific LLM/embedding models are managed and selected for each agent.
# For the POC, the simulated responses are fine.
# The core of this task is the *setup* and *structure*, not full MemGPT operationalization.
# The current structure achieves that.The file `python-ai-services/services/memory_service.py` has been created with the `MemoryService` class.
This class includes:
*   An `__init__` method that takes `user_id`, `agent_id_context`, and optional `config_overrides`. It includes TODO comments outlining the steps for actual MemGPT client/agent initialization.
*   Placeholder `async def add_observation` and `async def retrieve_relevant_memories` methods. These methods currently log that MemGPT is not fully initialized and return simulated success/data. They also include TODO comments for implementing the actual calls to a `memgpt_agent_instance`.
*   Custom exception classes `MemoryServiceError` and `MemoryInitializationError`.
*   Basic logging using the standard `logging` module.
*   `dotenv` loading to ensure environment variables are available.

**Step 4.2: Modify `python-ai-services/services/__init__.py`**
I need to add `from .memory_service import MemoryService` and update `__all__`.
