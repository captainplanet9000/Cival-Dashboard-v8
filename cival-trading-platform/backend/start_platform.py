#!/usr/bin/env python3
"""
MCP Trading Platform Startup Script
Orchestrated startup and health verification for all platform services
"""

import asyncio
import subprocess
import sys
import time
import json
import aiohttp
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import signal
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    name: str
    script: str
    port: int
    required: bool = True
    startup_delay: int = 5
    health_endpoint: str = "/health"
    dependencies: List[str] = None

class PlatformManager:
    """Manages startup and shutdown of the entire trading platform"""
    
    def __init__(self):
        self.processes = {}
        self.service_configs = [
            # Core Infrastructure Services
            ServiceConfig("market_data", "mcp_servers/market_data_server.py", 8001, True, 5),
            ServiceConfig("historical_data", "mcp_servers/historical_data_server.py", 8002, True, 5),
            
            # Trading Engine Services
            ServiceConfig("trading_engine", "mcp_servers/trading_engine.py", 8010, True, 10, dependencies=["market_data"]),
            ServiceConfig("order_management", "mcp_servers/order_management.py", 8011, True, 5, dependencies=["trading_engine"]),
            ServiceConfig("risk_management", "mcp_servers/risk_management.py", 8012, True, 10, dependencies=["portfolio_tracker"]),
            ServiceConfig("portfolio_tracker", "mcp_servers/portfolio_tracker.py", 8013, True, 5, dependencies=["market_data"]),
            
            # Intelligence Services
            ServiceConfig("octagon_intelligence", "mcp_servers/octagon_intelligence.py", 8020, False, 15),
            ServiceConfig("mongodb_intelligence", "mcp_servers/mongodb_intelligence.py", 8021, False, 10),
            ServiceConfig("neo4j_intelligence", "mcp_servers/neo4j_intelligence.py", 8022, False, 10),
            
            # AI and Analytics Services
            ServiceConfig("ai_prediction", "mcp_servers/ai_prediction_engine.py", 8050, False, 20),
            ServiceConfig("technical_analysis", "mcp_servers/technical_analysis_engine.py", 8051, False, 15),
            ServiceConfig("ml_portfolio_optimizer", "mcp_servers/ml_portfolio_optimizer.py", 8052, False, 20),
            ServiceConfig("sentiment_analysis", "mcp_servers/sentiment_analysis_engine.py", 8053, False, 15),
            
            # Performance and Infrastructure Services
            ServiceConfig("optimization_engine", "mcp_servers/optimization_engine.py", 8060, False, 10),
            ServiceConfig("load_balancer", "mcp_servers/load_balancer.py", 8070, False, 10),
            ServiceConfig("performance_monitor", "mcp_servers/performance_monitor.py", 8080, False, 10),
            
            # Advanced Features
            ServiceConfig("trading_strategies", "mcp_servers/trading_strategies_framework.py", 8090, False, 15),
            ServiceConfig("risk_management_advanced", "mcp_servers/advanced_risk_management.py", 8091, False, 15),
            ServiceConfig("market_microstructure", "mcp_servers/market_microstructure.py", 8092, False, 10),
            ServiceConfig("external_data_integration", "mcp_servers/external_data_integration.py", 8093, False, 10),
            
            # System Health Monitor (last to start)
            ServiceConfig("system_health_monitor", "system_health_monitor.py", 8100, False, 5, dependencies=["market_data", "trading_engine"])
        ]
        
        self.startup_order = self._calculate_startup_order()
        
    def _calculate_startup_order(self) -> List[ServiceConfig]:
        """Calculate optimal startup order based on dependencies"""
        ordered = []
        remaining = self.service_configs.copy()
        
        while remaining:
            # Find services with no unmet dependencies
            ready = []
            for service in remaining:
                if not service.dependencies:
                    ready.append(service)
                else:
                    deps_met = all(
                        any(s.name == dep for s in ordered) 
                        for dep in service.dependencies
                    )
                    if deps_met:
                        ready.append(service)
            
            if not ready:
                # No services ready - add any remaining to break cycles
                ready = [remaining[0]]
            
            # Add ready services to ordered list
            for service in ready:
                ordered.append(service)
                remaining.remove(service)
        
        return ordered
    
    async def start_service(self, service: ServiceConfig) -> bool:
        """Start a single service"""
        logger.info(f"Starting {service.name} on port {service.port}...")
        
        script_path = Path(__file__).parent / service.script
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            return False
        
        try:
            # Start the service process
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[service.name] = process
            
            # Wait for startup
            await asyncio.sleep(service.startup_delay)
            
            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"Service {service.name} failed to start:")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
            
            # Verify health endpoint
            if await self._check_health(service):
                logger.info(f"✅ {service.name} started successfully")
                return True
            else:
                logger.warning(f"⚠️ {service.name} started but health check failed")
                return not service.required
                
        except Exception as e:
            logger.error(f"Error starting {service.name}: {e}")
            return False
    
    async def _check_health(self, service: ServiceConfig, retries: int = 3) -> bool:
        """Check if service is healthy"""
        url = f"http://localhost:{service.port}{service.health_endpoint}"
        
        for attempt in range(retries):
            try:
                async with aiohttp.ClientSession() as session:
                    timeout = aiohttp.ClientTimeout(total=10)
                    async with session.get(url, timeout=timeout) as response:
                        if response.status == 200:
                            return True
            except Exception as e:
                if attempt < retries - 1:
                    logger.debug(f"Health check attempt {attempt + 1} failed for {service.name}: {e}")
                    await asyncio.sleep(2)
                else:
                    logger.warning(f"Health check failed for {service.name}: {e}")
        
        return False
    
    async def start_platform(self) -> bool:
        """Start the entire platform"""
        logger.info("🚀 Starting MCP Trading Platform...")
        logger.info(f"Service startup order: {[s.name for s in self.startup_order]}")
        
        failed_services = []
        
        for service in self.startup_order:
            success = await self.start_service(service)
            
            if not success:
                if service.required:
                    logger.error(f"❌ Required service {service.name} failed to start")
                    failed_services.append(service.name)
                else:
                    logger.warning(f"⚠️ Optional service {service.name} failed to start")
        
        if failed_services:
            logger.error(f"Platform startup failed. Failed required services: {failed_services}")
            return False
        
        # Final health check
        await asyncio.sleep(10)
        healthy_services = 0
        total_services = len(self.service_configs)
        
        for service in self.service_configs:
            if await self._check_health(service):
                healthy_services += 1
        
        logger.info(f"Platform startup complete: {healthy_services}/{total_services} services healthy")
        
        if healthy_services >= len([s for s in self.service_configs if s.required]):
            logger.info("✅ MCP Trading Platform is ready!")
            await self._print_service_status()
            return True
        else:
            logger.error("❌ Platform startup failed - insufficient healthy services")
            return False
    
    async def _print_service_status(self):
        """Print status of all services"""
        print("\n" + "="*80)
        print("MCP TRADING PLATFORM - SERVICE STATUS")
        print("="*80)
        
        for service in self.service_configs:
            status = "🟢 HEALTHY" if await self._check_health(service, retries=1) else "🔴 UNHEALTHY"
            required = "REQUIRED" if service.required else "OPTIONAL"
            print(f"{service.name:<30} Port {service.port:<6} {status:<12} ({required})")
        
        print("="*80)
        print("Dashboard: http://localhost:8100/dashboard/html")
        print("Health Monitor: http://localhost:8100/health")
        print("="*80)
    
    def stop_platform(self):
        """Stop all platform services"""
        logger.info("🛑 Stopping MCP Trading Platform...")
        
        # Stop in reverse order
        for service_name in reversed(list(self.processes.keys())):
            process = self.processes[service_name]
            if process.poll() is None:  # Process is still running
                logger.info(f"Stopping {service_name}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {service_name}...")
                    process.kill()
        
        logger.info("Platform stopped")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.stop_platform()
        sys.exit(0)

async def main():
    """Main startup function"""
    platform = PlatformManager()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, platform.signal_handler)
    signal.signal(signal.SIGTERM, platform.signal_handler)
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        sys.exit(1)
    
    # Start platform
    success = await platform.start_platform()
    
    if success:
        logger.info("Platform running. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(60)
                
                # Periodic health check
                healthy_count = 0
                for service in platform.service_configs:
                    if await platform._check_health(service, retries=1):
                        healthy_count += 1
                
                logger.info(f"Health check: {healthy_count}/{len(platform.service_configs)} services healthy")
        
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            platform.stop_platform()
    else:
        logger.error("Platform startup failed")
        platform.stop_platform()
        sys.exit(1)

if __name__ == "__main__":
    print("""
    ███╗   ███╗ ██████╗██████╗     ████████╗██████╗  █████╗ ██████╗ ██╗███╗   ██╗ ██████╗ 
    ████╗ ████║██╔════╝██╔══██╗    ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝ 
    ██╔████╔██║██║     ██████╔╝       ██║   ██████╔╝███████║██║  ██║██║██╔██╗ ██║██║  ███╗
    ██║╚██╔╝██║██║     ██╔═══╝        ██║   ██╔══██╗██╔══██║██║  ██║██║██║╚██╗██║██║   ██║
    ██║ ╚═╝ ██║╚██████╗██║            ██║   ██║  ██║██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝
    ╚═╝     ╚═╝ ╚═════╝╚═╝            ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ 
                                                                                            
                              🚀 PLATFORM STARTUP SCRIPT 🚀
    """)
    
    asyncio.run(main())