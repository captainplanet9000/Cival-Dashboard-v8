"""
Phase 9: Fund Distribution Engine
Advanced performance-based capital allocation with ML-powered optimization
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import numpy as np
from dataclasses import dataclass, asdict
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    import joblib
except ImportError:
    # Fallback if sklearn is not available
    RandomForestRegressor = None
    StandardScaler = None
    joblib = None

from ..models.master_wallet_models import (
    FundAllocation, FundDistributionRule, WalletPerformanceMetrics
)
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for allocation targets"""
    target_id: str
    target_type: str
    total_return: Decimal
    sharpe_ratio: Optional[Decimal]
    max_drawdown: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    volatility: Decimal
    risk_score: float
    consistency_score: float

@dataclass
class AllocationRecommendation:
    """Fund allocation recommendation"""
    target_id: str
    target_type: str
    recommended_amount: Decimal
    recommended_percentage: Decimal
    confidence_score: float
    reasoning: str

@dataclass
class MarketCondition:
    """Current market conditions affecting allocation"""
    volatility_index: float
    trend_direction: str  # 'bullish', 'bearish', 'neutral'
    market_sentiment: float  # -1 to 1
    liquidity_score: float
    uncertainty_level: float

@dataclass
class MLAllocationTarget:
    """Enhanced allocation target with ML features"""
    target_id: str
    target_name: str
    target_type: str
    current_allocation: Decimal
    recommended_allocation: Decimal
    performance_score: float
    risk_score: float
    confidence: float
    expected_return: float
    market_correlation: float
    liquidity_score: float
    last_updated: datetime

class FundDistributionEngine:
    """
    Advanced fund distribution engine with performance-based allocation
    Phase 9: Enhanced with ML-powered optimization and real-time market analysis
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Service dependencies
        self.master_wallet_service = None
        self.market_analysis_service = None
        self.event_service = None
        
        # Allocation algorithms
        self.allocation_methods = {
            "performance_weighted": self._performance_weighted_allocation,
            "risk_parity": self._risk_parity_allocation,
            "sharpe_optimized": self._sharpe_optimized_allocation,
            "kelly_criterion": self._kelly_criterion_allocation,
            "equal_weight": self._equal_weight_allocation,
            "momentum_based": self._momentum_based_allocation,
            "mean_reversion": self._mean_reversion_allocation,
            "ml_optimized": self._ml_optimized_allocation,  # New Phase 9 method
            "adaptive_risk": self._adaptive_risk_allocation  # New Phase 9 method
        }
        
        # ML models for allocation optimization
        self.allocation_model = None
        self.risk_model = None
        self.scaler = StandardScaler() if StandardScaler else None
        
        # Performance tracking
        self.performance_history: Dict[str, List[PerformanceMetrics]] = {}
        self.allocation_history: List[Dict[str, Any]] = []
        
        # Market conditions cache
        self.current_market_conditions: Optional[MarketCondition] = None
        self.market_update_interval = 300  # 5 minutes
        
        # Configuration
        self.min_allocation_amount = Decimal("100")  # Minimum $100 allocation
        self.max_allocation_percentage = Decimal("25")  # Max 25% to single target (increased for Phase 9)
        self.rebalance_threshold = Decimal("5")  # Rebalance if >5% deviation
        self.min_cash_reserve = 0.15  # 15% minimum cash reserve
        
        logger.info("FundDistributionEngine Phase 9 initialized")
    
    async def calculate_optimal_allocation(
        self,
        available_funds: Decimal,
        allocation_method: str,
        target_types: List[str] = None,
        constraints: Dict[str, Any] = None
    ) -> List[AllocationRecommendation]:
        """
        Calculate optimal fund allocation using specified method
        
        Args:
            available_funds: Total funds available for allocation
            allocation_method: Algorithm to use for allocation
            target_types: Types of targets to consider (agents, farms, goals)
            constraints: Additional constraints and parameters
        
        Returns:
            List of allocation recommendations
        """
        try:
            # Get performance data for all targets
            performance_data = await self._get_comprehensive_performance_data(target_types)
            
            if not performance_data:
                logger.warning("No performance data available for allocation")
                return []
            
            # Apply allocation method
            if allocation_method in self.allocation_methods:
                recommendations = await self.allocation_methods[allocation_method](
                    available_funds, performance_data, constraints or {}
                )
            else:
                raise ValueError(f"Unknown allocation method: {allocation_method}")
            
            # Apply constraints and filters
            recommendations = self._apply_allocation_constraints(recommendations, constraints or {})
            
            # Normalize allocations to available funds
            recommendations = self._normalize_allocations(recommendations, available_funds)
            
            logger.info(f"Generated {len(recommendations)} allocation recommendations using {allocation_method}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to calculate optimal allocation: {e}")
            raise
    
    async def _get_comprehensive_performance_data(self, target_types: List[str] = None) -> List[PerformanceMetrics]:
        """Get comprehensive performance data for all allocation targets"""
        performance_data = []
        
        try:
            # Default to all target types if none specified
            if not target_types:
                target_types = ["agent", "farm", "goal"]
            
            # Get agent performance data
            if "agent" in target_types:
                agent_data = await self._get_agent_performance_data()
                performance_data.extend(agent_data)
            
            # Get farm performance data
            if "farm" in target_types:
                farm_data = await self._get_farm_performance_data()
                performance_data.extend(farm_data)
            
            # Get goal performance data
            if "goal" in target_types:
                goal_data = await self._get_goal_performance_data()
                performance_data.extend(goal_data)
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Failed to get performance data: {e}")
            return []
    
    async def _get_agent_performance_data(self) -> List[PerformanceMetrics]:
        """Get performance data for all agents"""
        agent_data = []
        
        try:
            agent_performance_service = self.registry.get_service("agent_performance_service")
            if not agent_performance_service:
                return agent_data
            
            # Get agent rankings and metrics
            agent_rankings = await agent_performance_service.get_agent_rankings(period_days=30)
            
            for ranking in agent_rankings:
                metrics = PerformanceMetrics(
                    target_id=ranking.agent_id,
                    target_type="agent",
                    total_return=Decimal(str(ranking.total_return_percentage)),
                    sharpe_ratio=Decimal(str(ranking.sharpe_ratio)) if ranking.sharpe_ratio else None,
                    max_drawdown=Decimal(str(ranking.max_drawdown_percentage)),
                    win_rate=Decimal(str(ranking.win_rate)),
                    profit_factor=Decimal(str(ranking.profit_factor)) if ranking.profit_factor else Decimal("1"),
                    volatility=Decimal(str(ranking.volatility)) if ranking.volatility else Decimal("0"),
                    risk_score=ranking.risk_score or 50.0,
                    consistency_score=ranking.consistency_score or 50.0
                )
                agent_data.append(metrics)
            
        except Exception as e:
            logger.error(f"Failed to get agent performance data: {e}")
        
        return agent_data
    
    async def _get_farm_performance_data(self) -> List[PerformanceMetrics]:
        """Get performance data for all farms"""
        farm_data = []
        
        try:
            farm_service = self.registry.get_service("farm_management_service")
            if not farm_service:
                return farm_data
            
            # Get farm performance metrics
            farm_performance = await farm_service.get_all_farm_performance()
            
            for farm_id, performance in farm_performance.items():
                metrics = PerformanceMetrics(
                    target_id=farm_id,
                    target_type="farm",
                    total_return=Decimal(str(performance.get("total_return", 0))),
                    sharpe_ratio=Decimal(str(performance.get("sharpe_ratio", 0))) if performance.get("sharpe_ratio") else None,
                    max_drawdown=Decimal(str(performance.get("max_drawdown", 0))),
                    win_rate=Decimal(str(performance.get("win_rate", 0))),
                    profit_factor=Decimal(str(performance.get("profit_factor", 1))),
                    volatility=Decimal(str(performance.get("volatility", 0))),
                    risk_score=performance.get("risk_score", 50.0),
                    consistency_score=performance.get("consistency_score", 50.0)
                )
                farm_data.append(metrics)
            
        except Exception as e:
            logger.error(f"Failed to get farm performance data: {e}")
        
        return farm_data
    
    async def _get_goal_performance_data(self) -> List[PerformanceMetrics]:
        """Get performance data for all goals"""
        goal_data = []
        
        try:
            goal_service = self.registry.get_service("goal_management_service")
            if not goal_service:
                return goal_data
            
            # Get goal progress and performance
            goal_progress = await goal_service.get_all_goal_progress()
            
            for goal_id, progress in goal_progress.items():
                # Convert goal progress to performance metrics
                completion_rate = progress.get("completion_percentage", 0) / 100
                efficiency_score = progress.get("efficiency_score", 50)
                
                metrics = PerformanceMetrics(
                    target_id=goal_id,
                    target_type="goal",
                    total_return=Decimal(str(completion_rate * 10)),  # Convert completion to return-like metric
                    sharpe_ratio=None,
                    max_drawdown=Decimal("0"),
                    win_rate=Decimal(str(completion_rate)),
                    profit_factor=Decimal(str(efficiency_score / 50)),
                    volatility=Decimal("0"),
                    risk_score=progress.get("risk_score", 50.0),
                    consistency_score=efficiency_score
                )
                goal_data.append(metrics)
            
        except Exception as e:
            logger.error(f"Failed to get goal performance data: {e}")
        
        return goal_data
    
    async def _performance_weighted_allocation(
        self,
        available_funds: Decimal,
        performance_data: List[PerformanceMetrics],
        constraints: Dict[str, Any]
    ) -> List[AllocationRecommendation]:
        """Performance-weighted allocation based on multiple performance metrics"""
        recommendations = []
        
        try:
            if not performance_data:
                return recommendations
            
            # Calculate composite performance scores
            performance_scores = []
            for metrics in performance_data:
                # Weighted performance score
                return_weight = 0.3
                sharpe_weight = 0.25
                consistency_weight = 0.2
                win_rate_weight = 0.15
                drawdown_weight = 0.1
                
                score = (
                    float(metrics.total_return) * return_weight +
                    float(metrics.sharpe_ratio or 0) * sharpe_weight +
                    metrics.consistency_score * consistency_weight +
                    float(metrics.win_rate) * 100 * win_rate_weight -
                    float(metrics.max_drawdown) * drawdown_weight
                )
                
                performance_scores.append((metrics, score))
            
            # Sort by performance score
            performance_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Calculate allocations based on normalized scores
            total_score = sum(score for _, score in performance_scores if score > 0)
            
            for metrics, score in performance_scores:
                if score > 0:  # Only allocate to positive-performing targets
                    allocation_percentage = (score / total_score) * 100
                    allocation_amount = available_funds * (Decimal(str(allocation_percentage)) / 100)
                    
                    recommendation = AllocationRecommendation(
                        target_id=metrics.target_id,
                        target_type=metrics.target_type,
                        recommended_amount=allocation_amount,
                        recommended_percentage=Decimal(str(allocation_percentage)),
                        confidence_score=min(score / 100, 1.0),
                        reasoning=f"Performance score: {score:.2f}, Return: {metrics.total_return}%, Sharpe: {metrics.sharpe_ratio}"
                    )
                    recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Failed in performance-weighted allocation: {e}")
        
        return recommendations
    
    async def _risk_parity_allocation(
        self,
        available_funds: Decimal,
        performance_data: List[PerformanceMetrics],
        constraints: Dict[str, Any]
    ) -> List[AllocationRecommendation]:
        """Risk parity allocation - equal risk contribution from each target"""
        recommendations = []
        
        try:
            if not performance_data:
                return recommendations
            
            # Calculate risk contributions
            risk_contributions = []
            for metrics in performance_data:
                # Use volatility and max drawdown as risk measures
                risk_measure = float(metrics.volatility) + float(metrics.max_drawdown)
                if risk_measure > 0:
                    risk_contributions.append((metrics, risk_measure))
            
            if not risk_contributions:
                return recommendations
            
            # Calculate inverse risk weights
            total_inverse_risk = sum(1 / risk for _, risk in risk_contributions)
            
            for metrics, risk_measure in risk_contributions:
                weight = (1 / risk_measure) / total_inverse_risk
                allocation_amount = available_funds * Decimal(str(weight))
                
                recommendation = AllocationRecommendation(
                    target_id=metrics.target_id,
                    target_type=metrics.target_type,
                    recommended_amount=allocation_amount,
                    recommended_percentage=Decimal(str(weight * 100)),
                    confidence_score=0.8,  # High confidence in risk parity
                    reasoning=f"Risk parity allocation, risk measure: {risk_measure:.4f}"
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Failed in risk parity allocation: {e}")
        
        return recommendations
    
    async def _sharpe_optimized_allocation(
        self,
        available_funds: Decimal,
        performance_data: List[PerformanceMetrics],
        constraints: Dict[str, Any]
    ) -> List[AllocationRecommendation]:
        """Sharpe ratio optimized allocation"""
        recommendations = []
        
        try:
            if not performance_data:
                return recommendations
            
            # Filter targets with positive Sharpe ratios
            sharpe_targets = [
                metrics for metrics in performance_data
                if metrics.sharpe_ratio and metrics.sharpe_ratio > 0
            ]
            
            if not sharpe_targets:
                return recommendations
            
            # Sort by Sharpe ratio and allocate more to higher Sharpe
            sharpe_targets.sort(key=lambda x: x.sharpe_ratio, reverse=True)
            
            # Use exponential weighting based on Sharpe ratio
            weights = []
            for i, metrics in enumerate(sharpe_targets):
                weight = np.exp(-i * 0.5)  # Exponential decay
                weights.append(weight)
            
            total_weight = sum(weights)
            
            for metrics, weight in zip(sharpe_targets, weights):
                allocation_percentage = (weight / total_weight) * 100
                allocation_amount = available_funds * (Decimal(str(allocation_percentage)) / 100)
                
                recommendation = AllocationRecommendation(
                    target_id=metrics.target_id,
                    target_type=metrics.target_type,
                    recommended_amount=allocation_amount,
                    recommended_percentage=Decimal(str(allocation_percentage)),
                    confidence_score=float(metrics.sharpe_ratio) / 5.0,  # Normalize to 0-1
                    reasoning=f"Sharpe optimized, Sharpe ratio: {metrics.sharpe_ratio}"
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Failed in Sharpe optimized allocation: {e}")
        
        return recommendations
    
    async def _kelly_criterion_allocation(
        self,
        available_funds: Decimal,
        performance_data: List[PerformanceMetrics],
        constraints: Dict[str, Any]
    ) -> List[AllocationRecommendation]:
        """Kelly criterion allocation based on win rate and profit factor"""
        recommendations = []
        
        try:
            if not performance_data:
                return recommendations
            
            kelly_allocations = []
            
            for metrics in performance_data:
                # Kelly formula: f = (bp - q) / b
                # where b = odds (profit factor), p = win rate, q = loss rate
                win_rate = float(metrics.win_rate)
                profit_factor = float(metrics.profit_factor)
                
                if win_rate > 0 and profit_factor > 1:
                    loss_rate = 1 - win_rate
                    kelly_fraction = (profit_factor * win_rate - loss_rate) / profit_factor
                    
                    # Cap Kelly fraction at 25% for safety
                    kelly_fraction = max(0, min(kelly_fraction, 0.25))
                    
                    if kelly_fraction > 0:
                        kelly_allocations.append((metrics, kelly_fraction))
            
            if not kelly_allocations:
                return recommendations
            
            # Normalize Kelly fractions
            total_kelly = sum(fraction for _, fraction in kelly_allocations)
            
            for metrics, kelly_fraction in kelly_allocations:
                normalized_fraction = kelly_fraction / total_kelly if total_kelly > 0 else 0
                allocation_amount = available_funds * Decimal(str(normalized_fraction))
                
                recommendation = AllocationRecommendation(
                    target_id=metrics.target_id,
                    target_type=metrics.target_type,
                    recommended_amount=allocation_amount,
                    recommended_percentage=Decimal(str(normalized_fraction * 100)),
                    confidence_score=kelly_fraction,
                    reasoning=f"Kelly criterion: {kelly_fraction:.4f}, Win rate: {metrics.win_rate}, PF: {metrics.profit_factor}"
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Failed in Kelly criterion allocation: {e}")
        
        return recommendations
    
    async def _equal_weight_allocation(
        self,
        available_funds: Decimal,
        performance_data: List[PerformanceMetrics],
        constraints: Dict[str, Any]
    ) -> List[AllocationRecommendation]:
        """Equal weight allocation across all targets"""
        recommendations = []
        
        try:
            if not performance_data:
                return recommendations
            
            num_targets = len(performance_data)
            equal_amount = available_funds / num_targets
            equal_percentage = Decimal("100") / num_targets
            
            for metrics in performance_data:
                recommendation = AllocationRecommendation(
                    target_id=metrics.target_id,
                    target_type=metrics.target_type,
                    recommended_amount=equal_amount,
                    recommended_percentage=equal_percentage,
                    confidence_score=0.7,  # Moderate confidence
                    reasoning="Equal weight allocation across all targets"
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Failed in equal weight allocation: {e}")
        
        return recommendations
    
    async def _momentum_based_allocation(
        self,
        available_funds: Decimal,
        performance_data: List[PerformanceMetrics],
        constraints: Dict[str, Any]
    ) -> List[AllocationRecommendation]:
        """Momentum-based allocation favoring recent strong performers"""
        recommendations = []
        
        try:
            # Get recent performance trends
            momentum_scores = []
            
            for metrics in performance_data:
                # Calculate momentum score based on recent performance
                momentum_score = (
                    float(metrics.total_return) * 0.4 +
                    metrics.consistency_score * 0.3 +
                    float(metrics.win_rate) * 100 * 0.3
                )
                
                if momentum_score > 0:
                    momentum_scores.append((metrics, momentum_score))
            
            if not momentum_scores:
                return recommendations
            
            # Sort by momentum and allocate exponentially
            momentum_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Use momentum-weighted allocation
            total_momentum = sum(score for _, score in momentum_scores)
            
            for metrics, momentum_score in momentum_scores:
                allocation_percentage = (momentum_score / total_momentum) * 100
                allocation_amount = available_funds * (Decimal(str(allocation_percentage)) / 100)
                
                recommendation = AllocationRecommendation(
                    target_id=metrics.target_id,
                    target_type=metrics.target_type,
                    recommended_amount=allocation_amount,
                    recommended_percentage=Decimal(str(allocation_percentage)),
                    confidence_score=momentum_score / 100,
                    reasoning=f"Momentum allocation, momentum score: {momentum_score:.2f}"
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Failed in momentum-based allocation: {e}")
        
        return recommendations
    
    async def _mean_reversion_allocation(
        self,
        available_funds: Decimal,
        performance_data: List[PerformanceMetrics],
        constraints: Dict[str, Any]
    ) -> List[AllocationRecommendation]:
        """Mean reversion allocation favoring recently underperforming targets"""
        recommendations = []
        
        try:
            # Calculate mean reversion scores (inverse of recent performance)
            reversion_scores = []
            
            # Calculate average performance
            avg_return = sum(float(m.total_return) for m in performance_data) / len(performance_data)
            
            for metrics in performance_data:
                # Score based on how much below average (for mean reversion)
                performance_gap = avg_return - float(metrics.total_return)
                
                # Only consider targets that aren't too risky
                if metrics.risk_score < 80 and performance_gap > 0:
                    reversion_score = performance_gap * (100 - metrics.risk_score) / 100
                    reversion_scores.append((metrics, reversion_score))
            
            if not reversion_scores:
                return recommendations
            
            # Allocate based on reversion potential
            total_reversion = sum(score for _, score in reversion_scores)
            
            for metrics, reversion_score in reversion_scores:
                allocation_percentage = (reversion_score / total_reversion) * 100
                allocation_amount = available_funds * (Decimal(str(allocation_percentage)) / 100)
                
                recommendation = AllocationRecommendation(
                    target_id=metrics.target_id,
                    target_type=metrics.target_type,
                    recommended_amount=allocation_amount,
                    recommended_percentage=Decimal(str(allocation_percentage)),
                    confidence_score=0.6,  # Lower confidence for mean reversion
                    reasoning=f"Mean reversion allocation, reversion score: {reversion_score:.2f}"
                )
                recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Failed in mean reversion allocation: {e}")
        
        return recommendations
    
    def _apply_allocation_constraints(
        self,
        recommendations: List[AllocationRecommendation],
        constraints: Dict[str, Any]
    ) -> List[AllocationRecommendation]:
        """Apply allocation constraints and limits"""
        filtered_recommendations = []
        
        try:
            min_amount = constraints.get("min_allocation_amount", self.min_allocation_amount)
            max_percentage = constraints.get("max_allocation_percentage", self.max_allocation_percentage)
            max_targets = constraints.get("max_targets")
            
            # Filter by minimum amount
            for rec in recommendations:
                if rec.recommended_amount >= min_amount:
                    # Apply maximum percentage constraint
                    if rec.recommended_percentage <= max_percentage:
                        filtered_recommendations.append(rec)
                    else:
                        # Cap at maximum percentage
                        rec.recommended_percentage = max_percentage
                        rec.reasoning += f" (capped at {max_percentage}%)"
                        filtered_recommendations.append(rec)
            
            # Apply maximum targets constraint
            if max_targets and len(filtered_recommendations) > max_targets:
                # Keep top performers only
                filtered_recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
                filtered_recommendations = filtered_recommendations[:max_targets]
            
        except Exception as e:
            logger.error(f"Failed to apply constraints: {e}")
            return recommendations
        
        return filtered_recommendations
    
    def _normalize_allocations(
        self,
        recommendations: List[AllocationRecommendation],
        available_funds: Decimal
    ) -> List[AllocationRecommendation]:
        """Normalize allocations to match available funds"""
        try:
            if not recommendations:
                return recommendations
            
            # Calculate total recommended amount
            total_recommended = sum(rec.recommended_amount for rec in recommendations)
            
            if total_recommended == 0:
                return recommendations
            
            # Normalize to available funds
            scaling_factor = available_funds / total_recommended
            
            for rec in recommendations:
                rec.recommended_amount *= scaling_factor
                rec.recommended_percentage = (rec.recommended_amount / available_funds) * 100
            
        except Exception as e:
            logger.error(f"Failed to normalize allocations: {e}")
        
        return recommendations
    
    async def evaluate_rebalancing_needs(
        self,
        current_allocations: List[FundAllocation],
        target_allocations: List[AllocationRecommendation]
    ) -> List[Dict[str, Any]]:
        """Evaluate if rebalancing is needed based on current vs target allocations"""
        rebalancing_actions = []
        
        try:
            # Create mappings for easy lookup
            current_map = {alloc.target_id: alloc for alloc in current_allocations if alloc.is_active}
            target_map = {rec.target_id: rec for rec in target_allocations}
            
            # Check for rebalancing needs
            for target_id, current_alloc in current_map.items():
                if target_id in target_map:
                    target_alloc = target_map[target_id]
                    
                    # Calculate deviation
                    current_percentage = current_alloc.allocated_percentage
                    target_percentage = target_alloc.recommended_percentage
                    deviation = abs(current_percentage - target_percentage)
                    
                    if deviation > self.rebalance_threshold:
                        action = {
                            "action": "rebalance",
                            "target_id": target_id,
                            "target_type": current_alloc.target_type,
                            "current_amount": current_alloc.allocated_amount_usd,
                            "target_amount": target_alloc.recommended_amount,
                            "deviation_percentage": float(deviation),
                            "reasoning": f"Deviation of {deviation:.2f}% exceeds threshold of {self.rebalance_threshold}%"
                        }
                        rebalancing_actions.append(action)
                else:
                    # Target no longer in recommendations - consider removing
                    action = {
                        "action": "remove",
                        "target_id": target_id,
                        "target_type": current_alloc.target_type,
                        "current_amount": current_alloc.allocated_amount_usd,
                        "reasoning": "Target no longer recommended for allocation"
                    }
                    rebalancing_actions.append(action)
            
            # Check for new targets
            for target_id, target_alloc in target_map.items():
                if target_id not in current_map:
                    action = {
                        "action": "add",
                        "target_id": target_id,
                        "target_type": target_alloc.target_type,
                        "target_amount": target_alloc.recommended_amount,
                        "reasoning": f"New target recommended with {target_alloc.confidence_score:.2f} confidence"
                    }
                    rebalancing_actions.append(action)
            
        except Exception as e:
            logger.error(f"Failed to evaluate rebalancing needs: {e}")
        
        return rebalancing_actions
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and health metrics"""
        return {
            "service": "fund_distribution_engine",
            "status": "running",
            "available_methods": list(self.allocation_methods.keys()),
            "min_allocation_amount": float(self.min_allocation_amount),
            "max_allocation_percentage": float(self.max_allocation_percentage),
            "rebalance_threshold": float(self.rebalance_threshold),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_fund_distribution_engine():
    """Factory function to create FundDistributionEngine instance"""
    return FundDistributionEngine()