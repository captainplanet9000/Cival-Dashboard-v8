import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

from python_ai_services.models.alert_models import (
    AlertConfigInput, AlertConfigOutput, AlertCondition
)
from python_ai_services.services.alert_configuration_service import AlertConfigurationService
from python_ai_services.api.v1.alert_routes import router as alert_router, get_alert_configuration_service

# Minimal FastAPI app for testing this router
app = FastAPI()
app.include_router(alert_router, prefix="/api/v1")

# Mock service instance
mock_service_alert_config = MagicMock(spec=AlertConfigurationService)

# Override dependency
def override_get_alert_configuration_service():
    return mock_service_alert_config

app.dependency_overrides[get_alert_configuration_service] = override_get_alert_configuration_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_mock_service():
    mock_service_alert_config.reset_mock()

# --- Helper Functions ---
def _create_sample_alert_config_output(agent_id: str, alert_id: str, name: str = "Test Alert") -> AlertConfigOutput:
    return AlertConfigOutput(
        alert_id=alert_id,
        agent_id=agent_id,
        name=name,
        conditions=[AlertCondition(metric="account_value_usd", operator="<", threshold=1000.0)],
        notification_channels=["log"],
        is_enabled=True,
        cooldown_seconds=300,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

# --- Test Cases ---

def test_create_alert_config_for_agent():
    agent_id = "agent_alert_create"
    alert_input_data = {
        "name": "New API Alert",
        "conditions": [{"metric": "total_pnl_usd", "operator": ">=", "threshold": 100.0}],
        "notification_channels": ["log", "email_placeholder"],
        "target_email": "test@example.com",
        "is_enabled": True,
        "cooldown_seconds": 60
    }
    mock_alert_id = str(uuid.uuid4())

    async def async_create_alert(*args, **kwargs):
        # args[0] is agent_id, args[1] is AlertConfigInput
        return AlertConfigOutput(
            alert_id=mock_alert_id,
            agent_id=args[0],
            **args[1].model_dump(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    mock_service_alert_config.create_alert_config = MagicMock(side_effect=async_create_alert)

    response = client.post(f"/api/v1/agents/{agent_id}/alerts", json=alert_input_data)

    assert response.status_code == 201
    response_json = response.json()
    assert response_json["name"] == alert_input_data["name"]
    assert response_json["agent_id"] == agent_id
    assert response_json["alert_id"] == mock_alert_id
    assert response_json["conditions"][0]["metric"] == "total_pnl_usd"
    mock_service_alert_config.create_alert_config.assert_called_once()
    # Check that the service method was called with agent_id and an AlertConfigInput instance
    call_args = mock_service_alert_config.create_alert_config.call_args
    assert call_args[0][0] == agent_id
    assert isinstance(call_args[0][1], AlertConfigInput)


def test_create_alert_config_validation_error():
    agent_id = "agent_alert_val_err"
    alert_input_data = { # Missing 'name', which is required
        "conditions": [{"metric": "total_pnl_usd", "operator": ">=", "threshold": 100.0}],
        "notification_channels": ["log"]
    }
    # Pydantic validation happens before the service call for request body
    response = client.post(f"/api/v1/agents/{agent_id}/alerts", json=alert_input_data)
    assert response.status_code == 422 # Unprocessable Entity for Pydantic validation error

    # Test validation error from service (e.g., custom Pydantic error in model)
    async def async_create_alert_value_error(*args, **kwargs):
        raise ValueError("Service level validation failed")
    mock_service_alert_config.create_alert_config = MagicMock(side_effect=async_create_alert_value_error)
    valid_input_data = {
        "name": "Valid Name",
        "conditions": [{"metric": "total_pnl_usd", "operator": ">=", "threshold": 100.0}],
        "notification_channels": ["log"]
    }
    response_service_error = client.post(f"/api/v1/agents/{agent_id}/alerts", json=valid_input_data)
    assert response_service_error.status_code == 422 # Route catches ValueError
    assert "Service level validation failed" in response_service_error.json()["detail"]


def test_list_alert_configs_for_agent():
    agent_id = "agent_list_alerts"
    mock_alerts = [
        _create_sample_alert_config_output(agent_id, str(uuid.uuid4()), "Alert 1"),
        _create_sample_alert_config_output(agent_id, str(uuid.uuid4()), "Alert 2")
    ]
    mock_service_alert_config.get_alert_configs_for_agent = AsyncMock(return_value=mock_alerts)

    response = client.get(f"/api/v1/agents/{agent_id}/alerts?only_enabled=true")
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 2
    assert response_json[0]["name"] == "Alert 1"
    mock_service_alert_config.get_alert_configs_for_agent.assert_called_once_with(agent_id, True)

def test_get_specific_alert_config_found():
    agent_id = "agent_get_one_alert"
    alert_id = str(uuid.uuid4())
    mock_alert = _create_sample_alert_config_output(agent_id, alert_id)
    mock_service_alert_config.get_alert_config = AsyncMock(return_value=mock_alert)

    response = client.get(f"/api/v1/agents/{agent_id}/alerts/{alert_id}")
    assert response.status_code == 200
    assert response.json()["alert_id"] == alert_id
    mock_service_alert_config.get_alert_config.assert_called_once_with(alert_id)

def test_get_specific_alert_config_not_found_or_wrong_agent():
    agent_id = "agent_get_one_alert_nf"
    alert_id_found_wrong_agent = str(uuid.uuid4())
    alert_id_not_found = str(uuid.uuid4())

    # Mock for when alert exists but belongs to different agent
    mock_alert_wrong_agent = _create_sample_alert_config_output("other_agent", alert_id_found_wrong_agent)

    async def get_alert_side_effect(id_param):
        if id_param == alert_id_found_wrong_agent:
            return mock_alert_wrong_agent
        return None # For alert_id_not_found
    mock_service_alert_config.get_alert_config = AsyncMock(side_effect=get_alert_side_effect)

    response_wrong_agent = client.get(f"/api/v1/agents/{agent_id}/alerts/{alert_id_found_wrong_agent}")
    assert response_wrong_agent.status_code == 404

    response_not_found = client.get(f"/api/v1/agents/{agent_id}/alerts/{alert_id_not_found}")
    assert response_not_found.status_code == 404


def test_update_specific_alert_config():
    agent_id = "agent_update_one_alert"
    alert_id = str(uuid.uuid4())
    update_payload: Dict[str, Any] = {"name": "Updated Name via API", "is_enabled": False}

    original_alert = _create_sample_alert_config_output(agent_id, alert_id, name="Original API Name")
    # Simulate what the service's update_alert_config would return
    updated_alert_mock_return = original_alert.model_copy(
        update=update_payload,
        deep=True # Important for nested models if any were being updated
    )
    updated_alert_mock_return.updated_at = datetime.now(timezone.utc)


    mock_service_alert_config.get_alert_config = AsyncMock(return_value=original_alert) # For route pre-check
    mock_service_alert_config.update_alert_config = AsyncMock(return_value=updated_alert_mock_return)

    response = client.put(f"/api/v1/agents/{agent_id}/alerts/{alert_id}", json=update_payload)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["name"] == "Updated Name via API"
    assert response_json["is_enabled"] is False
    mock_service_alert_config.get_alert_config.assert_called_once_with(alert_id)
    mock_service_alert_config.update_alert_config.assert_called_once_with(alert_id, update_payload)


def test_update_alert_config_not_found_or_wrong_agent():
    agent_id = "agent_update_nf"
    alert_id = str(uuid.uuid4())
    update_payload = {"name": "Ghost Update"}
    mock_service_alert_config.get_alert_config = AsyncMock(return_value=None) # For route pre-check

    response = client.put(f"/api/v1/agents/{agent_id}/alerts/{alert_id}", json=update_payload)
    assert response.status_code == 404
    mock_service_alert_config.update_alert_config.assert_not_called()


def test_delete_specific_alert_config():
    agent_id = "agent_delete_one_alert"
    alert_id = str(uuid.uuid4())
    original_alert = _create_sample_alert_config_output(agent_id, alert_id)

    mock_service_alert_config.get_alert_config = AsyncMock(return_value=original_alert) # For route pre-check
    mock_service_alert_config.delete_alert_config = AsyncMock(return_value=True)

    response = client.delete(f"/api/v1/agents/{agent_id}/alerts/{alert_id}")
    assert response.status_code == 204
    mock_service_alert_config.delete_alert_config.assert_called_once_with(alert_id)

def test_delete_alert_config_not_found_or_wrong_agent():
    agent_id = "agent_delete_nf"
    alert_id = str(uuid.uuid4())
    mock_service_alert_config.get_alert_config = AsyncMock(return_value=None) # For route pre-check

    response = client.delete(f"/api/v1/agents/{agent_id}/alerts/{alert_id}")
    assert response.status_code == 404
    mock_service_alert_config.delete_alert_config.assert_not_called()

