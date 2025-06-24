#!/usr/bin/env python3
"""
System Health Monitor and Dashboard
Comprehensive monitoring service for the entire MCP trading platform
"""

import asyncio
import json
import logging
import aiohttp
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
from pydantic import BaseModel, Field
import uuid
import time
import psutil
import socket
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/system_health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="System Health Monitor",
    description="Comprehensive health monitoring and dashboard for MCP Trading Platform",
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
class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(str, Enum):
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    RATE = "rate"

# Data models
@dataclass
class ServiceHealth:
    service_name: str
    service_id: str
    url: str
    port: int
    status: ServiceStatus
    response_time_ms: float
    last_check: str
    uptime_percentage: float
    error_count: int
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    requests_per_minute: float
    throughput: float
    availability_24h: float
    latency_p95: float
    metadata: Dict[str, Any]

@dataclass
class SystemMetric:
    id: str
    name: str
    type: MetricType
    value: float
    unit: str
    timestamp: str
    service_name: str
    tags: Dict[str, str]
    threshold_warning: float
    threshold_critical: float

@dataclass
class SystemAlert:
    id: str
    title: str
    description: str
    severity: AlertSeverity
    service_name: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: str
    resolved: bool
    resolution_time: Optional[str]

@dataclass
class PerformanceProfile:
    service_name: str
    timestamp: str
    requests_per_second: float
    response_time_p50: float
    response_time_p95: float
    response_time_p99: float
    error_rate_percentage: float
    throughput_mbps: float
    concurrent_connections: int
    memory_usage_percentage: float
    cpu_usage_percentage: float
    disk_io_rate: float

class SystemHealthMonitor:
    """Comprehensive system health monitoring"""
    
    def __init__(self):
        self.services = {}
        self.metrics = {}
        self.alerts = {}
        self.performance_profiles = {}
        self.active_websockets = []
        self.monitoring_active = True
        
        # Service configurations
        self.service_configs = {
            "market_data": {"url": "http://localhost:8001", "port": 8001, "critical": True},
            "historical_data": {"url": "http://localhost:8002", "port": 8002, "critical": False},
            "trading_engine": {"url": "http://localhost:8010", "port": 8010, "critical": True},
            "order_management": {"url": "http://localhost:8011", "port": 8011, "critical": True},
            "risk_management": {"url": "http://localhost:8012", "port": 8012, "critical": True},
            "portfolio_tracker": {"url": "http://localhost:8013", "port": 8013, "critical": True},
            "octagon_intelligence": {"url": "http://localhost:8020", "port": 8020, "critical": False},
            "mongodb_intelligence": {"url": "http://localhost:8021", "port": 8021, "critical": False},
            "neo4j_intelligence": {"url": "http://localhost:8022", "port": 8022, "critical": False},
            "ai_prediction": {"url": "http://localhost:8050", "port": 8050, "critical": False},
            "technical_analysis": {"url": "http://localhost:8051", "port": 8051, "critical": False},
            "ml_portfolio_optimizer": {"url": "http://localhost:8052", "port": 8052, "critical": False},
            "sentiment_analysis": {"url": "http://localhost:8053", "port": 8053, "critical": False},
            "optimization_engine": {"url": "http://localhost:8060", "port": 8060, "critical": False},
            "load_balancer": {"url": "http://localhost:8070", "port": 8070, "critical": True},
            "performance_monitor": {"url": "http://localhost:8080", "port": 8080, "critical": False},
            "trading_strategies": {"url": "http://localhost:8090", "port": 8090, "critical": False},
            "risk_management_advanced": {"url": "http://localhost:8091", "port": 8091, "critical": False},
            "market_microstructure": {"url": "http://localhost:8092", "port": 8092, "critical": False},
            "external_data_integration": {"url": "http://localhost:8093", "port": 8093, "critical": False}
        }
        
        # Initialize monitoring
        self._initialize_services()
        
        # Start background tasks
        asyncio.create_task(self._monitor_services())
        asyncio.create_task(self._collect_metrics())
        asyncio.create_task(self._check_alerts())
        asyncio.create_task(self._broadcast_updates())
        
        logger.info("System Health Monitor initialized")
    
    def _initialize_services(self):
        """Initialize service health tracking"""
        for service_name, config in self.service_configs.items():
            service_id = str(uuid.uuid4())
            
            service_health = ServiceHealth(
                service_name=service_name,
                service_id=service_id,
                url=config["url"],
                port=config["port"],
                status=ServiceStatus.UNKNOWN,
                response_time_ms=0.0,
                last_check=datetime.now().isoformat(),
                uptime_percentage=0.0,
                error_count=0,
                error_rate=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                requests_per_minute=0.0,
                throughput=0.0,
                availability_24h=0.0,
                latency_p95=0.0,
                metadata={"critical": config["critical"]}
            )
            
            self.services[service_name] = service_health
        
        logger.info(f"Initialized health tracking for {len(self.service_configs)} services")
    
    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """Check health of a specific service"""
        if service_name not in self.services:
            raise ValueError(f"Service {service_name} not found")
        
        service = self.services[service_name]
        start_time = time.time()
        
        try:
            # Health check request
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(f"{service.url}/health", timeout=timeout) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    service.response_time_ms = response_time_ms
                    service.last_check = datetime.now().isoformat()
                    
                    if response.status == 200:
                        service.status = ServiceStatus.HEALTHY
                        
                        # Try to get additional metrics from health endpoint
                        try:
                            health_data = await response.json()
                            if isinstance(health_data, dict):
                                service.metadata.update(health_data)
                        except:
                            pass
                    
                    elif response.status in [503, 502, 504]:
                        service.status = ServiceStatus.DEGRADED
                        service.error_count += 1
                    else:
                        service.status = ServiceStatus.UNHEALTHY
                        service.error_count += 1
        
        except asyncio.TimeoutError:
            service.status = ServiceStatus.UNHEALTHY
            service.response_time_ms = 10000  # Timeout value
            service.error_count += 1
            service.last_check = datetime.now().isoformat()
        
        except Exception as e:
            service.status = ServiceStatus.CRITICAL if service.metadata.get("critical") else ServiceStatus.UNHEALTHY
            service.response_time_ms = (time.time() - start_time) * 1000
            service.error_count += 1
            service.last_check = datetime.now().isoformat()
            logger.error(f"Health check failed for {service_name}: {e}")
        
        return service
    
    async def _monitor_services(self):
        """Background task to monitor all services"""
        while self.monitoring_active:
            try:
                # Check all services in parallel
                tasks = []
                for service_name in self.services.keys():
                    task = self.check_service_health(service_name)
                    tasks.append(task)
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update aggregated metrics
                await self._update_system_metrics()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in service monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _collect_metrics(self):
        """Background task to collect system metrics"""
        while self.monitoring_active:
            try:
                timestamp = datetime.now().isoformat()
                
                # System-wide metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()
                
                # Create system metrics
                system_metrics = [
                    SystemMetric(
                        id=str(uuid.uuid4()),
                        name="cpu_usage",
                        type=MetricType.GAUGE,
                        value=cpu_percent,
                        unit="percent",
                        timestamp=timestamp,
                        service_name="system",
                        tags={"type": "system"},
                        threshold_warning=70.0,
                        threshold_critical=90.0
                    ),
                    SystemMetric(
                        id=str(uuid.uuid4()),
                        name="memory_usage",
                        type=MetricType.GAUGE,
                        value=memory.percent,
                        unit="percent",
                        timestamp=timestamp,
                        service_name="system",
                        tags={"type": "system"},
                        threshold_warning=80.0,
                        threshold_critical=95.0
                    ),
                    SystemMetric(
                        id=str(uuid.uuid4()),
                        name="disk_usage",
                        type=MetricType.GAUGE,
                        value=(disk.used / disk.total) * 100,
                        unit="percent",
                        timestamp=timestamp,
                        service_name="system",
                        tags={"type": "system"},
                        threshold_warning=80.0,
                        threshold_critical=95.0
                    )
                ]
                
                # Store metrics
                for metric in system_metrics:
                    self.metrics[metric.id] = metric
                
                # Service-specific metrics
                for service_name, service in self.services.items():
                    service_metrics = [
                        SystemMetric(
                            id=str(uuid.uuid4()),
                            name="response_time",
                            type=MetricType.GAUGE,
                            value=service.response_time_ms,
                            unit="ms",
                            timestamp=timestamp,
                            service_name=service_name,
                            tags={"type": "performance"},
                            threshold_warning=1000.0,
                            threshold_critical=5000.0
                        ),
                        SystemMetric(
                            id=str(uuid.uuid4()),
                            name="error_rate",
                            type=MetricType.RATE,
                            value=service.error_rate,
                            unit="percent",
                            timestamp=timestamp,
                            service_name=service_name,
                            tags={"type": "reliability"},
                            threshold_warning=5.0,
                            threshold_critical=15.0
                        )
                    ]
                    
                    for metric in service_metrics:
                        self.metrics[metric.id] = metric
                
                # Cleanup old metrics (keep last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                old_metrics = [
                    metric_id for metric_id, metric in self.metrics.items()
                    if datetime.fromisoformat(metric.timestamp) < cutoff_time
                ]
                
                for metric_id in old_metrics:
                    del self.metrics[metric_id]
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(60)
    
    async def _check_alerts(self):
        """Background task to check for alerts"""
        while self.monitoring_active:
            try:
                current_time = datetime.now().isoformat()
                
                # Check metric thresholds
                for metric in self.metrics.values():
                    # Skip old metrics
                    if datetime.fromisoformat(metric.timestamp) < datetime.now() - timedelta(minutes=5):
                        continue
                    
                    # Check critical threshold
                    if metric.value >= metric.threshold_critical:
                        alert_id = f"{metric.service_name}_{metric.name}_critical"
                        
                        if alert_id not in self.alerts or self.alerts[alert_id].resolved:
                            alert = SystemAlert(
                                id=alert_id,
                                title=f"Critical: {metric.name} threshold exceeded",
                                description=f"{metric.service_name} {metric.name} is {metric.value}{metric.unit} (threshold: {metric.threshold_critical}{metric.unit})",
                                severity=AlertSeverity.CRITICAL,
                                service_name=metric.service_name,
                                metric_name=metric.name,
                                current_value=metric.value,
                                threshold_value=metric.threshold_critical,
                                timestamp=current_time,
                                resolved=False,
                                resolution_time=None
                            )
                            
                            self.alerts[alert_id] = alert
                            logger.critical(f"CRITICAL ALERT: {alert.description}")
                    
                    # Check warning threshold
                    elif metric.value >= metric.threshold_warning:
                        alert_id = f"{metric.service_name}_{metric.name}_warning"
                        
                        if alert_id not in self.alerts or self.alerts[alert_id].resolved:
                            alert = SystemAlert(
                                id=alert_id,
                                title=f"Warning: {metric.name} threshold exceeded",
                                description=f"{metric.service_name} {metric.name} is {metric.value}{metric.unit} (threshold: {metric.threshold_warning}{metric.unit})",
                                severity=AlertSeverity.WARNING,
                                service_name=metric.service_name,
                                metric_name=metric.name,
                                current_value=metric.value,
                                threshold_value=metric.threshold_warning,
                                timestamp=current_time,
                                resolved=False,
                                resolution_time=None
                            )
                            
                            self.alerts[alert_id] = alert
                            logger.warning(f"WARNING ALERT: {alert.description}")
                
                # Check service health alerts
                for service in self.services.values():
                    if service.status in [ServiceStatus.CRITICAL, ServiceStatus.UNHEALTHY]:
                        alert_id = f"{service.service_name}_health_critical"
                        
                        if alert_id not in self.alerts or self.alerts[alert_id].resolved:
                            alert = SystemAlert(
                                id=alert_id,
                                title=f"Service Health: {service.service_name}",
                                description=f"{service.service_name} is {service.status.value}",
                                severity=AlertSeverity.CRITICAL if service.status == ServiceStatus.CRITICAL else AlertSeverity.ERROR,
                                service_name=service.service_name,
                                metric_name="service_health",
                                current_value=0.0,
                                threshold_value=1.0,
                                timestamp=current_time,
                                resolved=False,
                                resolution_time=None
                            )
                            
                            self.alerts[alert_id] = alert
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error checking alerts: {e}")
                await asyncio.sleep(60)
    
    async def _update_system_metrics(self):
        """Update system-wide health metrics"""
        try:
            total_services = len(self.services)
            healthy_services = len([s for s in self.services.values() if s.status == ServiceStatus.HEALTHY])
            critical_services = len([s for s in self.services.values() if s.status == ServiceStatus.CRITICAL])
            
            # Update service availability
            for service in self.services.values():
                if service.status == ServiceStatus.HEALTHY:
                    service.uptime_percentage = min(100.0, service.uptime_percentage + 0.1)
                else:
                    service.uptime_percentage = max(0.0, service.uptime_percentage - 0.5)
                
                # Calculate error rate
                total_checks = max(1, service.error_count + (service.uptime_percentage * 10))
                service.error_rate = (service.error_count / total_checks) * 100
                
                # Mock additional metrics for demonstration
                service.memory_usage_mb = np.random.uniform(100, 500)
                service.cpu_usage_percent = np.random.uniform(10, 60)
                service.requests_per_minute = np.random.uniform(50, 200)
                service.throughput = np.random.uniform(10, 100)
                service.availability_24h = service.uptime_percentage
                service.latency_p95 = service.response_time_ms * 1.5
        
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    async def _broadcast_updates(self):
        """Broadcast updates to connected WebSocket clients"""
        while self.monitoring_active:
            try:
                if self.active_websockets:
                    # Prepare dashboard data
                    dashboard_data = await self.get_dashboard_summary()
                    
                    # Broadcast to all connected clients
                    disconnected = []
                    for websocket in self.active_websockets:
                        try:
                            await websocket.send_json(dashboard_data)
                        except:
                            disconnected.append(websocket)
                    
                    # Remove disconnected clients
                    for ws in disconnected:
                        if ws in self.active_websockets:
                            self.active_websockets.remove(ws)
                
                await asyncio.sleep(5)  # Broadcast every 5 seconds
                
            except Exception as e:
                logger.error(f"Error broadcasting updates: {e}")
                await asyncio.sleep(5)
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get comprehensive dashboard summary"""
        total_services = len(self.services)
        healthy_services = len([s for s in self.services.values() if s.status == ServiceStatus.HEALTHY])
        critical_services = len([s for s in self.services.values() if s.status == ServiceStatus.CRITICAL])
        degraded_services = len([s for s in self.services.values() if s.status == ServiceStatus.DEGRADED])
        
        active_alerts = [a for a in self.alerts.values() if not a.resolved]
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        
        # System health score (0-100)
        health_score = (healthy_services / total_services) * 100 if total_services > 0 else 0
        
        # Average response time
        response_times = [s.response_time_ms for s in self.services.values() if s.response_time_ms > 0]
        avg_response_time = np.mean(response_times) if response_times else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_health_score": round(health_score, 1),
            "overall_status": "healthy" if health_score >= 80 else "degraded" if health_score >= 60 else "critical",
            "services": {
                "total": total_services,
                "healthy": healthy_services,
                "degraded": degraded_services,
                "critical": critical_services,
                "health_percentage": round(health_score, 1)
            },
            "alerts": {
                "total_active": len(active_alerts),
                "critical": len(critical_alerts),
                "warnings": len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
                "errors": len([a for a in active_alerts if a.severity == AlertSeverity.ERROR])
            },
            "performance": {
                "average_response_time_ms": round(avg_response_time, 2),
                "total_requests_per_minute": sum(s.requests_per_minute for s in self.services.values()),
                "average_cpu_usage": round(np.mean([s.cpu_usage_percent for s in self.services.values()]), 1),
                "average_memory_usage_mb": round(np.mean([s.memory_usage_mb for s in self.services.values()]), 1)
            },
            "system_resources": {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            }
        }

# Initialize the health monitor
health_monitor = SystemHealthMonitor()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "System Health Monitor",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "service_health_monitoring",
            "real_time_metrics_collection",
            "intelligent_alerting",
            "performance_profiling",
            "system_resource_monitoring",
            "dashboard_visualization"
        ],
        "monitored_services": len(health_monitor.services),
        "active_alerts": len([a for a in health_monitor.alerts.values() if not a.resolved])
    }

@app.get("/dashboard")
async def get_dashboard():
    """Get comprehensive dashboard data"""
    return await health_monitor.get_dashboard_summary()

@app.get("/services")
async def get_all_services(status: ServiceStatus = None):
    """Get all monitored services"""
    services = health_monitor.services
    
    if status:
        services = {k: v for k, v in services.items() if v.status == status}
    
    return {
        "services": [asdict(service) for service in services.values()],
        "total": len(services)
    }

@app.get("/services/{service_name}")
async def get_service_health(service_name: str):
    """Get specific service health"""
    if service_name not in health_monitor.services:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service = await health_monitor.check_service_health(service_name)
    return {"service": asdict(service)}

@app.get("/metrics")
async def get_metrics(service_name: str = None, metric_type: MetricType = None):
    """Get system metrics"""
    metrics = health_monitor.metrics
    
    if service_name:
        metrics = {k: v for k, v in metrics.items() if v.service_name == service_name}
    
    if metric_type:
        metrics = {k: v for k, v in metrics.items() if v.type == metric_type}
    
    return {
        "metrics": [asdict(metric) for metric in metrics.values()],
        "total": len(metrics)
    }

@app.get("/alerts")
async def get_alerts(resolved: bool = None, severity: AlertSeverity = None):
    """Get system alerts"""
    alerts = health_monitor.alerts
    
    if resolved is not None:
        alerts = {k: v for k, v in alerts.items() if v.resolved == resolved}
    
    if severity:
        alerts = {k: v for k, v in alerts.items() if v.severity == severity}
    
    return {
        "alerts": [asdict(alert) for alert in alerts.values()],
        "total": len(alerts)
    }

@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert"""
    if alert_id not in health_monitor.alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = health_monitor.alerts[alert_id]
    alert.resolved = True
    alert.resolution_time = datetime.now().isoformat()
    
    return {"status": "resolved", "alert_id": alert_id}

@app.get("/system/resources")
async def get_system_resources():
    """Get system resource usage"""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu": {
            "usage_percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "usage_percent": memory.percent,
            "available_gb": round(memory.available / (1024**3), 2)
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "usage_percent": round((disk.used / disk.total) * 100, 2),
            "free_gb": round(disk.free / (1024**3), 2)
        },
        "network": {
            "bytes_sent": psutil.net_io_counters().bytes_sent,
            "bytes_recv": psutil.net_io_counters().bytes_recv,
            "packets_sent": psutil.net_io_counters().packets_sent,
            "packets_recv": psutil.net_io_counters().packets_recv
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    health_monitor.active_websockets.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        if websocket in health_monitor.active_websockets:
            health_monitor.active_websockets.remove(websocket)

@app.get("/dashboard/html", response_class=HTMLResponse)
async def get_dashboard_html():
    """Get HTML dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCP Trading Platform - System Health Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .metric { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #eee; }
            .status-healthy { color: #28a745; }
            .status-degraded { color: #ffc107; }
            .status-critical { color: #dc3545; }
            .alert { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .alert-critical { background-color: #f8d7da; border: 1px solid #f5c6cb; }
            .alert-warning { background-color: #fff3cd; border: 1px solid #ffeaa7; }
            .progress-bar { width: 100%; height: 20px; background-color: #e9ecef; border-radius: 10px; overflow: hidden; }
            .progress-fill { height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.3s ease; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>MCP Trading Platform - System Health Dashboard</h1>
                <p>Real-time monitoring and health status</p>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>System Overview</h3>
                    <div id="system-overview">Loading...</div>
                </div>
                
                <div class="card">
                    <h3>Service Health</h3>
                    <div id="service-health">Loading...</div>
                </div>
                
                <div class="card">
                    <h3>Active Alerts</h3>
                    <div id="active-alerts">Loading...</div>
                </div>
                
                <div class="card">
                    <h3>Performance Metrics</h3>
                    <div id="performance-metrics">Loading...</div>
                </div>
            </div>
        </div>
        
        <script>
            // WebSocket connection for real-time updates
            const ws = new WebSocket('ws://localhost:8100/ws');
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            function updateDashboard(data) {
                // Update system overview
                document.getElementById('system-overview').innerHTML = `
                    <div class="metric">
                        <span>System Health Score</span>
                        <span class="${getStatusClass(data.overall_status)}">${data.system_health_score}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${data.system_health_score}%"></div>
                    </div>
                `;
                
                // Update service health
                document.getElementById('service-health').innerHTML = `
                    <div class="metric">
                        <span>Healthy Services</span>
                        <span class="status-healthy">${data.services.healthy}/${data.services.total}</span>
                    </div>
                    <div class="metric">
                        <span>Degraded Services</span>
                        <span class="status-degraded">${data.services.degraded}</span>
                    </div>
                    <div class="metric">
                        <span>Critical Services</span>
                        <span class="status-critical">${data.services.critical}</span>
                    </div>
                `;
                
                // Update alerts
                document.getElementById('active-alerts').innerHTML = `
                    <div class="metric">
                        <span>Total Active</span>
                        <span>${data.alerts.total_active}</span>
                    </div>
                    <div class="metric">
                        <span>Critical Alerts</span>
                        <span class="status-critical">${data.alerts.critical}</span>
                    </div>
                    <div class="metric">
                        <span>Warnings</span>
                        <span class="status-degraded">${data.alerts.warnings}</span>
                    </div>
                `;
                
                // Update performance
                document.getElementById('performance-metrics').innerHTML = `
                    <div class="metric">
                        <span>Avg Response Time</span>
                        <span>${data.performance.average_response_time_ms}ms</span>
                    </div>
                    <div class="metric">
                        <span>CPU Usage</span>
                        <span>${data.performance.average_cpu_usage}%</span>
                    </div>
                    <div class="metric">
                        <span>Memory Usage</span>
                        <span>${data.performance.average_memory_usage_mb}MB</span>
                    </div>
                `;
            }
            
            function getStatusClass(status) {
                switch(status) {
                    case 'healthy': return 'status-healthy';
                    case 'degraded': return 'status-degraded';
                    case 'critical': return 'status-critical';
                    default: return '';
                }
            }
            
            // Initial load
            fetch('/dashboard')
                .then(response => response.json())
                .then(data => updateDashboard(data));
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(
        "system_health_monitor:app",
        host="0.0.0.0",
        port=8100,
        reload=True,
        log_level="info"
    )