"""
Goal Management Service - Phase 8
Advanced autonomous goal creation, tracking, and completion system
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

import redis.asyncio as redis
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class GoalType(Enum):
    PROFIT_TARGET = "profit_target"
    TRADE_COUNT = "trade_count"
    WIN_RATE = "win_rate"
    PORTFOLIO_VALUE = "portfolio_value"
    RISK_MANAGEMENT = "risk_management"
    STRATEGY_PERFORMANCE = "strategy_performance"
    TIME_BASED = "time_based"
    COLLABORATIVE = "collaborative"

class GoalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class GoalPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5

@dataclass
class Goal:
    """Goal definition"""
    goal_id: str
    goal_name: str
    goal_type: GoalType
    description: str
    target_value: Decimal
    current_value: Decimal
    progress_percentage: float
    status: GoalStatus
    priority: GoalPriority
    created_at: datetime
    target_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agents: List[str] = None
    assigned_farms: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.assigned_agents is None:
            self.assigned_agents = []
        if self.assigned_farms is None:
            self.assigned_farms = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class GoalCompletion:
    """Goal completion details"""
    goal_id: str
    completion_timestamp: datetime
    final_value: Decimal
    success_rate: float
    total_profit: Decimal
    total_trades: int
    completion_time_days: int
    contributing_agents: List[str]
    contributing_farms: List[str]
    performance_metrics: Dict[str, Any]

@dataclass
class GoalProgress:
    """Goal progress tracking"""
    goal_id: str
    timestamp: datetime
    current_value: Decimal
    progress_percentage: float
    velocity: float  # Progress per day
    estimated_completion: Optional[datetime]
    milestones_achieved: List[str]
    blockers: List[str]

class GoalManagementService:
    """
    Advanced goal management service with autonomous goal creation and completion detection
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # Active goals tracking
        self.active_goals: Dict[str, Goal] = {}
        self.goal_progress: Dict[str, List[GoalProgress]] = {}
        self.completed_goals: Dict[str, GoalCompletion] = {}
        
        # Goal templates for autonomous creation
        self.goal_templates = {
            "daily_profit": {
                "name": "Daily Profit Target",
                "type": GoalType.PROFIT_TARGET,
                "target_value": Decimal("50"),
                "description": "Achieve $50 profit in a single day"
            },
            "weekly_trades": {
                "name": "Weekly Trade Volume",
                "type": GoalType.TRADE_COUNT,
                "target_value": Decimal("100"),
                "description": "Execute 100 trades in one week"
            },
            "monthly_win_rate": {
                "name": "Monthly Win Rate",
                "type": GoalType.WIN_RATE,
                "target_value": Decimal("0.7"),
                "description": "Maintain 70% win rate for the month"
            }
        }
        
        # Completion detection settings
        self.completion_check_interval = 60  # seconds
        self.progress_update_interval = 300  # seconds
        
        logger.info("GoalManagementService initialized")
    
    async def initialize(self):
        """Initialize the goal management service"""
        try:
            # Load active goals from database
            await self._load_active_goals()
            
            # Start background monitoring
            asyncio.create_task(self._goal_monitoring_loop())
            asyncio.create_task(self._progress_tracking_loop())
            asyncio.create_task(self._autonomous_goal_creation_loop())
            
            logger.info("GoalManagementService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GoalManagementService: {e}")
            raise
    
    async def create_goal(self, goal_data: Dict[str, Any]) -> Goal:
        """Create a new goal"""
        try:
            goal = Goal(
                goal_id=str(uuid.uuid4()),
                goal_name=goal_data["name"],
                goal_type=GoalType(goal_data["type"]),
                description=goal_data["description"],
                target_value=Decimal(str(goal_data["target_value"])),
                current_value=Decimal("0"),
                progress_percentage=0.0,
                status=GoalStatus.PENDING,
                priority=GoalPriority(goal_data.get("priority", 2)),
                created_at=datetime.now(timezone.utc),
                target_date=datetime.fromisoformat(goal_data["target_date"]) if goal_data.get("target_date") else None,
                assigned_agents=goal_data.get("assigned_agents", []),
                assigned_farms=goal_data.get("assigned_farms", []),
                metadata=goal_data.get("metadata", {})
            )
            
            # Save to database
            if self.supabase:
                goal_dict = asdict(goal)
                goal_dict["goal_type"] = goal.goal_type.value
                goal_dict["status"] = goal.status.value
                goal_dict["priority"] = goal.priority.value
                goal_dict["created_at"] = goal.created_at.isoformat()
                if goal.target_date:
                    goal_dict["target_date"] = goal.target_date.isoformat()
                
                self.supabase.table('goals').insert(goal_dict).execute()
            
            # Add to active goals
            self.active_goals[goal.goal_id] = goal
            
            # Initialize progress tracking
            self.goal_progress[goal.goal_id] = []
            
            # Cache in Redis
            if self.redis:
                await self.redis.setex(
                    f"goal:{goal.goal_id}",
                    3600,
                    json.dumps(asdict(goal), default=str)
                )
            
            # Auto-assign to agents/farms if specified
            if goal.assigned_agents:
                await self._assign_goal_to_agents(goal.goal_id, goal.assigned_agents)
            
            if goal.assigned_farms:
                await self._assign_goal_to_farms(goal.goal_id, goal.assigned_farms)
            
            logger.info(f"Created goal: {goal.goal_name} ({goal.goal_id})")
            return goal
            
        except Exception as e:
            logger.error(f"Failed to create goal: {e}")
            raise
    
    async def update_goal_progress(self, goal_id: str, current_value: Decimal) -> GoalProgress:
        """Update goal progress"""
        try:
            goal = self.active_goals.get(goal_id)
            if not goal:
                raise ValueError(f"Goal {goal_id} not found")
            
            # Calculate progress percentage
            if goal.target_value > 0:
                progress_percentage = min(float(current_value / goal.target_value * 100), 100.0)
            else:
                progress_percentage = 0.0
            
            # Calculate velocity (progress per day)
            velocity = 0.0
            if self.goal_progress.get(goal_id):
                last_progress = self.goal_progress[goal_id][-1]
                time_diff = (datetime.now(timezone.utc) - last_progress.timestamp).total_seconds() / 86400  # days
                if time_diff > 0:
                    value_diff = float(current_value - last_progress.current_value)
                    velocity = value_diff / time_diff
            
            # Estimate completion date
            estimated_completion = None
            if velocity > 0 and progress_percentage < 100:
                remaining_value = float(goal.target_value - current_value)
                days_to_completion = remaining_value / velocity
                estimated_completion = datetime.now(timezone.utc) + timedelta(days=days_to_completion)
            
            # Create progress record
            progress = GoalProgress(
                goal_id=goal_id,
                timestamp=datetime.now(timezone.utc),
                current_value=current_value,
                progress_percentage=progress_percentage,
                velocity=velocity,
                estimated_completion=estimated_completion,
                milestones_achieved=[],
                blockers=[]
            )
            
            # Update goal
            goal.current_value = current_value
            goal.progress_percentage = progress_percentage
            
            # Check if goal is completed
            if progress_percentage >= 100.0 and goal.status != GoalStatus.COMPLETED:
                await self._complete_goal(goal_id)
            
            # Store progress
            if goal_id not in self.goal_progress:
                self.goal_progress[goal_id] = []
            self.goal_progress[goal_id].append(progress)
            
            # Keep only last 100 progress records
            if len(self.goal_progress[goal_id]) > 100:
                self.goal_progress[goal_id] = self.goal_progress[goal_id][-100:]
            
            # Update database
            if self.supabase:
                progress_dict = asdict(progress)
                progress_dict["timestamp"] = progress.timestamp.isoformat()
                if progress.estimated_completion:
                    progress_dict["estimated_completion"] = progress.estimated_completion.isoformat()
                
                self.supabase.table('goal_progress').insert(progress_dict).execute()
                
                # Update goal in database
                goal_update = {
                    "current_value": float(current_value),
                    "progress_percentage": progress_percentage,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                self.supabase.table('goals').update(goal_update).eq('goal_id', goal_id).execute()
            
            logger.info(f"Updated progress for goal {goal_id}: {progress_percentage:.1f}%")
            return progress
            
        except Exception as e:
            logger.error(f"Failed to update goal progress: {e}")
            raise
    
    async def _complete_goal(self, goal_id: str) -> GoalCompletion:
        """Complete a goal and trigger fund collection"""
        try:
            goal = self.active_goals.get(goal_id)
            if not goal:
                raise ValueError(f"Goal {goal_id} not found")
            
            # Calculate completion metrics
            completion_time_days = (datetime.now(timezone.utc) - goal.created_at).days
            
            # Get performance metrics from agents and farms
            performance_metrics = await self._calculate_goal_performance_metrics(goal_id)
            
            # Create completion record
            completion = GoalCompletion(
                goal_id=goal_id,
                completion_timestamp=datetime.now(timezone.utc),
                final_value=goal.current_value,
                success_rate=1.0,  # Successful completion
                total_profit=performance_metrics.get("total_profit", Decimal("0")),
                total_trades=performance_metrics.get("total_trades", 0),
                completion_time_days=completion_time_days,
                contributing_agents=goal.assigned_agents.copy(),
                contributing_farms=goal.assigned_farms.copy(),
                performance_metrics=performance_metrics
            )
            
            # Update goal status
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.now(timezone.utc)
            
            # Store completion
            self.completed_goals[goal_id] = completion
            
            # Remove from active goals
            self.active_goals.pop(goal_id, None)
            
            # Update database
            if self.supabase:
                completion_dict = asdict(completion)
                completion_dict["completion_timestamp"] = completion.completion_timestamp.isoformat()
                completion_dict["performance_metrics"] = json.dumps(performance_metrics, default=str)
                
                self.supabase.table('goal_completions').insert(completion_dict).execute()
                
                # Update goal status
                self.supabase.table('goals').update({
                    "status": GoalStatus.COMPLETED.value,
                    "completed_at": goal.completed_at.isoformat()
                }).eq('goal_id', goal_id).execute()
            
            # Trigger automatic fund collection
            await self._trigger_goal_completion_collection(goal_id, completion)
            
            logger.info(f"Goal completed: {goal.goal_name} ({goal_id})")
            return completion
            
        except Exception as e:
            logger.error(f"Failed to complete goal: {e}")
            raise
    
    async def _trigger_goal_completion_collection(self, goal_id: str, completion: GoalCompletion):
        """Trigger automatic fund collection when goal is completed"""
        try:
            # Get master wallet service
            master_wallet_service = self.registry.get_service("master_wallet_service")
            if not master_wallet_service:
                logger.warning("Master wallet service not available for fund collection")
                return
            
            # Collect funds from all contributing agents and farms
            total_collected = Decimal("0")
            
            # Collect from agents
            for agent_id in completion.contributing_agents:
                try:
                    collection_request = {
                        "target_type": "agent",
                        "target_id": agent_id,
                        "collection_type": "goal_completion",
                        "goal_id": goal_id,
                        "collection_reason": f"Goal completion: {goal_id}"
                    }
                    
                    # This would need the actual wallet ID - simplified for now
                    collected_amount = await master_wallet_service.collect_funds("master_wallet", collection_request)
                    total_collected += collected_amount
                    
                    logger.info(f"Collected {collected_amount} from agent {agent_id} for goal {goal_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to collect from agent {agent_id}: {e}")
            
            # Collect from farms
            for farm_id in completion.contributing_farms:
                try:
                    collection_request = {
                        "target_type": "farm", 
                        "target_id": farm_id,
                        "collection_type": "goal_completion",
                        "goal_id": goal_id,
                        "collection_reason": f"Goal completion: {goal_id}"
                    }
                    
                    collected_amount = await master_wallet_service.collect_funds("master_wallet", collection_request)
                    total_collected += collected_amount
                    
                    logger.info(f"Collected {collected_amount} from farm {farm_id} for goal {goal_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to collect from farm {farm_id}: {e}")
            
            # Record collection in completion
            completion.performance_metrics["total_collected"] = float(total_collected)
            
            # Notify other services of goal completion
            await self._notify_goal_completion(goal_id, completion, total_collected)
            
            logger.info(f"Goal completion collection: {total_collected} total collected for goal {goal_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger goal completion collection: {e}")
    
    async def _notify_goal_completion(self, goal_id: str, completion: GoalCompletion, total_collected: Decimal):
        """Notify other services of goal completion"""
        try:
            # Publish completion event
            completion_event = {
                "event_type": "goal_completed",
                "goal_id": goal_id,
                "completion_timestamp": completion.completion_timestamp.isoformat(),
                "total_profit": float(completion.total_profit),
                "total_collected": float(total_collected),
                "contributing_agents": completion.contributing_agents,
                "contributing_farms": completion.contributing_farms,
                "performance_metrics": completion.performance_metrics
            }
            
            # Publish to Redis if available
            if self.redis:
                await self.redis.publish("goal_completion", json.dumps(completion_event, default=str))
            
            # Notify agent performance service
            agent_performance_service = self.registry.get_service("agent_performance_service")
            if agent_performance_service:
                await agent_performance_service.record_goal_completion(goal_id, completion)
            
            # Notify farm management service
            farm_service = self.registry.get_service("farm_management_service")
            if farm_service:
                await farm_service.record_goal_completion(goal_id, completion)
            
            logger.info(f"Notified services of goal completion: {goal_id}")
            
        except Exception as e:
            logger.error(f"Failed to notify goal completion: {e}")
    
    async def _calculate_goal_performance_metrics(self, goal_id: str) -> Dict[str, Any]:
        """Calculate performance metrics for a completed goal"""
        try:
            metrics = {
                "total_profit": Decimal("0"),
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_profit_per_trade": Decimal("0"),
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0
            }
            
            goal = self.active_goals.get(goal_id) or self._get_goal_from_completed(goal_id)
            if not goal:
                return metrics
            
            # Get metrics from assigned agents
            agent_performance_service = self.registry.get_service("agent_performance_service")
            if agent_performance_service:
                for agent_id in goal.assigned_agents:
                    agent_metrics = await agent_performance_service.get_goal_specific_metrics(agent_id, goal_id)
                    if agent_metrics:
                        metrics["total_profit"] += agent_metrics.get("profit", Decimal("0"))
                        metrics["total_trades"] += agent_metrics.get("trades", 0)
            
            # Get metrics from assigned farms
            farm_service = self.registry.get_service("farm_management_service")
            if farm_service:
                for farm_id in goal.assigned_farms:
                    farm_metrics = await farm_service.get_goal_specific_metrics(farm_id, goal_id)
                    if farm_metrics:
                        metrics["total_profit"] += farm_metrics.get("profit", Decimal("0"))
                        metrics["total_trades"] += farm_metrics.get("trades", 0)
            
            # Calculate derived metrics
            if metrics["total_trades"] > 0:
                metrics["avg_profit_per_trade"] = metrics["total_profit"] / metrics["total_trades"]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate goal performance metrics: {e}")
            return {}
    
    async def _assign_goal_to_agents(self, goal_id: str, agent_ids: List[str]):
        """Assign goal to specific agents"""
        try:
            agent_service = self.registry.get_service("agent_management_service")
            if agent_service:
                for agent_id in agent_ids:
                    await agent_service.assign_goal(agent_id, goal_id)
                    logger.info(f"Assigned goal {goal_id} to agent {agent_id}")
                    
        except Exception as e:
            logger.error(f"Failed to assign goal to agents: {e}")
    
    async def _assign_goal_to_farms(self, goal_id: str, farm_ids: List[str]):
        """Assign goal to specific farms"""
        try:
            farm_service = self.registry.get_service("farm_management_service")
            if farm_service:
                for farm_id in farm_ids:
                    await farm_service.assign_goal(farm_id, goal_id)
                    logger.info(f"Assigned goal {goal_id} to farm {farm_id}")
                    
        except Exception as e:
            logger.error(f"Failed to assign goal to farms: {e}")
    
    async def _load_active_goals(self):
        """Load active goals from database"""
        try:
            if self.supabase:
                response = self.supabase.table('goals').select('*')\
                    .in_('status', [GoalStatus.PENDING.value, GoalStatus.ACTIVE.value, GoalStatus.IN_PROGRESS.value])\
                    .execute()
                
                for goal_data in response.data:
                    goal = Goal(
                        goal_id=goal_data['goal_id'],
                        goal_name=goal_data['goal_name'],
                        goal_type=GoalType(goal_data['goal_type']),
                        description=goal_data['description'],
                        target_value=Decimal(str(goal_data['target_value'])),
                        current_value=Decimal(str(goal_data['current_value'])),
                        progress_percentage=goal_data['progress_percentage'],
                        status=GoalStatus(goal_data['status']),
                        priority=GoalPriority(goal_data['priority']),
                        created_at=datetime.fromisoformat(goal_data['created_at']),
                        target_date=datetime.fromisoformat(goal_data['target_date']) if goal_data.get('target_date') else None,
                        completed_at=datetime.fromisoformat(goal_data['completed_at']) if goal_data.get('completed_at') else None,
                        assigned_agents=goal_data.get('assigned_agents', []),
                        assigned_farms=goal_data.get('assigned_farms', []),
                        metadata=goal_data.get('metadata', {})
                    )
                    
                    self.active_goals[goal.goal_id] = goal
                
                logger.info(f"Loaded {len(self.active_goals)} active goals")
                
        except Exception as e:
            logger.error(f"Failed to load active goals: {e}")
    
    async def _goal_monitoring_loop(self):
        """Background goal monitoring and completion detection"""
        while True:
            try:
                await asyncio.sleep(self.completion_check_interval)
                
                for goal_id, goal in self.active_goals.items():
                    try:
                        # Check if goal should be completed based on current progress
                        if goal.progress_percentage >= 100.0 and goal.status != GoalStatus.COMPLETED:
                            await self._complete_goal(goal_id)
                        
                        # Check for goal expiration
                        if goal.target_date and datetime.now(timezone.utc) > goal.target_date:
                            if goal.status not in [GoalStatus.COMPLETED, GoalStatus.FAILED]:
                                await self._expire_goal(goal_id)
                        
                    except Exception as e:
                        logger.error(f"Error monitoring goal {goal_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in goal monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _progress_tracking_loop(self):
        """Background progress tracking"""
        while True:
            try:
                await asyncio.sleep(self.progress_update_interval)
                
                for goal_id, goal in self.active_goals.items():
                    try:
                        # Update progress based on current agent/farm performance
                        current_value = await self._calculate_current_goal_value(goal_id)
                        if current_value != goal.current_value:
                            await self.update_goal_progress(goal_id, current_value)
                        
                    except Exception as e:
                        logger.error(f"Error tracking progress for goal {goal_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in progress tracking loop: {e}")
                await asyncio.sleep(60)
    
    async def _autonomous_goal_creation_loop(self):
        """Background autonomous goal creation"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Analyze system performance and create goals as needed
                await self._create_autonomous_goals()
                
            except Exception as e:
                logger.error(f"Error in autonomous goal creation loop: {e}")
                await asyncio.sleep(1800)  # Retry in 30 minutes
    
    async def _create_autonomous_goals(self):
        """Create goals autonomously based on system performance"""
        try:
            # Analyze current goal completion rates
            completion_rate = await self._calculate_goal_completion_rate()
            
            # Create new goals if completion rate is high
            if completion_rate > 0.8 and len(self.active_goals) < 10:
                # Create profit-based goals
                await self._create_adaptive_profit_goal()
                
                # Create trade volume goals
                await self._create_adaptive_volume_goal()
                
                logger.info("Created autonomous goals based on performance analysis")
                
        except Exception as e:
            logger.error(f"Failed to create autonomous goals: {e}")
    
    async def _calculate_current_goal_value(self, goal_id: str) -> Decimal:
        """Calculate current value of a goal based on agent/farm performance"""
        try:
            goal = self.active_goals.get(goal_id)
            if not goal:
                return Decimal("0")
            
            current_value = Decimal("0")
            
            # Get value from assigned agents
            agent_performance_service = self.registry.get_service("agent_performance_service")
            if agent_performance_service:
                for agent_id in goal.assigned_agents:
                    agent_contribution = await agent_performance_service.get_goal_contribution(agent_id, goal_id)
                    current_value += agent_contribution
            
            # Get value from assigned farms
            farm_service = self.registry.get_service("farm_management_service")
            if farm_service:
                for farm_id in goal.assigned_farms:
                    farm_contribution = await farm_service.get_goal_contribution(farm_id, goal_id)
                    current_value += farm_contribution
            
            return current_value
            
        except Exception as e:
            logger.error(f"Failed to calculate current goal value: {e}")
            return Decimal("0")
    
    async def get_goal_status(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive goal status"""
        try:
            goal = self.active_goals.get(goal_id)
            if not goal:
                # Check completed goals
                completion = self.completed_goals.get(goal_id)
                if completion:
                    return {
                        "goal_id": goal_id,
                        "status": "completed",
                        "completion_data": asdict(completion)
                    }
                return None
            
            # Get latest progress
            latest_progress = None
            if goal_id in self.goal_progress and self.goal_progress[goal_id]:
                latest_progress = self.goal_progress[goal_id][-1]
            
            return {
                "goal_id": goal_id,
                "name": goal.goal_name,
                "type": goal.goal_type.value,
                "status": goal.status.value,
                "progress_percentage": goal.progress_percentage,
                "current_value": float(goal.current_value),
                "target_value": float(goal.target_value),
                "assigned_agents": goal.assigned_agents,
                "assigned_farms": goal.assigned_farms,
                "latest_progress": asdict(latest_progress) if latest_progress else None,
                "created_at": goal.created_at.isoformat(),
                "target_date": goal.target_date.isoformat() if goal.target_date else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get goal status: {e}")
            return None
    
    async def get_all_active_goals(self) -> List[Goal]:
        """Get all active goals"""
        return list(self.active_goals.values())
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        return {
            "service": "goal_management_service",
            "status": "running",
            "active_goals": len(self.active_goals),
            "completed_goals": len(self.completed_goals),
            "goal_completion_rate": await self._calculate_goal_completion_rate(),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }
    
    async def _calculate_goal_completion_rate(self) -> float:
        """Calculate goal completion rate"""
        try:
            total_goals = len(self.active_goals) + len(self.completed_goals)
            if total_goals == 0:
                return 0.0
            
            return len(self.completed_goals) / total_goals
            
        except Exception:
            return 0.0

    async def analyze_natural_language_goal(self, input_text: str) -> Dict[str, Any]:
        """Analyze natural language input and extract goal parameters"""
        try:
            # Basic NLP analysis - in production, you'd use LLM integration
            analysis = {
                "input": input_text,
                "suggested_name": "",
                "description": f"Goal created from: \"{input_text}\"",
                "goal_type": "custom",
                "target_value": 1000,
                "priority": 2,
                "unit": "USD",
                "timeframe": "daily",
                "feasibility": "High",
                "risk_level": "medium",
                "success_probability": 75,
                "suggested_agents": [],
                "suggested_farms": []
            }
            
            input_lower = input_text.lower()
            
            # Extract monetary amounts
            import re
            money_patterns = [
                r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:dollars?|usd|\$)',
                r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:per|daily|day)',
            ]
            
            for pattern in money_patterns:
                match = re.search(pattern, input_lower)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        analysis["target_value"] = float(amount_str)
                        analysis["unit"] = "USD"
                        break
                    except ValueError:
                        continue
            
            # Extract percentages
            percent_pattern = r'(\d+(?:\.\d+)?)\s*(?:%|percent)'
            percent_match = re.search(percent_pattern, input_lower)
            if percent_match:
                percentage = float(percent_match.group(1))
                if 'win' in input_lower or 'success' in input_lower:
                    analysis["goal_type"] = "win_rate"
                    analysis["target_value"] = percentage
                    analysis["unit"] = "%"
            
            # Determine goal type and timeframe
            if any(word in input_lower for word in ['profit', 'money', 'earn', 'make', '$']):
                analysis["goal_type"] = "profit_target"
                analysis["suggested_name"] = f"Profit Target: ${analysis['target_value']}"
                
            if any(word in input_lower for word in ['win rate', 'success rate', 'accuracy']):
                analysis["goal_type"] = "win_rate"
                analysis["suggested_name"] = f"Win Rate: {analysis['target_value']}%"
                
            if any(word in input_lower for word in ['trade', 'trades', 'transaction']):
                analysis["goal_type"] = "trade_count"
                analysis["unit"] = "trades"
                analysis["suggested_name"] = f"Trade Count: {analysis['target_value']}"
            
            # Determine timeframe
            if any(word in input_lower for word in ['daily', 'day', 'per day']):
                analysis["timeframe"] = "daily"
            elif any(word in input_lower for word in ['weekly', 'week', 'per week']):
                analysis["timeframe"] = "weekly"
            elif any(word in input_lower for word in ['monthly', 'month', 'per month']):
                analysis["timeframe"] = "monthly"
            
            # Determine priority based on keywords
            if any(word in input_lower for word in ['urgent', 'critical', 'immediately', 'asap']):
                analysis["priority"] = 4
            elif any(word in input_lower for word in ['important', 'high priority', 'soon']):
                analysis["priority"] = 3
            elif any(word in input_lower for word in ['low priority', 'when possible', 'eventually']):
                analysis["priority"] = 1
            
            # Risk assessment
            if analysis["target_value"] > 10000:
                analysis["risk_level"] = "high"
                analysis["success_probability"] = 60
            elif analysis["target_value"] > 1000:
                analysis["risk_level"] = "medium"
                analysis["success_probability"] = 75
            else:
                analysis["risk_level"] = "low"
                analysis["success_probability"] = 85
            
            # Suggest agents based on goal type
            if analysis["goal_type"] == "profit_target":
                analysis["suggested_agents"] = ["marcus_momentum", "alex_arbitrage"]
            elif analysis["goal_type"] == "win_rate":
                analysis["suggested_agents"] = ["sophia_reversion", "riley_risk"]
            elif analysis["goal_type"] == "trade_count":
                analysis["suggested_agents"] = ["marcus_momentum", "trading_bot_1"]
            
            # Suggest farms
            if analysis["target_value"] > 5000:
                analysis["suggested_farms"] = ["darvas_box_farm", "elliott_wave_farm"]
            else:
                analysis["suggested_farms"] = ["multi_strategy_farm"]
            
            # Set default name if not set
            if not analysis["suggested_name"]:
                analysis["suggested_name"] = f"Custom Goal: {input_text[:50]}..."
            
            logger.info(f"Analyzed natural language goal: {input_text}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze natural language goal: {e}")
            # Return basic fallback analysis
            return {
                "input": input_text,
                "suggested_name": f"Goal: {input_text[:50]}...",
                "description": f"Goal created from: \"{input_text}\"",
                "goal_type": "custom",
                "target_value": 1000,
                "priority": 2,
                "unit": "USD",
                "timeframe": "daily",
                "feasibility": "Medium",
                "risk_level": "medium",
                "success_probability": 70,
                "suggested_agents": [],
                "suggested_farms": []
            }

    async def get_goal_metrics(self) -> Dict[str, Any]:
        """Get comprehensive goal metrics for dashboard"""
        try:
            total_goals = len(self.active_goals) + len(self.completed_goals)
            active_goals = [g for g in self.active_goals.values() if g.status == GoalStatus.ACTIVE]
            
            # Calculate average progress
            avg_progress = 0.0
            if self.active_goals:
                total_progress = sum(goal.progress_percentage for goal in self.active_goals.values())
                avg_progress = total_progress / len(self.active_goals)
            
            # Calculate completion rate
            completion_rate = await self._calculate_goal_completion_rate()
            
            # Get total profit from completed goals
            total_profit = sum(
                float(completion.total_profit) 
                for completion in self.completed_goals.values()
            )
            
            return {
                "total_goals": total_goals,
                "active_goals": len(active_goals),
                "completed_goals": len(self.completed_goals),
                "pending_goals": len([g for g in self.active_goals.values() if g.status == GoalStatus.PENDING]),
                "average_progress": avg_progress,
                "completion_rate": completion_rate * 100,
                "total_profit": total_profit,
                "goals_by_type": self._get_goals_by_type(),
                "goals_by_priority": self._get_goals_by_priority(),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get goal metrics: {e}")
            return {
                "total_goals": 0,
                "active_goals": 0,
                "completed_goals": 0,
                "pending_goals": 0,
                "average_progress": 0.0,
                "completion_rate": 0.0,
                "total_profit": 0.0,
                "goals_by_type": {},
                "goals_by_priority": {},
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

    def _get_goals_by_type(self) -> Dict[str, int]:
        """Get goal counts by type"""
        type_counts = {}
        for goal in self.active_goals.values():
            goal_type = goal.goal_type.value
            type_counts[goal_type] = type_counts.get(goal_type, 0) + 1
        return type_counts

    def _get_goals_by_priority(self) -> Dict[str, int]:
        """Get goal counts by priority"""
        priority_counts = {}
        for goal in self.active_goals.values():
            priority = goal.priority.value
            priority_counts[str(priority)] = priority_counts.get(str(priority), 0) + 1
        return priority_counts

# Factory function for service registry
def create_goal_management_service():
    """Factory function to create GoalManagementService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = GoalManagementService(redis_client, supabase_client)
    return service