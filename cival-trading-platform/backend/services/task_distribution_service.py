"""
Phase 9: Autonomous Task Distribution and Execution Service
Manages intelligent task assignment, execution, and workflow orchestration
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import json
import logging
from dataclasses import dataclass, field
import heapq
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.agent_orchestration_models import (
    AutonomousAgent, AutonomousTask, AgentWorkflow, TaskStatus, TaskPriority,
    AgentStatus, AgentCapability, CoordinationMode, TaskRequirement, TaskResult,
    TaskAssignmentRequest, WorkflowExecutionRequest
)
from services.agent_lifecycle_service import get_lifecycle_service
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class TaskAssignmentStrategy(str, Enum):
    """Task assignment strategies"""
    CAPABILITY_MATCH = "capability_match"      # Best capability match
    LOAD_BALANCE = "load_balance"             # Even distribution
    COST_OPTIMIZE = "cost_optimize"           # Lowest cost
    SPEED_OPTIMIZE = "speed_optimize"         # Fastest execution
    RELIABILITY_OPTIMIZE = "reliability_optimize"  # Highest success rate


class WorkflowExecutionMode(str, Enum):
    """Workflow execution modes"""
    IMMEDIATE = "immediate"      # Start immediately
    SCHEDULED = "scheduled"      # Start at specific time
    CONDITIONAL = "conditional"  # Start when conditions met


@dataclass
class TaskQueue:
    """Priority queue for task management"""
    pending: List[AutonomousTask] = field(default_factory=list)
    executing: List[AutonomousTask] = field(default_factory=list)
    completed: List[AutonomousTask] = field(default_factory=list)
    failed: List[AutonomousTask] = field(default_factory=list)
    
    def __post_init__(self):
        heapq.heapify(self.pending)


@dataclass
class AgentWorkload:
    """Agent workload tracking"""
    agent_id: str
    current_tasks: Set[str] = field(default_factory=set)
    pending_tasks: Set[str] = field(default_factory=set)
    max_concurrent_tasks: int = 3
    estimated_completion_time: Optional[datetime] = None
    
    @property
    def total_load(self) -> int:
        return len(self.current_tasks) + len(self.pending_tasks)
    
    @property
    def available_capacity(self) -> int:
        return max(0, self.max_concurrent_tasks - len(self.current_tasks))
    
    @property
    def load_percentage(self) -> float:
        return (len(self.current_tasks) / self.max_concurrent_tasks) * 100


class TaskExecutionContext(BaseModel):
    """Task execution context and environment"""
    task_id: str
    agent_id: str
    execution_environment: Dict[str, Any] = Field(default_factory=dict)
    resource_allocations: Dict[str, float] = Field(default_factory=dict)
    dependencies_resolved: List[str] = Field(default_factory=list)
    collaboration_context: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3


class TaskExecutionResult(BaseModel):
    """Detailed task execution result"""
    task_id: str
    agent_id: str
    status: TaskStatus
    execution_time_seconds: float
    resource_usage: Dict[str, float] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    quality_metrics: Dict[str, float] = Field(default_factory=dict)
    collaboration_feedback: Optional[Dict[str, Any]] = None


class WorkflowExecutionPlan(BaseModel):
    """Workflow execution plan"""
    workflow_id: str
    execution_mode: WorkflowExecutionMode
    task_sequence: List[List[str]]  # List of parallel task groups
    agent_assignments: Dict[str, str]  # task_id -> agent_id
    estimated_duration: timedelta
    resource_requirements: Dict[str, float]
    coordination_protocol: CoordinationMode
    checkpoint_intervals: List[int] = Field(default_factory=list)


class TaskDistributionService:
    """
    Intelligent task distribution and execution orchestration service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.task_queues: Dict[TaskPriority, TaskQueue] = {
            priority: TaskQueue() for priority in TaskPriority
        }
        self.agent_workloads: Dict[str, AgentWorkload] = {}
        self.active_workflows: Dict[str, AgentWorkflow] = {}
        self.execution_contexts: Dict[str, TaskExecutionContext] = {}
        self.task_dependencies: Dict[str, Set[str]] = {}  # task_id -> dependencies
        self.dependency_graph: Dict[str, Set[str]] = {}   # task_id -> dependents
        
        # Performance tracking
        self.assignment_history: List[Dict[str, Any]] = []
        self.execution_metrics: Dict[str, Dict[str, float]] = {}
        self.strategy_performance: Dict[TaskAssignmentStrategy, Dict[str, float]] = {}
        
        # Configuration
        self.max_queue_size = 1000
        self.task_timeout_default = 3600  # 1 hour
        self.workflow_timeout_default = 7200  # 2 hours
        self.rebalance_interval = 300  # 5 minutes
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the task distribution service"""
        try:
            logger.info("Initializing Task Distribution Service...")
            
            # Load pending tasks from database
            await self._load_pending_tasks()
            
            # Load active workflows
            await self._load_active_workflows()
            
            # Initialize agent workload tracking
            await self._initialize_agent_workloads()
            
            # Start background services
            asyncio.create_task(self._task_distribution_loop())
            asyncio.create_task(self._workflow_execution_loop())
            asyncio.create_task(self._task_monitoring_loop())
            asyncio.create_task(self._load_balancing_loop())
            
            logger.info("Task Distribution Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Task Distribution Service: {e}")
            raise
    
    async def submit_task(
        self, 
        task: AutonomousTask,
        assignment_request: Optional[TaskAssignmentRequest] = None
    ) -> str:
        """Submit a new task for execution"""
        try:
            logger.info(f"Submitting task: {task.name}")
            
            # Validate task
            await self._validate_task(task)
            
            # Save to database
            await self._save_task_to_database(task)
            
            # Add to appropriate priority queue
            priority_queue = self.task_queues[task.priority]
            heapq.heappush(priority_queue.pending, task)
            
            # Track dependencies
            if task.requirements.dependencies:
                self.task_dependencies[task.task_id] = set(task.requirements.dependencies)
                for dep_id in task.requirements.dependencies:
                    if dep_id not in self.dependency_graph:
                        self.dependency_graph[dep_id] = set()
                    self.dependency_graph[dep_id].add(task.task_id)
            
            # Attempt immediate assignment if requested
            if assignment_request:
                await self._attempt_immediate_assignment(task, assignment_request)
            
            logger.info(f"Task {task.task_id} submitted successfully")
            return task.task_id
            
        except Exception as e:
            logger.error(f"Failed to submit task {task.name}: {e}")
            raise HTTPException(status_code=500, detail=f"Task submission failed: {str(e)}")
    
    async def submit_workflow(
        self, 
        workflow: AgentWorkflow,
        execution_request: WorkflowExecutionRequest
    ) -> str:
        """Submit a workflow for execution"""
        try:
            logger.info(f"Submitting workflow: {workflow.name}")
            
            # Validate workflow
            await self._validate_workflow(workflow)
            
            # Create execution plan
            execution_plan = await self._create_execution_plan(workflow, execution_request)
            
            # Save workflow to database
            await self._save_workflow_to_database(workflow)
            
            # Add to active workflows
            self.active_workflows[workflow.workflow_id] = workflow
            
            # Schedule execution based on mode
            if execution_request.execution_mode == WorkflowExecutionMode.IMMEDIATE:
                asyncio.create_task(self._execute_workflow(workflow, execution_plan))
            elif execution_request.execution_mode == WorkflowExecutionMode.SCHEDULED:
                asyncio.create_task(self._schedule_workflow_execution(workflow, execution_plan, execution_request))
            else:  # CONDITIONAL
                asyncio.create_task(self._conditional_workflow_execution(workflow, execution_plan, execution_request))
            
            logger.info(f"Workflow {workflow.workflow_id} submitted successfully")
            return workflow.workflow_id
            
        except Exception as e:
            logger.error(f"Failed to submit workflow {workflow.name}: {e}")
            raise HTTPException(status_code=500, detail=f"Workflow submission failed: {str(e)}")
    
    async def assign_task_to_agent(
        self,
        task_id: str,
        agent_id: Optional[str] = None,
        strategy: TaskAssignmentStrategy = TaskAssignmentStrategy.CAPABILITY_MATCH
    ) -> bool:
        """Assign a specific task to an agent"""
        try:
            # Get task
            task = await self._get_task_by_id(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            if task.status != TaskStatus.PENDING:
                raise HTTPException(status_code=400, detail="Task is not in pending status")
            
            # Find best agent if not specified
            if not agent_id:
                agent_id = await self._find_best_agent_for_task(task, strategy)
                if not agent_id:
                    logger.warning(f"No suitable agent found for task {task_id}")
                    return False
            
            # Validate agent can handle task
            lifecycle_service = await get_lifecycle_service()
            agent = await lifecycle_service.get_agent(agent_id)
            if not agent or agent.status not in [AgentStatus.IDLE, AgentStatus.BUSY]:
                logger.warning(f"Agent {agent_id} is not available for task assignment")
                return False
            
            # Check agent workload
            if agent_id in self.agent_workloads:
                workload = self.agent_workloads[agent_id]
                if workload.available_capacity <= 0:
                    logger.warning(f"Agent {agent_id} is at maximum capacity")
                    return False
            
            # Create execution context
            context = TaskExecutionContext(
                task_id=task_id,
                agent_id=agent_id,
                timeout_seconds=task.requirements.estimated_duration or self.task_timeout_default
            )
            self.execution_contexts[task_id] = context
            
            # Update task
            task.assigned_agent_id = agent_id
            task.assignment_timestamp = datetime.now(timezone.utc)
            task.status = TaskStatus.ASSIGNED
            
            # Update agent workload
            if agent_id not in self.agent_workloads:
                self.agent_workloads[agent_id] = AgentWorkload(agent_id=agent_id)
            self.agent_workloads[agent_id].pending_tasks.add(task_id)
            
            # Update database
            await self._update_task_in_database(task)
            
            # Move from pending to executing queue
            await self._move_task_to_executing(task)
            
            # Record assignment
            self.assignment_history.append({
                "task_id": task_id,
                "agent_id": agent_id,
                "strategy": strategy,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "assignment_time_ms": 0  # Would measure actual time
            })
            
            logger.info(f"Task {task_id} assigned to agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign task {task_id} to agent {agent_id}: {e}")
            return False
    
    async def execute_task(self, task_id: str) -> TaskExecutionResult:
        """Execute a task"""
        try:
            logger.info(f"Executing task: {task_id}")
            
            # Get task and context
            task = await self._get_task_by_id(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            context = self.execution_contexts.get(task_id)
            if not context:
                raise HTTPException(status_code=400, detail="Task execution context not found")
            
            # Validate dependencies are resolved
            if not await self._check_dependencies_resolved(task_id):
                raise HTTPException(status_code=400, detail="Task dependencies not resolved")
            
            # Update task status
            task.status = TaskStatus.EXECUTING
            task.execution_attempts += 1
            start_time = datetime.now(timezone.utc)
            
            # Update agent workload
            agent_id = context.agent_id
            if agent_id in self.agent_workloads:
                workload = self.agent_workloads[agent_id]
                workload.pending_tasks.discard(task_id)
                workload.current_tasks.add(task_id)
            
            # Update database
            await self._update_task_in_database(task)
            
            try:
                # Execute the actual task
                execution_result = await self._perform_task_execution(task, context)
                
                # Calculate execution time
                end_time = datetime.now(timezone.utc)
                execution_time = (end_time - start_time).total_seconds()
                
                # Update task with results
                task.status = execution_result.status
                task.result = TaskResult(
                    task_id=task_id,
                    agent_id=agent_id,
                    status=execution_result.status,
                    result_data=execution_result.output_data,
                    execution_time=execution_time,
                    started_at=start_time,
                    completed_at=end_time if execution_result.status == TaskStatus.COMPLETED else None
                )
                task.progress_percentage = 100.0 if execution_result.status == TaskStatus.COMPLETED else 0.0
                
                # Update agent workload
                if agent_id in self.agent_workloads:
                    self.agent_workloads[agent_id].current_tasks.discard(task_id)
                
                # Move task to appropriate queue
                if execution_result.status == TaskStatus.COMPLETED:
                    await self._move_task_to_completed(task)
                    # Trigger dependent tasks
                    await self._trigger_dependent_tasks(task_id)
                else:
                    await self._handle_task_failure(task, execution_result)
                
                # Update database
                await self._update_task_in_database(task)
                
                # Update execution metrics
                await self._update_execution_metrics(task, execution_result)
                
                logger.info(f"Task {task_id} executed with status: {execution_result.status}")
                return execution_result
                
            except asyncio.TimeoutError:
                # Handle timeout
                execution_result = TaskExecutionResult(
                    task_id=task_id,
                    agent_id=agent_id,
                    status=TaskStatus.FAILED,
                    execution_time_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
                    error_details={"error": "Task execution timeout"}
                )
                
                task.status = TaskStatus.FAILED
                await self._handle_task_failure(task, execution_result)
                return execution_result
                
        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {e}")
            
            # Create error result
            execution_result = TaskExecutionResult(
                task_id=task_id,
                agent_id=context.agent_id if context else "unknown",
                status=TaskStatus.FAILED,
                execution_time_seconds=0.0,
                error_details={"error": str(e)}
            )
            
            return execution_result
    
    async def cancel_task(self, task_id: str, reason: str = "") -> bool:
        """Cancel a task"""
        try:
            task = await self._get_task_by_id(task_id)
            if not task:
                return False
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                return True
            
            # Update task status
            task.status = TaskStatus.CANCELLED
            
            # Clean up execution context
            if task_id in self.execution_contexts:
                del self.execution_contexts[task_id]
            
            # Update agent workload
            if task.assigned_agent_id and task.assigned_agent_id in self.agent_workloads:
                workload = self.agent_workloads[task.assigned_agent_id]
                workload.current_tasks.discard(task_id)
                workload.pending_tasks.discard(task_id)
            
            # Remove from queues
            await self._remove_task_from_queues(task)
            
            # Update database
            await self._update_task_in_database(task)
            
            logger.info(f"Task {task_id} cancelled: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed task status"""
        try:
            task = await self._get_task_by_id(task_id)
            if not task:
                return None
            
            context = self.execution_contexts.get(task_id)
            
            return {
                "task_id": task_id,
                "name": task.name,
                "status": task.status,
                "priority": task.priority,
                "assigned_agent_id": task.assigned_agent_id,
                "progress_percentage": task.progress_percentage,
                "execution_attempts": task.execution_attempts,
                "created_at": task.created_at.isoformat(),
                "assignment_timestamp": task.assignment_timestamp.isoformat() if task.assignment_timestamp else None,
                "estimated_completion": self._estimate_task_completion(task),
                "dependencies": list(self.task_dependencies.get(task_id, set())),
                "dependents": list(self.dependency_graph.get(task_id, set())),
                "execution_context": context.dict() if context else None,
                "result": task.result.dict() if task.result else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return None
    
    async def get_agent_workload(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent workload information"""
        try:
            if agent_id not in self.agent_workloads:
                return None
            
            workload = self.agent_workloads[agent_id]
            
            # Get task details
            current_tasks = []
            for task_id in workload.current_tasks:
                task_status = await self.get_task_status(task_id)
                if task_status:
                    current_tasks.append(task_status)
            
            pending_tasks = []
            for task_id in workload.pending_tasks:
                task_status = await self.get_task_status(task_id)
                if task_status:
                    pending_tasks.append(task_status)
            
            return {
                "agent_id": agent_id,
                "current_tasks": current_tasks,
                "pending_tasks": pending_tasks,
                "max_concurrent_tasks": workload.max_concurrent_tasks,
                "available_capacity": workload.available_capacity,
                "load_percentage": workload.load_percentage,
                "estimated_completion_time": workload.estimated_completion_time.isoformat() if workload.estimated_completion_time else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get agent workload for {agent_id}: {e}")
            return None
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            # Count tasks by status
            task_counts = {status: 0 for status in TaskStatus}
            for priority_queue in self.task_queues.values():
                task_counts[TaskStatus.PENDING] += len(priority_queue.pending)
                task_counts[TaskStatus.EXECUTING] += len(priority_queue.executing)
                task_counts[TaskStatus.COMPLETED] += len(priority_queue.completed)
                task_counts[TaskStatus.FAILED] += len(priority_queue.failed)
            
            # Agent statistics
            total_agents = len(self.agent_workloads)
            busy_agents = sum(1 for w in self.agent_workloads.values() if w.current_tasks)
            total_capacity = sum(w.max_concurrent_tasks for w in self.agent_workloads.values())
            used_capacity = sum(len(w.current_tasks) for w in self.agent_workloads.values())
            
            # Performance metrics
            avg_assignment_time = 0.0
            if self.assignment_history:
                recent_assignments = self.assignment_history[-100:]  # Last 100 assignments
                avg_assignment_time = sum(a.get("assignment_time_ms", 0) for a in recent_assignments) / len(recent_assignments)
            
            return {
                "task_counts": task_counts,
                "active_workflows": len(self.active_workflows),
                "agent_statistics": {
                    "total_agents": total_agents,
                    "busy_agents": busy_agents,
                    "idle_agents": total_agents - busy_agents,
                    "capacity_utilization": (used_capacity / total_capacity * 100) if total_capacity > 0 else 0
                },
                "performance_metrics": {
                    "avg_assignment_time_ms": avg_assignment_time,
                    "total_assignments": len(self.assignment_history),
                    "assignment_success_rate": self._calculate_assignment_success_rate()
                },
                "queue_health": {
                    "queue_sizes": {priority.value: len(queue.pending) for priority, queue in self.task_queues.items()},
                    "oldest_pending_task": await self._get_oldest_pending_task_age()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {"error": str(e)}
    
    # Background service methods
    
    async def _task_distribution_loop(self):
        """Main task distribution loop"""
        while not self._shutdown:
            try:
                # Process high priority tasks first
                for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW, TaskPriority.BACKGROUND]:
                    queue = self.task_queues[priority]
                    
                    # Process pending tasks
                    tasks_to_assign = []
                    while queue.pending and len(tasks_to_assign) < 10:  # Batch size
                        task = heapq.heappop(queue.pending)
                        if await self._can_assign_task(task):
                            tasks_to_assign.append(task)
                        else:
                            # Put back in queue if dependencies not ready
                            heapq.heappush(queue.pending, task)
                            break
                    
                    # Assign tasks
                    for task in tasks_to_assign:
                        await self.assign_task_to_agent(task.task_id)
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in task distribution loop: {e}")
                await asyncio.sleep(5)
    
    async def _workflow_execution_loop(self):
        """Workflow execution monitoring loop"""
        while not self._shutdown:
            try:
                for workflow_id, workflow in list(self.active_workflows.items()):
                    await self._update_workflow_progress(workflow)
                    
                    if workflow.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        del self.active_workflows[workflow_id]
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in workflow execution loop: {e}")
                await asyncio.sleep(10)
    
    async def _task_monitoring_loop(self):
        """Task execution monitoring loop"""
        while not self._shutdown:
            try:
                # Monitor executing tasks for timeouts
                for priority_queue in self.task_queues.values():
                    for task in priority_queue.executing:
                        if await self._is_task_timeout(task):
                            await self._handle_task_timeout(task)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in task monitoring loop: {e}")
                await asyncio.sleep(15)
    
    async def _load_balancing_loop(self):
        """Load balancing and optimization loop"""
        while not self._shutdown:
            try:
                # Rebalance workloads if needed
                await self._rebalance_agent_workloads()
                
                # Optimize task assignments
                await self._optimize_task_assignments()
                
                await asyncio.sleep(self.rebalance_interval)
                
            except Exception as e:
                logger.error(f"Error in load balancing loop: {e}")
                await asyncio.sleep(self.rebalance_interval)
    
    # Helper methods
    
    async def _find_best_agent_for_task(self, task: AutonomousTask, strategy: TaskAssignmentStrategy) -> Optional[str]:
        """Find the best agent for a task using the specified strategy"""
        lifecycle_service = await get_lifecycle_service()
        available_agents = await lifecycle_service.list_agents(
            status_filter=[AgentStatus.IDLE, AgentStatus.BUSY]
        )
        
        if not available_agents:
            return None
        
        # Filter agents by capability
        capable_agents = []
        for agent in available_agents:
            if self._agent_can_handle_task(agent, task):
                workload = self.agent_workloads.get(agent.agent_id, AgentWorkload(agent_id=agent.agent_id))
                if workload.available_capacity > 0:
                    capable_agents.append(agent)
        
        if not capable_agents:
            return None
        
        # Apply assignment strategy
        if strategy == TaskAssignmentStrategy.CAPABILITY_MATCH:
            return self._find_best_capability_match(capable_agents, task)
        elif strategy == TaskAssignmentStrategy.LOAD_BALANCE:
            return self._find_least_loaded_agent(capable_agents)
        elif strategy == TaskAssignmentStrategy.COST_OPTIMIZE:
            return self._find_lowest_cost_agent(capable_agents)
        elif strategy == TaskAssignmentStrategy.SPEED_OPTIMIZE:
            return self._find_fastest_agent(capable_agents, task)
        elif strategy == TaskAssignmentStrategy.RELIABILITY_OPTIMIZE:
            return self._find_most_reliable_agent(capable_agents, task)
        
        # Default to capability match
        return self._find_best_capability_match(capable_agents, task)
    
    def _agent_can_handle_task(self, agent: AutonomousAgent, task: AutonomousTask) -> bool:
        """Check if agent can handle the task"""
        # Check if agent has required capabilities
        required_capabilities = set(task.requirements.required_capabilities)
        agent_capabilities = set(cap.capability for cap in agent.capabilities)
        
        return required_capabilities.issubset(agent_capabilities)
    
    def _find_best_capability_match(self, agents: List[AutonomousAgent], task: AutonomousTask) -> str:
        """Find agent with best capability match"""
        best_agent = None
        best_score = -1
        
        for agent in agents:
            score = self._calculate_capability_score(agent, task)
            if score > best_score:
                best_score = score
                best_agent = agent
        
        return best_agent.agent_id if best_agent else agents[0].agent_id
    
    def _calculate_capability_score(self, agent: AutonomousAgent, task: AutonomousTask) -> float:
        """Calculate capability match score"""
        required_capabilities = task.requirements.required_capabilities
        total_score = 0.0
        
        for req_cap in required_capabilities:
            for agent_cap in agent.capabilities:
                if agent_cap.capability == req_cap:
                    total_score += agent_cap.proficiency_level * agent_cap.success_rate
                    break
        
        return total_score / len(required_capabilities) if required_capabilities else 0.0
    
    def _find_least_loaded_agent(self, agents: List[AutonomousAgent]) -> str:
        """Find agent with least workload"""
        best_agent = None
        min_load = float('inf')
        
        for agent in agents:
            workload = self.agent_workloads.get(agent.agent_id, AgentWorkload(agent_id=agent.agent_id))
            if workload.total_load < min_load:
                min_load = workload.total_load
                best_agent = agent
        
        return best_agent.agent_id if best_agent else agents[0].agent_id
    
    def _find_lowest_cost_agent(self, agents: List[AutonomousAgent]) -> str:
        """Find agent with lowest cost"""
        return min(agents, key=lambda a: a.resources.cost_per_hour).agent_id
    
    def _find_fastest_agent(self, agents: List[AutonomousAgent], task: AutonomousTask) -> str:
        """Find agent likely to execute fastest"""
        # This would analyze historical execution times
        return agents[0].agent_id
    
    def _find_most_reliable_agent(self, agents: List[AutonomousAgent], task: AutonomousTask) -> str:
        """Find most reliable agent for task type"""
        # This would analyze success rates for similar tasks
        return agents[0].agent_id
    
    # Additional helper methods would be implemented here...
    
    async def _validate_task(self, task: AutonomousTask):
        """Validate task before submission"""
        if not task.name or not task.requirements:
            raise ValueError("Task name and requirements are required")
    
    async def _validate_workflow(self, workflow: AgentWorkflow):
        """Validate workflow before submission"""
        if not workflow.name or not workflow.tasks:
            raise ValueError("Workflow name and tasks are required")
    
    async def _save_task_to_database(self, task: AutonomousTask):
        """Save task to database"""
        # Implementation would save to Supabase
        pass
    
    async def _save_workflow_to_database(self, workflow: AgentWorkflow):
        """Save workflow to database"""
        # Implementation would save to Supabase
        pass
    
    async def _get_task_by_id(self, task_id: str) -> Optional[AutonomousTask]:
        """Get task by ID"""
        # Implementation would load from database
        return None
    
    # Additional methods continue here...


# Global service instance
_task_distribution_service: Optional[TaskDistributionService] = None


async def get_task_distribution_service() -> TaskDistributionService:
    """Get the global task distribution service instance"""
    global _task_distribution_service
    
    if _task_distribution_service is None:
        _task_distribution_service = TaskDistributionService()
        await _task_distribution_service.initialize()
    
    return _task_distribution_service


@asynccontextmanager
async def task_distribution_context():
    """Context manager for task distribution service"""
    service = await get_task_distribution_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass