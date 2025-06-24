"""
Agent Scheduler Service - Phase 5 Implementation
Intelligent agent scheduling and workload distribution for optimal performance
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Literal
from loguru import logger
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict, deque

class SchedulePriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

class TaskType(str, Enum):
    """Types of agent tasks"""
    ANALYSIS = "analysis"
    TRADING = "trading"
    MONITORING = "monitoring"
    OPTIMIZATION = "optimization"
    RESEARCH = "research"

class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentCapability(BaseModel):
    """Agent capability definition"""
    agent_id: str
    supported_tasks: List[TaskType]
    max_concurrent_tasks: int = 3
    performance_score: float = 1.0
    resource_usage: Dict[str, float] = Field(default_factory=dict)  # CPU, memory, etc.
    specializations: List[str] = Field(default_factory=list)
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ScheduledTask(BaseModel):
    """Scheduled task definition"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    priority: SchedulePriority
    agent_id: Optional[str] = None  # Assigned agent
    task_data: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)  # Task IDs this depends on
    estimated_duration_minutes: Optional[int] = None
    max_retries: int = 3
    retry_count: int = 0
    
    # Scheduling metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Status and results
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class WorkloadMetrics(BaseModel):
    """Agent workload metrics"""
    agent_id: str
    current_tasks: int
    completed_tasks_24h: int
    avg_task_duration_minutes: float
    success_rate: float
    resource_utilization: Dict[str, float] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class AgentWorkload:
    """Real-time agent workload tracking"""
    agent_id: str
    active_tasks: List[str] = field(default_factory=list)
    task_history: deque = field(default_factory=lambda: deque(maxlen=100))
    total_task_time: float = 0.0
    total_tasks_completed: int = 0
    current_utilization: float = 0.0
    last_task_completion: Optional[datetime] = None

class AgentSchedulerService:
    """
    Intelligent agent scheduler for optimal workload distribution and performance
    """
    
    def __init__(self):
        self.agent_capabilities: Dict[str, AgentCapability] = {}
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.task_queue: List[ScheduledTask] = []
        self.agent_workloads: Dict[str, AgentWorkload] = {}
        self.completed_tasks: List[ScheduledTask] = []
        
        # Scheduling configuration
        self.max_queue_size = 1000
        self.scheduling_interval_seconds = 10
        self.workload_balance_threshold = 0.7  # 70% utilization before rebalancing
        self.priority_weights = {
            SchedulePriority.CRITICAL: 10,
            SchedulePriority.URGENT: 7,
            SchedulePriority.HIGH: 5,
            SchedulePriority.MEDIUM: 3,
            SchedulePriority.LOW: 1
        }
        
        # Start background scheduler
        self.scheduler_running = True
        self._start_scheduler()
        
        logger.info("AgentSchedulerService initialized with intelligent workload distribution")
    
    def _start_scheduler(self):
        """Start background scheduling task"""
        asyncio.create_task(self._scheduling_loop())
        asyncio.create_task(self._workload_monitoring_loop())
    
    async def _scheduling_loop(self):
        """Main scheduling loop"""
        while self.scheduler_running:
            try:
                await self._process_task_queue()
                await asyncio.sleep(self.scheduling_interval_seconds)
            except Exception as e:
                logger.error(f"Error in scheduling loop: {e}", exc_info=True)
                await asyncio.sleep(self.scheduling_interval_seconds)
    
    async def _workload_monitoring_loop(self):
        """Monitor agent workloads and rebalance if needed"""
        while self.scheduler_running:
            try:
                await self._update_workload_metrics()
                await self._rebalance_workloads()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in workload monitoring: {e}", exc_info=True)
                await asyncio.sleep(30)
    
    async def register_agent(self, agent_capability: AgentCapability):
        """Register an agent with its capabilities"""
        self.agent_capabilities[agent_capability.agent_id] = agent_capability
        
        if agent_capability.agent_id not in self.agent_workloads:
            self.agent_workloads[agent_capability.agent_id] = AgentWorkload(
                agent_id=agent_capability.agent_id
            )
        
        logger.info(f"Registered agent {agent_capability.agent_id} with capabilities: {agent_capability.supported_tasks}")
    
    async def submit_task(self, task: ScheduledTask) -> str:
        """Submit a new task for scheduling"""
        
        if len(self.task_queue) >= self.max_queue_size:
            raise ValueError(f"Task queue is full (max {self.max_queue_size} tasks)")
        
        # Validate task
        if not await self._validate_task(task):
            raise ValueError("Invalid task configuration")
        
        # Add to queue
        self.scheduled_tasks[task.task_id] = task
        self.task_queue.append(task)
        
        # Sort queue by priority
        self.task_queue.sort(key=lambda t: self.priority_weights[t.priority], reverse=True)
        
        logger.info(f"Submitted task {task.task_id} ({task.task_type.value}, priority: {task.priority.value})")
        return task.task_id
    
    async def _validate_task(self, task: ScheduledTask) -> bool:
        """Validate task configuration"""
        
        # Check if any agent can handle this task type
        capable_agents = [
            agent for agent in self.agent_capabilities.values()
            if task.task_type in agent.supported_tasks
        ]
        
        if not capable_agents:
            logger.warning(f"No agents capable of handling task type {task.task_type.value}")
            return False
        
        # Validate dependencies
        for dep_id in task.dependencies:
            if dep_id not in self.scheduled_tasks:
                logger.warning(f"Task {task.task_id} has invalid dependency: {dep_id}")
                return False
        
        return True
    
    async def _process_task_queue(self):
        """Process pending tasks in the queue"""
        
        processed_count = 0
        
        for task in self.task_queue[:]:
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check dependencies
            if not await self._dependencies_satisfied(task):
                continue
            
            # Find best agent for task
            best_agent = await self._find_best_agent(task)
            if not best_agent:
                continue
            
            # Assign task to agent
            await self._assign_task_to_agent(task, best_agent.agent_id)
            processed_count += 1
            
            # Remove from queue
            self.task_queue.remove(task)
        
        if processed_count > 0:
            logger.info(f"Processed {processed_count} tasks in scheduling cycle")
    
    async def _dependencies_satisfied(self, task: ScheduledTask) -> bool:
        """Check if all task dependencies are satisfied"""
        
        for dep_id in task.dependencies:
            dep_task = self.scheduled_tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    async def _find_best_agent(self, task: ScheduledTask) -> Optional[AgentCapability]:
        """Find the best agent for a task using intelligent scoring"""
        
        capable_agents = [
            agent for agent in self.agent_capabilities.values()
            if task.task_type in agent.supported_tasks
        ]
        
        if not capable_agents:
            return None
        
        best_agent = None
        best_score = -1
        
        for agent in capable_agents:
            score = await self._calculate_agent_score(agent, task)
            if score > best_score:
                best_score = score
                best_agent = agent
        
        return best_agent
    
    async def _calculate_agent_score(self, agent: AgentCapability, task: ScheduledTask) -> float:
        """Calculate agent suitability score for a task"""
        
        workload = self.agent_workloads.get(agent.agent_id)
        if not workload:
            return 0.0
        
        # Base score from agent performance
        score = agent.performance_score
        
        # Penalty for high workload
        utilization = len(workload.active_tasks) / agent.max_concurrent_tasks
        if utilization > self.workload_balance_threshold:
            score *= (1.0 - utilization + self.workload_balance_threshold)
        
        # Bonus for specializations
        if hasattr(task.task_data, 'required_specialization'):
            required_spec = task.task_data.get('required_specialization')
            if required_spec in agent.specializations:
                score *= 1.5
        
        # Recent activity bonus
        time_since_active = (datetime.now(timezone.utc) - agent.last_active).total_seconds()
        if time_since_active < 300:  # 5 minutes
            score *= 1.2
        
        # Priority bonus for high-priority tasks
        if task.priority in [SchedulePriority.URGENT, SchedulePriority.CRITICAL]:
            score *= 1.3
        
        return score
    
    async def _assign_task_to_agent(self, task: ScheduledTask, agent_id: str):
        """Assign a task to a specific agent"""
        
        task.agent_id = agent_id
        task.status = TaskStatus.SCHEDULED
        task.scheduled_at = datetime.now(timezone.utc)
        
        # Add to agent workload
        workload = self.agent_workloads[agent_id]
        workload.active_tasks.append(task.task_id)
        
        # Start task execution
        asyncio.create_task(self._execute_task(task))
        
        logger.info(f"Assigned task {task.task_id} to agent {agent_id}")
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            
            logger.info(f"Starting execution of task {task.task_id} on agent {task.agent_id}")
            
            # Simulate task execution (in real implementation, this would call agent services)
            execution_time = task.estimated_duration_minutes or 2  # Default 2 minutes
            await asyncio.sleep(execution_time * 60)  # Convert to seconds for simulation
            
            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.result = {
                "success": True,
                "execution_time_minutes": execution_time,
                "agent_id": task.agent_id
            }
            
            # Update workload
            await self._update_agent_workload_on_completion(task)
            
            # Move to completed tasks
            self.completed_tasks.append(task)
            
            logger.info(f"Completed task {task.task_id} successfully")
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)
            
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now(timezone.utc)
            
            # Handle retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.agent_id = None
                task.scheduled_at = None
                task.started_at = None
                task.completed_at = None
                
                # Add back to queue for retry
                self.task_queue.append(task)
                logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count + 1})")
            else:
                await self._update_agent_workload_on_completion(task)
                logger.error(f"Task {task.task_id} failed permanently after {task.max_retries} retries")
    
    async def _update_agent_workload_on_completion(self, task: ScheduledTask):
        """Update agent workload metrics when task completes"""
        
        if not task.agent_id:
            return
        
        workload = self.agent_workloads.get(task.agent_id)
        if not workload:
            return
        
        # Remove from active tasks
        if task.task_id in workload.active_tasks:
            workload.active_tasks.remove(task.task_id)
        
        # Update metrics
        if task.started_at and task.completed_at:
            duration = (task.completed_at - task.started_at).total_seconds() / 60.0  # minutes
            workload.total_task_time += duration
            workload.total_tasks_completed += 1
            workload.last_task_completion = task.completed_at
            
            # Add to history
            workload.task_history.append({
                "task_id": task.task_id,
                "duration_minutes": duration,
                "success": task.status == TaskStatus.COMPLETED,
                "completed_at": task.completed_at
            })
    
    async def _update_workload_metrics(self):
        """Update real-time workload metrics for all agents"""
        
        for agent_id, workload in self.agent_workloads.items():
            agent_capability = self.agent_capabilities.get(agent_id)
            if not agent_capability:
                continue
            
            # Calculate current utilization
            workload.current_utilization = len(workload.active_tasks) / agent_capability.max_concurrent_tasks
            
            # Update agent performance score based on recent performance
            if len(workload.task_history) > 0:
                recent_tasks = list(workload.task_history)[-10:]  # Last 10 tasks
                success_rate = sum(1 for t in recent_tasks if t.get('success', False)) / len(recent_tasks)
                
                # Update agent performance score (weighted average)
                agent_capability.performance_score = (
                    agent_capability.performance_score * 0.8 + success_rate * 0.2
                )
    
    async def _rebalance_workloads(self):
        """Rebalance workloads if agents are overloaded"""
        
        overloaded_agents = [
            agent_id for agent_id, workload in self.agent_workloads.items()
            if workload.current_utilization > self.workload_balance_threshold
        ]
        
        underloaded_agents = [
            agent_id for agent_id, workload in self.agent_workloads.items()
            if workload.current_utilization < 0.5  # Less than 50% utilized
        ]
        
        if overloaded_agents and underloaded_agents:
            logger.info(f"Rebalancing workloads: {len(overloaded_agents)} overloaded, {len(underloaded_agents)} underloaded")
            # In a real implementation, this would reassign pending tasks
    
    async def get_task_status(self, task_id: str) -> Optional[ScheduledTask]:
        """Get status of a specific task"""
        return self.scheduled_tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        
        task = self.scheduled_tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc)
        
        # Remove from queue if pending
        if task in self.task_queue:
            self.task_queue.remove(task)
        
        # Update agent workload if assigned
        if task.agent_id:
            workload = self.agent_workloads.get(task.agent_id)
            if workload and task.task_id in workload.active_tasks:
                workload.active_tasks.remove(task.task_id)
        
        logger.info(f"Cancelled task {task_id}")
        return True
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get comprehensive scheduler status"""
        
        # Calculate queue statistics
        queue_by_priority = defaultdict(int)
        queue_by_type = defaultdict(int)
        
        for task in self.task_queue:
            queue_by_priority[task.priority.value] += 1
            queue_by_type[task.task_type.value] += 1
        
        # Calculate agent utilization
        agent_utilizations = {}
        for agent_id, workload in self.agent_workloads.items():
            capability = self.agent_capabilities.get(agent_id)
            if capability:
                agent_utilizations[agent_id] = {
                    "current_tasks": len(workload.active_tasks),
                    "max_tasks": capability.max_concurrent_tasks,
                    "utilization": workload.current_utilization,
                    "performance_score": capability.performance_score
                }
        
        return {
            "scheduler_status": "running" if self.scheduler_running else "stopped",
            "queue_statistics": {
                "total_queued": len(self.task_queue),
                "by_priority": dict(queue_by_priority),
                "by_type": dict(queue_by_type)
            },
            "agent_statistics": {
                "total_agents": len(self.agent_capabilities),
                "active_agents": len([a for a in self.agent_workloads.values() if len(a.active_tasks) > 0]),
                "utilizations": agent_utilizations
            },
            "task_statistics": {
                "total_scheduled": len(self.scheduled_tasks),
                "completed_tasks": len(self.completed_tasks),
                "running_tasks": len([t for t in self.scheduled_tasks.values() if t.status == TaskStatus.RUNNING])
            },
            "configuration": {
                "max_queue_size": self.max_queue_size,
                "scheduling_interval_seconds": self.scheduling_interval_seconds,
                "workload_balance_threshold": self.workload_balance_threshold
            }
        }
    
    def get_agent_workload_metrics(self, agent_id: str) -> Optional[WorkloadMetrics]:
        """Get detailed workload metrics for a specific agent"""
        
        workload = self.agent_workloads.get(agent_id)
        capability = self.agent_capabilities.get(agent_id)
        
        if not workload or not capability:
            return None
        
        # Calculate 24h statistics
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        
        recent_tasks = [
            t for t in workload.task_history
            if t.get('completed_at') and t['completed_at'] > yesterday
        ]
        
        completed_24h = len(recent_tasks)
        avg_duration = 0.0
        success_rate = 0.0
        
        if recent_tasks:
            avg_duration = sum(t.get('duration_minutes', 0) for t in recent_tasks) / len(recent_tasks)
            success_rate = sum(1 for t in recent_tasks if t.get('success', False)) / len(recent_tasks)
        
        return WorkloadMetrics(
            agent_id=agent_id,
            current_tasks=len(workload.active_tasks),
            completed_tasks_24h=completed_24h,
            avg_task_duration_minutes=avg_duration,
            success_rate=success_rate,
            resource_utilization={"cpu": workload.current_utilization}
        )

# Factory function for service registry
def create_agent_scheduler_service() -> AgentSchedulerService:
    """Factory function to create agent scheduler service"""
    return AgentSchedulerService()