#!/usr/bin/env python3
"""
Load Balancer and Scaling Infrastructure
Advanced load balancing with auto-scaling capabilities
"""

import asyncio
import json
import logging
import time
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field
import uuid
from enum import Enum
import numpy as np
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/load_balancer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Load Balancer & Scaling Infrastructure",
    description="Advanced load balancing with auto-scaling capabilities",
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
class LoadBalancingAlgorithm(str, Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    LEAST_LOAD = "least_load"
    HEALTH_AWARE = "health_aware"

class ServerStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"
    STARTING = "starting"
    STOPPING = "stopping"

class ScalingDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"

class AutoScalingTrigger(str, Enum):
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    REQUEST_RATE = "request_rate"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    QUEUE_LENGTH = "queue_length"

# Data models
@dataclass
class ServerInstance:
    id: str
    host: str
    port: int
    weight: float
    status: ServerStatus
    health_score: float
    last_health_check: str
    active_connections: int
    total_requests: int
    avg_response_time: float
    error_rate: float
    cpu_usage: float
    memory_usage: float
    created_at: str
    tags: Dict[str, str]

@dataclass
class LoadBalancerConfig:
    algorithm: LoadBalancingAlgorithm
    health_check_interval: int
    health_check_timeout: int
    health_check_path: str
    max_failures: int
    sticky_sessions: bool
    session_timeout: int
    circuit_breaker_enabled: bool
    circuit_breaker_threshold: float

@dataclass
class AutoScalingRule:
    id: str
    name: str
    trigger: AutoScalingTrigger
    threshold_up: float
    threshold_down: float
    min_instances: int
    max_instances: int
    scale_up_count: int
    scale_down_count: int
    cooldown_period: int
    enabled: bool

@dataclass
class ScalingEvent:
    id: str
    timestamp: str
    direction: ScalingDirection
    trigger: AutoScalingTrigger
    trigger_value: float
    instances_before: int
    instances_after: int
    rule_id: str
    reason: str

@dataclass
class RequestMetrics:
    request_id: str
    timestamp: str
    client_ip: str
    method: str
    path: str
    target_server: str
    response_time: float
    status_code: int
    response_size: int

class ServerConfig(BaseModel):
    host: str = Field(..., description="Server host")
    port: int = Field(..., description="Server port")
    weight: float = Field(default=1.0, description="Server weight")
    tags: Dict[str, str] = Field(default={}, description="Server tags")

class LoadBalancerSetup(BaseModel):
    algorithm: LoadBalancingAlgorithm = Field(default=LoadBalancingAlgorithm.ROUND_ROBIN)
    servers: List[ServerConfig] = Field(..., description="Server instances")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    sticky_sessions: bool = Field(default=False, description="Enable sticky sessions")

class AutoScalingConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable auto-scaling")
    rules: List[Dict[str, Any]] = Field(default=[], description="Scaling rules")
    min_instances: int = Field(default=2, description="Minimum instances")
    max_instances: int = Field(default=10, description="Maximum instances")

class LoadBalancerSystem:
    def __init__(self):
        self.servers = {}
        self.config = LoadBalancerConfig(
            algorithm=LoadBalancingAlgorithm.ROUND_ROBIN,
            health_check_interval=30,
            health_check_timeout=5,
            health_check_path="/health",
            max_failures=3,
            sticky_sessions=False,
            session_timeout=3600,
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=0.5
        )
        
        self.autoscaling_rules = {}
        self.scaling_events = {}
        self.request_metrics = deque(maxlen=10000)
        self.sessions = {}  # For sticky sessions
        
        # Load balancing state
        self.round_robin_index = 0
        self.server_connections = defaultdict(int)
        self.server_response_times = defaultdict(list)
        
        # Circuit breaker state
        self.circuit_breaker_state = defaultdict(lambda: {"failures": 0, "last_failure": 0, "open": False})
        
        # Initialize sample servers
        self._initialize_sample_servers()
        self._initialize_autoscaling_rules()
        
        # Start background tasks
        self.monitoring_active = True
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._autoscaling_monitor())
        
        logger.info("Load Balancer System initialized")
    
    def _initialize_sample_servers(self):
        """Initialize sample MCP servers for load balancing"""
        sample_servers = [
            {"host": "localhost", "port": 8001, "weight": 1.0, "tags": {"type": "market_data"}},
            {"host": "localhost", "port": 8002, "weight": 1.0, "tags": {"type": "market_data"}},
            {"host": "localhost", "port": 8010, "weight": 1.5, "tags": {"type": "trading"}},
            {"host": "localhost", "port": 8013, "weight": 1.2, "tags": {"type": "trading"}},
            {"host": "localhost", "port": 8020, "weight": 1.0, "tags": {"type": "intelligence"}},
            {"host": "localhost", "port": 8021, "weight": 1.0, "tags": {"type": "intelligence"}},
        ]
        
        for server_data in sample_servers:
            server_id = f"{server_data['host']}:{server_data['port']}"
            
            server = ServerInstance(
                id=server_id,
                host=server_data["host"],
                port=server_data["port"],
                weight=server_data["weight"],
                status=ServerStatus.HEALTHY,
                health_score=1.0,
                last_health_check=datetime.now().isoformat(),
                active_connections=0,
                total_requests=0,
                avg_response_time=0.0,
                error_rate=0.0,
                cpu_usage=np.random.uniform(20, 60),
                memory_usage=np.random.uniform(30, 70),
                created_at=datetime.now().isoformat(),
                tags=server_data["tags"]
            )
            
            self.servers[server_id] = server
        
        logger.info(f"Initialized {len(sample_servers)} sample servers")
    
    def _initialize_autoscaling_rules(self):
        """Initialize auto-scaling rules"""
        rules = [
            {
                "name": "CPU-based scaling",
                "trigger": AutoScalingTrigger.CPU_USAGE,
                "threshold_up": 80.0,
                "threshold_down": 30.0,
                "scale_up_count": 1,
                "scale_down_count": 1,
                "cooldown_period": 300
            },
            {
                "name": "Response time scaling",
                "trigger": AutoScalingTrigger.RESPONSE_TIME,
                "threshold_up": 1000.0,  # 1 second
                "threshold_down": 200.0,
                "scale_up_count": 2,
                "scale_down_count": 1,
                "cooldown_period": 180
            },
            {
                "name": "Request rate scaling",
                "trigger": AutoScalingTrigger.REQUEST_RATE,
                "threshold_up": 1000.0,  # requests per minute
                "threshold_down": 100.0,
                "scale_up_count": 1,
                "scale_down_count": 1,
                "cooldown_period": 240
            }
        ]
        
        for rule_data in rules:
            rule_id = str(uuid.uuid4())
            
            rule = AutoScalingRule(
                id=rule_id,
                name=rule_data["name"],
                trigger=rule_data["trigger"],
                threshold_up=rule_data["threshold_up"],
                threshold_down=rule_data["threshold_down"],
                min_instances=2,
                max_instances=10,
                scale_up_count=rule_data["scale_up_count"],
                scale_down_count=rule_data["scale_down_count"],
                cooldown_period=rule_data["cooldown_period"],
                enabled=True
            )
            
            self.autoscaling_rules[rule_id] = rule
        
        logger.info(f"Initialized {len(rules)} auto-scaling rules")
    
    async def select_server(self, request_info: Dict[str, Any]) -> Optional[ServerInstance]:
        """Select server using configured load balancing algorithm"""
        healthy_servers = [s for s in self.servers.values() if s.status == ServerStatus.HEALTHY]
        
        if not healthy_servers:
            logger.warning("No healthy servers available")
            return None
        
        if self.config.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            return await self._round_robin_selection(healthy_servers)
        elif self.config.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            return await self._weighted_round_robin_selection(healthy_servers)
        elif self.config.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            return await self._least_connections_selection(healthy_servers)
        elif self.config.algorithm == LoadBalancingAlgorithm.LEAST_RESPONSE_TIME:
            return await self._least_response_time_selection(healthy_servers)
        elif self.config.algorithm == LoadBalancingAlgorithm.IP_HASH:
            return await self._ip_hash_selection(healthy_servers, request_info.get("client_ip", ""))
        elif self.config.algorithm == LoadBalancingAlgorithm.LEAST_LOAD:
            return await self._least_load_selection(healthy_servers)
        elif self.config.algorithm == LoadBalancingAlgorithm.HEALTH_AWARE:
            return await self._health_aware_selection(healthy_servers)
        else:
            return healthy_servers[0]  # Fallback
    
    async def _round_robin_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Round-robin server selection"""
        selected = servers[self.round_robin_index % len(servers)]
        self.round_robin_index += 1
        return selected
    
    async def _weighted_round_robin_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Weighted round-robin server selection"""
        # Create weighted list
        weighted_servers = []
        for server in servers:
            weight_count = max(1, int(server.weight * 10))
            weighted_servers.extend([server] * weight_count)
        
        selected = weighted_servers[self.round_robin_index % len(weighted_servers)]
        self.round_robin_index += 1
        return selected
    
    async def _least_connections_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Least connections server selection"""
        return min(servers, key=lambda s: s.active_connections)
    
    async def _least_response_time_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Least response time server selection"""
        return min(servers, key=lambda s: s.avg_response_time)
    
    async def _ip_hash_selection(self, servers: List[ServerInstance], client_ip: str) -> ServerInstance:
        """IP hash-based server selection for sticky sessions"""
        if not client_ip:
            return servers[0]
        
        # Simple hash-based selection
        hash_value = hash(client_ip) % len(servers)
        return servers[hash_value]
    
    async def _least_load_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Least load server selection based on multiple metrics"""
        def calculate_load_score(server):
            # Combine multiple metrics for load calculation
            connection_load = server.active_connections / max(1, server.weight)
            cpu_load = server.cpu_usage / 100
            memory_load = server.memory_usage / 100
            response_time_load = min(1.0, server.avg_response_time / 1000)
            
            return (connection_load + cpu_load + memory_load + response_time_load) / 4
        
        return min(servers, key=calculate_load_score)
    
    async def _health_aware_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Health-aware server selection"""
        # Weight servers by health score
        weighted_servers = []
        for server in servers:
            weight = max(0.1, server.health_score * server.weight)
            weighted_servers.append((server, weight))
        
        # Select based on weighted probability
        total_weight = sum(weight for _, weight in weighted_servers)
        if total_weight == 0:
            return servers[0]
        
        r = np.random.uniform(0, total_weight)
        cumulative_weight = 0
        
        for server, weight in weighted_servers:
            cumulative_weight += weight
            if r <= cumulative_weight:
                return server
        
        return servers[0]  # Fallback
    
    async def route_request(self, request: Request) -> JSONResponse:
        """Route request to selected server"""
        # Extract request information
        request_info = {
            "client_ip": request.client.host,
            "method": request.method,
            "path": request.url.path,
            "headers": dict(request.headers)
        }
        
        # Select target server
        target_server = await self.select_server(request_info)
        
        if not target_server:
            raise HTTPException(status_code=503, detail="No healthy servers available")
        
        # Check circuit breaker
        if self._is_circuit_breaker_open(target_server.id):
            # Try to select alternative server
            alternative_servers = [s for s in self.servers.values() 
                                 if s.status == ServerStatus.HEALTHY and s.id != target_server.id]
            if alternative_servers:
                target_server = alternative_servers[0]
            else:
                raise HTTPException(status_code=503, detail="Circuit breaker open - no alternative servers")
        
        # Forward request
        start_time = time.time()
        
        try:
            # Increment connection count
            target_server.active_connections += 1
            self.server_connections[target_server.id] += 1
            
            # Simulate request forwarding
            response_data = await self._forward_request(target_server, request_info)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            # Update server metrics
            await self._update_server_metrics(target_server, response_time, True)
            
            # Record request metrics
            await self._record_request_metrics(target_server, request_info, response_time, 200)
            
            # Reset circuit breaker on successful request
            self._reset_circuit_breaker(target_server.id)
            
            return JSONResponse(
                content=response_data,
                headers={"X-Load-Balancer": "true", "X-Target-Server": target_server.id}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            # Update server metrics for failure
            await self._update_server_metrics(target_server, response_time, False)
            
            # Record failed request
            await self._record_request_metrics(target_server, request_info, response_time, 500)
            
            # Update circuit breaker
            self._record_circuit_breaker_failure(target_server.id)
            
            logger.error(f"Request forwarding failed to {target_server.id}: {e}")
            raise HTTPException(status_code=502, detail="Backend server error")
            
        finally:
            # Decrement connection count
            target_server.active_connections = max(0, target_server.active_connections - 1)
    
    async def _forward_request(self, server: ServerInstance, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Forward request to target server (simplified simulation)"""
        # Simulate network delay
        await asyncio.sleep(np.random.uniform(0.05, 0.3))
        
        # Simulate occasional failures
        if np.random.random() < 0.02:  # 2% failure rate
            raise Exception("Simulated server error")
        
        # Return mock response
        return {
            "status": "success",
            "server_id": server.id,
            "timestamp": datetime.now().isoformat(),
            "data": f"Response from {server.host}:{server.port}"
        }
    
    async def _update_server_metrics(self, server: ServerInstance, response_time: float, success: bool):
        """Update server performance metrics"""
        server.total_requests += 1
        
        # Update response time (exponential moving average)
        alpha = 0.1
        server.avg_response_time = (alpha * response_time + 
                                   (1 - alpha) * server.avg_response_time)
        
        # Update error rate
        if not success:
            server.error_rate = (alpha * 1.0 + (1 - alpha) * server.error_rate)
        else:
            server.error_rate = (1 - alpha) * server.error_rate
        
        # Update health score based on performance
        await self._calculate_health_score(server)
    
    async def _calculate_health_score(self, server: ServerInstance):
        """Calculate server health score"""
        # Base score from status
        if server.status != ServerStatus.HEALTHY:
            server.health_score = 0.0
            return
        
        # Factor in various metrics
        response_time_score = max(0, 1 - server.avg_response_time / 2000)  # Penalty for >2s response
        error_rate_score = max(0, 1 - server.error_rate * 10)  # Penalty for errors
        cpu_score = max(0, 1 - server.cpu_usage / 100)
        memory_score = max(0, 1 - server.memory_usage / 100)
        
        # Weighted average
        server.health_score = (
            response_time_score * 0.3 +
            error_rate_score * 0.3 +
            cpu_score * 0.2 +
            memory_score * 0.2
        )
    
    async def _record_request_metrics(self, server: ServerInstance, request_info: Dict[str, Any], 
                                    response_time: float, status_code: int):
        """Record request metrics"""
        metric = RequestMetrics(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            client_ip=request_info.get("client_ip", ""),
            method=request_info.get("method", ""),
            path=request_info.get("path", ""),
            target_server=server.id,
            response_time=response_time,
            status_code=status_code,
            response_size=1024  # Mock response size
        )
        
        self.request_metrics.append(metric)
    
    def _is_circuit_breaker_open(self, server_id: str) -> bool:
        """Check if circuit breaker is open for server"""
        if not self.config.circuit_breaker_enabled:
            return False
        
        cb_state = self.circuit_breaker_state[server_id]
        
        # Check if circuit breaker should be reset (half-open state)
        if cb_state["open"] and time.time() - cb_state["last_failure"] > 60:  # 1 minute timeout
            cb_state["open"] = False
            cb_state["failures"] = 0
        
        return cb_state["open"]
    
    def _record_circuit_breaker_failure(self, server_id: str):
        """Record circuit breaker failure"""
        cb_state = self.circuit_breaker_state[server_id]
        cb_state["failures"] += 1
        cb_state["last_failure"] = time.time()
        
        # Open circuit breaker if threshold exceeded
        if cb_state["failures"] >= self.config.max_failures:
            cb_state["open"] = True
            logger.warning(f"Circuit breaker opened for server {server_id}")
    
    def _reset_circuit_breaker(self, server_id: str):
        """Reset circuit breaker on successful request"""
        cb_state = self.circuit_breaker_state[server_id]
        cb_state["failures"] = max(0, cb_state["failures"] - 1)
        
        if cb_state["failures"] == 0:
            cb_state["open"] = False
    
    async def _health_check_loop(self):
        """Background health checking loop"""
        while self.monitoring_active:
            try:
                for server in self.servers.values():
                    await self._perform_health_check(server)
                
                await asyncio.sleep(self.config.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)
    
    async def _perform_health_check(self, server: ServerInstance):
        """Perform health check on server"""
        try:
            # Simulate health check
            start_time = time.time()
            
            # Mock health check with random success/failure
            health_success = np.random.random() > 0.05  # 95% success rate
            
            response_time = (time.time() - start_time) * 1000
            
            if health_success:
                if server.status == ServerStatus.UNHEALTHY:
                    server.status = ServerStatus.HEALTHY
                    logger.info(f"Server {server.id} recovered")
                
                # Update resource usage (simulate monitoring)
                server.cpu_usage = max(0, min(100, server.cpu_usage + np.random.uniform(-5, 5)))
                server.memory_usage = max(0, min(100, server.memory_usage + np.random.uniform(-3, 3)))
                
            else:
                server.status = ServerStatus.UNHEALTHY
                logger.warning(f"Health check failed for server {server.id}")
            
            server.last_health_check = datetime.now().isoformat()
            await self._calculate_health_score(server)
            
        except Exception as e:
            server.status = ServerStatus.UNHEALTHY
            logger.error(f"Health check error for {server.id}: {e}")
    
    async def _autoscaling_monitor(self):
        """Monitor metrics and trigger auto-scaling"""
        while self.monitoring_active:
            try:
                for rule in self.autoscaling_rules.values():
                    if rule.enabled:
                        await self._evaluate_scaling_rule(rule)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in auto-scaling monitor: {e}")
                await asyncio.sleep(30)
    
    async def _evaluate_scaling_rule(self, rule: AutoScalingRule):
        """Evaluate auto-scaling rule"""
        current_value = await self._get_metric_value(rule.trigger)
        healthy_instances = len([s for s in self.servers.values() if s.status == ServerStatus.HEALTHY])
        
        # Check for scale-up condition
        if (current_value > rule.threshold_up and 
            healthy_instances < rule.max_instances and
            self._can_scale(rule)):
            
            await self._scale_out(rule, current_value, healthy_instances)
        
        # Check for scale-down condition
        elif (current_value < rule.threshold_down and 
              healthy_instances > rule.min_instances and
              self._can_scale(rule)):
            
            await self._scale_in(rule, current_value, healthy_instances)
    
    async def _get_metric_value(self, trigger: AutoScalingTrigger) -> float:
        """Get current metric value for scaling trigger"""
        if trigger == AutoScalingTrigger.CPU_USAGE:
            healthy_servers = [s for s in self.servers.values() if s.status == ServerStatus.HEALTHY]
            return np.mean([s.cpu_usage for s in healthy_servers]) if healthy_servers else 0
        
        elif trigger == AutoScalingTrigger.MEMORY_USAGE:
            healthy_servers = [s for s in self.servers.values() if s.status == ServerStatus.HEALTHY]
            return np.mean([s.memory_usage for s in healthy_servers]) if healthy_servers else 0
        
        elif trigger == AutoScalingTrigger.RESPONSE_TIME:
            healthy_servers = [s for s in self.servers.values() if s.status == ServerStatus.HEALTHY]
            return np.mean([s.avg_response_time for s in healthy_servers]) if healthy_servers else 0
        
        elif trigger == AutoScalingTrigger.REQUEST_RATE:
            # Calculate requests per minute from recent metrics
            recent_requests = [m for m in self.request_metrics 
                             if datetime.fromisoformat(m.timestamp.replace('Z', '+00:00').replace('+00:00', '')) > 
                                datetime.now() - timedelta(minutes=1)]
            return len(recent_requests)
        
        elif trigger == AutoScalingTrigger.ERROR_RATE:
            if self.request_metrics:
                recent_requests = list(self.request_metrics)[-100:]  # Last 100 requests
                error_count = sum(1 for r in recent_requests if r.status_code >= 400)
                return (error_count / len(recent_requests)) * 100
            return 0
        
        return 0
    
    def _can_scale(self, rule: AutoScalingRule) -> bool:
        """Check if scaling is allowed (cooldown period)"""
        # Check if there's a recent scaling event for this rule
        recent_events = [e for e in self.scaling_events.values() 
                        if e.rule_id == rule.id and 
                           datetime.fromisoformat(e.timestamp.replace('Z', '+00:00').replace('+00:00', '')) > 
                           datetime.now() - timedelta(seconds=rule.cooldown_period)]
        
        return len(recent_events) == 0
    
    async def _scale_out(self, rule: AutoScalingRule, trigger_value: float, current_instances: int):
        """Scale out (add instances)"""
        new_instances = min(rule.scale_up_count, rule.max_instances - current_instances)
        
        for i in range(new_instances):
            # Create new server instance (simplified)
            base_port = 9000 + len(self.servers)
            server_id = f"auto-{base_port}"
            
            new_server = ServerInstance(
                id=server_id,
                host="localhost",
                port=base_port,
                weight=1.0,
                status=ServerStatus.STARTING,
                health_score=1.0,
                last_health_check=datetime.now().isoformat(),
                active_connections=0,
                total_requests=0,
                avg_response_time=0.0,
                error_rate=0.0,
                cpu_usage=20.0,
                memory_usage=30.0,
                created_at=datetime.now().isoformat(),
                tags={"auto_scaled": "true"}
            )
            
            self.servers[server_id] = new_server
            
            # Simulate startup time
            await asyncio.sleep(1)
            new_server.status = ServerStatus.HEALTHY
        
        # Record scaling event
        event = ScalingEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            direction=ScalingDirection.UP,
            trigger=rule.trigger,
            trigger_value=trigger_value,
            instances_before=current_instances,
            instances_after=current_instances + new_instances,
            rule_id=rule.id,
            reason=f"Metric {rule.trigger.value} exceeded threshold {rule.threshold_up}"
        )
        
        self.scaling_events[event.id] = event
        logger.info(f"Scaled out: added {new_instances} instances due to {rule.trigger.value} = {trigger_value}")
    
    async def _scale_in(self, rule: AutoScalingRule, trigger_value: float, current_instances: int):
        """Scale in (remove instances)"""
        # Find auto-scaled instances to remove
        auto_scaled_servers = [s for s in self.servers.values() 
                              if s.tags.get("auto_scaled") == "true" and s.status == ServerStatus.HEALTHY]
        
        remove_count = min(rule.scale_down_count, 
                          len(auto_scaled_servers),
                          current_instances - rule.min_instances)
        
        if remove_count > 0:
            # Sort by lowest utilization and remove
            auto_scaled_servers.sort(key=lambda s: s.active_connections + s.cpu_usage)
            
            for i in range(remove_count):
                server = auto_scaled_servers[i]
                server.status = ServerStatus.STOPPING
                
                # Wait for connections to drain
                await asyncio.sleep(5)
                
                # Remove server
                del self.servers[server.id]
            
            # Record scaling event
            event = ScalingEvent(
                id=str(uuid.uuid4()),
                timestamp=datetime.now().isoformat(),
                direction=ScalingDirection.DOWN,
                trigger=rule.trigger,
                trigger_value=trigger_value,
                instances_before=current_instances,
                instances_after=current_instances - remove_count,
                rule_id=rule.id,
                reason=f"Metric {rule.trigger.value} below threshold {rule.threshold_down}"
            )
            
            self.scaling_events[event.id] = event
            logger.info(f"Scaled in: removed {remove_count} instances due to {rule.trigger.value} = {trigger_value}")
    
    async def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics"""
        healthy_servers = [s for s in self.servers.values() if s.status == ServerStatus.HEALTHY]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "algorithm": self.config.algorithm.value,
            "total_servers": len(self.servers),
            "healthy_servers": len(healthy_servers),
            "total_requests": sum(len(self.request_metrics)),
            "avg_response_time": np.mean([s.avg_response_time for s in healthy_servers]) if healthy_servers else 0,
            "total_active_connections": sum(s.active_connections for s in healthy_servers),
            "avg_cpu_usage": np.mean([s.cpu_usage for s in healthy_servers]) if healthy_servers else 0,
            "avg_memory_usage": np.mean([s.memory_usage for s in healthy_servers]) if healthy_servers else 0,
            "circuit_breakers_open": sum(1 for cb in self.circuit_breaker_state.values() if cb["open"]),
            "recent_scaling_events": len([e for e in self.scaling_events.values() 
                                        if datetime.fromisoformat(e.timestamp.replace('Z', '+00:00').replace('+00:00', '')) > 
                                           datetime.now() - timedelta(hours=1)])
        }

# Initialize the load balancer system
load_balancer = LoadBalancerSystem()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Load Balancer & Scaling Infrastructure",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "load_balancing",
            "auto_scaling",
            "health_monitoring",
            "circuit_breaker",
            "sticky_sessions"
        ],
        "servers_count": len(load_balancer.servers),
        "healthy_servers": len([s for s in load_balancer.servers.values() if s.status == ServerStatus.HEALTHY])
    }

@app.get("/servers")
async def get_servers():
    """Get all server instances"""
    return {
        "servers": [asdict(server) for server in load_balancer.servers.values()],
        "total": len(load_balancer.servers)
    }

@app.post("/servers")
async def add_server(server_config: ServerConfig):
    """Add new server instance"""
    server_id = f"{server_config.host}:{server_config.port}"
    
    if server_id in load_balancer.servers:
        raise HTTPException(status_code=409, detail="Server already exists")
    
    new_server = ServerInstance(
        id=server_id,
        host=server_config.host,
        port=server_config.port,
        weight=server_config.weight,
        status=ServerStatus.HEALTHY,
        health_score=1.0,
        last_health_check=datetime.now().isoformat(),
        active_connections=0,
        total_requests=0,
        avg_response_time=0.0,
        error_rate=0.0,
        cpu_usage=50.0,
        memory_usage=50.0,
        created_at=datetime.now().isoformat(),
        tags=server_config.tags
    )
    
    load_balancer.servers[server_id] = new_server
    
    return {"message": "Server added successfully", "server": asdict(new_server)}

@app.delete("/servers/{server_id}")
async def remove_server(server_id: str):
    """Remove server instance"""
    if server_id not in load_balancer.servers:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server = load_balancer.servers[server_id]
    server.status = ServerStatus.STOPPING
    
    # Wait for connections to drain
    await asyncio.sleep(2)
    
    del load_balancer.servers[server_id]
    
    return {"message": "Server removed successfully"}

@app.get("/stats")
async def get_load_balancer_stats():
    """Get load balancer statistics"""
    stats = await load_balancer.get_load_balancer_stats()
    return {"stats": stats}

@app.get("/scaling/rules")
async def get_scaling_rules():
    """Get auto-scaling rules"""
    return {
        "rules": [asdict(rule) for rule in load_balancer.autoscaling_rules.values()],
        "total": len(load_balancer.autoscaling_rules)
    }

@app.get("/scaling/events")
async def get_scaling_events(limit: int = 50):
    """Get scaling events history"""
    events = list(load_balancer.scaling_events.values())
    events.sort(key=lambda x: x.timestamp, reverse=True)
    
    return {
        "events": [asdict(event) for event in events[:limit]],
        "total": len(events)
    }

@app.get("/metrics/requests")
async def get_request_metrics(limit: int = 100):
    """Get request metrics"""
    metrics = list(load_balancer.request_metrics)[-limit:]
    
    return {
        "metrics": [asdict(metric) for metric in metrics],
        "total": len(metrics)
    }

@app.post("/config/algorithm")
async def update_algorithm(algorithm: LoadBalancingAlgorithm):
    """Update load balancing algorithm"""
    load_balancer.config.algorithm = algorithm
    load_balancer.round_robin_index = 0  # Reset round robin counter
    
    return {"message": "Algorithm updated", "algorithm": algorithm.value}

# Load balancing proxy endpoint
@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(request: Request):
    """Proxy requests to backend servers"""
    return await load_balancer.route_request(request)

if __name__ == "__main__":
    uvicorn.run(
        "load_balancer:app",
        host="0.0.0.0",
        port=8070,
        reload=True,
        log_level="info"
    )