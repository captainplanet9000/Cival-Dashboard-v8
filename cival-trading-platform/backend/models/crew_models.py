# This file will contain Pydantic models specific to CrewAI workflows
# or for structuring data passed between agents/tasks.

# Note:
# The final output of the trading crew is intended to be a `TradingDecision` object
# as defined in `python_ai_services.types.trading_types.TradingDecision`.
# The output of the market analyst agent/task is intended to be a `MarketAnalysis` object
# as defined in `python_ai_services.types.trading_types.MarketAnalysis`.

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from uuid import UUID, uuid4 # Added UUID, uuid4
from enum import Enum # Added Enum

# Attempting relative import from sibling package 'types'
try:
    from ..types.trading_types import TradeAction, MarketCondition, RiskLevel
except ImportError:
    # Fallback for environments where relative imports might be tricky
    # This is primarily for the subtask execution context.
    print("Warning: Could not perform relative imports for enums from types.trading_types. Using string placeholders.")
    class TradeAction: BUY="BUY"; SELL="SELL"; HOLD="HOLD"; INFO="INFO" # Basic placeholder
    class MarketCondition: PASS # Basic placeholder
    class RiskLevel: LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH" # Basic placeholder


class StrategyApplicationResult(BaseModel):
    """
    Represents the direct output from a specific trading strategy's application
    before final synthesis into a TradeSignal/TradingDecision.
    """
    symbol: str = Field(..., example="BTC/USD", description="The financial instrument symbol.")
    strategy_name: str = Field(..., example="DarvasBoxStrategy", description="Name of the strategy that produced this result.")

    advice: TradeAction = Field(..., description="The trading advice from this specific strategy (BUY, SELL, HOLD).")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the advice (0.0 to 1.0).")

    target_price: Optional[float] = Field(None, example=65000.0, description="Suggested target price for the trade, if applicable.")
    stop_loss: Optional[float] = Field(None, example=58000.0, description="Suggested stop-loss price for the trade, if applicable.")
    take_profit: Optional[float] = Field(None, example=70000.0, description="Suggested take-profit price for the trade, if applicable.")

    rationale: str = Field(..., description="Brief explanation or rationale behind the strategy's advice.")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Any other strategy-specific outputs, e.g., calculated indicator values, pattern details.")

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of when the strategy result was generated.")

class AssessTradeRiskArgs(BaseModel):
    """
    Input arguments for the Assess Trade Risk Tool.
    Details the proposed trade and context for risk assessment.
    """
    symbol: str = Field(..., description="The trading symbol (e.g., 'BTC/USD').")
    proposed_action: TradeAction = Field(..., description="The proposed trading action (BUY, SELL, HOLD).")
    confidence_score: Optional[float] = Field(None, description="Confidence score of the proposed action (0.0 to 1.0).", ge=0.0, le=1.0)
    entry_price: Optional[float] = Field(None, description="Proposed entry price for the trade.")
    stop_loss_price: Optional[float] = Field(None, description="Proposed stop-loss price for the trade.")
    take_profit_price: Optional[float] = Field(None, description="Proposed take-profit price for the trade.")
    quantity_or_value: Optional[float] = Field(None, description="Proposed quantity (e.g., number of shares, contracts) or monetary value of the trade.", gt=0)
    current_portfolio_value: Optional[float] = Field(None, description="Total current value of the portfolio.", gt=0)
    existing_position_size: Optional[float] = Field(None, description="Size (e.g., number of shares, contracts, or value) of existing position in the same symbol, if any.", ge=0)
    portfolio_context: Optional[Dict[str, Any]] = Field(None, description="Additional portfolio context (e.g., overall risk exposure, diversification metrics).")
    market_conditions_summary: Optional[str] = Field(None, description="Brief summary of current market conditions relevant to risk (e.g., high volatility, specific news).")

    @field_validator('proposed_action', mode='before')
    @classmethod
    def validate_trade_action_str(cls, value):
        if isinstance(value, str):
            action_upper = value.upper()
            if hasattr(TradeAction, action_upper): # Check if the string is a valid enum member name
                return TradeAction[action_upper]
            # Additionally, check if the string is one of the enum's values
            for member in TradeAction:
                if action_upper == member.value:
                    return member
            raise ValueError(f"Invalid trade action string: '{value}'. Must be one of { [e.value for e in TradeAction] }.")
        return value # Already an enum or other type Pydantic will handle


class TradeRiskAssessmentOutput(BaseModel):
    """
    Structured output from the Assess Trade Risk Tool.
    Provides the assessed risk level, any warnings, and a summary.
    """
    risk_level: RiskLevel = Field(..., description="Assessed risk level for the trade (LOW, MEDIUM, HIGH).")
    warnings: List[str] = Field(default_factory=list, description="List of any specific risk warnings identified.")
    max_potential_loss_estimate_percent: Optional[float] = Field(
        None,
        description="Estimated maximum potential loss as a percentage of trade value or entry price if stop-loss is hit.",
        ge=0.0
    )
    max_potential_loss_value: Optional[float] = Field(
        None,
        description="Estimated absolute maximum potential loss in currency if stop-loss is hit.",
        ge=0.0
    )
    suggested_position_size_adjustment_factor: Optional[float] = Field(
        None,
        description="Suggestion for adjusting position size (e.g., 0.5 for half, 1.0 for no change, 0 to avoid). Based on risk.",
        ge=0.0,
        le=1.0
    )
    sanity_checks_passed: bool = Field(
        default=True,
        description="Whether basic sanity checks on the proposed trade parameters (e.g., stop-loss vs entry price) passed."
    )
    assessment_summary: str = Field(..., description="A brief textual summary of the overall risk assessment and key factors.")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of when the risk assessment was generated.")


class TaskStatus(str, Enum):
    """Enum for the status of an agent task."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentTask(BaseModel):
    """
    Pydantic model representing a task executed by an AI crew or agent.
    This model is used for tracking and logging task executions.
    """
    task_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the task.")
    crew_id: str = Field(..., description="Identifier for the crew that is executing or has executed this task (e.g., 'trading_analysis_crew').")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status of the task.")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the task processing started.")
    end_time: Optional[datetime] = Field(None, description="Timestamp when the task processing completed or failed.")
    inputs: Dict[str, Any] = Field(..., description="Initial inputs provided to the crew for this task run.")
    output: Optional[Any] = Field(None, description="Final result/output from the crew for this task. Can be complex dict/JSON.")
    error_message: Optional[str] = Field(None, description="Error message if the task failed.")
    logs_summary: Optional[List[Dict[str, Any]]] = Field(None, description="A summary of key log entries or events during the task execution. E.g., tool calls, agent outputs.")

    # Pydantic model's own created_at/updated_at for application use, distinct from DB table's defaults
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of Pydantic model task record creation.")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of last Pydantic model task record update.")

    class Config:
        use_enum_values = True # Ensures enum values (strings) are used in serialization
        # For FastAPI, orm_mode or from_attributes = True might be needed if creating from ORM objects
        # For now, this is a data transfer object.
