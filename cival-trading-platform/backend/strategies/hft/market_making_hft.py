"""
Market Making HFT Strategy - Ultra-Low Latency Implementation
High-frequency market making strategy with agent coordination and real-time optimization
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import numpy as np
import pandas as pd
from loguru import logger
from dataclasses import dataclass
from enum import Enum

from ..base_strategy import BaseStrategy
from ...models.trading_strategy_models import SignalType, TradingSignal
from ...models.agent_models import AgentDecision, AgentRecommendation


class MarketSide(Enum):
    BID = "bid"
    ASK = "ask"
    BOTH = "both"


@dataclass
class PricingRecommendation:
    """Pricing recommendation from pricing agent"""
    signal: str
    bid_price: Optional[float]
    ask_price: Optional[float]
    spread: float
    confidence: float
    volatility_adjustment: float
    market_impact_estimate: float


@dataclass
class InventoryRecommendation:
    """Inventory management recommendation"""
    can_buy: bool
    can_sell: bool
    inventory_delta: float
    target_adjustment: float
    urgency_level: float
    status: str


@dataclass
class RiskAssessment:
    """Risk assessment from risk management agent"""
    risk_level: float
    max_position_allowed: float
    stop_loss_price: Optional[float]
    position_sizing_multiplier: float
    emergency_exit_required: bool
    risk_factors: List[str]


class PricingAgent:
    """Specialized pricing optimization agent for market making"""
    
    def __init__(self, strategy_id: str, min_spread: float, volatility_adjustment: bool = True):
        self.strategy_id = strategy_id
        self.min_spread = min_spread
        self.volatility_adjustment = volatility_adjustment
        self.pricing_history = []
        self.volatility_model = VolatilityModel()
        
    async def analyze_pricing_opportunity(self, symbol: str, market_data: pd.DataFrame) -> PricingRecommendation:
        """Analyze optimal pricing for market making"""
        
        try:
            if len(market_data) < 5:
                return PricingRecommendation(
                    signal="HOLD",
                    bid_price=None,
                    ask_price=None,
                    spread=self.min_spread,
                    confidence=0.0,
                    volatility_adjustment=0.0,
                    market_impact_estimate=0.0
                )
            
            # Get current price and calculate base spread
            current_price = float(market_data['close'].iloc[-1])
            
            # Calculate realized volatility
            returns = market_data['close'].pct_change().dropna()
            realized_vol = returns.std() * np.sqrt(252 * 24 * 60)  # Annualized minute-level volatility
            
            # Volatility-adjusted spread
            vol_adjustment = realized_vol * 0.5 if self.volatility_adjustment else 0.0
            adjusted_spread = max(self.min_spread, self.min_spread + vol_adjustment)
            
            # Calculate optimal bid/ask prices
            half_spread = adjusted_spread / 2
            optimal_bid = current_price - half_spread
            optimal_ask = current_price + half_spread
            
            # Estimate market impact
            volume_profile = market_data['volume'].rolling(window=5).mean()
            current_volume = float(market_data['volume'].iloc[-1])
            volume_ratio = current_volume / float(volume_profile.iloc[-1]) if volume_profile.iloc[-1] > 0 else 1.0
            
            market_impact = min(0.001, adjusted_spread * 0.1 * volume_ratio)
            
            # Determine signal based on spread opportunity
            signal = "BUY" if adjusted_spread > self.min_spread * 1.2 else "SELL" if adjusted_spread < self.min_spread * 0.8 else "BOTH"
            
            # Calculate confidence based on volatility and spread
            confidence = min(0.95, max(0.3, 1.0 - (realized_vol * 10)))
            
            recommendation = PricingRecommendation(
                signal=signal,
                bid_price=optimal_bid,
                ask_price=optimal_ask,
                spread=adjusted_spread,
                confidence=confidence,
                volatility_adjustment=vol_adjustment,
                market_impact_estimate=market_impact
            )
            
            # Store for learning
            self.pricing_history.append({
                "timestamp": datetime.now(timezone.utc),
                "symbol": symbol,
                "recommendation": recommendation,
                "realized_volatility": realized_vol
            })
            
            # Keep only recent history
            if len(self.pricing_history) > 1000:
                self.pricing_history = self.pricing_history[-500:]
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Pricing analysis failed for {symbol}: {e}")
            return PricingRecommendation(
                signal="HOLD",
                bid_price=None,
                ask_price=None,
                spread=self.min_spread,
                confidence=0.0,
                volatility_adjustment=0.0,
                market_impact_estimate=0.0
            )


class InventoryManagementAgent:
    """Inventory management agent for position optimization"""
    
    def __init__(self, strategy_id: str, target_inventory: float, max_position: float):
        self.strategy_id = strategy_id
        self.target_inventory = target_inventory
        self.max_position = max_position
        self.inventory_history = []
        
    async def assess_inventory_needs(self, symbol: str, current_position: float) -> InventoryRecommendation:
        """Assess inventory management needs"""
        
        try:
            # Calculate inventory deviation from target
            inventory_deviation = current_position - self.target_inventory
            deviation_ratio = abs(inventory_deviation) / self.max_position if self.max_position > 0 else 0
            
            # Determine position limits
            can_buy = current_position < self.max_position * 0.9
            can_sell = current_position > -self.max_position * 0.9
            
            # Calculate urgency based on deviation
            urgency_level = min(1.0, deviation_ratio * 2)
            
            # Determine target adjustment
            if deviation_ratio > 0.7:
                # High deviation - urgent rebalancing needed
                target_adjustment = -inventory_deviation * 0.5
                status = "URGENT_REBALANCE"
            elif deviation_ratio > 0.3:
                # Moderate deviation - gradual rebalancing
                target_adjustment = -inventory_deviation * 0.2
                status = "GRADUAL_REBALANCE"
            else:
                # Low deviation - normal operation
                target_adjustment = 0.0
                status = "NORMAL"
            
            # Adjust buy/sell permissions based on inventory needs
            if inventory_deviation > self.max_position * 0.5:
                can_buy = False  # Too long, prioritize selling
            elif inventory_deviation < -self.max_position * 0.5:
                can_sell = False  # Too short, prioritize buying
            
            recommendation = InventoryRecommendation(
                can_buy=can_buy,
                can_sell=can_sell,
                inventory_delta=inventory_deviation,
                target_adjustment=target_adjustment,
                urgency_level=urgency_level,
                status=status
            )
            
            # Store inventory tracking
            self.inventory_history.append({
                "timestamp": datetime.now(timezone.utc),
                "symbol": symbol,
                "position": current_position,
                "deviation": inventory_deviation,
                "recommendation": recommendation
            })
            
            # Keep recent history
            if len(self.inventory_history) > 1000:
                self.inventory_history = self.inventory_history[-500:]
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Inventory assessment failed for {symbol}: {e}")
            return InventoryRecommendation(
                can_buy=False,
                can_sell=False,
                inventory_delta=0.0,
                target_adjustment=0.0,
                urgency_level=1.0,
                status="ERROR"
            )


class RiskManagementAgent:
    """Risk management agent for real-time risk assessment"""
    
    def __init__(self, strategy_id: str, max_drawdown: float, stop_loss_multiplier: float):
        self.strategy_id = strategy_id
        self.max_drawdown = max_drawdown
        self.stop_loss_multiplier = stop_loss_multiplier
        self.risk_history = []
        self.drawdown_tracker = DrawdownTracker()
        
    async def evaluate_risk_exposure(self, symbol: str, market_data: pd.DataFrame, current_position: float) -> RiskAssessment:
        """Evaluate current risk exposure"""
        
        try:
            if len(market_data) < 10:
                return RiskAssessment(
                    risk_level=1.0,
                    max_position_allowed=0.0,
                    stop_loss_price=None,
                    position_sizing_multiplier=0.0,
                    emergency_exit_required=True,
                    risk_factors=["insufficient_data"]
                )
            
            # Calculate various risk metrics
            current_price = float(market_data['close'].iloc[-1])
            returns = market_data['close'].pct_change().dropna()
            
            # Volatility risk
            volatility = returns.std() * np.sqrt(252 * 24 * 60)
            vol_risk = min(1.0, volatility / 0.5)  # Normalize against 50% annual vol
            
            # Drawdown risk
            current_drawdown = self.drawdown_tracker.calculate_current_drawdown(market_data)
            drawdown_risk = min(1.0, current_drawdown / self.max_drawdown)
            
            # Position concentration risk
            position_value = abs(current_position * current_price)
            concentration_risk = min(1.0, position_value / 100000)  # Normalize against $100K
            
            # Composite risk score
            risk_level = max(vol_risk, drawdown_risk, concentration_risk)
            
            # Calculate position sizing
            if risk_level < 0.3:
                position_multiplier = 1.0
            elif risk_level < 0.6:
                position_multiplier = 0.7
            elif risk_level < 0.8:
                position_multiplier = 0.4
            else:
                position_multiplier = 0.1
            
            # Maximum position allowed
            base_max_position = 10000  # Base maximum position
            max_position_allowed = base_max_position * position_multiplier
            
            # Stop loss calculation
            if current_position != 0:
                volatility_stop = volatility * self.stop_loss_multiplier
                if current_position > 0:
                    stop_loss_price = current_price * (1 - volatility_stop)
                else:
                    stop_loss_price = current_price * (1 + volatility_stop)
            else:
                stop_loss_price = None
            
            # Emergency exit conditions
            emergency_exit_required = (
                risk_level > 0.9 or
                current_drawdown > self.max_drawdown * 0.8 or
                volatility > 1.0
            )
            
            # Risk factors identification
            risk_factors = []
            if vol_risk > 0.7:
                risk_factors.append("high_volatility")
            if drawdown_risk > 0.7:
                risk_factors.append("excessive_drawdown")
            if concentration_risk > 0.7:
                risk_factors.append("position_concentration")
            
            assessment = RiskAssessment(
                risk_level=risk_level,
                max_position_allowed=max_position_allowed,
                stop_loss_price=stop_loss_price,
                position_sizing_multiplier=position_multiplier,
                emergency_exit_required=emergency_exit_required,
                risk_factors=risk_factors
            )
            
            # Store risk tracking
            self.risk_history.append({
                "timestamp": datetime.now(timezone.utc),
                "symbol": symbol,
                "risk_level": risk_level,
                "assessment": assessment
            })
            
            # Keep recent history
            if len(self.risk_history) > 1000:
                self.risk_history = self.risk_history[-500:]
            
            return assessment
            
        except Exception as e:
            logger.error(f"Risk evaluation failed for {symbol}: {e}")
            return RiskAssessment(
                risk_level=1.0,
                max_position_allowed=0.0,
                stop_loss_price=None,
                position_sizing_multiplier=0.0,
                emergency_exit_required=True,
                risk_factors=["evaluation_error"]
            )


class VolatilityModel:
    """Simple volatility estimation model"""
    
    def __init__(self, window: int = 20):
        self.window = window
        
    def estimate_volatility(self, price_series: pd.Series) -> float:
        """Estimate current volatility"""
        returns = price_series.pct_change().dropna()
        if len(returns) < 2:
            return 0.01  # Default low volatility
        
        return returns.rolling(window=min(len(returns), self.window)).std().iloc[-1]


class DrawdownTracker:
    """Drawdown tracking utility"""
    
    def __init__(self):
        self.peak_price = None
        
    def calculate_current_drawdown(self, market_data: pd.DataFrame) -> float:
        """Calculate current drawdown"""
        prices = market_data['close']
        
        # Calculate running maximum
        running_max = prices.expanding().max()
        
        # Calculate drawdown
        drawdown = (prices - running_max) / running_max
        
        return abs(float(drawdown.iloc[-1]))


class MarketMakingHFTStrategy(BaseStrategy):
    """
    Ultra-low latency market making strategy with agent coordination
    """
    
    def __init__(self, **params):
        super().__init__(
            strategy_name="Market Making HFT",
            strategy_type="market_making_hft",
            parameters=params
        )
        
        # HFT-specific parameters
        self.min_spread = params.get('min_spread', 0.0001)
        self.max_position = params.get('max_position', 10000)
        self.inventory_target = params.get('inventory_target', 0)
        self.risk_multiplier = params.get('risk_multiplier', 1.5)
        self.execution_latency_target = params.get('latency_target_ms', 1.0)
        
        # Agent coordination
        self.pricing_agent = None
        self.inventory_agent = None
        self.risk_agent = None
        
        # Performance tracking
        self.trades_per_second = 0
        self.fill_rate = 0.0
        self.inventory_turnover = 0.0
        self.current_position = 0.0
        
        # Execution metrics
        self.execution_times = []
        self.spread_captures = []
        self.adverse_selections = []
        
    async def initialize_agent_farm(self):
        """Initialize specialized agents for market making"""
        
        try:
            self.pricing_agent = PricingAgent(
                strategy_id=self.strategy_id,
                min_spread=self.min_spread,
                volatility_adjustment=True
            )
            
            self.inventory_agent = InventoryManagementAgent(
                strategy_id=self.strategy_id,
                target_inventory=self.inventory_target,
                max_position=self.max_position
            )
            
            self.risk_agent = RiskManagementAgent(
                strategy_id=self.strategy_id,
                max_drawdown=0.02,
                stop_loss_multiplier=self.risk_multiplier
            )
            
            logger.info(f"Market making agent farm initialized for strategy {self.strategy_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent farm: {e}")
            raise
    
    async def _generate_signal_internal(self, symbol: str, timeframe: str) -> Tuple[SignalType, Optional[float], Dict[str, Any]]:
        """Generate market making signals with agent coordination"""
        
        try:
            # Ensure agents are initialized
            if not all([self.pricing_agent, self.inventory_agent, self.risk_agent]):
                await self.initialize_agent_farm()
            
            # Get market data
            market_data = self.get_market_data(symbol, timeframe)
            if market_data is None or len(market_data) < 10:
                return SignalType.HOLD, 0.0, {"reason": "insufficient_data"}
            
            start_time = datetime.now(timezone.utc)
            
            # Agent coordination for signal generation
            pricing_recommendation = await self.pricing_agent.analyze_pricing_opportunity(
                symbol, market_data
            )
            
            inventory_recommendation = await self.inventory_agent.assess_inventory_needs(
                symbol, self.current_position
            )
            
            risk_assessment = await self.risk_agent.evaluate_risk_exposure(
                symbol, market_data, self.current_position
            )
            
            # Calculate coordination latency
            coordination_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Emergency exit check
            if risk_assessment.emergency_exit_required:
                return SignalType.SELL if self.current_position > 0 else SignalType.BUY, 0.9, {
                    "strategy": "emergency_exit",
                    "risk_level": risk_assessment.risk_level,
                    "emergency_reason": risk_assessment.risk_factors,
                    "coordination_latency_ms": coordination_time
                }
            
            # Combine agent recommendations for buy signal
            if (pricing_recommendation.signal in ["BUY", "BOTH"] and 
                inventory_recommendation.can_buy and 
                risk_assessment.risk_level < 0.7):
                
                # Calculate position size
                base_quantity = min(1000, risk_assessment.max_position_allowed * 0.1)
                adjusted_quantity = base_quantity * risk_assessment.position_sizing_multiplier
                
                return SignalType.BUY, 0.85, {
                    "strategy": "market_making_buy",
                    "bid_price": pricing_recommendation.bid_price,
                    "quantity": adjusted_quantity,
                    "expected_spread": pricing_recommendation.spread,
                    "spread_capture_bps": pricing_recommendation.spread * 10000,
                    "inventory_impact": inventory_recommendation.inventory_delta,
                    "risk_score": risk_assessment.risk_level,
                    "volatility_adjustment": pricing_recommendation.volatility_adjustment,
                    "market_impact_estimate": pricing_recommendation.market_impact_estimate,
                    "coordination_latency_ms": coordination_time,
                    "pricing_confidence": pricing_recommendation.confidence,
                    "inventory_status": inventory_recommendation.status,
                    "risk_factors": risk_assessment.risk_factors
                }
                
            # Combine agent recommendations for sell signal
            elif (pricing_recommendation.signal in ["SELL", "BOTH"] and 
                  inventory_recommendation.can_sell and 
                  risk_assessment.risk_level < 0.7):
                
                # Calculate position size
                base_quantity = min(1000, risk_assessment.max_position_allowed * 0.1)
                adjusted_quantity = base_quantity * risk_assessment.position_sizing_multiplier
                
                return SignalType.SELL, 0.85, {
                    "strategy": "market_making_sell", 
                    "ask_price": pricing_recommendation.ask_price,
                    "quantity": adjusted_quantity,
                    "expected_spread": pricing_recommendation.spread,
                    "spread_capture_bps": pricing_recommendation.spread * 10000,
                    "inventory_impact": inventory_recommendation.inventory_delta,
                    "risk_score": risk_assessment.risk_level,
                    "volatility_adjustment": pricing_recommendation.volatility_adjustment,
                    "market_impact_estimate": pricing_recommendation.market_impact_estimate,
                    "coordination_latency_ms": coordination_time,
                    "pricing_confidence": pricing_recommendation.confidence,
                    "inventory_status": inventory_recommendation.status,
                    "risk_factors": risk_assessment.risk_factors
                }
            
            # No trading opportunity or risk too high
            return SignalType.HOLD, 0.3, {
                "reason": "no_opportunity_or_high_risk",
                "pricing_signal": pricing_recommendation.signal,
                "inventory_status": inventory_recommendation.status,
                "risk_level": risk_assessment.risk_level,
                "can_buy": inventory_recommendation.can_buy,
                "can_sell": inventory_recommendation.can_sell,
                "coordination_latency_ms": coordination_time,
                "spread_opportunity": pricing_recommendation.spread,
                "risk_factors": risk_assessment.risk_factors
            }
            
        except Exception as e:
            logger.error(f"Signal generation failed for {symbol}: {e}")
            return SignalType.HOLD, 0.0, {
                "reason": "signal_generation_error", 
                "error": str(e)
            }
    
    async def update_position(self, position_delta: float):
        """Update current position tracking"""
        self.current_position += position_delta
        
    async def record_trade_execution(self, execution_time_ms: float, spread_captured: float, adverse_selection: bool):
        """Record trade execution metrics"""
        
        self.execution_times.append(execution_time_ms)
        self.spread_captures.append(spread_captured)
        self.adverse_selections.append(adverse_selection)
        
        # Keep only recent metrics
        max_history = 1000
        if len(self.execution_times) > max_history:
            self.execution_times = self.execution_times[-max_history//2:]
            self.spread_captures = self.spread_captures[-max_history//2:]
            self.adverse_selections = self.adverse_selections[-max_history//2:]
        
        # Update performance metrics
        await self.update_performance_metrics()
    
    async def update_performance_metrics(self):
        """Update strategy performance metrics"""
        
        if self.execution_times:
            avg_execution_time = np.mean(self.execution_times)
            self.performance_metrics["avg_execution_latency_ms"] = avg_execution_time
            
        if self.spread_captures:
            avg_spread_capture = np.mean(self.spread_captures)
            self.performance_metrics["avg_spread_capture_bps"] = avg_spread_capture * 10000
            
        if self.adverse_selections:
            adverse_selection_rate = np.mean(self.adverse_selections)
            self.performance_metrics["adverse_selection_rate"] = adverse_selection_rate
            self.fill_rate = 1.0 - adverse_selection_rate
            
        # Calculate trades per second (approximate)
        total_trades = len(self.execution_times)
        time_range_seconds = 3600  # Assume 1 hour window
        self.trades_per_second = total_trades / time_range_seconds if time_range_seconds > 0 else 0
        
        self.performance_metrics["trades_per_second"] = self.trades_per_second
        self.performance_metrics["fill_rate"] = self.fill_rate
        self.performance_metrics["current_position"] = self.current_position
        self.performance_metrics["inventory_deviation"] = abs(self.current_position - self.inventory_target)
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get comprehensive strategy status"""
        
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_type": self.strategy_type,
            "is_active": True,
            "current_position": self.current_position,
            "inventory_target": self.inventory_target,
            "performance_metrics": self.performance_metrics,
            "agent_status": {
                "pricing_agent": "active" if self.pricing_agent else "inactive",
                "inventory_agent": "active" if self.inventory_agent else "inactive", 
                "risk_agent": "active" if self.risk_agent else "inactive"
            },
            "configuration": {
                "min_spread": self.min_spread,
                "max_position": self.max_position,
                "risk_multiplier": self.risk_multiplier,
                "latency_target_ms": self.execution_latency_target
            },
            "recent_performance": {
                "avg_execution_latency_ms": np.mean(self.execution_times[-100:]) if self.execution_times else 0,
                "recent_spread_capture_bps": np.mean(self.spread_captures[-100:]) * 10000 if self.spread_captures else 0,
                "recent_adverse_selection_rate": np.mean(self.adverse_selections[-100:]) if self.adverse_selections else 0
            }
        }


# Factory function for strategy creation
def create_market_making_hft_strategy(**params) -> MarketMakingHFTStrategy:
    """Factory function to create market making HFT strategy"""
    return MarketMakingHFTStrategy(**params)


# Goal achievement integration examples
MARKET_MAKING_GOALS = [
    {
        "goal_name": "Achieve 95% Fill Rate",
        "goal_type": "performance_metric",
        "target_value": 0.95,
        "timeframe": "1 day",
        "success_criteria": [
            "Maintain bid-ask spread within 0.01%",
            "Execute minimum 1000 trades per hour",
            "Keep inventory neutral within 5% deviation"
        ],
        "optimization_targets": {
            "min_spread": "dynamic_optimization",
            "position_sizing": "volatility_adjusted",
            "risk_multiplier": "drawdown_optimized"
        }
    },
    {
        "goal_name": "Generate $10K Daily Revenue",
        "goal_type": "profit_target", 
        "target_value": 10000,
        "timeframe": "1 day",
        "success_criteria": [
            "Maintain consistent spread capture",
            "Minimize adverse selection below 15%",
            "Optimize inventory costs"
        ],
        "optimization_targets": {
            "spread_capture": "maximize_revenue",
            "inventory_management": "minimize_holding_costs",
            "execution_speed": "minimize_latency"
        }
    },
    {
        "goal_name": "Maintain Sub-1ms Execution Latency",
        "goal_type": "latency_target",
        "target_value": 1.0,
        "timeframe": "continuous",
        "success_criteria": [
            "99th percentile execution time < 1ms",
            "Agent coordination time < 0.5ms", 
            "Signal generation time < 0.2ms"
        ],
        "optimization_targets": {
            "agent_coordination": "minimize_communication_overhead",
            "signal_processing": "optimize_calculation_speed",
            "execution_path": "direct_market_access"
        }
    }
]