import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime

from python_ai_services.models.agent_models import (
    AgentConfigInput, AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig,
    AgentUpdateRequest, AgentStatus
)
from python_ai_services.services.agent_management_service import AgentManagementService
from python_ai_services.api.v1.agent_management_routes import router as agent_management_router, get_agent_management_service

# Create a minimal FastAPI app for testing this specific router
app = FastAPI()
app.include_router(agent_management_router, prefix="/api/v1")

# Mock service instance that will be used by the router's dependency override
mock_service = MagicMock(spec=AgentManagementService)

# Override the dependency for testing
def override_get_agent_management_service():
    return mock_service

app.dependency_overrides[get_agent_management_service] = override_get_agent_management_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_mock_service():
    """Reset the mock service before each test."""
    mock_service.reset_mock()

def _create_sample_agent_config_output(agent_id: str, name: str = "Test Agent") -> AgentConfigOutput:
    return AgentConfigOutput(
        agent_id=agent_id,
        name=name,
        strategy=AgentStrategyConfig(strategy_name="test_strat", parameters={"p": 1}),
        risk_config=AgentRiskConfig(max_capital_allocation_usd=1000, risk_per_trade_percentage=0.01),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=False
    )

def _create_sample_agent_status(agent_id: str, status: str = "stopped") -> AgentStatus:
    return AgentStatus(agent_id=agent_id, status=status, last_heartbeat=datetime.utcnow())


def test_create_new_agent():
    agent_input_data = {
        "name": "API Test Agent",
        "strategy": {"strategy_name": "api_strat", "parameters": {"key": "val"}},
        "risk_config": {"max_capital_allocation_usd": 2000, "risk_per_trade_percentage": 0.02},
        "execution_provider": "paper"
    }
    mock_agent_id = str(uuid.uuid4())
    # Ensure the mock service's create_agent returns an awaitable mock if it's an async method
    # The actual service method is async, so the mock should reflect that.
    async def async_create_agent(*args, **kwargs):
        # Simulate the creation and return an AgentConfigOutput-like structure
        return AgentConfigOutput(
            agent_id=mock_agent_id,
            **args[0].model_dump(), # args[0] is AgentConfigInput
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=False
        )
    mock_service.create_agent = MagicMock(side_effect=async_create_agent)

    response = client.post("/api/v1/agents", json=agent_input_data)

    assert response.status_code == 201
    response_json = response.json()
    assert response_json["name"] == agent_input_data["name"]
    assert response_json["agent_id"] == mock_agent_id
    assert response_json["strategy"]["strategy_name"] == "api_strat"
    mock_service.create_agent.assert_called_once()
    # Check if called with an instance of AgentConfigInput
    assert isinstance(mock_service.create_agent.call_args[0][0], AgentConfigInput)


def test_list_all_agents():
    mock_agent_id1 = str(uuid.uuid4())
    mock_agent_id2 = str(uuid.uuid4())
    mock_agents_list = [
        _create_sample_agent_config_output(agent_id=mock_agent_id1, name="Agent1"),
        _create_sample_agent_config_output(agent_id=mock_agent_id2, name="Agent2"),
    ]
    async def async_get_agents(): return mock_agents_list
    mock_service.get_agents = MagicMock(side_effect=async_get_agents)

    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 2
    assert response_json[0]["name"] == "Agent1"
    assert response_json[1]["name"] == "Agent2"
    mock_service.get_agents.assert_called_once()

def test_get_specific_agent_found():
    mock_agent_id = str(uuid.uuid4())
    agent_data = _create_sample_agent_config_output(agent_id=mock_agent_id)
    async def async_get_agent(id): return agent_data if id == mock_agent_id else None
    mock_service.get_agent = MagicMock(side_effect=async_get_agent)

    response = client.get(f"/api/v1/agents/{mock_agent_id}")
    assert response.status_code == 200
    assert response.json()["agent_id"] == mock_agent_id
    mock_service.get_agent.assert_called_once_with(mock_agent_id)

def test_get_specific_agent_not_found():
    mock_agent_id = str(uuid.uuid4())
    async def async_get_agent(id): return None
    mock_service.get_agent = MagicMock(side_effect=async_get_agent)

    response = client.get(f"/api/v1/agents/{mock_agent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    mock_service.get_agent.assert_called_once_with(mock_agent_id)

def test_update_existing_agent():
    mock_agent_id = str(uuid.uuid4())
    update_data = {"name": "Updated Agent Name"}

    # Mock get_agent to return an existing agent, then update_agent to return the updated one
    original_agent = _create_sample_agent_config_output(agent_id=mock_agent_id, name="Original Name")
    updated_agent_mock_data = original_agent.model_copy(update={"name": "Updated Agent Name", "updated_at": datetime.utcnow()})

    async def async_get_agent_for_update(id): return original_agent if id == mock_agent_id else None
    async def async_update_agent(id, data: AgentUpdateRequest):
        if id == mock_agent_id:
            # Simulate update based on data
            # This is a simplified version, actual service has more complex merge
            temp_data = original_agent.model_dump()
            temp_data.update(data.model_dump(exclude_unset=True))
            return AgentConfigOutput(**temp_data, updated_at=datetime.utcnow())
        return None

    mock_service.get_agent = MagicMock(side_effect=async_get_agent_for_update) # For the check in route
    mock_service.update_agent = MagicMock(side_effect=async_update_agent)

    response = client.put(f"/api/v1/agents/{mock_agent_id}", json=update_data)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["name"] == "Updated Agent Name"
    assert response_json["agent_id"] == mock_agent_id
    mock_service.update_agent.assert_called_once()
    assert isinstance(mock_service.update_agent.call_args[0][1], AgentUpdateRequest)


def test_update_agent_not_found():
    mock_agent_id = str(uuid.uuid4())
    update_data = {"name": "Ghost Agent"}
    async def async_get_agent_for_update_notfound(id): return None
    mock_service.get_agent = MagicMock(side_effect=async_get_agent_for_update_notfound) # For the check in route
    # update_agent mock won't be called if get_agent returns None in the route's pre-check
    async def async_update_agent_notfound(id, data): return None
    mock_service.update_agent = MagicMock(side_effect=async_update_agent_notfound)


    response = client.put(f"/api/v1/agents/{mock_agent_id}", json=update_data)
    assert response.status_code == 404
    mock_service.get_agent.assert_called_once_with(mock_agent_id)
    mock_service.update_agent.assert_not_called()


def test_delete_specific_agent():
    mock_agent_id = str(uuid.uuid4())
    original_agent = _create_sample_agent_config_output(agent_id=mock_agent_id)
    async def async_get_agent_for_delete(id): return original_agent if id == mock_agent_id else None
    async def async_delete_agent(id): return True if id == mock_agent_id else False
    mock_service.get_agent = MagicMock(side_effect=async_get_agent_for_delete) # For the check in route
    mock_service.delete_agent = MagicMock(side_effect=async_delete_agent)

    response = client.delete(f"/api/v1/agents/{mock_agent_id}")
    assert response.status_code == 204
    mock_service.delete_agent.assert_called_once_with(mock_agent_id)

def test_delete_agent_not_found():
    mock_agent_id = str(uuid.uuid4())
    async def async_get_agent_for_delete_notfound(id): return None
    async def async_delete_agent_notfound(id): return False
    mock_service.get_agent = MagicMock(side_effect=async_get_agent_for_delete_notfound) # For the check in route
    mock_service.delete_agent = MagicMock(side_effect=async_delete_agent_notfound)


    response = client.delete(f"/api/v1/agents/{mock_agent_id}")
    assert response.status_code == 404
    mock_service.get_agent.assert_called_once_with(mock_agent_id)
    mock_service.delete_agent.assert_not_called() # Delete in service won't be called if route check fails


def test_start_specific_agent():
    mock_agent_id = str(uuid.uuid4())
    status_data = _create_sample_agent_status(agent_id=mock_agent_id, status="running")
    async def async_start_agent(id): return status_data if id == mock_agent_id else None # Simplified
    mock_service.start_agent = MagicMock(side_effect=async_start_agent)

    response = client.post(f"/api/v1/agents/{mock_agent_id}/start")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    mock_service.start_agent.assert_called_once_with(mock_agent_id)

def test_start_agent_not_found():
    mock_agent_id = str(uuid.uuid4())
    async def async_start_agent_error(id): raise ValueError(f"Agent with ID {id} not found.")
    mock_service.start_agent = MagicMock(side_effect=async_start_agent_error)

    response = client.post(f"/api/v1/agents/{mock_agent_id}/start")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_stop_specific_agent():
    mock_agent_id = str(uuid.uuid4())
    status_data = _create_sample_agent_status(agent_id=mock_agent_id, status="stopped")
    async def async_stop_agent(id): return status_data if id == mock_agent_id else None # Simplified
    mock_service.stop_agent = MagicMock(side_effect=async_stop_agent)

    response = client.post(f"/api/v1/agents/{mock_agent_id}/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "stopped"
    mock_service.stop_agent.assert_called_once_with(mock_agent_id)

def test_get_specific_agent_status():
    mock_agent_id = str(uuid.uuid4())
    status_data = _create_sample_agent_status(agent_id=mock_agent_id, status="running")
    async def async_get_status(id): return status_data if id == mock_agent_id else None
    mock_service.get_agent_status = MagicMock(side_effect=async_get_status)

    response = client.get(f"/api/v1/agents/{mock_agent_id}/status")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    mock_service.get_agent_status.assert_called_once_with(mock_agent_id)

def test_get_agent_status_not_found():
    mock_agent_id = str(uuid.uuid4())
    async def async_get_status_notfound(id): return None
    mock_service.get_agent_status = MagicMock(side_effect=async_get_status_notfound)

    response = client.get(f"/api/v1/agents/{mock_agent_id}/status")
    assert response.status_code == 404
    assert "not found or no status available" in response.json()["detail"]

