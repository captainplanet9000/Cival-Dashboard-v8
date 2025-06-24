from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field as PydanticField # Renamed Field
from loguru import logger
import json
import asyncio # For __main__ example

# Attempt to import the 'tool' decorator from crewai_tools
try:
    from crewai_tools import tool
except ImportError:
    logger.warning("crewai_tools.tool not found. Using a placeholder decorator '@tool_stub'.")
    def tool_stub(name: str, args_schema: Optional[Any] = None, description: Optional[str] = None):
        def decorator(func):
            func.tool_name = name
            func.args_schema = args_schema
            func.description = description
            logger.debug(f"Tool stub '{name}' registered for {func.__name__} with args_schema: {args_schema}, desc: {description}")
            return func
        return decorator
    tool = tool_stub

# Attempt to import MemoryService and app_services
try:
    from ..services.memory_service import MemoryService
    from ..main import services as app_services # Accessing the global 'services' dict from main.py
    MEMORY_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning(
        "Could not import MemoryService or app_services from ..services or ..main. "
        "Memory tools will use a stubbed MemoryService if run directly."
    )
    MEMORY_SERVICE_AVAILABLE = False
    # Define a placeholder MemoryService for standalone tool testing if actual import fails
    class MemoryService: # type: ignore
        async def store_memory_message(self, app_agent_id: str, observation: str, role: str = "user") -> bool:
            logger.info(f"STUB MemoryService: Storing memory for {app_agent_id} (role: {role}): '{observation[:50]}...'")
            return True
        async def get_memory_response(self, app_agent_id: str, query: str, role: str = "user") -> Optional[str]:
            logger.info(f"STUB MemoryService: Getting memory response for {app_agent_id} (role: {role}) with query: '{query[:50]}...'")
            return f"Stub response for {app_agent_id} to query: '{query}'"

    # Define placeholder app_services if running standalone
    app_services: Dict[str, Any] = {"memory_service": MemoryService(letta_server_url="http://stubbed-letta-server:8283")} if not MEMORY_SERVICE_AVAILABLE else {}


# --- Argument Schemas ---

class StoreMemoryArgs(BaseModel):
    """Arguments for the Store Memory Tool."""
    app_agent_id: str = PydanticField(..., description="The application-specific agent ID to associate the memory with (e.g., 'trading_crew_run_123_market_analyst', or a specific strategy agent's unique ID).")
    observation: str = PydanticField(..., description="The observation or piece of information to store in memory.")
    role: str = PydanticField(default="user", description="The role associated with the message being stored (e.g., 'user' for observations, 'system' for instructions).")

class RecallMemoriesArgs(BaseModel):
    """Arguments for the Recall Memories Tool."""
    app_agent_id: str = PydanticField(..., description="The application-specific agent ID whose memory should be queried.")
    query: str = PydanticField(..., description="The query or prompt to retrieve relevant memories or get a synthesized response from memory.")
    role: str = PydanticField(default="user", description="The role associated with the query message (typically 'user').")


# --- Memory Tools ---

@tool("Store Memory Tool", args_schema=StoreMemoryArgs, description="Stores an observation or message into the specified agent's long-term memory via MemoryService.")
async def store_memory_tool(app_agent_id: str, observation: str, role: str = "user") -> str:
    """
    Stores an observation or message into an agent's long-term memory using MemoryService.
    """
    logger.info(f"TOOL: store_memory_tool called for app_agent_id='{app_agent_id}', role='{role}'. Observation: '{observation[:100]}...'")

    memory_service: Optional[MemoryService] = app_services.get("memory_service")
    if not memory_service:
        logger.error("MemoryService not available in app_services. Cannot store memory.")
        return json.dumps({"success": False, "error": "MemoryService not available.", "app_agent_id": app_agent_id})

    try:
        success = await memory_service.store_memory_message(app_agent_id, observation, role)
        if success:
            logger.info(f"Memory successfully stored for app_agent_id='{app_agent_id}'.")
            return json.dumps({"success": True, "app_agent_id": app_agent_id, "action": "store_memory"})
        else:
            logger.warning(f"Failed to store memory for app_agent_id='{app_agent_id}' via MemoryService.")
            return json.dumps({"success": False, "error": "MemoryService reported failure to store memory.", "app_agent_id": app_agent_id})
    except Exception as e:
        logger.exception(f"Error calling MemoryService.store_memory_message for app_agent_id='{app_agent_id}': {e}")
        return json.dumps({"success": False, "error": f"Exception storing memory: {str(e)}", "app_agent_id": app_agent_id})


@tool("Recall Memories Tool", args_schema=RecallMemoriesArgs, description="Retrieves relevant memories or a synthesized response from the specified agent's long-term memory via MemoryService based on a query.")
async def recall_memories_tool(app_agent_id: str, query: str, role: str = "user") -> str:
    """
    Recalls memories or gets a synthesized response from an agent's long-term memory
    using MemoryService.
    """
    logger.info(f"TOOL: recall_memories_tool called for app_agent_id='{app_agent_id}', role='{role}'. Query: '{query[:100]}...'")

    memory_service: Optional[MemoryService] = app_services.get("memory_service")
    if not memory_service:
        logger.error("MemoryService not available in app_services. Cannot recall memories.")
        return json.dumps({"success": False, "error": "MemoryService not available.", "app_agent_id": app_agent_id, "query": query, "response": None})

    try:
        response = await memory_service.get_memory_response(app_agent_id, query, role)
        if response is not None:
            logger.info(f"Successfully recalled memories/response for app_agent_id='{app_agent_id}'.")
            return json.dumps({"success": True, "app_agent_id": app_agent_id, "query": query, "response": response})
        else:
            logger.info(f"No response or memories found for app_agent_id='{app_agent_id}' with query: '{query}'.")
            return json.dumps({"success": False, "app_agent_id": app_agent_id, "query": query, "response": "No specific response from memory."})
    except Exception as e:
        logger.exception(f"Error calling MemoryService.get_memory_response for app_agent_id='{app_agent_id}': {e}")
        return json.dumps({"success": False, "error": f"Exception recalling memories: {str(e)}", "app_agent_id": app_agent_id, "query": query, "response": None})


if __name__ == '__main__':
    # This block is for demonstration and basic testing of the tool structure.
    # It requires MemoryService to be available in app_services.
    # If MemoryService itself relies on a running Letta server, that would also be a dependency for full end-to-end testing.

    logger.remove() # Remove default logger to avoid duplicate output if this file is imported
    logger.add(lambda msg: print(msg, end=''), colorize=True, format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level="DEBUG")

    # --- Mocking MemoryService for standalone __main__ example ---
    # This ensures the __main__ block can run without the full application context.
    # In a real application, MemoryService would be initialized and placed in app_services during startup.

    class MockMemoryServiceForExample:
        def __init__(self, letta_server_url: str): # Match constructor
            self.letta_server_url = letta_server_url
            logger.info(f"MockMemoryServiceForExample initialized with URL: {self.letta_server_url}")

        async def connect_letta_client(self) -> bool: # Added connect method
            logger.info("MockMemoryServiceForExample: connect_letta_client called (simulated success).")
            return True

        async def get_or_create_memgpt_agent(self, app_agent_id: str, memgpt_config: Any) -> Optional[str]:
            logger.info(f"MockMemoryServiceForExample: get_or_create_memgpt_agent for {app_agent_id}")
            return f"mock_letta_id_for_{app_agent_id}"

        async def store_memory_message(self, app_agent_id: str, observation: str, role: str = "user") -> bool:
            logger.info(f"MockMemoryServiceForExample: Storing for {app_agent_id} (role: {role}): '{observation}'")
            # Simulate storage in a mock internal dictionary if needed for more complex tests
            if not hasattr(self, '_mock_storage'):
                self._mock_storage = {} # type: ignore
            self._mock_storage.setdefault(app_agent_id, []).append({"role": role, "observation": observation}) # type: ignore
            return True

        async def get_memory_response(self, app_agent_id: str, query: str, role: str = "user") -> Optional[str]:
            logger.info(f"MockMemoryServiceForExample: Recalling for {app_agent_id} (role: {role}) with query: '{query}'")
            if hasattr(self, '_mock_storage') and app_agent_id in self._mock_storage: # type: ignore
                # Simulate a simple recall of the last stored message
                last_mem = self._mock_storage[app_agent_id][-1]['observation'] # type: ignore
                return f"Mock response for '{query}'. Last memory was: '{last_mem}'"
            return f"Mock response for '{query}'. No specific memories found for {app_agent_id} in this mock."

    # Replace the actual MemoryService in app_services with the mock for this example
    if not MEMORY_SERVICE_AVAILABLE or "memory_service" not in app_services: # If it wasn't imported or if app_services is empty
        mock_memory_service_instance = MockMemoryServiceForExample("http://mock-letta:8283")
        asyncio.run(mock_memory_service_instance.connect_letta_client()) # Connect the mock
        app_services["memory_service"] = mock_memory_service_instance
        logger.info("Using MockMemoryServiceForExample for __main__ demo.")
    # --- End Mocking MemoryService ---

    async def demo_tools():
        test_app_agent_id = "demo_agent_001"

        # 1. Store some memories
        logger.info("\n--- Demonstrating store_memory_tool ---")
        store_args1 = StoreMemoryArgs(app_agent_id=test_app_agent_id, observation="Bitcoin price is currently volatile.")
        result1_json = await store_memory_tool(**store_args1.model_dump())
        logger.info(f"Store Memory Tool Output 1:\n{json.dumps(json.loads(result1_json), indent=2)}\n")

        store_args2 = StoreMemoryArgs(app_agent_id=test_app_agent_id, observation="User is bullish on Ethereum.", role="system_observation")
        result2_json = await store_memory_tool(**store_args2.model_dump())
        logger.info(f"Store Memory Tool Output 2:\n{json.dumps(json.loads(result2_json), indent=2)}\n")

        # 2. Recall memories
        logger.info("\n--- Demonstrating recall_memories_tool ---")
        recall_args1 = RecallMemoriesArgs(app_agent_id=test_app_agent_id, query="What's the user's sentiment on Ethereum?")
        result3_json = await recall_memories_tool(**recall_args1.model_dump())
        logger.info(f"Recall Memories Tool Output 1:\n{json.dumps(json.loads(result3_json), indent=2)}\n")

        recall_args2 = RecallMemoriesArgs(app_agent_id="non_existent_agent", query="Any data for me?")
        result4_json = await recall_memories_tool(**recall_args2.model_dump()) # Assuming memory_service handles non-existent agent gracefully
        logger.info(f"Recall Memories Tool Output 2 (non-existent agent):\n{json.dumps(json.loads(result4_json), indent=2)}\n")

        # 3. Example of tool usage if MemoryService is not available
        if "memory_service" in app_services: # Temporarily remove for this test case
            original_ms = app_services.pop("memory_service")

        logger.info("\n--- Demonstrating tool with MemoryService unavailable ---")
        store_args_no_service = StoreMemoryArgs(app_agent_id=test_app_agent_id, observation="This should fail.")
        result_no_service_json = await store_memory_tool(**store_args_no_service.model_dump())
        logger.info(f"Store Memory Tool Output (No Service):\n{json.dumps(json.loads(result_no_service_json), indent=2)}\n")

        if original_ms: # Restore if it was popped
             app_services["memory_service"] = original_ms


    asyncio.run(demo_tools())

