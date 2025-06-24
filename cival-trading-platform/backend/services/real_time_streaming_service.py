"""
Real-time WebSocket Streaming Service
High-performance real-time market data streaming with AG-UI Protocol v2 integration
"""

import asyncio
import json
import websockets
from typing import Dict, List, Set, Any, Optional, Callable
from datetime import datetime
from decimal import Decimal
from loguru import logger
import weakref

from python_ai_services.services.enhanced_market_data_service import EnhancedMarketDataService
from python_ai_services.models.enhanced_market_data_models import (
    StreamUpdate, StreamSubscription, PriceData, MarketAlert, TradingSignal
)

class WebSocketConnection:
    """Individual WebSocket connection handler"""
    
    def __init__(self, websocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.subscriptions: Set[str] = set()
        self.last_ping = datetime.utcnow()
        self.is_alive = True
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message to client with error handling"""
        try:
            if self.websocket.closed:
                self.is_alive = False
                return False
            
            await self.websocket.send(json.dumps(message, default=str))
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to {self.client_id}: {e}")
            self.is_alive = False
            return False
    
    async def close(self):
        """Close connection gracefully"""
        try:
            if not self.websocket.closed:
                await self.websocket.close()
        except Exception as e:
            logger.warning(f"Error closing connection {self.client_id}: {e}")
        finally:
            self.is_alive = False

class RealTimeStreamingService:
    """
    Real-time WebSocket Streaming Service
    Manages live market data streams, trading signals, and system events
    """
    
    def __init__(self, market_data_service: EnhancedMarketDataService):
        self.market_data_service = market_data_service
        self.connections: Dict[str, WebSocketConnection] = {}
        self.symbol_subscriptions: Dict[str, Set[str]] = {}  # symbol -> set of client_ids
        self.active_streams: Dict[str, asyncio.Task] = {}
        self.server = None
        self.is_running = False
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            "price_update": [],
            "trading_signal": [],
            "market_alert": [],
            "system_event": []
        }
        
        # Stream configuration
        self.stream_config = {
            "price_update_interval": 1.0,  # seconds
            "signal_check_interval": 10.0,  # seconds
            "heartbeat_interval": 30.0,    # seconds
            "max_connections": 1000,
            "max_subscriptions_per_client": 50
        }
    
    async def start_server(self, host: str = "localhost", port: int = 8001):
        """Start WebSocket server"""
        try:
            self.server = await websockets.serve(
                self.handle_connection,
                host,
                port,
                ping_interval=20,
                ping_timeout=10,
                max_size=1024*1024,  # 1MB max message size
                max_queue=32
            )
            
            self.is_running = True
            
            # Start background tasks
            asyncio.create_task(self._price_streaming_loop())
            asyncio.create_task(self._signal_monitoring_loop())
            asyncio.create_task(self._heartbeat_loop())
            asyncio.create_task(self._cleanup_loop())
            
            logger.info(f"WebSocket server started on {host}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop WebSocket server"""
        try:
            self.is_running = False
            
            # Close all connections
            for connection in list(self.connections.values()):
                await connection.close()
            self.connections.clear()
            
            # Cancel all streams
            for task in self.active_streams.values():
                task.cancel()
            self.active_streams.clear()
            
            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            logger.info("WebSocket server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping WebSocket server: {e}")
    
    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        client_id = None
        connection = None
        
        try:
            # Extract client ID from path or generate one
            if path.startswith("/stream/"):
                client_id = path.split("/")[-1]
            else:
                client_id = f"client_{len(self.connections)}_{int(datetime.utcnow().timestamp())}"
            
            # Check connection limits
            if len(self.connections) >= self.stream_config["max_connections"]:
                await websocket.close(code=1013, reason="Server overloaded")
                return
            
            # Create connection
            connection = WebSocketConnection(websocket, client_id)
            self.connections[client_id] = connection
            
            logger.info(f"New WebSocket connection: {client_id}")
            
            # Send welcome message
            await connection.send_message({
                "type": "welcome",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "config": {
                    "max_subscriptions": self.stream_config["max_subscriptions_per_client"],
                    "update_intervals": {
                        "price": self.stream_config["price_update_interval"],
                        "signals": self.stream_config["signal_check_interval"]
                    }
                }
            })
            
            # Handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(connection, data)
                except json.JSONDecodeError:
                    await connection.send_message({
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    await connection.send_message({
                        "type": "error",
                        "message": "Internal server error"
                    })
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket connection error for {client_id}: {e}")
        finally:
            # Cleanup
            if client_id and client_id in self.connections:
                await self._cleanup_connection(client_id)
    
    async def _handle_client_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle message from client"""
        message_type = data.get("type")
        
        if message_type == "subscribe":
            await self._handle_subscribe(connection, data)
        elif message_type == "unsubscribe":
            await self._handle_unsubscribe(connection, data)
        elif message_type == "ping":
            await self._handle_ping(connection)
        elif message_type == "get_status":
            await self._handle_get_status(connection)
        else:
            await connection.send_message({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            })
    
    async def _handle_subscribe(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle subscription request"""
        try:
            symbols = data.get("symbols", [])
            data_types = data.get("data_types", ["price"])
            
            # Validate subscription limits
            new_subscriptions = len(symbols)
            current_subscriptions = len(connection.subscriptions)
            
            if current_subscriptions + new_subscriptions > self.stream_config["max_subscriptions_per_client"]:
                await connection.send_message({
                    "type": "error",
                    "message": "Subscription limit exceeded"
                })
                return
            
            # Add subscriptions
            for symbol in symbols:
                subscription_key = f"{symbol}:{':'.join(data_types)}"
                connection.subscriptions.add(subscription_key)
                
                # Track symbol subscriptions
                if symbol not in self.symbol_subscriptions:
                    self.symbol_subscriptions[symbol] = set()
                self.symbol_subscriptions[symbol].add(connection.client_id)
            
            await connection.send_message({
                "type": "subscription_success",
                "symbols": symbols,
                "data_types": data_types,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Client {connection.client_id} subscribed to {symbols}")
            
        except Exception as e:
            logger.error(f"Error handling subscribe for {connection.client_id}: {e}")
            await connection.send_message({
                "type": "error",
                "message": "Subscription failed"
            })
    
    async def _handle_unsubscribe(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle unsubscription request"""
        try:
            symbols = data.get("symbols", [])
            
            # Remove subscriptions
            for symbol in symbols:
                # Remove from connection subscriptions
                subscriptions_to_remove = [sub for sub in connection.subscriptions if sub.startswith(f"{symbol}:")]
                for sub in subscriptions_to_remove:
                    connection.subscriptions.discard(sub)
                
                # Remove from symbol subscriptions
                if symbol in self.symbol_subscriptions:
                    self.symbol_subscriptions[symbol].discard(connection.client_id)
                    if not self.symbol_subscriptions[symbol]:
                        del self.symbol_subscriptions[symbol]
            
            await connection.send_message({
                "type": "unsubscription_success",
                "symbols": symbols,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Client {connection.client_id} unsubscribed from {symbols}")
            
        except Exception as e:
            logger.error(f"Error handling unsubscribe for {connection.client_id}: {e}")
    
    async def _handle_ping(self, connection: WebSocketConnection):
        """Handle ping message"""
        connection.last_ping = datetime.utcnow()
        await connection.send_message({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_get_status(self, connection: WebSocketConnection):
        """Handle status request"""
        try:
            status = await self.market_data_service.get_provider_status()
            
            await connection.send_message({
                "type": "status",
                "data": status,
                "active_connections": len(self.connections),
                "subscribed_symbols": list(self.symbol_subscriptions.keys()),
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting status for {connection.client_id}: {e}")
    
    async def _cleanup_connection(self, client_id: str):
        """Clean up connection and subscriptions"""
        try:
            if client_id in self.connections:
                connection = self.connections[client_id]
                
                # Remove from symbol subscriptions
                for symbol, clients in list(self.symbol_subscriptions.items()):
                    clients.discard(client_id)
                    if not clients:
                        del self.symbol_subscriptions[symbol]
                
                # Remove connection
                del self.connections[client_id]
                
                logger.info(f"Cleaned up connection: {client_id}")
                
        except Exception as e:
            logger.error(f"Error cleaning up connection {client_id}: {e}")
    
    # Background streaming loops
    
    async def _price_streaming_loop(self):
        """Background loop for streaming price updates"""
        while self.is_running:
            try:
                if not self.symbol_subscriptions:
                    await asyncio.sleep(1)
                    continue
                
                # Get symbols that have active subscriptions
                symbols_to_update = list(self.symbol_subscriptions.keys())
                
                if symbols_to_update:
                    # Get price updates
                    quotes = await self.market_data_service.get_multiple_quotes(symbols_to_update)
                    
                    # Broadcast updates
                    for quote in quotes:
                        await self._broadcast_price_update(quote)
                
                await asyncio.sleep(self.stream_config["price_update_interval"])
                
            except Exception as e:
                logger.error(f"Error in price streaming loop: {e}")
                await asyncio.sleep(5)
    
    async def _signal_monitoring_loop(self):
        """Background loop for monitoring trading signals"""
        while self.is_running:
            try:
                if not self.symbol_subscriptions:
                    await asyncio.sleep(10)
                    continue
                
                # Check for signals on subscribed symbols
                symbols_to_check = list(self.symbol_subscriptions.keys())
                
                for symbol in symbols_to_check:
                    try:
                        signals = await self.market_data_service.generate_trading_signals(symbol)
                        
                        for signal in signals:
                            if signal.confidence >= Decimal("0.6"):  # Only high-confidence signals
                                await self._broadcast_trading_signal(signal)
                        
                        # Small delay between symbols
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.warning(f"Error checking signals for {symbol}: {e}")
                        continue
                
                await asyncio.sleep(self.stream_config["signal_check_interval"])
                
            except Exception as e:
                logger.error(f"Error in signal monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _heartbeat_loop(self):
        """Background loop for heartbeat/ping"""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                # Send heartbeat to all connections
                for client_id, connection in list(self.connections.items()):
                    try:
                        if not connection.is_alive:
                            continue
                        
                        # Check if connection is stale
                        time_since_ping = (current_time - connection.last_ping).total_seconds()
                        if time_since_ping > 120:  # 2 minutes without ping
                            logger.info(f"Connection {client_id} appears stale, closing")
                            await connection.close()
                            continue
                        
                        # Send heartbeat
                        await connection.send_message({
                            "type": "heartbeat",
                            "timestamp": current_time.isoformat(),
                            "connections": len(self.connections),
                            "subscriptions": len(connection.subscriptions)
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error in heartbeat for {client_id}: {e}")
                        connection.is_alive = False
                
                await asyncio.sleep(self.stream_config["heartbeat_interval"])
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(30)
    
    async def _cleanup_loop(self):
        """Background loop for cleaning up dead connections"""
        while self.is_running:
            try:
                # Clean up dead connections
                dead_connections = [
                    client_id for client_id, conn in self.connections.items()
                    if not conn.is_alive or conn.websocket.closed
                ]
                
                for client_id in dead_connections:
                    await self._cleanup_connection(client_id)
                
                if dead_connections:
                    logger.info(f"Cleaned up {len(dead_connections)} dead connections")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    # Broadcasting methods
    
    async def _broadcast_price_update(self, price_data: PriceData):
        """Broadcast price update to subscribed clients"""
        try:
            symbol = price_data.symbol
            
            if symbol not in self.symbol_subscriptions:
                return
            
            message = {
                "type": "price_update",
                "symbol": symbol,
                "data": {
                    "price": float(price_data.price),
                    "change": float(price_data.change or 0),
                    "change_percent": float(price_data.change_percent or 0),
                    "volume": float(price_data.volume or 0),
                    "bid": float(price_data.bid or 0),
                    "ask": float(price_data.ask or 0),
                    "high_24h": float(price_data.high_24h or 0),
                    "low_24h": float(price_data.low_24h or 0),
                    "provider": price_data.provider.value,
                    "timestamp": price_data.timestamp.isoformat()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to all subscribed clients
            client_ids = self.symbol_subscriptions[symbol].copy()
            for client_id in client_ids:
                if client_id in self.connections:
                    connection = self.connections[client_id]
                    if connection.is_alive:
                        await connection.send_message(message)
            
        except Exception as e:
            logger.error(f"Error broadcasting price update for {price_data.symbol}: {e}")
    
    async def _broadcast_trading_signal(self, signal: TradingSignal):
        """Broadcast trading signal to subscribed clients"""
        try:
            symbol = signal.symbol
            
            if symbol not in self.symbol_subscriptions:
                return
            
            message = {
                "type": "trading_signal",
                "symbol": symbol,
                "data": {
                    "signal_type": signal.signal_type,
                    "confidence": float(signal.confidence),
                    "source": signal.source,
                    "reasoning": signal.reasoning,
                    "timeframe": signal.timeframe.value,
                    "risk_score": float(signal.risk_score or 0),
                    "target_price": float(signal.target_price or 0),
                    "stop_loss": float(signal.stop_loss or 0),
                    "take_profit": float(signal.take_profit or 0)
                },
                "timestamp": signal.timestamp.isoformat()
            }
            
            # Send to all subscribed clients
            client_ids = self.symbol_subscriptions[symbol].copy()
            for client_id in client_ids:
                if client_id in self.connections:
                    connection = self.connections[client_id]
                    if connection.is_alive:
                        await connection.send_message(message)
            
            logger.info(f"Broadcasted trading signal: {signal.signal_type} for {symbol}")
            
        except Exception as e:
            logger.error(f"Error broadcasting trading signal for {signal.symbol}: {e}")
    
    async def broadcast_market_alert(self, alert: MarketAlert):
        """Broadcast market alert to all connected clients"""
        try:
            message = {
                "type": "market_alert",
                "alert_id": alert.alert_id,
                "symbol": alert.symbol,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "severity": alert.severity,
                "data": alert.data,
                "timestamp": alert.timestamp.isoformat()
            }
            
            # Send to all connected clients
            for client_id, connection in list(self.connections.items()):
                if connection.is_alive:
                    await connection.send_message(message)
            
            logger.info(f"Broadcasted market alert: {alert.alert_type} for {alert.symbol}")
            
        except Exception as e:
            logger.error(f"Error broadcasting market alert: {e}")
    
    # Public API methods
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.connections),
            "active_connections": sum(1 for conn in self.connections.values() if conn.is_alive),
            "subscribed_symbols": len(self.symbol_subscriptions),
            "total_subscriptions": sum(len(clients) for clients in self.symbol_subscriptions.values()),
            "server_running": self.is_running,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_symbol_subscribers(self, symbol: str) -> List[str]:
        """Get list of client IDs subscribed to a symbol"""
        return list(self.symbol_subscriptions.get(symbol, set()))
    
    async def force_broadcast_test(self, symbol: str = "TEST"):
        """Force broadcast a test message (for debugging)"""
        test_message = {
            "type": "test_broadcast",
            "symbol": symbol,
            "message": "This is a test broadcast",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for client_id, connection in list(self.connections.items()):
            if connection.is_alive:
                await connection.send_message(test_message)