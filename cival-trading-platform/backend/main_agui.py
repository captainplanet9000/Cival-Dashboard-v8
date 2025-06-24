"""
Cival Trading Platform - Backend API
Railway-optimized FastAPI application with comprehensive services
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import core modules
from core.service_registry import ServiceRegistry
from core.websocket_manager import connection_manager, AGUIMessageType, AGUIMessage
from core.api_router import ComprehensiveAPIRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service registry
service_registry = ServiceRegistry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Cival Trading Platform Backend...")
    
    # Initialize services
    await service_registry.initialize_all_services()
    
    # Setup API routes
    api_router = ComprehensiveAPIRouter()
    await api_router.register_all_routes(app, service_registry)
    
    # Register WebSocket message handlers
    await setup_websocket_handlers()
    
    logger.info("✅ Backend startup complete!")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down services...")
    await service_registry.cleanup_all_services()

async def setup_websocket_handlers():
    """Setup AG-UI Protocol v2 message handlers"""
    
    async def handle_agent_create(client_id: str, message: AGUIMessage):
        """Handle agent creation requests"""
        try:
            system_service = service_registry.get_service('system_lifecycle')
            result = await system_service.createCompleteAgent(message.payload)
            
            # Send response
            response = AGUIMessage(
                id=message.id + "_response",
                timestamp=asyncio.get_event_loop().time(),
                type=AGUIMessageType.AGENT_CREATED,
                source="backend",
                target=client_id,
                payload=result,
                correlation_id=message.id
            )
            
            await connection_manager.send_to_client(client_id, response)
            
        except Exception as e:
            logger.error(f"Error handling agent creation: {e}")
    
    async def handle_farm_create(client_id: str, message: AGUIMessage):
        """Handle farm creation requests"""
        try:
            system_service = service_registry.get_service('system_lifecycle')
            result = await system_service.createFarm(message.payload)
            
            # Send response
            response = AGUIMessage(
                id=message.id + "_response",
                timestamp=asyncio.get_event_loop().time(),
                type=AGUIMessageType.FARM_CREATED,
                source="backend",
                target=client_id,
                payload=result,
                correlation_id=message.id
            )
            
            await connection_manager.send_to_client(client_id, response)
            
        except Exception as e:
            logger.error(f"Error handling farm creation: {e}")
    
    async def handle_mcp_execute(client_id: str, message: AGUIMessage):
        """Handle MCP tool execution"""
        try:
            mcp_service = service_registry.get_service('mcp_integration')
            result = await mcp_service.callTool(
                message.payload.get('agentId'),
                message.payload.get('toolId'),
                message.payload.get('parameters', {})
            )
            
            # Send response
            response = AGUIMessage(
                id=message.id + "_response",
                timestamp=asyncio.get_event_loop().time(),
                type=AGUIMessageType.MCP_RESULT,
                source="backend",
                target=client_id,
                payload=result,
                correlation_id=message.id
            )
            
            await connection_manager.send_to_client(client_id, response)
            
        except Exception as e:
            logger.error(f"Error handling MCP execution: {e}")
    
    async def handle_vault_create(client_id: str, message: AGUIMessage):
        """Handle vault creation"""
        try:
            vault_service = service_registry.get_service('vault_integration')
            result = await vault_service.createVault(message.payload)
            
            # Send response
            response = AGUIMessage(
                id=message.id + "_response",
                timestamp=asyncio.get_event_loop().time(),
                type=AGUIMessageType.VAULT_UPDATE,
                source="backend",
                target=client_id,
                payload=result,
                correlation_id=message.id
            )
            
            await connection_manager.send_to_client(client_id, response)
            
        except Exception as e:
            logger.error(f"Error handling vault creation: {e}")
    
    # Register handlers
    connection_manager.register_message_handler(AGUIMessageType.AGENT_CREATE, handle_agent_create)
    connection_manager.register_message_handler(AGUIMessageType.FARM_CREATE, handle_farm_create)
    connection_manager.register_message_handler(AGUIMessageType.MCP_EXECUTE, handle_mcp_execute)
    connection_manager.register_message_handler(AGUIMessageType.VAULT_CREATE, handle_vault_create)
    
    logger.info("🔗 AG-UI Protocol v2 message handlers registered")

# Create FastAPI app
app = FastAPI(
    title="Cival Trading Platform API",
    description="Advanced Multi-Agent Trading System with AG-UI Protocol v2",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "cival-trading-platform",
        "version": "2.0.0",
        "timestamp": asyncio.get_event_loop().time(),
        "websocket_stats": connection_manager.get_stats()
    }

# WebSocket endpoint for AG-UI Protocol v2
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint with AG-UI Protocol v2 support"""
    await connection_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                import json
                message_data = json.loads(data)
                await connection_manager.handle_message(client_id, message_data)
                
            except json.JSONDecodeError:
                logger.error(f"❌ Invalid JSON received from client {client_id}")
                
            except Exception as e:
                logger.error(f"❌ Error processing message from {client_id}: {e}")
                
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
        logger.info(f"🔌 Client {client_id} disconnected")
        
    except Exception as e:
        logger.error(f"❌ WebSocket error for client {client_id}: {e}")
        connection_manager.disconnect(client_id)

# Background task for system health broadcasts
async def system_health_broadcaster():
    """Broadcast system health to subscribed clients"""
    while True:
        try:
            await asyncio.sleep(30)  # Every 30 seconds
            
            if len(connection_manager.active_connections) > 0:
                # Get system health
                system_service = service_registry.get_service('system_lifecycle')
                health_data = await system_service.getSystemHealth()
                
                # Create health message
                health_message = AGUIMessage(
                    id=f"health_{asyncio.get_event_loop().time()}",
                    timestamp=asyncio.get_event_loop().time(),
                    type=AGUIMessageType.SYSTEM_HEALTH,
                    source="backend",
                    payload=health_data
                )
                
                # Broadcast to subscribed clients
                await connection_manager.broadcast_to_all(
                    health_message, 
                    subscription_filter="system.health"
                )
                
        except Exception as e:
            logger.error(f"❌ Error broadcasting system health: {e}")

# Start background tasks on startup
@app.on_event("startup")
async def start_background_tasks():
    """Start background tasks"""
    asyncio.create_task(system_health_broadcaster())
    logger.info("📡 Background tasks started")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"❌ Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment (Railway sets PORT)
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🚀 Starting server on port {port}")
    
    uvicorn.run(
        "main_agui:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable in production
        log_level="info"
    )