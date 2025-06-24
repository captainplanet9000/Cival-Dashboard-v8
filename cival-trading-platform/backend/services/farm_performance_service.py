"""
Farm Performance Service - Phase 7
Advanced performance monitoring and analytics for multi-agent farms
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import statistics

logger = logging.getLogger(__name__)

class PerformanceMetric(str, Enum):
    """Performance metric types"""
    ROI = "roi"
    SHARPE_RATIO = "sharpe_ratio"
    VOLATILITY = "volatility"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    TRADE_FREQUENCY = "trade_frequency"
    CAPITAL_EFFICIENCY = "capital_efficiency"

class PerformancePeriod(str, Enum):
    """Performance analysis periods"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class BenchmarkType(str, Enum):
    """Benchmark comparison types"""
    MARKET_INDEX = "market_index"
    PEER_FARMS = "peer_farms"
    HISTORICAL_SELF = "historical_self"
    TARGET_PERFORMANCE = "target_performance"
    RISK_FREE_RATE = "risk_free_rate"

class FarmPerformanceService:
    """
    Advanced Farm Performance Service
    Comprehensive performance monitoring, analytics, and benchmarking for farm operations
    """
    
    def __init__(self):
        self.performance_data: Dict[str, Any] = {}
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.benchmarks: Dict[str, Any] = {}
        self.performance_alerts: Dict[str, List[Dict[str, Any]]] = {}
        self.analytics_cache: Dict[str, Any] = {}
        
        # Performance monitoring settings
        self.monitoring_interval = 300  # 5 minutes
        self.alert_thresholds = {
            "roi_decline": Decimal('-5'),      # 5% decline
            "drawdown_limit": Decimal('15'),   # 15% max drawdown
            "volatility_spike": Decimal('25'), # 25% volatility increase
            "win_rate_drop": Decimal('40'),    # Below 40% win rate
            "capital_efficiency": Decimal('70') # Below 70% efficiency
        }
        
        # Analytics settings
        self.cache_duration = 300  # 5 minutes
        self.historical_periods = {
            "short_term": timedelta(days=7),
            "medium_term": timedelta(days=30),
            "long_term": timedelta(days=90)
        }
        
        logger.info("=Ê Farm Performance Service initialized")
    
    async def initialize(self):
        """Initialize the performance monitoring service"""
        # Start background monitoring tasks
        asyncio.create_task(self._performance_monitoring_loop())
        asyncio.create_task(self._performance_analytics_loop())
        asyncio.create_task(self._alert_monitoring_loop())
        
        # Initialize benchmark data
        await self._initialize_benchmarks()
        
        logger.info(" Farm Performance Service ready")
    
    async def track_farm_performance(self, farm_id: str, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track and record farm performance data"""
        try:
            timestamp = datetime.utcnow()
            
            # Create performance snapshot
            performance_snapshot = {
                "farm_id": farm_id,
                "timestamp": timestamp,
                "period": performance_data.get("period", PerformancePeriod.DAILY),
                
                # Core performance metrics
                "total_pnl": Decimal(str(performance_data.get("total_pnl", 0))),
                "realized_pnl": Decimal(str(performance_data.get("realized_pnl", 0))),
                "unrealized_pnl": Decimal(str(performance_data.get("unrealized_pnl", 0))),
                "roi": Decimal(str(performance_data.get("roi", 0))),
                "capital_deployed": Decimal(str(performance_data.get("capital_deployed", 0))),
                "capital_available": Decimal(str(performance_data.get("capital_available", 0))),
                
                # Risk metrics
                "volatility": Decimal(str(performance_data.get("volatility", 0))),
                "sharpe_ratio": Decimal(str(performance_data.get("sharpe_ratio", 0))),
                "max_drawdown": Decimal(str(performance_data.get("max_drawdown", 0))),
                "current_drawdown": Decimal(str(performance_data.get("current_drawdown", 0))),
                "var_95": Decimal(str(performance_data.get("var_95", 0))),
                
                # Trading metrics
                "total_trades": performance_data.get("total_trades", 0),
                "winning_trades": performance_data.get("winning_trades", 0),
                "losing_trades": performance_data.get("losing_trades", 0),
                "win_rate": Decimal(str(performance_data.get("win_rate", 0))),
                "avg_win": Decimal(str(performance_data.get("avg_win", 0))),
                "avg_loss": Decimal(str(performance_data.get("avg_loss", 0))),
                "profit_factor": Decimal(str(performance_data.get("profit_factor", 0))),
                
                # Efficiency metrics
                "capital_efficiency": Decimal(str(performance_data.get("capital_efficiency", 0))),
                "trade_frequency": Decimal(str(performance_data.get("trade_frequency", 0))),
                "cost_efficiency": Decimal(str(performance_data.get("cost_efficiency", 0))),
                
                # Agent-level breakdown
                "agent_performance": performance_data.get("agent_performance", {}),
                "strategy_performance": performance_data.get("strategy_performance", {}),
                
                # Market context
                "market_conditions": performance_data.get("market_conditions", {}),
                "external_factors": performance_data.get("external_factors", {})
            }
            
            # Store current performance data
            self.performance_data[farm_id] = performance_snapshot
            
            # Add to historical data
            if farm_id not in self.performance_history:
                self.performance_history[farm_id] = []
            self.performance_history[farm_id].append(performance_snapshot)
            
            # Limit historical data (keep last 1000 snapshots)
            if len(self.performance_history[farm_id]) > 1000:
                self.performance_history[farm_id] = self.performance_history[farm_id][-1000:]
            
            # Check for performance alerts
            await self._check_performance_alerts(farm_id, performance_snapshot)
            
            # Update analytics cache
            await self._update_performance_analytics(farm_id)
            
            logger.info(f"=Ê Tracked performance for farm {farm_id}: ROI {performance_snapshot['roi']}%, Trades {performance_snapshot['total_trades']}")
            
            return {
                "farm_id": farm_id,
                "snapshot_recorded": True,
                "timestamp": timestamp,
                "alerts_triggered": len(self.performance_alerts.get(farm_id, [])),
                "performance_summary": {
                    "roi": performance_snapshot["roi"],
                    "total_pnl": performance_snapshot["total_pnl"],
                    "win_rate": performance_snapshot["win_rate"],
                    "max_drawdown": performance_snapshot["max_drawdown"]
                }
            }
            
        except Exception as e:
            logger.error(f"L Failed to track farm performance: {e}")
            raise
    
    async def analyze_farm_performance(self, farm_id: str, analysis_config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive performance analysis"""
        try:
            if farm_id not in self.performance_history:
                raise ValueError(f"No performance history found for farm {farm_id}")
            
            analysis_period = analysis_config.get("period", PerformancePeriod.MONTHLY)
            include_benchmarks = analysis_config.get("include_benchmarks", True)
            include_attribution = analysis_config.get("include_attribution", True)
            include_predictions = analysis_config.get("include_predictions", False)
            
            analysis_id = f"analysis_{uuid.uuid4().hex[:8]}"
            
            # Get performance data for analysis period
            performance_data = await self._get_performance_data_for_period(farm_id, analysis_period)
            
            if not performance_data:
                raise ValueError(f"No performance data available for period {analysis_period}")
            
            # Core performance analysis
            core_analysis = await self._perform_core_performance_analysis(farm_id, performance_data)
            
            # Risk analysis
            risk_analysis = await self._perform_risk_analysis(farm_id, performance_data)
            
            # Trend analysis
            trend_analysis = await self._perform_trend_analysis(farm_id, performance_data)
            
            # Agent performance analysis
            agent_analysis = await self._perform_agent_performance_analysis(farm_id, performance_data)
            
            # Strategy performance analysis
            strategy_analysis = await self._perform_strategy_performance_analysis(farm_id, performance_data)
            
            analysis_result = {
                "analysis_id": analysis_id,
                "farm_id": farm_id,
                "analysis_period": analysis_period,
                "data_points": len(performance_data),
                "analysis_timestamp": datetime.utcnow(),
                
                # Core analysis results
                "core_performance": core_analysis,
                "risk_metrics": risk_analysis,
                "trend_analysis": trend_analysis,
                "agent_performance": agent_analysis,
                "strategy_performance": strategy_analysis,
                
                # Summary insights
                "key_insights": await self._generate_performance_insights(farm_id, core_analysis, risk_analysis, trend_analysis),
                "performance_score": await self._calculate_overall_performance_score(core_analysis, risk_analysis),
                "recommendations": await self._generate_performance_recommendations(farm_id, core_analysis, risk_analysis)
            }
            
            # Add benchmark comparison if requested
            if include_benchmarks:
                benchmark_analysis = await self._perform_benchmark_comparison(farm_id, performance_data)
                analysis_result["benchmark_comparison"] = benchmark_analysis
            
            # Add performance attribution if requested
            if include_attribution:
                attribution_analysis = await self._perform_performance_attribution(farm_id, performance_data)
                analysis_result["performance_attribution"] = attribution_analysis
            
            # Add performance predictions if requested
            if include_predictions:
                prediction_analysis = await self._perform_performance_prediction(farm_id, performance_data)
                analysis_result["performance_predictions"] = prediction_analysis
            
            logger.info(f"=È Completed performance analysis {analysis_id} for farm {farm_id}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"L Failed to analyze farm performance: {e}")
            raise
    
    async def compare_farm_performance(
        self, 
        farm_ids: List[str], 
        comparison_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare performance across multiple farms"""
        try:
            comparison_id = f"comparison_{uuid.uuid4().hex[:8]}"
            comparison_period = comparison_config.get("period", PerformancePeriod.MONTHLY)
            metrics = comparison_config.get("metrics", [metric.value for metric in PerformanceMetric])
            
            # Validate farms
            available_farms = [farm_id for farm_id in farm_ids if farm_id in self.performance_history]
            if len(available_farms) < 2:
                raise ValueError("At least 2 farms with performance history required for comparison")
            
            comparison_result = {
                "comparison_id": comparison_id,
                "farms_compared": available_farms,
                "comparison_period": comparison_period,
                "metrics_compared": metrics,
                "comparison_timestamp": datetime.utcnow(),
                
                # Individual farm summaries
                "farm_summaries": {},
                
                # Comparative analysis
                "metric_rankings": {},
                "performance_leaders": {},
                "performance_correlations": {},
                "efficiency_comparison": {},
                
                # Insights
                "key_differences": [],
                "best_practices": [],
                "improvement_opportunities": {}
            }
            
            # Get performance data for each farm
            farm_performance_data = {}
            for farm_id in available_farms:
                farm_data = await self._get_performance_data_for_period(farm_id, comparison_period)
                if farm_data:
                    farm_performance_data[farm_id] = farm_data
                    
                    # Generate farm summary
                    summary = await self._generate_farm_performance_summary(farm_id, farm_data)
                    comparison_result["farm_summaries"][farm_id] = summary
            
            # Perform comparative analysis
            if len(farm_performance_data) >= 2:
                # Rank farms by each metric
                for metric in metrics:
                    ranking = await self._rank_farms_by_metric(farm_performance_data, metric)
                    comparison_result["metric_rankings"][metric] = ranking
                
                # Identify performance leaders
                comparison_result["performance_leaders"] = await self._identify_performance_leaders(farm_performance_data)
                
                # Calculate correlations
                comparison_result["performance_correlations"] = await self._calculate_performance_correlations(farm_performance_data)
                
                # Efficiency comparison
                comparison_result["efficiency_comparison"] = await self._compare_farm_efficiency(farm_performance_data)
                
                # Generate insights
                comparison_result["key_differences"] = await self._identify_key_performance_differences(farm_performance_data)
                comparison_result["best_practices"] = await self._identify_best_practices(farm_performance_data)
                comparison_result["improvement_opportunities"] = await self._identify_improvement_opportunities(farm_performance_data)
            
            logger.info(f"<Æ Completed farm comparison {comparison_id} for {len(available_farms)} farms")
            return comparison_result
            
        except Exception as e:
            logger.error(f"L Failed to compare farm performance: {e}")
            raise
    
    async def get_performance_alerts(self, farm_id: str) -> List[Dict[str, Any]]:
        """Get current performance alerts for a farm"""
        try:
            alerts = self.performance_alerts.get(farm_id, [])
            
            # Filter active alerts (last 24 hours)
            current_time = datetime.utcnow()
            active_alerts = [
                alert for alert in alerts
                if (current_time - alert["timestamp"]).total_seconds() < 86400
            ]
            
            return sorted(active_alerts, key=lambda x: x["timestamp"], reverse=True)
            
        except Exception as e:
            logger.error(f"L Failed to get performance alerts: {e}")
            raise
    
    async def generate_performance_report(
        self, 
        farm_id: str, 
        report_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            report_id = f"report_{uuid.uuid4().hex[:8]}"
            report_period = report_config.get("period", PerformancePeriod.MONTHLY)
            report_type = report_config.get("type", "comprehensive")
            include_charts = report_config.get("include_charts", True)
            
            # Get performance analysis
            analysis = await self.analyze_farm_performance(farm_id, {
                "period": report_period,
                "include_benchmarks": True,
                "include_attribution": True,
                "include_predictions": report_config.get("include_forecasts", False)
            })
            
            # Generate report structure
            report = {
                "report_id": report_id,
                "farm_id": farm_id,
                "report_type": report_type,
                "report_period": report_period,
                "generated_at": datetime.utcnow(),
                
                # Executive summary
                "executive_summary": await self._generate_executive_summary(farm_id, analysis),
                
                # Detailed sections
                "performance_overview": analysis["core_performance"],
                "risk_assessment": analysis["risk_metrics"],
                "agent_analysis": analysis["agent_performance"],
                "strategy_analysis": analysis["strategy_performance"],
                
                # Insights and recommendations
                "key_insights": analysis["key_insights"],
                "recommendations": analysis["recommendations"],
                "action_items": await self._generate_action_items(farm_id, analysis),
                
                # Appendices
                "methodology": await self._generate_methodology_section(),
                "glossary": await self._generate_glossary()
            }
            
            # Add benchmark comparison if available
            if "benchmark_comparison" in analysis:
                report["benchmark_analysis"] = analysis["benchmark_comparison"]
            
            # Add performance attribution if available
            if "performance_attribution" in analysis:
                report["attribution_analysis"] = analysis["performance_attribution"]
            
            # Add forecasts if requested
            if "performance_predictions" in analysis:
                report["performance_forecasts"] = analysis["performance_predictions"]
            
            # Generate charts data if requested
            if include_charts:
                report["charts_data"] = await self._generate_charts_data(farm_id, analysis)
            
            logger.info(f"=Ë Generated performance report {report_id} for farm {farm_id}")
            return report
            
        except Exception as e:
            logger.error(f"L Failed to generate performance report: {e}")
            raise
    
    # Private helper methods
    
    async def _get_performance_data_for_period(
        self, 
        farm_id: str, 
        period: PerformancePeriod
    ) -> List[Dict[str, Any]]:
        """Get performance data for specified period"""
        if farm_id not in self.performance_history:
            return []
        
        current_time = datetime.utcnow()
        
        # Define period durations
        period_durations = {
            PerformancePeriod.HOURLY: timedelta(hours=24),
            PerformancePeriod.DAILY: timedelta(days=30),
            PerformancePeriod.WEEKLY: timedelta(weeks=12),
            PerformancePeriod.MONTHLY: timedelta(days=365),
            PerformancePeriod.QUARTERLY: timedelta(days=1095),  # 3 years
            PerformancePeriod.YEARLY: timedelta(days=1825)     # 5 years
        }
        
        cutoff_time = current_time - period_durations.get(period, timedelta(days=30))
        
        return [
            snapshot for snapshot in self.performance_history[farm_id]
            if snapshot["timestamp"] >= cutoff_time
        ]
    
    async def _perform_core_performance_analysis(
        self, 
        farm_id: str, 
        performance_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform core performance analysis"""
        if not performance_data:
            return {}
        
        latest = performance_data[-1]
        first = performance_data[0]
        
        # Calculate metrics
        roi_values = [float(snapshot["roi"]) for snapshot in performance_data]
        pnl_values = [float(snapshot["total_pnl"]) for snapshot in performance_data]
        
        return {
            "total_return": float(latest["roi"]),
            "cumulative_pnl": float(latest["total_pnl"]),
            "average_daily_return": statistics.mean(roi_values) if roi_values else 0,
            "volatility": statistics.stdev(roi_values) if len(roi_values) > 1 else 0,
            "sharpe_ratio": float(latest["sharpe_ratio"]),
            "max_drawdown": float(latest["max_drawdown"]),
            "current_drawdown": float(latest["current_drawdown"]),
            "total_trades": latest["total_trades"],
            "win_rate": float(latest["win_rate"]),
            "profit_factor": float(latest["profit_factor"]),
            "capital_efficiency": float(latest["capital_efficiency"]),
            "period_start": first["timestamp"].isoformat(),
            "period_end": latest["timestamp"].isoformat()
        }
    
    async def _perform_risk_analysis(
        self, 
        farm_id: str, 
        performance_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform risk analysis"""
        if not performance_data:
            return {}
        
        latest = performance_data[-1]
        
        # Calculate risk metrics
        returns = [float(snapshot["roi"]) for snapshot in performance_data]
        
        return {
            "value_at_risk_95": float(latest["var_95"]),
            "maximum_drawdown": float(latest["max_drawdown"]),
            "volatility": statistics.stdev(returns) if len(returns) > 1 else 0,
            "downside_deviation": await self._calculate_downside_deviation(returns),
            "risk_adjusted_return": float(latest["sharpe_ratio"]),
            "correlation_risk": await self._calculate_correlation_risk(farm_id),
            "concentration_risk": await self._calculate_concentration_risk(farm_id),
            "liquidity_risk": await self._calculate_liquidity_risk(farm_id),
            "overall_risk_score": await self._calculate_overall_risk_score(latest)
        }
    
    async def _perform_trend_analysis(
        self, 
        farm_id: str, 
        performance_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform trend analysis"""
        if len(performance_data) < 2:
            return {}
        
        # Calculate trends
        roi_values = [float(snapshot["roi"]) for snapshot in performance_data]
        timestamps = [snapshot["timestamp"] for snapshot in performance_data]
        
        return {
            "roi_trend": await self._calculate_trend(roi_values),
            "volatility_trend": await self._calculate_volatility_trend(performance_data),
            "performance_momentum": await self._calculate_momentum(roi_values),
            "consistency_score": await self._calculate_consistency_score(roi_values),
            "trend_strength": await self._calculate_trend_strength(roi_values),
            "recent_performance": roi_values[-5:] if len(roi_values) >= 5 else roi_values
        }
    
    async def _perform_agent_performance_analysis(
        self, 
        farm_id: str, 
        performance_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform agent-level performance analysis"""
        # Mock implementation - would aggregate agent performance data
        return {
            "top_performers": [
                {"agent_id": "agent_1", "roi": 12.5, "win_rate": 78},
                {"agent_id": "agent_2", "roi": 10.8, "win_rate": 72}
            ],
            "performance_distribution": {
                "high_performers": 2,
                "average_performers": 3,
                "underperformers": 1
            },
            "agent_correlation": 0.65,
            "contribution_analysis": {
                "agent_1": 35.2,
                "agent_2": 28.7,
                "agent_3": 22.1,
                "others": 14.0
            }
        }
    
    async def _perform_strategy_performance_analysis(
        self, 
        farm_id: str, 
        performance_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform strategy-level performance analysis"""
        # Mock implementation - would analyze strategy performance
        return {
            "strategy_returns": {
                "momentum": 8.7,
                "mean_reversion": 6.2,
                "arbitrage": 4.8
            },
            "strategy_allocation": {
                "momentum": 45.0,
                "mean_reversion": 30.0,
                "arbitrage": 25.0
            },
            "best_performing_strategy": "momentum",
            "strategy_correlation": 0.42,
            "optimization_opportunities": [
                "increase_momentum_allocation",
                "reduce_arbitrage_exposure"
            ]
        }
    
    async def _check_performance_alerts(self, farm_id: str, performance_snapshot: Dict[str, Any]):
        """Check for performance alerts"""
        alerts = []
        current_time = datetime.utcnow()
        
        # Check ROI decline
        if performance_snapshot["roi"] <= self.alert_thresholds["roi_decline"]:
            alerts.append({
                "type": "roi_decline",
                "severity": "high",
                "message": f"ROI declined to {performance_snapshot['roi']}%",
                "threshold": self.alert_thresholds["roi_decline"],
                "current_value": performance_snapshot["roi"],
                "timestamp": current_time
            })
        
        # Check max drawdown
        if performance_snapshot["max_drawdown"] >= self.alert_thresholds["drawdown_limit"]:
            alerts.append({
                "type": "drawdown_limit",
                "severity": "critical",
                "message": f"Max drawdown reached {performance_snapshot['max_drawdown']}%",
                "threshold": self.alert_thresholds["drawdown_limit"],
                "current_value": performance_snapshot["max_drawdown"],
                "timestamp": current_time
            })
        
        # Check win rate
        if performance_snapshot["win_rate"] <= self.alert_thresholds["win_rate_drop"]:
            alerts.append({
                "type": "win_rate_drop",
                "severity": "medium",
                "message": f"Win rate dropped to {performance_snapshot['win_rate']}%",
                "threshold": self.alert_thresholds["win_rate_drop"],
                "current_value": performance_snapshot["win_rate"],
                "timestamp": current_time
            })
        
        # Store alerts
        if alerts:
            if farm_id not in self.performance_alerts:
                self.performance_alerts[farm_id] = []
            self.performance_alerts[farm_id].extend(alerts)
            
            # Limit alert history (keep last 100 alerts)
            if len(self.performance_alerts[farm_id]) > 100:
                self.performance_alerts[farm_id] = self.performance_alerts[farm_id][-100:]
    
    # Mock implementations for complex calculations
    
    async def _calculate_downside_deviation(self, returns: List[float]) -> float:
        negative_returns = [r for r in returns if r < 0]
        return statistics.stdev(negative_returns) if len(negative_returns) > 1 else 0
    
    async def _calculate_correlation_risk(self, farm_id: str) -> float:
        return 0.35  # Mock 35% correlation risk
    
    async def _calculate_concentration_risk(self, farm_id: str) -> float:
        return 0.25  # Mock 25% concentration risk
    
    async def _calculate_liquidity_risk(self, farm_id: str) -> float:
        return 0.15  # Mock 15% liquidity risk
    
    async def _calculate_overall_risk_score(self, latest_data: Dict[str, Any]) -> float:
        # Simple risk score calculation
        volatility_score = min(float(latest_data.get("volatility", 0)) * 2, 40)
        drawdown_score = min(float(latest_data.get("max_drawdown", 0)), 30)
        return min(volatility_score + drawdown_score, 100)
    
    async def _calculate_trend(self, values: List[float]) -> str:
        if len(values) < 2:
            return "insufficient_data"
        
        recent_avg = statistics.mean(values[-5:]) if len(values) >= 5 else statistics.mean(values)
        overall_avg = statistics.mean(values)
        
        if recent_avg > overall_avg * 1.05:
            return "upward"
        elif recent_avg < overall_avg * 0.95:
            return "downward"
        else:
            return "stable"
    
    async def _calculate_volatility_trend(self, performance_data: List[Dict[str, Any]]) -> str:
        return "stable"  # Mock implementation
    
    async def _calculate_momentum(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        return (values[-1] - values[0]) / abs(values[0]) if values[0] != 0 else 0.0
    
    async def _calculate_consistency_score(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        
        volatility = statistics.stdev(values)
        mean_return = statistics.mean(values)
        
        # Higher consistency = lower volatility relative to returns
        if mean_return > 0:
            return max(0, 100 - (volatility / mean_return * 100))
        else:
            return 0.0
    
    async def _calculate_trend_strength(self, values: List[float]) -> float:
        return 75.0  # Mock trend strength
    
    async def _generate_performance_insights(
        self, 
        farm_id: str, 
        core_analysis: Dict[str, Any], 
        risk_analysis: Dict[str, Any], 
        trend_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate performance insights"""
        insights = []
        
        if core_analysis.get("total_return", 0) > 10:
            insights.append("Strong positive returns indicate effective strategy execution")
        
        if core_analysis.get("win_rate", 0) > 70:
            insights.append("High win rate demonstrates consistent trading performance")
        
        if risk_analysis.get("maximum_drawdown", 0) < 10:
            insights.append("Low drawdown shows effective risk management")
        
        if trend_analysis.get("roi_trend") == "upward":
            insights.append("Positive performance trend suggests improving strategy effectiveness")
        
        return insights
    
    async def _calculate_overall_performance_score(
        self, 
        core_analysis: Dict[str, Any], 
        risk_analysis: Dict[str, Any]
    ) -> float:
        """Calculate overall performance score"""
        # Weighted average of key metrics
        return_score = min(max(core_analysis.get("total_return", 0), 0), 20) * 2.5  # Max 50 points
        risk_score = max(0, 50 - risk_analysis.get("overall_risk_score", 50))  # Max 50 points
        
        return min(return_score + risk_score, 100)
    
    async def _generate_performance_recommendations(
        self, 
        farm_id: str, 
        core_analysis: Dict[str, Any], 
        risk_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        if core_analysis.get("win_rate", 0) < 60:
            recommendations.append("Consider reviewing and optimizing trading strategies")
        
        if risk_analysis.get("maximum_drawdown", 0) > 15:
            recommendations.append("Implement stronger risk management controls")
        
        if core_analysis.get("capital_efficiency", 0) < 80:
            recommendations.append("Optimize capital allocation across agents")
        
        return recommendations
    
    # Background task loops
    
    async def _performance_monitoring_loop(self):
        """Background task for performance monitoring"""
        while True:
            try:
                await asyncio.sleep(self.monitoring_interval)
                
                # Update performance metrics for all farms
                for farm_id in self.performance_data.keys():
                    await self._update_performance_metrics(farm_id)
                
            except Exception as e:
                logger.error(f"L Performance monitoring error: {e}")
    
    async def _performance_analytics_loop(self):
        """Background task for analytics updates"""
        while True:
            try:
                await asyncio.sleep(600)  # 10 minutes
                
                # Update analytics cache
                for farm_id in self.performance_history.keys():
                    await self._update_performance_analytics(farm_id)
                
            except Exception as e:
                logger.error(f"L Performance analytics error: {e}")
    
    async def _alert_monitoring_loop(self):
        """Background task for alert monitoring"""
        while True:
            try:
                await asyncio.sleep(60)  # 1 minute
                
                # Check for new alerts
                current_time = datetime.utcnow()
                
                # Clean up old alerts (older than 24 hours)
                for farm_id in list(self.performance_alerts.keys()):
                    self.performance_alerts[farm_id] = [
                        alert for alert in self.performance_alerts[farm_id]
                        if (current_time - alert["timestamp"]).total_seconds() < 86400
                    ]
                
            except Exception as e:
                logger.error(f"L Alert monitoring error: {e}")
    
    async def _initialize_benchmarks(self):
        """Initialize benchmark data"""
        # Mock benchmark initialization
        self.benchmarks = {
            "market_index": {"return": 8.5, "volatility": 15.2},
            "peer_farms": {"return": 11.2, "volatility": 18.7},
            "risk_free_rate": {"return": 2.5, "volatility": 0.1}
        }
    
    async def _update_performance_metrics(self, farm_id: str):
        """Update performance metrics for a farm"""
        # Mock metric update
        pass
    
    async def _update_performance_analytics(self, farm_id: str):
        """Update analytics cache for a farm"""
        # Mock analytics update
        pass

# Service factory
def create_farm_performance_service() -> FarmPerformanceService:
    """Create and configure farm performance service"""
    return FarmPerformanceService()