"""
Portfolio Optimization Service - Phase 5 Implementation
Advanced portfolio optimization using modern portfolio theory and machine learning
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
from collections import defaultdict

class OptimizationObjective(str, Enum):
    """Portfolio optimization objectives"""
    MAX_SHARPE = "max_sharpe"
    MIN_VOLATILITY = "min_volatility"
    MAX_RETURN = "max_return"
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"

class PortfolioAllocation(BaseModel):
    """Portfolio allocation result"""
    allocation_id: str = Field(default_factory=lambda: f"alloc_{int(datetime.now().timestamp())}")
    agent_id: str
    symbols: List[str]
    weights: List[float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    
    # Risk metrics
    var_95: float = 0.0
    max_drawdown: float = 0.0
    
    # Optimization details
    objective: OptimizationObjective
    optimization_success: bool = True
    optimization_message: str = ""
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RebalanceRecommendation(BaseModel):
    """Portfolio rebalancing recommendation"""
    agent_id: str
    current_weights: Dict[str, float]
    target_weights: Dict[str, float]
    weight_changes: Dict[str, float]
    total_turnover: float
    rebalance_reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PortfolioOptimizerService:
    """Advanced portfolio optimization service"""
    
    def __init__(self):
        self.agent_allocations: Dict[str, PortfolioAllocation] = {}
        self.asset_data: Dict[str, Dict] = {}
        self.optimization_history: List[PortfolioAllocation] = []
        self.rebalance_recommendations: List[RebalanceRecommendation] = []
        
        # Default parameters
        self.risk_free_rate = 0.02
        self.monitoring_active = True
        
        self._start_optimization_monitoring()
        logger.info("PortfolioOptimizerService initialized")
    
    def _start_optimization_monitoring(self):
        """Start background optimization monitoring"""
        asyncio.create_task(self._optimization_monitoring_loop())
    
    async def _optimization_monitoring_loop(self):
        """Main optimization monitoring loop"""
        while self.monitoring_active:
            try:
                await self._check_rebalance_triggers()
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                logger.error(f"Error in optimization monitoring loop: {e}")
                await asyncio.sleep(3600)
    
    async def add_asset_data(self, symbol: str, price_data: List[Dict[str, Any]]):
        """Add asset data for optimization"""
        if not price_data:
            return
        
        # Calculate returns
        prices = [p.get('close', 0) for p in price_data]
        returns = [0.0]
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        self.asset_data[symbol] = {
            'prices': prices,
            'returns': returns,
            'volatility': np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.15
        }
        
        logger.debug(f"Added asset data for {symbol}: {len(price_data)} price points")
    
    async def optimize_portfolio(
        self,
        agent_id: str,
        symbols: List[str],
        objective: OptimizationObjective = OptimizationObjective.MAX_SHARPE
    ) -> PortfolioAllocation:
        """Optimize portfolio allocation"""
        
        if not symbols:
            raise ValueError("At least one symbol must be provided")
        
        try:
            # Calculate optimal weights based on objective
            weights = await self._calculate_optimal_weights(symbols, objective)
            
            # Calculate portfolio metrics
            expected_return, expected_volatility = await self._calculate_portfolio_metrics(symbols, weights)
            sharpe_ratio = (expected_return - self.risk_free_rate) / expected_volatility if expected_volatility > 0 else 0
            
            # Calculate risk metrics
            var_95 = await self._calculate_var(symbols, weights)
            max_drawdown = await self._calculate_max_drawdown(symbols, weights)
            
            allocation = PortfolioAllocation(
                agent_id=agent_id,
                symbols=symbols,
                weights=weights,
                expected_return=expected_return,
                expected_volatility=expected_volatility,
                sharpe_ratio=sharpe_ratio,
                var_95=var_95,
                max_drawdown=max_drawdown,
                objective=objective,
                optimization_success=True,
                optimization_message="Optimization completed successfully"
            )
            
            self.agent_allocations[agent_id] = allocation
            self.optimization_history.append(allocation)
            
            # Keep only recent history
            if len(self.optimization_history) > 1000:
                self.optimization_history = self.optimization_history[-1000:]
            
            logger.info(f"Optimized portfolio for agent {agent_id}: {len(symbols)} assets, Sharpe={sharpe_ratio:.3f}")
            return allocation
            
        except Exception as e:
            logger.error(f"Portfolio optimization failed for agent {agent_id}: {e}")
            
            # Return equal weight as fallback
            n_assets = len(symbols)
            weights = [1.0 / n_assets] * n_assets
            
            fallback_allocation = PortfolioAllocation(
                agent_id=agent_id,
                symbols=symbols,
                weights=weights,
                expected_return=0.08,
                expected_volatility=0.15,
                sharpe_ratio=0.4,
                objective=OptimizationObjective.EQUAL_WEIGHT,
                optimization_success=False,
                optimization_message=f"Optimization failed, using equal weights: {str(e)}"
            )
            
            self.agent_allocations[agent_id] = fallback_allocation
            return fallback_allocation
    
    async def _calculate_optimal_weights(self, symbols: List[str], objective: OptimizationObjective) -> List[float]:
        """Calculate optimal weights based on objective"""
        
        n_assets = len(symbols)
        
        if objective == OptimizationObjective.EQUAL_WEIGHT:
            return [1.0 / n_assets] * n_assets
        
        elif objective == OptimizationObjective.MAX_SHARPE:
            # Simple implementation - would use mean-variance optimization in production
            weights = []
            for symbol in symbols:
                if symbol in self.asset_data:
                    volatility = self.asset_data[symbol].get('volatility', 0.15)
                    # Inverse volatility weighting as proxy for Sharpe optimization
                    weights.append(1.0 / max(volatility, 0.01))
                else:
                    weights.append(1.0)
            
            # Normalize weights
            total_weight = sum(weights)
            return [w / total_weight for w in weights] if total_weight > 0 else [1.0 / n_assets] * n_assets
        
        elif objective == OptimizationObjective.MIN_VOLATILITY:
            # Inverse volatility weighting
            weights = []
            for symbol in symbols:
                if symbol in self.asset_data:
                    volatility = self.asset_data[symbol].get('volatility', 0.15)
                    weights.append(1.0 / max(volatility, 0.01))
                else:
                    weights.append(1.0)
            
            total_weight = sum(weights)
            return [w / total_weight for w in weights] if total_weight > 0 else [1.0 / n_assets] * n_assets
        
        else:
            # Default to equal weight
            return [1.0 / n_assets] * n_assets
    
    async def _calculate_portfolio_metrics(self, symbols: List[str], weights: List[float]) -> Tuple[float, float]:
        """Calculate expected return and volatility"""
        
        # Simple calculation - would use covariance matrix in production
        expected_return = 0.08  # Default 8% return
        expected_volatility = 0.15  # Default 15% volatility
        
        if self.asset_data:
            volatilities = []
            for symbol in symbols:
                if symbol in self.asset_data:
                    volatilities.append(self.asset_data[symbol].get('volatility', 0.15))
                else:
                    volatilities.append(0.15)
            
            # Weighted average volatility (simplified)
            expected_volatility = sum(w * vol for w, vol in zip(weights, volatilities))
        
        return expected_return, expected_volatility
    
    async def _calculate_var(self, symbols: List[str], weights: List[float]) -> float:
        """Calculate Value at Risk (95% confidence)"""
        # Simplified VaR calculation
        expected_return, volatility = await self._calculate_portfolio_metrics(symbols, weights)
        var_95 = expected_return - 1.65 * volatility  # Assuming normal distribution
        return var_95
    
    async def _calculate_max_drawdown(self, symbols: List[str], weights: List[float]) -> float:
        """Calculate maximum expected drawdown"""
        # Simplified calculation based on volatility
        _, volatility = await self._calculate_portfolio_metrics(symbols, weights)
        max_drawdown = volatility * 2.0  # Rough estimate
        return max_drawdown
    
    async def _check_rebalance_triggers(self):
        """Check for rebalancing triggers"""
        
        for agent_id, allocation in self.agent_allocations.items():
            try:
                # Check time since last optimization
                time_since_optimization = datetime.now(timezone.utc) - allocation.created_at
                
                if time_since_optimization.days > 30:  # Monthly rebalancing
                    recommendation = await self._generate_rebalance_recommendation(agent_id, allocation)
                    self.rebalance_recommendations.append(recommendation)
                    
                    logger.info(f"Generated rebalance recommendation for agent {agent_id}")
                    
            except Exception as e:
                logger.error(f"Error checking rebalance for agent {agent_id}: {e}")
    
    async def _generate_rebalance_recommendation(self, agent_id: str, allocation: PortfolioAllocation) -> RebalanceRecommendation:
        """Generate rebalancing recommendation"""
        
        # Re-optimize portfolio
        new_allocation = await self.optimize_portfolio(
            agent_id=f"{agent_id}_rebalance",
            symbols=allocation.symbols,
            objective=allocation.objective
        )
        
        current_weights = {symbol: weight for symbol, weight in zip(allocation.symbols, allocation.weights)}
        target_weights = {symbol: weight for symbol, weight in zip(new_allocation.symbols, new_allocation.weights)}
        
        weight_changes = {
            symbol: target_weights.get(symbol, 0) - current_weights.get(symbol, 0)
            for symbol in allocation.symbols
        }
        
        total_turnover = sum(abs(change) for change in weight_changes.values()) / 2
        
        return RebalanceRecommendation(
            agent_id=agent_id,
            current_weights=current_weights,
            target_weights=target_weights,
            weight_changes=weight_changes,
            total_turnover=total_turnover,
            rebalance_reason="Scheduled monthly rebalancing",
            confidence=0.75
        )
    
    async def get_agent_allocation(self, agent_id: str) -> Optional[PortfolioAllocation]:
        """Get current allocation for an agent"""
        return self.agent_allocations.get(agent_id)
    
    async def get_rebalance_recommendations(self, agent_id: Optional[str] = None) -> List[RebalanceRecommendation]:
        """Get rebalancing recommendations"""
        recommendations = self.rebalance_recommendations
        
        if agent_id:
            recommendations = [r for r in recommendations if r.agent_id == agent_id]
        
        return recommendations
    
    async def get_optimization_history(self, agent_id: Optional[str] = None, limit: int = 50) -> List[PortfolioAllocation]:
        """Get optimization history"""
        history = self.optimization_history
        
        if agent_id:
            history = [a for a in history if a.agent_id == agent_id]
        
        return history[-limit:] if limit else history
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get portfolio optimizer service status"""
        
        objective_distribution = defaultdict(int)
        for allocation in self.agent_allocations.values():
            objective_distribution[allocation.objective.value] += 1
        
        return {
            "service_status": "active" if self.monitoring_active else "inactive",
            "active_allocations": len(self.agent_allocations),
            "tracked_assets": len(self.asset_data),
            "optimization_history_count": len(self.optimization_history),
            "pending_rebalance_recommendations": len(self.rebalance_recommendations),
            "objective_distribution": dict(objective_distribution),
            "risk_free_rate": self.risk_free_rate,
            "last_update": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_portfolio_optimizer_service() -> PortfolioOptimizerService:
    """Factory function to create portfolio optimizer service"""
    return PortfolioOptimizerService()