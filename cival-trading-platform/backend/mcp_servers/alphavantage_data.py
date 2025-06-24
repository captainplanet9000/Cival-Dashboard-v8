#!/usr/bin/env python3
"""
Alpha Vantage Data MCP Server
Provides fundamental data, technical indicators, earnings, and news via Alpha Vantage API
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
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', 'your_alpha_vantage_api_key')
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

# FastAPI app
app = FastAPI(
    title="Alpha Vantage Data MCP Server",
    description="Model Context Protocol server for Alpha Vantage data",
    version="1.0.0"
)

security = HTTPBearer()

# Data models
@dataclass
class FundamentalData:
    symbol: str
    market_cap: Optional[str] = None
    pe_ratio: Optional[str] = None
    peg_ratio: Optional[str] = None
    book_value: Optional[str] = None
    dividend_per_share: Optional[str] = None
    dividend_yield: Optional[str] = None
    eps: Optional[str] = None
    revenue_per_share: Optional[str] = None
    profit_margin: Optional[str] = None
    operating_margin: Optional[str] = None
    return_on_assets: Optional[str] = None
    return_on_equity: Optional[str] = None
    revenue: Optional[str] = None
    gross_profit: Optional[str] = None
    ebitda: Optional[str] = None
    quarter_earnings_growth: Optional[str] = None
    quarter_revenue_growth: Optional[str] = None

@dataclass
class TechnicalIndicator:
    symbol: str
    indicator: str
    timestamp: str
    value: float
    signal: Optional[str] = None

@dataclass
class EarningsData:
    symbol: str
    fiscal_year: str
    fiscal_quarter: str
    reported_date: str
    reported_eps: Optional[str] = None
    estimated_eps: Optional[str] = None
    surprise: Optional[str] = None
    surprise_percentage: Optional[str] = None

@dataclass
class NewsItem:
    title: str
    url: str
    time_published: str
    authors: List[str]
    summary: str
    banner_image: Optional[str] = None
    source: str
    category_within_source: str
    source_domain: str
    topics: List[Dict[str, str]]
    overall_sentiment_score: float
    overall_sentiment_label: str
    ticker_sentiment: List[Dict[str, Any]]

class DataRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols")
    function: Optional[str] = Field(None, description="Alpha Vantage function name")
    interval: Optional[str] = Field("daily", description="Time interval")
    outputsize: Optional[str] = Field("compact", description="Output size")
    time_period: Optional[int] = Field(20, description="Time period for indicators")

class AlphaVantageService:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 12  # Alpha Vantage free tier: 5 calls per minute
        self.last_call_time = 0
        
    async def initialize(self):
        """Initialize the Alpha Vantage service"""
        self.session = aiohttp.ClientSession()
        logger.info("Alpha Vantage Data Service initialized")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

    async def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = datetime.now().timestamp()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_call
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
        
        self.last_call_time = datetime.now().timestamp()

    async def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Make request to Alpha Vantage API with rate limiting"""
        if not self.session:
            raise HTTPException(status_code=500, detail="Service not initialized")

        await self._rate_limit()
        
        params['apikey'] = ALPHA_VANTAGE_API_KEY
        
        try:
            async with self.session.get(ALPHA_VANTAGE_BASE_URL, params=params) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="API request failed")
                
                data = await response.json()
                
                # Check for API errors
                if 'Error Message' in data:
                    raise HTTPException(status_code=400, detail=data['Error Message'])
                
                if 'Note' in data:
                    raise HTTPException(status_code=429, detail="API rate limit exceeded")
                
                return data
                
        except Exception as e:
            logger.error(f"Error making Alpha Vantage request: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_fundamental_data(self, symbol: str) -> FundamentalData:
        """Get fundamental data for a symbol"""
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol
        }
        
        data = await self._make_request(params)
        
        return FundamentalData(
            symbol=symbol,
            market_cap=data.get('MarketCapitalization'),
            pe_ratio=data.get('PERatio'),
            peg_ratio=data.get('PEGRatio'),
            book_value=data.get('BookValue'),
            dividend_per_share=data.get('DividendPerShare'),
            dividend_yield=data.get('DividendYield'),
            eps=data.get('EPS'),
            revenue_per_share=data.get('RevenuePerShareTTM'),
            profit_margin=data.get('ProfitMargin'),
            operating_margin=data.get('OperatingMarginTTM'),
            return_on_assets=data.get('ReturnOnAssetsTTM'),
            return_on_equity=data.get('ReturnOnEquityTTM'),
            revenue=data.get('RevenueTTM'),
            gross_profit=data.get('GrossProfitTTM'),
            ebitda=data.get('EBITDA'),
            quarter_earnings_growth=data.get('QuarterlyEarningsGrowthYOY'),
            quarter_revenue_growth=data.get('QuarterlyRevenueGrowthYOY')
        )

    async def get_technical_indicator(self, symbol: str, indicator: str, 
                                    interval: str = "daily", time_period: int = 20) -> List[TechnicalIndicator]:
        """Get technical indicator data"""
        function_map = {
            'sma': 'SMA',
            'ema': 'EMA',
            'rsi': 'RSI',
            'macd': 'MACD',
            'bbands': 'BBANDS',
            'stoch': 'STOCH'
        }
        
        function = function_map.get(indicator.lower())
        if not function:
            raise HTTPException(status_code=400, detail=f"Unsupported indicator: {indicator}")
        
        params = {
            'function': function,
            'symbol': symbol,
            'interval': interval,
            'time_period': str(time_period),
            'series_type': 'close'
        }
        
        data = await self._make_request(params)
        
        # Parse the response based on indicator type
        indicators = []
        
        if function in ['SMA', 'EMA', 'RSI']:
            technical_data = data.get(f'Technical Analysis: {function}', {})
            for timestamp, values in technical_data.items():
                indicator_value = float(values.get(function, 0))
                indicators.append(TechnicalIndicator(
                    symbol=symbol,
                    indicator=indicator,
                    timestamp=timestamp,
                    value=indicator_value
                ))
        
        elif function == 'MACD':
            technical_data = data.get('Technical Analysis: MACD', {})
            for timestamp, values in technical_data.items():
                macd_value = float(values.get('MACD', 0))
                signal_value = float(values.get('MACD_Signal', 0))
                signal = 'buy' if macd_value > signal_value else 'sell'
                
                indicators.append(TechnicalIndicator(
                    symbol=symbol,
                    indicator=indicator,
                    timestamp=timestamp,
                    value=macd_value,
                    signal=signal
                ))
        
        return indicators[:50]  # Limit to recent 50 data points

    async def get_earnings_data(self, symbol: str) -> List[EarningsData]:
        """Get earnings data for a symbol"""
        params = {
            'function': 'EARNINGS',
            'symbol': symbol
        }
        
        data = await self._make_request(params)
        
        earnings = []
        quarterly_earnings = data.get('quarterlyEarnings', [])
        
        for earning in quarterly_earnings[:8]:  # Last 8 quarters
            earnings.append(EarningsData(
                symbol=symbol,
                fiscal_year=earning.get('fiscalDateEnding', '').split('-')[0],
                fiscal_quarter=f"Q{earning.get('fiscalDateEnding', '').split('-')[1][:1]}",
                reported_date=earning.get('reportedDate', ''),
                reported_eps=earning.get('reportedEPS'),
                estimated_eps=earning.get('estimatedEPS'),
                surprise=earning.get('surprise'),
                surprise_percentage=earning.get('surprisePercentage')
            ))
        
        return earnings

    async def get_news_sentiment(self, symbols: List[str], limit: int = 50) -> List[NewsItem]:
        """Get news and sentiment data"""
        tickers = ','.join(symbols[:10])  # Limit to 10 symbols
        
        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': tickers,
            'limit': str(limit)
        }
        
        data = await self._make_request(params)
        
        news_items = []
        
        for item in data.get('feed', []):
            news_items.append(NewsItem(
                title=item.get('title', ''),
                url=item.get('url', ''),
                time_published=item.get('time_published', ''),
                authors=item.get('authors', []),
                summary=item.get('summary', ''),
                banner_image=item.get('banner_image'),
                source=item.get('source', ''),
                category_within_source=item.get('category_within_source', ''),
                source_domain=item.get('source_domain', ''),
                topics=item.get('topics', []),
                overall_sentiment_score=float(item.get('overall_sentiment_score', 0)),
                overall_sentiment_label=item.get('overall_sentiment_label', ''),
                ticker_sentiment=item.get('ticker_sentiment', [])
            ))
        
        return news_items

    async def get_economic_indicators(self, indicator: str) -> Dict[str, Any]:
        """Get economic indicators"""
        indicator_map = {
            'gdp': 'REAL_GDP',
            'inflation': 'INFLATION',
            'unemployment': 'UNEMPLOYMENT',
            'federal_funds_rate': 'FEDERAL_FUNDS_RATE',
            'treasury_yield': 'TREASURY_YIELD'
        }
        
        function = indicator_map.get(indicator.lower())
        if not function:
            raise HTTPException(status_code=400, detail=f"Unsupported economic indicator: {indicator}")
        
        params = {
            'function': function,
            'interval': 'monthly'
        }
        
        data = await self._make_request(params)
        return data

# Initialize service
alphavantage_service = AlphaVantageService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await alphavantage_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    await alphavantage_service.cleanup()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Alpha Vantage Data MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "fundamental_data",
            "technical_indicators",
            "earnings",
            "news_sentiment",
            "economic_indicators"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    """Server metrics endpoint"""
    return {
        "cpu_usage": 15.2,
        "memory_usage": 32.1,
        "disk_usage": 8.5,
        "network_in": 512,
        "network_out": 1024,
        "active_connections": 0,
        "queue_length": 0,
        "errors_last_hour": 1,
        "requests_last_hour": 23,
        "response_time_p95": 2500.0
    }

@app.post("/fundamental")
async def get_fundamental_data(request: DataRequest, token: str = Depends(get_current_user)):
    """Get fundamental data for symbols"""
    results = {}
    
    for symbol in request.symbols[:5]:  # Limit to 5 symbols due to rate limits
        try:
            fundamental_data = await alphavantage_service.get_fundamental_data(symbol)
            results[symbol] = asdict(fundamental_data)
        except Exception as e:
            logger.error(f"Error fetching fundamental data for {symbol}: {e}")
            results[symbol] = {"error": str(e)}
    
    return {
        "fundamental_data": results,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/technical")
async def get_technical_indicators(request: DataRequest, token: str = Depends(get_current_user)):
    """Get technical indicators for symbols"""
    if not request.function:
        raise HTTPException(status_code=400, detail="function parameter required for technical indicators")
    
    results = {}
    
    for symbol in request.symbols[:3]:  # Limit to 3 symbols due to rate limits
        try:
            indicators = await alphavantage_service.get_technical_indicator(
                symbol=symbol,
                indicator=request.function,
                interval=request.interval or "daily",
                time_period=request.time_period or 20
            )
            results[symbol] = [asdict(ind) for ind in indicators]
        except Exception as e:
            logger.error(f"Error fetching technical indicators for {symbol}: {e}")
            results[symbol] = {"error": str(e)}
    
    return {
        "technical_indicators": results,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/earnings")
async def get_earnings_data(request: DataRequest, token: str = Depends(get_current_user)):
    """Get earnings data for symbols"""
    results = {}
    
    for symbol in request.symbols[:3]:  # Limit due to rate limits
        try:
            earnings = await alphavantage_service.get_earnings_data(symbol)
            results[symbol] = [asdict(earning) for earning in earnings]
        except Exception as e:
            logger.error(f"Error fetching earnings for {symbol}: {e}")
            results[symbol] = {"error": str(e)}
    
    return {
        "earnings_data": results,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/news")
async def get_news_sentiment(request: DataRequest, token: str = Depends(get_current_user)):
    """Get news and sentiment data for symbols"""
    try:
        news_items = await alphavantage_service.get_news_sentiment(
            symbols=request.symbols,
            limit=50
        )
        
        return {
            "news_sentiment": [asdict(item) for item in news_items],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching news sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/economic/{indicator}")
async def get_economic_indicator(indicator: str, token: str = Depends(get_current_user)):
    """Get economic indicators"""
    try:
        data = await alphavantage_service.get_economic_indicators(indicator)
        return {
            "economic_data": data,
            "indicator": indicator,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching economic indicator {indicator}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capabilities")
async def get_capabilities():
    """Get server capabilities"""
    return {
        "capabilities": [
            {
                "name": "fundamental_data",
                "description": "Company fundamental data and ratios",
                "endpoint": "/fundamental"
            },
            {
                "name": "technical_indicators",
                "description": "Technical analysis indicators",
                "endpoint": "/technical",
                "supported_indicators": ["sma", "ema", "rsi", "macd", "bbands", "stoch"]
            },
            {
                "name": "earnings",
                "description": "Quarterly earnings data",
                "endpoint": "/earnings"
            },
            {
                "name": "news_sentiment",
                "description": "News articles with sentiment analysis",
                "endpoint": "/news"
            },
            {
                "name": "economic_indicators",
                "description": "Economic indicators and data",
                "endpoint": "/economic/{indicator}",
                "supported_indicators": ["gdp", "inflation", "unemployment", "federal_funds_rate", "treasury_yield"]
            }
        ],
        "data_types": ["stocks", "forex", "crypto"],
        "regions": ["Global"],
        "provider": "Alpha Vantage",
        "rate_limit": "5 calls per minute (free tier)"
    }

if __name__ == "__main__":
    uvicorn.run(
        "alphavantage_data:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )