#!/usr/bin/env python3
"""
MCP Trading Platform - Monorepo Startup and Health Check Script
Tests the consolidated application before Railway deployment
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime, timezone
import subprocess
import sys
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MonorepoHealthChecker:
    """Health checker for the consolidated monorepo application"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.startup_process = None
        
    async def start_application(self) -> bool:
        """Start the monorepo application"""
        logger.info("🚀 Starting MCP Trading Platform Monorepo...")
        
        try:
            # Start the application
            self.startup_process = subprocess.Popen(
                [sys.executable, "main_consolidated.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=Path(__file__).parent
            )
            
            # Wait for startup
            logger.info("Waiting for application startup...")
            await asyncio.sleep(10)
            
            # Check if process is still running
            if self.startup_process.poll() is not None:
                stdout, stderr = self.startup_process.communicate()
                logger.error(f"Application failed to start:")
                logger.error(f"Output: {stdout}")
                return False
            
            logger.info("✅ Application process started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            return False
    
    async def check_health(self, retries: int = 5) -> dict:
        """Check application health"""
        logger.info("🏥 Checking application health...")
        
        for attempt in range(retries):
            try:
                async with aiohttp.ClientSession() as session:
                    timeout = aiohttp.ClientTimeout(total=30)
                    async with session.get(f"{self.base_url}/health", timeout=timeout) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            logger.info("✅ Health check passed")
                            return health_data
                        else:
                            logger.warning(f"Health check returned status {response.status}")
                            
            except Exception as e:
                logger.warning(f"Health check attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(5)
        
        logger.error("❌ All health check attempts failed")
        return {"status": "error", "message": "Health check failed"}
    
    async def test_endpoints(self) -> dict:
        """Test key API endpoints"""
        logger.info("🧪 Testing API endpoints...")
        
        test_results = {}
        
        # Test endpoints to check
        endpoints = [
            ("/", "Root endpoint"),
            ("/health", "Health check"),
            ("/docs", "API documentation"),
            ("/api/v1/debug/services", "Service debug info")
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint, description in endpoints:
                try:
                    timeout = aiohttp.ClientTimeout(total=15)
                    async with session.get(f"{self.base_url}{endpoint}", timeout=timeout) as response:
                        test_results[endpoint] = {
                            "status": response.status,
                            "description": description,
                            "success": response.status < 400
                        }
                        
                        if response.status == 200:
                            logger.info(f"✅ {description}: OK")
                        else:
                            logger.warning(f"⚠️ {description}: Status {response.status}")
                            
                except Exception as e:
                    test_results[endpoint] = {
                        "status": "error",
                        "description": description,
                        "success": False,
                        "error": str(e)
                    }
                    logger.error(f"❌ {description}: {e}")
        
        return test_results
    
    async def test_agent_operations(self) -> dict:
        """Test agent-related operations"""
        logger.info("🤖 Testing agent operations...")
        
        agent_results = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test agent list endpoint (should work without auth in debug mode)
                timeout = aiohttp.ClientTimeout(total=15)
                async with session.get(f"{self.base_url}/api/v1/debug/services", timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        agent_results["services_available"] = "agent_management" in data.get("services", [])
                        agent_results["registry_status"] = data.get("registry_initialized", False)
                        logger.info("✅ Agent services are available")
                    else:
                        agent_results["services_available"] = False
                        logger.warning("⚠️ Agent services status unknown")
                        
        except Exception as e:
            agent_results["error"] = str(e)
            logger.error(f"❌ Agent operations test failed: {e}")
        
        return agent_results
    
    async def run_comprehensive_test(self) -> dict:
        """Run comprehensive test suite"""
        logger.info("🔬 Running comprehensive test suite...")
        
        # Start application
        startup_success = await self.start_application()
        if not startup_success:
            return {"success": False, "error": "Failed to start application"}
        
        # Wait for full initialization
        await asyncio.sleep(15)
        
        # Run health check
        health_results = await self.check_health()
        
        # Test endpoints
        endpoint_results = await self.test_endpoints()
        
        # Test agent operations
        agent_results = await self.test_agent_operations()
        
        # Compile results
        results = {
            "success": health_results.get("status") == "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health": health_results,
            "endpoints": endpoint_results,
            "agent_operations": agent_results,
            "startup": {
                "process_running": self.startup_process and self.startup_process.poll() is None,
                "base_url": self.base_url
            }
        }
        
        return results
    
    def stop_application(self):
        """Stop the application"""
        if self.startup_process and self.startup_process.poll() is None:
            logger.info("🛑 Stopping application...")
            self.startup_process.terminate()
            try:
                self.startup_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Force killing application...")
                self.startup_process.kill()
            logger.info("Application stopped")

async def main():
    """Main test runner"""
    print("""
    ███╗   ███╗ ██████╗██████╗     ████████╗███████╗███████╗████████╗
    ████╗ ████║██╔════╝██╔══██╗    ╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝
    ██╔████╔██║██║     ██████╔╝       ██║   █████╗  ███████╗   ██║   
    ██║╚██╔╝██║██║     ██╔═══╝        ██║   ██╔══╝  ╚════██║   ██║   
    ██║ ╚═╝ ██║╚██████╗██║            ██║   ███████╗███████║   ██║   
    ╚═╝     ╚═╝ ╚═════╝╚═╝            ╚═╝   ╚══════╝╚══════╝   ╚═╝   
                                                                      
                    🧪 MONOREPO HEALTH CHECK & TEST SUITE 🧪
    """)
    
    # Check if environment is configured
    required_env_vars = ["SUPABASE_URL", "REDIS_URL"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please check your .env file configuration")
        return False
    
    checker = MonorepoHealthChecker()
    
    try:
        # Run comprehensive test
        results = await checker.run_comprehensive_test()
        
        # Print results
        print("\n" + "="*80)
        print("MCP TRADING PLATFORM - MONOREPO TEST RESULTS")
        print("="*80)
        
        print(f"Overall Success: {'✅ PASSED' if results['success'] else '❌ FAILED'}")
        print(f"Test Time: {results['timestamp']}")
        print(f"Base URL: {checker.base_url}")
        
        print("\n📊 Health Status:")
        health = results.get('health', {})
        print(f"  Status: {health.get('status', 'unknown')}")
        print(f"  Services: {len(health.get('services', {}))}")
        print(f"  Connections: {len(health.get('connections', {}))}")
        
        print("\n🌐 Endpoint Tests:")
        for endpoint, result in results.get('endpoints', {}).items():
            status = "✅" if result.get('success') else "❌"
            print(f"  {status} {endpoint}: {result.get('description')}")
        
        print("\n🤖 Agent Operations:")
        agent_ops = results.get('agent_operations', {})
        services_ok = "✅" if agent_ops.get('services_available') else "❌"
        registry_ok = "✅" if agent_ops.get('registry_status') else "❌"
        print(f"  {services_ok} Agent services available")
        print(f"  {registry_ok} Service registry initialized")
        
        print("\n🚀 Startup Status:")
        startup = results.get('startup', {})
        process_ok = "✅" if startup.get('process_running') else "❌"
        print(f"  {process_ok} Application process running")
        
        print("="*80)
        
        if results['success']:
            print("🎉 MONOREPO IS READY FOR RAILWAY DEPLOYMENT!")
            print("\nNext steps:")
            print("1. Push to GitHub repository")
            print("2. Connect Railway to repository") 
            print("3. Set environment variables in Railway")
            print("4. Deploy to production")
        else:
            print("⚠️ ISSUES DETECTED - PLEASE REVIEW BEFORE DEPLOYMENT")
            print("\nRecommended actions:")
            print("1. Check environment variable configuration")
            print("2. Verify database and Redis connections")
            print("3. Review application logs")
            print("4. Test individual service endpoints")
        
        return results['success']
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        return False
    finally:
        checker.stop_application()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)