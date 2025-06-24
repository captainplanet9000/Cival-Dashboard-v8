from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal # Added Literal
from .agent_models import AgentStrategyConfig # Assuming AgentStrategyConfig is the output
import uuid # For request_id

class StrategyDevRequest(BaseModel):
    user_id: str
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    preferred_risk_level: Optional[Literal["low", "medium", "high"]] = Field(default="medium")
    target_assets: Optional[List[str]] = Field(default_factory=list, description="e.g., ['BTC/USD', 'ETH/USD']")
    desired_strategy_types: Optional[List[str]] = Field(default_factory=list, description="e.g., ['sma_crossover', 'darvas_box']")
    custom_prompt: Optional[str] = Field(default=None, description="User prompt for specific requests.")

class StrategyDevResponse(BaseModel):
    request_id: str
    proposed_strategy_configs: List[AgentStrategyConfig] = Field(default_factory=list)
    notes: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
