import asyncio
import json
import logging
import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Set, Any, Union
from datetime import datetime
from fastapi import WebSocket
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# AGUIProtocol v2 Message Types
class AGUIMessageType(str, Enum):
    # System Events
    SYSTEM_CONNECTED = "system.connected"
    SYSTEM_HEALTH = "system.health"
    SYSTEM_ERROR = "system.error"
    SYSTEM_METRICS = "system.metrics"
    
    # Agent Events
    AGENT_CREATE = "agent.create" 
    AGENT_CREATED = "agent.created"
    AGENT_STATUS = "agent.status"
    AGENT_PERFORMANCE = "agent.performance"
    AGENT_UPDATE = "agent.update"
    
    # Farm Events
    FARM_CREATE = "farm.create"
    FARM_CREATED = "farm.created"
    FARM_UPDATE = "farm.update"
    FARM_REBALANCE = "farm.rebalance"
    
    # MCP Events
    MCP_EXECUTE = "mcp.execute"
    MCP_RESULT = "mcp.result"
    MCP_TOOLS_UPDATED = "mcp.tools_updated"
    
    # Trading Events
    TRADE_EXECUTE = "trade.execute"
    TRADE_EXECUTED = "trade.executed"
    TRADE_STATUS = "trade.status"
    PORTFOLIO_UPDATE = "portfolio.update"
    
    # Vault Events
    VAULT_CREATE = "vault.create"
    VAULT_UPDATE = "vault.update"
    VAULT_POSITION_UPDATE = "vault.position_update"
    VAULT_HARVEST = "vault.harvest"
    
    # Subscription Events
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIPTION_CONFIRMED = "subscription.confirmed"
    SUBSCRIPTION_ERROR = "subscription.error"

# AGUIProtocol v2 Message Structure
class AGUIMessage(BaseModel):
    id: str
    timestamp: float
    type: AGUIMessageType
    source: str  # 'frontend' | 'backend' | 'agent' | 'mcp'
    target: Optional[str] = None
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    requires_response: bool = False

class WebSocketEnvelope(BaseModel):
    event_type: str
    data: Dict[str, Any]
    timestamp: float = None
    client_id: Optional[str] = None
    message_id: Optional[str] = None
    
    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.utcnow().timestamp()
        if data.get('message_id') is None:
            data['message_id'] = str(uuid.uuid4())
        super().__init__(**data)

class ConnectionManager:
    def __init__(self):
        # Core connection storage
        self.active_connections: Dict[str, WebSocket] = {}
        
        # AG-UI Protocol v2 features
        self.client_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self.message_handlers: Dict[AGUIMessageType, List[callable]] = defaultdict(list)
        self.pending_responses: Dict[str, Dict] = {}  # correlation_id -> response_data
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        
        # Performance tracking
        self.message_stats = {
            'sent': 0,
            'received': 0,
            'errors': 0,
            'subscriptions': 0
        }

    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect client with AG-UI Protocol v2 initialization"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # Initialize client subscriptions
        self.client_subscriptions[client_id] = set()
        
        # Start heartbeat for this client
        self.heartbeat_tasks[client_id] = asyncio.create_task(
            self._heartbeat_loop(client_id)
        )
        
        # Send connection confirmation
        welcome_message = AGUIMessage(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().timestamp(),
            type=AGUIMessageType.SYSTEM_CONNECTED,
            source="backend",
            target=client_id,
            payload={
                "client_id": client_id,
                "protocol_version": "2.0",
                "server_time": datetime.utcnow().isoformat(),
                "available_subscriptions": [
                    "system.health", "agent.status", "farm.updates", 
                    "trading.signals", "vault.positions", "mcp.tools"
                ]
            }
        )
        
        await self._send_agui_message(client_id, welcome_message)
        logger.info(f"✅ AG-UI client '{client_id}' connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, client_id: str, websocket: Optional[WebSocket] = None):
        """Disconnect client and cleanup AG-UI resources"""
        if client_id in self.active_connections:
            # Verify websocket if provided
            if websocket and self.active_connections[client_id] != websocket:
                logger.warning(f"Disconnect request for client '{client_id}' but different WebSocket instance provided. Disconnecting stored instance.")
            
            # Cleanup AG-UI resources
            self._cleanup_client_resources(client_id)
            
            # Remove connection
            del self.active_connections[client_id]
            logger.info(f"🔌 AG-UI client '{client_id}' disconnected. Total clients: {len(self.active_connections)}")
        else:
            logger.warning(f"Attempted to disconnect unknown or already disconnected client_id: {client_id}")
    
    def _cleanup_client_resources(self, client_id: str):
        """Clean up all resources for disconnected client"""
        # Cancel heartbeat task
        if client_id in self.heartbeat_tasks:
            self.heartbeat_tasks[client_id].cancel()
            del self.heartbeat_tasks[client_id]
        
        # Clear subscriptions
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
        
        # Clear pending responses
        pending_to_remove = []
        for correlation_id, response_data in self.pending_responses.items():
            if response_data.get('client_id') == client_id:
                pending_to_remove.append(correlation_id)
        
        for correlation_id in pending_to_remove:
            del self.pending_responses[correlation_id]


    async def send_to_client(self, client_id: str, message: Union[WebSocketEnvelope, AGUIMessage]):
        """Send message to specific client with AG-UI Protocol support"""
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                if isinstance(message, AGUIMessage):
                    await self._send_agui_message(client_id, message)
                else:
                    await websocket.send_text(message.model_dump_json())
                    logger.debug(f"📤 Sent WebSocket message to client '{client_id}': {message.event_type}")
                
                self.message_stats['sent'] += 1
                
            except Exception as e:
                logger.error(f"❌ Error sending WebSocket message to client '{client_id}': {e}. Removing connection.")
                self.message_stats['errors'] += 1
                self.disconnect(client_id, websocket)
        else:
            logger.debug(f"📭 No active WebSocket connection for client_id '{client_id}'. Message not sent.")
    
    async def _send_agui_message(self, client_id: str, message: AGUIMessage):
        """Send AG-UI Protocol v2 message"""
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                message_json = message.model_dump_json()
                await websocket.send_text(message_json)
                logger.debug(f"📤 AG-UI message sent to '{client_id}': {message.type}")
                
                # Store correlation for responses
                if message.correlation_id:
                    self.pending_responses[message.correlation_id] = {
                        'client_id': client_id,
                        'message_id': message.id,
                        'timestamp': message.timestamp
                    }
                    
            except Exception as e:
                logger.error(f"❌ Error sending AG-UI message: {e}")
                raise

    async def broadcast_to_all(self, message: Union[WebSocketEnvelope, AGUIMessage], subscription_filter: Optional[str] = None):
        """Broadcast message to all clients or filtered by subscription"""
        if not self.active_connections:
            logger.info("📭 No active WebSocket clients to broadcast to.")
            return

        # Filter clients by subscription if specified
        target_clients = []
        if subscription_filter:
            for client_id in self.active_connections.keys():
                if subscription_filter in self.client_subscriptions.get(client_id, set()):
                    target_clients.append(client_id)
            logger.info(f"📡 Broadcasting to {len(target_clients)} subscribed clients for '{subscription_filter}'")
        else:
            target_clients = list(self.active_connections.keys())
            logger.info(f"📡 Broadcasting to all {len(target_clients)} clients")

        if not target_clients:
            return

        # Prepare message
        if isinstance(message, AGUIMessage):
            message_json = message.model_dump_json()
        else:
            message_json = message.model_dump_json()

        # Send to all target clients
        tasks = []
        for client_id in target_clients:
            websocket = self.active_connections.get(client_id)
            if websocket:
                tasks.append(self._send_text_to_websocket(websocket, message_json, client_id))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_client_id = target_clients[i]
                    logger.warning(f"❌ Broadcast to client '{failed_client_id}' failed: {result}")
                    self.message_stats['errors'] += 1
                else:
                    success_count += 1
            
            self.message_stats['sent'] += success_count
            logger.info(f"✅ Broadcast completed: {success_count}/{len(tasks)} successful")


    async def _send_text_to_websocket(self, websocket: WebSocket, message_json: str, client_id: str):
        """Helper to send text and handle potential disconnection for a single websocket."""
        try:
            await websocket.send_text(message_json)
        except Exception as e:
            logger.error(f"❌ Error sending during broadcast to client '{client_id}': {e}. Removing connection.")
            self.disconnect(client_id, websocket)
            raise
    
    async def _heartbeat_loop(self, client_id: str):
        """Maintain heartbeat with client"""
        try:
            while client_id in self.active_connections:
                await asyncio.sleep(30)  # 30 second heartbeat
                
                if client_id not in self.active_connections:
                    break
                    
                heartbeat = AGUIMessage(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow().timestamp(),
                    type=AGUIMessageType.SYSTEM_HEALTH,
                    source="backend",
                    target=client_id,
                    payload={
                        "status": "healthy",
                        "uptime": datetime.utcnow().timestamp(),
                        "active_connections": len(self.active_connections)
                    }
                )
                
                try:
                    await self._send_agui_message(client_id, heartbeat)
                except Exception as e:
                    logger.warning(f"💔 Heartbeat failed for client {client_id}: {e}")
                    break
                    
        except asyncio.CancelledError:
            logger.debug(f"💔 Heartbeat cancelled for client {client_id}")
        except Exception as e:
            logger.error(f"❌ Heartbeat error for client {client_id}: {e}")
    
    async def handle_subscription(self, client_id: str, subscription: str, action: str = "subscribe"):
        """Handle client subscription management"""
        if client_id not in self.active_connections:
            return False
            
        if action == "subscribe":
            self.client_subscriptions[client_id].add(subscription)
            self.message_stats['subscriptions'] += 1
            
            # Send confirmation
            confirmation = AGUIMessage(
                id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().timestamp(),
                type=AGUIMessageType.SUBSCRIPTION_CONFIRMED,
                source="backend",
                target=client_id,
                payload={
                    "subscription": subscription,
                    "status": "confirmed",
                    "active_subscriptions": list(self.client_subscriptions[client_id])
                }
            )
            
            await self._send_agui_message(client_id, confirmation)
            logger.info(f"✅ Client {client_id} subscribed to {subscription}")
            
        elif action == "unsubscribe":
            self.client_subscriptions[client_id].discard(subscription)
            logger.info(f"❌ Client {client_id} unsubscribed from {subscription}")
            
        return True
    
    async def handle_message(self, client_id: str, message_data: Dict[str, Any]):
        """Handle incoming AG-UI Protocol message"""
        try:
            # Parse AG-UI message
            message = AGUIMessage(**message_data)
            self.message_stats['received'] += 1
            
            logger.debug(f"📥 Received AG-UI message from {client_id}: {message.type}")
            
            # Handle subscription messages
            if message.type == AGUIMessageType.SUBSCRIBE:
                subscription = message.payload.get('subscription')
                if subscription:
                    await self.handle_subscription(client_id, subscription, "subscribe")
                    
            elif message.type == AGUIMessageType.UNSUBSCRIBE:
                subscription = message.payload.get('subscription')
                if subscription:
                    await self.handle_subscription(client_id, subscription, "unsubscribe")
            
            # Handle other message types through registered handlers
            handlers = self.message_handlers.get(message.type, [])
            for handler in handlers:
                try:
                    await handler(client_id, message)
                except Exception as e:
                    logger.error(f"❌ Handler error for {message.type}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error handling message from {client_id}: {e}")
            self.message_stats['errors'] += 1
    
    def register_message_handler(self, message_type: AGUIMessageType, handler: callable):
        """Register handler for specific message type"""
        self.message_handlers[message_type].append(handler)
        logger.info(f"📝 Registered handler for {message_type}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection and message statistics"""
        return {
            "active_connections": len(self.active_connections),
            "total_subscriptions": sum(len(subs) for subs in self.client_subscriptions.values()),
            "message_stats": self.message_stats.copy(),
            "pending_responses": len(self.pending_responses),
            "heartbeat_tasks": len(self.heartbeat_tasks)
        }

# Singleton instance
connection_manager = ConnectionManager()
