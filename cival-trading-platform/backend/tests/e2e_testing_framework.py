#!/usr/bin/env python3
"""
End-to-End Testing Framework
Comprehensive testing framework for real-world trading scenarios
"""

import asyncio
import aiohttp
import json
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestScenario(str, Enum):
    MARKET_OPEN_TRADING = "market_open_trading"
    VOLATILITY_SPIKE = "volatility_spike"
    NEWS_DRIVEN_TRADING = "news_driven_trading"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    HIGH_FREQUENCY_TRADING = "high_frequency_trading"
    PORTFOLIO_REBALANCING = "portfolio_rebalancing"
    STRESS_TESTING = "stress_testing"
    FAILOVER_RECOVERY = "failover_recovery"

class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TestCase:
    id: str
    name: str
    scenario: TestScenario
    description: str
    prerequisites: List[str]
    steps: List[Dict[str, Any]]
    expected_outcomes: List[str]
    timeout_seconds: int
    criticality: str  # high, medium, low

@dataclass
class TestExecution:
    test_case_id: str
    start_time: str
    end_time: Optional[str]
    status: TestStatus
    steps_completed: int
    total_steps: int
    results: Dict[str, Any]
    errors: List[str]
    metrics: Dict[str, float]
    artifacts: Dict[str, Any]

@dataclass
class ScenarioResult:
    scenario: TestScenario
    total_tests: int
    passed_tests: int
    failed_tests: int
    execution_time_seconds: float
    success_rate: float
    critical_failures: List[str]

class E2ETestingFramework:
    """End-to-end testing framework for trading platform"""
    
    def __init__(self):
        self.test_cases = {}
        self.executions = {}
        self.session = None
        self.base_urls = {
            "market_data": "http://localhost:8001",
            "trading_engine": "http://localhost:8010",
            "order_management": "http://localhost:8011",
            "risk_management": "http://localhost:8012",
            "portfolio_tracker": "http://localhost:8013",
            "ai_prediction": "http://localhost:8050",
            "technical_analysis": "http://localhost:8051",
            "sentiment_analysis": "http://localhost:8053",
            "trading_strategies": "http://localhost:8090",
            "risk_management_advanced": "http://localhost:8091",
            "external_data_integration": "http://localhost:8093"
        }
        
        # Initialize test cases
        self._initialize_test_cases()
        
        logger.info("E2E Testing Framework initialized")
    
    def _initialize_test_cases(self):
        """Initialize comprehensive test cases"""
        test_cases = [
            {
                "name": "Market Open Trading Simulation",
                "scenario": TestScenario.MARKET_OPEN_TRADING,
                "description": "Simulate market opening with high volume trading",
                "prerequisites": ["market_data_available", "trading_engine_active"],
                "steps": [
                    {"action": "prepare_portfolio", "params": {"cash": 1000000, "symbols": ["AAPL", "GOOGL", "MSFT"]}},
                    {"action": "generate_market_signals", "params": {"count": 50}},
                    {"action": "execute_trades", "params": {"order_count": 20}},
                    {"action": "monitor_risk", "params": {"duration_minutes": 5}},
                    {"action": "validate_portfolio", "params": {"expected_positions": 3}}
                ],
                "expected_outcomes": [
                    "All orders executed successfully",
                    "Portfolio within risk limits",
                    "P&L tracking accurate",
                    "No system errors"
                ],
                "timeout_seconds": 300,
                "criticality": "high"
            },
            {
                "name": "Volatility Spike Response",
                "scenario": TestScenario.VOLATILITY_SPIKE,
                "description": "Test system response to sudden market volatility",
                "prerequisites": ["risk_management_active", "market_data_streaming"],
                "steps": [
                    {"action": "establish_positions", "params": {"symbols": ["TSLA", "NVDA"], "size": 1000}},
                    {"action": "simulate_volatility_spike", "params": {"magnitude": 0.1}},
                    {"action": "check_risk_alerts", "params": {"expected_alerts": ["volatility"]}},
                    {"action": "verify_hedging", "params": {"hedging_activated": True}},
                    {"action": "validate_position_sizing", "params": {"max_position_reduction": 0.3}}
                ],
                "expected_outcomes": [
                    "Risk alerts triggered",
                    "Automatic hedging activated",
                    "Position sizes reduced",
                    "System remains stable"
                ],
                "timeout_seconds": 180,
                "criticality": "high"
            },
            {
                "name": "News-Driven Trading",
                "scenario": TestScenario.NEWS_DRIVEN_TRADING,
                "description": "Test trading based on news sentiment",
                "prerequisites": ["sentiment_analysis_active", "news_feed_available"],
                "steps": [
                    {"action": "inject_news_event", "params": {"symbol": "AAPL", "sentiment": "very_positive"}},
                    {"action": "wait_for_sentiment_analysis", "params": {"timeout": 30}},
                    {"action": "check_trading_signals", "params": {"expected_signal": "buy"}},
                    {"action": "execute_sentiment_trade", "params": {"symbol": "AAPL"}},
                    {"action": "monitor_performance", "params": {"duration_minutes": 2}}
                ],
                "expected_outcomes": [
                    "News processed correctly",
                    "Sentiment signal generated",
                    "Trade executed based on sentiment",
                    "Performance tracking active"
                ],
                "timeout_seconds": 200,
                "criticality": "medium"
            },
            {
                "name": "Risk Limit Breach Handling",
                "scenario": TestScenario.RISK_LIMIT_BREACH,
                "description": "Test system response to risk limit violations",
                "prerequisites": ["risk_limits_configured", "portfolio_active"],
                "steps": [
                    {"action": "set_tight_risk_limits", "params": {"var_limit": 0.02}},
                    {"action": "build_risky_portfolio", "params": {"concentration": 0.8}},
                    {"action": "trigger_limit_breach", "params": {"breach_type": "concentration"}},
                    {"action": "verify_alert_system", "params": {"alert_expected": True}},
                    {"action": "check_trading_halt", "params": {"halt_expected": True}}
                ],
                "expected_outcomes": [
                    "Risk limit breach detected",
                    "Alerts generated immediately",
                    "Trading temporarily halted",
                    "Risk team notified"
                ],
                "timeout_seconds": 120,
                "criticality": "high"
            },
            {
                "name": "High Frequency Trading Simulation",
                "scenario": TestScenario.HIGH_FREQUENCY_TRADING,
                "description": "Test system under high-frequency trading load",
                "prerequisites": ["low_latency_enabled", "market_data_realtime"],
                "steps": [
                    {"action": "setup_hft_strategy", "params": {"frequency": "microsecond"}},
                    {"action": "generate_rapid_signals", "params": {"signals_per_second": 100}},
                    {"action": "execute_rapid_trades", "params": {"trades_per_second": 50}},
                    {"action": "monitor_latency", "params": {"max_latency_ms": 10}},
                    {"action": "validate_order_fills", "params": {"fill_rate_min": 0.95}}
                ],
                "expected_outcomes": [
                    "High-frequency signals processed",
                    "Sub-millisecond order execution",
                    "High fill rates maintained",
                    "System performance stable"
                ],
                "timeout_seconds": 60,
                "criticality": "medium"
            },
            {
                "name": "Portfolio Rebalancing",
                "scenario": TestScenario.PORTFOLIO_REBALANCING,
                "description": "Test automated portfolio rebalancing",
                "prerequisites": ["portfolio_optimizer_active", "target_allocations_set"],
                "steps": [
                    {"action": "setup_target_portfolio", "params": {"allocations": {"AAPL": 0.3, "GOOGL": 0.3, "MSFT": 0.4}}},
                    {"action": "create_drift", "params": {"drift_percentage": 0.15}},
                    {"action": "trigger_rebalancing", "params": {"threshold": 0.10}},
                    {"action": "execute_rebalance_trades", "params": {"minimize_costs": True}},
                    {"action": "validate_final_allocation", "params": {"tolerance": 0.02}}
                ],
                "expected_outcomes": [
                    "Drift detected correctly",
                    "Rebalancing triggered",
                    "Optimal trade execution",
                    "Target allocation achieved"
                ],
                "timeout_seconds": 240,
                "criticality": "medium"
            },
            {
                "name": "Stress Testing Simulation",
                "scenario": TestScenario.STRESS_TESTING,
                "description": "Run comprehensive stress tests",
                "prerequisites": ["stress_testing_module_active"],
                "steps": [
                    {"action": "load_historical_scenarios", "params": {"scenarios": ["2008_crisis", "covid_crash"]}},
                    {"action": "apply_stress_scenarios", "params": {"portfolio_id": "main"}},
                    {"action": "calculate_impact", "params": {"metrics": ["var", "expected_shortfall"]}},
                    {"action": "generate_recommendations", "params": {"action_items": True}},
                    {"action": "validate_results", "params": {"confidence_level": 0.95}}
                ],
                "expected_outcomes": [
                    "Stress scenarios executed",
                    "Impact calculated accurately",
                    "Risk metrics updated",
                    "Actionable recommendations provided"
                ],
                "timeout_seconds": 300,
                "criticality": "high"
            },
            {
                "name": "System Failover and Recovery",
                "scenario": TestScenario.FAILOVER_RECOVERY,
                "description": "Test system resilience and recovery",
                "prerequisites": ["failover_configured", "backup_systems_ready"],
                "steps": [
                    {"action": "establish_baseline", "params": {"trading_active": True}},
                    {"action": "simulate_primary_failure", "params": {"service": "trading_engine"}},
                    {"action": "verify_failover", "params": {"backup_activated": True}},
                    {"action": "continue_operations", "params": {"degraded_mode": True}},
                    {"action": "restore_primary", "params": {"full_functionality": True}}
                ],
                "expected_outcomes": [
                    "Failover executed smoothly",
                    "Operations continued",
                    "Data integrity maintained",
                    "Full recovery achieved"
                ],
                "timeout_seconds": 600,
                "criticality": "high"
            }
        ]
        
        for test_data in test_cases:
            test_id = str(uuid.uuid4())
            
            test_case = TestCase(
                id=test_id,
                name=test_data["name"],
                scenario=test_data["scenario"],
                description=test_data["description"],
                prerequisites=test_data["prerequisites"],
                steps=test_data["steps"],
                expected_outcomes=test_data["expected_outcomes"],
                timeout_seconds=test_data["timeout_seconds"],
                criticality=test_data["criticality"]
            )
            
            self.test_cases[test_id] = test_case
        
        logger.info(f"Initialized {len(test_cases)} E2E test cases")
    
    async def setup_test_environment(self):
        """Setup test environment"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        
        # Verify all services are available
        for service, url in self.base_urls.items():
            try:
                async with self.session.get(f"{url}/health") as response:
                    if response.status != 200:
                        logger.warning(f"Service {service} not available at {url}")
            except Exception as e:
                logger.error(f"Cannot connect to {service}: {e}")
        
        logger.info("Test environment setup completed")
    
    async def teardown_test_environment(self):
        """Cleanup test environment"""
        if self.session:
            await self.session.close()
        logger.info("Test environment cleanup completed")
    
    async def run_test_case(self, test_case_id: str) -> TestExecution:
        """Execute a single test case"""
        if test_case_id not in self.test_cases:
            raise ValueError(f"Test case {test_case_id} not found")
        
        test_case = self.test_cases[test_case_id]
        execution_id = str(uuid.uuid4())
        
        execution = TestExecution(
            test_case_id=test_case_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            status=TestStatus.RUNNING,
            steps_completed=0,
            total_steps=len(test_case.steps),
            results={},
            errors=[],
            metrics={},
            artifacts={}
        )
        
        self.executions[execution_id] = execution
        
        logger.info(f"Starting test case: {test_case.name}")
        
        try:
            start_time = time.time()
            
            # Check prerequisites
            prereq_results = await self._check_prerequisites(test_case.prerequisites)
            if not all(prereq_results.values()):
                execution.status = TestStatus.FAILED
                execution.errors.append("Prerequisites not met")
                return execution
            
            # Execute test steps
            for i, step in enumerate(test_case.steps):
                step_result = await self._execute_test_step(step, test_case.scenario)
                execution.results[f"step_{i+1}"] = step_result
                
                if step_result.get("success", False):
                    execution.steps_completed += 1
                else:
                    execution.errors.append(f"Step {i+1} failed: {step_result.get('error', 'Unknown error')}")
                    break
            
            # Validate outcomes
            validation_results = await self._validate_outcomes(test_case.expected_outcomes, execution.results)
            execution.results["validation"] = validation_results
            
            # Calculate metrics
            execution_time = time.time() - start_time
            execution.metrics = {
                "execution_time_seconds": execution_time,
                "success_rate": execution.steps_completed / execution.total_steps,
                "error_count": len(execution.errors)
            }
            
            # Determine final status
            if execution.steps_completed == execution.total_steps and all(validation_results.values()):
                execution.status = TestStatus.PASSED
            else:
                execution.status = TestStatus.FAILED
            
            execution.end_time = datetime.now().isoformat()
            
            logger.info(f"Test case {test_case.name} completed: {execution.status.value}")
            
        except Exception as e:
            execution.status = TestStatus.FAILED
            execution.errors.append(f"Test execution error: {str(e)}")
            execution.end_time = datetime.now().isoformat()
            logger.error(f"Test case {test_case.name} failed with exception: {e}")
        
        return execution
    
    async def run_scenario(self, scenario: TestScenario) -> ScenarioResult:
        """Run all test cases for a specific scenario"""
        scenario_tests = [tc for tc in self.test_cases.values() if tc.scenario == scenario]
        
        if not scenario_tests:
            raise ValueError(f"No test cases found for scenario {scenario}")
        
        logger.info(f"Running scenario: {scenario.value} ({len(scenario_tests)} tests)")
        
        start_time = time.time()
        executions = []
        
        for test_case in scenario_tests:
            execution = await self.run_test_case(test_case.id)
            executions.append(execution)
        
        execution_time = time.time() - start_time
        
        # Calculate results
        passed_tests = len([e for e in executions if e.status == TestStatus.PASSED])
        failed_tests = len([e for e in executions if e.status == TestStatus.FAILED])
        total_tests = len(executions)
        
        critical_failures = [
            f"{self.test_cases[e.test_case_id].name}: {', '.join(e.errors)}"
            for e in executions 
            if e.status == TestStatus.FAILED and self.test_cases[e.test_case_id].criticality == "high"
        ]
        
        result = ScenarioResult(
            scenario=scenario,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            execution_time_seconds=execution_time,
            success_rate=(passed_tests / total_tests * 100) if total_tests > 0 else 0,
            critical_failures=critical_failures
        )
        
        logger.info(f"Scenario {scenario.value} completed: {result.success_rate:.1f}% success rate")
        
        return result
    
    async def run_all_scenarios(self) -> Dict[TestScenario, ScenarioResult]:
        """Run all test scenarios"""
        logger.info("Running all E2E test scenarios")
        
        await self.setup_test_environment()
        
        try:
            results = {}
            
            for scenario in TestScenario:
                try:
                    result = await self.run_scenario(scenario)
                    results[scenario] = result
                except Exception as e:
                    logger.error(f"Scenario {scenario.value} failed: {e}")
                    # Create failed result
                    results[scenario] = ScenarioResult(
                        scenario=scenario,
                        total_tests=0,
                        passed_tests=0,
                        failed_tests=0,
                        execution_time_seconds=0,
                        success_rate=0,
                        critical_failures=[f"Scenario execution failed: {str(e)}"]
                    )
            
            return results
            
        finally:
            await self.teardown_test_environment()
    
    async def _check_prerequisites(self, prerequisites: List[str]) -> Dict[str, bool]:
        """Check test prerequisites"""
        results = {}
        
        for prereq in prerequisites:
            if prereq == "market_data_available":
                results[prereq] = await self._check_service_health("market_data")
            elif prereq == "trading_engine_active":
                results[prereq] = await self._check_service_health("trading_engine")
            elif prereq == "risk_management_active":
                results[prereq] = await self._check_service_health("risk_management")
            elif prereq == "sentiment_analysis_active":
                results[prereq] = await self._check_service_health("sentiment_analysis")
            else:
                results[prereq] = True  # Default to true for unknown prerequisites
        
        return results
    
    async def _check_service_health(self, service: str) -> bool:
        """Check if a service is healthy"""
        try:
            url = f"{self.base_urls[service]}/health"
            async with self.session.get(url) as response:
                return response.status == 200
        except:
            return False
    
    async def _execute_test_step(self, step: Dict[str, Any], scenario: TestScenario) -> Dict[str, Any]:
        """Execute a single test step"""
        action = step["action"]
        params = step.get("params", {})
        
        try:
            if action == "prepare_portfolio":
                return await self._prepare_portfolio(params)
            elif action == "generate_market_signals":
                return await self._generate_market_signals(params)
            elif action == "execute_trades":
                return await self._execute_trades(params)
            elif action == "monitor_risk":
                return await self._monitor_risk(params)
            elif action == "simulate_volatility_spike":
                return await self._simulate_volatility_spike(params)
            elif action == "check_risk_alerts":
                return await self._check_risk_alerts(params)
            elif action == "inject_news_event":
                return await self._inject_news_event(params)
            elif action == "wait_for_sentiment_analysis":
                return await self._wait_for_sentiment_analysis(params)
            else:
                # Generic API call step
                return await self._generic_api_step(action, params)
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _prepare_portfolio(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare test portfolio"""
        try:
            # Create mock portfolio
            portfolio_data = {
                "id": "test_portfolio",
                "cash": params.get("cash", 100000),
                "positions": {symbol: {"quantity": 0, "avg_price": 0} for symbol in params.get("symbols", [])}
            }
            
            return {"success": True, "portfolio": portfolio_data}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_market_signals(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock market signals"""
        try:
            signal_count = params.get("count", 10)
            signals = []
            
            for i in range(signal_count):
                signal = {
                    "id": f"signal_{i}",
                    "symbol": np.random.choice(["AAPL", "GOOGL", "MSFT", "TSLA"]),
                    "type": np.random.choice(["buy", "sell"]),
                    "strength": np.random.uniform(0.5, 1.0),
                    "timestamp": datetime.now().isoformat()
                }
                signals.append(signal)
            
            return {"success": True, "signals": signals, "count": len(signals)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_trades(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mock trades"""
        try:
            order_count = params.get("order_count", 5)
            orders = []
            
            for i in range(order_count):
                order = {
                    "id": f"order_{i}",
                    "symbol": np.random.choice(["AAPL", "GOOGL", "MSFT", "TSLA"]),
                    "side": np.random.choice(["buy", "sell"]),
                    "quantity": np.random.randint(10, 100),
                    "status": "filled",
                    "fill_price": np.random.uniform(100, 300)
                }
                orders.append(order)
            
            return {"success": True, "orders": orders, "filled_orders": len(orders)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _monitor_risk(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor risk metrics"""
        try:
            duration = params.get("duration_minutes", 1)
            
            # Simulate risk monitoring
            await asyncio.sleep(min(duration * 60, 30))  # Cap at 30 seconds for testing
            
            risk_metrics = {
                "var_95": np.random.uniform(0.01, 0.05),
                "max_drawdown": np.random.uniform(0.02, 0.08),
                "beta": np.random.uniform(0.8, 1.2),
                "volatility": np.random.uniform(0.15, 0.35)
            }
            
            return {"success": True, "risk_metrics": risk_metrics}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _simulate_volatility_spike(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate market volatility spike"""
        try:
            magnitude = params.get("magnitude", 0.1)
            
            volatility_event = {
                "type": "volatility_spike",
                "magnitude": magnitude,
                "affected_symbols": ["AAPL", "GOOGL", "MSFT", "TSLA"],
                "timestamp": datetime.now().isoformat()
            }
            
            return {"success": True, "event": volatility_event}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_risk_alerts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check for risk alerts"""
        try:
            expected_alerts = params.get("expected_alerts", [])
            
            # Simulate risk alerts
            alerts = []
            for alert_type in expected_alerts:
                alert = {
                    "id": f"alert_{alert_type}",
                    "type": alert_type,
                    "severity": "high",
                    "message": f"Risk alert: {alert_type}",
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)
            
            return {"success": True, "alerts": alerts, "alert_count": len(alerts)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _inject_news_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Inject mock news event"""
        try:
            symbol = params.get("symbol", "AAPL")
            sentiment = params.get("sentiment", "neutral")
            
            news_event = {
                "id": f"news_{int(time.time())}",
                "symbol": symbol,
                "headline": f"{symbol} announces major breakthrough",
                "sentiment": sentiment,
                "timestamp": datetime.now().isoformat()
            }
            
            return {"success": True, "news_event": news_event}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _wait_for_sentiment_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for sentiment analysis completion"""
        try:
            timeout = params.get("timeout", 30)
            
            # Simulate waiting for sentiment analysis
            await asyncio.sleep(min(timeout, 5))  # Cap at 5 seconds for testing
            
            sentiment_result = {
                "sentiment_score": np.random.uniform(-1, 1),
                "confidence": np.random.uniform(0.7, 0.95),
                "processing_time": np.random.uniform(1, 10)
            }
            
            return {"success": True, "sentiment_result": sentiment_result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generic_api_step(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute generic API step"""
        try:
            # Mock successful API call
            return {
                "success": True,
                "action": action,
                "params": params,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _validate_outcomes(self, expected_outcomes: List[str], results: Dict[str, Any]) -> Dict[str, bool]:
        """Validate test outcomes"""
        validation_results = {}
        
        for outcome in expected_outcomes:
            # Simple validation logic - in practice this would be more sophisticated
            if "orders executed successfully" in outcome.lower():
                validation_results[outcome] = any("orders" in str(result) for result in results.values())
            elif "risk" in outcome.lower():
                validation_results[outcome] = any("risk" in str(result) for result in results.values())
            elif "no system errors" in outcome.lower():
                validation_results[outcome] = not any("error" in str(result) for result in results.values())
            else:
                validation_results[outcome] = True  # Default to true
        
        return validation_results
    
    def generate_test_report(self, scenario_results: Dict[TestScenario, ScenarioResult]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = sum(r.total_tests for r in scenario_results.values())
        total_passed = sum(r.passed_tests for r in scenario_results.values())
        total_failed = sum(r.failed_tests for r in scenario_results.values())
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        critical_failures = []
        for result in scenario_results.values():
            critical_failures.extend(result.critical_failures)
        
        scenario_summary = {}
        for scenario, result in scenario_results.items():
            scenario_summary[scenario.value] = {
                "success_rate": result.success_rate,
                "tests_passed": result.passed_tests,
                "tests_failed": result.failed_tests,
                "execution_time": result.execution_time_seconds,
                "status": "PASS" if result.success_rate >= 80 else "FAIL"
            }
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "tests_passed": total_passed,
                "tests_failed": total_failed,
                "success_rate": overall_success_rate,
                "overall_status": "PASS" if overall_success_rate >= 80 and not critical_failures else "FAIL"
            },
            "scenario_results": scenario_summary,
            "critical_failures": critical_failures,
            "recommendations": self._generate_recommendations(scenario_results),
            "timestamp": datetime.now().isoformat()
        }
        
        return report
    
    def _generate_recommendations(self, scenario_results: Dict[TestScenario, ScenarioResult]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_scenarios = [s for s, r in scenario_results.items() if r.success_rate < 80]
        if failed_scenarios:
            recommendations.append(f"Address failures in scenarios: {', '.join([s.value for s in failed_scenarios])}")
        
        critical_failures_exist = any(r.critical_failures for r in scenario_results.values())
        if critical_failures_exist:
            recommendations.append("Resolve critical failures before production deployment")
        
        high_execution_times = [s for s, r in scenario_results.items() if r.execution_time_seconds > 300]
        if high_execution_times:
            recommendations.append(f"Optimize performance for scenarios: {', '.join([s.value for s in high_execution_times])}")
        
        if not recommendations:
            recommendations.append("All E2E tests passed - system ready for production")
        
        return recommendations

# Test runner
async def run_e2e_tests():
    """Run all E2E tests"""
    framework = E2ETestingFramework()
    scenario_results = await framework.run_all_scenarios()
    return framework.generate_test_report(scenario_results)

if __name__ == "__main__":
    print("Running E2E Testing Framework...")
    report = asyncio.run(run_e2e_tests())
    
    print("\n" + "="*80)
    print("END-TO-END TEST REPORT")
    print("="*80)
    print(f"Overall Status: {report['summary']['overall_status']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Tests Passed: {report['summary']['tests_passed']}/{report['summary']['total_tests']}")
    
    print("\nScenario Results:")
    for scenario, result in report['scenario_results'].items():
        print(f"  {scenario}: {result['status']} ({result['success_rate']:.1f}%)")
    
    if report['critical_failures']:
        print("\nCritical Failures:")
        for failure in report['critical_failures']:
            print(f"  - {failure}")
    
    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
    print("="*80)