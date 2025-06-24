"""
Expert Agent Integration Service
Manages specialized expert agents with Trading Farm Brain memory integration
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, and_, or_, func
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from ..models.specialized_expert_agents import (
    ExpertAgentType, LearningPhase, DecisionConfidence,
    DarvasBoxExpert, ElliottWaveExpert, WilliamsAlligatorExpert, ADXExpert, RenkoExpert,
    ExpertAgentCoordinator, ExpertAgentDecision, AgentGoal, ExpertAgentPerformanceMetrics,
    AgentMemoryLayer
)

class ExpertAgentIntegrationService:
    """
    Comprehensive service for managing expert agents with Trading Farm Brain integration
    """
    
    def __init__(self, database_manager):
        self.db_manager = database_manager
        self.expert_coordinator = ExpertAgentCoordinator()
        self.active_agents: Dict[str, Union[DarvasBoxExpert, ElliottWaveExpert, WilliamsAlligatorExpert, ADXExpert, RenkoExpert]] = {}
        self.agent_goals: Dict[str, List[AgentGoal]] = {}
        self.performance_metrics: Dict[str, ExpertAgentPerformanceMetrics] = {}
        
        # Initialize expert agents
        self._initialize_expert_agents()
    
    def _initialize_expert_agents(self):
        """Initialize all expert agents"""
        
        # Create specialized expert agents
        self.darvas_expert = DarvasBoxExpert()
        self.elliott_expert = ElliottWaveExpert() 
        self.alligator_expert = WilliamsAlligatorExpert()
        self.adx_expert = ADXExpert()
        self.renko_expert = RenkoExpert()
        
        # Register agents with coordinator
        self.expert_coordinator.expert_agents = {
            self.darvas_expert.agent_id: self.darvas_expert,
            self.elliott_expert.agent_id: self.elliott_expert,
            self.alligator_expert.agent_id: self.alligator_expert,
            self.adx_expert.agent_id: self.adx_expert,
            self.renko_expert.agent_id: self.renko_expert
        }
        
        # Track active agents
        self.active_agents = self.expert_coordinator.expert_agents.copy()
        
        # Initialize performance metrics
        for agent_id, agent in self.active_agents.items():
            self.performance_metrics[agent_id] = ExpertAgentPerformanceMetrics(
                agent_id=agent_id,
                agent_type=agent.agent_type
            )
    
    async def create_expert_agent(self, agent_type: ExpertAgentType, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new expert agent with custom configuration"""
        
        try:
            # Create agent based on type
            if agent_type == ExpertAgentType.DARVAS_BOX:
                agent = DarvasBoxExpert(**config)
            elif agent_type == ExpertAgentType.ELLIOTT_WAVE:
                agent = ElliottWaveExpert(**config)
            elif agent_type == ExpertAgentType.WILLIAMS_ALLIGATOR:
                agent = WilliamsAlligatorExpert(**config)
            elif agent_type == ExpertAgentType.ADX:
                agent = ADXExpert(**config)
            elif agent_type == ExpertAgentType.RENKO:
                agent = RenkoExpert(**config)
            else:
                raise ValueError(f"Unsupported agent type: {agent_type}")
            
            # Register agent
            self.active_agents[agent.agent_id] = agent
            self.expert_coordinator.expert_agents[agent.agent_id] = agent
            
            # Initialize performance metrics
            self.performance_metrics[agent.agent_id] = ExpertAgentPerformanceMetrics(
                agent_id=agent.agent_id,
                agent_type=agent.agent_type
            )
            
            # Persist to Trading Farm Brain
            await self._persist_agent_to_brain(agent)
            
            return {
                "success": True,
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type.value,
                "message": f"Expert agent {agent.name} created successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create expert agent: {e}"
            }
    
    async def analyze_symbol(self, symbol: str, market_data: Dict[str, Any], agent_types: Optional[List[ExpertAgentType]] = None) -> Dict[str, Any]:
        """Get analysis from expert agents"""
        
        try:
            # Filter agents if specific types requested
            if agent_types:
                agents_to_use = {
                    agent_id: agent for agent_id, agent in self.active_agents.items()
                    if agent.agent_type in agent_types
                }
            else:
                agents_to_use = self.active_agents
            
            # Get individual expert analyses
            expert_analyses = {}
            for agent_id, agent in agents_to_use.items():
                try:
                    decision = agent.analyze_symbol(market_data)
                    expert_analyses[agent_id] = {
                        "agent_type": agent.agent_type.value,
                        "agent_name": agent.name,
                        "decision": decision.dict(),
                        "expertise_level": getattr(agent, 'expertise_level', 0.5)
                    }
                    
                    # Store decision in Trading Farm Brain
                    await self._persist_decision_to_brain(decision)
                    
                except Exception as e:
                    expert_analyses[agent_id] = {
                        "error": str(e),
                        "agent_type": agent.agent_type.value if hasattr(agent, 'agent_type') else "unknown"
                    }
            
            # Get coordinated analysis
            coordination_result = self.expert_coordinator.coordinate_analysis(symbol, market_data)
            
            # Store coordination result
            await self._persist_coordination_to_brain(coordination_result)
            
            return {
                "symbol": symbol,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "individual_analyses": expert_analyses,
                "coordinated_analysis": coordination_result,
                "total_experts": len(expert_analyses),
                "successful_analyses": len([a for a in expert_analyses.values() if "error" not in a])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to analyze symbol {symbol}: {e}"
            }
    
    async def assign_goal_to_agent(self, agent_id: str, goal_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assign a goal to an expert agent"""
        
        try:
            if agent_id not in self.active_agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            agent = self.active_agents[agent_id]
            
            # Create goal
            goal = AgentGoal(
                agent_id=agent_id,
                agent_type=agent.agent_type,
                **goal_config
            )
            
            # Add to agent goals
            if agent_id not in self.agent_goals:
                self.agent_goals[agent_id] = []
            self.agent_goals[agent_id].append(goal)
            
            # Persist to Trading Farm Brain
            await self._persist_goal_to_brain(goal)
            
            return {
                "success": True,
                "goal_id": goal.goal_id,
                "agent_id": agent_id,
                "goal_type": goal.goal_type,
                "target_value": goal.target_value,
                "message": f"Goal assigned to {agent.name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to assign goal: {e}"
            }
    
    async def update_agent_performance(self, agent_id: str, decision_correct: bool, trade_profitable: Optional[bool] = None) -> Dict[str, Any]:
        """Update agent performance metrics"""
        
        try:
            if agent_id not in self.performance_metrics:
                raise ValueError(f"Agent {agent_id} performance metrics not found")
            
            # Update metrics
            metrics = self.performance_metrics[agent_id]
            metrics.update_metrics(decision_correct, trade_profitable)
            
            # Update agent expertise level
            if agent_id in self.active_agents:
                agent = self.active_agents[agent_id]
                if hasattr(agent, 'expertise_level'):
                    agent.expertise_level = metrics.expertise_level
            
            # Check and update goals
            await self._check_goal_progress(agent_id, metrics)
            
            # Persist to Trading Farm Brain
            await self._persist_performance_to_brain(metrics)
            
            return {
                "success": True,
                "agent_id": agent_id,
                "accuracy_rate": metrics.accuracy_rate,
                "win_rate": metrics.win_rate,
                "expertise_level": metrics.expertise_level,
                "learning_velocity": metrics.learning_velocity
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to update performance: {e}"
            }
    
    async def get_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of expert agents"""
        
        try:
            if agent_id:
                # Get specific agent status
                if agent_id not in self.active_agents:
                    raise ValueError(f"Agent {agent_id} not found")
                
                agent = self.active_agents[agent_id]
                metrics = self.performance_metrics.get(agent_id)
                goals = self.agent_goals.get(agent_id, [])
                
                return {
                    "agent_id": agent_id,
                    "agent_type": agent.agent_type.value,
                    "name": agent.name,
                    "expertise_level": getattr(agent, 'expertise_level', 0.5),
                    "learning_phase": getattr(agent, 'learning_phase', LearningPhase.LEARNING).value,
                    "performance": metrics.dict() if metrics else None,
                    "active_goals": len([g for g in goals if g.is_active]),
                    "completed_goals": len([g for g in goals if g.is_completed])
                }
            else:
                # Get all agents status
                agents_status = {}
                for agent_id, agent in self.active_agents.items():
                    metrics = self.performance_metrics.get(agent_id)
                    goals = self.agent_goals.get(agent_id, [])
                    
                    agents_status[agent_id] = {
                        "agent_type": agent.agent_type.value,
                        "name": agent.name,
                        "expertise_level": getattr(agent, 'expertise_level', 0.5),
                        "learning_phase": getattr(agent, 'learning_phase', LearningPhase.LEARNING).value,
                        "accuracy_rate": metrics.accuracy_rate if metrics else 0.0,
                        "total_decisions": metrics.total_decisions if metrics else 0,
                        "active_goals": len([g for g in goals if g.is_active]),
                        "completed_goals": len([g for g in goals if g.is_completed])
                    }
                
                return {
                    "total_agents": len(self.active_agents),
                    "agents": agents_status,
                    "coordinator_status": {
                        "consensus_threshold": self.expert_coordinator.consensus_threshold,
                        "weight_by_performance": self.expert_coordinator.weight_by_performance
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get agent status: {e}"
            }
    
    async def trigger_learning_cycle(self, agent_id: str, learning_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a learning cycle for an agent"""
        
        try:
            if agent_id not in self.active_agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            agent = self.active_agents[agent_id]
            
            # Update agent memory
            if hasattr(agent, 'memory'):
                # Add to short-term memory
                agent.memory.short_term.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": learning_data,
                    "learning_type": "experience"
                })
                
                # Keep only last 100 experiences
                if len(agent.memory.short_term) > 100:
                    agent.memory.short_term = agent.memory.short_term[-100:]
                
                # Update medium-term patterns
                if "pattern" in learning_data:
                    pattern_key = learning_data["pattern"]["type"]
                    if pattern_key not in agent.memory.medium_term:
                        agent.memory.medium_term[pattern_key] = {"count": 0, "success_rate": 0.5}
                    
                    agent.memory.medium_term[pattern_key]["count"] += 1
                    if learning_data.get("success", False):
                        current_success = agent.memory.medium_term[pattern_key]["success_rate"]
                        count = agent.memory.medium_term[pattern_key]["count"]
                        agent.memory.medium_term[pattern_key]["success_rate"] = (current_success * (count - 1) + 1) / count
            
            # Update learning cycles
            if hasattr(agent, 'learning_cycles_completed'):
                agent.learning_cycles_completed += 1
            
            # Persist memory to Trading Farm Brain
            await self._persist_memory_to_brain(agent_id, agent.memory)
            
            return {
                "success": True,
                "agent_id": agent_id,
                "learning_cycles": getattr(agent, 'learning_cycles_completed', 0),
                "memory_size": len(agent.memory.short_term) if hasattr(agent, 'memory') else 0,
                "message": "Learning cycle completed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to trigger learning cycle: {e}"
            }
    
    async def optimize_agent_parameters(self, agent_id: str) -> Dict[str, Any]:
        """Optimize agent parameters based on performance"""
        
        try:
            if agent_id not in self.active_agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            agent = self.active_agents[agent_id]
            metrics = self.performance_metrics.get(agent_id)
            
            if not metrics:
                raise ValueError(f"No performance metrics found for agent {agent_id}")
            
            # Optimize based on agent type and performance
            optimization_result = {}
            
            if agent.agent_type == ExpertAgentType.DARVAS_BOX:
                optimization_result = await self._optimize_darvas_parameters(agent, metrics)
            elif agent.agent_type == ExpertAgentType.ELLIOTT_WAVE:
                optimization_result = await self._optimize_elliott_parameters(agent, metrics)
            elif agent.agent_type == ExpertAgentType.WILLIAMS_ALLIGATOR:
                optimization_result = await self._optimize_alligator_parameters(agent, metrics)
            elif agent.agent_type == ExpertAgentType.ADX:
                optimization_result = await self._optimize_adx_parameters(agent, metrics)
            elif agent.agent_type == ExpertAgentType.RENKO:
                optimization_result = await self._optimize_renko_parameters(agent, metrics)
            
            # Persist optimization to Trading Farm Brain
            await self._persist_optimization_to_brain(agent_id, optimization_result)
            
            return {
                "success": True,
                "agent_id": agent_id,
                "optimization_result": optimization_result,
                "message": "Agent parameters optimized"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to optimize agent: {e}"
            }
    
    # Trading Farm Brain Integration Methods
    
    async def _persist_agent_to_brain(self, agent: Union[DarvasBoxExpert, ElliottWaveExpert, WilliamsAlligatorExpert, ADXExpert, RenkoExpert]):
        """Persist agent configuration to Trading Farm Brain"""
        try:
            async with self.db_manager.get_session() as session:
                # Implementation would store agent data
                pass
        except Exception as e:
            print(f"Error persisting agent to brain: {e}")
    
    async def _persist_decision_to_brain(self, decision: ExpertAgentDecision):
        """Persist agent decision to Trading Farm Brain"""
        try:
            async with self.db_manager.get_session() as session:
                # Implementation would store decision data
                pass
        except Exception as e:
            print(f"Error persisting decision to brain: {e}")
    
    async def _persist_coordination_to_brain(self, coordination_result: Dict[str, Any]):
        """Persist coordination result to Trading Farm Brain"""
        try:
            async with self.db_manager.get_session() as session:
                # Implementation would store coordination data
                pass
        except Exception as e:
            print(f"Error persisting coordination to brain: {e}")
    
    async def _persist_goal_to_brain(self, goal: AgentGoal):
        """Persist agent goal to Trading Farm Brain"""
        try:
            async with self.db_manager.get_session() as session:
                # Implementation would store goal data
                pass
        except Exception as e:
            print(f"Error persisting goal to brain: {e}")
    
    async def _persist_performance_to_brain(self, metrics: ExpertAgentPerformanceMetrics):
        """Persist performance metrics to Trading Farm Brain"""
        try:
            async with self.db_manager.get_session() as session:
                # Implementation would store performance data
                pass
        except Exception as e:
            print(f"Error persisting performance to brain: {e}")
    
    async def _persist_memory_to_brain(self, agent_id: str, memory: AgentMemoryLayer):
        """Persist agent memory to Trading Farm Brain"""
        try:
            async with self.db_manager.get_session() as session:
                # Implementation would store memory data
                pass
        except Exception as e:
            print(f"Error persisting memory to brain: {e}")
    
    async def _persist_optimization_to_brain(self, agent_id: str, optimization_result: Dict[str, Any]):
        """Persist optimization result to Trading Farm Brain"""
        try:
            async with self.db_manager.get_session() as session:
                # Implementation would store optimization data
                pass
        except Exception as e:
            print(f"Error persisting optimization to brain: {e}")
    
    # Goal Management Methods
    
    async def _check_goal_progress(self, agent_id: str, metrics: ExpertAgentPerformanceMetrics):
        """Check and update goal progress"""
        if agent_id not in self.agent_goals:
            return
        
        for goal in self.agent_goals[agent_id]:
            if not goal.is_active:
                continue
            
            # Update goal based on type
            if goal.goal_type == "accuracy":
                goal.update_progress(metrics.accuracy_rate)
            elif goal.goal_type == "win_rate":
                goal.update_progress(metrics.win_rate)
            elif goal.goal_type == "learning_cycles":
                goal.update_progress(metrics.learning_cycles)
            elif goal.goal_type == "expertise_level":
                goal.update_progress(metrics.expertise_level)
    
    # Parameter Optimization Methods
    
    async def _optimize_darvas_parameters(self, agent: DarvasBoxExpert, metrics: ExpertAgentPerformanceMetrics) -> Dict[str, Any]:
        """Optimize Darvas Box agent parameters"""
        
        current_accuracy = metrics.accuracy_rate
        optimization_suggestions = []
        
        # Adjust consolidation period based on performance
        if current_accuracy < 0.6:
            optimization_suggestions.append({
                "parameter": "min_consolidation_days",
                "current": agent.box_formation_rules["min_consolidation_days"],
                "suggested": agent.box_formation_rules["min_consolidation_days"] + 1,
                "reason": "Increase consolidation period for higher quality signals"
            })
        
        # Adjust volume threshold
        if metrics.win_rate < 0.65:
            optimization_suggestions.append({
                "parameter": "volume_confirmation_threshold",
                "current": agent.volume_analysis_params["volume_confirmation_threshold"],
                "suggested": agent.volume_analysis_params["volume_confirmation_threshold"] * 1.1,
                "reason": "Increase volume threshold for stronger confirmation"
            })
        
        return {
            "optimization_type": "darvas_box",
            "current_accuracy": current_accuracy,
            "suggestions": optimization_suggestions,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _optimize_elliott_parameters(self, agent: ElliottWaveExpert, metrics: ExpertAgentPerformanceMetrics) -> Dict[str, Any]:
        """Optimize Elliott Wave agent parameters"""
        
        optimization_suggestions = []
        
        # Adjust wave count accuracy threshold
        if metrics.accuracy_rate < agent.wave_count_accuracy:
            optimization_suggestions.append({
                "parameter": "wave_count_accuracy",
                "current": agent.wave_count_accuracy,
                "suggested": agent.wave_count_accuracy * 0.95,
                "reason": "Lower accuracy threshold to increase signal frequency"
            })
        
        return {
            "optimization_type": "elliott_wave",
            "current_accuracy": metrics.accuracy_rate,
            "suggestions": optimization_suggestions,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _optimize_alligator_parameters(self, agent: WilliamsAlligatorExpert, metrics: ExpertAgentPerformanceMetrics) -> Dict[str, Any]:
        """Optimize Williams Alligator agent parameters"""
        
        optimization_suggestions = []
        
        # Adjust jaw period for trend sensitivity
        if metrics.accuracy_rate < 0.7:
            optimization_suggestions.append({
                "parameter": "jaw_period",
                "current": agent.alligator_params["jaw_period"],
                "suggested": agent.alligator_params["jaw_period"] + 2,
                "reason": "Increase jaw period for smoother trend detection"
            })
        
        return {
            "optimization_type": "williams_alligator",
            "current_accuracy": metrics.accuracy_rate,
            "suggestions": optimization_suggestions,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _optimize_adx_parameters(self, agent: ADXExpert, metrics: ExpertAgentPerformanceMetrics) -> Dict[str, Any]:
        """Optimize ADX agent parameters"""
        
        optimization_suggestions = []
        
        # Adjust trend threshold
        if metrics.win_rate < 0.7:
            optimization_suggestions.append({
                "parameter": "trend_threshold",
                "current": agent.adx_params["trend_threshold"],
                "suggested": agent.adx_params["trend_threshold"] + 5,
                "reason": "Increase trend threshold for stronger signals"
            })
        
        return {
            "optimization_type": "adx",
            "current_accuracy": metrics.accuracy_rate,
            "suggestions": optimization_suggestions,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _optimize_renko_parameters(self, agent: RenkoExpert, metrics: ExpertAgentPerformanceMetrics) -> Dict[str, Any]:
        """Optimize Renko agent parameters"""
        
        optimization_suggestions = []
        
        # Adjust ATR multiplier
        if metrics.accuracy_rate < 0.65:
            optimization_suggestions.append({
                "parameter": "atr_multiplier",
                "current": agent.renko_params["atr_multiplier"],
                "suggested": agent.renko_params["atr_multiplier"] * 1.1,
                "reason": "Increase ATR multiplier for larger brick size and cleaner signals"
            })
        
        return {
            "optimization_type": "renko",
            "current_accuracy": metrics.accuracy_rate,
            "suggestions": optimization_suggestions,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }