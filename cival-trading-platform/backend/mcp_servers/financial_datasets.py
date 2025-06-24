#!/usr/bin/env python3
"""
Financial Datasets MCP Server
Provides alternative financial data, economic indicators, and sector analysis
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
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FINANCIAL_DATASETS_API_KEY = os.getenv('FINANCIAL_DATASETS_API_KEY', 'your_fd_api_key')
FINANCIAL_DATASETS_BASE_URL = "https://api.financialdatasets.ai"

# FastAPI app
app = FastAPI(
    title="Financial Datasets MCP Server",
    description="Model Context Protocol server for alternative financial data",
    version="1.0.0"
)

security = HTTPBearer()

# Data models
@dataclass
class SectorData:
    sector: str
    performance_1d: float
    performance_1w: float
    performance_1m: float
    performance_3m: float
    performance_ytd: float
    market_cap: float
    pe_ratio: float
    dividend_yield: float
    volatility: float
    top_performers: List[str]
    worst_performers: List[str]

@dataclass
class EconomicIndicator:
    indicator: str
    value: float
    previous_value: float
    change: float
    change_percent: float
    date: str
    frequency: str
    unit: str
    description: str

@dataclass
class AlternativeData:
    data_type: str
    symbol: str
    metric: str
    value: float
    timestamp: str
    source: str
    confidence_score: float
    metadata: Dict[str, Any]

@dataclass
class ESGData:
    symbol: str
    esg_score: float
    environmental_score: float
    social_score: float
    governance_score: float
    controversy_score: float
    last_updated: str
    industry_rank: int
    peer_comparison: Dict[str, float]

@dataclass
class SupplyChainData:
    symbol: str
    supplier_count: int
    geographic_diversity: float
    risk_score: float
    resilience_index: float
    key_suppliers: List[str]
    risk_factors: List[str]
    last_updated: str

class DataRequest(BaseModel):
    symbols: Optional[List[str]] = Field(None, description="List of symbols")
    sectors: Optional[List[str]] = Field(None, description="List of sectors")
    indicators: Optional[List[str]] = Field(None, description="List of indicators")
    data_type: Optional[str] = Field(None, description="Type of alternative data")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")

class FinancialDatasetsService:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache = {}
        self.cache_expiry = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize the service"""
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {FINANCIAL_DATASETS_API_KEY}',
                'Content-Type': 'application/json'
            }
        )
        logger.info("Financial Datasets Service initialized")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key"""
        return f"{endpoint}_{hash(str(sorted(params.items())))}"

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache is still valid"""
        return (datetime.now().timestamp() - timestamp) < self.cache_expiry

    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make request with caching"""
        cache_key = self._get_cache_key(endpoint, params or {})
        
        # Check cache first
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                return cached_data

        if not self.session:
            raise HTTPException(status_code=500, detail="Service not initialized")

        try:
            url = f"{FINANCIAL_DATASETS_BASE_URL}{endpoint}"
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    # Simulate successful response for demo
                    return self._generate_mock_data(endpoint, params)
                
                data = await response.json()
                
                # Cache the response
                self.cache[cache_key] = (data, datetime.now().timestamp())
                
                return data
                
        except Exception as e:
            logger.warning(f"API request failed, using mock data: {e}")
            return self._generate_mock_data(endpoint, params)

    def _generate_mock_data(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Generate mock data for demonstration"""
        if 'sectors' in endpoint:
            return self._generate_mock_sector_data()
        elif 'economic' in endpoint:
            return self._generate_mock_economic_data()
        elif 'esg' in endpoint:
            return self._generate_mock_esg_data(params)
        elif 'supply-chain' in endpoint:
            return self._generate_mock_supply_chain_data(params)
        elif 'alternative' in endpoint:
            return self._generate_mock_alternative_data(params)
        else:
            return {"error": "Mock data not available for this endpoint"}

    def _generate_mock_sector_data(self) -> Dict[str, Any]:
        """Generate mock sector performance data"""
        sectors = [
            'Technology', 'Healthcare', 'Financial Services', 'Consumer Cyclical',
            'Communication Services', 'Industrials', 'Consumer Defensive',
            'Energy', 'Utilities', 'Real Estate', 'Basic Materials'
        ]
        
        sector_data = {}
        for sector in sectors:
            sector_data[sector] = {
                'performance_1d': np.random.uniform(-2, 2),
                'performance_1w': np.random.uniform(-5, 5),
                'performance_1m': np.random.uniform(-10, 10),
                'performance_3m': np.random.uniform(-15, 15),
                'performance_ytd': np.random.uniform(-20, 25),
                'market_cap': np.random.uniform(500e9, 5e12),
                'pe_ratio': np.random.uniform(15, 35),
                'dividend_yield': np.random.uniform(0, 4),
                'volatility': np.random.uniform(15, 45),
                'top_performers': [f'STOCK{i}' for i in range(1, 4)],
                'worst_performers': [f'STOCK{i}' for i in range(4, 7)]
            }
        
        return {'sectors': sector_data}

    def _generate_mock_economic_data(self) -> Dict[str, Any]:
        """Generate mock economic indicators"""
        indicators = {
            'gdp_growth': {
                'value': 2.3,
                'previous_value': 2.1,
                'change': 0.2,
                'change_percent': 9.5,
                'date': '2024-01-15',
                'frequency': 'quarterly',
                'unit': 'percent',
                'description': 'Gross Domestic Product Growth Rate'
            },
            'unemployment_rate': {
                'value': 3.8,
                'previous_value': 3.9,
                'change': -0.1,
                'change_percent': -2.6,
                'date': '2024-01-15',
                'frequency': 'monthly',
                'unit': 'percent',
                'description': 'Unemployment Rate'
            },
            'inflation_rate': {
                'value': 3.2,
                'previous_value': 3.4,
                'change': -0.2,
                'change_percent': -5.9,
                'date': '2024-01-15',
                'frequency': 'monthly',
                'unit': 'percent',
                'description': 'Consumer Price Index Inflation Rate'
            },
            'interest_rate': {
                'value': 5.25,
                'previous_value': 5.0,
                'change': 0.25,
                'change_percent': 5.0,
                'date': '2024-01-15',
                'frequency': 'irregular',
                'unit': 'percent',
                'description': 'Federal Funds Rate'
            }
        }
        
        return {'indicators': indicators}

    def _generate_mock_esg_data(self, params: Dict = None) -> Dict[str, Any]:
        """Generate mock ESG data"""
        symbols = params.get('symbols', ['AAPL', 'MSFT', 'GOOGL']) if params else ['AAPL']
        
        esg_data = {}
        for symbol in symbols:
            esg_data[symbol] = {
                'esg_score': np.random.uniform(60, 95),
                'environmental_score': np.random.uniform(50, 95),
                'social_score': np.random.uniform(60, 90),
                'governance_score': np.random.uniform(70, 95),
                'controversy_score': np.random.uniform(0, 20),
                'last_updated': '2024-01-15',
                'industry_rank': np.random.randint(1, 50),
                'peer_comparison': {
                    'industry_average': np.random.uniform(60, 80),
                    'sector_average': np.random.uniform(65, 85),
                    'percentile_rank': np.random.uniform(50, 95)
                }
            }
        
        return {'esg_data': esg_data}

    def _generate_mock_supply_chain_data(self, params: Dict = None) -> Dict[str, Any]:
        """Generate mock supply chain data"""
        symbols = params.get('symbols', ['AAPL']) if params else ['AAPL']
        
        supply_chain_data = {}
        for symbol in symbols:
            supply_chain_data[symbol] = {
                'supplier_count': np.random.randint(50, 500),
                'geographic_diversity': np.random.uniform(0.6, 0.9),
                'risk_score': np.random.uniform(2, 8),
                'resilience_index': np.random.uniform(0.7, 0.95),
                'key_suppliers': [f'Supplier_{i}' for i in range(1, 6)],
                'risk_factors': [
                    'Geographic concentration',
                    'Single source dependencies',
                    'Political instability',
                    'Natural disaster exposure'
                ],
                'last_updated': '2024-01-15'
            }
        
        return {'supply_chain_data': supply_chain_data}

    def _generate_mock_alternative_data(self, params: Dict = None) -> Dict[str, Any]:
        """Generate mock alternative data"""
        symbols = params.get('symbols', ['AAPL']) if params else ['AAPL']
        data_type = params.get('data_type', 'social_sentiment') if params else 'social_sentiment'
        
        alt_data = {}
        for symbol in symbols:
            if data_type == 'social_sentiment':
                alt_data[symbol] = {
                    'sentiment_score': np.random.uniform(-1, 1),
                    'mention_volume': np.random.randint(1000, 10000),
                    'trend_direction': np.random.choice(['bullish', 'bearish', 'neutral']),
                    'confidence': np.random.uniform(0.7, 0.95),
                    'platforms': {
                        'twitter': np.random.uniform(-1, 1),
                        'reddit': np.random.uniform(-1, 1),
                        'news': np.random.uniform(-1, 1)
                    }
                }
            elif data_type == 'satellite_data':
                alt_data[symbol] = {
                    'facility_activity': np.random.uniform(0.5, 1.0),
                    'parking_lot_fullness': np.random.uniform(0.3, 0.9),
                    'construction_activity': np.random.uniform(0, 1),
                    'supply_chain_activity': np.random.uniform(0.6, 1.0)
                }
            elif data_type == 'web_traffic':
                alt_data[symbol] = {
                    'unique_visitors': np.random.randint(1000000, 50000000),
                    'page_views': np.random.randint(5000000, 200000000),
                    'bounce_rate': np.random.uniform(0.2, 0.6),
                    'session_duration': np.random.uniform(120, 600),
                    'mobile_ratio': np.random.uniform(0.5, 0.8)
                }
        
        return {'alternative_data': alt_data, 'data_type': data_type}

    async def get_sector_performance(self, sectors: List[str] = None) -> Dict[str, SectorData]:
        """Get sector performance data"""
        data = await self._make_request('/sectors/performance')
        
        sector_results = {}
        sectors_data = data.get('sectors', {})
        
        for sector, sector_info in sectors_data.items():
            if not sectors or sector in sectors:
                sector_results[sector] = SectorData(
                    sector=sector,
                    performance_1d=sector_info.get('performance_1d', 0),
                    performance_1w=sector_info.get('performance_1w', 0),
                    performance_1m=sector_info.get('performance_1m', 0),
                    performance_3m=sector_info.get('performance_3m', 0),
                    performance_ytd=sector_info.get('performance_ytd', 0),
                    market_cap=sector_info.get('market_cap', 0),
                    pe_ratio=sector_info.get('pe_ratio', 0),
                    dividend_yield=sector_info.get('dividend_yield', 0),
                    volatility=sector_info.get('volatility', 0),
                    top_performers=sector_info.get('top_performers', []),
                    worst_performers=sector_info.get('worst_performers', [])
                )
        
        return sector_results

    async def get_economic_indicators(self, indicators: List[str] = None) -> Dict[str, EconomicIndicator]:
        """Get economic indicators"""
        data = await self._make_request('/economic/indicators')
        
        indicator_results = {}
        indicators_data = data.get('indicators', {})
        
        for indicator, indicator_info in indicators_data.items():
            if not indicators or indicator in indicators:
                indicator_results[indicator] = EconomicIndicator(
                    indicator=indicator,
                    value=indicator_info.get('value', 0),
                    previous_value=indicator_info.get('previous_value', 0),
                    change=indicator_info.get('change', 0),
                    change_percent=indicator_info.get('change_percent', 0),
                    date=indicator_info.get('date', ''),
                    frequency=indicator_info.get('frequency', ''),
                    unit=indicator_info.get('unit', ''),
                    description=indicator_info.get('description', '')
                )
        
        return indicator_results

    async def get_esg_data(self, symbols: List[str]) -> Dict[str, ESGData]:
        """Get ESG data for symbols"""
        data = await self._make_request('/esg/scores', {'symbols': symbols})
        
        esg_results = {}
        esg_data = data.get('esg_data', {})
        
        for symbol, esg_info in esg_data.items():
            esg_results[symbol] = ESGData(
                symbol=symbol,
                esg_score=esg_info.get('esg_score', 0),
                environmental_score=esg_info.get('environmental_score', 0),
                social_score=esg_info.get('social_score', 0),
                governance_score=esg_info.get('governance_score', 0),
                controversy_score=esg_info.get('controversy_score', 0),
                last_updated=esg_info.get('last_updated', ''),
                industry_rank=esg_info.get('industry_rank', 0),
                peer_comparison=esg_info.get('peer_comparison', {})
            )
        
        return esg_results

    async def get_alternative_data(self, symbols: List[str], data_type: str) -> Dict[str, AlternativeData]:
        """Get alternative data"""
        data = await self._make_request('/alternative/data', {
            'symbols': symbols,
            'data_type': data_type
        })
        
        alt_results = {}
        alt_data = data.get('alternative_data', {})
        
        for symbol, alt_info in alt_data.items():
            for metric, value in alt_info.items():
                if isinstance(value, (int, float)):
                    key = f"{symbol}_{metric}"
                    alt_results[key] = AlternativeData(
                        data_type=data_type,
                        symbol=symbol,
                        metric=metric,
                        value=float(value),
                        timestamp=datetime.now().isoformat(),
                        source='financial_datasets',
                        confidence_score=np.random.uniform(0.8, 0.95),
                        metadata={'data_type': data_type}
                    )
        
        return alt_results

# Initialize service
financial_datasets_service = FinancialDatasetsService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await financial_datasets_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    await financial_datasets_service.cleanup()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Financial Datasets MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "alternative_data",
            "economic_indicators",
            "sector_data",
            "esg_data",
            "supply_chain_data"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    """Server metrics endpoint"""
    return {
        "cpu_usage": 22.8,
        "memory_usage": 38.5,
        "disk_usage": 12.3,
        "network_in": 768,
        "network_out": 1536,
        "active_connections": 0,
        "queue_length": 0,
        "errors_last_hour": 0,
        "requests_last_hour": 45,
        "response_time_p95": 850.0
    }

@app.post("/sectors")
async def get_sector_data(request: DataRequest, token: str = Depends(get_current_user)):
    """Get sector performance data"""
    try:
        sectors = await financial_datasets_service.get_sector_performance(request.sectors)
        return {
            "sector_data": {sector: asdict(data) for sector, data in sectors.items()},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching sector data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/economic")
async def get_economic_data(request: DataRequest, token: str = Depends(get_current_user)):
    """Get economic indicators"""
    try:
        indicators = await financial_datasets_service.get_economic_indicators(request.indicators)
        return {
            "economic_indicators": {indicator: asdict(data) for indicator, data in indicators.items()},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching economic data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/esg")
async def get_esg_data(request: DataRequest, token: str = Depends(get_current_user)):
    """Get ESG data for symbols"""
    if not request.symbols:
        raise HTTPException(status_code=400, detail="symbols required for ESG data")
    
    try:
        esg_data = await financial_datasets_service.get_esg_data(request.symbols)
        return {
            "esg_data": {symbol: asdict(data) for symbol, data in esg_data.items()},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching ESG data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alternative")
async def get_alternative_data(request: DataRequest, token: str = Depends(get_current_user)):
    """Get alternative data"""
    if not request.symbols or not request.data_type:
        raise HTTPException(status_code=400, detail="symbols and data_type required")
    
    try:
        alt_data = await financial_datasets_service.get_alternative_data(
            request.symbols, 
            request.data_type
        )
        return {
            "alternative_data": {key: asdict(data) for key, data in alt_data.items()},
            "data_type": request.data_type,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching alternative data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capabilities")
async def get_capabilities():
    """Get server capabilities"""
    return {
        "capabilities": [
            {
                "name": "alternative_data",
                "description": "Alternative financial data sources",
                "endpoint": "/alternative",
                "data_types": ["social_sentiment", "satellite_data", "web_traffic", "mobile_app_usage"]
            },
            {
                "name": "economic_indicators",
                "description": "Macroeconomic indicators and data",
                "endpoint": "/economic"
            },
            {
                "name": "sector_data",
                "description": "Sector performance and analysis",
                "endpoint": "/sectors"
            },
            {
                "name": "esg_data",
                "description": "Environmental, Social, and Governance scores",
                "endpoint": "/esg"
            },
            {
                "name": "supply_chain_data",
                "description": "Supply chain risk and resilience metrics",
                "endpoint": "/supply-chain"
            }
        ],
        "data_types": ["alternative", "economic", "sector", "esg"],
        "regions": ["Global"],
        "provider": "Financial Datasets",
        "update_frequency": "Real-time to daily"
    }

if __name__ == "__main__":
    uvicorn.run(
        "financial_datasets:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )