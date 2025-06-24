"""
Adaptive Risk Management Service - Phase 5 Implementation
Machine learning-enhanced risk management with dynamic parameter adjustment
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Literal, Tuple
from loguru import logger
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
from collections import deque

class RiskLevel(str, Enum):
    """Risk level classifications"""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"

class MarketCondition(str, Enum):
    """Market condition types for risk adjustment"""
    STABLE = "stable"
    VOLATILE = "volatile"
    TRENDING = "trending"
    CRISIS = "crisis"
    RECOVERY = "recovery"

class RiskAdjustment(BaseModel):
    """Risk parameter adjustment recommendation"""
    parameter_name: str
    current_value: float
    recommended_value: float
    adjustment_factor: float
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    market_condition: MarketCondition
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AdaptiveRiskProfile(BaseModel):
    """Adaptive risk profile for an agent or portfolio"""
    agent_id: str
    risk_level: RiskLevel
    
    # Dynamic risk parameters
    max_position_size_multiplier: float = 1.0
    stop_loss_multiplier: float = 1.0
    correlation_limit_multiplier: float = 1.0
    volatility_adjustment_factor: float = 1.0
    
    # Market condition adjustments
    market_condition: MarketCondition = MarketCondition.STABLE
    volatility_regime: str = "normal"
    
    # Learning metrics
    prediction_accuracy: float = 0.5
    adaptation_speed: float = 0.1
    risk_score: float = 50.0  # 0-100 scale
    
    # Historical performance
    recent_performance: Dict[str, float] = Field(default_factory=dict)
    drawdown_history: List[float] = Field(default_factory=list)
    
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RiskEvent(BaseModel):
    """Risk event detection and classification"""
    event_id: str
    event_type: str
    severity: RiskLevel
    affected_assets: List[str]
    description: str
    probability: float = Field(ge=0.0, le=1.0)
    impact_score: float = Field(ge=0.0, le=10.0)
    
    # Recommended actions
    recommended_actions: List[str] = Field(default_factory=list)
    risk_adjustments: List[RiskAdjustment] = Field(default_factory=list)
    
    detection_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiry_time: Optional[datetime] = None

@dataclass
class MarketRiskMetrics:
    """Real-time market risk metrics"""
    symbol: str
    volatility_1d: float = 0.0
    volatility_7d: float = 0.0
    volatility_30d: float = 0.0
    beta: float = 1.0
    correlation_spy: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    cvar_95: float = 0.0  # Conditional VaR 95%
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    last_updated: datetime = datetime.now(timezone.utc)

class AdaptiveRiskService:
    """
    Adaptive risk management using machine learning for dynamic parameter adjustment
    """
    
    def __init__(self):
        self.agent_risk_profiles: Dict[str, AdaptiveRiskProfile] = {}
        self.market_risk_metrics: Dict[str, MarketRiskMetrics] = {}
        self.risk_events: List[RiskEvent] = []
        self.risk_adjustments_history: List[RiskAdjustment] = []
        
        # Learning parameters
        self.learning_rate = 0.1
        self.adaptation_window = 30  # Days
        self.risk_threshold_multipliers = {
            RiskLevel.VERY_LOW: 0.5,
            RiskLevel.LOW: 0.7,
            RiskLevel.MODERATE: 1.0,
            RiskLevel.HIGH: 1.3,
            RiskLevel.VERY_HIGH: 1.7,
            RiskLevel.EXTREME: 2.5
        }
        
        # Market condition thresholds
        self.volatility_thresholds = {
            "low": 0.15,
            "normal": 0.25,
            "high": 0.40,
            "extreme": 0.60
        }
        
        # Start background monitoring
        self.monitoring_active = True
        self._start_risk_monitoring()
        
        logger.info("AdaptiveRiskService initialized with ML-enhanced risk management")
    
    def _start_risk_monitoring(self):
        """Start background risk monitoring and adaptation"""
        asyncio.create_task(self._risk_monitoring_loop())
        asyncio.create_task(self._adaptation_loop())
    
    async def _risk_monitoring_loop(self):
        """Main risk monitoring loop"""
        while self.monitoring_active:
            try:
                await self._update_market_risk_metrics()
                await self._detect_risk_events()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _adaptation_loop(self):
        """Adaptive learning loop for risk parameter adjustment"""
        while self.monitoring_active:
            try:
                await self._adapt_risk_parameters()
                await asyncio.sleep(300)  # Adapt every 5 minutes
            except Exception as e:
                logger.error(f"Error in adaptation loop: {e}", exc_info=True)
                await asyncio.sleep(300)
    
    async def register_agent(self, agent_id: str, initial_risk_level: RiskLevel = RiskLevel.MODERATE):
        """Register an agent for adaptive risk management"""
        
        profile = AdaptiveRiskProfile(
            agent_id=agent_id,
            risk_level=initial_risk_level,
            risk_score=self._risk_level_to_score(initial_risk_level)
        )
        
        self.agent_risk_profiles[agent_id] = profile
        logger.info(f"Registered agent {agent_id} for adaptive risk management")
    
    def _risk_level_to_score(self, risk_level: RiskLevel) -> float:
        """Convert risk level to numeric score"""
        mapping = {
            RiskLevel.VERY_LOW: 20.0,
            RiskLevel.LOW: 35.0,
            RiskLevel.MODERATE: 50.0,
            RiskLevel.HIGH: 70.0,
            RiskLevel.VERY_HIGH: 85.0,
            RiskLevel.EXTREME: 95.0
        }
        return mapping.get(risk_level, 50.0)
    
    async def assess_position_risk(
        self,
        agent_id: str,
        symbol: str,
        position_size: float,
        entry_price: float,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risk for a specific position with adaptive adjustments"""
        
        if agent_id not in self.agent_risk_profiles:
            await self.register_agent(agent_id)
        
        profile = self.agent_risk_profiles[agent_id]
        
        # Get market risk metrics
        if symbol not in self.market_risk_metrics:
            await self._calculate_market_risk_metrics(symbol, market_data)
        
        market_metrics = self.market_risk_metrics[symbol]
        
        # Base risk calculations
        base_risk = await self._calculate_base_risk(symbol, position_size, entry_price, market_metrics)
        
        # Apply adaptive adjustments
        adjusted_risk = await self._apply_adaptive_adjustments(base_risk, profile, market_metrics)
        
        # Generate risk assessment
        assessment = {
            "agent_id": agent_id,
            "symbol": symbol,
            "base_risk_score": base_risk["risk_score"],
            "adjusted_risk_score": adjusted_risk["risk_score"],
            "risk_level": self._score_to_risk_level(adjusted_risk["risk_score"]),
            "position_size": position_size,
            "max_recommended_size": adjusted_risk["max_recommended_size"],
            "stop_loss_level": adjusted_risk["stop_loss_level"],
            "var_1d": adjusted_risk["var_1d"],
            "expected_drawdown": adjusted_risk["expected_drawdown"],
            "market_condition": profile.market_condition,
            "volatility_regime": profile.volatility_regime,
            "adjustments_applied": adjusted_risk["adjustments"],
            "confidence": adjusted_risk["confidence"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return assessment
    
    async def _calculate_base_risk(
        self,
        symbol: str,
        position_size: float,
        entry_price: float,
        market_metrics: MarketRiskMetrics
    ) -> Dict[str, Any]:
        """Calculate base risk metrics without adaptive adjustments"""
        
        position_value = position_size * entry_price
        
        # Volatility-based risk
        volatility_risk = market_metrics.volatility_30d * position_value
        
        # VaR calculation
        var_1d = market_metrics.var_95 * position_value
        
        # Expected drawdown based on historical data
        expected_drawdown = market_metrics.max_drawdown * position_value
        
        # Base risk score (0-100)
        risk_components = [
            market_metrics.volatility_30d * 100,
            abs(market_metrics.beta - 1.0) * 50,
            market_metrics.max_drawdown * 100,
            (1.0 - max(market_metrics.sharpe_ratio, 0)) * 30
        ]
        
        risk_score = min(100, np.mean(risk_components))
        
        return {
            "risk_score": risk_score,
            "volatility_risk": volatility_risk,
            "var_1d": var_1d,
            "expected_drawdown": expected_drawdown,
            "position_value": position_value
        }
    
    async def _apply_adaptive_adjustments(
        self,
        base_risk: Dict[str, Any],
        profile: AdaptiveRiskProfile,
        market_metrics: MarketRiskMetrics
    ) -> Dict[str, Any]:
        """Apply adaptive adjustments based on learning and market conditions"""
        
        adjustments = []
        adjusted_risk = base_risk.copy()
        
        # Market condition adjustments
        if profile.market_condition == MarketCondition.VOLATILE:
            volatility_adjustment = 1.3
            adjustments.append("Increased risk due to volatile market conditions")
        elif profile.market_condition == MarketCondition.CRISIS:
            volatility_adjustment = 2.0
            adjustments.append("Significantly increased risk due to crisis conditions")
        elif profile.market_condition == MarketCondition.STABLE:
            volatility_adjustment = 0.8
            adjustments.append("Reduced risk due to stable market conditions")
        else:
            volatility_adjustment = 1.0
        
        # Apply volatility adjustment
        adjusted_risk["risk_score"] *= volatility_adjustment
        adjusted_risk["var_1d"] *= volatility_adjustment
        
        # Position size adjustment based on recent performance
        if profile.recent_performance.get("win_rate", 0.5) > 0.7:
            size_multiplier = 1.2
            adjustments.append("Increased position size due to strong recent performance")
        elif profile.recent_performance.get("win_rate", 0.5) < 0.3:
            size_multiplier = 0.7
            adjustments.append("Reduced position size due to poor recent performance")
        else:
            size_multiplier = 1.0
        
        # Calculate recommended position size
        base_position_value = base_risk["position_value"]
        risk_budget = 100000 * profile.max_position_size_multiplier  # Example risk budget
        max_recommended_value = risk_budget * size_multiplier
        max_recommended_size = max_recommended_value / (base_position_value / (base_position_value / market_metrics.volatility_30d)) if market_metrics.volatility_30d > 0 else 0
        
        # Stop loss calculation with adaptive adjustment
        base_stop_distance = market_metrics.volatility_7d * 2  # 2x 7-day volatility
        adjusted_stop_distance = base_stop_distance * profile.stop_loss_multiplier
        stop_loss_level = (1.0 - adjusted_stop_distance) if adjusted_stop_distance < 1.0 else 0.5
        
        # Confidence calculation
        confidence = min(1.0, profile.prediction_accuracy + 0.1)
        
        adjusted_risk.update({
            "max_recommended_size": max_recommended_size,
            "stop_loss_level": stop_loss_level,
            "adjustments": adjustments,
            "confidence": confidence,
            "size_multiplier": size_multiplier,
            "volatility_adjustment": volatility_adjustment
        })
        
        return adjusted_risk
    
    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """Convert numeric risk score to risk level"""
        if score <= 25:
            return RiskLevel.VERY_LOW
        elif score <= 40:
            return RiskLevel.LOW
        elif score <= 60:
            return RiskLevel.MODERATE
        elif score <= 80:
            return RiskLevel.HIGH
        elif score <= 90:
            return RiskLevel.VERY_HIGH
        else:
            return RiskLevel.EXTREME
    
    async def _calculate_market_risk_metrics(self, symbol: str, market_data: Dict[str, Any]):
        """Calculate comprehensive market risk metrics"""
        
        # Extract price data
        prices = market_data.get("prices", [])
        if len(prices) < 30:
            logger.warning(f"Insufficient price data for {symbol} risk calculation")
            return
        
        # Convert to pandas for calculations
        df = pd.DataFrame(prices)
        df['returns'] = df['close'].pct_change()
        
        # Volatility calculations
        volatility_1d = df['returns'].rolling(window=1).std().iloc[-1] * np.sqrt(252)
        volatility_7d = df['returns'].rolling(window=7).std().iloc[-1] * np.sqrt(252)
        volatility_30d = df['returns'].rolling(window=30).std().iloc[-1] * np.sqrt(252)
        
        # VaR and CVaR (95% confidence)
        returns_sorted = df['returns'].dropna().sort_values()
        var_95 = returns_sorted.quantile(0.05)  # 5th percentile
        cvar_95 = returns_sorted[returns_sorted <= var_95].mean()
        
        # Maximum drawdown
        cumulative_returns = (1 + df['returns']).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        
        # Sharpe and Sortino ratios
        excess_returns = df['returns'] - 0.02/252  # Assuming 2% risk-free rate
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        negative_returns = excess_returns[excess_returns < 0]
        sortino_ratio = excess_returns.mean() / negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 and negative_returns.std() > 0 else 0
        
        # Beta calculation (assuming SPY as benchmark - would need SPY data)
        beta = 1.0  # Placeholder - would calculate against benchmark
        correlation_spy = 0.0  # Placeholder
        
        # Store metrics
        self.market_risk_metrics[symbol] = MarketRiskMetrics(
            symbol=symbol,
            volatility_1d=volatility_1d or 0.0,
            volatility_7d=volatility_7d or 0.0,
            volatility_30d=volatility_30d or 0.0,
            beta=beta,
            correlation_spy=correlation_spy,
            var_95=var_95 or 0.0,
            cvar_95=cvar_95 or 0.0,
            max_drawdown=max_drawdown or 0.0,
            sharpe_ratio=sharpe_ratio or 0.0,
            sortino_ratio=sortino_ratio or 0.0
        )
    
    async def _update_market_risk_metrics(self):
        """Update market risk metrics for all tracked symbols"""
        # This would integrate with market data service to get latest data
        # For now, it's a placeholder for the update cycle
        pass
    
    async def _detect_risk_events(self):
        """Detect potential risk events using market conditions"""
        
        current_time = datetime.now(timezone.utc)
        
        # Check for volatility spikes
        for symbol, metrics in self.market_risk_metrics.items():
            if metrics.volatility_1d > self.volatility_thresholds["extreme"]:
                event = RiskEvent(
                    event_id=f"vol_spike_{symbol}_{int(current_time.timestamp())}",
                    event_type="volatility_spike",
                    severity=RiskLevel.VERY_HIGH,
                    affected_assets=[symbol],
                    description=f"Extreme volatility spike detected in {symbol} ({metrics.volatility_1d:.2%})",
                    probability=0.9,
                    impact_score=8.0,
                    recommended_actions=[
                        "Reduce position sizes",
                        "Tighten stop losses",
                        "Increase monitoring frequency"
                    ],
                    expiry_time=current_time + timedelta(hours=4)
                )
                
                self.risk_events.append(event)
                logger.warning(f"Risk event detected: {event.description}")
        
        # Clean up expired events
        self.risk_events = [
            event for event in self.risk_events
            if not event.expiry_time or event.expiry_time > current_time
        ]
    
    async def _adapt_risk_parameters(self):
        """Adapt risk parameters based on performance feedback"""
        
        for agent_id, profile in self.agent_risk_profiles.items():
            try:
                # Calculate recent performance metrics
                performance_data = await self._get_agent_performance_data(agent_id)
                
                if performance_data:
                    # Update profile with recent performance
                    profile.recent_performance = performance_data
                    
                    # Adapt parameters based on performance
                    adaptations = await self._calculate_parameter_adaptations(profile, performance_data)
                    
                    # Apply adaptations
                    for adaptation in adaptations:
                        await self._apply_parameter_adaptation(profile, adaptation)
                    
                    profile.last_updated = datetime.now(timezone.utc)
                    
                    logger.debug(f"Adapted risk parameters for agent {agent_id}")
                    
            except Exception as e:
                logger.error(f"Error adapting parameters for agent {agent_id}: {e}")
    
    async def _get_agent_performance_data(self, agent_id: str) -> Optional[Dict[str, float]]:
        """Get recent performance data for an agent"""
        # This would integrate with the agent performance service
        # For now, return mock data structure
        return {
            "win_rate": 0.6,
            "avg_return": 0.02,
            "max_drawdown": 0.05,
            "sharpe_ratio": 1.2,
            "total_trades": 50
        }
    
    async def _calculate_parameter_adaptations(
        self,
        profile: AdaptiveRiskProfile,
        performance_data: Dict[str, float]
    ) -> List[RiskAdjustment]:
        """Calculate recommended parameter adaptations"""
        
        adaptations = []
        
        # Adapt position size multiplier based on performance
        if performance_data["win_rate"] > 0.7 and performance_data["sharpe_ratio"] > 1.5:
            new_multiplier = min(2.0, profile.max_position_size_multiplier * 1.1)
            adaptations.append(RiskAdjustment(
                parameter_name="max_position_size_multiplier",
                current_value=profile.max_position_size_multiplier,
                recommended_value=new_multiplier,
                adjustment_factor=1.1,
                reason="Strong performance justifies increased position sizing",
                confidence=0.8,
                market_condition=profile.market_condition
            ))
        elif performance_data["win_rate"] < 0.4 or performance_data["max_drawdown"] > 0.15:
            new_multiplier = max(0.5, profile.max_position_size_multiplier * 0.9)
            adaptations.append(RiskAdjustment(
                parameter_name="max_position_size_multiplier",
                current_value=profile.max_position_size_multiplier,
                recommended_value=new_multiplier,
                adjustment_factor=0.9,
                reason="Poor performance requires reduced position sizing",
                confidence=0.9,
                market_condition=profile.market_condition
            ))
        
        # Adapt stop loss multiplier
        if performance_data["max_drawdown"] > 0.10:
            new_multiplier = min(2.0, profile.stop_loss_multiplier * 1.05)
            adaptations.append(RiskAdjustment(
                parameter_name="stop_loss_multiplier",
                current_value=profile.stop_loss_multiplier,
                recommended_value=new_multiplier,
                adjustment_factor=1.05,
                reason="High drawdown requires tighter stop losses",
                confidence=0.85,
                market_condition=profile.market_condition
            ))
        
        return adaptations
    
    async def _apply_parameter_adaptation(self, profile: AdaptiveRiskProfile, adaptation: RiskAdjustment):
        """Apply a parameter adaptation to the risk profile"""
        
        if adaptation.parameter_name == "max_position_size_multiplier":
            profile.max_position_size_multiplier = adaptation.recommended_value
        elif adaptation.parameter_name == "stop_loss_multiplier":
            profile.stop_loss_multiplier = adaptation.recommended_value
        elif adaptation.parameter_name == "correlation_limit_multiplier":
            profile.correlation_limit_multiplier = adaptation.recommended_value
        elif adaptation.parameter_name == "volatility_adjustment_factor":
            profile.volatility_adjustment_factor = adaptation.recommended_value
        
        # Store adaptation in history
        self.risk_adjustments_history.append(adaptation)
        
        # Keep only recent history
        if len(self.risk_adjustments_history) > 1000:
            self.risk_adjustments_history = self.risk_adjustments_history[-1000:]
    
    async def get_agent_risk_profile(self, agent_id: str) -> Optional[AdaptiveRiskProfile]:
        """Get adaptive risk profile for an agent"""
        return self.agent_risk_profiles.get(agent_id)
    
    async def get_active_risk_events(self) -> List[RiskEvent]:
        """Get currently active risk events"""
        current_time = datetime.now(timezone.utc)
        return [
            event for event in self.risk_events
            if not event.expiry_time or event.expiry_time > current_time
        ]
    
    async def get_recent_adaptations(self, agent_id: Optional[str] = None, limit: int = 50) -> List[RiskAdjustment]:
        """Get recent risk parameter adaptations"""
        adaptations = self.risk_adjustments_history
        
        # Filter by agent if specified
        if agent_id:
            # This would require storing agent_id in RiskAdjustment model
            pass
        
        return adaptations[-limit:] if limit else adaptations
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get adaptive risk service status"""
        
        risk_distribution = {}
        for level in RiskLevel:
            count = sum(1 for profile in self.agent_risk_profiles.values() if profile.risk_level == level)
            risk_distribution[level.value] = count
        
        return {
            "service_status": "active" if self.monitoring_active else "inactive",
            "monitored_agents": len(self.agent_risk_profiles),
            "tracked_symbols": len(self.market_risk_metrics),
            "active_risk_events": len([e for e in self.risk_events if not e.expiry_time or e.expiry_time > datetime.now(timezone.utc)]),
            "risk_level_distribution": risk_distribution,
            "recent_adaptations": len(self.risk_adjustments_history[-24:]),  # Last 24 adaptations
            "learning_parameters": {
                "learning_rate": self.learning_rate,
                "adaptation_window_days": self.adaptation_window
            },
            "last_update": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_adaptive_risk_service() -> AdaptiveRiskService:
    """Factory function to create adaptive risk service"""
    return AdaptiveRiskService()