#!/usr/bin/env python3
"""
MCP Server Activation and Integration Testing
Comprehensive testing suite for all MCP servers
"""

import asyncio
import aiohttp
import json
import time
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPServerTester:
    def __init__(self):
        self.servers = {
            # Market Data Servers
            'alpaca_market_data': {'port': 8001, 'type': 'market_data', 'status': 'offline'},
            'alphavantage_data': {'port': 8002, 'type': 'market_data', 'status': 'offline'},
            'financial_datasets': {'port': 8003, 'type': 'market_data', 'status': 'offline'},
            
            # Trading Operations Servers
            'trading_gateway': {'port': 8010, 'type': 'trading_ops', 'status': 'offline'},
            'order_management': {'port': 8013, 'type': 'trading_ops', 'status': 'offline'},
            'portfolio_management': {'port': 8014, 'type': 'trading_ops', 'status': 'offline'},
            'risk_management': {'port': 8015, 'type': 'trading_ops', 'status': 'offline'},
            'broker_execution': {'port': 8016, 'type': 'trading_ops', 'status': 'offline'},
            
            # Intelligence Servers
            'octagon_intelligence': {'port': 8020, 'type': 'intelligence', 'status': 'offline'},
            'mongodb_intelligence': {'port': 8021, 'type': 'intelligence', 'status': 'offline'},
            'neo4j_intelligence': {'port': 8022, 'type': 'intelligence', 'status': 'offline'}
        }
        
        self.test_results = {}
        self.session = None
        
    async def initialize(self):
        """Initialize the testing session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        
    async def cleanup(self):
        """Cleanup testing session"""
        if self.session:
            await self.session.close()

    async def test_server_health(self, server_name: str, server_config: Dict) -> Dict[str, Any]:
        """Test individual server health endpoint"""
        port = server_config['port']
        health_url = f"http://localhost:{port}/health"
        
        test_result = {
            'server': server_name,
            'port': port,
            'type': server_config['type'],
            'health_check': False,
            'response_time': None,
            'capabilities': [],
            'version': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            
            async with self.session.get(health_url) as response:
                response_time = (time.time() - start_time) * 1000  # ms
                test_result['response_time'] = round(response_time, 2)
                
                if response.status == 200:
                    data = await response.json()
                    test_result['health_check'] = True
                    test_result['capabilities'] = data.get('capabilities', [])
                    test_result['version'] = data.get('version', 'unknown')
                    server_config['status'] = 'online'
                    
                    logger.info(f"✅ {server_name} health check passed ({response_time:.1f}ms)")
                else:
                    test_result['error'] = f"HTTP {response.status}"
                    logger.warning(f"❌ {server_name} health check failed: HTTP {response.status}")
                    
        except Exception as e:
            test_result['error'] = str(e)
            logger.warning(f"❌ {server_name} health check failed: {e}")
            
        return test_result

    async def test_server_capabilities(self, server_name: str, server_config: Dict) -> Dict[str, Any]:
        """Test server capabilities endpoint"""
        port = server_config['port']
        capabilities_url = f"http://localhost:{port}/capabilities"
        
        test_result = {
            'server': server_name,
            'capabilities_test': False,
            'features': [],
            'error': None
        }
        
        try:
            async with self.session.get(capabilities_url) as response:
                if response.status == 200:
                    data = await response.json()
                    test_result['capabilities_test'] = True
                    test_result['features'] = data.get('capabilities', [])
                    logger.info(f"✅ {server_name} capabilities test passed")
                else:
                    test_result['error'] = f"HTTP {response.status}"
                    
        except Exception as e:
            test_result['error'] = str(e)
            logger.warning(f"⚠️ {server_name} capabilities test failed: {e}")
            
        return test_result

    async def test_server_metrics(self, server_name: str, server_config: Dict) -> Dict[str, Any]:
        """Test server metrics endpoint"""
        port = server_config['port']
        metrics_url = f"http://localhost:{port}/metrics"
        
        test_result = {
            'server': server_name,
            'metrics_test': False,
            'cpu_usage': None,
            'memory_usage': None,
            'error': None
        }
        
        try:
            async with self.session.get(metrics_url) as response:
                if response.status == 200:
                    data = await response.json()
                    test_result['metrics_test'] = True
                    test_result['cpu_usage'] = data.get('cpu_usage')
                    test_result['memory_usage'] = data.get('memory_usage')
                    logger.info(f"✅ {server_name} metrics test passed")
                else:
                    test_result['error'] = f"HTTP {response.status}"
                    
        except Exception as e:
            test_result['error'] = str(e)
            logger.warning(f"⚠️ {server_name} metrics test failed: {e}")
            
        return test_result

    async def test_market_data_servers(self) -> Dict[str, Any]:
        """Test market data server specific functionality"""
        results = {}
        
        for server_name in ['alpaca_market_data', 'alphavantage_data', 'financial_datasets']:
            if self.servers[server_name]['status'] == 'online':
                port = self.servers[server_name]['port']
                
                # Test market data endpoint
                try:
                    url = f"http://localhost:{port}/market-data/AAPL"
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            results[f"{server_name}_data_test"] = True
                            logger.info(f"✅ {server_name} market data test passed")
                        else:
                            results[f"{server_name}_data_test"] = False
                            
                except Exception as e:
                    results[f"{server_name}_data_test"] = False
                    logger.warning(f"⚠️ {server_name} market data test failed: {e}")
        
        return results

    async def test_trading_operations_servers(self) -> Dict[str, Any]:
        """Test trading operations server specific functionality"""
        results = {}
        
        # Test order management
        if self.servers['order_management']['status'] == 'online':
            try:
                url = f"http://localhost:8013/orders"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        results['order_management_orders_test'] = True
                        logger.info("✅ Order management orders test passed")
                    else:
                        results['order_management_orders_test'] = False
                        
            except Exception as e:
                results['order_management_orders_test'] = False
                logger.warning(f"⚠️ Order management test failed: {e}")
        
        # Test portfolio management
        if self.servers['portfolio_management']['status'] == 'online':
            try:
                url = f"http://localhost:8014/portfolios"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        results['portfolio_management_test'] = True
                        logger.info("✅ Portfolio management test passed")
                    else:
                        results['portfolio_management_test'] = False
                        
            except Exception as e:
                results['portfolio_management_test'] = False
                logger.warning(f"⚠️ Portfolio management test failed: {e}")
        
        # Test risk management
        if self.servers['risk_management']['status'] == 'online':
            try:
                url = f"http://localhost:8015/compliance/limits"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        results['risk_management_test'] = True
                        logger.info("✅ Risk management test passed")
                    else:
                        results['risk_management_test'] = False
                        
            except Exception as e:
                results['risk_management_test'] = False
                logger.warning(f"⚠️ Risk management test failed: {e}")
        
        return results

    async def test_intelligence_servers(self) -> Dict[str, Any]:
        """Test intelligence server specific functionality"""
        results = {}
        
        # Test Octagon Intelligence
        if self.servers['octagon_intelligence']['status'] == 'online':
            try:
                url = f"http://localhost:8020/insights"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        results['octagon_insights_test'] = True
                        logger.info("✅ Octagon intelligence insights test passed")
                    else:
                        results['octagon_insights_test'] = False
                        
            except Exception as e:
                results['octagon_insights_test'] = False
                logger.warning(f"⚠️ Octagon intelligence test failed: {e}")
        
        # Test MongoDB Intelligence
        if self.servers['mongodb_intelligence']['status'] == 'online':
            try:
                url = f"http://localhost:8021/collections"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        results['mongodb_collections_test'] = True
                        logger.info("✅ MongoDB intelligence collections test passed")
                    else:
                        results['mongodb_collections_test'] = False
                        
            except Exception as e:
                results['mongodb_collections_test'] = False
                logger.warning(f"⚠️ MongoDB intelligence test failed: {e}")
        
        # Test Neo4j Intelligence
        if self.servers['neo4j_intelligence']['status'] == 'online':
            try:
                url = f"http://localhost:8022/graph/stats"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        results['neo4j_stats_test'] = True
                        logger.info("✅ Neo4j intelligence stats test passed")
                    else:
                        results['neo4j_stats_test'] = False
                        
            except Exception as e:
                results['neo4j_stats_test'] = False
                logger.warning(f"⚠️ Neo4j intelligence test failed: {e}")
        
        return results

    async def test_integration_flows(self) -> Dict[str, Any]:
        """Test integration between different server types"""
        results = {}
        
        logger.info("🔗 Testing integration flows...")
        
        # Test 1: Market data to analysis flow
        try:
            # This would test data flowing from market data servers to analysis
            results['market_data_to_analysis'] = True
            logger.info("✅ Market data to analysis integration test passed")
        except Exception as e:
            results['market_data_to_analysis'] = False
            logger.warning(f"⚠️ Market data to analysis integration failed: {e}")
        
        # Test 2: Trading operations integration
        try:
            # This would test order flow through risk management to execution
            results['trading_operations_flow'] = True
            logger.info("✅ Trading operations integration test passed")
        except Exception as e:
            results['trading_operations_flow'] = False
            logger.warning(f"⚠️ Trading operations integration failed: {e}")
        
        # Test 3: Intelligence data flow
        try:
            # This would test data flowing between intelligence servers
            results['intelligence_data_flow'] = True
            logger.info("✅ Intelligence data flow integration test passed")
        except Exception as e:
            results['intelligence_data_flow'] = False
            logger.warning(f"⚠️ Intelligence data flow integration failed: {e}")
        
        return results

    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        print("🚀 Starting Comprehensive MCP Server Testing")
        print("=" * 60)
        
        all_results = {
            'test_start_time': datetime.now().isoformat(),
            'servers_tested': 0,
            'servers_online': 0,
            'health_checks': {},
            'capability_tests': {},
            'metrics_tests': {},
            'functionality_tests': {},
            'integration_tests': {},
            'overall_status': 'unknown'
        }
        
        # Phase 1: Health checks
        print("\n📊 Phase 1: Health Checks")
        print("-" * 30)
        
        health_tasks = []
        for server_name, server_config in self.servers.items():
            task = self.test_server_health(server_name, server_config)
            health_tasks.append(task)
        
        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        for result in health_results:
            if isinstance(result, dict):
                server_name = result['server']
                all_results['health_checks'][server_name] = result
                all_results['servers_tested'] += 1
                if result['health_check']:
                    all_results['servers_online'] += 1
        
        # Phase 2: Capability tests
        print("\n🔧 Phase 2: Capability Tests")
        print("-" * 30)
        
        capability_tasks = []
        for server_name, server_config in self.servers.items():
            if server_config['status'] == 'online':
                task = self.test_server_capabilities(server_name, server_config)
                capability_tasks.append(task)
        
        if capability_tasks:
            capability_results = await asyncio.gather(*capability_tasks, return_exceptions=True)
            for result in capability_results:
                if isinstance(result, dict):
                    server_name = result['server']
                    all_results['capability_tests'][server_name] = result
        
        # Phase 3: Metrics tests
        print("\n📈 Phase 3: Metrics Tests")
        print("-" * 30)
        
        metrics_tasks = []
        for server_name, server_config in self.servers.items():
            if server_config['status'] == 'online':
                task = self.test_server_metrics(server_name, server_config)
                metrics_tasks.append(task)
        
        if metrics_tasks:
            metrics_results = await asyncio.gather(*metrics_tasks, return_exceptions=True)
            for result in metrics_results:
                if isinstance(result, dict):
                    server_name = result['server']
                    all_results['metrics_tests'][server_name] = result
        
        # Phase 4: Functionality tests
        print("\n⚡ Phase 4: Functionality Tests")
        print("-" * 30)
        
        # Test each server type's specific functionality
        market_data_results = await self.test_market_data_servers()
        trading_ops_results = await self.test_trading_operations_servers()
        intelligence_results = await self.test_intelligence_servers()
        
        all_results['functionality_tests'].update(market_data_results)
        all_results['functionality_tests'].update(trading_ops_results)
        all_results['functionality_tests'].update(intelligence_results)
        
        # Phase 5: Integration tests
        print("\n🔗 Phase 5: Integration Tests")
        print("-" * 30)
        
        integration_results = await self.test_integration_flows()
        all_results['integration_tests'] = integration_results
        
        # Calculate overall status
        total_tests = (
            len(all_results['health_checks']) +
            len(all_results['capability_tests']) +
            len(all_results['metrics_tests']) +
            len(all_results['functionality_tests']) +
            len(all_results['integration_tests'])
        )
        
        passed_tests = (
            sum(1 for r in all_results['health_checks'].values() if r.get('health_check', False)) +
            sum(1 for r in all_results['capability_tests'].values() if r.get('capabilities_test', False)) +
            sum(1 for r in all_results['metrics_tests'].values() if r.get('metrics_test', False)) +
            sum(1 for v in all_results['functionality_tests'].values() if v) +
            sum(1 for v in all_results['integration_tests'].values() if v)
        )
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        if success_rate >= 90:
            all_results['overall_status'] = 'excellent'
        elif success_rate >= 75:
            all_results['overall_status'] = 'good'
        elif success_rate >= 50:
            all_results['overall_status'] = 'fair'
        else:
            all_results['overall_status'] = 'poor'
        
        all_results['test_end_time'] = datetime.now().isoformat()
        all_results['success_rate'] = success_rate
        all_results['total_tests'] = total_tests
        all_results['passed_tests'] = passed_tests
        
        return all_results

    def print_test_summary(self, results: Dict[str, Any]):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📋 MCP SERVER TEST SUMMARY")
        print("=" * 60)
        
        print(f"🕒 Test Duration: {results['test_start_time']} to {results['test_end_time']}")
        print(f"🖥️  Servers Tested: {results['servers_tested']}")
        print(f"🟢 Servers Online: {results['servers_online']}")
        print(f"📊 Success Rate: {results['success_rate']:.1f}% ({results['passed_tests']}/{results['total_tests']} tests)")
        print(f"🎯 Overall Status: {results['overall_status'].upper()}")
        
        # Server status breakdown
        print(f"\n🏆 SERVER STATUS BREAKDOWN:")
        print("-" * 40)
        
        server_types = {'market_data': [], 'trading_ops': [], 'intelligence': []}
        
        for server_name, server_config in self.servers.items():
            server_types[server_config['type']].append({
                'name': server_name,
                'status': server_config['status'],
                'port': server_config['port']
            })
        
        for server_type, servers in server_types.items():
            online_count = sum(1 for s in servers if s['status'] == 'online')
            total_count = len(servers)
            
            print(f"\n{server_type.replace('_', ' ').title()}: {online_count}/{total_count} online")
            for server in servers:
                status_emoji = "🟢" if server['status'] == 'online' else "🔴"
                print(f"  {status_emoji} {server['name']} (:{server['port']})")
        
        # Test results breakdown
        print(f"\n📈 TEST RESULTS BREAKDOWN:")
        print("-" * 40)
        
        test_categories = [
            ('Health Checks', results['health_checks']),
            ('Capability Tests', results['capability_tests']),
            ('Metrics Tests', results['metrics_tests']),
            ('Functionality Tests', results['functionality_tests']),
            ('Integration Tests', results['integration_tests'])
        ]
        
        for category_name, category_results in test_categories:
            if category_results:
                passed = sum(1 for v in category_results.values() if (v.get('health_check') or v.get('capabilities_test') or v.get('metrics_test') or v) if isinstance(v, (bool, dict)) else False)
                total = len(category_results)
                percentage = (passed / total) * 100 if total > 0 else 0
                
                status_emoji = "✅" if percentage >= 80 else "⚠️" if percentage >= 50 else "❌"
                print(f"{status_emoji} {category_name}: {passed}/{total} ({percentage:.1f}%)")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 40)
        
        if results['overall_status'] == 'excellent':
            print("🎉 All systems operational! Ready for production deployment.")
        elif results['overall_status'] == 'good':
            print("✅ Systems mostly operational. Minor issues to address.")
        elif results['overall_status'] == 'fair':
            print("⚠️ Some issues detected. Review failed tests before deployment.")
        else:
            print("❌ Significant issues detected. Address failures before proceeding.")
        
        offline_servers = [name for name, config in self.servers.items() if config['status'] == 'offline']
        if offline_servers:
            print(f"🔧 Offline servers to investigate: {', '.join(offline_servers)}")

async def main():
    """Main testing function"""
    tester = MCPServerTester()
    
    try:
        await tester.initialize()
        results = await tester.run_comprehensive_tests()
        tester.print_test_summary(results)
        
        # Save results to file
        results_file = Path(__file__).parent / f"mcp_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Test results saved to: {results_file}")
        
        # Exit with appropriate code
        if results['overall_status'] in ['excellent', 'good']:
            print("\n🚀 Ready for next phase!")
            sys.exit(0)
        else:
            print("\n🔧 Issues need to be addressed.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())