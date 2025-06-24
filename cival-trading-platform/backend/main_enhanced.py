#!/usr/bin/env python3
"""
Enhanced Main Application
Complete autonomous trading system with all phases integrated
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import uvicorn

# Import all services
from core.service_registry import ServiceRegistry, get_registry
from services.autonomous_trading_engine import AutonomousTradingEngine
from services.real_time_market_service import RealTimeMarketService
from services.performance_optimization_service import PerformanceOptimizationService
from services.llm_integration_service import LLMIntegrationService
from services.autonomous_agent_coordinator import AutonomousAgentCoordinator
from services.agent_decision_engine import AgentDecisionEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TradingSystemManager:
    """
    Main system manager that coordinates all services and ensures proper
    startup, shutdown, and inter-service communication
    """
    
    def __init__(self):
        self.registry = ServiceRegistry()
        self.services = {}
        self.is_running = False
        
    async def initialize_services(self):
        """Initialize all services in the correct order"""
        try:
            logger.info("Starting Enhanced Autonomous Trading System...")
            
            # Phase 1: Core Infrastructure Services
            logger.info("Phase 1: Initializing core infrastructure...")
            
            # LLM Integration Service (Foundation for AI features)
            llm_service = LLMIntegrationService()
            await llm_service.initialize()
            self.registry.register_service("llm_integration_service", llm_service)
            self.services["llm_integration_service"] = llm_service
            logger.info("✅ LLM Integration Service initialized")
            
            # Real-Time Market Service (Data foundation)
            market_service = RealTimeMarketService()
            await market_service.initialize()
            self.registry.register_service("real_time_market_service", market_service)
            self.services["real_time_market_service"] = market_service
            logger.info("✅ Real-Time Market Service initialized")
            
            # Phase 2: Agent and Decision Systems
            logger.info("Phase 2: Initializing agent systems...")
            
            # Agent Decision Engine
            decision_engine = AgentDecisionEngine()
            await decision_engine.initialize()
            self.registry.register_service("agent_decision_engine", decision_engine)
            self.services["agent_decision_engine"] = decision_engine
            logger.info("✅ Agent Decision Engine initialized")
            
            # Agent Coordinator
            agent_coordinator = AutonomousAgentCoordinator()
            await agent_coordinator.initialize()
            self.registry.register_service("autonomous_agent_coordinator", agent_coordinator)
            self.services["autonomous_agent_coordinator"] = agent_coordinator
            logger.info("✅ Autonomous Agent Coordinator initialized")
            
            # Phase 3: Trading Engine
            logger.info("Phase 3: Initializing trading engine...")
            
            # Autonomous Trading Engine (Main trading logic)
            trading_engine = AutonomousTradingEngine()
            await trading_engine.initialize()
            self.registry.register_service("autonomous_trading_engine", trading_engine)
            self.services["autonomous_trading_engine"] = trading_engine
            logger.info("✅ Autonomous Trading Engine initialized")
            
            # Phase 4: Monitoring and Optimization
            logger.info("Phase 4: Initializing monitoring systems...")
            
            # Performance Optimization Service
            optimization_service = PerformanceOptimizationService()
            await optimization_service.initialize()
            self.registry.register_service("performance_optimization_service", optimization_service)
            self.services["performance_optimization_service"] = optimization_service
            logger.info("✅ Performance Optimization Service initialized")
            
            self.is_running = True
            logger.info("🚀 All services initialized successfully!")
            
            # Display system status
            await self._display_system_status()
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            await self.shutdown()
            raise
    
    async def _display_system_status(self):
        """Display comprehensive system status"""
        logger.info("=" * 80)
        logger.info("🎯 ENHANCED AUTONOMOUS TRADING SYSTEM STATUS")
        logger.info("=" * 80)
        
        # Service status
        logger.info("📊 Service Status:")
        for service_name, service in self.services.items():
            status = "🟢 RUNNING" if service else "🔴 FAILED"
            logger.info(f"   {service_name}: {status}")
        
        # Get system metrics
        try:
            if "autonomous_trading_engine" in self.services:
                trading_status = await self.services["autonomous_trading_engine"].get_status()
                logger.info(f"💰 Trading Status:")
                logger.info(f"   Mode: {trading_status.get('trading_mode', 'Unknown')}")
                logger.info(f"   Enabled: {trading_status.get('is_enabled', False)}")
                logger.info(f"   Active Signals: {trading_status.get('active_signals', 0)}")
                logger.info(f"   Opportunities: {trading_status.get('active_opportunities', 0)}")
                logger.info(f"   Active Orders: {trading_status.get('active_orders', 0)}")
            
            if "real_time_market_service" in self.services:
                market_overview = await self.services["real_time_market_service"].get_market_overview()
                logger.info(f"📈 Market Data:")
                logger.info(f"   Active Symbols: {market_overview.get('active_symbols', 0)}")
                logger.info(f"   Last Update: {market_overview.get('last_update', 'Unknown')}")
            
            if "performance_optimization_service" in self.services:
                perf_overview = await self.services["performance_optimization_service"].get_performance_overview()
                logger.info(f"⚡ System Performance:")
                logger.info(f"   Health Score: {perf_overview.get('system_health', 0):.1f}/100")
                logger.info(f"   Active Alerts: {len(perf_overview.get('active_alerts', []))}")
                logger.info(f"   Optimizations: {perf_overview.get('active_optimizations', 0)}")
                
        except Exception as e:
            logger.warning(f"Could not retrieve all status information: {e}")
        
        logger.info("=" * 80)
        logger.info("🚀 System Ready for Autonomous Trading!")
        logger.info("=" * 80)
    
    async def shutdown(self):
        """Gracefully shutdown all services"""
        if not self.is_running:
            return
            
        logger.info("🛑 Shutting down Enhanced Autonomous Trading System...")
        
        # Shutdown services in reverse order
        shutdown_order = [
            "performance_optimization_service",
            "autonomous_trading_engine", 
            "autonomous_agent_coordinator",
            "agent_decision_engine",
            "real_time_market_service",
            "llm_integration_service"
        ]
        
        for service_name in shutdown_order:
            if service_name in self.services:
                try:
                    service = self.services[service_name]
                    if hasattr(service, 'stop'):
                        await service.stop()
                    logger.info(f"✅ Stopped {service_name}")
                except Exception as e:
                    logger.error(f"Error stopping {service_name}: {e}")
        
        self.is_running = False
        logger.info("🛑 System shutdown complete")
    
    async def get_system_status(self):
        """Get comprehensive system status"""
        status = {
            "system_running": self.is_running,
            "services": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'get_status'):
                    service_status = await service.get_status()
                else:
                    service_status = {"status": "running" if service else "stopped"}
                
                status["services"][service_name] = service_status
                
            except Exception as e:
                status["services"][service_name] = {"status": "error", "error": str(e)}
        
        return status

# Global system manager
system_manager = TradingSystemManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    # Startup
    await system_manager.initialize_services()
    
    yield
    
    # Shutdown
    await system_manager.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Enhanced Autonomous Trading System",
    description="Complete AI-powered autonomous trading platform with real-time monitoring",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        system_status = await system_manager.get_system_status()
        
        # Determine overall health
        all_healthy = all(
            service.get("status") in ["running", "healthy", "active"]
            for service in system_status["services"].values()
        )
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_running": system_status["system_running"],
            "services_count": len(system_status["services"]),
            "healthy_services": sum(
                1 for service in system_status["services"].values()
                if service.get("status") in ["running", "healthy", "active"]
            )
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

# System status endpoint
@app.get("/api/v1/system/status")
async def get_system_status():
    """Get detailed system status"""
    return await system_manager.get_system_status()

# Trading engine endpoints
@app.get("/api/v1/trading/status")
async def get_trading_status():
    """Get trading engine status"""
    try:
        trading_engine = system_manager.services.get("autonomous_trading_engine")
        if not trading_engine:
            raise HTTPException(status_code=503, detail="Trading engine not available")
        
        return await trading_engine.get_status()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/trading/enable")
async def enable_trading():
    """Enable autonomous trading"""
    try:
        trading_engine = system_manager.services.get("autonomous_trading_engine")
        if not trading_engine:
            raise HTTPException(status_code=503, detail="Trading engine not available")
        
        trading_engine.is_trading_enabled = True
        return {"status": "enabled", "timestamp": datetime.now(timezone.utc).isoformat()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/trading/disable")
async def disable_trading():
    """Disable autonomous trading"""
    try:
        trading_engine = system_manager.services.get("autonomous_trading_engine")
        if not trading_engine:
            raise HTTPException(status_code=503, detail="Trading engine not available")
        
        trading_engine.is_trading_enabled = False
        return {"status": "disabled", "timestamp": datetime.now(timezone.utc).isoformat()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Market data endpoints
@app.get("/api/v1/market/overview")
async def get_market_overview():
    """Get market data overview"""
    try:
        market_service = system_manager.services.get("real_time_market_service")
        if not market_service:
            raise HTTPException(status_code=503, detail="Market service not available")
        
        return await market_service.get_market_overview()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market/tickers")
async def get_all_tickers():
    """Get all ticker data"""
    try:
        market_service = system_manager.services.get("real_time_market_service")
        if not market_service:
            raise HTTPException(status_code=503, detail="Market service not available")
        
        tickers = await market_service.get_all_tickers()
        return {symbol: ticker.__dict__ if hasattr(ticker, '__dict__') else ticker 
                for symbol, ticker in tickers.items()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Performance monitoring endpoints
@app.get("/api/v1/monitoring/overview")
async def get_monitoring_overview():
    """Get performance monitoring overview"""
    try:
        optimization_service = system_manager.services.get("performance_optimization_service")
        if not optimization_service:
            raise HTTPException(status_code=503, detail="Optimization service not available")
        
        return await optimization_service.get_performance_overview()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Agent status endpoints
@app.get("/api/v1/agents/status")
async def get_agents_status():
    """Get agent coordinator status"""
    try:
        agent_coordinator = system_manager.services.get("autonomous_agent_coordinator")
        if not agent_coordinator:
            raise HTTPException(status_code=503, detail="Agent coordinator not available")
        
        return await agent_coordinator.get_status()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# LLM service endpoints
@app.get("/api/v1/llm/status")
async def get_llm_status():
    """Get LLM service status"""
    try:
        llm_service = system_manager.services.get("llm_integration_service")
        if not llm_service:
            raise HTTPException(status_code=503, detail="LLM service not available")
        
        return {
            "status": "active",
            "providers_available": len(llm_service.providers) if hasattr(llm_service, 'providers') else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Shutdown endpoint
@app.post("/api/v1/system/shutdown")
async def shutdown_system():
    """Gracefully shutdown the system"""
    try:
        # Schedule shutdown in background
        async def delayed_shutdown():
            await asyncio.sleep(1)  # Give time for response
            await system_manager.shutdown()
            
        asyncio.create_task(delayed_shutdown())
        
        return {
            "status": "shutdown_initiated",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    asyncio.create_task(system_manager.shutdown())
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    uvicorn.run(
        "main_enhanced:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for production
        log_level="info",
        access_log=True
    )