#!/usr/bin/env python3
"""
MCP Trading Platform - Consolidated Monorepo Application
Unified FastAPI application consolidating all microservices for Railway deployment
"""

import asyncio
import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager
import uuid

# FastAPI and web framework imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

# SSE for real-time updates
from sse_starlette.sse import EventSourceResponse

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_PORT = int(os.getenv("PORT", 8000))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"

# Database and Cache Connections
from supabase import create_client, Client as SupabaseClient
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Import all consolidated services
from services.market_data_service import MarketDataService
from services.historical_data_service import HistoricalDataService
from services.trading_engine_service import TradingEngineService
from services.order_management_service import OrderManagementService
from services.risk_management_service import RiskManagementService
from services.portfolio_tracker_service import PortfolioTrackerService
from services.ai_prediction_service import AIPredictionService
from services.technical_analysis_service import TechnicalAnalysisService
from services.sentiment_analysis_service import SentimentAnalysisService
from services.ml_portfolio_optimizer_service import MLPortfolioOptimizerService
from services.agent_management_service import AgentManagementService
from services.execution_specialist_service import ExecutionSpecialistService
from services.hyperliquid_execution_service import HyperliquidExecutionService
from services.strategy_config_service import StrategyConfigService
from services.watchlist_service import WatchlistService
from services.user_preference_service import UserPreferenceService

# Import agent frameworks
from agents.crew_setup import trading_analysis_crew
from agents.autogen_setup import autogen_trading_system, run_trading_analysis_autogen

# Import all models
from models.api_models import *
from models.agent_models import *
from models.trading_history_models import *
from models.paper_trading_models import *
from models.execution_models import *
from models.hyperliquid_models import *
from models.watchlist_models import *
from models.strategy_models import *
from models.user_models import *
from models.event_models import *

# Authentication
from auth.dependencies import get_current_active_user
from models.auth_models import AuthenticatedUser

# Global services registry for dependency injection
services: Dict[str, Any] = {}
connections: Dict[str, Any] = {}

class ServiceRegistry:
    """Centralized service registry for dependency injection"""
    
    def __init__(self):
        self._services = {}
        self._connections = {}
    
    def register_connection(self, name: str, connection: Any):
        """Register a database/cache connection"""
        self._connections[name] = connection
        logger.info(f"Registered connection: {name}")
    
    def register_service(self, name: str, service: Any):
        """Register a service instance"""
        self._services[name] = service
        logger.info(f"Registered service: {name}")
    
    def get_connection(self, name: str):
        """Get a connection by name"""
        return self._connections.get(name)
    
    def get_service(self, name: str):
        """Get a service by name"""
        return self._services.get(name)
    
    @property
    def all_services(self):
        return self._services.copy()
    
    @property 
    def all_connections(self):
        return self._connections.copy()

# Global service registry
registry = ServiceRegistry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    logger.info("🚀 Starting MCP Trading Platform (Monorepo)")
    
    # Initialize connections
    await initialize_connections()
    
    # Initialize services
    await initialize_services()
    
    # Initialize agent frameworks
    await initialize_agent_frameworks()
    
    logger.info("✅ MCP Trading Platform ready!")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down MCP Trading Platform")
    await cleanup_connections()

async def initialize_connections():
    """Initialize all database and cache connections"""
    logger.info("Initializing connections...")
    
    # Supabase connection
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    if supabase_url and supabase_key:
        supabase_client = create_client(supabase_url, supabase_key)
        registry.register_connection("supabase", supabase_client)
        logger.info("✅ Supabase connection initialized")
    
    # Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping() if hasattr(redis_client, 'ping') else redis_client.ping()
        registry.register_connection("redis", redis_client)
        logger.info("✅ Redis connection initialized")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
    
    # SQLAlchemy for local operations
    database_url = os.getenv("DATABASE_URL", "sqlite:///./trading_platform.db")
    engine = create_engine(database_url)
    session_factory = sessionmaker(bind=engine)
    registry.register_connection("database_engine", engine)
    registry.register_connection("session_factory", session_factory)
    logger.info("✅ Database engine initialized")

async def initialize_services():
    """Initialize all platform services"""
    logger.info("Initializing services...")
    
    session_factory = registry.get_connection("session_factory")
    supabase_client = registry.get_connection("supabase")
    redis_client = registry.get_connection("redis")
    
    # Core Infrastructure Services
    market_data_service = MarketDataService(redis_client=redis_client)
    registry.register_service("market_data", market_data_service)
    
    historical_data_service = HistoricalDataService(supabase_client=supabase_client)
    registry.register_service("historical_data", historical_data_service)
    
    # Trading Engine Services
    trading_engine_service = TradingEngineService(
        market_data_service=market_data_service
    )
    registry.register_service("trading_engine", trading_engine_service)
    
    order_management_service = OrderManagementService(
        session_factory=session_factory
    )
    registry.register_service("order_management", order_management_service)
    
    portfolio_tracker_service = PortfolioTrackerService(
        session_factory=session_factory,
        market_data_service=market_data_service
    )
    registry.register_service("portfolio_tracker", portfolio_tracker_service)
    
    risk_management_service = RiskManagementService(
        portfolio_service=portfolio_tracker_service
    )
    registry.register_service("risk_management", risk_management_service)
    
    # AI and Analytics Services
    ai_prediction_service = AIPredictionService()
    registry.register_service("ai_prediction", ai_prediction_service)
    
    technical_analysis_service = TechnicalAnalysisService()
    registry.register_service("technical_analysis", technical_analysis_service)
    
    sentiment_analysis_service = SentimentAnalysisService()
    registry.register_service("sentiment_analysis", sentiment_analysis_service)
    
    ml_portfolio_optimizer_service = MLPortfolioOptimizerService()
    registry.register_service("ml_portfolio_optimizer", ml_portfolio_optimizer_service)
    
    # Agent and Execution Services
    agent_management_service = AgentManagementService(session_factory=session_factory)
    registry.register_service("agent_management", agent_management_service)
    
    execution_specialist_service = ExecutionSpecialistService()
    registry.register_service("execution_specialist", execution_specialist_service)
    
    hyperliquid_service = HyperliquidExecutionService()
    registry.register_service("hyperliquid_execution", hyperliquid_service)
    
    # Business Logic Services
    strategy_config_service = StrategyConfigService(session_factory=session_factory)
    registry.register_service("strategy_config", strategy_config_service)
    
    watchlist_service = WatchlistService(supabase_client=supabase_client)
    registry.register_service("watchlist", watchlist_service)
    
    user_preference_service = UserPreferenceService(supabase_client=supabase_client)
    registry.register_service("user_preference", user_preference_service)
    
    logger.info("✅ All services initialized")

async def initialize_agent_frameworks():
    """Initialize agent frameworks for trading"""
    logger.info("Initializing agent frameworks...")
    
    # Initialize CrewAI framework
    registry.register_service("crew_trading_analysis", trading_analysis_crew)
    
    # Initialize AutoGen framework
    registry.register_service("autogen_trading_system", autogen_trading_system)
    
    logger.info("✅ Agent frameworks initialized")

async def cleanup_connections():
    """Cleanup connections on shutdown"""
    redis_client = registry.get_connection("redis")
    if redis_client:
        await redis_client.close() if hasattr(redis_client, 'close') else redis_client.close()
        logger.info("Redis connection closed")

# Create FastAPI application
app = FastAPI(
    title="MCP Trading Platform",
    description="Consolidated AI-Powered Algorithmic Trading Platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEBUG else [os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency injection helpers
def get_service(service_name: str):
    """Dependency to get a service by name"""
    def _get_service():
        service = registry.get_service(service_name)
        if not service:
            raise HTTPException(status_code=500, detail=f"Service {service_name} not available")
        return service
    return _get_service

def get_connection(connection_name: str):
    """Dependency to get a connection by name"""
    def _get_connection():
        connection = registry.get_connection(connection_name)
        if not connection:
            raise HTTPException(status_code=500, detail=f"Connection {connection_name} not available")
        return connection
    return _get_connection

# Health check endpoints
@app.get("/health")
async def health_check():
    """Consolidated health check for all services"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "environment": ENVIRONMENT,
        "services": {},
        "connections": {}
    }
    
    # Check all service health
    for service_name, service in registry.all_services.items():
        try:
            if hasattr(service, 'health_check'):
                health_status["services"][service_name] = await service.health_check()
            else:
                health_status["services"][service_name] = "available"
        except Exception as e:
            health_status["services"][service_name] = f"error: {str(e)}"
    
    # Check connection health
    for conn_name, connection in registry.all_connections.items():
        try:
            if conn_name == "redis" and hasattr(connection, 'ping'):
                await connection.ping()
                health_status["connections"][conn_name] = "connected"
            elif conn_name == "supabase":
                # Simple query to test connection
                result = connection.table('users').select('id').limit(1).execute()
                health_status["connections"][conn_name] = "connected"
            else:
                health_status["connections"][conn_name] = "available"
        except Exception as e:
            health_status["connections"][conn_name] = f"error: {str(e)}"
    
    return health_status

@app.get("/")
async def root():
    """Root endpoint with platform information"""
    return {
        "name": "MCP Trading Platform",
        "version": "2.0.0",
        "description": "Consolidated AI-Powered Algorithmic Trading Platform",
        "environment": ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "market_data": "/api/v1/market-data",
            "trading": "/api/v1/trading",
            "agents": "/api/v1/agents",
            "portfolio": "/api/v1/portfolio",
            "risk": "/api/v1/risk"
        }
    }

# Market Data Endpoints (Port 8001-8002 consolidated)
@app.get("/api/v1/market-data/live/{symbol}")
async def get_live_market_data(
    symbol: str,
    market_data_service = Depends(get_service("market_data"))
):
    """Get real-time market data for a symbol"""
    try:
        data = await market_data_service.get_live_data(symbol)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market-data/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    period: str = "1d",
    interval: str = "1h",
    historical_data_service = Depends(get_service("historical_data"))
):
    """Get historical market data"""
    try:
        data = await historical_data_service.get_historical_data(symbol, period, interval)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Trading Engine Endpoints (Port 8010-8013 consolidated)
@app.post("/api/v1/trading/orders")
async def create_order(
    order_request: dict,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    order_management_service = Depends(get_service("order_management"))
):
    """Create a new trading order"""
    try:
        order = await order_management_service.create_order(order_request, current_user.user_id)
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/trading/orders")
async def get_orders(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    order_management_service = Depends(get_service("order_management"))
):
    """Get user's trading orders"""
    try:
        orders = await order_management_service.get_user_orders(current_user.user_id)
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/portfolio/positions")
async def get_portfolio_positions(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    portfolio_service = Depends(get_service("portfolio_tracker"))
):
    """Get user's portfolio positions"""
    try:
        positions = await portfolio_service.get_positions(current_user.user_id)
        return positions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/risk/assessment")
async def get_risk_assessment(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    risk_service = Depends(get_service("risk_management"))
):
    """Get portfolio risk assessment"""
    try:
        assessment = await risk_service.assess_portfolio_risk(current_user.user_id)
        return assessment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Agent Management Endpoints
@app.post("/api/v1/agents")
async def create_agent(
    agent_request: AgentConfigInput,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    agent_service = Depends(get_service("agent_management"))
):
    """Create a new trading agent"""
    try:
        agent = await agent_service.create_agent(agent_request)
        return agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents")
async def get_agents(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    agent_service = Depends(get_service("agent_management"))
):
    """Get user's trading agents"""
    try:
        agents = await agent_service.get_agents()
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/agents/{agent_id}/start")
async def start_agent(
    agent_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    agent_service = Depends(get_service("agent_management"))
):
    """Start a trading agent"""
    try:
        status = await agent_service.start_agent(agent_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/agents/{agent_id}/stop")
async def stop_agent(
    agent_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    agent_service = Depends(get_service("agent_management"))
):
    """Stop a trading agent"""
    try:
        status = await agent_service.stop_agent(agent_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Agent Trading Execution Bridge
@app.post("/api/v1/agents/execute-trade")
async def execute_agent_trade(
    execution_request: ExecutionRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    execution_service = Depends(get_service("execution_specialist"))
):
    """Execute a trade request from an agent"""
    try:
        receipt = await execution_service.process_trade_order(execution_request)
        return receipt
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# AI and Analytics Endpoints (Port 8050-8053 consolidated)
@app.post("/api/v1/ai/predict")
async def get_ai_prediction(
    symbol: str,
    prediction_service = Depends(get_service("ai_prediction"))
):
    """Get AI market prediction"""
    try:
        prediction = await prediction_service.predict_price_movement(symbol)
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/technical/{symbol}")
async def get_technical_analysis(
    symbol: str,
    technical_service = Depends(get_service("technical_analysis"))
):
    """Get technical analysis for a symbol"""
    try:
        analysis = await technical_service.analyze_symbol(symbol)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/sentiment/{symbol}")
async def get_sentiment_analysis(
    symbol: str,
    sentiment_service = Depends(get_service("sentiment_analysis"))
):
    """Get sentiment analysis for a symbol"""
    try:
        sentiment = await sentiment_service.analyze_sentiment(symbol)
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Real-time WebSocket endpoint for live updates
@app.get("/api/v1/stream/events")
async def stream_events(
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Server-sent events for real-time updates"""
    
    async def event_generator():
        while True:
            # Generate real-time events for the user
            yield {
                "event": "heartbeat",
                "data": json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": current_user.user_id
                })
            }
            await asyncio.sleep(30)
    
    return EventSourceResponse(event_generator())

# Development and testing endpoints
if DEBUG:
    @app.get("/api/v1/debug/services")
    async def debug_services():
        """Debug endpoint to check service status"""
        return {
            "services": list(registry.all_services.keys()),
            "connections": list(registry.all_connections.keys()),
            "registry_status": "active"
        }

# Static files for any frontend assets
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Main entry point
if __name__ == "__main__":
    print("""
    ███╗   ███╗ ██████╗██████╗     ████████╗██████╗  █████╗ ██████╗ ██╗███╗   ██╗ ██████╗ 
    ████╗ ████║██╔════╝██╔══██╗    ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝ 
    ██╔████╔██║██║     ██████╔╝       ██║   ██████╔╝███████║██║  ██║██║██╔██╗ ██║██║  ███╗
    ██║╚██╔╝██║██║     ██╔═══╝        ██║   ██╔══██╗██╔══██║██║  ██║██║██║╚██╗██║██║   ██║
    ██║ ╚═╝ ██║╚██████╗██║            ██║   ██║  ██║██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝
    ╚═╝     ╚═╝ ╚═════╝╚═╝            ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ 
                                                                                            
                        🚀 MONOREPO TRADING PLATFORM v2.0.0 🚀
    """)
    
    uvicorn.run(
        "main_monorepo:app",
        host="0.0.0.0",
        port=API_PORT,
        reload=DEBUG,
        log_level="info"
    )