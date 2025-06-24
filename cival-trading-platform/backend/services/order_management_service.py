"""
Order Management Service
Handles order lifecycle, execution, and tracking
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"

class OrderManagementService:
    """Service for managing order lifecycle and execution"""
    
    def __init__(self, execution_service=None, portfolio_service=None):
        self.execution_service = execution_service
        self.portfolio_service = portfolio_service
        
        # Order tracking
        self.orders = {}
        self.order_history = []
        self.active_orders = {}
        
        # Configuration
        self.max_order_age_minutes = 1440  # 24 hours
        self.retry_failed_orders = True
        self.max_retry_attempts = 3
        
        # Performance metrics
        self.metrics = {
            "total_orders": 0,
            "filled_orders": 0,
            "cancelled_orders": 0,
            "rejected_orders": 0,
            "avg_fill_time": 0.0,
            "fill_rate": 0.0
        }
        
    async def submit_order(self, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a new order for execution
        
        Args:
            order_request: Order details (symbol, side, quantity, type, etc.)
        """
        try:
            # Generate order ID if not provided
            order_id = order_request.get('order_id', str(uuid.uuid4()))
            
            # Create order object
            order = {
                'order_id': order_id,
                'symbol': order_request['symbol'],
                'side': order_request['side'].lower(),
                'quantity': Decimal(str(order_request['quantity'])),
                'order_type': order_request.get('order_type', 'market'),
                'price': Decimal(str(order_request['price'])) if order_request.get('price') else None,
                'stop_price': Decimal(str(order_request['stop_price'])) if order_request.get('stop_price') else None,
                'status': OrderStatus.PENDING.value,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'filled_quantity': Decimal('0'),
                'avg_fill_price': None,
                'fees': Decimal('0'),
                'exchange': order_request.get('exchange', 'default'),
                'time_in_force': order_request.get('time_in_force', 'GTC'),
                'client_order_id': order_request.get('client_order_id'),
                'retry_count': 0
            }
            
            # Validate order
            validation_result = await self._validate_order(order)
            if not validation_result['valid']:
                order['status'] = OrderStatus.REJECTED.value
                order['rejection_reason'] = validation_result['reason']
                self.orders[order_id] = order
                self.metrics["rejected_orders"] += 1
                return {
                    'status': 'rejected',
                    'order_id': order_id,
                    'reason': validation_result['reason']
                }
            
            # Store order
            self.orders[order_id] = order
            self.active_orders[order_id] = order
            self.metrics["total_orders"] += 1
            
            # Submit to execution service
            execution_result = await self._execute_order(order)
            
            return {
                'status': 'submitted',
                'order_id': order_id,
                'execution_result': execution_result
            }
            
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            return {
                'status': 'error',
                'reason': str(e)
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        try:
            if order_id not in self.orders:
                return {
                    'status': 'not_found',
                    'order_id': order_id,
                    'message': 'Order not found'
                }
            
            order = self.orders[order_id]
            
            # Check if order can be cancelled
            if order['status'] in ['filled', 'cancelled', 'rejected']:
                return {
                    'status': 'cannot_cancel',
                    'order_id': order_id,
                    'message': f"Order already {order['status']}"
                }
            
            # Cancel with execution service
            if self.execution_service:
                cancel_result = await self.execution_service.cancel_order(order_id)
                if not cancel_result.get('success', False):
                    return {
                        'status': 'cancel_failed',
                        'order_id': order_id,
                        'reason': cancel_result.get('message', 'Unknown error')
                    }
            
            # Update order status
            order['status'] = OrderStatus.CANCELLED.value
            order['updated_at'] = datetime.now(timezone.utc)
            order['cancellation_time'] = datetime.now(timezone.utc)
            
            # Remove from active orders
            if order_id in self.active_orders:
                del self.active_orders[order_id]
            
            self.metrics["cancelled_orders"] += 1
            
            return {
                'status': 'cancelled',
                'order_id': order_id,
                'cancelled_at': order['cancellation_time'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return {
                'status': 'error',
                'order_id': order_id,
                'reason': str(e)
            }
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an order"""
        try:
            if order_id not in self.orders:
                return None
            
            order = self.orders[order_id]
            
            # Get latest status from execution service if active
            if order['status'] in ['pending', 'submitted', 'partially_filled']:
                if self.execution_service:
                    try:
                        status_update = await self.execution_service.get_order_status(order_id)
                        if status_update:
                            await self._update_order_status(order_id, status_update)
                    except Exception as e:
                        logger.warning(f"Could not get status update for order {order_id}: {e}")
            
            return {
                'order_id': order_id,
                'status': order['status'],
                'symbol': order['symbol'],
                'side': order['side'],
                'quantity': float(order['quantity']),
                'filled_quantity': float(order['filled_quantity']),
                'avg_fill_price': float(order['avg_fill_price']) if order['avg_fill_price'] else None,
                'created_at': order['created_at'].isoformat(),
                'updated_at': order['updated_at'].isoformat(),
                'fees': float(order['fees'])
            }
            
        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {e}")
            return None
    
    async def get_orders(
        self, 
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get orders with optional filtering"""
        try:
            orders = list(self.orders.values())
            
            # Apply filters
            if status:
                orders = [o for o in orders if o['status'] == status]
            
            if symbol:
                orders = [o for o in orders if o['symbol'] == symbol]
            
            # Sort by creation time (newest first)
            orders.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Limit results
            orders = orders[:limit]
            
            # Format for API response
            return [
                {
                    'order_id': order['order_id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'quantity': float(order['quantity']),
                    'order_type': order['order_type'],
                    'status': order['status'],
                    'filled_quantity': float(order['filled_quantity']),
                    'avg_fill_price': float(order['avg_fill_price']) if order['avg_fill_price'] else None,
                    'created_at': order['created_at'].isoformat(),
                    'updated_at': order['updated_at'].isoformat()
                }
                for order in orders
            ]
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    async def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get all active (non-terminal) orders"""
        return await self.get_orders(status=None)  # Will filter in implementation
    
    async def _validate_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order before submission"""
        try:
            # Check required fields
            required_fields = ['symbol', 'side', 'quantity', 'order_type']
            for field in required_fields:
                if not order.get(field):
                    return {
                        'valid': False,
                        'reason': f"Missing required field: {field}"
                    }
            
            # Validate side
            if order['side'] not in ['buy', 'sell']:
                return {
                    'valid': False,
                    'reason': f"Invalid side: {order['side']}"
                }
            
            # Validate quantity
            if order['quantity'] <= 0:
                return {
                    'valid': False,
                    'reason': "Quantity must be positive"
                }
            
            # Validate price for limit orders
            if order['order_type'] == 'limit' and not order.get('price'):
                return {
                    'valid': False,
                    'reason': "Limit orders require a price"
                }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return {
                'valid': False,
                'reason': f"Validation error: {str(e)}"
            }
    
    async def _execute_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order through execution service"""
        try:
            order_id = order['order_id']
            
            # Update status to submitted
            order['status'] = OrderStatus.SUBMITTED.value
            order['updated_at'] = datetime.now(timezone.utc)
            
            if self.execution_service:
                # Submit to real execution service
                result = await self.execution_service.execute_order(order)
                return result
            else:
                # Mock execution for testing
                await asyncio.sleep(0.1)  # Simulate processing time
                
                # Mock successful execution
                fill_price = order.get('price', Decimal('100.0'))
                order['status'] = OrderStatus.FILLED.value
                order['filled_quantity'] = order['quantity']
                order['avg_fill_price'] = fill_price
                order['updated_at'] = datetime.now(timezone.utc)
                order['fill_time'] = datetime.now(timezone.utc)
                
                # Remove from active orders
                if order_id in self.active_orders:
                    del self.active_orders[order_id]
                
                self.metrics["filled_orders"] += 1
                
                return {
                    'status': 'filled',
                    'fill_price': float(fill_price),
                    'fill_quantity': float(order['quantity']),
                    'fill_time': order['fill_time'].isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error executing order {order['order_id']}: {e}")
            order['status'] = OrderStatus.REJECTED.value
            order['rejection_reason'] = str(e)
            order['updated_at'] = datetime.now(timezone.utc)
            return {
                'status': 'rejected',
                'reason': str(e)
            }
    
    async def _update_order_status(self, order_id: str, status_update: Dict[str, Any]):
        """Update order with status information from execution service"""
        try:
            if order_id not in self.orders:
                return
            
            order = self.orders[order_id]
            
            # Update fields from status update
            if 'status' in status_update:
                order['status'] = status_update['status']
            
            if 'filled_quantity' in status_update:
                order['filled_quantity'] = Decimal(str(status_update['filled_quantity']))
            
            if 'avg_fill_price' in status_update:
                order['avg_fill_price'] = Decimal(str(status_update['avg_fill_price']))
            
            if 'fees' in status_update:
                order['fees'] = Decimal(str(status_update['fees']))
            
            order['updated_at'] = datetime.now(timezone.utc)
            
            # Remove from active orders if terminal status
            if order['status'] in ['filled', 'cancelled', 'rejected']:
                if order_id in self.active_orders:
                    del self.active_orders[order_id]
                
                if order['status'] == 'filled':
                    self.metrics["filled_orders"] += 1
                elif order['status'] == 'cancelled':
                    self.metrics["cancelled_orders"] += 1
                elif order['status'] == 'rejected':
                    self.metrics["rejected_orders"] += 1
            
        except Exception as e:
            logger.error(f"Error updating order status for {order_id}: {e}")
    
    async def get_order_metrics(self) -> Dict[str, Any]:
        """Get order management performance metrics"""
        try:
            total_orders = self.metrics["total_orders"]
            if total_orders > 0:
                self.metrics["fill_rate"] = self.metrics["filled_orders"] / total_orders
            
            return {
                **self.metrics,
                "active_orders": len(self.active_orders),
                "total_orders_managed": len(self.orders),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating order metrics: {e}")
            return self.metrics
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": "order_management_service",
            "status": "running",
            "active_orders": len(self.active_orders),
            "total_orders": len(self.orders),
            "metrics": await self.get_order_metrics(),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_order_management_service():
    """Factory function to create OrderManagementService instance"""
    return OrderManagementService()