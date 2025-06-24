import pytest
import pytest_asyncio
from datetime import datetime, timezone
import uuid
from typing import Dict, Any

from python_ai_services.models.alert_models import (
    AlertConfigInput,
    AlertConfigOutput,
    AlertCondition
)
from python_ai_services.services.alert_configuration_service import AlertConfigurationService

@pytest_asyncio.fixture
async def service() -> AlertConfigurationService:
    """Provides a fresh instance of AlertConfigurationService for each test."""
    return AlertConfigurationService()

def create_sample_alert_condition() -> AlertCondition:
    return AlertCondition(metric="account_value_usd", operator="<", threshold=1000.0)

def create_sample_alert_input(name: str = "Test Alert") -> AlertConfigInput:
    return AlertConfigInput(
        name=name,
        conditions=[create_sample_alert_condition()],
        notification_channels=["log"]
    )

@pytest.mark.asyncio
async def test_create_alert_config(service: AlertConfigurationService):
    agent_id = "agent_for_alerts_1"
    alert_input = create_sample_alert_input()

    created_config = await service.create_alert_config(agent_id, alert_input)

    assert isinstance(created_config, AlertConfigOutput)
    assert created_config.name == alert_input.name
    assert created_config.agent_id == agent_id
    assert created_config.alert_id is not None
    assert len(created_config.conditions) == 1
    assert created_config.conditions[0].metric == "account_value_usd"

@pytest.mark.asyncio
async def test_get_alert_config(service: AlertConfigurationService):
    agent_id = "agent_get_alert"
    alert_input = create_sample_alert_input()
    created_config = await service.create_alert_config(agent_id, alert_input)

    retrieved_config = await service.get_alert_config(created_config.alert_id)
    assert retrieved_config is not None
    assert retrieved_config.alert_id == created_config.alert_id
    assert retrieved_config.name == alert_input.name

    non_existent_config = await service.get_alert_config(str(uuid.uuid4()))
    assert non_existent_config is None

@pytest.mark.asyncio
async def test_get_alert_configs_for_agent(service: AlertConfigurationService):
    agent_id_1 = "agent_multi_alerts_1"
    agent_id_2 = "agent_multi_alerts_2"

    config1_agent1 = await service.create_alert_config(agent_id_1, create_sample_alert_input("Alert1_A1"))
    config2_agent1_disabled = await service.create_alert_config(agent_id_1, create_sample_alert_input("Alert2_A1"))
    # Manually disable one for testing filter
    config2_agent1_disabled.is_enabled = False
    service._alerts_configs[config2_agent1_disabled.alert_id] = config2_agent1_disabled # Update internal store

    await service.create_alert_config(agent_id_2, create_sample_alert_input("Alert1_A2"))

    # Get all for agent_id_1
    agent1_configs = await service.get_alert_configs_for_agent(agent_id_1)
    assert len(agent1_configs) == 2
    assert any(c.alert_id == config1_agent1.alert_id for c in agent1_configs)
    assert any(c.alert_id == config2_agent1_disabled.alert_id for c in agent1_configs)

    # Get only enabled for agent_id_1
    agent1_enabled_configs = await service.get_alert_configs_for_agent(agent_id_1, only_enabled=True)
    assert len(agent1_enabled_configs) == 1
    assert agent1_enabled_configs[0].alert_id == config1_agent1.alert_id
    assert agent1_enabled_configs[0].is_enabled is True

    # Get for agent_id_2
    agent2_configs = await service.get_alert_configs_for_agent(agent_id_2)
    assert len(agent2_configs) == 1

    # Get for non-existent agent
    no_agent_configs = await service.get_alert_configs_for_agent("non_existent_agent")
    assert len(no_agent_configs) == 0

@pytest.mark.asyncio
async def test_update_alert_config(service: AlertConfigurationService):
    agent_id = "agent_update_alert"
    alert_input = create_sample_alert_input(name="Initial Alert Name")
    created_config = await service.create_alert_config(agent_id, alert_input)
    original_updated_at = created_config.updated_at

    update_payload: Dict[str, Any] = {
        "name": "Updated Alert Name",
        "is_enabled": False,
        "cooldown_seconds": 600,
        "conditions": [ # Replace conditions
            AlertCondition(metric="total_pnl_usd", operator=">", threshold=500.0).model_dump()
        ]
    }

    # Ensure time passes for updated_at check
    await asyncio.sleep(0.01)
    updated_config = await service.update_alert_config(created_config.alert_id, update_payload)

    assert updated_config is not None
    assert updated_config.name == "Updated Alert Name"
    assert updated_config.is_enabled is False
    assert updated_config.cooldown_seconds == 600
    assert len(updated_config.conditions) == 1
    assert updated_config.conditions[0].metric == "total_pnl_usd"
    assert updated_config.updated_at > original_updated_at

    # Test partial update: only name
    partial_update_payload = {"name": "Super Updated Name"}
    further_updated_config = await service.update_alert_config(created_config.alert_id, partial_update_payload)
    assert further_updated_config is not None
    assert further_updated_config.name == "Super Updated Name"
    assert further_updated_config.is_enabled is False # Should remain from previous update

    # Test updating a non-existent config
    non_existent_update = await service.update_alert_config(str(uuid.uuid4()), {"name": "ghost"})
    assert non_existent_update is None

    # Test update with invalid data that would fail Pydantic validation (e.g. bad condition)
    invalid_update_payload = {"conditions": [{"metric": "account_value_usd", "operator": ">>", "threshold": 100}]} # Invalid operator
    failed_update_config = await service.update_alert_config(created_config.alert_id, invalid_update_payload)
    # The service's update re-constructs AlertConfigOutput, so Pydantic validation should catch this.
    # Depending on how Pydantic errors are caught and propagated, this might return None or raise.
    # Current service returns None on Pydantic error in update.
    assert failed_update_config is None

@pytest.mark.asyncio
async def test_delete_alert_config(service: AlertConfigurationService):
    agent_id = "agent_delete_alert"
    alert_input = create_sample_alert_input()
    created_config = await service.create_alert_config(agent_id, alert_input)

    assert await service.get_alert_config(created_config.alert_id) is not None
    deleted = await service.delete_alert_config(created_config.alert_id)
    assert deleted is True
    assert await service.get_alert_config(created_config.alert_id) is None

    # Try to delete non-existent config
    deleted_non_existent = await service.delete_alert_config(str(uuid.uuid4()))
    assert deleted_non_existent is False

# Need asyncio for sleep
import asyncio
