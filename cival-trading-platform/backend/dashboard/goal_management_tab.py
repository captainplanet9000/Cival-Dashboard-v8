"""
Phase 8: Goal Management Dashboard Tab
Enhanced dashboard integration with React components and AG-UI events
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json

from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class GoalManagementTab:
    """
    Goal Management Tab for the comprehensive dashboard
    Phase 8: Intelligent Goal Management with AG-UI Protocol integration
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Core services
        self.goal_service = None
        self.analytics_service = None
        self.wallet_service = None
        self.event_service = None
        
        # Tab configuration
        self.tab_id = "goal_management"
        self.tab_name = "🎯 Intelligent Goal Management"
        self.tab_order = 8
        self.is_active = False
        
        # Real-time data
        self.active_goals: List[Dict[str, Any]] = []
        self.recent_completions: List[Dict[str, Any]] = []
        self.analytics_summary: Dict[str, Any] = {}
        self.goal_templates: List[Dict[str, Any]] = []
        
        # UI state
        self.selected_timeframe = "last_30d"
        self.show_analytics = True
        self.show_completed = False
        self.goal_creation_mode = False
        
        logger.info("GoalManagementTab initialized")
    
    async def initialize(self):
        """Initialize goal management tab"""
        try:
            # Get required services
            self.goal_service = self.registry.get_service("intelligent_goal_service")
            self.analytics_service = self.registry.get_service("goal_analytics_service")
            self.wallet_service = self.registry.get_service("master_wallet_service")
            self.event_service = self.registry.get_service("wallet_event_streaming_service")
            
            if not self.goal_service:
                logger.warning("Intelligent goal service not available")
                return
            
            # Load initial data
            await self._load_initial_data()
            
            # Set up event subscriptions
            await self._setup_event_subscriptions()
            
            self.is_active = True
            logger.info("Goal management tab initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize goal management tab: {e}")
            raise
    
    async def _load_initial_data(self):
        """Load initial data for the tab"""
        try:
            # Load active goals
            if self.goal_service:
                goals = await self.goal_service.list_goals()
                self.active_goals = [self._format_goal_for_ui(goal) for goal in goals]
                
                # Separate completed goals
                self.recent_completions = [
                    goal for goal in self.active_goals 
                    if goal.get("status") == "completed"
                ][-10:]  # Last 10 completions
            
            # Load analytics summary
            if self.analytics_service:
                try:
                    report = await self.analytics_service.generate_analytics_report(
                        timeframe=self.selected_timeframe
                    )
                    self.analytics_summary = self._format_analytics_for_ui(report)
                except Exception as e:
                    logger.warning(f"Failed to load analytics: {e}")
                    self.analytics_summary = {}
            
            # Load goal templates
            self.goal_templates = self._get_goal_templates()
            
            logger.info(f"Loaded {len(self.active_goals)} goals and analytics data")
            
        except Exception as e:
            logger.error(f"Failed to load initial data: {e}")
    
    async def _setup_event_subscriptions(self):
        """Set up event subscriptions for real-time updates"""
        try:
            if not self.event_service:
                return
            
            # Subscribe to goal events
            relevant_events = [
                "goal.created",
                "goal.analyzed", 
                "goal.progress_updated",
                "goal.completed",
                "goal.optimization_suggested",
                "goal.cancelled"
            ]
            
            for event_type in relevant_events:
                await self.event_service.subscribe_to_events(
                    self._handle_goal_event,
                    event_types=[event_type]
                )
            
            # Subscribe to analytics events
            analytics_events = [
                "analytics.report_generated",
                "prediction.completed",
                "pattern.identified"
            ]
            
            for event_type in analytics_events:
                await self.event_service.subscribe_to_events(
                    self._handle_analytics_event,
                    event_types=[event_type]
                )
            
            logger.info("Set up event subscriptions for goal management tab")
            
        except Exception as e:
            logger.error(f"Failed to set up event subscriptions: {e}")
    
    async def _handle_goal_event(self, event):
        """Handle goal-related events"""
        try:
            event_type = event.event_type
            data = event.data
            
            if event_type == "goal.created":
                await self._handle_goal_created(data)
            elif event_type == "goal.progress_updated":
                await self._handle_goal_progress_updated(data)
            elif event_type == "goal.completed":
                await self._handle_goal_completed(data)
            elif event_type == "goal.cancelled":
                await self._handle_goal_cancelled(data)
            
        except Exception as e:
            logger.error(f"Failed to handle goal event: {e}")
    
    async def _handle_goal_created(self, data):
        """Handle goal creation event"""
        try:
            if "goal" in data:
                formatted_goal = self._format_goal_data(data["goal"])
                self.active_goals.append(formatted_goal)
                
                # Sort goals by priority and creation time
                self.active_goals.sort(
                    key=lambda g: (self._get_priority_score(g.get("priority", "medium")), g.get("created_at", "")),
                    reverse=True
                )
                
                logger.info(f"Added new goal: {formatted_goal.get('goal_id', 'unknown')}")
        
        except Exception as e:
            logger.error(f"Failed to handle goal created event: {e}")
    
    async def _handle_goal_progress_updated(self, data):
        """Handle goal progress update event"""
        try:
            if "goal" in data:
                updated_goal = self._format_goal_data(data["goal"])
                goal_id = updated_goal.get("goal_id")
                
                # Update existing goal
                for i, goal in enumerate(self.active_goals):
                    if goal.get("goal_id") == goal_id:
                        self.active_goals[i] = updated_goal
                        break
                
                logger.info(f"Updated goal progress: {goal_id}")
        
        except Exception as e:
            logger.error(f"Failed to handle goal progress update: {e}")
    
    async def _handle_goal_completed(self, data):
        """Handle goal completion event"""
        try:
            if "goal" in data:
                completed_goal = self._format_goal_data(data["goal"])
                goal_id = completed_goal.get("goal_id")
                
                # Update existing goal
                for i, goal in enumerate(self.active_goals):
                    if goal.get("goal_id") == goal_id:
                        self.active_goals[i] = completed_goal
                        break
                
                # Add to recent completions
                self.recent_completions.insert(0, completed_goal)
                self.recent_completions = self.recent_completions[:10]  # Keep last 10
                
                logger.info(f"Goal completed: {goal_id}")
        
        except Exception as e:
            logger.error(f"Failed to handle goal completion: {e}")
    
    async def _handle_goal_cancelled(self, data):
        """Handle goal cancellation event"""
        try:
            if "goal" in data:
                cancelled_goal = self._format_goal_data(data["goal"])
                goal_id = cancelled_goal.get("goal_id")
                
                # Update existing goal
                for i, goal in enumerate(self.active_goals):
                    if goal.get("goal_id") == goal_id:
                        self.active_goals[i] = cancelled_goal
                        break
                
                logger.info(f"Goal cancelled: {goal_id}")
        
        except Exception as e:
            logger.error(f"Failed to handle goal cancellation: {e}")
    
    async def _handle_analytics_event(self, event):
        """Handle analytics-related events"""
        try:
            event_type = event.event_type
            data = event.data
            
            if event_type == "analytics.report_generated":
                if data.get("timeframe") == self.selected_timeframe:
                    self.analytics_summary = self._format_analytics_data(data.get("report", {}))
            
        except Exception as e:
            logger.error(f"Failed to handle analytics event: {e}")
    
    def _format_goal_for_ui(self, goal) -> Dict[str, Any]:
        """Format goal data for UI display"""
        try:
            if hasattr(goal, 'to_dict'):
                goal_data = goal.to_dict()
            else:
                goal_data = goal
            
            return self._format_goal_data(goal_data)
            
        except Exception as e:
            logger.error(f"Failed to format goal for UI: {e}")
            return {}
    
    def _format_goal_data(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format goal data for consistent UI usage"""
        try:
            return {
                "goal_id": goal_data.get("goal_id", ""),
                "original_text": goal_data.get("original_text", ""),
                "parsed_objective": goal_data.get("parsed_objective", goal_data.get("original_text", "")),
                "priority": goal_data.get("priority", "medium"),
                "complexity": goal_data.get("complexity", "simple"),
                "status": goal_data.get("status", "pending"),
                "target_value": float(goal_data.get("target_value", 0)),
                "current_value": float(goal_data.get("current_value", 0)),
                "progress_percentage": float(goal_data.get("progress_percentage", 0)),
                "optimization_suggestions": goal_data.get("optimization_suggestions", []),
                "risk_assessment": goal_data.get("risk_assessment", {}),
                "learning_insights": goal_data.get("learning_insights", []),
                "estimated_completion": goal_data.get("estimated_completion"),
                "actual_start": goal_data.get("actual_start"),
                "actual_completion": goal_data.get("actual_completion"),
                "deadline": goal_data.get("deadline"),
                "created_at": goal_data.get("created_at", datetime.now(timezone.utc).isoformat()),
                "updated_at": goal_data.get("updated_at", datetime.now(timezone.utc).isoformat()),
                "wallet_id": goal_data.get("wallet_id"),
                "allocation_id": goal_data.get("allocation_id"),
                "metadata": goal_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to format goal data: {e}")
            return goal_data
    
    def _format_analytics_for_ui(self, report) -> Dict[str, Any]:
        """Format analytics report for UI display"""
        try:
            if hasattr(report, '__dict__'):
                # Convert dataclass to dict
                import dataclasses
                report_data = dataclasses.asdict(report)
            else:
                report_data = report
            
            return self._format_analytics_data(report_data)
            
        except Exception as e:
            logger.error(f"Failed to format analytics for UI: {e}")
            return {}
    
    def _format_analytics_data(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format analytics data for consistent UI usage"""
        try:
            return {
                "timeframe": report_data.get("timeframe", self.selected_timeframe),
                "total_goals": report_data.get("total_goals", 0),
                "completed_goals": report_data.get("completed_goals", 0),
                "failed_goals": report_data.get("failed_goals", 0),
                "cancelled_goals": report_data.get("cancelled_goals", 0),
                "in_progress_goals": report_data.get("in_progress_goals", 0),
                "overall_success_rate": float(report_data.get("overall_success_rate", 0)),
                "avg_completion_time": float(report_data.get("avg_completion_time", 0)),
                "median_completion_time": float(report_data.get("median_completion_time", 0)),
                "total_target_value": float(report_data.get("total_target_value", 0)),
                "total_achieved_value": float(report_data.get("total_achieved_value", 0)),
                "achievement_ratio": float(report_data.get("achievement_ratio", 0)),
                "goals_completed_on_time": report_data.get("goals_completed_on_time", 0),
                "goals_completed_early": report_data.get("goals_completed_early", 0),
                "goals_completed_late": report_data.get("goals_completed_late", 0),
                "avg_timeline_accuracy": float(report_data.get("avg_timeline_accuracy", 0)),
                "optimization_recommendations": report_data.get("optimization_recommendations", []),
                "risk_warnings": report_data.get("risk_warnings", []),
                "most_successful_patterns": report_data.get("most_successful_patterns", []),
                "emerging_patterns": report_data.get("emerging_patterns", []),
                "generated_at": report_data.get("generated_at", datetime.now(timezone.utc).isoformat())
            }
            
        except Exception as e:
            logger.error(f"Failed to format analytics data: {e}")
            return report_data
    
    def _get_goal_templates(self) -> List[Dict[str, Any]]:
        """Get goal templates for UI"""
        return [
            {
                "id": "profit_target",
                "name": "Profit Target",
                "description": "Set a specific profit amount to achieve",
                "icon": "DollarSign",
                "template": "Make ${{amount}} profit in {{timeframe}}",
                "category": "financial",
                "examples": [
                    "Make $1000 profit in 30 days",
                    "Make $5000 profit in 3 months",
                    "Make $500 profit this week"
                ]
            },
            {
                "id": "roi_target",
                "name": "ROI Target",
                "description": "Achieve a specific return on investment percentage",
                "icon": "TrendingUp",
                "template": "Achieve {{percentage}}% ROI in {{timeframe}}",
                "category": "performance",
                "examples": [
                    "Achieve 20% ROI in 60 days",
                    "Achieve 15% ROI this month",
                    "Achieve 30% ROI in 6 months"
                ]
            },
            {
                "id": "risk_control",
                "name": "Risk Control",
                "description": "Limit risk exposure or drawdown",
                "icon": "AlertTriangle",
                "template": "Limit {{risk_type}} to {{percentage}}%",
                "category": "risk",
                "examples": [
                    "Limit risk to 10%",
                    "Keep drawdown under 15%",
                    "Maintain 85% win rate"
                ]
            },
            {
                "id": "time_based",
                "name": "Time-based Goal",
                "description": "Complete an objective by a specific date",
                "icon": "Clock",
                "template": "{{objective}} by {{date}}",
                "category": "timeline",
                "examples": [
                    "Reach break-even by month end",
                    "Double account by year end",
                    "Achieve consistency in 90 days"
                ]
            },
            {
                "id": "strategy_performance",
                "name": "Strategy Performance",
                "description": "Optimize performance of specific trading strategies",
                "icon": "Brain",
                "template": "Improve {{strategy}} performance to {{target}}",
                "category": "strategy",
                "examples": [
                    "Improve breakout strategy win rate to 70%",
                    "Increase trend following profits by 25%",
                    "Optimize scalping strategy efficiency"
                ]
            }
        ]
    
    def _get_priority_score(self, priority: str) -> int:
        """Convert priority to numeric score for sorting"""
        priority_scores = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
            "background": 0
        }
        return priority_scores.get(priority.lower(), 2)
    
    async def get_tab_data(self) -> Dict[str, Any]:
        """Get complete tab data for rendering"""
        try:
            # Filter goals based on UI state
            active_goals = [
                goal for goal in self.active_goals 
                if goal.get("status") not in ["completed", "cancelled"] or self.show_completed
            ]
            
            # Get wallets for goal creation
            available_wallets = []
            if self.wallet_service:
                try:
                    wallets = await self.wallet_service.list_wallets()
                    available_wallets = [
                        {
                            "wallet_id": wallet.get("wallet_id", ""),
                            "name": wallet.get("name", "Unknown"),
                            "balance": wallet.get("total_balance_usd", 0)
                        }
                        for wallet in wallets
                    ]
                except Exception as e:
                    logger.warning(f"Failed to get wallets: {e}")
            
            return {
                "tab_id": self.tab_id,
                "tab_name": self.tab_name,
                "tab_order": self.tab_order,
                "is_active": self.is_active,
                
                # Goal data
                "goals": {
                    "active": active_goals,
                    "recent_completions": self.recent_completions,
                    "total_count": len(self.active_goals),
                    "active_count": len([g for g in self.active_goals if g.get("status") == "in_progress"]),
                    "completed_count": len([g for g in self.active_goals if g.get("status") == "completed"]),
                    "templates": self.goal_templates
                },
                
                # Analytics data
                "analytics": self.analytics_summary,
                
                # UI state
                "ui_state": {
                    "selected_timeframe": self.selected_timeframe,
                    "show_analytics": self.show_analytics,
                    "show_completed": self.show_completed,
                    "goal_creation_mode": self.goal_creation_mode
                },
                
                # Resources
                "resources": {
                    "available_wallets": available_wallets
                },
                
                # Meta information
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "services_status": {
                    "goal_service": self.goal_service is not None,
                    "analytics_service": self.analytics_service is not None,
                    "wallet_service": self.wallet_service is not None,
                    "event_service": self.event_service is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get tab data: {e}")
            return {
                "tab_id": self.tab_id,
                "tab_name": self.tab_name,
                "error": str(e),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
    
    async def handle_tab_action(self, action: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle tab-specific actions"""
        try:
            if action == "create_goal":
                return await self._handle_create_goal(data or {})
            
            elif action == "update_timeframe":
                return await self._handle_update_timeframe(data or {})
            
            elif action == "toggle_analytics":
                return await self._handle_toggle_analytics(data or {})
            
            elif action == "toggle_completed":
                return await self._handle_toggle_completed(data or {})
            
            elif action == "refresh_data":
                return await self._handle_refresh_data()
            
            elif action == "cancel_goal":
                return await self._handle_cancel_goal(data or {})
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Failed to handle tab action {action}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_create_goal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle goal creation action"""
        try:
            if not self.goal_service:
                return {"success": False, "error": "Goal service not available"}
            
            goal_text = data.get("goal_text", "")
            if not goal_text:
                return {"success": False, "error": "Goal text is required"}
            
            # Create goal through service
            goal = await self.goal_service.parse_natural_language_goal(
                goal_text,
                context={
                    "wallet_id": data.get("wallet_id"),
                    "allocation_id": data.get("allocation_id"),
                    "priority": data.get("priority", "medium"),
                    "deadline": data.get("deadline")
                }
            )
            
            return {
                "success": True,
                "goal_id": goal.goal_id,
                "message": "Goal created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create goal: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_update_timeframe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle timeframe update action"""
        try:
            new_timeframe = data.get("timeframe", "last_30d")
            self.selected_timeframe = new_timeframe
            
            # Refresh analytics with new timeframe
            if self.analytics_service:
                report = await self.analytics_service.generate_analytics_report(
                    timeframe=new_timeframe
                )
                self.analytics_summary = self._format_analytics_for_ui(report)
            
            return {
                "success": True,
                "timeframe": new_timeframe,
                "message": "Timeframe updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to update timeframe: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_toggle_analytics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analytics visibility toggle"""
        try:
            self.show_analytics = not self.show_analytics
            return {
                "success": True,
                "show_analytics": self.show_analytics,
                "message": f"Analytics {'shown' if self.show_analytics else 'hidden'}"
            }
            
        except Exception as e:
            logger.error(f"Failed to toggle analytics: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_toggle_completed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completed goals visibility toggle"""
        try:
            self.show_completed = not self.show_completed
            return {
                "success": True,
                "show_completed": self.show_completed,
                "message": f"Completed goals {'shown' if self.show_completed else 'hidden'}"
            }
            
        except Exception as e:
            logger.error(f"Failed to toggle completed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_refresh_data(self) -> Dict[str, Any]:
        """Handle data refresh action"""
        try:
            await self._load_initial_data()
            return {
                "success": True,
                "message": "Data refreshed successfully",
                "goals_count": len(self.active_goals),
                "analytics_updated": bool(self.analytics_summary)
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh data: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_cancel_goal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle goal cancellation action"""
        try:
            if not self.goal_service:
                return {"success": False, "error": "Goal service not available"}
            
            goal_id = data.get("goal_id", "")
            reason = data.get("reason", "User requested cancellation")
            
            if not goal_id:
                return {"success": False, "error": "Goal ID is required"}
            
            # Cancel goal through service
            success = await self.goal_service.cancel_goal(goal_id, reason)
            
            return {
                "success": success,
                "goal_id": goal_id,
                "message": "Goal cancelled successfully" if success else "Failed to cancel goal"
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel goal: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_tab_status(self) -> Dict[str, Any]:
        """Get tab status information"""
        return {
            "tab_id": self.tab_id,
            "tab_name": self.tab_name,
            "is_active": self.is_active,
            "services_connected": {
                "goal_service": self.goal_service is not None,
                "analytics_service": self.analytics_service is not None,
                "wallet_service": self.wallet_service is not None,
                "event_service": self.event_service is not None
            },
            "data_status": {
                "active_goals": len(self.active_goals),
                "recent_completions": len(self.recent_completions),
                "has_analytics": bool(self.analytics_summary),
                "goal_templates": len(self.goal_templates)
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

# Factory function for dashboard integration
def create_goal_management_tab():
    """Factory function to create GoalManagementTab instance"""
    return GoalManagementTab()