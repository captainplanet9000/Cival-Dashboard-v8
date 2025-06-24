from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone
import uuid

TradeSide = Literal["BUY", "SELL"]
OrderStatus = Literal["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED", "PENDING_CANCEL"]
OrderType = Literal["MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAILING_STOP"]

class TradeRecord(BaseModel):
    trade_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for this trade record.")
    user_id: uuid.UUID = Field(..., description="Identifier of the user who owns this trade.")
    agent_id: Optional[uuid.UUID] = Field(default=None, description="Identifier of the agent that executed or proposed this trade.")
    strategy_id: Optional[uuid.UUID] = Field(default=None, description="Identifier of the strategy instance that generated this trade.")
    # crew_run_id: Optional[uuid.UUID] = Field(default=None, description="If part of a specific crew execution.") # Could be in metadata

    symbol: str = Field(..., description="Financial symbol traded (e.g., BTC/USD, AAPL).")
    exchange: Optional[str] = Field(default=None, description="Exchange where the trade was executed (e.g., Binance, NYSE).")

    order_id: str = Field(..., description="The unique order ID from the exchange or broker.")
    client_order_id: Optional[str] = Field(default=None, description="Client-side order ID, if applicable.")

    side: TradeSide = Field(..., description="Side of the trade: BUY or SELL.")
    order_type: OrderType = Field(..., description="Type of order (MARKET, LIMIT, etc.).")
    status: OrderStatus = Field(..., description="Current status of the order/trade.")

    quantity_ordered: float = Field(..., gt=0, description="Quantity of the asset ordered.")
    quantity_filled: float = Field(default=0.0, ge=0, description="Quantity of the asset filled.")

    price: Optional[float] = Field(default=None, description="Execution price for a market order or limit price for a limit order. Average fill price if partially/fully filled.")
    limit_price: Optional[float] = Field(default=None, gt=0, description="Limit price for LIMIT or STOP_LIMIT orders.")
    stop_price: Optional[float] = Field(default=None, gt=0, description="Stop price for STOP or STOP_LIMIT orders.")

    commission: Optional[float] = Field(default=None, ge=0, description="Commission paid for the trade.")
    commission_asset: Optional[str] = Field(default=None, description="Asset in which commission was paid (e.g., USDT, USD, or the base/quote asset).")

    created_at: datetime = Field(description="Timestamp when the order was created/placed (UTC).") # Should be provided by exchange or order system
    updated_at: datetime = Field(description="Timestamp when the order was last updated (e.g., filled, canceled) (UTC).") # Should be provided
    filled_at: Optional[datetime] = Field(default=None, description="Timestamp when the order was fully filled (UTC).")

    # For linking related trades, e.g., entry and exit of a position
    related_trade_id: Optional[uuid.UUID] = Field(default=None, description="ID of a related trade (e.g., to link entry and exit).")
    position_id: Optional[str] = Field(default=None, description="Identifier for the position this trade belongs to or affects.")

    notes: Optional[str] = Field(default=None, description="Any additional notes or reasons for the trade provided by the agent or user.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata (e.g., slippage, source of signal).")

    class Config:
        from_attributes = True # Changed from orm_mode for Pydantic v2 compatibility
        validate_assignment = True
        extra = 'forbid'
