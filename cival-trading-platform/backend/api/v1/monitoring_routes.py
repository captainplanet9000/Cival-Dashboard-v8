from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from uuid import UUID
from loguru import logger

# Adjust relative paths based on the final location of this file
# Assuming this file is in /api/v1/ and services/models are siblings of /api
try:
    from ...services.agent_persistence_service import AgentPersistenceService
    from ...services.memory_service import MemoryService, LETTA_CLIENT_AVAILABLE as MEMORY_SERVICE_LETTA_LIB_AVAILABLE
    from ...models.crew_models import AgentTask, TaskStatus # Full AgentTask model
    from ...models.monitoring_models import (
        AgentTaskSummary, TaskListResponse,
        AgentMemoryStats,
        SystemHealthSummary, DependencyStatus
    )
    from ...main import services as app_services # Accessing the global 'services' dict
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import dependencies for monitoring_routes: {e}. API may not function correctly.")
    SERVICES_AVAILABLE = False
    # Define placeholders if imports fail, to allow file to be parsable
    AgentPersistenceService = type('AgentPersistenceService', (), {})
    MemoryService = type('MemoryService', (), {})
    AgentTask = type('AgentTask', (), {}) # type: ignore
    class TaskStatus(str, Enum): PENDING="PENDING"; RUNNING="RUNNING"; COMPLETED="COMPLETED"; FAILED="FAILED" # type: ignore
    AgentTaskSummary = type('AgentTaskSummary', (), {}) # type: ignore
    TaskListResponse = type('TaskListResponse', (), {}) # type: ignore
    AgentMemoryStats = type('AgentMemoryStats', (), {}) # type: ignore
    SystemHealthSummary = type('SystemHealthSummary', (), {}) # type: ignore
    DependencyStatus = type('DependencyStatus', (), {}) # type: ignore
    app_services: Dict[str, Any] = {}
    MEMORY_SERVICE_LETTA_LIB_AVAILABLE = False


router = APIRouter(
    prefix="/api/v1/monitoring",
    tags=["Monitoring"]
)

# Helper function to encapsulate the core logic of /health/deep
# This will be called by main.py's /health/deep and the new /system/health route.
async def get_deep_health_logic(current_request: Request) -> Dict[str, Any]:
    """
    Provides detailed health check logic for critical dependencies.
    This function is intended to be reusable by different health endpoints.
    """
    dependencies_status_list: List[Dict[str, Any]] = []
    overall_app_status: str = "healthy" # Assume healthy until a check fails critically
    # http_status_code: int = 200 # Not used by this helper directly, but by endpoint calling it.

    if not SERVICES_AVAILABLE: # If core imports failed
        dependencies_status_list.append({"name": "core_services_import", "status": "failed", "details": "Critical service/model imports failed."})
        overall_app_status = "unhealthy"
        return {"overall_status": overall_app_status, "dependencies": dependencies_status_list}

    # 1. Check Redis Cache Client (from app.state, passed via current_request)
    redis_cache_client = current_request.app.state.redis_cache_client if hasattr(current_request.app.state, 'redis_cache_client') else None
    if redis_cache_client:
        try:
            await redis_cache_client.ping()
            dependencies_status_list.append({"name": "redis_cache", "status": "connected"})
        except Exception as e:
            dependencies_status_list.append({"name": "redis_cache", "status": "disconnected", "error": str(e)})
            overall_app_status = "unhealthy"
    else:
        dependencies_status_list.append({"name": "redis_cache", "status": "not_configured"})
        # Not necessarily unhealthy if caching is optional.

    # 2. Check AgentPersistenceService (Supabase & Redis clients)
    persistence_svc = app_services.get("agent_persistence_service")
    if persistence_svc and isinstance(persistence_svc, AgentPersistenceService):
        supabase_status = "connected" if persistence_svc.supabase_client else "not_connected_or_configured"
        redis_persistence_status = "connected" if persistence_svc.redis_client else "not_connected_or_configured"
        dependencies_status_list.append({"name": "agent_persistence_supabase_client", "status": supabase_status})
        dependencies_status_list.append({"name": "agent_persistence_redis_client", "status": redis_persistence_status})
        if not persistence_svc.supabase_client or not persistence_svc.redis_client:
            # If either critical persistence client is down, service might be impaired
            if overall_app_status != "unhealthy": overall_app_status = "degraded"
    else:
        dependencies_status_list.append({"name": "agent_persistence_service", "status": "not_initialized"})
        overall_app_status = "unhealthy"

    # 3. Check MemoryService (Letta client)
    memory_svc = app_services.get("memory_service")
    if memory_svc and isinstance(memory_svc, MemoryService):
        letta_client_status = "connected_conceptual" if memory_svc.letta_client else "not_connected"
        if MEMORY_SERVICE_LETTA_LIB_AVAILABLE and not memory_svc.letta_client:
            letta_client_status = "connection_failed" # Library there, but client not init
            if overall_app_status != "unhealthy": overall_app_status = "degraded"
        elif not MEMORY_SERVICE_LETTA_LIB_AVAILABLE:
            letta_client_status = "library_unavailable_stub_mode"
            # This might be acceptable, so not necessarily degrading overall status unless Letta is critical.

        dependencies_status_list.append({
            "name": "memory_service_letta_client",
            "status": letta_client_status,
            "letta_library_available": MEMORY_SERVICE_LETTA_LIB_AVAILABLE
        })
    else:
        dependencies_status_list.append({"name": "memory_service", "status": "not_initialized"})
        if overall_app_status != "unhealthy": overall_app_status = "degraded" # Memory is important

    # Add checks for other critical services if any (e.g., TradingCrewService, AgentStateManager)
    if not app_services.get("agent_state_manager"):
        dependencies_status_list.append({"name": "agent_state_manager", "status": "not_initialized"})
        overall_app_status = "unhealthy"
    else:
        dependencies_status_list.append({"name": "agent_state_manager", "status": "initialized"})

    if not app_services.get("trading_crew_service"):
        dependencies_status_list.append({"name": "trading_crew_service", "status": "not_initialized"})
        if overall_app_status != "unhealthy": overall_app_status = "degraded"
    else:
        dependencies_status_list.append({"name": "trading_crew_service", "status": "initialized"})

    return {"overall_status": overall_app_status, "dependencies": dependencies_status_list}


@router.get("/tasks", response_model=TaskListResponse, summary="List Agent Tasks")
async def list_tasks(
    crew_id: Optional[str] = Query(None, description="Filter tasks by specific crew_id."),
    status: Optional[TaskStatus] = Query(None, description="Filter tasks by status."),
    start_date_from: Optional[datetime] = Query(None, description="Filter tasks starting from this ISO datetime."),
    start_date_to: Optional[datetime] = Query(None, description="Filter tasks starting up to this ISO datetime."),
    limit: int = Query(20, ge=1, le=100, description="Number of tasks to return."),
    offset: int = Query(0, ge=0, description="Offset for pagination.")
):
    if not SERVICES_AVAILABLE or not AgentPersistenceService: # Check if class itself was imported
        raise HTTPException(status_code=503, detail="AgentPersistenceService not available due to import errors.")

    persistence_service: Optional[AgentPersistenceService] = app_services.get("agent_persistence_service")
    if not persistence_service:
        raise HTTPException(status_code=503, detail="AgentPersistenceService not available.")

    try:
        raw_tasks, total_count = await persistence_service.list_and_count_agent_tasks_paginated(
            crew_id=crew_id, status=status, start_date_from=start_date_from,
            start_date_to=start_date_to, limit=limit, offset=offset
        )
    except Exception as e:
        logger.exception(f"Error listing agent tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tasks from database.")

    task_summaries: List[AgentTaskSummary] = []
    for task_dict in raw_tasks:
        duration_ms = None
        if task_dict.get("start_time") and task_dict.get("end_time"):
            start = task_dict["start_time"]
            end = task_dict["end_time"]
            if isinstance(start, str): start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            if isinstance(end, str): end = datetime.fromisoformat(end.replace("Z", "+00:00"))
            if isinstance(start, datetime) and isinstance(end, datetime): # Ensure they are datetime objects
                 duration_ms = (end - start).total_seconds() * 1000

        input_data = task_dict.get("inputs")
        input_summary_preview = {}
        if isinstance(input_data, dict):
            # Selectively pick key fields for summary, avoid large/sensitive data
            for key in ["symbol", "timeframe", "strategy_name", "llm_config_id", "crew_run_id"]:
                if key in input_data:
                    input_summary_preview[key] = input_data[key]
            if "strategy_config" in input_data and isinstance(input_data["strategy_config"], dict):
                input_summary_preview["strategy_config_keys"] = list(input_data["strategy_config"].keys())


        error_msg = task_dict.get("error_message")
        error_preview_str = (error_msg[:100] + '...') if error_msg and len(error_msg) > 100 else error_msg

        task_summaries.append(AgentTaskSummary(
            task_id=task_dict["task_id"],
            crew_id=task_dict.get("crew_id"),
            status=TaskStatus(task_dict["status"]), # Cast to enum
            start_time=task_dict["start_time"],
            end_time=task_dict.get("end_time"),
            duration_ms=duration_ms,
            input_summary=input_summary_preview if input_summary_preview else None,
            error_preview=error_preview_str
        ))

    return TaskListResponse(tasks=task_summaries, total=total_count, limit=limit, offset=offset)

@router.get("/tasks/{task_id}", response_model=AgentTask, summary="Get Agent Task Details")
async def get_task_details(task_id: UUID = Path(..., description="The UUID of the agent task.")):
    if not SERVICES_AVAILABLE or not AgentPersistenceService:
        raise HTTPException(status_code=503, detail="AgentPersistenceService not available due to import errors.")

    persistence_service: Optional[AgentPersistenceService] = app_services.get("agent_persistence_service")
    if not persistence_service:
        raise HTTPException(status_code=503, detail="AgentPersistenceService not available.")

    task_data = await persistence_service.get_agent_task(str(task_id))
    if not task_data:
        raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found.")

    # FastAPI will validate against AgentTask model.
    # Ensure all fields required by AgentTask are present in task_data or handle missing ones.
    return task_data


@router.get("/agents/{app_agent_id}/memory/stats", response_model=Optional[AgentMemoryStats], summary="Get Agent Memory Statistics (Stubbed)")
async def get_agent_memory_stats_route(app_agent_id: str = Path(..., description="Application-specific agent identifier.")):
    if not SERVICES_AVAILABLE or not MemoryService or AgentMemoryStats is None: # Check also if AgentMemoryStats model loaded
        raise HTTPException(status_code=503, detail="MemoryService or AgentMemoryStats model not available due to import errors.")

    memory_service: Optional[MemoryService] = app_services.get("memory_service")
    if not memory_service:
        raise HTTPException(status_code=503, detail="MemoryService not available.")

    stats = await memory_service.get_agent_memory_stats(app_agent_id)
    if not stats:
        # The service method returns None if agent_id is like "error_case" or if AgentMemoryStats model itself failed to import.
        # If AgentMemoryStats model failed to import in service, stats would be None.
        raise HTTPException(status_code=404, detail=f"Memory stats not found for agent '{app_agent_id}' or service error.")
    return stats


@router.get("/system/health", response_model=SystemHealthSummary, summary="Get Summarized System Health")
async def get_system_health_summary(request: Request):
    if not SERVICES_AVAILABLE or not SystemHealthSummary or not DependencyStatus : # Check if models loaded
         raise HTTPException(status_code=503, detail="SystemHealthSummary or DependencyStatus model not available due to import errors.")

    detailed_health_data = await get_deep_health_logic(request)

    overall_status = detailed_health_data.get("overall_status", "unknown")
    dependencies = detailed_health_data.get("dependencies", [])

    service_statuses: List[DependencyStatus] = []
    for dep in dependencies:
        service_statuses.append(DependencyStatus(
            name=dep.get("name", "Unknown Service"),
            status=dep.get("status", "unknown"),
            details=dep.get("error") # Map 'error' field from deep health to 'details'
        ))

    return SystemHealthSummary(
        overall_status=overall_status,
        service_statuses=service_statuses
        # timestamp will use default_factory
    )

