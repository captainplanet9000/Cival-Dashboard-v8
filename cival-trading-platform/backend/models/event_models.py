from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone
import uuid

# --- Base Event Model ---

class BaseEvent(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the event.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the event occurred (UTC).")
    event_type: str = Field(..., description="Type of the event (e.g., 'AgentTaskStarted', 'AgentLog').")
    source_id: str = Field(..., description="Identifier of the source emitting the event (e.g., agent_id, task_id, crew_id).")
    crew_run_id: Optional[uuid.UUID] = Field(default=None, description="Optional run ID if the event is part of a specific crew execution.")

# --- Specific Event Models ---

class AgentCallbackEvent(BaseEvent):
    event_type: Literal["AgentCallback"] = Field(default="AgentCallback", description="Event type for generic agent callbacks.")
    agent_id: str = Field(..., description="ID of the agent.")
    callback_type: str = Field(..., description="Type of callback (e.g., 'on_tool_start', 'on_tool_end', 'on_llm_start', 'on_llm_end', 'on_agent_step').")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Data associated with the callback.")
    # Add more specific callback fields if needed, like tool_name, input_str, output_str, etc.

class AgentTaskExecutionEvent(BaseEvent):
    event_type: Literal["AgentTaskExecution"] = Field(default="AgentTaskExecution", description="Event type for task execution phases.")
    task_id: str # This would be the Task's internal ID or a generated one.
    agent_id: str # Agent executing the task
    task_description: str
    status: Literal["STARTED", "IN_PROGRESS", "COMPLETED", "FAILED", "SKIPPED"]
    output: Optional[str] = None # Task's string output on completion
    error_message: Optional[str] = None
    error_details: Optional[str] = None # Stack trace or more detailed error
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None

class AgentLogEvent(BaseEvent):
    event_type: Literal["AgentLog"] = Field(default="AgentLog", description="Event type for general agent logs or thoughts.")
    agent_id: str
    message: str
    log_level: Literal["INFO", "WARNING", "ERROR", "DEBUG"] = Field(default="INFO")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured data associated with the log.")

class CrewLifecycleEvent(BaseEvent):
    event_type: Literal["CrewLifecycle"] = Field(default="CrewLifecycle", description="Event type for crew lifecycle events.")
    # crew_run_id is already in BaseEvent
    status: Literal["STARTED", "COMPLETED", "FAILED"]
    inputs: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None # Can be complex, consider string representation or summary
    error_message: Optional[str] = None

# Union type for all possible events (optional, but can be useful)
# AgentEvent = Union[AgentTaskStartedEvent, AgentTaskCompletedEvent, AgentTaskErrorEvent, AgentLogEvent]

AlertLevel = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]

class AlertEvent(BaseEvent):
    event_type: Literal["AlertEvent"] = Field(default="AlertEvent", description="The fixed type for alert events.")

    alert_level: AlertLevel = Field(..., description="Severity level of the alert (e.g., INFO, WARNING, ERROR, CRITICAL).")
    message: str = Field(..., description="A human-readable message describing the alert.")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional dictionary for structured data related to the alert.")

    # source_id from BaseEvent can be used to indicate the component generating the alert,
    # e.g., "TradingCoordinator", "SimulatedTradeExecutor", or a specific strategy_id/agent_id.

    class Config:
        from_attributes = True
        validate_assignment = True
        extra = 'forbid' # Assuming BaseEvent also has this or it's compatible.

# Example usage:
# alert = AlertEvent(
#     source_id="TradingCoordinator",
#     alert_level="INFO",
#     message="New trade signal generated for AAPL.",
#     details={"symbol": "AAPL", "signal": "BUY", "confidence": 0.75}
# )
# print(alert.model_dump_json(indent=2))
