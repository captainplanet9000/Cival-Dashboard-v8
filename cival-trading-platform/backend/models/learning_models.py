from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

class LearningLogEntry(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    primary_agent_id: Optional[str] = Field(default=None, description="Agent whose direct action/data is being logged, or the agent context for an event.")
    source_service: str = Field(description="Name of the service class logging this, e.g., 'TradingCoordinator'")
    event_type: str = Field(description="Categorization of the log, e.g., 'ExternalSignalReceived', 'ComplianceCheckResult', 'TradeExecutionAttempt'")

    # Contextual IDs
    triggering_event_id: Optional[str] = Field(default=None, description="e.g., ID of the EventBus Event that triggered this action")
    # trade_signal_id: Optional[str] = Field(default=None, description="If related to a specific trade signal (could be from event.payload.signal_id if signals have IDs)")
    # Let's simplify for now, specific IDs can be part of data_snapshot or outcome_or_result if needed.

    data_snapshot: Dict[str, Any] = Field(description="Payload of an incoming event, parameters of an action being taken, or data being generated.")
    outcome_or_result: Optional[Dict[str, Any]] = Field(default=None, description="Result of an action, e.g., compliance/risk result, execution status, new config.")

    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    class Config:
        # For Pydantic V2, to ensure model_dump_json serializes datetime and uuid correctly
        # For Pydantic V1, this is not needed as default json encoders handle it.
        # If using Pydantic V2, this might be:
        # json_encoders = {
        #     datetime: lambda v: v.isoformat(),
        #     uuid.UUID: lambda v: str(v),
        # }
        pass
