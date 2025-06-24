from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Any

from python_ai_services.models.dashboard_models import (
    PortfolioSummary,
    TradeLogItem,
    OrderLogItem,
    PortfolioSnapshotOutput # Added
)
from python_ai_services.services.trading_data_service import TradingDataService
from python_ai_services.services.portfolio_snapshot_service import PortfolioSnapshotService # Added
from python_ai_services.core.database import SessionLocal # Added for PSS factory
from python_ai_services.services.event_bus_service import EventBusService # Added for PSS factory (optional)
from datetime import datetime # Ensure datetime is imported for Query type hint
from fastapi import Query # Ensure Query is imported for Query type hint
from python_ai_services.services.agent_management_service import AgentManagementService
# Assuming the get_agent_management_service from agent_management_routes can be reused or a similar one exists
# For simplicity, let's assume we can import the one from agent_management_routes if it provides the singleton
from python_ai_services.api.v1.agent_management_routes import get_agent_management_service as get_agent_management_service_singleton

# Placeholder for HyperliquidExecutionService - actual service would be imported
# from python_ai_services.services.hyperliquid_execution_service import HyperliquidExecutionService

router = APIRouter()

# Dependency for HyperliquidExecutionService Factory - REMOVED
# def get_hyperliquid_service_factory_placeholder()...


from python_ai_services.services.trade_history_service import TradeHistoryService # Added
from pathlib import Path # Added for default fills_dir path

# Dependency for TradeHistoryService (singleton)
# This should ideally be in a central dependency management file or main.py
# For now, defining here for clarity of this subtask.
_trade_history_service_instance = TradeHistoryService(fills_dir=Path("agent_fills")) # Default path
def get_trade_history_service_instance() -> TradeHistoryService:
    return _trade_history_service_instance

# Dependency for TradingDataService
def get_trading_data_service(
    agent_service: AgentManagementService = Depends(get_agent_management_service_singleton),
    # hl_factory removed from parameters
    trade_history_service: TradeHistoryService = Depends(get_trade_history_service_instance)
) -> TradingDataService:
    # TradingDataService no longer takes hyperliquid_service_factory
    return TradingDataService(
        agent_service=agent_service,
        trade_history_service=trade_history_service
    )


@router.get("/agents/{agent_id}/portfolio/summary", response_model=PortfolioSummary)
async def get_agent_portfolio_summary(
    agent_id: str,
    service: TradingDataService = Depends(get_trading_data_service)
):
    """
    Retrieve the portfolio summary for a specific trading agent.
    """
    summary = await service.get_portfolio_summary(agent_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Portfolio summary not available for agent {agent_id}.")
    return summary

@router.get("/agents/{agent_id}/portfolio/trade-history", response_model=List[TradeLogItem])
async def get_agent_trade_history(
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    service: TradingDataService = Depends(get_trading_data_service)
):
    """
    Retrieve the trade history for a specific trading agent.
    (Currently returns mocked data)
    """
    if limit < 1 or limit > 500: # Example validation
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 500.")
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be non-negative.")

    history = await service.get_trade_history(agent_id, limit, offset)
    # If agent_id itself is invalid, service methods typically return empty list or None.
    # Consider if agent existence should be checked here first via AgentManagementService for a 404.
    # For now, if service returns empty, it could be valid (no history) or agent not found.
    return history

@router.get("/agents/{agent_id}/orders/open", response_model=List[OrderLogItem])
async def get_agent_open_orders(
    agent_id: str,
    service: TradingDataService = Depends(get_trading_data_service)
):
    """
    Retrieve a list of open orders for a specific trading agent.
    """
    open_orders = await service.get_open_orders(agent_id)
    return open_orders

@router.get("/agents/{agent_id}/orders/history", response_model=List[OrderLogItem])
async def get_agent_order_history(
    agent_id: str,
    limit: int = 100,
    offset: int = 0,
    service: TradingDataService = Depends(get_trading_data_service)
):
    """
    Retrieve the historical orders for a specific trading agent.
    (Currently returns mocked data)
    """
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 500.")
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be non-negative.")

    order_history = await service.get_order_history(agent_id, limit, offset)
    return order_history

# Need to import logger if used in factory, e.g. from loguru import logger - REMOVED
# from loguru import logger
from typing import Callable # Added for factory type hint - NO LONGER NEEDED for hl_factory
# We still need Callable if we were to type hint the Depends more strictly, but not essential here.
# For simplicity, can remove if not used elsewhere, or keep for general utility.
# Let's remove to reflect that the specific HLES factory Callable is gone.
# from typing import Callable

# Dependency for EventBusService (simplified for this subtask if not already global)
# In a real app, this would be a singleton from main.py or a central DI provider.
_event_bus_service_instance_temp: Optional[EventBusService] = None
def get_event_bus_service_instance_temp() -> Optional[EventBusService]:
    global _event_bus_service_instance_temp
    if _event_bus_service_instance_temp is None:
        # _event_bus_service_instance_temp = EventBusService() # Basic instantiation
        # For this subtask, PortfolioSnapshotService makes EventBus optional, so pass None
        pass
    return _event_bus_service_instance_temp

# Dependency for PortfolioSnapshotService
_portfolio_snapshot_service_instance: Optional[PortfolioSnapshotService] = None
def get_portfolio_snapshot_service_instance() -> PortfolioSnapshotService:
    global _portfolio_snapshot_service_instance
    if _portfolio_snapshot_service_instance is None:
        _portfolio_snapshot_service_instance = PortfolioSnapshotService(
            session_factory=SessionLocal,
            event_bus=get_event_bus_service_instance_temp() # Pass optional event_bus
        )
    return _portfolio_snapshot_service_instance

@router.get(
    "/agents/{agent_id}/portfolio/equity-curve",
    response_model=List[PortfolioSnapshotOutput],
    summary="Get historical equity curve for an agent",
    tags=["Dashboard Data", "Portfolio"] # Added Portfolio tag
)
async def get_agent_equity_curve(
    agent_id: str,
    start_time: Optional[datetime] = Query(None, description="ISO 8601 format start time, e.g., 2023-01-01T00:00:00Z"),
    end_time: Optional[datetime] = Query(None, description="ISO 8601 format end time, e.g., 2023-12-31T23:59:59Z"),
    limit: Optional[int] = Query(1000, ge=1, le=10000, description="Max number of data points. Default 1000."), # Increased max limit
    sort_ascending: bool = Query(True, description="Sort snapshots by time ascending (chronological). False for descending."),
    snapshot_service: PortfolioSnapshotService = Depends(get_portfolio_snapshot_service_instance)
):
    """
    Retrieves historical portfolio equity data points for a given agent,
    allowing for time-based filtering and pagination.
    This data can be used to plot an equity curve.
    """
    try:
        # Ensure timezone-aware datetimes if provided (FastAPI might handle this based on model)
        # For direct Query params, it's good to be explicit if service expects aware datetimes.
        # PortfolioSnapshotService now handles timezone awareness internally if naive is passed
        # if start_time and start_time.tzinfo is None:
        #     start_time = start_time.replace(tzinfo=timezone.utc) # timezone needs import from datetime
        # if end_time and end_time.tzinfo is None:
        #     end_time = end_time.replace(tzinfo=timezone.utc)

        snapshots = await snapshot_service.get_historical_snapshots(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            sort_ascending=sort_ascending
        )
        if not snapshots:
            # Return 200 with empty list if no snapshots found, or 404 if agent itself not found (service doesn't check agent existence)
            pass
        return snapshots
    except Exception as e:
        # from loguru import logger # Import logger if used here, or ensure it's module level
        # logger.error(f"Error fetching equity curve for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve equity curve: {str(e)}")

# The following @router.get an exact duplicate of the one defined earlier in the file.
# This was likely a copy-paste error during previous modifications. Removing it.
# @router.get("/agents/{agent_id}/portfolio/summary", response_model=PortfolioSummary)
