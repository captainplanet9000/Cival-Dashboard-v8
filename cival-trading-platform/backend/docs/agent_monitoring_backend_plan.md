# Backend Plan: Agent & System Monitoring

## 1. Introduction & Goals

Effective monitoring is crucial for understanding the operational status, performance, and reliability of our AI agent system. This plan outlines the backend components required to monitor agent task execution, overall system health, and potentially agent memory usage. The goals are to provide operational insight for debugging, performance tracking, and ensuring system stability.

## 2. Key Monitoring Data Points

The following data points are identified as key for monitoring:

*   **Agent Task Lifecycle & Details:**
    *   `task_id`: Unique identifier for each task execution.
    *   `crew_id`: Identifier for the crew definition that executed the task (e.g., "trading_analysis_crew").
    *   `status`: Current status of the task (e.g., PENDING, RUNNING, COMPLETED, FAILED).
    *   `start_time`, `end_time`, `duration_ms`: Timing information for performance analysis.
    *   `inputs`: Key inputs provided to the task (potentially summarized or selectively chosen to avoid excessive storage, e.g., symbol, timeframe, strategy_name).
    *   `output`: The result of the task (potentially summarized or a reference to where the full output is stored).
    *   `error_message`: Any error message if the task failed.
    *   `logs_summary`: Key log entries or a summary of interactions during the task (e.g., agent steps, tool calls, warnings).

*   **CrewAI Agent Interactions (to be logged within `AgentTask.logs_summary`):**
    *   Individual agent steps within a task.
    *   Tool calls made by agents (tool name, inputs, outputs).
    *   (Conceptual) LLM interaction metrics: token counts, latency per call (if obtainable from LLM provider/Langchain).

*   **`MemoryService` / MemGPT (Letta) Usage (Conceptual - Requires `MemoryService` to track/expose):**
    *   Number of memory store operations per `app_agent_id`.
    *   Number of memory recall operations per `app_agent_id`.
    *   Timestamp of last activity for a given `app_agent_id`.
    *   (Future) Size of memory store per agent, frequency of specific memory access.

*   **API Endpoint Performance (via API Gateway/FastAPI Middleware & Logging):**
    *   Request counts per endpoint.
    *   Error rates (4xx, 5xx) per endpoint.
    *   Latency (p50, p90, p99) per endpoint.

*   **System Health (derived from existing `/health/deep`):**
    *   Overall system status ("healthy", "unhealthy", "degraded").
    *   Status of critical dependencies (Redis, Supabase client, Letta client).

## 3. Monitoring API Endpoints

### GET `/api/v1/monitoring/tasks`
- **Summary:** List agent tasks with pagination and filtering capabilities.
- **Query Parameters:**
    - `crew_id: Optional[str] = None` (Filter by crew ID)
    - `status: Optional[TaskStatus] = None` (Filter by task status: PENDING, RUNNING, COMPLETED, FAILED)
    - `start_date_from: Optional[datetime] = None` (Filter tasks started from this date/time)
    - `start_date_to: Optional[datetime] = None` (Filter tasks started up to this date/time)
    - `limit: int = Field(default=20, ge=1, le=100)` (Number of tasks to return)
    - `offset: int = Field(default=0, ge=0)` (Offset for pagination)
- **Response Model:** `TaskListResponse`
- **Tags:** `["Monitoring"]`

### GET `/api/v1/monitoring/tasks/{task_id}`
- **Summary:** Get detailed information for a specific agent task.
- **Path Parameter:** `task_id: UUID` (The unique ID of the task)
- **Response Model:** `AgentTask` (The full model from `models.crew_models`)
- **Tags:** `["Monitoring"]`

### GET `/api/v1/monitoring/agents/{app_agent_id}/memory/stats` (Conceptual)
- **Summary:** Get memory usage statistics for a specific application agent ID (as used by `MemoryService`).
- **Path Parameter:** `app_agent_id: str`
- **Response Model:** `AgentMemoryStats`
- **Tags:** `["Monitoring", "Memory"]`
- **Note:** This endpoint is conceptual and depends on `MemoryService` implementing stat collection or a way to query such stats from the Letta server.

### GET `/api/v1/monitoring/system/health`
- **Summary:** Provides a summarized system health status, derived from the more detailed `/health/deep` endpoint.
- **Response Model:** `SystemHealthSummary`
- **Tags:** `["Monitoring", "Health"]`

## 4. Pydantic Models for Monitoring API

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

# Note: AgentTask model is assumed to be defined in ..models.crew_models
# from ..models.crew_models import AgentTask

# TaskStatus enum, often defined in ..models.crew_models or ..types
# Re-defined here for clarity if this doc is standalone.
class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AgentTaskSummary(BaseModel):
    """Summary of an agent task for list views."""
    task_id: UUID
    crew_id: Optional[str] = None # Made optional as it might not always be set for all types of tasks initially
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None # Calculated: (end_time - start_time) in ms
    input_summary: Optional[Dict[str, Any]] = Field(None, description="Key inputs, e.g., symbol, timeframe, strategy. Avoid large objects.")
    error_preview: Optional[str] = Field(None, description="Short preview of error_message if status is FAILED.")

class TaskListResponse(BaseModel):
    """Response model for listing agent tasks."""
    tasks: List[AgentTaskSummary]
    total: int # Total number of tasks matching filter criteria
    limit: int
    offset: int

class AgentMemoryStats(BaseModel): # Conceptual model for memory stats
    """Statistics for an agent's memory usage (via MemoryService/Letta)."""
    app_agent_id: str
    letta_agent_id: Optional[str] = None # The corresponding ID on the Letta server
    memories_stored_count: Optional[int] = Field(None, description="Conceptual: Number of messages/observations stored.")
    memories_recalled_count: Optional[int] = Field(None, description="Conceptual: Number of times memories were recalled.")
    last_activity_timestamp: Optional[datetime] = None
    # Other potential stats: core_memory_size_kb, archival_memory_size_kb, vector_db_entries_count

class DependencyStatus(BaseModel):
    """Represents the status of a single system dependency."""
    name: str
    status: str # e.g., "connected", "disconnected", "unhealthy", "healthy", "not_configured"
    details: Optional[str] = None

class SystemHealthSummary(BaseModel):
    """Summarized system health status."""
    overall_status: str = Field(..., example="healthy", description="Overall health: 'healthy', 'unhealthy', 'degraded'.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service_statuses: List[DependencyStatus] # List of key dependencies and their statuses
```

## 5. Service Logic Outline

### For `GET /api/v1/monitoring/tasks`:
- **Route Handler (`main.py`):**
    - Accepts query parameters: `crew_id`, `status`, `start_date_from`, `start_date_to`, `limit`, `offset`.
    - Validates parameters (FastAPI handles Pydantic model validation for path/query params if models are used).
    - Retrieves `AgentPersistenceService` from `app_services`.
    - Calls `tasks_data, total_count = await agent_persistence_service.list_and_count_agent_tasks_paginated(...)` with validated filters.
    - Iterates through `tasks_data` to create `AgentTaskSummary` objects:
        - Calculates `duration_ms` if `end_time` is present.
        - Creates `input_summary` by selectively picking key fields from `task.inputs` (e.g., "symbol", "timeframe", "strategy_name"). Avoids logging full, potentially large, `strategy_config`.
        - Creates `error_preview` by taking the first N characters of `task.error_message`.
    - Returns `TaskListResponse(tasks=summaries, total=total_count, limit=limit, offset=offset)`.
- **`AgentPersistenceService.list_and_count_agent_tasks_paginated` Method:**
    - Signature: `async def list_and_count_agent_tasks_paginated(self, crew_id: Optional[str] = None, status: Optional[str] = None, start_date_from: Optional[datetime] = None, start_date_to: Optional[datetime] = None, limit: int = 20, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:` (Returns raw dicts from DB)
    - Logic:
        1.  Construct base Supabase query for `agent_tasks` table.
        2.  Apply filters (`eq` for `crew_id`, `status`; `gte` for `start_date_from` on `start_time`; `lte` for `start_date_to` on `start_time`).
        3.  Execute a `count` query with the same filters (e.g., `self.supabase_client.table("agent_tasks").select("*", count="exact")...execute()`). Store `total_count`.
        4.  Apply `order("start_time", desc=True)`, `offset(offset)`, `limit(limit)` to the data query.
        5.  Execute data query.
        6.  Return `(task_list_from_db, total_count)`. Handle DB errors.

### For `GET /api/v1/monitoring/tasks/{task_id}`:
- **Route Handler (`main.py`):**
    - Accepts `task_id: UUID` path parameter.
    - Retrieves `AgentPersistenceService`.
    - Calls `task_data = await agent_persistence_service.get_agent_task(str(task_id))`.
    - If `task_data` is found, return it directly (as `AgentTask` model is already used for this method's return type hint in service, and should be compatible with the DB schema).
    - If not found, raise `HTTPException(status_code=404, detail="Task not found")`.
- **`AgentPersistenceService.get_agent_task`:** (Existing method)
    - Ensure this method fetches all necessary fields from the `agent_tasks` table to fully populate the `AgentTask` Pydantic model defined in `models.crew_models`.

### For `GET /api/v1/monitoring/agents/{app_agent_id}/memory/stats` (Conceptual):
- **Route Handler (`main.py`):**
    - Accepts `app_agent_id: str` path parameter.
    - Retrieves `MemoryService` from `app_services`.
    - If `MemoryService` is unavailable or `letta-client` is not functional, return an appropriate error (e.g., 503 Service Unavailable or specific error message).
    - Calls `stats = await memory_service.get_agent_memory_stats(app_agent_id)`. (This method needs to be created in `MemoryService`).
    - If `stats` are found, return them.
    - If not found (e.g., agent ID unknown to `MemoryService`), raise `HTTPException(status_code=404, detail="Agent memory stats not found or agent unknown")`.
- **`MemoryService.get_agent_memory_stats` Method (Conceptual - to be added to `MemoryService`):**
    - Signature: `async def get_agent_memory_stats(self, app_agent_id: str) -> Optional[AgentMemoryStats]:`
    - Logic:
        1.  Retrieve `letta_agent_id` associated with `app_agent_id` (e.g., from cache or persistence). If not found, return `None`.
        2.  **Conceptual:** Query the Letta server for statistics related to `letta_agent_id`. The `letta-client` SDK would need to support this. This might involve:
            *   Getting agent details which might include memory usage metrics.
            *   Querying message counts or memory interaction counts if exposed by Letta API.
        3.  If Letta doesn't provide these directly, `MemoryService` might need to infer some stats by logging its own interactions (e.g., count calls to `store_memory_message`, `get_memory_response` per `app_agent_id`) and storing these in Redis or its own DB table. This is more complex.
        4.  For this plan, assume a simple stub: return mock data like `AgentMemoryStats(app_agent_id=app_agent_id, letta_agent_id=letta_id, memories_stored_count=0, memories_recalled_count=0, last_activity_timestamp=datetime.utcnow())`.

### For `GET /api/v1/monitoring/system/health`:
- **Route Handler (`main.py`):**
    - Call the existing `/health/deep` endpoint logic internally (or refactor `/health/deep`'s core logic into a reusable function).
    - Process the `dependencies` list from `/health/deep`'s output.
    - Construct the `SystemHealthSummary` model:
        - `overall_status` can be derived (e.g., "healthy" if all critical dependencies are "connected" or "healthy", "unhealthy" if any critical one is "disconnected"/"unhealthy", "degraded" otherwise).
        - `service_statuses` will be a list of `DependencyStatus` objects, mapped from the `/health/deep` output.
    - Return the `SystemHealthSummary`.

## 6. Conceptual Frontend Visualization (Brief Note)

The monitoring API endpoints will enable a frontend dashboard to display:
- A sortable and filterable list of all agent/crew tasks, showing key summary data.
- Detailed views for individual tasks, providing access to inputs, full outputs (or previews), error messages, and log summaries.
- (Future, if `AgentMemoryStats` is implemented) Statistics on agent memory usage, such as message counts and last activity.
- A system health overview panel indicating the status of the backend service and its critical dependencies.
