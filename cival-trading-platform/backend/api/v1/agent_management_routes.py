from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

from python_ai_services.models.agent_models import (
    AgentConfigInput,
    AgentConfigOutput,
    AgentUpdateRequest,
    AgentStatus
)
from python_ai_services.services.agent_management_service import AgentManagementService

router = APIRouter()

from python_ai_services.core.database import SessionLocal # Import the session factory

# Dependency for AgentManagementService
# Instantiate with the session factory. This instance will be a singleton for the app.
_agent_service_instance = AgentManagementService(session_factory=SessionLocal)

# It's good practice to have an async function to initialize things if needed,
# like calling _load_existing_statuses_from_db. This can be tied to FastAPI startup.
# For now, _load_existing_statuses_from_db would be called separately or via first request to relevant method.
# However, the service is designed to be robust if status isn't in memory yet.

# To ensure statuses are loaded at startup, you might do this in main.py or here (if this module is loaded early):
# asyncio.create_task(_agent_service_instance._load_existing_statuses_from_db())
# This is a bit advanced for a simple route file. Better in main.py startup event.


def get_agent_management_service() -> AgentManagementService:
    # This now returns the singleton initialized with the DB session factory.
    return _agent_service_instance

@router.post("/agents", response_model=AgentConfigOutput, status_code=201)
async def create_new_agent(
    agent_input: AgentConfigInput,
    service: AgentManagementService = Depends(get_agent_management_service)
):
    """
    Create a new trading agent configuration.
    """
    return await service.create_agent(agent_input)

@router.get("/agents", response_model=List[AgentConfigOutput])
async def list_all_agents(
    service: AgentManagementService = Depends(get_agent_management_service)
):
    """
    Retrieve a list of all configured trading agents.
    """
    return await service.get_agents()

@router.get("/agents/{agent_id}", response_model=AgentConfigOutput)
async def get_specific_agent(
    agent_id: str,
    service: AgentManagementService = Depends(get_agent_management_service)
):
    """
    Retrieve the configuration for a specific trading agent by its ID.
    """
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found.")
    return agent

@router.put("/agents/{agent_id}", response_model=AgentConfigOutput)
async def update_existing_agent(
    agent_id: str,
    update_data: AgentUpdateRequest,
    service: AgentManagementService = Depends(get_agent_management_service)
):
    """
    Update an existing trading agent's configuration.
    Only fields provided in the request body will be updated.
    """
    updated_agent = await service.update_agent(agent_id, update_data)
    if not updated_agent:
        raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found for update.")
    return updated_agent

@router.delete("/agents/{agent_id}", status_code=204) # No content response for successful delete
async def delete_specific_agent(
    agent_id: str,
    service: AgentManagementService = Depends(get_agent_management_service)
):
    """
    Delete a specific trading agent by its ID.
    """
    deleted = await service.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found for deletion.")
    return None # Return None for 204 status code

@router.post("/agents/{agent_id}/start", response_model=AgentStatus)
async def start_specific_agent(
    agent_id: str,
    service: AgentManagementService = Depends(get_agent_management_service)
):
    """
    Start a specific trading agent. (Simulated: updates status to 'running')
    """
    try:
        status = await service.start_agent(agent_id)
        return status
    except ValueError as e: # Raised by service if agent not found
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/agents/{agent_id}/stop", response_model=AgentStatus)
async def stop_specific_agent(
    agent_id: str,
    service: AgentManagementService = Depends(get_agent_management_service)
):
    """
    Stop a specific trading agent. (Simulated: updates status to 'stopped')
    """
    try:
        status = await service.stop_agent(agent_id)
        return status
    except ValueError as e: # Raised by service if agent not found
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/agents/{agent_id}/status", response_model=AgentStatus)
async def get_specific_agent_status(
    agent_id: str,
    service: AgentManagementService = Depends(get_agent_management_service)
):
    """
    Retrieve the current status of a specific trading agent.
    """
    status = await service.get_agent_status(agent_id)
    if not status:
        # Service's get_agent_status might return a default 'stopped' status if agent exists but status was missing.
        # If it strictly returns None only when agent is unknown, this 404 is fine.
        # Based on current service impl, it returns a default or None if agent itself not found.
        # So, if status is None, it means agent ID is truly unknown.
        raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found or no status available.")
    return status
