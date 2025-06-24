from fastapi import APIRouter, Depends, HTTPException

from python_ai_services.models.performance_models import PerformanceMetrics
from python_ai_services.services.performance_calculation_service import PerformanceCalculationService
from python_ai_services.services.trading_data_service import TradingDataService

# Assuming get_trading_data_service is available from dashboard_data_routes or a similar central place
# For this subtask, we might need to redefine how TradingDataService is obtained if not using a global singleton approach.
# Let's try to import the one defined in dashboard_data_routes for consistency,
# assuming it correctly sets up TradingDataService with its dependencies.
from python_ai_services.api.v1.dashboard_data_routes import get_trading_data_service

router = APIRouter()

# Dependency for PerformanceCalculationService
def get_performance_calculation_service(
    trading_data_service: TradingDataService = Depends(get_trading_data_service)
) -> PerformanceCalculationService:
    """
    Provides a PerformanceCalculationService instance,
    injecting the TradingDataService dependency.
    """
    return PerformanceCalculationService(trading_data_service=trading_data_service)


@router.get("/agents/{agent_id}/performance", response_model=PerformanceMetrics)
async def get_agent_performance_metrics(
    agent_id: str,
    service: PerformanceCalculationService = Depends(get_performance_calculation_service)
):
    """
    Calculate and retrieve performance metrics for a specific trading agent.
    Metrics are calculated based on the agent's trade history.
    Note: Trade history may be mocked, which will affect metric accuracy.
    """
    try:
        metrics = await service.calculate_performance_metrics(agent_id)
        if metrics.notes and "Failed to fetch trade history" in metrics.notes:
             # This case means trade history itself was inaccessible, leading to minimal metrics object
             raise HTTPException(status_code=503, detail=f"Could not calculate performance: {metrics.notes}")
        if metrics.notes and "No trade history available" in metrics.notes:
             # This means history was accessible but empty. Return the metrics object with the note.
             pass # Allow returning the object with the note
        return metrics
    except Exception as e:
        # Catch any unexpected errors from the service layer
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while calculating performance metrics: {str(e)}")

