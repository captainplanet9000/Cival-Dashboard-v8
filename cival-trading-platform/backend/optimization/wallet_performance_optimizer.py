"""
Phase 7: Wallet Performance Optimization Engine
Advanced optimization algorithms for wallet performance and system efficiency
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import numpy as np
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OptimizationStrategy(Enum):
    """Optimization strategies available"""
    PROFIT_MAXIMIZATION = "profit_maximization"
    RISK_MINIMIZATION = "risk_minimization"
    SHARPE_OPTIMIZATION = "sharpe_optimization"
    DRAWDOWN_CONTROL = "drawdown_control"
    DIVERSIFICATION = "diversification"
    ADAPTIVE_ALLOCATION = "adaptive_allocation"

@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization analysis"""
    total_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    information_ratio: Decimal
    tracking_error: Decimal

@dataclass
class OptimizationResult:
    """Result of optimization analysis"""
    strategy: OptimizationStrategy
    recommended_allocations: Dict[str, Decimal]
    expected_return: Decimal
    expected_risk: Decimal
    confidence_score: Decimal
    optimization_time: float
    metadata: Dict[str, Any]

class WalletPerformanceOptimizer:
    """
    Advanced wallet performance optimization engine
    Phase 7: AI-driven optimization with multiple strategies
    """
    
    def __init__(self):
        # Optimization parameters
        self.optimization_window = 30  # days
        self.rebalancing_threshold = Decimal("0.05")  # 5% drift
        self.risk_tolerance = Decimal("0.15")  # 15% max portfolio risk
        self.min_allocation = Decimal("0.01")  # 1% minimum allocation
        self.max_allocation = Decimal("0.25")  # 25% maximum allocation
        
        # Performance tracking
        self.optimization_history: List[OptimizationResult] = []
        self.performance_cache: Dict[str, PerformanceMetrics] = {}
        
        # Machine learning models (placeholder for real ML integration)
        self.ml_models = {
            "return_predictor": None,
            "risk_predictor": None,
            "correlation_model": None
        }
        
        logger.info("WalletPerformanceOptimizer initialized")
    
    async def optimize_wallet_allocation(
        self, 
        wallet_data: Dict[str, Any],
        strategy: OptimizationStrategy = OptimizationStrategy.SHARPE_OPTIMIZATION,
        constraints: Optional[Dict[str, Any]] = None
    ) -> OptimizationResult:
        """
        Optimize wallet allocation using specified strategy
        Main optimization entry point
        """
        try:
            start_time = datetime.now()
            
            # Extract allocation data
            allocations = wallet_data.get("allocations", [])
            if not allocations:
                return self._create_empty_result(strategy, "No allocations found")
            
            # Calculate current performance metrics
            current_metrics = await self._calculate_portfolio_metrics(allocations)
            
            # Apply optimization strategy
            if strategy == OptimizationStrategy.PROFIT_MAXIMIZATION:
                result = await self._optimize_for_profit(allocations, constraints)
            elif strategy == OptimizationStrategy.RISK_MINIMIZATION:
                result = await self._optimize_for_risk(allocations, constraints)
            elif strategy == OptimizationStrategy.SHARPE_OPTIMIZATION:
                result = await self._optimize_sharpe_ratio(allocations, constraints)
            elif strategy == OptimizationStrategy.DRAWDOWN_CONTROL:
                result = await self._optimize_drawdown_control(allocations, constraints)
            elif strategy == OptimizationStrategy.DIVERSIFICATION:
                result = await self._optimize_diversification(allocations, constraints)
            elif strategy == OptimizationStrategy.ADAPTIVE_ALLOCATION:
                result = await self._optimize_adaptive_allocation(allocations, constraints)
            else:
                result = await self._optimize_sharpe_ratio(allocations, constraints)
            
            # Calculate optimization time
            optimization_time = (datetime.now() - start_time).total_seconds()
            result.optimization_time = optimization_time
            
            # Add to history
            self.optimization_history.append(result)
            
            # Keep only last 100 optimization results
            if len(self.optimization_history) > 100:
                self.optimization_history = self.optimization_history[-100:]
            
            logger.info(f"Optimization completed: {strategy.value} in {optimization_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to optimize wallet allocation: {e}")
            return self._create_empty_result(strategy, str(e))
    
    async def _calculate_portfolio_metrics(self, allocations: List[Dict[str, Any]]) -> PerformanceMetrics:
        """Calculate comprehensive portfolio performance metrics"""
        try:
            if not allocations:
                return self._create_empty_metrics()
            
            # Extract performance data
            returns = []
            allocated_amounts = []
            current_values = []
            
            for allocation in allocations:
                if allocation.get("is_active", False):
                    allocated = Decimal(str(allocation.get("allocated_amount_usd", 0)))
                    current = Decimal(str(allocation.get("current_value_usd", 0)))
                    
                    if allocated > 0:
                        return_pct = ((current - allocated) / allocated) * 100
                        returns.append(float(return_pct))
                        allocated_amounts.append(float(allocated))
                        current_values.append(float(current))
            
            if not returns:
                return self._create_empty_metrics()
            
            # Convert to numpy arrays for calculations
            returns_array = np.array(returns)
            weights = np.array(allocated_amounts) / sum(allocated_amounts)
            
            # Calculate portfolio metrics
            portfolio_return = np.average(returns_array, weights=weights)
            portfolio_volatility = np.sqrt(np.average((returns_array - portfolio_return) ** 2, weights=weights))
            
            # Risk-free rate assumption (3% annual)
            risk_free_rate = 3.0
            
            # Sharpe ratio
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
            
            # Maximum drawdown calculation
            cumulative_returns = np.cumprod(1 + returns_array / 100)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max * 100
            max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0
            
            # Win rate
            winning_trades = sum(1 for r in returns if r > 0)
            win_rate = (winning_trades / len(returns)) * 100 if returns else 0
            
            # Profit factor
            gross_profit = sum(r for r in returns if r > 0)
            gross_loss = abs(sum(r for r in returns if r < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Sortino ratio (downside deviation)
            negative_returns = [r for r in returns if r < 0]
            downside_volatility = np.std(negative_returns) if negative_returns else 0
            sortino_ratio = (portfolio_return - risk_free_rate) / downside_volatility if downside_volatility > 0 else 0
            
            # Calmar ratio
            calmar_ratio = portfolio_return / max_drawdown if max_drawdown > 0 else 0
            
            return PerformanceMetrics(
                total_return=Decimal(str(portfolio_return)),
                volatility=Decimal(str(portfolio_volatility)),
                sharpe_ratio=Decimal(str(sharpe_ratio)),
                max_drawdown=Decimal(str(max_drawdown)),
                win_rate=Decimal(str(win_rate)),
                profit_factor=Decimal(str(profit_factor)),
                sortino_ratio=Decimal(str(sortino_ratio)),
                calmar_ratio=Decimal(str(calmar_ratio)),
                information_ratio=Decimal(str(sharpe_ratio)),  # Simplified
                tracking_error=Decimal(str(portfolio_volatility))
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio metrics: {e}")
            return self._create_empty_metrics()
    
    async def _optimize_for_profit(self, allocations: List[Dict[str, Any]], constraints: Optional[Dict[str, Any]]) -> OptimizationResult:
        """Optimize for maximum profit"""
        try:
            # Analyze historical performance to identify best performers
            performance_scores = {}
            
            for allocation in allocations:
                if allocation.get("is_active", False):
                    target_id = allocation.get("target_id", "")
                    allocated = Decimal(str(allocation.get("allocated_amount_usd", 0)))
                    current = Decimal(str(allocation.get("current_value_usd", 0)))
                    
                    if allocated > 0:
                        roi = ((current - allocated) / allocated) * 100
                        performance_scores[target_id] = float(roi)
            
            # Sort by performance (descending)
            sorted_targets = sorted(performance_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Allocate more to top performers
            total_allocation = Decimal("100")  # 100% allocation
            recommended_allocations = {}
            
            if sorted_targets:
                # Top performer gets 40%, second 30%, third 20%, rest 10%
                allocation_weights = [0.4, 0.3, 0.2, 0.1]
                
                for i, (target_id, performance) in enumerate(sorted_targets[:4]):
                    weight = allocation_weights[i] if i < len(allocation_weights) else 0.1 / len(sorted_targets[4:])
                    recommended_allocations[target_id] = Decimal(str(weight * 100))
            
            # Calculate expected return (weighted average of top performers)
            expected_return = Decimal("0")
            if sorted_targets:
                for target_id, performance in sorted_targets[:3]:
                    weight = recommended_allocations.get(target_id, Decimal("0")) / 100
                    expected_return += Decimal(str(performance)) * weight
            
            return OptimizationResult(
                strategy=OptimizationStrategy.PROFIT_MAXIMIZATION,
                recommended_allocations=recommended_allocations,
                expected_return=expected_return,
                expected_risk=Decimal("15"),  # Estimated risk
                confidence_score=Decimal("0.8"),
                optimization_time=0.0,
                metadata={"top_performers": sorted_targets[:3]}
            )
            
        except Exception as e:
            logger.error(f"Failed to optimize for profit: {e}")
            return self._create_empty_result(OptimizationStrategy.PROFIT_MAXIMIZATION, str(e))
    
    async def _optimize_for_risk(self, allocations: List[Dict[str, Any]], constraints: Optional[Dict[str, Any]]) -> OptimizationResult:
        """Optimize for minimum risk"""
        try:
            # Calculate risk metrics for each allocation
            risk_scores = {}
            
            for allocation in allocations:
                if allocation.get("is_active", False):
                    target_id = allocation.get("target_id", "")
                    max_drawdown = Decimal(str(allocation.get("max_drawdown", 0)))
                    current_drawdown = Decimal(str(allocation.get("current_drawdown", 0)))
                    
                    # Risk score based on drawdown metrics (lower is better)
                    risk_score = float(max_drawdown + current_drawdown)
                    risk_scores[target_id] = risk_score
            
            # Sort by risk (ascending - lower risk first)
            sorted_targets = sorted(risk_scores.items(), key=lambda x: x[1])
            
            # Allocate more to lower risk targets
            recommended_allocations = {}
            total_targets = len(sorted_targets)
            
            if total_targets > 0:
                # Equal weight for simplicity, could use more sophisticated risk budgeting
                equal_weight = Decimal("100") / total_targets
                
                for target_id, risk_score in sorted_targets:
                    # Adjust weight based on inverse risk
                    if risk_score > 0:
                        inverse_risk = 1.0 / (1.0 + risk_score)
                        weight = Decimal(str(inverse_risk * 100 / total_targets))
                    else:
                        weight = equal_weight
                    
                    recommended_allocations[target_id] = weight
            
            # Normalize allocations to 100%
            total_allocation = sum(recommended_allocations.values())
            if total_allocation > 0:
                for target_id in recommended_allocations:
                    recommended_allocations[target_id] = (
                        recommended_allocations[target_id] / total_allocation * 100
                    )
            
            # Calculate expected risk (weighted average)
            expected_risk = Decimal("0")
            if sorted_targets:
                for target_id, risk_score in sorted_targets:
                    weight = recommended_allocations.get(target_id, Decimal("0")) / 100
                    expected_risk += Decimal(str(risk_score)) * weight
            
            return OptimizationResult(
                strategy=OptimizationStrategy.RISK_MINIMIZATION,
                recommended_allocations=recommended_allocations,
                expected_return=Decimal("8"),  # Conservative return estimate
                expected_risk=expected_risk,
                confidence_score=Decimal("0.9"),
                optimization_time=0.0,
                metadata={"lowest_risk_targets": sorted_targets[:3]}
            )
            
        except Exception as e:
            logger.error(f"Failed to optimize for risk: {e}")
            return self._create_empty_result(OptimizationStrategy.RISK_MINIMIZATION, str(e))
    
    async def _optimize_sharpe_ratio(self, allocations: List[Dict[str, Any]], constraints: Optional[Dict[str, Any]]) -> OptimizationResult:
        """Optimize for maximum Sharpe ratio (risk-adjusted return)"""
        try:
            # Calculate Sharpe ratio for each allocation
            sharpe_ratios = {}
            
            for allocation in allocations:
                if allocation.get("is_active", False):
                    target_id = allocation.get("target_id", "")
                    allocated = Decimal(str(allocation.get("allocated_amount_usd", 0)))
                    current = Decimal(str(allocation.get("current_value_usd", 0)))
                    max_drawdown = Decimal(str(allocation.get("max_drawdown", 1)))
                    
                    if allocated > 0 and max_drawdown > 0:
                        roi = ((current - allocated) / allocated) * 100
                        risk_measure = max_drawdown  # Use max drawdown as risk proxy
                        
                        # Simple Sharpe ratio calculation
                        risk_free_rate = Decimal("3")  # 3% risk-free rate
                        sharpe = (roi - risk_free_rate) / risk_measure
                        sharpe_ratios[target_id] = float(sharpe)
            
            # Sort by Sharpe ratio (descending)
            sorted_targets = sorted(sharpe_ratios.items(), key=lambda x: x[1], reverse=True)
            
            # Allocate based on Sharpe ratio ranking
            recommended_allocations = {}
            total_sharpe = sum(max(0, sharpe) for _, sharpe in sorted_targets)
            
            if total_sharpe > 0:
                for target_id, sharpe in sorted_targets:
                    if sharpe > 0:
                        weight = (sharpe / total_sharpe) * 100
                        recommended_allocations[target_id] = Decimal(str(weight))
            else:
                # Equal allocation if no positive Sharpe ratios
                equal_weight = Decimal("100") / len(sorted_targets) if sorted_targets else Decimal("0")
                for target_id, _ in sorted_targets:
                    recommended_allocations[target_id] = equal_weight
            
            # Calculate expected metrics
            expected_return = Decimal("0")
            expected_risk = Decimal("0")
            
            if sorted_targets:
                # Weighted average of top performers
                for target_id, sharpe in sorted_targets[:3]:
                    weight = recommended_allocations.get(target_id, Decimal("0")) / 100
                    expected_return += Decimal("12") * weight  # Base return estimate
                    expected_risk += Decimal("10") * weight  # Base risk estimate
            
            return OptimizationResult(
                strategy=OptimizationStrategy.SHARPE_OPTIMIZATION,
                recommended_allocations=recommended_allocations,
                expected_return=expected_return,
                expected_risk=expected_risk,
                confidence_score=Decimal("0.85"),
                optimization_time=0.0,
                metadata={"best_sharpe_ratios": sorted_targets[:3]}
            )
            
        except Exception as e:
            logger.error(f"Failed to optimize Sharpe ratio: {e}")
            return self._create_empty_result(OptimizationStrategy.SHARPE_OPTIMIZATION, str(e))
    
    async def _optimize_drawdown_control(self, allocations: List[Dict[str, Any]], constraints: Optional[Dict[str, Any]]) -> OptimizationResult:
        """Optimize for drawdown control"""
        try:
            # Focus on allocations with low current drawdown
            drawdown_scores = {}
            
            for allocation in allocations:
                if allocation.get("is_active", False):
                    target_id = allocation.get("target_id", "")
                    current_drawdown = Decimal(str(allocation.get("current_drawdown", 0)))
                    max_drawdown = Decimal(str(allocation.get("max_drawdown", 0)))
                    
                    # Score based on drawdown control (lower is better)
                    drawdown_score = float(current_drawdown + max_drawdown * 0.5)
                    drawdown_scores[target_id] = drawdown_score
            
            # Sort by drawdown score (ascending)
            sorted_targets = sorted(drawdown_scores.items(), key=lambda x: x[1])
            
            # Conservative allocation favoring low drawdown targets
            recommended_allocations = {}
            
            if sorted_targets:
                # Allocate 60% to best drawdown target, rest distributed
                best_target = sorted_targets[0][0]
                recommended_allocations[best_target] = Decimal("60")
                
                remaining_weight = Decimal("40")
                remaining_targets = sorted_targets[1:]
                
                if remaining_targets:
                    equal_weight = remaining_weight / len(remaining_targets)
                    for target_id, _ in remaining_targets:
                        recommended_allocations[target_id] = equal_weight
            
            return OptimizationResult(
                strategy=OptimizationStrategy.DRAWDOWN_CONTROL,
                recommended_allocations=recommended_allocations,
                expected_return=Decimal("10"),  # Conservative return
                expected_risk=Decimal("5"),  # Low risk
                confidence_score=Decimal("0.9"),
                optimization_time=0.0,
                metadata={"best_drawdown_control": sorted_targets[:3]}
            )
            
        except Exception as e:
            logger.error(f"Failed to optimize drawdown control: {e}")
            return self._create_empty_result(OptimizationStrategy.DRAWDOWN_CONTROL, str(e))
    
    async def _optimize_diversification(self, allocations: List[Dict[str, Any]], constraints: Optional[Dict[str, Any]]) -> OptimizationResult:
        """Optimize for diversification"""
        try:
            # Equal weight allocation for maximum diversification
            active_allocations = [alloc for alloc in allocations if alloc.get("is_active", False)]
            
            if not active_allocations:
                return self._create_empty_result(OptimizationStrategy.DIVERSIFICATION, "No active allocations")
            
            equal_weight = Decimal("100") / len(active_allocations)
            recommended_allocations = {}
            
            for allocation in active_allocations:
                target_id = allocation.get("target_id", "")
                recommended_allocations[target_id] = equal_weight
            
            # Calculate expected metrics (average of all allocations)
            total_return = Decimal("0")
            total_risk = Decimal("0")
            
            for allocation in active_allocations:
                allocated = Decimal(str(allocation.get("allocated_amount_usd", 0)))
                current = Decimal(str(allocation.get("current_value_usd", 0)))
                
                if allocated > 0:
                    roi = ((current - allocated) / allocated) * 100
                    total_return += roi
            
            expected_return = total_return / len(active_allocations) if active_allocations else Decimal("0")
            expected_risk = Decimal("8")  # Diversified portfolio typically has lower risk
            
            return OptimizationResult(
                strategy=OptimizationStrategy.DIVERSIFICATION,
                recommended_allocations=recommended_allocations,
                expected_return=expected_return,
                expected_risk=expected_risk,
                confidence_score=Decimal("0.7"),
                optimization_time=0.0,
                metadata={"diversification_targets": len(active_allocations)}
            )
            
        except Exception as e:
            logger.error(f"Failed to optimize diversification: {e}")
            return self._create_empty_result(OptimizationStrategy.DIVERSIFICATION, str(e))
    
    async def _optimize_adaptive_allocation(self, allocations: List[Dict[str, Any]], constraints: Optional[Dict[str, Any]]) -> OptimizationResult:
        """Optimize using adaptive allocation based on recent performance"""
        try:
            # Combine multiple factors for adaptive allocation
            adaptive_scores = {}
            
            for allocation in allocations:
                if allocation.get("is_active", False):
                    target_id = allocation.get("target_id", "")
                    allocated = Decimal(str(allocation.get("allocated_amount_usd", 0)))
                    current = Decimal(str(allocation.get("current_value_usd", 0)))
                    max_drawdown = Decimal(str(allocation.get("max_drawdown", 1)))
                    
                    if allocated > 0:
                        # Multi-factor score
                        roi = ((current - allocated) / allocated) * 100
                        risk_adjusted_return = roi / max_drawdown if max_drawdown > 0 else roi
                        
                        # Momentum factor (simplified)
                        momentum_score = roi * Decimal("0.3")  # 30% weight on recent performance
                        risk_score = risk_adjusted_return * Decimal("0.7")  # 70% weight on risk-adjusted return
                        
                        adaptive_score = float(momentum_score + risk_score)
                        adaptive_scores[target_id] = adaptive_score
            
            # Sort by adaptive score (descending)
            sorted_targets = sorted(adaptive_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Dynamic allocation based on adaptive scores
            recommended_allocations = {}
            total_positive_score = sum(max(0, score) for _, score in sorted_targets)
            
            if total_positive_score > 0:
                for target_id, score in sorted_targets:
                    if score > 0:
                        weight = (score / total_positive_score) * 100
                        recommended_allocations[target_id] = Decimal(str(weight))
            else:
                # Fallback to equal allocation
                equal_weight = Decimal("100") / len(sorted_targets) if sorted_targets else Decimal("0")
                for target_id, _ in sorted_targets:
                    recommended_allocations[target_id] = equal_weight
            
            # Calculate expected metrics
            expected_return = Decimal("15")  # Adaptive strategies typically aim higher
            expected_risk = Decimal("12")
            
            return OptimizationResult(
                strategy=OptimizationStrategy.ADAPTIVE_ALLOCATION,
                recommended_allocations=recommended_allocations,
                expected_return=expected_return,
                expected_risk=expected_risk,
                confidence_score=Decimal("0.75"),
                optimization_time=0.0,
                metadata={"adaptive_scores": sorted_targets[:5]}
            )
            
        except Exception as e:
            logger.error(f"Failed to optimize adaptive allocation: {e}")
            return self._create_empty_result(OptimizationStrategy.ADAPTIVE_ALLOCATION, str(e))
    
    def _create_empty_result(self, strategy: OptimizationStrategy, error_message: str) -> OptimizationResult:
        """Create empty optimization result for error cases"""
        return OptimizationResult(
            strategy=strategy,
            recommended_allocations={},
            expected_return=Decimal("0"),
            expected_risk=Decimal("0"),
            confidence_score=Decimal("0"),
            optimization_time=0.0,
            metadata={"error": error_message}
        )
    
    def _create_empty_metrics(self) -> PerformanceMetrics:
        """Create empty performance metrics"""
        return PerformanceMetrics(
            total_return=Decimal("0"),
            volatility=Decimal("0"),
            sharpe_ratio=Decimal("0"),
            max_drawdown=Decimal("0"),
            win_rate=Decimal("0"),
            profit_factor=Decimal("0"),
            sortino_ratio=Decimal("0"),
            calmar_ratio=Decimal("0"),
            information_ratio=Decimal("0"),
            tracking_error=Decimal("0")
        )
    
    async def analyze_rebalancing_opportunity(self, current_allocations: Dict[str, Decimal], target_allocations: Dict[str, Decimal]) -> Dict[str, Any]:
        """Analyze if rebalancing is needed"""
        try:
            rebalancing_needed = False
            rebalancing_actions = []
            total_drift = Decimal("0")
            
            # Calculate allocation drift
            for target_id in set(current_allocations.keys()) | set(target_allocations.keys()):
                current = current_allocations.get(target_id, Decimal("0"))
                target = target_allocations.get(target_id, Decimal("0"))
                drift = abs(current - target)
                total_drift += drift
                
                if drift > self.rebalancing_threshold * 100:  # Convert to percentage
                    rebalancing_needed = True
                    rebalancing_actions.append({
                        "target_id": target_id,
                        "current_allocation": float(current),
                        "target_allocation": float(target),
                        "drift": float(drift),
                        "action": "increase" if target > current else "decrease"
                    })
            
            return {
                "rebalancing_needed": rebalancing_needed,
                "total_drift": float(total_drift),
                "rebalancing_threshold": float(self.rebalancing_threshold * 100),
                "rebalancing_actions": rebalancing_actions,
                "estimated_improvement": float(total_drift * Decimal("0.1"))  # Estimated return improvement
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze rebalancing opportunity: {e}")
            return {"error": str(e)}
    
    async def get_optimization_recommendations(self, wallet_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get optimization recommendations for multiple strategies"""
        try:
            recommendations = []
            
            strategies = [
                OptimizationStrategy.SHARPE_OPTIMIZATION,
                OptimizationStrategy.PROFIT_MAXIMIZATION,
                OptimizationStrategy.RISK_MINIMIZATION,
                OptimizationStrategy.ADAPTIVE_ALLOCATION
            ]
            
            # Run optimization for each strategy
            for strategy in strategies:
                result = await self.optimize_wallet_allocation(wallet_data, strategy)
                
                recommendations.append({
                    "strategy": strategy.value,
                    "expected_return": float(result.expected_return),
                    "expected_risk": float(result.expected_risk),
                    "confidence_score": float(result.confidence_score),
                    "recommended_allocations": {k: float(v) for k, v in result.recommended_allocations.items()},
                    "optimization_time": result.optimization_time,
                    "metadata": result.metadata
                })
            
            # Sort by confidence score (descending)
            recommendations.sort(key=lambda x: x["confidence_score"], reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {e}")
            return []
    
    def get_optimization_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get optimization history"""
        try:
            history = self.optimization_history[-limit:] if limit else self.optimization_history
            
            return [
                {
                    "strategy": result.strategy.value,
                    "expected_return": float(result.expected_return),
                    "expected_risk": float(result.expected_risk),
                    "confidence_score": float(result.confidence_score),
                    "optimization_time": result.optimization_time,
                    "timestamp": result.metadata.get("timestamp", datetime.now().isoformat())
                }
                for result in history
            ]
            
        except Exception as e:
            logger.error(f"Failed to get optimization history: {e}")
            return []
    
    def get_optimizer_status(self) -> Dict[str, Any]:
        """Get optimizer status and configuration"""
        return {
            "service": "wallet_performance_optimizer",
            "status": "active",
            "optimization_window_days": self.optimization_window,
            "rebalancing_threshold": float(self.rebalancing_threshold),
            "risk_tolerance": float(self.risk_tolerance),
            "min_allocation": float(self.min_allocation),
            "max_allocation": float(self.max_allocation),
            "optimization_history_count": len(self.optimization_history),
            "available_strategies": [strategy.value for strategy in OptimizationStrategy],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

# Global optimizer instance
wallet_performance_optimizer = WalletPerformanceOptimizer()