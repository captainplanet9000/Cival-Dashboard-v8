"""
Farm Management Service - Phase 7
Comprehensive farm coordination with MCP backend integration
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)

class FarmStatus(str, Enum):
    """Farm status enumeration"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    STOPPED = "stopped"
    ERROR = "error"

class FarmType(str, Enum):
    """Farm type enumeration"""
    MOMENTUM = "momentum"
    ARBITRAGE = "arbitrage"
    MEAN_REVERSION = "mean_reversion"
    MULTI_STRATEGY = "multi_strategy"
    DEFI_YIELD = "defi_yield"
    MARKET_MAKING = "market_making"

class AgentRole(str, Enum):
    """Agent role within farm"""
    LEADER = "leader"
    SPECIALIST = "specialist"
    WORKER = "worker"
    MONITOR = "monitor"

class FarmManagementService:
    """
    Comprehensive Farm Management Service
    Manages multi-agent farms with autonomous coordination and performance optimization
    """
    
    def __init__(self):
        self.farms: Dict[str, Any] = {}
        self.farm_agents: Dict[str, List[str]] = {}  # farm_id -> agent_ids
        self.agent_farms: Dict[str, str] = {}  # agent_id -> farm_id
        self.farm_performance: Dict[str, Any] = {}
        self.farm_coordination: Dict[str, Any] = {}
        self.active_strategies: Dict[str, Any] = {}
        
        # Performance tracking
        self.performance_cache: Dict[str, Any] = {}
        self.coordination_metrics: Dict[str, Any] = {}
        
        # Farm management settings
        self.auto_optimization_enabled = True
        self.performance_rebalance_threshold = Decimal('10')  # 10% performance deviation
        self.coordination_interval = 300  # 5 minutes
        self.health_check_interval = 60   # 1 minute
        
        logger.info("🏭 Farm Management Service initialized")
    
    async def initialize(self):
        """Initialize the farm management service"""
        # Start background tasks
        asyncio.create_task(self._farm_coordination_loop())
        asyncio.create_task(self._farm_performance_monitoring_loop())
        asyncio.create_task(self._farm_health_monitoring_loop())
        
        logger.info("✅ Farm Management Service ready")
    
    async def create_farm(self, farm_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new farming operation"""
        try:
            farm_id = f"farm_{uuid.uuid4().hex[:8]}"
            
            # Create farm configuration
            farm = {
                "id": farm_id,
                "name": farm_config.get("name", f"Farm {farm_id}"),
                "description": farm_config.get("description", ""),
                "farm_type": farm_config.get("farm_type", FarmType.MULTI_STRATEGY),
                "status": FarmStatus.INITIALIZING,
                
                # Farm configuration
                "max_agents": farm_config.get("max_agents", 8),
                "min_agents": farm_config.get("min_agents", 2),
                "target_agents": farm_config.get("target_agents", 4),
                "coordination_style": farm_config.get("coordination_style", "collaborative"),
                
                # Financial settings
                "initial_capital": Decimal(str(farm_config.get("initial_capital", 50000))),
                "capital_allocation_method": farm_config.get("capital_allocation_method", "performance_based"),
                "profit_sharing_model": farm_config.get("profit_sharing_model", "contribution_based"),
                
                # Risk management
                "farm_risk_limit": Decimal(str(farm_config.get("farm_risk_limit", 15))),  # 15% max loss
                "agent_risk_limit": Decimal(str(farm_config.get("agent_risk_limit", 5))),   # 5% per agent
                "daily_loss_limit": Decimal(str(farm_config.get("daily_loss_limit", 3))),   # 3% daily
                "stop_loss_enabled": farm_config.get("stop_loss_enabled", True),
                
                # Performance tracking
                "performance": {
                    "total_pnl": Decimal('0'),
                    "daily_pnl": Decimal('0'),
                    "weekly_pnl": Decimal('0'),
                    "monthly_pnl": Decimal('0'),
                    "roi": Decimal('0'),
                    "sharpe_ratio": Decimal('0'),
                    "win_rate": Decimal('0'),
                    "total_trades": 0,
                    "successful_trades": 0
                },
                
                # Coordination metrics
                "coordination": {
                    "efficiency_score": Decimal('0'),
                    "communication_score": Decimal('0'),
                    "collaboration_score": Decimal('0'),
                    "conflict_resolution_score": Decimal('0')
                },
                
                # Operational data
                "agents": [],
                "active_agents": 0,
                "strategies": [],
                "last_coordination": None,
                "last_rebalance": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Apply additional configuration if provided
            if "custom_config" in farm_config:
                for key, value in farm_config["custom_config"].items():
                    if key in farm:
                        farm[key] = value
            
            # Store farm
            self.farms[farm_id] = farm
            self.farm_agents[farm_id] = []
            
            # Initialize farm coordination
            self.farm_coordination[farm_id] = {
                "coordination_history": [],
                "active_decisions": {},
                "pending_actions": [],
                "communication_log": [],
                "performance_alerts": []
            }
            
            # Initialize performance tracking
            self.farm_performance[farm_id] = {
                "daily_snapshots": [],
                "weekly_reports": [],
                "monthly_reports": [],
                "benchmark_comparison": {},
                "risk_metrics": {}
            }
            
            logger.info(f"🏭 Created farm: {farm['name']} ({farm_type}) with target of {farm['target_agents']} agents")
            return farm
            
        except Exception as e:
            logger.error(f"❌ Failed to create farm: {e}")
            raise
    
    async def add_agent_to_farm(self, farm_id: str, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Add an agent to a farm"""
        try:
            if farm_id not in self.farms:
                raise ValueError(f"Farm {farm_id} not found")
            
            farm = self.farms[farm_id]
            
            # Check capacity
            if len(self.farm_agents[farm_id]) >= farm["max_agents"]:
                raise ValueError(f"Farm {farm_id} has reached maximum capacity")
            
            agent_id = agent_config.get("agent_id") or f"agent_{uuid.uuid4().hex[:8]}"
            
            # Create agent farm configuration
            agent_farm_config = {
                "agent_id": agent_id,
                "farm_id": farm_id,
                "agent_name": agent_config.get("name", f"Agent {agent_id}"),
                "role": agent_config.get("role", AgentRole.WORKER),
                "strategy": agent_config.get("strategy", "balanced"),
                "specialization": agent_config.get("specialization", "general"),
                
                # Resource allocation
                "allocated_capital": Decimal('0'),
                "capital_percentage": Decimal('0'),
                "max_position_size": Decimal(str(agent_config.get("max_position_size", 5000))),
                "leverage": Decimal(str(agent_config.get("leverage", 1))),
                
                # Performance tracking
                "performance": {
                    "total_pnl": Decimal('0'),
                    "daily_pnl": Decimal('0'),
                    "roi": Decimal('0'),
                    "trades_today": 0,
                    "successful_trades": 0,
                    "win_rate": Decimal('0'),
                    "avg_trade_size": Decimal('0'),
                    "risk_score": Decimal('0')
                },
                
                # Farm participation
                "coordination_score": Decimal('0'),
                "communication_activity": 0,
                "collaboration_rating": Decimal('0'),
                "leadership_score": Decimal('0'),
                
                # Status
                "status": "active",
                "last_activity": datetime.utcnow(),
                "join_date": datetime.utcnow(),
                "total_farm_time": timedelta(0)
            }
            
            # Add agent to farm
            self.farm_agents[farm_id].append(agent_id)
            self.agent_farms[agent_id] = farm_id
            farm["agents"].append(agent_farm_config)
            farm["active_agents"] += 1
            farm["updated_at"] = datetime.utcnow()
            
            # Allocate initial capital
            await self._allocate_capital_to_agent(farm_id, agent_id)
            
            # Update farm status if needed
            if farm["status"] == FarmStatus.INITIALIZING and farm["active_agents"] >= farm["min_agents"]:
                farm["status"] = FarmStatus.ACTIVE
                await self._start_farm_operations(farm_id)
            
            logger.info(f"🤖 Added agent {agent_id} to farm {farm_id} with role {agent_farm_config['role']}")
            return agent_farm_config
            
        except Exception as e:
            logger.error(f"❌ Failed to add agent to farm: {e}")
            raise
    
    async def coordinate_farm_decision(self, farm_id: str, decision_context: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate a farm-level decision among agents"""
        try:
            if farm_id not in self.farms:
                raise ValueError(f"Farm {farm_id} not found")
            
            farm = self.farms[farm_id]
            coordination = self.farm_coordination[farm_id]
            
            decision_id = f"decision_{uuid.uuid4().hex[:8]}"
            
            # Create decision coordination
            decision = {
                "id": decision_id,
                "farm_id": farm_id,
                "decision_type": decision_context.get("type", "general"),
                "priority": decision_context.get("priority", "normal"),
                "context": decision_context,
                
                # Participants
                "participating_agents": [],
                "required_roles": decision_context.get("required_roles", []),
                "minimum_participants": decision_context.get("minimum_participants", 2),
                
                # Decision process
                "coordination_style": farm.get("coordination_style", "collaborative"),
                "decision_method": decision_context.get("decision_method", "consensus"),
                "timeout": decision_context.get("timeout", 300),  # 5 minutes
                
                # Responses
                "agent_responses": {},
                "consensus_reached": False,
                "final_decision": None,
                
                # Timing
                "created_at": datetime.utcnow(),
                "started_at": None,
                "completed_at": None,
                "status": "pending"
            }
            
            # Get eligible agents
            eligible_agents = await self._get_eligible_agents(farm_id, decision["required_roles"])
            decision["participating_agents"] = eligible_agents
            
            if len(eligible_agents) < decision["minimum_participants"]:
                raise ValueError(f"Not enough eligible agents for decision (need {decision['minimum_participants']}, have {len(eligible_agents)})")
            
            # Execute coordination based on style
            if decision["coordination_style"] == "hierarchical":
                result = await self._hierarchical_decision(decision)
            elif decision["coordination_style"] == "consensus":
                result = await self._consensus_decision(decision)
            elif decision["coordination_style"] == "collaborative":
                result = await self._collaborative_decision(decision)
            else:
                result = await self._default_decision(decision)
            
            # Store decision
            coordination["coordination_history"].append(decision)
            farm["last_coordination"] = datetime.utcnow()
            
            # Update coordination metrics
            await self._update_coordination_metrics(farm_id, decision)
            
            logger.info(f"🤝 Coordinated farm decision {decision_id} for farm {farm_id}: {result.get('decision_summary', 'No summary')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to coordinate farm decision: {e}")
            raise
    
    async def optimize_farm_performance(self, farm_id: str) -> Dict[str, Any]:
        """Optimize farm performance through agent reallocation and strategy adjustment"""
        try:
            if farm_id not in self.farms:
                raise ValueError(f"Farm {farm_id} not found")
            
            farm = self.farms[farm_id]
            
            optimization_id = f"opt_{uuid.uuid4().hex[:8]}"
            
            # Analyze current performance
            performance_analysis = await self._analyze_farm_performance(farm_id)
            
            # Identify optimization opportunities
            opportunities = await self._identify_optimization_opportunities(farm_id, performance_analysis)
            
            # Create optimization plan
            optimization_plan = {
                "id": optimization_id,
                "farm_id": farm_id,
                "triggered_by": "performance_analysis",
                "analysis": performance_analysis,
                "opportunities": opportunities,
                "planned_actions": [],
                "executed_actions": [],
                "expected_improvement": Decimal('0'),
                "created_at": datetime.utcnow()
            }
            
            # Generate optimization actions
            if opportunities.get("capital_reallocation", False):
                reallocation_action = await self._generate_capital_reallocation_plan(farm_id)
                optimization_plan["planned_actions"].append(reallocation_action)
            
            if opportunities.get("agent_role_adjustment", False):
                role_adjustment_action = await self._generate_role_adjustment_plan(farm_id)
                optimization_plan["planned_actions"].append(role_adjustment_action)
            
            if opportunities.get("strategy_optimization", False):
                strategy_action = await self._generate_strategy_optimization_plan(farm_id)
                optimization_plan["planned_actions"].append(strategy_action)
            
            # Execute optimization actions
            total_improvement = Decimal('0')
            for action in optimization_plan["planned_actions"]:
                try:
                    execution_result = await self._execute_optimization_action(farm_id, action)
                    optimization_plan["executed_actions"].append(execution_result)
                    total_improvement += execution_result.get("improvement_estimate", Decimal('0'))
                except Exception as e:
                    logger.error(f"❌ Failed to execute optimization action: {e}")
                    action["execution_error"] = str(e)
            
            optimization_plan["actual_improvement"] = total_improvement
            optimization_plan["completed_at"] = datetime.utcnow()
            
            # Update farm
            farm["last_optimization"] = datetime.utcnow()
            farm["updated_at"] = datetime.utcnow()
            
            logger.info(f"⚡ Optimized farm {farm_id}: {len(optimization_plan['executed_actions'])} actions executed, {total_improvement}% estimated improvement")
            return optimization_plan
            
        except Exception as e:
            logger.error(f"❌ Failed to optimize farm performance: {e}")
            raise
    
    async def get_farm_analytics(self, farm_id: str) -> Dict[str, Any]:
        """Get comprehensive farm analytics"""
        try:
            if farm_id not in self.farms:
                raise ValueError(f"Farm {farm_id} not found")
            
            farm = self.farms[farm_id]
            coordination = self.farm_coordination[farm_id]
            performance = self.farm_performance[farm_id]
            
            # Calculate farm-level metrics
            total_capital = farm["initial_capital"]
            total_pnl = farm["performance"]["total_pnl"]
            roi = (total_pnl / total_capital * 100) if total_capital > 0 else Decimal('0')
            
            # Agent analytics
            agent_analytics = {}
            for agent_config in farm["agents"]:
                agent_id = agent_config["agent_id"]
                agent_analytics[agent_id] = {
                    "name": agent_config["agent_name"],
                    "role": agent_config["role"],
                    "specialization": agent_config["specialization"],
                    "capital_allocated": agent_config["allocated_capital"],
                    "performance": agent_config["performance"],
                    "coordination_score": agent_config["coordination_score"],
                    "status": agent_config["status"]
                }
            
            # Coordination analytics
            coordination_analytics = {
                "total_decisions": len(coordination["coordination_history"]),
                "successful_decisions": len([d for d in coordination["coordination_history"] if d.get("consensus_reached", False)]),
                "avg_decision_time": self._calculate_avg_decision_time(coordination["coordination_history"]),
                "communication_frequency": len(coordination["communication_log"]),
                "active_conflicts": len([d for d in coordination["coordination_history"] if d.get("status") == "conflict"]),
                "efficiency_score": farm["coordination"]["efficiency_score"]
            }
            
            # Performance analytics
            performance_analytics = {
                "current_performance": farm["performance"],
                "historical_snapshots": performance["daily_snapshots"][-30:],  # Last 30 days
                "benchmark_comparison": performance["benchmark_comparison"],
                "risk_metrics": performance["risk_metrics"],
                "trend_analysis": await self._calculate_performance_trends(farm_id)
            }
            
            # Risk analytics
            risk_analytics = await self._calculate_farm_risk_metrics(farm_id)
            
            return {
                "farm_overview": {
                    "id": farm_id,
                    "name": farm["name"],
                    "type": farm["farm_type"],
                    "status": farm["status"],
                    "agent_count": farm["active_agents"],
                    "capital": total_capital,
                    "current_value": total_capital + total_pnl,
                    "roi": roi,
                    "created_at": farm["created_at"],
                    "uptime": (datetime.utcnow() - farm["created_at"]).total_seconds() / 3600  # hours
                },
                "agents": agent_analytics,
                "coordination": coordination_analytics,
                "performance": performance_analytics,
                "risk": risk_analytics,
                "summary": {
                    "health_score": await self._calculate_farm_health_score(farm_id),
                    "efficiency_rating": farm["coordination"]["efficiency_score"],
                    "risk_rating": risk_analytics.get("overall_risk_score", 50),
                    "recommendation": await self._generate_farm_recommendation(farm_id)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get farm analytics: {e}")
            raise
    
    async def get_all_farms(self) -> List[Dict[str, Any]]:
        """Get all farms with summary information"""
        farm_summaries = []
        
        for farm_id, farm in self.farms.items():
            summary = {
                "id": farm_id,
                "name": farm["name"],
                "type": farm["farm_type"],
                "status": farm["status"],
                "agent_count": farm["active_agents"],
                "total_capital": farm["initial_capital"],
                "current_pnl": farm["performance"]["total_pnl"],
                "roi": farm["performance"]["roi"],
                "efficiency_score": farm["coordination"]["efficiency_score"],
                "created_at": farm["created_at"],
                "last_activity": farm["updated_at"]
            }
            farm_summaries.append(summary)
        
        return sorted(farm_summaries, key=lambda x: x["created_at"], reverse=True)
    
    # Private helper methods
    
    async def _allocate_capital_to_agent(self, farm_id: str, agent_id: str) -> Decimal:
        """Allocate capital to an agent based on farm strategy"""
        farm = self.farms[farm_id]
        agent_config = next((a for a in farm["agents"] if a["agent_id"] == agent_id), None)
        
        if not agent_config:
            raise ValueError(f"Agent {agent_id} not found in farm {farm_id}")
        
        # Calculate allocation based on method
        allocation_method = farm["capital_allocation_method"]
        
        if allocation_method == "equal":
            allocation = farm["initial_capital"] / farm["target_agents"]
        elif allocation_method == "performance_based":
            # Use historical performance or default for new agents
            performance_score = agent_config["performance"]["roi"] + Decimal('5')  # Base allocation
            allocation = farm["initial_capital"] * (performance_score / 100)
        elif allocation_method == "role_based":
            role_multipliers = {
                AgentRole.LEADER: Decimal('1.5'),
                AgentRole.SPECIALIST: Decimal('1.2'),
                AgentRole.WORKER: Decimal('1.0'),
                AgentRole.MONITOR: Decimal('0.8')
            }
            base_allocation = farm["initial_capital"] / farm["target_agents"]
            allocation = base_allocation * role_multipliers.get(agent_config["role"], Decimal('1.0'))
        else:
            allocation = farm["initial_capital"] / farm["target_agents"]  # Default to equal
        
        # Apply constraints
        max_allocation = farm["initial_capital"] * Decimal('0.3')  # Max 30% per agent
        allocation = min(allocation, max_allocation)
        
        # Update agent configuration
        agent_config["allocated_capital"] = allocation
        agent_config["capital_percentage"] = (allocation / farm["initial_capital"]) * 100
        
        return allocation
    
    async def _start_farm_operations(self, farm_id: str):
        """Start farm operations when minimum agents are reached"""
        farm = self.farms[farm_id]
        
        # Initialize farm strategies
        await self._initialize_farm_strategies(farm_id)
        
        # Start coordination processes
        await self._start_farm_coordination(farm_id)
        
        # Begin performance monitoring
        await self._start_performance_monitoring(farm_id)
        
        logger.info(f"🚀 Started operations for farm {farm_id}")
    
    async def _get_eligible_agents(self, farm_id: str, required_roles: List[str]) -> List[str]:
        """Get agents eligible for a coordination decision"""
        if not required_roles:
            return self.farm_agents[farm_id]
        
        farm = self.farms[farm_id]
        eligible = []
        
        for agent_config in farm["agents"]:
            if agent_config["status"] == "active" and agent_config["role"] in required_roles:
                eligible.append(agent_config["agent_id"])
        
        return eligible
    
    async def _hierarchical_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hierarchical decision making"""
        # Mock implementation for hierarchy
        decision["status"] = "completed"
        decision["consensus_reached"] = True
        decision["final_decision"] = {"action": "approved", "method": "hierarchical"}
        decision["completed_at"] = datetime.utcnow()
        
        return {
            "decision_id": decision["id"],
            "method": "hierarchical",
            "result": "approved",
            "decision_summary": "Decision approved through hierarchical process"
        }
    
    async def _consensus_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute consensus-based decision making"""
        # Mock implementation for consensus
        decision["status"] = "completed"
        decision["consensus_reached"] = True
        decision["final_decision"] = {"action": "consensus_reached", "method": "consensus"}
        decision["completed_at"] = datetime.utcnow()
        
        return {
            "decision_id": decision["id"],
            "method": "consensus",
            "result": "consensus_reached",
            "decision_summary": "Consensus reached among participating agents"
        }
    
    async def _collaborative_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute collaborative decision making"""
        # Mock implementation for collaboration
        decision["status"] = "completed"
        decision["consensus_reached"] = True
        decision["final_decision"] = {"action": "collaborative_solution", "method": "collaborative"}
        decision["completed_at"] = datetime.utcnow()
        
        return {
            "decision_id": decision["id"],
            "method": "collaborative",
            "result": "collaborative_solution",
            "decision_summary": "Collaborative solution developed through agent interaction"
        }
    
    async def _default_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Default decision making fallback"""
        decision["status"] = "completed"
        decision["consensus_reached"] = True
        decision["final_decision"] = {"action": "default_approved", "method": "default"}
        decision["completed_at"] = datetime.utcnow()
        
        return {
            "decision_id": decision["id"],
            "method": "default",
            "result": "default_approved",
            "decision_summary": "Decision resolved using default method"
        }
    
    async def _analyze_farm_performance(self, farm_id: str) -> Dict[str, Any]:
        """Analyze farm performance for optimization"""
        farm = self.farms[farm_id]
        
        # Mock performance analysis
        return {
            "overall_performance": farm["performance"]["roi"],
            "agent_performance_variance": Decimal('5.2'),
            "coordination_efficiency": farm["coordination"]["efficiency_score"],
            "capital_utilization": Decimal('87.5'),
            "risk_adjusted_return": Decimal('12.3'),
            "benchmark_comparison": Decimal('3.1'),  # 3.1% above benchmark
            "improvement_potential": Decimal('8.7')   # 8.7% potential improvement
        }
    
    async def _identify_optimization_opportunities(self, farm_id: str, analysis: Dict[str, Any]) -> Dict[str, bool]:
        """Identify optimization opportunities"""
        return {
            "capital_reallocation": analysis["agent_performance_variance"] > Decimal('5'),
            "agent_role_adjustment": analysis["coordination_efficiency"] < Decimal('80'),
            "strategy_optimization": analysis["risk_adjusted_return"] < Decimal('15'),
            "performance_tuning": analysis["improvement_potential"] > Decimal('5')
        }
    
    async def _generate_capital_reallocation_plan(self, farm_id: str) -> Dict[str, Any]:
        """Generate capital reallocation plan"""
        return {
            "type": "capital_reallocation",
            "description": "Reallocate capital based on agent performance",
            "estimated_improvement": Decimal('3.2'),
            "risk_level": "low",
            "execution_time": "immediate"
        }
    
    async def _generate_role_adjustment_plan(self, farm_id: str) -> Dict[str, Any]:
        """Generate agent role adjustment plan"""
        return {
            "type": "role_adjustment",
            "description": "Adjust agent roles to improve coordination",
            "estimated_improvement": Decimal('2.8'),
            "risk_level": "medium",
            "execution_time": "gradual"
        }
    
    async def _generate_strategy_optimization_plan(self, farm_id: str) -> Dict[str, Any]:
        """Generate strategy optimization plan"""
        return {
            "type": "strategy_optimization",
            "description": "Optimize trading strategies for current market conditions",
            "estimated_improvement": Decimal('4.1'),
            "risk_level": "medium",
            "execution_time": "immediate"
        }
    
    async def _execute_optimization_action(self, farm_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an optimization action"""
        # Mock execution
        return {
            "action_type": action["type"],
            "status": "completed",
            "improvement_estimate": action["estimated_improvement"],
            "executed_at": datetime.utcnow(),
            "success": True
        }
    
    async def _calculate_avg_decision_time(self, decisions: List[Dict[str, Any]]) -> float:
        """Calculate average decision time"""
        completed_decisions = [
            d for d in decisions 
            if d.get("started_at") and d.get("completed_at")
        ]
        
        if not completed_decisions:
            return 0.0
        
        total_time = sum(
            (d["completed_at"] - d["started_at"]).total_seconds()
            for d in completed_decisions
        )
        
        return total_time / len(completed_decisions)
    
    async def _calculate_performance_trends(self, farm_id: str) -> Dict[str, Any]:
        """Calculate performance trends"""
        # Mock trend analysis
        return {
            "roi_trend": "increasing",
            "volatility_trend": "stable",
            "coordination_trend": "improving",
            "risk_trend": "decreasing"
        }
    
    async def _calculate_farm_risk_metrics(self, farm_id: str) -> Dict[str, Any]:
        """Calculate comprehensive farm risk metrics"""
        # Mock risk metrics
        return {
            "overall_risk_score": 35,  # Low-medium risk
            "value_at_risk": Decimal('2.1'),
            "maximum_drawdown": Decimal('4.8'),
            "concentration_risk": Decimal('15.2'),
            "correlation_risk": Decimal('8.7'),
            "liquidity_risk": Decimal('5.3')
        }
    
    async def _calculate_farm_health_score(self, farm_id: str) -> float:
        """Calculate overall farm health score"""
        farm = self.farms[farm_id]
        
        # Simple health calculation
        performance_score = min(float(abs(farm["performance"]["roi"])), 20) * 2.5  # Max 50 points
        coordination_score = min(float(farm["coordination"]["efficiency_score"]), 50)   # Max 50 points
        
        return min(performance_score + coordination_score, 100)
    
    async def _generate_farm_recommendation(self, farm_id: str) -> str:
        """Generate farm recommendation"""
        health_score = await self._calculate_farm_health_score(farm_id)
        
        if health_score >= 80:
            return "Farm performing excellently. Consider scaling operations."
        elif health_score >= 60:
            return "Farm performing well. Monitor for optimization opportunities."
        elif health_score >= 40:
            return "Farm performance acceptable. Consider agent rebalancing."
        else:
            return "Farm underperforming. Immediate optimization required."
    
    # Background task loops
    
    async def _farm_coordination_loop(self):
        """Background task for farm coordination"""
        while True:
            try:
                await asyncio.sleep(self.coordination_interval)
                
                for farm_id in self.farms.keys():
                    if self.farms[farm_id]["status"] == FarmStatus.ACTIVE:
                        await self._update_farm_coordination(farm_id)
                        
            except Exception as e:
                logger.error(f"❌ Farm coordination loop error: {e}")
    
    async def _farm_performance_monitoring_loop(self):
        """Background task for performance monitoring"""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                for farm_id in self.farms.keys():
                    if self.farms[farm_id]["status"] == FarmStatus.ACTIVE:
                        await self._update_farm_performance(farm_id)
                        
            except Exception as e:
                logger.error(f"❌ Farm performance monitoring error: {e}")
    
    async def _farm_health_monitoring_loop(self):
        """Background task for farm health monitoring"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                for farm_id in self.farms.keys():
                    await self._check_farm_health(farm_id)
                        
            except Exception as e:
                logger.error(f"❌ Farm health monitoring error: {e}")
    
    async def _update_farm_coordination(self, farm_id: str):
        """Update farm coordination metrics"""
        farm = self.farms[farm_id]
        
        # Mock coordination update
        farm["coordination"]["efficiency_score"] = min(
            farm["coordination"]["efficiency_score"] + Decimal('0.1'),
            Decimal('100')
        )
    
    async def _update_farm_performance(self, farm_id: str):
        """Update farm performance metrics"""
        farm = self.farms[farm_id]
        
        # Mock performance update
        daily_change = Decimal('0.05')  # 0.05% daily gain
        farm["performance"]["daily_pnl"] = farm["initial_capital"] * (daily_change / 100)
        farm["performance"]["total_pnl"] += farm["performance"]["daily_pnl"]
        farm["performance"]["roi"] = (farm["performance"]["total_pnl"] / farm["initial_capital"]) * 100
    
    async def _check_farm_health(self, farm_id: str):
        """Check farm health and status"""
        farm = self.farms[farm_id]
        
        # Check if farm needs attention
        if farm["performance"]["roi"] < Decimal('-10'):  # 10% loss
            logger.warning(f"⚠️ Farm {farm_id} has significant losses: {farm['performance']['roi']}%")
        
        # Update last activity
        farm["updated_at"] = datetime.utcnow()
    
    async def _initialize_farm_strategies(self, farm_id: str):
        """Initialize strategies for the farm"""
        # Mock strategy initialization
        pass
    
    async def _start_farm_coordination(self, farm_id: str):
        """Start coordination processes"""
        # Mock coordination start
        pass
    
    async def _start_performance_monitoring(self, farm_id: str):
        """Start performance monitoring"""
        # Mock monitoring start
        pass

# Service factory
def create_farm_management_service() -> FarmManagementService:
    """Create and configure farm management service"""
    return FarmManagementService()