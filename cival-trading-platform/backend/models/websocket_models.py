from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime, timezone # Ensure timezone for utcnow

class WebSocketEnvelope(BaseModel):
    event_type: str  # e.g., "NEW_FILL", "ALERT_TRIGGERED", "PORTFOLIO_UPDATE"
    agent_id: Optional[str] = None # If the message is specific to an agent
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
