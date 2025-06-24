"""
Phase 15: Advanced Risk Management System
Comprehensive risk assessment, monitoring, and mitigation for autonomous trading
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
import pandas as pd
from collections import defaultdict, deque
import math

from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskType(Enum):
    """Types of risk"""
    MARKET_RISK = "market_risk"
    CREDIT_RISK = "credit_risk"
    OPERATIONAL_RISK = "operational_risk"
    LIQUIDITY_RISK = "liquidity_risk"
    CONCENTRATION_RISK = "concentration_risk"
    CORRELATION_RISK = "correlation_risk"
    VOLATILITY_RISK = "volatility_risk"
    DRAWDOWN_RISK = "drawdown_risk"
    LEVERAGE_RISK = "leverage_risk"
    COUNTERPARTY_RISK = "counterparty_risk"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    portfolio_var: Decimal  # Value at Risk
    portfolio_cvar: Decimal  # Conditional Value at Risk
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    beta: float
    alpha: float
    volatility: float
    correlation_matrix: Dict[str, Dict[str, float]]
    leverage_ratio: float
    liquidity_score: float
    concentration_risk: float
    stress_test_results: Dict[str, float]
    timestamp: datetime

@dataclass
class RiskLimit:
    """Risk limit definition"""
    limit_id: str
    name: str
    risk_type: RiskType
    metric: str
    threshold: float
    operator: str  # >, <, >=, <=
    action: str  # alert, reduce_position, stop_trading
    severity: AlertSeverity
    enabled: bool
    description: str

@dataclass
class RiskAlert:
    """Risk alert structure"""
    alert_id: str
    risk_type: RiskType
    severity: AlertSeverity
    title: str
    description: str
    current_value: float
    threshold: float
    recommended_action: str
    affected_positions: List[str]
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None

@dataclass
class StressTestScenario:
    """Stress test scenario definition"""
    scenario_id: str
    name: str
    description: str
    market_shocks: Dict[str, float]  # symbol -> percentage change
    correlation_changes: Dict[str, float]
    volatility_multipliers: Dict[str, float]
    duration_days: int
    probability: float

@dataclass
class Position:
    """Position data for risk calculations"""
    symbol: str
    quantity: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    cost_basis: Decimal
    last_price: Decimal
    volatility: float
    beta: float
    weight: float  # Portfolio weight

class AdvancedRiskManagement:
    """
    Advanced risk management system
    Phase 15: Comprehensive risk assessment and mitigation
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Service dependencies
        self.portfolio_service = None
        self.market_data_service = None
        self.trading_orchestrator = None
        self.multi_exchange_service = None
        self.event_service = None
        
        # Risk state
        self.current_metrics: Optional[RiskMetrics] = None
        self.risk_limits: Dict[str, RiskLimit] = {}
        self.active_alerts: List[RiskAlert] = []
        self.alert_history: deque = deque(maxlen=1000)
        
        # Historical data for calculations
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=252))  # 1 year
        self.return_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=252))
        self.portfolio_value_history: deque = deque(maxlen=252)
        self.drawdown_history: deque = deque(maxlen=252)
        
        # Risk models
        self.correlation_matrix: pd.DataFrame = pd.DataFrame()
        self.var_model_params: Dict[str, Any] = {}
        self.stress_test_scenarios: Dict[str, StressTestScenario] = {}
        
        # Configuration
        self.risk_config = {
            'var_confidence_level': 0.95,
            'var_lookback_days': 252,
            'correlation_lookback_days': 60,
            'max_portfolio_var': 0.05,  # 5% of portfolio
            'max_single_position_weight': 0.20,  # 20%
            'max_sector_weight': 0.40,  # 40%
            'max_leverage': 3.0,
            'min_liquidity_score': 0.3,
            'stress_test_frequency_hours': 6
        }
        
        # Performance tracking
        self.risk_metrics_history: deque = deque(maxlen=1000)
        self.intervention_count = 0
        self.prevented_losses = Decimal("0")
        
        logger.info("AdvancedRiskManagement Phase 15 initialized")
    
    async def initialize(self):
        """Initialize the risk management system"""
        try:
            # Get required services
            self.portfolio_service = self.registry.get_service("portfolio_management_service")
            self.market_data_service = self.registry.get_service("market_data_service")
            self.trading_orchestrator = self.registry.get_service("advanced_trading_orchestrator")
            self.multi_exchange_service = self.registry.get_service("multi_exchange_integration")
            self.event_service = self.registry.get_service("wallet_event_streaming_service")
            
            # Initialize risk limits
            await self._initialize_risk_limits()
            
            # Initialize stress test scenarios
            await self._initialize_stress_test_scenarios()
            
            # Start background risk monitoring
            asyncio.create_task(self._risk_monitoring_loop())
            asyncio.create_task(self._correlation_analysis_loop())
            asyncio.create_task(self._stress_testing_loop())
            asyncio.create_task(self._drawdown_monitoring_loop())
            asyncio.create_task(self._liquidity_monitoring_loop())
            asyncio.create_task(self._risk_reporting_loop())
            
            logger.info("AdvancedRiskManagement initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AdvancedRiskManagement: {e}")
            raise
    
    async def _initialize_risk_limits(self):
        """Initialize default risk limits"""
        try:
            limits = [
                RiskLimit(
                    limit_id="portfolio_var_limit",
                    name="Portfolio Value at Risk",
                    risk_type=RiskType.MARKET_RISK,
                    metric="portfolio_var",
                    threshold=0.05,  # 5%
                    operator=">=",
                    action="reduce_position",
                    severity=AlertSeverity.WARNING,
                    enabled=True,
                    description="Maximum portfolio VaR at 95% confidence"
                ),
                
                RiskLimit(
                    limit_id="max_drawdown_limit",
                    name="Maximum Drawdown",
                    risk_type=RiskType.DRAWDOWN_RISK,
                    metric="max_drawdown",
                    threshold=0.15,  # 15%
                    operator=">=",
                    action="stop_trading",
                    severity=AlertSeverity.CRITICAL,
                    enabled=True,
                    description="Maximum allowable portfolio drawdown"
                ),
                
                RiskLimit(
                    limit_id="single_position_limit",
                    name="Single Position Weight",
                    risk_type=RiskType.CONCENTRATION_RISK,
                    metric="max_position_weight",
                    threshold=0.20,  # 20%
                    operator=">=",
                    action="reduce_position",
                    severity=AlertSeverity.WARNING,
                    enabled=True,
                    description="Maximum weight for any single position"
                ),
                
                RiskLimit(
                    limit_id="leverage_limit",
                    name="Portfolio Leverage",
                    risk_type=RiskType.LEVERAGE_RISK,
                    metric="leverage_ratio",
                    threshold=3.0,
                    operator=">=",
                    action="reduce_position",
                    severity=AlertSeverity.CRITICAL,
                    enabled=True,
                    description="Maximum portfolio leverage ratio"
                ),
                
                RiskLimit(
                    limit_id="correlation_limit",
                    name="Portfolio Correlation",
                    risk_type=RiskType.CORRELATION_RISK,
                    metric="avg_correlation",
                    threshold=0.80,
                    operator=">=",
                    action="alert",
                    severity=AlertSeverity.WARNING,
                    enabled=True,
                    description="Maximum average correlation between positions"
                ),
                
                RiskLimit(
                    limit_id="liquidity_limit",
                    name="Portfolio Liquidity",
                    risk_type=RiskType.LIQUIDITY_RISK,
                    metric="liquidity_score",
                    threshold=0.30,
                    operator="<=",
                    action="alert",
                    severity=AlertSeverity.WARNING,
                    enabled=True,
                    description="Minimum portfolio liquidity score"
                ),
                
                RiskLimit(
                    limit_id="volatility_limit",
                    name="Portfolio Volatility",
                    risk_type=RiskType.VOLATILITY_RISK,
                    metric="volatility",
                    threshold=0.40,  # 40% annualized
                    operator=">=",
                    action="reduce_position",
                    severity=AlertSeverity.WARNING,
                    enabled=True,
                    description="Maximum portfolio volatility"
                )
            ]
            
            for limit in limits:
                self.risk_limits[limit.limit_id] = limit
            
            logger.info(f"Initialized {len(limits)} risk limits")
            
        except Exception as e:
            logger.error(f"Failed to initialize risk limits: {e}")
            raise
    
    async def _initialize_stress_test_scenarios(self):
        """Initialize stress test scenarios"""
        try:
            scenarios = {
                "market_crash": StressTestScenario(
                    scenario_id="market_crash",
                    name="Market Crash",
                    description="20% market decline across all assets",
                    market_shocks={"BTC": -0.20, "ETH": -0.25, "SOL": -0.30, "AVAX": -0.35},
                    correlation_changes={"all": 0.9},  # High correlation during crisis
                    volatility_multipliers={"all": 2.0},
                    duration_days=30,
                    probability=0.05
                ),
                
                "crypto_winter": StressTestScenario(
                    scenario_id="crypto_winter",
                    name="Crypto Winter",
                    description="Extended bear market with 50% decline",
                    market_shocks={"BTC": -0.50, "ETH": -0.55, "SOL": -0.60, "AVAX": -0.65},
                    correlation_changes={"all": 0.85},
                    volatility_multipliers={"all": 1.8},
                    duration_days=180,
                    probability=0.10
                ),
                
                "regulatory_shock": StressTestScenario(
                    scenario_id="regulatory_shock",
                    name="Regulatory Shock",
                    description="Sudden regulatory crackdown",
                    market_shocks={"BTC": -0.15, "ETH": -0.20, "SOL": -0.25, "AVAX": -0.30},
                    correlation_changes={"all": 0.75},
                    volatility_multipliers={"all": 1.5},
                    duration_days=14,
                    probability=0.15
                ),
                
                "liquidity_crisis": StressTestScenario(
                    scenario_id="liquidity_crisis",
                    name="Liquidity Crisis",
                    description="Major exchange outages and liquidity shortage",
                    market_shocks={"BTC": -0.10, "ETH": -0.12, "SOL": -0.18, "AVAX": -0.20},
                    correlation_changes={"all": 0.95},
                    volatility_multipliers={"all": 3.0},
                    duration_days=7,
                    probability=0.08
                ),
                
                "black_swan": StressTestScenario(
                    scenario_id="black_swan",
                    name="Black Swan Event",
                    description="Extreme tail risk event",
                    market_shocks={"BTC": -0.40, "ETH": -0.45, "SOL": -0.50, "AVAX": -0.55},
                    correlation_changes={"all": 0.98},
                    volatility_multipliers={"all": 4.0},
                    duration_days=3,
                    probability=0.01
                )
            }
            
            self.stress_test_scenarios = scenarios
            logger.info(f"Initialized {len(scenarios)} stress test scenarios")
            
        except Exception as e:
            logger.error(f"Failed to initialize stress test scenarios: {e}")
            raise
    
    async def _risk_monitoring_loop(self):
        """Main risk monitoring loop"""
        while True:
            try:
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
                # Calculate current risk metrics
                risk_metrics = await self._calculate_risk_metrics()
                
                if risk_metrics:
                    self.current_metrics = risk_metrics
                    self.risk_metrics_history.append(risk_metrics)
                    
                    # Check risk limits
                    violations = await self._check_risk_limits(risk_metrics)
                    
                    # Handle violations
                    if violations:
                        await self._handle_risk_violations(violations)
                    
                    # Emit risk update event
                    if self.event_service:
                        await self.event_service.emit_event({
                            'event_type': 'risk.metrics_update',
                            'metrics': asdict(risk_metrics),
                            'violations': [asdict(v) for v in violations],
                            'alert_count': len(self.active_alerts),
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _calculate_risk_metrics(self) -> Optional[RiskMetrics]:
        """Calculate comprehensive risk metrics"""
        try:
            # Get current positions
            positions = await self._get_current_positions()
            if not positions:
                return None
            
            # Calculate portfolio value
            total_value = sum(p.market_value for p in positions)
            
            # Calculate VaR and CVaR
            portfolio_var, portfolio_cvar = await self._calculate_var_cvar(positions)
            
            # Calculate drawdown metrics
            max_drawdown, current_drawdown = await self._calculate_drawdown_metrics()
            
            # Calculate performance ratios
            sharpe_ratio = await self._calculate_sharpe_ratio()
            sortino_ratio = await self._calculate_sortino_ratio()
            
            # Calculate market risk metrics
            beta, alpha = await self._calculate_beta_alpha(positions)
            volatility = await self._calculate_portfolio_volatility(positions)
            
            # Calculate correlation matrix
            correlation_matrix = await self._calculate_correlation_matrix(positions)
            
            # Calculate leverage and concentration
            leverage_ratio = await self._calculate_leverage_ratio(positions, total_value)
            concentration_risk = await self._calculate_concentration_risk(positions)
            
            # Calculate liquidity score
            liquidity_score = await self._calculate_liquidity_score(positions)
            
            # Run stress tests
            stress_test_results = await self._run_stress_tests(positions)
            
            return RiskMetrics(
                portfolio_var=portfolio_var,
                portfolio_cvar=portfolio_cvar,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                beta=beta,
                alpha=alpha,
                volatility=volatility,
                correlation_matrix=correlation_matrix,
                leverage_ratio=leverage_ratio,
                liquidity_score=liquidity_score,
                concentration_risk=concentration_risk,
                stress_test_results=stress_test_results,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return None
    
    async def _calculate_var_cvar(self, positions: List[Position]) -> Tuple[Decimal, Decimal]:
        """Calculate Value at Risk and Conditional Value at Risk"""
        try:
            # Get portfolio returns
            portfolio_returns = await self._calculate_portfolio_returns(positions)
            
            if len(portfolio_returns) < 30:  # Need minimum data
                return Decimal("0"), Decimal("0")
            
            # Convert to numpy array for calculations
            returns = np.array(portfolio_returns)
            
            # Calculate VaR at specified confidence level
            confidence_level = self.risk_config['var_confidence_level']
            var_percentile = (1 - confidence_level) * 100
            var = np.percentile(returns, var_percentile)
            
            # Calculate CVaR (Expected Shortfall)
            tail_returns = returns[returns <= var]
            cvar = np.mean(tail_returns) if len(tail_returns) > 0 else var
            
            # Convert to portfolio value terms
            total_value = sum(p.market_value for p in positions)
            portfolio_var = Decimal(str(abs(var))) * total_value
            portfolio_cvar = Decimal(str(abs(cvar))) * total_value
            
            return portfolio_var, portfolio_cvar
            
        except Exception as e:
            logger.error(f"Error calculating VaR/CVaR: {e}")
            return Decimal("0"), Decimal("0")
    
    async def _calculate_drawdown_metrics(self) -> Tuple[float, float]:
        """Calculate maximum and current drawdown"""
        try:
            if len(self.portfolio_value_history) < 2:
                return 0.0, 0.0
            
            values = list(self.portfolio_value_history)
            
            # Calculate running maximum
            running_max = [values[0]]
            for i in range(1, len(values)):
                running_max.append(max(running_max[i-1], values[i]))
            
            # Calculate drawdowns
            drawdowns = [(values[i] - running_max[i]) / running_max[i] for i in range(len(values))]
            
            max_drawdown = abs(min(drawdowns)) if drawdowns else 0.0
            current_drawdown = abs(drawdowns[-1]) if drawdowns else 0.0
            
            return max_drawdown, current_drawdown
            
        except Exception as e:
            logger.error(f"Error calculating drawdown metrics: {e}")
            return 0.0, 0.0
    
    async def _calculate_portfolio_returns(self, positions: List[Position]) -> List[float]:
        """Calculate historical portfolio returns"""
        try:
            if len(self.portfolio_value_history) < 2:
                return []
            
            values = list(self.portfolio_value_history)
            returns = []
            
            for i in range(1, len(values)):
                if values[i-1] > 0:
                    daily_return = (values[i] - values[i-1]) / values[i-1]
                    returns.append(daily_return)
            
            return returns
            
        except Exception as e:
            logger.error(f"Error calculating portfolio returns: {e}")
            return []
    
    async def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio"""
        try:
            if len(self.portfolio_value_history) < 30:
                return 0.0
            
            returns = await self._calculate_portfolio_returns([])
            if not returns:
                return 0.0
            
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            # Assume risk-free rate of 2% annually (0.02/252 daily)
            risk_free_rate = 0.02 / 252
            
            # Annualize the Sharpe ratio
            sharpe = (avg_return - risk_free_rate) / std_return * np.sqrt(252)
            
            return float(sharpe)
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    async def _calculate_sortino_ratio(self) -> float:
        """Calculate Sortino ratio"""
        try:
            if len(self.portfolio_value_history) < 30:
                return 0.0
            
            returns = await self._calculate_portfolio_returns([])
            if not returns:
                return 0.0
            
            avg_return = np.mean(returns)
            negative_returns = [r for r in returns if r < 0]
            
            if not negative_returns:
                return float('inf')  # No downside risk
            
            downside_std = np.std(negative_returns)
            
            if downside_std == 0:
                return 0.0
            
            # Risk-free rate
            risk_free_rate = 0.02 / 252
            
            # Annualize the Sortino ratio
            sortino = (avg_return - risk_free_rate) / downside_std * np.sqrt(252)
            
            return float(sortino)
            
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0.0
    
    async def _check_risk_limits(self, metrics: RiskMetrics) -> List[RiskAlert]:
        """Check risk metrics against defined limits"""
        violations = []
        
        try:
            for limit_id, limit in self.risk_limits.items():
                if not limit.enabled:
                    continue
                
                # Get current value for the metric
                current_value = self._get_metric_value(metrics, limit.metric)
                
                # Check if limit is violated
                violated = self._check_limit_violation(current_value, limit.threshold, limit.operator)
                
                if violated:
                    # Create alert
                    alert = RiskAlert(
                        alert_id=str(uuid.uuid4()),
                        risk_type=limit.risk_type,
                        severity=limit.severity,
                        title=f"{limit.name} Limit Exceeded",
                        description=f"{limit.description}. Current: {current_value:.4f}, Limit: {limit.threshold}",
                        current_value=current_value,
                        threshold=limit.threshold,
                        recommended_action=limit.action,
                        affected_positions=await self._get_affected_positions(limit.risk_type),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    violations.append(alert)
            
            return violations
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return []
    
    def _get_metric_value(self, metrics: RiskMetrics, metric_name: str) -> float:
        """Get metric value from risk metrics object"""
        metric_mapping = {
            'portfolio_var': float(metrics.portfolio_var),
            'max_drawdown': metrics.max_drawdown,
            'current_drawdown': metrics.current_drawdown,
            'leverage_ratio': metrics.leverage_ratio,
            'volatility': metrics.volatility,
            'liquidity_score': metrics.liquidity_score,
            'concentration_risk': metrics.concentration_risk,
            'avg_correlation': self._calculate_avg_correlation(metrics.correlation_matrix)
        }
        
        return metric_mapping.get(metric_name, 0.0)
    
    def _calculate_avg_correlation(self, correlation_matrix: Dict[str, Dict[str, float]]) -> float:
        """Calculate average correlation from correlation matrix"""
        if not correlation_matrix:
            return 0.0
        
        correlations = []
        symbols = list(correlation_matrix.keys())
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i < j:  # Avoid diagonal and duplicates
                    corr = correlation_matrix.get(symbol1, {}).get(symbol2, 0.0)
                    correlations.append(abs(corr))
        
        return np.mean(correlations) if correlations else 0.0
    
    def _check_limit_violation(self, current_value: float, threshold: float, operator: str) -> bool:
        """Check if a limit is violated"""
        if operator == ">=":
            return current_value >= threshold
        elif operator == "<=":
            return current_value <= threshold
        elif operator == ">":
            return current_value > threshold
        elif operator == "<":
            return current_value < threshold
        else:
            return False
    
    async def _handle_risk_violations(self, violations: List[RiskAlert]):
        """Handle risk limit violations"""
        try:
            for alert in violations:
                # Add to active alerts
                self.active_alerts.append(alert)
                self.alert_history.append(alert)
                
                # Execute recommended actions
                await self._execute_risk_action(alert)
                
                # Emit alert event
                if self.event_service:
                    await self.event_service.emit_event({
                        'event_type': 'risk.alert_created',
                        'alert': asdict(alert),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
                logger.warning(f"Risk alert created: {alert.title}")
            
        except Exception as e:
            logger.error(f"Error handling risk violations: {e}")
    
    async def _execute_risk_action(self, alert: RiskAlert):
        """Execute risk mitigation action"""
        try:
            action = alert.recommended_action
            
            if action == "alert":
                # Just alerting, no automatic action
                pass
            
            elif action == "reduce_position":
                # Reduce positions contributing to risk
                await self._reduce_risky_positions(alert)
                
            elif action == "stop_trading":
                # Stop all trading activities
                await self._emergency_stop_trading(alert)
                
            elif action == "rebalance":
                # Trigger portfolio rebalancing
                await self._trigger_rebalancing(alert)
            
            self.intervention_count += 1
            
        except Exception as e:
            logger.error(f"Error executing risk action {alert.recommended_action}: {e}")
    
    async def _reduce_risky_positions(self, alert: RiskAlert):
        """Reduce positions contributing to risk"""
        try:
            # Get positions to reduce
            positions_to_reduce = alert.affected_positions
            
            # Calculate reduction amounts
            for symbol in positions_to_reduce:
                reduction_percentage = 0.25  # Reduce by 25% initially
                
                # Emit position reduction request
                if self.event_service:
                    await self.event_service.emit_event({
                        'event_type': 'risk.position_reduction_requested',
                        'symbol': symbol,
                        'reduction_percentage': reduction_percentage,
                        'reason': alert.title,
                        'alert_id': alert.alert_id,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            logger.info(f"Requested position reductions for {len(positions_to_reduce)} symbols")
            
        except Exception as e:
            logger.error(f"Error reducing risky positions: {e}")
    
    async def _emergency_stop_trading(self, alert: RiskAlert):
        """Emergency stop all trading"""
        try:
            # Emit emergency stop event
            if self.event_service:
                await self.event_service.emit_event({
                    'event_type': 'risk.emergency_stop_trading',
                    'reason': alert.title,
                    'alert_id': alert.alert_id,
                    'severity': alert.severity.value,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            logger.critical(f"EMERGENCY STOP: Trading halted due to {alert.title}")
            
        except Exception as e:
            logger.error(f"Error executing emergency stop: {e}")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and health metrics"""
        return {
            "service": "advanced_risk_management",
            "status": "running",
            "active_alerts": len(self.active_alerts),
            "risk_limits": len(self.risk_limits),
            "enabled_limits": len([l for l in self.risk_limits.values() if l.enabled]),
            "stress_test_scenarios": len(self.stress_test_scenarios),
            "intervention_count": self.intervention_count,
            "current_metrics": asdict(self.current_metrics) if self.current_metrics else None,
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_advanced_risk_management():
    """Factory function to create AdvancedRiskManagement instance"""
    return AdvancedRiskManagement()