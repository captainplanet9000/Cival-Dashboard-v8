"""
Agent Decision Engine
Real-time autonomous trading decision system with LLM integration
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid
from decimal import Decimal

from ..core.service_registry import get_registry
from ..models.agent_models import AgentDecision
from ..models.llm_models import LLMRequest, LLMTaskType

logger = logging.getLogger(__name__)

class DecisionUrgency(Enum):
    """Decision urgency levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class MarketEvent:
    """Market event data"""
    event_id: str
    event_type: str
    symbol: str
    price: Decimal
    volume: Decimal
    timestamp: datetime
    significance: float  # 0-1 scale
    metadata: Dict[str, Any]

@dataclass
class TradingDecision:
    """Trading decision result"""
    decision_id: str
    agent_id: str
    action: str  # buy, sell, hold, close
    symbol: str
    quantity: Decimal
    price: Optional[Decimal]
    confidence: float
    reasoning: str
    risk_assessment: Dict[str, Any]
    timestamp: datetime
    urgency: DecisionUrgency
    estimated_profit: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]

class AgentDecisionEngine:
    """
    Real-time decision engine for autonomous trading agents
    Processes market events and generates trading decisions using LLM analysis
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Service dependencies
        self.llm_service = None
        self.agent_coordinator = None
        self.market_data_service = None
        self.portfolio_service = None
        self.risk_service = None
        self.trading_service = None
        self.mcp_tools_service = None  # MCP tools integration
        
        # Decision tracking
        self.pending_decisions: Dict[str, TradingDecision] = {}
        self.executed_decisions: List[TradingDecision] = []
        self.decision_queue = asyncio.Queue()
        
        # Agent states
        self.agent_states: Dict[str, Dict[str, Any]] = {}
        self.agent_performance: Dict[str, Dict[str, float]] = {}
        
        # Market event processing
        self.event_queue = asyncio.Queue()
        self.event_handlers: Dict[str, List[callable]] = {}
        
        # Decision thresholds
        self.decision_thresholds = {
            "min_confidence": 0.7,
            "max_position_size": 0.05,  # 5% of portfolio
            "min_profit_target": 0.02,  # 2% minimum profit target
            "max_risk_per_trade": 0.01  # 1% max risk per trade
        }
        
        logger.info("AgentDecisionEngine initialized")
    
    async def initialize(self):
        """Initialize the decision engine"""
        try:
            # Get required services
            self.llm_service = self.registry.get_service("llm_integration_service")
            self.agent_coordinator = self.registry.get_service("autonomous_agent_coordinator")
            self.market_data_service = self.registry.get_service("market_data_service")
            self.portfolio_service = self.registry.get_service("portfolio_management_service")
            self.risk_service = self.registry.get_service("risk_management_service")
            self.trading_service = self.registry.get_service("trading_service")
            
            # Start background tasks
            asyncio.create_task(self._market_event_processor())
            asyncio.create_task(self._decision_processor())
            asyncio.create_task(self._performance_monitor())
            asyncio.create_task(self._real_time_analysis())
            
            logger.info("AgentDecisionEngine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AgentDecisionEngine: {e}")
            raise
    
    async def process_market_event(self, event: MarketEvent, agent_id: str = None):
        """Process market event and generate trading decisions"""
        try:
            # Determine which agents should respond to this event
            responding_agents = [agent_id] if agent_id else await self._get_responding_agents(event)
            
            for agent_id in responding_agents:
                # Check if agent is active and able to make decisions
                if not await self._is_agent_ready_for_decision(agent_id):
                    continue
                
                # Generate decision using LLM analysis
                decision = await self._generate_trading_decision(agent_id, event)
                
                if decision and decision.confidence >= self.decision_thresholds["min_confidence"]:
                    # Validate decision against risk limits
                    if await self._validate_decision(decision):
                        await self.decision_queue.put(decision)
                        logger.info(f"Agent {agent_id} generated decision: {decision.action} {decision.symbol}")
                    else:
                        logger.warning(f"Decision rejected due to risk validation: {decision.decision_id}")
                
        except Exception as e:
            logger.error(f"Failed to process market event: {e}")
    
    async def _generate_trading_decision(self, agent_id: str, event: MarketEvent) -> Optional[TradingDecision]:
        """Generate trading decision using LLM analysis"""
        try:
            # Get current market context
            market_context = await self._get_market_context(event.symbol)
            portfolio_context = await self._get_portfolio_context()
            risk_context = await self._get_risk_context()
            
            # First, gather additional analysis using MCP tools
            tool_analysis = await self._gather_tool_analysis(agent_id, event)
            
            # Create enhanced decision prompt with tool analysis
            decision_prompt = f"""
            You are an autonomous trading agent analyzing a market event. Make a trading decision.
            
            Market Event:
            - Symbol: {event.symbol}
            - Event Type: {event.event_type}
            - Price: ${event.price}
            - Volume: {event.volume}
            - Significance: {event.significance}/1.0
            - Timestamp: {event.timestamp}
            
            Market Context:
            {json.dumps(market_context, indent=2, default=str)}
            
            Portfolio Context:
            {json.dumps(portfolio_context, indent=2, default=str)}
            
            Risk Context:
            {json.dumps(risk_context, indent=2, default=str)}
            
            Decision Thresholds:
            - Minimum Confidence: {self.decision_thresholds['min_confidence']}
            - Maximum Position Size: {self.decision_thresholds['max_position_size'] * 100}%
            - Minimum Profit Target: {self.decision_thresholds['min_profit_target'] * 100}%
            - Maximum Risk per Trade: {self.decision_thresholds['max_risk_per_trade'] * 100}%
            
            Provide a JSON response with:
            {
                "action": "buy|sell|hold|close",
                "quantity": number,
                "confidence": 0.0-1.0,
                "reasoning": "detailed explanation",
                "estimated_profit": number,
                "stop_loss": number,
                "take_profit": number,
                "risk_assessment": {
                    "risk_level": "low|medium|high",
                    "potential_loss": number,
                    "risk_reward_ratio": number
                },
                "urgency": "low|medium|high|critical"
            }
            
            Only recommend trades with high confidence and favorable risk/reward ratios.
            """
            
            # Make LLM request
            if self.llm_service:
                request = LLMRequest(
                    task_type=LLMTaskType.TRADING_DECISION,
                    prompt=decision_prompt,
                    context={
                        "market_event": asdict(event),
                        "agent_id": agent_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                response = await self.llm_service.process_llm_request(
                    request, 
                    agent_id=agent_id
                )
                
                # Parse LLM response
                try:
                    decision_data = json.loads(response.content)
                    
                    decision = TradingDecision(
                        decision_id=str(uuid.uuid4()),
                        agent_id=agent_id,
                        action=decision_data.get("action", "hold"),
                        symbol=event.symbol,
                        quantity=Decimal(str(decision_data.get("quantity", 0))),
                        price=event.price,
                        confidence=float(decision_data.get("confidence", 0.0)),
                        reasoning=decision_data.get("reasoning", "LLM analysis"),
                        risk_assessment=decision_data.get("risk_assessment", {}),
                        timestamp=datetime.now(timezone.utc),
                        urgency=DecisionUrgency(decision_data.get("urgency", "medium")),
                        estimated_profit=Decimal(str(decision_data.get("estimated_profit", 0))) if decision_data.get("estimated_profit") else None,
                        stop_loss=Decimal(str(decision_data.get("stop_loss", 0))) if decision_data.get("stop_loss") else None,
                        take_profit=Decimal(str(decision_data.get("take_profit", 0))) if decision_data.get("take_profit") else None
                    )
                    
                    return decision
                    
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse LLM response as JSON: {response.content}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate trading decision: {e}")
            return None
    
    async def _validate_decision(self, decision: TradingDecision) -> bool:
        """Validate trading decision against risk limits"""
        try:
            # Check confidence threshold
            if decision.confidence < self.decision_thresholds["min_confidence"]:
                return False
            
            # Check position size limits
            if self.portfolio_service:
                portfolio_value = await self.portfolio_service.get_total_value()
                position_value = decision.quantity * decision.price if decision.price else 0
                position_percentage = float(position_value) / float(portfolio_value) if portfolio_value > 0 else 0
                
                if position_percentage > self.decision_thresholds["max_position_size"]:
                    logger.warning(f"Position size {position_percentage:.2%} exceeds limit {self.decision_thresholds['max_position_size']:.2%}")
                    return False
            
            # Check risk per trade
            if decision.stop_loss and decision.price:
                risk_per_trade = abs(float(decision.price - decision.stop_loss)) / float(decision.price)
                if risk_per_trade > self.decision_thresholds["max_risk_per_trade"]:
                    logger.warning(f"Risk per trade {risk_per_trade:.2%} exceeds limit {self.decision_thresholds['max_risk_per_trade']:.2%}")
                    return False
            
            # Check profit target
            if decision.take_profit and decision.price:
                profit_target = abs(float(decision.take_profit - decision.price)) / float(decision.price)
                if profit_target < self.decision_thresholds["min_profit_target"]:
                    logger.warning(f"Profit target {profit_target:.2%} below minimum {self.decision_thresholds['min_profit_target']:.2%}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate decision: {e}")
            return False
    
    async def execute_decision(self, decision: TradingDecision) -> Dict[str, Any]:
        """Execute a validated trading decision"""
        try:
            if self.trading_service:
                # Execute the trade
                execution_result = await self.trading_service.execute_trade(
                    symbol=decision.symbol,
                    action=decision.action,
                    quantity=decision.quantity,
                    price=decision.price,
                    stop_loss=decision.stop_loss,
                    take_profit=decision.take_profit
                )
                
                # Update decision status
                decision.timestamp = datetime.now(timezone.utc)
                self.executed_decisions.append(decision)
                
                # Track performance
                await self._track_decision_performance(decision, execution_result)
                
                logger.info(f"Executed decision {decision.decision_id}: {decision.action} {decision.quantity} {decision.symbol}")
                
                return execution_result
            
            # Mock execution for testing
            logger.info(f"MOCK EXECUTION: {decision.action} {decision.quantity} {decision.symbol} at ${decision.price}")
            return {
                "status": "executed",
                "decision_id": decision.decision_id,
                "execution_price": decision.price,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to execute decision: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _market_event_processor(self):
        """Background task to process market events"""
        while True:
            try:
                # Process events from queue
                event = await self.event_queue.get()
                await self.process_market_event(event)
                
            except Exception as e:
                logger.error(f"Market event processor error: {e}")
                await asyncio.sleep(1)
    
    async def _decision_processor(self):
        """Background task to process trading decisions"""
        while True:
            try:
                # Process decisions from queue
                decision = await self.decision_queue.get()
                
                # Execute decision if validation passes
                if await self._validate_decision(decision):
                    result = await self.execute_decision(decision)
                    logger.info(f"Decision executed: {result}")
                else:
                    logger.warning(f"Decision validation failed: {decision.decision_id}")
                
            except Exception as e:
                logger.error(f"Decision processor error: {e}")
                await asyncio.sleep(1)
    
    async def _real_time_analysis(self):
        """Continuous market analysis and opportunity detection"""
        while True:
            try:
                # Analyze market conditions every 30 seconds
                await asyncio.sleep(30)
                
                # Check for opportunities
                opportunities = await self._scan_for_opportunities()
                
                for opportunity in opportunities:
                    # Create market event for opportunity
                    event = MarketEvent(
                        event_id=str(uuid.uuid4()),
                        event_type="opportunity_detected",
                        symbol=opportunity["symbol"],
                        price=opportunity["price"],
                        volume=opportunity.get("volume", Decimal("0")),
                        timestamp=datetime.now(timezone.utc),
                        significance=opportunity["significance"],
                        metadata=opportunity
                    )
                    
                    await self.event_queue.put(event)
                
            except Exception as e:
                logger.error(f"Real-time analysis error: {e}")
                await asyncio.sleep(60)
    
    async def _get_market_context(self, symbol: str) -> Dict[str, Any]:
        """Get current market context for symbol"""
        try:
            if self.market_data_service:
                return await self.market_data_service.get_market_context(symbol)
            return {"symbol": symbol, "mock_data": True}
        except Exception:
            return {"symbol": symbol, "error": "market_data_unavailable"}
    
    async def _get_portfolio_context(self) -> Dict[str, Any]:
        """Get current portfolio context"""
        try:
            if self.portfolio_service:
                return await self.portfolio_service.get_portfolio_summary()
            return {"mock_portfolio": True}
        except Exception:
            return {"error": "portfolio_data_unavailable"}
    
    async def _get_risk_context(self) -> Dict[str, Any]:
        """Get current risk context"""
        try:
            if self.risk_service:
                return await self.risk_service.get_risk_summary()
            return {"mock_risk": True}
        except Exception:
            return {"error": "risk_data_unavailable"}
    
    async def _scan_for_opportunities(self) -> List[Dict[str, Any]]:
        """Scan for trading opportunities"""
        # Mock opportunity detection
        return [
            {
                "symbol": "BTCUSD",
                "price": Decimal("45000"),
                "significance": 0.8,
                "opportunity_type": "trend_breakout",
                "volume": Decimal("1000")
            }
        ]
    
    async def _is_agent_ready_for_decision(self, agent_id: str) -> bool:
        """Check if agent is ready to make decisions"""
        # Check agent status, rate limits, etc.
        return True
    
    async def _get_responding_agents(self, event: MarketEvent) -> List[str]:
        """Get list of agents that should respond to event"""
        # Return all active agents for now
        return ["trend_follower_001", "arbitrage_bot_003", "mean_reversion_002", "risk_manager_004"]
    
    async def _track_decision_performance(self, decision: TradingDecision, execution_result: Dict[str, Any]):
        """Track decision performance"""
        # Update agent performance metrics
        if decision.agent_id not in self.agent_performance:
            self.agent_performance[decision.agent_id] = {
                "total_decisions": 0,
                "successful_decisions": 0,
                "total_profit": 0.0,
                "total_loss": 0.0
            }
        
        self.agent_performance[decision.agent_id]["total_decisions"] += 1
    
    async def _performance_monitor(self):
        """Monitor agent performance"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Log performance summary
                logger.info(f"Agent performance summary: {self.agent_performance}")
                
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(300)
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent decision engine status"""
        return {
            "pending_decisions": len(self.pending_decisions),
            "executed_decisions": len(self.executed_decisions),
            "agent_performance": self.agent_performance,
            "decision_thresholds": self.decision_thresholds,
            "status": "active"
        }
    
    async def _gather_tool_analysis(self, agent_id: str, event: MarketEvent) -> Dict[str, Any]:
        """Gather comprehensive analysis using MCP tools"""
        tool_results = {}
        
        try:
            # Mock tool analysis - in production, this would call actual MCP tools
            # Tool 1: Market Sentiment Analysis
            tool_results["sentiment_analysis"] = {
                "overall_sentiment": "bullish",
                "sentiment_score": 0.72,
                "confidence": 0.85,
                "key_factors": ["Strong technical breakout", "Positive momentum indicators"],
                "risk_factors": ["Market volatility", "External economic factors"]
            }
            
            # Tool 2: Technical Analysis
            tool_results["technical_analysis"] = {
                "trend": "bullish",
                "support_levels": [44000, 42500],
                "resistance_levels": [46000, 47500],
                "rsi": 68.5,
                "macd_signal": "bullish",
                "bollinger_position": "upper_half",
                "recommendation": "buy"
            }
            
            # Tool 3: Order Book Analysis
            tool_results["order_book_analysis"] = {
                "bid_ask_spread": 10.50,
                "liquidity_score": 8.5,
                "market_depth_score": 7.8,
                "optimal_order_size": 1000,
                "execution_risk": "low"
            }
            
            # Tool 4: Portfolio Risk Assessment
            tool_results["risk_assessment"] = {
                "portfolio_var_95": 0.025,
                "position_size_recommendation": 0.03,  # 3% of portfolio
                "risk_level": "moderate",
                "correlation_risk": "low",
                "concentration_risk": "acceptable"
            }
            
            # Tool 5: Performance Prediction
            tool_results["performance_prediction"] = {
                "expected_return_1d": 0.023,
                "probability_of_profit": 0.68,
                "estimated_holding_period": "2-4 hours",
                "confidence_interval": [0.015, 0.031]
            }
            
            return {
                "tools_executed": len(tool_results),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "symbol": event.symbol,
                "results": tool_results,
                "summary": {
                    "overall_recommendation": "buy",
                    "confidence_score": 0.75,
                    "risk_level": "moderate",
                    "expected_outcome": "positive"
                }
            }
            
        except Exception as e:
            logger.error(f"Tool analysis failed for agent {agent_id}: {e}")
            return {
                "tools_executed": 0,
                "error": str(e),
                "fallback_analysis": True,
                "agent_id": agent_id,
                "symbol": event.symbol
            }
