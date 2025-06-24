"""
ML Portfolio Optimizer Service
Provides machine learning-based portfolio optimization and asset allocation
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class MLPortfolioOptimizerService:
    """Service for ML-based portfolio optimization and asset allocation"""
    
    def __init__(self, historical_data_service=None, market_data_service=None):
        self.historical_data_service = historical_data_service
        self.market_data_service = market_data_service
        
        # Optimization models and parameters
        self.optimization_models = {}
        self.risk_models = {}
        self.allocation_cache = {}
        
        # Supported assets and strategies
        self.supported_assets = ['BTC-USD', 'ETH-USD', 'AAPL', 'TSLA', 'SPY', 'QQQ', 'MSFT', 'GOOGL']
        self.optimization_strategies = ['mean_variance', 'risk_parity', 'momentum', 'mean_reversion']
        
        # Configuration
        self.lookback_period = 252  # Trading days
        self.rebalance_frequency = 'weekly'  # weekly, monthly, quarterly
        self.max_position_size = 0.3  # 30% max allocation per asset
        self.min_position_size = 0.01  # 1% min allocation
        
        # Performance tracking
        self.optimization_history = []
        self.performance_metrics = {}
        
    async def optimize_portfolio(
        self, 
        assets: List[str] = None,
        strategy: str = 'mean_variance',
        risk_tolerance: float = 0.5,
        target_return: float = None,
        constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Optimize portfolio allocation using ML algorithms
        
        Args:
            assets: List of assets to include in optimization
            strategy: Optimization strategy ('mean_variance', 'risk_parity', etc.)
            risk_tolerance: Risk tolerance level (0-1, higher = more risk)
            target_return: Target return rate (optional)
            constraints: Additional constraints for optimization
        """
        try:
            # Use default assets if none provided
            if assets is None:
                assets = self.supported_assets[:5]  # Top 5 assets
            
            # Validate strategy
            if strategy not in self.optimization_strategies:
                return {
                    'error': f'Unsupported optimization strategy: {strategy}',
                    'supported_strategies': self.optimization_strategies
                }
            
            # Get historical data for assets
            historical_data = await self._get_historical_data(assets)
            
            # Calculate returns and risk metrics
            returns_data = await self._calculate_returns(historical_data)
            risk_metrics = await self._calculate_risk_metrics(returns_data)
            
            # Perform optimization based on strategy
            optimization_result = await self._optimize_by_strategy(
                assets, returns_data, risk_metrics, strategy, risk_tolerance, target_return, constraints
            )
            
            # Validate and adjust allocations
            final_allocations = await self._validate_allocations(optimization_result['allocations'])
            
            # Calculate expected portfolio metrics
            portfolio_metrics = await self._calculate_portfolio_metrics(
                final_allocations, returns_data, risk_metrics
            )
            
            result = {
                'strategy': strategy,
                'risk_tolerance': risk_tolerance,
                'target_return': target_return,
                'allocations': final_allocations,
                'portfolio_metrics': portfolio_metrics,
                'optimization_metadata': {
                    'assets_analyzed': len(assets),
                    'data_points': len(returns_data) if returns_data is not None else 0,
                    'optimization_time': datetime.now(timezone.utc).isoformat(),
                    'rebalance_frequency': self.rebalance_frequency
                }
            }
            
            # Cache result
            cache_key = f"{strategy}_{risk_tolerance}_{len(assets)}"
            self.allocation_cache[cache_key] = result
            
            # Record optimization
            self.optimization_history.append({
                'timestamp': datetime.now(timezone.utc),
                'strategy': strategy,
                'risk_tolerance': risk_tolerance,
                'num_assets': len(assets),
                'expected_return': portfolio_metrics.get('expected_return', 0),
                'expected_volatility': portfolio_metrics.get('expected_volatility', 0)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            return {
                'error': str(e),
                'strategy': strategy,
                'risk_tolerance': risk_tolerance
            }
    
    async def get_rebalancing_recommendations(
        self, 
        current_allocations: Dict[str, float],
        target_allocations: Dict[str, float],
        portfolio_value: float,
        rebalance_threshold: float = 0.05
    ) -> Dict[str, Any]:
        """
        Get recommendations for rebalancing portfolio to target allocations
        
        Args:
            current_allocations: Current portfolio allocations (symbol -> weight)
            target_allocations: Target allocations from optimization
            portfolio_value: Total portfolio value
            rebalance_threshold: Minimum deviation to trigger rebalancing (5%)
        """
        try:
            recommendations = {
                'rebalance_needed': False,
                'trades': [],
                'total_trade_value': 0.0,
                'max_deviation': 0.0,
                'analysis': {}
            }
            
            # Calculate deviations
            deviations = {}
            max_deviation = 0.0
            
            for symbol in set(list(current_allocations.keys()) + list(target_allocations.keys())):
                current_weight = current_allocations.get(symbol, 0.0)
                target_weight = target_allocations.get(symbol, 0.0)
                deviation = abs(current_weight - target_weight)
                deviations[symbol] = {
                    'current': current_weight,
                    'target': target_weight,
                    'deviation': deviation,
                    'deviation_pct': deviation * 100
                }
                max_deviation = max(max_deviation, deviation)
            
            recommendations['max_deviation'] = max_deviation
            recommendations['analysis'] = deviations
            
            # Check if rebalancing is needed
            if max_deviation > rebalance_threshold:
                recommendations['rebalance_needed'] = True
                
                # Calculate trades needed
                for symbol, analysis in deviations.items():
                    weight_change = analysis['target'] - analysis['current']
                    if abs(weight_change) > rebalance_threshold:
                        trade_value = weight_change * portfolio_value
                        recommendations['trades'].append({
                            'symbol': symbol,
                            'action': 'buy' if weight_change > 0 else 'sell',
                            'weight_change': weight_change,
                            'trade_value': abs(trade_value),
                            'current_weight': analysis['current'],
                            'target_weight': analysis['target']
                        })
                        recommendations['total_trade_value'] += abs(trade_value)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating rebalancing recommendations: {e}")
            return {
                'error': str(e),
                'rebalance_needed': False
            }
    
    async def get_risk_adjusted_returns(
        self, 
        assets: List[str] = None,
        period: str = '1y'
    ) -> Dict[str, Any]:
        """
        Calculate risk-adjusted returns for assets
        
        Args:
            assets: List of assets to analyze
            period: Analysis period ('1y', '6m', '3m', '1m')
        """
        try:
            if assets is None:
                assets = self.supported_assets
            
            # Get historical data
            historical_data = await self._get_historical_data(assets, period)
            
            # Calculate returns
            returns_data = await self._calculate_returns(historical_data)
            
            if returns_data is None:
                return {'error': 'Could not calculate returns data'}
            
            risk_adjusted_metrics = {}
            
            for asset in assets:
                if asset in returns_data:
                    asset_returns = returns_data[asset]
                    
                    # Calculate metrics
                    mean_return = np.mean(asset_returns) * 252  # Annualized
                    volatility = np.std(asset_returns) * np.sqrt(252)  # Annualized
                    sharpe_ratio = mean_return / volatility if volatility > 0 else 0
                    
                    # Simple maximum drawdown calculation
                    cumulative_returns = np.cumprod(1 + asset_returns)
                    peak = np.maximum.accumulate(cumulative_returns)
                    drawdown = (cumulative_returns - peak) / peak
                    max_drawdown = np.min(drawdown)
                    
                    risk_adjusted_metrics[asset] = {
                        'expected_return': float(mean_return),
                        'volatility': float(volatility),
                        'sharpe_ratio': float(sharpe_ratio),
                        'max_drawdown': float(max_drawdown),
                        'calmar_ratio': float(mean_return / abs(max_drawdown)) if max_drawdown < 0 else 0,
                        'data_points': len(asset_returns)
                    }
            
            return {
                'assets': risk_adjusted_metrics,
                'analysis_period': period,
                'calculation_date': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk-adjusted returns: {e}")
            return {'error': str(e)}
    
    async def _get_historical_data(self, assets: List[str], period: str = '1y') -> Optional[Dict[str, Any]]:
        """Get historical data for assets"""
        try:
            if self.historical_data_service:
                data = {}
                for asset in assets:
                    asset_data = await self.historical_data_service.get_historical_data(asset, period=period)
                    if asset_data is not None and not asset_data.empty:
                        data[asset] = asset_data
                return data if data else None
            else:
                # Mock data for testing
                return {asset: pd.DataFrame({
                    'Close': np.random.lognormal(0, 0.02, 252) * 100,
                    'Volume': np.random.randint(1000000, 10000000, 252)
                }) for asset in assets}
                
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return None
    
    async def _calculate_returns(self, historical_data: Dict[str, Any]) -> Optional[Dict[str, np.ndarray]]:
        """Calculate returns from historical data"""
        try:
            if not historical_data:
                return None
            
            returns_data = {}
            for asset, data in historical_data.items():
                if 'Close' in data.columns:
                    prices = data['Close']
                    returns = prices.pct_change().dropna()
                    returns_data[asset] = returns.values
            
            return returns_data if returns_data else None
            
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            return None
    
    async def _calculate_risk_metrics(self, returns_data: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Calculate risk metrics from returns data"""
        try:
            if not returns_data:
                return {}
            
            # Calculate correlation matrix
            assets = list(returns_data.keys())
            returns_matrix = np.column_stack([returns_data[asset] for asset in assets])
            correlation_matrix = np.corrcoef(returns_matrix.T)
            
            # Calculate covariance matrix
            covariance_matrix = np.cov(returns_matrix.T)
            
            # Calculate individual asset metrics
            asset_metrics = {}
            for i, asset in enumerate(assets):
                returns = returns_data[asset]
                asset_metrics[asset] = {
                    'mean_return': np.mean(returns),
                    'volatility': np.std(returns),
                    'skewness': float(np.mean(((returns - np.mean(returns)) / np.std(returns)) ** 3)),
                    'kurtosis': float(np.mean(((returns - np.mean(returns)) / np.std(returns)) ** 4))
                }
            
            return {
                'correlation_matrix': correlation_matrix.tolist(),
                'covariance_matrix': covariance_matrix.tolist(),
                'asset_metrics': asset_metrics,
                'assets': assets
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {}
    
    async def _optimize_by_strategy(
        self, 
        assets: List[str], 
        returns_data: Dict[str, np.ndarray], 
        risk_metrics: Dict[str, Any],
        strategy: str,
        risk_tolerance: float,
        target_return: float,
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform optimization based on selected strategy"""
        try:
            if strategy == 'mean_variance':
                return await self._mean_variance_optimization(assets, returns_data, risk_metrics, risk_tolerance, target_return)
            elif strategy == 'risk_parity':
                return await self._risk_parity_optimization(assets, returns_data, risk_metrics)
            elif strategy == 'momentum':
                return await self._momentum_optimization(assets, returns_data, risk_metrics)
            elif strategy == 'mean_reversion':
                return await self._mean_reversion_optimization(assets, returns_data, risk_metrics)
            else:
                return await self._equal_weight_fallback(assets)
                
        except Exception as e:
            logger.error(f"Error in {strategy} optimization: {e}")
            return await self._equal_weight_fallback(assets)
    
    async def _mean_variance_optimization(self, assets: List[str], returns_data: Dict[str, np.ndarray], risk_metrics: Dict[str, Any], risk_tolerance: float, target_return: float) -> Dict[str, Any]:
        """Simple mean-variance optimization"""
        try:
            # Extract expected returns and covariance
            expected_returns = []
            for asset in assets:
                if asset in risk_metrics['asset_metrics']:
                    expected_returns.append(risk_metrics['asset_metrics'][asset]['mean_return'])
                else:
                    expected_returns.append(0.001)  # Default small positive return
            
            expected_returns = np.array(expected_returns)
            
            # Simple optimization based on risk tolerance
            # Higher risk tolerance = more weight on high return assets
            # Lower risk tolerance = more equal weighting
            
            if risk_tolerance > 0.7:  # High risk tolerance
                # Weight by expected returns
                weights = np.maximum(expected_returns, 0)
                weights = weights / np.sum(weights) if np.sum(weights) > 0 else np.ones(len(assets)) / len(assets)
            elif risk_tolerance < 0.3:  # Low risk tolerance
                # Equal weighting (low risk)
                weights = np.ones(len(assets)) / len(assets)
            else:  # Moderate risk tolerance
                # Blend of return-weighted and equal-weighted
                return_weights = np.maximum(expected_returns, 0)
                return_weights = return_weights / np.sum(return_weights) if np.sum(return_weights) > 0 else np.ones(len(assets)) / len(assets)
                equal_weights = np.ones(len(assets)) / len(assets)
                
                # Blend based on risk tolerance
                blend_factor = (risk_tolerance - 0.3) / 0.4  # Scale to 0-1 for moderate range
                weights = blend_factor * return_weights + (1 - blend_factor) * equal_weights
            
            # Apply position size constraints
            weights = np.clip(weights, self.min_position_size, self.max_position_size)
            weights = weights / np.sum(weights)  # Normalize
            
            allocations = {asset: float(weight) for asset, weight in zip(assets, weights)}
            
            return {
                'allocations': allocations,
                'optimization_method': 'mean_variance',
                'risk_tolerance_applied': risk_tolerance
            }
            
        except Exception as e:
            logger.error(f"Error in mean-variance optimization: {e}")
            return await self._equal_weight_fallback(assets)
    
    async def _risk_parity_optimization(self, assets: List[str], returns_data: Dict[str, np.ndarray], risk_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Risk parity optimization (equal risk contribution)"""
        try:
            # Simple risk parity: inverse volatility weighting
            volatilities = []
            for asset in assets:
                if asset in risk_metrics['asset_metrics']:
                    volatilities.append(risk_metrics['asset_metrics'][asset]['volatility'])
                else:
                    volatilities.append(0.01)  # Default low volatility
            
            volatilities = np.array(volatilities)
            
            # Inverse volatility weights
            inv_vol_weights = 1 / np.maximum(volatilities, 0.001)  # Avoid division by zero
            weights = inv_vol_weights / np.sum(inv_vol_weights)
            
            # Apply constraints
            weights = np.clip(weights, self.min_position_size, self.max_position_size)
            weights = weights / np.sum(weights)
            
            allocations = {asset: float(weight) for asset, weight in zip(assets, weights)}
            
            return {
                'allocations': allocations,
                'optimization_method': 'risk_parity'
            }
            
        except Exception as e:
            logger.error(f"Error in risk parity optimization: {e}")
            return await self._equal_weight_fallback(assets)
    
    async def _momentum_optimization(self, assets: List[str], returns_data: Dict[str, np.ndarray], risk_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Momentum-based optimization"""
        try:
            # Calculate momentum scores (simplified as recent returns)
            momentum_scores = []
            for asset in assets:
                if asset in returns_data:
                    recent_returns = returns_data[asset][-20:]  # Last 20 periods
                    momentum_score = np.mean(recent_returns) if len(recent_returns) > 0 else 0
                    momentum_scores.append(momentum_score)
                else:
                    momentum_scores.append(0)
            
            momentum_scores = np.array(momentum_scores)
            
            # Weight by positive momentum
            positive_momentum = np.maximum(momentum_scores, 0)
            if np.sum(positive_momentum) > 0:
                weights = positive_momentum / np.sum(positive_momentum)
            else:
                weights = np.ones(len(assets)) / len(assets)
            
            # Apply constraints
            weights = np.clip(weights, self.min_position_size, self.max_position_size)
            weights = weights / np.sum(weights)
            
            allocations = {asset: float(weight) for asset, weight in zip(assets, weights)}
            
            return {
                'allocations': allocations,
                'optimization_method': 'momentum'
            }
            
        except Exception as e:
            logger.error(f"Error in momentum optimization: {e}")
            return await self._equal_weight_fallback(assets)
    
    async def _mean_reversion_optimization(self, assets: List[str], returns_data: Dict[str, np.ndarray], risk_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Mean reversion optimization"""
        try:
            # Calculate mean reversion scores (inverse of recent performance)
            reversion_scores = []
            for asset in assets:
                if asset in returns_data:
                    recent_returns = returns_data[asset][-20:]  # Last 20 periods
                    recent_performance = np.mean(recent_returns) if len(recent_returns) > 0 else 0
                    # Inverse weighting - favor assets with poor recent performance
                    reversion_score = -recent_performance
                    reversion_scores.append(reversion_score)
                else:
                    reversion_scores.append(0)
            
            reversion_scores = np.array(reversion_scores)
            
            # Normalize scores to positive weights
            min_score = np.min(reversion_scores)
            adjusted_scores = reversion_scores - min_score + 0.01  # Ensure positive
            weights = adjusted_scores / np.sum(adjusted_scores)
            
            # Apply constraints
            weights = np.clip(weights, self.min_position_size, self.max_position_size)
            weights = weights / np.sum(weights)
            
            allocations = {asset: float(weight) for asset, weight in zip(assets, weights)}
            
            return {
                'allocations': allocations,
                'optimization_method': 'mean_reversion'
            }
            
        except Exception as e:
            logger.error(f"Error in mean reversion optimization: {e}")
            return await self._equal_weight_fallback(assets)
    
    async def _equal_weight_fallback(self, assets: List[str]) -> Dict[str, Any]:
        """Fallback to equal weighting"""
        equal_weight = 1.0 / len(assets)
        allocations = {asset: equal_weight for asset in assets}
        
        return {
            'allocations': allocations,
            'optimization_method': 'equal_weight_fallback'
        }
    
    async def _validate_allocations(self, allocations: Dict[str, float]) -> Dict[str, float]:
        """Validate and adjust allocations to meet constraints"""
        try:
            # Ensure allocations sum to 1.0
            total_allocation = sum(allocations.values())
            if total_allocation != 1.0:
                # Normalize
                allocations = {asset: weight / total_allocation for asset, weight in allocations.items()}
            
            # Apply min/max constraints
            adjusted_allocations = {}
            for asset, weight in allocations.items():
                adjusted_weight = max(self.min_position_size, min(self.max_position_size, weight))
                adjusted_allocations[asset] = adjusted_weight
            
            # Renormalize after constraints
            total_adjusted = sum(adjusted_allocations.values())
            if total_adjusted != 1.0:
                adjusted_allocations = {asset: weight / total_adjusted for asset, weight in adjusted_allocations.items()}
            
            return adjusted_allocations
            
        except Exception as e:
            logger.error(f"Error validating allocations: {e}")
            return allocations
    
    async def _calculate_portfolio_metrics(self, allocations: Dict[str, float], returns_data: Dict[str, np.ndarray], risk_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate expected portfolio metrics"""
        try:
            if not risk_metrics.get('asset_metrics'):
                return {'error': 'Missing risk metrics'}
            
            # Calculate expected return
            expected_return = 0.0
            expected_volatility = 0.0
            
            for asset, weight in allocations.items():
                if asset in risk_metrics['asset_metrics']:
                    asset_return = risk_metrics['asset_metrics'][asset]['mean_return']
                    expected_return += weight * asset_return * 252  # Annualized
            
            # Simple volatility calculation (ignoring correlations for simplicity)
            for asset, weight in allocations.items():
                if asset in risk_metrics['asset_metrics']:
                    asset_vol = risk_metrics['asset_metrics'][asset]['volatility']
                    expected_volatility += (weight ** 2) * (asset_vol ** 2) * 252  # Annualized
            
            expected_volatility = np.sqrt(expected_volatility)
            
            # Calculate Sharpe ratio (assuming 0% risk-free rate)
            sharpe_ratio = expected_return / expected_volatility if expected_volatility > 0 else 0
            
            return {
                'expected_return': float(expected_return),
                'expected_volatility': float(expected_volatility),
                'sharpe_ratio': float(sharpe_ratio),
                'diversification_ratio': len([w for w in allocations.values() if w > 0.05])  # Number of meaningful positions
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {'error': str(e)}
    
    async def get_optimization_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent optimization history"""
        try:
            # Sort by timestamp (newest first)
            sorted_history = sorted(self.optimization_history, key=lambda x: x['timestamp'], reverse=True)
            
            # Format for API response
            history = []
            for record in sorted_history[:limit]:
                history.append({
                    'timestamp': record['timestamp'].isoformat(),
                    'strategy': record['strategy'],
                    'risk_tolerance': record['risk_tolerance'],
                    'num_assets': record['num_assets'],
                    'expected_return': record['expected_return'],
                    'expected_volatility': record['expected_volatility']
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting optimization history: {e}")
            return []
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": "ml_portfolio_optimizer_service",
            "status": "running",
            "supported_assets": len(self.supported_assets),
            "optimization_strategies": len(self.optimization_strategies),
            "cached_optimizations": len(self.allocation_cache),
            "optimization_history": len(self.optimization_history),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_ml_portfolio_optimizer_service():
    """Factory function to create MLPortfolioOptimizerService instance"""
    return MLPortfolioOptimizerService()