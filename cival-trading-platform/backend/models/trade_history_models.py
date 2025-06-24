from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
import uuid

class TradeSide(BaseModel): # Assuming this was a simple Literal previously, making it a class for consistency if needed
    # Or it could be: TradeSide = Literal["buy", "sell"]
    # For now, let's assume it's a string literal if used directly in other models.
    # If it's a Pydantic model elsewhere, this definition would need to match.
    # Based on TradeLogItem using Literal["buy", "sell"], this might not be needed as a class.
    # Let's define it as a Literal for now, as used by other models.
    pass # Placeholder, will define as Literal in TradeRecord if that's the pattern

# Re-defining based on common usage patterns if the original was simple Literals
TradeSideType = Literal["buy", "sell"]
OrderStatusType = Literal["open", "partially_filled", "filled", "canceled", "rejected", "expired", "unknown"]
OrderTypeType = Literal["market", "limit", "stop_loss", "take_profit", "trigger"]


class TradeRecord(BaseModel):
    """
    Represents a single completed trade with its P&L.
    This might be derived from one or more fills.
    """
    trade_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) # Or execution time
    asset: str
    side: TradeSideType
    order_type: OrderTypeType
    quantity: float
    entry_price: float # Average entry price for this trade
    exit_price: float # Average exit price for this trade
    realized_pnl: float
    entry_timestamp: datetime # Timestamp of the fill(s) that opened the trade
    exit_timestamp: datetime # Timestamp of the fill(s) that closed the trade
    # Link to fills if necessary:
    # entry_fill_ids: List[str] = Field(default_factory=list)
    # exit_fill_ids: List[str] = Field(default_factory=list)
    fees: Optional[float] = None
    notes: Optional[str] = None


class TradingHistory(BaseModel):
    agent_id: str
    trades: List[TradeRecord] = Field(default_factory=list)
    # Add other summary fields if needed, e.g., total_pnl, win_rate for this history snapshot


# --- Added for Phase 6, Step 5 ---
class TradeFillData(BaseModel):
    agent_id: str
    fill_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    asset: str
    side: TradeSideType # Using the Literal defined above
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    fee: float = Field(default=0.0, ge=0)
    fee_currency: Optional[str] = None # e.g., "USD" or the asset itself
    exchange_order_id: Optional[str] = None
    exchange_trade_id: Optional[str] = None # Often exchanges have a separate trade/fill ID
