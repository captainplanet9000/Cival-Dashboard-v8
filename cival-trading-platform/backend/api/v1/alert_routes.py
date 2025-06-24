from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional, Dict, Any

from python_ai_services.models.alert_models import (
    AlertConfigInput,
    AlertConfigOutput
)
from python_ai_services.services.alert_configuration_service import AlertConfigurationService

router = APIRouter()

# Dependency for AlertConfigurationService
# Similar to AgentManagementService, instantiate it directly for this phase.
_alert_config_service_instance = AlertConfigurationService()

def get_alert_configuration_service() -> AlertConfigurationService:
    return _alert_config_service_instance

@router.post(
    "/agents/{agent_id}/alerts",
    response_model=AlertConfigOutput,
    status_code=201,
    summary="Create Alert Configuration",
    description="Create a new alert configuration for a specific agent."
)
async def create_alert_config_for_agent(
    agent_id: str,
    config_input: AlertConfigInput,
    service: AlertConfigurationService = Depends(get_alert_configuration_service)
):
    # Note: Agent existence check might be desired here via AgentManagementService,
    # or rely on service/business logic to handle invalid agent_ids if necessary.
    # For now, AlertConfigurationService doesn't validate agent_id against AgentManagementService.
    try:
        return await service.create_alert_config(agent_id, config_input)
    except ValueError as e: # Catch Pydantic validation errors from models
        raise HTTPException(status_code=422, detail=str(e))


@router.get(
    "/agents/{agent_id}/alerts",
    response_model=List[AlertConfigOutput],
    summary="List Alert Configurations",
    description="Retrieve all alert configurations for a specific agent. Can filter by enabled status."
)
async def list_alert_configs_for_agent(
    agent_id: str,
    only_enabled: bool = False, # Query parameter
    service: AlertConfigurationService = Depends(get_alert_configuration_service)
):
    return await service.get_alert_configs_for_agent(agent_id, only_enabled)

@router.get(
    "/agents/{agent_id}/alerts/{alert_id}",
    response_model=AlertConfigOutput,
    summary="Get Alert Configuration",
    description="Retrieve a specific alert configuration by its ID and agent ID."
)
async def get_specific_alert_config(
    agent_id: str, # Used to ensure alert belongs to agent, though service currently only uses alert_id
    alert_id: str,
    service: AlertConfigurationService = Depends(get_alert_configuration_service)
):
    alert_config = await service.get_alert_config(alert_id)
    if not alert_config or alert_config.agent_id != agent_id:
        raise HTTPException(status_code=404, detail=f"Alert config with ID {alert_id} not found for agent {agent_id}.")
    return alert_config

@router.put(
    "/agents/{agent_id}/alerts/{alert_id}",
    response_model=AlertConfigOutput,
    summary="Update Alert Configuration",
    description="Update an existing alert configuration. Only provided fields will be updated."
)
async def update_specific_alert_config(
    agent_id: str, # Path parameter to scope, though service primarily uses alert_id
    alert_id: str,
    update_data: Dict[str, Any] = Body(...), # Using Dict[str, Any] as per service method
    service: AlertConfigurationService = Depends(get_alert_configuration_service)
):
    # Check if alert belongs to the agent before updating
    existing_alert = await service.get_alert_config(alert_id)
    if not existing_alert or existing_alert.agent_id != agent_id:
        raise HTTPException(status_code=404, detail=f"Alert config with ID {alert_id} not found for agent {agent_id} for update.")

    try:
        updated_config = await service.update_alert_config(alert_id, update_data)
        if not updated_config: # Should not happen if previous check passed, unless race condition or internal error
            raise HTTPException(status_code=404, detail=f"Failed to update alert config {alert_id}.")
        return updated_config
    except ValueError as e: # Catch Pydantic validation errors from models if service re-validates badly
        raise HTTPException(status_code=422, detail=str(e))


@router.delete(
    "/agents/{agent_id}/alerts/{alert_id}",
    status_code=204, # No content
    summary="Delete Alert Configuration",
    description="Delete a specific alert configuration by its ID and agent ID."
)
async def delete_specific_alert_config(
    agent_id: str, # Path parameter to scope
    alert_id: str,
    service: AlertConfigurationService = Depends(get_alert_configuration_service)
):
    # Optional: Check if alert belongs to the agent before deleting
    existing_alert = await service.get_alert_config(alert_id)
    if not existing_alert or existing_alert.agent_id != agent_id:
        raise HTTPException(status_code=404, detail=f"Alert config {alert_id} not found for agent {agent_id}.")

    deleted = await service.delete_alert_config(alert_id)
    if not deleted: # Should ideally not happen if previous check passed
        raise HTTPException(status_code=404, detail=f"Alert config {alert_id} could not be deleted or was already deleted.")
    return None # For 204 response
