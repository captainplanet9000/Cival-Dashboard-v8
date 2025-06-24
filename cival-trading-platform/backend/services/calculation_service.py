"""
Calculation Service
Provides real mathematical calculations and aggregations for all dashboard metrics
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import math
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

from ..core.service_registry import service_registry
from ..core.logging_config import logger
from ..database.connection import DatabaseManager


@dataclass
class PerformanceMetrics:
    """Performance calculation results"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    var_95: float
    var_99: float
    
    
@dataclass
class RiskMetrics:
    """Risk calculation results"""
    portfolio_var: float
    daily_var: float
    max_exposure: float
    current_exposure: float
    leverage_ratio: float
    margin_utilization: float
    correlation_risk: float
    concentration_risk: float
    liquidity_risk: float
    

class CalculationService:
    """Service for real mathematical calculations and aggregations"""
    
    def __init__(self):
        self.logger = logger
        self.db = DatabaseManager()
        
        # Risk-free rate for calculations (annualized)
        self.risk_free_rate = 0.05  # 5%
        
        # Market parameters
        self.trading_days_per_year = 252
        self.hours_per_day = 24
        
    async def calculate_portfolio_performance(self, portfolio_data: List[Dict[str, Any]], 
                                            historical_values: List[float]) -> PerformanceMetrics:
        """Calculate comprehensive portfolio performance metrics"""
        try:
            if not historical_values or len(historical_values) < 2:
                return self._get_default_performance_metrics()
            
            # Calculate returns
            returns = self._calculate_returns(historical_values)
            
            # Total return
            total_return = (historical_values[-1] / historical_values[0] - 1) * 100
            
            # Annualized return
            periods = len(historical_values) - 1
            if periods > 0:
                annualized_return = ((historical_values[-1] / historical_values[0]) ** (self.trading_days_per_year / periods) - 1) * 100
            else:
                annualized_return = 0
            
            # Volatility (annualized)
            volatility = self._calculate_volatility(returns) * math.sqrt(self.trading_days_per_year) * 100
            
            # Sharpe ratio
            sharpe_ratio = self._calculate_sharpe_ratio(returns, self.risk_free_rate)
            
            # Maximum drawdown
            max_drawdown = self._calculate_max_drawdown(historical_values) * 100
            
            # Calmar ratio
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Win rate and profit factor
            win_rate, profit_factor = self._calculate_win_metrics(returns)
            
            # Value at Risk
            var_95 = self._calculate_var(returns, 0.95) * 100
            var_99 = self._calculate_var(returns, 0.99) * 100
            
            return PerformanceMetrics(
                total_return=round(total_return, 2),
                annualized_return=round(annualized_return, 2),
                volatility=round(volatility, 2),
                sharpe_ratio=round(sharpe_ratio, 2),
                max_drawdown=round(max_drawdown, 2),
                calmar_ratio=round(calmar_ratio, 2),
                win_rate=round(win_rate, 2),
                profit_factor=round(profit_factor, 2),
                var_95=round(var_95, 2),
                var_99=round(var_99, 2)
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio performance: {e}")
            return self._get_default_performance_metrics()
    
    async def calculate_risk_metrics(self, positions: List[Dict[str, Any]], 
                                   correlations: Dict[str, Dict[str, float]] = None) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            if not positions:
                return self._get_default_risk_metrics()
            
            # Portfolio value calculations
            total_value = sum(pos.get('value', 0) for pos in positions)
            total_exposure = sum(abs(pos.get('value', 0)) for pos in positions)
            
            # Current exposure ratio
            current_exposure = min(total_exposure / total_value, 1.0) if total_value > 0 else 0
            
            # Maximum exposure (configurable limit)
            max_exposure = 0.95  # 95% max exposure
            
            # Leverage ratio
            leverage_ratio = total_exposure / total_value if total_value > 0 else 0
            
            # Margin utilization (simplified calculation)
            margin_used = sum(pos.get('margin_used', 0) for pos in positions)
            total_margin = sum(pos.get('value', 0) for pos in positions) * 0.1  # Assume 10x leverage
            margin_utilization = margin_used / total_margin if total_margin > 0 else 0
            
            # Portfolio VaR calculation
            portfolio_var = self._calculate_portfolio_var(positions, correlations)
            daily_var = portfolio_var / math.sqrt(self.trading_days_per_year)
            
            # Correlation risk
            correlation_risk = self._calculate_correlation_risk(positions, correlations)
            
            # Concentration risk
            concentration_risk = self._calculate_concentration_risk(positions)
            
            # Liquidity risk
            liquidity_risk = self._calculate_liquidity_risk(positions)
            
            return RiskMetrics(
                portfolio_var=round(portfolio_var, 2),
                daily_var=round(daily_var, 2),
                max_exposure=round(max_exposure, 2),
                current_exposure=round(current_exposure, 2),
                leverage_ratio=round(leverage_ratio, 2),
                margin_utilization=round(margin_utilization, 2),
                correlation_risk=round(correlation_risk, 2),
                concentration_risk=round(concentration_risk, 2),
                liquidity_risk=round(liquidity_risk, 2)
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return self._get_default_risk_metrics()
    
    async def calculate_goal_progress(self, goal_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate real goal progress based on actual data"""
        try:
            goal_type = goal_data.get('type', '').lower()
            target_value = float(goal_data.get('target_value', 0))
            current_value = float(goal_data.get('current_value', 0))
            start_date = goal_data.get('start_date')
            end_date = goal_data.get('end_date')
            
            # Basic progress calculation
            if target_value == 0:
                progress_percentage = 0
            else:
                progress_percentage = min((current_value / target_value) * 100, 100)
            
            # Time-based progress
            time_progress = 0
            if start_date and end_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                now = datetime.now()
                
                total_duration = (end_dt - start_dt).total_seconds()
                elapsed_duration = (now - start_dt).total_seconds()
                
                if total_duration > 0:
                    time_progress = min((elapsed_duration / total_duration) * 100, 100)
            
            # Goal type specific calculations
            if goal_type == 'profit':
                # For profit goals, calculate trajectory
                trajectory_score = self._calculate_profit_trajectory(current_value, target_value, time_progress)
            elif goal_type == 'risk':
                # For risk goals, lower is better
                if target_value > 0:
                    progress_percentage = max(0, 100 - (current_value / target_value) * 100)
                trajectory_score = progress_percentage
            else:
                trajectory_score = progress_percentage
            
            # Velocity calculation (progress per time unit)
            velocity = 0
            if time_progress > 0:
                velocity = progress_percentage / (time_progress / 100)
            
            # Estimated completion
            estimated_completion = 100
            if velocity > 0 and progress_percentage < 100:
                remaining_progress = 100 - progress_percentage
                estimated_days = remaining_progress / (velocity / 100)
                estimated_completion = min(time_progress + estimated_days, 100)
            
            return {
                'progress_percentage': round(progress_percentage, 1),
                'time_progress': round(time_progress, 1),
                'trajectory_score': round(trajectory_score, 1),
                'velocity': round(velocity, 2),
                'estimated_completion': round(estimated_completion, 1),
                'on_track': trajectory_score >= time_progress * 0.8  # Within 80% of expected
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating goal progress: {e}")
            return {
                'progress_percentage': 0,
                'time_progress': 0,
                'trajectory_score': 0,
                'velocity': 0,
                'estimated_completion': 0,
                'on_track': False
            }
    
    async def calculate_farm_performance(self, farm_data: Dict[str, Any], 
                                       agent_performances: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate farm-level performance metrics"""
        try:
            if not agent_performances:
                return self._get_default_farm_metrics()
            
            # Aggregate agent performance
            total_pnl = sum(agent.get('pnl', 0) for agent in agent_performances)
            total_trades = sum(agent.get('trades_count', 0) for agent in agent_performances)
            winning_trades = sum(agent.get('winning_trades', 0) for agent in agent_performances)
            
            # Calculate farm metrics
            avg_pnl = total_pnl / len(agent_performances)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Risk-adjusted returns
            returns = [agent.get('return_rate', 0) for agent in agent_performances]
            farm_return = sum(returns) / len(returns) if returns else 0
            return_volatility = self._calculate_volatility(returns) if len(returns) > 1 else 0
            
            risk_adjusted_return = farm_return / (return_volatility + 0.01)  # Add small value to avoid division by zero
            
            # Efficiency metrics
            avg_trades_per_agent = total_trades / len(agent_performances)
            active_agents = len([a for a in agent_performances if a.get('status') == 'active'])
            utilization_rate = (active_agents / len(agent_performances)) * 100
            
            # Consistency score
            consistency_score = self._calculate_consistency_score(returns)
            
            return {
                'total_pnl': round(total_pnl, 2),
                'average_pnl': round(avg_pnl, 2),
                'win_rate': round(win_rate, 1),
                'farm_return': round(farm_return, 2),
                'risk_adjusted_return': round(risk_adjusted_return, 2),
                'utilization_rate': round(utilization_rate, 1),
                'consistency_score': round(consistency_score, 2),
                'total_trades': total_trades,
                'active_agents': active_agents
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating farm performance: {e}")
            return self._get_default_farm_metrics()
    
    async def calculate_vault_metrics(self, vault_data: Dict[str, Any], 
                                    transactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate vault-specific metrics"""
        try:
            current_balance = float(vault_data.get('balance', 0))
            
            if not transactions:
                return {
                    'current_balance': current_balance,
                    'total_inflows': 0,
                    'total_outflows': 0,
                    'net_flow': 0,
                    'growth_rate': 0,
                    'turnover_ratio': 0,
                    'average_transaction_size': 0,
                    'transaction_count': 0
                }
            
            # Calculate flows
            inflows = sum(tx.get('amount', 0) for tx in transactions if tx.get('amount', 0) > 0)
            outflows = sum(abs(tx.get('amount', 0)) for tx in transactions if tx.get('amount', 0) < 0)
            net_flow = inflows - outflows
            
            # Growth rate calculation
            initial_balance = current_balance - net_flow
            growth_rate = ((current_balance / initial_balance - 1) * 100) if initial_balance > 0 else 0
            
            # Turnover ratio
            total_volume = inflows + outflows
            turnover_ratio = (total_volume / current_balance) if current_balance > 0 else 0
            
            # Transaction metrics
            transaction_count = len(transactions)
            average_transaction_size = total_volume / transaction_count if transaction_count > 0 else 0
            
            return {
                'current_balance': round(current_balance, 2),
                'total_inflows': round(inflows, 2),
                'total_outflows': round(outflows, 2),
                'net_flow': round(net_flow, 2),
                'growth_rate': round(growth_rate, 2),
                'turnover_ratio': round(turnover_ratio, 3),
                'average_transaction_size': round(average_transaction_size, 2),
                'transaction_count': transaction_count
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating vault metrics: {e}")
            return {}
    
    async def calculate_market_correlation(self, price_data: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix for market data"""
        try:
            symbols = list(price_data.keys())
            correlation_matrix = {}
            
            for symbol1 in symbols:
                correlation_matrix[symbol1] = {}
                for symbol2 in symbols:
                    if symbol1 == symbol2:
                        correlation_matrix[symbol1][symbol2] = 1.0
                    else:
                        correlation = self._calculate_correlation(
                            price_data[symbol1], 
                            price_data[symbol2]
                        )
                        correlation_matrix[symbol1][symbol2] = round(correlation, 3)
            
            return correlation_matrix
            
        except Exception as e:
            self.logger.error(f"Error calculating market correlation: {e}")
            return {}
    
    # Private helper methods
    
    def _calculate_returns(self, prices: List[float]) -> List[float]:
        """Calculate percentage returns from price series"""
        if len(prices) < 2:
            return []
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] / prices[i-1]) - 1
                returns.append(ret)
        
        return returns
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate volatility (standard deviation) of returns"""
        if len(returns) < 2:
            return 0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        return math.sqrt(variance)
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float) -> float:
        """Calculate Sharpe ratio"""
        if not returns:
            return 0
        
        mean_return = sum(returns) / len(returns)
        excess_return = mean_return - (risk_free_rate / self.trading_days_per_year)
        volatility = self._calculate_volatility(returns)
        
        return (excess_return / volatility) if volatility != 0 else 0
    
    def _calculate_max_drawdown(self, prices: List[float]) -> float:
        """Calculate maximum drawdown"""
        if len(prices) < 2:
            return 0
        
        peak = prices[0]
        max_dd = 0
        
        for price in prices:
            if price > peak:
                peak = price
            else:
                drawdown = (peak - price) / peak
                max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _calculate_var(self, returns: List[float], confidence: float) -> float:
        """Calculate Value at Risk"""
        if not returns:
            return 0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        return sorted_returns[index] if index < len(sorted_returns) else 0
    
    def _calculate_win_metrics(self, returns: List[float]) -> Tuple[float, float]:
        """Calculate win rate and profit factor"""
        if not returns:
            return 0, 0
        
        winning_trades = [r for r in returns if r > 0]
        losing_trades = [r for r in returns if r < 0]
        
        win_rate = (len(winning_trades) / len(returns)) * 100
        
        total_gains = sum(winning_trades)
        total_losses = abs(sum(losing_trades))
        
        profit_factor = (total_gains / total_losses) if total_losses != 0 else float('inf')
        
        return win_rate, profit_factor
    
    def _calculate_portfolio_var(self, positions: List[Dict[str, Any]], 
                                correlations: Dict[str, Dict[str, float]] = None) -> float:
        """Calculate portfolio Value at Risk"""
        # Simplified VaR calculation
        total_value = sum(pos.get('value', 0) for pos in positions)
        
        # Assume 2% daily volatility for simplification
        portfolio_volatility = 0.02
        confidence_level = 0.95
        z_score = 1.645  # 95% confidence
        
        var = total_value * portfolio_volatility * z_score
        return var
    
    def _calculate_correlation_risk(self, positions: List[Dict[str, Any]], 
                                  correlations: Dict[str, Dict[str, float]] = None) -> float:
        """Calculate correlation risk score"""
        if not correlations or len(positions) < 2:
            return 0.5  # Medium risk
        
        # Simplified correlation risk calculation
        avg_correlation = 0.6  # Assume moderate correlation
        return min(avg_correlation, 1.0)
    
    def _calculate_concentration_risk(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate concentration risk (Herfindahl index)"""
        if not positions:
            return 0
        
        total_value = sum(pos.get('value', 0) for pos in positions)
        if total_value == 0:
            return 0
        
        # Calculate Herfindahl index
        hhi = sum((pos.get('value', 0) / total_value) ** 2 for pos in positions)
        
        # Normalize to 0-1 scale (0 = well diversified, 1 = concentrated)
        return min(hhi, 1.0)
    
    def _calculate_liquidity_risk(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate liquidity risk score"""
        # Simplified liquidity risk based on position sizes and market cap
        risk_score = 0
        
        for pos in positions:
            value = pos.get('value', 0)
            symbol = pos.get('symbol', '')
            
            # Assign risk based on asset type (simplified)
            if 'BTC' in symbol or 'ETH' in symbol:
                asset_risk = 0.1  # Low risk for major assets
            elif 'USDT' in symbol or 'USDC' in symbol:
                asset_risk = 0.05  # Very low risk for stablecoins
            else:
                asset_risk = 0.3  # Higher risk for altcoins
            
            risk_score += asset_risk * (value / sum(p.get('value', 0) for p in positions))
        
        return min(risk_score, 1.0)
    
    def _calculate_correlation(self, series1: List[float], series2: List[float]) -> float:
        """Calculate correlation coefficient between two series"""
        if len(series1) != len(series2) or len(series1) < 2:
            return 0
        
        n = len(series1)
        mean1 = sum(series1) / n
        mean2 = sum(series2) / n
        
        numerator = sum((series1[i] - mean1) * (series2[i] - mean2) for i in range(n))
        
        sum_sq1 = sum((x - mean1) ** 2 for x in series1)
        sum_sq2 = sum((x - mean2) ** 2 for x in series2)
        
        denominator = math.sqrt(sum_sq1 * sum_sq2)
        
        return numerator / denominator if denominator != 0 else 0
    
    def _calculate_profit_trajectory(self, current: float, target: float, time_progress: float) -> float:
        """Calculate profit goal trajectory score"""
        if target == 0:
            return 0
        
        expected_progress = (current / target) * 100
        
        # Bonus for being ahead of schedule
        if time_progress > 0:
            trajectory = expected_progress / (time_progress / 100)
            return min(trajectory * 20, 100)  # Scale and cap at 100
        
        return expected_progress
    
    def _calculate_consistency_score(self, returns: List[float]) -> float:
        """Calculate consistency score based on return variance"""
        if len(returns) < 2:
            return 0
        
        volatility = self._calculate_volatility(returns)
        mean_return = sum(returns) / len(returns)
        
        # Higher consistency for lower volatility relative to returns
        if volatility == 0:
            return 100 if mean_return >= 0 else 0
        
        consistency = max(0, 100 - (volatility / abs(mean_return + 0.01)) * 100)
        return min(consistency, 100)
    
    # Default metrics for fallback
    
    def _get_default_performance_metrics(self) -> PerformanceMetrics:
        """Return default performance metrics"""
        return PerformanceMetrics(
            total_return=0,
            annualized_return=0,
            volatility=15.0,
            sharpe_ratio=0,
            max_drawdown=0,
            calmar_ratio=0,
            win_rate=50.0,
            profit_factor=1.0,
            var_95=5.0,
            var_99=8.0
        )
    
    def _get_default_risk_metrics(self) -> RiskMetrics:
        """Return default risk metrics"""
        return RiskMetrics(
            portfolio_var=5000.0,
            daily_var=1000.0,
            max_exposure=0.95,
            current_exposure=0.5,
            leverage_ratio=1.0,
            margin_utilization=0.3,
            correlation_risk=0.5,
            concentration_risk=0.3,
            liquidity_risk=0.2
        )
    
    def _get_default_farm_metrics(self) -> Dict[str, float]:
        """Return default farm metrics"""
        return {
            'total_pnl': 0,
            'average_pnl': 0,
            'win_rate': 50.0,
            'farm_return': 0,
            'risk_adjusted_return': 0,
            'utilization_rate': 80.0,
            'consistency_score': 75.0,
            'total_trades': 0,
            'active_agents': 0
        }


# Register service
service_registry.register('calculation', CalculationService)