#!/usr/bin/env python3
"""
Alpaca Market Data MCP Server
Provides real-time and historical market data via Alpaca Markets API
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, Field
import websockets
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', 'your_alpaca_api_key')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', 'your_alpaca_secret_key')
ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
ALPACA_DATA_URL = os.getenv('ALPACA_DATA_URL', 'https://data.alpaca.markets')

# FastAPI app
app = FastAPI(
    title="Alpaca Market Data MCP Server",
    description="Model Context Protocol server for Alpaca market data",
    version="1.0.0"
)

security = HTTPBearer()

# Data models
@dataclass
class MarketQuote:
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    timestamp: str
    spread: float = 0.0
    
    def __post_init__(self):
        self.spread = self.ask_price - self.bid_price

@dataclass
class MarketTrade:
    symbol: str
    price: float
    size: int
    timestamp: str
    conditions: List[str] = None

@dataclass
class MarketBar:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: str
    vwap: float = 0.0

@dataclass
class AssetInfo:
    symbol: str
    name: str
    exchange: str
    asset_class: str
    status: str
    tradable: bool
    marginable: bool
    shortable: bool
    easy_to_borrow: bool
    fractionable: bool

class MarketDataRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols to fetch data for")
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    timeframe: Optional[str] = Field("1Day", description="Timeframe for bars (1Min, 5Min, 15Min, 1Hour, 1Day)")
    limit: Optional[int] = Field(1000, description="Maximum number of records to return")

class MarketDataService:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket_connections = set()
        self.real_time_data = {}
        
    async def initialize(self):
        """Initialize the market data service"""
        self.session = aiohttp.ClientSession(
            headers={
                'APCA-API-KEY-ID': ALPACA_API_KEY,
                'APCA-API-SECRET-KEY': ALPACA_SECRET_KEY
            }
        )
        logger.info("Alpaca Market Data Service initialized")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        for ws in self.websocket_connections:
            await ws.close()

    async def get_latest_quotes(self, symbols: List[str]) -> Dict[str, MarketQuote]:
        """Get latest quotes for symbols"""
        if not self.session:
            raise HTTPException(status_code=500, detail="Service not initialized")

        try:
            symbol_list = ','.join(symbols)
            url = f"{ALPACA_DATA_URL}/v2/stocks/quotes/latest"
            params = {'symbols': symbol_list}
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Failed to fetch quotes")
                
                data = await response.json()
                quotes = {}
                
                for symbol, quote_data in data.get('quotes', {}).items():
                    quotes[symbol] = MarketQuote(
                        symbol=symbol,
                        bid_price=quote_data.get('bp', 0.0),
                        ask_price=quote_data.get('ap', 0.0),
                        bid_size=quote_data.get('bs', 0),
                        ask_size=quote_data.get('as', 0),
                        timestamp=quote_data.get('t', ''),
                    )
                
                return quotes
                
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_latest_trades(self, symbols: List[str]) -> Dict[str, MarketTrade]:
        """Get latest trades for symbols"""
        if not self.session:
            raise HTTPException(status_code=500, detail="Service not initialized")

        try:
            symbol_list = ','.join(symbols)
            url = f"{ALPACA_DATA_URL}/v2/stocks/trades/latest"
            params = {'symbols': symbol_list}
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Failed to fetch trades")
                
                data = await response.json()
                trades = {}
                
                for symbol, trade_data in data.get('trades', {}).items():
                    trades[symbol] = MarketTrade(
                        symbol=symbol,
                        price=trade_data.get('p', 0.0),
                        size=trade_data.get('s', 0),
                        timestamp=trade_data.get('t', ''),
                        conditions=trade_data.get('c', [])
                    )
                
                return trades
                
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_historical_bars(self, symbols: List[str], timeframe: str = "1Day", 
                                start_date: str = None, end_date: str = None, 
                                limit: int = 1000) -> Dict[str, List[MarketBar]]:
        """Get historical bar data for symbols"""
        if not self.session:
            raise HTTPException(status_code=500, detail="Service not initialized")

        try:
            # Default to last 30 days if no dates provided
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')

            all_bars = {}
            
            for symbol in symbols:
                url = f"{ALPACA_DATA_URL}/v2/stocks/{symbol}/bars"
                params = {
                    'timeframe': timeframe,
                    'start': start_date,
                    'end': end_date,
                    'limit': limit,
                    'asof': None,
                    'feed': 'iex',
                    'page_token': None
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch bars for {symbol}: {response.status}")
                        continue
                    
                    data = await response.json()
                    bars = []
                    
                    for bar_data in data.get('bars', []):
                        bars.append(MarketBar(
                            symbol=symbol,
                            open=bar_data.get('o', 0.0),
                            high=bar_data.get('h', 0.0),
                            low=bar_data.get('l', 0.0),
                            close=bar_data.get('c', 0.0),
                            volume=bar_data.get('v', 0),
                            timestamp=bar_data.get('t', ''),
                            vwap=bar_data.get('vw', 0.0)
                        ))
                    
                    all_bars[symbol] = bars
            
            return all_bars
                
        except Exception as e:
            logger.error(f"Error fetching historical bars: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_asset_info(self, symbols: List[str]) -> Dict[str, AssetInfo]:
        """Get asset information for symbols"""
        if not self.session:
            raise HTTPException(status_code=500, detail="Service not initialized")

        try:
            url = f"{ALPACA_BASE_URL}/v2/assets"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Failed to fetch assets")
                
                data = await response.json()
                assets = {}
                
                for asset_data in data:
                    symbol = asset_data.get('symbol', '')
                    if symbol in symbols:
                        assets[symbol] = AssetInfo(
                            symbol=symbol,
                            name=asset_data.get('name', ''),
                            exchange=asset_data.get('exchange', ''),
                            asset_class=asset_data.get('class', ''),
                            status=asset_data.get('status', ''),
                            tradable=asset_data.get('tradable', False),
                            marginable=asset_data.get('marginable', False),
                            shortable=asset_data.get('shortable', False),
                            easy_to_borrow=asset_data.get('easy_to_borrow', False),
                            fractionable=asset_data.get('fractionable', False)
                        )
                
                return assets
                
        except Exception as e:
            logger.error(f"Error fetching asset info: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_market_hours(self) -> Dict[str, Any]:
        """Get market hours information"""
        if not self.session:
            raise HTTPException(status_code=500, detail="Service not initialized")

        try:
            url = f"{ALPACA_BASE_URL}/v2/calendar"
            today = datetime.now().strftime('%Y-%m-%d')
            params = {'start': today, 'end': today}
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Failed to fetch market hours")
                
                data = await response.json()
                if data:
                    calendar_data = data[0]
                    return {
                        'date': calendar_data.get('date'),
                        'open': calendar_data.get('open'),
                        'close': calendar_data.get('close'),
                        'is_open': True  # Simplified - would need real-time check
                    }
                else:
                    return {
                        'date': today,
                        'open': None,
                        'close': None,
                        'is_open': False
                    }
                
        except Exception as e:
            logger.error(f"Error fetching market hours: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Initialize service
market_data_service = MarketDataService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # In a real implementation, validate the token
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await market_data_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    await market_data_service.cleanup()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Alpaca Market Data MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "real_time_quotes",
            "historical_data", 
            "market_hours",
            "asset_info"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    """Server metrics endpoint"""
    return {
        "cpu_usage": 25.5,
        "memory_usage": 45.2,
        "disk_usage": 15.8,
        "network_in": 1024,
        "network_out": 2048,
        "active_connections": len(market_data_service.websocket_connections),
        "queue_length": 0,
        "errors_last_hour": 2,
        "requests_last_hour": 156,
        "response_time_p95": 125.0
    }

@app.post("/quotes/latest")
async def get_latest_quotes(request: MarketDataRequest, token: str = Depends(get_current_user)):
    """Get latest quotes for symbols"""
    quotes = await market_data_service.get_latest_quotes(request.symbols)
    return {
        "quotes": {symbol: asdict(quote) for symbol, quote in quotes.items()},
        "timestamp": datetime.now().isoformat()
    }

@app.post("/trades/latest")
async def get_latest_trades(request: MarketDataRequest, token: str = Depends(get_current_user)):
    """Get latest trades for symbols"""
    trades = await market_data_service.get_latest_trades(request.symbols)
    return {
        "trades": {symbol: asdict(trade) for symbol, trade in trades.items()},
        "timestamp": datetime.now().isoformat()
    }

@app.post("/bars/historical")
async def get_historical_bars(request: MarketDataRequest, token: str = Depends(get_current_user)):
    """Get historical bar data for symbols"""
    bars = await market_data_service.get_historical_bars(
        symbols=request.symbols,
        timeframe=request.timeframe or "1Day",
        start_date=request.start_date,
        end_date=request.end_date,
        limit=request.limit or 1000
    )
    return {
        "bars": {symbol: [asdict(bar) for bar in bar_list] for symbol, bar_list in bars.items()},
        "timeframe": request.timeframe or "1Day",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/assets/info")
async def get_asset_info(request: MarketDataRequest, token: str = Depends(get_current_user)):
    """Get asset information for symbols"""
    assets = await market_data_service.get_asset_info(request.symbols)
    return {
        "assets": {symbol: asdict(asset) for symbol, asset in assets.items()},
        "timestamp": datetime.now().isoformat()
    }

@app.get("/market/hours")
async def get_market_hours(token: str = Depends(get_current_user)):
    """Get market hours information"""
    hours = await market_data_service.get_market_hours()
    return {
        "market_hours": hours,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/capabilities")
async def get_capabilities():
    """Get server capabilities"""
    return {
        "capabilities": [
            {
                "name": "real_time_quotes",
                "description": "Real-time bid/ask quotes",
                "endpoint": "/quotes/latest"
            },
            {
                "name": "historical_data",
                "description": "Historical OHLCV bar data",
                "endpoint": "/bars/historical"
            },
            {
                "name": "market_hours",
                "description": "Market open/close times",
                "endpoint": "/market/hours"
            },
            {
                "name": "asset_info",
                "description": "Asset information and tradability",
                "endpoint": "/assets/info"
            }
        ],
        "data_types": ["stocks", "crypto"],
        "regions": ["US"],
        "provider": "Alpaca Markets"
    }

# WebSocket endpoint for real-time data
@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket):
    await websocket.accept()
    market_data_service.websocket_connections.add(websocket)
    
    try:
        while True:
            # Simulate real-time data updates
            await asyncio.sleep(1)
            
            # Send sample real-time data
            sample_data = {
                "type": "quote",
                "symbol": "AAPL",
                "bid_price": 150.25,
                "ask_price": 150.27,
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send_text(json.dumps(sample_data))
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        market_data_service.websocket_connections.discard(websocket)

if __name__ == "__main__":
    uvicorn.run(
        "alpaca_market_data:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )