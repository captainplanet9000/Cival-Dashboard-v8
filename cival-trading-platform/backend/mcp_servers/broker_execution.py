#!/usr/bin/env python3
"""
Broker Execution MCP Server
Multi-broker integration and smart order routing
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
    title="Broker Execution MCP Server",
    description="Multi-broker integration and smart order routing",
    version="1.0.0"
)

security = HTTPBearer()

# Enums
class BrokerType(str, Enum):
    ALPACA = "alpaca"
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"
    E_TRADE = "e_trade"
    CHARLES_SCHWAB = "charles_schwab"
    FIDELITY = "fidelity"
    ROBINHOOD = "robinhood"

class RoutingStrategy(str, Enum):
    BEST_PRICE = "best_price"
    FASTEST_EXECUTION = "fastest_execution"
    LOWEST_COST = "lowest_cost"
    HIGHEST_LIQUIDITY = "highest_liquidity"
    LOAD_BALANCE = "load_balance"
    SPECIFIC_BROKER = "specific_broker"

class ExecutionQuality(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    FAILED = "failed"

class OrderStatus(str, Enum):
    SUBMITTED = "submitted"
    ROUTED = "routed"
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"

# Data models
@dataclass
class BrokerConnection:
    broker_type: BrokerType
    name: str
    status: str  # online, offline, error
    api_endpoint: str
    credentials: Dict[str, str]
    capabilities: List[str]
    supported_order_types: List[str]
    supported_assets: List[str]
    commission_structure: Dict[str, float]
    execution_speed: float  # Average execution time in ms
    reliability_score: float  # 0-1 reliability rating
    last_health_check: str
    daily_limits: Dict[str, float]
    current_usage: Dict[str, float]

@dataclass
class ExecutionVenue:
    venue_id: str
    broker_type: BrokerType
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    last_price: float
    volume: int
    execution_cost: float
    estimated_fill_time: float
    reliability: float
    last_update: str

@dataclass
class SmartOrder:
    id: str
    original_order_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    price: Optional[float]
    routing_strategy: RoutingStrategy
    preferred_broker: Optional[BrokerType]
    max_execution_cost: Optional[float]
    max_execution_time: Optional[float]
    status: OrderStatus
    created_at: str
    routed_at: Optional[str] = None
    executed_at: Optional[str] = None
    selected_broker: Optional[BrokerType] = None
    execution_quality: Optional[ExecutionQuality] = None
    total_cost: float = 0.0
    slippage: float = 0.0
    execution_time: float = 0.0
    agent_id: Optional[str] = None

@dataclass
class ExecutionReport:
    order_id: str
    broker: BrokerType
    symbol: str
    side: str
    quantity: float
    executed_quantity: float
    avg_price: float
    execution_cost: float
    slippage: float
    execution_time: float
    execution_quality: ExecutionQuality
    timestamp: str
    venue_breakdown: List[Dict[str, Any]]
    metrics: Dict[str, float]

class BrokerOrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="buy/sell")
    quantity: float = Field(..., description="Order quantity")
    order_type: str = Field(..., description="Order type")
    price: Optional[float] = Field(None, description="Limit price")
    routing_strategy: RoutingStrategy = Field(RoutingStrategy.BEST_PRICE, description="Routing strategy")
    preferred_broker: Optional[BrokerType] = Field(None, description="Preferred broker")
    max_execution_cost: Optional[float] = Field(None, description="Maximum execution cost")
    max_execution_time: Optional[float] = Field(None, description="Maximum execution time (ms)")
    agent_id: Optional[str] = Field(None, description="Agent ID")

class BrokerExecutionService:
    def __init__(self):
        self.broker_connections: Dict[BrokerType, BrokerConnection] = {}
        self.execution_venues: Dict[str, List[ExecutionVenue]] = defaultdict(list)
        self.smart_orders: Dict[str, SmartOrder] = {}
        self.execution_reports: List[ExecutionReport] = []
        self.routing_engine_active = False
        self.market_data_feeds: Dict[BrokerType, Dict] = {}
        self.execution_stats: Dict[BrokerType, Dict] = defaultdict(dict)
        self.connected_clients: List[WebSocket] = []
        
    async def initialize(self):
        """Initialize the broker execution service"""
        # Setup broker connections
        await self._setup_broker_connections()
        
        # Start engines
        asyncio.create_task(self._market_data_aggregator())
        asyncio.create_task(self._smart_routing_engine())
        asyncio.create_task(self._execution_monitor())
        asyncio.create_task(self._broker_health_monitor())
        
        logger.info("Broker Execution Service initialized")

    async def _setup_broker_connections(self):
        """Setup connections to various brokers"""
        # Alpaca
        self.broker_connections[BrokerType.ALPACA] = BrokerConnection(
            broker_type=BrokerType.ALPACA,
            name="Alpaca Trading",
            status="online",
            api_endpoint="https://paper-api.alpaca.markets",
            credentials={
                "api_key": os.getenv('ALPACA_API_KEY', 'demo_key'),
                "secret_key": os.getenv('ALPACA_SECRET_KEY', 'demo_secret')
            },
            capabilities=["stocks", "crypto", "options"],
            supported_order_types=["market", "limit", "stop", "stop_limit"],
            supported_assets=["stocks", "etfs", "crypto"],
            commission_structure={"stocks": 0.0, "options": 0.65, "crypto": 0.25},
            execution_speed=150.0,  # ms
            reliability_score=0.95,
            last_health_check=datetime.now().isoformat(),
            daily_limits={"orders": 10000, "volume": 50000000},
            current_usage={"orders": 245, "volume": 1250000}
        )
        
        # Interactive Brokers
        self.broker_connections[BrokerType.INTERACTIVE_BROKERS] = BrokerConnection(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            name="Interactive Brokers",
            status="online",
            api_endpoint="https://localhost:5000/v1/api",
            credentials={
                "account": os.getenv('IB_ACCOUNT', 'demo_account'),
                "username": os.getenv('IB_USERNAME', 'demo_user')
            },
            capabilities=["stocks", "options", "futures", "forex", "bonds"],
            supported_order_types=["market", "limit", "stop", "stop_limit", "trailing_stop", "bracket"],
            supported_assets=["stocks", "options", "futures", "forex", "bonds"],
            commission_structure={"stocks": 0.005, "options": 0.70, "futures": 2.25},
            execution_speed=100.0,  # ms
            reliability_score=0.98,
            last_health_check=datetime.now().isoformat(),
            daily_limits={"orders": 50000, "volume": 100000000},
            current_usage={"orders": 89, "volume": 850000}
        )
        
        # TD Ameritrade
        self.broker_connections[BrokerType.TD_AMERITRADE] = BrokerConnection(
            broker_type=BrokerType.TD_AMERITRADE,
            name="TD Ameritrade",
            status="online",
            api_endpoint="https://api.tdameritrade.com/v1",
            credentials={
                "client_id": os.getenv('TDA_CLIENT_ID', 'demo_client'),
                "access_token": os.getenv('TDA_ACCESS_TOKEN', 'demo_token')
            },
            capabilities=["stocks", "options", "etfs", "mutual_funds"],
            supported_order_types=["market", "limit", "stop", "stop_limit"],
            supported_assets=["stocks", "options", "etfs", "mutual_funds"],
            commission_structure={"stocks": 0.0, "options": 0.65, "mutual_funds": 49.99},
            execution_speed=200.0,  # ms
            reliability_score=0.92,
            last_health_check=datetime.now().isoformat(),
            daily_limits={"orders": 25000, "volume": 75000000},
            current_usage={"orders": 156, "volume": 2100000}
        )
        
        # Charles Schwab
        self.broker_connections[BrokerType.CHARLES_SCHWAB] = BrokerConnection(
            broker_type=BrokerType.CHARLES_SCHWAB,
            name="Charles Schwab",
            status="online",
            api_endpoint="https://api.schwabapi.com/v1",
            credentials={
                "app_key": os.getenv('SCHWAB_APP_KEY', 'demo_key'),
                "app_secret": os.getenv('SCHWAB_APP_SECRET', 'demo_secret')
            },
            capabilities=["stocks", "options", "etfs", "mutual_funds", "bonds"],
            supported_order_types=["market", "limit", "stop", "stop_limit"],
            supported_assets=["stocks", "options", "etfs", "mutual_funds", "bonds"],
            commission_structure={"stocks": 0.0, "options": 0.65, "bonds": 1.0},
            execution_speed=180.0,  # ms
            reliability_score=0.94,
            last_health_check=datetime.now().isoformat(),
            daily_limits={"orders": 20000, "volume": 60000000},
            current_usage={"orders": 78, "volume": 950000}
        )

        # Initialize execution stats
        for broker_type in self.broker_connections:
            self.execution_stats[broker_type] = {
                "total_orders": 0,
                "successful_orders": 0,
                "avg_execution_time": 0.0,
                "avg_slippage": 0.0,
                "total_volume": 0.0,
                "success_rate": 0.0,
                "cost_per_share": 0.0
            }

    async def _market_data_aggregator(self):
        """Aggregate market data from all brokers"""
        while True:
            try:
                symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
                
                for symbol in symbols:
                    venues = []
                    
                    for broker_type, connection in self.broker_connections.items():
                        if connection.status == "online":
                            # Simulate market data from each broker
                            base_price = np.random.uniform(100, 400)
                            spread = base_price * np.random.uniform(0.001, 0.01)
                            
                            venue = ExecutionVenue(
                                venue_id=f"{broker_type.value}_{symbol}",
                                broker_type=broker_type,
                                symbol=symbol,
                                bid_price=base_price - spread/2,
                                ask_price=base_price + spread/2,
                                bid_size=np.random.randint(100, 10000),
                                ask_size=np.random.randint(100, 10000),
                                last_price=base_price,
                                volume=np.random.randint(10000, 1000000),
                                execution_cost=connection.commission_structure.get('stocks', 0.005),
                                estimated_fill_time=connection.execution_speed,
                                reliability=connection.reliability_score,
                                last_update=datetime.now().isoformat()
                            )
                            venues.append(venue)
                    
                    self.execution_venues[symbol] = venues
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in market data aggregator: {e}")
                await asyncio.sleep(10)

    async def _smart_routing_engine(self):
        """Smart order routing engine"""
        self.routing_engine_active = True
        
        while self.routing_engine_active:
            try:
                # Process pending smart orders
                pending_orders = [order for order in self.smart_orders.values() 
                                if order.status == OrderStatus.SUBMITTED]
                
                for order in pending_orders:
                    await self._route_smart_order(order)
                
                await asyncio.sleep(1)  # Process every second
                
            except Exception as e:
                logger.error(f"Error in smart routing engine: {e}")
                await asyncio.sleep(5)

    async def _route_smart_order(self, order: SmartOrder):
        """Route a smart order to the best venue"""
        try:
            venues = self.execution_venues.get(order.symbol, [])
            if not venues:
                order.status = OrderStatus.FAILED
                return
            
            # Filter venues based on broker availability
            available_venues = [v for v in venues 
                              if self.broker_connections[v.broker_type].status == "online"]
            
            if not available_venues:
                order.status = OrderStatus.FAILED
                return
            
            # Select best venue based on routing strategy
            selected_venue = await self._select_best_venue(order, available_venues)
            
            if selected_venue:
                # Route order to selected broker
                order.selected_broker = selected_venue.broker_type
                order.status = OrderStatus.ROUTED
                order.routed_at = datetime.now().isoformat()
                
                # Simulate order execution
                asyncio.create_task(self._execute_order_at_venue(order, selected_venue))
                
                logger.info(f"Order {order.id} routed to {selected_venue.broker_type.value}")
            else:
                order.status = OrderStatus.FAILED
                
        except Exception as e:
            logger.error(f"Error routing order {order.id}: {e}")
            order.status = OrderStatus.FAILED

    async def _select_best_venue(self, order: SmartOrder, venues: List[ExecutionVenue]) -> Optional[ExecutionVenue]:
        """Select the best venue based on routing strategy"""
        if order.preferred_broker:
            # Find preferred broker venue
            for venue in venues:
                if venue.broker_type == order.preferred_broker:
                    return venue
        
        if order.routing_strategy == RoutingStrategy.BEST_PRICE:
            # Best price for the side
            if order.side == "buy":
                return min(venues, key=lambda v: v.ask_price)
            else:
                return max(venues, key=lambda v: v.bid_price)
        
        elif order.routing_strategy == RoutingStrategy.FASTEST_EXECUTION:
            # Fastest execution time
            return min(venues, key=lambda v: v.estimated_fill_time)
        
        elif order.routing_strategy == RoutingStrategy.LOWEST_COST:
            # Lowest total cost (price + commission)
            def total_cost(venue):
                price = venue.ask_price if order.side == "buy" else venue.bid_price
                return price + venue.execution_cost
            return min(venues, key=total_cost)
        
        elif order.routing_strategy == RoutingStrategy.HIGHEST_LIQUIDITY:
            # Highest liquidity (size)
            if order.side == "buy":
                return max(venues, key=lambda v: v.ask_size)
            else:
                return max(venues, key=lambda v: v.bid_size)
        
        elif order.routing_strategy == RoutingStrategy.LOAD_BALANCE:
            # Load balance across brokers
            broker_loads = {}
            for broker_type in BrokerType:
                connection = self.broker_connections.get(broker_type)
                if connection:
                    usage_ratio = connection.current_usage.get('orders', 0) / connection.daily_limits.get('orders', 1)
                    broker_loads[broker_type] = usage_ratio
            
            # Select venue from least loaded broker
            available_brokers = [v.broker_type for v in venues]
            least_loaded_broker = min(available_brokers, key=lambda b: broker_loads.get(b, 1.0))
            
            for venue in venues:
                if venue.broker_type == least_loaded_broker:
                    return venue
        
        # Default: best price
        if order.side == "buy":
            return min(venues, key=lambda v: v.ask_price)
        else:
            return max(venues, key=lambda v: v.bid_price)

    async def _execute_order_at_venue(self, order: SmartOrder, venue: ExecutionVenue):
        """Simulate order execution at selected venue"""
        try:
            # Simulate execution delay
            execution_delay = venue.estimated_fill_time / 1000  # Convert ms to seconds
            await asyncio.sleep(execution_delay)
            
            # Simulate execution
            order.status = OrderStatus.PENDING
            
            # Calculate execution metrics
            expected_price = venue.ask_price if order.side == "buy" else venue.bid_price
            
            # Add some randomness for realistic execution
            price_impact = np.random.uniform(-0.002, 0.002)  # ±0.2% price impact
            executed_price = expected_price * (1 + price_impact)
            
            # Simulate slippage
            if order.price:  # Limit order
                if order.side == "buy" and executed_price > order.price:
                    # Limit order not filled at better price
                    order.status = OrderStatus.CANCELLED
                    return
                elif order.side == "sell" and executed_price < order.price:
                    order.status = OrderStatus.CANCELLED
                    return
                slippage = abs(executed_price - order.price) / order.price
            else:  # Market order
                market_price = venue.last_price
                slippage = abs(executed_price - market_price) / market_price
            
            # Calculate costs
            commission = venue.execution_cost * order.quantity
            total_cost = commission
            
            # Update order
            order.status = OrderStatus.FILLED
            order.executed_at = datetime.now().isoformat()
            order.total_cost = total_cost
            order.slippage = slippage
            order.execution_time = execution_delay * 1000  # Convert back to ms
            
            # Determine execution quality
            if slippage < 0.001 and execution_delay < 0.2:
                order.execution_quality = ExecutionQuality.EXCELLENT
            elif slippage < 0.005 and execution_delay < 0.5:
                order.execution_quality = ExecutionQuality.GOOD
            elif slippage < 0.01 and execution_delay < 1.0:
                order.execution_quality = ExecutionQuality.AVERAGE
            else:
                order.execution_quality = ExecutionQuality.POOR
            
            # Create execution report
            report = ExecutionReport(
                order_id=order.id,
                broker=venue.broker_type,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                executed_quantity=order.quantity,
                avg_price=executed_price,
                execution_cost=total_cost,
                slippage=slippage,
                execution_time=order.execution_time,
                execution_quality=order.execution_quality,
                timestamp=datetime.now().isoformat(),
                venue_breakdown=[{
                    "venue": venue.venue_id,
                    "quantity": order.quantity,
                    "price": executed_price,
                    "cost": total_cost
                }],
                metrics={
                    "price_improvement": max(0, (venue.last_price - executed_price) / venue.last_price) if order.side == "buy" else max(0, (executed_price - venue.last_price) / venue.last_price),
                    "fill_rate": 1.0,
                    "market_impact": abs(price_impact)
                }
            )
            
            self.execution_reports.append(report)
            
            # Update broker statistics
            self._update_broker_stats(venue.broker_type, order, report)
            
            # Notify clients
            await self._notify_execution_update(order, report)
            
            logger.info(f"Order {order.id} executed: {order.quantity} {order.symbol} @ {executed_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error executing order {order.id}: {e}")
            order.status = OrderStatus.FAILED

    def _update_broker_stats(self, broker_type: BrokerType, order: SmartOrder, report: ExecutionReport):
        """Update broker execution statistics"""
        stats = self.execution_stats[broker_type]
        
        stats["total_orders"] += 1
        if order.status == OrderStatus.FILLED:
            stats["successful_orders"] += 1
        
        # Update averages
        total_orders = stats["total_orders"]
        stats["avg_execution_time"] = ((stats["avg_execution_time"] * (total_orders - 1)) + order.execution_time) / total_orders
        stats["avg_slippage"] = ((stats["avg_slippage"] * (total_orders - 1)) + order.slippage) / total_orders
        stats["total_volume"] += order.quantity * report.avg_price
        stats["success_rate"] = stats["successful_orders"] / stats["total_orders"]
        stats["cost_per_share"] = report.execution_cost / order.quantity

    async def _execution_monitor(self):
        """Monitor execution performance"""
        while True:
            try:
                # Monitor for stuck orders
                current_time = datetime.now()
                
                for order in self.smart_orders.values():
                    if order.status in [OrderStatus.SUBMITTED, OrderStatus.ROUTED, OrderStatus.PENDING]:
                        order_time = datetime.fromisoformat(order.created_at.replace('Z', '+00:00').replace('+00:00', ''))
                        time_diff = (current_time - order_time).total_seconds()
                        
                        # If order is stuck for more than 5 minutes
                        if time_diff > 300:
                            order.status = OrderStatus.FAILED
                            logger.warning(f"Order {order.id} marked as failed due to timeout")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in execution monitor: {e}")
                await asyncio.sleep(60)

    async def _broker_health_monitor(self):
        """Monitor broker connection health"""
        while True:
            try:
                for broker_type, connection in self.broker_connections.items():
                    # Simulate health check
                    health_check_success = np.random.random() > 0.05  # 95% success rate
                    
                    if health_check_success:
                        connection.status = "online"
                    else:
                        connection.status = "error"
                        logger.warning(f"Broker {broker_type.value} health check failed")
                    
                    connection.last_health_check = datetime.now().isoformat()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in broker health monitor: {e}")
                await asyncio.sleep(120)

    async def submit_smart_order(self, order_request: BrokerOrderRequest) -> SmartOrder:
        """Submit a smart order for execution"""
        order_id = str(uuid.uuid4())
        
        order = SmartOrder(
            id=order_id,
            original_order_id=order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            price=order_request.price,
            routing_strategy=order_request.routing_strategy,
            preferred_broker=order_request.preferred_broker,
            max_execution_cost=order_request.max_execution_cost,
            max_execution_time=order_request.max_execution_time,
            status=OrderStatus.SUBMITTED,
            created_at=datetime.now().isoformat(),
            agent_id=order_request.agent_id
        )
        
        self.smart_orders[order_id] = order
        
        logger.info(f"Smart order submitted: {order_id} - {order_request.routing_strategy.value} {order_request.quantity} {order_request.symbol}")
        
        return order

    async def get_execution_venues(self, symbol: str) -> List[ExecutionVenue]:
        """Get available execution venues for a symbol"""
        return self.execution_venues.get(symbol, [])

    async def get_broker_status(self) -> Dict[BrokerType, Dict]:
        """Get status of all broker connections"""
        status = {}
        for broker_type, connection in self.broker_connections.items():
            status[broker_type] = {
                "status": connection.status,
                "last_health_check": connection.last_health_check,
                "execution_speed": connection.execution_speed,
                "reliability_score": connection.reliability_score,
                "current_usage": connection.current_usage,
                "daily_limits": connection.daily_limits,
                "stats": self.execution_stats[broker_type]
            }
        return status

    async def _notify_execution_update(self, order: SmartOrder, report: ExecutionReport):
        """Notify clients of execution updates"""
        message = {
            "type": "execution_update",
            "order": asdict(order),
            "report": asdict(report),
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

# Initialize service
broker_service = BrokerExecutionService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await broker_service.initialize()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Broker Execution MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "multi_broker_routing",
            "smart_order_routing",
            "execution_analytics",
            "real_time_monitoring"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    return {
        "cpu_usage": 42.3,
        "memory_usage": 51.8,
        "disk_usage": 18.2,
        "network_in": 4096,
        "network_out": 8192,
        "active_connections": len(broker_service.connected_clients),
        "queue_length": len([o for o in broker_service.smart_orders.values() if o.status in [OrderStatus.SUBMITTED, OrderStatus.ROUTED]]),
        "errors_last_hour": 5,
        "requests_last_hour": 423,
        "response_time_p95": 89.0
    }

@app.post("/orders/smart")
async def submit_smart_order(order_request: BrokerOrderRequest, token: str = Depends(get_current_user)):
    try:
        order = await broker_service.submit_smart_order(order_request)
        return {"order": asdict(order), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error submitting smart order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders/{order_id}")
async def get_order_status(order_id: str, token: str = Depends(get_current_user)):
    order = broker_service.smart_orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order": asdict(order), "timestamp": datetime.now().isoformat()}

@app.get("/orders")
async def get_all_orders(token: str = Depends(get_current_user)):
    orders = list(broker_service.smart_orders.values())
    return {
        "orders": [asdict(order) for order in orders],
        "total": len(orders),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/venues/{symbol}")
async def get_execution_venues(symbol: str, token: str = Depends(get_current_user)):
    venues = await broker_service.get_execution_venues(symbol)
    return {
        "venues": [asdict(venue) for venue in venues],
        "symbol": symbol,
        "total": len(venues),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/brokers/status")
async def get_broker_status(token: str = Depends(get_current_user)):
    status = await broker_service.get_broker_status()
    return {
        "brokers": {k.value: v for k, v in status.items()},
        "timestamp": datetime.now().isoformat()
    }

@app.get("/reports/execution")
async def get_execution_reports(limit: int = 100, token: str = Depends(get_current_user)):
    reports = broker_service.execution_reports[-limit:]
    return {
        "reports": [asdict(report) for report in reports],
        "total": len(reports),
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/execution")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    broker_service.connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except:
        pass
    finally:
        if websocket in broker_service.connected_clients:
            broker_service.connected_clients.remove(websocket)

@app.get("/capabilities")
async def get_capabilities():
    return {
        "brokers": [bt.value for bt in BrokerType],
        "routing_strategies": [rs.value for rs in RoutingStrategy],
        "capabilities": [
            {
                "name": "multi_broker_routing",
                "description": "Route orders across multiple brokers"
            },
            {
                "name": "smart_order_routing",
                "description": "Intelligent order routing based on various strategies"
            },
            {
                "name": "execution_analytics",
                "description": "Detailed execution analysis and reporting"
            },
            {
                "name": "real_time_monitoring",
                "description": "Real-time order and execution monitoring"
            }
        ],
        "order_types": ["market", "limit", "stop", "stop_limit", "trailing_stop"],
        "supported_assets": ["stocks", "options", "etfs", "crypto", "futures"]
    }

if __name__ == "__main__":
    uvicorn.run(
        "broker_execution:app",
        host="0.0.0.0", 
        port=8016,
        reload=True,
        log_level="info"
    )