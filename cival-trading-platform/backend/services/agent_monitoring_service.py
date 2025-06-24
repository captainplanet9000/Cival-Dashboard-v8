"""
Phase 9: Agent Performance Monitoring and Optimization Service
Real-time monitoring, analytics, and optimization recommendations for autonomous agents
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import json
import logging
import statistics
from dataclasses import dataclass, field
from collections import defaultdict, deque
import numpy as np
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.agent_orchestration_models import (
    AutonomousAgent, AgentStatus, AgentOptimization, AgentMetrics,
    TaskStatus, TaskPriority, CoordinationMode
)
from services.agent_lifecycle_service import get_lifecycle_service
from services.task_distribution_service import get_task_distribution_service
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of performance metrics"""
    PERFORMANCE = "performance"
    RESOURCE_USAGE = "resource_usage"
    RELIABILITY = "reliability"
    EFFICIENCY = "efficiency"
    COLLABORATION = "collaboration"
    LEARNING = "learning"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class OptimizationCategory(str, Enum):
    """Optimization categories"""
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    COLLABORATION = "collaboration"
    LEARNING = "learning"
    RELIABILITY = "reliability"


@dataclass
class MetricDataPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSeriesMetric:
    """Time series metric storage"""
    metric_name: str
    metric_type: MetricType
    data_points: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_point(self, value: float, metadata: Dict[str, Any] = None):
        """Add a new data point"""
        self.data_points.append(MetricDataPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            metadata=metadata or {}
        ))
    
    def get_recent_values(self, hours: int = 1) -> List[float]:
        """Get values from the last N hours"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            point.value for point in self.data_points 
            if point.timestamp >= cutoff
        ]
    
    def get_average(self, hours: int = 1) -> float:
        """Get average value over time period"""
        values = self.get_recent_values(hours)
        return statistics.mean(values) if values else 0.0
    
    def get_trend(self, hours: int = 1) -> str:
        """Determine trend direction"""
        values = self.get_recent_values(hours)
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        if not first_half or not second_half:
            return "stable"
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        if second_avg > first_avg * 1.05:
            return "increasing"
        elif second_avg < first_avg * 0.95:
            return "decreasing"
        else:
            return "stable"


class PerformanceAlert(BaseModel):
    """Performance alert"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    metric_name: str
    current_value: float
    threshold: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PerformanceBaseline(BaseModel):
    """Performance baseline for an agent"""
    agent_id: str
    metric_baselines: Dict[str, Dict[str, float]] = Field(default_factory=dict)  # metric_name -> {mean, std, min, max}
    established_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sample_count: int = 0
    confidence_level: float = 0.0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OptimizationRecommendation(BaseModel):
    """Optimization recommendation"""
    recommendation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    category: OptimizationCategory
    title: str
    description: str
    impact_level: str  # low, medium, high
    confidence: float = Field(ge=0.0, le=1.0)
    estimated_improvement: Dict[str, float] = Field(default_factory=dict)
    implementation_steps: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending, approved, implemented, rejected


class AgentPerformanceProfile(BaseModel):
    """Comprehensive agent performance profile"""
    agent_id: str
    current_metrics: Dict[str, float] = Field(default_factory=dict)
    performance_score: float = 0.0
    efficiency_rating: str = "unknown"
    reliability_score: float = 0.0
    collaboration_score: float = 0.0
    learning_rate: float = 0.0
    trend_analysis: Dict[str, str] = Field(default_factory=dict)
    bottlenecks: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    last_assessment: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMonitoringService:
    """
    Comprehensive agent performance monitoring and optimization service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
        # Metric storage
        self.agent_metrics: Dict[str, Dict[str, TimeSeriesMetric]] = defaultdict(dict)
        self.performance_baselines: Dict[str, PerformanceBaseline] = {}
        self.performance_profiles: Dict[str, AgentPerformanceProfile] = {}
        
        # Alerting
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_thresholds: Dict[str, Dict[str, float]] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        
        # Optimization
        self.optimization_recommendations: Dict[str, List[OptimizationRecommendation]] = defaultdict(list)
        self.optimization_history: List[Dict[str, Any]] = []
        
        # Configuration
        self.monitoring_interval = 30  # seconds
        self.baseline_learning_period = timedelta(hours=24)
        self.alert_cooldown = timedelta(minutes=15)
        self.optimization_check_interval = 3600  # 1 hour
        self._shutdown = False
        
        # Default thresholds
        self._initialize_default_thresholds()
    
    async def initialize(self):
        """Initialize the monitoring service"""
        try:
            logger.info("Initializing Agent Monitoring Service...")
            
            # Load existing baselines and profiles
            await self._load_performance_baselines()
            await self._load_performance_profiles()
            await self._load_active_alerts()
            
            # Start monitoring loops
            asyncio.create_task(self._metrics_collection_loop())
            asyncio.create_task(self._performance_analysis_loop())
            asyncio.create_task(self._alerting_loop())
            asyncio.create_task(self._optimization_loop())
            asyncio.create_task(self._baseline_update_loop())
            
            logger.info("Agent Monitoring Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Agent Monitoring Service: {e}")
            raise
    
    async def record_metric(
        self,
        agent_id: str,
        metric_name: str,
        value: float,
        metric_type: MetricType = MetricType.PERFORMANCE,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a metric for an agent"""
        try:
            # Ensure metric storage exists
            if metric_name not in self.agent_metrics[agent_id]:
                self.agent_metrics[agent_id][metric_name] = TimeSeriesMetric(
                    metric_name=metric_name,
                    metric_type=metric_type
                )
            
            # Add data point
            self.agent_metrics[agent_id][metric_name].add_point(value, metadata)
            
            # Check for alerts
            await self._check_metric_alerts(agent_id, metric_name, value)
            
            # Update performance profile
            await self._update_performance_profile(agent_id)
            
            logger.debug(f"Recorded metric {metric_name}={value} for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to record metric {metric_name} for agent {agent_id}: {e}")
    
    async def get_agent_performance(self, agent_id: str) -> Optional[AgentPerformanceProfile]:
        """Get comprehensive performance profile for an agent"""
        try:
            # Update real-time metrics
            await self._collect_agent_metrics(agent_id)
            
            # Return cached profile
            return self.performance_profiles.get(agent_id)
            
        except Exception as e:
            logger.error(f"Failed to get performance profile for agent {agent_id}: {e}")
            return None
    
    async def get_metric_history(
        self,
        agent_id: str,
        metric_name: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get metric history for an agent"""
        try:
            if agent_id not in self.agent_metrics or metric_name not in self.agent_metrics[agent_id]:
                return []
            
            metric = self.agent_metrics[agent_id][metric_name]
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            return [
                {
                    "timestamp": point.timestamp.isoformat(),
                    "value": point.value,
                    "metadata": point.metadata
                }
                for point in metric.data_points
                if point.timestamp >= cutoff
            ]
            
        except Exception as e:
            logger.error(f"Failed to get metric history for {agent_id}.{metric_name}: {e}")
            return []
    
    async def get_performance_analytics(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed performance analytics for an agent"""
        try:
            profile = await self.get_agent_performance(agent_id)
            if not profile:
                return {}
            
            # Get metric trends
            trends = {}
            for metric_name, metric in self.agent_metrics.get(agent_id, {}).items():
                trends[metric_name] = {
                    "current": metric.data_points[-1].value if metric.data_points else 0,
                    "average_1h": metric.get_average(1),
                    "average_24h": metric.get_average(24),
                    "trend": metric.get_trend(4)  # 4-hour trend
                }
            
            # Get active alerts
            agent_alerts = [
                alert.dict() for alert in self.active_alerts.values()
                if alert.agent_id == agent_id and not alert.resolved
            ]
            
            # Get optimization recommendations
            recommendations = [
                rec.dict() for rec in self.optimization_recommendations.get(agent_id, [])
                if rec.status == "pending"
            ]
            
            # Calculate performance scores
            performance_scores = await self._calculate_performance_scores(agent_id)
            
            return {
                "agent_id": agent_id,
                "profile": profile.dict(),
                "metric_trends": trends,
                "performance_scores": performance_scores,
                "active_alerts": agent_alerts,
                "optimization_recommendations": recommendations,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance analytics for agent {agent_id}: {e}")
            return {}
    
    async def generate_optimization_recommendations(self, agent_id: str) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations for an agent"""
        try:
            logger.info(f"Generating optimization recommendations for agent {agent_id}")
            
            profile = await self.get_agent_performance(agent_id)
            if not profile:
                return []
            
            recommendations = []
            
            # Performance optimization
            perf_recs = await self._generate_performance_recommendations(agent_id, profile)
            recommendations.extend(perf_recs)
            
            # Resource optimization
            resource_recs = await self._generate_resource_recommendations(agent_id, profile)
            recommendations.extend(resource_recs)
            
            # Collaboration optimization
            collab_recs = await self._generate_collaboration_recommendations(agent_id, profile)
            recommendations.extend(collab_recs)
            
            # Learning optimization
            learning_recs = await self._generate_learning_recommendations(agent_id, profile)
            recommendations.extend(learning_recs)
            
            # Store recommendations
            self.optimization_recommendations[agent_id] = recommendations
            
            # Save to database
            for rec in recommendations:
                await self._save_recommendation_to_database(rec)
            
            logger.info(f"Generated {len(recommendations)} optimization recommendations for agent {agent_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate optimization recommendations for agent {agent_id}: {e}")
            return []
    
    async def implement_optimization(
        self,
        agent_id: str,
        recommendation_id: str,
        auto_implement: bool = False
    ) -> bool:
        """Implement an optimization recommendation"""
        try:
            # Find recommendation
            recommendation = None
            for rec in self.optimization_recommendations.get(agent_id, []):
                if rec.recommendation_id == recommendation_id:
                    recommendation = rec
                    break
            
            if not recommendation:
                raise HTTPException(status_code=404, detail="Recommendation not found")
            
            if recommendation.status != "pending":
                raise HTTPException(status_code=400, detail="Recommendation already processed")
            
            logger.info(f"Implementing optimization {recommendation_id} for agent {agent_id}")
            
            # Apply optimization based on category
            success = False
            if recommendation.category == OptimizationCategory.PERFORMANCE:
                success = await self._implement_performance_optimization(agent_id, recommendation)
            elif recommendation.category == OptimizationCategory.RESOURCE:
                success = await self._implement_resource_optimization(agent_id, recommendation)
            elif recommendation.category == OptimizationCategory.COLLABORATION:
                success = await self._implement_collaboration_optimization(agent_id, recommendation)
            elif recommendation.category == OptimizationCategory.LEARNING:
                success = await self._implement_learning_optimization(agent_id, recommendation)
            
            # Update recommendation status
            recommendation.status = "implemented" if success else "failed"
            
            # Record implementation
            self.optimization_history.append({
                "agent_id": agent_id,
                "recommendation_id": recommendation_id,
                "category": recommendation.category,
                "success": success,
                "implemented_at": datetime.now(timezone.utc).isoformat(),
                "auto_implemented": auto_implement
            })
            
            # Update database
            await self._update_recommendation_in_database(recommendation)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to implement optimization {recommendation_id} for agent {agent_id}: {e}")
            return False
    
    async def set_alert_threshold(
        self,
        agent_id: str,
        metric_name: str,
        threshold_type: str,  # "min", "max", "rate"
        threshold_value: float
    ):
        """Set custom alert threshold for an agent"""
        try:
            if agent_id not in self.alert_thresholds:
                self.alert_thresholds[agent_id] = {}
            
            if metric_name not in self.alert_thresholds[agent_id]:
                self.alert_thresholds[agent_id][metric_name] = {}
            
            self.alert_thresholds[agent_id][metric_name][threshold_type] = threshold_value
            
            logger.info(f"Set alert threshold for {agent_id}.{metric_name}.{threshold_type} = {threshold_value}")
            
        except Exception as e:
            logger.error(f"Failed to set alert threshold: {e}")
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge an alert"""
        try:
            if alert_id not in self.active_alerts:
                return False
            
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.metadata["acknowledged_by"] = acknowledged_by
            alert.metadata["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update database
            await self._update_alert_in_database(alert)
            
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """Resolve an alert"""
        try:
            if alert_id not in self.active_alerts:
                return False
            
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.metadata["resolved_by"] = resolved_by
            alert.metadata["resolved_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update database
            await self._update_alert_in_database(alert)
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        try:
            lifecycle_service = await get_lifecycle_service()
            task_service = await get_task_distribution_service()
            
            # Get all agents
            all_agents = await lifecycle_service.list_agents()
            
            # Calculate health metrics
            total_agents = len(all_agents)
            healthy_agents = sum(1 for agent in all_agents if agent.health_score > 0.8)
            warning_agents = sum(1 for agent in all_agents if 0.5 < agent.health_score <= 0.8)
            critical_agents = sum(1 for agent in all_agents if agent.health_score <= 0.5)
            
            # Alert statistics
            total_alerts = len(self.active_alerts)
            critical_alerts = sum(1 for alert in self.active_alerts.values() if alert.severity == AlertSeverity.CRITICAL)
            unacknowledged_alerts = sum(1 for alert in self.active_alerts.values() if not alert.acknowledged)
            
            # Performance statistics
            avg_performance_score = 0.0
            if self.performance_profiles:
                avg_performance_score = statistics.mean(
                    profile.performance_score for profile in self.performance_profiles.values()
                )
            
            # System load
            system_status = await task_service.get_system_status()
            
            return {
                "overall_health": "healthy" if critical_agents == 0 and critical_alerts == 0 else 
                                "warning" if warning_agents > 0 or unacknowledged_alerts > 0 else "critical",
                "agent_health": {
                    "total": total_agents,
                    "healthy": healthy_agents,
                    "warning": warning_agents,
                    "critical": critical_agents,
                    "health_percentage": (healthy_agents / total_agents * 100) if total_agents > 0 else 0
                },
                "alert_status": {
                    "total_active": total_alerts,
                    "critical": critical_alerts,
                    "unacknowledged": unacknowledged_alerts
                },
                "performance_metrics": {
                    "average_performance_score": avg_performance_score,
                    "total_recommendations": sum(len(recs) for recs in self.optimization_recommendations.values()),
                    "implemented_optimizations": len([h for h in self.optimization_history if h["success"]])
                },
                "system_load": system_status.get("agent_statistics", {}),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {"error": str(e)}
    
    # Background monitoring loops
    
    async def _metrics_collection_loop(self):
        """Main metrics collection loop"""
        while not self._shutdown:
            try:
                lifecycle_service = await get_lifecycle_service()
                active_agents = await lifecycle_service.list_agents(
                    status_filter=[AgentStatus.IDLE, AgentStatus.BUSY, AgentStatus.EXECUTING]
                )
                
                # Collect metrics for each active agent
                for agent in active_agents:
                    await self._collect_agent_metrics(agent.agent_id)
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _performance_analysis_loop(self):
        """Performance analysis and profiling loop"""
        while not self._shutdown:
            try:
                # Update performance profiles for all monitored agents
                for agent_id in self.agent_metrics.keys():
                    await self._update_performance_profile(agent_id)
                
                await asyncio.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in performance analysis loop: {e}")
                await asyncio.sleep(300)
    
    async def _alerting_loop(self):
        """Alerting and notification loop"""
        while not self._shutdown:
            try:
                # Check for alert conditions
                for agent_id, metrics in self.agent_metrics.items():
                    for metric_name, metric in metrics.items():
                        if metric.data_points:
                            latest_value = metric.data_points[-1].value
                            await self._check_metric_alerts(agent_id, metric_name, latest_value)
                
                # Check for stale alerts to auto-resolve
                await self._check_stale_alerts()
                
                await asyncio.sleep(60)  # Every minute
                
            except Exception as e:
                logger.error(f"Error in alerting loop: {e}")
                await asyncio.sleep(60)
    
    async def _optimization_loop(self):
        """Optimization recommendation loop"""
        while not self._shutdown:
            try:
                # Generate optimization recommendations for agents that need them
                for agent_id in self.performance_profiles.keys():
                    profile = self.performance_profiles[agent_id]
                    
                    # Check if optimization is needed
                    if (profile.performance_score < 0.7 or 
                        profile.reliability_score < 0.8 or 
                        len(profile.bottlenecks) > 0):
                        
                        # Check if we have recent recommendations
                        recent_recs = [
                            rec for rec in self.optimization_recommendations.get(agent_id, [])
                            if (datetime.now(timezone.utc) - rec.created_at).total_seconds() < 3600
                        ]
                        
                        if not recent_recs:
                            await self.generate_optimization_recommendations(agent_id)
                
                await asyncio.sleep(self.optimization_check_interval)
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(self.optimization_check_interval)
    
    async def _baseline_update_loop(self):
        """Baseline learning and update loop"""
        while not self._shutdown:
            try:
                # Update performance baselines
                for agent_id in self.agent_metrics.keys():
                    await self._update_performance_baseline(agent_id)
                
                await asyncio.sleep(3600)  # Every hour
                
            except Exception as e:
                logger.error(f"Error in baseline update loop: {e}")
                await asyncio.sleep(3600)
    
    # Helper methods
    
    async def _collect_agent_metrics(self, agent_id: str):
        """Collect real-time metrics for an agent"""
        try:
            lifecycle_service = await get_lifecycle_service()
            task_service = await get_task_distribution_service()
            
            # Get agent health
            agent_health = await lifecycle_service.get_agent_health(agent_id)
            if agent_health.get("status") != "error":
                await self.record_metric(agent_id, "health_score", agent_health.get("health_score", 0.0))
                await self.record_metric(agent_id, "uptime_percentage", agent_health.get("uptime", {}).get("uptime_percentage", 0.0))
            
            # Get workload metrics
            workload = await task_service.get_agent_workload(agent_id)
            if workload:
                await self.record_metric(agent_id, "load_percentage", workload.get("load_percentage", 0.0))
                await self.record_metric(agent_id, "task_count", len(workload.get("current_tasks", [])))
            
            # Additional metrics would be collected here...
            
        except Exception as e:
            logger.error(f"Failed to collect metrics for agent {agent_id}: {e}")
    
    # Additional helper methods continue here...
    
    def _initialize_default_thresholds(self):
        """Initialize default alert thresholds"""
        self.alert_thresholds["default"] = {
            "health_score": {"min": 0.3},
            "load_percentage": {"max": 90.0},
            "error_rate": {"max": 0.1},
            "response_time": {"max": 5000.0}  # milliseconds
        }
    
    # Additional methods would be implemented here...


# Global service instance
_monitoring_service: Optional[AgentMonitoringService] = None


async def get_monitoring_service() -> AgentMonitoringService:
    """Get the global monitoring service instance"""
    global _monitoring_service
    
    if _monitoring_service is None:
        _monitoring_service = AgentMonitoringService()
        await _monitoring_service.initialize()
    
    return _monitoring_service


@asynccontextmanager
async def monitoring_service_context():
    """Context manager for monitoring service"""
    service = await get_monitoring_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass