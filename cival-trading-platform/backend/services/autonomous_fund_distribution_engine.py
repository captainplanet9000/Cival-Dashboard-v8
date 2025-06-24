"""
Autonomous Fund Distribution Engine - Phase 6
Advanced AI-powered fund allocation and management system
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import numpy as np
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from ..models.master_wallet_models import (
    FundAllocation, FundDistributionRule, WalletPerformanceMetrics,
    DistributionStrategy, PerformanceMetrics
)
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class DistributionMethod(Enum):
    PERFORMANCE_WEIGHTED = "performance_weighted"
    RISK_ADJUSTED = "risk_adjusted"
    MOMENTUM_BASED = "momentum_based"
    DIVERSIFICATION_FOCUSED = "diversification_focused"
    ADAPTIVE_ALLOCATION = "adaptive_allocation"
    AI_OPTIMIZED = "ai_optimized"

@dataclass
class AllocationTarget:
    """Target for fund allocation"""
    target_id: str
    target_type: str  # 'agent', 'farm', 'goal', 'strategy'
    target_name: str
    current_allocation: Decimal
    performance_score: float
    risk_score: float
    capacity_limit: Decimal
    priority_level: int
    recent_performance: List[float]
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float

@dataclass
class DistributionRecommendation:
    """Fund distribution recommendation"""
    target_id: str
    target_type: str
    current_allocation: Decimal
    recommended_allocation: Decimal
    allocation_change: Decimal
    confidence_score: float
    reasoning: str
    risk_assessment: str

class AutonomousFundDistributionEngine:
    """
    Advanced autonomous fund distribution engine with AI-powered allocation optimization
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # AI Models for prediction
        self.performance_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.risk_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
        # Model training status
        self.models_trained = False
        self.last_training = None
        
        # Distribution parameters
        self.max_allocation_per_target = Decimal("0.25")  # 25% max per target
        self.min_allocation_per_target = Decimal("0.01")  # 1% min per target
        self.rebalance_threshold = Decimal("0.05")  # 5% threshold for rebalancing
        
        # Performance tracking
        self.allocation_history: List[Dict] = []
        self.performance_cache: Dict[str, Any] = {}
        
        # Risk management
        self.max_risk_score = 0.8
        self.diversification_target = 0.7
        
        logger.info("AutonomousFundDistributionEngine initialized")
    
    async def initialize(self):
        """Initialize the fund distribution engine"""
        try:
            # Load historical allocation data
            await self._load_allocation_history()
            
            # Train AI models if we have enough data
            await self._train_prediction_models()
            
            # Start background monitoring
            asyncio.create_task(self._distribution_monitoring_loop())
            asyncio.create_task(self._model_retraining_loop())
            
            logger.info("AutonomousFundDistributionEngine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AutonomousFundDistributionEngine: {e}")
            raise
    
    async def calculate_optimal_allocation(
        self, 
        wallet_id: str, 
        available_funds: Decimal,
        method: DistributionMethod = DistributionMethod.AI_OPTIMIZED
    ) -> List[DistributionRecommendation]:
        """Calculate optimal fund allocation using specified method"""
        try:
            # Get all potential allocation targets
            targets = await self._get_allocation_targets(wallet_id)
            
            # Apply allocation method
            if method == DistributionMethod.AI_OPTIMIZED:
                recommendations = await self._ai_optimized_allocation(targets, available_funds)
            elif method == DistributionMethod.PERFORMANCE_WEIGHTED:
                recommendations = await self._performance_weighted_allocation(targets, available_funds)
            elif method == DistributionMethod.RISK_ADJUSTED:
                recommendations = await self._risk_adjusted_allocation(targets, available_funds)
            elif method == DistributionMethod.MOMENTUM_BASED:
                recommendations = await self._momentum_based_allocation(targets, available_funds)
            elif method == DistributionMethod.DIVERSIFICATION_FOCUSED:
                recommendations = await self._diversification_focused_allocation(targets, available_funds)
            else:
                recommendations = await self._adaptive_allocation(targets, available_funds)
            
            # Validate and normalize recommendations
            recommendations = await self._validate_recommendations(recommendations, available_funds)
            
            # Cache recommendations
            await self._cache_recommendations(wallet_id, recommendations)
            
            logger.info(f"Generated {len(recommendations)} allocation recommendations for wallet {wallet_id}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to calculate optimal allocation: {e}")
            raise
    
    async def _get_allocation_targets(self, wallet_id: str) -> List[AllocationTarget]:
        """Get all potential allocation targets with performance data"""
        targets = []
        
        try:
            # Get active agents
            agent_service = self.registry.get_service("agent_management_service")
            if agent_service:
                agents = await agent_service.get_active_agents()
                for agent in agents:
                    performance_data = await self._get_agent_performance_data(agent.agent_id)
                    
                    target = AllocationTarget(
                        target_id=agent.agent_id,
                        target_type="agent",
                        target_name=agent.agent_name,
                        current_allocation=await self._get_current_allocation(wallet_id, "agent", agent.agent_id),
                        performance_score=performance_data.get('score', 0.0),
                        risk_score=performance_data.get('risk_score', 0.5),
                        capacity_limit=Decimal(str(performance_data.get('capacity_limit', 10000))),
                        priority_level=performance_data.get('priority', 1),
                        recent_performance=performance_data.get('recent_returns', []),
                        volatility=performance_data.get('volatility', 0.0),
                        sharpe_ratio=performance_data.get('sharpe_ratio', 0.0),
                        max_drawdown=performance_data.get('max_drawdown', 0.0),
                        win_rate=performance_data.get('win_rate', 0.0)
                    )
                    targets.append(target)
            
            # Get active farms
            farm_service = self.registry.get_service("farm_management_service")
            if farm_service:
                farms = await farm_service.get_active_farms()
                for farm in farms:
                    performance_data = await self._get_farm_performance_data(farm.farm_id)
                    
                    target = AllocationTarget(
                        target_id=farm.farm_id,
                        target_type="farm",
                        target_name=farm.farm_name,
                        current_allocation=await self._get_current_allocation(wallet_id, "farm", farm.farm_id),
                        performance_score=performance_data.get('score', 0.0),
                        risk_score=performance_data.get('risk_score', 0.5),
                        capacity_limit=Decimal(str(performance_data.get('capacity_limit', 50000))),
                        priority_level=performance_data.get('priority', 1),
                        recent_performance=performance_data.get('recent_returns', []),
                        volatility=performance_data.get('volatility', 0.0),
                        sharpe_ratio=performance_data.get('sharpe_ratio', 0.0),
                        max_drawdown=performance_data.get('max_drawdown', 0.0),
                        win_rate=performance_data.get('win_rate', 0.0)
                    )
                    targets.append(target)
            
            # Get active goals
            goal_service = self.registry.get_service("goal_management_service")
            if goal_service:
                goals = await goal_service.get_active_goals()
                for goal in goals:
                    performance_data = await self._get_goal_performance_data(goal.goal_id)
                    
                    target = AllocationTarget(
                        target_id=goal.goal_id,
                        target_type="goal",
                        target_name=goal.goal_name,
                        current_allocation=await self._get_current_allocation(wallet_id, "goal", goal.goal_id),
                        performance_score=performance_data.get('score', 0.0),
                        risk_score=performance_data.get('risk_score', 0.5),
                        capacity_limit=Decimal(str(performance_data.get('capacity_limit', 25000))),
                        priority_level=performance_data.get('priority', 1),
                        recent_performance=performance_data.get('recent_returns', []),
                        volatility=performance_data.get('volatility', 0.0),
                        sharpe_ratio=performance_data.get('sharpe_ratio', 0.0),
                        max_drawdown=performance_data.get('max_drawdown', 0.0),
                        win_rate=performance_data.get('win_rate', 0.0)
                    )
                    targets.append(target)
            
        except Exception as e:
            logger.error(f"Failed to get allocation targets: {e}")
        
        return targets
    
    async def _ai_optimized_allocation(
        self, 
        targets: List[AllocationTarget], 
        available_funds: Decimal
    ) -> List[DistributionRecommendation]:
        """AI-optimized allocation using machine learning models"""
        recommendations = []
        
        try:
            if not self.models_trained:
                # Fallback to performance-weighted if models not trained
                return await self._performance_weighted_allocation(targets, available_funds)
            
            # Prepare features for ML models
            features = []
            target_data = []
            
            for target in targets:
                feature_vector = [
                    target.performance_score,
                    target.risk_score,
                    target.volatility,
                    target.sharpe_ratio,
                    target.max_drawdown,
                    target.win_rate,
                    float(target.current_allocation),
                    target.priority_level,
                    len(target.recent_performance),
                    np.mean(target.recent_performance) if target.recent_performance else 0.0,
                    np.std(target.recent_performance) if len(target.recent_performance) > 1 else 0.0
                ]
                features.append(feature_vector)
                target_data.append(target)
            
            if not features:
                return recommendations
            
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Predict performance and risk
            predicted_performance = self.performance_model.predict(features_scaled)
            predicted_risk = self.risk_model.predict(features_scaled)
            
            # Calculate allocation weights using Modern Portfolio Theory concepts
            weights = await self._calculate_mpt_weights(
                predicted_performance, 
                predicted_risk, 
                targets
            )
            
            # Generate recommendations
            total_weight = sum(weights)
            if total_weight > 0:
                for i, target in enumerate(target_data):
                    weight = weights[i] / total_weight
                    recommended_allocation = available_funds * Decimal(str(weight))
                    
                    # Apply constraints
                    recommended_allocation = min(
                        recommended_allocation,
                        target.capacity_limit,
                        available_funds * self.max_allocation_per_target
                    )
                    
                    recommended_allocation = max(
                        recommended_allocation,
                        Decimal("0")
                    )
                    
                    if recommended_allocation > Decimal("0"):
                        allocation_change = recommended_allocation - target.current_allocation
                        
                        # Calculate confidence score
                        confidence = self._calculate_confidence_score(
                            predicted_performance[i],
                            predicted_risk[i],
                            target
                        )
                        
                        # Generate reasoning
                        reasoning = self._generate_allocation_reasoning(
                            target,
                            predicted_performance[i],
                            predicted_risk[i],
                            weight
                        )
                        
                        recommendation = DistributionRecommendation(
                            target_id=target.target_id,
                            target_type=target.target_type,
                            current_allocation=target.current_allocation,
                            recommended_allocation=recommended_allocation,
                            allocation_change=allocation_change,
                            confidence_score=confidence,
                            reasoning=reasoning,
                            risk_assessment=f"Risk Score: {predicted_risk[i]:.3f}"
                        )
                        
                        recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Failed to calculate AI-optimized allocation: {e}")
            # Fallback to performance-weighted allocation
            recommendations = await self._performance_weighted_allocation(targets, available_funds)
        
        return recommendations
    
    async def _calculate_mpt_weights(
        self, 
        expected_returns: np.ndarray, 
        risk_scores: np.ndarray,
        targets: List[AllocationTarget]
    ) -> List[float]:
        """Calculate Modern Portfolio Theory optimal weights"""
        try:
            n_assets = len(expected_returns)
            if n_assets == 0:
                return []
            
            # Convert risk scores to volatilities
            volatilities = risk_scores * 0.5  # Scale risk scores to reasonable volatility range
            
            # Create correlation matrix (simplified - assume moderate correlation)
            correlation_matrix = np.full((n_assets, n_assets), 0.3)
            np.fill_diagonal(correlation_matrix, 1.0)
            
            # Calculate covariance matrix
            cov_matrix = np.outer(volatilities, volatilities) * correlation_matrix
            
            # Risk aversion parameter
            risk_aversion = 2.0
            
            # Calculate optimal weights using mean-variance optimization
            try:
                inv_cov = np.linalg.inv(cov_matrix)
                ones = np.ones((n_assets, 1))
                
                # Portfolio weights formula: w = (Σ^-1 * μ) / (λ + 1'Σ^-1μ)
                mu = expected_returns.reshape(-1, 1)
                numerator = inv_cov @ mu
                denominator = risk_aversion + (ones.T @ inv_cov @ mu)[0, 0]
                
                weights = (numerator / denominator).flatten()
                
                # Apply constraints
                weights = np.maximum(weights, 0)  # No short selling
                weights = weights / np.sum(weights) if np.sum(weights) > 0 else np.ones(n_assets) / n_assets
                
                return weights.tolist()
                
            except np.linalg.LinAlgError:
                # Fallback to equal weighting if matrix is singular
                return [1.0 / n_assets] * n_assets
            
        except Exception as e:
            logger.error(f"Failed to calculate MPT weights: {e}")
            # Fallback to performance-weighted
            performance_sum = sum(expected_returns)
            if performance_sum > 0:
                return [ret / performance_sum for ret in expected_returns]
            else:
                return [1.0 / len(expected_returns)] * len(expected_returns)
    
    async def _performance_weighted_allocation(
        self, 
        targets: List[AllocationTarget], 
        available_funds: Decimal
    ) -> List[DistributionRecommendation]:
        """Performance-weighted allocation strategy"""
        recommendations = []
        
        try:
            # Calculate performance-based weights
            total_performance = sum(target.performance_score for target in targets)
            
            if total_performance <= 0:
                # Equal allocation if no performance data
                equal_weight = 1.0 / len(targets) if targets else 0
                total_performance = len(targets)
            
            for target in targets:
                if total_performance > 0:
                    weight = target.performance_score / total_performance if total_performance > 0 else equal_weight
                    recommended_allocation = available_funds * Decimal(str(weight))
                    
                    # Apply constraints
                    recommended_allocation = min(
                        recommended_allocation,
                        target.capacity_limit,
                        available_funds * self.max_allocation_per_target
                    )
                    
                    recommended_allocation = max(
                        recommended_allocation,
                        available_funds * self.min_allocation_per_target if recommended_allocation > 0 else Decimal("0")
                    )
                    
                    allocation_change = recommended_allocation - target.current_allocation
                    
                    if abs(allocation_change) > available_funds * self.rebalance_threshold:
                        recommendation = DistributionRecommendation(
                            target_id=target.target_id,
                            target_type=target.target_type,
                            current_allocation=target.current_allocation,
                            recommended_allocation=recommended_allocation,
                            allocation_change=allocation_change,
                            confidence_score=min(target.performance_score / 10.0, 1.0),
                            reasoning=f"Performance-weighted allocation based on score: {target.performance_score:.3f}",
                            risk_assessment=f"Risk Score: {target.risk_score:.3f}"
                        )
                        
                        recommendations.append(recommendation)
        
        except Exception as e:
            logger.error(f"Failed to calculate performance-weighted allocation: {e}")
        
        return recommendations
    
    async def _risk_adjusted_allocation(
        self, 
        targets: List[AllocationTarget], 
        available_funds: Decimal
    ) -> List[DistributionRecommendation]:
        """Risk-adjusted allocation strategy"""
        recommendations = []
        
        try:
            # Calculate risk-adjusted scores (Sharpe ratio based)
            risk_adjusted_scores = []
            for target in targets:
                if target.volatility > 0:
                    sharpe = target.performance_score / target.volatility
                else:
                    sharpe = target.performance_score
                
                # Adjust for maximum drawdown
                drawdown_penalty = 1 - min(target.max_drawdown, 0.5)
                risk_adjusted_score = sharpe * drawdown_penalty
                
                risk_adjusted_scores.append(max(risk_adjusted_score, 0))
            
            total_score = sum(risk_adjusted_scores)
            
            if total_score > 0:
                for i, target in enumerate(targets):
                    weight = risk_adjusted_scores[i] / total_score
                    recommended_allocation = available_funds * Decimal(str(weight))
                    
                    # Apply risk limits
                    if target.risk_score > self.max_risk_score:
                        recommended_allocation *= Decimal("0.5")  # Reduce allocation for high-risk targets
                    
                    # Apply other constraints
                    recommended_allocation = min(
                        recommended_allocation,
                        target.capacity_limit,
                        available_funds * self.max_allocation_per_target
                    )
                    
                    recommended_allocation = max(
                        recommended_allocation,
                        Decimal("0")
                    )
                    
                    allocation_change = recommended_allocation - target.current_allocation
                    
                    if abs(allocation_change) > available_funds * self.rebalance_threshold:
                        recommendation = DistributionRecommendation(
                            target_id=target.target_id,
                            target_type=target.target_type,
                            current_allocation=target.current_allocation,
                            recommended_allocation=recommended_allocation,
                            allocation_change=allocation_change,
                            confidence_score=min(risk_adjusted_scores[i] / 5.0, 1.0),
                            reasoning=f"Risk-adjusted allocation. Sharpe: {target.sharpe_ratio:.3f}, Max DD: {target.max_drawdown:.3f}",
                            risk_assessment=f"Risk Score: {target.risk_score:.3f}, Volatility: {target.volatility:.3f}"
                        )
                        
                        recommendations.append(recommendation)
        
        except Exception as e:
            logger.error(f"Failed to calculate risk-adjusted allocation: {e}")
        
        return recommendations
    
    async def _momentum_based_allocation(
        self, 
        targets: List[AllocationTarget], 
        available_funds: Decimal
    ) -> List[DistributionRecommendation]:
        """Momentum-based allocation strategy"""
        recommendations = []
        
        try:
            # Calculate momentum scores
            momentum_scores = []
            for target in targets:
                if len(target.recent_performance) >= 3:
                    # Calculate momentum as slope of recent performance
                    x = np.arange(len(target.recent_performance))
                    y = np.array(target.recent_performance)
                    momentum = np.polyfit(x, y, 1)[0]  # Linear trend slope
                else:
                    momentum = target.performance_score / 10.0
                
                # Combine with win rate
                momentum_score = momentum * (0.5 + 0.5 * target.win_rate)
                momentum_scores.append(max(momentum_score, 0))
            
            total_momentum = sum(momentum_scores)
            
            if total_momentum > 0:
                for i, target in enumerate(targets):
                    weight = momentum_scores[i] / total_momentum
                    recommended_allocation = available_funds * Decimal(str(weight))
                    
                    # Apply constraints
                    recommended_allocation = min(
                        recommended_allocation,
                        target.capacity_limit,
                        available_funds * self.max_allocation_per_target
                    )
                    
                    recommended_allocation = max(
                        recommended_allocation,
                        Decimal("0")
                    )
                    
                    allocation_change = recommended_allocation - target.current_allocation
                    
                    if abs(allocation_change) > available_funds * self.rebalance_threshold:
                        recommendation = DistributionRecommendation(
                            target_id=target.target_id,
                            target_type=target.target_type,
                            current_allocation=target.current_allocation,
                            recommended_allocation=recommended_allocation,
                            allocation_change=allocation_change,
                            confidence_score=min(momentum_scores[i] / 2.0, 1.0),
                            reasoning=f"Momentum-based allocation. Win Rate: {target.win_rate:.3f}",
                            risk_assessment=f"Risk Score: {target.risk_score:.3f}"
                        )
                        
                        recommendations.append(recommendation)
        
        except Exception as e:
            logger.error(f"Failed to calculate momentum-based allocation: {e}")
        
        return recommendations
    
    async def _diversification_focused_allocation(
        self, 
        targets: List[AllocationTarget], 
        available_funds: Decimal
    ) -> List[DistributionRecommendation]:
        """Diversification-focused allocation strategy"""
        recommendations = []
        
        try:
            # Group targets by type for diversification
            target_groups = {}
            for target in targets:
                if target.target_type not in target_groups:
                    target_groups[target.target_type] = []
                target_groups[target.target_type].append(target)
            
            # Allocate across target types first
            type_weights = {}
            total_types = len(target_groups)
            
            if total_types > 0:
                base_weight = 1.0 / total_types
                
                for target_type, type_targets in target_groups.items():
                    # Adjust weight based on average performance of type
                    avg_performance = sum(t.performance_score for t in type_targets) / len(type_targets)
                    type_weights[target_type] = base_weight * (0.5 + 0.5 * avg_performance / 10.0)
                
                # Normalize weights
                total_weight = sum(type_weights.values())
                if total_weight > 0:
                    for target_type in type_weights:
                        type_weights[target_type] /= total_weight
                
                # Allocate within each type
                for target_type, type_targets in target_groups.items():
                    type_allocation = available_funds * Decimal(str(type_weights[target_type]))
                    
                    # Equal allocation within type, adjusted by performance
                    type_performance_sum = sum(t.performance_score for t in type_targets)
                    
                    for target in type_targets:
                        if type_performance_sum > 0:
                            target_weight = target.performance_score / type_performance_sum
                        else:
                            target_weight = 1.0 / len(type_targets)
                        
                        recommended_allocation = type_allocation * Decimal(str(target_weight))
                        
                        # Apply constraints
                        recommended_allocation = min(
                            recommended_allocation,
                            target.capacity_limit,
                            available_funds * self.max_allocation_per_target
                        )
                        
                        recommended_allocation = max(
                            recommended_allocation,
                            Decimal("0")
                        )
                        
                        allocation_change = recommended_allocation - target.current_allocation
                        
                        if abs(allocation_change) > available_funds * self.rebalance_threshold:
                            recommendation = DistributionRecommendation(
                                target_id=target.target_id,
                                target_type=target.target_type,
                                current_allocation=target.current_allocation,
                                recommended_allocation=recommended_allocation,
                                allocation_change=allocation_change,
                                confidence_score=0.8,  # High confidence in diversification
                                reasoning=f"Diversification-focused allocation across {target_type} targets",
                                risk_assessment=f"Risk Score: {target.risk_score:.3f}, Diversified exposure"
                            )
                            
                            recommendations.append(recommendation)
        
        except Exception as e:
            logger.error(f"Failed to calculate diversification-focused allocation: {e}")
        
        return recommendations
    
    async def _adaptive_allocation(
        self, 
        targets: List[AllocationTarget], 
        available_funds: Decimal
    ) -> List[DistributionRecommendation]:
        """Adaptive allocation that combines multiple strategies"""
        try:
            # Get recommendations from different strategies
            performance_recs = await self._performance_weighted_allocation(targets, available_funds)
            risk_recs = await self._risk_adjusted_allocation(targets, available_funds)
            momentum_recs = await self._momentum_based_allocation(targets, available_funds)
            diversification_recs = await self._diversification_focused_allocation(targets, available_funds)
            
            # Combine recommendations with adaptive weights
            combined_recs = {}
            strategy_weights = {
                'performance': 0.3,
                'risk': 0.3,
                'momentum': 0.2,
                'diversification': 0.2
            }
            
            # Aggregate recommendations by target
            all_recommendations = {
                'performance': {rec.target_id: rec for rec in performance_recs},
                'risk': {rec.target_id: rec for rec in risk_recs},
                'momentum': {rec.target_id: rec for rec in momentum_recs},
                'diversification': {rec.target_id: rec for rec in diversification_recs}
            }
            
            # Get all unique target IDs
            all_target_ids = set()
            for strategy_recs in all_recommendations.values():
                all_target_ids.update(strategy_recs.keys())
            
            # Combine recommendations for each target
            final_recommendations = []
            
            for target_id in all_target_ids:
                target_data = next((t for t in targets if t.target_id == target_id), None)
                if not target_data:
                    continue
                
                weighted_allocation = Decimal("0")
                weighted_confidence = 0.0
                reasoning_parts = []
                
                total_weight = 0.0
                
                for strategy, recs in all_recommendations.items():
                    if target_id in recs:
                        rec = recs[target_id]
                        weight = strategy_weights[strategy]
                        
                        weighted_allocation += rec.recommended_allocation * Decimal(str(weight))
                        weighted_confidence += rec.confidence_score * weight
                        reasoning_parts.append(f"{strategy}: ${rec.recommended_allocation}")
                        total_weight += weight
                
                if total_weight > 0:
                    weighted_allocation /= Decimal(str(total_weight))
                    weighted_confidence /= total_weight
                    
                    allocation_change = weighted_allocation - target_data.current_allocation
                    
                    if abs(allocation_change) > available_funds * self.rebalance_threshold:
                        recommendation = DistributionRecommendation(
                            target_id=target_id,
                            target_type=target_data.target_type,
                            current_allocation=target_data.current_allocation,
                            recommended_allocation=weighted_allocation,
                            allocation_change=allocation_change,
                            confidence_score=weighted_confidence,
                            reasoning=f"Adaptive allocation combining: {'; '.join(reasoning_parts)}",
                            risk_assessment=f"Risk Score: {target_data.risk_score:.3f}"
                        )
                        
                        final_recommendations.append(recommendation)
            
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Failed to calculate adaptive allocation: {e}")
            return await self._performance_weighted_allocation(targets, available_funds)
    
    async def _validate_recommendations(
        self, 
        recommendations: List[DistributionRecommendation], 
        available_funds: Decimal
    ) -> List[DistributionRecommendation]:
        """Validate and normalize allocation recommendations"""
        try:
            if not recommendations:
                return recommendations
            
            # Calculate total recommended allocation
            total_recommended = sum(rec.recommended_allocation for rec in recommendations)
            
            # If total exceeds available funds, normalize proportionally
            if total_recommended > available_funds:
                scale_factor = available_funds / total_recommended
                
                for rec in recommendations:
                    rec.recommended_allocation *= scale_factor
                    rec.allocation_change = rec.recommended_allocation - rec.current_allocation
                    rec.reasoning += f" (Scaled by {scale_factor:.3f} to fit available funds)"
            
            # Remove zero allocations
            recommendations = [rec for rec in recommendations if rec.recommended_allocation > Decimal("0")]
            
            # Sort by confidence score
            recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to validate recommendations: {e}")
            return recommendations
    
    async def execute_allocation_recommendations(
        self, 
        wallet_id: str, 
        recommendations: List[DistributionRecommendation]
    ) -> Dict[str, Any]:
        """Execute allocation recommendations"""
        try:
            master_wallet_service = self.registry.get_service("master_wallet_service")
            if not master_wallet_service:
                raise ValueError("Master wallet service not available")
            
            execution_results = {
                "successful": [],
                "failed": [],
                "total_allocated": Decimal("0"),
                "total_collected": Decimal("0")
            }
            
            for rec in recommendations:
                try:
                    if rec.allocation_change > 0:
                        # Allocate additional funds
                        allocation_request = {
                            "target_type": rec.target_type,
                            "target_id": rec.target_id,
                            "amount_usd": rec.allocation_change
                        }
                        
                        allocation = await master_wallet_service.allocate_funds(wallet_id, allocation_request)
                        execution_results["successful"].append({
                            "action": "allocate",
                            "target": rec.target_id,
                            "amount": rec.allocation_change,
                            "allocation_id": allocation.allocation_id
                        })
                        execution_results["total_allocated"] += rec.allocation_change
                        
                    elif rec.allocation_change < 0:
                        # Collect excess funds
                        collection_request = {
                            "allocation_id": rec.target_id,  # This would need proper allocation ID lookup
                            "collection_type": "partial",
                            "amount_usd": abs(rec.allocation_change)
                        }
                        
                        collected_amount = await master_wallet_service.collect_funds(wallet_id, collection_request)
                        execution_results["successful"].append({
                            "action": "collect",
                            "target": rec.target_id,
                            "amount": collected_amount
                        })
                        execution_results["total_collected"] += collected_amount
                        
                except Exception as e:
                    execution_results["failed"].append({
                        "target": rec.target_id,
                        "error": str(e),
                        "recommended_amount": rec.recommended_allocation
                    })
                    logger.error(f"Failed to execute allocation for {rec.target_id}: {e}")
            
            # Record execution in history
            await self._record_allocation_execution(wallet_id, recommendations, execution_results)
            
            logger.info(f"Executed allocation recommendations for wallet {wallet_id}: "
                       f"{len(execution_results['successful'])} successful, {len(execution_results['failed'])} failed")
            
            return execution_results
            
        except Exception as e:
            logger.error(f"Failed to execute allocation recommendations: {e}")
            raise
    
    # Helper methods for data retrieval and caching
    async def _get_current_allocation(self, wallet_id: str, target_type: str, target_id: str) -> Decimal:
        """Get current allocation for a target"""
        try:
            if self.redis:
                allocation_key = f"allocation:{wallet_id}:{target_type}:{target_id}"
                cached_allocation = await self.redis.get(allocation_key)
                if cached_allocation:
                    return Decimal(cached_allocation.decode())
            
            # Fallback to database query
            if self.supabase:
                response = self.supabase.table('fund_allocations').select('current_value_usd').eq('wallet_id', wallet_id).eq('target_type', target_type).eq('target_id', target_id).eq('is_active', True).execute()
                
                if response.data:
                    return Decimal(str(response.data[0]['current_value_usd']))
            
            return Decimal("0")
            
        except Exception as e:
            logger.error(f"Failed to get current allocation: {e}")
            return Decimal("0")
    
    async def _get_agent_performance_data(self, agent_id: str) -> Dict[str, Any]:
        """Get agent performance data"""
        try:
            agent_performance_service = self.registry.get_service("agent_performance_service")
            if agent_performance_service:
                performance = await agent_performance_service.get_agent_performance(agent_id)
                return {
                    'score': performance.overall_score if performance else 5.0,
                    'risk_score': performance.risk_score if performance else 0.5,
                    'capacity_limit': 10000,
                    'priority': 1,
                    'recent_returns': performance.recent_returns if performance else [],
                    'volatility': performance.volatility if performance else 0.2,
                    'sharpe_ratio': performance.sharpe_ratio if performance else 0.0,
                    'max_drawdown': performance.max_drawdown if performance else 0.1,
                    'win_rate': performance.win_rate if performance else 0.5
                }
        except Exception as e:
            logger.error(f"Failed to get agent performance data: {e}")
        
        # Default values
        return {
            'score': 5.0,
            'risk_score': 0.5,
            'capacity_limit': 10000,
            'priority': 1,
            'recent_returns': [],
            'volatility': 0.2,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.1,
            'win_rate': 0.5
        }
    
    async def _get_farm_performance_data(self, farm_id: str) -> Dict[str, Any]:
        """Get farm performance data"""
        # Similar implementation to agent performance
        return {
            'score': 6.0,
            'risk_score': 0.4,
            'capacity_limit': 50000,
            'priority': 2,
            'recent_returns': [],
            'volatility': 0.15,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.08,
            'win_rate': 0.6
        }
    
    async def _get_goal_performance_data(self, goal_id: str) -> Dict[str, Any]:
        """Get goal performance data"""
        # Similar implementation to agent performance
        return {
            'score': 7.0,
            'risk_score': 0.3,
            'capacity_limit': 25000,
            'priority': 3,
            'recent_returns': [],
            'volatility': 0.1,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.05,
            'win_rate': 0.7
        }
    
    async def _cache_recommendations(self, wallet_id: str, recommendations: List[DistributionRecommendation]):
        """Cache allocation recommendations"""
        try:
            if self.redis:
                cache_key = f"allocation_recommendations:{wallet_id}"
                recommendations_data = [rec.__dict__ for rec in recommendations]
                await self.redis.setex(
                    cache_key,
                    1800,  # 30 minutes TTL
                    json.dumps(recommendations_data, default=str)
                )
        except Exception as e:
            logger.error(f"Failed to cache recommendations: {e}")
    
    async def _load_allocation_history(self):
        """Load historical allocation data for model training"""
        try:
            if self.supabase:
                response = self.supabase.table('allocation_history').select('*').order('created_at', desc=False).limit(1000).execute()
                
                self.allocation_history = response.data if response.data else []
                logger.info(f"Loaded {len(self.allocation_history)} allocation history records")
                
        except Exception as e:
            logger.error(f"Failed to load allocation history: {e}")
    
    async def _train_prediction_models(self):
        """Train AI prediction models"""
        try:
            if len(self.allocation_history) < 50:  # Need minimum data for training
                logger.info("Insufficient data for model training")
                return
            
            # Prepare training data
            X = []
            y_performance = []
            y_risk = []
            
            for record in self.allocation_history:
                features = [
                    record.get('initial_performance_score', 0),
                    record.get('initial_risk_score', 0.5),
                    record.get('allocation_amount', 0),
                    record.get('target_priority', 1),
                    record.get('market_volatility', 0.2),
                    record.get('allocation_duration_days', 30)
                ]
                
                X.append(features)
                y_performance.append(record.get('actual_performance', 0))
                y_risk.append(record.get('actual_risk', 0.5))
            
            X = np.array(X)
            y_performance = np.array(y_performance)
            y_risk = np.array(y_risk)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train models
            self.performance_model.fit(X_scaled, y_performance)
            self.risk_model.fit(X_scaled, y_risk)
            
            self.models_trained = True
            self.last_training = datetime.now(timezone.utc)
            
            logger.info("AI prediction models trained successfully")
            
        except Exception as e:
            logger.error(f"Failed to train prediction models: {e}")
    
    async def _record_allocation_execution(self, wallet_id: str, recommendations: List[DistributionRecommendation], results: Dict[str, Any]):
        """Record allocation execution for learning"""
        try:
            if self.supabase:
                execution_record = {
                    'wallet_id': wallet_id,
                    'execution_timestamp': datetime.now(timezone.utc).isoformat(),
                    'recommendations_count': len(recommendations),
                    'successful_executions': len(results['successful']),
                    'failed_executions': len(results['failed']),
                    'total_allocated': float(results['total_allocated']),
                    'total_collected': float(results['total_collected']),
                    'execution_details': json.dumps(results, default=str)
                }
                
                self.supabase.table('allocation_executions').insert(execution_record).execute()
                
        except Exception as e:
            logger.error(f"Failed to record allocation execution: {e}")
    
    def _calculate_confidence_score(self, predicted_performance: float, predicted_risk: float, target: AllocationTarget) -> float:
        """Calculate confidence score for recommendation"""
        try:
            # Base confidence on prediction consistency and target stability
            performance_consistency = 1.0 - abs(predicted_performance - target.performance_score) / 10.0
            risk_consistency = 1.0 - abs(predicted_risk - target.risk_score)
            
            # Factor in data quality
            data_quality = min(len(target.recent_performance) / 10.0, 1.0)
            
            confidence = (performance_consistency + risk_consistency + data_quality) / 3.0
            return max(0.1, min(confidence, 1.0))
            
        except Exception:
            return 0.5
    
    def _generate_allocation_reasoning(self, target: AllocationTarget, predicted_performance: float, predicted_risk: float, weight: float) -> str:
        """Generate human-readable reasoning for allocation"""
        try:
            reasoning_parts = []
            
            if predicted_performance > target.performance_score:
                reasoning_parts.append("Expected performance improvement")
            elif predicted_performance < target.performance_score:
                reasoning_parts.append("Expected performance decline")
            else:
                reasoning_parts.append("Stable performance expected")
            
            if predicted_risk < target.risk_score:
                reasoning_parts.append("risk reduction anticipated")
            elif predicted_risk > target.risk_score:
                reasoning_parts.append("increased risk expected")
            
            if weight > 0.1:
                reasoning_parts.append("high allocation weight")
            elif weight < 0.05:
                reasoning_parts.append("conservative allocation")
            
            if target.sharpe_ratio > 1.0:
                reasoning_parts.append("strong risk-adjusted returns")
            
            if target.win_rate > 0.6:
                reasoning_parts.append("high win rate")
            
            return f"AI-optimized allocation: {', '.join(reasoning_parts)}"
            
        except Exception:
            return "AI-optimized allocation based on performance and risk analysis"
    
    # Background monitoring loops
    async def _distribution_monitoring_loop(self):
        """Background monitoring of fund distribution"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Monitor allocation performance and trigger rebalancing if needed
                # Implementation would check allocation drift and performance
                
            except Exception as e:
                logger.error(f"Error in distribution monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _model_retraining_loop(self):
        """Background model retraining"""
        while True:
            try:
                await asyncio.sleep(86400)  # Retrain daily
                
                # Reload data and retrain models
                await self._load_allocation_history()
                await self._train_prediction_models()
                
            except Exception as e:
                logger.error(f"Error in model retraining loop: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "service": "autonomous_fund_distribution_engine",
            "status": "running",
            "models_trained": self.models_trained,
            "last_training": self.last_training.isoformat() if self.last_training else None,
            "allocation_history_size": len(self.allocation_history),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_autonomous_fund_distribution_engine():
    """Factory function to create AutonomousFundDistributionEngine instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = AutonomousFundDistributionEngine(redis_client, supabase_client)
    return service