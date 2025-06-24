#!/usr/bin/env python3
"""
MCP Trading Platform - Monorepo Dashboard
Comprehensive dashboard for monitoring the consolidated trading platform
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Core platform imports
from core import registry, db_manager
from auth.dependencies import get_current_active_user
from models.auth_models import AuthenticatedUser

app = FastAPI(title="MCP Trading Platform Dashboard", version="2.0.0")

# Templates and static files
templates = Jinja2Templates(directory="dashboard/templates")
if Path("dashboard/static").exists():
    app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

class MonorepoDashboard:
    """Comprehensive dashboard for the consolidated trading platform"""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.metrics_cache = {}
        self.last_update = None
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview"""
        try:
            # Get service registry status
            registry_health = await registry.health_check()
            
            # Get database manager status
            db_health = await db_manager.health_check()
            
            # Calculate uptime
            uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            
            overview = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": self._format_uptime(uptime_seconds),
                "version": "2.0.0",
                "architecture": "consolidated_monorepo",
                "environment": "production",
                "status": "healthy",
                "registry": {
                    "initialized": registry.is_initialized(),
                    "services_count": len(registry.all_services),
                    "connections_count": len(registry.all_connections),
                    "services": list(registry.all_services.keys()),
                    "connections": list(registry.all_connections.keys())
                },
                "database": {
                    "initialized": db_manager.is_initialized(),
                    "health": db_health
                },
                "performance": await self._get_performance_metrics()
            }
            
            # Determine overall health
            if registry_health.get("registry") != "healthy" or any(
                "error" in str(status).lower() 
                for status in registry_health.get("services", {}).values()
            ):
                overview["status"] = "degraded"
            
            return overview
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": str(e),
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": self._format_uptime(uptime_seconds)
            }
    
    async def get_service_details(self) -> Dict[str, Any]:
        """Get detailed service information"""
        try:
            services_info = {}
            
            # Get all services from registry
            for service_name, service in registry.all_services.items():
                service_info = {
                    "name": service_name,
                    "type": type(service).__name__,
                    "status": "active",
                    "endpoints": self._get_service_endpoints(service_name),
                    "health": "healthy"
                }
                
                # Try to get health check if available
                try:
                    if hasattr(service, 'health_check'):
                        health = await service.health_check()
                        service_info["health"] = health
                except Exception as e:
                    service_info["health"] = f"error: {str(e)}"
                
                services_info[service_name] = service_info
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_services": len(services_info),
                "services": services_info
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "services": {}
            }
    
    async def get_agent_dashboard(self) -> Dict[str, Any]:
        """Get agent management dashboard data"""
        try:
            agent_service = registry.get_service("agent_management")
            if not agent_service:
                return {"error": "Agent management service not available"}
            
            # Get all agents
            agents = await agent_service.get_agents()
            
            # Get agent statistics
            total_agents = len(agents)
            active_agents = len([a for a in agents if a.is_active])
            
            # Get agent status breakdown
            status_breakdown = {}
            for agent in agents:
                status = await agent_service.get_agent_status(agent.agent_id)
                if status:
                    status_str = status.status
                    status_breakdown[status_str] = status_breakdown.get(status_str, 0) + 1
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_agents": total_agents,
                "active_agents": active_agents,
                "inactive_agents": total_agents - active_agents,
                "status_breakdown": status_breakdown,
                "agents": [
                    {
                        "id": agent.agent_id,
                        "name": agent.name,
                        "type": agent.agent_type,
                        "is_active": agent.is_active,
                        "strategy": agent.strategy.strategy_name if agent.strategy else "none",
                        "created_at": agent.created_at.isoformat() if agent.created_at else None,
                        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
                    }
                    for agent in agents
                ]
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "total_agents": 0,
                "active_agents": 0
            }
    
    async def get_trading_dashboard(self) -> Dict[str, Any]:
        """Get trading operations dashboard data"""
        try:
            # Get portfolio service
            portfolio_service = registry.get_service("portfolio_tracker")
            order_service = registry.get_service("order_management")
            
            dashboard_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "portfolio": {},
                "orders": {},
                "trading_status": "paper_trading_enabled"
            }
            
            # Get portfolio information if available
            if portfolio_service:
                try:
                    # This would need user context in real implementation
                    dashboard_data["portfolio"] = {
                        "status": "available",
                        "service": "portfolio_tracker"
                    }
                except Exception as e:
                    dashboard_data["portfolio"] = {"error": str(e)}
            
            # Get order information if available
            if order_service:
                try:
                    dashboard_data["orders"] = {
                        "status": "available", 
                        "service": "order_management"
                    }
                except Exception as e:
                    dashboard_data["orders"] = {"error": str(e)}
            
            return dashboard_data
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def get_market_data_dashboard(self) -> Dict[str, Any]:
        """Get market data dashboard"""
        try:
            market_service = registry.get_service("market_data")
            historical_service = registry.get_service("historical_data")
            
            dashboard_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data_service": "unavailable",
                "historical_data_service": "unavailable",
                "data_feeds": []
            }
            
            if market_service:
                dashboard_data["market_data_service"] = "available"
                dashboard_data["data_feeds"].append("real_time_market_data")
            
            if historical_service:
                dashboard_data["historical_data_service"] = "available"
                dashboard_data["data_feeds"].append("historical_market_data")
            
            return dashboard_data
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def get_ai_analytics_dashboard(self) -> Dict[str, Any]:
        """Get AI and analytics dashboard"""
        try:
            ai_services = {
                "ai_prediction": registry.get_service("ai_prediction"),
                "technical_analysis": registry.get_service("technical_analysis"),
                "sentiment_analysis": registry.get_service("sentiment_analysis"),
                "ml_portfolio_optimizer": registry.get_service("ml_portfolio_optimizer")
            }
            
            dashboard_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ai_services": {},
                "frameworks": {
                    "crewai": registry.get_service("crew_trading_analysis") is not None,
                    "autogen": registry.get_service("autogen_trading_system") is not None
                }
            }
            
            for service_name, service in ai_services.items():
                dashboard_data["ai_services"][service_name] = {
                    "status": "available" if service else "unavailable",
                    "endpoint": f"/api/v1/ai/{service_name.replace('_', '-')}" if service else None
                }
            
            return dashboard_data
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {secs}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def _get_service_endpoints(self, service_name: str) -> List[str]:
        """Get API endpoints for a service"""
        endpoint_map = {
            "market_data": ["/api/v1/market-data/live", "/api/v1/market-data/historical"],
            "trading_engine": ["/api/v1/trading/orders", "/api/v1/trading/positions"],
            "portfolio_tracker": ["/api/v1/portfolio/positions", "/api/v1/portfolio/performance"],
            "risk_management": ["/api/v1/risk/assessment"],
            "agent_management": ["/api/v1/agents", "/api/v1/agents/{id}/start", "/api/v1/agents/{id}/stop"],
            "execution_specialist": ["/api/v1/agents/execute-trade"],
            "ai_prediction": ["/api/v1/ai/predict"],
            "technical_analysis": ["/api/v1/analytics/technical"],
            "sentiment_analysis": ["/api/v1/analytics/sentiment"]
        }
        return endpoint_map.get(service_name, [])
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            }
        except Exception as e:
            return {"error": str(e)}

# Global dashboard instance
dashboard = MonorepoDashboard()

# Dashboard API endpoints
@app.get("/")
async def dashboard_home(request: Request):
    """Main dashboard home page"""
    overview = await dashboard.get_system_overview()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "overview": overview,
        "title": "MCP Trading Platform Dashboard"
    })

@app.get("/api/overview")
async def get_overview():
    """Get system overview API"""
    return await dashboard.get_system_overview()

@app.get("/api/services")
async def get_services():
    """Get services information API"""
    return await dashboard.get_service_details()

@app.get("/api/agents")
async def get_agents_dashboard():
    """Get agents dashboard API"""
    return await dashboard.get_agent_dashboard()

@app.get("/api/trading")
async def get_trading_dashboard():
    """Get trading dashboard API"""
    return await dashboard.get_trading_dashboard()

@app.get("/api/market-data")
async def get_market_data_dashboard():
    """Get market data dashboard API"""
    return await dashboard.get_market_data_dashboard()

@app.get("/api/ai-analytics")
async def get_ai_analytics_dashboard():
    """Get AI analytics dashboard API"""
    return await dashboard.get_ai_analytics_dashboard()

@app.get("/health")
async def health_check():
    """Dashboard health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dashboard_version": "2.0.0"
    }

if __name__ == "__main__":
    print("🖥️ Starting MCP Trading Platform Dashboard...")
    uvicorn.run(
        "dashboard.monorepo_dashboard:app",
        host="0.0.0.0",
        port=8100,
        reload=True
    )