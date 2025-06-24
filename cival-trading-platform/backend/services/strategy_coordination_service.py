"""
Phase 10: Multi-Strategy Coordination and Arbitrage Detection Service
Advanced agent coordination, conflict resolution, and arbitrage opportunity detection
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import logging
import numpy as np
import pandas as pd
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from enum import Enum
import networkx as nx
from dataclasses import dataclass

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.trading_strategy_models import (
    TradingSignal, TradingStrategy, TradingPosition, MultiAgentCoordination,
    MarketData, PositionSide, SignalStrength, ConflictResolution
)
from services.market_analysis_service import get_market_analysis_service
from services.portfolio_management_service import get_portfolio_management_service
from services.risk_management_service import get_risk_management_service
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class CoordinationStatus(str, Enum):
    """Agent coordination status"""
    ACTIVE = "active"
    PAUSED = "paused"
    CONFLICT = "conflict"
    ARBITRAGE = "arbitrage"
    SYNCHRONIZED = "synchronized"


class ArbitrageType(str, Enum):
    """Types of arbitrage opportunities"""
    SPATIAL = "spatial"          # Price differences across exchanges
    TEMPORAL = "temporal"        # Time-based price inefficiencies
    STATISTICAL = "statistical"  # Mean reversion opportunities
    TRIANGULAR = "triangular"    # Currency/asset triangular arbitrage
    CALENDAR = "calendar"        # Futures contract spreads
    VOLATILITY = "volatility"    # Volatility arbitrage


@dataclass
class AgentState:
    """Agent state tracking"""
    agent_id: str
    strategy_id: str
    status: CoordinationStatus
    active_signals: List[str]
    position_exposure: Dict[str, Decimal]
    last_action: Optional[datetime]
    performance_score: float
    risk_score: float
    coordination_weight: float


class SignalConflict(BaseModel):
    """Signal conflict representation"""
    conflict_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_signals: List[TradingSignal]
    conflict_type: str  # opposing_directions, overlapping_exposure, resource_contention
    severity: str       # low, medium, high, critical
    resolution_method: ConflictResolution
    resolution_action: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    resolved: bool = False


class ArbitrageOpportunity(BaseModel):
    """Arbitrage opportunity detection"""
    opportunity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    arbitrage_type: ArbitrageType
    assets_involved: List[str]
    exchanges_involved: List[str]
    
    # Price information
    price_differential: Decimal
    percentage_spread: float
    expected_profit: Decimal
    execution_cost: Decimal
    net_profit: Decimal
    
    # Risk metrics
    risk_score: float
    confidence: float
    time_window: timedelta
    
    # Execution details
    required_capital: Decimal
    max_position_size: Decimal
    execution_steps: List[Dict[str, Any]]
    
    # Status
    status: str = "detected"  # detected, validated, executing, completed, expired
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    # Performance tracking
    executed_profit: Optional[Decimal] = None
    execution_time: Optional[timedelta] = None


class CoordinationRule(BaseModel):
    """Multi-agent coordination rule"""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    
    # Rule conditions
    applies_to_strategies: List[str] = Field(default_factory=list)  # Empty means all
    symbol_filters: List[str] = Field(default_factory=list)
    
    # Conflict resolution
    conflict_resolution: ConflictResolution
    priority_weights: Dict[str, float] = Field(default_factory=dict)
    
    # Resource allocation
    max_concurrent_signals: int = 5
    max_portfolio_exposure: float = 0.8  # 80%
    max_symbol_exposure: float = 0.3     # 30%
    
    # Performance thresholds
    min_signal_confidence: float = 0.6
    min_strategy_performance: float = 0.1  # 10% minimum return
    
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StrategyCoordinator:
    """Multi-strategy coordination engine"""
    
    def __init__(self):
        self.agent_states: Dict[str, AgentState] = {}
        self.coordination_graph = nx.DiGraph()
        
    def add_agent(self, agent_id: str, strategy_id: str, coordination_weight: float = 1.0):
        """Add agent to coordination"""
        state = AgentState(
            agent_id=agent_id,
            strategy_id=strategy_id,
            status=CoordinationStatus.ACTIVE,
            active_signals=[],
            position_exposure={},
            last_action=None,
            performance_score=0.5,
            risk_score=0.3,
            coordination_weight=coordination_weight
        )
        
        self.agent_states[agent_id] = state
        self.coordination_graph.add_node(agent_id, **state.__dict__)
    
    def detect_signal_conflicts(self, signals: List[TradingSignal]) -> List[SignalConflict]:
        """Detect conflicts between trading signals"""
        conflicts = []
        
        # Group signals by symbol
        symbol_signals = defaultdict(list)
        for signal in signals:
            symbol_signals[signal.symbol].append(signal)
        
        for symbol, symbol_signals_list in symbol_signals.items():
            if len(symbol_signals_list) <= 1:
                continue
            
            # Check for opposing directions
            buy_signals = [s for s in symbol_signals_list if s.signal_type == "buy"]
            sell_signals = [s for s in symbol_signals_list if s.signal_type == "sell"]
            
            if buy_signals and sell_signals:
                conflict = SignalConflict(
                    agent_signals=buy_signals + sell_signals,
                    conflict_type="opposing_directions",
                    severity="high",
                    resolution_method=ConflictResolution.WEIGHTED_AVERAGE
                )
                conflicts.append(conflict)
            
            # Check for overlapping exposure
            elif len(symbol_signals_list) > 1:
                total_exposure = sum(
                    float(s.entry_price or 0) * 0.1  # Estimated position size
                    for s in symbol_signals_list
                )
                
                if total_exposure > 10000:  # Threshold
                    conflict = SignalConflict(
                        agent_signals=symbol_signals_list,
                        conflict_type="overlapping_exposure",
                        severity="medium",
                        resolution_method=ConflictResolution.PRIORITY_BASED
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def resolve_conflicts(self, conflicts: List[SignalConflict]) -> List[TradingSignal]:
        """Resolve signal conflicts and return coordinated signals"""
        resolved_signals = []
        
        for conflict in conflicts:
            if conflict.resolution_method == ConflictResolution.FIRST_COME_FIRST_SERVE:
                # Take earliest signal
                earliest_signal = min(conflict.agent_signals, key=lambda s: s.generated_at)
                resolved_signals.append(earliest_signal)
                
            elif conflict.resolution_method == ConflictResolution.HIGHEST_CONFIDENCE:
                # Take highest confidence signal
                best_signal = max(conflict.agent_signals, key=lambda s: s.confidence)
                resolved_signals.append(best_signal)
                
            elif conflict.resolution_method == ConflictResolution.WEIGHTED_AVERAGE:
                # Create weighted average signal
                averaged_signal = self._create_weighted_average_signal(conflict.agent_signals)
                if averaged_signal:
                    resolved_signals.append(averaged_signal)
                    
            elif conflict.resolution_method == ConflictResolution.PRIORITY_BASED:
                # Use agent performance scores for priority
                scored_signals = [
                    (signal, self.agent_states.get(signal.agent_id, AgentState("", "", CoordinationStatus.ACTIVE, [], {}, None, 0.5, 0.5, 1.0)).performance_score)
                    for signal in conflict.agent_signals
                ]
                best_signal = max(scored_signals, key=lambda x: x[1])[0]
                resolved_signals.append(best_signal)
            
            # Mark conflict as resolved
            conflict.resolved = True
            conflict.resolved_at = datetime.now(timezone.utc)
        
        return resolved_signals
    
    def _create_weighted_average_signal(self, signals: List[TradingSignal]) -> Optional[TradingSignal]:
        """Create weighted average signal from multiple signals"""
        if not signals:
            return None
        
        # Calculate weights based on confidence and agent performance
        weights = []
        for signal in signals:
            agent_perf = self.agent_states.get(signal.agent_id, 
                AgentState("", "", CoordinationStatus.ACTIVE, [], {}, None, 0.5, 0.5, 1.0)).performance_score
            weight = signal.confidence * agent_perf
            weights.append(weight)
        
        total_weight = sum(weights)
        if total_weight == 0:
            return signals[0]  # Fallback to first signal
        
        # Weighted averages
        avg_confidence = sum(s.confidence * w for s, w in zip(signals, weights)) / total_weight
        
        # For prices, only average if they're close (within 5%)
        prices = [float(s.entry_price) for s in signals if s.entry_price]
        if prices and (max(prices) - min(prices)) / np.mean(prices) < 0.05:
            avg_price = sum(p * w for p, w in zip(prices, weights)) / total_weight
        else:
            # Take price from highest confidence signal if spread too wide
            best_signal = max(signals, key=lambda s: s.confidence)
            avg_price = float(best_signal.entry_price) if best_signal.entry_price else None
        
        # Take majority signal type
        buy_weight = sum(w for s, w in zip(signals, weights) if s.signal_type == "buy")
        sell_weight = sum(w for s, w in zip(signals, weights) if s.signal_type == "sell")
        signal_type = "buy" if buy_weight > sell_weight else "sell"
        
        # Create averaged signal
        base_signal = signals[0]
        return TradingSignal(
            strategy_id="coordinated",
            agent_id="strategy_coordinator",
            symbol=base_signal.symbol,
            signal_type=signal_type,
            strength=base_signal.strength,
            confidence=avg_confidence,
            entry_price=Decimal(str(avg_price)) if avg_price else None,
            target_price=base_signal.target_price,
            stop_loss=base_signal.stop_loss,
            position_side=base_signal.position_side,
            timeframe=base_signal.timeframe,
            market_condition=base_signal.market_condition
        )


class ArbitrageDetector:
    """Advanced arbitrage opportunity detector"""
    
    def __init__(self):
        self.price_feeds: Dict[str, Dict[str, MarketData]] = defaultdict(dict)  # exchange -> symbol -> data
        self.opportunity_cache: Dict[str, ArbitrageOpportunity] = {}
        
    async def detect_spatial_arbitrage(
        self, 
        symbols: List[str], 
        exchanges: List[str] = None
    ) -> List[ArbitrageOpportunity]:
        """Detect spatial arbitrage opportunities across exchanges"""
        if not exchanges:
            exchanges = ["binance", "coinbase", "kraken"]  # Default exchanges
        
        opportunities = []
        
        for symbol in symbols:
            # Get prices from different exchanges
            exchange_prices = {}
            for exchange in exchanges:
                if exchange in self.price_feeds and symbol in self.price_feeds[exchange]:
                    market_data = self.price_feeds[exchange][symbol]
                    exchange_prices[exchange] = float(market_data.close)
            
            if len(exchange_prices) < 2:
                continue
            
            # Find price differentials
            min_exchange = min(exchange_prices, key=exchange_prices.get)
            max_exchange = max(exchange_prices, key=exchange_prices.get)
            
            min_price = exchange_prices[min_exchange]
            max_price = exchange_prices[max_exchange]
            
            spread = (max_price - min_price) / min_price
            
            # Check if spread is significant enough (> 0.5% after costs)
            execution_cost = 0.002  # 0.2% total execution cost
            if spread > execution_cost + 0.005:  # 0.5% minimum profit
                
                # Calculate opportunity details
                trade_size = Decimal("1000")  # $1000 trade size
                gross_profit = trade_size * Decimal(str(spread))
                execution_cost_amount = trade_size * Decimal(str(execution_cost))
                net_profit = gross_profit - execution_cost_amount
                
                opportunity = ArbitrageOpportunity(
                    arbitrage_type=ArbitrageType.SPATIAL,
                    assets_involved=[symbol],
                    exchanges_involved=[min_exchange, max_exchange],
                    price_differential=Decimal(str(max_price - min_price)),
                    percentage_spread=spread * 100,
                    expected_profit=gross_profit,
                    execution_cost=execution_cost_amount,
                    net_profit=net_profit,
                    risk_score=0.3,  # Relatively low risk
                    confidence=0.8,
                    time_window=timedelta(minutes=5),
                    required_capital=trade_size * 2,  # Need capital on both exchanges
                    max_position_size=trade_size,
                    execution_steps=[
                        {"action": "buy", "exchange": min_exchange, "amount": float(trade_size), "price": min_price},
                        {"action": "sell", "exchange": max_exchange, "amount": float(trade_size), "price": max_price}
                    ],
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
                )
                
                opportunities.append(opportunity)
                self.opportunity_cache[opportunity.opportunity_id] = opportunity
        
        return opportunities
    
    async def detect_triangular_arbitrage(
        self, 
        base_currency: str = "USD",
        exchange: str = "binance"
    ) -> List[ArbitrageOpportunity]:
        """Detect triangular arbitrage opportunities"""
        opportunities = []
        
        # Common trading pairs for triangular arbitrage
        currencies = ["BTC", "ETH", "ADA", "SOL"]
        
        for curr_a in currencies:
            for curr_b in currencies:
                if curr_a == curr_b:
                    continue
                
                # Check triangular path: USD -> A -> B -> USD
                pair_1 = f"{curr_a}{base_currency}"  # USD to A
                pair_2 = f"{curr_b}{curr_a}"         # A to B  
                pair_3 = f"{base_currency}{curr_b}"  # B to USD
                
                # Get prices (simplified - would need real exchange data)
                if not all(pair in self.price_feeds.get(exchange, {}) 
                          for pair in [pair_1, pair_2, pair_3]):
                    continue
                
                price_1 = 1 / float(self.price_feeds[exchange][pair_1].close)  # USD -> A
                price_2 = float(self.price_feeds[exchange][pair_2].close)      # A -> B
                price_3 = float(self.price_feeds[exchange][pair_3].close)      # B -> USD
                
                # Calculate arbitrage profit
                final_amount = 1.0 * price_1 * price_2 * price_3
                profit_ratio = final_amount - 1.0
                
                # Account for transaction fees (0.1% per trade * 3 trades)
                fee_cost = 0.003
                net_profit_ratio = profit_ratio - fee_cost
                
                if net_profit_ratio > 0.005:  # 0.5% minimum profit
                    trade_amount = Decimal("1000")
                    profit_amount = trade_amount * Decimal(str(net_profit_ratio))
                    
                    opportunity = ArbitrageOpportunity(
                        arbitrage_type=ArbitrageType.TRIANGULAR,
                        assets_involved=[curr_a, curr_b, base_currency],
                        exchanges_involved=[exchange],
                        price_differential=Decimal(str(abs(final_amount - 1.0))),
                        percentage_spread=profit_ratio * 100,
                        expected_profit=profit_amount,
                        execution_cost=trade_amount * Decimal(str(fee_cost)),
                        net_profit=profit_amount,
                        risk_score=0.4,
                        confidence=0.7,
                        time_window=timedelta(minutes=2),
                        required_capital=trade_amount,
                        max_position_size=trade_amount,
                        execution_steps=[
                            {"action": "buy", "pair": pair_1, "amount": 1.0},
                            {"action": "buy", "pair": pair_2, "amount": price_1},
                            {"action": "buy", "pair": pair_3, "amount": price_1 * price_2}
                        ],
                        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2)
                    )
                    
                    opportunities.append(opportunity)
        
        return opportunities
    
    async def detect_statistical_arbitrage(
        self, 
        symbols: List[str],
        lookback_period: int = 100
    ) -> List[ArbitrageOpportunity]:
        """Detect statistical arbitrage opportunities (pairs trading)"""
        opportunities = []
        
        # Get historical price data for correlation analysis
        price_data = {}
        for symbol in symbols:
            # Would fetch historical data - simplified here
            price_data[symbol] = np.random.normal(100, 10, lookback_period).cumsum()
        
        # Find highly correlated pairs
        for i, symbol_a in enumerate(symbols):
            for symbol_b in symbols[i+1:]:
                if symbol_a == symbol_b:
                    continue
                
                # Calculate correlation
                correlation = np.corrcoef(price_data[symbol_a], price_data[symbol_b])[0, 1]
                
                if abs(correlation) > 0.8:  # High correlation threshold
                    # Calculate current spread
                    current_a = price_data[symbol_a][-1]
                    current_b = price_data[symbol_b][-1]
                    
                    # Calculate historical spread statistics
                    spread_series = np.array(price_data[symbol_a]) - np.array(price_data[symbol_b])
                    spread_mean = np.mean(spread_series)
                    spread_std = np.std(spread_series)
                    
                    current_spread = current_a - current_b
                    z_score = (current_spread - spread_mean) / spread_std
                    
                    # Signal when spread is > 2 standard deviations from mean
                    if abs(z_score) > 2.0:
                        expected_reversion = spread_mean - current_spread
                        confidence = min(0.9, abs(z_score) / 3.0)
                        
                        trade_amount = Decimal("500")  # $500 per leg
                        profit_amount = trade_amount * Decimal(str(abs(expected_reversion) / current_a))
                        
                        opportunity = ArbitrageOpportunity(
                            arbitrage_type=ArbitrageType.STATISTICAL,
                            assets_involved=[symbol_a, symbol_b],
                            exchanges_involved=["primary"],
                            price_differential=Decimal(str(abs(expected_reversion))),
                            percentage_spread=abs(z_score) * 10,  # Scaled representation
                            expected_profit=profit_amount,
                            execution_cost=trade_amount * Decimal("0.002"),
                            net_profit=profit_amount * Decimal("0.98"),
                            risk_score=0.6,  # Higher risk for stat arb
                            confidence=confidence,
                            time_window=timedelta(days=5),  # Longer holding period
                            required_capital=trade_amount * 2,
                            max_position_size=trade_amount,
                            execution_steps=[
                                {"action": "long" if z_score < 0 else "short", "symbol": symbol_a, "amount": float(trade_amount)},
                                {"action": "short" if z_score < 0 else "long", "symbol": symbol_b, "amount": float(trade_amount)}
                            ],
                            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
                        )
                        
                        opportunities.append(opportunity)
        
        return opportunities


class StrategyCoordinationService:
    """
    Multi-strategy coordination and arbitrage detection service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
        # Coordination components
        self.coordinator = StrategyCoordinator()
        self.arbitrage_detector = ArbitrageDetector()
        
        # Coordination state
        self.coordination_rules: Dict[str, CoordinationRule] = {}
        self.active_conflicts: Dict[str, SignalConflict] = {}
        self.active_opportunities: Dict[str, ArbitrageOpportunity] = {}
        
        # Agent management
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_signals: Dict[str, List[TradingSignal]] = defaultdict(list)
        
        # Performance tracking
        self.coordination_metrics: Dict[str, Any] = {}
        self.arbitrage_history: List[ArbitrageOpportunity] = []
        
        # Configuration
        self.coordination_interval = 30      # 30 seconds
        self.arbitrage_scan_interval = 60   # 1 minute
        self.conflict_resolution_timeout = 10  # 10 seconds
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the strategy coordination service"""
        try:
            logger.info("Initializing Strategy Coordination Service...")
            
            # Load coordination rules
            await self._load_coordination_rules()
            
            # Register active agents
            await self._register_active_agents()
            
            # Load historical arbitrage data
            await self._load_arbitrage_history()
            
            # Start background tasks
            asyncio.create_task(self._coordination_loop())
            asyncio.create_task(self._arbitrage_detection_loop())
            asyncio.create_task(self._conflict_resolution_loop())
            asyncio.create_task(self._opportunity_validation_loop())
            
            logger.info("Strategy Coordination Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Strategy Coordination Service: {e}")
            raise
    
    async def coordinate_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Coordinate multiple trading signals to resolve conflicts"""
        try:
            logger.info(f"Coordinating {len(signals)} trading signals")
            
            # Update agent signal tracking
            for signal in signals:
                self.agent_signals[signal.agent_id].append(signal)
                
                # Keep only recent signals (last hour)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
                self.agent_signals[signal.agent_id] = [
                    s for s in self.agent_signals[signal.agent_id] 
                    if s.generated_at > cutoff_time
                ]
            
            # Detect conflicts
            conflicts = self.coordinator.detect_signal_conflicts(signals)
            
            if conflicts:
                logger.info(f"Detected {len(conflicts)} signal conflicts")
                
                # Store conflicts
                for conflict in conflicts:
                    self.active_conflicts[conflict.conflict_id] = conflict
                
                # Resolve conflicts
                coordinated_signals = self.coordinator.resolve_conflicts(conflicts)
                
                # Update coordination metrics
                await self._update_coordination_metrics(signals, coordinated_signals, conflicts)
                
                return coordinated_signals
            else:
                return signals
                
        except Exception as e:
            logger.error(f"Failed to coordinate signals: {e}")
            return signals  # Return original signals if coordination fails
    
    async def detect_arbitrage_opportunities(
        self, 
        symbols: List[str] = None,
        arbitrage_types: List[ArbitrageType] = None
    ) -> List[ArbitrageOpportunity]:
        """Detect various types of arbitrage opportunities"""
        try:
            if not symbols:
                symbols = ["BTCUSD", "ETHUSD", "ADAUSD", "SOLUSD"]
            
            if not arbitrage_types:
                arbitrage_types = [ArbitrageType.SPATIAL, ArbitrageType.TRIANGULAR, ArbitrageType.STATISTICAL]
            
            all_opportunities = []
            
            # Detect different types of arbitrage
            for arb_type in arbitrage_types:
                if arb_type == ArbitrageType.SPATIAL:
                    opportunities = await self.arbitrage_detector.detect_spatial_arbitrage(symbols)
                elif arb_type == ArbitrageType.TRIANGULAR:
                    opportunities = await self.arbitrage_detector.detect_triangular_arbitrage()
                elif arb_type == ArbitrageType.STATISTICAL:
                    opportunities = await self.arbitrage_detector.detect_statistical_arbitrage(symbols)
                else:
                    continue
                
                all_opportunities.extend(opportunities)
            
            # Rank opportunities by expected profit and confidence
            ranked_opportunities = sorted(
                all_opportunities,
                key=lambda o: float(o.net_profit) * o.confidence,
                reverse=True
            )
            
            # Store active opportunities
            for opportunity in ranked_opportunities[:10]:  # Keep top 10
                self.active_opportunities[opportunity.opportunity_id] = opportunity
                await self._save_arbitrage_opportunity(opportunity)
            
            logger.info(f"Detected {len(ranked_opportunities)} arbitrage opportunities")
            
            return ranked_opportunities
            
        except Exception as e:
            logger.error(f"Failed to detect arbitrage opportunities: {e}")
            return []
    
    async def register_agent(
        self, 
        agent_id: str, 
        strategy_id: str, 
        coordination_params: Dict[str, Any] = None
    ) -> bool:
        """Register trading agent for coordination"""
        try:
            # Add to coordinator
            coordination_weight = coordination_params.get("weight", 1.0) if coordination_params else 1.0
            self.coordinator.add_agent(agent_id, strategy_id, coordination_weight)
            
            # Store agent information
            self.registered_agents[agent_id] = {
                "strategy_id": strategy_id,
                "registered_at": datetime.now(timezone.utc),
                "coordination_params": coordination_params or {},
                "status": "active"
            }
            
            logger.info(f"Registered agent {agent_id} for strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    async def execute_arbitrage_opportunity(
        self, 
        opportunity_id: str,
        portfolio_id: str,
        auto_execute: bool = False
    ) -> Dict[str, Any]:
        """Execute an arbitrage opportunity"""
        try:
            opportunity = self.active_opportunities.get(opportunity_id)
            if not opportunity:
                return {"status": "error", "message": "Opportunity not found"}
            
            if opportunity.status != "detected":
                return {"status": "error", "message": f"Opportunity status is {opportunity.status}"}
            
            # Validate opportunity is still valid
            if opportunity.expires_at and datetime.now(timezone.utc) > opportunity.expires_at:
                opportunity.status = "expired"
                return {"status": "error", "message": "Opportunity has expired"}
            
            # Risk validation
            risk_service = await get_risk_management_service()
            portfolio_service = await get_portfolio_management_service()
            
            # Check available capital
            portfolio_analytics = await portfolio_service.get_portfolio_analytics(portfolio_id)
            if "error" in portfolio_analytics:
                return {"status": "error", "message": "Portfolio not found"}
            
            available_capital = Decimal(str(portfolio_analytics["available_capital"]))
            if available_capital < opportunity.required_capital:
                return {"status": "error", "message": "Insufficient capital"}
            
            # Update opportunity status
            opportunity.status = "executing"
            execution_start = datetime.now(timezone.utc)
            
            # Execute arbitrage steps (simplified - would integrate with live trading service)
            execution_results = []
            total_executed_profit = Decimal("0")
            
            for step in opportunity.execution_steps:
                # This would execute actual trades through the live trading service
                execution_result = {
                    "step": step,
                    "status": "simulated",  # Would be "executed" in live trading
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "profit": float(opportunity.net_profit) / len(opportunity.execution_steps)
                }
                execution_results.append(execution_result)
                total_executed_profit += opportunity.net_profit / len(opportunity.execution_steps)
            
            # Update opportunity with execution results
            opportunity.status = "completed"
            opportunity.executed_profit = total_executed_profit
            opportunity.execution_time = datetime.now(timezone.utc) - execution_start
            
            # Add to history
            self.arbitrage_history.append(opportunity)
            
            # Update metrics
            await self._update_arbitrage_metrics(opportunity)
            
            logger.info(f"Executed arbitrage opportunity {opportunity_id} with profit: {total_executed_profit}")
            
            return {
                "status": "executed",
                "opportunity_id": opportunity_id,
                "executed_profit": float(total_executed_profit),
                "execution_time": opportunity.execution_time.total_seconds(),
                "execution_steps": execution_results
            }
            
        except Exception as e:
            logger.error(f"Failed to execute arbitrage opportunity {opportunity_id}: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_coordination_analytics(self) -> Dict[str, Any]:
        """Get coordination and arbitrage analytics"""
        try:
            # Coordination metrics
            total_agents = len(self.registered_agents)
            active_conflicts = len([c for c in self.active_conflicts.values() if not c.resolved])
            total_signals_coordinated = sum(len(signals) for signals in self.agent_signals.values())
            
            # Arbitrage metrics
            total_opportunities = len(self.arbitrage_history)
            successful_arbitrages = len([o for o in self.arbitrage_history if o.status == "completed"])
            total_arbitrage_profit = sum(
                float(o.executed_profit or 0) for o in self.arbitrage_history 
                if o.executed_profit
            )
            
            # Recent performance
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_opportunities = [
                o for o in self.arbitrage_history 
                if o.detected_at > recent_cutoff
            ]
            
            # Agent performance
            agent_performance = {}
            for agent_id, agent_info in self.registered_agents.items():
                agent_state = self.coordinator.agent_states.get(agent_id)
                if agent_state:
                    agent_performance[agent_id] = {
                        "performance_score": agent_state.performance_score,
                        "risk_score": agent_state.risk_score,
                        "active_signals": len(agent_state.active_signals),
                        "coordination_weight": agent_state.coordination_weight
                    }
            
            return {
                "coordination_summary": {
                    "total_agents": total_agents,
                    "active_conflicts": active_conflicts,
                    "signals_coordinated": total_signals_coordinated,
                    "coordination_efficiency": 1.0 - (active_conflicts / max(1, total_signals_coordinated))
                },
                "arbitrage_summary": {
                    "total_opportunities": total_opportunities,
                    "successful_executions": successful_arbitrages,
                    "success_rate": successful_arbitrages / max(1, total_opportunities),
                    "total_profit": total_arbitrage_profit,
                    "recent_opportunities": len(recent_opportunities)
                },
                "agent_performance": agent_performance,
                "active_opportunities": len(self.active_opportunities),
                "coordination_rules": len(self.coordination_rules)
            }
            
        except Exception as e:
            logger.error(f"Failed to get coordination analytics: {e}")
            return {"error": str(e)}
    
    # Background monitoring loops
    
    async def _coordination_loop(self):
        """Main coordination monitoring loop"""
        while not self._shutdown:
            try:
                # Check for new conflicts
                all_recent_signals = []
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
                
                for signals in self.agent_signals.values():
                    recent_signals = [s for s in signals if s.generated_at > cutoff_time]
                    all_recent_signals.extend(recent_signals)
                
                if all_recent_signals:
                    conflicts = self.coordinator.detect_signal_conflicts(all_recent_signals)
                    for conflict in conflicts:
                        if conflict.conflict_id not in self.active_conflicts:
                            self.active_conflicts[conflict.conflict_id] = conflict
                
                await asyncio.sleep(self.coordination_interval)
                
            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(self.coordination_interval)
    
    async def _arbitrage_detection_loop(self):
        """Arbitrage opportunity detection loop"""
        while not self._shutdown:
            try:
                # Detect new arbitrage opportunities
                opportunities = await self.detect_arbitrage_opportunities()
                
                # Clean up expired opportunities
                current_time = datetime.now(timezone.utc)
                expired_ids = [
                    opp_id for opp_id, opp in self.active_opportunities.items()
                    if opp.expires_at and current_time > opp.expires_at
                ]
                
                for opp_id in expired_ids:
                    self.active_opportunities[opp_id].status = "expired"
                    del self.active_opportunities[opp_id]
                
                await asyncio.sleep(self.arbitrage_scan_interval)
                
            except Exception as e:
                logger.error(f"Error in arbitrage detection loop: {e}")
                await asyncio.sleep(self.arbitrage_scan_interval)
    
    async def _conflict_resolution_loop(self):
        """Conflict resolution processing loop"""
        while not self._shutdown:
            try:
                # Process unresolved conflicts
                unresolved_conflicts = [
                    conflict for conflict in self.active_conflicts.values()
                    if not conflict.resolved
                ]
                
                for conflict in unresolved_conflicts:
                    # Check if conflict has timed out
                    if (datetime.now(timezone.utc) - conflict.created_at).total_seconds() > self.conflict_resolution_timeout:
                        # Auto-resolve using highest confidence
                        conflict.resolution_method = ConflictResolution.HIGHEST_CONFIDENCE
                        resolved_signals = self.coordinator.resolve_conflicts([conflict])
                        
                        logger.info(f"Auto-resolved conflict {conflict.conflict_id}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in conflict resolution loop: {e}")
                await asyncio.sleep(10)
    
    async def _opportunity_validation_loop(self):
        """Arbitrage opportunity validation loop"""
        while not self._shutdown:
            try:
                # Validate active opportunities are still profitable
                for opportunity in list(self.active_opportunities.values()):
                    if opportunity.status == "detected":
                        # Re-validate opportunity (simplified)
                        if opportunity.confidence < 0.5:
                            opportunity.status = "invalid"
                            logger.info(f"Invalidated opportunity {opportunity.opportunity_id}")
                
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Error in opportunity validation loop: {e}")
                await asyncio.sleep(120)
    
    # Helper methods
    
    async def _update_coordination_metrics(
        self, 
        original_signals: List[TradingSignal],
        coordinated_signals: List[TradingSignal],
        conflicts: List[SignalConflict]
    ):
        """Update coordination performance metrics"""
        self.coordination_metrics["last_coordination"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_signals": len(original_signals),
            "coordinated_signals": len(coordinated_signals),
            "conflicts_resolved": len(conflicts),
            "efficiency": len(coordinated_signals) / max(1, len(original_signals))
        }
    
    # Additional helper methods would be implemented here...


# Global service instance
_strategy_coordination_service: Optional[StrategyCoordinationService] = None


async def get_strategy_coordination_service() -> StrategyCoordinationService:
    """Get the global strategy coordination service instance"""
    global _strategy_coordination_service
    
    if _strategy_coordination_service is None:
        _strategy_coordination_service = StrategyCoordinationService()
        await _strategy_coordination_service.initialize()
    
    return _strategy_coordination_service


@asynccontextmanager
async def strategy_coordination_context():
    """Context manager for strategy coordination service"""
    service = await get_strategy_coordination_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass