"""
Trading Engine Service
Core trading logic and order execution coordination
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class TradingEngineService:
    """Core trading engine for order execution and position management"""
    
    def __init__(self, order_management_service=None, risk_service=None, portfolio_service=None):
        self.order_service = order_management_service
        self.risk_service = risk_service
        self.portfolio_service = portfolio_service
        
        # Trading state
        self.active_orders = {}
        self.pending_signals = []
        self.execution_history = []
        
        # Configuration
        self.max_position_size_percent = Decimal("0.1")  # 10% max position
        self.default_stop_loss_percent = Decimal("0.03")  # 3% stop loss
        self.min_order_size_usd = Decimal("10.0")
        
        # Performance tracking
        self.metrics = {
            "total_orders": 0,
            "successful_orders": 0,
            "failed_orders": 0,
            "total_volume": Decimal("0"),
            "avg_execution_time": 0.0
        }
        
    async def submit_trading_signal(
        self, 
        signal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process and execute a trading signal
        
        Args:
            signal: Trading signal with symbol, action, quantity, etc.
        """
        try:
            signal_id = signal.get('signal_id', str(uuid.uuid4()))
            
            # Validate signal
            validation_result = await self._validate_signal(signal)
            if not validation_result['valid']:
                return {
                    'signal_id': signal_id,
                    'status': 'rejected',
                    'reason': validation_result['reason']
                }
            
            # Risk checks
            risk_check = await self._check_risk_limits(signal)
            if not risk_check['approved']:
                return {
                    'signal_id': signal_id,
                    'status': 'rejected',
                    'reason': f"Risk check failed: {risk_check['reason']}"
                }
            
            # Position sizing
            adjusted_signal = await self._calculate_position_size(signal)
            
            # Execute the trade
            execution_result = await self._execute_trade(adjusted_signal)
            
            # Update metrics
            self.metrics["total_orders"] += 1
            if execution_result['status'] == 'success':
                self.metrics["successful_orders"] += 1
                self.metrics["total_volume"] += Decimal(str(adjusted_signal.get('quantity', 0)))
            else:
                self.metrics["failed_orders"] += 1
            
            return {
                'signal_id': signal_id,
                'status': execution_result['status'],
                'order_id': execution_result.get('order_id'),
                'executed_quantity': execution_result.get('quantity'),
                'execution_price': execution_result.get('price'),
                'message': execution_result.get('message')
            }
            
        except Exception as e:
            logger.error(f"Error processing trading signal: {e}")
            return {
                'signal_id': signal.get('signal_id'),
                'status': 'error',
                'reason': str(e)
            }
    
    async def _validate_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Validate trading signal format and content"""
        try:
            required_fields = ['symbol', 'action', 'quantity']
            for field in required_fields:
                if field not in signal:
                    return {
                        'valid': False,
                        'reason': f"Missing required field: {field}"
                    }
            
            # Validate action
            if signal['action'].lower() not in ['buy', 'sell']:
                return {
                    'valid': False,
                    'reason': f"Invalid action: {signal['action']}"
                }
            
            # Validate quantity
            try:
                quantity = Decimal(str(signal['quantity']))
                if quantity <= 0:
                    return {
                        'valid': False,
                        'reason': "Quantity must be positive"
                    }
            except:
                return {
                    'valid': False,
                    'reason': "Invalid quantity format"
                }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return {
                'valid': False,
                'reason': f"Validation error: {str(e)}"
            }
    
    async def _check_risk_limits(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Check if signal passes risk management rules"""
        try:
            # Basic risk checks
            symbol = signal['symbol']
            action = signal['action'].lower()
            quantity = Decimal(str(signal['quantity']))
            
            # Check minimum order size
            if self.portfolio_service:
                current_price = await self._get_current_price(symbol)
                if current_price:
                    order_value = quantity * current_price
                    if order_value < self.min_order_size_usd:
                        return {
                            'approved': False,
                            'reason': f"Order value ${order_value} below minimum ${self.min_order_size_usd}"
                        }
            
            # Check position size limits
            if self.portfolio_service:
                portfolio_value = await self._get_portfolio_value()
                if portfolio_value and current_price:
                    position_value = quantity * current_price
                    position_percent = position_value / portfolio_value
                    
                    if position_percent > self.max_position_size_percent:
                        return {
                            'approved': False,
                            'reason': f"Position size {position_percent:.1%} exceeds limit {self.max_position_size_percent:.1%}"
                        }
            
            # Additional risk checks can be added here
            if self.risk_service:
                risk_result = await self.risk_service.evaluate_trade_risk(signal)
                if not risk_result.get('approved', True):
                    return risk_result
            
            return {'approved': True}
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return {
                'approved': False,
                'reason': f"Risk check error: {str(e)}"
            }
    
    async def _calculate_position_size(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimal position size based on risk management"""
        try:
            # For now, use the signal as-is
            # Future: implement Kelly criterion, volatility-based sizing, etc.
            return signal
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return signal
    
    async def _execute_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual trade through order management service"""
        try:
            symbol = signal['symbol']
            action = signal['action'].lower()
            quantity = Decimal(str(signal['quantity']))
            
            # Create order
            order = {
                'order_id': str(uuid.uuid4()),
                'symbol': symbol,
                'side': action,
                'quantity': float(quantity),
                'order_type': signal.get('order_type', 'market'),
                'price': signal.get('price'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Submit to order management service
            if self.order_service:
                result = await self.order_service.submit_order(order)
                return result
            else:
                # Mock execution for testing
                return {
                    'status': 'success',
                    'order_id': order['order_id'],
                    'quantity': float(quantity),
                    'price': signal.get('price', 100.0),  # Mock price
                    'message': 'Trade executed (mock)'
                }
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def _get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current market price for symbol"""
        try:
            # This would typically fetch from market data service
            # For now, return a mock price
            mock_prices = {
                'BTC-USD': Decimal('45000'),
                'ETH-USD': Decimal('2500'),
                'AAPL': Decimal('150'),
                'TSLA': Decimal('200')
            }
            return mock_prices.get(symbol, Decimal('100'))
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    async def _get_portfolio_value(self) -> Optional[Decimal]:
        """Get current portfolio value"""
        try:
            if self.portfolio_service:
                portfolio = await self.portfolio_service.get_portfolio_summary()
                return Decimal(str(portfolio.get('total_value', 0)))
            else:
                # Mock portfolio value
                return Decimal('50000')
                
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
            return None
    
    async def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get list of active orders"""
        return list(self.active_orders.values())
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        try:
            if self.order_service:
                result = await self.order_service.cancel_order(order_id)
                return result
            else:
                # Mock cancellation
                if order_id in self.active_orders:
                    del self.active_orders[order_id]
                    return {'status': 'cancelled', 'order_id': order_id}
                else:
                    return {'status': 'not_found', 'order_id': order_id}
                    
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def get_trading_metrics(self) -> Dict[str, Any]:
        """Get trading performance metrics"""
        return {
            **self.metrics,
            "success_rate": self.metrics["successful_orders"] / max(self.metrics["total_orders"], 1),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": "trading_engine_service",
            "status": "running",
            "active_orders": len(self.active_orders),
            "pending_signals": len(self.pending_signals),
            "metrics": await self.get_trading_metrics(),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_trading_engine_service():
    """Factory function to create TradingEngineService instance"""
    return TradingEngineService()