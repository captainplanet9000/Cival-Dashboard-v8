from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import uuid

class AssetPositionSummary(BaseModel):
    asset: str
    size: float
    entry_price: Optional[float] = None
    current_price: Optional[float] = None # Placeholder, would need market data feed
    unrealized_pnl: Optional[float] = None
    margin_used: Optional[float] = None

class PortfolioSummary(BaseModel):
    agent_id: str
    timestamp: datetime
    account_value_usd: float
    total_pnl_usd: float # Overall PnL (e.g., from Hyperliquid's totalNtlPos)
    available_balance_usd: Optional[float] = None # e.g., from Hyperliquid's withdrawable
    margin_used_usd: Optional[float] = None # e.g., from Hyperliquid's totalMarginUsed
    open_positions: List[AssetPositionSummary]

class TradeLogItem(BaseModel):
    trade_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    asset: str
    opening_side: Literal["buy", "sell"] # Side of the trade that opened the position

    order_type: Literal["market", "limit"] # Assuming type of the entry order

    quantity: float # Matched quantity for this closed trade portion
    entry_price_avg: float # Average entry price for the matched quantity
    exit_price_avg: float # Average exit price for the matched quantity

    entry_timestamp: Optional[datetime] = None
    exit_timestamp: datetime # Timestamp of the fill that closed this trade portion
    holding_period_seconds: Optional[float] = None

    initial_value_usd: Optional[float] = None # Gross value at entry (qty * entry_price_avg)
    final_value_usd: Optional[float] = None   # Gross value at exit (qty * exit_price_avg)

    realized_pnl: Optional[float] = None # Net PnL (Final - Initial - Fees)
    percentage_pnl: Optional[float] = None # (realized_pnl / initial_value_usd) * 100

    total_fees: Optional[float] = None # Sum of fees for this matched trade portion

    # Optional: Could include list of fill_ids involved
    # entry_fill_ids: List[str] = Field(default_factory=list)
    # exit_fill_ids: List[str] = Field(default_factory=list)

class OrderLogItem(BaseModel):
    order_id: str # Could be int from exchange or UUID string for paper/internal
    agent_id: str
    timestamp: datetime # Creation timestamp
    asset: str
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit", "stop_loss", "take_profit", "trigger"] # Extended with common types
    quantity: float
    limit_price: Optional[float] = None
    filled_quantity: float = 0.0
    avg_fill_price: Optional[float] = None
    status: Literal["open", "partially_filled", "filled", "canceled", "rejected", "expired", "unknown"]
    raw_details: Optional[Dict[str, Any]] = None # To store original exchange data if needed

class PortfolioSnapshotOutput(BaseModel):
    agent_id: str
    timestamp: datetime
    total_equity_usd: float
    # snapshot_id: Optional[str] = None # Optional if not needed by frontend for e.g. direct linking

    class Config:
        from_attributes = True # Renamed from orm_mode for Pydantic v2
