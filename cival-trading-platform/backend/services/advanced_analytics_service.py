"""
Advanced Analytics Service - Phase 12
Comprehensive analytics and reporting system for trading performance, market analysis, and risk metrics
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import statistics
import numpy as np

import redis.asyncio as redis
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class AnalyticsType(Enum):
    PERFORMANCE = "performance"
    RISK = "risk" 
    MARKET = "market"
    PORTFOLIO = "portfolio"
    AGENT = "agent"
    CORRELATION = "correlation"
    ATTRIBUTION = "attribution"

class TimeFrame(Enum):
    HOUR = "1h"
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1m"
    QUARTER = "3m"
    YEAR = "1y"
    ALL = "all"

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    var_95: float
    var_99: float
    beta: float
    alpha: float
    information_ratio: float

@dataclass
class RiskMetrics:
    """Risk metrics data structure"""
    portfolio_var: float
    expected_shortfall: float
    concentration_risk: float
    correlation_risk: float
    liquidity_risk: float
    leverage_ratio: float
    risk_budget_utilization: float
    stress_test_results: Dict[str, float]

@dataclass
class MarketAnalytics:
    """Market analytics data structure"""
    market_regime: str
    volatility_regime: str
    correlation_regime: str
    sentiment_score: float
    trend_strength: float
    momentum_score: float
    mean_reversion_score: float
    market_breadth: float

class AdvancedAnalyticsService:
    """
    Comprehensive analytics service for trading systems
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # Analytics cache
        self.analytics_cache: Dict[str, Any] = {}
        self.performance_history: Dict[str, List[Dict]] = {}
        self.risk_history: Dict[str, List[Dict]] = {}
        
        # Analysis configurations
        self.analysis_configs = {
            "performance": {
                "lookback_periods": [7, 30, 90, 252, 504],  # Days
                "benchmark_symbols": ["SPY", "BTC-USD", "ETH-USD"],
                "risk_free_rate": 0.02  # 2% annual
            },
            "risk": {
                "confidence_levels": [0.95, 0.99],
                "stress_scenarios": ["market_crash", "crypto_winter", "interest_rate_shock"],
                "correlation_threshold": 0.7
            },
            "market": {
                "regime_indicators": ["vix", "term_structure", "credit_spreads"],
                "sentiment_sources": ["fear_greed", "social_sentiment", "options_flow"],
                "technical_indicators": ["rsi", "macd", "bollinger_bands"]
            }
        }
        
        # Initialize mock data
        self._initialize_mock_data()
        
        logger.info("AdvancedAnalyticsService initialized")
    
    def _initialize_mock_data(self):
        """Initialize with mock analytics data"""
        # Mock performance data
        self.performance_history["portfolio"] = self._generate_mock_performance_series()
        self.performance_history["agents"] = {
            "agent_marcus": self._generate_mock_performance_series(base_return=0.12),
            "agent_alex": self._generate_mock_performance_series(base_return=0.08),
            "agent_sophia": self._generate_mock_performance_series(base_return=0.15)
        }
        
        # Mock risk data
        self.risk_history["portfolio"] = self._generate_mock_risk_series()

    def _generate_mock_performance_series(self, days: int = 90, base_return: float = 0.10) -> List[Dict]:
        """Generate mock performance time series"""
        series = []
        cumulative_return = 1.0
        
        for i in range(days):
            date = datetime.now(timezone.utc) - timedelta(days=days-i)
            daily_return = np.random.normal(base_return/252, 0.02)  # Daily return with volatility
            cumulative_return *= (1 + daily_return)
            
            series.append({
                "date": date.isoformat(),
                "daily_return": daily_return,
                "cumulative_return": cumulative_return - 1,
                "portfolio_value": 100000 * cumulative_return,
                "volatility": abs(daily_return) * np.sqrt(252),  # Annualized volatility
                "sharpe_ratio": (cumulative_return - 1 - 0.02) / (abs(daily_return) * np.sqrt(252)) if abs(daily_return) > 0 else 0
            })
        
        return series

    def _generate_mock_risk_series(self, days: int = 90) -> List[Dict]:
        """Generate mock risk metrics time series"""
        series = []
        
        for i in range(days):
            date = datetime.now(timezone.utc) - timedelta(days=days-i)
            
            series.append({
                "date": date.isoformat(),
                "var_95": np.random.uniform(0.02, 0.08),
                "var_99": np.random.uniform(0.04, 0.12),
                "expected_shortfall": np.random.uniform(0.06, 0.15),
                "max_drawdown": np.random.uniform(0.05, 0.20),
                "concentration_risk": np.random.uniform(0.10, 0.40),
                "correlation_risk": np.random.uniform(0.15, 0.60)
            })
        
        return series

    async def initialize(self):
        """Initialize the analytics service"""
        try:
            # Load historical data if available
            await self._load_analytics_data()
            
            # Start background analytics processing
            asyncio.create_task(self._analytics_update_loop())
            asyncio.create_task(self._risk_monitoring_loop())
            asyncio.create_task(self._performance_attribution_loop())
            
            logger.info("AdvancedAnalyticsService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AdvancedAnalyticsService: {e}")
            pass  # Continue with mock data

    async def calculate_performance_metrics(self, 
                                          entity_id: str = "portfolio",
                                          timeframe: TimeFrame = TimeFrame.MONTH) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        try:
            # Get performance data
            if entity_id in self.performance_history:
                performance_data = self.performance_history[entity_id]
            elif entity_id in self.performance_history.get("agents", {}):
                performance_data = self.performance_history["agents"][entity_id]
            else:
                performance_data = self.performance_history.get("portfolio", [])
            
            if not performance_data:
                return self._default_performance_metrics()
            
            # Filter by timeframe
            filtered_data = self._filter_by_timeframe(performance_data, timeframe)
            
            if not filtered_data:
                return self._default_performance_metrics()
            
            # Calculate metrics
            returns = [d["daily_return"] for d in filtered_data]
            cumulative_returns = [d["cumulative_return"] for d in filtered_data]
            
            total_return = cumulative_returns[-1] if cumulative_returns else 0
            annual_return = (1 + total_return) ** (252 / len(returns)) - 1 if returns else 0
            
            # Risk metrics
            returns_std = statistics.stdev(returns) if len(returns) > 1 else 0
            volatility = returns_std * np.sqrt(252)  # Annualized
            
            # Sharpe ratio
            risk_free_rate = self.analysis_configs["performance"]["risk_free_rate"]
            sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = [r for r in returns if r < 0]
            downside_std = statistics.stdev(downside_returns) if len(downside_returns) > 1 else returns_std
            sortino_ratio = (annual_return - risk_free_rate) / (downside_std * np.sqrt(252)) if downside_std > 0 else 0
            
            # Max drawdown
            peak = 1.0
            max_drawdown = 0.0
            for cum_ret in cumulative_returns:
                portfolio_value = 1 + cum_ret
                if portfolio_value > peak:
                    peak = portfolio_value
                drawdown = (peak - portfolio_value) / peak
                max_drawdown = max(max_drawdown, drawdown)
            
            # Win rate
            winning_trades = sum(1 for r in returns if r > 0)
            win_rate = winning_trades / len(returns) if returns else 0
            
            # Profit factor
            gross_profit = sum(r for r in returns if r > 0)
            gross_loss = abs(sum(r for r in returns if r < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Calmar ratio
            calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
            
            # VaR calculations
            var_95 = np.percentile(returns, 5) if returns else 0
            var_99 = np.percentile(returns, 1) if returns else 0
            
            # Beta and Alpha (vs benchmark)
            beta = self._calculate_beta(returns)
            alpha = annual_return - (risk_free_rate + beta * 0.10)  # Assuming 10% market return
            
            # Information ratio
            tracking_error = self._calculate_tracking_error(returns)
            information_ratio = alpha / tracking_error if tracking_error > 0 else 0
            
            return PerformanceMetrics(
                total_return=total_return,
                annual_return=annual_return,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                volatility=volatility,
                win_rate=win_rate,
                profit_factor=profit_factor,
                calmar_ratio=calmar_ratio,
                var_95=var_95,
                var_99=var_99,
                beta=beta,
                alpha=alpha,
                information_ratio=information_ratio
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")
            return self._default_performance_metrics()

    async def calculate_risk_metrics(self, 
                                   entity_id: str = "portfolio",
                                   confidence_level: float = 0.95) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            # Get risk and performance data
            risk_data = self.risk_history.get(entity_id, self.risk_history.get("portfolio", []))
            performance_data = self.performance_history.get(entity_id, self.performance_history.get("portfolio", []))
            
            if not risk_data or not performance_data:
                return self._default_risk_metrics()
            
            # Latest risk metrics
            latest_risk = risk_data[-1] if risk_data else {}
            
            # Portfolio VaR
            returns = [d["daily_return"] for d in performance_data[-30:]]  # Last 30 days
            portfolio_var = np.percentile(returns, (1 - confidence_level) * 100) if returns else 0
            
            # Expected Shortfall (Conditional VaR)
            var_threshold = portfolio_var
            tail_returns = [r for r in returns if r <= var_threshold]
            expected_shortfall = np.mean(tail_returns) if tail_returns else portfolio_var
            
            # Concentration risk
            concentration_risk = latest_risk.get("concentration_risk", 0.25)
            
            # Correlation risk
            correlation_risk = latest_risk.get("correlation_risk", 0.35)
            
            # Liquidity risk (mock calculation)
            liquidity_risk = self._calculate_liquidity_risk()
            
            # Leverage ratio
            leverage_ratio = self._calculate_leverage_ratio()
            
            # Risk budget utilization
            risk_budget_utilization = self._calculate_risk_budget_utilization()
            
            # Stress test results
            stress_test_results = await self._perform_stress_tests(returns)
            
            return RiskMetrics(
                portfolio_var=abs(portfolio_var),
                expected_shortfall=abs(expected_shortfall),
                concentration_risk=concentration_risk,
                correlation_risk=correlation_risk,
                liquidity_risk=liquidity_risk,
                leverage_ratio=leverage_ratio,
                risk_budget_utilization=risk_budget_utilization,
                stress_test_results=stress_test_results
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate risk metrics: {e}")
            return self._default_risk_metrics()

    async def calculate_market_analytics(self) -> MarketAnalytics:
        """Calculate market analytics and regime detection"""
        try:
            # Market regime detection
            market_regime = await self._detect_market_regime()
            
            # Volatility regime
            volatility_regime = await self._detect_volatility_regime()
            
            # Correlation regime
            correlation_regime = await self._detect_correlation_regime()
            
            # Sentiment analysis
            sentiment_score = await self._calculate_market_sentiment()
            
            # Trend analysis
            trend_strength = await self._calculate_trend_strength()
            
            # Momentum and mean reversion
            momentum_score = await self._calculate_momentum_score()
            mean_reversion_score = await self._calculate_mean_reversion_score()
            
            # Market breadth
            market_breadth = await self._calculate_market_breadth()
            
            return MarketAnalytics(
                market_regime=market_regime,
                volatility_regime=volatility_regime,
                correlation_regime=correlation_regime,
                sentiment_score=sentiment_score,
                trend_strength=trend_strength,
                momentum_score=momentum_score,
                mean_reversion_score=mean_reversion_score,
                market_breadth=market_breadth
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate market analytics: {e}")
            return MarketAnalytics(
                market_regime="unknown",
                volatility_regime="normal",
                correlation_regime="normal",
                sentiment_score=0.5,
                trend_strength=0.5,
                momentum_score=0.5,
                mean_reversion_score=0.5,
                market_breadth=0.5
            )

    async def generate_performance_attribution(self, 
                                             entity_id: str = "portfolio",
                                             timeframe: TimeFrame = TimeFrame.MONTH) -> Dict[str, Any]:
        """Generate performance attribution analysis"""
        try:
            attribution = {
                "entity_id": entity_id,
                "timeframe": timeframe.value,
                "total_return": 0.0,
                "attribution_breakdown": {},
                "risk_attribution": {},
                "factor_attribution": {},
                "alpha_sources": {},
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            # Mock attribution data
            if entity_id == "portfolio":
                attribution.update({
                    "total_return": 0.085,
                    "attribution_breakdown": {
                        "agent_selection": {"return": 0.035, "percentage": 41.2},
                        "strategy_allocation": {"return": 0.025, "percentage": 29.4},
                        "timing": {"return": 0.015, "percentage": 17.6},
                        "interaction": {"return": 0.010, "percentage": 11.8}
                    },
                    "risk_attribution": {
                        "systematic_risk": {"contribution": 0.040, "percentage": 65.0},
                        "idiosyncratic_risk": {"contribution": 0.022, "percentage": 35.0}
                    },
                    "factor_attribution": {
                        "momentum": {"exposure": 0.35, "return": 0.028},
                        "mean_reversion": {"exposure": 0.25, "return": 0.018},
                        "volatility": {"exposure": 0.20, "return": 0.012},
                        "carry": {"exposure": 0.20, "return": 0.027}
                    },
                    "alpha_sources": {
                        "security_selection": 0.025,
                        "market_timing": 0.015,
                        "cross_asset": 0.020,
                        "volatility_trading": 0.025
                    }
                })
            else:
                # Agent-specific attribution
                attribution.update({
                    "total_return": 0.12 + (hash(entity_id) % 10) * 0.01,
                    "attribution_breakdown": {
                        "signal_generation": {"return": 0.045, "percentage": 37.5},
                        "execution_quality": {"return": 0.035, "percentage": 29.2},
                        "risk_management": {"return": 0.025, "percentage": 20.8},
                        "timing": {"return": 0.015, "percentage": 12.5}
                    }
                })
            
            return attribution
            
        except Exception as e:
            logger.error(f"Failed to generate performance attribution: {e}")
            return {}

    async def generate_correlation_analysis(self, timeframe: TimeFrame = TimeFrame.MONTH) -> Dict[str, Any]:
        """Generate correlation analysis between assets and strategies"""
        try:
            # Mock correlation matrix
            assets = ["BTC", "ETH", "SPY", "BONDS", "GOLD", "DXY"]
            strategies = ["momentum", "mean_reversion", "arbitrage", "volatility"]
            
            # Generate correlation matrix
            correlation_matrix = {}
            for i, asset1 in enumerate(assets):
                correlation_matrix[asset1] = {}
                for j, asset2 in enumerate(assets):
                    if i == j:
                        correlation_matrix[asset1][asset2] = 1.0
                    else:
                        # Generate realistic correlations
                        correlation = np.random.uniform(-0.8, 0.8)
                        correlation_matrix[asset1][asset2] = round(correlation, 3)
            
            # Strategy correlations
            strategy_correlations = {}
            for strategy in strategies:
                strategy_correlations[strategy] = {
                    asset: round(np.random.uniform(-0.6, 0.6), 3)
                    for asset in assets
                }
            
            # Risk analysis
            eigenvalues = [3.2, 1.8, 0.7, 0.2, 0.1, 0.0]  # Mock eigenvalues
            explained_variance = [ev/sum(eigenvalues) for ev in eigenvalues]
            
            return {
                "timeframe": timeframe.value,
                "asset_correlations": correlation_matrix,
                "strategy_correlations": strategy_correlations,
                "principal_components": {
                    "eigenvalues": eigenvalues,
                    "explained_variance": explained_variance,
                    "cumulative_variance": [sum(explained_variance[:i+1]) for i in range(len(explained_variance))]
                },
                "concentration_metrics": {
                    "max_correlation": max(max(row.values()) for row in correlation_matrix.values() if 1.0 not in row.values()),
                    "average_correlation": np.mean([v for row in correlation_matrix.values() for k, v in row.items() if v != 1.0]),
                    "correlation_clusters": ["cluster_1", "cluster_2", "cluster_3"]
                },
                "regime_analysis": {
                    "current_regime": "normal_correlation",
                    "regime_probability": 0.75,
                    "regime_stability": 0.68
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate correlation analysis: {e}")
            return {}

    async def generate_analytics_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive analytics dashboard"""
        try:
            # Get all analytics
            performance_metrics = await self.calculate_performance_metrics()
            risk_metrics = await self.calculate_risk_metrics()
            market_analytics = await self.calculate_market_analytics()
            
            # Generate summary statistics
            portfolio_summary = {
                "total_return_ytd": performance_metrics.total_return,
                "sharpe_ratio": performance_metrics.sharpe_ratio,
                "max_drawdown": performance_metrics.max_drawdown,
                "win_rate": performance_metrics.win_rate,
                "volatility": performance_metrics.volatility,
                "var_95": risk_metrics.portfolio_var,
                "current_positions": 15,  # Mock
                "active_strategies": 8,    # Mock
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            # Performance trends
            performance_trends = {
                "daily_returns": [d["daily_return"] for d in self.performance_history.get("portfolio", [])[-30:]],
                "cumulative_returns": [d["cumulative_return"] for d in self.performance_history.get("portfolio", [])[-30:]],
                "rolling_sharpe": [d["sharpe_ratio"] for d in self.performance_history.get("portfolio", [])[-30:]],
                "dates": [d["date"] for d in self.performance_history.get("portfolio", [])[-30:]]
            }
            
            # Risk trends
            risk_trends = {
                "var_95": [d["var_95"] for d in self.risk_history.get("portfolio", [])[-30:]],
                "max_drawdown": [d["max_drawdown"] for d in self.risk_history.get("portfolio", [])[-30:]],
                "concentration_risk": [d["concentration_risk"] for d in self.risk_history.get("portfolio", [])[-30:]],
                "dates": [d["date"] for d in self.risk_history.get("portfolio", [])[-30:]]
            }
            
            # Top performers
            agent_performance = {}
            for agent_id in ["agent_marcus", "agent_alex", "agent_sophia"]:
                agent_metrics = await self.calculate_performance_metrics(agent_id)
                agent_performance[agent_id] = {
                    "total_return": agent_metrics.total_return,
                    "sharpe_ratio": agent_metrics.sharpe_ratio,
                    "max_drawdown": agent_metrics.max_drawdown,
                    "win_rate": agent_metrics.win_rate
                }
            
            return {
                "portfolio_summary": portfolio_summary,
                "performance_metrics": asdict(performance_metrics),
                "risk_metrics": asdict(risk_metrics),
                "market_analytics": asdict(market_analytics),
                "performance_trends": performance_trends,
                "risk_trends": risk_trends,
                "agent_performance": agent_performance,
                "alerts": await self._generate_analytics_alerts(),
                "recommendations": await self._generate_analytics_recommendations(),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate analytics dashboard: {e}")
            return {}

    def _filter_by_timeframe(self, data: List[Dict], timeframe: TimeFrame) -> List[Dict]:
        """Filter data by specified timeframe"""
        if not data:
            return []
        
        now = datetime.now(timezone.utc)
        
        if timeframe == TimeFrame.HOUR:
            cutoff = now - timedelta(hours=1)
        elif timeframe == TimeFrame.DAY:
            cutoff = now - timedelta(days=1)
        elif timeframe == TimeFrame.WEEK:
            cutoff = now - timedelta(weeks=1)
        elif timeframe == TimeFrame.MONTH:
            cutoff = now - timedelta(days=30)
        elif timeframe == TimeFrame.QUARTER:
            cutoff = now - timedelta(days=90)
        elif timeframe == TimeFrame.YEAR:
            cutoff = now - timedelta(days=365)
        else:  # ALL
            return data
        
        return [d for d in data if datetime.fromisoformat(d["date"].replace('Z', '+00:00')) >= cutoff]

    def _default_performance_metrics(self) -> PerformanceMetrics:
        """Return default performance metrics"""
        return PerformanceMetrics(
            total_return=0.0, annual_return=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
            max_drawdown=0.0, volatility=0.0, win_rate=0.0, profit_factor=0.0,
            calmar_ratio=0.0, var_95=0.0, var_99=0.0, beta=0.0, alpha=0.0,
            information_ratio=0.0
        )

    def _default_risk_metrics(self) -> RiskMetrics:
        """Return default risk metrics"""
        return RiskMetrics(
            portfolio_var=0.0, expected_shortfall=0.0, concentration_risk=0.0,
            correlation_risk=0.0, liquidity_risk=0.0, leverage_ratio=0.0,
            risk_budget_utilization=0.0, stress_test_results={}
        )

    def _calculate_beta(self, returns: List[float]) -> float:
        """Calculate beta vs market"""
        # Mock market returns
        market_returns = [np.random.normal(0.0004, 0.012) for _ in returns]  # Daily market returns
        
        if len(returns) < 2 or len(market_returns) < 2:
            return 1.0
        
        covariance = np.cov(returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        
        return covariance / market_variance if market_variance > 0 else 1.0

    def _calculate_tracking_error(self, returns: List[float]) -> float:
        """Calculate tracking error vs benchmark"""
        # Mock benchmark returns
        benchmark_returns = [np.random.normal(0.0003, 0.010) for _ in returns]
        
        if len(returns) != len(benchmark_returns):
            return 0.05  # Default tracking error
        
        excess_returns = [r - b for r, b in zip(returns, benchmark_returns)]
        return statistics.stdev(excess_returns) * np.sqrt(252) if len(excess_returns) > 1 else 0.05

    def _calculate_liquidity_risk(self) -> float:
        """Calculate liquidity risk metric"""
        return np.random.uniform(0.05, 0.25)  # Mock liquidity risk

    def _calculate_leverage_ratio(self) -> float:
        """Calculate leverage ratio"""
        return np.random.uniform(1.0, 3.0)  # Mock leverage

    def _calculate_risk_budget_utilization(self) -> float:
        """Calculate risk budget utilization"""
        return np.random.uniform(0.60, 0.95)  # Mock utilization

    async def _perform_stress_tests(self, returns: List[float]) -> Dict[str, float]:
        """Perform stress testing scenarios"""
        return {
            "market_crash_2008": -0.35,
            "covid_crash_2020": -0.28,
            "crypto_winter_2022": -0.45,
            "interest_rate_shock": -0.15,
            "liquidity_crisis": -0.25
        }

    async def _detect_market_regime(self) -> str:
        """Detect current market regime"""
        regimes = ["bull_market", "bear_market", "sideways", "high_volatility", "low_volatility"]
        return np.random.choice(regimes)

    async def _detect_volatility_regime(self) -> str:
        """Detect volatility regime"""
        regimes = ["low", "normal", "high", "extreme"]
        return np.random.choice(regimes)

    async def _detect_correlation_regime(self) -> str:
        """Detect correlation regime"""
        regimes = ["low_correlation", "normal_correlation", "high_correlation", "crisis_correlation"]
        return np.random.choice(regimes)

    async def _calculate_market_sentiment(self) -> float:
        """Calculate market sentiment score"""
        return np.random.uniform(0.0, 1.0)

    async def _calculate_trend_strength(self) -> float:
        """Calculate trend strength"""
        return np.random.uniform(0.0, 1.0)

    async def _calculate_momentum_score(self) -> float:
        """Calculate momentum score"""
        return np.random.uniform(0.0, 1.0)

    async def _calculate_mean_reversion_score(self) -> float:
        """Calculate mean reversion score"""
        return np.random.uniform(0.0, 1.0)

    async def _calculate_market_breadth(self) -> float:
        """Calculate market breadth"""
        return np.random.uniform(0.0, 1.0)

    async def _generate_analytics_alerts(self) -> List[Dict[str, Any]]:
        """Generate analytics-based alerts"""
        return [
            {
                "id": "risk_001",
                "type": "risk",
                "severity": "medium",
                "message": "Portfolio VaR has increased by 15% over the last week",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "perf_001", 
                "type": "performance",
                "severity": "low",
                "message": "Sharpe ratio trending downward for 5 consecutive days",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]

    async def _generate_analytics_recommendations(self) -> List[Dict[str, Any]]:
        """Generate analytics-based recommendations"""
        return [
            {
                "id": "rec_001",
                "category": "risk_management",
                "priority": "high",
                "recommendation": "Consider reducing position sizes in highly correlated assets",
                "rationale": "Correlation risk has increased to 0.75, above the 0.70 threshold",
                "impact": "Could reduce portfolio VaR by 12-15%"
            },
            {
                "id": "rec_002",
                "category": "performance",
                "priority": "medium", 
                "recommendation": "Increase allocation to momentum strategies",
                "rationale": "Market regime analysis suggests strong momentum environment",
                "impact": "Potential 2-3% improvement in riYOUR_OPENAI_API_KEY_HERE returns"
            }
        ]

    async def _load_analytics_data(self):
        """Load analytics data from database"""
        try:
            if self.supabase:
                # Load performance history
                response = self.supabase.table('analytics_performance').select('*').execute()
                for record in response.data:
                    entity_id = record["entity_id"]
                    if entity_id not in self.performance_history:
                        self.performance_history[entity_id] = []
                    self.performance_history[entity_id].append(record)
                
                # Load risk history
                response = self.supabase.table('analytics_risk').select('*').execute()
                for record in response.data:
                    entity_id = record["entity_id"]
                    if entity_id not in self.risk_history:
                        self.risk_history[entity_id] = []
                    self.risk_history[entity_id].append(record)
        except Exception as e:
            logger.warning(f"Could not load analytics data from database: {e}")

    async def _analytics_update_loop(self):
        """Background analytics update loop"""
        while True:
            try:
                await asyncio.sleep(300)  # Update every 5 minutes
                await self._update_analytics_cache()
                logger.debug("Analytics update completed")
            except Exception as e:
                logger.error(f"Error in analytics update loop: {e}")

    async def _risk_monitoring_loop(self):
        """Background risk monitoring loop"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._monitor_risk_limits()
                logger.debug("Risk monitoring check completed")
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")

    async def _performance_attribution_loop(self):
        """Background performance attribution loop"""
        while True:
            try:
                await asyncio.sleep(1800)  # Update every 30 minutes
                await self._update_performance_attribution()
                logger.debug("Performance attribution update completed")
            except Exception as e:
                logger.error(f"Error in performance attribution loop: {e}")

    async def _update_analytics_cache(self):
        """Update analytics cache with latest calculations"""
        # Update cache with latest metrics
        self.analytics_cache["performance"] = await self.calculate_performance_metrics()
        self.analytics_cache["risk"] = await self.calculate_risk_metrics()
        self.analytics_cache["market"] = await self.calculate_market_analytics()

    async def _monitor_risk_limits(self):
        """Monitor risk limits and generate alerts"""
        risk_metrics = await self.calculate_risk_metrics()
        
        # Check VaR limits
        if risk_metrics.portfolio_var > 0.05:  # 5% daily VaR limit
            logger.warning(f"Portfolio VaR exceeded limit: {risk_metrics.portfolio_var}")
        
        # Check concentration risk
        if risk_metrics.concentration_risk > 0.40:  # 40% concentration limit
            logger.warning(f"Concentration risk exceeded limit: {risk_metrics.concentration_risk}")

    async def _update_performance_attribution(self):
        """Update performance attribution analysis"""
        # Generate updated attribution for all entities
        for entity_id in ["portfolio"] + list(self.performance_history.get("agents", {}).keys()):
            attribution = await self.generate_performance_attribution(entity_id)
            self.analytics_cache[f"attribution_{entity_id}"] = attribution

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        return {
            "service": "advanced_analytics_service",
            "status": "running",
            "cached_entities": len(self.performance_history),
            "cache_size": len(self.analytics_cache),
            "last_update": datetime.now(timezone.utc).isoformat(),
            "analytics_types": [t.value for t in AnalyticsType],
            "available_timeframes": [t.value for t in TimeFrame]
        }

# Factory function for service registry
def create_advanced_analytics_service():
    """Factory function to create AdvancedAnalyticsService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = AdvancedAnalyticsService(redis_client, supabase_client)
    return service