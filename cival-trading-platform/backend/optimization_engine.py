#!/usr/bin/env python3
"""
Performance Optimization Engine
Advanced caching, optimization, and performance monitoring system
"""

import asyncio
import json
import logging
import time
import psutil
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field
import uuid
from enum import Enum
import redis
from collections import defaultdict, deque
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/optimization_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Performance Optimization Engine",
    description="Advanced caching, optimization, and performance monitoring",
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
class CacheType(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    HYBRID = "hybrid"

class OptimizationLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

class MetricType(str, Enum):
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    CACHE_HIT_RATE = "cache_hit_rate"
    ERROR_RATE = "error_rate"

# Data models
@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: Optional[float]
    size_bytes: int
    metadata: Dict[str, Any]

@dataclass
class PerformanceMetric:
    metric_type: MetricType
    value: float
    timestamp: str
    tags: Dict[str, str]
    aggregation_window: str

@dataclass
class OptimizationRecommendation:
    id: str
    type: str
    description: str
    impact: str
    implementation_effort: str
    estimated_improvement: float
    priority: int
    automated: bool
    parameters: Dict[str, Any]

@dataclass
class SystemHealthReport:
    id: str
    timestamp: str
    overall_health: float
    performance_metrics: Dict[str, float]
    resource_utilization: Dict[str, float]
    bottlenecks: List[str]
    recommendations: List[OptimizationRecommendation]
    alerts: List[str]
    trends: Dict[str, str]

class CacheConfig(BaseModel):
    cache_type: CacheType = Field(default=CacheType.MEMORY, description="Cache implementation type")
    max_size: int = Field(default=10000, description="Maximum cache entries")
    ttl_seconds: int = Field(default=3600, description="Default TTL in seconds")
    eviction_policy: str = Field(default="lru", description="Cache eviction policy")
    compression: bool = Field(default=False, description="Enable data compression")

class OptimizationRequest(BaseModel):
    target: str = Field(..., description="Optimization target (endpoint, service, etc.)")
    level: OptimizationLevel = Field(default=OptimizationLevel.MEDIUM, description="Optimization level")
    metrics: List[MetricType] = Field(default=[], description="Metrics to optimize")
    constraints: Dict[str, Any] = Field(default={}, description="Optimization constraints")

class PerformanceOptimizationEngine:
    def __init__(self):
        self.cache_layers = {}
        self.performance_metrics = defaultdict(deque)
        self.optimization_recommendations = {}
        self.health_reports = {}
        
        # Performance monitoring
        self.request_latencies = deque(maxlen=10000)
        self.error_counts = defaultdict(int)
        self.cache_stats = defaultdict(lambda: {'hits': 0, 'misses': 0})
        
        # Initialize cache layers
        self._initialize_cache_layers()
        
        # Initialize optimization algorithms
        self._initialize_optimization_algorithms()
        
        # Start background monitoring
        self.monitoring_active = True
        asyncio.create_task(self._monitor_performance())
        
        logger.info("Performance Optimization Engine initialized")
    
    def _initialize_cache_layers(self):
        """Initialize multi-layer caching system"""
        # L1 Cache: In-memory for hot data
        self.cache_layers['l1'] = {
            'type': CacheType.MEMORY,
            'data': {},
            'stats': {'hits': 0, 'misses': 0, 'evictions': 0},
            'config': {'max_size': 1000, 'ttl': 300}  # 5 minutes
        }
        
        # L2 Cache: Redis for shared cache
        self.cache_layers['l2'] = {
            'type': CacheType.REDIS,
            'data': {},  # Mock Redis interface
            'stats': {'hits': 0, 'misses': 0, 'evictions': 0},
            'config': {'max_size': 10000, 'ttl': 3600}  # 1 hour
        }
        
        # L3 Cache: Disk for large data
        self.cache_layers['l3'] = {
            'type': CacheType.DISK,
            'data': {},  # Mock disk cache
            'stats': {'hits': 0, 'misses': 0, 'evictions': 0},
            'config': {'max_size': 100000, 'ttl': 86400}  # 24 hours
        }
        
        logger.info("Multi-layer cache system initialized")
    
    def _initialize_optimization_algorithms(self):
        """Initialize optimization algorithms"""
        self.optimization_algorithms = {
            'auto_scaling': self._auto_scaling_optimizer,
            'cache_tuning': self._cache_tuning_optimizer,
            'query_optimization': self._query_optimization,
            'resource_allocation': self._resource_allocation_optimizer,
            'load_balancing': self._load_balancing_optimizer
        }
        
        logger.info("Optimization algorithms initialized")
    
    async def get_from_cache(self, key: str, layer: str = None) -> Optional[Any]:
        """Get value from cache with automatic layer traversal"""
        cache_key = self._generate_cache_key(key)
        
        if layer:
            return await self._get_from_specific_layer(cache_key, layer)
        
        # Try L1 first (fastest)
        value = await self._get_from_specific_layer(cache_key, 'l1')
        if value is not None:
            return value
        
        # Try L2 (Redis)
        value = await self._get_from_specific_layer(cache_key, 'l2')
        if value is not None:
            # Promote to L1
            await self._set_to_specific_layer(cache_key, value, 'l1')
            return value
        
        # Try L3 (Disk)
        value = await self._get_from_specific_layer(cache_key, 'l3')
        if value is not None:
            # Promote to L2 and L1
            await self._set_to_specific_layer(cache_key, value, 'l2')
            await self._set_to_specific_layer(cache_key, value, 'l1')
            return value
        
        return None
    
    async def set_to_cache(self, key: str, value: Any, ttl: int = None, layer: str = None) -> bool:
        """Set value to cache with automatic layer distribution"""
        cache_key = self._generate_cache_key(key)
        
        if layer:
            return await self._set_to_specific_layer(cache_key, value, layer, ttl)
        
        # Set to all layers (write-through strategy)
        success = True
        success &= await self._set_to_specific_layer(cache_key, value, 'l1', ttl or 300)
        success &= await self._set_to_specific_layer(cache_key, value, 'l2', ttl or 3600)
        success &= await self._set_to_specific_layer(cache_key, value, 'l3', ttl or 86400)
        
        return success
    
    async def _get_from_specific_layer(self, key: str, layer: str) -> Optional[Any]:
        """Get value from specific cache layer"""
        cache_layer = self.cache_layers[layer]
        
        if key in cache_layer['data']:
            entry = cache_layer['data'][key]
            
            # Check TTL
            if entry.ttl and time.time() > entry.created_at + entry.ttl:
                del cache_layer['data'][key]
                cache_layer['stats']['misses'] += 1
                return None
            
            # Update access statistics
            entry.last_accessed = time.time()
            entry.access_count += 1
            cache_layer['stats']['hits'] += 1
            
            return entry.value
        
        cache_layer['stats']['misses'] += 1
        return None
    
    async def _set_to_specific_layer(self, key: str, value: Any, layer: str, ttl: int = None) -> bool:
        """Set value to specific cache layer"""
        cache_layer = self.cache_layers[layer]
        config = cache_layer['config']
        
        # Check size limits
        if len(cache_layer['data']) >= config['max_size']:
            await self._evict_cache_entries(layer)
        
        # Calculate entry size (simplified)
        try:
            size_bytes = len(json.dumps(value, default=str))
        except:
            size_bytes = 1024  # Default size
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=1,
            ttl=ttl or config['ttl'],
            size_bytes=size_bytes,
            metadata={'layer': layer}
        )
        
        cache_layer['data'][key] = entry
        return True
    
    async def _evict_cache_entries(self, layer: str):
        """Evict cache entries using LRU policy"""
        cache_layer = self.cache_layers[layer]
        
        if not cache_layer['data']:
            return
        
        # Sort by last access time (LRU)
        sorted_entries = sorted(
            cache_layer['data'].items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove 10% of entries
        evict_count = max(1, len(sorted_entries) // 10)
        
        for i in range(evict_count):
            key, _ = sorted_entries[i]
            del cache_layer['data'][key]
            cache_layer['stats']['evictions'] += 1
    
    def _generate_cache_key(self, key: str) -> str:
        """Generate consistent cache key"""
        return hashlib.md5(key.encode()).hexdigest()
    
    async def record_performance_metric(self, metric_type: MetricType, value: float, tags: Dict[str, str] = None):
        """Record performance metric"""
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now().isoformat(),
            tags=tags or {},
            aggregation_window="1m"
        )
        
        self.performance_metrics[metric_type].append(metric)
        
        # Keep only recent metrics
        if len(self.performance_metrics[metric_type]) > 10000:
            self.performance_metrics[metric_type].popleft()
    
    async def optimize_performance(self, request: OptimizationRequest) -> List[OptimizationRecommendation]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Analyze current performance
        current_metrics = await self._analyze_current_performance(request.target)
        
        # Run optimization algorithms
        for algorithm_name, algorithm_func in self.optimization_algorithms.items():
            try:
                recs = await algorithm_func(request, current_metrics)
                recommendations.extend(recs)
            except Exception as e:
                logger.error(f"Error in {algorithm_name}: {e}")
        
        # Sort by priority and impact
        recommendations.sort(key=lambda x: (x.priority, -x.estimated_improvement))
        
        # Store recommendations
        for rec in recommendations:
            self.optimization_recommendations[rec.id] = rec
        
        logger.info(f"Generated {len(recommendations)} optimization recommendations for {request.target}")
        
        return recommendations
    
    async def _analyze_current_performance(self, target: str) -> Dict[str, float]:
        """Analyze current performance metrics"""
        metrics = {}
        
        # Calculate average latency
        if self.request_latencies:
            metrics['avg_latency'] = np.mean(list(self.request_latencies))
            metrics['p95_latency'] = np.percentile(list(self.request_latencies), 95)
            metrics['p99_latency'] = np.percentile(list(self.request_latencies), 99)
        
        # Calculate cache hit rates
        total_hits = sum(layer['stats']['hits'] for layer in self.cache_layers.values())
        total_requests = total_hits + sum(layer['stats']['misses'] for layer in self.cache_layers.values())
        
        if total_requests > 0:
            metrics['cache_hit_rate'] = total_hits / total_requests
        
        # System resource metrics
        metrics['cpu_usage'] = psutil.cpu_percent()
        metrics['memory_usage'] = psutil.virtual_memory().percent
        
        # Error rate
        total_errors = sum(self.error_counts.values())
        metrics['error_rate'] = total_errors / max(1, total_requests)
        
        return metrics
    
    async def _auto_scaling_optimizer(self, request: OptimizationRequest, metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Auto-scaling optimization recommendations"""
        recommendations = []
        
        cpu_usage = metrics.get('cpu_usage', 0)
        memory_usage = metrics.get('memory_usage', 0)
        
        if cpu_usage > 80:
            rec = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type="auto_scaling",
                description="High CPU usage detected - recommend horizontal scaling",
                impact="high",
                implementation_effort="medium",
                estimated_improvement=25.0,
                priority=1,
                automated=True,
                parameters={
                    "action": "scale_out",
                    "target_instances": 2,
                    "cpu_threshold": 80
                }
            )
            recommendations.append(rec)
        
        if memory_usage > 85:
            rec = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type="memory_optimization",
                description="High memory usage - recommend memory optimization",
                impact="medium",
                implementation_effort="low",
                estimated_improvement=15.0,
                priority=2,
                automated=True,
                parameters={
                    "action": "optimize_memory",
                    "target_reduction": 20
                }
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _cache_tuning_optimizer(self, request: OptimizationRequest, metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Cache tuning optimization recommendations"""
        recommendations = []
        
        cache_hit_rate = metrics.get('cache_hit_rate', 0)
        
        if cache_hit_rate < 0.7:  # Less than 70% hit rate
            rec = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type="cache_optimization",
                description="Low cache hit rate - recommend cache tuning",
                impact="high",
                implementation_effort="medium",
                estimated_improvement=30.0,
                priority=1,
                automated=True,
                parameters={
                    "action": "increase_cache_size",
                    "l1_size_multiplier": 2,
                    "l2_size_multiplier": 1.5,
                    "optimize_ttl": True
                }
            )
            recommendations.append(rec)
        
        # Analyze cache layer efficiency
        l1_efficiency = self._calculate_cache_efficiency('l1')
        l2_efficiency = self._calculate_cache_efficiency('l2')
        
        if l1_efficiency < 0.5:
            rec = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type="cache_strategy",
                description="L1 cache inefficient - optimize hot data identification",
                impact="medium",
                implementation_effort="high",
                estimated_improvement=20.0,
                priority=3,
                automated=False,
                parameters={
                    "action": "optimize_l1_strategy",
                    "use_access_patterns": True,
                    "implement_predictive_caching": True
                }
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _calculate_cache_efficiency(self, layer: str) -> float:
        """Calculate cache layer efficiency"""
        cache_layer = self.cache_layers[layer]
        stats = cache_layer['stats']
        
        total_operations = stats['hits'] + stats['misses']
        if total_operations == 0:
            return 0.0
        
        hit_rate = stats['hits'] / total_operations
        eviction_rate = stats['evictions'] / max(1, stats['hits'])
        
        # Efficiency considers both hit rate and eviction impact
        efficiency = hit_rate * (1 - min(0.5, eviction_rate))
        
        return efficiency
    
    async def _query_optimization(self, request: OptimizationRequest, metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Query optimization recommendations"""
        recommendations = []
        
        avg_latency = metrics.get('avg_latency', 0)
        p95_latency = metrics.get('p95_latency', 0)
        
        if avg_latency > 500:  # More than 500ms average
            rec = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type="query_optimization",
                description="High query latency - recommend query optimization",
                impact="high",
                implementation_effort="medium",
                estimated_improvement=40.0,
                priority=1,
                automated=False,
                parameters={
                    "action": "optimize_queries",
                    "add_indexes": True,
                    "optimize_joins": True,
                    "implement_query_caching": True
                }
            )
            recommendations.append(rec)
        
        if p95_latency > 2000:  # P95 > 2 seconds
            rec = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type="database_optimization",
                description="High P95 latency - recommend database optimization",
                impact="high",
                implementation_effort="high",
                estimated_improvement=35.0,
                priority=2,
                automated=False,
                parameters={
                    "action": "database_tuning",
                    "connection_pooling": True,
                    "read_replicas": True,
                    "partition_tables": True
                }
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _resource_allocation_optimizer(self, request: OptimizationRequest, metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Resource allocation optimization recommendations"""
        recommendations = []
        
        cpu_usage = metrics.get('cpu_usage', 0)
        memory_usage = metrics.get('memory_usage', 0)
        
        # Check for resource imbalance
        if cpu_usage > 80 and memory_usage < 50:
            rec = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type="resource_rebalancing",
                description="CPU-bound workload with available memory - optimize resource allocation",
                impact="medium",
                implementation_effort="low",
                estimated_improvement=20.0,
                priority=2,
                automated=True,
                parameters={
                    "action": "rebalance_resources",
                    "increase_cpu_allocation": True,
                    "enable_cpu_caching": True
                }
            )
            recommendations.append(rec)
        
        elif memory_usage > 80 and cpu_usage < 50:
            rec = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type="memory_optimization",
                description="Memory-bound workload - optimize memory usage",
                impact="medium",
                implementation_effort="medium",
                estimated_improvement=25.0,
                priority=2,
                automated=True,
                parameters={
                    "action": "optimize_memory_usage",
                    "enable_compression": True,
                    "implement_memory_pooling": True
                }
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _load_balancing_optimizer(self, request: OptimizationRequest, metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Load balancing optimization recommendations"""
        recommendations = []
        
        error_rate = metrics.get('error_rate', 0)
        avg_latency = metrics.get('avg_latency', 0)
        
        if error_rate > 0.01:  # More than 1% error rate
            rec = OptimizationRecommendation(
                id=str(uuid.uuid4()),
                type="load_balancing",
                description="High error rate - implement intelligent load balancing",
                impact="high",
                implementation_effort="medium",
                estimated_improvement=30.0,
                priority=1,
                automated=True,
                parameters={
                    "action": "implement_load_balancing",
                    "algorithm": "weighted_round_robin",
                    "health_checks": True,
                    "circuit_breaker": True
                }
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def generate_health_report(self) -> SystemHealthReport:
        """Generate comprehensive system health report"""
        report_id = str(uuid.uuid4())
        
        # Collect current metrics
        current_metrics = await self._analyze_current_performance("system")
        
        # Calculate overall health score
        health_factors = []
        
        # Latency health (lower is better)
        avg_latency = current_metrics.get('avg_latency', 0)
        latency_health = max(0, 1 - min(1, avg_latency / 1000))  # Normalize to 1000ms
        health_factors.append(latency_health)
        
        # Cache hit rate health
        cache_health = current_metrics.get('cache_hit_rate', 0)
        health_factors.append(cache_health)
        
        # Resource utilization health
        cpu_health = max(0, 1 - current_metrics.get('cpu_usage', 0) / 100)
        memory_health = max(0, 1 - current_metrics.get('memory_usage', 0) / 100)
        health_factors.extend([cpu_health, memory_health])
        
        # Error rate health
        error_health = max(0, 1 - current_metrics.get('error_rate', 0) * 100)
        health_factors.append(error_health)
        
        overall_health = np.mean(health_factors)
        
        # Identify bottlenecks
        bottlenecks = []
        if current_metrics.get('cpu_usage', 0) > 80:
            bottlenecks.append("High CPU utilization")
        if current_metrics.get('memory_usage', 0) > 80:
            bottlenecks.append("High memory utilization")
        if current_metrics.get('cache_hit_rate', 1) < 0.7:
            bottlenecks.append("Low cache hit rate")
        if current_metrics.get('avg_latency', 0) > 500:
            bottlenecks.append("High response latency")
        
        # Generate optimization recommendations
        opt_request = OptimizationRequest(
            target="system",
            level=OptimizationLevel.MEDIUM,
            metrics=[MetricType.LATENCY, MetricType.THROUGHPUT, MetricType.CACHE_HIT_RATE]
        )
        recommendations = await self.optimize_performance(opt_request)
        
        # Generate alerts
        alerts = []
        if overall_health < 0.7:
            alerts.append("System health below threshold")
        if current_metrics.get('error_rate', 0) > 0.05:
            alerts.append("High error rate detected")
        if len(bottlenecks) > 2:
            alerts.append("Multiple performance bottlenecks identified")
        
        # Analyze trends (simplified)
        trends = {
            "performance": "stable",
            "resource_usage": "increasing" if current_metrics.get('cpu_usage', 0) > 70 else "stable",
            "error_rate": "stable"
        }
        
        report = SystemHealthReport(
            id=report_id,
            timestamp=datetime.now().isoformat(),
            overall_health=round(overall_health, 3),
            performance_metrics=current_metrics,
            resource_utilization={
                "cpu": current_metrics.get('cpu_usage', 0),
                "memory": current_metrics.get('memory_usage', 0),
                "cache": current_metrics.get('cache_hit_rate', 0) * 100
            },
            bottlenecks=bottlenecks,
            recommendations=recommendations[:5],  # Top 5 recommendations
            alerts=alerts,
            trends=trends
        )
        
        self.health_reports[report_id] = report
        
        logger.info(f"Generated health report: {overall_health:.1%} health score")
        
        return report
    
    async def _monitor_performance(self):
        """Background performance monitoring"""
        while self.monitoring_active:
            try:
                # Record system metrics
                await self.record_performance_metric(
                    MetricType.CPU_USAGE,
                    psutil.cpu_percent(),
                    {"component": "system"}
                )
                
                await self.record_performance_metric(
                    MetricType.MEMORY_USAGE,
                    psutil.virtual_memory().percent,
                    {"component": "system"}
                )
                
                # Calculate and record cache hit rates
                for layer_name, layer in self.cache_layers.items():
                    stats = layer['stats']
                    total_ops = stats['hits'] + stats['misses']
                    
                    if total_ops > 0:
                        hit_rate = stats['hits'] / total_ops
                        await self.record_performance_metric(
                            MetricType.CACHE_HIT_RATE,
                            hit_rate,
                            {"layer": layer_name}
                        )
                
                # Check for performance degradation
                await self._check_performance_degradation()
                
                # Wait before next monitoring cycle
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _check_performance_degradation(self):
        """Check for performance degradation and trigger auto-optimization"""
        current_metrics = await self._analyze_current_performance("system")
        
        # Auto-trigger optimization if performance degrades
        if (current_metrics.get('avg_latency', 0) > 1000 or 
            current_metrics.get('cpu_usage', 0) > 90 or
            current_metrics.get('error_rate', 0) > 0.05):
            
            logger.warning("Performance degradation detected - triggering auto-optimization")
            
            opt_request = OptimizationRequest(
                target="system",
                level=OptimizationLevel.HIGH,
                metrics=[MetricType.LATENCY, MetricType.CPU_USAGE, MetricType.ERROR_RATE]
            )
            
            recommendations = await self.optimize_performance(opt_request)
            
            # Auto-apply certain optimizations
            for rec in recommendations:
                if rec.automated and rec.priority <= 2:
                    await self._apply_optimization(rec)
    
    async def _apply_optimization(self, recommendation: OptimizationRecommendation):
        """Apply automated optimization recommendation"""
        try:
            action = recommendation.parameters.get("action")
            
            if action == "increase_cache_size":
                # Increase cache sizes
                multiplier = recommendation.parameters.get("l1_size_multiplier", 1.5)
                self.cache_layers['l1']['config']['max_size'] = int(
                    self.cache_layers['l1']['config']['max_size'] * multiplier
                )
                
                logger.info(f"Applied cache size optimization: L1 cache increased by {multiplier}x")
            
            elif action == "optimize_memory":
                # Enable compression for cache layers
                for layer in self.cache_layers.values():
                    layer['config']['compression'] = True
                
                logger.info("Applied memory optimization: enabled compression")
            
            # Mark recommendation as applied
            recommendation.parameters['applied_at'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Error applying optimization {recommendation.id}: {e}")

# Initialize the optimization engine
optimization_engine = PerformanceOptimizationEngine()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Performance Optimization Engine",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "multi_layer_caching",
            "performance_monitoring",
            "auto_optimization",
            "resource_analysis",
            "bottleneck_detection"
        ],
        "cache_layers": len(optimization_engine.cache_layers),
        "active_recommendations": len(optimization_engine.optimization_recommendations),
        "monitoring_active": optimization_engine.monitoring_active
    }

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    stats = {}
    
    for layer_name, layer in optimization_engine.cache_layers.items():
        layer_stats = layer['stats'].copy()
        layer_stats['entries'] = len(layer['data'])
        layer_stats['config'] = layer['config']
        
        # Calculate hit rate
        total_ops = layer_stats['hits'] + layer_stats['misses']
        layer_stats['hit_rate'] = layer_stats['hits'] / total_ops if total_ops > 0 else 0
        
        stats[layer_name] = layer_stats
    
    return {"cache_stats": stats}

@app.get("/cache/{key}")
async def get_cached_value(key: str):
    """Get value from cache"""
    value = await optimization_engine.get_from_cache(key)
    
    if value is not None:
        return {"key": key, "value": value, "cached": True}
    else:
        raise HTTPException(status_code=404, detail="Key not found in cache")

@app.post("/cache/{key}")
async def set_cached_value(key: str, value: dict, ttl: int = None):
    """Set value in cache"""
    success = await optimization_engine.set_to_cache(key, value, ttl)
    
    if success:
        return {"key": key, "cached": True, "ttl": ttl}
    else:
        raise HTTPException(status_code=500, detail="Failed to cache value")

@app.post("/optimize")
async def optimize_performance(request: OptimizationRequest):
    """Generate performance optimization recommendations"""
    try:
        recommendations = await optimization_engine.optimize_performance(request)
        return {
            "recommendations": [asdict(rec) for rec in recommendations],
            "total": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"Error optimizing performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health-report")
async def get_health_report():
    """Generate and return system health report"""
    try:
        report = await optimization_engine.generate_health_report()
        return {"health_report": asdict(report)}
        
    except Exception as e:
        logger.error(f"Error generating health report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations")
async def get_recommendations(limit: int = 50):
    """Get optimization recommendations"""
    recommendations = list(optimization_engine.optimization_recommendations.values())
    
    # Sort by priority and timestamp
    recommendations.sort(key=lambda x: (x.priority, x.estimated_improvement), reverse=True)
    
    return {
        "recommendations": [asdict(rec) for rec in recommendations[:limit]],
        "total": len(recommendations)
    }

@app.get("/metrics/{metric_type}")
async def get_performance_metrics(metric_type: MetricType, limit: int = 100):
    """Get performance metrics"""
    if metric_type not in optimization_engine.performance_metrics:
        raise HTTPException(status_code=404, detail="Metric type not found")
    
    metrics = list(optimization_engine.performance_metrics[metric_type])[-limit:]
    
    return {
        "metric_type": metric_type,
        "metrics": [asdict(metric) for metric in metrics],
        "total": len(metrics)
    }

@app.post("/metrics/record")
async def record_metric(metric_type: MetricType, value: float, tags: dict = None):
    """Record a performance metric"""
    await optimization_engine.record_performance_metric(metric_type, value, tags)
    
    return {
        "metric_type": metric_type,
        "value": value,
        "recorded_at": datetime.now().isoformat()
    }

@app.get("/system/status")
async def get_system_status():
    """Get current system status"""
    current_metrics = await optimization_engine._analyze_current_performance("system")
    
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": current_metrics,
        "cache_layers": len(optimization_engine.cache_layers),
        "monitoring_active": optimization_engine.monitoring_active,
        "total_recommendations": len(optimization_engine.optimization_recommendations)
    }

if __name__ == "__main__":
    uvicorn.run(
        "optimization_engine:app",
        host="0.0.0.0",
        port=8060,
        reload=True,
        log_level="info"
    )