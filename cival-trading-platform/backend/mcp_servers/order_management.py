#!/usr/bin/env python3
"""
Order Management MCP Server
Specialized server for advanced order management, routing, and execution strategies
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import aiohttp
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict
import numpy as np
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Order Management MCP Server",
    description="Advanced order management and execution strategies",
    version="1.0.0"
)

security = HTTPBearer()

# Enums
class OrderStrategy(str, Enum):
    IMMEDIATE = "immediate"
    TWAP = "twap"  # Time-Weighted Average Price
    VWAP = "vwap"  # Volume-Weighted Average Price
    ICEBERG = "iceberg"
    SNIPER = "sniper"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"

class OrderPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    PAUSED = "paused"

# Data models
@dataclass
class OrderSlice:
    id: str
    parent_order_id: str
    symbol: str
    side: str
    quantity: float
    price: Optional[float]
    order_type: str
    status: str
    scheduled_time: str
    executed_time: Optional[str] = None
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None

@dataclass
class AdvancedOrder:
    id: str
    symbol: str
    side: str
    total_quantity: float
    strategy: OrderStrategy
    priority: OrderPriority
    status: ExecutionStatus
    created_at: str
    target_price: Optional[float] = None
    price_range: Optional[Tuple[float, float]] = None
    time_window: Optional[int] = None  # minutes
    max_participation_rate: float = 0.1  # 10% of volume
    min_slice_size: float = 100.0
    max_slice_size: float = 1000.0
    urgency_multiplier: float = 1.0
    agent_id: Optional[str] = None
    strategy_id: Optional[str] = None
    slices: List[OrderSlice] = None
    completed_quantity: float = 0.0
    avg_fill_price: Optional[float] = None
    remaining_quantity: float = 0.0
    estimated_completion: Optional[str] = None

class AdvancedOrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Order side (buy/sell)")
    quantity: float = Field(..., description="Total order quantity")
    strategy: OrderStrategy = Field(..., description="Execution strategy")
    priority: OrderPriority = Field(OrderPriority.NORMAL, description="Order priority")
    target_price: Optional[float] = Field(None, description="Target price")
    price_range: Optional[Tuple[float, float]] = Field(None, description="Price range (min, max)")
    time_window: Optional[int] = Field(None, description="Time window in minutes")
    max_participation_rate: float = Field(0.1, description="Max participation rate")
    min_slice_size: float = Field(100.0, description="Minimum slice size")
    max_slice_size: float = Field(1000.0, description="Maximum slice size")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    strategy_id: Optional[str] = Field(None, description="Strategy ID")

class OrderManagementService:
    def __init__(self):
        self.orders: Dict[str, AdvancedOrder] = {}
        self.order_slices: Dict[str, List[OrderSlice]] = defaultdict(list)
        self.execution_queues: Dict[OrderPriority, deque] = {
            OrderPriority.URGENT: deque(),
            OrderPriority.HIGH: deque(),
            OrderPriority.NORMAL: deque(),
            OrderPriority.LOW: deque()
        }
        self.market_data_cache: Dict[str, Dict] = {}
        self.volume_profiles: Dict[str, List] = defaultdict(list)
        self.execution_engine_running = False
        self.connected_clients: List[WebSocket] = []
        
    async def initialize(self):
        """Initialize the order management service"""
        # Start execution engine
        asyncio.create_task(self._execution_engine())
        asyncio.create_task(self._market_data_updater())
        
        # Initialize with mock market data
        await self._initialize_market_data()
        
        logger.info("Order Management Service initialized")

    async def _initialize_market_data(self):
        """Initialize with mock market data"""
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        for symbol in symbols:
            self.market_data_cache[symbol] = {
                'price': np.random.uniform(100, 300),
                'volume': np.random.uniform(1000000, 5000000),
                'bid': 0,
                'ask': 0,
                'spread': 0,
                'volatility': np.random.uniform(0.15, 0.45),
                'last_update': datetime.now().isoformat()
            }
            
            # Generate volume profile
            self.volume_profiles[symbol] = [
                np.random.uniform(50000, 200000) for _ in range(390)  # 6.5 hours * 60 minutes
            ]

    async def _market_data_updater(self):
        """Update market data every few seconds"""
        while True:
            try:
                for symbol in self.market_data_cache:
                    data = self.market_data_cache[symbol]
                    
                    # Simulate price movement
                    price_change = np.random.normal(0, data['volatility'] * 0.01)
                    data['price'] *= (1 + price_change)
                    data['volume'] += np.random.uniform(1000, 10000)
                    
                    # Update bid/ask
                    spread = data['price'] * 0.001  # 0.1% spread
                    data['bid'] = data['price'] - spread/2
                    data['ask'] = data['price'] + spread/2
                    data['spread'] = spread
                    data['last_update'] = datetime.now().isoformat()
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error updating market data: {e}")
                await asyncio.sleep(5)

    async def _execution_engine(self):
        """Main execution engine that processes orders"""
        self.execution_engine_running = True
        
        while self.execution_engine_running:
            try:
                # Process orders by priority
                for priority in [OrderPriority.URGENT, OrderPriority.HIGH, 
                               OrderPriority.NORMAL, OrderPriority.LOW]:
                    queue = self.execution_queues[priority]
                    
                    if queue:
                        order_id = queue.popleft()
                        order = self.orders.get(order_id)
                        
                        if order and order.status == ExecutionStatus.ACTIVE:
                            await self._process_order(order)
                
                await asyncio.sleep(1)  # Process every second
                
            except Exception as e:
                logger.error(f"Error in execution engine: {e}")
                await asyncio.sleep(5)

    async def _process_order(self, order: AdvancedOrder):
        """Process a single advanced order"""
        try:
            if order.strategy == OrderStrategy.IMMEDIATE:
                await self._execute_immediate_strategy(order)
            elif order.strategy == OrderStrategy.TWAP:
                await self._execute_twap_strategy(order)
            elif order.strategy == OrderStrategy.VWAP:
                await self._execute_vwap_strategy(order)
            elif order.strategy == OrderStrategy.ICEBERG:
                await self._execute_iceberg_strategy(order)
            elif order.strategy == OrderStrategy.SNIPER:
                await self._execute_sniper_strategy(order)
            elif order.strategy == OrderStrategy.ACCUMULATION:
                await self._execute_accumulation_strategy(order)
            elif order.strategy == OrderStrategy.DISTRIBUTION:
                await self._execute_distribution_strategy(order)
                
        except Exception as e:
            logger.error(f"Error processing order {order.id}: {e}")
            order.status = ExecutionStatus.FAILED

    async def _execute_immediate_strategy(self, order: AdvancedOrder):
        """Execute order immediately as market order"""
        market_data = self.market_data_cache.get(order.symbol)
        if not market_data:
            return
        
        fill_price = market_data['ask'] if order.side == 'buy' else market_data['bid']
        
        # Create single slice for immediate execution
        slice_order = OrderSlice(
            id=str(uuid.uuid4()),
            parent_order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.total_quantity,
            price=None,  # Market order
            order_type='market',
            status='filled',
            scheduled_time=datetime.now().isoformat(),
            executed_time=datetime.now().isoformat(),
            filled_quantity=order.total_quantity,
            filled_price=fill_price
        )
        
        self.order_slices[order.id].append(slice_order)
        
        # Update order
        order.completed_quantity = order.total_quantity
        order.remaining_quantity = 0
        order.avg_fill_price = fill_price
        order.status = ExecutionStatus.COMPLETED
        
        await self._notify_order_update(order)
        logger.info(f"Immediate order {order.id} completed: {order.total_quantity} {order.symbol} @ {fill_price}")

    async def _execute_twap_strategy(self, order: AdvancedOrder):
        """Execute Time-Weighted Average Price strategy"""
        if not order.time_window:
            order.time_window = 60  # Default 1 hour
        
        # Calculate number of slices based on time window
        num_slices = min(order.time_window, int(order.total_quantity / order.min_slice_size))
        slice_size = order.total_quantity / num_slices
        interval_minutes = order.time_window / num_slices
        
        market_data = self.market_data_cache.get(order.symbol)
        current_price = market_data['price'] if market_data else 150.0
        
        # Create slices
        for i in range(num_slices):
            scheduled_time = datetime.now() + timedelta(minutes=i * interval_minutes)
            
            # Add some price randomness for TWAP
            slice_price = current_price * (1 + np.random.normal(0, 0.002))
            
            slice_order = OrderSlice(
                id=str(uuid.uuid4()),
                parent_order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=slice_size,
                price=slice_price,
                order_type='limit',
                status='scheduled',
                scheduled_time=scheduled_time.isoformat()
            )
            
            self.order_slices[order.id].append(slice_order)
        
        # Simulate execution of first slice
        if self.order_slices[order.id]:
            first_slice = self.order_slices[order.id][0]
            first_slice.status = 'filled'
            first_slice.executed_time = datetime.now().isoformat()
            first_slice.filled_quantity = first_slice.quantity
            first_slice.filled_price = first_slice.price
            
            order.completed_quantity += first_slice.quantity
            order.remaining_quantity = order.total_quantity - order.completed_quantity
            
            if order.remaining_quantity <= 0:
                order.status = ExecutionStatus.COMPLETED
            
            await self._notify_order_update(order)

    async def _execute_vwap_strategy(self, order: AdvancedOrder):
        """Execute Volume-Weighted Average Price strategy"""
        volume_profile = self.volume_profiles.get(order.symbol, [])
        if not volume_profile:
            # Fallback to TWAP if no volume data
            await self._execute_twap_strategy(order)
            return
        
        # Calculate slices based on volume profile
        total_volume = sum(volume_profile)
        target_participation = order.max_participation_rate
        
        market_data = self.market_data_cache.get(order.symbol)
        current_price = market_data['price'] if market_data else 150.0
        
        # Create slices based on volume periods
        for i, period_volume in enumerate(volume_profile[:60]):  # First hour
            if order.completed_quantity >= order.total_quantity:
                break
                
            # Calculate slice size based on volume
            slice_volume = period_volume * target_participation
            slice_size = min(slice_volume, order.remaining_quantity)
            
            if slice_size < order.min_slice_size:
                continue
            
            scheduled_time = datetime.now() + timedelta(minutes=i)
            slice_price = current_price * (1 + np.random.normal(0, 0.001))
            
            slice_order = OrderSlice(
                id=str(uuid.uuid4()),
                parent_order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=slice_size,
                price=slice_price,
                order_type='limit',
                status='scheduled',
                scheduled_time=scheduled_time.isoformat()
            )
            
            self.order_slices[order.id].append(slice_order)
        
        # Execute first slice
        if self.order_slices[order.id]:
            await self._execute_slice(self.order_slices[order.id][0], order)

    async def _execute_iceberg_strategy(self, order: AdvancedOrder):
        """Execute iceberg strategy - only show small portions"""
        visible_size = min(order.max_slice_size, order.total_quantity * 0.1)
        
        market_data = self.market_data_cache.get(order.symbol)
        current_price = market_data['price'] if market_data else 150.0
        
        # Create visible slice
        slice_order = OrderSlice(
            id=str(uuid.uuid4()),
            parent_order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=visible_size,
            price=current_price,
            order_type='limit',
            status='active',
            scheduled_time=datetime.now().isoformat()
        )
        
        self.order_slices[order.id].append(slice_order)
        await self._execute_slice(slice_order, order)

    async def _execute_sniper_strategy(self, order: AdvancedOrder):
        """Execute sniper strategy - wait for optimal price"""
        if not order.target_price:
            order.target_price = order.price_range[0] if order.price_range else None
        
        market_data = self.market_data_cache.get(order.symbol)
        if not market_data:
            return
        
        current_price = market_data['price']
        
        # Check if target price is hit
        price_hit = False
        if order.side == 'buy' and current_price <= order.target_price:
            price_hit = True
        elif order.side == 'sell' and current_price >= order.target_price:
            price_hit = True
        
        if price_hit:
            # Execute immediately
            await self._execute_immediate_strategy(order)
        else:
            # Keep monitoring
            logger.info(f"Sniper order {order.id} waiting for target price {order.target_price}, current: {current_price}")

    async def _execute_accumulation_strategy(self, order: AdvancedOrder):
        """Execute accumulation strategy - buy dips"""
        market_data = self.market_data_cache.get(order.symbol)
        if not market_data:
            return
        
        current_price = market_data['price']
        
        # Check if price is in favorable range for buying
        if order.side == 'buy':
            # Buy when price drops
            if order.price_range and current_price <= order.price_range[0]:
                slice_size = min(order.max_slice_size, order.remaining_quantity)
                await self._create_and_execute_slice(order, slice_size, current_price)
        else:
            # Sell when price rises
            if order.price_range and current_price >= order.price_range[1]:
                slice_size = min(order.max_slice_size, order.remaining_quantity)
                await self._create_and_execute_slice(order, slice_size, current_price)

    async def _execute_distribution_strategy(self, order: AdvancedOrder):
        """Execute distribution strategy - spread over time and price levels"""
        if not order.price_range:
            return
        
        min_price, max_price = order.price_range
        price_levels = 5  # Number of price levels
        time_periods = 10  # Number of time periods
        
        price_step = (max_price - min_price) / price_levels
        time_step = (order.time_window or 60) / time_periods
        
        quantity_per_level = order.total_quantity / (price_levels * time_periods)
        
        for i in range(price_levels):
            for j in range(time_periods):
                price_level = min_price + (i * price_step)
                scheduled_time = datetime.now() + timedelta(minutes=j * time_step)
                
                slice_order = OrderSlice(
                    id=str(uuid.uuid4()),
                    parent_order_id=order.id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=quantity_per_level,
                    price=price_level,
                    order_type='limit',
                    status='scheduled',
                    scheduled_time=scheduled_time.isoformat()
                )
                
                self.order_slices[order.id].append(slice_order)
        
        # Execute first slice
        if self.order_slices[order.id]:
            await self._execute_slice(self.order_slices[order.id][0], order)

    async def _create_and_execute_slice(self, order: AdvancedOrder, quantity: float, price: float):
        """Create and execute a slice"""
        slice_order = OrderSlice(
            id=str(uuid.uuid4()),
            parent_order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            order_type='limit',
            status='active',
            scheduled_time=datetime.now().isoformat(),
            executed_time=datetime.now().isoformat(),
            filled_quantity=quantity,
            filled_price=price
        )
        
        self.order_slices[order.id].append(slice_order)
        
        # Update order
        order.completed_quantity += quantity
        order.remaining_quantity = order.total_quantity - order.completed_quantity
        
        if order.remaining_quantity <= 0:
            order.status = ExecutionStatus.COMPLETED
        
        await self._notify_order_update(order)

    async def _execute_slice(self, slice_order: OrderSlice, parent_order: AdvancedOrder):
        """Execute a single slice"""
        # Simulate execution
        slice_order.status = 'filled'
        slice_order.executed_time = datetime.now().isoformat()
        slice_order.filled_quantity = slice_order.quantity
        slice_order.filled_price = slice_order.price
        
        # Update parent order
        parent_order.completed_quantity += slice_order.quantity
        parent_order.remaining_quantity = parent_order.total_quantity - parent_order.completed_quantity
        
        # Calculate average fill price
        total_filled_value = 0
        total_filled_quantity = 0
        
        for slice_ord in self.order_slices[parent_order.id]:
            if slice_ord.status == 'filled':
                total_filled_value += slice_ord.filled_quantity * slice_ord.filled_price
                total_filled_quantity += slice_ord.filled_quantity
        
        if total_filled_quantity > 0:
            parent_order.avg_fill_price = total_filled_value / total_filled_quantity
        
        if parent_order.remaining_quantity <= 0:
            parent_order.status = ExecutionStatus.COMPLETED
        
        await self._notify_order_update(parent_order)

    async def _notify_order_update(self, order: AdvancedOrder):
        """Notify connected clients of order updates"""
        update_message = {
            "type": "order_update",
            "order": asdict(order),
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all connected WebSocket clients
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(update_message))
            except:
                self.connected_clients.remove(client)

    async def submit_advanced_order(self, order_request: AdvancedOrderRequest) -> AdvancedOrder:
        """Submit an advanced order"""
        order_id = str(uuid.uuid4())
        
        order = AdvancedOrder(
            id=order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            total_quantity=order_request.quantity,
            strategy=order_request.strategy,
            priority=order_request.priority,
            status=ExecutionStatus.QUEUED,
            created_at=datetime.now().isoformat(),
            target_price=order_request.target_price,
            price_range=order_request.price_range,
            time_window=order_request.time_window,
            max_participation_rate=order_request.max_participation_rate,
            min_slice_size=order_request.min_slice_size,
            max_slice_size=order_request.max_slice_size,
            agent_id=order_request.agent_id,
            strategy_id=order_request.strategy_id,
            slices=[],
            remaining_quantity=order_request.quantity
        )
        
        # Estimate completion time
        if order_request.time_window:
            estimated_completion = datetime.now() + timedelta(minutes=order_request.time_window)
            order.estimated_completion = estimated_completion.isoformat()
        
        self.orders[order_id] = order
        
        # Add to execution queue
        self.execution_queues[order_request.priority].append(order_id)
        
        # Start processing
        order.status = ExecutionStatus.ACTIVE
        
        logger.info(f"Advanced order submitted: {order_id} - {order_request.strategy} {order_request.quantity} {order_request.symbol}")
        
        return order

    async def cancel_advanced_order(self, order_id: str) -> bool:
        """Cancel an advanced order"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        order.status = ExecutionStatus.CANCELLED
        
        # Cancel all pending slices
        for slice_order in self.order_slices[order_id]:
            if slice_order.status in ['scheduled', 'active']:
                slice_order.status = 'cancelled'
        
        await self._notify_order_update(order)
        return True

    async def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get detailed order status"""
        if order_id not in self.orders:
            return None
        
        order = self.orders[order_id]
        slices = self.order_slices.get(order_id, [])
        
        return {
            "order": asdict(order),
            "slices": [asdict(slice_ord) for slice_ord in slices],
            "progress": {
                "completion_percentage": (order.completed_quantity / order.total_quantity) * 100,
                "filled_quantity": order.completed_quantity,
                "remaining_quantity": order.remaining_quantity,
                "avg_fill_price": order.avg_fill_price,
                "total_slices": len(slices),
                "executed_slices": len([s for s in slices if s.status == 'filled'])
            }
        }

# Initialize service
order_management_service = OrderManagementService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await order_management_service.initialize()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Order Management MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "advanced_order_strategies",
            "order_slicing",
            "execution_algorithms",
            "real_time_monitoring"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    return {
        "cpu_usage": 28.5,
        "memory_usage": 38.2,
        "disk_usage": 15.8,
        "network_in": 1536,
        "network_out": 3072,
        "active_connections": len(order_management_service.connected_clients),
        "queue_length": sum(len(q) for q in order_management_service.execution_queues.values()),
        "errors_last_hour": 1,
        "requests_last_hour": 156,
        "response_time_p95": 45.0
    }

@app.post("/orders/advanced")
async def submit_advanced_order(order_request: AdvancedOrderRequest, 
                               token: str = Depends(get_current_user)):
    try:
        order = await order_management_service.submit_advanced_order(order_request)
        return {"order": asdict(order), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error submitting advanced order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders/{order_id}/status")
async def get_order_status(order_id: str, token: str = Depends(get_current_user)):
    status = await order_management_service.get_order_status(order_id)
    if not status:
        raise HTTPException(status_code=404, detail="Order not found")
    return status

@app.delete("/orders/{order_id}")
async def cancel_advanced_order(order_id: str, token: str = Depends(get_current_user)):
    cancelled = await order_management_service.cancel_advanced_order(order_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"cancelled": True, "order_id": order_id, "timestamp": datetime.now().isoformat()}

@app.get("/orders")
async def get_all_orders(token: str = Depends(get_current_user)):
    orders = list(order_management_service.orders.values())
    return {
        "orders": [asdict(order) for order in orders],
        "total": len(orders),
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/orders")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    order_management_service.connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed
    except:
        pass
    finally:
        if websocket in order_management_service.connected_clients:
            order_management_service.connected_clients.remove(websocket)

@app.get("/capabilities")
async def get_capabilities():
    return {
        "strategies": [
            {
                "name": "immediate",
                "description": "Execute order immediately as market order"
            },
            {
                "name": "twap",
                "description": "Time-Weighted Average Price execution"
            },
            {
                "name": "vwap", 
                "description": "Volume-Weighted Average Price execution"
            },
            {
                "name": "iceberg",
                "description": "Hide large orders by showing small portions"
            },
            {
                "name": "sniper",
                "description": "Wait for optimal price before executing"
            },
            {
                "name": "accumulation",
                "description": "Accumulate positions on price dips"
            },
            {
                "name": "distribution",
                "description": "Distribute orders across time and price levels"
            }
        ],
        "features": [
            "real_time_execution",
            "order_slicing",
            "priority_queues",
            "websocket_updates",
            "advanced_algorithms"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "order_management:app",
        host="0.0.0.0",
        port=8013,
        reload=True,
        log_level="info"
    )