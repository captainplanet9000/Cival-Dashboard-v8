"""
Agent Farm Coordination System
Central coordination system for HFT agent farms with real-time decision making
"""

import asyncio
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
import threading

# Agent and strategy imports
from ..strategies.hft.market_making_hft import MarketMakingHFTStrategy, PricingAgent, InventoryManagementAgent, RiskManagementAgent
from ..models.agent_models import AgentDecision, AgentRecommendation, AgentStatus
from ..models.trading_strategy_models import TradingSignal, SignalType


class AgentType(Enum):
    """Types of specialized agents"""
    PRICING = "pricing"
    INVENTORY = "inventory"
    RISK_MANAGEMENT = "risk_management"
    EXECUTION = "execution"
    MARKET_DATA = "market_data"
    COORDINATION = "coordination"
    PERFORMANCE = "performance"


class FarmStatus(Enum):
    """Agent farm operational status"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class AgentAllocation:
    """Agent allocation configuration"""
    agent_type: AgentType
    count: int
    cpu_allocation: float
    memory_allocation_mb: int
    priority: int
    specialized_config: Dict[str, Any]


@dataclass
class FarmConfiguration:
    """Agent farm configuration"""
    strategy_id: str
    strategy_type: str
    total_agents: int
    allocations: List[AgentAllocation]
    coordination_frequency_ms: int
    performance_target: Dict[str, float]
    risk_limits: Dict[str, float]


@dataclass
class CoordinationDecision:
    """Result of agent farm coordination"""
    decision_id: str
    strategy_id: str
    signal_type: SignalType
    confidence: float
    participating_agents: List[str]
    coordination_latency_ms: float
    decision_rationale: Dict[str, Any]
    execution_parameters: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    timestamp: datetime


@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for individual agents"""
    agent_id: str
    agent_type: AgentType
    response_time_ms: float
    accuracy_score: float
    recommendations_count: int
    successful_decisions: int
    failed_decisions: int
    uptime_percentage: float
    resource_usage: Dict[str, float]


class MessageBus:
    """High-performance message bus for agent communication"""
    
    def __init__(self):
        self.subscribers = {}
        self.message_queue = asyncio.Queue(maxsize=10000)
        self.processing_task = None
        
    async def start(self):
        """Start message bus processing"""
        self.processing_task = asyncio.create_task(self._process_messages())
        
    async def stop(self):
        """Stop message bus processing"""
        if self.processing_task:
            self.processing_task.cancel()
            
    def subscribe(self, topic: str, callback):
        """Subscribe to message topic"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)
        
    async def publish(self, topic: str, message: Dict[str, Any]):
        """Publish message to topic"""
        await self.message_queue.put({"topic": topic, "message": message})
        
    async def _process_messages(self):
        """Process messages from queue"""
        while True:
            try:
                msg_data = await self.message_queue.get()
                topic = msg_data["topic"]
                message = msg_data["message"]
                
                if topic in self.subscribers:
                    for callback in self.subscribers[topic]:
                        try:
                            await callback(message)
                        except Exception as e:
                            logger.error(f"Message processing error for topic {topic}: {e}")
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message bus processing error: {e}")


class AgentPerformanceMonitor:
    """Real-time agent performance monitoring"""
    
    def __init__(self):
        self.agent_metrics = {}
        self.performance_history = {}
        self.alert_thresholds = {
            "response_time_ms": 100,
            "accuracy_score": 0.7,
            "uptime_percentage": 0.95
        }
        
    async def record_agent_performance(self, agent_id: str, metrics: AgentPerformanceMetrics):
        """Record agent performance metrics"""
        
        self.agent_metrics[agent_id] = metrics
        
        if agent_id not in self.performance_history:
            self.performance_history[agent_id] = []
            
        self.performance_history[agent_id].append({
            "timestamp": datetime.now(timezone.utc),
            "metrics": metrics
        })
        
        # Keep only recent history
        if len(self.performance_history[agent_id]) > 1000:
            self.performance_history[agent_id] = self.performance_history[agent_id][-500:]
            
        # Check for performance issues
        await self._check_performance_alerts(agent_id, metrics)
        
    async def _check_performance_alerts(self, agent_id: str, metrics: AgentPerformanceMetrics):
        """Check for agent performance alerts"""
        
        alerts = []
        
        if metrics.response_time_ms > self.alert_thresholds["response_time_ms"]:
            alerts.append({
                "type": "high_latency",
                "agent_id": agent_id,
                "current_value": metrics.response_time_ms,
                "threshold": self.alert_thresholds["response_time_ms"]
            })
            
        if metrics.accuracy_score < self.alert_thresholds["accuracy_score"]:
            alerts.append({
                "type": "low_accuracy",
                "agent_id": agent_id,
                "current_value": metrics.accuracy_score,
                "threshold": self.alert_thresholds["accuracy_score"]
            })
            
        if metrics.uptime_percentage < self.alert_thresholds["uptime_percentage"]:
            alerts.append({
                "type": "low_uptime",
                "agent_id": agent_id,
                "current_value": metrics.uptime_percentage,
                "threshold": self.alert_thresholds["uptime_percentage"]
            })
            
        if alerts:
            logger.warning(f"Performance alerts for agent {agent_id}: {alerts}")
            
    def get_agent_performance_summary(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get performance summary for agent"""
        
        if agent_id not in self.performance_history:
            return None
            
        history = self.performance_history[agent_id]
        if not history:
            return None
            
        recent_metrics = [h["metrics"] for h in history[-100:]]  # Last 100 records
        
        return {
            "agent_id": agent_id,
            "avg_response_time_ms": np.mean([m.response_time_ms for m in recent_metrics]),
            "avg_accuracy_score": np.mean([m.accuracy_score for m in recent_metrics]),
            "avg_uptime_percentage": np.mean([m.uptime_percentage for m in recent_metrics]),
            "total_recommendations": sum([m.recommendations_count for m in recent_metrics]),
            "success_rate": np.mean([m.successful_decisions / max(1, m.successful_decisions + m.failed_decisions) for m in recent_metrics]),
            "last_updated": history[-1]["timestamp"].isoformat()
        }


class ResourceAllocator:
    """Dynamic resource allocation for agent farms"""
    
    def __init__(self):
        self.total_cpu_cores = 16  # Available CPU cores
        self.total_memory_gb = 64  # Available memory in GB
        self.allocation_strategy = "performance_optimized"
        
    async def calculate_optimal_allocation(self, strategy_config: Dict[str, Any]) -> Dict[AgentType, int]:
        """Calculate optimal agent allocation for strategy"""
        
        strategy_type = strategy_config.get("strategy_type", "unknown")
        performance_requirements = strategy_config.get("performance_requirements", {})
        
        if strategy_type == "market_making_hft":
            return await self._allocate_for_market_making(performance_requirements)
        elif strategy_type == "statistical_arbitrage_hft":
            return await self._allocate_for_stat_arb(performance_requirements)
        elif strategy_type == "momentum_ignition_hft":
            return await self._allocate_for_momentum(performance_requirements)
        else:
            return await self._allocate_default(performance_requirements)
            
    async def _allocate_for_market_making(self, requirements: Dict[str, Any]) -> Dict[AgentType, int]:
        """Allocate agents for market making strategy"""
        
        latency_target = requirements.get("latency_target_ms", 1.0)
        throughput_target = requirements.get("trades_per_second", 100)
        
        # Base allocation for market making
        allocation = {
            AgentType.PRICING: 2,  # Dual pricing agents for redundancy
            AgentType.INVENTORY: 1,  # Single inventory manager
            AgentType.RISK_MANAGEMENT: 1,  # Single risk manager
            AgentType.EXECUTION: 2,  # Dual execution for speed
            AgentType.MARKET_DATA: 2,  # Dual market data for reliability
            AgentType.COORDINATION: 1  # Single coordinator
        }
        
        # Adjust based on performance requirements
        if latency_target < 1.0:
            allocation[AgentType.EXECUTION] = 3  # More execution agents for ultra-low latency
            allocation[AgentType.PRICING] = 3  # More pricing agents
            
        if throughput_target > 1000:
            allocation[AgentType.MARKET_DATA] = 3  # More data agents for high throughput
            allocation[AgentType.COORDINATION] = 2  # Dual coordinators
            
        return allocation
        
    async def _allocate_for_stat_arb(self, requirements: Dict[str, Any]) -> Dict[AgentType, int]:
        """Allocate agents for statistical arbitrage"""
        
        return {
            AgentType.PRICING: 3,  # More pricing for multi-asset analysis
            AgentType.INVENTORY: 2,  # Multiple inventory managers for different assets
            AgentType.RISK_MANAGEMENT: 2,  # Enhanced risk management for correlation risk
            AgentType.EXECUTION: 3,  # Multiple execution for cross-asset trades
            AgentType.MARKET_DATA: 4,  # More data agents for multiple feeds
            AgentType.COORDINATION: 1
        }
        
    async def _allocate_for_momentum(self, requirements: Dict[str, Any]) -> Dict[AgentType, int]:
        """Allocate agents for momentum strategies"""
        
        return {
            AgentType.PRICING: 3,  # Enhanced pricing for momentum detection
            AgentType.INVENTORY: 1,  # Standard inventory management
            AgentType.RISK_MANAGEMENT: 2,  # Enhanced risk for momentum volatility
            AgentType.EXECUTION: 4,  # High execution capacity for momentum trades
            AgentType.MARKET_DATA: 3,  # Enhanced data processing
            AgentType.COORDINATION: 1
        }
        
    async def _allocate_default(self, requirements: Dict[str, Any]) -> Dict[AgentType, int]:
        """Default allocation for unknown strategies"""
        
        return {
            AgentType.PRICING: 2,
            AgentType.INVENTORY: 1,
            AgentType.RISK_MANAGEMENT: 1,
            AgentType.EXECUTION: 2,
            AgentType.MARKET_DATA: 2,
            AgentType.COORDINATION: 1
        }


class AgentFarmCoordinator:
    """
    Central coordination system for HFT agent farms
    """
    
    def __init__(self):
        self.strategy_farms = {}  # strategy_id -> farm_config
        self.agent_instances = {}  # agent_id -> agent_instance
        self.coordination_bus = MessageBus()
        self.performance_monitor = AgentPerformanceMonitor()
        self.resource_allocator = ResourceAllocator()
        
        # Coordination settings
        self.coordination_frequency_ms = 10  # 10ms coordination frequency
        self.max_coordination_latency_ms = 5  # Maximum allowed coordination latency
        
        # Background tasks
        self.coordination_tasks = {}
        self.monitoring_tasks = {}
        
        # Performance tracking
        self.coordination_metrics = {
            "total_decisions": 0,
            "successful_coordinations": 0,
            "failed_coordinations": 0,
            "avg_coordination_latency_ms": 0.0
        }
        
    async def initialize(self):
        """Initialize the agent farm coordinator"""
        
        try:
            await self.coordination_bus.start()
            logger.info("Agent farm coordinator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent farm coordinator: {e}")
            raise
            
    async def deploy_strategy_farm(self, strategy_id: str, strategy_config: Dict[str, Any]) -> FarmConfiguration:
        """Deploy a complete agent farm for a trading strategy"""
        
        try:
            logger.info(f"Deploying agent farm for strategy {strategy_id}")
            
            # Calculate optimal agent allocation
            agent_allocation = await self.resource_allocator.calculate_optimal_allocation(strategy_config)
            
            # Create farm configuration
            farm_config = FarmConfiguration(
                strategy_id=strategy_id,
                strategy_type=strategy_config.get("strategy_type", "unknown"),
                total_agents=sum(agent_allocation.values()),
                allocations=[
                    AgentAllocation(
                        agent_type=agent_type,
                        count=count,
                        cpu_allocation=1.0,  # 1 CPU per agent
                        memory_allocation_mb=512,  # 512MB per agent
                        priority=1,
                        specialized_config=strategy_config.get("agent_configs", {}).get(agent_type.value, {})
                    )
                    for agent_type, count in agent_allocation.items()
                ],
                coordination_frequency_ms=self.coordination_frequency_ms,
                performance_target=strategy_config.get("performance_target", {}),
                risk_limits=strategy_config.get("risk_limits", {})
            )
            
            # Deploy agents
            farm_agents = await self._deploy_farm_agents(farm_config)
            
            # Store farm configuration
            self.strategy_farms[strategy_id] = {
                "config": farm_config,
                "agents": farm_agents,
                "status": FarmStatus.ACTIVE,
                "deployed_at": datetime.now(timezone.utc)
            }
            
            # Start coordination for this farm
            await self._start_farm_coordination(strategy_id)
            
            logger.info(f"Successfully deployed agent farm for strategy {strategy_id} with {farm_config.total_agents} agents")
            return farm_config
            
        except Exception as e:
            logger.error(f"Failed to deploy agent farm for strategy {strategy_id}: {e}")
            raise
            
    async def _deploy_farm_agents(self, farm_config: FarmConfiguration) -> Dict[AgentType, List[Any]]:
        """Deploy individual agents for the farm"""
        
        farm_agents = {}
        
        for allocation in farm_config.allocations:
            agent_type = allocation.agent_type
            agent_count = allocation.count
            
            agents = []
            for i in range(agent_count):
                agent_id = f"{farm_config.strategy_id}_{agent_type.value}_{i}"
                
                # Create agent based on type
                agent = await self._create_agent(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    strategy_id=farm_config.strategy_id,
                    config=allocation.specialized_config
                )
                
                agents.append(agent)
                self.agent_instances[agent_id] = agent
                
            farm_agents[agent_type] = agents
            
        return farm_agents
        
    async def _create_agent(self, agent_id: str, agent_type: AgentType, strategy_id: str, config: Dict[str, Any]) -> Any:
        """Create specialized agent instance"""
        
        if agent_type == AgentType.PRICING:
            return PricingAgent(
                strategy_id=strategy_id,
                min_spread=config.get("min_spread", 0.0001),
                volatility_adjustment=config.get("volatility_adjustment", True)
            )
            
        elif agent_type == AgentType.INVENTORY:
            return InventoryManagementAgent(
                strategy_id=strategy_id,
                target_inventory=config.get("target_inventory", 0),
                max_position=config.get("max_position", 10000)
            )
            
        elif agent_type == AgentType.RISK_MANAGEMENT:
            return RiskManagementAgent(
                strategy_id=strategy_id,
                max_drawdown=config.get("max_drawdown", 0.02),
                stop_loss_multiplier=config.get("stop_loss_multiplier", 1.5)
            )
            
        elif agent_type == AgentType.EXECUTION:
            return ExecutionAgent(
                strategy_id=strategy_id,
                latency_target_ms=config.get("latency_target_ms", 1.0)
            )
            
        elif agent_type == AgentType.MARKET_DATA:
            return MarketDataAgent(
                strategy_id=strategy_id,
                update_frequency_ms=config.get("update_frequency_ms", 100)
            )
            
        elif agent_type == AgentType.COORDINATION:
            return CoordinationAgent(
                strategy_id=strategy_id,
                coordination_frequency_ms=config.get("coordination_frequency_ms", 10)
            )
            
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
    async def _start_farm_coordination(self, strategy_id: str):
        """Start coordination task for strategy farm"""
        
        coordination_task = asyncio.create_task(self._coordination_loop(strategy_id))
        self.coordination_tasks[strategy_id] = coordination_task
        
        monitoring_task = asyncio.create_task(self._monitoring_loop(strategy_id))
        self.monitoring_tasks[strategy_id] = monitoring_task
        
    async def _coordination_loop(self, strategy_id: str):
        """Main coordination loop for strategy farm"""
        
        while strategy_id in self.strategy_farms:
            try:
                start_time = datetime.now(timezone.utc)
                
                # Check if strategy farm is active
                farm_data = self.strategy_farms[strategy_id]
                if farm_data["status"] != FarmStatus.ACTIVE:
                    await asyncio.sleep(0.1)
                    continue
                
                # Coordinate agent decisions
                coordination_result = await self.coordinate_agent_decisions(strategy_id, {})
                
                # Calculate coordination latency
                coordination_latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                # Update metrics
                self.coordination_metrics["total_decisions"] += 1
                if coordination_result:
                    self.coordination_metrics["successful_coordinations"] += 1
                else:
                    self.coordination_metrics["failed_coordinations"] += 1
                    
                # Update average latency
                total_decisions = self.coordination_metrics["total_decisions"]
                current_avg = self.coordination_metrics["avg_coordination_latency_ms"]
                self.coordination_metrics["avg_coordination_latency_ms"] = (
                    (current_avg * (total_decisions - 1) + coordination_latency) / total_decisions
                )
                
                # Sleep until next coordination cycle
                sleep_time = max(0, (self.coordination_frequency_ms - coordination_latency) / 1000)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Coordination loop error for strategy {strategy_id}: {e}")
                await asyncio.sleep(0.1)
                
    async def _monitoring_loop(self, strategy_id: str):
        """Performance monitoring loop for strategy farm"""
        
        while strategy_id in self.strategy_farms:
            try:
                # Monitor agent performance
                farm_data = self.strategy_farms[strategy_id]
                
                for agent_type, agents in farm_data["agents"].items():
                    for agent in agents:
                        # Collect agent metrics (simplified)
                        metrics = AgentPerformanceMetrics(
                            agent_id=getattr(agent, 'strategy_id', f"unknown_{agent_type.value}"),
                            agent_type=agent_type,
                            response_time_ms=np.random.uniform(0.5, 5.0),  # Simulated for now
                            accuracy_score=np.random.uniform(0.8, 0.95),  # Simulated for now
                            recommendations_count=np.random.randint(10, 100),
                            successful_decisions=np.random.randint(8, 95),
                            failed_decisions=np.random.randint(0, 5),
                            uptime_percentage=np.random.uniform(0.95, 1.0),
                            resource_usage={"cpu": np.random.uniform(0.1, 0.8), "memory": np.random.uniform(0.2, 0.6)}
                        )
                        
                        await self.performance_monitor.record_agent_performance(
                            metrics.agent_id, metrics
                        )
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Monitoring loop error for strategy {strategy_id}: {e}")
                await asyncio.sleep(30)
                
    async def coordinate_agent_decisions(self, strategy_id: str, market_event: Dict[str, Any]) -> Optional[CoordinationDecision]:
        """Coordinate decisions across all agents in a strategy farm"""
        
        try:
            if strategy_id not in self.strategy_farms:
                return None
                
            start_time = datetime.now(timezone.utc)
            farm_data = self.strategy_farms[strategy_id]
            agents = farm_data["agents"]
            
            # Collect agent recommendations
            recommendations = {}
            participating_agents = []
            
            for agent_type, agent_list in agents.items():
                type_recommendations = []
                
                for agent in agent_list:
                    try:
                        # Get recommendation from agent (simplified for base implementation)
                        recommendation = await self._get_agent_recommendation(agent, agent_type, market_event)
                        if recommendation:
                            type_recommendations.append(recommendation)
                            participating_agents.append(getattr(agent, 'strategy_id', f"{agent_type.value}_agent"))
                    except Exception as e:
                        logger.error(f"Failed to get recommendation from {agent_type.value} agent: {e}")
                
                # Aggregate recommendations by type
                if type_recommendations:
                    recommendations[agent_type] = self._aggregate_agent_recommendations(type_recommendations)
            
            # Make coordinated decision
            coordinated_decision = await self._make_coordinated_decision(recommendations, strategy_id)
            
            # Calculate coordination latency
            coordination_latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            if coordinated_decision:
                decision = CoordinationDecision(
                    decision_id=str(uuid.uuid4()),
                    strategy_id=strategy_id,
                    signal_type=coordinated_decision["signal_type"],
                    confidence=coordinated_decision["confidence"],
                    participating_agents=participating_agents,
                    coordination_latency_ms=coordination_latency,
                    decision_rationale=coordinated_decision["rationale"],
                    execution_parameters=coordinated_decision["execution_params"],
                    risk_assessment=coordinated_decision["risk_assessment"],
                    timestamp=datetime.now(timezone.utc)
                )
                
                return decision
            
            return None
            
        except Exception as e:
            logger.error(f"Agent coordination failed for strategy {strategy_id}: {e}")
            return None
            
    async def _get_agent_recommendation(self, agent: Any, agent_type: AgentType, market_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get recommendation from individual agent"""
        
        # This is a simplified implementation
        # In a full implementation, each agent would have a standardized recommendation interface
        
        if agent_type == AgentType.PRICING:
            # Simulate pricing recommendation
            return {
                "signal": "BUY",
                "confidence": 0.8,
                "price_recommendation": 100.0,
                "spread_recommendation": 0.001
            }
        elif agent_type == AgentType.RISK_MANAGEMENT:
            # Simulate risk assessment
            return {
                "risk_level": 0.3,
                "position_limit": 1000,
                "stop_loss": 99.0
            }
        else:
            return {"status": "no_recommendation"}
            
    def _aggregate_agent_recommendations(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate recommendations from agents of the same type"""
        
        if not recommendations:
            return {}
            
        # Simple aggregation - in production this would be more sophisticated
        aggregated = {
            "count": len(recommendations),
            "recommendations": recommendations
        }
        
        # Try to aggregate numeric values
        numeric_keys = ["confidence", "risk_level", "price_recommendation"]
        for key in numeric_keys:
            values = [r.get(key) for r in recommendations if r.get(key) is not None]
            if values:
                aggregated[f"avg_{key}"] = np.mean(values)
                aggregated[f"max_{key}"] = np.max(values)
                aggregated[f"min_{key}"] = np.min(values)
                
        return aggregated
        
    async def _make_coordinated_decision(self, recommendations: Dict[AgentType, Dict], strategy_id: str) -> Optional[Dict[str, Any]]:
        """Make coordinated decision from agent recommendations"""
        
        if not recommendations:
            return None
            
        # Simple decision logic - in production this would be much more sophisticated
        risk_assessment = recommendations.get(AgentType.RISK_MANAGEMENT, {})
        pricing_recommendation = recommendations.get(AgentType.PRICING, {})
        
        # Check risk constraints
        avg_risk = risk_assessment.get("avg_risk_level", 0.5)
        if avg_risk > 0.8:
            return {
                "signal_type": SignalType.HOLD,
                "confidence": 0.9,
                "rationale": {"reason": "high_risk", "risk_level": avg_risk},
                "execution_params": {},
                "risk_assessment": risk_assessment
            }
        
        # Check pricing opportunity
        pricing_signal = pricing_recommendation.get("recommendations", [{}])[0].get("signal", "HOLD")
        pricing_confidence = pricing_recommendation.get("avg_confidence", 0.5)
        
        if pricing_signal == "BUY" and pricing_confidence > 0.7:
            return {
                "signal_type": SignalType.BUY,
                "confidence": pricing_confidence,
                "rationale": {"reason": "pricing_opportunity", "pricing_signal": pricing_signal},
                "execution_params": {
                    "price": pricing_recommendation.get("avg_price_recommendation", 100.0),
                    "quantity": 100
                },
                "risk_assessment": risk_assessment
            }
        elif pricing_signal == "SELL" and pricing_confidence > 0.7:
            return {
                "signal_type": SignalType.SELL,
                "confidence": pricing_confidence,
                "rationale": {"reason": "pricing_opportunity", "pricing_signal": pricing_signal},
                "execution_params": {
                    "price": pricing_recommendation.get("avg_price_recommendation", 100.0),
                    "quantity": 100
                },
                "risk_assessment": risk_assessment
            }
        
        return {
            "signal_type": SignalType.HOLD,
            "confidence": 0.5,
            "rationale": {"reason": "no_clear_opportunity"},
            "execution_params": {},
            "risk_assessment": risk_assessment
        }
        
    async def get_farm_status(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive status of strategy farm"""
        
        if strategy_id not in self.strategy_farms:
            return None
            
        farm_data = self.strategy_farms[strategy_id]
        config = farm_data["config"]
        
        # Agent status summary
        agent_status = {}
        for agent_type, agents in farm_data["agents"].items():
            agent_status[agent_type.value] = {
                "count": len(agents),
                "status": "active"  # Simplified
            }
        
        # Performance summary
        performance_summary = {}
        for agent_id in self.agent_instances:
            if agent_id.startswith(strategy_id):
                summary = self.performance_monitor.get_agent_performance_summary(agent_id)
                if summary:
                    performance_summary[agent_id] = summary
        
        return {
            "strategy_id": strategy_id,
            "farm_status": farm_data["status"].value,
            "total_agents": config.total_agents,
            "deployed_at": farm_data["deployed_at"].isoformat(),
            "agent_status": agent_status,
            "performance_summary": performance_summary,
            "coordination_metrics": self.coordination_metrics,
            "configuration": {
                "strategy_type": config.strategy_type,
                "coordination_frequency_ms": config.coordination_frequency_ms,
                "performance_target": config.performance_target,
                "risk_limits": config.risk_limits
            }
        }
        
    async def stop_strategy_farm(self, strategy_id: str):
        """Stop and cleanup strategy farm"""
        
        if strategy_id not in self.strategy_farms:
            return
            
        try:
            # Stop coordination tasks
            if strategy_id in self.coordination_tasks:
                self.coordination_tasks[strategy_id].cancel()
                del self.coordination_tasks[strategy_id]
                
            if strategy_id in self.monitoring_tasks:
                self.monitoring_tasks[strategy_id].cancel()
                del self.monitoring_tasks[strategy_id]
            
            # Clean up agent instances
            farm_data = self.strategy_farms[strategy_id]
            for agent_type, agents in farm_data["agents"].items():
                for agent in agents:
                    agent_id = getattr(agent, 'strategy_id', f"{strategy_id}_{agent_type.value}")
                    if agent_id in self.agent_instances:
                        del self.agent_instances[agent_id]
            
            # Update status
            self.strategy_farms[strategy_id]["status"] = FarmStatus.STOPPING
            
            # Remove farm
            del self.strategy_farms[strategy_id]
            
            logger.info(f"Successfully stopped strategy farm {strategy_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop strategy farm {strategy_id}: {e}")
            
    async def get_coordinator_status(self) -> Dict[str, Any]:
        """Get overall coordinator status"""
        
        return {
            "coordinator_status": "active",
            "active_farms": len(self.strategy_farms),
            "total_agents": len(self.agent_instances),
            "coordination_metrics": self.coordination_metrics,
            "active_strategies": list(self.strategy_farms.keys()),
            "resource_usage": {
                "coordination_tasks": len(self.coordination_tasks),
                "monitoring_tasks": len(self.monitoring_tasks)
            }
        }


# Simplified agent classes for coordination system
class ExecutionAgent:
    def __init__(self, strategy_id: str, latency_target_ms: float):
        self.strategy_id = strategy_id
        self.latency_target_ms = latency_target_ms


class MarketDataAgent:
    def __init__(self, strategy_id: str, update_frequency_ms: int):
        self.strategy_id = strategy_id
        self.update_frequency_ms = update_frequency_ms


class CoordinationAgent:
    def __init__(self, strategy_id: str, coordination_frequency_ms: int):
        self.strategy_id = strategy_id
        self.coordination_frequency_ms = coordination_frequency_ms


# Factory function for service registry
def create_agent_farm_coordinator() -> AgentFarmCoordinator:
    """Factory function to create agent farm coordinator"""
    return AgentFarmCoordinator()


# Example usage and configuration
EXAMPLE_FARM_DEPLOYMENT = {
    "strategy_type": "market_making_hft",
    "performance_requirements": {
        "latency_target_ms": 1.0,
        "trades_per_second": 500,
        "fill_rate_target": 0.95
    },
    "risk_limits": {
        "max_drawdown": 0.02,
        "max_position": 10000,
        "var_limit": 0.01
    },
    "agent_configs": {
        "pricing": {
            "min_spread": 0.0001,
            "volatility_adjustment": True
        },
        "inventory": {
            "target_inventory": 0,
            "max_position": 10000
        },
        "risk_management": {
            "max_drawdown": 0.02,
            "stop_loss_multiplier": 1.5
        }
    }
}