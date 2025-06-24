#!/usr/bin/env python3
"""
Simple Main Application - Basic FastAPI server without external dependencies
Tests the core application structure and service registry pattern
"""

import asyncio
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Use only standard library and minimal dependencies
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Simple service registry for testing
class SimpleServiceRegistry:
    """Simple service registry for testing"""
    
    def __init__(self):
        self.services = {}
        self.connections = {}
        self._initialized = False
    
    def register_service(self, name: str, service: Any):
        """Register a service"""
        self.services[name] = service
        logger.info(f"✅ Registered service: {name}")
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a service by name"""
        return self.services.get(name)
    
    def list_services(self) -> List[str]:
        """List all registered services"""
        return list(self.services.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check all services"""
        health_status = {}
        
        for name, service in self.services.items():
            try:
                if hasattr(service, 'get_service_status'):
                    status = await service.get_service_status()
                    health_status[name] = status
                else:
                    health_status[name] = {"status": "running", "type": "basic"}
            except Exception as e:
                health_status[name] = {"status": "error", "error": str(e)}
        
        return health_status
    
    def mark_initialized(self):
        """Mark registry as initialized"""
        self._initialized = True
    
    def is_initialized(self) -> bool:
        """Check if registry is initialized"""
        return self._initialized

# Create global registry
simple_registry = SimpleServiceRegistry()

async def initialize_simple_services():
    """Initialize our simple services"""
    logger.info("🔧 Initializing simple services...")
    
    try:
        # Import and create simple historical data service
        from services.simple_historical_data_service import create_simple_historical_data_service
        
        historical_service = create_simple_historical_data_service()
        simple_registry.register_service("historical_data", historical_service)
        
        # Mark as initialized
        simple_registry.mark_initialized()
        
        logger.info("✅ Simple services initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize simple services: {e}")
        return False

if FASTAPI_AVAILABLE:
    # Create FastAPI app if available
    app = FastAPI(
        title="MCP Trading Platform - Simple Test",
        description="Simple version for testing core functionality",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Startup event handler"""
        logger.info("🚀 Starting simple MCP Trading Platform...")
        await initialize_simple_services()
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "MCP Trading Platform - Simple",
            "version": "1.0.0",
            "description": "Simple test version",
            "services": simple_registry.list_services(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        if not simple_registry.is_initialized():
            raise HTTPException(status_code=503, detail="Services not initialized")
        
        health_status = await simple_registry.health_check()
        
        return {
            "status": "healthy",
            "services": health_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @app.get("/api/v1/market-data/{symbol}")
    async def get_market_data(symbol: str):
        """Get market data for a symbol"""
        historical_service = simple_registry.get_service("historical_data")
        if not historical_service:
            raise HTTPException(status_code=503, detail="Historical data service not available")
        
        try:
            current_price = await historical_service.get_current_price(symbol)
            historical_data = await historical_service.get_historical_data(symbol, "1mo")
            volatility = await historical_service.get_volatility(symbol)
            
            return {
                "symbol": symbol,
                "current_price": current_price,
                "volatility": volatility,
                "historical_data_points": len(historical_data["data"]) if historical_data else 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/services")
    async def list_services():
        """List all available services"""
        return {
            "services": simple_registry.list_services(),
            "initialized": simple_registry.is_initialized(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @app.get("/api/v1/portfolio/summary")
    async def get_portfolio_summary():
        """Get portfolio summary"""
        try:
            # Mock portfolio data for now
            return {
                "total_equity": 50000.0,
                "cash_balance": 25000.0,
                "total_position_value": 25000.0,
                "total_unrealized_pnl": 1250.0,
                "total_realized_pnl": 500.0,
                "total_pnl": 1750.0,
                "daily_pnl": 250.0,
                "total_return_percent": 3.5,
                "number_of_positions": 3,
                "long_positions": 2,
                "short_positions": 1,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/portfolio/positions")
    async def get_portfolio_positions():
        """Get current portfolio positions"""
        try:
            # Mock positions data
            return [
                {
                    "symbol": "BTC-USD",
                    "quantity": 0.5,
                    "avg_cost": 43000.0,
                    "current_price": 45000.0,
                    "market_value": 22500.0,
                    "unrealized_pnl": 1000.0,
                    "realized_pnl": 0.0,
                    "pnl_percent": 4.65,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                },
                {
                    "symbol": "ETH-USD",
                    "quantity": 5.0,
                    "avg_cost": 2400.0,
                    "current_price": 2550.0,
                    "market_value": 12750.0,
                    "unrealized_pnl": 750.0,
                    "realized_pnl": 200.0,
                    "pnl_percent": 6.25,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/trading/signals")
    async def get_trading_signals():
        """Get recent trading signals"""
        try:
            # Mock trading signals
            return [
                {
                    "symbol": "BTC-USD",
                    "signal": "buy",
                    "strength": 0.75,
                    "confidence": 0.82,
                    "predicted_change_pct": 3.2,
                    "reasoning": "Strong momentum indicators with volume confirmation",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source": "ai_prediction"
                },
                {
                    "symbol": "ETH-USD",
                    "signal": "hold",
                    "strength": 0.5,
                    "confidence": 0.65,
                    "predicted_change_pct": 0.8,
                    "reasoning": "Mixed technical indicators, awaiting clearer direction",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source": "technical_analysis"
                },
                {
                    "symbol": "AAPL",
                    "signal": "sell",
                    "strength": 0.68,
                    "confidence": 0.71,
                    "predicted_change_pct": -2.1,
                    "reasoning": "Overbought conditions with negative earnings sentiment",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source": "sentiment_analysis"
                }
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/agents/status")
    async def get_agents_status():
        """Get status of all trading agents"""
        try:
            # Mock agent status data
            return [
                {
                    "agent_id": "marcus_momentum",
                    "name": "Marcus Momentum",
                    "status": "active",
                    "strategy": "momentum_trading",
                    "current_allocation": 15000.0,
                    "pnl": 825.50,
                    "trades_today": 3,
                    "win_rate": 0.68,
                    "last_action": "bought 0.1 BTC-USD at $44,950",
                    "last_updated": datetime.now(timezone.utc).isoformat()
                },
                {
                    "agent_id": "alex_arbitrage",
                    "name": "Alex Arbitrage", 
                    "status": "active",
                    "strategy": "arbitrage",
                    "current_allocation": 12000.0,
                    "pnl": 345.75,
                    "trades_today": 8,
                    "win_rate": 0.85,
                    "last_action": "arbitrage opportunity detected BTC-USD",
                    "last_updated": datetime.now(timezone.utc).isoformat()
                },
                {
                    "agent_id": "sophia_reversion",
                    "name": "Sophia Reversion",
                    "status": "monitoring",
                    "strategy": "mean_reversion",
                    "current_allocation": 8000.0,
                    "pnl": -125.25,
                    "trades_today": 1,
                    "win_rate": 0.72,
                    "last_action": "waiting for mean reversion signal",
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/market/overview")
    async def get_market_overview():
        """Get market overview data"""
        try:
            historical_service = simple_registry.get_service("historical_data")
            if not historical_service:
                raise HTTPException(status_code=503, detail="Historical data service not available")
            
            # Get data for major symbols
            major_symbols = ["BTC-USD", "ETH-USD", "AAPL", "SPY"]
            market_data = []
            
            for symbol in major_symbols:
                price_data = await historical_service.get_current_price(symbol)
                volatility = await historical_service.get_volatility(symbol)
                
                # Calculate mock change
                import random
                change_pct = random.uniform(-3.0, 3.0)
                
                market_data.append({
                    "symbol": symbol,
                    "price": price_data["price"],
                    "change_pct": round(change_pct, 2),
                    "volatility": volatility,
                    "volume": random.randint(1000000, 50000000),
                    "market_cap": price_data["price"] * random.randint(100000, 10000000),
                    "last_updated": price_data["timestamp"]
                })
            
            return {
                "market_data": market_data,
                "market_sentiment": {
                    "overall": "neutral",
                    "score": 0.52,
                    "fear_greed_index": 45,
                    "vix": 18.5
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/performance/metrics")
    async def get_performance_metrics():
        """Get performance metrics"""
        try:
            return {
                "total_return_percent": 3.5,
                "total_pnl": 1750.0,
                "daily_pnl": 250.0,
                "win_rate": 0.72,
                "sharpe_ratio": 1.35,
                "volatility": 0.18,
                "max_drawdown": -0.045,
                "total_trades": 247,
                "total_equity": 50000.0,
                "initial_equity": 48250.0,
                "best_trade": 850.0,
                "worst_trade": -320.0,
                "avg_trade": 7.09,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

async def run_simple_test():
    """Run a simple test without FastAPI"""
    logger.info("🧪 Running simple test without web server...")
    
    success = await initialize_simple_services()
    if not success:
        return False
    
    # Test service functionality
    historical_service = simple_registry.get_service("historical_data")
    if historical_service:
        status = await historical_service.get_service_status()
        logger.info(f"✅ Historical service status: {status['status']}")
        
        price = await historical_service.get_current_price("BTC-USD")
        logger.info(f"✅ BTC price: ${price['price']}")
        
    # Test health check
    health = await simple_registry.health_check()
    logger.info(f"✅ Health check: {len(health)} services checked")
    
    logger.info("🎉 Simple test completed successfully!")
    return True

def main():
    """Main entry point"""
    logger.info("🚀 Starting MCP Trading Platform - Simple Version")
    
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "--test":
        # Run test mode
        result = asyncio.run(run_simple_test())
        exit(0 if result else 1)
    
    if FASTAPI_AVAILABLE:
        logger.info("🌐 Starting web server...")
        uvicorn.run(
            "simple_main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),
            reload=False,
            log_level="info"
        )
    else:
        logger.warning("FastAPI not available, running simple test...")
        result = asyncio.run(run_simple_test())
        exit(0 if result else 1)

if __name__ == "__main__":
    main()