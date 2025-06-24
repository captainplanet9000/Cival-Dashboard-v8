"""
Fund Allocation Service - Advanced Allocation Algorithms
Implements sophisticated fund allocation strategies for optimal performance
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from core.database_manager import DatabaseManager
from models.database_models import (
    FarmDB, GoalDB, FundAllocationDB, WalletTransactionDB, 
    AgentFarmAssignmentDB, FarmGoalAssignmentDB
)
from services.wallet_hierarchy_service import AllocationMethod, WalletHierarchyService


class RiskProfile(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


@dataclass
class AllocationTarget:
    """Represents a potential allocation target with metrics"""
    target_id: str
    target_type: str  # 'farm', 'agent', 'goal'
    name: str
    current_allocation: Decimal
    performance_score: float
    risk_score: float
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    win_rate: Optional[float]
    volatility: Optional[float]
    correlation_score: float = 0.0
    capacity_remaining: Decimal = Decimal('1000000')  # Default large capacity


@dataclass
class AllocationRecommendation:
    """Recommendation for fund allocation"""
    target_id: str
    target_type: str
    name: str
    recommended_amount: Decimal
    confidence_score: float
    reasoning: str
    risk_assessment: str
    expected_return: Optional[float] = None


@dataclass
class PortfolioOptimizationResult:
    """Result from portfolio optimization"""
    allocations: List[AllocationRecommendation]
    total_allocation: Decimal
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    diversification_score: float
    optimization_method: str


class FundAllocationService:
    """
    Advanced fund allocation service with multiple optimization strategies
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.wallet_service = WalletHierarchyService(db_manager)
    
    async def get_allocation_targets(
        self, 
        master_wallet_id: str,
        include_farms: bool = True,
        include_agents: bool = True,
        include_goals: bool = True
    ) -> List[AllocationTarget]:
        """Get all potential allocation targets with performance metrics"""
        
        targets = []
        
        async with self.db_manager.get_session() as session:
            if include_farms:
                farms = await self._get_farm_targets(session, master_wallet_id)
                targets.extend(farms)
            
            if include_agents:
                agents = await self._get_agent_targets(session, master_wallet_id)
                targets.extend(agents)
            
            if include_goals:
                goals = await self._get_goal_targets(session, master_wallet_id)
                targets.extend(goals)
        
        # Calculate correlation scores between targets
        await self._calculate_correlation_scores(targets)
        
        return targets
    
    async def optimize_portfolio(
        self,
        master_wallet_id: str,
        total_allocation: Decimal,
        risk_profile: RiskProfile = RiskProfile.MODERATE,
        optimization_method: str = "modern_portfolio_theory",
        constraints: Dict[str, Any] = None
    ) -> PortfolioOptimizationResult:
        """
        Optimize portfolio allocation using various methods
        """
        
        # Get all allocation targets
        targets = await self.get_allocation_targets(master_wallet_id)
        
        if not targets:
            raise ValueError("No allocation targets available")
        
        # Apply constraints
        constraints = constraints or {}
        targets = self._apply_constraints(targets, constraints)
        
        # Choose optimization method
        if optimization_method == "modern_portfolio_theory":
            return await self._optimize_modern_portfolio_theory(
                targets, total_allocation, risk_profile
            )
        elif optimization_method == "risk_parity":
            return await self._optimize_risk_parity(
                targets, total_allocation, risk_profile
            )
        elif optimization_method == "momentum_based":
            return await self._optimize_momentum_based(
                targets, total_allocation, risk_profile
            )
        elif optimization_method == "kelly_criterion":
            return await self._optimize_kelly_criterion(
                targets, total_allocation, risk_profile
            )
        else:
            raise ValueError(f"Unknown optimization method: {optimization_method}")
    
    async def performance_based_allocation(
        self,
        master_wallet_id: str,
        total_allocation: Decimal,
        lookback_days: int = 30,
        min_allocation: Decimal = Decimal('100'),
        max_allocation_pct: float = 0.4
    ) -> List[AllocationRecommendation]:
        """
        Allocate funds based on historical performance
        """
        
        targets = await self.get_allocation_targets(master_wallet_id)
        
        # Filter targets with sufficient history
        performance_targets = [
            t for t in targets 
            if t.performance_score is not None and t.performance_score > -0.5  # Not terrible
        ]
        
        if not performance_targets:
            # Fallback to equal weight if no performance data
            return await self._equal_weight_allocation(targets, total_allocation)
        
        # Sort by performance score (higher is better)
        performance_targets.sort(key=lambda x: x.performance_score, reverse=True)
        
        recommendations = []
        remaining_allocation = total_allocation
        max_single_allocation = total_allocation * Decimal(str(max_allocation_pct))
        
        # Calculate performance-weighted allocations
        total_performance = sum(max(0, t.performance_score) for t in performance_targets)
        
        if total_performance <= 0:
            return await self._equal_weight_allocation(performance_targets, total_allocation)
        
        for target in performance_targets:
            if remaining_allocation <= min_allocation:
                break
            
            # Calculate allocation based on performance weight
            performance_weight = max(0, target.performance_score) / total_performance
            allocation_amount = min(
                max_single_allocation,
                remaining_allocation * Decimal(str(performance_weight))
            )
            allocation_amount = max(min_allocation, allocation_amount)
            
            if allocation_amount > remaining_allocation:
                allocation_amount = remaining_allocation
            
            confidence = min(0.9, target.performance_score + 0.5) if target.performance_score >= 0 else 0.3
            
            recommendations.append(AllocationRecommendation(
                target_id=target.target_id,
                target_type=target.target_type,
                name=target.name,
                recommended_amount=allocation_amount,
                confidence_score=confidence,
                reasoning=f"Performance score: {target.performance_score:.3f}, outperforming average",
                risk_assessment=self._assess_risk_level(target),
                expected_return=target.performance_score * 0.1  # Conservative estimate
            ))
            
            remaining_allocation -= allocation_amount
        
        return recommendations
    
    async def risk_adjusted_allocation(
        self,
        master_wallet_id: str,
        total_allocation: Decimal,
        target_risk: float = 0.15,
        risk_tolerance: float = 0.05
    ) -> List[AllocationRecommendation]:
        """
        Allocate funds based on risk-adjusted returns (Sharpe ratio optimization)
        """
        
        targets = await self.get_allocation_targets(master_wallet_id)
        
        # Filter targets with Sharpe ratio data
        risk_targets = [
            t for t in targets 
            if t.sharpe_ratio is not None and t.sharpe_ratio > 0
        ]
        
        if not risk_targets:
            return await self.performance_based_allocation(master_wallet_id, total_allocation)
        
        # Sort by Sharpe ratio (higher is better)
        risk_targets.sort(key=lambda x: x.sharpe_ratio, reverse=True)
        
        recommendations = []
        remaining_allocation = total_allocation
        
        # Calculate risk budget allocation
        total_risk_budget = target_risk
        allocated_risk = 0.0
        
        for target in risk_targets:
            if remaining_allocation <= Decimal('100') or allocated_risk >= total_risk_budget:
                break
            
            # Calculate risk contribution
            target_volatility = target.volatility or 0.2  # Default 20% volatility
            max_allocation_for_risk = min(
                remaining_allocation,
                total_allocation * Decimal(str((total_risk_budget - allocated_risk) / target_volatility))
            )
            
            # Weight by Sharpe ratio
            sharpe_weight = target.sharpe_ratio / sum(t.sharpe_ratio for t in risk_targets[:5])  # Top 5
            allocation_amount = min(
                max_allocation_for_risk,
                total_allocation * Decimal(str(sharpe_weight * 0.8))  # Max 80% based on Sharpe
            )
            
            if allocation_amount >= Decimal('100'):
                confidence = min(0.95, 0.5 + target.sharpe_ratio * 0.2)
                
                recommendations.append(AllocationRecommendation(
                    target_id=target.target_id,
                    target_type=target.target_type,
                    name=target.name,
                    recommended_amount=allocation_amount,
                    confidence_score=confidence,
                    reasoning=f"Sharpe ratio: {target.sharpe_ratio:.2f}, excellent risk-adjusted returns",
                    risk_assessment=f"Volatility: {target_volatility:.1%}, Risk score: {target.risk_score:.2f}",
                    expected_return=target.sharpe_ratio * target_volatility
                ))
                
                remaining_allocation -= allocation_amount
                allocated_risk += float(allocation_amount / total_allocation) * target_volatility
        
        return recommendations
    
    async def diversified_allocation(
        self,
        master_wallet_id: str,
        total_allocation: Decimal,
        max_correlation: float = 0.6,
        min_targets: int = 3
    ) -> List[AllocationRecommendation]:
        """
        Create a diversified allocation minimizing correlation between targets
        """
        
        targets = await self.get_allocation_targets(master_wallet_id)
        
        if len(targets) < min_targets:
            return await self._equal_weight_allocation(targets, total_allocation)
        
        # Select diversified targets using correlation matrix
        selected_targets = self._select_diversified_targets(targets, max_correlation, min_targets)
        
        recommendations = []
        allocation_per_target = total_allocation / len(selected_targets)
        
        for target in selected_targets:
            # Adjust allocation based on capacity and performance
            capacity_factor = min(1.0, float(target.capacity_remaining / allocation_per_target))
            performance_factor = max(0.5, 1.0 + target.performance_score * 0.3)
            
            adjusted_allocation = allocation_per_target * Decimal(str(capacity_factor * performance_factor))
            
            recommendations.append(AllocationRecommendation(
                target_id=target.target_id,
                target_type=target.target_type,
                name=target.name,
                recommended_amount=adjusted_allocation,
                confidence_score=0.8,  # High confidence in diversification
                reasoning=f"Diversification target, correlation < {max_correlation}",
                risk_assessment=f"Diversified portfolio component, risk score: {target.risk_score:.2f}",
                expected_return=target.performance_score * 0.08
            ))
        
        # Normalize to total allocation
        total_recommended = sum(r.recommended_amount for r in recommendations)
        if total_recommended != total_allocation:
            scale_factor = total_allocation / total_recommended
            for rec in recommendations:
                rec.recommended_amount *= scale_factor
        
        return recommendations
    
    async def _get_farm_targets(self, session: Session, master_wallet_id: str) -> List[AllocationTarget]:
        """Get farm allocation targets with performance metrics"""
        
        farms = session.query(FarmDB).filter(FarmDB.is_active == True).all()
        targets = []
        
        for farm in farms:
            # Get current allocation
            current_allocation = session.query(func.sum(FundAllocationDB.current_value_usd)).filter(
                and_(
                    FundAllocationDB.source_wallet_id == master_wallet_id,
                    FundAllocationDB.target_type == "farm",
                    FundAllocationDB.target_id == str(farm.farm_id),
                    FundAllocationDB.is_active == True
                )
            ).scalar() or Decimal('0')
            
            # Calculate performance metrics
            performance_metrics = farm.performance_metrics or {}
            performance_score = performance_metrics.get('performance_score', 0.0)
            risk_score = self._calculate_risk_score(performance_metrics)
            
            targets.append(AllocationTarget(
                target_id=str(farm.farm_id),
                target_type="farm",
                name=farm.name,
                current_allocation=current_allocation,
                performance_score=performance_score,
                risk_score=risk_score,
                sharpe_ratio=performance_metrics.get('sharpe_ratio'),
                max_drawdown=performance_metrics.get('max_drawdown'),
                win_rate=performance_metrics.get('win_rate'),
                volatility=performance_metrics.get('volatility'),
                capacity_remaining=Decimal(str(performance_metrics.get('capacity_usd', 100000)))
            ))
        
        return targets
    
    async def _get_agent_targets(self, session: Session, master_wallet_id: str) -> List[AllocationTarget]:
        """Get agent allocation targets (simplified for now)"""
        
        # Get agents assigned to farms
        agent_assignments = session.query(AgentFarmAssignmentDB).filter(
            AgentFarmAssignmentDB.is_active == True
        ).all()
        
        targets = []
        agent_ids_seen = set()
        
        for assignment in agent_assignments:
            if assignment.agent_id in agent_ids_seen:
                continue
            agent_ids_seen.add(assignment.agent_id)
            
            # Get current allocation
            current_allocation = session.query(func.sum(FundAllocationDB.current_value_usd)).filter(
                and_(
                    FundAllocationDB.source_wallet_id == master_wallet_id,
                    FundAllocationDB.target_type == "agent",
                    FundAllocationDB.target_id == assignment.agent_id,
                    FundAllocationDB.is_active == True
                )
            ).scalar() or Decimal('0')
            
            # Use assignment performance data
            performance_contribution = assignment.performance_contribution or {}
            performance_score = performance_contribution.get('pnl_ratio', 0.0)
            
            targets.append(AllocationTarget(
                target_id=assignment.agent_id,
                target_type="agent",
                name=f"Agent {assignment.agent_id[:8]}",
                current_allocation=current_allocation,
                performance_score=performance_score,
                risk_score=0.5,  # Default moderate risk
                capacity_remaining=Decimal('50000')  # Smaller capacity for individual agents
            ))
        
        return targets
    
    async def _get_goal_targets(self, session: Session, master_wallet_id: str) -> List[AllocationTarget]:
        """Get goal allocation targets"""
        
        goals = session.query(GoalDB).filter(
            and_(
                GoalDB.completion_status == "active",
                GoalDB.is_active == True
            )
        ).all()
        
        targets = []
        
        for goal in goals:
            # Get current allocation
            current_allocation = session.query(func.sum(FundAllocationDB.current_value_usd)).filter(
                and_(
                    FundAllocationDB.source_wallet_id == master_wallet_id,
                    FundAllocationDB.target_type == "goal",
                    FundAllocationDB.target_id == str(goal.goal_id),
                    FundAllocationDB.is_active == True
                )
            ).scalar() or Decimal('0')
            
            # Calculate goal attractiveness based on progress and type
            progress = goal.completion_percentage or 0
            progress_score = min(1.0, (100 - progress) / 100)  # Higher score for less complete goals
            
            # Adjust score based on goal type
            type_multiplier = {
                'profit_target': 1.2,
                'trade_volume': 1.0,
                'strategy_performance': 1.1
            }.get(goal.goal_type, 1.0)
            
            performance_score = progress_score * type_multiplier
            risk_score = 0.3 if goal.goal_type == 'profit_target' else 0.5
            
            targets.append(AllocationTarget(
                target_id=str(goal.goal_id),
                target_type="goal",
                name=goal.name,
                current_allocation=current_allocation,
                performance_score=performance_score,
                risk_score=risk_score,
                capacity_remaining=Decimal(str(goal.wallet_allocation_usd or 25000))
            ))
        
        return targets
    
    def _calculate_risk_score(self, performance_metrics: Dict) -> float:
        """Calculate risk score from performance metrics"""
        
        max_drawdown = performance_metrics.get('max_drawdown', 0.1)
        volatility = performance_metrics.get('volatility', 0.2)
        win_rate = performance_metrics.get('win_rate', 0.5)
        
        # Higher risk score = higher risk
        risk_score = (max_drawdown * 0.4 + volatility * 0.4 + (1 - win_rate) * 0.2)
        return min(1.0, max(0.0, risk_score))
    
    def _assess_risk_level(self, target: AllocationTarget) -> str:
        """Assess risk level as human-readable string"""
        
        if target.risk_score <= 0.3:
            return "Low Risk"
        elif target.risk_score <= 0.6:
            return "Moderate Risk"
        else:
            return "High Risk"
    
    async def _equal_weight_allocation(
        self, 
        targets: List[AllocationTarget], 
        total_allocation: Decimal
    ) -> List[AllocationRecommendation]:
        """Fallback equal weight allocation"""
        
        if not targets:
            return []
        
        allocation_per_target = total_allocation / len(targets)
        
        return [
            AllocationRecommendation(
                target_id=target.target_id,
                target_type=target.target_type,
                name=target.name,
                recommended_amount=allocation_per_target,
                confidence_score=0.5,
                reasoning="Equal weight allocation (fallback)",
                risk_assessment=self._assess_risk_level(target)
            )
            for target in targets
        ]
    
    def _apply_constraints(
        self, 
        targets: List[AllocationTarget], 
        constraints: Dict[str, Any]
    ) -> List[AllocationTarget]:
        """Apply allocation constraints to filter targets"""
        
        filtered = targets.copy()
        
        # Minimum performance constraint
        min_performance = constraints.get('min_performance_score')
        if min_performance is not None:
            filtered = [t for t in filtered if t.performance_score >= min_performance]
        
        # Maximum risk constraint
        max_risk = constraints.get('max_risk_score')
        if max_risk is not None:
            filtered = [t for t in filtered if t.risk_score <= max_risk]
        
        # Target type filters
        allowed_types = constraints.get('allowed_target_types')
        if allowed_types:
            filtered = [t for t in filtered if t.target_type in allowed_types]
        
        # Capacity constraints
        min_capacity = constraints.get('min_capacity_usd')
        if min_capacity is not None:
            filtered = [t for t in filtered if t.capacity_remaining >= Decimal(str(min_capacity))]
        
        return filtered
    
    async def _calculate_correlation_scores(self, targets: List[AllocationTarget]):
        """Calculate correlation scores between targets (simplified)"""
        
        # This is a simplified correlation calculation
        # In a real system, you'd calculate actual correlation based on historical returns
        
        for i, target1 in enumerate(targets):
            correlations = []
            
            for j, target2 in enumerate(targets):
                if i == j:
                    continue
                
                # Simple correlation based on target type and performance similarity
                type_correlation = 0.3 if target1.target_type == target2.target_type else 0.1
                performance_correlation = abs(target1.performance_score - target2.performance_score) * 0.2
                
                correlation = min(0.9, type_correlation + performance_correlation)
                correlations.append(correlation)
            
            target1.correlation_score = sum(correlations) / len(correlations) if correlations else 0.0
    
    def _select_diversified_targets(
        self, 
        targets: List[AllocationTarget], 
        max_correlation: float, 
        min_targets: int
    ) -> List[AllocationTarget]:
        """Select targets for diversified portfolio"""
        
        # Start with best performing target
        targets_sorted = sorted(targets, key=lambda x: x.performance_score, reverse=True)
        selected = [targets_sorted[0]]
        
        # Add targets with low correlation to selected ones
        for target in targets_sorted[1:]:
            if len(selected) >= min_targets:
                # Check if we have enough diversity
                avg_correlation = sum(t.correlation_score for t in selected) / len(selected)
                if avg_correlation <= max_correlation:
                    break
            
            # Check correlation with all selected targets
            max_corr_with_selected = max(
                (abs(target.performance_score - s.performance_score) * 0.5 + 
                 (0.3 if target.target_type == s.target_type else 0.1))
                for s in selected
            )
            
            if max_corr_with_selected <= max_correlation or len(selected) < min_targets:
                selected.append(target)
        
        return selected
    
    # Advanced optimization methods (simplified implementations)
    
    async def _optimize_modern_portfolio_theory(
        self, 
        targets: List[AllocationTarget], 
        total_allocation: Decimal, 
        risk_profile: RiskProfile
    ) -> PortfolioOptimizationResult:
        """Simplified Modern Portfolio Theory optimization"""
        
        # Risk tolerance based on profile
        risk_tolerance = {
            RiskProfile.CONSERVATIVE: 0.1,
            RiskProfile.MODERATE: 0.15,
            RiskProfile.AGGRESSIVE: 0.25,
            RiskProfile.CUSTOM: 0.2
        }[risk_profile]
        
        allocations = []
        total_risk = 0.0
        total_expected_return = 0.0
        
        # Simple mean-variance optimization (simplified)
        for target in targets:
            expected_return = target.performance_score * 0.1
            risk = target.risk_score * target.risk_score  # Variance approximation
            
            # Weight by risk-adjusted return
            if risk > 0:
                weight = (expected_return / risk) / sum((t.performance_score * 0.1) / (t.risk_score * t.risk_score) for t in targets if t.risk_score > 0)
            else:
                weight = 1.0 / len(targets)
            
            allocation_amount = total_allocation * Decimal(str(weight))
            
            allocations.append(AllocationRecommendation(
                target_id=target.target_id,
                target_type=target.target_type,
                name=target.name,
                recommended_amount=allocation_amount,
                confidence_score=0.8,
                reasoning="Modern Portfolio Theory optimization",
                risk_assessment=self._assess_risk_level(target),
                expected_return=expected_return
            ))
            
            total_risk += weight * risk
            total_expected_return += weight * expected_return
        
        return PortfolioOptimizationResult(
            allocations=allocations,
            total_allocation=total_allocation,
            expected_return=total_expected_return,
            expected_risk=total_risk ** 0.5,
            sharpe_ratio=total_expected_return / (total_risk ** 0.5) if total_risk > 0 else 0.0,
            diversification_score=1.0 - (sum(t.correlation_score for t in targets) / len(targets)),
            optimization_method="modern_portfolio_theory"
        )
    
    async def _optimize_risk_parity(
        self, 
        targets: List[AllocationTarget], 
        total_allocation: Decimal, 
        risk_profile: RiskProfile
    ) -> PortfolioOptimizationResult:
        """Risk parity optimization - equal risk contribution"""
        
        # Calculate risk budgets (equal for risk parity)
        risk_budget_per_target = 1.0 / len(targets)
        
        allocations = []
        total_expected_return = 0.0
        
        for target in targets:
            # Allocation inversely proportional to risk
            if target.risk_score > 0:
                weight = (risk_budget_per_target / target.risk_score) / sum(risk_budget_per_target / t.risk_score for t in targets if t.risk_score > 0)
            else:
                weight = 1.0 / len(targets)
            
            allocation_amount = total_allocation * Decimal(str(weight))
            expected_return = target.performance_score * 0.1
            
            allocations.append(AllocationRecommendation(
                target_id=target.target_id,
                target_type=target.target_type,
                name=target.name,
                recommended_amount=allocation_amount,
                confidence_score=0.75,
                reasoning="Risk parity - equal risk contribution",
                risk_assessment=self._assess_risk_level(target),
                expected_return=expected_return
            ))
            
            total_expected_return += weight * expected_return
        
        # Calculate portfolio risk (simplified)
        portfolio_risk = sum(t.risk_score for t in targets) / len(targets)
        
        return PortfolioOptimizationResult(
            allocations=allocations,
            total_allocation=total_allocation,
            expected_return=total_expected_return,
            expected_risk=portfolio_risk,
            sharpe_ratio=total_expected_return / portfolio_risk if portfolio_risk > 0 else 0.0,
            diversification_score=0.9,  # High diversification by design
            optimization_method="risk_parity"
        )
    
    async def _optimize_momentum_based(
        self, 
        targets: List[AllocationTarget], 
        total_allocation: Decimal, 
        risk_profile: RiskProfile
    ) -> PortfolioOptimizationResult:
        """Momentum-based allocation - favor recent winners"""
        
        # Sort by performance (momentum)
        momentum_targets = sorted(targets, key=lambda x: x.performance_score, reverse=True)
        
        allocations = []
        total_expected_return = 0.0
        
        # Exponential weighting for momentum
        momentum_weights = []
        for i, target in enumerate(momentum_targets):
            weight = np.exp(-i * 0.5)  # Exponential decay
            momentum_weights.append(weight)
        
        total_momentum_weight = sum(momentum_weights)
        
        for i, target in enumerate(momentum_targets):
            weight = momentum_weights[i] / total_momentum_weight
            allocation_amount = total_allocation * Decimal(str(weight))
            expected_return = target.performance_score * 0.15  # Higher return expectation for momentum
            
            allocations.append(AllocationRecommendation(
                target_id=target.target_id,
                target_type=target.target_type,
                name=target.name,
                recommended_amount=allocation_amount,
                confidence_score=0.7,
                reasoning=f"Momentum strategy - rank #{i+1} performer",
                risk_assessment=self._assess_risk_level(target),
                expected_return=expected_return
            ))
            
            total_expected_return += weight * expected_return
        
        # Higher expected risk for momentum strategy
        portfolio_risk = sum(t.risk_score for t in targets) / len(targets) * 1.2
        
        return PortfolioOptimizationResult(
            allocations=allocations,
            total_allocation=total_allocation,
            expected_return=total_expected_return,
            expected_risk=portfolio_risk,
            sharpe_ratio=total_expected_return / portfolio_risk if portfolio_risk > 0 else 0.0,
            diversification_score=0.6,  # Lower diversification (momentum concentration)
            optimization_method="momentum_based"
        )
    
    async def _optimize_kelly_criterion(
        self, 
        targets: List[AllocationTarget], 
        total_allocation: Decimal, 
        risk_profile: RiskProfile
    ) -> PortfolioOptimizationResult:
        """Kelly criterion optimization for optimal bet sizing"""
        
        allocations = []
        total_expected_return = 0.0
        kelly_weights = []
        
        for target in targets:
            # Simplified Kelly fraction calculation
            win_rate = target.win_rate or 0.6  # Default 60% win rate
            avg_win = target.performance_score * 0.2 if target.performance_score > 0 else 0.1
            avg_loss = abs(target.performance_score * 0.1) if target.performance_score < 0 else 0.05
            
            if avg_loss > 0:
                kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
                kelly_fraction = max(0, min(0.25, kelly_fraction))  # Cap at 25%
            else:
                kelly_fraction = 0.1  # Default small allocation
            
            kelly_weights.append(kelly_fraction)
        
        # Normalize weights
        total_kelly_weight = sum(kelly_weights) if sum(kelly_weights) > 0 else 1.0
        
        for i, target in enumerate(targets):
            weight = kelly_weights[i] / total_kelly_weight
            allocation_amount = total_allocation * Decimal(str(weight))
            expected_return = target.performance_score * 0.12
            
            allocations.append(AllocationRecommendation(
                target_id=target.target_id,
                target_type=target.target_type,
                name=target.name,
                recommended_amount=allocation_amount,
                confidence_score=0.85,
                reasoning=f"Kelly criterion - optimal bet size: {kelly_weights[i]:.2%}",
                risk_assessment=self._assess_risk_level(target),
                expected_return=expected_return
            ))
            
            total_expected_return += weight * expected_return
        
        portfolio_risk = sum(w * t.risk_score for w, t in zip(kelly_weights, targets)) / total_kelly_weight
        
        return PortfolioOptimizationResult(
            allocations=allocations,
            total_allocation=total_allocation,
            expected_return=total_expected_return,
            expected_risk=portfolio_risk,
            sharpe_ratio=total_expected_return / portfolio_risk if portfolio_risk > 0 else 0.0,
            diversification_score=0.8,
            optimization_method="kelly_criterion"
        )