"""
Phase 10: Multi-Agent Portfolio Management Service
Intelligent portfolio construction, optimization, and multi-strategy coordination
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
from collections import defaultdict
from contextlib import asynccontextmanager
import scipy.optimize as optimize

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.trading_strategy_models import (
    TradingStrategy, TradingPosition, PortfolioAllocation, MultiAgentCoordination,
    RiskMetrics, StrategyPerformance, MultiStrategyPortfolioRequest, PositionSide
)
from services.market_analysis_service import get_market_analysis_service
from services.agent_lifecycle_service import get_lifecycle_service
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class Portfolio(BaseModel):
    """Portfolio representation"""
    portfolio_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    
    # Capital allocation
    total_capital: Decimal
    available_capital: Decimal
    allocated_capital: Decimal = Decimal("0")
    
    # Strategy allocation
    strategy_allocations: Dict[str, Decimal] = Field(default_factory=dict)  # strategy_id -> allocation
    strategy_weights: Dict[str, float] = Field(default_factory=dict)        # strategy_id -> weight
    
    # Positions
    positions: Dict[str, TradingPosition] = Field(default_factory=dict)     # position_id -> position
    
    # Performance metrics
    total_value: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    total_return: float = 0.0
    
    # Risk metrics
    risk_metrics: Optional[RiskMetrics] = None
    
    # Configuration
    rebalancing_frequency: str = "daily"
    rebalance_threshold: float = 0.05  # 5%
    max_position_size: float = 0.1     # 10%
    max_strategy_allocation: float = 0.3  # 30%
    
    # Status
    status: str = "active"  # active, paused, liquidating
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_rebalanced: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioOptimizer:
    """Portfolio optimization algorithms"""
    
    @staticmethod
    def mean_variance_optimization(
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        risk_tolerance: float = 0.5
    ) -> np.ndarray:
        """Mean-variance optimization (Markowitz)"""
        n_assets = len(expected_returns)
        
        # Objective function: minimize risk for given return
        def objective(weights):
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_variance = np.dot(weights.T, np.dot(covariance_matrix, weights))
            return portfolio_variance - risk_tolerance * portfolio_return
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0},  # weights sum to 1
        ]
        
        # Bounds (0 to 100% allocation per asset)
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Initial guess (equal weights)
        initial_guess = np.array([1.0 / n_assets] * n_assets)
        
        # Optimize
        result = optimize.minimize(
            objective, initial_guess, method='SLSQP',
            bounds=bounds, constraints=constraints
        )
        
        return result.x if result.success else initial_guess
    
    @staticmethod
    def risk_parity_optimization(covariance_matrix: np.ndarray) -> np.ndarray:
        """Risk parity optimization - equal risk contribution"""
        n_assets = len(covariance_matrix)
        
        def risk_budget_objective(weights, covariance_matrix):
            weights = np.array(weights)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
            marginal_contrib = np.dot(covariance_matrix, weights) / portfolio_vol
            contrib = np.multiply(marginal_contrib, weights)
            return np.sum((contrib - contrib.mean()) ** 2)
        
        # Constraints and bounds
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}]
        bounds = tuple((0.01, 1) for _ in range(n_assets))
        initial_guess = np.array([1.0 / n_assets] * n_assets)
        
        result = optimize.minimize(
            risk_budget_objective, initial_guess, args=(covariance_matrix,),
            method='SLSQP', bounds=bounds, constraints=constraints
        )
        
        return result.x if result.success else initial_guess
    
    @staticmethod
    def black_litterman_optimization(
        market_caps: np.ndarray,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        views: Optional[Dict[int, float]] = None,
        view_confidences: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """Black-Litterman optimization with investor views"""
        # Market capitalization weights (prior)
        w_market = market_caps / np.sum(market_caps)
        
        # Risk aversion parameter
        delta = 3.0
        
        # Implied returns
        pi = delta * np.dot(covariance_matrix, w_market)
        
        if views is None:
            # No views, return market cap weights
            return w_market
        
        # Convert views to matrix form
        P = np.zeros((len(views), len(expected_returns)))
        Q = np.zeros(len(views))
        
        for i, (asset_idx, view_return) in enumerate(views.items()):
            P[i, asset_idx] = 1.0
            Q[i] = view_return
        
        # View uncertainty
        if view_confidences is None:
            tau = 0.025
            omega = tau * np.dot(P, np.dot(covariance_matrix, P.T))
        else:
            omega = np.diag(1.0 / view_confidences)
        
        # Black-Litterman formula
        tau = 0.025
        M1 = np.linalg.inv(tau * covariance_matrix)
        M2 = np.dot(P.T, np.dot(np.linalg.inv(omega), P))
        M3 = np.dot(np.linalg.inv(tau * covariance_matrix), pi)
        M4 = np.dot(P.T, np.dot(np.linalg.inv(omega), Q))
        
        mu_bl = np.dot(np.linalg.inv(M1 + M2), M3 + M4)
        
        # Optimal weights
        w_opt = np.dot(np.linalg.inv(delta * covariance_matrix), mu_bl)
        
        # Normalize weights
        w_opt = w_opt / np.sum(w_opt)
        
        # Ensure non-negative weights
        w_opt = np.maximum(w_opt, 0)
        w_opt = w_opt / np.sum(w_opt)
        
        return w_opt


class PortfolioRebalancer:
    """Portfolio rebalancing logic"""
    
    def __init__(self):
        self.rebalance_costs = 0.001  # 0.1% transaction cost
    
    def should_rebalance(self, portfolio: Portfolio, target_weights: Dict[str, float]) -> bool:
        """Determine if portfolio should be rebalanced"""
        if not portfolio.last_rebalanced:
            return True
        
        # Check time-based rebalancing
        time_since_rebalance = datetime.now(timezone.utc) - portfolio.last_rebalanced
        
        if portfolio.rebalancing_frequency == "daily" and time_since_rebalance.days >= 1:
            return True
        elif portfolio.rebalancing_frequency == "weekly" and time_since_rebalance.days >= 7:
            return True
        elif portfolio.rebalancing_frequency == "monthly" and time_since_rebalance.days >= 30:
            return True
        
        # Check deviation-based rebalancing
        current_weights = self._calculate_current_weights(portfolio)
        
        for strategy_id, target_weight in target_weights.items():
            current_weight = current_weights.get(strategy_id, 0.0)
            if abs(current_weight - target_weight) > portfolio.rebalance_threshold:
                return True
        
        return False
    
    def calculate_rebalance_trades(
        self, 
        portfolio: Portfolio, 
        target_weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Calculate trades needed for rebalancing"""
        trades = []
        
        current_weights = self._calculate_current_weights(portfolio)
        total_value = float(portfolio.total_value)
        
        for strategy_id, target_weight in target_weights.items():
            current_weight = current_weights.get(strategy_id, 0.0)
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > 0.001:  # 0.1% minimum trade size
                trade_value = weight_diff * total_value
                
                trades.append({
                    "strategy_id": strategy_id,
                    "action": "buy" if trade_value > 0 else "sell",
                    "amount": abs(trade_value),
                    "current_weight": current_weight,
                    "target_weight": target_weight,
                    "weight_change": weight_diff
                })
        
        return trades
    
    def _calculate_current_weights(self, portfolio: Portfolio) -> Dict[str, float]:
        """Calculate current strategy weights in portfolio"""
        if portfolio.total_value == 0:
            return {}
        
        weights = {}
        total_value = float(portfolio.total_value)
        
        # Group positions by strategy
        strategy_values = defaultdict(float)
        for position in portfolio.positions.values():
            if position.status == "open":
                position_value = float(position.quantity * (position.current_price or position.entry_price))
                strategy_values[position.strategy_id] += position_value
        
        # Calculate weights
        for strategy_id, value in strategy_values.items():
            weights[strategy_id] = value / total_value
        
        return weights


class PortfolioManagerService:
    """
    Multi-agent portfolio management service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
        # Portfolio storage
        self.portfolios: Dict[str, Portfolio] = {}
        self.portfolio_allocations: Dict[str, PortfolioAllocation] = {}
        
        # Optimization engines
        self.optimizer = PortfolioOptimizer()
        self.rebalancer = PortfolioRebalancer()
        
        # Performance tracking
        self.performance_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.rebalance_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Configuration
        self.portfolio_update_interval = 300  # 5 minutes
        self.rebalance_check_interval = 3600  # 1 hour
        self.performance_calc_interval = 86400  # 24 hours
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the portfolio management service"""
        try:
            logger.info("Initializing Portfolio Management Service...")
            
            # Load existing portfolios
            await self._load_portfolios()
            
            # Load portfolio allocations
            await self._load_portfolio_allocations()
            
            # Start background tasks
            asyncio.create_task(self._portfolio_update_loop())
            asyncio.create_task(self._rebalancing_loop())
            asyncio.create_task(self._performance_calculation_loop())
            
            logger.info("Portfolio Management Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Portfolio Management Service: {e}")
            raise
    
    async def create_portfolio(self, request: MultiStrategyPortfolioRequest) -> Portfolio:
        """Create a new multi-strategy portfolio"""
        try:
            logger.info(f"Creating portfolio: {request.portfolio_name}")
            
            # Validate strategies exist
            valid_strategies = []
            for strategy_id in request.strategies:
                strategy = await self._get_strategy_by_id(strategy_id)
                if strategy:
                    valid_strategies.append(strategy_id)
                else:
                    logger.warning(f"Strategy {strategy_id} not found")
            
            if not valid_strategies:
                raise HTTPException(status_code=400, detail="No valid strategies provided")
            
            # Create portfolio
            portfolio = Portfolio(
                name=request.portfolio_name,
                total_capital=request.initial_capital,
                available_capital=request.initial_capital,
                rebalancing_frequency=request.rebalancing_frequency,
                max_position_size=request.max_position_size,
                max_strategy_allocation=request.max_sector_exposure
            )
            
            # Calculate initial allocation
            if request.allocation_method == "equal_weight":
                weight_per_strategy = 1.0 / len(valid_strategies)
                for strategy_id in valid_strategies:
                    portfolio.strategy_weights[strategy_id] = weight_per_strategy
                    portfolio.strategy_allocations[strategy_id] = request.initial_capital * Decimal(str(weight_per_strategy))
            
            elif request.allocation_method == "risk_parity":
                # Calculate risk parity weights
                weights = await self._calculate_risk_parity_weights(valid_strategies)
                for i, strategy_id in enumerate(valid_strategies):
                    weight = weights[i] if i < len(weights) else 1.0 / len(valid_strategies)
                    portfolio.strategy_weights[strategy_id] = weight
                    portfolio.strategy_allocations[strategy_id] = request.initial_capital * Decimal(str(weight))
            
            elif request.allocation_method == "optimization":
                # Use mean-variance optimization
                weights = await self._calculate_optimized_weights(valid_strategies)
                for i, strategy_id in enumerate(valid_strategies):
                    weight = weights[i] if i < len(weights) else 1.0 / len(valid_strategies)
                    portfolio.strategy_weights[strategy_id] = weight
                    portfolio.strategy_allocations[strategy_id] = request.initial_capital * Decimal(str(weight))
            
            # Update allocated capital
            portfolio.allocated_capital = sum(portfolio.strategy_allocations.values())
            portfolio.available_capital = portfolio.total_capital - portfolio.allocated_capital
            portfolio.total_value = portfolio.total_capital
            
            # Store portfolio
            self.portfolios[portfolio.portfolio_id] = portfolio
            
            # Create portfolio allocation record
            allocation = PortfolioAllocation(
                portfolio_id=portfolio.portfolio_id,
                strategy_allocations={k: float(v) for k, v in portfolio.strategy_allocations.items()},
                max_single_position=request.max_position_size,
                max_sector_exposure=request.max_sector_exposure,
                rebalance_frequency=request.rebalancing_frequency
            )
            
            self.portfolio_allocations[portfolio.portfolio_id] = allocation
            
            # Save to database
            await self._save_portfolio_to_database(portfolio)
            await self._save_allocation_to_database(allocation)
            
            # Setup multi-agent coordination if enabled
            if request.enable_signal_coordination:
                await self._setup_signal_coordination(portfolio, valid_strategies, request.conflict_resolution)
            
            logger.info(f"Portfolio {portfolio.portfolio_id} created successfully")
            return portfolio
            
        except Exception as e:
            logger.error(f"Failed to create portfolio: {e}")
            raise HTTPException(status_code=500, detail=f"Portfolio creation failed: {str(e)}")
    
    async def add_position(self, portfolio_id: str, position: TradingPosition) -> bool:
        """Add a new position to portfolio"""
        try:
            portfolio = self.portfolios.get(portfolio_id)
            if not portfolio:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            # Validate position size
            position_value = float(position.quantity * position.entry_price)
            max_position_value = float(portfolio.total_value) * portfolio.max_position_size
            
            if position_value > max_position_value:
                logger.warning(f"Position size {position_value} exceeds maximum {max_position_value}")
                return False
            
            # Check strategy allocation
            strategy_current_value = sum(
                float(pos.quantity * (pos.current_price or pos.entry_price))
                for pos in portfolio.positions.values()
                if pos.strategy_id == position.strategy_id and pos.status == "open"
            )
            
            strategy_target_allocation = portfolio.strategy_allocations.get(position.strategy_id, Decimal("0"))
            
            if strategy_current_value + position_value > float(strategy_target_allocation) * 1.1:  # 10% tolerance
                logger.warning(f"Position would exceed strategy allocation")
                return False
            
            # Add position
            portfolio.positions[position.position_id] = position
            
            # Update portfolio metrics
            await self._update_portfolio_value(portfolio)
            
            # Save to database
            await self._save_position_to_database(position)
            await self._update_portfolio_in_database(portfolio)
            
            logger.info(f"Position {position.position_id} added to portfolio {portfolio_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add position to portfolio {portfolio_id}: {e}")
            return False
    
    async def close_position(self, portfolio_id: str, position_id: str, exit_price: Decimal) -> bool:
        """Close a position in portfolio"""
        try:
            portfolio = self.portfolios.get(portfolio_id)
            if not portfolio:
                return False
            
            position = portfolio.positions.get(position_id)
            if not position:
                return False
            
            # Calculate P&L
            if position.side == PositionSide.LONG:
                pnl = (exit_price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - exit_price) * position.quantity
            
            # Update position
            position.status = "closed"
            position.closed_at = datetime.now(timezone.utc)
            position.realized_pnl = pnl
            position.current_price = exit_price
            
            # Update portfolio
            portfolio.realized_pnl += pnl
            await self._update_portfolio_value(portfolio)
            
            # Save to database
            await self._update_position_in_database(position)
            await self._update_portfolio_in_database(portfolio)
            
            logger.info(f"Position {position_id} closed with P&L: {pnl}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {e}")
            return False
    
    async def rebalance_portfolio(self, portfolio_id: str) -> Dict[str, Any]:
        """Rebalance portfolio to target allocations"""
        try:
            portfolio = self.portfolios.get(portfolio_id)
            if not portfolio:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            logger.info(f"Rebalancing portfolio {portfolio_id}")
            
            # Get target weights
            target_weights = portfolio.strategy_weights
            
            # Check if rebalancing is needed
            if not self.rebalancer.should_rebalance(portfolio, target_weights):
                return {"status": "no_rebalancing_needed", "portfolio_id": portfolio_id}
            
            # Calculate rebalance trades
            trades = self.rebalancer.calculate_rebalance_trades(portfolio, target_weights)
            
            if not trades:
                return {"status": "no_trades_needed", "portfolio_id": portfolio_id}
            
            # Execute rebalancing (simplified - would integrate with execution service)
            executed_trades = []
            for trade in trades:
                # This would execute actual trades through the trading execution service
                executed_trades.append({
                    "strategy_id": trade["strategy_id"],
                    "action": trade["action"],
                    "amount": trade["amount"],
                    "executed_at": datetime.now(timezone.utc).isoformat()
                })
            
            # Update portfolio
            portfolio.last_rebalanced = datetime.now(timezone.utc)
            
            # Record rebalancing
            rebalance_record = {
                "portfolio_id": portfolio_id,
                "rebalanced_at": portfolio.last_rebalanced.isoformat(),
                "trades": executed_trades,
                "target_weights": target_weights,
                "reason": "scheduled_rebalance"
            }
            
            self.rebalance_history[portfolio_id].append(rebalance_record)
            
            # Save to database
            await self._update_portfolio_in_database(portfolio)
            
            logger.info(f"Portfolio {portfolio_id} rebalanced with {len(executed_trades)} trades")
            
            return {
                "status": "rebalanced",
                "portfolio_id": portfolio_id,
                "trades_executed": len(executed_trades),
                "trades": executed_trades
            }
            
        except Exception as e:
            logger.error(f"Failed to rebalance portfolio {portfolio_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_portfolio_analytics(self, portfolio_id: str) -> Dict[str, Any]:
        """Get comprehensive portfolio analytics"""
        try:
            portfolio = self.portfolios.get(portfolio_id)
            if not portfolio:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            # Update portfolio value
            await self._update_portfolio_value(portfolio)
            
            # Calculate performance metrics
            performance_metrics = await self._calculate_portfolio_performance(portfolio)
            
            # Calculate risk metrics
            risk_metrics = await self._calculate_portfolio_risk(portfolio)
            
            # Get position summary
            position_summary = self._get_position_summary(portfolio)
            
            # Get strategy allocation breakdown
            allocation_breakdown = self._get_allocation_breakdown(portfolio)
            
            return {
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.name,
                "total_value": float(portfolio.total_value),
                "total_capital": float(portfolio.total_capital),
                "available_capital": float(portfolio.available_capital),
                "allocated_capital": float(portfolio.allocated_capital),
                "unrealized_pnl": float(portfolio.unrealized_pnl),
                "realized_pnl": float(portfolio.realized_pnl),
                "total_return": portfolio.total_return,
                "performance_metrics": performance_metrics,
                "risk_metrics": risk_metrics,
                "position_summary": position_summary,
                "allocation_breakdown": allocation_breakdown,
                "last_rebalanced": portfolio.last_rebalanced.isoformat() if portfolio.last_rebalanced else None,
                "status": portfolio.status,
                "created_at": portfolio.created_at.isoformat(),
                "last_updated": portfolio.last_updated.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio analytics for {portfolio_id}: {e}")
            return {"error": str(e)}
    
    async def optimize_portfolio_allocation(self, portfolio_id: str, method: str = "mean_variance") -> Dict[str, float]:
        """Optimize portfolio allocation using specified method"""
        try:
            portfolio = self.portfolios.get(portfolio_id)
            if not portfolio:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            strategy_ids = list(portfolio.strategy_weights.keys())
            
            if method == "risk_parity":
                optimal_weights = await self._calculate_risk_parity_weights(strategy_ids)
            elif method == "mean_variance":
                optimal_weights = await self._calculate_optimized_weights(strategy_ids)
            elif method == "equal_weight":
                optimal_weights = [1.0 / len(strategy_ids)] * len(strategy_ids)
            else:
                raise HTTPException(status_code=400, detail="Invalid optimization method")
            
            # Convert to dictionary
            optimized_allocation = {}
            for i, strategy_id in enumerate(strategy_ids):
                weight = optimal_weights[i] if i < len(optimal_weights) else 0.0
                optimized_allocation[strategy_id] = weight
            
            return optimized_allocation
            
        except Exception as e:
            logger.error(f"Failed to optimize portfolio allocation: {e}")
            return {}
    
    # Background service loops
    
    async def _portfolio_update_loop(self):
        """Portfolio value and metrics update loop"""
        while not self._shutdown:
            try:
                for portfolio_id, portfolio in self.portfolios.items():
                    await self._update_portfolio_value(portfolio)
                    await self._update_portfolio_in_database(portfolio)
                
                await asyncio.sleep(self.portfolio_update_interval)
                
            except Exception as e:
                logger.error(f"Error in portfolio update loop: {e}")
                await asyncio.sleep(self.portfolio_update_interval)
    
    async def _rebalancing_loop(self):
        """Portfolio rebalancing check loop"""
        while not self._shutdown:
            try:
                for portfolio_id in list(self.portfolios.keys()):
                    await self.rebalance_portfolio(portfolio_id)
                
                await asyncio.sleep(self.rebalance_check_interval)
                
            except Exception as e:
                logger.error(f"Error in rebalancing loop: {e}")
                await asyncio.sleep(self.rebalance_check_interval)
    
    async def _performance_calculation_loop(self):
        """Portfolio performance calculation loop"""
        while not self._shutdown:
            try:
                for portfolio_id, portfolio in self.portfolios.items():
                    performance = await self._calculate_portfolio_performance(portfolio)
                    self.performance_history[portfolio_id].append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "performance": performance
                    })
                    
                    # Keep only last 365 days of performance data
                    if len(self.performance_history[portfolio_id]) > 365:
                        self.performance_history[portfolio_id] = self.performance_history[portfolio_id][-365:]
                
                await asyncio.sleep(self.performance_calc_interval)
                
            except Exception as e:
                logger.error(f"Error in performance calculation loop: {e}")
                await asyncio.sleep(self.performance_calc_interval)
    
    # Helper methods
    
    async def _update_portfolio_value(self, portfolio: Portfolio):
        """Update portfolio total value and P&L"""
        total_value = Decimal("0")
        unrealized_pnl = Decimal("0")
        
        # Sum up all positions
        for position in portfolio.positions.values():
            if position.status == "open":
                current_price = position.current_price or position.entry_price
                position_value = position.quantity * current_price
                total_value += position_value
                
                # Calculate unrealized P&L
                if position.side == PositionSide.LONG:
                    unrealized_pnl += (current_price - position.entry_price) * position.quantity
                else:
                    unrealized_pnl += (position.entry_price - current_price) * position.quantity
        
        # Add available capital
        total_value += portfolio.available_capital
        
        # Update portfolio
        portfolio.total_value = total_value
        portfolio.unrealized_pnl = unrealized_pnl
        portfolio.total_return = float((total_value - portfolio.total_capital) / portfolio.total_capital * 100)
        portfolio.last_updated = datetime.now(timezone.utc)
    
    # Additional helper methods would be implemented here...
    
    async def _get_strategy_by_id(self, strategy_id: str):
        """Get strategy from database"""
        # Implementation would load from Supabase
        return None
    
    async def _calculate_risk_parity_weights(self, strategy_ids: List[str]) -> List[float]:
        """Calculate risk parity weights for strategies"""
        # Simplified implementation - would use real covariance matrix
        n_strategies = len(strategy_ids)
        return [1.0 / n_strategies] * n_strategies
    
    async def _calculate_optimized_weights(self, strategy_ids: List[str]) -> List[float]:
        """Calculate optimized weights using mean-variance optimization"""
        # Simplified implementation - would use real expected returns and covariance
        n_strategies = len(strategy_ids)
        return [1.0 / n_strategies] * n_strategies
    
    # Additional methods continue here...


# Global service instance
_portfolio_management_service: Optional[PortfolioManagerService] = None


async def get_portfolio_management_service() -> PortfolioManagerService:
    """Get the global portfolio management service instance"""
    global _portfolio_management_service
    
    if _portfolio_management_service is None:
        _portfolio_management_service = PortfolioManagerService()
        await _portfolio_management_service.initialize()
    
    return _portfolio_management_service


@asynccontextmanager
async def portfolio_management_context():
    """Context manager for portfolio management service"""
    service = await get_portfolio_management_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass