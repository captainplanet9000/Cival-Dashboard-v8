"""
Phase 10: Real-Time Risk Management and Position Sizing Service
Advanced risk control, position sizing, and portfolio protection
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import logging
import numpy as np
import pandas as pd
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from enum import Enum

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.trading_strategy_models import (
    TradingPosition, TradingSignal, RiskMetrics, PositionSide, RiskLevel
)
from services.portfolio_management_service import get_portfolio_management_service
from services.market_analysis_service import get_market_analysis_service
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class RiskAlert(BaseModel):
    """Risk management alert"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str
    alert_type: str  # var_breach, drawdown_limit, concentration_risk, etc.
    severity: str    # low, medium, high, critical
    message: str
    current_value: float
    threshold: float
    recommended_action: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    resolved: bool = False


class PositionSizingRule(BaseModel):
    """Position sizing rule configuration"""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    strategy_id: Optional[str] = None  # None means applies to all strategies
    
    # Kelly Criterion parameters
    kelly_fraction: Optional[float] = None
    kelly_multiplier: float = 0.25  # Conservative Kelly
    
    # Fixed sizing
    fixed_amount: Optional[Decimal] = None
    fixed_percentage: Optional[float] = None
    
    # Risk-based sizing
    risk_per_trade: float = 0.02  # 2% risk per trade
    max_risk_per_trade: float = 0.05  # 5% maximum
    
    # Volatility adjustment
    volatility_adjustment: bool = True
    base_volatility: float = 0.02  # 2% base volatility
    
    # Position limits
    max_position_size: Decimal = Decimal("10000")
    max_portfolio_percentage: float = 0.1  # 10%
    
    # Market condition adjustments
    bull_market_multiplier: float = 1.2
    bear_market_multiplier: float = 0.8
    high_volatility_multiplier: float = 0.6
    
    active: bool = True


class RiskLimit(BaseModel):
    """Risk limit configuration"""
    limit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str
    limit_type: str  # var, drawdown, concentration, leverage, etc.
    
    # Limit values
    warning_threshold: float
    critical_threshold: float
    
    # Actions
    warning_action: str = "alert"  # alert, reduce_positions, pause_trading
    critical_action: str = "emergency_liquidation"
    
    # Timeframe
    measurement_period: str = "1d"  # 1d, 1w, 1m
    
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PositionSizer:
    """Advanced position sizing algorithms"""
    
    def __init__(self):
        self.default_risk_per_trade = 0.02  # 2%
        self.max_position_percentage = 0.1   # 10%
        
    def kelly_criterion_sizing(
        self,
        portfolio_value: Decimal,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        kelly_multiplier: float = 0.25
    ) -> Decimal:
        """Calculate position size using Kelly Criterion"""
        if avg_loss == 0:
            return Decimal("0")
        
        # Kelly formula: f* = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate
        
        kelly_fraction = (b * p - q) / b
        
        # Apply multiplier for conservative sizing
        kelly_fraction = max(0, kelly_fraction * kelly_multiplier)
        
        # Apply maximum position limit
        kelly_fraction = min(kelly_fraction, self.max_position_percentage)
        
        return portfolio_value * Decimal(str(kelly_fraction))
    
    def volatility_adjusted_sizing(
        self,
        portfolio_value: Decimal,
        signal: TradingSignal,
        current_volatility: float,
        base_volatility: float = 0.02,
        target_risk: float = 0.02
    ) -> Decimal:
        """Calculate position size adjusted for volatility"""
        if current_volatility == 0:
            return Decimal("0")
        
        # Volatility adjustment factor
        vol_adjustment = base_volatility / current_volatility
        
        # Apply confidence multiplier
        confidence_multiplier = signal.confidence
        
        # Calculate base position size
        base_size = portfolio_value * Decimal(str(target_risk))
        
        # Apply adjustments
        adjusted_size = base_size * Decimal(str(vol_adjustment * confidence_multiplier))
        
        # Apply limits
        max_size = portfolio_value * Decimal(str(self.max_position_percentage))
        
        return min(adjusted_size, max_size)
    
    def risk_parity_sizing(
        self,
        portfolio_value: Decimal,
        signal: TradingSignal,
        stop_loss_distance: float,
        target_risk: float = 0.02
    ) -> Decimal:
        """Calculate position size based on risk parity"""
        if stop_loss_distance == 0:
            return Decimal("0")
        
        # Calculate position size to risk exactly target_risk of portfolio
        risk_amount = portfolio_value * Decimal(str(target_risk))
        
        # Position size = Risk Amount / Stop Loss Distance
        position_size = risk_amount / Decimal(str(stop_loss_distance))
        
        # Apply maximum position limit
        max_size = portfolio_value * Decimal(str(self.max_position_percentage))
        
        return min(position_size, max_size)
    
    def adaptive_sizing(
        self,
        portfolio_value: Decimal,
        signal: TradingSignal,
        strategy_performance: Dict[str, float],
        market_regime: str,
        current_volatility: float
    ) -> Decimal:
        """Adaptive position sizing based on multiple factors"""
        base_risk = 0.02  # 2% base risk
        
        # Performance adjustment
        if "win_rate" in strategy_performance:
            win_rate = strategy_performance["win_rate"]
            if win_rate > 0.6:
                performance_multiplier = 1.2
            elif win_rate < 0.4:
                performance_multiplier = 0.8
            else:
                performance_multiplier = 1.0
        else:
            performance_multiplier = 1.0
        
        # Market regime adjustment
        if market_regime == "bull_market":
            regime_multiplier = 1.1
        elif market_regime == "bear_market":
            regime_multiplier = 0.9
        elif market_regime == "high_volatility":
            regime_multiplier = 0.7
        else:
            regime_multiplier = 1.0
        
        # Volatility adjustment
        if current_volatility > 0.05:  # High volatility
            vol_multiplier = 0.8
        elif current_volatility < 0.01:  # Low volatility
            vol_multiplier = 1.2
        else:
            vol_multiplier = 1.0
        
        # Signal strength adjustment
        strength_multiplier = {
            "very_strong": 1.2,
            "strong": 1.1,
            "moderate": 1.0,
            "weak": 0.8,
            "very_weak": 0.6
        }.get(signal.strength.value, 1.0)
        
        # Combine all factors
        total_multiplier = (performance_multiplier * regime_multiplier * 
                          vol_multiplier * strength_multiplier * signal.confidence)
        
        # Calculate final position size
        adjusted_risk = base_risk * total_multiplier
        position_value = portfolio_value * Decimal(str(adjusted_risk))
        
        # Apply limits
        max_size = portfolio_value * Decimal(str(self.max_position_percentage))
        
        return min(position_value, max_size)


class RiskCalculator:
    """Risk metrics calculator"""
    
    def __init__(self):
        self.confidence_level = 0.95  # 95% confidence for VaR
        
    def calculate_var(
        self,
        returns: List[float],
        confidence_level: float = 0.95,
        holding_period: int = 1
    ) -> float:
        """Calculate Value at Risk (VaR)"""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        
        # Sort returns in ascending order
        sorted_returns = np.sort(returns_array)
        
        # Find the percentile
        percentile = (1 - confidence_level) * 100
        var = np.percentile(sorted_returns, percentile)
        
        # Adjust for holding period
        var_adjusted = var * np.sqrt(holding_period)
        
        return abs(var_adjusted)
    
    def calculate_expected_shortfall(
        self,
        returns: List[float],
        confidence_level: float = 0.95
    ) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if not returns:
            return 0.0
        
        var = self.calculate_var(returns, confidence_level)
        returns_array = np.array(returns)
        
        # Expected shortfall is the mean of returns worse than VaR
        tail_returns = returns_array[returns_array <= -var]
        
        if len(tail_returns) == 0:
            return var
        
        return abs(np.mean(tail_returns))
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> Dict[str, float]:
        """Calculate maximum drawdown"""
        if not equity_curve:
            return {"max_drawdown": 0.0, "current_drawdown": 0.0}
        
        equity_array = np.array(equity_curve)
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(equity_array)
        
        # Calculate drawdown
        drawdown = (equity_array - running_max) / running_max
        
        max_drawdown = np.min(drawdown)
        current_drawdown = drawdown[-1]
        
        return {
            "max_drawdown": abs(max_drawdown),
            "current_drawdown": abs(current_drawdown)
        }
    
    def calculate_portfolio_volatility(
        self,
        positions: List[TradingPosition],
        correlation_matrix: np.ndarray
    ) -> float:
        """Calculate portfolio volatility"""
        if not positions or correlation_matrix.size == 0:
            return 0.0
        
        # Extract position weights and individual volatilities
        weights = []
        volatilities = []
        
        for position in positions:
            # Simplified: would calculate actual volatility from price history
            weights.append(float(position.quantity))
            volatilities.append(0.02)  # Placeholder 2% volatility
        
        weights = np.array(weights)
        volatilities = np.array(volatilities)
        
        # Normalize weights
        if np.sum(weights) > 0:
            weights = weights / np.sum(weights)
        
        # Portfolio variance
        portfolio_variance = np.dot(weights.T, np.dot(correlation_matrix * np.outer(volatilities, volatilities), weights))
        
        return np.sqrt(portfolio_variance)
    
    def calculate_concentration_risk(self, positions: List[TradingPosition]) -> Dict[str, float]:
        """Calculate concentration risk metrics"""
        if not positions:
            return {"herfindahl_index": 0.0, "largest_position": 0.0, "top_5_concentration": 0.0}
        
        # Calculate position values
        position_values = []
        total_value = 0.0
        
        for position in positions:
            if position.status == "open":
                value = float(position.quantity * (position.current_price or position.entry_price))
                position_values.append(value)
                total_value += value
        
        if total_value == 0:
            return {"herfindahl_index": 0.0, "largest_position": 0.0, "top_5_concentration": 0.0}
        
        # Calculate weights
        weights = [value / total_value for value in position_values]
        
        # Herfindahl Index (sum of squared weights)
        herfindahl_index = sum(w**2 for w in weights)
        
        # Largest position weight
        largest_position = max(weights) if weights else 0.0
        
        # Top 5 concentration
        sorted_weights = sorted(weights, reverse=True)
        top_5_concentration = sum(sorted_weights[:5])
        
        return {
            "herfindahl_index": herfindahl_index,
            "largest_position": largest_position,
            "top_5_concentration": top_5_concentration
        }


class RiskManagementService:
    """
    Real-time risk management and position sizing service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
        # Risk components
        self.position_sizer = PositionSizer()
        self.risk_calculator = RiskCalculator()
        
        # Risk monitoring
        self.risk_limits: Dict[str, List[RiskLimit]] = defaultdict(list)
        self.active_alerts: Dict[str, RiskAlert] = {}
        self.position_sizing_rules: Dict[str, PositionSizingRule] = {}
        
        # Risk metrics cache
        self.portfolio_risk_metrics: Dict[str, RiskMetrics] = {}
        self.risk_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Performance tracking
        self.position_performance: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Configuration
        self.risk_check_interval = 60       # 1 minute
        self.metrics_update_interval = 300  # 5 minutes
        self.alert_check_interval = 30      # 30 seconds
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the risk management service"""
        try:
            logger.info("Initializing Risk Management Service...")
            
            # Load risk limits and rules
            await self._load_risk_limits()
            await self._load_position_sizing_rules()
            
            # Load active alerts
            await self._load_active_alerts()
            
            # Start background tasks
            asyncio.create_task(self._risk_monitoring_loop())
            asyncio.create_task(self._metrics_update_loop())
            asyncio.create_task(self._alert_processing_loop())
            
            logger.info("Risk Management Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Risk Management Service: {e}")
            raise
    
    async def calculate_position_size(
        self,
        signal: TradingSignal,
        portfolio_id: str,
        strategy_id: str,
        sizing_method: str = "adaptive"
    ) -> Tuple[Decimal, Dict[str, Any]]:
        """Calculate optimal position size for a trading signal"""
        try:
            # Get portfolio information
            portfolio_service = await get_portfolio_management_service()
            portfolio_analytics = await portfolio_service.get_portfolio_analytics(portfolio_id)
            
            if "error" in portfolio_analytics:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            portfolio_value = Decimal(str(portfolio_analytics["total_value"]))
            
            # Get position sizing rule
            sizing_rule = self.position_sizing_rules.get(strategy_id) or self.position_sizing_rules.get("default")
            
            if not sizing_rule:
                # Create default rule
                sizing_rule = PositionSizingRule(name="default", strategy_id="default")
                self.position_sizing_rules["default"] = sizing_rule
            
            # Get market data for volatility calculation
            market_service = await get_market_analysis_service()
            market_regimes = await market_service.analyze_market_regime([signal.symbol])
            current_regime = market_regimes.get(signal.symbol)
            
            # Calculate position size based on method
            if sizing_method == "kelly":
                # Get strategy performance for Kelly calculation
                strategy_perf = self.position_performance.get(strategy_id, {})
                win_rate = strategy_perf.get("win_rate", 0.5)
                avg_win = strategy_perf.get("avg_win", 0.02)
                avg_loss = strategy_perf.get("avg_loss", 0.02)
                
                position_size = self.position_sizer.kelly_criterion_sizing(
                    portfolio_value, win_rate, avg_win, avg_loss, sizing_rule.kelly_multiplier
                )
                
            elif sizing_method == "volatility_adjusted":
                # Estimate current volatility (simplified)
                current_volatility = current_regime.average_volatility if current_regime else 0.02
                
                position_size = self.position_sizer.volatility_adjusted_sizing(
                    portfolio_value, signal, current_volatility, sizing_rule.base_volatility, sizing_rule.risk_per_trade
                )
                
            elif sizing_method == "risk_parity":
                # Calculate stop loss distance
                if signal.stop_loss and signal.entry_price:
                    stop_distance = abs(float(signal.entry_price - signal.stop_loss)) / float(signal.entry_price)
                else:
                    stop_distance = sizing_rule.risk_per_trade  # Default 2%
                
                position_size = self.position_sizer.risk_parity_sizing(
                    portfolio_value, signal, stop_distance, sizing_rule.risk_per_trade
                )
                
            else:  # adaptive
                strategy_perf = self.position_performance.get(strategy_id, {})
                regime_name = current_regime.regime_name if current_regime else "normal"
                current_volatility = current_regime.average_volatility if current_regime else 0.02
                
                position_size = self.position_sizer.adaptive_sizing(
                    portfolio_value, signal, strategy_perf, regime_name, current_volatility
                )
            
            # Apply sizing rule limits
            max_size = min(
                sizing_rule.max_position_size,
                portfolio_value * Decimal(str(sizing_rule.max_portfolio_percentage))
            )
            
            position_size = min(position_size, max_size)
            
            # Validate against risk limits
            risk_check = await self._validate_position_risk(portfolio_id, signal, position_size)
            
            if not risk_check["approved"]:
                # Reduce position size if risk limits exceeded
                position_size = position_size * Decimal(str(risk_check.get("max_multiplier", 0.5)))
            
            calculation_details = {
                "method": sizing_method,
                "portfolio_value": float(portfolio_value),
                "calculated_size": float(position_size),
                "max_allowed_size": float(max_size),
                "risk_per_trade": sizing_rule.risk_per_trade,
                "signal_confidence": signal.confidence,
                "market_regime": regime_name if current_regime else "unknown",
                "risk_approved": risk_check["approved"],
                "risk_warnings": risk_check.get("warnings", [])
            }
            
            logger.info(f"Calculated position size: {position_size} for signal {signal.signal_id}")
            
            return position_size, calculation_details
            
        except Exception as e:
            logger.error(f"Failed to calculate position size for signal {signal.signal_id}: {e}")
            return Decimal("0"), {"error": str(e)}
    
    async def validate_trade_risk(
        self,
        portfolio_id: str,
        signal: TradingSignal,
        position_size: Decimal
    ) -> Dict[str, Any]:
        """Validate trade against all risk limits"""
        try:
            validation_result = {
                "approved": True,
                "warnings": [],
                "critical_issues": [],
                "risk_score": 0.0
            }
            
            # Get portfolio risk metrics
            risk_metrics = await self.calculate_portfolio_risk(portfolio_id)
            
            # Check position size limits
            portfolio_service = await get_portfolio_management_service()
            portfolio_analytics = await portfolio_service.get_portfolio_analytics(portfolio_id)
            
            if "error" not in portfolio_analytics:
                portfolio_value = float(portfolio_analytics["total_value"])
                position_percentage = float(position_size) / portfolio_value
                
                if position_percentage > 0.1:  # 10% limit
                    validation_result["warnings"].append(f"Position size {position_percentage:.1%} exceeds 10% of portfolio")
                    validation_result["risk_score"] += 0.3
                
                if position_percentage > 0.2:  # 20% critical limit
                    validation_result["critical_issues"].append(f"Position size {position_percentage:.1%} exceeds critical 20% limit")
                    validation_result["approved"] = False
            
            # Check portfolio concentration
            concentration_metrics = risk_metrics.get("concentration_risk", {})
            if concentration_metrics.get("largest_position", 0) > 0.15:
                validation_result["warnings"].append("Portfolio concentration risk: largest position > 15%")
                validation_result["risk_score"] += 0.2
            
            # Check VaR limits
            current_var = risk_metrics.get("var_1day", 0)
            if current_var > 0.05:  # 5% daily VaR limit
                validation_result["warnings"].append(f"Portfolio VaR {current_var:.1%} exceeds 5% limit")
                validation_result["risk_score"] += 0.4
            
            # Check drawdown
            drawdown_metrics = risk_metrics.get("drawdown_analysis", {})
            current_drawdown = drawdown_metrics.get("current_drawdown", 0)
            if current_drawdown > 0.15:  # 15% drawdown limit
                validation_result["critical_issues"].append(f"Current drawdown {current_drawdown:.1%} exceeds 15% limit")
                validation_result["approved"] = False
            
            # Check correlation risk
            if signal.symbol in ["BTCUSD", "ETHUSD"]:  # Crypto correlation check
                crypto_exposure = self._calculate_crypto_exposure(portfolio_analytics)
                if crypto_exposure > 0.5:  # 50% crypto exposure limit
                    validation_result["warnings"].append(f"Crypto exposure {crypto_exposure:.1%} is high")
                    validation_result["risk_score"] += 0.3
            
            # Final approval decision
            if validation_result["risk_score"] > 0.8:
                validation_result["approved"] = False
                validation_result["critical_issues"].append("Cumulative risk score too high")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to validate trade risk: {e}")
            return {
                "approved": False,
                "warnings": [],
                "critical_issues": [f"Risk validation error: {str(e)}"],
                "risk_score": 1.0
            }
    
    async def calculate_portfolio_risk(self, portfolio_id: str) -> Dict[str, Any]:
        """Calculate comprehensive portfolio risk metrics"""
        try:
            # Get portfolio data
            portfolio_service = await get_portfolio_management_service()
            portfolio_analytics = await portfolio_service.get_portfolio_analytics(portfolio_id)
            
            if "error" in portfolio_analytics:
                return {"error": "Portfolio not found"}
            
            # Extract positions for analysis
            position_summary = portfolio_analytics.get("position_summary", {})
            
            # Simulate return series (in production, would use historical data)
            returns = self._generate_simulated_returns(portfolio_id)
            
            # Calculate risk metrics
            var_1day = self.risk_calculator.calculate_var(returns, 0.95, 1)
            var_5day = self.risk_calculator.calculate_var(returns, 0.95, 5)
            expected_shortfall = self.risk_calculator.calculate_expected_shortfall(returns, 0.95)
            
            # Calculate drawdown
            equity_curve = self._generate_equity_curve(portfolio_id)
            drawdown_metrics = self.risk_calculator.calculate_max_drawdown(equity_curve)
            
            # Calculate concentration risk
            # This would use actual positions in production
            concentration_risk = {
                "largest_position": 0.08,  # Placeholder
                "top_5_concentration": 0.35,
                "herfindahl_index": 0.15
            }
            
            risk_metrics = {
                "portfolio_id": portfolio_id,
                "calculation_timestamp": datetime.now(timezone.utc).isoformat(),
                "var_1day": var_1day,
                "var_5day": var_5day,
                "expected_shortfall": expected_shortfall,
                "drawdown_analysis": drawdown_metrics,
                "concentration_risk": concentration_risk,
                "portfolio_volatility": np.std(returns) * np.sqrt(252) if returns else 0.0,
                "liquidity_score": 0.8,  # Placeholder
                "correlation_risk": "medium"  # Placeholder
            }
            
            # Cache the metrics
            self.portfolio_risk_metrics[portfolio_id] = risk_metrics
            
            # Store in history
            self.risk_history[portfolio_id].append({
                "timestamp": datetime.now(timezone.utc),
                "metrics": risk_metrics
            })
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio risk for {portfolio_id}: {e}")
            return {"error": str(e)}
    
    async def create_risk_alert(
        self,
        portfolio_id: str,
        alert_type: str,
        severity: str,
        message: str,
        current_value: float,
        threshold: float,
        recommended_action: str
    ) -> RiskAlert:
        """Create a new risk alert"""
        try:
            alert = RiskAlert(
                portfolio_id=portfolio_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                current_value=current_value,
                threshold=threshold,
                recommended_action=recommended_action
            )
            
            # Store alert
            self.active_alerts[alert.alert_id] = alert
            
            # Save to database
            await self._save_alert_to_database(alert)
            
            # Log alert
            logger.warning(f"Risk alert created: {alert_type} for portfolio {portfolio_id} - {message}")
            
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create risk alert: {e}")
            raise
    
    # Background monitoring loops
    
    async def _risk_monitoring_loop(self):
        """Main risk monitoring loop"""
        while not self._shutdown:
            try:
                # Get all portfolios
                portfolio_service = await get_portfolio_management_service()
                
                # Check risk limits for each portfolio
                for portfolio_id in portfolio_service.portfolios.keys():
                    await self._check_risk_limits(portfolio_id)
                
                await asyncio.sleep(self.risk_check_interval)
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(self.risk_check_interval)
    
    async def _metrics_update_loop(self):
        """Risk metrics update loop"""
        while not self._shutdown:
            try:
                # Update risk metrics for all portfolios
                portfolio_service = await get_portfolio_management_service()
                
                for portfolio_id in portfolio_service.portfolios.keys():
                    await self.calculate_portfolio_risk(portfolio_id)
                
                await asyncio.sleep(self.metrics_update_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics update loop: {e}")
                await asyncio.sleep(self.metrics_update_interval)
    
    async def _alert_processing_loop(self):
        """Alert processing and escalation loop"""
        while not self._shutdown:
            try:
                # Process unacknowledged alerts
                critical_alerts = [
                    alert for alert in self.active_alerts.values()
                    if alert.severity == "critical" and not alert.acknowledged
                ]
                
                for alert in critical_alerts:
                    await self._process_critical_alert(alert)
                
                await asyncio.sleep(self.alert_check_interval)
                
            except Exception as e:
                logger.error(f"Error in alert processing loop: {e}")
                await asyncio.sleep(self.alert_check_interval)
    
    # Helper methods
    
    async def _validate_position_risk(
        self,
        portfolio_id: str,
        signal: TradingSignal,
        position_size: Decimal
    ) -> Dict[str, Any]:
        """Validate position against risk limits"""
        # Simplified validation - would be more comprehensive in production
        return {
            "approved": True,
            "warnings": [],
            "max_multiplier": 1.0
        }
    
    def _calculate_crypto_exposure(self, portfolio_analytics: Dict[str, Any]) -> float:
        """Calculate cryptocurrency exposure percentage"""
        # Simplified calculation - would analyze actual positions
        return 0.3  # Placeholder 30%
    
    def _generate_simulated_returns(self, portfolio_id: str) -> List[float]:
        """Generate simulated return series for testing"""
        # In production, this would fetch actual historical returns
        np.random.seed(hash(portfolio_id) % 2**32)
        returns = np.random.normal(0.0008, 0.02, 252)  # Daily returns for 1 year
        return returns.tolist()
    
    def _generate_equity_curve(self, portfolio_id: str) -> List[float]:
        """Generate equity curve for drawdown calculation"""
        returns = self._generate_simulated_returns(portfolio_id)
        equity_curve = [100000]  # Starting value
        
        for return_val in returns:
            new_value = equity_curve[-1] * (1 + return_val)
            equity_curve.append(new_value)
        
        return equity_curve
    
    # Additional helper methods would be implemented here...


# Global service instance
_risk_management_service: Optional[RiskManagementService] = None


async def get_risk_management_service() -> RiskManagementService:
    """Get the global risk management service instance"""
    global _risk_management_service
    
    if _risk_management_service is None:
        _risk_management_service = RiskManagementService()
        await _risk_management_service.initialize()
    
    return _risk_management_service


@asynccontextmanager
async def risk_management_context():
    """Context manager for risk management service"""
    service = await get_risk_management_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass