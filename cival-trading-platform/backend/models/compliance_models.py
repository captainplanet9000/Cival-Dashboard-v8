from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
import uuid # For ComplianceRule.rule_id default_factory

# Assuming TradeSignalEventPayload is defined in event_bus_models
# Adjust the import path if it's located elsewhere.
from ..models.event_bus_models import TradeSignalEventPayload

class ComplianceRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    applies_to_agent_type: Optional[List[str]] = None
    applies_to_agent_id: Optional[List[str]] = None
    condition_type: Literal[
        "max_order_value_usd",
        "restricted_symbols",
        "max_daily_trades_for_symbol" # Stateful, placeholder logic for now
    ]
    parameters: Dict[str, Any] # e.g., {"value": 10000}, {"symbols": ["XYZ"]}, {"symbol": "BTC", "limit": 5}

class ComplianceCheckRequest(BaseModel):
    agent_id: str
    agent_type: str # From AgentConfigOutput
    action_type: Literal["place_order"] # Currently only for placing orders
    trade_signal_payload: TradeSignalEventPayload

class ViolatedRuleInfo(BaseModel):
    rule_id: str
    description: str
    reason: str # Specific reason for violation based on parameters

class ComplianceCheckResult(BaseModel):
    is_compliant: bool = True
    violated_rules: List[ViolatedRuleInfo] = Field(default_factory=list)
