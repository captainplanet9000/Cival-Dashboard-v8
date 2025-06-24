from fastapi import APIRouter, Depends, HTTPException
from python_ai_services.services.simulation_service import SimulationService
from python_ai_services.models.simulation_models import BacktestRequest, BacktestResult
from python_ai_services.services.market_data_service import MarketDataService
from python_ai_services.services.agent_management_service import AgentManagementService
# Removed SessionLocal import as it's a deeper DI concern for a subtask
from loguru import logger # Added logger

router = APIRouter()

# --- Dependency Injection Setup (Simplified for Subtask) ---
# In a real application, MarketDataService and AgentManagementService would likely be
# singletons managed by a proper DI framework (e.g., FastAPI's Depends with a provider).
# For this subtask, we'll instantiate them as needed, acknowledging this is not ideal for production.

# This is a placeholder for how one might structure DI.
# For the subtask, direct instantiation will be used in the route if this is too complex.
# def get_market_data_service():
#     # This would typically return a pre-configured singleton instance
#     return MarketDataService()

# def get_agent_management_service():
#     # This would typically return a pre-configured singleton instance
#     # from python_ai_services.core.database import SessionLocal
#     # return AgentManagementService(session_factory=SessionLocal)
#     return None # Return None if AMS cannot be easily instantiated here for subtask

# def get_simulation_service(
#     md_service: MarketDataService = Depends(get_market_data_service),
#     ams: Optional[AgentManagementService] = Depends(get_agent_management_service)
# ) -> SimulationService:
#     return SimulationService(market_data_service=md_service, agent_management_service=ams)


@router.post("/simulations/backtest", response_model=BacktestResult, tags=["Simulations"])
async def run_backtest_endpoint(
    request: BacktestRequest,
    # simulation_service: SimulationService = Depends(get_simulation_service) # Using simplified instantiation below
):
    """
    Runs a backtest simulation for a given agent configuration or ID against historical market data.
    """
    logger.info(f"Received backtest request for symbol {request.symbol} from {request.start_date_iso} to {request.end_date_iso}.")

    # Simplified instantiation for the subtask, avoiding complex DI setup here.
    # A real app would use FastAPI's dependency injection for these services.
    market_data_service_instance = MarketDataService() # Default instantiation

    agent_management_service_instance: Optional[AgentManagementService] = None
    if request.agent_id_to_simulate:
        # AgentManagementService typically requires a database session factory.
        # For this subtask, if an agent_id is provided, we acknowledge AMS would be needed
        # but might not be fully functional without proper DI setup.
        # The SimulationService itself handles the error if AMS is needed but not provided.
        logger.warning("Agent_id_to_simulate provided; AgentManagementService would be needed. Using None for this simplified setup if full DI is not in place for AMS.")
        # from python_ai_services.core.database import SessionLocal # Example of what might be needed
        # agent_management_service_instance = AgentManagementService(session_factory=SessionLocal)
        # try:
        #    await agent_management_service_instance._load_existing_statuses_from_db() # If this is an async init step
        # except Exception as ams_init_e:
        #    logger.error(f"Failed to initialize AgentManagementService for backtest: {ams_init_e}")
        #    raise HTTPException(status_code=500, detail="Error initializing dependent service for backtest.")
        pass # Let SimulationService handle it if AMS is None but required.

    simulation_service_instance = SimulationService(
        market_data_service=market_data_service_instance,
        agent_management_service=agent_management_service_instance
    )

    try:
        result = await simulation_service_instance.run_backtest(request)
        logger.info(f"Backtest completed for symbol {request.symbol}. Final PnL %: {result.total_pnl_percentage:.2f}%")
        return result
    except ValueError as ve:
        logger.warning(f"Backtest request validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except SimulationServiceError as sse: # Custom error from the service
        logger.error(f"Backtest service error for symbol {request.symbol}: {str(sse)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(sse)) # Or a more specific code like 503
    except Exception as e:
        logger.error(f"Backtest internal error for symbol {request.symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during backtest: {str(e)}")

# To integrate this router into your main FastAPI application:
# from .simulation_routes import router as simulation_router
# app.include_router(simulation_router, prefix="/api/v1")
