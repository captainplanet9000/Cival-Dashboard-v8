"""
Phase 10: Live Trading Execution and Order Management Service
Real-time order execution, trade management, and exchange connectivity
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import logging
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from enum import Enum
import aiohttp
import websockets

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.trading_strategy_models import (
    TradingSignal, TradingPosition, OrderType, PositionSide, LiveTradingRequest
)
from services.risk_management_service import get_risk_management_service
from services.portfolio_management_service import get_portfolio_management_service
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionQuality(str, Enum):
    """Execution quality classification"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class TradingOrder(BaseModel):
    """Trading order model"""
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    agent_id: str
    portfolio_id: str
    
    # Order details
    symbol: str
    side: PositionSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    
    # Stop/limit parameters
    stop_price: Optional[Decimal] = None
    limit_price: Optional[Decimal] = None
    trailing_amount: Optional[Decimal] = None
    
    # Execution details
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Optional[Decimal] = None
    
    # Risk and validation
    risk_validated: bool = False
    position_size_validated: bool = False
    max_slippage: float = 0.005  # 0.5%
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Exchange details
    exchange: str = "binance"
    exchange_order_id: Optional[str] = None
    
    # Execution quality
    expected_price: Optional[Decimal] = None
    slippage: Optional[float] = None
    execution_quality: Optional[ExecutionQuality] = None
    
    # Metadata
    signal_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    child_order_ids: List[str] = Field(default_factory=list)


class OrderExecution(BaseModel):
    """Order execution record"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    
    # Execution details
    quantity: Decimal
    price: Decimal
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Costs
    commission: Decimal = Decimal("0")
    fee_currency: str = "USD"
    
    # Exchange details
    exchange_execution_id: Optional[str] = None
    trade_id: Optional[str] = None
    
    # Quality metrics
    market_impact: Optional[float] = None
    timing_alpha: Optional[float] = None


class ExchangeConnector:
    """Base exchange connector interface"""
    
    def __init__(self, exchange_name: str, api_key: str = "", secret: str = ""):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret = secret
        self.connected = False
        self.last_heartbeat = None
        
    async def connect(self):
        """Connect to exchange"""
        self.connected = True
        self.last_heartbeat = datetime.now(timezone.utc)
        logger.info(f"Connected to {self.exchange_name}")
        
    async def disconnect(self):
        """Disconnect from exchange"""
        self.connected = False
        logger.info(f"Disconnected from {self.exchange_name}")
        
    async def submit_order(self, order: TradingOrder) -> Dict[str, Any]:
        """Submit order to exchange"""
        # Simulate order submission
        await asyncio.sleep(0.1)  # Simulate network latency
        
        exchange_order_id = f"{self.exchange_name}_{uuid.uuid4().hex[:8]}"
        
        return {
            "exchange_order_id": exchange_order_id,
            "status": "submitted",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    async def cancel_order(self, order_id: str, exchange_order_id: str) -> bool:
        """Cancel order on exchange"""
        await asyncio.sleep(0.05)
        return True
        
    async def get_order_status(self, exchange_order_id: str) -> Dict[str, Any]:
        """Get order status from exchange"""
        # Simulate order status check
        return {
            "status": "filled",
            "filled_quantity": "100.0",
            "average_price": "50000.0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    async def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balance"""
        # Simulate balance check
        return {
            "USD": Decimal("10000.0"),
            "BTC": Decimal("0.1"),
            "ETH": Decimal("2.0")
        }


class BinanceConnector(ExchangeConnector):
    """Binance exchange connector"""
    
    def __init__(self, api_key: str = "", secret: str = ""):
        super().__init__("binance", api_key, secret)
        self.base_url = "https://api.binance.com"
        self.ws_url = "wss://stream.binance.com:9443/ws"
        
    async def submit_order(self, order: TradingOrder) -> Dict[str, Any]:
        """Submit order to Binance"""
        # In production, this would make actual API calls to Binance
        order_data = {
            "symbol": order.symbol.replace("USD", "USDT"),  # Convert to Binance format
            "side": "BUY" if order.side == PositionSide.LONG else "SELL",
            "type": order.order_type.value.upper(),
            "quantity": str(order.quantity),
            "timeInForce": "GTC"  # Good Till Cancelled
        }
        
        if order.order_type == OrderType.LIMIT and order.price:
            order_data["price"] = str(order.price)
            
        # Simulate API call
        await asyncio.sleep(0.1)
        
        return {
            "exchange_order_id": f"binance_{uuid.uuid4().hex[:12]}",
            "status": "submitted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_order_id": order.order_id
        }


class OrderManager:
    """Order lifecycle management"""
    
    def __init__(self):
        self.active_orders: Dict[str, TradingOrder] = {}
        self.order_history: List[TradingOrder] = []
        self.executions: Dict[str, List[OrderExecution]] = defaultdict(list)
        
    def add_order(self, order: TradingOrder):
        """Add order to management"""
        self.active_orders[order.order_id] = order
        
    def update_order_status(self, order_id: str, status: OrderStatus, **kwargs):
        """Update order status"""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            order.status = status
            
            for key, value in kwargs.items():
                if hasattr(order, key):
                    setattr(order, key, value)
            
            # Move to history if completed
            if status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
                self.order_history.append(order)
                del self.active_orders[order_id]
                
    def add_execution(self, order_id: str, execution: OrderExecution):
        """Add execution to order"""
        self.executions[order_id].append(execution)
        
        # Update order fill status
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            total_filled = sum(ex.quantity for ex in self.executions[order_id])
            order.filled_quantity = total_filled
            
            if total_filled >= order.quantity:
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now(timezone.utc)
                
                # Calculate average fill price
                total_value = sum(ex.quantity * ex.price for ex in self.executions[order_id])
                order.average_fill_price = total_value / total_filled
            elif total_filled > 0:
                order.status = OrderStatus.PARTIAL_FILLED


class ExecutionAlgorithm:
    """Smart order execution algorithms"""
    
    @staticmethod
    def calculate_twap_schedule(
        total_quantity: Decimal,
        duration_minutes: int,
        interval_minutes: int = 5
    ) -> List[Tuple[datetime, Decimal]]:
        """Calculate TWAP (Time-Weighted Average Price) execution schedule"""
        num_intervals = duration_minutes // interval_minutes
        quantity_per_interval = total_quantity / num_intervals
        
        schedule = []
        start_time = datetime.now(timezone.utc)
        
        for i in range(num_intervals):
            execution_time = start_time + timedelta(minutes=i * interval_minutes)
            schedule.append((execution_time, quantity_per_interval))
            
        return schedule
    
    @staticmethod
    def calculate_vwap_weights(
        volume_profile: List[float],
        total_quantity: Decimal
    ) -> List[Decimal]:
        """Calculate VWAP (Volume-Weighted Average Price) execution weights"""
        total_volume = sum(volume_profile)
        weights = []
        
        for volume in volume_profile:
            weight = volume / total_volume
            quantity = total_quantity * Decimal(str(weight))
            weights.append(quantity)
            
        return weights
    
    @staticmethod
    def calculate_participation_rate(
        market_volume: Decimal,
        participation_rate: float = 0.1
    ) -> Decimal:
        """Calculate maximum order size based on market participation rate"""
        return market_volume * Decimal(str(participation_rate))


class LiveTradingService:
    """
    Live trading execution and order management service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
        # Order management
        self.order_manager = OrderManager()
        self.execution_algorithms = ExecutionAlgorithm()
        
        # Exchange connections
        self.exchanges: Dict[str, ExchangeConnector] = {}
        self.default_exchange = "binance"
        
        # Trading state
        self.active_strategies: Dict[str, Dict[str, Any]] = {}
        self.trading_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Risk and limits
        self.daily_limits: Dict[str, Dict[str, Decimal]] = defaultdict(dict)
        self.position_limits: Dict[str, Dict[str, Decimal]] = defaultdict(dict)
        
        # Performance tracking
        self.execution_metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.slippage_history: deque = deque(maxlen=1000)
        
        # Configuration
        self.order_check_interval = 5      # 5 seconds
        self.risk_check_interval = 30      # 30 seconds
        self.heartbeat_interval = 60       # 1 minute
        self.max_order_age = 3600          # 1 hour
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the live trading service"""
        try:
            logger.info("Initializing Live Trading Service...")
            
            # Initialize exchange connections
            await self._initialize_exchanges()
            
            # Load active trading sessions
            await self._load_trading_sessions()
            
            # Start background tasks
            asyncio.create_task(self._order_monitoring_loop())
            asyncio.create_task(self._risk_monitoring_loop())
            asyncio.create_task(self._exchange_heartbeat_loop())
            asyncio.create_task(self._execution_quality_loop())
            
            logger.info("Live Trading Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Live Trading Service: {e}")
            raise
    
    async def activate_strategy_trading(self, request: LiveTradingRequest) -> Dict[str, Any]:
        """Activate live trading for a strategy"""
        try:
            logger.info(f"Activating live trading for strategy {request.strategy_id}")
            
            # Validate strategy and portfolio
            portfolio_service = await get_portfolio_management_service()
            risk_service = await get_risk_management_service()
            
            # Create trading session
            session_id = str(uuid.uuid4())
            session = {
                "session_id": session_id,
                "strategy_id": request.strategy_id,
                "allocated_capital": request.allocated_capital,
                "max_position_size": request.max_position_size,
                "risk_per_trade": request.risk_per_trade,
                "daily_loss_limit": request.daily_loss_limit,
                "max_open_positions": request.max_open_positions,
                "auto_start": request.auto_start,
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "orders_placed": 0,
                "total_pnl": Decimal("0"),
                "daily_pnl": Decimal("0")
            }
            
            self.trading_sessions[session_id] = session
            self.active_strategies[request.strategy_id] = session
            
            # Set up risk limits
            await self._setup_strategy_risk_limits(request.strategy_id, request)
            
            # Save to database
            await self._save_trading_session(session)
            
            logger.info(f"Live trading activated for strategy {request.strategy_id} with session {session_id}")
            
            return {
                "session_id": session_id,
                "status": "activated",
                "strategy_id": request.strategy_id,
                "allocated_capital": float(request.allocated_capital),
                "message": "Live trading activated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to activate live trading for strategy {request.strategy_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Live trading activation failed: {str(e)}")
    
    async def execute_signal(self, signal: TradingSignal, portfolio_id: str) -> Dict[str, Any]:
        """Execute a trading signal"""
        try:
            logger.info(f"Executing signal {signal.signal_id} for strategy {signal.strategy_id}")
            
            # Validate trading session is active
            if signal.strategy_id not in self.active_strategies:
                raise HTTPException(status_code=400, detail="Strategy not active for live trading")
            
            session = self.active_strategies[signal.strategy_id]
            
            # Risk validation
            risk_service = await get_risk_management_service()
            
            # Calculate position size
            position_size, sizing_details = await risk_service.calculate_position_size(
                signal, portfolio_id, signal.strategy_id, "adaptive"
            )
            
            if position_size == 0:
                return {
                    "status": "rejected",
                    "reason": "Position size calculation resulted in zero",
                    "signal_id": signal.signal_id
                }
            
            # Trade risk validation
            risk_validation = await risk_service.validate_trade_risk(
                portfolio_id, signal, position_size
            )
            
            if not risk_validation["approved"]:
                return {
                    "status": "rejected",
                    "reason": "Trade rejected by risk management",
                    "signal_id": signal.signal_id,
                    "risk_issues": risk_validation.get("critical_issues", [])
                }
            
            # Create trading order
            order = await self._create_order_from_signal(signal, position_size, portfolio_id, session)
            
            # Submit order to exchange
            execution_result = await self._submit_order(order)
            
            if execution_result["success"]:
                # Update session metrics
                session["orders_placed"] += 1
                
                # Track execution
                await self._track_execution_metrics(order, execution_result)
                
                logger.info(f"Signal {signal.signal_id} executed successfully as order {order.order_id}")
                
                return {
                    "status": "executed",
                    "order_id": order.order_id,
                    "signal_id": signal.signal_id,
                    "position_size": float(position_size),
                    "expected_fill_price": float(order.price) if order.price else None,
                    "exchange_order_id": execution_result.get("exchange_order_id")
                }
            else:
                return {
                    "status": "failed",
                    "reason": execution_result.get("error", "Order submission failed"),
                    "signal_id": signal.signal_id
                }
                
        except Exception as e:
            logger.error(f"Failed to execute signal {signal.signal_id}: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "signal_id": signal.signal_id
            }
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order"""
        try:
            if order_id not in self.order_manager.active_orders:
                return False
            
            order = self.order_manager.active_orders[order_id]
            
            if order.status not in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]:
                return False
            
            # Cancel on exchange
            exchange = self.exchanges.get(order.exchange)
            if exchange and order.exchange_order_id:
                success = await exchange.cancel_order(order_id, order.exchange_order_id)
                
                if success:
                    self.order_manager.update_order_status(order_id, OrderStatus.CANCELLED)
                    logger.info(f"Order {order_id} cancelled successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status and details"""
        try:
            # Check active orders
            if order_id in self.order_manager.active_orders:
                order = self.order_manager.active_orders[order_id]
            else:
                # Check order history
                order = next((o for o in self.order_manager.order_history if o.order_id == order_id), None)
            
            if not order:
                return None
            
            executions = self.order_manager.executions.get(order_id, [])
            
            return {
                "order_id": order_id,
                "status": order.status.value,
                "symbol": order.symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": float(order.quantity),
                "filled_quantity": float(order.filled_quantity),
                "average_fill_price": float(order.average_fill_price) if order.average_fill_price else None,
                "created_at": order.created_at.isoformat(),
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "executions": [
                    {
                        "quantity": float(ex.quantity),
                        "price": float(ex.price),
                        "timestamp": ex.timestamp.isoformat(),
                        "commission": float(ex.commission)
                    }
                    for ex in executions
                ],
                "slippage": order.slippage,
                "execution_quality": order.execution_quality.value if order.execution_quality else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return None
    
    async def get_trading_session_status(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get trading session status for strategy"""
        try:
            if strategy_id not in self.active_strategies:
                return None
            
            session = self.active_strategies[strategy_id]
            
            # Get current positions
            portfolio_service = await get_portfolio_management_service()
            
            # Calculate session metrics
            active_orders_count = len([
                o for o in self.order_manager.active_orders.values()
                if o.strategy_id == strategy_id
            ])
            
            return {
                "session_id": session["session_id"],
                "strategy_id": strategy_id,
                "status": session["status"],
                "allocated_capital": float(session["allocated_capital"]),
                "orders_placed": session["orders_placed"],
                "active_orders": active_orders_count,
                "total_pnl": float(session["total_pnl"]),
                "daily_pnl": float(session["daily_pnl"]),
                "created_at": session["created_at"].isoformat(),
                "risk_limits": self.daily_limits.get(strategy_id, {}),
                "performance_metrics": self._calculate_session_performance_metrics(strategy_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to get trading session status for strategy {strategy_id}: {e}")
            return None
    
    async def pause_strategy_trading(self, strategy_id: str) -> bool:
        """Pause live trading for a strategy"""
        try:
            if strategy_id not in self.active_strategies:
                return False
            
            session = self.active_strategies[strategy_id]
            session["status"] = "paused"
            
            logger.info(f"Live trading paused for strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause trading for strategy {strategy_id}: {e}")
            return False
    
    async def resume_strategy_trading(self, strategy_id: str) -> bool:
        """Resume live trading for a strategy"""
        try:
            if strategy_id not in self.active_strategies:
                return False
            
            session = self.active_strategies[strategy_id]
            session["status"] = "active"
            
            logger.info(f"Live trading resumed for strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume trading for strategy {strategy_id}: {e}")
            return False
    
    # Background monitoring loops
    
    async def _order_monitoring_loop(self):
        """Order status monitoring loop"""
        while not self._shutdown:
            try:
                # Check status of all active orders
                for order_id, order in list(self.order_manager.active_orders.items()):
                    await self._check_order_status(order)
                
                # Clean up expired orders
                await self._cleanup_expired_orders()
                
                await asyncio.sleep(self.order_check_interval)
                
            except Exception as e:
                logger.error(f"Error in order monitoring loop: {e}")
                await asyncio.sleep(self.order_check_interval)
    
    async def _risk_monitoring_loop(self):
        """Risk monitoring and limits enforcement"""
        while not self._shutdown:
            try:
                # Check all active trading sessions
                for strategy_id, session in self.active_strategies.items():
                    await self._check_strategy_risk_limits(strategy_id, session)
                
                await asyncio.sleep(self.risk_check_interval)
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(self.risk_check_interval)
    
    async def _exchange_heartbeat_loop(self):
        """Exchange connection heartbeat"""
        while not self._shutdown:
            try:
                for exchange_name, exchange in self.exchanges.items():
                    if exchange.connected:
                        # Check connection health
                        try:
                            await exchange.get_account_balance()
                            exchange.last_heartbeat = datetime.now(timezone.utc)
                        except Exception as e:
                            logger.warning(f"Exchange {exchange_name} heartbeat failed: {e}")
                            await self._reconnect_exchange(exchange_name)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in exchange heartbeat loop: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _execution_quality_loop(self):
        """Execution quality analysis"""
        while not self._shutdown:
            try:
                # Analyze recent executions for quality metrics
                await self._analyze_execution_quality()
                
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in execution quality loop: {e}")
                await asyncio.sleep(300)
    
    # Helper methods
    
    async def _create_order_from_signal(
        self,
        signal: TradingSignal,
        position_size: Decimal,
        portfolio_id: str,
        session: Dict[str, Any]
    ) -> TradingOrder:
        """Create trading order from signal"""
        
        # Determine order type and price
        if signal.entry_price:
            order_type = OrderType.LIMIT
            price = signal.entry_price
        else:
            order_type = OrderType.MARKET
            price = None
        
        order = TradingOrder(
            strategy_id=signal.strategy_id,
            agent_id=signal.agent_id,
            portfolio_id=portfolio_id,
            symbol=signal.symbol,
            side=signal.position_side,
            order_type=order_type,
            quantity=position_size / (signal.entry_price or Decimal("1")),  # Convert to quantity
            price=price,
            stop_price=signal.stop_loss,
            signal_id=signal.signal_id,
            expected_price=signal.entry_price,
            exchange=self.default_exchange
        )
        
        # Add to order manager
        self.order_manager.add_order(order)
        
        return order
    
    async def _submit_order(self, order: TradingOrder) -> Dict[str, Any]:
        """Submit order to exchange"""
        try:
            exchange = self.exchanges.get(order.exchange)
            if not exchange or not exchange.connected:
                return {"success": False, "error": f"Exchange {order.exchange} not connected"}
            
            # Submit to exchange
            result = await exchange.submit_order(order)
            
            if "exchange_order_id" in result:
                # Update order with exchange details
                order.exchange_order_id = result["exchange_order_id"]
                order.status = OrderStatus.SUBMITTED
                order.submitted_at = datetime.now(timezone.utc)
                
                logger.info(f"Order {order.order_id} submitted to {order.exchange}: {result['exchange_order_id']}")
                
                return {"success": True, **result}
            else:
                return {"success": False, "error": "No exchange order ID returned"}
                
        except Exception as e:
            logger.error(f"Failed to submit order {order.order_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _check_order_status(self, order: TradingOrder):
        """Check order status on exchange"""
        try:
            if not order.exchange_order_id:
                return
            
            exchange = self.exchanges.get(order.exchange)
            if not exchange:
                return
            
            status_result = await exchange.get_order_status(order.exchange_order_id)
            
            # Update order based on exchange status
            if status_result.get("status") == "filled":
                self.order_manager.update_order_status(
                    order.order_id,
                    OrderStatus.FILLED,
                    filled_quantity=Decimal(status_result.get("filled_quantity", "0")),
                    average_fill_price=Decimal(status_result.get("average_price", "0")),
                    filled_at=datetime.now(timezone.utc)
                )
                
                # Calculate execution quality
                await self._calculate_execution_quality(order)
                
        except Exception as e:
            logger.error(f"Failed to check order status for {order.order_id}: {e}")
    
    async def _calculate_execution_quality(self, order: TradingOrder):
        """Calculate execution quality metrics"""
        try:
            if not order.expected_price or not order.average_fill_price:
                return
            
            # Calculate slippage
            if order.side == PositionSide.LONG:
                slippage = (order.average_fill_price - order.expected_price) / order.expected_price
            else:
                slippage = (order.expected_price - order.average_fill_price) / order.expected_price
            
            order.slippage = float(slippage)
            self.slippage_history.append(order.slippage)
            
            # Classify execution quality
            if abs(slippage) < 0.001:  # <0.1%
                order.execution_quality = ExecutionQuality.EXCELLENT
            elif abs(slippage) < 0.003:  # <0.3%
                order.execution_quality = ExecutionQuality.GOOD
            elif abs(slippage) < 0.005:  # <0.5%
                order.execution_quality = ExecutionQuality.FAIR
            else:
                order.execution_quality = ExecutionQuality.POOR
            
        except Exception as e:
            logger.error(f"Failed to calculate execution quality for order {order.order_id}: {e}")
    
    # Additional helper methods would be implemented here...
    
    async def _initialize_exchanges(self):
        """Initialize exchange connections"""
        # Initialize Binance connector
        binance = BinanceConnector()
        await binance.connect()
        self.exchanges["binance"] = binance
        
        logger.info("Exchange connections initialized")
    
    # Additional methods continue here...


# Global service instance
_live_trading_service: Optional[LiveTradingService] = None


async def get_live_trading_service() -> LiveTradingService:
    """Get the global live trading service instance"""
    global _live_trading_service
    
    if _live_trading_service is None:
        _live_trading_service = LiveTradingService()
        await _live_trading_service.initialize()
    
    return _live_trading_service


@asynccontextmanager
async def live_trading_context():
    """Context manager for live trading service"""
    service = await get_live_trading_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass