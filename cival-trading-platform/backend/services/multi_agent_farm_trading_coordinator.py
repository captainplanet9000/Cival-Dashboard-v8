"""
Multi-Agent Farm Trading Coordinator
Integrates farm coordination with real-time trading operations
"""

import asyncio
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)

# Coordination modes for farm trading
class FarmTradingMode:
    AUTONOMOUS = "autonomous"  # Each agent trades independently
    COORDINATED = "coordinated"  # Agents coordinate positions
    CONSENSUS = "consensus"  # Requires agreement before trading
    HIERARCHICAL = "hierarchical"  # Follow lead agent decisions
    DISTRIBUTED = "distributed"  # Distribute trades across agents

# Trading action types
class TradingAction:
    OPEN_POSITION = "open_position"
    CLOSE_POSITION = "close_position"
    MODIFY_POSITION = "modify_position"
    HEDGE_POSITION = "hedge_position"
    REBALANCE = "rebalance"

class MultiAgentFarmTradingCoordinator:
    """Coordinates trading activities across farm agents"""
    
    def __init__(self, farm_coordination_service, real_time_trading_orchestrator, 
                 farm_performance_service, master_wallet_service):
        self.farm_coordination = farm_coordination_service
        self.trading_orchestrator = real_time_trading_orchestrator
        self.farm_performance = farm_performance_service
        self.master_wallet = master_wallet_service
        
        # Farm trading sessions
        self.farm_trading_sessions = {}
        
        # Agent trading allocations
        self.agent_allocations = {}
        
        # Coordination history
        self.coordination_history = []
        
        logger.info("Multi-Agent Farm Trading Coordinator initialized")
    
    async def start_farm_trading_session(
        self,
        farm_id: str,
        session_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start a coordinated trading session for a farm"""
        try:
            session_id = f"farm_session_{uuid.uuid4().hex[:8]}"
            
            # Get farm configuration
            farm_config = await self._get_farm_configuration(farm_id)
            
            # Allocate trading capital to agents
            allocations = await self._allocate_trading_capital(
                farm_id,
                session_config.get("total_capital", 100000),
                session_config.get("allocation_strategy", "performance_weighted")
            )
            
            # Create trading session
            session = {
                "session_id": session_id,
                "farm_id": farm_id,
                "status": "active",
                
                # Configuration
                "trading_mode": session_config.get("mode", FarmTradingMode.COORDINATED),
                "strategies": session_config.get("strategies", ["momentum", "arbitrage"]),
                "symbols": session_config.get("symbols", ["BTC/USDT", "ETH/USDT"]),
                "risk_limits": session_config.get("risk_limits", {
                    "max_farm_exposure": 50000,
                    "max_agent_exposure": 10000,
                    "max_correlation": 0.7,
                    "stop_loss_percentage": 0.05
                }),
                
                # Agent allocations
                "agent_allocations": allocations,
                "active_agents": list(allocations.keys()),
                
                # Trading state
                "agent_sessions": {},  # Individual agent trading sessions
                "active_positions": [],
                "coordination_events": [],
                
                # Performance tracking
                "total_pnl": 0,
                "agent_pnl": {agent: 0 for agent in allocations},
                "trade_count": 0,
                "win_rate": 0,
                
                # Timing
                "started_at": datetime.utcnow(),
                "last_coordination": datetime.utcnow()
            }
            
            # Start individual agent trading sessions
            for agent_id, allocation in allocations.items():
                agent_session = await self._start_agent_trading_session(
                    session_id,
                    agent_id,
                    allocation,
                    session_config
                )
                session["agent_sessions"][agent_id] = agent_session
            
            # Store session
            self.farm_trading_sessions[session_id] = session
            
            # Start coordination background tasks
            asyncio.create_task(self._run_coordination_loop(session_id))
            asyncio.create_task(self._monitor_risk_limits(session_id))
            
            logger.info(f"Started farm trading session {session_id} for farm {farm_id}")
            
            return {
                "session_id": session_id,
                "farm_id": farm_id,
                "status": "active",
                "trading_mode": session["trading_mode"],
                "active_agents": session["active_agents"],
                "total_capital": session_config.get("total_capital", 100000),
                "agent_allocations": allocations,
                "strategies": session["strategies"],
                "symbols": session["symbols"],
                "started_at": session["started_at"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to start farm trading session: {e}")
            raise
    
    async def coordinate_trading_decision(
        self,
        session_id: str,
        decision_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate a trading decision across farm agents"""
        try:
            session = self.farm_trading_sessions.get(session_id)
            if not session:
                raise ValueError(f"Trading session {session_id} not found")
            
            coordination_id = f"coord_{uuid.uuid4().hex[:8]}"
            
            # Create coordination event
            coordination_event = {
                "coordination_id": coordination_id,
                "session_id": session_id,
                "farm_id": session["farm_id"],
                "type": decision_context.get("action", TradingAction.OPEN_POSITION),
                "symbol": decision_context.get("symbol"),
                "timestamp": datetime.utcnow(),
                
                # Decision context
                "market_conditions": await self._analyze_market_conditions(
                    decision_context.get("symbol")
                ),
                "risk_assessment": await self._assess_coordination_risk(
                    session,
                    decision_context
                ),
                
                # Agent decisions
                "agent_proposals": {},
                "consensus_reached": False,
                "final_decision": None,
                "execution_plan": None
            }
            
            # Get proposals from each agent based on trading mode
            if session["trading_mode"] == FarmTradingMode.AUTONOMOUS:
                result = await self._autonomous_coordination(
                    session,
                    coordination_event,
                    decision_context
                )
            elif session["trading_mode"] == FarmTradingMode.CONSENSUS:
                result = await self._consensus_coordination(
                    session,
                    coordination_event,
                    decision_context
                )
            elif session["trading_mode"] == FarmTradingMode.HIERARCHICAL:
                result = await self._hierarchical_coordination(
                    session,
                    coordination_event,
                    decision_context
                )
            elif session["trading_mode"] == FarmTradingMode.DISTRIBUTED:
                result = await self._distributed_coordination(
                    session,
                    coordination_event,
                    decision_context
                )
            else:
                # Default coordinated mode
                result = await self._standard_coordination(
                    session,
                    coordination_event,
                    decision_context
                )
            
            # Store coordination event
            session["coordination_events"].append(coordination_event)
            self.coordination_history.append(coordination_event)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to coordinate trading decision: {e}")
            raise
    
    async def execute_coordinated_trade(
        self,
        session_id: str,
        execution_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a coordinated trade across multiple agents"""
        try:
            session = self.farm_trading_sessions.get(session_id)
            if not session:
                raise ValueError(f"Trading session {session_id} not found")
            
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
            
            # Prepare execution tracking
            execution_result = {
                "execution_id": execution_id,
                "session_id": session_id,
                "plan": execution_plan,
                "agent_orders": {},
                "total_executed": 0,
                "average_price": 0,
                "status": "executing",
                "started_at": datetime.utcnow()
            }
            
            # Execute orders for each agent
            order_tasks = []
            for agent_id, agent_plan in execution_plan.get("agent_allocations", {}).items():
                if agent_plan.get("quantity", 0) > 0:
                    order_task = self._execute_agent_order(
                        session,
                        agent_id,
                        agent_plan,
                        execution_id
                    )
                    order_tasks.append(order_task)
            
            # Execute orders concurrently
            if order_tasks:
                agent_results = await asyncio.gather(*order_tasks, return_exceptions=True)
                
                # Process results
                total_quantity = 0
                weighted_price = 0
                
                for i, result in enumerate(agent_results):
                    if isinstance(result, Exception):
                        logger.error(f"Agent order failed: {result}")
                        continue
                    
                    agent_id = list(execution_plan["agent_allocations"].keys())[i]
                    execution_result["agent_orders"][agent_id] = result
                    
                    if result.get("status") == "filled":
                        quantity = result.get("filled_quantity", 0)
                        price = result.get("average_price", 0)
                        total_quantity += quantity
                        weighted_price += quantity * price
                
                # Calculate execution summary
                if total_quantity > 0:
                    execution_result["total_executed"] = total_quantity
                    execution_result["average_price"] = weighted_price / total_quantity
                    execution_result["status"] = "completed"
                else:
                    execution_result["status"] = "failed"
            
            execution_result["completed_at"] = datetime.utcnow()
            
            # Update session positions
            if execution_result["status"] == "completed":
                await self._update_farm_positions(session, execution_result)
            
            # Broadcast execution result to agents
            await self.farm_coordination.facilitate_agent_communication(
                session["farm_id"],
                "coordinator",
                {
                    "type": "execution_complete",
                    "execution_id": execution_id,
                    "result": execution_result
                }
            )
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Failed to execute coordinated trade: {e}")
            raise
    
    async def get_farm_trading_performance(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive performance metrics for farm trading session"""
        try:
            session = self.farm_trading_sessions.get(session_id)
            if not session:
                raise ValueError(f"Trading session {session_id} not found")
            
            # Calculate aggregate metrics
            total_trades = session.get("trade_count", 0)
            winning_trades = sum(1 for p in session.get("active_positions", []) 
                               if p.get("unrealized_pnl", 0) > 0)
            
            # Get performance from each agent
            agent_performances = {}
            for agent_id, agent_session in session.get("agent_sessions", {}).items():
                if agent_session.get("trading_session_id"):
                    perf = await self.trading_orchestrator.get_session_performance(
                        agent_session["trading_session_id"]
                    )
                    agent_performances[agent_id] = perf
            
            # Calculate farm-level metrics
            performance = {
                "session_id": session_id,
                "farm_id": session["farm_id"],
                "status": session["status"],
                
                # Trading metrics
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": winning_trades / total_trades if total_trades > 0 else 0,
                "active_positions": len(session.get("active_positions", [])),
                
                # Financial metrics
                "total_pnl": session.get("total_pnl", 0),
                "agent_pnl": session.get("agent_pnl", {}),
                "best_performing_agent": max(
                    session.get("agent_pnl", {}).items(),
                    key=lambda x: x[1],
                    default=("none", 0)
                )[0],
                
                # Risk metrics
                "total_exposure": sum(p.get("position_value", 0) 
                                    for p in session.get("active_positions", [])),
                "risk_utilization": await self._calculate_risk_utilization(session),
                
                # Coordination metrics
                "coordination_events": len(session.get("coordination_events", [])),
                "consensus_rate": await self._calculate_consensus_rate(session),
                "average_decision_time": await self._calculate_avg_decision_time(session),
                
                # Agent performances
                "agent_performances": agent_performances,
                
                # Timing
                "session_duration": str(
                    datetime.utcnow() - session["started_at"]
                ),
                "last_update": datetime.utcnow().isoformat()
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Failed to get farm trading performance: {e}")
            raise
    
    async def stop_farm_trading_session(
        self,
        session_id: str,
        close_positions: bool = True
    ) -> Dict[str, Any]:
        """Stop a farm trading session"""
        try:
            session = self.farm_trading_sessions.get(session_id)
            if not session:
                raise ValueError(f"Trading session {session_id} not found")
            
            # Mark session as stopping
            session["status"] = "stopping"
            
            # Close all positions if requested
            if close_positions and session.get("active_positions"):
                close_tasks = []
                for position in session["active_positions"]:
                    close_task = self._close_farm_position(session, position)
                    close_tasks.append(close_task)
                
                if close_tasks:
                    await asyncio.gather(*close_tasks, return_exceptions=True)
            
            # Stop individual agent sessions
            for agent_id, agent_session in session.get("agent_sessions", {}).items():
                if agent_session.get("trading_session_id"):
                    try:
                        await self.trading_orchestrator.stop_trading_session(
                            agent_session["trading_session_id"]
                        )
                    except Exception as e:
                        logger.error(f"Failed to stop agent session: {e}")
            
            # Calculate final performance
            final_performance = await self.get_farm_trading_performance(session_id)
            
            # Update session status
            session["status"] = "stopped"
            session["stopped_at"] = datetime.utcnow()
            
            # Return final summary
            return {
                "session_id": session_id,
                "farm_id": session["farm_id"],
                "status": "stopped",
                "final_performance": final_performance,
                "positions_closed": close_positions,
                "session_duration": str(session["stopped_at"] - session["started_at"]),
                "stopped_at": session["stopped_at"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to stop farm trading session: {e}")
            raise
    
    # Private helper methods
    
    async def _get_farm_configuration(self, farm_id: str) -> Dict[str, Any]:
        """Get farm configuration"""
        # This would integrate with farm management service
        return {
            "farm_id": farm_id,
            "name": f"Farm {farm_id}",
            "agents": ["agent_1", "agent_2", "agent_3"],
            "strategies": ["momentum", "mean_reversion", "arbitrage"]
        }
    
    async def _allocate_trading_capital(
        self,
        farm_id: str,
        total_capital: float,
        strategy: str
    ) -> Dict[str, float]:
        """Allocate capital to farm agents"""
        if strategy == "performance_weighted":
            # Get agent performances
            performance = await self.farm_performance.get_agent_performance_metrics(farm_id)
            
            # Weight by performance
            total_score = sum(p.get("performance_score", 1) for p in performance.values())
            
            allocations = {}
            for agent_id, perf in performance.items():
                weight = perf.get("performance_score", 1) / total_score
                allocations[agent_id] = total_capital * weight
            
            return allocations
        else:
            # Equal allocation
            agents = ["agent_1", "agent_2", "agent_3"]  # Mock for now
            allocation_per_agent = total_capital / len(agents)
            return {agent: allocation_per_agent for agent in agents}
    
    async def _start_agent_trading_session(
        self,
        farm_session_id: str,
        agent_id: str,
        allocation: float,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start trading session for individual agent"""
        agent_config = {
            "strategies": config.get("strategies", ["momentum"]),
            "symbols": config.get("symbols", ["BTC/USDT"]),
            "risk_limits": {
                "max_position_size": allocation * 0.2,  # 20% per position
                "max_daily_loss": allocation * 0.05,    # 5% stop loss
                "max_leverage": 2
            },
            "agent_id": agent_id,
            "farm_session_id": farm_session_id
        }
        
        # Start real-time trading session
        session = await self.trading_orchestrator.start_trading_session(agent_config)
        
        return {
            "agent_id": agent_id,
            "trading_session_id": session.get("session_id"),
            "allocation": allocation,
            "status": "active"
        }
    
    async def _analyze_market_conditions(self, symbol: str) -> Dict[str, Any]:
        """Analyze current market conditions"""
        return {
            "symbol": symbol,
            "trend": "bullish",
            "volatility": "medium",
            "volume": "high",
            "support_levels": [49000, 48500, 48000],
            "resistance_levels": [51000, 51500, 52000]
        }
    
    async def _assess_coordination_risk(
        self,
        session: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risk for coordination decision"""
        return {
            "current_exposure": sum(p.get("position_value", 0) 
                                  for p in session.get("active_positions", [])),
            "risk_score": 0.65,
            "correlation_risk": "medium",
            "concentration_risk": "low",
            "market_risk": "medium"
        }
    
    async def _standard_coordination(
        self,
        session: Dict[str, Any],
        event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Standard coordinated decision making"""
        # Collect proposals from agents
        proposals = await self._collect_agent_proposals(session, context)
        
        # Aggregate proposals
        aggregated = await self._aggregate_proposals(proposals)
        
        # Create execution plan
        execution_plan = {
            "action": context.get("action"),
            "symbol": context.get("symbol"),
            "total_quantity": aggregated["total_quantity"],
            "average_price": aggregated["average_price"],
            "agent_allocations": aggregated["allocations"]
        }
        
        event["agent_proposals"] = proposals
        event["consensus_reached"] = True
        event["final_decision"] = aggregated
        event["execution_plan"] = execution_plan
        
        return {
            "coordination_id": event["coordination_id"],
            "decision": "execute",
            "execution_plan": execution_plan,
            "consensus": True
        }
    
    async def _autonomous_coordination(
        self,
        session: Dict[str, Any],
        event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Autonomous mode - agents act independently"""
        # Each agent makes independent decision
        return {
            "coordination_id": event["coordination_id"],
            "decision": "autonomous",
            "message": "Agents will trade independently based on their strategies"
        }
    
    async def _consensus_coordination(
        self,
        session: Dict[str, Any],
        event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Consensus mode - require agreement"""
        proposals = await self._collect_agent_proposals(session, context)
        
        # Check for consensus
        votes = {"buy": 0, "sell": 0, "hold": 0}
        for proposal in proposals.values():
            action = proposal.get("action", "hold")
            votes[action] += 1
        
        # Require majority
        total_agents = len(proposals)
        threshold = total_agents * 0.6
        
        consensus_action = None
        for action, count in votes.items():
            if count >= threshold:
                consensus_action = action
                break
        
        if consensus_action and consensus_action != "hold":
            # Create execution plan
            aggregated = await self._aggregate_proposals(proposals)
            execution_plan = {
                "action": consensus_action,
                "symbol": context.get("symbol"),
                "total_quantity": aggregated["total_quantity"],
                "agent_allocations": aggregated["allocations"]
            }
            
            return {
                "coordination_id": event["coordination_id"],
                "decision": "execute",
                "execution_plan": execution_plan,
                "consensus": True,
                "votes": votes
            }
        else:
            return {
                "coordination_id": event["coordination_id"],
                "decision": "no_action",
                "reason": "No consensus reached",
                "votes": votes
            }
    
    async def _hierarchical_coordination(
        self,
        session: Dict[str, Any],
        event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Hierarchical mode - follow lead agent"""
        # Identify lead agent (best performing)
        agent_pnl = session.get("agent_pnl", {})
        lead_agent = max(agent_pnl.items(), key=lambda x: x[1], default=("agent_1", 0))[0]
        
        # Get lead agent proposal
        lead_proposal = await self._get_agent_proposal(lead_agent, context)
        
        if lead_proposal.get("action") != "hold":
            # Other agents follow with proportional allocation
            execution_plan = {
                "action": lead_proposal["action"],
                "symbol": context.get("symbol"),
                "lead_agent": lead_agent,
                "agent_allocations": {}
            }
            
            # Allocate to agents
            for agent_id in session["active_agents"]:
                allocation = session["agent_allocations"].get(agent_id, 0)
                execution_plan["agent_allocations"][agent_id] = {
                    "quantity": lead_proposal["quantity"] * (allocation / sum(session["agent_allocations"].values())),
                    "action": lead_proposal["action"]
                }
            
            return {
                "coordination_id": event["coordination_id"],
                "decision": "execute",
                "execution_plan": execution_plan,
                "mode": "hierarchical",
                "lead_agent": lead_agent
            }
        else:
            return {
                "coordination_id": event["coordination_id"],
                "decision": "no_action",
                "reason": "Lead agent recommends hold"
            }
    
    async def _distributed_coordination(
        self,
        session: Dict[str, Any],
        event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Distributed mode - split trades across agents"""
        total_quantity = context.get("quantity", 1000)
        
        # Distribute based on agent specializations
        distribution = {}
        for agent_id in session["active_agents"]:
            # Could check agent specialization here
            distribution[agent_id] = total_quantity / len(session["active_agents"])
        
        execution_plan = {
            "action": context.get("action"),
            "symbol": context.get("symbol"),
            "distribution_strategy": "equal",
            "agent_allocations": {
                agent: {
                    "quantity": qty,
                    "action": context.get("action")
                }
                for agent, qty in distribution.items()
            }
        }
        
        return {
            "coordination_id": event["coordination_id"],
            "decision": "execute",
            "execution_plan": execution_plan,
            "mode": "distributed"
        }
    
    async def _collect_agent_proposals(
        self,
        session: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Collect trading proposals from all agents"""
        proposals = {}
        
        # This would integrate with agent decision systems
        for agent_id in session["active_agents"]:
            proposal = await self._get_agent_proposal(agent_id, context)
            proposals[agent_id] = proposal
        
        return proposals
    
    async def _get_agent_proposal(
        self,
        agent_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get proposal from individual agent"""
        # Mock implementation - would integrate with agent systems
        import random
        
        actions = ["buy", "sell", "hold"]
        action = random.choice(actions)
        
        return {
            "agent_id": agent_id,
            "action": action,
            "symbol": context.get("symbol"),
            "quantity": random.uniform(100, 1000),
            "price": context.get("current_price", 50000) * random.uniform(0.99, 1.01),
            "confidence": random.uniform(0.5, 0.95),
            "reasoning": f"Based on {agent_id} strategy analysis"
        }
    
    async def _aggregate_proposals(
        self,
        proposals: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate agent proposals into execution plan"""
        total_quantity = 0
        weighted_price = 0
        allocations = {}
        
        for agent_id, proposal in proposals.items():
            if proposal.get("action") != "hold":
                qty = proposal.get("quantity", 0)
                price = proposal.get("price", 0)
                
                total_quantity += qty
                weighted_price += qty * price
                
                allocations[agent_id] = {
                    "quantity": qty,
                    "target_price": price,
                    "action": proposal["action"]
                }
        
        return {
            "total_quantity": total_quantity,
            "average_price": weighted_price / total_quantity if total_quantity > 0 else 0,
            "allocations": allocations
        }
    
    async def _execute_agent_order(
        self,
        session: Dict[str, Any],
        agent_id: str,
        plan: Dict[str, Any],
        execution_id: str
    ) -> Dict[str, Any]:
        """Execute order for individual agent"""
        agent_session = session["agent_sessions"].get(agent_id, {})
        
        order_config = {
            "symbol": plan.get("symbol", "BTC/USDT"),
            "order_type": "limit",
            "side": "buy" if plan.get("action") == "buy" else "sell",
            "quantity": plan.get("quantity", 0),
            "price": plan.get("target_price", 50000),
            "agent_id": agent_id,
            "execution_id": execution_id
        }
        
        # Submit through real-time trading orchestrator
        result = await self.trading_orchestrator.submit_real_time_order(order_config)
        
        return result
    
    async def _update_farm_positions(
        self,
        session: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> None:
        """Update farm positions after execution"""
        position = {
            "position_id": f"pos_{uuid.uuid4().hex[:8]}",
            "farm_id": session["farm_id"],
            "session_id": session["session_id"],
            "symbol": execution_result["plan"]["symbol"],
            "side": execution_result["plan"]["action"],
            "quantity": execution_result["total_executed"],
            "average_price": execution_result["average_price"],
            "position_value": execution_result["total_executed"] * execution_result["average_price"],
            "unrealized_pnl": 0,
            "agent_contributions": execution_result["agent_orders"],
            "opened_at": execution_result["completed_at"]
        }
        
        session["active_positions"].append(position)
        session["trade_count"] += 1
    
    async def _close_farm_position(
        self,
        session: Dict[str, Any],
        position: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Close a farm position"""
        # Create close order
        close_plan = {
            "action": "sell" if position["side"] == "buy" else "buy",
            "symbol": position["symbol"],
            "total_quantity": position["quantity"],
            "agent_allocations": {}
        }
        
        # Distribute close order to agents who contributed
        for agent_id, contribution in position.get("agent_contributions", {}).items():
            close_plan["agent_allocations"][agent_id] = {
                "quantity": contribution.get("filled_quantity", 0),
                "action": close_plan["action"]
            }
        
        # Execute close order
        result = await self.execute_coordinated_trade(
            session["session_id"],
            close_plan
        )
        
        return result
    
    async def _run_coordination_loop(self, session_id: str) -> None:
        """Background task for periodic coordination"""
        while session_id in self.farm_trading_sessions:
            session = self.farm_trading_sessions[session_id]
            
            if session["status"] != "active":
                break
            
            try:
                # Check for coordination opportunities
                await self._check_coordination_opportunities(session)
                
                # Update performance metrics
                await self._update_session_metrics(session)
                
                # Sleep before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Coordination loop error: {e}")
    
    async def _monitor_risk_limits(self, session_id: str) -> None:
        """Monitor and enforce risk limits"""
        while session_id in self.farm_trading_sessions:
            session = self.farm_trading_sessions[session_id]
            
            if session["status"] != "active":
                break
            
            try:
                # Check risk limits
                risk_status = await self._check_risk_limits(session)
                
                if risk_status.get("violations"):
                    await self._handle_risk_violations(session, risk_status["violations"])
                
                # Sleep before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Risk monitoring error: {e}")
    
    async def _check_coordination_opportunities(
        self,
        session: Dict[str, Any]
    ) -> None:
        """Check for trading coordination opportunities"""
        # This would integrate with market analysis and agent strategies
        pass
    
    async def _update_session_metrics(self, session: Dict[str, Any]) -> None:
        """Update session performance metrics"""
        # Calculate current P&L
        total_pnl = 0
        for position in session.get("active_positions", []):
            # Would get current market price and calculate unrealized P&L
            position["unrealized_pnl"] = 0  # Mock for now
            total_pnl += position["unrealized_pnl"]
        
        session["total_pnl"] = total_pnl
    
    async def _check_risk_limits(
        self,
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if risk limits are breached"""
        violations = []
        risk_limits = session.get("risk_limits", {})
        
        # Check exposure limits
        total_exposure = sum(p.get("position_value", 0) 
                           for p in session.get("active_positions", []))
        
        if total_exposure > risk_limits.get("max_farm_exposure", float('inf')):
            violations.append({
                "type": "max_exposure",
                "current": total_exposure,
                "limit": risk_limits["max_farm_exposure"]
            })
        
        # Check stop loss
        if session["total_pnl"] < -risk_limits.get("stop_loss_percentage", 0.05) * session["agent_allocations"]:
            violations.append({
                "type": "stop_loss",
                "current_pnl": session["total_pnl"],
                "threshold": -risk_limits["stop_loss_percentage"] * sum(session["agent_allocations"].values())
            })
        
        return {"violations": violations}
    
    async def _handle_risk_violations(
        self,
        session: Dict[str, Any],
        violations: List[Dict[str, Any]]
    ) -> None:
        """Handle risk limit violations"""
        for violation in violations:
            if violation["type"] == "stop_loss":
                # Stop trading session
                logger.warning(f"Stop loss triggered for session {session['session_id']}")
                await self.stop_farm_trading_session(session["session_id"], close_positions=True)
            elif violation["type"] == "max_exposure":
                # Reduce positions
                logger.warning(f"Max exposure reached for session {session['session_id']}")
                # Would implement position reduction logic
    
    async def _calculate_risk_utilization(self, session: Dict[str, Any]) -> float:
        """Calculate risk utilization percentage"""
        risk_limits = session.get("risk_limits", {})
        total_exposure = sum(p.get("position_value", 0) 
                           for p in session.get("active_positions", []))
        
        max_exposure = risk_limits.get("max_farm_exposure", float('inf'))
        return total_exposure / max_exposure if max_exposure > 0 else 0
    
    async def _calculate_consensus_rate(self, session: Dict[str, Any]) -> float:
        """Calculate consensus rate from coordination events"""
        events = session.get("coordination_events", [])
        if not events:
            return 0
        
        consensus_count = sum(1 for e in events if e.get("consensus_reached", False))
        return consensus_count / len(events)
    
    async def _calculate_avg_decision_time(self, session: Dict[str, Any]) -> str:
        """Calculate average decision time"""
        # Would calculate from coordination event timestamps
        return "00:00:45"  # Mock 45 seconds


def create_multi_agent_farm_trading_coordinator(
    farm_coordination_service,
    real_time_trading_orchestrator,
    farm_performance_service,
    master_wallet_service
):
    """Factory function to create coordinator"""
    return MultiAgentFarmTradingCoordinator(
        farm_coordination_service,
        real_time_trading_orchestrator,
        farm_performance_service,
        master_wallet_service
    )