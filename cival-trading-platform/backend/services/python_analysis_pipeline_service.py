"""
Python Analysis Pipeline Service - Phase 18
Advanced Python code analysis and execution pipeline for trading strategies
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import subprocess
import ast
import sys
import traceback
import tempfile
import os
from pathlib import Path

import redis.asyncio as redis
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    SYNTAX_CHECK = "syntax_check"
    STATIC_ANALYSIS = "static_analysis"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    SECURITY_SCAN = "security_scan"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    CODE_QUALITY = "code_quality"
    EXECUTION_ANALYSIS = "execution_analysis"

class ExecutionMode(Enum):
    SANDBOX = "sandbox"
    ISOLATED = "isolated"
    VALIDATION = "validation"
    PRODUCTION = "production"

class AnalysisStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class PythonScript:
    """Python script for analysis"""
    script_id: str
    name: str
    code: str
    language: str = "python"
    version: str = "3.11"
    dependencies: List[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class AnalysisRequest:
    """Analysis request configuration"""
    request_id: str
    script_id: str
    analysis_types: List[AnalysisType]
    execution_mode: ExecutionMode
    timeout_seconds: int
    parameters: Dict[str, Any]
    created_at: datetime
    priority: int = 5

@dataclass
class AnalysisResult:
    """Analysis result with detailed metrics"""
    request_id: str
    script_id: str
    analysis_type: AnalysisType
    status: AnalysisStatus
    result: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    execution_time_ms: float
    memory_usage_mb: float
    timestamp: datetime

@dataclass
class ExecutionResult:
    """Code execution result"""
    execution_id: str
    script_id: str
    success: bool
    output: str
    error_output: str
    return_value: Any
    execution_time_ms: float
    memory_peak_mb: float
    cpu_usage_percent: float
    timestamp: datetime

class PythonAnalysisPipelineService:
    """
    Comprehensive Python analysis and execution pipeline
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # Pipeline management
        self.scripts: Dict[str, PythonScript] = {}
        self.analysis_requests: Dict[str, AnalysisRequest] = {}
        self.analysis_results: Dict[str, List[AnalysisResult]] = {}
        self.execution_history: List[ExecutionResult] = []
        
        # Analysis configurations
        self.analysis_configs = {
            AnalysisType.SYNTAX_CHECK: {
                "enabled": True,
                "timeout": 5,
                "tools": ["ast", "py_compile"]
            },
            AnalysisType.STATIC_ANALYSIS: {
                "enabled": True,
                "timeout": 30,
                "tools": ["pylint", "flake8", "mypy"]
            },
            AnalysisType.PERFORMANCE_ANALYSIS: {
                "enabled": True,
                "timeout": 60,
                "tools": ["cProfile", "memory_profiler"]
            },
            AnalysisType.SECURITY_SCAN: {
                "enabled": True,
                "timeout": 45,
                "tools": ["bandit", "safety"]
            },
            AnalysisType.DEPENDENCY_ANALYSIS: {
                "enabled": True,
                "timeout": 30,
                "tools": ["pipdeptree", "pip-audit"]
            },
            AnalysisType.CODE_QUALITY: {
                "enabled": True,
                "timeout": 45,
                "tools": ["radon", "vulture"]
            }
        }
        
        # Execution environments
        self.execution_environments = {
            ExecutionMode.SANDBOX: {
                "timeout": 30,
                "memory_limit_mb": 256,
                "allowed_modules": ["math", "datetime", "json", "decimal", "typing"],
                "restricted_builtins": ["exec", "eval", "compile", "__import__"]
            },
            ExecutionMode.ISOLATED: {
                "timeout": 60,
                "memory_limit_mb": 512,
                "allowed_modules": ["pandas", "numpy", "ta", "ccxt"],
                "restricted_builtins": ["exec", "eval"]
            },
            ExecutionMode.VALIDATION: {
                "timeout": 120,
                "memory_limit_mb": 1024,
                "allowed_modules": ["*"],
                "restricted_builtins": []
            }
        }
        
        # Initialize mock data
        self._initialize_mock_data()
        
        logger.info("PythonAnalysisPipelineService initialized")
    
    def _initialize_mock_data(self):
        """Initialize with mock Python scripts and analysis data"""
        # Create mock trading strategy scripts
        mock_scripts = [
            {
                "name": "Moving Average Strategy",
                "code": '''
import pandas as pd
import numpy as np

def moving_average_strategy(prices, short_window=10, long_window=30):
    """
    Simple moving average crossover strategy
    """
    data = pd.DataFrame({'price': prices})
    data['short_ma'] = data['price'].rolling(window=short_window).mean()
    data['long_ma'] = data['price'].rolling(window=long_window).mean()
    
    # Generate signals
    data['signal'] = 0
    data['signal'][short_window:] = np.where(
        data['short_ma'][short_window:] > data['long_ma'][short_window:], 1, 0
    )
    data['positions'] = data['signal'].diff()
    
    return data

# Example usage
prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112]
result = moving_average_strategy(prices)
print(f"Generated {len(result)} signals")
''',
                "dependencies": ["pandas", "numpy"],
                "metadata": {"type": "trading_strategy", "complexity": "low"}
            },
            {
                "name": "Risk Calculator",
                "code": '''
import math
from decimal import Decimal

def calculate_position_size(account_balance, risk_percentage, entry_price, stop_loss):
    """
    Calculate position size based on risk management rules
    """
    risk_amount = Decimal(str(account_balance)) * Decimal(str(risk_percentage)) / 100
    price_diff = abs(Decimal(str(entry_price)) - Decimal(str(stop_loss)))
    
    if price_diff == 0:
        return 0
    
    position_size = risk_amount / price_diff
    return float(position_size)

def calculate_var(returns, confidence_level=0.95):
    """
    Calculate Value at Risk (VaR)
    """
    sorted_returns = sorted(returns)
    index = int((1 - confidence_level) * len(sorted_returns))
    return sorted_returns[index] if index < len(sorted_returns) else 0

# Example usage
balance = 10000
risk_pct = 2
entry = 100
stop = 95
size = calculate_position_size(balance, risk_pct, entry, stop)
print(f"Position size: {size}")
''',
                "dependencies": ["decimal"],
                "metadata": {"type": "risk_management", "complexity": "medium"}
            },
            {
                "name": "Market Data Analyzer",
                "code": '''
def analyze_price_action(ohlc_data):
    """
    Analyze price action patterns
    """
    patterns = []
    
    for i in range(1, len(ohlc_data)):
        prev = ohlc_data[i-1]
        curr = ohlc_data[i]
        
        # Bullish engulfing
        if (curr['open'] < prev['close'] and 
            curr['close'] > prev['open'] and
            curr['close'] > curr['open']):
            patterns.append({'index': i, 'pattern': 'bullish_engulfing'})
        
        # Bearish engulfing
        elif (curr['open'] > prev['close'] and 
              curr['close'] < prev['open'] and
              curr['close'] < curr['open']):
            patterns.append({'index': i, 'pattern': 'bearish_engulfing'})
    
    return patterns

# Mock data
ohlc = [
    {'open': 100, 'high': 105, 'low': 99, 'close': 103},
    {'open': 103, 'high': 108, 'low': 101, 'close': 106},
    {'open': 106, 'high': 109, 'low': 104, 'close': 105}
]

patterns = analyze_price_action(ohlc)
print(f"Found {len(patterns)} patterns")
''',
                "dependencies": [],
                "metadata": {"type": "market_analysis", "complexity": "medium"}
            }
        ]
        
        for i, script_data in enumerate(mock_scripts):
            script_id = f"script_{i+1}"
            script = PythonScript(
                script_id=script_id,
                name=script_data["name"],
                code=script_data["code"],
                dependencies=script_data["dependencies"],
                metadata=script_data["metadata"]
            )
            self.scripts[script_id] = script
        
        # Create mock analysis results
        for script_id in self.scripts.keys():
            results = []
            for analysis_type in [AnalysisType.SYNTAX_CHECK, AnalysisType.STATIC_ANALYSIS, AnalysisType.CODE_QUALITY]:
                result = AnalysisResult(
                    request_id=f"req_{script_id}_{analysis_type.value}",
                    script_id=script_id,
                    analysis_type=analysis_type,
                    status=AnalysisStatus.COMPLETED,
                    result=self._generate_mock_analysis_result(analysis_type),
                    errors=[],
                    warnings=["Unused import 'sys'" if analysis_type == AnalysisType.STATIC_ANALYSIS else ""],
                    execution_time_ms=150.0 + hash(script_id) % 100,
                    memory_usage_mb=45.2 + hash(script_id) % 20,
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=hash(script_id) % 60)
                )
                results.append(result)
            self.analysis_results[script_id] = results
        
        # Create mock execution history
        for i, script_id in enumerate(list(self.scripts.keys())[:3]):
            execution = ExecutionResult(
                execution_id=f"exec_{i+1}",
                script_id=script_id,
                success=True,
                output=f"Execution completed successfully for {self.scripts[script_id].name}",
                error_output="",
                return_value={"status": "success", "result": f"Mock result {i+1}"},
                execution_time_ms=250.0 + i*50,
                memory_peak_mb=128.5 + i*25,
                cpu_usage_percent=15.2 + i*5,
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=i*15)
            )
            self.execution_history.append(execution)

    def _generate_mock_analysis_result(self, analysis_type: AnalysisType) -> Dict[str, Any]:
        """Generate mock analysis results"""
        if analysis_type == AnalysisType.SYNTAX_CHECK:
            return {
                "syntax_valid": True,
                "parse_errors": [],
                "ast_nodes": 45,
                "complexity_score": 3.2
            }
        elif analysis_type == AnalysisType.STATIC_ANALYSIS:
            return {
                "pylint_score": 8.5,
                "flake8_issues": 2,
                "mypy_errors": 0,
                "code_style_violations": ["E302: expected 2 blank lines"],
                "maintainability_index": 85.4
            }
        elif analysis_type == AnalysisType.PERFORMANCE_ANALYSIS:
            return {
                "execution_time_estimate": "0.025s",
                "memory_estimate": "12.5MB",
                "cpu_complexity": "O(n)",
                "bottlenecks": ["pandas operations"]
            }
        elif analysis_type == AnalysisType.SECURITY_SCAN:
            return {
                "security_score": 9.2,
                "vulnerabilities": [],
                "warnings": ["Use of eval() detected (low severity)"],
                "safe_dependencies": True
            }
        elif analysis_type == AnalysisType.CODE_QUALITY:
            return {
                "cyclomatic_complexity": 4.2,
                "maintainability_index": 78.5,
                "lines_of_code": 45,
                "documentation_coverage": 85.0,
                "test_coverage": 0.0
            }
        else:
            return {"analysis_type": analysis_type.value, "status": "completed"}

    async def initialize(self):
        """Initialize the Python analysis pipeline service"""
        try:
            # Load scripts from database if available
            await self._load_scripts()
            
            # Start background processing
            asyncio.create_task(self._analysis_processing_loop())
            asyncio.create_task(self._performance_monitoring_loop())
            asyncio.create_task(self._cleanup_loop())
            
            logger.info("PythonAnalysisPipelineService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PythonAnalysisPipelineService: {e}")
            pass  # Continue with mock data

    async def submit_script(self, script_data: Dict[str, Any]) -> PythonScript:
        """Submit a Python script for analysis"""
        try:
            script_id = str(uuid.uuid4())
            
            script = PythonScript(
                script_id=script_id,
                name=script_data["name"],
                code=script_data["code"],
                language=script_data.get("language", "python"),
                version=script_data.get("version", "3.11"),
                dependencies=script_data.get("dependencies", []),
                metadata=script_data.get("metadata", {})
            )
            
            self.scripts[script_id] = script
            
            # Save to database if available
            if self.supabase:
                script_dict = asdict(script)
                self.supabase.table('python_scripts').insert(script_dict).execute()
            
            logger.info(f"Submitted Python script: {script_id}")
            return script
            
        except Exception as e:
            logger.error(f"Failed to submit script: {e}")
            raise

    async def run_analysis(self, 
                         script_id: str,
                         analysis_types: List[AnalysisType],
                         execution_mode: ExecutionMode = ExecutionMode.SANDBOX,
                         timeout: int = 60) -> str:
        """Run analysis on a Python script"""
        try:
            if script_id not in self.scripts:
                raise ValueError(f"Script {script_id} not found")
            
            request_id = str(uuid.uuid4())
            
            request = AnalysisRequest(
                request_id=request_id,
                script_id=script_id,
                analysis_types=analysis_types,
                execution_mode=execution_mode,
                timeout_seconds=timeout,
                parameters={},
                created_at=datetime.now(timezone.utc)
            )
            
            self.analysis_requests[request_id] = request
            
            # Start analysis processing
            asyncio.create_task(self._process_analysis_request(request))
            
            logger.info(f"Started analysis request: {request_id}")
            return request_id
            
        except Exception as e:
            logger.error(f"Failed to run analysis: {e}")
            raise

    async def execute_script(self, 
                           script_id: str,
                           execution_mode: ExecutionMode = ExecutionMode.SANDBOX,
                           parameters: Dict[str, Any] = None) -> ExecutionResult:
        """Execute a Python script with safety measures"""
        try:
            script = self.scripts.get(script_id)
            if not script:
                raise ValueError(f"Script {script_id} not found")
            
            execution_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)
            
            # Create safe execution environment
            exec_env = self.execution_environments.get(execution_mode, self.execution_environments[ExecutionMode.SANDBOX])
            
            # Mock execution - in real implementation, this would use subprocess/docker
            await asyncio.sleep(0.2)  # Simulate execution time
            
            end_time = datetime.now(timezone.utc)
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            result = ExecutionResult(
                execution_id=execution_id,
                script_id=script_id,
                success=True,
                output=f"Script '{script.name}' executed successfully",
                error_output="",
                return_value={"status": "success", "message": "Mock execution completed"},
                execution_time_ms=execution_time,
                memory_peak_mb=exec_env["memory_limit_mb"] * 0.3,  # Mock memory usage
                cpu_usage_percent=25.5,
                timestamp=end_time
            )
            
            self.execution_history.append(result)
            
            # Save to database if available
            if self.supabase:
                result_dict = asdict(result)
                result_dict["timestamp"] = result.timestamp.isoformat()
                self.supabase.table('execution_results').insert(result_dict).execute()
            
            logger.info(f"Executed script {script_id} in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            # Create error result
            result = ExecutionResult(
                execution_id=execution_id if 'execution_id' in locals() else str(uuid.uuid4()),
                script_id=script_id,
                success=False,
                output="",
                error_output=str(e),
                return_value=None,
                execution_time_ms=0.0,
                memory_peak_mb=0.0,
                cpu_usage_percent=0.0,
                timestamp=datetime.now(timezone.utc)
            )
            self.execution_history.append(result)
            logger.error(f"Failed to execute script {script_id}: {e}")
            return result

    async def get_analysis_results(self, script_id: str) -> List[AnalysisResult]:
        """Get analysis results for a script"""
        return self.analysis_results.get(script_id, [])

    async def get_script_analytics(self, script_id: str = None) -> Dict[str, Any]:
        """Get comprehensive script analytics"""
        try:
            if script_id:
                # Script-specific analytics
                script = self.scripts.get(script_id)
                if not script:
                    return {"error": f"Script {script_id} not found"}
                
                results = self.analysis_results.get(script_id, [])
                executions = [e for e in self.execution_history if e.script_id == script_id]
                
                return {
                    "script_info": {
                        "script_id": script.script_id,
                        "name": script.name,
                        "language": script.language,
                        "version": script.version,
                        "dependencies": script.dependencies,
                        "lines_of_code": len(script.code.split('\n')),
                        "character_count": len(script.code)
                    },
                    "analysis_summary": {
                        "total_analyses": len(results),
                        "completed_analyses": len([r for r in results if r.status == AnalysisStatus.COMPLETED]),
                        "failed_analyses": len([r for r in results if r.status == AnalysisStatus.FAILED]),
                        "avg_analysis_time_ms": sum(r.execution_time_ms for r in results) / len(results) if results else 0
                    },
                    "execution_summary": {
                        "total_executions": len(executions),
                        "successful_executions": len([e for e in executions if e.success]),
                        "failed_executions": len([e for e in executions if not e.success]),
                        "avg_execution_time_ms": sum(e.execution_time_ms for e in executions) / len(executions) if executions else 0,
                        "avg_memory_usage_mb": sum(e.memory_peak_mb for e in executions) / len(executions) if executions else 0
                    },
                    "quality_metrics": {
                        "syntax_score": 10.0,  # Mock score
                        "complexity_score": 7.5,
                        "maintainability_index": 85.2,
                        "security_score": 9.1
                    },
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            else:
                # Overall analytics
                total_scripts = len(self.scripts)
                total_analyses = sum(len(results) for results in self.analysis_results.values())
                total_executions = len(self.execution_history)
                
                return {
                    "overview": {
                        "total_scripts": total_scripts,
                        "total_analyses": total_analyses,
                        "total_executions": total_executions,
                        "successful_executions": len([e for e in self.execution_history if e.success]),
                        "avg_execution_time_ms": sum(e.execution_time_ms for e in self.execution_history) / len(self.execution_history) if self.execution_history else 0
                    },
                    "script_breakdown": {
                        script_type: len([s for s in self.scripts.values() if s.metadata and s.metadata.get("type") == script_type])
                        for script_type in ["trading_strategy", "risk_management", "market_analysis", "other"]
                    },
                    "analysis_performance": {
                        analysis_type.value: {
                            "total_runs": len([r for results in self.analysis_results.values() for r in results if r.analysis_type == analysis_type]),
                            "avg_time_ms": sum(r.execution_time_ms for results in self.analysis_results.values() for r in results if r.analysis_type == analysis_type) / max(len([r for results in self.analysis_results.values() for r in results if r.analysis_type == analysis_type]), 1)
                        } for analysis_type in AnalysisType
                    },
                    "execution_trends": {
                        "hourly_executions": [len([e for e in self.execution_history if e.timestamp.hour == hour]) for hour in range(24)],
                        "success_rate": len([e for e in self.execution_history if e.success]) / len(self.execution_history) if self.execution_history else 0
                    },
                    "resource_usage": {
                        "avg_memory_mb": sum(e.memory_peak_mb for e in self.execution_history) / len(self.execution_history) if self.execution_history else 0,
                        "avg_cpu_percent": sum(e.cpu_usage_percent for e in self.execution_history) / len(self.execution_history) if self.execution_history else 0,
                        "peak_memory_mb": max((e.memory_peak_mb for e in self.execution_history), default=0),
                        "peak_cpu_percent": max((e.cpu_usage_percent for e in self.execution_history), default=0)
                    },
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get script analytics: {e}")
            return {"error": str(e)}

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get comprehensive pipeline status"""
        try:
            pending_requests = len([r for r in self.analysis_requests.values()])
            recent_executions = [e for e in self.execution_history if e.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)]
            
            return {
                "pipeline_status": "running",
                "processing_queue": {
                    "pending_requests": pending_requests,
                    "active_analyses": 0,  # Mock
                    "queue_depth": pending_requests
                },
                "script_metrics": {
                    "total_scripts": len(self.scripts),
                    "analyzed_scripts": len(self.analysis_results),
                    "executed_scripts": len(set(e.script_id for e in self.execution_history))
                },
                "performance_metrics": {
                    "recent_executions_1h": len(recent_executions),
                    "avg_execution_time_ms": sum(e.execution_time_ms for e in recent_executions) / len(recent_executions) if recent_executions else 0,
                    "success_rate": len([e for e in recent_executions if e.success]) / len(recent_executions) if recent_executions else 0
                },
                "resource_utilization": {
                    "cpu_usage_percent": 15.2,  # Mock
                    "memory_usage_mb": 245.8,   # Mock
                    "disk_usage_mb": 1024.5     # Mock
                },
                "analysis_capabilities": {
                    analysis_type.value: config["enabled"]
                    for analysis_type, config in self.analysis_configs.items()
                },
                "execution_modes": list(self.execution_environments.keys()),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return {"error": str(e)}

    async def _process_analysis_request(self, request: AnalysisRequest):
        """Process an analysis request"""
        try:
            script = self.scripts.get(request.script_id)
            if not script:
                logger.error(f"Script {request.script_id} not found for analysis")
                return
            
            results = []
            for analysis_type in request.analysis_types:
                start_time = datetime.now(timezone.utc)
                
                # Mock analysis processing
                await asyncio.sleep(0.1)
                
                end_time = datetime.now(timezone.utc)
                execution_time = (end_time - start_time).total_seconds() * 1000
                
                result = AnalysisResult(
                    request_id=request.request_id,
                    script_id=request.script_id,
                    analysis_type=analysis_type,
                    status=AnalysisStatus.COMPLETED,
                    result=self._generate_mock_analysis_result(analysis_type),
                    errors=[],
                    warnings=[],
                    execution_time_ms=execution_time,
                    memory_usage_mb=50.0,
                    timestamp=end_time
                )
                results.append(result)
            
            # Store results
            if request.script_id not in self.analysis_results:
                self.analysis_results[request.script_id] = []
            self.analysis_results[request.script_id].extend(results)
            
            # Clean up request
            self.analysis_requests.pop(request.request_id, None)
            
        except Exception as e:
            logger.error(f"Failed to process analysis request {request.request_id}: {e}")

    async def _load_scripts(self):
        """Load scripts from database"""
        try:
            if self.supabase:
                response = self.supabase.table('python_scripts').select('*').execute()
                for script_data in response.data:
                    script = PythonScript(
                        script_id=script_data["script_id"],
                        name=script_data["name"],
                        code=script_data["code"],
                        language=script_data["language"],
                        version=script_data["version"],
                        dependencies=script_data["dependencies"],
                        metadata=script_data["metadata"]
                    )
                    self.scripts[script.script_id] = script
        except Exception as e:
            logger.warning(f"Could not load scripts from database: {e}")

    async def _analysis_processing_loop(self):
        """Background analysis processing"""
        while True:
            try:
                await asyncio.sleep(10)  # Process every 10 seconds
                # Process pending analysis requests
                for request in list(self.analysis_requests.values()):
                    asyncio.create_task(self._process_analysis_request(request))
                logger.debug("Analysis processing loop completed")
            except Exception as e:
                logger.error(f"Error in analysis processing loop: {e}")

    async def _performance_monitoring_loop(self):
        """Background performance monitoring"""
        while True:
            try:
                await asyncio.sleep(60)  # Monitor every minute
                # Monitor system performance
                logger.debug("Performance monitoring completed")
            except Exception as e:
                logger.error(f"Error in performance monitoring loop: {e}")

    async def _cleanup_loop(self):
        """Background cleanup of old data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
                
                # Clean old execution history
                self.execution_history = [e for e in self.execution_history if e.timestamp > cutoff_time]
                
                logger.debug("Cleanup loop completed")
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        return {
            "service": "python_analysis_pipeline_service",
            "status": "running",
            "scripts_loaded": len(self.scripts),
            "pending_analyses": len(self.analysis_requests),
            "total_executions": len(self.execution_history),
            "analysis_types_supported": len(self.analysis_configs),
            "execution_modes_available": len(self.execution_environments),
            "last_update": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_python_analysis_pipeline_service():
    """Factory function to create PythonAnalysisPipelineService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = PythonAnalysisPipelineService(redis_client, supabase_client)
    return service