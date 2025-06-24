from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

# Attempt to import TaskStatus from crew_models, define locally as fallback
try:
    from .crew_models import TaskStatus
except ImportError:
    # Fallback definition if crew_models or TaskStatus is not found (e.g., standalone execution)
    # This ensures the file is self-contained for basic validation if needed.
    class TaskStatus(str, Enum):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

class AgentTaskSummary(BaseModel):
    """Summary of an agent task for list views."""
    task_id: UUID
    crew_id: Optional[str] = None
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = Field(None, description="Task duration in milliseconds, calculated if start_time and end_time are present.")
    input_summary: Optional[Dict[str, Any]] = Field(None, description="Key inputs, e.g., symbol, timeframe, strategy_name. Avoids logging full, potentially large, strategy_config.")
    error_preview: Optional[str] = Field(None, description="Short preview of error_message if status is FAILED.")

    class Config:
        use_enum_values = True # Ensures enum values are used in serialization

class TaskListResponse(BaseModel):
    """Response model for listing agent tasks."""
    tasks: List[AgentTaskSummary]
    total: int = Field(..., description="Total number of tasks matching filter criteria.")
    limit: int
    offset: int

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

if __name__ == '__main__':
    from uuid import uuid4
    # Example Usage
    print("--- Example AgentTaskSummary ---")
    task_summary_example = AgentTaskSummary(
        task_id=uuid4(),
        crew_id="trading_analysis_crew_v1",
        status=TaskStatus.COMPLETED,
        start_time=datetime.utcnow() - timedelta(minutes=5),
        end_time=datetime.utcnow(),
        duration_ms=300000.0,
        input_summary={"symbol": "BTC/USD", "strategy": "DarvasBox"},
        error_preview=None
    )
    print(task_summary_example.model_dump_json(indent=2))

    print("\n--- Example TaskListResponse ---")
    task_list_response_example = TaskListResponse(
        tasks=[task_summary_example],
        total=1,
        limit=20,
        offset=0
    )
    print(task_list_response_example.model_dump_json(indent=2))

    print("\n--- Example DependencyStatus ---")
    dep_status_example = DependencyStatus(name="Redis Cache", status="connected")
    print(dep_status_example.model_dump_json(indent=2))

    print("\n--- Example SystemHealthSummary ---")
    health_summary_example = SystemHealthSummary(
        overall_status="healthy",
        service_statuses=[
            dep_status_example,
            DependencyStatus(name="Supabase DB", status="connected"),
            DependencyStatus(name="Letta Server", status="degraded", details="High latency on memory recall")
        ]
    )
    print(health_summary_example.model_dump_json(indent=2))

    # Example with TaskStatus directly (if imported successfully)
    if TaskStatus.PENDING: # Check if it's a usable enum
        print(f"\nTaskStatus PENDING value: {TaskStatus.PENDING.value}")

    # Add timedelta import for __main__
    from datetime import timedelta
