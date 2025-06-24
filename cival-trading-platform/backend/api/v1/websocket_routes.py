from fastapi import APIRouter, WebSocket, WebSocketDisconnect
# Adjust path based on actual project structure if core is not directly under python_ai_services
# Assuming 'python_ai_services' is the root package in PYTHONPATH
from python_ai_services.core.websocket_manager import connection_manager
from loguru import logger

router = APIRouter()

@router.websocket("/ws/dashboard/{client_id}")
async def websocket_dashboard_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time dashboard updates.
    A unique client_id should be provided by each connecting client.
    """
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            # This loop keeps the connection alive.
            # It can optionally process messages sent from the client to the server.
            data = await websocket.receive_text()
            logger.debug(f"WebSocket client '{client_id}' sent message: {data}")

            # Example: Echoing message back or processing client commands
            # if data == "ping":
            #     await websocket.send_text("pong")
            # else:
            #     # For this subtask, we are primarily focused on server-to-client pushes,
            #     # so direct responses to client messages might not be the main feature.
            #     # However, this shows where client message handling would go.
            #     from python_ai_services.models.websocket_models import WebSocketEnvelope # Local import for example
            #     response_envelope = WebSocketEnvelope(
            #         event_type="ECHO_RESPONSE",
            #         agent_id=client_id, # Or None if general
            #         payload={"received_message": data, "reply": f"Server acknowledges: {data}"}
            #     )
            #     await connection_manager.send_to_client(client_id, response_envelope)
            pass # Keep connection open, primarily for server pushes

    except WebSocketDisconnect:
        logger.info(f"Client '{client_id}' disconnected from dashboard WebSocket.")
    except Exception as e:
        # Log other exceptions that might occur during the receive_text or processing loop
        logger.error(f"Error in dashboard WebSocket for client '{client_id}': {e}", exc_info=True)
    finally:
        # Ensure client is disconnected from the manager on any exit (graceful or error)
        connection_manager.disconnect(client_id, websocket)
        logger.info(f"Cleaned up connection for client '{client_id}'.")

# To include this router in your main FastAPI application (e.g., in main.py):
# from python_ai_services.api.v1 import websocket_routes
# app.include_router(websocket_routes.router) # No prefix for /ws routes typically, or specific like /ws_api/v1
