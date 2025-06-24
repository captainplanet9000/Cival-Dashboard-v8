from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

class RunContext(BaseModel):
    """
    Standardizes contextual information passed during agent, crew, or service executions.
    """
    run_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for this specific run or execution context.")
    correlation_id: Optional[uuid.UUID] = Field(default=None, description="Optional ID to correlate multiple related runs or events.")

    user_id: Optional[str] = Field(default=None, description="Identifier for the user initiating or associated with this run. Could be a string or UUID depending on system design.")
    # If user_id is strictly UUID, use: user_id: Optional[uuid.UUID] = None

    session_id: Optional[str] = Field(default=None, description="Identifier for the user's session, if applicable.")

    request_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the run/request was initiated (UTC).")

    # Context specific to trading or analysis
    market_conditions_summary: Optional[str] = Field(default=None, description="A brief textual summary of current market conditions relevant to this run.")
    relevant_symbols: Optional[List[str]] = Field(default_factory=list, description="List of financial symbols relevant to this run (e.g., ['BTC/USD', 'AAPL']).")
    timeframe: Optional[str] = Field(default=None, description="Primary timeframe context for this run (e.g., '1h', '1d').") # Could use StrategyTimeframe Literal if shared

    # For passing arbitrary additional parameters or configurations
    custom_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="A dictionary for any other custom parameters or context-specific data.")

    class Config:
        from_attributes = True
        validate_assignment = True
        extra = 'forbid' # Or 'allow' if more flexibility is needed for custom_params to truly be open

# Example usage:
# context = RunContext(user_id="user123", relevant_symbols=["ETH/USD"], custom_params={"strategy_mode": "conservative"})
# print(context.model_dump_json(indent=2))
