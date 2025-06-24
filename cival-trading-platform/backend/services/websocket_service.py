"""
WebSocket Service
Provides real-time data streaming for the dashboard
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from ..core.service_registry import service_registry
from ..core.logging_config import logger


class EventType(Enum):
    """WebSocket event types"""
    # Market Data Events
    PRICE_UPDATE = "price_update"
    MARKET_SUMMARY = "market_summary"
    ORDER_BOOK_UPDATE = "order_book_update"
    TRADE_UPDATE = "trade_update"
    
    # Portfolio Events
    PORTFOLIO_UPDATE = "portfolio_update"
    POSITION_UPDATE = "position_update"
    BALANCE_UPDATE = "balance_update"
    PNL_UPDATE = "pnl_update"
    
    # Trading Events
    ORDER_STATUS = "order_status"
    TRADE_EXECUTION = "trade_execution"
    STRATEGY_UPDATE = "strategy_update"
    
    # Agent Events
    AGENT_STATUS = "agent_status"
    AGENT_DECISION = "agent_decision"
    AGENT_COMMUNICATION = "agent_communication"
    
    # Goal Events
    GOAL_PROGRESS = "goal_progress"
    GOAL_ACHIEVEMENT = "goal_achievement"
    GOAL_UPDATE = "goal_update"
    
    # Farm Events
    FARM_STATUS = "farm_status"
    FARM_PERFORMANCE = "farm_performance"
    FARM_ALLOCATION = "farm_allocation"
    
    # Vault Events
    VAULT_BALANCE = "vault_balance"
    VAULT_TRANSACTION = "vault_transaction"
    VAULT_REBALANCE = "vault_rebalance"
    
    # Risk Events
    RISK_ALERT = "risk_alert"
    RISK_METRICS = "risk_metrics"
    LIMIT_BREACH = "limit_breach"
    
    # System Events
    SYSTEM_STATUS = "system_status"
    CONNECTION_STATUS = "connection_status"
    ERROR = "error"


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    event_type: str
    data: Dict[str, Any]
    timestamp: str
    id: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # connection_id -> event_types
        self.event_subscribers: Dict[str, Set[str]] = {}  # event_type -> connection_ids
        
    async def connect(self, websocket: WebSocket, connection_id: str = None) -> str:
        """Accept and track new WebSocket connection"""
        if connection_id is None:
            connection_id = str(uuid.uuid4())
            
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.subscriptions[connection_id] = set()
        
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # Send connection confirmation
        await self.send_to_connection(connection_id, WebSocketMessage(
            event_type=EventType.CONNECTION_STATUS.value,
            data={"status": "connected", "connection_id": connection_id},
            timestamp=datetime.now().isoformat()
        ))
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            # Remove from all event subscriptions
            if connection_id in self.subscriptions:
                for event_type in self.subscriptions[connection_id]:
                    if event_type in self.event_subscribers:
                        self.event_subscribers[event_type].discard(connection_id)
                del self.subscriptions[connection_id]
            
            del self.active_connections[connection_id]
            logger.info(f"WebSocket connection closed: {connection_id}")
    
    def subscribe(self, connection_id: str, event_types: List[str]):
        """Subscribe connection to specific event types"""
        if connection_id not in self.active_connections:
            return False
            
        for event_type in event_types:
            self.subscriptions[connection_id].add(event_type)
            
            if event_type not in self.event_subscribers:
                self.event_subscribers[event_type] = set()
            self.event_subscribers[event_type].add(connection_id)
        
        logger.info(f"Connection {connection_id} subscribed to: {event_types}")
        return True
    
    def unsubscribe(self, connection_id: str, event_types: List[str]):
        """Unsubscribe connection from specific event types"""
        if connection_id not in self.subscriptions:
            return False
            
        for event_type in event_types:
            self.subscriptions[connection_id].discard(event_type)
            
            if event_type in self.event_subscribers:
                self.event_subscribers[event_type].discard(connection_id)
        
        logger.info(f"Connection {connection_id} unsubscribed from: {event_types}")
        return True
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(asdict(message)))
            except Exception as e:
                logger.error(f"Error sending to connection {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast_to_subscribers(self, event_type: str, data: Dict[str, Any]):
        """Broadcast message to all subscribers of an event type"""
        if event_type not in self.event_subscribers:
            return
        
        message = WebSocketMessage(
            event_type=event_type,
            data=data,
            timestamp=datetime.now().isoformat()
        )
        
        # Send to all subscribers
        subscribers = list(self.event_subscribers[event_type])
        tasks = []
        
        for connection_id in subscribers:
            tasks.append(self.send_to_connection(connection_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all active connections"""
        if not self.active_connections:
            return
        
        tasks = []
        for connection_id in list(self.active_connections.keys()):
            tasks.append(self.send_to_connection(connection_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_subscription_stats(self) -> Dict[str, int]:
        """Get subscription statistics"""
        stats = {}
        for event_type, subscribers in self.event_subscribers.items():
            stats[event_type] = len(subscribers)
        return stats


class WebSocketService:
    """Main WebSocket service for real-time updates"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.update_tasks: Dict[str, asyncio.Task] = {}
        self.update_intervals = {
            EventType.PRICE_UPDATE.value: 5,  # 5 seconds
            EventType.PORTFOLIO_UPDATE.value: 10,  # 10 seconds
            EventType.AGENT_STATUS.value: 15,  # 15 seconds
            EventType.MARKET_SUMMARY.value: 30,  # 30 seconds
            EventType.RISK_METRICS.value: 30,  # 30 seconds
            EventType.SYSTEM_STATUS.value: 60,  # 60 seconds
        }
        self.mock_data_generators = {}
        self._initialize_mock_data_generators()
        
    def _initialize_mock_data_generators(self):
        """Initialize mock data generators for real-time updates"""
        
        self.mock_data_generators = {
            EventType.PRICE_UPDATE.value: self._generate_price_update,
            EventType.PORTFOLIO_UPDATE.value: self._generate_portfolio_update,
            EventType.AGENT_STATUS.value: self._generate_agent_status,
            EventType.MARKET_SUMMARY.value: self._generate_market_summary,
            EventType.RISK_METRICS.value: self._generate_risk_metrics,
            EventType.SYSTEM_STATUS.value: self._generate_system_status,
            EventType.GOAL_PROGRESS.value: self._generate_goal_progress,
            EventType.FARM_STATUS.value: self._generate_farm_status,
            EventType.VAULT_BALANCE.value: self._generate_vault_balance,
        }
    
    async def handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connection lifecycle"""
        connection_id = await self.connection_manager.connect(websocket)
        
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await self._handle_client_message(connection_id, message)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        finally:
            self.connection_manager.disconnect(connection_id)
    
    async def _handle_client_message(self, connection_id: str, message: Dict[str, Any]):
        """Handle incoming client messages"""
        message_type = message.get("type")
        
        if message_type == "subscribe":
            event_types = message.get("events", [])
            success = self.connection_manager.subscribe(connection_id, event_types)
            
            # Start update tasks for new subscriptions
            for event_type in event_types:
                await self._start_update_task(event_type)
            
            await self.connection_manager.send_to_connection(connection_id, WebSocketMessage(
                event_type="subscription_response",
                data={"success": success, "subscribed_events": event_types},
                timestamp=datetime.now().isoformat()
            ))
            
        elif message_type == "unsubscribe":
            event_types = message.get("events", [])
            success = self.connection_manager.unsubscribe(connection_id, event_types)
            
            await self.connection_manager.send_to_connection(connection_id, WebSocketMessage(
                event_type="unsubscription_response",
                data={"success": success, "unsubscribed_events": event_types},
                timestamp=datetime.now().isoformat()
            ))
            
        elif message_type == "ping":
            await self.connection_manager.send_to_connection(connection_id, WebSocketMessage(
                event_type="pong",
                data={"timestamp": datetime.now().isoformat()},
                timestamp=datetime.now().isoformat()
            ))
    
    async def _start_update_task(self, event_type: str):
        """Start periodic update task for event type"""
        if event_type in self.update_tasks and not self.update_tasks[event_type].done():
            return  # Task already running
        
        if event_type in self.update_intervals:
            self.update_tasks[event_type] = asyncio.create_task(
                self._periodic_update_task(event_type)
            )
    
    async def _periodic_update_task(self, event_type: str):
        """Periodic update task for specific event type"""
        interval = self.update_intervals.get(event_type, 30)
        
        while True:
            try:
                # Check if anyone is still subscribed
                if event_type not in self.connection_manager.event_subscribers or \
                   not self.connection_manager.event_subscribers[event_type]:
                    # No subscribers, stop the task
                    break
                
                # Generate and broadcast update
                if event_type in self.mock_data_generators:
                    data = await self.mock_data_generators[event_type]()
                    await self.connection_manager.broadcast_to_subscribers(event_type, data)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in periodic update task for {event_type}: {e}")
                await asyncio.sleep(interval)
    
    # Mock data generators for real-time updates
    
    async def _generate_price_update(self) -> Dict[str, Any]:
        """Generate mock price update data"""
        import random
        
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT']
        
        prices = {}
        for symbol in symbols:
            base_prices = {
                'BTC/USDT': 45000,
                'ETH/USDT': 2500,
                'SOL/USDT': 100,
                'BNB/USDT': 350,
                'ADA/USDT': 0.50
            }
            
            base_price = base_prices.get(symbol, 100)
            variation = random.uniform(-0.002, 0.002)
            price = base_price * (1 + variation)
            
            prices[symbol] = {
                'price': round(price, 2),
                'change': round(variation * 100, 2),
                'volume': int(random.uniform(1e6, 1e8)),
                'timestamp': datetime.now().isoformat()
            }
        
        return {'prices': prices}
    
    async def _generate_portfolio_update(self) -> Dict[str, Any]:
        """Generate mock portfolio update data"""
        import random
        
        return {
            'total_value': round(random.uniform(90000, 110000), 2),
            'total_pnl': round(random.uniform(-5000, 5000), 2),
            'total_pnl_percent': round(random.uniform(-5, 5), 2),
            'positions': [
                {
                    'symbol': 'BTC/USDT',
                    'size': round(random.uniform(0.5, 2.0), 4),
                    'value': round(random.uniform(20000, 40000), 2),
                    'pnl': round(random.uniform(-1000, 1000), 2)
                },
                {
                    'symbol': 'ETH/USDT',
                    'size': round(random.uniform(5, 20), 2),
                    'value': round(random.uniform(10000, 30000), 2),
                    'pnl': round(random.uniform(-500, 500), 2)
                }
            ],
            'timestamp': datetime.now().isoformat()
        }
    
    async def _generate_agent_status(self) -> Dict[str, Any]:
        """Generate mock agent status data"""
        import random
        
        agents = ['Marcus Momentum', 'Alex Arbitrage', 'Sophia Reversion', 'Riley Risk']
        statuses = ['active', 'idle', 'analyzing', 'executing']
        
        agent_data = []
        for agent in agents:
            agent_data.append({
                'name': agent,
                'status': random.choice(statuses),
                'last_action': datetime.now().isoformat(),
                'active_trades': random.randint(0, 5),
                'success_rate': round(random.uniform(60, 90), 1),
                'pnl_today': round(random.uniform(-500, 1000), 2)
            })
        
        return {'agents': agent_data}
    
    async def _generate_market_summary(self) -> Dict[str, Any]:
        """Generate mock market summary data"""
        import random
        
        return {
            'total_market_cap': 1.85e12,
            'total_volume_24h': round(random.uniform(80e9, 120e9), 0),
            'btc_dominance': round(random.uniform(47, 50), 1),
            'fear_greed_index': random.randint(20, 80),
            'trending_up': random.randint(45, 65),
            'trending_down': random.randint(35, 55),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _generate_risk_metrics(self) -> Dict[str, Any]:
        """Generate mock risk metrics data"""
        import random
        
        return {
            'portfolio_var': round(random.uniform(2000, 5000), 2),
            'max_drawdown': round(random.uniform(5, 15), 2),
            'sharpe_ratio': round(random.uniform(1.2, 2.5), 2),
            'volatility': round(random.uniform(15, 25), 1),
            'risk_score': random.randint(3, 7),
            'active_alerts': random.randint(0, 3),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _generate_system_status(self) -> Dict[str, Any]:
        """Generate mock system status data"""
        import random
        
        return {
            'uptime': '5d 12h 34m',
            'cpu_usage': round(random.uniform(10, 40), 1),
            'memory_usage': round(random.uniform(45, 75), 1),
            'active_connections': self.connection_manager.get_connection_count(),
            'api_response_time': round(random.uniform(50, 150), 0),
            'services_healthy': random.randint(8, 10),
            'services_total': 10,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _generate_goal_progress(self) -> Dict[str, Any]:
        """Generate mock goal progress data"""
        import random
        
        goals = [
            {'id': 'goal_1', 'name': 'Monthly Profit Target', 'progress': random.uniform(65, 95)},
            {'id': 'goal_2', 'name': 'Risk Management', 'progress': random.uniform(80, 100)},
            {'id': 'goal_3', 'name': 'Portfolio Diversification', 'progress': random.uniform(70, 95)}
        ]
        
        for goal in goals:
            goal['progress'] = round(goal['progress'], 1)
            goal['last_updated'] = datetime.now().isoformat()
        
        return {'goals': goals}
    
    async def _generate_farm_status(self) -> Dict[str, Any]:
        """Generate mock farm status data"""
        import random
        
        farms = [
            {'id': 'momentum_farm', 'name': 'Momentum Farm', 'active_agents': random.randint(2, 5)},
            {'id': 'arbitrage_farm', 'name': 'Arbitrage Farm', 'active_agents': random.randint(1, 3)},
            {'id': 'reversion_farm', 'name': 'Mean Reversion Farm', 'active_agents': random.randint(2, 4)}
        ]
        
        for farm in farms:
            farm['performance'] = round(random.uniform(-2, 8), 2)
            farm['allocated_capital'] = round(random.uniform(10000, 50000), 2)
            farm['status'] = random.choice(['active', 'paused', 'optimizing'])
            farm['last_updated'] = datetime.now().isoformat()
        
        return {'farms': farms}
    
    async def _generate_vault_balance(self) -> Dict[str, Any]:
        """Generate mock vault balance data"""
        import random
        
        vaults = [
            {'id': 'master_vault', 'name': 'Master Vault', 'balance': random.uniform(80000, 120000)},
            {'id': 'trading_vault', 'name': 'Trading Vault', 'balance': random.uniform(30000, 60000)},
            {'id': 'reserve_vault', 'name': 'Reserve Vault', 'balance': random.uniform(20000, 40000)}
        ]
        
        for vault in vaults:
            vault['balance'] = round(vault['balance'], 2)
            vault['change_24h'] = round(random.uniform(-5, 5), 2)
            vault['last_updated'] = datetime.now().isoformat()
        
        return {'vaults': vaults}
    
    # Public API methods
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit custom event to subscribers"""
        await self.connection_manager.broadcast_to_subscribers(event_type, data)
    
    async def emit_to_connection(self, connection_id: str, event_type: str, data: Dict[str, Any]):
        """Emit event to specific connection"""
        message = WebSocketMessage(
            event_type=event_type,
            data=data,
            timestamp=datetime.now().isoformat()
        )
        await self.connection_manager.send_to_connection(connection_id, message)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket service statistics"""
        return {
            'active_connections': self.connection_manager.get_connection_count(),
            'subscription_stats': self.connection_manager.get_subscription_stats(),
            'active_update_tasks': len([task for task in self.update_tasks.values() if not task.done()]),
            'supported_events': [event.value for event in EventType]
        }
    
    async def shutdown(self):
        """Shutdown WebSocket service"""
        # Cancel all update tasks
        for task in self.update_tasks.values():
            if not task.done():
                task.cancel()
        
        # Close all connections
        for connection_id in list(self.connection_manager.active_connections.keys()):
            self.connection_manager.disconnect(connection_id)
        
        logger.info("WebSocket service shutdown complete")


# Register service
service_registry.register('websocket', WebSocketService)