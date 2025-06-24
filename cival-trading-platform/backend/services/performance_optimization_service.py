#!/usr/bin/env python3
"""
Phase 6: Performance Optimization Service
Advanced system monitoring, optimization, and self-healing capabilities
"""

import asyncio
import logging
import json
import psutil
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
from collections import deque, defaultdict
import statistics

from ..core.service_registry import get_registry
from ..models.llm_models import LLMRequest, LLMTaskType

logger = logging.getLogger(__name__)

class OptimizationLevel(Enum):
    """Optimization levels"""
    MINIMAL = "minimal"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    EMERGENCY = "emergency"

class MetricType(Enum):
    """Types of performance metrics"""
    SYSTEM = "system"
    SERVICE = "service"
    TRADING = "trading"
    LLM = "llm"
    DATABASE = "database"
    NETWORK = "network"

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    metric_name: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    threshold_warning: float
    threshold_critical: float
    source: str
    metadata: Dict[str, Any]

@dataclass
class OptimizationRecommendation:
    """System optimization recommendation"""
    recommendation_id: str
    priority: str  # low, medium, high, critical
    category: str
    title: str
    description: str
    impact_level: str
    estimated_improvement: str
    implementation_complexity: str
    auto_applicable: bool
    implementation_steps: List[str]
    estimated_cost: float
    estimated_benefit: float
    confidence_score: float
    created_at: datetime

@dataclass
class SystemAlert:
    """System performance alert"""
    alert_id: str
    severity: str  # info, warning, error, critical
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    service_affected: str
    auto_remediation: bool
    remediation_actions: List[str]
    timestamp: datetime

class PerformanceOptimizationService:
    """
    Advanced performance optimization service with AI-powered analysis,
    self-healing capabilities, and predictive optimization
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Core services
        self.llm_service = None
        
        # Performance data storage
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.system_alerts: List[SystemAlert] = []
        self.optimization_recommendations: List[OptimizationRecommendation] = []
        
        # Monitoring configuration
        self.config = {
            "monitoring_interval": 30,  # seconds
            "metrics_retention_hours": 24,
            "alert_cooldown_minutes": 5,
            "optimization_analysis_interval": 300,  # 5 minutes
            "auto_optimization_enabled": True,
            "emergency_thresholds": {
                "cpu_usage": 90.0,
                "memory_usage": 95.0,
                "disk_usage": 95.0,
                "response_time": 5000.0,  # ms
                "error_rate": 10.0  # %
            },
            "warning_thresholds": {
                "cpu_usage": 70.0,
                "memory_usage": 80.0,
                "disk_usage": 85.0,
                "response_time": 1000.0,  # ms
                "error_rate": 5.0  # %
            }
        }
        
        # Performance baseline
        self.performance_baseline: Dict[str, float] = {}
        self.optimization_history: List[Dict[str, Any]] = []
        
        # Active optimizations
        self.active_optimizations: Dict[str, Any] = {}
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Running tasks
        self.running_tasks: List[asyncio.Task] = []
        
        logger.info("PerformanceOptimizationService initialized")
    
    async def initialize(self):
        """Initialize the performance optimization service"""
        try:
            # Get required services
            self.llm_service = self.registry.get_service("llm_integration_service")
            
            # Establish performance baselines
            await self._establish_performance_baselines()
            
            # Start monitoring tasks
            await self._start_monitoring_tasks()
            
            logger.info("PerformanceOptimizationService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PerformanceOptimizationService: {e}")
            raise
    
    async def _start_monitoring_tasks(self):
        """Start all monitoring and optimization tasks"""
        self.running_tasks = [
            asyncio.create_task(self._system_metrics_monitor()),
            asyncio.create_task(self._service_performance_monitor()),
            asyncio.create_task(self._trading_performance_monitor()),
            asyncio.create_task(self._llm_performance_monitor()),
            asyncio.create_task(self._database_performance_monitor()),
            asyncio.create_task(self._network_performance_monitor()),
            asyncio.create_task(self._optimization_analyzer()),
            asyncio.create_task(self._auto_optimization_engine()),
            asyncio.create_task(self._predictive_scaling()),
            asyncio.create_task(self._alert_manager()),
        ]
        
        logger.info(f"Started {len(self.running_tasks)} monitoring and optimization tasks")
    
    async def _system_metrics_monitor(self):
        """Monitor system-level performance metrics"""
        while True:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0
                
                await self._record_metric(PerformanceMetric(
                    metric_name="system.cpu.usage_percent",
                    metric_type=MetricType.SYSTEM,
                    value=cpu_percent,
                    unit="percent",
                    timestamp=datetime.now(timezone.utc),
                    threshold_warning=self.config["warning_thresholds"]["cpu_usage"],
                    threshold_critical=self.config["emergency_thresholds"]["cpu_usage"],
                    source="psutil",
                    metadata={"cpu_count": cpu_count, "cpu_freq": cpu_freq}
                ))
                
                # Memory metrics
                memory = psutil.virtual_memory()
                await self._record_metric(PerformanceMetric(
                    metric_name="system.memory.usage_percent",
                    metric_type=MetricType.SYSTEM,
                    value=memory.percent,
                    unit="percent",
                    timestamp=datetime.now(timezone.utc),
                    threshold_warning=self.config["warning_thresholds"]["memory_usage"],
                    threshold_critical=self.config["emergency_thresholds"]["memory_usage"],
                    source="psutil",
                    metadata={"total": memory.total, "available": memory.available, "used": memory.used}
                ))
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                await self._record_metric(PerformanceMetric(
                    metric_name="system.disk.usage_percent",
                    metric_type=MetricType.SYSTEM,
                    value=disk_percent,
                    unit="percent",
                    timestamp=datetime.now(timezone.utc),
                    threshold_warning=self.config["warning_thresholds"]["disk_usage"],
                    threshold_critical=self.config["emergency_thresholds"]["disk_usage"],
                    source="psutil",
                    metadata={"total": disk.total, "used": disk.used, "free": disk.free}
                ))
                
                # Network metrics
                network = psutil.net_io_counters()
                await self._record_metric(PerformanceMetric(
                    metric_name="system.network.bytes_sent",
                    metric_type=MetricType.NETWORK,
                    value=network.bytes_sent,
                    unit="bytes",
                    timestamp=datetime.now(timezone.utc),
                    threshold_warning=float('inf'),
                    threshold_critical=float('inf'),
                    source="psutil",
                    metadata={"bytes_recv": network.bytes_recv, "packets_sent": network.packets_sent}
                ))
                
                await asyncio.sleep(self.config["monitoring_interval"])
                
            except Exception as e:
                logger.error(f"System metrics monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _service_performance_monitor(self):
        """Monitor service-level performance metrics"""
        while True:
            try:
                # Get service registry
                services = ["autonomous_trading_engine", "real_time_market_service", 
                          "llm_integration_service", "agent_coordinator", "risk_management_service"]
                
                for service_name in services:
                    service = self.registry.get_service(service_name)
                    if service and hasattr(service, 'get_performance_metrics'):
                        try:
                            metrics = await service.get_performance_metrics()
                            
                            for metric_name, value in metrics.items():
                                await self._record_metric(PerformanceMetric(
                                    metric_name=f"service.{service_name}.{metric_name}",
                                    metric_type=MetricType.SERVICE,
                                    value=float(value),
                                    unit="various",
                                    timestamp=datetime.now(timezone.utc),
                                    threshold_warning=1000.0,  # Default thresholds
                                    threshold_critical=5000.0,
                                    source=service_name,
                                    metadata={"service": service_name}
                                ))
                                
                        except Exception as e:
                            logger.error(f"Error getting metrics from {service_name}: {e}")
                
                await asyncio.sleep(self.config["monitoring_interval"])
                
            except Exception as e:
                logger.error(f"Service performance monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _trading_performance_monitor(self):
        """Monitor trading-specific performance metrics"""
        while True:
            try:
                # Get trading engine
                trading_engine = self.registry.get_service("autonomous_trading_engine")
                
                if trading_engine:
                    status = await trading_engine.get_status()
                    
                    # Record trading metrics
                    metrics_to_record = [
                        ("trading.opportunities.active", status.get("active_opportunities", 0)),
                        ("trading.orders.active", status.get("active_orders", 0)),
                        ("trading.performance.win_rate", status.get("performance_metrics", {}).get("win_rate", 0) * 100),
                        ("trading.performance.total_pnl", status.get("performance_metrics", {}).get("total_pnl", 0)),
                        ("trading.risk.exposure", status.get("performance_metrics", {}).get("risk_exposure", 0) * 100),
                    ]
                    
                    for metric_name, value in metrics_to_record:
                        await self._record_metric(PerformanceMetric(
                            metric_name=metric_name,
                            metric_type=MetricType.TRADING,
                            value=float(value),
                            unit="various",
                            timestamp=datetime.now(timezone.utc),
                            threshold_warning=float('inf'),
                            threshold_critical=float('inf'),
                            source="trading_engine",
                            metadata={"category": "trading_performance"}
                        ))
                
                await asyncio.sleep(self.config["monitoring_interval"])
                
            except Exception as e:
                logger.error(f"Trading performance monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _llm_performance_monitor(self):
        """Monitor LLM service performance"""
        while True:
            try:
                llm_service = self.registry.get_service("llm_integration_service")
                
                if llm_service and hasattr(llm_service, 'get_performance_metrics'):
                    metrics = await llm_service.get_performance_metrics()
                    
                    for provider, provider_metrics in metrics.items():
                        for metric_name, value in provider_metrics.items():
                            await self._record_metric(PerformanceMetric(
                                metric_name=f"llm.{provider}.{metric_name}",
                                metric_type=MetricType.LLM,
                                value=float(value),
                                unit="various",
                                timestamp=datetime.now(timezone.utc),
                                threshold_warning=2000.0 if "response_time" in metric_name else float('inf'),
                                threshold_critical=5000.0 if "response_time" in metric_name else float('inf'),
                                source="llm_service",
                                metadata={"provider": provider}
                            ))
                
                await asyncio.sleep(self.config["monitoring_interval"])
                
            except Exception as e:
                logger.error(f"LLM performance monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _database_performance_monitor(self):
        """Monitor database performance"""
        while True:
            try:
                # Mock database metrics - in production, this would connect to actual DB
                await self._record_metric(PerformanceMetric(
                    metric_name="database.connections.active",
                    metric_type=MetricType.DATABASE,
                    value=47.0,
                    unit="count",
                    timestamp=datetime.now(timezone.utc),
                    threshold_warning=80.0,
                    threshold_critical=100.0,
                    source="database",
                    metadata={"max_connections": 100}
                ))
                
                await self._record_metric(PerformanceMetric(
                    metric_name="database.query.avg_response_time",
                    metric_type=MetricType.DATABASE,
                    value=45.5,
                    unit="ms",
                    timestamp=datetime.now(timezone.utc),
                    threshold_warning=100.0,
                    threshold_critical=500.0,
                    source="database",
                    metadata={"queries_per_second": 150}
                ))
                
                await asyncio.sleep(self.config["monitoring_interval"])
                
            except Exception as e:
                logger.error(f"Database performance monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _network_performance_monitor(self):
        """Monitor network performance"""
        while True:
            try:
                # Test network latency to key services
                test_endpoints = [
                    "https://api.binance.com/api/v3/ping",
                    "https://api.openrouter.ai/v1/models",
                ]
                
                for endpoint in test_endpoints:
                    try:
                        start_time = time.time()
                        async with aiohttp.ClientSession() as session:
                            async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as response:
                                latency = (time.time() - start_time) * 1000  # ms
                                
                                await self._record_metric(PerformanceMetric(
                                    metric_name=f"network.latency.{endpoint.split('/')[2]}",
                                    metric_type=MetricType.NETWORK,
                                    value=latency,
                                    unit="ms",
                                    timestamp=datetime.now(timezone.utc),
                                    threshold_warning=200.0,
                                    threshold_critical=1000.0,
                                    source="network_monitor",
                                    metadata={"endpoint": endpoint, "status_code": response.status}
                                ))
                                
                    except Exception as e:
                        logger.error(f"Network test failed for {endpoint}: {e}")
                
                await asyncio.sleep(self.config["monitoring_interval"])
                
            except Exception as e:
                logger.error(f"Network performance monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _optimization_analyzer(self):
        """Analyze performance and generate optimization recommendations"""
        while True:
            try:
                # Analyze recent metrics for optimization opportunities
                recommendations = await self._analyze_optimization_opportunities()
                
                # Update recommendations
                self.optimization_recommendations.extend(recommendations)
                
                # Keep only recent recommendations
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                self.optimization_recommendations = [
                    r for r in self.optimization_recommendations 
                    if r.created_at > cutoff
                ]
                
                if recommendations:
                    logger.info(f"Generated {len(recommendations)} optimization recommendations")
                
                await asyncio.sleep(self.config["optimization_analysis_interval"])
                
            except Exception as e:
                logger.error(f"Optimization analyzer error: {e}")
                await asyncio.sleep(300)
    
    async def _analyze_optimization_opportunities(self) -> List[OptimizationRecommendation]:
        """Use LLM to analyze performance data and suggest optimizations"""
        recommendations = []
        
        try:
            # Prepare performance summary
            performance_summary = await self._generate_performance_summary()
            
            # Create LLM prompt for optimization analysis
            prompt = f"""
            Analyze the following system performance data and provide optimization recommendations.
            
            Performance Summary:
            {json.dumps(performance_summary, indent=2, default=str)}
            
            System Configuration:
            - Monitoring Interval: {self.config['monitoring_interval']}s
            - Auto Optimization: {self.config['auto_optimization_enabled']}
            - Emergency Thresholds: {json.dumps(self.config['emergency_thresholds'])}
            
            Provide optimization recommendations in JSON format:
            {{
                "recommendations": [
                    {{
                        "priority": "low|medium|high|critical",
                        "category": "performance|cost|reliability|security",
                        "title": "Short descriptive title",
                        "description": "Detailed description",
                        "impact_level": "low|medium|high",
                        "estimated_improvement": "Quantified improvement estimate",
                        "implementation_complexity": "low|medium|high",
                        "auto_applicable": true/false,
                        "implementation_steps": ["step1", "step2"],
                        "estimated_cost": 0.0,
                        "estimated_benefit": 100.0,
                        "confidence_score": 0.0-1.0
                    }}
                ]
            }}
            
            Focus on actionable, specific recommendations with measurable benefits.
            """
            
            if self.llm_service:
                request = LLMRequest(
                    task_type=LLMTaskType.PERFORMANCE_ANALYSIS,
                    prompt=prompt,
                    context={"performance_data": performance_summary}
                )
                
                response = await self.llm_service.process_llm_request(request)
                analysis = json.loads(response.content)
                
                # Create recommendation objects
                for rec_data in analysis.get("recommendations", []):
                    recommendation = OptimizationRecommendation(
                        recommendation_id=f"opt_{int(time.time())}_{len(recommendations)}",
                        priority=rec_data.get("priority", "medium"),
                        category=rec_data.get("category", "performance"),
                        title=rec_data.get("title", "Optimization Recommendation"),
                        description=rec_data.get("description", ""),
                        impact_level=rec_data.get("impact_level", "medium"),
                        estimated_improvement=rec_data.get("estimated_improvement", "Unknown"),
                        implementation_complexity=rec_data.get("implementation_complexity", "medium"),
                        auto_applicable=rec_data.get("auto_applicable", False),
                        implementation_steps=rec_data.get("implementation_steps", []),
                        estimated_cost=float(rec_data.get("estimated_cost", 0.0)),
                        estimated_benefit=float(rec_data.get("estimated_benefit", 0.0)),
                        confidence_score=float(rec_data.get("confidence_score", 0.5)),
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to analyze optimization opportunities: {e}")
            return []
    
    async def _auto_optimization_engine(self):
        """Automatically apply safe optimizations"""
        while True:
            try:
                if not self.config["auto_optimization_enabled"]:
                    await asyncio.sleep(300)
                    continue
                
                # Find auto-applicable optimizations
                auto_optimizations = [
                    r for r in self.optimization_recommendations
                    if r.auto_applicable and r.priority in ["medium", "high", "critical"]
                    and r.confidence_score >= 0.7
                ]
                
                for optimization in auto_optimizations:
                    if optimization.recommendation_id not in self.active_optimizations:
                        success = await self._apply_optimization(optimization)
                        
                        if success:
                            self.active_optimizations[optimization.recommendation_id] = {
                                "optimization": optimization,
                                "applied_at": datetime.now(timezone.utc),
                                "status": "active"
                            }
                            
                            logger.info(f"Auto-applied optimization: {optimization.title}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Auto optimization engine error: {e}")
                await asyncio.sleep(300)
    
    async def _apply_optimization(self, optimization: OptimizationRecommendation) -> bool:
        """Apply a specific optimization"""
        try:
            # Mock optimization application - in production, this would implement actual optimizations
            logger.info(f"Applying optimization: {optimization.title}")
            
            # Simulate optimization steps
            for step in optimization.implementation_steps:
                logger.info(f"Executing step: {step}")
                await asyncio.sleep(1)  # Simulate work
            
            # Record optimization in history
            self.optimization_history.append({
                "optimization_id": optimization.recommendation_id,
                "title": optimization.title,
                "applied_at": datetime.now(timezone.utc),
                "estimated_benefit": optimization.estimated_benefit,
                "implementation_complexity": optimization.implementation_complexity
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply optimization {optimization.title}: {e}")
            return False
    
    async def _record_metric(self, metric: PerformanceMetric):
        """Record a performance metric and check thresholds"""
        # Store metric
        self.metrics_history[metric.metric_name].append(metric)
        
        # Check thresholds and generate alerts
        await self._check_metric_thresholds(metric)
    
    async def _check_metric_thresholds(self, metric: PerformanceMetric):
        """Check metric against thresholds and generate alerts"""
        alert_severity = None
        
        if metric.value >= metric.threshold_critical:
            alert_severity = "critical"
        elif metric.value >= metric.threshold_warning:
            alert_severity = "warning"
        
        if alert_severity:
            # Check alert cooldown
            last_alert_key = f"{metric.metric_name}_{alert_severity}"
            now = datetime.now(timezone.utc)
            
            if (last_alert_key not in self.last_alert_times or 
                now - self.last_alert_times[last_alert_key] > timedelta(minutes=self.config["alert_cooldown_minutes"])):
                
                alert = SystemAlert(
                    alert_id=f"alert_{int(time.time())}_{metric.metric_name}",
                    severity=alert_severity,
                    metric_name=metric.metric_name,
                    current_value=metric.value,
                    threshold_value=metric.threshold_critical if alert_severity == "critical" else metric.threshold_warning,
                    message=f"{metric.metric_name} is {metric.value:.2f}{metric.unit}, exceeding {alert_severity} threshold",
                    service_affected=metric.source,
                    auto_remediation=alert_severity == "critical",
                    remediation_actions=await self._get_remediation_actions(metric.metric_name, alert_severity),
                    timestamp=now
                )
                
                self.system_alerts.append(alert)
                self.last_alert_times[last_alert_key] = now
                
                logger.warning(f"Generated {alert_severity} alert: {alert.message}")
                
                # Trigger auto-remediation for critical alerts
                if alert.auto_remediation:
                    await self._trigger_auto_remediation(alert)
    
    async def _get_remediation_actions(self, metric_name: str, severity: str) -> List[str]:
        """Get remediation actions for a specific metric and severity"""
        remediation_map = {
            "system.cpu.usage_percent": [
                "Scale down non-critical services",
                "Increase process priority for critical services",
                "Enable CPU throttling for background tasks"
            ],
            "system.memory.usage_percent": [
                "Clear application caches",
                "Restart memory-intensive services",
                "Enable memory compression"
            ],
            "system.disk.usage_percent": [
                "Clean temporary files",
                "Archive old log files",
                "Remove unused data"
            ]
        }
        
        return remediation_map.get(metric_name, ["Manual investigation required"])
    
    async def _trigger_auto_remediation(self, alert: SystemAlert):
        """Trigger automatic remediation for critical alerts"""
        try:
            logger.info(f"Triggering auto-remediation for alert: {alert.alert_id}")
            
            for action in alert.remediation_actions:
                logger.info(f"Executing remediation action: {action}")
                # Mock remediation - in production, this would execute actual remediation
                await asyncio.sleep(1)
            
            logger.info(f"Completed auto-remediation for alert: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Auto-remediation failed for alert {alert.alert_id}: {e}")
    
    async def get_performance_overview(self) -> Dict[str, Any]:
        """Get comprehensive performance overview"""
        recent_metrics = {}
        
        # Get latest metrics for each type
        for metric_name, history in self.metrics_history.items():
            if history:
                recent_metrics[metric_name] = asdict(history[-1])
        
        # Get active alerts
        active_alerts = [asdict(alert) for alert in self.system_alerts[-10:]]
        
        # Get recent recommendations
        recent_recommendations = [asdict(rec) for rec in self.optimization_recommendations[-5:]]
        
        return {
            "system_health": self._calculate_system_health(),
            "recent_metrics": recent_metrics,
            "active_alerts": active_alerts,
            "optimization_recommendations": recent_recommendations,
            "active_optimizations": len(self.active_optimizations),
            "performance_trends": await self._calculate_performance_trends(),
            "resource_utilization": await self._get_resource_utilization(),
            "service_status": await self._get_service_status_summary()
        }
    
    def _calculate_system_health(self) -> float:
        """Calculate overall system health score (0-100)"""
        health_score = 100.0
        
        # Check recent critical alerts
        recent_critical = len([a for a in self.system_alerts[-20:] if a.severity == "critical"])
        health_score -= recent_critical * 20
        
        # Check resource utilization
        if "system.cpu.usage_percent" in self.metrics_history:
            latest_cpu = self.metrics_history["system.cpu.usage_percent"][-1].value
            if latest_cpu > 90:
                health_score -= 30
            elif latest_cpu > 70:
                health_score -= 15
        
        if "system.memory.usage_percent" in self.metrics_history:
            latest_memory = self.metrics_history["system.memory.usage_percent"][-1].value
            if latest_memory > 95:
                health_score -= 25
            elif latest_memory > 80:
                health_score -= 10
        
        return max(0, min(100, health_score))
    
    async def stop(self):
        """Stop the performance optimization service"""
        # Cancel all running tasks
        for task in self.running_tasks:
            task.cancel()
        
        await asyncio.gather(*self.running_tasks, return_exceptions=True)
        
        logger.info("PerformanceOptimizationService stopped")
    
    # Placeholder methods for additional functionality
    async def _establish_performance_baselines(self): pass
    async def _predictive_scaling(self): pass
    async def _alert_manager(self): pass
    async def _generate_performance_summary(self): return {}
    async def _calculate_performance_trends(self): return {}
    async def _get_resource_utilization(self): return {}
    async def _get_service_status_summary(self): return {}