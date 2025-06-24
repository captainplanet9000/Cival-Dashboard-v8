import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Tools and Args Schemas to test
from python_ai_services.tools.memory_tools import (
    store_memory_tool, StoreMemoryArgs,
    recall_memories_tool, RecallMemoriesArgs
)
# For type hinting the mocked service
from python_ai_services.services.memory_service import MemoryService

APP_SERVICES_PATH = "python_ai_services.tools.memory_tools.app_services"

# --- Tests for store_memory_tool ---

@pytest.mark.asyncio
@patch(APP_SERVICES_PATH, new_callable=MagicMock) # Mocks the app_services dict itself
async def test_store_memory_tool_success(mock_app_services: MagicMock):
    # Configure the mock MemoryService that app_services.get() will return
    mock_memory_service_instance = AsyncMock(spec=MemoryService)
    mock_memory_service_instance.store_memory_message.return_value = True
    mock_app_services.get.return_value = mock_memory_service_instance

    app_agent_id="agent_store_success"
    observation="Test observation for successful storage."
    role="user"

    result_json = await store_memory_tool(app_agent_id=app_agent_id, observation=observation, role=role)
    data = json.loads(result_json)

    mock_app_services.get.assert_called_once_with("memory_service")
    mock_memory_service_instance.store_memory_message.assert_called_once_with(app_agent_id, observation, role)
    assert data["success"] is True
    assert data["app_agent_id"] == app_agent_id
    assert data["action"] == "store_memory"

@pytest.mark.asyncio
@patch(APP_SERVICES_PATH, new_callable=MagicMock)
async def test_store_memory_tool_service_fails(mock_app_services: MagicMock):
    mock_memory_service_instance = AsyncMock(spec=MemoryService)
    mock_memory_service_instance.store_memory_message.return_value = False
    mock_app_services.get.return_value = mock_memory_service_instance

    app_agent_id="agent_store_fail_service"
    observation="Observation that service reports as failed to store."

    result_json = await store_memory_tool(app_agent_id=app_agent_id, observation=observation)
    data = json.loads(result_json)

    mock_memory_service_instance.store_memory_message.assert_called_once()
    assert data["success"] is False
    assert data["app_agent_id"] == app_agent_id
    assert "error" in data
    assert data["error"] == "MemoryService reported failure to store memory."

@pytest.mark.asyncio
@patch(APP_SERVICES_PATH, new_callable=MagicMock)
async def test_store_memory_tool_service_exception(mock_app_services: MagicMock):
    mock_memory_service_instance = AsyncMock(spec=MemoryService)
    exception_message = "MemService DB error"
    mock_memory_service_instance.store_memory_message.side_effect = Exception(exception_message)
    mock_app_services.get.return_value = mock_memory_service_instance

    app_agent_id="agent_store_exception"
    observation="Observation during service exception."

    result_json = await store_memory_tool(app_agent_id=app_agent_id, observation=observation)
    data = json.loads(result_json)

    mock_memory_service_instance.store_memory_message.assert_called_once()
    assert data["success"] is False
    assert data["app_agent_id"] == app_agent_id
    assert "error" in data
    assert f"Exception storing memory: {exception_message}" in data["error"]

@pytest.mark.asyncio
@patch(APP_SERVICES_PATH, new_callable=MagicMock)
async def test_store_memory_tool_service_unavailable(mock_app_services: MagicMock):
    mock_app_services.get.return_value = None # Simulate MemoryService not being in app_services

    app_agent_id="agent_store_no_service"
    observation="Observation when service is unavailable."

    result_json = await store_memory_tool(app_agent_id=app_agent_id, observation=observation)
    data = json.loads(result_json)

    mock_app_services.get.assert_called_once_with("memory_service")
    assert data["success"] is False
    assert data["app_agent_id"] == app_agent_id
    assert "error" in data
    assert data["error"] == "MemoryService not available."

def test_store_memory_tool_args_schema():
    """Test that the tool has the correct args_schema linked."""
    # This check depends on how crewai_tools.tool decorator assigns the schema
    if hasattr(store_memory_tool, 'args_schema'):
        assert store_memory_tool.args_schema == StoreMemoryArgs
    elif hasattr(store_memory_tool, '_crew_tool_input_schema'): # For some versions/setups
         assert store_memory_tool._crew_tool_input_schema == StoreMemoryArgs
    else:
        pytest.fail("Tool schema attribute not found for store_memory_tool.")


# --- Tests for recall_memories_tool ---

@pytest.mark.asyncio
@patch(APP_SERVICES_PATH, new_callable=MagicMock)
async def test_recall_memories_tool_success(mock_app_services: MagicMock):
    mock_memory_service_instance = AsyncMock(spec=MemoryService)
    mock_response_content = "Mocked memory response from service."
    mock_memory_service_instance.get_memory_response.return_value = mock_response_content
    mock_app_services.get.return_value = mock_memory_service_instance

    app_agent_id="agent_recall_success"
    query="What was my last important note?"

    result_json = await recall_memories_tool(app_agent_id=app_agent_id, query=query)
    data = json.loads(result_json)

    mock_app_services.get.assert_called_once_with("memory_service")
    mock_memory_service_instance.get_memory_response.assert_called_once_with(app_agent_id, query, "user")
    assert data["success"] is True
    assert data["app_agent_id"] == app_agent_id
    assert data["query"] == query
    assert data["response"] == mock_response_content

@pytest.mark.asyncio
@patch(APP_SERVICES_PATH, new_callable=MagicMock)
async def test_recall_memories_tool_service_returns_none(mock_app_services: MagicMock):
    mock_memory_service_instance = AsyncMock(spec=MemoryService)
    mock_memory_service_instance.get_memory_response.return_value = None # Simulate service finding no specific response
    mock_app_services.get.return_value = mock_memory_service_instance

    app_agent_id="agent_recall_none"
    query="A query that yields no specific response."

    result_json = await recall_memories_tool(app_agent_id=app_agent_id, query=query)
    data = json.loads(result_json)

    mock_memory_service_instance.get_memory_response.assert_called_once()
    assert data["success"] is False # As per tool logic: success is response is not None
    assert data["app_agent_id"] == app_agent_id
    assert data["response"] == "No specific response from memory."

@pytest.mark.asyncio
@patch(APP_SERVICES_PATH, new_callable=MagicMock)
async def test_recall_memories_tool_service_exception(mock_app_services: MagicMock):
    mock_memory_service_instance = AsyncMock(spec=MemoryService)
    exception_message = "MemService recall DB error"
    mock_memory_service_instance.get_memory_response.side_effect = Exception(exception_message)
    mock_app_services.get.return_value = mock_memory_service_instance

    app_agent_id="agent_recall_exception"
    query="Query during recall service exception."

    result_json = await recall_memories_tool(app_agent_id=app_agent_id, query=query)
    data = json.loads(result_json)

    mock_memory_service_instance.get_memory_response.assert_called_once()
    assert data["success"] is False
    assert data["app_agent_id"] == app_agent_id
    assert "error" in data
    assert f"Exception recalling memories: {exception_message}" in data["error"]
    assert data["response"] is None

@pytest.mark.asyncio
@patch(APP_SERVICES_PATH, new_callable=MagicMock)
async def test_recall_memories_tool_service_unavailable(mock_app_services: MagicMock):
    mock_app_services.get.return_value = None # Simulate MemoryService not being in app_services

    app_agent_id="agent_recall_no_service"
    query="Query when recall service is unavailable."

    result_json = await recall_memories_tool(app_agent_id=app_agent_id, query=query)
    data = json.loads(result_json)

    mock_app_services.get.assert_called_once_with("memory_service")
    assert data["success"] is False
    assert data["app_agent_id"] == app_agent_id
    assert "error" in data
    assert data["error"] == "MemoryService not available."
    assert data["response"] is None

def test_recall_memories_tool_args_schema():
    """Test that the tool has the correct args_schema linked."""
    if hasattr(recall_memories_tool, 'args_schema'):
        assert recall_memories_tool.args_schema == RecallMemoriesArgs
    elif hasattr(recall_memories_tool, '_crew_tool_input_schema'):
         assert recall_memories_tool._crew_tool_input_schema == RecallMemoriesArgs
    else:
        pytest.fail("Tool schema attribute not found for recall_memories_tool.")

