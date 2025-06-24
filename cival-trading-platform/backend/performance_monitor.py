#!/usr/bin/env python3
"""
Performance Monitoring and Metrics System
Real-time performance tracking and comprehensive metrics collection
"""

import asyncio
import json
import logging
import time
import psutil
import os
import gc
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field
import uuid
from enum import Enum
import numpy as np
from collections import defaultdict, deque
import aiohttp
import asyncpg
import redis
import threading
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/performance_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Performance Monitoring & Metrics System",
    description="Real-time performance tracking and comprehensive metrics collection",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"

class MetricCategory(str, Enum):
    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS = "business"
    NETWORK = "network"
    DATABASE = "database"

# Data models
@dataclass
class MetricValue:
    timestamp: str
    value: float
    tags: Dict[str, str]
    metadata: Dict[str, Any]

@dataclass
class Metric:
    id: str
    name: str
    type: MetricType
    category: MetricCategory
    description: str
    unit: str
    values: deque
    aggregations: Dict[str, float]
    thresholds: Dict[str, float]
    created_at: str

@dataclass
class Alert:
    id: str
    name: str
    description: str
    severity: AlertSeverity
    metric_id: str
    threshold_value: float
    current_value: float
    condition: str  # gt, lt, eq, ne
    triggered_at: str
    resolved_at: Optional[str]
    status: str  # active, resolved, suppressed
    actions: List[str]

@dataclass
class ServiceHealth:
    service_name: str
    status: ServiceStatus
    last_check: str
    response_time: float
    error_rate: float
    uptime_percentage: float
    dependencies: List[str]
    health_score: float
    issues: List[str]
    recommendations: List[str]

@dataclass
class PerformanceReport:
    id: str
    timestamp: str
    timeframe: str
    system_metrics: Dict[str, Any]
    application_metrics: Dict[str, Any]
    business_metrics: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    trends: Dict[str, str]
    recommendations: List[str]
    overall_score: float

class MetricRequest(BaseModel):
    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    type: MetricType = Field(default=MetricType.GAUGE, description="Metric type")
    category: MetricCategory = Field(default=MetricCategory.APPLICATION, description="Metric category")
    tags: Dict[str, str] = Field(default={}, description="Metric tags")
    unit: str = Field(default="", description="Metric unit")

class AlertRule(BaseModel):
    metric_name: str = Field(..., description="Metric to monitor")
    condition: str = Field(..., description="Alert condition (gt, lt, eq, ne)")
    threshold: float = Field(..., description="Threshold value")
    severity: AlertSeverity = Field(..., description="Alert severity")
    description: str = Field(default="", description="Alert description")

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
        self.alerts = {}
        self.alert_rules = {}
        self.services = {}
        self.reports = {}
        
        # Performance tracking
        self.request_times = deque(maxlen=10000)
        self.error_counts = defaultdict(int)
        self.throughput_counter = 0
        self.last_throughput_reset = time.time()
        
        # System monitoring
        self.system_metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.anomaly_detector = AnomalyDetector()
        
        # Background tasks
        self.monitoring_active = True
        
        # Initialize MCP services to monitor
        self._initialize_monitored_services()
        
        # Start monitoring tasks
        asyncio.create_task(self._system_monitoring_loop())
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._alert_processing_loop())
        asyncio.create_task(self._cleanup_old_data())
        
        logger.info("Performance Monitor initialized")
    
    def _initialize_monitored_services(self):
        """Initialize list of MCP services to monitor"""
        services = [
            {"name": "market_data_server", "url": "http://localhost:8001/health", "port": 8001},
            {"name": "historical_data_server", "url": "http://localhost:8002/health", "port": 8002},
            {"name": "trading_engine", "url": "http://localhost:8010/health", "port": 8010},
            {"name": "order_management", "url": "http://localhost:8011/health", "port": 8011},
            {"name": "risk_management", "url": "http://localhost:8012/health", "port": 8012},
            {"name": "portfolio_tracker", "url": "http://localhost:8013/health", "port": 8013},
            {"name": "octagon_intelligence", "url": "http://localhost:8020/health", "port": 8020},
            {"name": "mongodb_intelligence", "url": "http://localhost:8021/health", "port": 8021},
            {"name": "neo4j_intelligence", "url": "http://localhost:8022/health", "port": 8022},
            {"name": "ai_prediction_engine", "url": "http://localhost:8050/health", "port": 8050},
            {"name": "technical_analysis_engine", "url": "http://localhost:8051/health", "port": 8051},
            {"name": "ml_portfolio_optimizer", "url": "http://localhost:8052/health", "port": 8052},
            {"name": "sentiment_analysis_engine", "url": "http://localhost:8053/health", "port": 8053},
            {"name": "optimization_engine", "url": "http://localhost:8060/health", "port": 8060},
            {"name": "load_balancer", "url": "http://localhost:8070/health", "port": 8070},
        ]
        
        for service in services:
            self.services[service["name"]] = ServiceHealth(
                service_name=service["name"],
                status=ServiceStatus.HEALTHY,
                last_check=datetime.now().isoformat(),
                response_time=0.0,
                error_rate=0.0,
                uptime_percentage=100.0,
                dependencies=[],
                health_score=1.0,
                issues=[],
                recommendations=[]
            )
        
        logger.info(f"Initialized monitoring for {len(services)} MCP services")
    
    async def record_metric(self, request: MetricRequest) -> str:
        """Record a new metric value"""
        metric_id = f"{request.category.value}_{request.name}"
        
        if metric_id not in self.metrics:
            self.metrics[metric_id] = Metric(
                id=metric_id,
                name=request.name,
                type=request.type,
                category=request.category,
                description=f"{request.name} metric",
                unit=request.unit,
                values=deque(maxlen=10000),
                aggregations={},
                thresholds={},
                created_at=datetime.now().isoformat()
            )
        
        metric = self.metrics[metric_id]
        
        # Create metric value
        metric_value = MetricValue(
            timestamp=datetime.now().isoformat(),
            value=request.value,
            tags=request.tags,
            metadata={}
        )
        
        metric.values.append(metric_value)
        
        # Update aggregations
        await self._update_metric_aggregations(metric)
        
        # Check for alerts
        await self._check_metric_alerts(metric)
        
        # Store in time series for anomaly detection
        self.system_metrics_history[metric_id].append({
            "timestamp": time.time(),
            "value": request.value
        })
        
        return metric_id
    
    async def _update_metric_aggregations(self, metric: Metric):
        """Update metric aggregations (min, max, avg, etc.)"""
        if not metric.values:
            return
        
        values = [v.value for v in metric.values]
        
        # Calculate basic aggregations
        metric.aggregations = {
            "min": min(values),
            "max": max(values),
            "avg": np.mean(values),
            "median": np.median(values),
            "std": np.std(values),
            "count": len(values),
            "sum": sum(values)
        }
        
        # Calculate percentiles
        if len(values) > 1:
            metric.aggregations.update({
                "p50": np.percentile(values, 50),
                "p90": np.percentile(values, 90),
                "p95": np.percentile(values, 95),
                "p99": np.percentile(values, 99)
            })
        
        # Calculate rate for counters
        if metric.type == MetricType.COUNTER and len(metric.values) > 1:
            recent_values = list(metric.values)[-60:]  # Last 60 values
            if len(recent_values) > 1:
                time_diff = (datetime.fromisoformat(recent_values[-1].timestamp.replace('Z', '+00:00').replace('+00:00', '')) - 
                           datetime.fromisoformat(recent_values[0].timestamp.replace('Z', '+00:00').replace('+00:00', ''))).total_seconds()
                if time_diff > 0:
                    value_diff = recent_values[-1].value - recent_values[0].value
                    metric.aggregations["rate_per_second"] = value_diff / time_diff
    
    async def _check_metric_alerts(self, metric: Metric):
        """Check if metric values trigger any alerts"""
        if not metric.values:
            return
        
        current_value = metric.values[-1].value
        
        for rule_id, rule in self.alert_rules.items():
            if rule.metric_name != metric.name:
                continue
            
            triggered = False
            
            if rule.condition == "gt" and current_value > rule.threshold:
                triggered = True
            elif rule.condition == "lt" and current_value < rule.threshold:
                triggered = True
            elif rule.condition == "eq" and abs(current_value - rule.threshold) < 0.001:
                triggered = True
            elif rule.condition == "ne" and abs(current_value - rule.threshold) >= 0.001:
                triggered = True
            
            if triggered:
                await self._trigger_alert(rule, metric, current_value)
    
    async def _trigger_alert(self, rule: AlertRule, metric: Metric, current_value: float):
        """Trigger an alert"""
        alert_id = f"{rule.metric_name}_{rule.condition}_{rule.threshold}"
        
        # Check if alert is already active
        if alert_id in self.alerts and self.alerts[alert_id].status == "active":
            return
        
        alert = Alert(
            id=alert_id,
            name=f"{rule.metric_name} {rule.condition} {rule.threshold}",
            description=rule.description or f"Metric {rule.metric_name} triggered alert condition",
            severity=rule.severity,
            metric_id=metric.id,
            threshold_value=rule.threshold,
            current_value=current_value,
            condition=rule.condition,
            triggered_at=datetime.now().isoformat(),
            resolved_at=None,
            status="active",
            actions=["log", "notify"]
        )
        
        self.alerts[alert_id] = alert
        
        # Execute alert actions
        await self._execute_alert_actions(alert)
        
        logger.warning(f"Alert triggered: {alert.name} - Current value: {current_value}, Threshold: {rule.threshold}")
    
    async def _execute_alert_actions(self, alert: Alert):
        """Execute alert actions"""
        for action in alert.actions:
            if action == "log":
                logger.warning(f"ALERT: {alert.name} - {alert.description}")
            elif action == "notify":
                # In a real implementation, this would send notifications
                logger.info(f"Notification sent for alert: {alert.name}")
    
    async def add_alert_rule(self, rule: AlertRule) -> str:
        """Add a new alert rule"""
        rule_id = str(uuid.uuid4())
        self.alert_rules[rule_id] = rule
        
        logger.info(f"Added alert rule: {rule.metric_name} {rule.condition} {rule.threshold}")
        
        return rule_id
    
    async def _system_monitoring_loop(self):
        """Background task to monitor system metrics"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Collect application metrics
                await self._collect_application_metrics()
                
                # Run anomaly detection
                await self._detect_anomalies()
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in system monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_metric(MetricRequest(
                name="cpu_usage_percent",
                value=cpu_percent,
                type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                unit="percent"
            ))
            
            # Memory metrics
            memory = psutil.virtual_memory()
            await self.record_metric(MetricRequest(
                name="memory_usage_percent",
                value=memory.percent,
                type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                unit="percent"
            ))
            
            await self.record_metric(MetricRequest(
                name="memory_available_bytes",
                value=memory.available,
                type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                unit="bytes"
            ))
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            await self.record_metric(MetricRequest(
                name="disk_usage_percent",
                value=(disk.used / disk.total) * 100,
                type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                unit="percent"
            ))
            
            # Network metrics
            net_io = psutil.net_io_counters()
            await self.record_metric(MetricRequest(
                name="network_bytes_sent",
                value=net_io.bytes_sent,
                type=MetricType.COUNTER,
                category=MetricCategory.NETWORK,
                unit="bytes"
            ))
            
            await self.record_metric(MetricRequest(
                name="network_bytes_received",
                value=net_io.bytes_recv,
                type=MetricType.COUNTER,
                category=MetricCategory.NETWORK,
                unit="bytes"
            ))
            
            # Process metrics
            process = psutil.Process()
            await self.record_metric(MetricRequest(
                name="process_memory_rss",
                value=process.memory_info().rss,
                type=MetricType.GAUGE,
                category=MetricCategory.APPLICATION,
                unit="bytes"
            ))
            
            await self.record_metric(MetricRequest(
                name="process_cpu_percent",
                value=process.cpu_percent(),
                type=MetricType.GAUGE,
                category=MetricCategory.APPLICATION,
                unit="percent"
            ))
            
            # File descriptor count
            try:
                fd_count = process.num_fds() if hasattr(process, 'num_fds') else 0
                await self.record_metric(MetricRequest(
                    name="open_file_descriptors",
                    value=fd_count,
                    type=MetricType.GAUGE,
                    category=MetricCategory.SYSTEM,
                    unit="count"
                ))
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        try:
            # Garbage collection metrics
            gc_stats = gc.get_stats()
            if gc_stats:
                for i, stat in enumerate(gc_stats):
                    await self.record_metric(MetricRequest(
                        name=f"gc_collections_gen{i}",
                        value=stat.get("collections", 0),
                        type=MetricType.COUNTER,
                        category=MetricCategory.APPLICATION,
                        unit="count"
                    ))
            
            # Thread count
            thread_count = threading.active_count()
            await self.record_metric(MetricRequest(
                name="active_threads",
                value=thread_count,
                type=MetricType.GAUGE,
                category=MetricCategory.APPLICATION,
                unit="count"
            ))
            
            # Calculate current throughput
            current_time = time.time()
            time_since_reset = current_time - self.last_throughput_reset
            
            if time_since_reset >= 60:  # Reset every minute
                throughput = self.throughput_counter / time_since_reset
                await self.record_metric(MetricRequest(
                    name="requests_per_second",
                    value=throughput,
                    type=MetricType.GAUGE,
                    category=MetricCategory.APPLICATION,
                    unit="requests/sec"
                ))
                
                self.throughput_counter = 0
                self.last_throughput_reset = current_time
            
            # Response time percentiles
            if self.request_times:
                response_times = list(self.request_times)
                await self.record_metric(MetricRequest(
                    name="response_time_p95",
                    value=np.percentile(response_times, 95),
                    type=MetricType.GAUGE,
                    category=MetricCategory.APPLICATION,
                    unit="milliseconds"
                ))
                
                await self.record_metric(MetricRequest(
                    name="response_time_avg",
                    value=np.mean(response_times),
                    type=MetricType.GAUGE,
                    category=MetricCategory.APPLICATION,
                    unit="milliseconds"
                ))
            
            # Error rate
            total_errors = sum(self.error_counts.values())
            total_requests = len(self.request_times) + total_errors
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
            
            await self.record_metric(MetricRequest(
                name="error_rate_percent",
                value=error_rate,
                type=MetricType.GAUGE,
                category=MetricCategory.APPLICATION,
                unit="percent"
            ))
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
    
    async def _health_check_loop(self):
        """Background task to check service health"""
        while self.monitoring_active:
            try:
                for service_name, service in self.services.items():
                    await self._check_service_health(service)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)
    
    async def _check_service_health(self, service: ServiceHealth):
        """Check health of a specific service"""
        try:
            # Determine URL from service name
            port_map = {
                "market_data_server": 8001,
                "historical_data_server": 8002,
                "trading_engine": 8010,
                "order_management": 8011,
                "risk_management": 8012,
                "portfolio_tracker": 8013,
                "octagon_intelligence": 8020,
                "mongodb_intelligence": 8021,
                "neo4j_intelligence": 8022,
                "ai_prediction_engine": 8050,
                "technical_analysis_engine": 8051,
                "ml_portfolio_optimizer": 8052,
                "sentiment_analysis_engine": 8053,
                "optimization_engine": 8060,
                "load_balancer": 8070,
            }
            
            port = port_map.get(service.service_name, 8000)
            url = f"http://localhost:{port}/health"
            
            start_time = time.time()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                try:
                    async with session.get(url) as response:
                        response_time = (time.time() - start_time) * 1000
                        
                        if response.status == 200:
                            service.status = ServiceStatus.HEALTHY
                            service.response_time = response_time
                            service.issues = []
                        else:
                            service.status = ServiceStatus.DEGRADED
                            service.issues = [f"HTTP {response.status} response"]
                            
                except asyncio.TimeoutError:
                    service.status = ServiceStatus.UNHEALTHY
                    service.response_time = 5000  # Timeout value
                    service.issues = ["Request timeout"]
                    
                except Exception as e:
                    service.status = ServiceStatus.DOWN
                    service.response_time = 0
                    service.issues = [f"Connection error: {str(e)}"]
            
            service.last_check = datetime.now().isoformat()
            
            # Calculate health score
            if service.status == ServiceStatus.HEALTHY:
                service.health_score = 1.0
            elif service.status == ServiceStatus.DEGRADED:
                service.health_score = 0.7
            elif service.status == ServiceStatus.UNHEALTHY:
                service.health_score = 0.3
            else:  # DOWN
                service.health_score = 0.0
            
            # Update uptime calculation (simplified)
            if service.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
                service.uptime_percentage = min(100.0, service.uptime_percentage + 0.1)
            else:
                service.uptime_percentage = max(0.0, service.uptime_percentage - 1.0)
            
            # Record service metrics
            await self.record_metric(MetricRequest(
                name=f"service_health_score",
                value=service.health_score,
                type=MetricType.GAUGE,
                category=MetricCategory.APPLICATION,
                tags={"service": service.service_name},
                unit="score"
            ))
            
            await self.record_metric(MetricRequest(
                name=f"service_response_time",
                value=service.response_time,
                type=MetricType.GAUGE,
                category=MetricCategory.APPLICATION,
                tags={"service": service.service_name},
                unit="milliseconds"
            ))
            
        except Exception as e:
            logger.error(f"Error checking health for {service.service_name}: {e}")
            service.status = ServiceStatus.DOWN
            service.issues = [f"Health check error: {str(e)}"]
    
    async def _detect_anomalies(self):
        """Detect anomalies in metrics"""
        try:
            for metric_id, history in self.system_metrics_history.items():
                if len(history) < 10:  # Need minimum data points
                    continue
                
                values = [point["value"] for point in history]
                anomalies = self.anomaly_detector.detect_anomalies(values)
                
                if anomalies:
                    logger.warning(f"Anomalies detected in {metric_id}: {len(anomalies)} points")
                    
                    # Record anomaly metric
                    await self.record_metric(MetricRequest(
                        name="anomalies_detected",
                        value=len(anomalies),
                        type=MetricType.COUNTER,
                        category=MetricCategory.APPLICATION,
                        tags={"metric": metric_id},
                        unit="count"
                    ))
                    
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
    
    async def _alert_processing_loop(self):
        """Background task to process and resolve alerts"""
        while self.monitoring_active:
            try:
                current_time = datetime.now()
                
                for alert_id, alert in list(self.alerts.items()):
                    if alert.status == "active":
                        # Check if alert should be auto-resolved
                        triggered_time = datetime.fromisoformat(alert.triggered_at.replace('Z', '+00:00').replace('+00:00', ''))
                        
                        # Auto-resolve after 1 hour if not manually resolved
                        if current_time - triggered_time > timedelta(hours=1):
                            alert.status = "resolved"
                            alert.resolved_at = current_time.isoformat()
                            logger.info(f"Auto-resolved alert: {alert.name}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in alert processing loop: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_data(self):
        """Background task to cleanup old data"""
        while self.monitoring_active:
            try:
                # Clean up old metric values (keep last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                for metric in self.metrics.values():
                    # Remove old values
                    while (metric.values and 
                           datetime.fromisoformat(metric.values[0].timestamp.replace('Z', '+00:00').replace('+00:00', '')) < cutoff_time):
                        metric.values.popleft()
                
                # Clean up resolved alerts older than 7 days
                alert_cutoff = datetime.now() - timedelta(days=7)
                alerts_to_remove = []
                
                for alert_id, alert in self.alerts.items():
                    if (alert.status == "resolved" and alert.resolved_at and
                        datetime.fromisoformat(alert.resolved_at.replace('Z', '+00:00').replace('+00:00', '')) < alert_cutoff):
                        alerts_to_remove.append(alert_id)
                
                for alert_id in alerts_to_remove:
                    del self.alerts[alert_id]
                
                if alerts_to_remove:
                    logger.info(f"Cleaned up {len(alerts_to_remove)} old resolved alerts")
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    def record_request_time(self, duration_ms: float):
        """Record request response time"""
        self.request_times.append(duration_ms)
        self.throughput_counter += 1
    
    def record_error(self, error_type: str):
        """Record an error occurrence"""
        self.error_counts[error_type] += 1
    
    async def generate_performance_report(self, timeframe: str = "1h") -> PerformanceReport:
        """Generate comprehensive performance report"""
        report_id = str(uuid.uuid4())
        
        # Parse timeframe
        if timeframe == "1h":
            cutoff_time = datetime.now() - timedelta(hours=1)
        elif timeframe == "1d":
            cutoff_time = datetime.now() - timedelta(days=1)
        elif timeframe == "1w":
            cutoff_time = datetime.now() - timedelta(weeks=1)
        else:
            cutoff_time = datetime.now() - timedelta(hours=1)
        
        # Collect system metrics
        system_metrics = {}
        application_metrics = {}
        business_metrics = {}
        
        for metric in self.metrics.values():
            if not metric.values:
                continue
            
            # Filter values by timeframe
            recent_values = [v for v in metric.values 
                           if datetime.fromisoformat(v.timestamp.replace('Z', '+00:00').replace('+00:00', '')) >= cutoff_time]
            
            if not recent_values:
                continue
            
            metric_summary = {
                "current": recent_values[-1].value,
                "min": min(v.value for v in recent_values),
                "max": max(v.value for v in recent_values),
                "avg": np.mean([v.value for v in recent_values]),
                "trend": self._calculate_trend([v.value for v in recent_values])
            }
            
            if metric.category == MetricCategory.SYSTEM:
                system_metrics[metric.name] = metric_summary
            elif metric.category == MetricCategory.APPLICATION:
                application_metrics[metric.name] = metric_summary
            elif metric.category == MetricCategory.BUSINESS:
                business_metrics[metric.name] = metric_summary
        
        # Detect anomalies
        anomalies = []
        for metric_id, history in self.system_metrics_history.items():
            if len(history) >= 10:
                values = [point["value"] for point in history]
                detected_anomalies = self.anomaly_detector.detect_anomalies(values)
                if detected_anomalies:
                    anomalies.append({
                        "metric": metric_id,
                        "anomaly_count": len(detected_anomalies),
                        "severity": "high" if len(detected_anomalies) > 5 else "medium"
                    })
        
        # Generate trends
        trends = {}
        for metric_name, metric_data in {**system_metrics, **application_metrics}.items():
            trends[metric_name] = metric_data.get("trend", "stable")
        
        # Generate recommendations
        recommendations = await self._generate_performance_recommendations(
            system_metrics, application_metrics, anomalies)
        
        # Calculate overall performance score
        overall_score = await self._calculate_overall_performance_score(
            system_metrics, application_metrics, anomalies)
        
        report = PerformanceReport(
            id=report_id,
            timestamp=datetime.now().isoformat(),
            timeframe=timeframe,
            system_metrics=system_metrics,
            application_metrics=application_metrics,
            business_metrics=business_metrics,
            anomalies=anomalies,
            trends=trends,
            recommendations=recommendations,
            overall_score=overall_score
        )
        
        self.reports[report_id] = report
        
        logger.info(f"Generated performance report: {overall_score:.1f}% overall score")
        
        return report
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        threshold = np.std(values) * 0.1  # 10% of standard deviation
        
        if slope > threshold:
            return "increasing"
        elif slope < -threshold:
            return "decreasing"
        else:
            return "stable"
    
    async def _generate_performance_recommendations(self, system_metrics: Dict, 
                                                  application_metrics: Dict,
                                                  anomalies: List[Dict]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # CPU recommendations
        cpu_usage = system_metrics.get("cpu_usage_percent", {})
        if cpu_usage.get("avg", 0) > 80:
            recommendations.append("High CPU usage detected - consider scaling horizontally or optimizing algorithms")
        
        # Memory recommendations
        memory_usage = system_metrics.get("memory_usage_percent", {})
        if memory_usage.get("avg", 0) > 85:
            recommendations.append("High memory usage - investigate memory leaks and optimize data structures")
        
        # Response time recommendations
        response_time = application_metrics.get("response_time_avg", {})
        if response_time.get("avg", 0) > 1000:  # 1 second
            recommendations.append("High response times - optimize queries and add caching layers")
        
        # Error rate recommendations
        error_rate = application_metrics.get("error_rate_percent", {})
        if error_rate.get("avg", 0) > 5:
            recommendations.append("High error rate detected - review error logs and improve error handling")
        
        # Anomaly recommendations
        if len(anomalies) > 3:
            recommendations.append("Multiple anomalies detected - investigate unusual patterns in system behavior")
        
        # Disk usage recommendations
        disk_usage = system_metrics.get("disk_usage_percent", {})
        if disk_usage.get("current", 0) > 90:
            recommendations.append("Critical disk usage - clean up logs and temporary files immediately")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    async def _calculate_overall_performance_score(self, system_metrics: Dict,
                                                 application_metrics: Dict,
                                                 anomalies: List[Dict]) -> float:
        """Calculate overall performance score (0-100)"""
        scores = []
        
        # CPU score
        cpu_usage = system_metrics.get("cpu_usage_percent", {}).get("avg", 0)
        cpu_score = max(0, 100 - cpu_usage)
        scores.append(cpu_score)
        
        # Memory score
        memory_usage = system_metrics.get("memory_usage_percent", {}).get("avg", 0)
        memory_score = max(0, 100 - memory_usage)
        scores.append(memory_score)
        
        # Response time score
        response_time = application_metrics.get("response_time_avg", {}).get("avg", 0)
        response_score = max(0, 100 - min(100, response_time / 20))  # 2000ms = 0 score
        scores.append(response_score)
        
        # Error rate score
        error_rate = application_metrics.get("error_rate_percent", {}).get("avg", 0)
        error_score = max(0, 100 - error_rate * 10)  # 10% error = 0 score
        scores.append(error_score)
        
        # Anomaly penalty
        anomaly_penalty = min(50, len(anomalies) * 10)
        
        # Calculate weighted average
        overall_score = np.mean(scores) - anomaly_penalty
        
        return max(0, min(100, overall_score))

class AnomalyDetector:
    """Simple anomaly detection using statistical methods"""
    
    def detect_anomalies(self, values: List[float], threshold: float = 2.0) -> List[int]:
        """Detect anomalies using z-score method"""
        if len(values) < 5:
            return []
        
        values_array = np.array(values)
        mean = np.mean(values_array)
        std = np.std(values_array)
        
        if std == 0:
            return []
        
        z_scores = np.abs((values_array - mean) / std)
        anomalies = np.where(z_scores > threshold)[0].tolist()
        
        return anomalies

# Initialize the performance monitor
monitor = PerformanceMonitor()

# Middleware to track request metrics
@app.middleware("http")
async def track_requests(request, call_next):
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        monitor.record_request_time(duration_ms)
        
        return response
        
    except Exception as e:
        monitor.record_error(type(e).__name__)
        raise

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Performance Monitor & Metrics System",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "metrics_collection",
            "performance_monitoring",
            "anomaly_detection",
            "alerting",
            "health_checking",
            "performance_reporting"
        ],
        "metrics_count": len(monitor.metrics),
        "active_alerts": len([a for a in monitor.alerts.values() if a.status == "active"]),
        "services_monitored": len(monitor.services)
    }

@app.post("/metrics/record")
async def record_metric(request: MetricRequest):
    """Record a metric value"""
    try:
        metric_id = await monitor.record_metric(request)
        return {"metric_id": metric_id, "status": "recorded"}
        
    except Exception as e:
        logger.error(f"Error recording metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics(category: MetricCategory = None):
    """Get all metrics or filtered by category"""
    metrics = monitor.metrics
    
    if category:
        metrics = {k: v for k, v in metrics.items() if v.category == category}
    
    return {
        "metrics": [asdict(metric) for metric in metrics.values()],
        "total": len(metrics)
    }

@app.get("/metrics/{metric_id}")
async def get_metric(metric_id: str):
    """Get specific metric details"""
    if metric_id not in monitor.metrics:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    return {"metric": asdict(monitor.metrics[metric_id])}

@app.post("/alerts/rules")
async def add_alert_rule(rule: AlertRule):
    """Add a new alert rule"""
    try:
        rule_id = await monitor.add_alert_rule(rule)
        return {"rule_id": rule_id, "status": "created"}
        
    except Exception as e:
        logger.error(f"Error creating alert rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts")
async def get_alerts(status: str = None):
    """Get alerts, optionally filtered by status"""
    alerts = monitor.alerts
    
    if status:
        alerts = {k: v for k, v in alerts.items() if v.status == status}
    
    return {
        "alerts": [asdict(alert) for alert in alerts.values()],
        "total": len(alerts)
    }

@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an active alert"""
    if alert_id not in monitor.alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = monitor.alerts[alert_id]
    alert.status = "resolved"
    alert.resolved_at = datetime.now().isoformat()
    
    return {"status": "resolved", "alert_id": alert_id}

@app.get("/services/health")
async def get_services_health():
    """Get health status of all monitored services"""
    return {
        "services": [asdict(service) for service in monitor.services.values()],
        "summary": {
            "total": len(monitor.services),
            "healthy": len([s for s in monitor.services.values() if s.status == ServiceStatus.HEALTHY]),
            "degraded": len([s for s in monitor.services.values() if s.status == ServiceStatus.DEGRADED]),
            "unhealthy": len([s for s in monitor.services.values() if s.status == ServiceStatus.UNHEALTHY]),
            "down": len([s for s in monitor.services.values() if s.status == ServiceStatus.DOWN])
        }
    }

@app.get("/services/{service_name}/health")
async def get_service_health(service_name: str):
    """Get health status of a specific service"""
    if service_name not in monitor.services:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return {"service": asdict(monitor.services[service_name])}

@app.get("/reports/performance")
async def generate_performance_report(timeframe: str = "1h"):
    """Generate performance report"""
    try:
        report = await monitor.generate_performance_report(timeframe)
        return {"report": asdict(report)}
        
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/{report_id}")
async def get_performance_report(report_id: str):
    """Get a specific performance report"""
    if report_id not in monitor.reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {"report": asdict(monitor.reports[report_id])}

@app.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard summary data"""
    # Calculate summary statistics
    total_metrics = len(monitor.metrics)
    active_alerts = len([a for a in monitor.alerts.values() if a.status == "active"])
    healthy_services = len([s for s in monitor.services.values() if s.status == ServiceStatus.HEALTHY])
    total_services = len(monitor.services)
    
    # Get recent metrics
    recent_metrics = {}
    for metric in monitor.metrics.values():
        if metric.values:
            recent_metrics[metric.name] = {
                "current": metric.values[-1].value,
                "unit": metric.unit,
                "trend": monitor._calculate_trend([v.value for v in list(metric.values)[-10:]])
            }
    
    return {
        "summary": {
            "total_metrics": total_metrics,
            "active_alerts": active_alerts,
            "healthy_services": healthy_services,
            "total_services": total_services,
            "service_health_percentage": (healthy_services / total_services * 100) if total_services > 0 else 0
        },
        "recent_metrics": recent_metrics,
        "system_status": "healthy" if active_alerts == 0 else "degraded" if active_alerts < 5 else "critical"
    }

@app.get("/system/status")
async def get_system_status():
    """Get overall system status"""
    # Calculate system health score
    healthy_services = len([s for s in monitor.services.values() if s.status == ServiceStatus.HEALTHY])
    total_services = len(monitor.services)
    active_alerts = len([a for a in monitor.alerts.values() if a.status == "active"])
    
    # Get key metrics
    key_metrics = {}
    for metric_name in ["cpu_usage_percent", "memory_usage_percent", "response_time_avg", "error_rate_percent"]:
        for metric in monitor.metrics.values():
            if metric.name == metric_name and metric.values:
                key_metrics[metric_name] = metric.values[-1].value
                break
    
    # Calculate overall health
    if healthy_services == total_services and active_alerts == 0:
        overall_status = "healthy"
    elif healthy_services >= total_services * 0.8 and active_alerts < 3:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "overall_status": overall_status,
        "service_health": f"{healthy_services}/{total_services}",
        "active_alerts": active_alerts,
        "key_metrics": key_metrics,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "performance_monitor:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )