"""
Phase 10: Performance Attribution and Strategy Analytics Service
Comprehensive performance analysis, attribution, and strategy optimization insights
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
import scipy.stats as stats
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.trading_strategy_models import (
    TradingStrategy, TradingPosition, StrategyPerformance, TradingSignal,
    PositionSide, PerformanceMetrics
)
from services.portfolio_management_service import get_portfolio_management_service
from services.risk_management_service import get_risk_management_service
from services.backtesting_service import get_backtesting_service
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class PerformancePeriod(str, Enum):
    """Performance analysis periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    INCEPTION = "inception"


class AttributionMethod(str, Enum):
    """Performance attribution methods"""
    BRINSON = "brinson"          # Brinson-Hood-Beebower
    FACTOR_BASED = "factor_based" # Factor-based attribution
    HOLDINGS_BASED = "holdings_based"  # Holdings-based attribution
    RETURNS_BASED = "returns_based"   # Returns-based attribution


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    benchmark_value: Optional[float] = None
    percentile_rank: Optional[float] = None
    description: str = ""
    category: str = "general"


class StrategyAttribution(BaseModel):
    """Strategy performance attribution"""
    attribution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    period_start: datetime
    period_end: datetime
    
    # Return components
    total_return: float
    benchmark_return: float
    active_return: float
    
    # Attribution breakdown
    security_selection: float  # Alpha from stock picking
    asset_allocation: float    # Alpha from sector/asset allocation
    interaction_effect: float  # Interaction between selection and allocation
    timing_effect: float      # Market timing contribution
    
    # Risk metrics
    tracking_error: float
    information_ratio: float
    beta: float
    alpha: float
    
    # Detailed breakdowns
    sector_attribution: Dict[str, float] = Field(default_factory=dict)
    security_attribution: Dict[str, float] = Field(default_factory=dict)
    factor_attribution: Dict[str, float] = Field(default_factory=dict)
    
    # Confidence intervals
    alpha_confidence_interval: Tuple[float, float] = (0.0, 0.0)
    ir_confidence_interval: Tuple[float, float] = (0.0, 0.0)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PerformanceRegression(BaseModel):
    """Performance regression analysis"""
    regression_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    period_analyzed: str
    
    # Single factor model (CAPM)
    market_beta: float
    alpha: float
    r_squared: float
    
    # Multi-factor model (Fama-French, etc.)
    factor_loadings: Dict[str, float] = Field(default_factory=dict)
    factor_significance: Dict[str, float] = Field(default_factory=dict)
    
    # Statistical measures
    tracking_error: float
    information_ratio: float
    sharpe_ratio: float
    
    # Regression diagnostics
    durbin_watson: float
    jarque_bera: float
    heteroscedasticity_test: float
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StrategyComparison(BaseModel):
    """Strategy comparison analysis"""
    comparison_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_ids: List[str]
    period_start: datetime
    period_end: datetime
    
    # Performance rankings
    return_ranking: Dict[str, int] = Field(default_factory=dict)
    sharpe_ranking: Dict[str, int] = Field(default_factory=dict)
    drawdown_ranking: Dict[str, int] = Field(default_factory=dict)
    
    # Statistical comparisons
    return_correlation_matrix: List[List[float]] = Field(default_factory=list)
    performance_significance: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # Style analysis
    style_drift: Dict[str, float] = Field(default_factory=dict)
    strategy_uniqueness: Dict[str, float] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PerformanceAnalyzer:
    """Core performance analysis engine"""
    
    def __init__(self):
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        
    def calculate_performance_metrics(
        self, 
        returns: List[float],
        benchmark_returns: List[float] = None
    ) -> Dict[str, PerformanceMetric]:
        """Calculate comprehensive performance metrics"""
        if not returns:
            return {}
        
        returns_array = np.array(returns)
        metrics = {}
        
        # Basic return metrics
        total_return = np.prod(1 + returns_array) - 1
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        metrics["total_return"] = PerformanceMetric(
            name="Total Return",
            value=total_return,
            description="Cumulative return over the period",
            category="returns"
        )
        
        metrics["annualized_return"] = PerformanceMetric(
            name="Annualized Return",
            value=annualized_return,
            description="Annualized return",
            category="returns"
        )
        
        # Risk metrics
        volatility = np.std(returns_array) * np.sqrt(252)
        
        metrics["volatility"] = PerformanceMetric(
            name="Volatility",
            value=volatility,
            description="Annualized volatility",
            category="risk"
        )
        
        # Sharpe ratio
        sharpe_ratio = (annualized_return - self.risk_free_rate) / volatility if volatility > 0 else 0
        
        metrics["sharpe_ratio"] = PerformanceMetric(
            name="Sharpe Ratio",
            value=sharpe_ratio,
            description="Risk-adjusted return measure",
            category="risk_adjusted"
        )
        
        # Downside metrics
        negative_returns = returns_array[returns_array < 0]
        downside_deviation = np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 0 else 0
        
        sortino_ratio = (annualized_return - self.risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
        
        metrics["sortino_ratio"] = PerformanceMetric(
            name="Sortino Ratio",
            value=sortino_ratio,
            description="Downside risk-adjusted return",
            category="risk_adjusted"
        )
        
        # Drawdown analysis
        cumulative_returns = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        
        max_drawdown = np.min(drawdowns)
        current_drawdown = drawdowns[-1]
        
        metrics["max_drawdown"] = PerformanceMetric(
            name="Maximum Drawdown",
            value=abs(max_drawdown),
            description="Largest peak-to-trough decline",
            category="drawdown"
        )
        
        metrics["current_drawdown"] = PerformanceMetric(
            name="Current Drawdown",
            value=abs(current_drawdown),
            description="Current drawdown from peak",
            category="drawdown"
        )
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        metrics["calmar_ratio"] = PerformanceMetric(
            name="Calmar Ratio",
            value=calmar_ratio,
            description="Return to max drawdown ratio",
            category="risk_adjusted"
        )
        
        # Tail risk metrics
        var_95 = np.percentile(returns_array, 5)
        var_99 = np.percentile(returns_array, 1)
        
        metrics["var_95"] = PerformanceMetric(
            name="VaR 95%",
            value=abs(var_95),
            description="Value at Risk (95% confidence)",
            category="tail_risk"
        )
        
        metrics["var_99"] = PerformanceMetric(
            name="VaR 99%",
            value=abs(var_99),
            description="Value at Risk (99% confidence)",
            category="tail_risk"
        )
        
        # Expected shortfall
        tail_returns = returns_array[returns_array <= var_95]
        expected_shortfall = np.mean(tail_returns) if len(tail_returns) > 0 else 0
        
        metrics["expected_shortfall"] = PerformanceMetric(
            name="Expected Shortfall",
            value=abs(expected_shortfall),
            description="Average loss in worst 5% of cases",
            category="tail_risk"
        )
        
        # Benchmark comparison if provided
        if benchmark_returns:
            benchmark_array = np.array(benchmark_returns)
            
            # Tracking error
            active_returns = returns_array - benchmark_array
            tracking_error = np.std(active_returns) * np.sqrt(252)
            
            metrics["tracking_error"] = PerformanceMetric(
                name="Tracking Error",
                value=tracking_error,
                description="Volatility of active returns",
                category="relative"
            )
            
            # Information ratio
            active_return = np.mean(active_returns) * 252
            information_ratio = active_return / tracking_error if tracking_error > 0 else 0
            
            metrics["information_ratio"] = PerformanceMetric(
                name="Information Ratio",
                value=information_ratio,
                description="Active return per unit of tracking error",
                category="relative"
            )
            
            # Beta
            beta = np.cov(returns_array, benchmark_array)[0][1] / np.var(benchmark_array) if np.var(benchmark_array) > 0 else 1
            
            metrics["beta"] = PerformanceMetric(
                name="Beta",
                value=beta,
                description="Sensitivity to benchmark movements",
                category="relative"
            )
            
            # Alpha
            benchmark_return = np.mean(benchmark_array) * 252
            alpha = annualized_return - (self.risk_free_rate + beta * (benchmark_return - self.risk_free_rate))
            
            metrics["alpha"] = PerformanceMetric(
                name="Alpha",
                value=alpha,
                description="Risk-adjusted excess return",
                category="relative"
            )
        
        return metrics
    
    def perform_attribution_analysis(
        self,
        strategy_returns: List[float],
        benchmark_returns: List[float],
        sector_weights: Dict[str, List[float]],
        benchmark_weights: Dict[str, List[float]],
        sector_returns: Dict[str, List[float]]
    ) -> StrategyAttribution:
        """Perform Brinson-Hood-Beebower attribution analysis"""
        
        if not strategy_returns or not benchmark_returns:
            return StrategyAttribution(
                strategy_id="unknown",
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc),
                total_return=0.0,
                benchmark_return=0.0,
                active_return=0.0,
                security_selection=0.0,
                asset_allocation=0.0,
                interaction_effect=0.0,
                timing_effect=0.0,
                tracking_error=0.0,
                information_ratio=0.0,
                beta=1.0,
                alpha=0.0
            )
        
        # Calculate portfolio and benchmark returns
        portfolio_return = np.prod(1 + np.array(strategy_returns)) - 1
        benchmark_return = np.prod(1 + np.array(benchmark_returns)) - 1
        active_return = portfolio_return - benchmark_return
        
        # Attribution calculations (simplified Brinson model)
        sector_attribution = {}
        total_allocation_effect = 0.0
        total_selection_effect = 0.0
        total_interaction_effect = 0.0
        
        for sector in sector_weights.keys():
            if sector in benchmark_weights and sector in sector_returns:
                # Average weights over period
                avg_portfolio_weight = np.mean(sector_weights[sector])
                avg_benchmark_weight = np.mean(benchmark_weights[sector])
                
                # Sector returns
                sector_return = np.prod(1 + np.array(sector_returns[sector])) - 1
                
                # Allocation effect: (wp - wb) * (rb - r_bench)
                allocation_effect = (avg_portfolio_weight - avg_benchmark_weight) * (sector_return - benchmark_return)
                
                # Selection effect: wb * (rp - rb)  
                # Simplified: assume sector return represents selection
                selection_effect = avg_benchmark_weight * (sector_return - benchmark_return) * 0.1  # Simplified
                
                # Interaction effect: (wp - wb) * (rp - rb)
                interaction_effect = (avg_portfolio_weight - avg_benchmark_weight) * (sector_return - benchmark_return) * 0.05
                
                sector_attribution[sector] = {
                    "allocation": allocation_effect,
                    "selection": selection_effect,
                    "interaction": interaction_effect
                }
                
                total_allocation_effect += allocation_effect
                total_selection_effect += selection_effect
                total_interaction_effect += interaction_effect
        
        # Risk metrics
        returns_array = np.array(strategy_returns)
        benchmark_array = np.array(benchmark_returns)
        active_returns = returns_array - benchmark_array
        
        tracking_error = np.std(active_returns) * np.sqrt(252)
        information_ratio = (np.mean(active_returns) * 252) / tracking_error if tracking_error > 0 else 0
        
        # Beta and Alpha
        beta = np.cov(returns_array, benchmark_array)[0][1] / np.var(benchmark_array) if np.var(benchmark_array) > 0 else 1
        alpha = (np.mean(returns_array) * 252) - (self.risk_free_rate + beta * (np.mean(benchmark_array) * 252 - self.risk_free_rate))
        
        return StrategyAttribution(
            strategy_id="analyzed_strategy",
            period_start=datetime.now(timezone.utc) - timedelta(days=252),
            period_end=datetime.now(timezone.utc),
            total_return=portfolio_return,
            benchmark_return=benchmark_return,
            active_return=active_return,
            security_selection=total_selection_effect,
            asset_allocation=total_allocation_effect,
            interaction_effect=total_interaction_effect,
            timing_effect=0.0,  # Would require more complex analysis
            tracking_error=tracking_error,
            information_ratio=information_ratio,
            beta=beta,
            alpha=alpha,
            sector_attribution=sector_attribution
        )
    
    def perform_regression_analysis(
        self,
        strategy_returns: List[float],
        market_returns: List[float],
        factor_returns: Dict[str, List[float]] = None
    ) -> PerformanceRegression:
        """Perform regression analysis (CAPM and multi-factor)"""
        
        if not strategy_returns or not market_returns:
            return PerformanceRegression(
                strategy_id="unknown",
                period_analyzed="unknown",
                market_beta=1.0,
                alpha=0.0,
                r_squared=0.0,
                tracking_error=0.0,
                information_ratio=0.0,
                sharpe_ratio=0.0,
                durbin_watson=2.0,
                jarque_bera=0.0,
                heteroscedasticity_test=0.0
            )
        
        returns_array = np.array(strategy_returns)
        market_array = np.array(market_returns)
        
        # CAPM regression: R_p - R_f = alpha + beta * (R_m - R_f) + epsilon
        excess_returns = returns_array - self.risk_free_rate / 252
        market_excess = market_array - self.risk_free_rate / 252
        
        # Simple linear regression
        beta, alpha_intercept = np.polyfit(market_excess, excess_returns, 1)
        
        # Calculate R-squared
        predicted_returns = alpha_intercept + beta * market_excess
        ss_res = np.sum((excess_returns - predicted_returns) ** 2)
        ss_tot = np.sum((excess_returns - np.mean(excess_returns)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Risk metrics
        tracking_error = np.std(returns_array - market_array) * np.sqrt(252)
        active_return = (np.mean(returns_array) - np.mean(market_array)) * 252
        information_ratio = active_return / tracking_error if tracking_error > 0 else 0
        
        volatility = np.std(returns_array) * np.sqrt(252)
        sharpe_ratio = (np.mean(returns_array) * 252 - self.risk_free_rate) / volatility if volatility > 0 else 0
        
        # Multi-factor analysis if factor data provided
        factor_loadings = {}
        factor_significance = {}
        
        if factor_returns:
            # Prepare factor matrix
            factors = []
            factor_names = []
            
            for factor_name, factor_data in factor_returns.items():
                if len(factor_data) == len(returns_array):
                    factors.append(factor_data)
                    factor_names.append(factor_name)
            
            if factors:
                X = np.column_stack([market_excess] + factors)
                
                # Multiple regression (simplified)
                try:
                    coefficients = np.linalg.lstsq(X, excess_returns, rcond=None)[0]
                    
                    factor_loadings["market"] = float(coefficients[0])
                    for i, factor_name in enumerate(factor_names):
                        factor_loadings[factor_name] = float(coefficients[i + 1])
                        # Simplified significance test
                        factor_significance[factor_name] = abs(coefficients[i + 1]) / (np.std(factors[i]) + 1e-8)
                        
                except np.linalg.LinAlgError:
                    factor_loadings["market"] = beta
        
        return PerformanceRegression(
            strategy_id="analyzed_strategy",
            period_analyzed="full_period",
            market_beta=beta,
            alpha=alpha_intercept * 252,  # Annualize alpha
            r_squared=r_squared,
            factor_loadings=factor_loadings,
            factor_significance=factor_significance,
            tracking_error=tracking_error,
            information_ratio=information_ratio,
            sharpe_ratio=sharpe_ratio,
            durbin_watson=2.0,  # Placeholder - would calculate actual DW statistic
            jarque_bera=0.0,    # Placeholder - would perform actual normality test
            heteroscedasticity_test=0.0  # Placeholder - would perform actual heteroscedasticity test
        )


class PerformanceReporter:
    """Performance reporting and visualization"""
    
    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        
    def generate_performance_report(
        self,
        strategy_id: str,
        metrics: Dict[str, PerformanceMetric],
        attribution: StrategyAttribution,
        regression: PerformanceRegression,
        period: PerformancePeriod = PerformancePeriod.MONTHLY
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        report = {
            "strategy_id": strategy_id,
            "report_date": datetime.now(timezone.utc).isoformat(),
            "period": period.value,
            "executive_summary": self._generate_executive_summary(metrics, attribution),
            "performance_metrics": self._format_metrics_for_report(metrics),
            "attribution_analysis": self._format_attribution_for_report(attribution),
            "regression_analysis": self._format_regression_for_report(regression),
            "risk_analysis": self._generate_risk_analysis(metrics),
            "recommendations": self._generate_recommendations(metrics, attribution, regression)
        }
        
        return report
    
    def _generate_executive_summary(
        self,
        metrics: Dict[str, PerformanceMetric],
        attribution: StrategyAttribution
    ) -> Dict[str, Any]:
        """Generate executive summary"""
        
        total_return = metrics.get("total_return", PerformanceMetric("", 0.0)).value
        sharpe_ratio = metrics.get("sharpe_ratio", PerformanceMetric("", 0.0)).value
        max_drawdown = metrics.get("max_drawdown", PerformanceMetric("", 0.0)).value
        
        performance_rating = "Excellent" if sharpe_ratio > 1.5 else \
                           "Good" if sharpe_ratio > 1.0 else \
                           "Fair" if sharpe_ratio > 0.5 else "Poor"
        
        risk_rating = "Low" if max_drawdown < 0.05 else \
                     "Medium" if max_drawdown < 0.15 else \
                     "High" if max_drawdown < 0.25 else "Very High"
        
        key_insights = []
        
        if attribution.alpha > 0.05:
            key_insights.append("Strong alpha generation indicating skilled management")
        elif attribution.alpha < -0.05:
            key_insights.append("Negative alpha suggests underperformance vs. risk-adjusted benchmark")
        
        if abs(attribution.asset_allocation) > abs(attribution.security_selection):
            key_insights.append("Performance primarily driven by asset allocation decisions")
        else:
            key_insights.append("Performance primarily driven by security selection")
        
        if attribution.information_ratio > 0.5:
            key_insights.append("High information ratio indicates efficient use of active risk")
        
        return {
            "total_return": f"{total_return:.2%}",
            "performance_rating": performance_rating,
            "risk_rating": risk_rating,
            "alpha": f"{attribution.alpha:.2%}",
            "information_ratio": f"{attribution.information_ratio:.2f}",
            "key_insights": key_insights
        }
    
    def _format_metrics_for_report(self, metrics: Dict[str, PerformanceMetric]) -> Dict[str, Any]:
        """Format metrics for report display"""
        formatted = {}
        
        categories = defaultdict(list)
        for metric in metrics.values():
            categories[metric.category].append({
                "name": metric.name,
                "value": f"{metric.value:.4f}",
                "description": metric.description
            })
        
        return dict(categories)
    
    def _format_attribution_for_report(self, attribution: StrategyAttribution) -> Dict[str, Any]:
        """Format attribution analysis for report"""
        return {
            "total_active_return": f"{attribution.active_return:.2%}",
            "components": {
                "asset_allocation": f"{attribution.asset_allocation:.2%}",
                "security_selection": f"{attribution.security_selection:.2%}",
                "interaction_effect": f"{attribution.interaction_effect:.2%}",
                "timing_effect": f"{attribution.timing_effect:.2%}"
            },
            "sector_breakdown": {
                sector: {
                    "allocation": f"{data['allocation']:.2%}",
                    "selection": f"{data['selection']:.2%}",
                    "interaction": f"{data['interaction']:.2%}"
                }
                for sector, data in attribution.sector_attribution.items()
            }
        }
    
    def _format_regression_for_report(self, regression: PerformanceRegression) -> Dict[str, Any]:
        """Format regression analysis for report"""
        return {
            "market_beta": f"{regression.market_beta:.3f}",
            "alpha": f"{regression.alpha:.2%}",
            "r_squared": f"{regression.r_squared:.3f}",
            "tracking_error": f"{regression.tracking_error:.2%}",
            "information_ratio": f"{regression.information_ratio:.2f}",
            "factor_exposures": {
                factor: f"{loading:.3f}"
                for factor, loading in regression.factor_loadings.items()
            }
        }
    
    def _generate_risk_analysis(self, metrics: Dict[str, PerformanceMetric]) -> Dict[str, Any]:
        """Generate risk analysis section"""
        volatility = metrics.get("volatility", PerformanceMetric("", 0.0)).value
        max_drawdown = metrics.get("max_drawdown", PerformanceMetric("", 0.0)).value
        var_95 = metrics.get("var_95", PerformanceMetric("", 0.0)).value
        
        risk_level = "Conservative" if volatility < 0.1 else \
                    "Moderate" if volatility < 0.2 else \
                    "Aggressive" if volatility < 0.3 else "Very Aggressive"
        
        return {
            "risk_profile": risk_level,
            "volatility": f"{volatility:.2%}",
            "max_drawdown": f"{max_drawdown:.2%}",
            "value_at_risk": f"{var_95:.2%}",
            "risk_commentary": self._generate_risk_commentary(volatility, max_drawdown, var_95)
        }
    
    def _generate_risk_commentary(self, volatility: float, max_drawdown: float, var_95: float) -> List[str]:
        """Generate risk commentary"""
        commentary = []
        
        if volatility > 0.25:
            commentary.append("High volatility suggests significant price fluctuations")
        elif volatility < 0.1:
            commentary.append("Low volatility indicates stable returns")
        
        if max_drawdown > 0.2:
            commentary.append("Large maximum drawdown indicates potential for significant losses")
        elif max_drawdown < 0.05:
            commentary.append("Small maximum drawdown suggests good downside protection")
        
        if var_95 > 0.05:
            commentary.append("High VaR indicates potential for large daily losses")
        
        return commentary
    
    def _generate_recommendations(
        self,
        metrics: Dict[str, PerformanceMetric],
        attribution: StrategyAttribution,
        regression: PerformanceRegression
    ) -> List[str]:
        """Generate strategy recommendations"""
        recommendations = []
        
        # Performance-based recommendations
        if attribution.alpha < 0:
            recommendations.append("Consider reviewing investment process as alpha is negative")
        
        if attribution.information_ratio < 0.3:
            recommendations.append("Low information ratio suggests inefficient use of active risk")
        
        if abs(attribution.asset_allocation) > 0.05:
            recommendations.append("Asset allocation is a significant driver - consider tactical allocation models")
        
        # Risk-based recommendations
        max_drawdown = metrics.get("max_drawdown", PerformanceMetric("", 0.0)).value
        if max_drawdown > 0.15:
            recommendations.append("Consider implementing better risk management to reduce drawdowns")
        
        volatility = metrics.get("volatility", PerformanceMetric("", 0.0)).value
        if volatility > 0.25:
            recommendations.append("High volatility - consider position sizing adjustments")
        
        # Beta-based recommendations
        if abs(regression.market_beta - 1.0) > 0.3:
            if regression.market_beta > 1.3:
                recommendations.append("High beta strategy - consider defensive hedges in volatile markets")
            elif regression.market_beta < 0.7:
                recommendations.append("Low beta strategy - may underperform in strong bull markets")
        
        return recommendations


class PerformanceAnalyticsService:
    """
    Performance attribution and strategy analytics service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
        # Analysis components
        self.analyzer = PerformanceAnalyzer()
        self.reporter = PerformanceReporter()
        
        # Performance data cache
        self.strategy_metrics: Dict[str, Dict[str, PerformanceMetric]] = {}
        self.attribution_cache: Dict[str, StrategyAttribution] = {}
        self.regression_cache: Dict[str, PerformanceRegression] = {}
        
        # Historical data
        self.performance_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.benchmark_data: Dict[str, List[float]] = {}
        
        # Configuration
        self.analysis_interval = 3600       # 1 hour
        self.report_generation_interval = 86400  # 24 hours
        self.data_retention_days = 365
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the performance analytics service"""
        try:
            logger.info("Initializing Performance Analytics Service...")
            
            # Load historical performance data
            await self._load_historical_data()
            
            # Load benchmark data
            await self._load_benchmark_data()
            
            # Start background tasks
            asyncio.create_task(self._performance_analysis_loop())
            asyncio.create_task(self._report_generation_loop())
            asyncio.create_task(self._data_cleanup_loop())
            
            logger.info("Performance Analytics Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Performance Analytics Service: {e}")
            raise
    
    async def analyze_strategy_performance(
        self,
        strategy_id: str,
        period: PerformancePeriod = PerformancePeriod.MONTHLY,
        benchmark_symbol: str = "SPY"
    ) -> Dict[str, Any]:
        """Perform comprehensive strategy performance analysis"""
        try:
            logger.info(f"Analyzing performance for strategy {strategy_id}")
            
            # Get strategy performance data
            portfolio_service = await get_portfolio_management_service()
            backtesting_service = await get_backtesting_service()
            
            # Get historical returns
            strategy_returns = await self._get_strategy_returns(strategy_id, period)
            benchmark_returns = self.benchmark_data.get(benchmark_symbol, [])
            
            if not strategy_returns:
                return {"error": "No performance data available for strategy"}
            
            # Calculate performance metrics
            metrics = self.analyzer.calculate_performance_metrics(
                strategy_returns, benchmark_returns[:len(strategy_returns)]
            )
            
            # Perform attribution analysis
            attribution = await self._perform_strategy_attribution(
                strategy_id, strategy_returns, benchmark_returns, period
            )
            
            # Perform regression analysis
            regression = self.analyzer.perform_regression_analysis(
                strategy_returns, benchmark_returns[:len(strategy_returns)]
            )
            
            # Cache results
            self.strategy_metrics[strategy_id] = metrics
            self.attribution_cache[strategy_id] = attribution
            self.regression_cache[strategy_id] = regression
            
            # Generate comprehensive report
            report = self.reporter.generate_performance_report(
                strategy_id, metrics, attribution, regression, period
            )
            
            # Save analysis to database
            await self._save_performance_analysis(strategy_id, report)
            
            logger.info(f"Performance analysis completed for strategy {strategy_id}")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to analyze strategy performance for {strategy_id}: {e}")
            return {"error": str(e)}
    
    async def compare_strategies(
        self,
        strategy_ids: List[str],
        period: PerformancePeriod = PerformancePeriod.MONTHLY
    ) -> StrategyComparison:
        """Compare multiple strategies"""
        try:
            logger.info(f"Comparing {len(strategy_ids)} strategies")
            
            # Get returns for all strategies
            strategy_returns = {}
            for strategy_id in strategy_ids:
                returns = await self._get_strategy_returns(strategy_id, period)
                if returns:
                    strategy_returns[strategy_id] = returns
            
            if len(strategy_returns) < 2:
                raise HTTPException(status_code=400, detail="Need at least 2 strategies with data")
            
            # Calculate performance metrics for comparison
            strategy_metrics = {}
            for strategy_id, returns in strategy_returns.items():
                metrics = self.analyzer.calculate_performance_metrics(returns)
                strategy_metrics[strategy_id] = metrics
            
            # Performance rankings
            return_ranking = {}
            sharpe_ranking = {}
            drawdown_ranking = {}
            
            # Sort by total return
            sorted_by_return = sorted(
                strategy_metrics.items(),
                key=lambda x: x[1].get("total_return", PerformanceMetric("", 0.0)).value,
                reverse=True
            )
            for i, (strategy_id, _) in enumerate(sorted_by_return):
                return_ranking[strategy_id] = i + 1
            
            # Sort by Sharpe ratio
            sorted_by_sharpe = sorted(
                strategy_metrics.items(),
                key=lambda x: x[1].get("sharpe_ratio", PerformanceMetric("", 0.0)).value,
                reverse=True
            )
            for i, (strategy_id, _) in enumerate(sorted_by_sharpe):
                sharpe_ranking[strategy_id] = i + 1
            
            # Sort by drawdown (ascending - lower is better)
            sorted_by_drawdown = sorted(
                strategy_metrics.items(),
                key=lambda x: x[1].get("max_drawdown", PerformanceMetric("", 1.0)).value
            )
            for i, (strategy_id, _) in enumerate(sorted_by_drawdown):
                drawdown_ranking[strategy_id] = i + 1
            
            # Calculate correlation matrix
            returns_matrix = []
            strategy_list = list(strategy_returns.keys())
            min_length = min(len(returns) for returns in strategy_returns.values())
            
            for strategy_id in strategy_list:
                returns_matrix.append(strategy_returns[strategy_id][:min_length])
            
            correlation_matrix = np.corrcoef(returns_matrix).tolist()
            
            # Statistical significance testing (simplified)
            performance_significance = {}
            for i, strategy_a in enumerate(strategy_list):
                performance_significance[strategy_a] = {}
                for j, strategy_b in enumerate(strategy_list):
                    if i != j:
                        # T-test for difference in means
                        returns_a = strategy_returns[strategy_a][:min_length]
                        returns_b = strategy_returns[strategy_b][:min_length]
                        
                        if len(returns_a) > 1 and len(returns_b) > 1:
                            t_stat, p_value = stats.ttest_ind(returns_a, returns_b)
                            performance_significance[strategy_a][strategy_b] = p_value
                        else:
                            performance_significance[strategy_a][strategy_b] = 1.0
            
            comparison = StrategyComparison(
                strategy_ids=strategy_ids,
                period_start=datetime.now(timezone.utc) - timedelta(days=30 * period.value.count("month")),
                period_end=datetime.now(timezone.utc),
                return_ranking=return_ranking,
                sharpe_ranking=sharpe_ranking,
                drawdown_ranking=drawdown_ranking,
                return_correlation_matrix=correlation_matrix,
                performance_significance=performance_significance
            )
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to compare strategies: {e}")
            raise HTTPException(status_code=500, detail=f"Strategy comparison failed: {str(e)}")
    
    async def get_strategy_analytics_dashboard(self, strategy_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics dashboard for strategy"""
        try:
            # Get cached metrics
            metrics = self.strategy_metrics.get(strategy_id, {})
            attribution = self.attribution_cache.get(strategy_id)
            regression = self.regression_cache.get(strategy_id)
            
            if not metrics:
                # Generate fresh analysis
                analysis = await self.analyze_strategy_performance(strategy_id)
                if "error" in analysis:
                    return analysis
            
            # Recent performance history
            recent_history = self.performance_history[strategy_id][-30:]  # Last 30 data points
            
            # Key performance indicators
            kpis = {}
            if metrics:
                kpis = {
                    "total_return": metrics.get("total_return", PerformanceMetric("", 0.0)).value,
                    "sharpe_ratio": metrics.get("sharpe_ratio", PerformanceMetric("", 0.0)).value,
                    "max_drawdown": metrics.get("max_drawdown", PerformanceMetric("", 0.0)).value,
                    "volatility": metrics.get("volatility", PerformanceMetric("", 0.0)).value,
                    "alpha": attribution.alpha if attribution else 0.0,
                    "beta": regression.market_beta if regression else 1.0,
                    "information_ratio": attribution.information_ratio if attribution else 0.0
                }
            
            # Performance trends
            trends = self._calculate_performance_trends(recent_history)
            
            # Risk breakdown
            risk_breakdown = self._calculate_risk_breakdown(metrics)
            
            return {
                "strategy_id": strategy_id,
                "dashboard_timestamp": datetime.now(timezone.utc).isoformat(),
                "key_performance_indicators": kpis,
                "performance_trends": trends,
                "risk_breakdown": risk_breakdown,
                "recent_performance": recent_history,
                "attribution_summary": {
                    "alpha": attribution.alpha if attribution else 0.0,
                    "asset_allocation_effect": attribution.asset_allocation if attribution else 0.0,
                    "security_selection_effect": attribution.security_selection if attribution else 0.0,
                    "total_active_return": attribution.active_return if attribution else 0.0
                },
                "regression_summary": {
                    "market_beta": regression.market_beta if regression else 1.0,
                    "r_squared": regression.r_squared if regression else 0.0,
                    "tracking_error": regression.tracking_error if regression else 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get analytics dashboard for strategy {strategy_id}: {e}")
            return {"error": str(e)}
    
    # Background service loops
    
    async def _performance_analysis_loop(self):
        """Background performance analysis loop"""
        while not self._shutdown:
            try:
                # Get list of active strategies
                portfolio_service = await get_portfolio_management_service()
                
                # Analyze performance for each strategy
                for portfolio_id in list(portfolio_service.portfolios.keys())[:5]:  # Limit to avoid overload
                    try:
                        await self.analyze_strategy_performance(portfolio_id)
                    except Exception as e:
                        logger.error(f"Error analyzing strategy {portfolio_id}: {e}")
                
                await asyncio.sleep(self.analysis_interval)
                
            except Exception as e:
                logger.error(f"Error in performance analysis loop: {e}")
                await asyncio.sleep(self.analysis_interval)
    
    async def _report_generation_loop(self):
        """Background report generation loop"""
        while not self._shutdown:
            try:
                # Generate daily reports for all strategies
                for strategy_id in list(self.strategy_metrics.keys()):
                    await self._generate_daily_report(strategy_id)
                
                await asyncio.sleep(self.report_generation_interval)
                
            except Exception as e:
                logger.error(f"Error in report generation loop: {e}")
                await asyncio.sleep(self.report_generation_interval)
    
    async def _data_cleanup_loop(self):
        """Background data cleanup loop"""
        while not self._shutdown:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.data_retention_days)
                
                # Clean up old performance history
                for strategy_id in list(self.performance_history.keys()):
                    self.performance_history[strategy_id] = [
                        entry for entry in self.performance_history[strategy_id]
                        if datetime.fromisoformat(entry.get("timestamp", "1970-01-01T00:00:00+00:00").replace("Z", "+00:00")) > cutoff_date
                    ]
                
                await asyncio.sleep(86400)  # Daily cleanup
                
            except Exception as e:
                logger.error(f"Error in data cleanup loop: {e}")
                await asyncio.sleep(86400)
    
    # Helper methods
    
    async def _get_strategy_returns(self, strategy_id: str, period: PerformancePeriod) -> List[float]:
        """Get historical returns for strategy"""
        # Simplified implementation - would fetch actual data from database
        # Generate sample returns for demonstration
        np.random.seed(hash(strategy_id) % 2**32)
        
        if period == PerformancePeriod.DAILY:
            num_periods = 30
        elif period == PerformancePeriod.WEEKLY:
            num_periods = 52
        elif period == PerformancePeriod.MONTHLY:
            num_periods = 12
        else:
            num_periods = 252  # Daily for a year
        
        # Generate realistic returns
        returns = np.random.normal(0.0008, 0.02, num_periods)  # 0.08% daily mean, 2% volatility
        return returns.tolist()
    
    # Additional helper methods would be implemented here...


# Global service instance
_performance_analytics_service: Optional[PerformanceAnalyticsService] = None


async def get_performance_analytics_service() -> PerformanceAnalyticsService:
    """Get the global performance analytics service instance"""
    global _performance_analytics_service
    
    if _performance_analytics_service is None:
        _performance_analytics_service = PerformanceAnalyticsService()
        await _performance_analytics_service.initialize()
    
    return _performance_analytics_service


@asynccontextmanager
async def performance_analytics_context():
    """Context manager for performance analytics service"""
    service = await get_performance_analytics_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass