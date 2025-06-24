from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime, timezone
import uuid

class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    publisher_agent_id: str # ID of the agent that published the event
    message_type: str # Discriminator for the event type, e.g., "TradeSignal", "MarketInsight"
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Example Specific Event Payloads (for clarity and potential future typed events)
class TradeSignalEventPayload(BaseModel):
    symbol: str
    action: Literal["buy", "sell", "hold"]
    quantity: Optional[float] = None
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    strategy_name: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class MarketInsightEventPayload(BaseModel):
    insight_type: str # e.g., "VolatilitySpike", "TrendIdentified"
    symbol: Optional[str] = None
    data: Dict[str, Any] # e.g., {"period": "5m", "current_volatility": 0.8}
    summary: str

class RiskAlertEventPayload(BaseModel):
    alert_level: Literal["info", "warning", "critical"]
    metric_name: str # e.g., "MaxDrawdown", "PositionExposure"
    value: Any
    threshold: Any
    message: str

class MarketConditionEventPayload(BaseModel):
    symbol: str
    regime: Literal["trending_up", "trending_down", "ranging", "volatile", "undetermined"]
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    supporting_data: Dict[str, Any] = Field(default_factory=dict) # e.g., {"adx": 27, "ma_short_slope": 0.002}


# --- Added for Phase 6, Step 6 (TradingCoordinator Refactor) ---

class RiskAssessmentRequestData(BaseModel):
    proposing_agent_id: str
    trade_signal: TradeSignalEventPayload
    # Optional: add portfolio_context if RiskManagerService needs it directly
    # portfolio_context: Optional[Dict[str, Any]] = None

class RiskAssessmentResponseData(BaseModel):
    signal_approved: bool
    rejection_reason: Optional[str] = None
    # Optional: if risk manager can adjust signals
    # adjusted_trade_signal: Optional[TradeSignalEventPayload] = None

class NewsArticleEventPayload(BaseModel):
    source_feed_url: str
    headline: str
    link: str
    published_date: Optional[datetime] = None
    summary: Optional[str] = None
    mentioned_symbols: List[str] = Field(default_factory=list)
    sentiment_score: float = 0.0 # e.g., -1.0 (very negative) to 1.0 (very positive)
    sentiment_label: Literal["positive", "negative", "neutral"] = "neutral"
    matched_keywords: List[str] = Field(default_factory=list)
    raw_content_snippet: Optional[str] = None # Optional: a snippet of original text
