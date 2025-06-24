"""
Phase 9: Agent Lifecycle Management Service
Manages autonomous agent creation, deployment, monitoring, and retirement
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import json
import logging
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.agent_orchestration_models import (
    AutonomousAgent, AgentStatus, AgentType, AgentCapability, CoordinationMode,
    AgentCapabilityProfile, AgentResource, AgentMetrics, CreateAgentRequest,
    TaskRequirement, ResourcePool, AgentOptimization
)
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class AgentHealthStatus(str, Enum):
    """Agent health status classifications"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNRESPONSIVE = "unresponsive"


class LifecycleEvent(BaseModel):
    """Agent lifecycle event"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    event_type: str
    event_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "lifecycle_service"
    severity: str = "info"


class AgentDeploymentConfig(BaseModel):
    """Agent deployment configuration"""
    environment: str = "production"
    resource_constraints: Dict[str, Any] = Field(default_factory=dict)
    scaling_policy: Dict[str, Any] = Field(default_factory=dict)
    monitoring_config: Dict[str, Any] = Field(default_factory=dict)
    backup_config: Dict[str, Any] = Field(default_factory=dict)
    recovery_policy: Dict[str, Any] = Field(default_factory=dict)


class AgentLifecycleService:
    """
    Manages the complete lifecycle of autonomous agents from creation to retirement
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.active_agents: Dict[str, AutonomousAgent] = {}
        self.agent_monitors: Dict[str, asyncio.Task] = {}
        self.lifecycle_events: List[LifecycleEvent] = []
        self.resource_pools: Dict[str, ResourcePool] = {}
        self.health_check_interval = 30  # seconds
        self.performance_evaluation_interval = 300  # 5 minutes
        self.optimization_check_interval = 3600  # 1 hour
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the lifecycle service"""
        try:
            logger.info("Initializing Agent Lifecycle Service...")
            
            # Load existing agents from database
            await self._load_existing_agents()
            
            # Load resource pools
            await self._load_resource_pools()
            
            # Start background tasks
            asyncio.create_task(self._health_monitor_loop())
            asyncio.create_task(self._performance_monitor_loop())
            asyncio.create_task(self._optimization_monitor_loop())
            
            logger.info(f"Agent Lifecycle Service initialized with {len(self.active_agents)} active agents")
            
        except Exception as e:
            logger.error(f"Failed to initialize Agent Lifecycle Service: {e}")
            raise
    
    async def create_agent(
        self, 
        request: CreateAgentRequest,
        deployment_config: Optional[AgentDeploymentConfig] = None
    ) -> AutonomousAgent:
        """Create and deploy a new autonomous agent"""
        try:
            logger.info(f"Creating new agent: {request.name}")
            
            # Validate resource requirements
            await self._validate_resource_requirements(request.resource_requirements)
            
            # Create agent instance
            agent = AutonomousAgent(
                name=request.name,
                agent_type=request.agent_type,
                primary_capability=request.primary_capability,
                capabilities=self._create_capability_profiles(request.capabilities),
                resources=self._allocate_resources(request.resource_requirements),
                coordination_mode=request.coordination_mode,
                supervisor_agent_id=request.supervisor_agent_id,
                configuration=request.configuration or {}
            )
            
            # Deploy agent
            await self._deploy_agent(agent, deployment_config or AgentDeploymentConfig())
            
            # Save to database
            await self._save_agent_to_database(agent)
            
            # Add to active agents
            self.active_agents[agent.agent_id] = agent
            
            # Start monitoring
            await self._start_agent_monitoring(agent.agent_id)
            
            # Log lifecycle event
            await self._log_lifecycle_event(
                agent.agent_id,
                "agent_created",
                {"agent_type": agent.agent_type, "primary_capability": agent.primary_capability}
            )
            
            logger.info(f"Successfully created and deployed agent: {agent.agent_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent {request.name}: {e}")
            raise HTTPException(status_code=500, detail=f"Agent creation failed: {str(e)}")
    
    async def deploy_agent(self, agent_id: str, config: AgentDeploymentConfig) -> bool:
        """Deploy an existing agent with specific configuration"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            # Update agent status
            agent.status = AgentStatus.INITIALIZING
            
            # Deploy with configuration
            success = await self._deploy_agent(agent, config)
            
            if success:
                agent.status = AgentStatus.IDLE
                await self._update_agent_in_database(agent)
                
                await self._log_lifecycle_event(
                    agent_id,
                    "agent_deployed",
                    {"environment": config.environment}
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to deploy agent {agent_id}: {e}")
            return False
    
    async def start_agent(self, agent_id: str) -> bool:
        """Start an idle agent"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return False
            
            if agent.status not in [AgentStatus.IDLE, AgentStatus.OFFLINE]:
                logger.warning(f"Cannot start agent {agent_id} in status {agent.status}")
                return False
            
            # Perform health check
            health_status = await self._perform_health_check(agent_id)
            if health_status != AgentHealthStatus.HEALTHY:
                logger.warning(f"Agent {agent_id} failed health check: {health_status}")
                return False
            
            # Update status
            agent.status = AgentStatus.IDLE
            agent.last_active = datetime.now(timezone.utc)
            
            # Update database
            await self._update_agent_in_database(agent)
            
            # Start monitoring if not already active
            if agent_id not in self.agent_monitors:
                await self._start_agent_monitoring(agent_id)
            
            await self._log_lifecycle_event(agent_id, "agent_started", {})
            
            logger.info(f"Successfully started agent: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {e}")
            return False
    
    async def stop_agent(self, agent_id: str, graceful: bool = True) -> bool:
        """Stop a running agent"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return False
            
            if graceful:
                # Allow agent to complete current tasks
                agent.status = AgentStatus.MAINTENANCE
                await self._update_agent_in_database(agent)
                
                # Wait for tasks to complete (with timeout)
                timeout = 300  # 5 minutes
                start_time = datetime.now(timezone.utc)
                
                while (datetime.now(timezone.utc) - start_time).seconds < timeout:
                    if await self._agent_has_no_active_tasks(agent_id):
                        break
                    await asyncio.sleep(10)
            
            # Stop agent
            agent.status = AgentStatus.OFFLINE
            await self._update_agent_in_database(agent)
            
            # Stop monitoring
            await self._stop_agent_monitoring(agent_id)
            
            await self._log_lifecycle_event(
                agent_id,
                "agent_stopped",
                {"graceful": graceful}
            )
            
            logger.info(f"Successfully stopped agent: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop agent {agent_id}: {e}")
            return False
    
    async def restart_agent(self, agent_id: str) -> bool:
        """Restart an agent"""
        try:
            logger.info(f"Restarting agent: {agent_id}")
            
            # Stop agent
            await self.stop_agent(agent_id, graceful=True)
            
            # Wait a moment
            await asyncio.sleep(5)
            
            # Start agent
            return await self.start_agent(agent_id)
            
        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")
            return False
    
    async def retire_agent(self, agent_id: str, preserve_data: bool = True) -> bool:
        """Retire an agent permanently"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return False
            
            logger.info(f"Retiring agent: {agent_id}")
            
            # Stop agent gracefully
            await self.stop_agent(agent_id, graceful=True)
            
            # Update status
            agent.status = AgentStatus.TERMINATED
            await self._update_agent_in_database(agent)
            
            # Clean up resources
            await self._deallocate_agent_resources(agent_id)
            
            # Remove from active agents
            if agent_id in self.active_agents:
                del self.active_agents[agent_id]
            
            # Archive or delete data
            if preserve_data:
                await self._archive_agent_data(agent_id)
            else:
                await self._delete_agent_data(agent_id)
            
            await self._log_lifecycle_event(
                agent_id,
                "agent_retired",
                {"preserve_data": preserve_data}
            )
            
            logger.info(f"Successfully retired agent: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retire agent {agent_id}: {e}")
            return False
    
    async def get_agent(self, agent_id: str) -> Optional[AutonomousAgent]:
        """Get agent by ID"""
        # First check active agents cache
        if agent_id in self.active_agents:
            return self.active_agents[agent_id]
        
        # Load from database
        try:
            result = self.supabase.table("autonomous_agents").select("*").eq("agent_id", agent_id).execute()
            
            if result.data:
                agent_data = result.data[0]
                agent = self._parse_agent_from_db(agent_data)
                
                # Add to cache if active
                if agent.status not in [AgentStatus.TERMINATED, AgentStatus.OFFLINE]:
                    self.active_agents[agent_id] = agent
                
                return agent
                
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
        
        return None
    
    async def list_agents(
        self,
        status_filter: Optional[List[AgentStatus]] = None,
        agent_type_filter: Optional[List[AgentType]] = None,
        capability_filter: Optional[List[AgentCapability]] = None
    ) -> List[AutonomousAgent]:
        """List agents with optional filters"""
        try:
            query = self.supabase.table("autonomous_agents").select("*")
            
            if status_filter:
                query = query.in_("status", [s.value for s in status_filter])
            
            if agent_type_filter:
                query = query.in_("agent_type", [t.value for t in agent_type_filter])
            
            if capability_filter:
                # This would require JSONB query for capabilities array
                pass
            
            result = query.execute()
            
            agents = []
            for agent_data in result.data:
                agent = self._parse_agent_from_db(agent_data)
                agents.append(agent)
            
            return agents
            
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []
    
    async def get_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive agent health information"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return {"status": "not_found"}
            
            # Perform real-time health check
            health_status = await self._perform_health_check(agent_id)
            
            # Get performance metrics
            metrics = await self._get_agent_performance_metrics(agent_id)
            
            # Get resource usage
            resource_usage = await self._get_agent_resource_usage(agent_id)
            
            return {
                "agent_id": agent_id,
                "status": agent.status,
                "health_status": health_status,
                "health_score": agent.health_score,
                "last_health_check": agent.last_health_check.isoformat(),
                "last_active": agent.last_active.isoformat(),
                "uptime": self._calculate_uptime(agent),
                "performance_metrics": metrics,
                "resource_usage": resource_usage,
                "current_tasks": await self._get_agent_current_tasks(agent_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to get agent health for {agent_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def optimize_agent(self, agent_id: str) -> Optional[AgentOptimization]:
        """Generate optimization recommendations for an agent"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return None
            
            # Analyze current performance
            metrics = await self._get_agent_performance_metrics(agent_id)
            
            # Identify bottlenecks
            bottlenecks = await self._identify_performance_bottlenecks(agent_id, metrics)
            
            # Generate recommendations
            recommendations = await self._generate_optimization_recommendations(agent_id, bottlenecks, metrics)
            
            # Create optimization record
            optimization = AgentOptimization(
                agent_id=agent_id,
                optimization_type="performance",
                current_metrics=metrics,
                bottlenecks_identified=bottlenecks,
                optimization_opportunities=recommendations["opportunities"],
                recommended_changes=recommendations["changes"],
                expected_improvements=recommendations["improvements"],
                implementation_complexity=recommendations["complexity"],
                confidence_score=recommendations["confidence"],
                risk_assessment=recommendations["risks"]
            )
            
            # Save to database
            await self._save_optimization_to_database(optimization)
            
            return optimization
            
        except Exception as e:
            logger.error(f"Failed to optimize agent {agent_id}: {e}")
            return None
    
    async def shutdown(self):
        """Gracefully shutdown the lifecycle service"""
        try:
            logger.info("Shutting down Agent Lifecycle Service...")
            self._shutdown = True
            
            # Stop all monitoring tasks
            for task in self.agent_monitors.values():
                task.cancel()
            
            # Wait for tasks to complete
            if self.agent_monitors:
                await asyncio.gather(*self.agent_monitors.values(), return_exceptions=True)
            
            # Stop all active agents gracefully
            for agent_id in list(self.active_agents.keys()):
                await self.stop_agent(agent_id, graceful=True)
            
            logger.info("Agent Lifecycle Service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    # Private methods
    
    async def _load_existing_agents(self):
        """Load existing agents from database"""
        try:
            result = self.supabase.table("autonomous_agents").select("*").not_.eq("status", "terminated").execute()
            
            for agent_data in result.data:
                agent = self._parse_agent_from_db(agent_data)
                self.active_agents[agent.agent_id] = agent
                
                # Start monitoring for active agents
                if agent.status in [AgentStatus.IDLE, AgentStatus.BUSY, AgentStatus.EXECUTING]:
                    await self._start_agent_monitoring(agent.agent_id)
                    
        except Exception as e:
            logger.error(f"Failed to load existing agents: {e}")
    
    async def _load_resource_pools(self):
        """Load resource pools from database"""
        try:
            result = self.supabase.table("resource_pools").select("*").execute()
            
            for pool_data in result.data:
                pool = ResourcePool(**pool_data)
                self.resource_pools[pool.pool_id] = pool
                
        except Exception as e:
            logger.error(f"Failed to load resource pools: {e}")
    
    def _parse_agent_from_db(self, agent_data: Dict[str, Any]) -> AutonomousAgent:
        """Parse agent data from database"""
        # Convert JSON fields back to objects
        capabilities = []
        if agent_data.get("capabilities"):
            for cap_data in agent_data["capabilities"]:
                capabilities.append(AgentCapabilityProfile(**cap_data))
        
        resources = AgentResource(**agent_data.get("resources", {}))
        metrics = AgentMetrics(**agent_data.get("metrics", {}))
        
        return AutonomousAgent(
            agent_id=agent_data["agent_id"],
            name=agent_data["name"],
            agent_type=AgentType(agent_data["agent_type"]),
            status=AgentStatus(agent_data["status"]),
            capabilities=capabilities,
            primary_capability=AgentCapability(agent_data["primary_capability"]),
            resources=resources,
            metrics=metrics,
            created_at=datetime.fromisoformat(agent_data["created_at"].replace('Z', '+00:00')),
            last_active=datetime.fromisoformat(agent_data["last_active"].replace('Z', '+00:00')),
            health_score=agent_data.get("health_score", 1.0),
            coordination_mode=CoordinationMode(agent_data.get("coordination_mode", "peer_to_peer")),
            configuration=agent_data.get("configuration", {}),
            supervisor_agent_id=agent_data.get("supervisor_agent_id")
        )
    
    async def _save_agent_to_database(self, agent: AutonomousAgent):
        """Save agent to database"""
        try:
            agent_data = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "agent_type": agent.agent_type.value,
                "status": agent.status.value,
                "primary_capability": agent.primary_capability.value,
                "capabilities": [cap.dict() for cap in agent.capabilities],
                "resources": agent.resources.dict(),
                "metrics": agent.metrics.dict(),
                "coordination_mode": agent.coordination_mode.value,
                "configuration": agent.configuration,
                "supervisor_agent_id": agent.supervisor_agent_id,
                "health_score": float(agent.health_score),
                "created_at": agent.created_at.isoformat(),
                "last_active": agent.last_active.isoformat(),
                "last_health_check": agent.last_health_check.isoformat()
            }
            
            result = self.supabase.table("autonomous_agents").insert(agent_data).execute()
            
            if not result.data:
                raise Exception("Failed to insert agent into database")
                
        except Exception as e:
            logger.error(f"Failed to save agent {agent.agent_id} to database: {e}")
            raise
    
    async def _update_agent_in_database(self, agent: AutonomousAgent):
        """Update agent in database"""
        try:
            agent_data = {
                "status": agent.status.value,
                "metrics": agent.metrics.dict(),
                "health_score": float(agent.health_score),
                "last_active": agent.last_active.isoformat(),
                "last_health_check": agent.last_health_check.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table("autonomous_agents").update(agent_data).eq("agent_id", agent.agent_id).execute()
            
            if not result.data:
                logger.warning(f"No rows updated for agent {agent.agent_id}")
                
        except Exception as e:
            logger.error(f"Failed to update agent {agent.agent_id} in database: {e}")
    
    async def _validate_resource_requirements(self, requirements: Dict[str, Any]):
        """Validate that resource requirements can be satisfied"""
        # Implementation would check against available resource pools
        pass
    
    def _create_capability_profiles(self, capabilities: List[AgentCapability]) -> List[AgentCapabilityProfile]:
        """Create capability profiles for agent"""
        profiles = []
        for capability in capabilities:
            profile = AgentCapabilityProfile(
                capability=capability,
                proficiency_level=0.5,  # Default starting proficiency
                experience_score=0.0,
                success_rate=0.0,
                average_execution_time=0.0
            )
            profiles.append(profile)
        return profiles
    
    def _allocate_resources(self, requirements: Dict[str, Any]) -> AgentResource:
        """Allocate resources for agent"""
        return AgentResource(
            cpu_allocation=requirements.get("cpu", 0.1),
            memory_allocation=requirements.get("memory", 1.0),
            storage_allocation=requirements.get("storage", 1.0),
            cost_per_hour=Decimal(str(requirements.get("cost_per_hour", 0.0)))
        )
    
    async def _deploy_agent(self, agent: AutonomousAgent, config: AgentDeploymentConfig) -> bool:
        """Deploy agent with configuration"""
        # Implementation would handle actual deployment
        # For now, simulate deployment
        await asyncio.sleep(0.1)
        return True
    
    async def _start_agent_monitoring(self, agent_id: str):
        """Start monitoring task for agent"""
        if agent_id not in self.agent_monitors:
            task = asyncio.create_task(self._monitor_agent(agent_id))
            self.agent_monitors[agent_id] = task
    
    async def _stop_agent_monitoring(self, agent_id: str):
        """Stop monitoring task for agent"""
        if agent_id in self.agent_monitors:
            task = self.agent_monitors[agent_id]
            task.cancel()
            del self.agent_monitors[agent_id]
    
    async def _monitor_agent(self, agent_id: str):
        """Monitor individual agent"""
        try:
            while not self._shutdown:
                agent = await self.get_agent(agent_id)
                if not agent or agent.status == AgentStatus.TERMINATED:
                    break
                
                # Perform health check
                health_status = await self._perform_health_check(agent_id)
                
                # Update health score based on status
                if health_status == AgentHealthStatus.HEALTHY:
                    agent.health_score = min(1.0, agent.health_score + 0.01)
                elif health_status == AgentHealthStatus.WARNING:
                    agent.health_score = max(0.0, agent.health_score - 0.05)
                elif health_status == AgentHealthStatus.CRITICAL:
                    agent.health_score = max(0.0, agent.health_score - 0.1)
                else:  # UNRESPONSIVE
                    agent.health_score = 0.0
                
                agent.last_health_check = datetime.now(timezone.utc)
                
                # Update database
                await self._update_agent_in_database(agent)
                
                # Check if intervention is needed
                if agent.health_score < 0.3:
                    await self._handle_unhealthy_agent(agent_id, health_status)
                
                await asyncio.sleep(self.health_check_interval)
                
        except asyncio.CancelledError:
            logger.info(f"Monitoring cancelled for agent {agent_id}")
        except Exception as e:
            logger.error(f"Error monitoring agent {agent_id}: {e}")
    
    async def _perform_health_check(self, agent_id: str) -> AgentHealthStatus:
        """Perform health check on agent"""
        # Implementation would check actual agent health
        # For now, simulate based on random factors
        import random
        
        agent = await self.get_agent(agent_id)
        if not agent:
            return AgentHealthStatus.UNRESPONSIVE
        
        # Simulate health based on various factors
        if agent.status == AgentStatus.ERROR:
            return AgentHealthStatus.CRITICAL
        elif agent.status == AgentStatus.OFFLINE:
            return AgentHealthStatus.UNRESPONSIVE
        elif random.random() < 0.9:  # 90% chance of being healthy
            return AgentHealthStatus.HEALTHY
        elif random.random() < 0.7:  # 70% chance of warning vs critical
            return AgentHealthStatus.WARNING
        else:
            return AgentHealthStatus.CRITICAL
    
    async def _handle_unhealthy_agent(self, agent_id: str, health_status: AgentHealthStatus):
        """Handle unhealthy agent"""
        logger.warning(f"Agent {agent_id} is unhealthy: {health_status}")
        
        if health_status == AgentHealthStatus.UNRESPONSIVE:
            # Try to restart agent
            await self.restart_agent(agent_id)
        elif health_status == AgentHealthStatus.CRITICAL:
            # Generate optimization recommendations
            await self.optimize_agent(agent_id)
    
    async def _health_monitor_loop(self):
        """Main health monitoring loop"""
        while not self._shutdown:
            try:
                # This is handled by individual agent monitors
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _performance_monitor_loop(self):
        """Performance monitoring loop"""
        while not self._shutdown:
            try:
                for agent_id in list(self.active_agents.keys()):
                    await self._update_agent_performance_metrics(agent_id)
                
                await asyncio.sleep(self.performance_evaluation_interval)
            except Exception as e:
                logger.error(f"Error in performance monitor loop: {e}")
                await asyncio.sleep(self.performance_evaluation_interval)
    
    async def _optimization_monitor_loop(self):
        """Optimization monitoring loop"""
        while not self._shutdown:
            try:
                for agent_id in list(self.active_agents.keys()):
                    agent = self.active_agents[agent_id]
                    
                    # Check if optimization is needed
                    if agent.health_score < 0.7 or agent.metrics.efficiency_score < 0.6:
                        await self.optimize_agent(agent_id)
                
                await asyncio.sleep(self.optimization_check_interval)
            except Exception as e:
                logger.error(f"Error in optimization monitor loop: {e}")
                await asyncio.sleep(self.optimization_check_interval)
    
    async def _log_lifecycle_event(self, agent_id: str, event_type: str, event_data: Dict[str, Any]):
        """Log lifecycle event"""
        event = LifecycleEvent(
            agent_id=agent_id,
            event_type=event_type,
            event_data=event_data
        )
        
        self.lifecycle_events.append(event)
        
        # Keep only last 1000 events in memory
        if len(self.lifecycle_events) > 1000:
            self.lifecycle_events = self.lifecycle_events[-1000:]
        
        # Also log to database or external system
        logger.info(f"Lifecycle event: {event_type} for agent {agent_id}")
    
    # Additional helper methods would be implemented here...
    
    async def _agent_has_no_active_tasks(self, agent_id: str) -> bool:
        """Check if agent has no active tasks"""
        # Implementation would check task assignments
        return True
    
    async def _deallocate_agent_resources(self, agent_id: str):
        """Deallocate resources for retired agent"""
        # Implementation would return resources to pools
        pass
    
    async def _archive_agent_data(self, agent_id: str):
        """Archive agent data"""
        # Implementation would move data to archive tables
        pass
    
    async def _delete_agent_data(self, agent_id: str):
        """Delete agent data"""
        # Implementation would delete agent data
        pass
    
    async def _get_agent_performance_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get agent performance metrics"""
        # Implementation would collect real metrics
        return {}
    
    async def _update_agent_performance_metrics(self, agent_id: str):
        """Update agent performance metrics"""
        # Implementation would update metrics
        pass
    
    async def _get_agent_resource_usage(self, agent_id: str) -> Dict[str, Any]:
        """Get agent resource usage"""
        # Implementation would get resource usage
        return {}
    
    async def _get_agent_current_tasks(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get agent's current tasks"""
        # Implementation would get current tasks
        return []
    
    async def _identify_performance_bottlenecks(self, agent_id: str, metrics: Dict[str, Any]) -> List[str]:
        """Identify performance bottlenecks"""
        # Implementation would analyze metrics and identify bottlenecks
        return []
    
    async def _generate_optimization_recommendations(
        self, 
        agent_id: str, 
        bottlenecks: List[str], 
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate optimization recommendations"""
        # Implementation would generate recommendations
        return {
            "opportunities": [],
            "changes": {},
            "improvements": {},
            "complexity": "medium",
            "confidence": 0.8,
            "risks": {}
        }
    
    async def _save_optimization_to_database(self, optimization: AgentOptimization):
        """Save optimization to database"""
        try:
            optimization_data = optimization.dict()
            result = self.supabase.table("agent_optimizations").insert(optimization_data).execute()
            
            if not result.data:
                raise Exception("Failed to insert optimization into database")
                
        except Exception as e:
            logger.error(f"Failed to save optimization to database: {e}")
            raise
    
    def _calculate_uptime(self, agent: AutonomousAgent) -> Dict[str, Any]:
        """Calculate agent uptime"""
        now = datetime.now(timezone.utc)
        total_time = (now - agent.created_at).total_seconds()
        
        # This is simplified - real implementation would track downtime
        uptime_percentage = agent.health_score * 100
        
        return {
            "total_seconds": total_time,
            "uptime_percentage": uptime_percentage,
            "last_restart": agent.created_at.isoformat()
        }


# Global service instance
_lifecycle_service: Optional[AgentLifecycleService] = None


async def get_lifecycle_service() -> AgentLifecycleService:
    """Get the global lifecycle service instance"""
    global _lifecycle_service
    
    if _lifecycle_service is None:
        _lifecycle_service = AgentLifecycleService()
        await _lifecycle_service.initialize()
    
    return _lifecycle_service


@asynccontextmanager
async def lifecycle_service_context():
    """Context manager for lifecycle service"""
    service = await get_lifecycle_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass