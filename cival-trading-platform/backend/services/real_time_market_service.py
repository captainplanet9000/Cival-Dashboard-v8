#!/usr/bin/env python3
"""
Phase 5: Real-Time Market Data Service
Live market data integration with WebSocket feeds and LLM analysis
"""

import asyncio
import logging
import json
import websockets
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from ..core.service_registry import get_registry
from ..models.llm_models import LLMRequest, LLMTaskType

logger = logging.getLogger(__name__)

class DataSource(Enum):
    """Market data sources"""
    BINANCE = "binance"
    COINBASE = "coinbase"
    HYPERLIQUID = "hyperliquid"
    MOCK = "mock"

class DataType(Enum):
    """Types of market data"""
    TICKER = "ticker"
    ORDERBOOK = "orderbook"
    TRADES = "trades"
    KLINES = "klines"
    LIQUIDATIONS = "liquidations"
    FUNDING = "funding"

@dataclass
class MarketTicker:
    """Real-time ticker data"""
    symbol: str
    price: Decimal
    bid: Decimal
    ask: Decimal
    volume_24h: Decimal
    change_24h: Decimal
    change_percent_24h: float
    high_24h: Decimal
    low_24h: Decimal
    timestamp: datetime
    source: str

@dataclass
class OrderBookLevel:
    """Order book price level"""
    price: Decimal
    quantity: Decimal
    orders: int

@dataclass
class OrderBookSnapshot:
    """Order book snapshot"""
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: datetime
    source: str

@dataclass
class Trade:
    """Individual trade data"""
    trade_id: str
    symbol: str
    price: Decimal
    quantity: Decimal
    side: str  # buy/sell
    timestamp: datetime
    source: str

@dataclass
class MarketAnalysis:
    """Real-time market analysis"""
    symbol: str
    trend: str  # bullish/bearish/neutral
    momentum: float  # -1 to 1
    volatility: float
    volume_profile: str
    support_levels: List[float]
    resistance_levels: List[float]
    sentiment_score: float
    confidence: float
    timestamp: datetime

class RealTimeMarketService:
    """
    Real-time market data service with WebSocket feeds,
    LLM-powered analysis, and comprehensive data aggregation
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Core services
        self.llm_service = None
        
        # Data storage
        self.tickers: Dict[str, MarketTicker] = {}
        self.orderbooks: Dict[str, OrderBookSnapshot] = {}
        self.recent_trades: Dict[str, List[Trade]] = {}
        self.market_analyses: Dict[str, MarketAnalysis] = {}
        
        # WebSocket connections
        self.ws_connections: Dict[str, Any] = {}
        self.data_subscribers: Dict[str, List[Callable]] = {}
        
        # Configuration
        self.config = {
            "symbols": ["BTCUSD", "ETHUSD", "SOLUSD", "ADAUSD", "DOTUSD"],
            "data_sources": [DataSource.MOCK, DataSource.BINANCE],
            "analysis_interval": 30,  # seconds
            "orderbook_depth": 20,
            "trade_history_limit": 100,
            "websocket_reconnect_delay": 5,
            "data_retention_hours": 24
        }
        
        # Statistics
        self.stats = {
            "messages_received": 0,
            "analysis_completed": 0,
            "websocket_reconnects": 0,
            "last_data_timestamp": None
        }
        
        # Running tasks
        self.running_tasks: List[asyncio.Task] = []
        
        logger.info("RealTimeMarketService initialized")
    
    async def initialize(self):
        """Initialize the real-time market service"""
        try:
            # Get required services
            self.llm_service = self.registry.get_service("llm_integration_service")
            
            # Start WebSocket connections
            await self._start_websocket_feeds()
            
            # Start analysis tasks
            await self._start_analysis_tasks()
            
            logger.info("RealTimeMarketService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RealTimeMarketService: {e}")
            raise
    
    async def _start_websocket_feeds(self):
        """Start WebSocket connections for real-time data"""
        for source in self.config["data_sources"]:
            if source == DataSource.MOCK:
                # Start mock data generator
                task = asyncio.create_task(self._mock_data_generator())
                self.running_tasks.append(task)
            elif source == DataSource.BINANCE:
                # Start Binance WebSocket feed
                task = asyncio.create_task(self._binance_websocket_feed())
                self.running_tasks.append(task)
            elif source == DataSource.COINBASE:
                # Start Coinbase WebSocket feed
                task = asyncio.create_task(self._coinbase_websocket_feed())
                self.running_tasks.append(task)
            elif source == DataSource.HYPERLIQUID:
                # Start Hyperliquid WebSocket feed
                task = asyncio.create_task(self._hyperliquid_websocket_feed())
                self.running_tasks.append(task)
        
        logger.info(f"Started WebSocket feeds for {len(self.config['data_sources'])} sources")
    
    async def _start_analysis_tasks(self):
        """Start market analysis tasks"""
        analysis_tasks = [
            asyncio.create_task(self._continuous_market_analysis()),
            asyncio.create_task(self._volume_analysis()),
            asyncio.create_task(self._sentiment_analysis()),
            asyncio.create_task(self._technical_analysis()),
            asyncio.create_task(self._data_cleanup())
        ]
        
        self.running_tasks.extend(analysis_tasks)
        logger.info(f"Started {len(analysis_tasks)} analysis tasks")
    
    async def _mock_data_generator(self):
        """Generate mock market data for testing"""
        import random
        
        base_prices = {
            "BTCUSD": 45000.0,
            "ETHUSD": 2300.0,
            "SOLUSD": 100.0,
            "ADAUSD": 0.5,
            "DOTUSD": 7.0
        }
        
        while True:
            try:
                for symbol in self.config["symbols"]:
                    base_price = base_prices.get(symbol, 1000.0)
                    
                    # Generate realistic price movement
                    price_change = random.uniform(-0.02, 0.02)  # 2% max change
                    new_price = base_price * (1 + price_change)
                    base_prices[symbol] = new_price
                    
                    # Create ticker data
                    ticker = MarketTicker(
                        symbol=symbol,
                        price=Decimal(str(new_price)),
                        bid=Decimal(str(new_price * 0.9999)),
                        ask=Decimal(str(new_price * 1.0001)),
                        volume_24h=Decimal(str(random.uniform(1000000, 5000000))),
                        change_24h=Decimal(str(random.uniform(-1000, 1000))),
                        change_percent_24h=random.uniform(-5.0, 5.0),
                        high_24h=Decimal(str(new_price * random.uniform(1.01, 1.05))),
                        low_24h=Decimal(str(new_price * random.uniform(0.95, 0.99))),
                        timestamp=datetime.now(timezone.utc),
                        source="mock"
                    )
                    
                    # Update ticker data
                    await self._update_ticker(ticker)
                    
                    # Generate order book data
                    orderbook = await self._generate_mock_orderbook(symbol, new_price)
                    await self._update_orderbook(orderbook)
                    
                    # Generate trade data
                    trade = Trade(
                        trade_id=str(uuid.uuid4()),
                        symbol=symbol,
                        price=Decimal(str(new_price)),
                        quantity=Decimal(str(random.uniform(0.1, 10.0))),
                        side=random.choice(["buy", "sell"]),
                        timestamp=datetime.now(timezone.utc),
                        source="mock"
                    )
                    
                    await self._update_trade(trade)
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Mock data generator error: {e}")
                await asyncio.sleep(5)
    
    async def _generate_mock_orderbook(self, symbol: str, price: float) -> OrderBookSnapshot:
        """Generate realistic mock order book"""
        import random
        
        bids = []
        asks = []
        
        # Generate bids (buy orders)
        for i in range(self.config["orderbook_depth"]):
            bid_price = price * (1 - (i + 1) * 0.001)  # 0.1% steps
            bid_quantity = random.uniform(0.1, 50.0)
            bids.append(OrderBookLevel(
                price=Decimal(str(bid_price)),
                quantity=Decimal(str(bid_quantity)),
                orders=random.randint(1, 10)
            ))
        
        # Generate asks (sell orders)
        for i in range(self.config["orderbook_depth"]):
            ask_price = price * (1 + (i + 1) * 0.001)  # 0.1% steps
            ask_quantity = random.uniform(0.1, 50.0)
            asks.append(OrderBookLevel(
                price=Decimal(str(ask_price)),
                quantity=Decimal(str(ask_quantity)),
                orders=random.randint(1, 10)
            ))
        
        return OrderBookSnapshot(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.now(timezone.utc),
            source="mock"
        )
    
    async def _binance_websocket_feed(self):
        """Binance WebSocket data feed"""
        while True:
            try:
                # Binance WebSocket URL for multiple streams
                symbols = [s.lower().replace("usd", "usdt") for s in self.config["symbols"]]
                streams = [f"{symbol}@ticker" for symbol in symbols]
                streams.extend([f"{symbol}@depth20@100ms" for symbol in symbols])
                
                url = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
                
                async with websockets.connect(url) as websocket:
                    logger.info("Connected to Binance WebSocket")
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self._process_binance_message(data)
                            self.stats["messages_received"] += 1
                            
                        except json.JSONDecodeError:
                            logger.error("Failed to decode Binance message")
                        except Exception as e:
                            logger.error(f"Error processing Binance message: {e}")
                            
            except Exception as e:
                logger.error(f"Binance WebSocket error: {e}")
                self.stats["websocket_reconnects"] += 1
                await asyncio.sleep(self.config["websocket_reconnect_delay"])
    
    async def _process_binance_message(self, data: Dict[str, Any]):
        """Process Binance WebSocket message"""
        try:
            stream = data.get("stream", "")
            data_content = data.get("data", {})
            
            if "@ticker" in stream:
                # Process ticker data
                ticker = MarketTicker(
                    symbol=data_content["s"].replace("USDT", "USD"),
                    price=Decimal(data_content["c"]),
                    bid=Decimal(data_content["b"]),
                    ask=Decimal(data_content["a"]),
                    volume_24h=Decimal(data_content["v"]),
                    change_24h=Decimal(data_content["P"]),
                    change_percent_24h=float(data_content["P"]),
                    high_24h=Decimal(data_content["h"]),
                    low_24h=Decimal(data_content["l"]),
                    timestamp=datetime.now(timezone.utc),
                    source="binance"
                )
                
                await self._update_ticker(ticker)
                
            elif "@depth" in stream:
                # Process order book data
                symbol = data_content["s"].replace("USDT", "USD")
                
                bids = [OrderBookLevel(
                    price=Decimal(level[0]),
                    quantity=Decimal(level[1]),
                    orders=1
                ) for level in data_content["bids"]]
                
                asks = [OrderBookLevel(
                    price=Decimal(level[0]),
                    quantity=Decimal(level[1]),
                    orders=1
                ) for level in data_content["asks"]]
                
                orderbook = OrderBookSnapshot(
                    symbol=symbol,
                    bids=bids,
                    asks=asks,
                    timestamp=datetime.now(timezone.utc),
                    source="binance"
                )
                
                await self._update_orderbook(orderbook)
                
        except Exception as e:
            logger.error(f"Error processing Binance message: {e}")
    
    async def _coinbase_websocket_feed(self):
        """Coinbase Pro WebSocket data feed"""
        # Placeholder for Coinbase WebSocket implementation
        logger.info("Coinbase WebSocket feed not implemented - using mock data")
        pass
    
    async def _hyperliquid_websocket_feed(self):
        """Hyperliquid WebSocket data feed"""
        # Placeholder for Hyperliquid WebSocket implementation
        logger.info("Hyperliquid WebSocket feed not implemented - using mock data")
        pass
    
    async def _update_ticker(self, ticker: MarketTicker):
        """Update ticker data and notify subscribers"""
        self.tickers[ticker.symbol] = ticker
        self.stats["last_data_timestamp"] = ticker.timestamp
        
        # Notify subscribers
        await self._notify_subscribers("ticker", ticker.symbol, asdict(ticker))
    
    async def _update_orderbook(self, orderbook: OrderBookSnapshot):
        """Update order book data and notify subscribers"""
        self.orderbooks[orderbook.symbol] = orderbook
        
        # Notify subscribers
        await self._notify_subscribers("orderbook", orderbook.symbol, asdict(orderbook))
    
    async def _update_trade(self, trade: Trade):
        """Update trade data and notify subscribers"""
        if trade.symbol not in self.recent_trades:
            self.recent_trades[trade.symbol] = []
        
        self.recent_trades[trade.symbol].append(trade)
        
        # Keep only recent trades
        limit = self.config["trade_history_limit"]
        if len(self.recent_trades[trade.symbol]) > limit:
            self.recent_trades[trade.symbol] = self.recent_trades[trade.symbol][-limit:]
        
        # Notify subscribers
        await self._notify_subscribers("trade", trade.symbol, asdict(trade))
    
    async def _continuous_market_analysis(self):
        """Continuously analyze market data using LLM"""
        while True:
            try:
                for symbol in self.config["symbols"]:
                    if symbol in self.tickers:
                        analysis = await self._analyze_market_data(symbol)
                        if analysis:
                            self.market_analyses[symbol] = analysis
                            self.stats["analysis_completed"] += 1
                            
                            # Notify subscribers
                            await self._notify_subscribers("analysis", symbol, asdict(analysis))
                
                await asyncio.sleep(self.config["analysis_interval"])
                
            except Exception as e:
                logger.error(f"Market analysis error: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_market_data(self, symbol: str) -> Optional[MarketAnalysis]:
        """Analyze market data for a symbol using LLM"""
        try:
            ticker = self.tickers.get(symbol)
            orderbook = self.orderbooks.get(symbol)
            trades = self.recent_trades.get(symbol, [])
            
            if not ticker:
                return None
            
            # Prepare market data for analysis
            market_data = {
                "ticker": asdict(ticker),
                "orderbook": asdict(orderbook) if orderbook else None,
                "recent_trades": [asdict(t) for t in trades[-10:]] if trades else [],
                "volume_analysis": await self._calculate_volume_metrics(symbol),
                "price_levels": await self._identify_key_levels(symbol)
            }
            
            # Create LLM prompt for market analysis
            prompt = f"""
            Analyze the real-time market data for {symbol} and provide comprehensive market analysis.
            
            Market Data:
            {json.dumps(market_data, indent=2, default=str)}
            
            Provide JSON response with:
            {{
                "trend": "bullish|bearish|neutral",
                "momentum": -1.0 to 1.0 (bearish to bullish),
                "volatility": 0.0 to 1.0,
                "volume_profile": "high|normal|low",
                "support_levels": [price1, price2, price3],
                "resistance_levels": [price1, price2, price3],
                "sentiment_score": 0.0 to 1.0,
                "confidence": 0.0 to 1.0,
                "key_insights": ["insight1", "insight2"],
                "risk_factors": ["risk1", "risk2"]
            }}
            """
            
            if self.llm_service:
                request = LLMRequest(
                    task_type=LLMTaskType.MARKET_ANALYSIS,
                    prompt=prompt,
                    context={"symbol": symbol, "market_data": market_data}
                )
                
                response = await self.llm_service.process_llm_request(request)
                analysis_data = json.loads(response.content)
                
                # Create market analysis object
                analysis = MarketAnalysis(
                    symbol=symbol,
                    trend=analysis_data.get("trend", "neutral"),
                    momentum=float(analysis_data.get("momentum", 0.0)),
                    volatility=float(analysis_data.get("volatility", 0.0)),
                    volume_profile=analysis_data.get("volume_profile", "normal"),
                    support_levels=analysis_data.get("support_levels", []),
                    resistance_levels=analysis_data.get("resistance_levels", []),
                    sentiment_score=float(analysis_data.get("sentiment_score", 0.5)),
                    confidence=float(analysis_data.get("confidence", 0.5)),
                    timestamp=datetime.now(timezone.utc)
                )
                
                return analysis
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to analyze market data for {symbol}: {e}")
            return None
    
    async def _notify_subscribers(self, data_type: str, symbol: str, data: Dict[str, Any]):
        """Notify data subscribers"""
        key = f"{data_type}:{symbol}"
        
        if key in self.data_subscribers:
            for callback in self.data_subscribers[key]:
                try:
                    await callback(data_type, symbol, data)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")
    
    def subscribe(self, data_type: str, symbol: str, callback: Callable):
        """Subscribe to real-time data updates"""
        key = f"{data_type}:{symbol}"
        
        if key not in self.data_subscribers:
            self.data_subscribers[key] = []
        
        self.data_subscribers[key].append(callback)
        logger.info(f"Added subscriber for {key}")
    
    def unsubscribe(self, data_type: str, symbol: str, callback: Callable):
        """Unsubscribe from data updates"""
        key = f"{data_type}:{symbol}"
        
        if key in self.data_subscribers and callback in self.data_subscribers[key]:
            self.data_subscribers[key].remove(callback)
            logger.info(f"Removed subscriber for {key}")
    
    async def get_ticker(self, symbol: str) -> Optional[MarketTicker]:
        """Get latest ticker data for symbol"""
        return self.tickers.get(symbol)
    
    async def get_orderbook(self, symbol: str) -> Optional[OrderBookSnapshot]:
        """Get latest order book for symbol"""
        return self.orderbooks.get(symbol)
    
    async def get_recent_trades(self, symbol: str, limit: int = 50) -> List[Trade]:
        """Get recent trades for symbol"""
        trades = self.recent_trades.get(symbol, [])
        return trades[-limit:] if trades else []
    
    async def get_market_analysis(self, symbol: str) -> Optional[MarketAnalysis]:
        """Get latest market analysis for symbol"""
        return self.market_analyses.get(symbol)
    
    async def get_all_tickers(self) -> Dict[str, MarketTicker]:
        """Get all ticker data"""
        return self.tickers.copy()
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get complete market overview"""
        return {
            "tickers": {k: asdict(v) for k, v in self.tickers.items()},
            "analyses": {k: asdict(v) for k, v in self.market_analyses.items()},
            "statistics": self.stats,
            "active_symbols": len(self.tickers),
            "last_update": self.stats.get("last_data_timestamp")
        }
    
    async def stop(self):
        """Stop the real-time market service"""
        # Cancel all running tasks
        for task in self.running_tasks:
            task.cancel()
        
        await asyncio.gather(*self.running_tasks, return_exceptions=True)
        
        # Close WebSocket connections
        for connection in self.ws_connections.values():
            if hasattr(connection, 'close'):
                await connection.close()
        
        logger.info("RealTimeMarketService stopped")
    
    # Placeholder methods for additional functionality
    async def _volume_analysis(self): pass
    async def _sentiment_analysis(self): pass
    async def _technical_analysis(self): pass
    async def _data_cleanup(self): pass
    async def _calculate_volume_metrics(self, symbol): return {}
    async def _identify_key_levels(self, symbol): return []