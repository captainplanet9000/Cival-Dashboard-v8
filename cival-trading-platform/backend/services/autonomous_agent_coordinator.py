"""
Phase 11: Autonomous Agent Coordinator
Advanced multi-agent coordination system with real-time decision making
Integrates LLM communication, goal management, and performance optimization
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid
from decimal import Decimal
import numpy as np

from ..core.service_registry import get_registry
from ..models.agent_models import (
    AutonomousAgent, AgentDecision, AgentPerformance,
    CoordinationTask, AgentCommunication, DecisionConsensus
)

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent status states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class DecisionType(Enum):
    """Types of agent decisions"""
    TRADING = "trading"
    RISK_MANAGEMENT = "risk_management"
    PORTFOLIO_ALLOCATION = "portfolio_allocation"
    GOAL_ADJUSTMENT = "goal_adjustment"
    STRATEGY_MODIFICATION = "strategy_modification"
    EMERGENCY_ACTION = "emergency_action"

class CoordinationMode(Enum):
    """Agent coordination modes"""
    INDEPENDENT = "independent"
    COLLABORATIVE = "collaborative"
    HIERARCHICAL = "hierarchical"
    CONSENSUS_REQUIRED = "consensus_required"
    EMERGENCY = "emergency"

@dataclass
class AgentConfiguration:
    """Agent configuration settings"""
    agent_id: str
    name: str
    agent_type: str
    trading_style: str
    risk_tolerance: float
    max_position_size: Decimal
    decision_confidence_threshold: float
    communication_enabled: bool
    autonomous_mode: bool
    performance_targets: Dict[str, float]
    constraints: Dict[str, Any]

@dataclass
class DecisionContext:
    """Context for agent decision making"""
    decision_id: str
    decision_type: DecisionType
    priority: int
    market_data: Dict[str, Any]
    portfolio_data: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    goal_progress: Dict[str, Any]
    agent_communications: List[Dict[str, Any]]
    time_constraints: Optional[datetime]
    coordination_mode: CoordinationMode

@dataclass
class ConsensusProcess:
    """Multi-agent consensus process"""
    consensus_id: str
    decision_context: DecisionContext
    participating_agents: List[str]
    agent_votes: Dict[str, Dict[str, Any]]
    required_agreement: float
    consensus_reached: bool
    final_decision: Optional[Dict[str, Any]]
    created_at: datetime
    deadline: Optional[datetime]

class AutonomousAgentCoordinator:
    """
    Advanced autonomous agent coordination system
    Phase 11: Real-time multi-agent decision making with LLM integration
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Service dependencies
        self.llm_service = None
        self.master_wallet_service = None
        self.goal_service = None
        self.market_data_service = None
        self.portfolio_service = None
        self.risk_service = None
        self.event_service = None
        
        # Agent management
        self.active_agents: Dict[str, AutonomousAgent] = {}
        self.agent_configurations: Dict[str, AgentConfiguration] = {}
        self.agent_performance: Dict[str, AgentPerformance] = {}
        
        # Decision coordination
        self.active_decisions: Dict[str, DecisionContext] = {}
        self.consensus_processes: Dict[str, ConsensusProcess] = {}
        self.decision_history: List[Dict[str, Any]] = []
        
        # Communication system
        self.message_queue: Dict[str, List[Dict[str, Any]]] = {}
        self.active_conversations: Set[str] = set()
        
        # Performance tracking
        self.coordination_metrics: Dict[str, Any] = {
            'decisions_per_hour': 0,
            'consensus_success_rate': 0.0,
            'avg_decision_time': 0.0,
            'agent_utilization': 0.0
        }
        
        # Real-time monitoring
        self.monitoring_enabled = True
        self.alert_thresholds = {
            'low_performance': 0.3,
            'high_risk': 0.8,
            'decision_timeout': 300  # 5 minutes
        }
        
        # Enhanced LLM Integration
        self.agent_llm_preferences = {
            "trend_follower_001": "marcus_trend_follower",
            "arbitrage_bot_003": "alex_arbitrage", 
            "mean_reversion_002": "sophia_mean_reversion",
            "risk_manager_004": "riley_risk_manager"
        }
        
        logger.info("AutonomousAgentCoordinator Phase 11 initialized with enhanced LLM integration")
    
    async def initialize(self):
        """Initialize the autonomous agent coordinator"""
        try:
            # Get required services
            self.llm_service = self.registry.get_service("llm_integration_service")
            self.master_wallet_service = self.registry.get_service("master_wallet_service")
            self.goal_service = self.registry.get_service("intelligent_goal_service")
            self.market_data_service = self.registry.get_service("market_data_service")
            self.portfolio_service = self.registry.get_service("portfolio_management_service")
            self.risk_service = self.registry.get_service("risk_management_service")
            self.event_service = self.registry.get_service("wallet_event_streaming_service")
            
            # Initialize agent configurations
            await self._initialize_agent_configurations()
            
            # Start agents
            await self._start_autonomous_agents()
            
            # Start background tasks
            asyncio.create_task(self._coordination_loop())
            asyncio.create_task(self._communication_manager())
            asyncio.create_task(self._performance_monitor())
            asyncio.create_task(self._consensus_manager())
            asyncio.create_task(self._real_time_dashboard_updates())
            
            logger.info("AutonomousAgentCoordinator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AutonomousAgentCoordinator: {e}")
            raise
    
    async def _initialize_agent_configurations(self):
        """Initialize agent configurations"""
        try:
            configurations = [
                AgentConfiguration(
                    agent_id="trend_follower_001",
                    name="Marcus Momentum",
                    agent_type="trend_following",
                    trading_style="aggressive_momentum",
                    risk_tolerance=0.7,
                    max_position_size=Decimal("5000"),
                    decision_confidence_threshold=0.75,
                    communication_enabled=True,
                    autonomous_mode=True,
                    performance_targets={
                        "win_rate": 0.65,
                        "max_drawdown": 0.15,
                        "sharpe_ratio": 1.5
                    },
                    constraints={
                        "max_trades_per_day": 10,
                        "min_position_hold_time": 3600,  # 1 hour
                        "max_correlation": 0.7
                    }
                ),
                
                AgentConfiguration(
                    agent_id="arbitrage_bot_003",
                    name="Alex Arbitrage",
                    agent_type="arbitrage",
                    trading_style="risk_neutral_arbitrage",
                    risk_tolerance=0.3,
                    max_position_size=Decimal("10000"),
                    decision_confidence_threshold=0.90,
                    communication_enabled=True,
                    autonomous_mode=True,
                    performance_targets={
                        "win_rate": 0.85,
                        "max_drawdown": 0.05,
                        "profit_factor": 2.0
                    },
                    constraints={
                        "min_spread": 0.001,
                        "max_execution_time": 30,
                        "min_liquidity": 100000
                    }
                ),
                
                AgentConfiguration(
                    agent_id="mean_reversion_002",
                    name="Sophia Reversion",
                    agent_type="mean_reversion",
                    trading_style="conservative_mean_reversion",
                    risk_tolerance=0.4,
                    max_position_size=Decimal("3000"),
                    decision_confidence_threshold=0.80,
                    communication_enabled=True,
                    autonomous_mode=True,
                    performance_targets={
                        "win_rate": 0.70,
                        "max_drawdown": 0.10,
                        "recovery_factor": 2.5
                    },
                    constraints={
                        "oversold_threshold": 30,
                        "overbought_threshold": 70,
                        "min_reversion_probability": 0.6
                    }
                ),
                
                AgentConfiguration(
                    agent_id="risk_manager_007",
                    name="Riley Risk",
                    agent_type="risk_management",
                    trading_style="defensive_risk_management",
                    risk_tolerance=0.2,
                    max_position_size=Decimal("0"),  # Risk manager doesn't trade
                    decision_confidence_threshold=0.95,
                    communication_enabled=True,
                    autonomous_mode=True,
                    performance_targets={
                        "portfolio_var": 0.02,
                        "max_exposure": 0.8,
                        "correlation_limit": 0.6
                    },
                    constraints={
                        "emergency_threshold": 0.05,
                        "rebalance_frequency": 3600,
                        "max_single_position": 0.25
                    }
                )
            ]
            
            for config in configurations:
                self.agent_configurations[config.agent_id] = config
            
            logger.info(f"Initialized {len(configurations)} agent configurations")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent configurations: {e}")
            raise
    
    async def _start_autonomous_agents(self):
        """Start all autonomous agents"""
        try:
            for agent_id, config in self.agent_configurations.items():
                agent = AutonomousAgent(
                    agent_id=agent_id,
                    name=config.name,
                    agent_type=config.agent_type,
                    status=AgentStatus.INITIALIZING,
                    configuration=asdict(config),
                    performance_metrics={},
                    created_at=datetime.now(timezone.utc)
                )
                
                # Initialize agent
                await self._initialize_agent(agent)
                
                # Add to active agents
                self.active_agents[agent_id] = agent
                
                # Initialize message queue
                self.message_queue[agent_id] = []
                
                logger.info(f"Started autonomous agent: {config.name}")
            
            logger.info(f"Started {len(self.active_agents)} autonomous agents")
            
        except Exception as e:
            logger.error(f"Failed to start autonomous agents: {e}")
            raise
    
    async def _initialize_agent(self, agent: AutonomousAgent):
        """Initialize individual agent"""
        try:
            # Set agent status to active
            agent.status = AgentStatus.ACTIVE
            
            # Initialize performance tracking
            self.agent_performance[agent.agent_id] = AgentPerformance(
                agent_id=agent.agent_id,
                total_trades=0,
                winning_trades=0,
                total_pnl=Decimal("0"),
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                win_rate=0.0,
                avg_trade_duration=0.0,
                last_updated=datetime.now(timezone.utc)
            )
            
            # Emit agent started event
            if self.event_service:
                await self.event_service.emit_event({
                    'event_type': 'agent.started',
                    'agent_id': agent.agent_id,
                    'agent_name': agent.name,
                    'agent_type': agent.agent_type,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
        except Exception as e:
            logger.error(f"Failed to initialize agent {agent.agent_id}: {e}")
            agent.status = AgentStatus.ERROR
            raise
    
    async def create_decision_context(
        self,
        decision_type: DecisionType,
        priority: int = 5,
        coordination_mode: CoordinationMode = CoordinationMode.COLLABORATIVE,
        time_limit: Optional[int] = None
    ) -> DecisionContext:
        """Create a new decision context for agent coordination"""
        try:
            # Gather current context data
            market_data = await self._get_current_market_data()
            portfolio_data = await self._get_current_portfolio_data()
            risk_metrics = await self._get_current_risk_metrics()
            goal_progress = await self._get_current_goal_progress()
            
            # Get recent agent communications
            recent_communications = await self._get_recent_communications()
            
            # Create decision context
            context = DecisionContext(
                decision_id=str(uuid.uuid4()),
                decision_type=decision_type,
                priority=priority,
                market_data=market_data,
                portfolio_data=portfolio_data,
                risk_metrics=risk_metrics,
                goal_progress=goal_progress,
                agent_communications=recent_communications,
                time_constraints=datetime.now(timezone.utc) + timedelta(seconds=time_limit) if time_limit else None,
                coordination_mode=coordination_mode
            )
            
            # Add to active decisions
            self.active_decisions[context.decision_id] = context
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to create decision context: {e}")
            raise
    
    async def coordinate_agent_decision(
        self,
        context: DecisionContext,
        participating_agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Coordinate multi-agent decision making"""
        try:
            # Determine participating agents
            if not participating_agents:
                participating_agents = list(self.active_agents.keys())
            
            # Filter active agents
            active_participating_agents = [
                agent_id for agent_id in participating_agents
                if agent_id in self.active_agents and self.active_agents[agent_id].status == AgentStatus.ACTIVE
            ]
            
            if not active_participating_agents:
                raise ValueError("No active agents available for decision coordination")
            
            # Handle different coordination modes
            if context.coordination_mode == CoordinationMode.INDEPENDENT:
                return await self._independent_decision(context, active_participating_agents)
            elif context.coordination_mode == CoordinationMode.COLLABORATIVE:
                return await self._collaborative_decision(context, active_participating_agents)
            elif context.coordination_mode == CoordinationMode.HIERARCHICAL:
                return await self._hierarchical_decision(context, active_participating_agents)
            elif context.coordination_mode == CoordinationMode.CONSENSUS_REQUIRED:
                return await self._consensus_decision(context, active_participating_agents)
            elif context.coordination_mode == CoordinationMode.EMERGENCY:
                return await self._emergency_decision(context, active_participating_agents)
            else:
                raise ValueError(f"Unknown coordination mode: {context.coordination_mode}")
            
        except Exception as e:
            logger.error(f"Failed to coordinate agent decision: {e}")
            raise
    
    async def _collaborative_decision(
        self,
        context: DecisionContext,
        participating_agents: List[str]
    ) -> Dict[str, Any]:
        """Handle collaborative decision making"""
        try:
            # Start conversation if LLM service is available
            conversation_id = None
            if self.llm_service:
                conversation_id = await self.llm_service.start_agent_conversation(
                    conversation_id=f"decision_{context.decision_id}",
                    participants=participating_agents,
                    topic=f"Decision: {context.decision_type.value}",
                    context={
                        'decision_context': asdict(context),
                        'coordination_mode': 'collaborative'
                    }
                )
                self.active_conversations.add(conversation_id)
            
            # Collect individual agent analyses
            agent_analyses = {}
            for agent_id in participating_agents:
                analysis = await self._get_agent_analysis(agent_id, context)
                agent_analyses[agent_id] = analysis
                
                # Send analysis to conversation
                if conversation_id and self.llm_service:
                    await self.llm_service.send_agent_message(
                        conversation_id=conversation_id,
                        sender_id=agent_id,
                        content=analysis['reasoning'],
                        message_type="discussion",
                        context=analysis
                    )
            
            # Synthesize collaborative decision
            final_decision = await self._synthesize_collaborative_decision(
                context, agent_analyses, conversation_id
            )
            
            # Record decision
            await self._record_decision(context, final_decision, agent_analyses)
            
            return final_decision
            
        except Exception as e:
            logger.error(f"Failed in collaborative decision: {e}")
            raise
    
    async def _consensus_decision(
        self,
        context: DecisionContext,
        participating_agents: List[str]
    ) -> Dict[str, Any]:
        """Handle consensus-required decision making"""
        try:
            # Create consensus process
            consensus = ConsensusProcess(
                consensus_id=str(uuid.uuid4()),
                decision_context=context,
                participating_agents=participating_agents,
                agent_votes={},
                required_agreement=0.7,  # 70% agreement required
                consensus_reached=False,
                final_decision=None,
                created_at=datetime.now(timezone.utc),
                deadline=context.time_constraints
            )
            
            self.consensus_processes[consensus.consensus_id] = consensus
            
            # Collect agent votes
            for agent_id in participating_agents:
                vote = await self._get_agent_vote(agent_id, context)
                consensus.agent_votes[agent_id] = vote
            
            # Check for consensus
            consensus_result = await self._evaluate_consensus(consensus)
            
            if consensus_result['consensus_reached']:
                consensus.consensus_reached = True
                consensus.final_decision = consensus_result['decision']
                
                # Emit consensus reached event
                if self.event_service:
                    await self.event_service.emit_event({
                        'event_type': 'consensus.reached',
                        'consensus_id': consensus.consensus_id,
                        'decision_id': context.decision_id,
                        'participating_agents': participating_agents,
                        'agreement_level': consensus_result['agreement_level'],
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
                return consensus.final_decision
            else:
                # No consensus reached - use fallback decision
                fallback_decision = await self._fallback_decision(context, consensus.agent_votes)
                
                # Emit consensus failed event
                if self.event_service:
                    await self.event_service.emit_event({
                        'event_type': 'consensus.failed',
                        'consensus_id': consensus.consensus_id,
                        'decision_id': context.decision_id,
                        'fallback_used': True,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
                return fallback_decision
            
        except Exception as e:
            logger.error(f"Failed in consensus decision: {e}")
            raise
    
    async def _get_agent_analysis(self, agent_id: str, context: DecisionContext) -> Dict[str, Any]:
        """Get individual agent analysis for decision context"""
        try:
            config = self.agent_configurations[agent_id]
            
            # Create agent-specific prompt
            analysis_prompt = f"""
            As {config.name}, a {config.agent_type} specialist, analyze the current situation and provide your recommendation.
            
            Decision Type: {context.decision_type.value}
            Priority: {context.priority}/10
            
            Market Data: {json.dumps(context.market_data, indent=2)}
            Portfolio Data: {json.dumps(context.portfolio_data, indent=2)}
            Risk Metrics: {json.dumps(context.risk_metrics, indent=2)}
            
            Your trading style: {config.trading_style}
            Risk tolerance: {config.risk_tolerance}
            Performance targets: {json.dumps(config.performance_targets, indent=2)}
            
            Provide:
            1. Your analysis of the situation
            2. Your recommendation
            3. Confidence level (0-1)
            4. Risk assessment
            5. Expected outcome
            """
            
            if self.llm_service:
                from ..models.llm_models import LLMRequest, LLMTaskType
                
                # Get agent-specific LLM preference
                agent_llm_id = self.agent_llm_preferences.get(agent_id)
                
                request = LLMRequest(
                    task_type=LLMTaskType.TRADING_DECISION,
                    prompt=analysis_prompt,
                    context=asdict(context),
                    agent_id=agent_llm_id  # Pass agent ID for optimal LLM routing
                )
                
                # Call LLM service with agent-specific routing
                response = await self.llm_service.process_llm_request(
                    request, 
                    agent_id=agent_llm_id
                )
                
                # Parse LLM response into structured analysis
                analysis = {
                    'agent_id': agent_id,
                    'recommendation': 'hold',  # Default
                    'confidence': response.confidence_score,
                    'reasoning': response.content,
                    'risk_level': 'medium',
                    'expected_outcome': 'neutral',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                # Fallback analysis without LLM
                analysis = await self._generate_fallback_analysis(agent_id, context)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to get agent analysis for {agent_id}: {e}")
            return await self._generate_fallback_analysis(agent_id, context)
    
    async def _generate_fallback_analysis(self, agent_id: str, context: DecisionContext) -> Dict[str, Any]:
        """Generate fallback analysis without LLM"""
        config = self.agent_configurations[agent_id]
        
        # Simple rule-based analysis based on agent type
        if config.agent_type == "trend_following":
            recommendation = "buy" if context.market_data.get('trend', 'neutral') == 'bullish' else "sell" if context.market_data.get('trend', 'neutral') == 'bearish' else "hold"
        elif config.agent_type == "arbitrage":
            recommendation = "buy" if context.market_data.get('spread', 0) > 0.001 else "hold"
        elif config.agent_type == "mean_reversion":
            rsi = context.market_data.get('rsi', 50)
            recommendation = "buy" if rsi < 30 else "sell" if rsi > 70 else "hold"
        elif config.agent_type == "risk_management":
            portfolio_risk = context.risk_metrics.get('portfolio_var', 0)
            recommendation = "reduce_exposure" if portfolio_risk > 0.05 else "maintain"
        else:
            recommendation = "hold"
        
        return {
            'agent_id': agent_id,
            'recommendation': recommendation,
            'confidence': 0.6,  # Moderate confidence for rule-based
            'reasoning': f"Rule-based {config.agent_type} analysis",
            'risk_level': 'medium',
            'expected_outcome': 'neutral',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _synthesize_collaborative_decision(
        self,
        context: DecisionContext,
        agent_analyses: Dict[str, Dict[str, Any]],
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synthesize final decision from collaborative agent analyses"""
        try:
            # Collect recommendations
            recommendations = {}
            total_confidence = 0
            
            for agent_id, analysis in agent_analyses.items():
                rec = analysis['recommendation']
                conf = analysis['confidence']
                
                if rec not in recommendations:
                    recommendations[rec] = {'count': 0, 'confidence': 0}
                
                recommendations[rec]['count'] += 1
                recommendations[rec]['confidence'] += conf
                total_confidence += conf
            
            # Find consensus recommendation
            best_recommendation = max(recommendations.items(), key=lambda x: x[1]['count'])
            final_recommendation = best_recommendation[0]
            
            # Calculate overall confidence
            overall_confidence = total_confidence / len(agent_analyses)
            
            # Use LLM to synthesize final reasoning
            final_reasoning = ""
            if conversation_id and self.llm_service:
                synthesis_prompt = f"""
                Synthesize the agent discussions into a final decision summary.
                
                Recommendation: {final_recommendation}
                Overall Confidence: {overall_confidence:.2f}
                
                Agent Analyses:
                {json.dumps(agent_analyses, indent=2)}
                
                Provide a clear, concise summary of the final decision and reasoning.
                """
                
                from ..models.llm_models import LLMRequest, LLMTaskType
                
                request = LLMRequest(
                    task_type=LLMTaskType.AGENT_COMMUNICATION,
                    prompt=synthesis_prompt,
                    context={'conversation_id': conversation_id}
                )
                
                response = await self.llm_service.process_llm_request(request)
                final_reasoning = response.content
            else:
                final_reasoning = f"Collaborative decision: {final_recommendation} (confidence: {overall_confidence:.2f})"
            
            return {
                'decision_id': context.decision_id,
                'recommendation': final_recommendation,
                'confidence': overall_confidence,
                'reasoning': final_reasoning,
                'participating_agents': list(agent_analyses.keys()),
                'individual_analyses': agent_analyses,
                'decision_method': 'collaborative',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to synthesize collaborative decision: {e}")
            raise
    
    async def _get_current_market_data(self) -> Dict[str, Any]:
        """Get current market data"""
        try:
            if self.market_data_service:
                return await self.market_data_service.get_current_market_snapshot()
            else:
                # Mock market data
                return {
                    'btc_usd_price': 43500.0,
                    'eth_usd_price': 2650.0,
                    'market_sentiment': 'neutral',
                    'volatility_index': 0.35,
                    'trend': 'bullish',
                    'volume_24h': 28500000,
                    'rsi': 58.5
                }
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return {}
    
    async def _get_current_portfolio_data(self) -> Dict[str, Any]:
        """Get current portfolio data"""
        try:
            if self.portfolio_service:
                return await self.portfolio_service.get_portfolio_summary()
            else:
                # Mock portfolio data
                return {
                    'total_value': 50000.0,
                    'cash_balance': 12000.0,
                    'btc_position': 0.5,
                    'eth_position': 8.2,
                    'total_pnl': 3500.0,
                    'open_positions': 5
                }
        except Exception as e:
            logger.error(f"Failed to get portfolio data: {e}")
            return {}
    
    async def _get_current_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics"""
        try:
            if self.risk_service:
                return await self.risk_service.get_risk_summary()
            else:
                # Mock risk data
                return {
                    'portfolio_var': 0.03,
                    'max_drawdown': 0.08,
                    'beta': 0.85,
                    'correlation': 0.62,
                    'volatility': 0.18
                }
        except Exception as e:
            logger.error(f"Failed to get risk metrics: {e}")
            return {}
    
    async def _get_current_goal_progress(self) -> Dict[str, Any]:
        """Get current goal progress"""
        try:
            if self.goal_service:
                return await self.goal_service.get_all_goal_progress()
            else:
                # Mock goal data
                return {
                    'monthly_return_goal': {'progress': 68.5, 'target': 15.0},
                    'risk_management_goal': {'progress': 92.3, 'target': 90.0},
                    'diversification_goal': {'progress': 78.1, 'target': 80.0}
                }
        except Exception as e:
            logger.error(f"Failed to get goal progress: {e}")
            return {}
    
    async def _get_recent_communications(self) -> List[Dict[str, Any]]:
        """Get recent agent communications"""
        try:
            recent_messages = []
            current_time = datetime.now(timezone.utc)
            
            for agent_id, messages in self.message_queue.items():
                for message in messages[-5:]:  # Last 5 messages per agent
                    if (current_time - datetime.fromisoformat(message['timestamp'])).total_seconds() < 3600:  # Last hour
                        recent_messages.append(message)
            
            return sorted(recent_messages, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get recent communications: {e}")
            return []
    
    async def _coordination_loop(self):
        """Main coordination loop"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Process active decisions
                for decision_id, context in list(self.active_decisions.items()):
                    # Check for timeout
                    if context.time_constraints and datetime.now(timezone.utc) > context.time_constraints:
                        logger.warning(f"Decision {decision_id} timed out")
                        del self.active_decisions[decision_id]
                        continue
                    
                    # Check if decision needs coordination
                    if context.coordination_mode == CoordinationMode.EMERGENCY:
                        result = await self.coordinate_agent_decision(context)
                        logger.info(f"Emergency decision completed: {result}")
                        del self.active_decisions[decision_id]
                
                # Update coordination metrics
                await self._update_coordination_metrics()
                
            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _communication_manager(self):
        """Manage agent communications"""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Process message queues
                for agent_id, messages in self.message_queue.items():
                    if messages:
                        # Process latest messages
                        for message in messages[-3:]:  # Process last 3 messages
                            await self._process_agent_message(agent_id, message)
                
                # Clean old messages
                current_time = datetime.now(timezone.utc)
                for agent_id in self.message_queue:
                    self.message_queue[agent_id] = [
                        msg for msg in self.message_queue[agent_id]
                        if (current_time - datetime.fromisoformat(msg['timestamp'])).total_seconds() < 3600
                    ]
                
            except Exception as e:
                logger.error(f"Error in communication manager: {e}")
    
    async def _performance_monitor(self):
        """Monitor agent performance"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                for agent_id, agent in self.active_agents.items():
                    # Update performance metrics
                    await self._update_agent_performance(agent_id)
                    
                    # Check performance thresholds
                    performance = self.agent_performance.get(agent_id)
                    if performance and performance.win_rate < self.alert_thresholds['low_performance']:
                        await self._send_performance_alert(agent_id, "low_performance")
                
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
    
    async def _real_time_dashboard_updates(self):
        """Send real-time updates to dashboard"""
        while True:
            try:
                await asyncio.sleep(15)  # Update every 15 seconds
                
                if self.event_service:
                    # Send agent status update
                    agent_status = {
                        agent_id: {
                            'status': agent.status.value,
                            'performance': asdict(self.agent_performance.get(agent_id, AgentPerformance(
                                agent_id=agent_id,
                                total_trades=0,
                                winning_trades=0,
                                total_pnl=Decimal("0"),
                                max_drawdown=0.0,
                                sharpe_ratio=0.0,
                                win_rate=0.0,
                                avg_trade_duration=0.0,
                                last_updated=datetime.now(timezone.utc)
                            )))
                        }
                        for agent_id, agent in self.active_agents.items()
                    }
                    
                    await self.event_service.emit_event({
                        'event_type': 'agents.status_update',
                        'agent_status': agent_status,
                        'coordination_metrics': self.coordination_metrics,
                        'active_decisions': len(self.active_decisions),
                        'active_conversations': len(self.active_conversations),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error in dashboard updates: {e}")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and health metrics"""
        return {
            "service": "autonomous_agent_coordinator",
            "status": "running",
            "active_agents": len(self.active_agents),
            "active_decisions": len(self.active_decisions),
            "active_conversations": len(self.active_conversations),
            "coordination_metrics": self.coordination_metrics,
            "monitoring_enabled": self.monitoring_enabled,
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_autonomous_agent_coordinator():
    """Factory function to create AutonomousAgentCoordinator instance"""
    return AutonomousAgentCoordinator()