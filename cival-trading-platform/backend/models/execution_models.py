from loguru import logger
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone # Added timezone
import uuid

# Attempt to import TradeParams. If not found, define a placeholder.
try:
    from .trade_history_models import TradeParams
except ImportError:
    logger.warning("TradeParams not found in trade_history_models, using placeholder for ExecutionRequest.")
    class TradeParams(BaseModel): # Placeholder
        symbol: str
        side: Literal["buy", "sell"]
        quantity: float
        order_type: Literal["market", "limit"]
        price: Optional[float] = None # For limit orders
        # Add other common fields if necessary for the specialist
        strategy_name: Optional[str] = None
        client_order_id: Optional[str] = None


class ExecutionRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_agent_id: str
    trade_params: TradeParams
    preferred_exchange: Optional[str] = None
    execution_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ExecutionFillLeg(BaseModel):
    exchange_trade_id: str
    exchange_order_id: str # Could be the same as trade_id for simple fills
    fill_price: float
    fill_quantity: float
    fee: float
    fee_currency: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExecutionReceipt(BaseModel):
    request_id: str
    execution_status: Literal["PENDING_EXECUTION", "ROUTED", "PARTIALLY_FILLED", "FILLED", "FAILED", "REJECTED_BY_SPECIALIST"]
    message: str
    exchange_order_ids: List[str] = Field(default_factory=list)
    fills: List[ExecutionFillLeg] = Field(default_factory=list)
