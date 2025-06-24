"""
Enhanced Market Data Models for Multi-Provider Integration
Comprehensive data structures for real-time market data, technical analysis, and trading signals
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum

class MarketDataProvider(str, Enum):
    """Supported market data providers"""
    YFINANCE = "yfinance"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    FINNHUB = "finnhub"
    TWELVE_DATA = "twelve_data"
    HYPERLIQUID = "hyperliquid"

class AssetType(str, Enum):
    """Asset type classification"""
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    INDEX = "index"
    OPTION = "option"
    FUTURES = "futures"

class TimeFrame(str, Enum):
    """Standard timeframes for market data"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MN1 = "1M"

class PriceData(BaseModel):
    """Real-time price data structure"""
    symbol: str
    price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    high_24h: Optional[Decimal] = None
    low_24h: Optional[Decimal] = None
    timestamp: datetime
    provider: MarketDataProvider
    asset_type: AssetType

class OHLCV(BaseModel):
    """OHLCV candlestick data"""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    provider: MarketDataProvider

class MarketQuote(BaseModel):
    """Comprehensive market quote"""
    symbol: str
    name: Optional[str] = None
    price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    spread: Optional[Decimal] = None
    volume: Decimal
    market_cap: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None
    high_52w: Optional[Decimal] = None
    low_52w: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    timestamp: datetime
    provider: MarketDataProvider
    asset_type: AssetType

class TechnicalIndicators(BaseModel):
    """Technical analysis indicators"""
    symbol: str
    timestamp: datetime
    
    # Moving Averages
    sma_20: Optional[Decimal] = None
    sma_50: Optional[Decimal] = None
    sma_200: Optional[Decimal] = None
    ema_12: Optional[Decimal] = None
    ema_26: Optional[Decimal] = None
    
    # Momentum Indicators
    rsi: Optional[Decimal] = None
    macd: Optional[Decimal] = None
    macd_signal: Optional[Decimal] = None
    macd_histogram: Optional[Decimal] = None
    
    # Volatility Indicators
    bollinger_upper: Optional[Decimal] = None
    bollinger_middle: Optional[Decimal] = None
    bollinger_lower: Optional[Decimal] = None
    atr: Optional[Decimal] = None
    
    # Volume Indicators
    volume_sma: Optional[Decimal] = None
    obv: Optional[Decimal] = None
    
    # Support/Resistance
    support_level: Optional[Decimal] = None
    resistance_level: Optional[Decimal] = None

class TradingSignal(BaseModel):
    """Trading signal with confidence and reasoning"""
    symbol: str
    signal_type: str  # "BUY", "SELL", "HOLD"
    confidence: Decimal = Field(ge=0, le=1)  # 0-1 confidence score
    timestamp: datetime
    source: str  # Indicator or strategy name
    reasoning: str
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    timeframe: TimeFrame
    risk_score: Optional[Decimal] = None

class MarketSentiment(BaseModel):
    """Market sentiment analysis"""
    symbol: str
    sentiment_score: Decimal = Field(ge=-1, le=1)  # -1 (bearish) to 1 (bullish)
    fear_greed_index: Optional[Decimal] = None
    social_sentiment: Optional[Decimal] = None
    news_sentiment: Optional[Decimal] = None
    options_sentiment: Optional[Decimal] = None
    timestamp: datetime
    confidence: Decimal = Field(ge=0, le=1)

class MarketOverview(BaseModel):
    """Overall market conditions"""
    timestamp: datetime
    market_status: str  # "OPEN", "CLOSED", "PRE_MARKET", "POST_MARKET"
    major_indices: Dict[str, Decimal]  # {"SPY": 450.25, "QQQ": 380.15}
    market_sentiment: Decimal = Field(ge=-1, le=1)
    volatility_index: Optional[Decimal] = None
    sector_performance: Dict[str, Decimal]  # {"Technology": 0.025, "Healthcare": -0.015}
    trending_symbols: List[str]
    top_gainers: List[str]
    top_losers: List[str]

class OrderBookLevel(BaseModel):
    """Order book price level"""
    price: Decimal
    quantity: Decimal

class OrderBookSnapshot(BaseModel):
    """Complete order book snapshot"""
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    spread: Decimal
    mid_price: Decimal
    provider: MarketDataProvider

class Trade(BaseModel):
    """Individual trade execution"""
    symbol: str
    timestamp: datetime
    price: Decimal
    quantity: Decimal
    side: str  # "BUY" or "SELL"
    trade_id: Optional[str] = None
    provider: MarketDataProvider

class MarketAlert(BaseModel):
    """Market alert/notification"""
    alert_id: str
    symbol: str
    alert_type: str  # "PRICE_BREAKOUT", "VOLUME_SPIKE", "TECHNICAL_SIGNAL"
    message: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    timestamp: datetime
    data: Dict[str, Any]  # Additional alert data

class ProviderStatus(BaseModel):
    """Market data provider health status"""
    provider: MarketDataProvider
    is_active: bool
    last_update: datetime
    request_count: int
    error_count: int
    rate_limit_remaining: Optional[int] = None
    latency_ms: Optional[float] = None
    status_message: Optional[str] = None

class MarketDataRequest(BaseModel):
    """Standardized market data request"""
    symbols: List[str]
    data_type: str  # "quote", "ohlcv", "orderbook", "trades"
    timeframe: Optional[TimeFrame] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: Optional[int] = 100
    provider_preference: Optional[List[MarketDataProvider]] = None

class MarketDataResponse(BaseModel):
    """Standardized market data response"""
    request_id: str
    symbols: List[str]
    data: List[Union[PriceData, OHLCV, MarketQuote, OrderBookSnapshot, Trade]]
    provider: MarketDataProvider
    timestamp: datetime
    latency_ms: float
    success: bool
    error_message: Optional[str] = None

class StreamSubscription(BaseModel):
    """WebSocket stream subscription"""
    subscription_id: str
    symbols: List[str]
    data_types: List[str]  # ["price", "orderbook", "trades"]
    client_id: str
    created_at: datetime
    is_active: bool

class StreamUpdate(BaseModel):
    """Real-time stream update"""
    subscription_id: str
    symbol: str
    data_type: str
    data: Union[PriceData, OrderBookSnapshot, Trade]
    timestamp: datetime
    sequence_number: int

# Aggregated Models for Dashboard Display

class SymbolSummary(BaseModel):
    """Complete symbol summary for dashboard"""
    symbol: str
    name: str
    current_price: Decimal
    change_24h: Decimal
    change_percent_24h: Decimal
    volume_24h: Decimal
    market_cap: Optional[Decimal] = None
    technical_indicators: TechnicalIndicators
    signals: List[TradingSignal]
    sentiment: MarketSentiment
    last_updated: datetime

class PortfolioMarketData(BaseModel):
    """Portfolio market data aggregation"""
    total_value: Decimal
    total_change: Decimal
    total_change_percent: Decimal
    positions: List[SymbolSummary]
    sector_allocation: Dict[str, Decimal]
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    risk_metrics: Dict[str, Decimal]
    last_updated: datetime

class MarketDataCache(BaseModel):
    """Cache entry for market data"""
    key: str
    data: Any
    timestamp: datetime
    ttl_seconds: int
    provider: MarketDataProvider
    hit_count: int = 0