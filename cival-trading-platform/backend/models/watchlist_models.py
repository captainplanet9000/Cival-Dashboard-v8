from pydantic import BaseModel, Field, field_validator, root_validator # field_validator for Pydantic v2, validator is legacy
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

class WatchlistItemBase(BaseModel):
    symbol: str = Field(..., description="Financial symbol being watched.")
    notes: Optional[str] = Field(default=None, description="User notes for this watchlist item.")
    # Could add: target_price_high, target_price_low, alert_conditions, etc.

class WatchlistItemCreate(WatchlistItemBase):
    # For creating a new item, user_id and watchlist_id will be context/path params
    pass

class WatchlistItem(WatchlistItemBase):
    item_id: uuid.UUID = Field(..., description="Unique identifier for the watchlist item.")
    watchlist_id: uuid.UUID = Field(..., description="ID of the watchlist this item belongs to.")
    user_id: uuid.UUID = Field(..., description="ID of the user this item belongs to (denormalized for easier access).")
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the item was added.")

    # Optional: To store last fetched quote data directly on the item for quick view
    # last_quote_price: Optional[float] = None
    # last_quote_timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True
        validate_assignment = True

class WatchlistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the watchlist.")
    description: Optional[str] = Field(default=None, max_length=500, description="Optional description for the watchlist.")

class WatchlistCreate(WatchlistBase):
    # user_id will be from auth context typically
    pass

class Watchlist(WatchlistBase):
    watchlist_id: uuid.UUID = Field(..., description="Unique identifier for the watchlist.")
    user_id: uuid.UUID = Field(..., description="ID of the user who owns this watchlist.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # items: List[WatchlistItem] = Field(default_factory=list, description="Items in this watchlist. Loaded separately usually.")

    class Config:
        from_attributes = True
        validate_assignment = True

# For API responses that might include items directly
class WatchlistWithItems(Watchlist):
    items: List[WatchlistItem] = Field(default_factory=list)

# For API request to add items to a watchlist
class AddWatchlistItemsRequest(BaseModel):
    # List of symbols or more detailed WatchlistItemCreate objects
    symbols: Optional[List[str]] = None # Simple case: just add symbols
    items: Optional[List[WatchlistItemCreate]] = None # More detailed case

    @root_validator(pre=True) # Changed to root_validator for Pydantic v2 cross-field validation
    @classmethod # root_validator needs to be a classmethod
    def check_at_least_one_input_method(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values.get('symbols') and not values.get('items'):
            raise ValueError('Either "symbols" or "items" must be provided.')
        if values.get('symbols') and values.get('items'):
            raise ValueError('Provide either "symbols" or "items", not both.')
        return values

class BatchQuotesRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, description="List of symbols to fetch quotes for.")
    provider: Optional[str] = Field(default="yfinance", description="Data provider.")

class BatchQuotesResponseItem(BaseModel):
    symbol: str
    quote_data: Optional[Dict[str, Any]] = None # From get_current_quote_tool
    error: Optional[str] = None

class BatchQuotesResponse(BaseModel):
    results: List[BatchQuotesResponseItem]
