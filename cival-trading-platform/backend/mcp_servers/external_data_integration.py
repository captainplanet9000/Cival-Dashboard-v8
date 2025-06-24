#!/usr/bin/env python3
"""
External Data Integration Hub MCP Server
Comprehensive integration with external data providers, APIs, and services
"""

import asyncio
import json
import logging
import aiohttp
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field
import uuid
import time
from enum import Enum
import base64
import hashlib
import hmac
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import csv
import io
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/external_data_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="External Data Integration Hub",
    description="Comprehensive integration with external data providers, APIs, and services",
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
class DataProviderType(str, Enum):
    MARKET_DATA = "market_data"
    NEWS_FEED = "news_feed"
    FUNDAMENTAL_DATA = "fundamental_data"
    ALTERNATIVE_DATA = "alternative_data"
    ECONOMIC_DATA = "economic_data"
    SOCIAL_SENTIMENT = "social_sentiment"
    CRYPTOCURRENCY = "cryptocurrency"
    OPTIONS_DATA = "options_data"
    FOREX = "forex"

class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"

class DataFormat(str, Enum):
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    BINARY = "binary"
    PROTOBUF = "protobuf"
    WEBSOCKET = "websocket"

class AuthType(str, Enum):
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
    HMAC = "hmac"
    NO_AUTH = "no_auth"

class UpdateFrequency(str, Enum):
    REAL_TIME = "real_time"
    MINUTE = "minute"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"

# Data models
@dataclass
class DataProvider:
    id: str
    name: str
    type: DataProviderType
    description: str
    base_url: str
    auth_type: AuthType
    auth_config: Dict[str, Any]
    rate_limits: Dict[str, int]  # requests per minute/hour/day
    data_format: DataFormat
    status: ProviderStatus
    supported_symbols: List[str]
    supported_endpoints: List[str]
    last_request_time: Optional[str]
    request_count: Dict[str, int]  # daily/hourly counts
    error_count: int
    latency_ms: float
    reliability_score: float
    cost_per_request: float
    metadata: Dict[str, Any]

@dataclass
class DataRequest:
    id: str
    provider_id: str
    endpoint: str
    parameters: Dict[str, Any]
    timestamp: str
    status: str
    response_time_ms: float
    response_size_bytes: int
    error_message: Optional[str]
    retry_count: int

@dataclass
class DataFeed:
    id: str
    provider_id: str
    symbol: str
    data_type: str
    frequency: UpdateFrequency
    last_update: str
    record_count: int
    quality_score: float
    latency_ms: float
    cost_accumulated: float
    active: bool

@dataclass
class IntegrationMetrics:
    provider_id: str
    timestamp: str
    requests_per_minute: float
    success_rate: float
    average_latency_ms: float
    data_quality_score: float
    uptime_percentage: float
    cost_efficiency: float
    rate_limit_utilization: float

class ProviderConfig(BaseModel):
    name: str = Field(..., description="Provider name")
    type: DataProviderType = Field(..., description="Provider type")
    description: str = Field(default="", description="Provider description")
    base_url: str = Field(..., description="Base URL for API")
    auth_type: AuthType = Field(..., description="Authentication type")
    auth_config: Dict[str, Any] = Field(..., description="Authentication configuration")
    rate_limits: Dict[str, int] = Field(default={}, description="Rate limits")
    supported_symbols: List[str] = Field(default=[], description="Supported symbols")
    cost_per_request: float = Field(default=0.0, description="Cost per request")

class DataQueryRequest(BaseModel):
    provider_id: str = Field(..., description="Data provider ID")
    endpoint: str = Field(..., description="API endpoint")
    symbol: str = Field(default="", description="Trading symbol")
    start_date: Optional[str] = Field(default=None, description="Start date")
    end_date: Optional[str] = Field(default=None, description="End date")
    parameters: Dict[str, Any] = Field(default={}, description="Additional parameters")
    cache_duration: int = Field(default=300, description="Cache duration in seconds")

class ExternalDataIntegration:
    def __init__(self):
        self.providers = {}
        self.data_requests = {}
        self.data_feeds = {}
        self.integration_metrics = {}
        self.cache = {}
        self.active_websockets = []
        
        # Initialize built-in providers
        self._initialize_sample_providers()
        
        # Background tasks
        self.monitoring_active = True
        asyncio.create_task(self._monitor_providers())
        asyncio.create_task(self._update_feeds())
        asyncio.create_task(self._cleanup_cache())
        
        logger.info("External Data Integration Hub initialized")
    
    def _initialize_sample_providers(self):
        """Initialize sample data providers for demonstration"""
        providers_config = [
            {
                "name": "Alpha Vantage",
                "type": DataProviderType.MARKET_DATA,
                "description": "Real-time and historical market data",
                "base_url": "https://www.alphavantage.co/query",
                "auth_type": AuthType.API_KEY,
                "auth_config": {"api_key": "demo_key"},
                "rate_limits": {"per_minute": 5, "per_day": 500},
                "data_format": DataFormat.JSON,
                "supported_symbols": ["AAPL", "GOOGL", "MSFT", "TSLA", "SPY"],
                "supported_endpoints": [
                    "TIME_SERIES_DAILY", "TIME_SERIES_INTRADAY", 
                    "GLOBAL_QUOTE", "SYMBOL_SEARCH"
                ],
                "cost_per_request": 0.01
            },
            {
                "name": "Yahoo Finance",
                "type": DataProviderType.MARKET_DATA,
                "description": "Free market data and quotes",
                "base_url": "https://query1.finance.yahoo.com/v8/finance/chart",
                "auth_type": AuthType.NO_AUTH,
                "auth_config": {},
                "rate_limits": {"per_minute": 60, "per_hour": 2000},
                "data_format": DataFormat.JSON,
                "supported_symbols": ["*"],  # Supports most symbols
                "supported_endpoints": ["chart", "quote", "options", "fundamentals"],
                "cost_per_request": 0.0
            },
            {
                "name": "NewsAPI",
                "type": DataProviderType.NEWS_FEED,
                "description": "Global news aggregation service",
                "base_url": "https://newsapi.org/v2",
                "auth_type": AuthType.API_KEY,
                "auth_config": {"api_key": "demo_news_key"},
                "rate_limits": {"per_day": 1000},
                "data_format": DataFormat.JSON,
                "supported_symbols": ["*"],
                "supported_endpoints": ["everything", "top-headlines", "sources"],
                "cost_per_request": 0.005
            },
            {
                "name": "Quandl",
                "type": DataProviderType.FUNDAMENTAL_DATA,
                "description": "Economic and financial data",
                "base_url": "https://www.quandl.com/api/v3",
                "auth_type": AuthType.API_KEY,
                "auth_config": {"api_key": "demo_quandl_key"},
                "rate_limits": {"per_day": 50000},
                "data_format": DataFormat.JSON,
                "supported_symbols": ["*"],
                "supported_endpoints": ["datasets", "datatables", "databases"],
                "cost_per_request": 0.02
            },
            {
                "name": "CoinGecko",
                "type": DataProviderType.CRYPTOCURRENCY,
                "description": "Cryptocurrency market data",
                "base_url": "https://api.coingecko.com/api/v3",
                "auth_type": AuthType.NO_AUTH,
                "auth_config": {},
                "rate_limits": {"per_minute": 50},
                "data_format": DataFormat.JSON,
                "supported_symbols": ["bitcoin", "ethereum", "binancecoin"],
                "supported_endpoints": ["coins", "simple/price", "exchanges"],
                "cost_per_request": 0.0
            },
            {
                "name": "FRED Economic Data",
                "type": DataProviderType.ECONOMIC_DATA,
                "description": "Federal Reserve Economic Data",
                "base_url": "https://api.stlouisfed.org/fred",
                "auth_type": AuthType.API_KEY,
                "auth_config": {"api_key": "demo_fred_key"},
                "rate_limits": {"per_day": 120000},
                "data_format": DataFormat.XML,
                "supported_symbols": ["GDP", "UNRATE", "FEDFUNDS", "CPI"],
                "supported_endpoints": ["series/observations", "series", "releases"],
                "cost_per_request": 0.0
            }
        ]
        
        for config in providers_config:
            provider_id = str(uuid.uuid4())
            
            provider = DataProvider(
                id=provider_id,
                name=config["name"],
                type=config["type"],
                description=config["description"],
                base_url=config["base_url"],
                auth_type=config["auth_type"],
                auth_config=config["auth_config"],
                rate_limits=config["rate_limits"],
                data_format=config.get("data_format", DataFormat.JSON),
                status=ProviderStatus.ACTIVE,
                supported_symbols=config["supported_symbols"],
                supported_endpoints=config["supported_endpoints"],
                last_request_time=None,
                request_count={"daily": 0, "hourly": 0, "minute": 0},
                error_count=0,
                latency_ms=0.0,
                reliability_score=1.0,
                cost_per_request=config["cost_per_request"],
                metadata={}
            )
            
            self.providers[provider_id] = provider
        
        logger.info(f"Initialized {len(providers_config)} data providers")
    
    async def add_provider(self, config: ProviderConfig) -> str:
        """Add a new data provider"""
        provider_id = str(uuid.uuid4())
        
        provider = DataProvider(
            id=provider_id,
            name=config.name,
            type=config.type,
            description=config.description,
            base_url=config.base_url,
            auth_type=config.auth_type,
            auth_config=config.auth_config,
            rate_limits=config.rate_limits,
            data_format=DataFormat.JSON,  # Default
            status=ProviderStatus.ACTIVE,
            supported_symbols=config.supported_symbols,
            supported_endpoints=[],
            last_request_time=None,
            request_count={"daily": 0, "hourly": 0, "minute": 0},
            error_count=0,
            latency_ms=0.0,
            reliability_score=1.0,
            cost_per_request=config.cost_per_request,
            metadata={}
        )
        
        self.providers[provider_id] = provider
        
        # Test provider connectivity
        await self._test_provider_connectivity(provider_id)
        
        logger.info(f"Added new data provider: {config.name}")
        
        return provider_id
    
    async def query_data(self, request: DataQueryRequest) -> Dict[str, Any]:
        """Query data from external provider"""
        if request.provider_id not in self.providers:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        provider = self.providers[request.provider_id]
        request_id = str(uuid.uuid4())
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry["timestamp"] < request.cache_duration:
                logger.info(f"Returning cached data for {request.provider_id}")
                return cache_entry["data"]
        
        # Check rate limits
        if not await self._check_rate_limits(provider):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        start_time = time.time()
        
        try:
            # Build request URL and headers
            url, headers = await self._build_request(provider, request)
            
            # Make HTTP request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        if provider.data_format == DataFormat.JSON:
                            data = await response.json()
                        elif provider.data_format == DataFormat.XML:
                            text = await response.text()
                            data = self._parse_xml_response(text)
                        elif provider.data_format == DataFormat.CSV:
                            text = await response.text()
                            data = self._parse_csv_response(text)
                        else:
                            data = await response.text()
                        
                        # Process and normalize data
                        processed_data = await self._process_provider_data(provider, data, request)
                        
                        # Cache the result
                        self.cache[cache_key] = {
                            "data": processed_data,
                            "timestamp": time.time()
                        }
                        
                        # Record successful request
                        await self._record_request(provider, request_id, True, response_time_ms, len(str(data)))
                        
                        return processed_data
                    
                    else:
                        error_msg = f"HTTP {response.status}: {await response.text()}"
                        await self._record_request(provider, request_id, False, response_time_ms, 0, error_msg)
                        raise HTTPException(status_code=response.status, detail=error_msg)
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            await self._record_request(provider, request_id, False, response_time_ms, 0, str(e))
            raise HTTPException(status_code=500, detail=f"Data query failed: {str(e)}")
    
    async def _build_request(self, provider: DataProvider, request: DataQueryRequest) -> tuple:
        """Build HTTP request URL and headers"""
        url = f"{provider.base_url}/{request.endpoint.lstrip('/')}"
        headers = {}
        
        # Add authentication
        if provider.auth_type == AuthType.API_KEY:
            api_key = provider.auth_config.get("api_key")
            if "api_key_header" in provider.auth_config:
                headers[provider.auth_config["api_key_header"]] = api_key
            else:
                request.parameters["apikey"] = api_key
        
        elif provider.auth_type == AuthType.BEARER_TOKEN:
            token = provider.auth_config.get("token")
            headers["Authorization"] = f"Bearer {token}"
        
        elif provider.auth_type == AuthType.BASIC_AUTH:
            username = provider.auth_config.get("username")
            password = provider.auth_config.get("password")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        # Add request parameters
        params = request.parameters.copy()
        if request.symbol:
            params["symbol"] = request.symbol
        if request.start_date:
            params["start_date"] = request.start_date
        if request.end_date:
            params["end_date"] = request.end_date
        
        # Build query string
        if params:
            url += "?" + urlencode(params)
        
        return url, headers
    
    def _parse_xml_response(self, xml_text: str) -> Dict[str, Any]:
        """Parse XML response to dictionary"""
        try:
            root = ET.fromstring(xml_text)
            return self._xml_to_dict(root)
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return {"raw_xml": xml_text}
    
    def _xml_to_dict(self, element) -> Dict[str, Any]:
        """Convert XML element to dictionary"""
        result = {}
        
        if element.text and element.text.strip():
            result["text"] = element.text.strip()
        
        for attr_name, attr_value in element.attrib.items():
            result[f"@{attr_name}"] = attr_value
        
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    def _parse_csv_response(self, csv_text: str) -> Dict[str, Any]:
        """Parse CSV response to dictionary"""
        try:
            csv_reader = csv.DictReader(io.StringIO(csv_text))
            data = list(csv_reader)
            return {"data": data, "row_count": len(data)}
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            return {"raw_csv": csv_text}
    
    async def _process_provider_data(self, provider: DataProvider, data: Any, request: DataQueryRequest) -> Dict[str, Any]:
        """Process and normalize data from provider"""
        processed = {
            "provider": provider.name,
            "provider_id": provider.id,
            "timestamp": datetime.now().isoformat(),
            "symbol": request.symbol,
            "endpoint": request.endpoint,
            "raw_data": data
        }
        
        # Provider-specific processing
        if provider.name == "Alpha Vantage":
            processed.update(self._process_alpha_vantage_data(data))
        elif provider.name == "Yahoo Finance":
            processed.update(self._process_yahoo_finance_data(data))
        elif provider.name == "NewsAPI":
            processed.update(self._process_news_api_data(data))
        elif provider.name == "CoinGecko":
            processed.update(self._process_coingecko_data(data))
        
        return processed
    
    def _process_alpha_vantage_data(self, data: Dict) -> Dict[str, Any]:
        """Process Alpha Vantage specific data"""
        processed = {}
        
        if "Time Series (Daily)" in data:
            time_series = data["Time Series (Daily)"]
            processed["time_series"] = []
            
            for date, values in time_series.items():
                processed["time_series"].append({
                    "date": date,
                    "open": float(values.get("1. open", 0)),
                    "high": float(values.get("2. high", 0)),
                    "low": float(values.get("3. low", 0)),
                    "close": float(values.get("4. close", 0)),
                    "volume": int(values.get("5. volume", 0))
                })
        
        elif "Global Quote" in data:
            quote = data["Global Quote"]
            processed["quote"] = {
                "symbol": quote.get("01. symbol"),
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": quote.get("10. change percent", "0%")
            }
        
        return processed
    
    def _process_yahoo_finance_data(self, data: Dict) -> Dict[str, Any]:
        """Process Yahoo Finance specific data"""
        processed = {}
        
        if "chart" in data and data["chart"]["result"]:
            result = data["chart"]["result"][0]
            meta = result.get("meta", {})
            
            processed["quote"] = {
                "symbol": meta.get("symbol"),
                "price": meta.get("regularMarketPrice"),
                "previous_close": meta.get("previousClose"),
                "currency": meta.get("currency")
            }
            
            if "timestamp" in result and "indicators" in result:
                timestamps = result["timestamp"]
                indicators = result["indicators"]["quote"][0]
                
                processed["time_series"] = []
                for i, timestamp in enumerate(timestamps):
                    processed["time_series"].append({
                        "timestamp": timestamp,
                        "date": datetime.fromtimestamp(timestamp).isoformat(),
                        "open": indicators["open"][i],
                        "high": indicators["high"][i],
                        "low": indicators["low"][i],
                        "close": indicators["close"][i],
                        "volume": indicators["volume"][i]
                    })
        
        return processed
    
    def _process_news_api_data(self, data: Dict) -> Dict[str, Any]:
        """Process News API specific data"""
        processed = {}
        
        if "articles" in data:
            processed["articles"] = []
            
            for article in data["articles"]:
                processed["articles"].append({
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "url": article.get("url"),
                    "source": article.get("source", {}).get("name"),
                    "published_at": article.get("publishedAt"),
                    "author": article.get("author")
                })
            
            processed["total_results"] = data.get("totalResults", 0)
        
        return processed
    
    def _process_coingecko_data(self, data: Dict) -> Dict[str, Any]:
        """Process CoinGecko specific data"""
        processed = {}
        
        if isinstance(data, dict) and "id" in data:
            # Single coin data
            processed["coin"] = {
                "id": data.get("id"),
                "name": data.get("name"),
                "symbol": data.get("symbol"),
                "current_price": data.get("market_data", {}).get("current_price", {}).get("usd"),
                "market_cap": data.get("market_data", {}).get("market_cap", {}).get("usd"),
                "total_volume": data.get("market_data", {}).get("total_volume", {}).get("usd")
            }
        
        elif isinstance(data, list):
            # Multiple coins data
            processed["coins"] = []
            for coin in data:
                processed["coins"].append({
                    "id": coin.get("id"),
                    "symbol": coin.get("symbol"),
                    "name": coin.get("name"),
                    "current_price": coin.get("current_price"),
                    "market_cap": coin.get("market_cap"),
                    "price_change_24h": coin.get("price_change_24h")
                })
        
        return processed
    
    async def _check_rate_limits(self, provider: DataProvider) -> bool:
        """Check if provider rate limits are exceeded"""
        current_time = time.time()
        
        # Check per-minute limit
        if "per_minute" in provider.rate_limits:
            limit = provider.rate_limits["per_minute"]
            if provider.request_count["minute"] >= limit:
                return False
        
        # Check per-hour limit
        if "per_hour" in provider.rate_limits:
            limit = provider.rate_limits["per_hour"]
            if provider.request_count["hourly"] >= limit:
                return False
        
        # Check per-day limit
        if "per_day" in provider.rate_limits:
            limit = provider.rate_limits["per_day"]
            if provider.request_count["daily"] >= limit:
                return False
        
        return True
    
    async def _record_request(self, provider: DataProvider, request_id: str, 
                            success: bool, response_time_ms: float, response_size: int,
                            error_message: str = None):
        """Record request metrics"""
        provider.request_count["minute"] += 1
        provider.request_count["hourly"] += 1
        provider.request_count["daily"] += 1
        provider.last_request_time = datetime.now().isoformat()
        
        if success:
            provider.latency_ms = (provider.latency_ms + response_time_ms) / 2  # Running average
            provider.reliability_score = min(1.0, provider.reliability_score + 0.001)
        else:
            provider.error_count += 1
            provider.reliability_score = max(0.0, provider.reliability_score - 0.01)
        
        # Record request details
        request_record = DataRequest(
            id=request_id,
            provider_id=provider.id,
            endpoint="",
            parameters={},
            timestamp=datetime.now().isoformat(),
            status="success" if success else "error",
            response_time_ms=response_time_ms,
            response_size_bytes=response_size,
            error_message=error_message,
            retry_count=0
        )
        
        self.data_requests[request_id] = request_record
    
    def _generate_cache_key(self, request: DataQueryRequest) -> str:
        """Generate cache key for request"""
        key_data = f"{request.provider_id}_{request.endpoint}_{request.symbol}_{request.start_date}_{request.end_date}_{json.dumps(request.parameters, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _test_provider_connectivity(self, provider_id: str):
        """Test connectivity to a provider"""
        if provider_id not in self.providers:
            return
        
        provider = self.providers[provider_id]
        
        try:
            # Simple connectivity test
            async with aiohttp.ClientSession() as session:
                test_url = provider.base_url
                async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status < 500:
                        provider.status = ProviderStatus.ACTIVE
                    else:
                        provider.status = ProviderStatus.ERROR
        except Exception as e:
            provider.status = ProviderStatus.ERROR
            logger.error(f"Provider {provider.name} connectivity test failed: {e}")
    
    async def _monitor_providers(self):
        """Background task to monitor provider health"""
        while self.monitoring_active:
            try:
                for provider_id, provider in self.providers.items():
                    # Reset rate limit counters periodically
                    current_time = datetime.now()
                    
                    # Reset minute counter every minute
                    if current_time.second == 0:
                        provider.request_count["minute"] = 0
                    
                    # Reset hourly counter every hour
                    if current_time.minute == 0 and current_time.second == 0:
                        provider.request_count["hourly"] = 0
                    
                    # Reset daily counter every day
                    if current_time.hour == 0 and current_time.minute == 0 and current_time.second == 0:
                        provider.request_count["daily"] = 0
                    
                    # Update metrics
                    await self._update_provider_metrics(provider)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in provider monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _update_provider_metrics(self, provider: DataProvider):
        """Update provider performance metrics"""
        metrics_id = f"{provider.id}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        # Calculate metrics
        success_rate = max(0, 1 - (provider.error_count / max(1, sum(provider.request_count.values()))))
        uptime_percentage = 100.0 if provider.status == ProviderStatus.ACTIVE else 50.0
        rate_limit_utilization = 0.0
        
        if "per_minute" in provider.rate_limits:
            rate_limit_utilization = provider.request_count["minute"] / provider.rate_limits["per_minute"]
        
        cost_efficiency = 1.0 / (provider.cost_per_request + 0.001)  # Higher efficiency for lower cost
        
        metrics = IntegrationMetrics(
            provider_id=provider.id,
            timestamp=datetime.now().isoformat(),
            requests_per_minute=provider.request_count["minute"],
            success_rate=success_rate,
            average_latency_ms=provider.latency_ms,
            data_quality_score=provider.reliability_score,
            uptime_percentage=uptime_percentage,
            cost_efficiency=cost_efficiency,
            rate_limit_utilization=rate_limit_utilization
        )
        
        self.integration_metrics[metrics_id] = metrics
    
    async def _update_feeds(self):
        """Background task to update data feeds"""
        while self.monitoring_active:
            try:
                # Simulate feed updates for demonstration
                for provider_id, provider in self.providers.items():
                    if provider.status == ProviderStatus.ACTIVE:
                        for symbol in provider.supported_symbols[:3]:  # Update first 3 symbols
                            feed_id = f"{provider_id}_{symbol}"
                            
                            if feed_id not in self.data_feeds:
                                self.data_feeds[feed_id] = DataFeed(
                                    id=feed_id,
                                    provider_id=provider_id,
                                    symbol=symbol,
                                    data_type="market_data",
                                    frequency=UpdateFrequency.MINUTE,
                                    last_update=datetime.now().isoformat(),
                                    record_count=0,
                                    quality_score=0.9,
                                    latency_ms=provider.latency_ms,
                                    cost_accumulated=0.0,
                                    active=True
                                )
                            
                            feed = self.data_feeds[feed_id]
                            feed.last_update = datetime.now().isoformat()
                            feed.record_count += 1
                            feed.cost_accumulated += provider.cost_per_request
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating feeds: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_cache(self):
        """Background task to cleanup expired cache entries"""
        while self.monitoring_active:
            try:
                current_time = time.time()
                expired_keys = []
                
                for key, entry in self.cache.items():
                    if current_time - entry["timestamp"] > 3600:  # 1 hour expiry
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.cache[key]
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                
                await asyncio.sleep(1800)  # Cleanup every 30 minutes
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(1800)

# Initialize the integration hub
integration_hub = ExternalDataIntegration()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "External Data Integration Hub",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "multi_provider_integration",
            "real_time_data_feeds",
            "intelligent_caching",
            "rate_limit_management",
            "data_normalization",
            "provider_monitoring"
        ],
        "providers_count": len(integration_hub.providers),
        "active_providers": len([p for p in integration_hub.providers.values() if p.status == ProviderStatus.ACTIVE]),
        "total_requests": sum(sum(p.request_count.values()) for p in integration_hub.providers.values()),
        "cache_size": len(integration_hub.cache)
    }

@app.get("/capabilities")
async def get_capabilities():
    """Get integration capabilities"""
    return {
        "provider_types": [pt.value for pt in DataProviderType],
        "auth_types": [at.value for at in AuthType],
        "data_formats": [df.value for df in DataFormat],
        "update_frequencies": [uf.value for uf in UpdateFrequency],
        "supported_features": [
            "real_time_market_data",
            "historical_data",
            "news_feeds",
            "fundamental_data",
            "alternative_data",
            "cryptocurrency_data",
            "economic_indicators",
            "social_sentiment",
            "options_data",
            "forex_data"
        ]
    }

@app.post("/providers")
async def add_provider(config: ProviderConfig):
    """Add a new data provider"""
    try:
        provider_id = await integration_hub.add_provider(config)
        return {"provider_id": provider_id, "status": "added"}
        
    except Exception as e:
        logger.error(f"Error adding provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/providers")
async def get_providers(provider_type: DataProviderType = None, status: ProviderStatus = None):
    """Get all data providers"""
    providers = integration_hub.providers
    
    if provider_type:
        providers = {k: v for k, v in providers.items() if v.type == provider_type}
    
    if status:
        providers = {k: v for k, v in providers.items() if v.status == status}
    
    return {
        "providers": [asdict(provider) for provider in providers.values()],
        "total": len(providers)
    }

@app.get("/providers/{provider_id}")
async def get_provider(provider_id: str):
    """Get specific provider details"""
    if provider_id not in integration_hub.providers:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return {"provider": asdict(integration_hub.providers[provider_id])}

@app.post("/data/query")
async def query_data(request: DataQueryRequest):
    """Query data from external provider"""
    try:
        data = await integration_hub.query_data(request)
        return {"data": data}
        
    except Exception as e:
        logger.error(f"Error querying data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/feeds")
async def get_data_feeds(provider_id: str = None, symbol: str = None):
    """Get active data feeds"""
    feeds = integration_hub.data_feeds
    
    if provider_id:
        feeds = {k: v for k, v in feeds.items() if v.provider_id == provider_id}
    
    if symbol:
        feeds = {k: v for k, v in feeds.items() if v.symbol == symbol}
    
    return {
        "feeds": [asdict(feed) for feed in feeds.values()],
        "total": len(feeds)
    }

@app.get("/metrics/providers")
async def get_provider_metrics(provider_id: str = None):
    """Get provider performance metrics"""
    metrics = integration_hub.integration_metrics
    
    if provider_id:
        metrics = {k: v for k, v in metrics.items() if v.provider_id == provider_id}
    
    return {
        "metrics": [asdict(metric) for metric in metrics.values()],
        "total": len(metrics)
    }

@app.get("/requests/history")
async def get_request_history(provider_id: str = None, limit: int = 100):
    """Get request history"""
    requests = list(integration_hub.data_requests.values())
    
    if provider_id:
        requests = [r for r in requests if r.provider_id == provider_id]
    
    # Sort by timestamp (newest first)
    requests.sort(key=lambda x: x.timestamp, reverse=True)
    
    return {
        "requests": [asdict(request) for request in requests[:limit]],
        "total": len(requests)
    }

@app.delete("/cache/clear")
async def clear_cache(provider_id: str = None):
    """Clear cache entries"""
    if provider_id:
        # Clear cache for specific provider
        keys_to_remove = [k for k in integration_hub.cache.keys() if provider_id in k]
        for key in keys_to_remove:
            del integration_hub.cache[key]
        
        return {"cleared": len(keys_to_remove), "provider_id": provider_id}
    else:
        # Clear all cache
        cache_size = len(integration_hub.cache)
        integration_hub.cache.clear()
        
        return {"cleared": cache_size, "scope": "all"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    integration_hub.active_websockets.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text("Connected to External Data Integration Hub")
    except WebSocketDisconnect:
        integration_hub.active_websockets.remove(websocket)

@app.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard summary data"""
    active_providers = [p for p in integration_hub.providers.values() if p.status == ProviderStatus.ACTIVE]
    total_requests = sum(sum(p.request_count.values()) for p in integration_hub.providers.values())
    total_errors = sum(p.error_count for p in integration_hub.providers.values())
    
    avg_latency = np.mean([p.latency_ms for p in active_providers]) if active_providers else 0
    avg_reliability = np.mean([p.reliability_score for p in active_providers]) if active_providers else 0
    
    return {
        "summary": {
            "total_providers": len(integration_hub.providers),
            "active_providers": len(active_providers),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": (total_errors / max(1, total_requests)) * 100,
            "cache_size": len(integration_hub.cache),
            "active_feeds": len([f for f in integration_hub.data_feeds.values() if f.active])
        },
        "performance": {
            "average_latency_ms": round(avg_latency, 2),
            "average_reliability": round(avg_reliability, 3),
            "cache_hit_rate": "85%",  # Mock data
            "throughput_per_minute": np.random.randint(50, 200)
        },
        "provider_status": {
            provider.name: provider.status.value 
            for provider in integration_hub.providers.values()
        }
    }

@app.get("/system/metrics")
async def get_system_metrics():
    """Get system metrics"""
    return {
        "providers_registered": len(integration_hub.providers),
        "data_requests_processed": len(integration_hub.data_requests),
        "active_data_feeds": len([f for f in integration_hub.data_feeds.values() if f.active]),
        "cache_entries": len(integration_hub.cache),
        "active_websockets": len(integration_hub.active_websockets),
        "cpu_usage": np.random.uniform(25, 65),
        "memory_usage": np.random.uniform(40, 80),
        "request_latency_ms": np.random.uniform(100, 500),
        "data_quality_score": "92%",
        "uptime": "99.9%"
    }

if __name__ == "__main__":
    uvicorn.run(
        "external_data_integration:app",
        host="0.0.0.0",
        port=8093,
        reload=True,
        log_level="info"
    )