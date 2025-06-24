from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
import uuid
from datetime import datetime

# Literals for Hyperliquid specific values (ensure these are comprehensive or as needed)
HyperliquidOrderType = Literal["market", "limit", "stop", "trigger"]
HyperliquidOrderSide = Literal["buy", "sell", "b", "s"]
HyperliquidOrderStatus = Literal["open", "filled", "partially_filled", "canceled", "rejected", "triggered"]

class HyperliquidCredentials(BaseModel):
    api_url: str = Field(..., description="Hyperliquid API URL (Mainnet or Testnet).")
    wallet_address: str = Field(..., description="Agent's wallet address for API trading.")
    private_key: str = Field(..., description="Agent's private key for signing. HANDLE WITH EXTREME CARE.")

class HyperliquidPlaceOrderParams(BaseModel):
    asset: str = Field(..., description="Asset symbol (e.g., 'ETH').")
    is_buy: bool = Field(..., description="True for buy, False for sell.")
    # Allow limit_px = 0, e.g. for market orders if API uses 0 as convention.
    # Actual price limits for limit orders should still be > 0.
    # The coordinator logic ensures a valid price for limit orders.
    limit_px: float = Field(..., ge=0, description="Limit price for the order. For market orders, this might be a conventional value like 0 or ignored by the exchange if the order_type specifies market.")
    sz: float = Field(..., gt=0, description="Size of the order (number of contracts or units).")
    cloid: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, description="Client Order ID (UUID).")
    reduce_only: bool = Field(default=False)
    order_type: Dict[str, Any] = Field(..., description="Order type details, e.g. {'limit': {'tif': 'Gtc'}} or {'trigger': {...}}")

class HyperliquidOrderResponseData(BaseModel):
    status: str
    oid: Optional[int] = None
    order_type_info: Optional[Dict[str, Any]] = Field(default=None, alias="type")
    # simulated_fills: Optional[List[Dict[str, Any]]] = Field(default=None, description="DEPRECATED: Fills are now fetched post-order via get_fills_for_order.")

class HyperliquidOrderStatusInfo(BaseModel):
    order: Dict[str, Any]
    status: str
    fills: List[Dict[str, Any]] = Field(default_factory=list)

class HyperliquidAssetPosition(BaseModel): # Renamed from HyperliquidPosition for clarity
    asset: str = Field(..., description="Asset symbol, e.g., 'ETH'.")
    szi: str = Field(..., description="Size of the position as a string (positive for long, negative for short).")
    entry_px: Optional[str] = Field(default=None, description="Average entry price of the position (as string).")
    unrealized_pnl: Optional[str] = Field(default=None, description="Unrealized PnL of the position (as string).")
    margin_used: Optional[str] = Field(default=None, description="Margin used by this position (as string).")
    liquidation_px: Optional[str] = Field(default=None, description="Estimated liquidation price (as string).")
    # raw_data: Dict[str, Any] # Optional: Keep if useful, or parse all known fields.

    @property
    def size_float(self) -> float:
        try: return float(self.szi)
        except ValueError: return 0.0

    @property
    def entry_price_float(self) -> Optional[float]:
        try: return float(self.entry_px) if self.entry_px is not None else None
        except ValueError: return None

    @property
    def unrealized_pnl_float(self) -> Optional[float]:
        try: return float(self.unrealized_pnl) if self.unrealized_pnl is not None else None
        except ValueError: return None

    @property
    def margin_used_float(self) -> Optional[float]:
        try: return float(self.margin_used) if self.margin_used is not None else None
        except ValueError: return None

    @property
    def liquidation_price_float(self) -> Optional[float]:
        try: return float(self.liquidation_px) if self.liquidation_px is not None else None
        except ValueError: return None

class HyperliquidOpenOrderItem(BaseModel):
    oid: int = Field(..., description="Order ID.")
    asset: str = Field(..., description="Asset symbol.")
    side: str = Field(..., description="Order side ('b' for buy, 's' for sell).")
    limit_px: str = Field(..., description="Limit price (as string).")
    sz: str = Field(..., description="Original size of the order (as string).")
    timestamp: int = Field(..., description="Order creation timestamp (milliseconds since epoch).")
    raw_order_data: Dict[str, Any] = Field(..., description="The raw dictionary representing the open order from user_state.")

class HyperliquidMarginSummary(BaseModel):
    account_value: str = Field(..., alias="accountValue", description="Total value of the account in USD collateral.")
    total_raw_usd: str = Field(..., alias="totalRawUsd", description="Total raw USD value, often same as accountValue.")
    total_ntl_pos: str = Field(..., alias="totalNtlPos", description="Total notional position value in USD.")
    total_margin_used: str = Field(..., alias="totalMarginUsed", description="Total margin currently used by open positions and orders.")
    # These fields are typically part of the margin summary; adding them as optional
    # as their presence might vary or they might be named differently (e.g. cross vs spot)
    total_pnl_on_positions: Optional[str] = Field(default=None, alias="totalNtlPos", description="Redundant if totalNtlPos is already capturing this. Typically, total PnL from positions.") # totalNtlPos often represents this.
    available_balance_for_new_orders: Optional[str] = Field(default=None, alias="withdrawable", description="Withdrawable amount, often used as available balance.") # 'withdrawable' is a common field name
    # Add other specific fields if they are consistently available and needed
    # For example, 'initial_margin_on_positions', 'maintenance_margin_on_positions'

    @validator('*', pre=True, allow_reuse=True)
    def ensure_str(cls, v):
        return str(v) if v is not None else None

class HyperliquidAccountSnapshot(BaseModel): # Replaces old HyperliquidAccountSummary
    timestamp_ms: int = Field(..., alias="time", description="Timestamp of the snapshot in milliseconds since epoch.")
    total_account_value_usd: str = Field(..., alias="totalRawUsd", description="Total account value in USD (as string from crossMarginSummary or similar).")

    # These will be populated by the service method after parsing the raw user_state
    parsed_positions: List[HyperliquidAssetPosition] = Field(default_factory=list)
    parsed_open_orders: List[HyperliquidOpenOrderItem] = Field(default_factory=list)

    # Optional: include a parsed margin summary if it's a distinct complex object
    # margin_summary: Optional[HyperliquidMarginSummary] = None

    # Optional: include parts of raw user_state if needed for passthrough or direct access
    # raw_user_state_subset: Optional[Dict[str, Any]] = None

    # Property for total PnL if it's part of the snapshot directly (e.g. from crossMarginSummary)
    # This depends on where total_pnl_usd_str is sourced from the raw user_state by the service
    total_pnl_usd_str: Optional[str] = Field(default=None, description="Total PnL for the account (as string).")

    @property
    def total_account_value_float(self) -> Optional[float]:
        try: return float(self.total_account_value_usd)
        except ValueError: return None

    @property
    def total_pnl_float(self) -> Optional[float]:
        try: return float(self.total_pnl_usd_str) if self.total_pnl_usd_str is not None else None
        except ValueError: return None
