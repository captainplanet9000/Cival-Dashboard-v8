#!/usr/bin/env python3
"""
Comprehensive Monitoring Dashboard for MCP Servers
Real-time system health visualization and metrics aggregation
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/monitoring_dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="MCP Monitoring Dashboard",
    description="Real-time monitoring dashboard for all MCP servers",
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

@dataclass
class ServerMetrics:
    server_id: str
    server_name: str
    server_type: str
    status: str
    port: int
    response_time: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    requests_per_second: float
    error_rate: float
    uptime: int
    last_check: str
    health_score: float

@dataclass
class SystemAlert:
    id: str
    timestamp: str
    severity: str
    server_id: str
    alert_type: str
    message: str
    details: Dict[str, Any]
    acknowledged: bool = False

class MonitoringDashboard:
    def __init__(self):
        self.servers = {
            # Market Data Servers
            'alpaca_market_data': {'port': 8001, 'name': 'Alpaca Market Data', 'type': 'market_data'},
            'alphavantage_data': {'port': 8002, 'name': 'Alpha Vantage Data', 'type': 'market_data'},
            'financial_datasets': {'port': 8003, 'name': 'Financial Datasets', 'type': 'market_data'},
            
            # Trading Operations Servers
            'trading_gateway': {'port': 8010, 'name': 'Trading Gateway', 'type': 'trading_ops'},
            'order_management': {'port': 8013, 'name': 'Order Management', 'type': 'trading_ops'},
            'portfolio_management': {'port': 8014, 'name': 'Portfolio Management', 'type': 'trading_ops'},
            'risk_management': {'port': 8015, 'name': 'Risk Management', 'type': 'trading_ops'},
            'broker_execution': {'port': 8016, 'name': 'Broker Execution', 'type': 'trading_ops'},
            
            # Intelligence Servers
            'octagon_intelligence': {'port': 8020, 'name': 'Octagon Intelligence', 'type': 'intelligence'},
            'mongodb_intelligence': {'port': 8021, 'name': 'MongoDB Intelligence', 'type': 'intelligence'},
            'neo4j_intelligence': {'port': 8022, 'name': 'Neo4j Intelligence', 'type': 'intelligence'},
            
            # Security & Monitoring
            'security_compliance': {'port': 8030, 'name': 'Security & Compliance', 'type': 'security'}
        }
        
        self.current_metrics: Dict[str, ServerMetrics] = {}
        self.alerts: List[SystemAlert] = []
        self.websocket_connections: List[WebSocket] = []
        self.monitoring_active = False
        self.session = None
        
    async def initialize(self):
        """Initialize monitoring session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=100)
        )
        self.monitoring_active = True
        
        # Start background monitoring
        asyncio.create_task(self.monitor_servers())
        asyncio.create_task(self.broadcast_updates())
        
    async def cleanup(self):
        """Cleanup monitoring session"""
        self.monitoring_active = False
        if self.session:
            await self.session.close()
    
    async def collect_server_metrics(self, server_id: str, server_config: Dict) -> Optional[ServerMetrics]:
        """Collect metrics from a single server"""
        port = server_config['port']
        name = server_config['name']
        server_type = server_config['type']
        
        try:
            start_time = time.time()
            
            # Health check
            health_url = f"http://localhost:{port}/health"
            async with self.session.get(health_url) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    health_data = await response.json()
                    status = "online"
                else:
                    status = "error"
                    health_data = {}
            
            # Metrics collection
            metrics_data = {}
            try:
                metrics_url = f"http://localhost:{port}/metrics"
                async with self.session.get(metrics_url) as metrics_response:
                    if metrics_response.status == 200:
                        metrics_data = await metrics_response.json()
            except:
                pass
            
            # Calculate health score
            health_score = self._calculate_health_score(status, response_time, metrics_data)
            
            # Check for alerts
            await self._check_server_alerts(server_id, status, response_time, metrics_data)
            
            return ServerMetrics(
                server_id=server_id,
                server_name=name,
                server_type=server_type,
                status=status,
                port=port,
                response_time=round(response_time, 2),
                cpu_usage=metrics_data.get('cpu_usage', 0.0),
                memory_usage=metrics_data.get('memory_usage', 0.0),
                disk_usage=metrics_data.get('disk_usage', 0.0),
                active_connections=metrics_data.get('active_connections', 0),
                requests_per_second=metrics_data.get('requests_per_second', 0.0),
                error_rate=metrics_data.get('error_rate', 0.0),
                uptime=metrics_data.get('uptime', 0),
                last_check=datetime.now().isoformat(),
                health_score=health_score
            )
            
        except Exception as e:
            logger.warning(f"Failed to collect metrics for {server_id}: {e}")
            
            # Generate offline alert
            await self._generate_alert(
                server_id=server_id,
                severity="high",
                alert_type="server_offline",
                message=f"{name} is offline or unreachable",
                details={"error": str(e), "port": port}
            )
            
            return ServerMetrics(
                server_id=server_id,
                server_name=name,
                server_type=server_type,
                status="offline",
                port=port,
                response_time=0.0,
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                active_connections=0,
                requests_per_second=0.0,
                error_rate=100.0,
                uptime=0,
                last_check=datetime.now().isoformat(),
                health_score=0.0
            )
    
    def _calculate_health_score(self, status: str, response_time: float, metrics: Dict) -> float:
        """Calculate overall health score for a server"""
        if status == "offline":
            return 0.0
        
        score = 100.0
        
        # Response time penalty
        if response_time > 1000:  # > 1 second
            score -= 20
        elif response_time > 500:  # > 500ms
            score -= 10
        elif response_time > 200:  # > 200ms
            score -= 5
        
        # CPU usage penalty
        cpu_usage = metrics.get('cpu_usage', 0)
        if cpu_usage > 90:
            score -= 15
        elif cpu_usage > 70:
            score -= 10
        elif cpu_usage > 50:
            score -= 5
        
        # Memory usage penalty
        memory_usage = metrics.get('memory_usage', 0)
        if memory_usage > 90:
            score -= 15
        elif memory_usage > 70:
            score -= 10
        elif memory_usage > 50:
            score -= 5
        
        # Error rate penalty
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 10:
            score -= 20
        elif error_rate > 5:
            score -= 10
        elif error_rate > 1:
            score -= 5
        
        return max(0.0, score)
    
    async def _check_server_alerts(self, server_id: str, status: str, response_time: float, metrics: Dict):
        """Check for alert conditions and generate alerts"""
        server_name = self.servers[server_id]['name']
        
        # High response time alert
        if response_time > 2000:  # > 2 seconds
            await self._generate_alert(
                server_id=server_id,
                severity="warning",
                alert_type="high_response_time",
                message=f"{server_name} has high response time: {response_time:.1f}ms",
                details={"response_time": response_time, "threshold": 2000}
            )
        
        # High CPU usage alert
        cpu_usage = metrics.get('cpu_usage', 0)
        if cpu_usage > 80:
            await self._generate_alert(
                server_id=server_id,
                severity="warning" if cpu_usage < 95 else "critical",
                alert_type="high_cpu_usage",
                message=f"{server_name} has high CPU usage: {cpu_usage:.1f}%",
                details={"cpu_usage": cpu_usage, "threshold": 80}
            )
        
        # High memory usage alert
        memory_usage = metrics.get('memory_usage', 0)
        if memory_usage > 80:
            await self._generate_alert(
                server_id=server_id,
                severity="warning" if memory_usage < 95 else "critical",
                alert_type="high_memory_usage",
                message=f"{server_name} has high memory usage: {memory_usage:.1f}%",
                details={"memory_usage": memory_usage, "threshold": 80}
            )
        
        # High error rate alert
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 5:
            await self._generate_alert(
                server_id=server_id,
                severity="warning" if error_rate < 20 else "critical",
                alert_type="high_error_rate",
                message=f"{server_name} has high error rate: {error_rate:.1f}%",
                details={"error_rate": error_rate, "threshold": 5}
            )
    
    async def _generate_alert(self, server_id: str, severity: str, alert_type: str, message: str, details: Dict):
        """Generate a system alert"""
        # Check if similar alert already exists (avoid spam)
        existing_alert = next(
            (a for a in self.alerts 
             if a.server_id == server_id and a.alert_type == alert_type and not a.acknowledged),
            None
        )
        
        if existing_alert:
            return  # Don't create duplicate alerts
        
        alert = SystemAlert(
            id=f"{server_id}_{alert_type}_{int(time.time())}",
            timestamp=datetime.now().isoformat(),
            severity=severity,
            server_id=server_id,
            alert_type=alert_type,
            message=message,
            details=details
        )
        
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        logger.warning(f"ALERT: {severity.upper()} - {message}")
    
    async def monitor_servers(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect metrics from all servers concurrently
                tasks = []
                for server_id, server_config in self.servers.items():
                    task = self.collect_server_metrics(server_id, server_config)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update current metrics
                for result in results:
                    if isinstance(result, ServerMetrics):
                        self.current_metrics[result.server_id] = result
                
                # Log overall system status
                online_count = sum(1 for m in self.current_metrics.values() if m.status == "online")
                total_count = len(self.current_metrics)
                logger.info(f"System Status: {online_count}/{total_count} servers online")
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            # Wait before next collection cycle
            await asyncio.sleep(30)  # Monitor every 30 seconds
    
    async def broadcast_updates(self):
        """Broadcast updates to connected WebSocket clients"""
        while self.monitoring_active:
            if self.websocket_connections:
                try:
                    update_data = {
                        "type": "metrics_update",
                        "timestamp": datetime.now().isoformat(),
                        "metrics": {k: asdict(v) for k, v in self.current_metrics.items()},
                        "system_stats": self.get_system_stats(),
                        "recent_alerts": [asdict(a) for a in self.alerts[-10:]]
                    }
                    
                    # Send to all connected clients
                    disconnected = []
                    for websocket in self.websocket_connections:
                        try:
                            await websocket.send_text(json.dumps(update_data))
                        except:
                            disconnected.append(websocket)
                    
                    # Remove disconnected clients
                    for ws in disconnected:
                        self.websocket_connections.remove(ws)
                        
                except Exception as e:
                    logger.error(f"Error broadcasting updates: {e}")
            
            await asyncio.sleep(5)  # Broadcast every 5 seconds
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        if not self.current_metrics:
            return {}
        
        metrics = list(self.current_metrics.values())
        
        # Status distribution
        status_counts = {}
        for metric in metrics:
            status_counts[metric.status] = status_counts.get(metric.status, 0) + 1
        
        # Type distribution
        type_counts = {}
        for metric in metrics:
            type_counts[metric.server_type] = type_counts.get(metric.server_type, 0) + 1
        
        # Average metrics
        online_metrics = [m for m in metrics if m.status == "online"]
        
        avg_response_time = sum(m.response_time for m in online_metrics) / len(online_metrics) if online_metrics else 0
        avg_cpu_usage = sum(m.cpu_usage for m in online_metrics) / len(online_metrics) if online_metrics else 0
        avg_memory_usage = sum(m.memory_usage for m in online_metrics) / len(online_metrics) if online_metrics else 0
        avg_health_score = sum(m.health_score for m in metrics) / len(metrics) if metrics else 0
        
        # Alert counts
        unacknowledged_alerts = sum(1 for a in self.alerts if not a.acknowledged)
        critical_alerts = sum(1 for a in self.alerts if a.severity == "critical" and not a.acknowledged)
        
        return {
            "total_servers": len(metrics),
            "online_servers": status_counts.get("online", 0),
            "offline_servers": status_counts.get("offline", 0),
            "error_servers": status_counts.get("error", 0),
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "avg_response_time": round(avg_response_time, 2),
            "avg_cpu_usage": round(avg_cpu_usage, 2),
            "avg_memory_usage": round(avg_memory_usage, 2),
            "avg_health_score": round(avg_health_score, 2),
            "unacknowledged_alerts": unacknowledged_alerts,
            "critical_alerts": critical_alerts,
            "total_alerts": len(self.alerts)
        }
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
        return False

# Initialize monitoring dashboard
dashboard = MonitoringDashboard()

# API Endpoints
@app.get("/")
async def get_dashboard():
    """Serve the monitoring dashboard HTML"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCP Monitoring Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-value { font-size: 2em; font-weight: bold; color: #2c3e50; }
            .stat-label { color: #7f8c8d; margin-top: 5px; }
            .servers-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .server-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .server-header { display: flex; justify-content: between; align-items: center; margin-bottom: 15px; }
            .status-online { color: #27ae60; }
            .status-offline { color: #e74c3c; }
            .status-error { color: #f39c12; }
            .metric-row { display: flex; justify-content: space-between; margin: 5px 0; }
            .alerts-section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .alert-item { padding: 10px; margin: 5px 0; border-left: 4px solid; border-radius: 4px; }
            .alert-critical { border-color: #e74c3c; background: #fdf2f2; }
            .alert-warning { border-color: #f39c12; background: #fdf6e3; }
            .alert-info { border-color: #3498db; background: #ebf3fd; }
            .timestamp { color: #7f8c8d; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🖥️ MCP Monitoring Dashboard</h1>
            <p>Real-time monitoring of all Model Context Protocol servers</p>
            <div class="timestamp" id="lastUpdate">Last Update: Loading...</div>
        </div>
        
        <div class="stats-grid" id="systemStats">
            <!-- System stats will be populated here -->
        </div>
        
        <div class="servers-grid" id="serversGrid">
            <!-- Server cards will be populated here -->
        </div>
        
        <div class="alerts-section">
            <h2>🚨 Recent Alerts</h2>
            <div id="alertsList">
                <!-- Alerts will be populated here -->
            </div>
        </div>
        
        <script>
            const ws = new WebSocket('ws://localhost:8040/ws');
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'metrics_update') {
                    updateDashboard(data);
                }
            };
            
            function updateDashboard(data) {
                document.getElementById('lastUpdate').textContent = 'Last Update: ' + new Date(data.timestamp).toLocaleString();
                updateSystemStats(data.system_stats);
                updateServersGrid(data.metrics);
                updateAlerts(data.recent_alerts);
            }
            
            function updateSystemStats(stats) {
                const statsHTML = `
                    <div class="stat-card">
                        <div class="stat-value">${stats.total_servers || 0}</div>
                        <div class="stat-label">Total Servers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value status-online">${stats.online_servers || 0}</div>
                        <div class="stat-label">Online</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value status-offline">${stats.offline_servers || 0}</div>
                        <div class="stat-label">Offline</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.avg_health_score || 0}%</div>
                        <div class="stat-label">Avg Health Score</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.avg_response_time || 0}ms</div>
                        <div class="stat-label">Avg Response Time</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.unacknowledged_alerts || 0}</div>
                        <div class="stat-label">Active Alerts</div>
                    </div>
                `;
                document.getElementById('systemStats').innerHTML = statsHTML;
            }
            
            function updateServersGrid(metrics) {
                const serversHTML = Object.values(metrics).map(server => `
                    <div class="server-card">
                        <div class="server-header">
                            <h3>${server.server_name}</h3>
                            <span class="status-${server.status}">${server.status.toUpperCase()}</span>
                        </div>
                        <div class="metric-row">
                            <span>Port:</span>
                            <span>${server.port}</span>
                        </div>
                        <div class="metric-row">
                            <span>Response Time:</span>
                            <span>${server.response_time}ms</span>
                        </div>
                        <div class="metric-row">
                            <span>CPU Usage:</span>
                            <span>${server.cpu_usage}%</span>
                        </div>
                        <div class="metric-row">
                            <span>Memory Usage:</span>
                            <span>${server.memory_usage}%</span>
                        </div>
                        <div class="metric-row">
                            <span>Health Score:</span>
                            <span>${server.health_score}%</span>
                        </div>
                        <div class="metric-row">
                            <span>Last Check:</span>
                            <span class="timestamp">${new Date(server.last_check).toLocaleTimeString()}</span>
                        </div>
                    </div>
                `).join('');
                document.getElementById('serversGrid').innerHTML = serversHTML;
            }
            
            function updateAlerts(alerts) {
                const alertsHTML = alerts.map(alert => `
                    <div class="alert-item alert-${alert.severity}">
                        <strong>${alert.severity.toUpperCase()}: ${alert.message}</strong>
                        <div class="timestamp">${new Date(alert.timestamp).toLocaleString()}</div>
                    </div>
                `).join('');
                document.getElementById('alertsList').innerHTML = alertsHTML || '<p>No recent alerts</p>';
            }
            
            // Initial connection message
            ws.onopen = function() {
                console.log('Connected to monitoring dashboard');
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    dashboard.websocket_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        dashboard.websocket_connections.remove(websocket)

@app.get("/api/metrics")
async def get_all_metrics():
    """Get current metrics for all servers"""
    return {
        "metrics": {k: asdict(v) for k, v in dashboard.current_metrics.items()},
        "system_stats": dashboard.get_system_stats(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/metrics/{server_id}")
async def get_server_metrics(server_id: str):
    """Get metrics for a specific server"""
    if server_id in dashboard.current_metrics:
        return asdict(dashboard.current_metrics[server_id])
    raise HTTPException(status_code=404, detail="Server not found")

@app.get("/api/alerts")
async def get_alerts():
    """Get all alerts"""
    return {
        "alerts": [asdict(a) for a in dashboard.alerts],
        "total": len(dashboard.alerts),
        "unacknowledged": sum(1 for a in dashboard.alerts if not a.acknowledged)
    }

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    if await dashboard.acknowledge_alert(alert_id):
        return {"message": "Alert acknowledged"}
    raise HTTPException(status_code=404, detail="Alert not found")

@app.get("/api/system/stats")
async def get_system_stats():
    """Get overall system statistics"""
    return dashboard.get_system_stats()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "MCP Monitoring Dashboard",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "monitoring_active": dashboard.monitoring_active,
        "connected_clients": len(dashboard.websocket_connections)
    }

@app.on_event("startup")
async def startup_event():
    """Initialize monitoring on startup"""
    await dashboard.initialize()
    logger.info("MCP Monitoring Dashboard started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await dashboard.cleanup()
    logger.info("MCP Monitoring Dashboard stopped")

if __name__ == "__main__":
    uvicorn.run(
        "monitoring_dashboard:app",
        host="0.0.0.0",
        port=8040,
        reload=True,
        log_level="info"
    )