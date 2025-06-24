"""
Real-Time Trading Orchestrator Service
Coordinates live trading operations across farms and agents with real-time execution
"""

import asyncio
import logging
import uuid
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import websockets
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class TradingMode(str, Enum):
    """Trading execution modes"""
    PAPER = "paper"
    LIVE = "live"
    SIMULATION = "simulation"
    BACKTEST = "backtest"

class OrderType(str, Enum):
    """Order types for real-time trading"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class OrderStatus(str, Enum):
    """Order execution status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class RealTimeOrder:
    """Real-time trading order"""
    order_id: str
    farm_id: str
    agent_id: str
    symbol: str
    side: str  # "buy" or "sell"
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal]
    stop_price: Optional[Decimal]
    time_in_force: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    filled_quantity: Decimal = Decimal('0')
    avg_fill_price: Optional[Decimal] = None
    fees: Decimal = Decimal('0')
    exchange: str = "internal"

@dataclass
class MarketData:
    """Real-time market data"""
    symbol: str
    price: Decimal
    bid: Decimal
    ask: Decimal
    volume: Decimal
    timestamp: datetime
    exchange: str

class RealTimeTradingOrchestrator:
    """
    Real-Time Trading Orchestrator
    Manages live trading operations with real-time execution and coordination
    """
    
    def __init__(self):
        self.active_orders: Dict[str, RealTimeOrder] = {}
        self.order_history: List[RealTimeOrder] = []
        self.market_data: Dict[str, MarketData] = {}
        self.trading_sessions: Dict[str, Dict[str, Any]] = {}
        self.websocket_connections: Dict[str, Any] = {}
        
        # Trading configuration
        self.trading_mode = TradingMode.PAPER
        self.max_orders_per_minute = 100
        self.max_position_size = Decimal('100000')
        self.risk_limits = {
            "max_daily_loss": Decimal('5000'),
            "max_position_concentration": Decimal('0.25'),  # 25%
            "max_leverage": Decimal('3.0')
        }
        
        # Performance tracking
        self.execution_metrics = {
            "orders_per_second": 0.0,
            "average_fill_time": 0.0,
            "slippage_average": Decimal('0'),
            "success_rate": Decimal('100'),
            "total_volume": Decimal('0'),
            "total_fees": Decimal('0')
        }
        
        # Real-time streams
        self.price_feeds: Dict[str, Any] = {}
        self.order_updates: asyncio.Queue = asyncio.Queue()
        self.market_updates: asyncio.Queue = asyncio.Queue()
        
        logger.info("🔄 Real-Time Trading Orchestrator initialized")
    
    async def initialize(self):
        """Initialize real-time trading systems"""
        # Start background tasks
        asyncio.create_task(self._market_data_stream())
        asyncio.create_task(self._order_execution_loop())
        asyncio.create_task(self._risk_monitoring_loop())
        asyncio.create_task(self._performance_tracking_loop())
        asyncio.create_task(self._websocket_broadcast_loop())
        
        # Initialize market data
        await self._initialize_market_feeds()
        
        logger.info("✅ Real-Time Trading Orchestrator ready")
    
    async def start_trading_session(self, session_config: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new real-time trading session"""
        try:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            
            session = {
                "id": session_id,
                "farm_id": session_config.get("farm_id"),
                "agent_ids": session_config.get("agent_ids", []),
                "trading_mode": session_config.get("mode", TradingMode.PAPER),
                "symbols": session_config.get("symbols", ["BTC/USD", "ETH/USD"]),
                "strategy": session_config.get("strategy", "balanced"),
                
                # Session limits
                "max_orders": session_config.get("max_orders", 50),
                "max_position_value": Decimal(str(session_config.get("max_position_value", 50000))),
                "stop_loss_pct": Decimal(str(session_config.get("stop_loss_pct", 5))),
                
                # State tracking
                "status": "active",
                "start_time": datetime.utcnow(),
                "orders": [],
                "positions": {},
                "pnl": Decimal('0'),
                "total_volume": Decimal('0'),
                
                # Real-time metrics
                "execution_stats": {
                    "orders_placed": 0,
                    "orders_filled": 0,
                    "avg_fill_time": 0.0,
                    "slippage": Decimal('0')
                }
            }
            
            self.trading_sessions[session_id] = session
            
            # Start session monitoring
            asyncio.create_task(self._monitor_trading_session(session_id))
            
            logger.info(f"🚀 Started trading session {session_id} for farm {session['farm_id']}")
            return session
            
        except Exception as e:
            logger.error(f"❌ Failed to start trading session: {e}")
            raise
    
    async def submit_real_time_order(self, order_config: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a real-time trading order"""
        try:
            order_id = f"order_{uuid.uuid4().hex[:8]}"
            
            # Create order
            order = RealTimeOrder(
                order_id=order_id,
                farm_id=order_config.get("farm_id"),
                agent_id=order_config.get("agent_id"),
                symbol=order_config.get("symbol"),
                side=order_config.get("side"),
                order_type=OrderType(order_config.get("order_type", "market")),
                quantity=Decimal(str(order_config.get("quantity"))),
                price=Decimal(str(order_config.get("price", 0))) if order_config.get("price") else None,
                stop_price=Decimal(str(order_config.get("stop_price", 0))) if order_config.get("stop_price") else None,
                time_in_force=order_config.get("time_in_force", "GTC"),
                status=OrderStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Risk checks
            risk_check = await self._validate_order_risk(order)
            if not risk_check["approved"]:
                order.status = OrderStatus.REJECTED
                logger.warning(f"⚠️ Order {order_id} rejected: {risk_check['reason']}")
                return {
                    "order_id": order_id,
                    "status": "rejected",
                    "reason": risk_check["reason"],
                    "order": order.__dict__
                }
            
            # Store order
            self.active_orders[order_id] = order
            
            # Queue for execution
            await self.order_updates.put({
                "type": "new_order",
                "order": order
            })
            
            # Execute immediately for market orders
            if order.order_type == OrderType.MARKET:
                await self._execute_market_order(order)
            
            logger.info(f"📈 Submitted {order.side} order {order_id}: {order.quantity} {order.symbol}")
            return {
                "order_id": order_id,
                "status": "submitted",
                "order": order.__dict__
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        try:
            if order_id not in self.active_orders:
                raise ValueError(f"Order {order_id} not found")
            
            order = self.active_orders[order_id]
            
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                raise ValueError(f"Cannot cancel order in status: {order.status}")
            
            # Update order status
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.utcnow()
            
            # Remove from active orders
            del self.active_orders[order_id]
            self.order_history.append(order)
            
            # Broadcast update
            await self._broadcast_order_update(order)
            
            logger.info(f"❌ Cancelled order {order_id}")
            return {
                "order_id": order_id,
                "status": "cancelled",
                "cancelled_at": order.updated_at
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel order: {e}")
            raise
    
    async def get_real_time_positions(self, farm_id: str) -> Dict[str, Any]:
        """Get real-time positions for a farm"""
        try:
            positions = {}
            total_value = Decimal('0')
            
            # Calculate positions from active orders and fills
            for order in list(self.active_orders.values()) + self.order_history:
                if order.farm_id != farm_id or order.status != OrderStatus.FILLED:
                    continue
                
                symbol = order.symbol
                if symbol not in positions:
                    positions[symbol] = {
                        "symbol": symbol,
                        "quantity": Decimal('0'),
                        "avg_price": Decimal('0'),
                        "market_value": Decimal('0'),
                        "unrealized_pnl": Decimal('0'),
                        "realized_pnl": Decimal('0')
                    }
                
                # Update position
                pos = positions[symbol]
                if order.side == "buy":
                    new_qty = pos["quantity"] + order.filled_quantity
                    if new_qty > 0:
                        pos["avg_price"] = (
                            (pos["avg_price"] * pos["quantity"] + order.avg_fill_price * order.filled_quantity) / new_qty
                        )
                    pos["quantity"] = new_qty
                else:  # sell
                    pos["quantity"] -= order.filled_quantity
                
                # Calculate market value and PnL
                current_price = self._get_current_price(symbol)
                pos["market_value"] = pos["quantity"] * current_price
                pos["unrealized_pnl"] = (current_price - pos["avg_price"]) * pos["quantity"]
                
                total_value += pos["market_value"]
            
            return {
                "farm_id": farm_id,
                "positions": positions,
                "total_value": total_value,
                "position_count": len(positions),
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get positions: {e}")
            raise
    
    async def get_trading_performance(self, farm_id: str) -> Dict[str, Any]:
        """Get real-time trading performance metrics"""
        try:
            # Filter orders for this farm
            farm_orders = [
                order for order in list(self.active_orders.values()) + self.order_history
                if order.farm_id == farm_id
            ]
            
            if not farm_orders:
                return {
                    "farm_id": farm_id,
                    "total_orders": 0,
                    "performance": "no_data"
                }
            
            # Calculate metrics
            filled_orders = [o for o in farm_orders if o.status == OrderStatus.FILLED]
            total_volume = sum(o.quantity * (o.avg_fill_price or Decimal('0')) for o in filled_orders)
            total_fees = sum(o.fees for o in filled_orders)
            
            # Calculate PnL
            positions = await self.get_real_time_positions(farm_id)
            unrealized_pnl = sum(pos["unrealized_pnl"] for pos in positions["positions"].values())
            
            # Win rate calculation (simplified)
            profitable_trades = sum(1 for pos in positions["positions"].values() if pos["unrealized_pnl"] > 0)
            total_positions = len(positions["positions"])
            win_rate = (profitable_trades / total_positions * 100) if total_positions > 0 else 0
            
            return {
                "farm_id": farm_id,
                "period": "real_time",
                "total_orders": len(farm_orders),
                "filled_orders": len(filled_orders),
                "total_volume": total_volume,
                "total_fees": total_fees,
                "unrealized_pnl": unrealized_pnl,
                "win_rate": win_rate,
                "execution_metrics": {
                    "avg_fill_time": self._calculate_avg_fill_time(filled_orders),
                    "success_rate": len(filled_orders) / len(farm_orders) * 100 if farm_orders else 0,
                    "orders_per_hour": len(farm_orders)  # Simplified
                },
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get performance: {e}")
            raise
    
    # Private helper methods
    
    async def _execute_market_order(self, order: RealTimeOrder):
        """Execute a market order immediately"""
        try:
            # Get current market price
            current_price = self._get_current_price(order.symbol)
            
            # Simulate execution (in real implementation, this would hit exchange APIs)
            execution_price = current_price
            if order.side == "buy":
                execution_price = current_price * Decimal('1.001')  # 0.1% slippage
            else:
                execution_price = current_price * Decimal('0.999')
            
            # Fill the order
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.avg_fill_price = execution_price
            order.fees = order.quantity * execution_price * Decimal('0.001')  # 0.1% fee
            order.updated_at = datetime.utcnow()
            
            # Move to history
            if order.order_id in self.active_orders:
                del self.active_orders[order.order_id]
            self.order_history.append(order)
            
            # Broadcast update
            await self._broadcast_order_update(order)
            
            logger.info(f"✅ Executed market order {order.order_id}: {order.filled_quantity} @ {execution_price}")
            
        except Exception as e:
            logger.error(f"❌ Failed to execute market order: {e}")
            order.status = OrderStatus.REJECTED
    
    async def _validate_order_risk(self, order: RealTimeOrder) -> Dict[str, Any]:
        """Validate order against risk limits"""
        try:
            # Position size check
            order_value = order.quantity * (order.price or self._get_current_price(order.symbol))
            if order_value > self.max_position_size:
                return {
                    "approved": False,
                    "reason": f"Order value {order_value} exceeds max position size {self.max_position_size}"
                }
            
            # Daily loss check (simplified)
            farm_performance = await self.get_trading_performance(order.farm_id)
            if farm_performance.get("unrealized_pnl", 0) < -self.risk_limits["max_daily_loss"]:
                return {
                    "approved": False,
                    "reason": "Daily loss limit exceeded"
                }
            
            return {"approved": True, "reason": "Risk checks passed"}
            
        except Exception as e:
            logger.error(f"❌ Risk validation error: {e}")
            return {"approved": False, "reason": f"Risk validation error: {e}"}
    
    def _get_current_price(self, symbol: str) -> Decimal:
        """Get current market price for symbol"""
        if symbol in self.market_data:
            return self.market_data[symbol].price
        
        # Mock prices for testing
        mock_prices = {
            "BTC/USD": Decimal('45000'),
            "ETH/USD": Decimal('3000'),
            "SOL/USD": Decimal('100'),
            "AAPL": Decimal('180'),
            "TSLA": Decimal('250')
        }
        return mock_prices.get(symbol, Decimal('100'))
    
    def _calculate_avg_fill_time(self, orders: List[RealTimeOrder]) -> float:
        """Calculate average fill time for orders"""
        if not orders:
            return 0.0
        
        fill_times = []
        for order in orders:
            if order.status == OrderStatus.FILLED:
                fill_time = (order.updated_at - order.created_at).total_seconds()
                fill_times.append(fill_time)
        
        return sum(fill_times) / len(fill_times) if fill_times else 0.0
    
    async def _broadcast_order_update(self, order: RealTimeOrder):
        """Broadcast order update via WebSocket"""
        try:
            update = {
                "type": "order_update",
                "order_id": order.order_id,
                "farm_id": order.farm_id,
                "status": order.status.value,
                "timestamp": order.updated_at.isoformat()
            }
            
            # Add to broadcast queue
            await self.market_updates.put(update)
            
        except Exception as e:
            logger.error(f"❌ Broadcast error: {e}")
    
    # Background tasks
    
    async def _market_data_stream(self):
        """Background task for market data updates"""
        while True:
            try:
                await asyncio.sleep(1)  # 1 second updates
                
                # Mock market data updates
                symbols = ["BTC/USD", "ETH/USD", "SOL/USD", "AAPL", "TSLA"]
                for symbol in symbols:
                    current_price = self._get_current_price(symbol)
                    # Simulate price movement
                    change_pct = (Decimal(str(__import__('random').uniform(-0.01, 0.01))))
                    new_price = current_price * (Decimal('1') + change_pct)
                    
                    self.market_data[symbol] = MarketData(
                        symbol=symbol,
                        price=new_price,
                        bid=new_price * Decimal('0.999'),
                        ask=new_price * Decimal('1.001'),
                        volume=Decimal('1000'),
                        timestamp=datetime.utcnow(),
                        exchange="mock"
                    )
                
            except Exception as e:
                logger.error(f"❌ Market data stream error: {e}")
    
    async def _order_execution_loop(self):
        """Background task for order execution"""
        while True:
            try:
                # Process order updates
                update = await self.order_updates.get()
                
                if update["type"] == "new_order":
                    order = update["order"]
                    if order.order_type == OrderType.LIMIT:
                        # Check if limit order can be filled
                        current_price = self._get_current_price(order.symbol)
                        if ((order.side == "buy" and current_price <= order.price) or
                            (order.side == "sell" and current_price >= order.price)):
                            await self._execute_market_order(order)
                
            except Exception as e:
                logger.error(f"❌ Order execution error: {e}")
    
    async def _risk_monitoring_loop(self):
        """Background task for continuous risk monitoring"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Monitor all active sessions
                for session_id, session in self.trading_sessions.items():
                    if session["status"] != "active":
                        continue
                    
                    # Check position limits
                    positions = await self.get_real_time_positions(session["farm_id"])
                    if positions["total_value"] > session["max_position_value"]:
                        logger.warning(f"⚠️ Position limit exceeded for session {session_id}")
                        # Could auto-close positions here
                
            except Exception as e:
                logger.error(f"❌ Risk monitoring error: {e}")
    
    async def _performance_tracking_loop(self):
        """Background task for performance metrics"""
        while True:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Update global execution metrics
                filled_orders = [o for o in self.order_history if o.status == OrderStatus.FILLED]
                if filled_orders:
                    self.execution_metrics["average_fill_time"] = self._calculate_avg_fill_time(filled_orders)
                    self.execution_metrics["total_volume"] = sum(
                        o.quantity * (o.avg_fill_price or Decimal('0')) for o in filled_orders
                    )
                    self.execution_metrics["total_fees"] = sum(o.fees for o in filled_orders)
                
            except Exception as e:
                logger.error(f"❌ Performance tracking error: {e}")
    
    async def _websocket_broadcast_loop(self):
        """Background task for WebSocket broadcasts"""
        while True:
            try:
                # Broadcast market updates
                update = await self.market_updates.get()
                
                # Here you would broadcast to connected WebSocket clients
                # For now, just log
                logger.debug(f"📡 Broadcasting: {update['type']}")
                
            except Exception as e:
                logger.error(f"❌ WebSocket broadcast error: {e}")
    
    async def _monitor_trading_session(self, session_id: str):
        """Monitor a specific trading session"""
        while session_id in self.trading_sessions:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                session = self.trading_sessions[session_id]
                if session["status"] != "active":
                    break
                
                # Update session metrics
                performance = await self.get_trading_performance(session["farm_id"])
                session["pnl"] = performance.get("unrealized_pnl", Decimal('0'))
                session["total_volume"] = performance.get("total_volume", Decimal('0'))
                
                logger.debug(f"📊 Session {session_id} PnL: {session['pnl']}")
                
            except Exception as e:
                logger.error(f"❌ Session monitoring error: {e}")
    
    async def _initialize_market_feeds(self):
        """Initialize market data feeds"""
        # Initialize with mock data
        symbols = ["BTC/USD", "ETH/USD", "SOL/USD", "AAPL", "TSLA"]
        for symbol in symbols:
            self.market_data[symbol] = MarketData(
                symbol=symbol,
                price=self._get_current_price(symbol),
                bid=self._get_current_price(symbol) * Decimal('0.999'),
                ask=self._get_current_price(symbol) * Decimal('1.001'),
                volume=Decimal('1000'),
                timestamp=datetime.utcnow(),
                exchange="mock"
            )
        
        logger.info(f"✅ Initialized market feeds for {len(symbols)} symbols")

# Service factory
def create_real_time_trading_orchestrator() -> RealTimeTradingOrchestrator:
    """Create and configure real-time trading orchestrator"""
    return RealTimeTradingOrchestrator()