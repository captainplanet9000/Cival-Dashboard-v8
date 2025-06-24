from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List # Added Dict, Any, List (List might not be needed for PaperPosition but good for consistency)
from datetime import datetime, timezone
import uuid

# Assuming these enums are correctly exposed from trading_history_models
# If not, they might need to be redefined or imported differently.
# For this subtask, we assume they can be imported like this:
from .trading_history_models import TradeSide, OrderType as PaperOrderType, OrderStatus as PaperOrderStatus
# Aliasing to avoid potential naming conflicts if this file also defines similar concepts,
# though for enums it's less likely. Using "Paper" prefix for clarity in this context.

class PaperTradeOrder(BaseModel):
    order_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Client-generated unique identifier for the paper trade order.")
    user_id: uuid.UUID = Field(..., description="Identifier of the user placing the paper order.")
    # agent_id: Optional[uuid.UUID] = Field(default=None, description="Optional agent ID if an agent placed this paper order.")
    # strategy_id: Optional[uuid.UUID] = Field(default=None, description="Optional strategy ID that generated this paper order.")

    symbol: str = Field(..., description="Financial symbol to trade (e.g., BTC/USD, AAPL).")
    side: TradeSide = Field(..., description="Side of the trade: BUY or SELL.")
    order_type: PaperOrderType = Field(..., description="Type of order (MARKET, LIMIT, etc.).")
    quantity: float = Field(..., gt=0, description="Quantity of the asset to trade.")

    limit_price: Optional[float] = Field(default=None, description="Limit price for LIMIT or STOP_LIMIT orders. Must be > 0 if set.")
    stop_price: Optional[float] = Field(default=None, description="Stop price for STOP or STOP_LIMIT orders. Must be > 0 if set.")

    time_in_force: str = Field(default="GTC", description="Time in force for the order (e.g., GTC, IOC, FOK). For simulator, GTC is typical.")

    order_request_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the paper order was created/requested by the client system (UTC).")
    status: PaperOrderStatus = Field(default="NEW", description="Current status of the paper order within the simulator.")

    notes: Optional[str] = Field(default=None, description="Optional notes for this paper order.")

    # Pydantic v2 style validator
    @field_validator('limit_price', 'stop_price')
    @classmethod
    def check_positive_prices(cls, value: Optional[float]):
        if value is not None and value <= 0:
            raise ValueError('Price must be positive if provided.')
        return value

    class Config:
        from_attributes = True
        validate_assignment = True
        extra = 'forbid'

class CreatePaperTradeOrderRequest(BaseModel):
    # user_id: uuid.UUID Field is REMOVED - will be derived from authenticated user context

    symbol: str = Field(..., description="Financial symbol to trade (e.g., BTC/USD, AAPL).")
    side: TradeSide = Field(..., description="Side of the trade: BUY or SELL.") # Reuses TradeSide enum
    order_type: PaperOrderType = Field(..., description="Type of order (MARKET, LIMIT, etc.).") # Reuses PaperOrderType enum
    quantity: float = Field(..., gt=0, description="Quantity of the asset to trade.")

    limit_price: Optional[float] = Field(default=None, description="Limit price for LIMIT or STOP_LIMIT orders. Must be > 0 if set.")
    stop_price: Optional[float] = Field(default=None, description="Stop price for STOP or STOP_LIMIT orders. Must be > 0 if set.")

    time_in_force: str = Field(default="GTC", description="Time in force for the order (e.g., GTC, IOC, FOK).")
    notes: Optional[str] = Field(default=None, description="Optional client notes for this paper order.")

    @field_validator('limit_price', 'stop_price') # Pydantic v2 style
    @classmethod
    def check_positive_prices(cls, value: Optional[float]): # Added type hint for value
        if value is not None and value <= 0:
            raise ValueError('Price must be positive if provided.')
        return value

    class Config:
        from_attributes = True
        validate_assignment = True
        extra = 'forbid'

# This model is a subset of PaperTradeOrder, excluding server-set fields like order_id, status, timestamps.

class PaperPosition(BaseModel):
    position_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for this paper trading position record.")
    user_id: uuid.UUID = Field(..., description="Identifier of the user who owns this position.")
    # account_id: Optional[uuid.UUID] = Field(default=None, description="Optional identifier for a specific paper trading account, if users can have multiple.")

    symbol: str = Field(..., description="Financial symbol of the asset (e.g., BTC/USD, AAPL).")

    quantity: float = Field(..., description="Current quantity of the asset held. Positive for long, negative for short.")
    average_entry_price: float = Field(..., gt=0, description="Average price at which the current quantity was acquired.")

    # Cost basis might be useful for more detailed P&L, but can be derived if all trades are stored.
    # total_cost_basis: float = Field(default=0.0, description="Total cost basis for the current open position.")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when this position record was first created (e.g., first trade of a new position).")
    last_modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when this position was last modified (e.g., trade added/reduced quantity).")

    # P&L - these might be calculated on demand rather than stored,
    # or updated periodically by a separate process.
    # For now, including them as optional stored values.
    # unrealized_pnl: Optional[float] = Field(default=None, description="Current unrealized profit or loss for this open position. Calculated with current market price.")
    # realized_pnl_from_closing_trades: float = Field(default=0.0, description="Total realized P&L from trades that closed or reduced this specific position instance.")

    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata related to the position.")

    @field_validator('quantity') # Pydantic v2 style validator
    @classmethod
    def quantity_cannot_be_zero(cls, value: float): # Added type hint for value
        if value == 0:
            # A position with quantity zero typically means the position is closed and should be archived or removed.
            # For an active position record, quantity should be non-zero.
            raise ValueError('Position quantity cannot be zero for an active position record.')
        return value

    class Config:
        from_attributes = True
        validate_assignment = True
        extra = 'forbid'

# Example:
# position = PaperPosition(user_id=uuid.uuid4(), symbol="AAPL", quantity=10, average_entry_price=150.00)
# print(position.model_dump_json(indent=2))

class PaperTradeFill(BaseModel):
    fill_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for this simulated fill.")
    order_id: uuid.UUID = Field(..., description="The ID of the PaperTradeOrder this fill belongs to.")
    user_id: uuid.UUID = Field(..., description="Identifier of the user associated with this fill.") # Denormalized for easier querying

    symbol: str = Field(..., description="Financial symbol traded.") # Denormalized
    side: TradeSide = Field(..., description="Side of the trade.") # Denormalized

    fill_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the fill was simulated (UTC).")
    price: float = Field(..., gt=0, description="Simulated execution price for this fill.")
    quantity: float = Field(..., gt=0, description="Quantity of the asset filled in this execution.")

    commission: float = Field(default=0.0, ge=0, description="Simulated commission for this fill.")
    commission_asset: Optional[str] = Field(default=None, description="Asset in which commission is denominated (e.g., USD or base/quote asset).")

    fill_notes: Optional[str] = Field(default=None, description="Notes specific to this fill (e.g., 'Simulated fill at next bar open').")

    class Config:
        from_attributes = True
        validate_assignment = True
        extra = 'forbid'
