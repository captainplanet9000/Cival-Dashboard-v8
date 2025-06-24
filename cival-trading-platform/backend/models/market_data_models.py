from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime

class Kline(BaseModel):
    timestamp: datetime # Timestamp of the kline's open time
    open: float
    high: float
    low: float
    close: float
    volume: float

class OrderBookLevel(BaseModel):
    price: float
    quantity: float

class OrderBookSnapshot(BaseModel):
    symbol: str
    timestamp: datetime # Timestamp of when the snapshot was taken
    bids: List[OrderBookLevel] = Field(default_factory=list)
    asks: List[OrderBookLevel] = Field(default_factory=list)

class Trade(BaseModel):
    trade_id: str # Unique identifier for the trade, if available from the exchange
    timestamp: datetime # Timestamp of the trade execution
    symbol: str
    price: float
    quantity: float
    side: Literal["buy", "sell"]
    # Optional: liquidation: Optional[bool] = None
    # Optional: aggressor_side: Optional[Literal["buy", "sell"]] = None
