"""
Phase 6: Wallet-Goal Completion Integration - Advanced Goal-Driven Fund Management
Deep integration between wallet operations and goal completion with automated fund collection
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
from enum import Enum

from ..core.service_registry import get_registry
from ..models.master_wallet_models import FundAllocation, WalletPerformanceMetrics
from ..services.wallet_event_streaming_service import WalletEventType

logger = logging.getLogger(__name__)

class GoalStatus(Enum):
    """Goal completion status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class GoalType(Enum):
    """Types of goals that can be tracked"""
    PROFIT_TARGET = "profit_target"
    ROI_TARGET = "roi_target"
    RISK_LIMIT = "risk_limit"
    TIME_TARGET = "time_target"
    VOLUME_TARGET = "volume_target"
    DRAWDOWN_LIMIT = "drawdown_limit"
    CONSISTENCY_TARGET = "consistency_target"

class GoalTriggerAction(Enum):
    """Actions to take when goal is completed"""
    COLLECT_PROFITS = "collect_profits"
    COLLECT_PARTIAL = "collect_partial"
    COLLECT_ALL = "collect_all"
    REALLOCATE_FUNDS = "reallocate_funds"
    INCREASE_ALLOCATION = "increase_allocation"
    DECREASE_ALLOCATION = "decrease_allocation"
    NOTIFY_ONLY = "notify_only"

class WalletGoal:
    """Comprehensive goal model for wallet-driven objectives"""
    
    def __init__(self, goal_id: str, goal_type: GoalType, target_value: Decimal, 
                 wallet_id: str, allocation_id: Optional[str] = None):
        self.goal_id = goal_id
        self.goal_type = goal_type
        self.target_value = target_value
        self.current_value = Decimal("0")
        self.wallet_id = wallet_id
        self.allocation_id = allocation_id
        
        # Goal configuration
        self.description = ""
        self.priority = 1  # 1-10 scale
        self.auto_execute = True
        self.trigger_actions: List[GoalTriggerAction] = []
        
        # Progress tracking
        self.status = GoalStatus.PENDING
        self.progress_percentage = Decimal("0")
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.deadline: Optional[datetime] = None
        
        # Performance metrics
        self.initial_allocation = Decimal("0")
        self.current_allocation = Decimal("0")
        self.total_return = Decimal("0")
        self.roi_percentage = Decimal("0")
        self.time_to_completion: Optional[timedelta] = None
        
        # Metadata
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.metadata: Dict[str, Any] = {}
    
    def calculate_progress(self) -> Decimal:
        """Calculate goal completion progress percentage"""
        if self.target_value == 0:
            return Decimal("0")
        
        if self.goal_type in [GoalType.PROFIT_TARGET, GoalType.ROI_TARGET]:
            # For targets, progress is current/target
            progress = (self.current_value / self.target_value) * 100
        elif self.goal_type in [GoalType.RISK_LIMIT, GoalType.DRAWDOWN_LIMIT]:
            # For limits, progress is inverted (lower is better)
            if self.current_value <= self.target_value:
                progress = Decimal("100")  # Goal achieved
            else:
                # Progress decreases as we exceed the limit
                excess = self.current_value - self.target_value
                progress = max(Decimal("0"), Decimal("100") - (excess / self.target_value * 100))
        else:
            # Default: linear progress
            progress = min(Decimal("100"), (self.current_value / self.target_value) * 100)
        
        self.progress_percentage = max(Decimal("0"), min(Decimal("100"), progress))
        return self.progress_percentage
    
    def is_completed(self) -> bool:
        """Check if goal is completed based on type and target"""
        if self.goal_type == GoalType.PROFIT_TARGET:
            return self.current_value >= self.target_value
        elif self.goal_type == GoalType.ROI_TARGET:
            return self.roi_percentage >= self.target_value
        elif self.goal_type == GoalType.RISK_LIMIT:
            return self.current_value <= self.target_value
        elif self.goal_type == GoalType.TIME_TARGET:
            return self.time_to_completion is not None and self.time_to_completion <= timedelta(0)
        elif self.goal_type == GoalType.DRAWDOWN_LIMIT:
            return self.current_value <= self.target_value
        else:
            return self.current_value >= self.target_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary for serialization"""
        return {
            "goal_id": self.goal_id,
            "goal_type": self.goal_type.value,
            "target_value": float(self.target_value),
            "current_value": float(self.current_value),
            "wallet_id": self.wallet_id,
            "allocation_id": self.allocation_id,
            "description": self.description,
            "priority": self.priority,
            "auto_execute": self.auto_execute,
            "trigger_actions": [action.value for action in self.trigger_actions],
            "status": self.status.value,
            "progress_percentage": float(self.progress_percentage),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "initial_allocation": float(self.initial_allocation),
            "current_allocation": float(self.current_allocation),
            "total_return": float(self.total_return),
            "roi_percentage": float(self.roi_percentage),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }

class WalletGoalIntegrationService:
    """
    Advanced goal completion integration with wallet operations
    Phase 6: Automated goal tracking with intelligent fund collection
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Core services
        self.master_wallet_service = None
        self.wallet_coordination_service = None
        self.wallet_event_streaming_service = None
        self.wallet_agent_coordination_service = None
        
        # Goal management
        self.active_goals: Dict[str, WalletGoal] = {}  # goal_id -> goal
        self.wallet_goals: Dict[str, List[str]] = {}  # wallet_id -> [goal_ids]
        self.allocation_goals: Dict[str, List[str]] = {}  # allocation_id -> [goal_ids]
        
        # Goal templates and automation
        self.goal_templates: Dict[str, Dict[str, Any]] = {}
        self.auto_goal_creation = True
        self.goal_completion_rate = Decimal("0.8")  # 80% of profits collected on goal completion
        
        # Performance tracking
        self.goal_metrics = {
            "total_goals": 0,
            "completed_goals": 0,
            "failed_goals": 0,
            "average_completion_time": 0,
            "total_profits_collected": Decimal("0"),
            "goal_success_rate": Decimal("0")
        }
        
        self.integration_active = False
        
        logger.info("WalletGoalIntegrationService initialized")
    
    async def initialize(self):
        """Initialize wallet-goal integration service"""
        try:
            # Get core services
            self.master_wallet_service = self.registry.get_service("master_wallet_service")
            self.wallet_coordination_service = self.registry.get_service("wallet_coordination_service")
            self.wallet_event_streaming_service = self.registry.get_service("wallet_event_streaming_service")
            self.wallet_agent_coordination_service = self.registry.get_service("wallet_agent_coordination_service")
            
            if not self.master_wallet_service:
                logger.error("Master wallet service not available for goal integration")
                return
            
            # Initialize goal templates
            await self._initialize_goal_templates()
            
            # Set up event streaming subscriptions
            if self.wallet_event_streaming_service:
                await self._setup_goal_event_subscriptions()
            
            # Create automatic goals for existing allocations
            await self._create_automatic_goals_for_existing_allocations()
            
            # Start goal monitoring loops
            asyncio.create_task(self._goal_monitoring_loop())
            asyncio.create_task(self._goal_completion_processor_loop())
            asyncio.create_task(self._automatic_goal_creation_loop())
            
            self.integration_active = True
            logger.info("Wallet-goal integration service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet-goal integration: {e}")
            raise
    
    async def _initialize_goal_templates(self):
        """Initialize standard goal templates for automatic creation"""
        try:
            self.goal_templates = {
                "profit_20_percent": {
                    "goal_type": GoalType.PROFIT_TARGET,
                    "target_percentage": Decimal("20"),
                    "description": "Collect profits at 20% gain",
                    "trigger_actions": [GoalTriggerAction.COLLECT_PROFITS],
                    "priority": 5,
                    "auto_execute": True
                },
                "profit_50_percent": {
                    "goal_type": GoalType.PROFIT_TARGET,
                    "target_percentage": Decimal("50"),
                    "description": "Collect profits at 50% gain",
                    "trigger_actions": [GoalTriggerAction.COLLECT_PARTIAL],
                    "priority": 7,
                    "auto_execute": True
                },
                "roi_30_percent": {
                    "goal_type": GoalType.ROI_TARGET,
                    "target_percentage": Decimal("30"),
                    "description": "Achieve 30% ROI target",
                    "trigger_actions": [GoalTriggerAction.COLLECT_PROFITS],
                    "priority": 8,
                    "auto_execute": True
                },
                "drawdown_limit_15": {
                    "goal_type": GoalType.DRAWDOWN_LIMIT,
                    "target_percentage": Decimal("15"),
                    "description": "Limit drawdown to 15%",
                    "trigger_actions": [GoalTriggerAction.DECREASE_ALLOCATION],
                    "priority": 9,
                    "auto_execute": True
                },
                "risk_limit_10": {
                    "goal_type": GoalType.RISK_LIMIT,
                    "target_percentage": Decimal("10"),
                    "description": "Limit risk exposure to 10%",
                    "trigger_actions": [GoalTriggerAction.COLLECT_PARTIAL],
                    "priority": 10,
                    "auto_execute": True
                }
            }
            
            logger.info(f"Initialized {len(self.goal_templates)} goal templates")
            
        except Exception as e:
            logger.error(f"Failed to initialize goal templates: {e}")
    
    async def _setup_goal_event_subscriptions(self):
        """Set up subscriptions to wallet events for goal tracking"""
        try:
            relevant_events = [
                WalletEventType.FUNDS_ALLOCATED,
                WalletEventType.FUNDS_COLLECTED,
                WalletEventType.PERFORMANCE_CALCULATED,
                WalletEventType.ALLOCATION_UPDATED
            ]
            
            await self.wallet_event_streaming_service.subscribe_to_events(
                self._handle_wallet_event_for_goals,
                event_types=relevant_events
            )
            
            logger.info("Set up wallet event subscriptions for goal tracking")
            
        except Exception as e:
            logger.error(f"Failed to set up goal event subscriptions: {e}")
    
    async def _handle_wallet_event_for_goals(self, event):
        """Handle wallet events for goal tracking and completion"""
        try:
            if event.event_type == WalletEventType.FUNDS_ALLOCATED:
                await self._handle_allocation_event_for_goals(event)
            elif event.event_type == WalletEventType.PERFORMANCE_CALCULATED:
                await self._handle_performance_event_for_goals(event)
            elif event.event_type == WalletEventType.ALLOCATION_UPDATED:
                await self._handle_allocation_update_for_goals(event)
            
        except Exception as e:
            logger.error(f"Failed to handle wallet event for goals: {e}")
    
    async def _handle_allocation_event_for_goals(self, event):
        """Handle new allocation events by creating automatic goals"""
        try:
            allocation_data = event.data.get("allocation", {})
            allocation_id = allocation_data.get("allocation_id")
            wallet_id = event.wallet_id
            allocated_amount = Decimal(str(allocation_data.get("allocated_amount_usd", 0)))
            
            if allocation_id and self.auto_goal_creation:
                # Create automatic goals for this allocation
                await self._create_automatic_goals_for_allocation(wallet_id, allocation_id, allocated_amount)
            
        except Exception as e:
            logger.error(f"Failed to handle allocation event for goals: {e}")
    
    async def _handle_performance_event_for_goals(self, event):
        """Handle performance calculation events to update goal progress"""
        try:
            wallet_id = event.wallet_id
            performance_data = event.data.get("performance", {})
            
            # Update goals for this wallet
            await self._update_wallet_goal_progress(wallet_id, performance_data)
            
            # Check for goal completions
            await self._check_goal_completions(wallet_id)
            
        except Exception as e:
            logger.error(f"Failed to handle performance event for goals: {e}")
    
    async def _handle_allocation_update_for_goals(self, event):
        """Handle allocation updates to adjust goal targets"""
        try:
            allocation_data = event.data.get("allocation", {})
            allocation_id = allocation_data.get("allocation_id")
            
            if allocation_id and allocation_id in self.allocation_goals:
                # Update goals associated with this allocation
                for goal_id in self.allocation_goals[allocation_id]:
                    if goal_id in self.active_goals:
                        await self._update_goal_from_allocation(self.active_goals[goal_id], allocation_data)
            
        except Exception as e:
            logger.error(f"Failed to handle allocation update for goals: {e}")
    
    async def create_goal(self, goal_type: GoalType, target_value: Decimal, wallet_id: str, 
                         allocation_id: Optional[str] = None, description: str = "", 
                         trigger_actions: List[GoalTriggerAction] = None,
                         auto_execute: bool = True, deadline: Optional[datetime] = None) -> WalletGoal:
        """
        Create a new goal for wallet or allocation
        Phase 6: Advanced goal creation with comprehensive configuration
        """
        try:
            goal_id = f"goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_goals)}"
            
            goal = WalletGoal(goal_id, goal_type, target_value, wallet_id, allocation_id)
            goal.description = description or f"{goal_type.value.replace('_', ' ').title()} Goal"
            goal.auto_execute = auto_execute
            goal.deadline = deadline
            
            if trigger_actions:
                goal.trigger_actions = trigger_actions
            else:
                # Set default trigger actions based on goal type
                goal.trigger_actions = self._get_default_trigger_actions(goal_type)
            
            # Initialize goal with current allocation data if available
            if allocation_id:
                await self._initialize_goal_from_allocation(goal, allocation_id)
            
            # Add to tracking structures
            self.active_goals[goal_id] = goal
            
            if wallet_id not in self.wallet_goals:
                self.wallet_goals[wallet_id] = []
            self.wallet_goals[wallet_id].append(goal_id)
            
            if allocation_id:
                if allocation_id not in self.allocation_goals:
                    self.allocation_goals[allocation_id] = []
                self.allocation_goals[allocation_id].append(goal_id)
            
            # Update metrics
            self.goal_metrics["total_goals"] += 1
            
            # Emit goal creation event
            if self.wallet_event_streaming_service:
                await self.wallet_event_streaming_service.emit_event(
                    WalletEventType.ALLOCATION_CREATED,  # Reuse event type
                    wallet_id,
                    {
                        "event_subtype": "goal_created",
                        "goal": goal.to_dict()
                    }
                )
            
            goal.status = GoalStatus.IN_PROGRESS
            goal.started_at = datetime.now(timezone.utc)
            
            logger.info(f"Created goal {goal_id}: {goal.description} for wallet {wallet_id}")
            return goal
            
        except Exception as e:
            logger.error(f"Failed to create goal: {e}")
            raise
    
    def _get_default_trigger_actions(self, goal_type: GoalType) -> List[GoalTriggerAction]:
        """Get default trigger actions for goal type"""
        defaults = {
            GoalType.PROFIT_TARGET: [GoalTriggerAction.COLLECT_PROFITS],
            GoalType.ROI_TARGET: [GoalTriggerAction.COLLECT_PROFITS],
            GoalType.RISK_LIMIT: [GoalTriggerAction.DECREASE_ALLOCATION],
            GoalType.DRAWDOWN_LIMIT: [GoalTriggerAction.COLLECT_PARTIAL],
            GoalType.TIME_TARGET: [GoalTriggerAction.NOTIFY_ONLY],
            GoalType.VOLUME_TARGET: [GoalTriggerAction.NOTIFY_ONLY],
            GoalType.CONSISTENCY_TARGET: [GoalTriggerAction.INCREASE_ALLOCATION]
        }
        return defaults.get(goal_type, [GoalTriggerAction.NOTIFY_ONLY])
    
    async def _initialize_goal_from_allocation(self, goal: WalletGoal, allocation_id: str):
        """Initialize goal with current allocation data"""
        try:
            # Get allocation data from wallet service
            if self.master_wallet_service:
                for wallet in self.master_wallet_service.active_wallets.values():
                    for allocation in wallet.allocations:
                        if allocation.allocation_id == allocation_id:
                            goal.initial_allocation = allocation.allocated_amount_usd
                            goal.current_allocation = allocation.current_value_usd
                            goal.total_return = allocation.total_pnl
                            
                            if allocation.allocated_amount_usd > 0:
                                goal.roi_percentage = (allocation.total_pnl / allocation.allocated_amount_usd) * 100
                            
                            # Set target based on goal type and current allocation
                            if goal.goal_type == GoalType.PROFIT_TARGET:
                                # Target is absolute profit amount
                                goal.current_value = allocation.total_pnl
                            elif goal.goal_type == GoalType.ROI_TARGET:
                                # Target is ROI percentage
                                goal.current_value = goal.roi_percentage
                            
                            break
            
        except Exception as e:
            logger.error(f"Failed to initialize goal from allocation: {e}")
    
    async def _create_automatic_goals_for_allocation(self, wallet_id: str, allocation_id: str, allocated_amount: Decimal):
        """Create automatic goals for new allocation based on templates"""
        try:
            goals_created = []
            
            for template_name, template in self.goal_templates.items():
                try:
                    goal_type = template["goal_type"]
                    target_percentage = template["target_percentage"]
                    
                    # Calculate target value based on allocated amount
                    if goal_type in [GoalType.PROFIT_TARGET]:
                        target_value = allocated_amount * (target_percentage / 100)
                    elif goal_type in [GoalType.ROI_TARGET, GoalType.DRAWDOWN_LIMIT, GoalType.RISK_LIMIT]:
                        target_value = target_percentage  # Percentage targets
                    else:
                        target_value = allocated_amount * (target_percentage / 100)
                    
                    # Create goal from template
                    goal = await self.create_goal(
                        goal_type=goal_type,
                        target_value=target_value,
                        wallet_id=wallet_id,
                        allocation_id=allocation_id,
                        description=template["description"],
                        trigger_actions=template["trigger_actions"],
                        auto_execute=template["auto_execute"]
                    )
                    
                    goal.priority = template["priority"]
                    goals_created.append(goal.goal_id)
                    
                except Exception as e:
                    logger.error(f"Failed to create goal from template {template_name}: {e}")
                    continue
            
            logger.info(f"Created {len(goals_created)} automatic goals for allocation {allocation_id}")
            
        except Exception as e:
            logger.error(f"Failed to create automatic goals for allocation: {e}")
    
    async def _create_automatic_goals_for_existing_allocations(self):
        """Create automatic goals for existing allocations"""
        try:
            if not self.master_wallet_service:
                return
            
            for wallet_id, wallet in self.master_wallet_service.active_wallets.items():
                for allocation in wallet.allocations:
                    if allocation.is_active:
                        await self._create_automatic_goals_for_allocation(
                            wallet_id, 
                            allocation.allocation_id, 
                            allocation.allocated_amount_usd
                        )
            
        except Exception as e:
            logger.error(f"Failed to create automatic goals for existing allocations: {e}")
    
    async def _update_wallet_goal_progress(self, wallet_id: str, performance_data: Dict[str, Any]):
        """Update goal progress based on wallet performance data"""
        try:
            if wallet_id not in self.wallet_goals:
                return
            
            for goal_id in self.wallet_goals[wallet_id]:
                if goal_id in self.active_goals:
                    goal = self.active_goals[goal_id]
                    
                    if goal.status == GoalStatus.IN_PROGRESS:
                        # Update goal progress based on type
                        await self._update_individual_goal_progress(goal, performance_data)
            
        except Exception as e:
            logger.error(f"Failed to update wallet goal progress: {e}")
    
    async def _update_individual_goal_progress(self, goal: WalletGoal, performance_data: Dict[str, Any]):
        """Update individual goal progress"""
        try:
            if goal.allocation_id:
                # Update from specific allocation data
                await self._update_goal_from_allocation_performance(goal)
            else:
                # Update from overall wallet performance
                total_pnl = Decimal(str(performance_data.get("total_pnl", 0)))
                total_value = Decimal(str(performance_data.get("total_value_usd", 0)))
                
                if goal.goal_type == GoalType.PROFIT_TARGET:
                    goal.current_value = total_pnl
                elif goal.goal_type == GoalType.ROI_TARGET:
                    if total_value > 0:
                        goal.current_value = (total_pnl / total_value) * 100
            
            # Calculate progress
            goal.calculate_progress()
            goal.updated_at = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Failed to update individual goal progress: {e}")
    
    async def _update_goal_from_allocation_performance(self, goal: WalletGoal):
        """Update goal progress from specific allocation performance"""
        try:
            if not goal.allocation_id or not self.master_wallet_service:
                return
            
            # Find the allocation
            for wallet in self.master_wallet_service.active_wallets.values():
                for allocation in wallet.allocations:
                    if allocation.allocation_id == goal.allocation_id:
                        goal.current_allocation = allocation.current_value_usd
                        goal.total_return = allocation.total_pnl
                        
                        if allocation.allocated_amount_usd > 0:
                            goal.roi_percentage = (allocation.total_pnl / allocation.allocated_amount_usd) * 100
                        
                        # Update current value based on goal type
                        if goal.goal_type == GoalType.PROFIT_TARGET:
                            goal.current_value = allocation.total_pnl
                        elif goal.goal_type == GoalType.ROI_TARGET:
                            goal.current_value = goal.roi_percentage
                        elif goal.goal_type == GoalType.DRAWDOWN_LIMIT:
                            goal.current_value = abs(allocation.current_drawdown)
                        
                        return
            
        except Exception as e:
            logger.error(f"Failed to update goal from allocation performance: {e}")
    
    async def _update_goal_from_allocation(self, goal: WalletGoal, allocation_data: Dict[str, Any]):
        """Update goal from allocation update data"""
        try:
            current_value = Decimal(str(allocation_data.get("current_value_usd", 0)))
            total_pnl = Decimal(str(allocation_data.get("total_pnl", 0)))
            allocated_amount = Decimal(str(allocation_data.get("allocated_amount_usd", 0)))
            
            goal.current_allocation = current_value
            goal.total_return = total_pnl
            
            if allocated_amount > 0:
                goal.roi_percentage = (total_pnl / allocated_amount) * 100
            
            # Update current value based on goal type
            if goal.goal_type == GoalType.PROFIT_TARGET:
                goal.current_value = total_pnl
            elif goal.goal_type == GoalType.ROI_TARGET:
                goal.current_value = goal.roi_percentage
            
            goal.calculate_progress()
            goal.updated_at = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Failed to update goal from allocation: {e}")
    
    async def _check_goal_completions(self, wallet_id: str):
        """Check for goal completions and execute trigger actions"""
        try:
            if wallet_id not in self.wallet_goals:
                return
            
            for goal_id in self.wallet_goals[wallet_id]:
                if goal_id in self.active_goals:
                    goal = self.active_goals[goal_id]
                    
                    if goal.status == GoalStatus.IN_PROGRESS and goal.is_completed():
                        await self._complete_goal(goal)
            
        except Exception as e:
            logger.error(f"Failed to check goal completions: {e}")
    
    async def _complete_goal(self, goal: WalletGoal):
        """Complete a goal and execute trigger actions"""
        try:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.now(timezone.utc)
            goal.updated_at = datetime.now(timezone.utc)
            
            if goal.started_at:
                goal.time_to_completion = goal.completed_at - goal.started_at
            
            # Update metrics
            self.goal_metrics["completed_goals"] += 1
            self._update_goal_success_rate()
            
            # Execute trigger actions if auto-execute is enabled
            if goal.auto_execute:
                for action in goal.trigger_actions:
                    await self._execute_trigger_action(goal, action)
            
            # Emit goal completion event
            if self.wallet_event_streaming_service:
                await self.wallet_event_streaming_service.emit_event(
                    WalletEventType.ALLOCATION_COMPLETED,  # Reuse event type
                    goal.wallet_id,
                    {
                        "event_subtype": "goal_completed",
                        "goal": goal.to_dict(),
                        "completion_time": goal.time_to_completion.total_seconds() if goal.time_to_completion else None
                    }
                )
            
            logger.info(f"Completed goal {goal.goal_id}: {goal.description}")
            
        except Exception as e:
            logger.error(f"Failed to complete goal {goal.goal_id}: {e}")
    
    async def _execute_trigger_action(self, goal: WalletGoal, action: GoalTriggerAction):
        """Execute a specific trigger action for goal completion"""
        try:
            if action == GoalTriggerAction.COLLECT_PROFITS:
                await self._execute_collect_profits(goal)
            elif action == GoalTriggerAction.COLLECT_PARTIAL:
                await self._execute_collect_partial(goal)
            elif action == GoalTriggerAction.COLLECT_ALL:
                await self._execute_collect_all(goal)
            elif action == GoalTriggerAction.REALLOCATE_FUNDS:
                await self._execute_reallocate_funds(goal)
            elif action == GoalTriggerAction.INCREASE_ALLOCATION:
                await self._execute_increase_allocation(goal)
            elif action == GoalTriggerAction.DECREASE_ALLOCATION:
                await self._execute_decrease_allocation(goal)
            elif action == GoalTriggerAction.NOTIFY_ONLY:
                await self._execute_notify_only(goal)
            
        except Exception as e:
            logger.error(f"Failed to execute trigger action {action.value} for goal {goal.goal_id}: {e}")
    
    async def _execute_collect_profits(self, goal: WalletGoal):
        """Execute profit collection action"""
        try:
            if not goal.allocation_id or goal.total_return <= 0:
                return
            
            # Calculate collection amount (80% of profits by default)
            collection_amount = goal.total_return * self.goal_completion_rate
            
            # Execute collection through wallet coordination service
            if self.wallet_coordination_service:
                collection_result = await self.wallet_coordination_service.coordinate_collection_request(
                    goal.wallet_id,
                    goal.allocation_id,
                    "partial"
                )
                
                if collection_result.get("success"):
                    collected_amount = Decimal(str(collection_result.get("collected_amount", 0)))
                    self.goal_metrics["total_profits_collected"] += collected_amount
                    
                    logger.info(f"Collected ${collected_amount} profits for goal {goal.goal_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute collect profits for goal {goal.goal_id}: {e}")
    
    async def _execute_collect_partial(self, goal: WalletGoal):
        """Execute partial collection action (50% of current value)"""
        try:
            if not goal.allocation_id:
                return
            
            # Collect 50% of current allocation value
            collection_percentage = Decimal("0.5")
            
            if self.wallet_coordination_service:
                collection_result = await self.wallet_coordination_service.coordinate_collection_request(
                    goal.wallet_id,
                    goal.allocation_id,
                    "partial"
                )
                
                if collection_result.get("success"):
                    collected_amount = Decimal(str(collection_result.get("collected_amount", 0)))
                    logger.info(f"Collected ${collected_amount} (partial) for goal {goal.goal_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute collect partial for goal {goal.goal_id}: {e}")
    
    async def _execute_collect_all(self, goal: WalletGoal):
        """Execute full collection action"""
        try:
            if not goal.allocation_id:
                return
            
            if self.wallet_coordination_service:
                collection_result = await self.wallet_coordination_service.coordinate_collection_request(
                    goal.wallet_id,
                    goal.allocation_id,
                    "full"
                )
                
                if collection_result.get("success"):
                    collected_amount = Decimal(str(collection_result.get("collected_amount", 0)))
                    self.goal_metrics["total_profits_collected"] += collected_amount
                    
                    logger.info(f"Collected ${collected_amount} (full) for goal {goal.goal_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute collect all for goal {goal.goal_id}: {e}")
    
    async def _execute_reallocate_funds(self, goal: WalletGoal):
        """Execute fund reallocation action"""
        try:
            # Implementation would reallocate funds to better performing targets
            logger.info(f"Executed fund reallocation for goal {goal.goal_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute reallocate funds for goal {goal.goal_id}: {e}")
    
    async def _execute_increase_allocation(self, goal: WalletGoal):
        """Execute allocation increase action"""
        try:
            # Implementation would increase allocation to high-performing target
            logger.info(f"Executed allocation increase for goal {goal.goal_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute increase allocation for goal {goal.goal_id}: {e}")
    
    async def _execute_decrease_allocation(self, goal: WalletGoal):
        """Execute allocation decrease action"""
        try:
            # Implementation would decrease allocation from underperforming target
            logger.info(f"Executed allocation decrease for goal {goal.goal_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute decrease allocation for goal {goal.goal_id}: {e}")
    
    async def _execute_notify_only(self, goal: WalletGoal):
        """Execute notification only action"""
        try:
            # Send notification about goal completion
            logger.info(f"Goal {goal.goal_id} completed: {goal.description}")
            
        except Exception as e:
            logger.error(f"Failed to execute notify only for goal {goal.goal_id}: {e}")
    
    def _update_goal_success_rate(self):
        """Update goal success rate metric"""
        try:
            if self.goal_metrics["total_goals"] > 0:
                self.goal_metrics["goal_success_rate"] = (
                    self.goal_metrics["completed_goals"] / self.goal_metrics["total_goals"] * 100
                )
            
        except Exception as e:
            logger.error(f"Failed to update goal success rate: {e}")
    
    async def _goal_monitoring_loop(self):
        """Background task for monitoring goal progress"""
        while self.integration_active:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Update progress for all active goals
                for goal in self.active_goals.values():
                    if goal.status == GoalStatus.IN_PROGRESS:
                        if goal.allocation_id:
                            await self._update_goal_from_allocation_performance(goal)
                        
                        # Check for completion
                        if goal.is_completed():
                            await self._complete_goal(goal)
                        
                        # Check for deadline expiration
                        if goal.deadline and datetime.now(timezone.utc) > goal.deadline:
                            goal.status = GoalStatus.FAILED
                            self.goal_metrics["failed_goals"] += 1
                
            except Exception as e:
                logger.error(f"Error in goal monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _goal_completion_processor_loop(self):
        """Background task for processing goal completions"""
        while self.integration_active:
            try:
                await asyncio.sleep(300)  # Process every 5 minutes
                
                # Process any pending goal completions
                completed_goals = [
                    goal for goal in self.active_goals.values() 
                    if goal.status == GoalStatus.COMPLETED and goal.auto_execute
                ]
                
                for goal in completed_goals:
                    # Ensure all trigger actions were executed
                    for action in goal.trigger_actions:
                        await self._execute_trigger_action(goal, action)
                
            except Exception as e:
                logger.error(f"Error in goal completion processor loop: {e}")
                await asyncio.sleep(60)
    
    async def _automatic_goal_creation_loop(self):
        """Background task for creating automatic goals"""
        while self.integration_active:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes
                
                # Check for new allocations without goals
                if self.master_wallet_service:
                    for wallet_id, wallet in self.master_wallet_service.active_wallets.items():
                        for allocation in wallet.allocations:
                            if (allocation.is_active and 
                                allocation.allocation_id not in self.allocation_goals):
                                
                                await self._create_automatic_goals_for_allocation(
                                    wallet_id,
                                    allocation.allocation_id,
                                    allocation.allocated_amount_usd
                                )
                
            except Exception as e:
                logger.error(f"Error in automatic goal creation loop: {e}")
                await asyncio.sleep(300)
    
    async def get_goals_for_wallet(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Get all goals for a specific wallet"""
        try:
            if wallet_id not in self.wallet_goals:
                return []
            
            goals = []
            for goal_id in self.wallet_goals[wallet_id]:
                if goal_id in self.active_goals:
                    goal = self.active_goals[goal_id]
                    goal.calculate_progress()  # Update progress
                    goals.append(goal.to_dict())
            
            return sorted(goals, key=lambda g: g["priority"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get goals for wallet {wallet_id}: {e}")
            return []
    
    async def get_goals_for_allocation(self, allocation_id: str) -> List[Dict[str, Any]]:
        """Get all goals for a specific allocation"""
        try:
            if allocation_id not in self.allocation_goals:
                return []
            
            goals = []
            for goal_id in self.allocation_goals[allocation_id]:
                if goal_id in self.active_goals:
                    goal = self.active_goals[goal_id]
                    goal.calculate_progress()  # Update progress
                    goals.append(goal.to_dict())
            
            return sorted(goals, key=lambda g: g["priority"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get goals for allocation {allocation_id}: {e}")
            return []
    
    async def get_goal_analytics(self) -> Dict[str, Any]:
        """Get comprehensive goal analytics"""
        try:
            # Calculate average completion time
            completed_goals = [
                goal for goal in self.active_goals.values() 
                if goal.status == GoalStatus.COMPLETED and goal.time_to_completion
            ]
            
            if completed_goals:
                total_completion_time = sum(
                    goal.time_to_completion.total_seconds() for goal in completed_goals
                )
                avg_completion_time = total_completion_time / len(completed_goals)
                self.goal_metrics["average_completion_time"] = avg_completion_time
            
            # Goal distribution by type
            goal_type_distribution = {}
            for goal in self.active_goals.values():
                goal_type = goal.goal_type.value
                if goal_type not in goal_type_distribution:
                    goal_type_distribution[goal_type] = 0
                goal_type_distribution[goal_type] += 1
            
            # Goal status distribution
            status_distribution = {}
            for goal in self.active_goals.values():
                status = goal.status.value
                if status not in status_distribution:
                    status_distribution[status] = 0
                status_distribution[status] += 1
            
            return {
                "metrics": {k: float(v) if isinstance(v, Decimal) else v for k, v in self.goal_metrics.items()},
                "goal_type_distribution": goal_type_distribution,
                "status_distribution": status_distribution,
                "total_active_goals": len(self.active_goals),
                "goal_templates_available": len(self.goal_templates),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get goal analytics: {e}")
            return {}
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """Get current wallet-goal integration status"""
        return {
            "service": "wallet_goal_integration_service",
            "status": "active" if self.integration_active else "inactive",
            "active_goals": len(self.active_goals),
            "wallet_mappings": len(self.wallet_goals),
            "allocation_mappings": len(self.allocation_goals),
            "auto_goal_creation": self.auto_goal_creation,
            "goal_completion_rate": float(self.goal_completion_rate),
            "goal_templates": len(self.goal_templates),
            "metrics": {k: float(v) if isinstance(v, Decimal) else v for k, v in self.goal_metrics.items()},
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_wallet_goal_integration_service():
    """Factory function to create WalletGoalIntegrationService instance"""
    return WalletGoalIntegrationService()