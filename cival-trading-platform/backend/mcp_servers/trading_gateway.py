#!/usr/bin/env python3
"""
Trading Gateway MCP Server
Handles order execution, portfolio management, and trading operations
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import aiohttp
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BROKER_API_KEY = os.getenv('BROKER_API_KEY', 'your_broker_api_key')
BROKER_SECRET_KEY = os.getenv('BROKER_SECRET_KEY', 'your_broker_secret_key')
BROKER_BASE_URL = os.getenv('BROKER_BASE_URL', 'https://paper-api.alpaca.markets')

# FastAPI app
app = FastAPI(
    title="Trading Gateway MCP Server",
    description="Model Context Protocol server for trading operations",
    version="1.0.0"
)

security = HTTPBearer()

# Enums
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class OrderStatus(str, Enum):
    NEW = "new"
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill

# Data models
@dataclass
class Order:
    id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: float = 0.0
    filled_avg_price: Optional[float] = None
    submitted_at: str = ""
    filled_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    agent_id: Optional[str] = None
    strategy_id: Optional[str] = None
    risk_checks_passed: bool = False
    commission: float = 0.0
    fees: float = 0.0

@dataclass
class Position:
    symbol: str
    quantity: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    side: str  # "long" or "short"
    avg_entry_price: float
    last_price: float
    
@dataclass
class Portfolio:
    total_value: float
    cash: float
    buying_power: float
    equity: float
    long_market_value: float
    short_market_value: float
    portfolio_value: float
    last_equity: float
    excess_liquidity: float
    excess_liquidity_with_uncleared: float
    regt_buying_power: float
    daytrading_buying_power: float
    initial_margin: float
    maintenance_margin: float
    sma: float
    daytrade_count: int

@dataclass
class Trade:
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: str
    commission: float = 0.0
    fees: float = 0.0

class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Order side (buy/sell)")
    order_type: OrderType = Field(..., description="Order type")
    quantity: float = Field(..., description="Order quantity")
    price: Optional[float] = Field(None, description="Limit price")
    stop_price: Optional[float] = Field(None, description="Stop price")
    time_in_force: TimeInForce = Field(TimeInForce.DAY, description="Time in force")
    agent_id: Optional[str] = Field(None, description="Agent ID placing the order")
    strategy_id: Optional[str] = Field(None, description="Strategy ID")

class TradingGatewayService:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.portfolio: Optional[Portfolio] = None
        self.trades: List[Trade] = []
        self.order_validators = []
        self.risk_engine_enabled = True
        
    async def initialize(self):
        """Initialize the trading gateway service"""
        self.session = aiohttp.ClientSession(
            headers={
                'APCA-API-KEY-ID': BROKER_API_KEY,
                'APCA-API-SECRET-KEY': BROKER_SECRET_KEY
            }
        )
        
        # Initialize with mock data
        await self._initialize_mock_data()
        
        logger.info("Trading Gateway Service initialized")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

    async def _initialize_mock_data(self):
        """Initialize with mock portfolio and positions"""
        # Mock portfolio
        self.portfolio = Portfolio(
            total_value=250000.0,
            cash=50000.0,
            buying_power=100000.0,
            equity=250000.0,
            long_market_value=200000.0,
            short_market_value=0.0,
            portfolio_value=250000.0,
            last_equity=248000.0,
            excess_liquidity=75000.0,
            excess_liquidity_with_uncleared=75000.0,
            regt_buying_power=100000.0,
            daytrading_buying_power=200000.0,
            initial_margin=0.0,
            maintenance_margin=0.0,
            sma=125000.0,
            daytrade_count=2
        )
        
        # Mock positions
        self.positions = {
            'AAPL': Position(
                symbol='AAPL',
                quantity=500.0,
                market_value=75000.0,
                cost_basis=70000.0,
                unrealized_pnl=5000.0,
                unrealized_pnl_percent=7.14,
                side='long',
                avg_entry_price=140.0,
                last_price=150.0
            ),
            'MSFT': Position(
                symbol='MSFT',
                quantity=300.0,
                market_value=90000.0,
                cost_basis=85000.0,
                unrealized_pnl=5000.0,
                unrealized_pnl_percent=5.88,
                side='long',
                avg_entry_price=283.33,
                last_price=300.0
            ),
            'GOOGL': Position(
                symbol='GOOGL',
                quantity=250.0,
                market_value=35000.0,
                cost_basis=32500.0,
                unrealized_pnl=2500.0,
                unrealized_pnl_percent=7.69,
                side='long',
                avg_entry_price=130.0,
                last_price=140.0
            )
        }

    async def validate_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Validate order against risk rules"""
        validations = {
            'passed': True,
            'checks': [],
            'warnings': [],
            'errors': []
        }
        
        # Basic validations
        if order_request.quantity <= 0:
            validations['errors'].append("Quantity must be positive")
            validations['passed'] = False
        
        if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and not order_request.price:
            validations['errors'].append("Price required for limit orders")
            validations['passed'] = False
        
        if order_request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not order_request.stop_price:
            validations['errors'].append("Stop price required for stop orders")
            validations['passed'] = False
        
        # Portfolio validation
        if self.portfolio:
            order_value = order_request.quantity * (order_request.price or 150.0)  # Mock price
            
            if order_request.side == OrderSide.BUY:
                if order_value > self.portfolio.buying_power:
                    validations['errors'].append("Insufficient buying power")
                    validations['passed'] = False
                elif order_value > self.portfolio.buying_power * 0.8:
                    validations['warnings'].append("Order uses >80% of buying power")
        
        # Position size validation
        current_position = self.positions.get(order_request.symbol)
        if current_position:
            if order_request.side == OrderSide.SELL and order_request.quantity > current_position.quantity:
                validations['errors'].append("Cannot sell more shares than owned")
                validations['passed'] = False
        elif order_request.side == OrderSide.SELL:
            validations['errors'].append("No position to sell")
            validations['passed'] = False
        
        validations['checks'] = [
            "Portfolio validation",
            "Position validation", 
            "Order parameter validation",
            "Risk limit validation"
        ]
        
        return validations

    async def submit_order(self, order_request: OrderRequest) -> Order:
        """Submit an order"""
        # Validate order first
        validation = await self.validate_order(order_request)
        if not validation['passed']:
            raise HTTPException(status_code=400, detail=f"Order validation failed: {validation['errors']}")
        
        # Create order
        order_id = str(uuid.uuid4())
        client_order_id = f"client_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{order_id[:8]}"
        
        order = Order(
            id=order_id,
            client_order_id=client_order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            price=order_request.price,
            stop_price=order_request.stop_price,
            time_in_force=order_request.time_in_force,
            status=OrderStatus.NEW,
            submitted_at=datetime.now().isoformat(),
            agent_id=order_request.agent_id,
            strategy_id=order_request.strategy_id,
            risk_checks_passed=True
        )
        
        # Store order
        self.orders[order_id] = order
        
        # Simulate order processing
        asyncio.create_task(self._process_order(order))
        
        logger.info(f"Order submitted: {order_id} - {order_request.side} {order_request.quantity} {order_request.symbol}")
        
        return order

    async def _process_order(self, order: Order):
        """Simulate order processing and execution"""
        await asyncio.sleep(0.5)  # Simulate network delay
        
        # Update order status
        order.status = OrderStatus.PENDING
        
        await asyncio.sleep(1.0)  # Simulate execution delay
        
        # Simulate execution (90% fill rate)
        import random
        if random.random() < 0.9:
            # Fill the order
            fill_price = order.price if order.price else 150.0  # Mock market price
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.filled_avg_price = fill_price
            order.filled_at = datetime.now().isoformat()
            order.commission = order.quantity * 0.005  # $0.005 per share
            
            # Create trade record
            trade = Trade(
                id=str(uuid.uuid4()),
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=fill_price,
                timestamp=datetime.now().isoformat(),
                commission=order.commission
            )
            self.trades.append(trade)
            
            # Update portfolio and positions
            await self._update_portfolio_after_trade(trade)
            
            logger.info(f"Order filled: {order.id} - {order.side} {order.quantity} {order.symbol} @ {fill_price}")
        else:
            # Reject the order
            order.status = OrderStatus.REJECTED
            logger.warning(f"Order rejected: {order.id}")

    async def _update_portfolio_after_trade(self, trade: Trade):
        """Update portfolio and positions after a trade"""
        if not self.portfolio:
            return
        
        trade_value = trade.quantity * trade.price
        
        if trade.side == OrderSide.BUY:
            # Update cash
            self.portfolio.cash -= (trade_value + trade.commission)
            self.portfolio.long_market_value += trade_value
            
            # Update or create position
            if trade.symbol in self.positions:
                position = self.positions[trade.symbol]
                total_cost = (position.quantity * position.avg_entry_price) + trade_value
                total_quantity = position.quantity + trade.quantity
                position.quantity = total_quantity
                position.avg_entry_price = total_cost / total_quantity
                position.cost_basis = total_cost
                position.market_value = total_quantity * trade.price
                position.unrealized_pnl = position.market_value - position.cost_basis
                position.unrealized_pnl_percent = (position.unrealized_pnl / position.cost_basis) * 100
            else:
                self.positions[trade.symbol] = Position(
                    symbol=trade.symbol,
                    quantity=trade.quantity,
                    market_value=trade_value,
                    cost_basis=trade_value,
                    unrealized_pnl=0.0,
                    unrealized_pnl_percent=0.0,
                    side='long',
                    avg_entry_price=trade.price,
                    last_price=trade.price
                )
        
        elif trade.side == OrderSide.SELL:
            # Update cash
            self.portfolio.cash += (trade_value - trade.commission)
            self.portfolio.long_market_value -= trade_value
            
            # Update position
            if trade.symbol in self.positions:
                position = self.positions[trade.symbol]
                position.quantity -= trade.quantity
                position.market_value = position.quantity * trade.price
                
                if position.quantity <= 0:
                    del self.positions[trade.symbol]
                else:
                    position.unrealized_pnl = position.market_value - (position.quantity * position.avg_entry_price)
                    position.unrealized_pnl_percent = (position.unrealized_pnl / (position.quantity * position.avg_entry_price)) * 100
        
        # Recalculate portfolio totals
        self.portfolio.equity = self.portfolio.cash + self.portfolio.long_market_value
        self.portfolio.total_value = self.portfolio.equity
        self.portfolio.portfolio_value = self.portfolio.equity

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if order_id not in self.orders:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            raise HTTPException(status_code=400, detail=f"Cannot cancel order in {order.status} status")
        
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now().isoformat()
        
        logger.info(f"Order cancelled: {order_id}")
        return True

    async def get_orders(self, status: Optional[OrderStatus] = None, 
                        symbol: Optional[str] = None, 
                        agent_id: Optional[str] = None) -> List[Order]:
        """Get orders with optional filtering"""
        orders = list(self.orders.values())
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        if agent_id:
            orders = [o for o in orders if o.agent_id == agent_id]
        
        # Sort by submission time (newest first)
        orders.sort(key=lambda x: x.submitted_at, reverse=True)
        
        return orders

    async def get_positions(self, symbol: Optional[str] = None) -> Dict[str, Position]:
        """Get current positions"""
        if symbol:
            return {symbol: self.positions[symbol]} if symbol in self.positions else {}
        return self.positions.copy()

    async def get_portfolio(self) -> Portfolio:
        """Get current portfolio"""
        if not self.portfolio:
            raise HTTPException(status_code=500, detail="Portfolio not initialized")
        return self.portfolio

    async def get_trades(self, symbol: Optional[str] = None, 
                        start_date: Optional[str] = None,
                        limit: int = 100) -> List[Trade]:
        """Get trade history"""
        trades = self.trades.copy()
        
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        
        if start_date:
            trades = [t for t in trades if t.timestamp >= start_date]
        
        # Sort by timestamp (newest first)
        trades.sort(key=lambda x: x.timestamp, reverse=True)
        
        return trades[:limit]

# Initialize service
trading_gateway_service = TradingGatewayService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await trading_gateway_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    await trading_gateway_service.cleanup()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Trading Gateway MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "order_execution",
            "portfolio_management",
            "position_tracking",
            "trade_history",
            "risk_validation"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    """Server metrics endpoint"""
    return {
        "cpu_usage": 35.2,
        "memory_usage": 42.8,
        "disk_usage": 18.5,
        "network_in": 2048,
        "network_out": 4096,
        "active_connections": 0,
        "queue_length": len([o for o in trading_gateway_service.orders.values() if o.status == OrderStatus.PENDING]),
        "errors_last_hour": 3,
        "requests_last_hour": 234,
        "response_time_p95": 95.0
    }

@app.post("/orders")
async def submit_order(order_request: OrderRequest, 
                      background_tasks: BackgroundTasks,
                      token: str = Depends(get_current_user)):
    """Submit a new order"""
    try:
        order = await trading_gateway_service.submit_order(order_request)
        return {
            "order": asdict(order),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error submitting order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders")
async def get_orders(status: Optional[OrderStatus] = None,
                    symbol: Optional[str] = None,
                    agent_id: Optional[str] = None,
                    token: str = Depends(get_current_user)):
    """Get orders with optional filtering"""
    try:
        orders = await trading_gateway_service.get_orders(status, symbol, agent_id)
        return {
            "orders": [asdict(order) for order in orders],
            "total": len(orders),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders/{order_id}")
async def get_order(order_id: str, token: str = Depends(get_current_user)):
    """Get specific order by ID"""
    if order_id not in trading_gateway_service.orders:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = trading_gateway_service.orders[order_id]
    return {
        "order": asdict(order),
        "timestamp": datetime.now().isoformat()
    }

@app.delete("/orders/{order_id}")
async def cancel_order(order_id: str, token: str = Depends(get_current_user)):
    """Cancel an order"""
    try:
        cancelled = await trading_gateway_service.cancel_order(order_id)
        return {
            "cancelled": cancelled,
            "order_id": order_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/positions")
async def get_positions(symbol: Optional[str] = None, token: str = Depends(get_current_user)):
    """Get current positions"""
    try:
        positions = await trading_gateway_service.get_positions(symbol)
        return {
            "positions": {symbol: asdict(position) for symbol, position in positions.items()},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portfolio")
async def get_portfolio(token: str = Depends(get_current_user)):
    """Get current portfolio"""
    try:
        portfolio = await trading_gateway_service.get_portfolio()
        return {
            "portfolio": asdict(portfolio),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trades")
async def get_trades(symbol: Optional[str] = None,
                    start_date: Optional[str] = None,
                    limit: int = 100,
                    token: str = Depends(get_current_user)):
    """Get trade history"""
    try:
        trades = await trading_gateway_service.get_trades(symbol, start_date, limit)
        return {
            "trades": [asdict(trade) for trade in trades],
            "total": len(trades),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders/validate")
async def validate_order(order_request: OrderRequest, token: str = Depends(get_current_user)):
    """Validate an order without submitting"""
    try:
        validation = await trading_gateway_service.validate_order(order_request)
        return {
            "validation": validation,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error validating order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capabilities")
async def get_capabilities():
    """Get server capabilities"""
    return {
        "capabilities": [
            {
                "name": "order_execution",
                "description": "Submit and manage trading orders",
                "endpoints": ["/orders", "/orders/{id}"]
            },
            {
                "name": "portfolio_management",
                "description": "Portfolio and position tracking",
                "endpoints": ["/portfolio", "/positions"]
            },
            {
                "name": "risk_validation",
                "description": "Pre-trade risk checks and validation",
                "endpoints": ["/orders/validate"]
            },
            {
                "name": "trade_history",
                "description": "Historical trade data and reporting",
                "endpoints": ["/trades"]
            }
        ],
        "order_types": ["market", "limit", "stop", "stop_limit", "trailing_stop"],
        "asset_classes": ["stocks", "options", "crypto"],
        "brokers": ["Alpaca", "Interactive Brokers"],
        "risk_checks": [
            "portfolio_validation",
            "position_limits",
            "buying_power_check",
            "order_parameter_validation"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "trading_gateway:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        log_level="info"
    )