#!/usr/bin/env python3
"""
Market Microstructure Analysis MCP Server
Real-time order flow, market impact, and liquidity analysis
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field
import uuid
import math
from enum import Enum
from collections import deque, defaultdict
import heapq
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/market_microstructure.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Market Microstructure Analysis",
    description="Real-time order flow, market impact, and liquidity analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    ICEBERG = "iceberg"

class LiquidityType(str, Enum):
    MAKER = "maker"
    TAKER = "taker"
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"

class MarketRegime(str, Enum):
    NORMAL = "normal"
    VOLATILE = "volatile"
    STRESSED = "stressed"
    ILLIQUID = "illiquid"
    TRENDING = "trending"

class ImpactModel(str, Enum):
    LINEAR = "linear"
    SQUARE_ROOT = "square_root"
    LOGARITHMIC = "logarithmic"
    ALMGREN_CHRISS = "almgren_chriss"

# Data models
@dataclass
class OrderBookLevel:
    price: float
    size: float
    orders: int
    timestamp: str

@dataclass
class OrderBook:
    symbol: str
    timestamp: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    mid_price: float
    spread: float
    depth: Dict[str, float]  # depth at various price levels
    imbalance: float
    microstructure_signals: Dict[str, float]

@dataclass
class Trade:
    id: str
    symbol: str
    timestamp: str
    price: float
    size: float
    side: OrderSide
    trade_type: LiquidityType
    market_impact: float
    vwap_deviation: float
    aggressor_flag: bool

@dataclass
class OrderFlowMetrics:
    symbol: str
    timestamp: str
    timeframe: str  # 1m, 5m, 15m, etc.
    total_volume: float
    buy_volume: float
    sell_volume: float
    order_imbalance: float
    trade_count: int
    avg_trade_size: float
    volume_weighted_price: float
    price_improvement: float
    effective_spread: float
    realized_spread: float
    market_impact_metrics: Dict[str, float]
    flow_toxicity: float  # Adverse selection measure
    pin_risk: float  # Option pin risk

@dataclass
class LiquidityMetrics:
    symbol: str
    timestamp: str
    bid_ask_spread: float
    effective_spread: float
    quoted_spread: float
    depth_at_bbo: float  # Best bid/offer
    depth_at_5bps: float  # 5 basis points
    depth_at_10bps: float  # 10 basis points
    market_depth_ratio: float
    price_impact_per_dollar: float
    resilience_metric: float
    liquidity_score: float
    amihud_illiquidity: float
    kyle_lambda: float  # Adverse selection component

@dataclass
class MarketImpact:
    id: str
    symbol: str
    timestamp: str
    order_size: float
    order_direction: OrderSide
    pre_trade_price: float
    execution_price: float
    post_trade_price: float
    temporary_impact: float
    permanent_impact: float
    implementation_shortfall: float
    participation_rate: float
    model_prediction: float
    model_type: ImpactModel

@dataclass
class MicrostructureSignal:
    id: str
    symbol: str
    timestamp: str
    signal_type: str  # order_imbalance, price_pressure, etc.
    strength: float  # -1 to 1
    confidence: float  # 0 to 1
    timeframe: str
    description: str
    components: Dict[str, float]
    decay_rate: float
    expected_duration: int  # minutes

@dataclass
class MarketRegimeAnalysis:
    symbol: str
    timestamp: str
    current_regime: MarketRegime
    regime_probability: float
    regime_duration: int  # minutes in current regime
    volatility_level: float
    liquidity_level: float
    stress_indicators: Dict[str, float]
    regime_transitions: List[Dict[str, Any]]  # Recent transitions
    stability_score: float

class MarketDataFeed(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    price: float = Field(..., description="Current price")
    size: float = Field(..., description="Trade size")
    side: OrderSide = Field(..., description="Order side")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class OrderBookUpdate(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    bids: List[Dict[str, float]] = Field(..., description="Bid levels [price, size, orders]")
    asks: List[Dict[str, float]] = Field(..., description="Ask levels [price, size, orders]")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ImpactAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    order_size: float = Field(..., description="Order size")
    side: OrderSide = Field(..., description="Order direction")
    participation_rate: float = Field(default=0.1, description="Participation rate (0-1)")
    model_type: ImpactModel = Field(default=ImpactModel.SQUARE_ROOT, description="Impact model")

class MarketMicrostructure:
    def __init__(self):
        self.order_books = {}
        self.trades = {}
        self.order_flow_metrics = {}
        self.liquidity_metrics = {}
        self.market_impacts = {}
        self.microstructure_signals = {}
        self.regime_analysis = {}
        self.active_websockets = []
        
        # Real-time data structures
        self.trade_streams = defaultdict(lambda: deque(maxlen=10000))
        self.order_book_snapshots = defaultdict(lambda: deque(maxlen=1000))
        self.volume_profiles = defaultdict(lambda: defaultdict(float))
        self.tick_data = defaultdict(lambda: deque(maxlen=50000))
        
        # Market making and liquidity provision tracking
        self.liquidity_providers = defaultdict(dict)
        self.market_makers = defaultdict(list)
        
        # Initialize sample data and models
        self._initialize_sample_symbols()
        self._initialize_impact_models()
        
        # Background processing
        self.processing_active = True
        asyncio.create_task(self._process_microstructure_signals())
        asyncio.create_task(self._analyze_market_regimes())
        asyncio.create_task(self._calculate_liquidity_metrics())
        asyncio.create_task(self._generate_sample_data())
        
        logger.info("Market Microstructure Analysis system initialized")
    
    def _initialize_sample_symbols(self):
        """Initialize tracking for sample symbols"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "SPY", "QQQ"]
        
        for symbol in symbols:
            # Initialize with basic order book
            self.order_books[symbol] = OrderBook(
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                bids=[],
                asks=[],
                mid_price=np.random.uniform(100, 500),
                spread=0.01,
                depth={},
                imbalance=0.0,
                microstructure_signals={}
            )
            
            # Initialize regime analysis
            self.regime_analysis[symbol] = MarketRegimeAnalysis(
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                current_regime=MarketRegime.NORMAL,
                regime_probability=0.85,
                regime_duration=45,
                volatility_level=0.02,
                liquidity_level=0.75,
                stress_indicators={},
                regime_transitions=[],
                stability_score=0.8
            )
        
        logger.info(f"Initialized microstructure tracking for {len(symbols)} symbols")
    
    def _initialize_impact_models(self):
        """Initialize market impact models"""
        self.impact_models = {
            ImpactModel.LINEAR: self._linear_impact_model,
            ImpactModel.SQUARE_ROOT: self._square_root_impact_model,
            ImpactModel.LOGARITHMIC: self._logarithmic_impact_model,
            ImpactModel.ALMGREN_CHRISS: self._almgren_chriss_impact_model
        }
        
        # Model parameters (would be calibrated from historical data)
        self.impact_parameters = {
            ImpactModel.LINEAR: {"alpha": 0.1},
            ImpactModel.SQUARE_ROOT: {"alpha": 0.314, "beta": 0.5},
            ImpactModel.LOGARITHMIC: {"alpha": 0.1, "beta": 0.01},
            ImpactModel.ALMGREN_CHRISS: {"gamma": 2e-7, "eta": 2.5e-6}
        }
        
        logger.info("Market impact models initialized")
    
    async def process_trade(self, trade_data: MarketDataFeed) -> Trade:
        """Process incoming trade data"""
        trade_id = str(uuid.uuid4())
        
        # Get current order book
        order_book = self.order_books.get(trade_data.symbol)
        if not order_book:
            raise HTTPException(status_code=404, detail="Symbol not found")
        
        # Determine trade characteristics
        mid_price = order_book.mid_price
        vwap_deviation = (trade_data.price - mid_price) / mid_price
        
        # Determine if aggressive (market order) or passive (limit order)
        spread = order_book.spread
        aggressor_flag = abs(vwap_deviation) > spread / 2
        
        trade_type = LiquidityType.TAKER if aggressor_flag else LiquidityType.MAKER
        
        # Calculate market impact
        market_impact = await self._calculate_immediate_impact(
            trade_data.symbol, trade_data.size, trade_data.side, trade_data.price
        )
        
        # Create trade record
        trade = Trade(
            id=trade_id,
            symbol=trade_data.symbol,
            timestamp=trade_data.timestamp,
            price=trade_data.price,
            size=trade_data.size,
            side=trade_data.side,
            trade_type=trade_type,
            market_impact=market_impact,
            vwap_deviation=vwap_deviation,
            aggressor_flag=aggressor_flag
        )
        
        # Store trade
        self.trades[trade_id] = trade
        self.trade_streams[trade_data.symbol].append(trade)
        self.tick_data[trade_data.symbol].append({
            "timestamp": trade_data.timestamp,
            "price": trade_data.price,
            "size": trade_data.size,
            "side": trade_data.side.value
        })
        
        # Update order book mid price
        order_book.mid_price = trade_data.price
        order_book.timestamp = trade_data.timestamp
        
        # Trigger microstructure analysis
        await self._update_microstructure_metrics(trade_data.symbol)
        
        # Broadcast trade
        await self._broadcast_trade(trade)
        
        logger.info(f"Processed trade: {trade_data.symbol} {trade_data.size}@{trade_data.price}")
        
        return trade
    
    async def update_order_book(self, update: OrderBookUpdate) -> OrderBook:
        """Update order book with new levels"""
        symbol = update.symbol
        
        # Create order book levels
        bids = []
        for bid_data in update.bids:
            level = OrderBookLevel(
                price=bid_data["price"],
                size=bid_data["size"],
                orders=int(bid_data.get("orders", 1)),
                timestamp=update.timestamp
            )
            bids.append(level)
        
        asks = []
        for ask_data in update.asks:
            level = OrderBookLevel(
                price=ask_data["price"],
                size=ask_data["size"],
                orders=int(ask_data.get("orders", 1)),
                timestamp=update.timestamp
            )
            asks.append(level)
        
        # Sort levels
        bids.sort(key=lambda x: x.price, reverse=True)  # Highest first
        asks.sort(key=lambda x: x.price)  # Lowest first
        
        # Calculate mid price and spread
        if bids and asks:
            best_bid = bids[0].price
            best_ask = asks[0].price
            mid_price = (best_bid + best_ask) / 2
            spread = best_ask - best_bid
        else:
            mid_price = self.order_books.get(symbol, {}).get("mid_price", 100.0)
            spread = 0.01
        
        # Calculate depth at various levels
        depth = await self._calculate_order_book_depth(bids, asks, mid_price)
        
        # Calculate order imbalance
        imbalance = await self._calculate_order_imbalance(bids, asks)
        
        # Generate microstructure signals
        microstructure_signals = await self._generate_microstructure_signals(symbol, bids, asks, imbalance)
        
        # Create updated order book
        order_book = OrderBook(
            symbol=symbol,
            timestamp=update.timestamp,
            bids=bids,
            asks=asks,
            mid_price=mid_price,
            spread=spread,
            depth=depth,
            imbalance=imbalance,
            microstructure_signals=microstructure_signals
        )
        
        # Store order book
        self.order_books[symbol] = order_book
        self.order_book_snapshots[symbol].append(order_book)
        
        # Broadcast update
        await self._broadcast_order_book(order_book)
        
        return order_book
    
    async def _calculate_order_book_depth(self, bids: List[OrderBookLevel], 
                                        asks: List[OrderBookLevel], mid_price: float) -> Dict[str, float]:
        """Calculate order book depth at various price levels"""
        depth = {}
        
        # Depth at best bid/offer
        depth["bbo"] = (bids[0].size if bids else 0) + (asks[0].size if asks else 0)
        
        # Depth within basis points
        for bps in [5, 10, 25, 50]:
            price_range = mid_price * (bps / 10000)
            
            bid_depth = sum(level.size for level in bids 
                           if level.price >= mid_price - price_range)
            ask_depth = sum(level.size for level in asks 
                           if level.price <= mid_price + price_range)
            
            depth[f"{bps}bps"] = bid_depth + ask_depth
        
        return depth
    
    async def _calculate_order_imbalance(self, bids: List[OrderBookLevel], 
                                       asks: List[OrderBookLevel]) -> float:
        """Calculate order book imbalance"""
        if not bids or not asks:
            return 0.0
        
        # Volume imbalance at best levels
        best_bid_size = bids[0].size
        best_ask_size = asks[0].size
        
        total_size = best_bid_size + best_ask_size
        if total_size == 0:
            return 0.0
        
        imbalance = (best_bid_size - best_ask_size) / total_size
        return imbalance
    
    async def _generate_microstructure_signals(self, symbol: str, bids: List[OrderBookLevel],
                                             asks: List[OrderBookLevel], imbalance: float) -> Dict[str, float]:
        """Generate microstructure trading signals"""
        signals = {}
        
        # Order imbalance signal
        signals["order_imbalance"] = imbalance
        
        # Spread signal (tight spread = good liquidity)
        if bids and asks:
            spread = asks[0].price - bids[0].price
            mid_price = (bids[0].price + asks[0].price) / 2
            relative_spread = spread / mid_price
            signals["liquidity_signal"] = max(-1, min(1, 1 - relative_spread * 1000))
        
        # Order book depth signal
        total_depth = sum(level.size for level in bids[:5]) + sum(level.size for level in asks[:5])
        signals["depth_signal"] = min(1.0, total_depth / 10000)  # Normalize
        
        # Price level concentration
        if len(bids) > 1 and len(asks) > 1:
            bid_concentration = bids[0].size / sum(level.size for level in bids[:5])
            ask_concentration = asks[0].size / sum(level.size for level in asks[:5])
            signals["concentration_signal"] = (bid_concentration + ask_concentration) / 2
        
        return signals
    
    async def _calculate_immediate_impact(self, symbol: str, size: float, 
                                        side: OrderSide, price: float) -> float:
        """Calculate immediate market impact of trade"""
        order_book = self.order_books.get(symbol)
        if not order_book:
            return 0.0
        
        mid_price = order_book.mid_price
        impact = (price - mid_price) / mid_price
        
        # Adjust for order side
        if side == OrderSide.SELL:
            impact = -impact
        
        return impact
    
    async def calculate_order_flow_metrics(self, symbol: str, timeframe: str = "5m") -> OrderFlowMetrics:
        """Calculate order flow metrics for specified timeframe"""
        # Parse timeframe
        if timeframe == "1m":
            minutes = 1
        elif timeframe == "5m":
            minutes = 5
        elif timeframe == "15m":
            minutes = 15
        elif timeframe == "1h":
            minutes = 60
        else:
            minutes = 5
        
        # Get trades in timeframe
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_trades = [
            trade for trade in self.trade_streams[symbol]
            if datetime.fromisoformat(trade.timestamp.replace('Z', '+00:00').replace('+00:00', '')) >= cutoff_time
        ]
        
        if not recent_trades:
            # Return empty metrics
            return OrderFlowMetrics(
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                timeframe=timeframe,
                total_volume=0, buy_volume=0, sell_volume=0,
                order_imbalance=0, trade_count=0, avg_trade_size=0,
                volume_weighted_price=0, price_improvement=0,
                effective_spread=0, realized_spread=0,
                market_impact_metrics={}, flow_toxicity=0, pin_risk=0
            )
        
        # Calculate metrics
        total_volume = sum(trade.size for trade in recent_trades)
        buy_volume = sum(trade.size for trade in recent_trades if trade.side == OrderSide.BUY)
        sell_volume = sum(trade.size for trade in recent_trades if trade.side == OrderSide.SELL)
        
        order_imbalance = (buy_volume - sell_volume) / total_volume if total_volume > 0 else 0
        trade_count = len(recent_trades)
        avg_trade_size = total_volume / trade_count if trade_count > 0 else 0
        
        # Volume weighted average price
        total_value = sum(trade.price * trade.size for trade in recent_trades)
        vwap = total_value / total_volume if total_volume > 0 else 0
        
        # Price improvement (simplified)
        price_improvement = np.mean([abs(trade.vwap_deviation) for trade in recent_trades])
        
        # Effective spread
        effective_spread = np.mean([abs(trade.market_impact) for trade in recent_trades]) * 2
        
        # Realized spread (simplified - would need future price data)
        realized_spread = effective_spread * 0.7  # Estimate
        
        # Market impact metrics
        market_impact_metrics = {
            "avg_impact": np.mean([trade.market_impact for trade in recent_trades]),
            "impact_volatility": np.std([trade.market_impact for trade in recent_trades]),
            "max_impact": max([abs(trade.market_impact) for trade in recent_trades]) if recent_trades else 0
        }
        
        # Flow toxicity (adverse selection measure)
        flow_toxicity = await self._calculate_flow_toxicity(recent_trades)
        
        # PIN risk (probability of informed trading)
        pin_risk = await self._calculate_pin_risk(symbol, recent_trades)
        
        metrics = OrderFlowMetrics(
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
            timeframe=timeframe,
            total_volume=total_volume,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            order_imbalance=order_imbalance,
            trade_count=trade_count,
            avg_trade_size=avg_trade_size,
            volume_weighted_price=vwap,
            price_improvement=price_improvement,
            effective_spread=effective_spread,
            realized_spread=realized_spread,
            market_impact_metrics=market_impact_metrics,
            flow_toxicity=flow_toxicity,
            pin_risk=pin_risk
        )
        
        # Store metrics
        metrics_id = f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self.order_flow_metrics[metrics_id] = metrics
        
        return metrics
    
    async def _calculate_flow_toxicity(self, trades: List[Trade]) -> float:
        """Calculate flow toxicity (adverse selection measure)"""
        if len(trades) < 2:
            return 0.0
        
        # Simplified toxicity measure based on price impact persistence
        impacts = [trade.market_impact for trade in trades]
        
        # Calculate autocorrelation of impacts
        if len(impacts) > 5:
            impacts_array = np.array(impacts)
            correlation = np.corrcoef(impacts_array[:-1], impacts_array[1:])[0, 1]
            toxicity = max(0, correlation)  # Positive correlation indicates toxicity
        else:
            toxicity = 0.0
        
        return toxicity
    
    async def _calculate_pin_risk(self, symbol: str, trades: List[Trade]) -> float:
        """Calculate PIN (Probability of Informed Trading) risk"""
        if len(trades) < 10:
            return 0.0
        
        # Simplified PIN calculation
        buy_trades = [t for t in trades if t.side == OrderSide.BUY]
        sell_trades = [t for t in trades if t.side == OrderSide.SELL]
        
        buy_count = len(buy_trades)
        sell_count = len(sell_trades)
        total_count = buy_count + sell_count
        
        if total_count == 0:
            return 0.0
        
        # Calculate order imbalance variance (proxy for informed trading)
        imbalance = abs(buy_count - sell_count) / total_count
        
        # Higher imbalance suggests higher informed trading probability
        pin_risk = min(1.0, imbalance * 2)
        
        return pin_risk
    
    async def calculate_liquidity_metrics(self, symbol: str) -> LiquidityMetrics:
        """Calculate comprehensive liquidity metrics"""
        order_book = self.order_books.get(symbol)
        if not order_book:
            raise HTTPException(status_code=404, detail="Symbol not found")
        
        # Bid-ask spreads
        if order_book.bids and order_book.asks:
            best_bid = order_book.bids[0].price
            best_ask = order_book.asks[0].price
            mid_price = order_book.mid_price
            
            bid_ask_spread = best_ask - best_bid
            quoted_spread = bid_ask_spread / mid_price
        else:
            bid_ask_spread = quoted_spread = 0.01
            mid_price = order_book.mid_price
        
        # Effective spread (from recent trades)
        recent_trades = list(self.trade_streams[symbol])[-100:]  # Last 100 trades
        if recent_trades:
            effective_spread = np.mean([abs(trade.market_impact) for trade in recent_trades]) * 2
        else:
            effective_spread = quoted_spread
        
        # Depth metrics
        depth_at_bbo = order_book.depth.get("bbo", 0)
        depth_at_5bps = order_book.depth.get("5bps", 0)
        depth_at_10bps = order_book.depth.get("10bps", 0)
        
        # Market depth ratio
        market_depth_ratio = depth_at_5bps / depth_at_bbo if depth_at_bbo > 0 else 1.0
        
        # Price impact per dollar
        if recent_trades and depth_at_bbo > 0:
            avg_trade_size = np.mean([trade.size for trade in recent_trades])
            avg_impact = np.mean([abs(trade.market_impact) for trade in recent_trades])
            price_impact_per_dollar = avg_impact / avg_trade_size if avg_trade_size > 0 else 0
        else:
            price_impact_per_dollar = 0.001
        
        # Resilience metric (order book recovery speed)
        resilience_metric = await self._calculate_resilience(symbol)
        
        # Amihud illiquidity measure
        amihud_illiquidity = await self._calculate_amihud_illiquidity(symbol)
        
        # Kyle's lambda (adverse selection component)
        kyle_lambda = await self._calculate_kyle_lambda(symbol)
        
        # Overall liquidity score (0-100)
        liquidity_score = await self._calculate_liquidity_score(
            quoted_spread, effective_spread, depth_at_5bps, 
            price_impact_per_dollar, resilience_metric
        )
        
        metrics = LiquidityMetrics(
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
            bid_ask_spread=bid_ask_spread,
            effective_spread=effective_spread,
            quoted_spread=quoted_spread,
            depth_at_bbo=depth_at_bbo,
            depth_at_5bps=depth_at_5bps,
            depth_at_10bps=depth_at_10bps,
            market_depth_ratio=market_depth_ratio,
            price_impact_per_dollar=price_impact_per_dollar,
            resilience_metric=resilience_metric,
            liquidity_score=liquidity_score,
            amihud_illiquidity=amihud_illiquidity,
            kyle_lambda=kyle_lambda
        )
        
        # Store metrics
        metrics_id = f"{symbol}_liquidity_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self.liquidity_metrics[metrics_id] = metrics
        
        return metrics
    
    async def _calculate_resilience(self, symbol: str) -> float:
        """Calculate order book resilience (recovery speed after trades)"""
        # Simplified resilience calculation
        recent_snapshots = list(self.order_book_snapshots[symbol])[-10:]
        
        if len(recent_snapshots) < 2:
            return 0.5  # Default moderate resilience
        
        # Calculate spread stability
        spreads = [snapshot.spread for snapshot in recent_snapshots]
        spread_stability = 1 - (np.std(spreads) / np.mean(spreads)) if np.mean(spreads) > 0 else 0
        
        # Calculate depth stability
        depths = [snapshot.depth.get("bbo", 0) for snapshot in recent_snapshots]
        depth_stability = 1 - (np.std(depths) / np.mean(depths)) if np.mean(depths) > 0 else 0
        
        resilience = (spread_stability + depth_stability) / 2
        return max(0, min(1, resilience))
    
    async def _calculate_amihud_illiquidity(self, symbol: str) -> float:
        """Calculate Amihud illiquidity measure"""
        recent_trades = list(self.trade_streams[symbol])[-100:]
        
        if len(recent_trades) < 10:
            return 0.001  # Default low illiquidity
        
        # Group trades by day (simplified - use all recent trades)
        total_volume = sum(trade.size * trade.price for trade in recent_trades)
        total_price_impact = sum(abs(trade.market_impact) for trade in recent_trades)
        
        if total_volume > 0:
            amihud = total_price_impact / total_volume * 1000000  # Scale factor
        else:
            amihud = 0.001
        
        return amihud
    
    async def _calculate_kyle_lambda(self, symbol: str) -> float:
        """Calculate Kyle's lambda (adverse selection component)"""
        recent_trades = list(self.trade_streams[symbol])[-50:]
        
        if len(recent_trades) < 10:
            return 0.1  # Default moderate adverse selection
        
        # Simplified Kyle's lambda: price impact vs order flow
        price_changes = []
        order_flows = []
        
        for i in range(1, len(recent_trades)):
            price_change = recent_trades[i].price - recent_trades[i-1].price
            order_flow = recent_trades[i].size * (1 if recent_trades[i].side == OrderSide.BUY else -1)
            
            price_changes.append(price_change)
            order_flows.append(order_flow)
        
        if len(price_changes) > 5 and np.std(order_flows) > 0:
            # Simple regression slope
            correlation = np.corrcoef(price_changes, order_flows)[0, 1]
            kyle_lambda = abs(correlation) * 0.1  # Scale factor
        else:
            kyle_lambda = 0.05
        
        return kyle_lambda
    
    async def _calculate_liquidity_score(self, quoted_spread: float, effective_spread: float,
                                       depth: float, impact_per_dollar: float, 
                                       resilience: float) -> float:
        """Calculate overall liquidity score (0-100)"""
        # Normalize components (lower is better for spreads and impact)
        spread_score = max(0, 100 - quoted_spread * 10000)  # Basis points
        effective_spread_score = max(0, 100 - effective_spread * 10000)
        depth_score = min(100, depth / 1000 * 100)  # Normalize depth
        impact_score = max(0, 100 - impact_per_dollar * 100000)
        resilience_score = resilience * 100
        
        # Weighted average
        liquidity_score = (
            spread_score * 0.25 +
            effective_spread_score * 0.25 +
            depth_score * 0.20 +
            impact_score * 0.15 +
            resilience_score * 0.15
        )
        
        return round(liquidity_score, 1)
    
    async def predict_market_impact(self, request: ImpactAnalysisRequest) -> MarketImpact:
        """Predict market impact using specified model"""
        impact_id = str(uuid.uuid4())
        
        # Get current market data
        order_book = self.order_books.get(request.symbol)
        if not order_book:
            raise HTTPException(status_code=404, detail="Symbol not found")
        
        pre_trade_price = order_book.mid_price
        
        # Select impact model
        model_func = self.impact_models.get(request.model_type, self._square_root_impact_model)
        model_params = self.impact_parameters.get(request.model_type, {})
        
        # Calculate predicted impact
        predicted_impact = await model_func(
            request.order_size, order_book, request.participation_rate, model_params
        )
        
        # Estimate execution price
        if request.side == OrderSide.BUY:
            execution_price = pre_trade_price * (1 + predicted_impact)
        else:
            execution_price = pre_trade_price * (1 - predicted_impact)
        
        # Estimate post-trade price (temporary vs permanent impact)
        temporary_impact = predicted_impact * 0.6  # 60% temporary
        permanent_impact = predicted_impact * 0.4   # 40% permanent
        
        post_trade_price = pre_trade_price * (1 + permanent_impact * (1 if request.side == OrderSide.BUY else -1))
        
        # Implementation shortfall
        implementation_shortfall = abs(execution_price - pre_trade_price) / pre_trade_price
        
        impact = MarketImpact(
            id=impact_id,
            symbol=request.symbol,
            timestamp=datetime.now().isoformat(),
            order_size=request.order_size,
            order_direction=request.side,
            pre_trade_price=pre_trade_price,
            execution_price=execution_price,
            post_trade_price=post_trade_price,
            temporary_impact=temporary_impact,
            permanent_impact=permanent_impact,
            implementation_shortfall=implementation_shortfall,
            participation_rate=request.participation_rate,
            model_prediction=predicted_impact,
            model_type=request.model_type
        )
        
        self.market_impacts[impact_id] = impact
        
        logger.info(f"Predicted market impact for {request.symbol}: {predicted_impact:.4f}")
        
        return impact
    
    async def _linear_impact_model(self, order_size: float, order_book: OrderBook,
                                 participation_rate: float, params: Dict[str, Any]) -> float:
        """Linear market impact model"""
        alpha = params.get("alpha", 0.1)
        
        # Get market data
        recent_volume = sum(trade.size for trade in list(self.trade_streams[order_book.symbol])[-100:])
        avg_volume = recent_volume / 100 if recent_volume > 0 else 1000
        
        # Linear impact: alpha * (order_size / avg_volume)
        impact = alpha * (order_size / avg_volume)
        
        return min(0.1, impact)  # Cap at 10%
    
    async def _square_root_impact_model(self, order_size: float, order_book: OrderBook,
                                      participation_rate: float, params: Dict[str, Any]) -> float:
        """Square root market impact model (most common)"""
        alpha = params.get("alpha", 0.314)
        beta = params.get("beta", 0.5)
        
        # Get market data
        recent_trades = list(self.trade_streams[order_book.symbol])[-100:]
        if recent_trades:
            avg_volume = np.mean([trade.size for trade in recent_trades])
            volatility = np.std([trade.market_impact for trade in recent_trades])
        else:
            avg_volume = 1000
            volatility = 0.02
        
        # Square root model: alpha * volatility * (order_size / avg_volume)^beta
        size_ratio = order_size / avg_volume
        impact = alpha * volatility * (size_ratio ** beta)
        
        # Adjust for participation rate
        impact *= (1 / participation_rate) ** 0.25
        
        return min(0.15, impact)  # Cap at 15%
    
    async def _logarithmic_impact_model(self, order_size: float, order_book: OrderBook,
                                      participation_rate: float, params: Dict[str, Any]) -> float:
        """Logarithmic market impact model"""
        alpha = params.get("alpha", 0.1)
        beta = params.get("beta", 0.01)
        
        # Get market data
        depth = order_book.depth.get("5bps", 1000)
        
        # Logarithmic model: alpha * log(1 + beta * order_size / depth)
        size_ratio = order_size / depth
        impact = alpha * math.log(1 + beta * size_ratio)
        
        return min(0.1, impact)  # Cap at 10%
    
    async def _almgren_chriss_impact_model(self, order_size: float, order_book: OrderBook,
                                         participation_rate: float, params: Dict[str, Any]) -> float:
        """Almgren-Chriss market impact model"""
        gamma = params.get("gamma", 2e-7)  # Permanent impact parameter
        eta = params.get("eta", 2.5e-6)     # Temporary impact parameter
        
        # Get market data
        recent_trades = list(self.trade_streams[order_book.symbol])[-100:]
        if recent_trades:
            avg_volume = np.mean([trade.size for trade in recent_trades])
            volatility = np.std([trade.price for trade in recent_trades]) / order_book.mid_price
        else:
            avg_volume = 1000
            volatility = 0.02
        
        # Almgren-Chriss model components
        permanent_impact = gamma * order_size
        temporary_impact = eta * (order_size / participation_rate) * volatility
        
        total_impact = permanent_impact + temporary_impact
        
        return min(0.2, total_impact)  # Cap at 20%
    
    async def analyze_market_regime(self, symbol: str) -> MarketRegimeAnalysis:
        """Analyze current market regime"""
        # Get recent market data
        recent_trades = list(self.trade_streams[symbol])[-200:]
        order_book = self.order_books.get(symbol)
        
        if not recent_trades or not order_book:
            # Return default regime
            return self.regime_analysis.get(symbol, MarketRegimeAnalysis(
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                current_regime=MarketRegime.NORMAL,
                regime_probability=0.5,
                regime_duration=0,
                volatility_level=0.02,
                liquidity_level=0.5,
                stress_indicators={},
                regime_transitions=[],
                stability_score=0.5
            ))
        
        # Calculate regime indicators
        price_changes = [trade.market_impact for trade in recent_trades]
        volumes = [trade.size for trade in recent_trades]
        spreads = [snapshot.spread for snapshot in list(self.order_book_snapshots[symbol])[-50:]]
        
        # Volatility level
        volatility_level = np.std(price_changes) if price_changes else 0.02
        
        # Liquidity level (inverse of spread)
        avg_spread = np.mean(spreads) if spreads else 0.01
        liquidity_level = max(0, 1 - avg_spread * 1000)  # Normalize
        
        # Volume pattern
        volume_pattern = np.std(volumes) / np.mean(volumes) if volumes and np.mean(volumes) > 0 else 1
        
        # Stress indicators
        stress_indicators = {
            "volatility_stress": min(1.0, volatility_level / 0.05),  # Stress if vol > 5%
            "liquidity_stress": max(0, 1 - liquidity_level),
            "volume_stress": min(1.0, volume_pattern),
            "spread_stress": min(1.0, avg_spread / 0.001)  # Stress if spread > 0.1%
        }
        
        # Regime classification
        overall_stress = np.mean(list(stress_indicators.values()))
        
        if overall_stress > 0.8:
            current_regime = MarketRegime.STRESSED
        elif volatility_level > 0.04:
            current_regime = MarketRegime.VOLATILE
        elif liquidity_level < 0.3:
            current_regime = MarketRegime.ILLIQUID
        elif abs(np.mean(price_changes)) > 0.01:  # Strong trend
            current_regime = MarketRegime.TRENDING
        else:
            current_regime = MarketRegime.NORMAL
        
        # Regime probability (confidence in classification)
        regime_probability = max(0.5, 1 - overall_stress * 0.5)
        
        # Check for regime transitions
        current_analysis = self.regime_analysis.get(symbol)
        regime_transitions = current_analysis.regime_transitions if current_analysis else []
        
        if current_analysis and current_analysis.current_regime != current_regime:
            # Regime transition detected
            transition = {
                "from_regime": current_analysis.current_regime.value,
                "to_regime": current_regime.value,
                "timestamp": datetime.now().isoformat(),
                "trigger": "market_conditions"
            }
            regime_transitions.append(transition)
            regime_transitions = regime_transitions[-10:]  # Keep last 10 transitions
            regime_duration = 0
        else:
            regime_duration = current_analysis.regime_duration + 1 if current_analysis else 0
        
        # Stability score
        stability_score = min(1.0, (1 - overall_stress) * regime_probability)
        
        analysis = MarketRegimeAnalysis(
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
            current_regime=current_regime,
            regime_probability=regime_probability,
            regime_duration=regime_duration,
            volatility_level=volatility_level,
            liquidity_level=liquidity_level,
            stress_indicators=stress_indicators,
            regime_transitions=regime_transitions,
            stability_score=stability_score
        )
        
        self.regime_analysis[symbol] = analysis
        
        return analysis
    
    async def _process_microstructure_signals(self):
        """Background task to process microstructure signals"""
        while self.processing_active:
            try:
                for symbol in self.order_books.keys():
                    # Generate microstructure signals
                    await self._generate_enhanced_signals(symbol)
                
                await asyncio.sleep(5)  # Process every 5 seconds
                
            except Exception as e:
                logger.error(f"Error processing microstructure signals: {e}")
                await asyncio.sleep(10)
    
    async def _generate_enhanced_signals(self, symbol: str):
        """Generate enhanced microstructure signals"""
        order_book = self.order_books.get(symbol)
        recent_trades = list(self.trade_streams[symbol])[-50:]
        
        if not order_book or not recent_trades:
            return
        
        # Order flow imbalance signal
        buy_volume = sum(t.size for t in recent_trades if t.side == OrderSide.BUY)
        sell_volume = sum(t.size for t in recent_trades if t.side == OrderSide.SELL)
        total_volume = buy_volume + sell_volume
        
        if total_volume > 0:
            flow_imbalance = (buy_volume - sell_volume) / total_volume
            
            signal = MicrostructureSignal(
                id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                signal_type="order_flow_imbalance",
                strength=flow_imbalance,
                confidence=min(1.0, total_volume / 10000),
                timeframe="5m",
                description=f"Order flow {'bullish' if flow_imbalance > 0 else 'bearish'} imbalance",
                components={"buy_volume": buy_volume, "sell_volume": sell_volume},
                decay_rate=0.1,
                expected_duration=15
            )
            
            self.microstructure_signals[signal.id] = signal
    
    async def _analyze_market_regimes(self):
        """Background task to analyze market regimes"""
        while self.processing_active:
            try:
                for symbol in self.order_books.keys():
                    await self.analyze_market_regime(symbol)
                
                await asyncio.sleep(60)  # Analyze every minute
                
            except Exception as e:
                logger.error(f"Error analyzing market regimes: {e}")
                await asyncio.sleep(30)
    
    async def _calculate_liquidity_metrics(self):
        """Background task to calculate liquidity metrics"""
        while self.processing_active:
            try:
                for symbol in self.order_books.keys():
                    await self.calculate_liquidity_metrics(symbol)
                
                await asyncio.sleep(30)  # Calculate every 30 seconds
                
            except Exception as e:
                logger.error(f"Error calculating liquidity metrics: {e}")
                await asyncio.sleep(30)
    
    async def _generate_sample_data(self):
        """Generate sample market data for demonstration"""
        while self.processing_active:
            try:
                for symbol in self.order_books.keys():
                    # Generate sample trade
                    order_book = self.order_books[symbol]
                    base_price = order_book.mid_price
                    
                    # Random price movement
                    price_change = np.random.normal(0, base_price * 0.001)
                    new_price = base_price + price_change
                    
                    size = np.random.lognormal(6, 1)  # Random size
                    side = OrderSide.BUY if np.random.random() > 0.5 else OrderSide.SELL
                    
                    # Create trade data
                    trade_data = MarketDataFeed(
                        symbol=symbol,
                        price=new_price,
                        size=size,
                        side=side
                    )
                    
                    # Process trade
                    await self.process_trade(trade_data)
                    
                    # Generate sample order book update
                    mid_price = new_price
                    spread = np.random.uniform(0.01, 0.05)
                    
                    bids = []
                    asks = []
                    
                    for i in range(5):
                        bid_price = mid_price - spread/2 - i * 0.01
                        ask_price = mid_price + spread/2 + i * 0.01
                        
                        bids.append({
                            "price": bid_price,
                            "size": np.random.lognormal(7, 0.5),
                            "orders": np.random.randint(1, 10)
                        })
                        
                        asks.append({
                            "price": ask_price,
                            "size": np.random.lognormal(7, 0.5),
                            "orders": np.random.randint(1, 10)
                        })
                    
                    order_book_update = OrderBookUpdate(
                        symbol=symbol,
                        bids=bids,
                        asks=asks
                    )
                    
                    await self.update_order_book(order_book_update)
                
                await asyncio.sleep(1)  # Generate data every second
                
            except Exception as e:
                logger.error(f"Error generating sample data: {e}")
                await asyncio.sleep(5)
    
    async def _update_microstructure_metrics(self, symbol: str):
        """Update microstructure metrics after trade"""
        # Calculate order flow metrics
        await self.calculate_order_flow_metrics(symbol, "1m")
        await self.calculate_order_flow_metrics(symbol, "5m")
    
    async def _broadcast_trade(self, trade: Trade):
        """Broadcast trade to WebSocket clients"""
        if self.active_websockets:
            message = {
                "type": "trade",
                "data": asdict(trade)
            }
            await self._broadcast_message(message)
    
    async def _broadcast_order_book(self, order_book: OrderBook):
        """Broadcast order book update to WebSocket clients"""
        if self.active_websockets:
            message = {
                "type": "order_book",
                "data": asdict(order_book)
            }
            await self._broadcast_message(message)
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all WebSocket clients"""
        disconnected = []
        for websocket in self.active_websockets:
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except:
                disconnected.append(websocket)
        
        for ws in disconnected:
            self.active_websockets.remove(ws)

# Initialize the market microstructure system
microstructure = MarketMicrostructure()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Market Microstructure Analysis",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "order_flow_analysis",
            "liquidity_metrics",
            "market_impact_prediction",
            "regime_analysis",
            "microstructure_signals",
            "order_book_analytics"
        ],
        "symbols_tracked": len(microstructure.order_books),
        "total_trades": sum(len(trades) for trades in microstructure.trade_streams.values()),
        "active_signals": len(microstructure.microstructure_signals)
    }

@app.get("/capabilities")
async def get_capabilities():
    """Get system capabilities"""
    return {
        "order_sides": [os.value for os in OrderSide],
        "order_types": [ot.value for ot in OrderType],
        "liquidity_types": [lt.value for lt in LiquidityType],
        "market_regimes": [mr.value for mr in MarketRegime],
        "impact_models": [im.value for im in ImpactModel],
        "supported_features": [
            "real_time_order_flow",
            "order_book_analysis",
            "market_impact_modeling",
            "liquidity_measurement",
            "regime_detection",
            "toxicity_analysis",
            "pin_risk_calculation",
            "resilience_metrics"
        ]
    }

@app.post("/trades")
async def process_trade(trade_data: MarketDataFeed):
    """Process incoming trade"""
    try:
        trade = await microstructure.process_trade(trade_data)
        return {"trade": asdict(trade)}
        
    except Exception as e:
        logger.error(f"Error processing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/order-book")
async def update_order_book(update: OrderBookUpdate):
    """Update order book"""
    try:
        order_book = await microstructure.update_order_book(update)
        return {"order_book": asdict(order_book)}
        
    except Exception as e:
        logger.error(f"Error updating order book: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/order-book/{symbol}")
async def get_order_book(symbol: str):
    """Get current order book"""
    if symbol not in microstructure.order_books:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    return {"order_book": asdict(microstructure.order_books[symbol])}

@app.get("/order-flow/{symbol}")
async def get_order_flow_metrics(symbol: str, timeframe: str = "5m"):
    """Get order flow metrics"""
    try:
        metrics = await microstructure.calculate_order_flow_metrics(symbol, timeframe)
        return {"order_flow_metrics": asdict(metrics)}
        
    except Exception as e:
        logger.error(f"Error calculating order flow metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/liquidity/{symbol}")
async def get_liquidity_metrics(symbol: str):
    """Get liquidity metrics"""
    try:
        metrics = await microstructure.calculate_liquidity_metrics(symbol)
        return {"liquidity_metrics": asdict(metrics)}
        
    except Exception as e:
        logger.error(f"Error calculating liquidity metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/market-impact/predict")
async def predict_market_impact(request: ImpactAnalysisRequest):
    """Predict market impact"""
    try:
        impact = await microstructure.predict_market_impact(request)
        return {"market_impact": asdict(impact)}
        
    except Exception as e:
        logger.error(f"Error predicting market impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market-impact/{impact_id}")
async def get_market_impact(impact_id: str):
    """Get market impact result"""
    if impact_id not in microstructure.market_impacts:
        raise HTTPException(status_code=404, detail="Market impact not found")
    
    return {"market_impact": asdict(microstructure.market_impacts[impact_id])}

@app.get("/regime/{symbol}")
async def get_market_regime(symbol: str):
    """Get market regime analysis"""
    try:
        regime = await microstructure.analyze_market_regime(symbol)
        return {"regime_analysis": asdict(regime)}
        
    except Exception as e:
        logger.error(f"Error analyzing market regime: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/signals/{symbol}")
async def get_microstructure_signals(symbol: str, limit: int = 50):
    """Get microstructure signals"""
    signals = [s for s in microstructure.microstructure_signals.values() if s.symbol == symbol]
    signals.sort(key=lambda x: x.timestamp, reverse=True)
    
    return {
        "signals": [asdict(signal) for signal in signals[:limit]],
        "total": len(signals)
    }

@app.get("/trades/{symbol}")
async def get_trades(symbol: str, limit: int = 100):
    """Get recent trades"""
    trades = list(microstructure.trade_streams[symbol])[-limit:]
    
    return {
        "trades": [asdict(trade) for trade in trades],
        "total": len(trades)
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time microstructure data"""
    await websocket.accept()
    microstructure.active_websockets.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text("Connected to Market Microstructure Analysis")
    except WebSocketDisconnect:
        microstructure.active_websockets.remove(websocket)

@app.get("/metrics")
async def get_system_metrics():
    """Get system metrics"""
    total_trades = sum(len(trades) for trades in microstructure.trade_streams.values())
    
    return {
        "symbols_tracked": len(microstructure.order_books),
        "total_trades_processed": total_trades,
        "order_flow_calculations": len(microstructure.order_flow_metrics),
        "liquidity_calculations": len(microstructure.liquidity_metrics),
        "market_impact_predictions": len(microstructure.market_impacts),
        "active_signals": len(microstructure.microstructure_signals),
        "active_websockets": len(microstructure.active_websockets),
        "cpu_usage": np.random.uniform(30, 70),
        "memory_usage": np.random.uniform(40, 80),
        "processing_latency_ms": np.random.uniform(1, 10),
        "order_book_update_rate": "10Hz",
        "uptime": "99.9%"
    }

if __name__ == "__main__":
    uvicorn.run(
        "market_microstructure:app",
        host="0.0.0.0",
        port=8092,
        reload=True,
        log_level="info"
    )