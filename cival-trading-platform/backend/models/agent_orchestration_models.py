"""
Phase 9: Autonomous Agent Orchestration Models
Multi-agent coordination, task distribution, and lifecycle management
"""

import uuid
from typing import Dict, List, Optional, Any, Union, Literal
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, validator
import json

# Agent Status and Capability Models

class AgentStatus(str, Enum):
    """Agent operational status"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    TERMINATED = "terminated"

class AgentCapability(str, Enum):
    """Agent capability types"""
    TRADING_EXECUTION = "trading_execution"
    MARKET_ANALYSIS = "market_analysis"
    RISK_MANAGEMENT = "risk_management"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    RESEARCH_ANALYSIS = "research_analysis"
    TECHNICAL_ANALYSIS = "technical_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    NEWS_PROCESSING = "news_processing"
    BACKTESTING = "backtesting"
    STRATEGY_DEVELOPMENT = "strategy_development"
    COMPLIANCE_MONITORING = "compliance_monitoring"
    REPORTING = "reporting"
    KNOWLEDGE_PROCESSING = "knowledge_processing"
    GOAL_MANAGEMENT = "goal_management"

class AgentType(str, Enum):
    """Agent type classifications"""
    SPECIALIST = "specialist"  # Single capability focus
    GENERALIST = "generalist"  # Multiple capabilities
    COORDINATOR = "coordinator"  # Orchestrates other agents
    SUPERVISOR = "supervisor"  # Monitors and manages agents
    LEARNER = "learner"  # Continuously learning agent
    HYBRID = "hybrid"  # Combines multiple agent types

class TaskPriority(str, Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"

class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"

class CoordinationMode(str, Enum):
    """Agent coordination modes"""
    HIERARCHICAL = "hierarchical"  # Top-down coordination
    PEER_TO_PEER = "peer_to_peer"  # Equal agent collaboration
    SWARM = "swarm"  # Emergent behavior coordination
    PIPELINE = "pipeline"  # Sequential task processing
    MARKET = "market"  # Auction-based task allocation

# Core Agent Models

class AgentCapabilityProfile(BaseModel):
    """Detailed agent capability profile"""
    capability: AgentCapability
    proficiency_level: float = Field(ge=0.0, le=1.0, description="Skill level 0-1")
    experience_score: float = Field(ge=0.0, description="Accumulated experience")
    success_rate: float = Field(ge=0.0, le=1.0, description="Historical success rate")
    average_execution_time: float = Field(ge=0.0, description="Average time in seconds")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentResource(BaseModel):
    """Agent resource allocation and usage"""
    cpu_allocation: float = Field(ge=0.0, le=1.0, description="CPU allocation ratio")
    memory_allocation: float = Field(ge=0.0, description="Memory in GB")
    gpu_allocation: Optional[float] = Field(None, ge=0.0, le=1.0, description="GPU allocation ratio")
    network_bandwidth: Optional[float] = Field(None, ge=0.0, description="Network bandwidth MB/s")
    storage_allocation: float = Field(ge=0.0, description="Storage in GB")
    cost_per_hour: Decimal = Field(default=Decimal("0.0"), description="Operating cost per hour")
    current_usage: Dict[str, float] = Field(default_factory=dict)

class AgentMetrics(BaseModel):
    """Agent performance metrics"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    average_task_time: float = 0.0
    success_rate: float = 0.0
    efficiency_score: float = 0.0
    collaboration_score: float = 0.0
    learning_rate: float = 0.0
    uptime_percentage: float = 0.0
    last_performance_update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AutonomousAgent(BaseModel):
    """Core autonomous agent model"""
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    agent_type: AgentType
    status: AgentStatus = AgentStatus.INITIALIZING
    
    # Capabilities and Performance
    capabilities: List[AgentCapabilityProfile] = Field(default_factory=list)
    primary_capability: AgentCapability
    specialization_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Resource Management
    resources: AgentResource
    metrics: AgentMetrics = Field(default_factory=AgentMetrics)
    
    # Lifecycle Management
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_health_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    health_score: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Coordination and Communication
    coordination_mode: CoordinationMode = CoordinationMode.PEER_TO_PEER
    communication_protocols: List[str] = Field(default_factory=list)
    current_collaborators: List[str] = Field(default_factory=list)
    supervisor_agent_id: Optional[str] = None
    supervised_agents: List[str] = Field(default_factory=list)
    
    # Configuration
    configuration: Dict[str, Any] = Field(default_factory=dict)
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    version: str = "1.0.0"
    
    # Knowledge Integration (Phase 8 connection)
    knowledge_profile_id: Optional[str] = None
    active_goals: List[str] = Field(default_factory=list)
    learned_patterns: Dict[str, Any] = Field(default_factory=dict)

# Task and Workflow Models

class TaskRequirement(BaseModel):
    """Task execution requirements"""
    required_capabilities: List[AgentCapability]
    minimum_proficiency: float = Field(ge=0.0, le=1.0, default=0.5)
    estimated_duration: float = Field(ge=0.0, description="Estimated duration in seconds")
    resource_requirements: AgentResource
    dependencies: List[str] = Field(default_factory=list)  # Other task IDs
    deadline: Optional[datetime] = None
    retry_policy: Dict[str, Any] = Field(default_factory=dict)

class TaskResult(BaseModel):
    """Task execution result"""
    task_id: str
    agent_id: str
    status: TaskStatus
    result_data: Dict[str, Any] = Field(default_factory=dict)
    execution_time: float = 0.0
    error_message: Optional[str] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AutonomousTask(BaseModel):
    """Autonomous task definition"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    task_type: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    
    # Task Definition
    requirements: TaskRequirement
    payload: Dict[str, Any] = Field(default_factory=dict)
    expected_output: Dict[str, Any] = Field(default_factory=dict)
    
    # Assignment and Execution
    assigned_agent_id: Optional[str] = None
    assignment_timestamp: Optional[datetime] = None
    execution_attempts: int = 0
    max_retries: int = 3
    
    # Lifecycle
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_for: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    # Results and Tracking
    result: Optional[TaskResult] = None
    progress_percentage: float = Field(ge=0.0, le=100.0, default=0.0)
    
    # Collaboration
    parent_workflow_id: Optional[str] = None
    child_tasks: List[str] = Field(default_factory=list)
    collaboration_context: Dict[str, Any] = Field(default_factory=dict)

class AgentWorkflow(BaseModel):
    """Multi-agent workflow orchestration"""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    workflow_type: Literal["sequential", "parallel", "conditional", "hybrid"]
    status: TaskStatus = TaskStatus.PENDING
    
    # Workflow Structure
    tasks: List[str] = Field(default_factory=list)  # Task IDs
    task_dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    coordination_mode: CoordinationMode = CoordinationMode.HIERARCHICAL
    
    # Agent Assignment
    participating_agents: List[str] = Field(default_factory=list)
    coordinator_agent_id: Optional[str] = None
    agent_roles: Dict[str, str] = Field(default_factory=dict)
    
    # Execution Control
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: float = Field(ge=0.0, le=100.0, default=0.0)
    
    # Results and Metrics
    workflow_result: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    collaboration_effectiveness: Optional[float] = Field(None, ge=0.0, le=1.0)

# Coordination and Communication Models

class AgentMessage(BaseModel):
    """Inter-agent communication message"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_agent_id: str
    recipient_agent_id: str
    message_type: Literal["request", "response", "notification", "coordination", "emergency"]
    content: Dict[str, Any]
    priority: TaskPriority = TaskPriority.MEDIUM
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    requires_acknowledgment: bool = False
    acknowledged_at: Optional[datetime] = None
    
    # Context
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    conversation_id: Optional[str] = None

class CoordinationProtocol(BaseModel):
    """Agent coordination protocol definition"""
    protocol_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    protocol_type: CoordinationMode
    
    # Protocol Rules
    coordination_rules: Dict[str, Any] = Field(default_factory=dict)
    communication_patterns: List[str] = Field(default_factory=list)
    conflict_resolution: Dict[str, Any] = Field(default_factory=dict)
    
    # Participants
    participating_agents: List[str] = Field(default_factory=list)
    leader_agent_id: Optional[str] = None
    
    # Lifecycle
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True
    version: str = "1.0.0"

class AgentCollaboration(BaseModel):
    """Active agent collaboration session"""
    collaboration_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    collaboration_type: Literal["task_sharing", "knowledge_sharing", "resource_sharing", "joint_execution"]
    
    # Participants
    participating_agents: List[str] = Field(default_factory=list)
    coordinator_agent_id: Optional[str] = None
    collaboration_protocol: str  # Protocol ID
    
    # Objectives
    shared_objectives: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    target_outcomes: Dict[str, Any] = Field(default_factory=dict)
    
    # Progress and Results
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_completion: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    progress_percentage: float = Field(ge=0.0, le=100.0, default=0.0)
    
    # Effectiveness Metrics
    collaboration_metrics: Dict[str, float] = Field(default_factory=dict)
    individual_contributions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    synergy_score: Optional[float] = Field(None, ge=0.0, le=1.0)

# Resource Management and Optimization

class ResourcePool(BaseModel):
    """Shared resource pool for agents"""
    pool_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    pool_type: Literal["compute", "memory", "storage", "network", "license"]
    
    # Capacity
    total_capacity: float
    available_capacity: float
    reserved_capacity: float = 0.0
    
    # Allocation
    current_allocations: Dict[str, float] = Field(default_factory=dict)  # agent_id -> allocation
    allocation_policy: Dict[str, Any] = Field(default_factory=dict)
    
    # Cost Management
    cost_per_unit: Decimal = Field(default=Decimal("0.0"))
    billing_interval: str = "hourly"
    
    # Monitoring
    utilization_history: List[Dict[str, Any]] = Field(default_factory=list)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)

class AgentOptimization(BaseModel):
    """Agent performance optimization recommendations"""
    optimization_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    optimization_type: Literal["performance", "resource", "collaboration", "learning"]
    
    # Analysis
    current_metrics: Dict[str, float]
    bottlenecks_identified: List[str] = Field(default_factory=list)
    optimization_opportunities: List[str] = Field(default_factory=list)
    
    # Recommendations
    recommended_changes: Dict[str, Any] = Field(default_factory=dict)
    expected_improvements: Dict[str, float] = Field(default_factory=dict)
    implementation_complexity: Literal["low", "medium", "high"] = "medium"
    
    # Timeline
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recommended_implementation_date: Optional[datetime] = None
    estimated_implementation_time: Optional[float] = None  # hours
    
    # Validation
    confidence_score: float = Field(ge=0.0, le=1.0)
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)

# Request/Response Models

class CreateAgentRequest(BaseModel):
    """Request to create a new autonomous agent"""
    name: str
    agent_type: AgentType
    primary_capability: AgentCapability
    capabilities: List[AgentCapability] = Field(default_factory=list)
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    coordination_mode: CoordinationMode = CoordinationMode.PEER_TO_PEER
    supervisor_agent_id: Optional[str] = None

class TaskAssignmentRequest(BaseModel):
    """Request to assign a task to agents"""
    task: AutonomousTask
    preferred_agents: Optional[List[str]] = None
    assignment_strategy: Literal["capability_match", "load_balance", "cost_optimize", "speed_optimize"] = "capability_match"
    allow_collaboration: bool = True
    max_agents: int = 1

class WorkflowExecutionRequest(BaseModel):
    """Request to execute a multi-agent workflow"""
    workflow: AgentWorkflow
    execution_mode: Literal["immediate", "scheduled", "conditional"] = "immediate"
    scheduling_preferences: Dict[str, Any] = Field(default_factory=dict)
    monitoring_level: Literal["basic", "detailed", "comprehensive"] = "detailed"

class AgentOrchestrationStatus(BaseModel):
    """Overall orchestration system status"""
    total_agents: int
    active_agents: int
    busy_agents: int
    pending_tasks: int
    executing_tasks: int
    completed_tasks_today: int
    failed_tasks_today: int
    active_workflows: int
    active_collaborations: int
    system_load: float = Field(ge=0.0, le=1.0)
    efficiency_score: float = Field(ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Export all models
__all__ = [
    "AgentStatus", "AgentCapability", "AgentType", "TaskPriority", "TaskStatus", "CoordinationMode",
    "AgentCapabilityProfile", "AgentResource", "AgentMetrics", "AutonomousAgent",
    "TaskRequirement", "TaskResult", "AutonomousTask", "AgentWorkflow",
    "AgentMessage", "CoordinationProtocol", "AgentCollaboration",
    "ResourcePool", "AgentOptimization",
    "CreateAgentRequest", "TaskAssignmentRequest", "WorkflowExecutionRequest", "AgentOrchestrationStatus"
]