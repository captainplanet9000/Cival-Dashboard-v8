"""
Portfolio Tracker Service
Tracks portfolio positions, performance, and analytics
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

class PortfolioTrackerService:
    """Service for tracking portfolio positions and performance"""
    
    def __init__(self, market_data_service=None, db_manager=None):
        self.market_data_service = market_data_service
        self.db_manager = db_manager
        
        # Portfolio state
        self.positions = {}
        self.cash_balance = Decimal('50000.0')  # Starting cash
        self.total_equity = Decimal('50000.0')
        
        # Performance tracking
        self.daily_values = []
        self.trade_history = []
        self.performance_metrics = {
            'total_return': Decimal('0'),
            'daily_pnl': Decimal('0'),
            'total_pnl': Decimal('0'),
            'win_rate': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0
        }
        
        # Configuration
        self.initial_equity = Decimal('50000.0')
        self.commission_rate = Decimal('0.001')  # 0.1%
        
    async def update_position(
        self, 
        symbol: str, 
        quantity_change: Decimal, 
        price: Decimal,
        trade_type: str = 'market'
    ) -> Dict[str, Any]:
        """
        Update position based on trade execution
        
        Args:
            symbol: Trading symbol
            quantity_change: Change in position (positive for buy, negative for sell)
            price: Execution price
            trade_type: Type of trade (market, limit, etc.)
        """
        try:
            # Initialize position if doesn't exist
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'symbol': symbol,
                    'quantity': Decimal('0'),
                    'avg_cost': Decimal('0'),
                    'total_cost': Decimal('0'),
                    'current_price': price,
                    'market_value': Decimal('0'),
                    'unrealized_pnl': Decimal('0'),
                    'realized_pnl': Decimal('0'),
                    'last_updated': datetime.now(timezone.utc)
                }
            
            position = self.positions[symbol]
            
            # Calculate trade value and commission
            trade_value = abs(quantity_change) * price
            commission = trade_value * self.commission_rate
            
            # Record trade
            trade_record = {
                'timestamp': datetime.now(timezone.utc),
                'symbol': symbol,
                'side': 'buy' if quantity_change > 0 else 'sell',
                'quantity': abs(quantity_change),
                'price': price,
                'value': trade_value,
                'commission': commission,
                'trade_type': trade_type
            }
            self.trade_history.append(trade_record)
            
            # Update position
            old_quantity = position['quantity']
            new_quantity = old_quantity + quantity_change
            
            if quantity_change > 0:  # Buy
                # Update average cost
                if old_quantity >= 0:  # Adding to long position
                    total_cost = position['total_cost'] + trade_value + commission
                    position['avg_cost'] = total_cost / new_quantity if new_quantity > 0 else Decimal('0')
                    position['total_cost'] = total_cost
                else:  # Covering short position
                    if abs(new_quantity) < abs(old_quantity):  # Partial cover
                        realized_pnl = quantity_change * (position['avg_cost'] - price) - commission
                        position['realized_pnl'] += realized_pnl
                    else:  # Full cover + possible new long
                        # Realize PnL from short cover
                        cover_quantity = abs(old_quantity)
                        realized_pnl = cover_quantity * (position['avg_cost'] - price) - commission
                        position['realized_pnl'] += realized_pnl
                        
                        # Start new long position if any quantity remains
                        remaining_quantity = new_quantity
                        if remaining_quantity > 0:
                            position['avg_cost'] = price
                            position['total_cost'] = remaining_quantity * price
                
            else:  # Sell
                if old_quantity > 0:  # Selling long position
                    if abs(quantity_change) <= old_quantity:  # Partial or full sale
                        realized_pnl = abs(quantity_change) * (price - position['avg_cost']) - commission
                        position['realized_pnl'] += realized_pnl
                        if new_quantity == 0:
                            position['total_cost'] = Decimal('0')
                            position['avg_cost'] = Decimal('0')
                    else:  # Oversell (go short)
                        # Realize PnL from long position
                        long_pnl = old_quantity * (price - position['avg_cost']) - commission
                        position['realized_pnl'] += long_pnl
                        
                        # Start short position
                        short_quantity = abs(quantity_change) - old_quantity
                        position['avg_cost'] = price
                        position['total_cost'] = short_quantity * price
                else:  # Adding to short position
                    total_cost = position['total_cost'] + trade_value + commission
                    position['avg_cost'] = total_cost / abs(new_quantity) if new_quantity != 0 else Decimal('0')
                    position['total_cost'] = total_cost
            
            # Update position quantity and current price
            position['quantity'] = new_quantity
            position['current_price'] = price
            position['last_updated'] = datetime.now(timezone.utc)
            
            # Update cash balance
            if quantity_change > 0:  # Buy
                self.cash_balance -= (trade_value + commission)
            else:  # Sell
                self.cash_balance += (trade_value - commission)
            
            # Calculate market value and unrealized PnL
            await self._update_position_values(symbol)
            
            # Update total equity
            await self._calculate_total_equity()
            
            return {
                'status': 'success',
                'symbol': symbol,
                'new_quantity': float(new_quantity),
                'avg_cost': float(position['avg_cost']),
                'realized_pnl': float(position['realized_pnl']),
                'unrealized_pnl': float(position['unrealized_pnl']),
                'cash_balance': float(self.cash_balance)
            }
            
        except Exception as e:
            logger.error(f"Error updating position for {symbol}: {e}")
            return {
                'status': 'error',
                'symbol': symbol,
                'error': str(e)
            }
    
    async def _update_position_values(self, symbol: str):
        """Update market value and unrealized PnL for a position"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            current_price = position['current_price']
            quantity = position['quantity']
            
            # Update market value
            position['market_value'] = abs(quantity) * current_price
            
            # Calculate unrealized PnL
            if quantity > 0:  # Long position
                position['unrealized_pnl'] = quantity * (current_price - position['avg_cost'])
            elif quantity < 0:  # Short position
                position['unrealized_pnl'] = abs(quantity) * (position['avg_cost'] - current_price)
            else:  # No position
                position['unrealized_pnl'] = Decimal('0')
                position['market_value'] = Decimal('0')
            
        except Exception as e:
            logger.error(f"Error updating position values for {symbol}: {e}")
    
    async def _calculate_total_equity(self):
        """Calculate total portfolio equity"""
        try:
            total_position_value = Decimal('0')
            total_unrealized_pnl = Decimal('0')
            
            for position in self.positions.values():
                if position['quantity'] > 0:  # Long positions add market value
                    total_position_value += position['market_value']
                elif position['quantity'] < 0:  # Short positions subtract market value
                    total_position_value -= position['market_value']
                
                total_unrealized_pnl += position['unrealized_pnl']
            
            self.total_equity = self.cash_balance + total_position_value
            
            # Update performance metrics
            self.performance_metrics['total_return'] = (self.total_equity - self.initial_equity) / self.initial_equity
            self.performance_metrics['total_pnl'] = self.total_equity - self.initial_equity
            
            # Calculate daily PnL if we have previous day data
            if self.daily_values:
                yesterday_value = self.daily_values[-1]['equity']
                self.performance_metrics['daily_pnl'] = self.total_equity - yesterday_value
            
        except Exception as e:
            logger.error(f"Error calculating total equity: {e}")
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        try:
            await self._calculate_total_equity()
            
            # Calculate position summary
            long_positions = [p for p in self.positions.values() if p['quantity'] > 0]
            short_positions = [p for p in self.positions.values() if p['quantity'] < 0]
            
            total_unrealized_pnl = sum(p['unrealized_pnl'] for p in self.positions.values())
            total_realized_pnl = sum(p['realized_pnl'] for p in self.positions.values())
            
            return {
                'total_equity': float(self.total_equity),
                'cash_balance': float(self.cash_balance),
                'total_position_value': float(sum(p['market_value'] for p in self.positions.values())),
                'total_unrealized_pnl': float(total_unrealized_pnl),
                'total_realized_pnl': float(total_realized_pnl),
                'total_pnl': float(total_unrealized_pnl + total_realized_pnl),
                'daily_pnl': float(self.performance_metrics['daily_pnl']),
                'total_return_percent': float(self.performance_metrics['total_return'] * 100),
                'number_of_positions': len([p for p in self.positions.values() if p['quantity'] != 0]),
                'long_positions': len(long_positions),
                'short_positions': len(short_positions),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {
                'total_equity': 0,
                'cash_balance': 0,
                'error': str(e)
            }
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all current positions"""
        try:
            positions = []
            for position in self.positions.values():
                if position['quantity'] != 0:  # Only include non-zero positions
                    positions.append({
                        'symbol': position['symbol'],
                        'quantity': float(position['quantity']),
                        'avg_cost': float(position['avg_cost']),
                        'current_price': float(position['current_price']),
                        'market_value': float(position['market_value']),
                        'unrealized_pnl': float(position['unrealized_pnl']),
                        'realized_pnl': float(position['realized_pnl']),
                        'pnl_percent': float(position['unrealized_pnl'] / (position['avg_cost'] * abs(position['quantity'])) * 100) if position['avg_cost'] > 0 else 0,
                        'last_updated': position['last_updated'].isoformat()
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trade history"""
        try:
            # Sort by timestamp (newest first)
            sorted_trades = sorted(self.trade_history, key=lambda x: x['timestamp'], reverse=True)
            
            # Limit results and format for API
            trades = []
            for trade in sorted_trades[:limit]:
                trades.append({
                    'timestamp': trade['timestamp'].isoformat(),
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'quantity': float(trade['quantity']),
                    'price': float(trade['price']),
                    'value': float(trade['value']),
                    'commission': float(trade['commission']),
                    'trade_type': trade['trade_type']
                })
            
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        try:
            # Calculate additional metrics if we have enough data
            if len(self.trade_history) > 0:
                winning_trades = [t for t in self.trade_history if t.get('pnl', 0) > 0]
                self.performance_metrics['win_rate'] = len(winning_trades) / len(self.trade_history)
            
            # Calculate Sharpe ratio (simplified)
            if len(self.daily_values) > 30:
                returns = []
                for i in range(1, len(self.daily_values)):
                    prev_value = self.daily_values[i-1]['equity']
                    curr_value = self.daily_values[i]['equity']
                    daily_return = (curr_value - prev_value) / prev_value
                    returns.append(daily_return)
                
                if returns:
                    import numpy as np
                    avg_return = np.mean(returns)
                    std_return = np.std(returns)
                    if std_return > 0:
                        self.performance_metrics['sharpe_ratio'] = (avg_return / std_return) * np.sqrt(252)  # Annualized
                        self.performance_metrics['volatility'] = std_return * np.sqrt(252)
            
            return {
                'total_return_percent': float(self.performance_metrics['total_return'] * 100),
                'total_pnl': float(self.performance_metrics['total_pnl']),
                'daily_pnl': float(self.performance_metrics['daily_pnl']),
                'win_rate': float(self.performance_metrics['win_rate']),
                'sharpe_ratio': float(self.performance_metrics['sharpe_ratio']),
                'volatility': float(self.performance_metrics['volatility']),
                'max_drawdown': float(self.performance_metrics['max_drawdown']),
                'total_trades': len(self.trade_history),
                'total_equity': float(self.total_equity),
                'initial_equity': float(self.initial_equity),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}
    
    async def update_market_prices(self, price_updates: Dict[str, Decimal]):
        """Update current market prices for positions"""
        try:
            for symbol, price in price_updates.items():
                if symbol in self.positions:
                    self.positions[symbol]['current_price'] = price
                    await self._update_position_values(symbol)
            
            await self._calculate_total_equity()
            
        except Exception as e:
            logger.error(f"Error updating market prices: {e}")
    
    async def record_daily_snapshot(self):
        """Record daily portfolio snapshot for performance tracking"""
        try:
            snapshot = {
                'date': datetime.now(timezone.utc).date(),
                'equity': self.total_equity,
                'cash': self.cash_balance,
                'positions': len([p for p in self.positions.values() if p['quantity'] != 0]),
                'timestamp': datetime.now(timezone.utc)
            }
            
            self.daily_values.append(snapshot)
            
            # Keep only last 365 days
            if len(self.daily_values) > 365:
                self.daily_values = self.daily_values[-365:]
            
        except Exception as e:
            logger.error(f"Error recording daily snapshot: {e}")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": "portfolio_tracker_service",
            "status": "running",
            "total_equity": float(self.total_equity),
            "positions_count": len([p for p in self.positions.values() if p['quantity'] != 0]),
            "trades_count": len(self.trade_history),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_portfolio_tracker_service():
    """Factory function to create PortfolioTrackerService instance"""
    return PortfolioTrackerService()