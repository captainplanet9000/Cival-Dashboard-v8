"""
Wallet Dashboard API - Phase 1: Master Wallet Control Endpoints
API endpoints for wallet-integrated dashboard with fund allocation and collection controls
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from loguru import logger

from ..dashboard.comprehensive_dashboard import wallet_integrated_dashboard
from ..models.master_wallet_models import (
    FundAllocationRequest, FundCollectionRequest, 
    MasterWallet, WalletPerformanceMetrics
)
from ..models.api_models import APIResponse

# Create router for wallet dashboard API
wallet_dashboard_router = APIRouter(prefix="/api/v1/dashboard/wallet", tags=["wallet-dashboard"])

@wallet_dashboard_router.get("/control-panel", response_model=Dict[str, Any])
async def get_wallet_control_panel():
    """
    Get master wallet control panel data
    Returns comprehensive wallet control interface data
    """
    try:
        data = await wallet_integrated_dashboard.get_master_wallet_control_data()
        return APIResponse(
            success=True,
            message="Wallet control panel data retrieved successfully",
            data=data
        ).dict()
    except Exception as e:
        logger.error(f"Error getting wallet control panel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.post("/allocate-funds", response_model=Dict[str, Any])
async def allocate_funds(allocation_request: FundAllocationRequest):
    """
    Execute fund allocation through dashboard
    Allocates funds to agents, farms, or goals
    """
    try:
        result = await wallet_integrated_dashboard.execute_fund_allocation(allocation_request)
        
        if result.get("success"):
            return APIResponse(
                success=True,
                message=result.get("message", "Fund allocation executed successfully"),
                data=result
            ).dict()
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Fund allocation failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing fund allocation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.post("/collect-funds", response_model=Dict[str, Any])
async def collect_funds(collection_request: FundCollectionRequest):
    """
    Execute fund collection through dashboard
    Collects funds from profitable allocations
    """
    try:
        result = await wallet_integrated_dashboard.execute_fund_collection(collection_request)
        
        if result.get("success"):
            return APIResponse(
                success=True,
                message=result.get("message", "Fund collection executed successfully"),
                data=result
            ).dict()
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Fund collection failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing fund collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.post("/switch-wallet/{wallet_id}", response_model=Dict[str, Any])
async def switch_active_wallet(wallet_id: str):
    """
    Switch active wallet in dashboard
    Changes the currently selected wallet for operations
    """
    try:
        result = await wallet_integrated_dashboard.switch_wallet(wallet_id)
        
        if result.get("success"):
            return APIResponse(
                success=True,
                message=result.get("message", f"Switched to wallet {wallet_id}"),
                data={"wallet_id": wallet_id}
            ).dict()
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Wallet switch failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching wallet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.get("/overview", response_model=Dict[str, Any])
async def get_wallet_enhanced_overview():
    """
    Get enhanced overview with wallet-centric data
    Returns platform overview with master wallet integration
    """
    try:
        data = await wallet_integrated_dashboard.get_overview_data()
        return APIResponse(
            success=True,
            message="Enhanced overview data retrieved successfully",
            data=data
        ).dict()
    except Exception as e:
        logger.error(f"Error getting wallet-enhanced overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.get("/allocation-opportunities", response_model=Dict[str, Any])
async def get_allocation_opportunities():
    """
    Get available fund allocation opportunities
    Returns agents, farms, and goals that could benefit from funding
    """
    try:
        # This calls the private method directly for this specific endpoint
        opportunities = await wallet_integrated_dashboard._get_allocation_opportunities()
        return APIResponse(
            success=True,
            message="Allocation opportunities retrieved successfully",
            data={"opportunities": opportunities}
        ).dict()
    except Exception as e:
        logger.error(f"Error getting allocation opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.get("/collection-opportunities", response_model=Dict[str, Any])
async def get_collection_opportunities():
    """
    Get fund collection opportunities
    Returns profitable allocations ready for harvest
    """
    try:
        # This calls the private method directly for this specific endpoint
        opportunities = await wallet_integrated_dashboard._get_collection_opportunities()
        return APIResponse(
            success=True,
            message="Collection opportunities retrieved successfully",
            data={"opportunities": opportunities}
        ).dict()
    except Exception as e:
        logger.error(f"Error getting collection opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.get("/fund-flow-analytics", response_model=Dict[str, Any])
async def get_fund_flow_analytics():
    """
    Get fund flow analytics for visualization
    Returns fund movement analytics and performance data
    """
    try:
        analytics = await wallet_integrated_dashboard._get_fund_flow_analytics()
        return APIResponse(
            success=True,
            message="Fund flow analytics retrieved successfully",
            data=analytics
        ).dict()
    except Exception as e:
        logger.error(f"Error getting fund flow analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.get("/hierarchy", response_model=Dict[str, Any])
async def get_wallet_hierarchy():
    """
    Get wallet hierarchy visualization data
    Returns master wallet → farm → agent hierarchy structure
    """
    try:
        hierarchy = await wallet_integrated_dashboard._get_wallet_hierarchy_data()
        return APIResponse(
            success=True,
            message="Wallet hierarchy data retrieved successfully",
            data=hierarchy
        ).dict()
    except Exception as e:
        logger.error(f"Error getting wallet hierarchy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.get("/complete-data", response_model=Dict[str, Any])
async def get_complete_dashboard_data():
    """
    Get complete wallet-integrated dashboard data
    Returns all dashboard tabs including the new wallet control panel
    """
    try:
        data = await wallet_integrated_dashboard.get_all_dashboard_data()
        return APIResponse(
            success=True,
            message="Complete wallet-integrated dashboard data retrieved successfully",
            data=data
        ).dict()
    except Exception as e:
        logger.error(f"Error getting complete dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.post("/toggle-wallet-mode", response_model=Dict[str, Any])
async def toggle_wallet_dashboard_mode():
    """
    Toggle wallet dashboard mode on/off
    Switches between wallet-centric and traditional dashboard views
    """
    try:
        # Toggle the mode
        wallet_integrated_dashboard.wallet_dashboard_mode = not wallet_integrated_dashboard.wallet_dashboard_mode
        
        return APIResponse(
            success=True,
            message=f"Wallet dashboard mode {'enabled' if wallet_integrated_dashboard.wallet_dashboard_mode else 'disabled'}",
            data={
                "wallet_mode": wallet_integrated_dashboard.wallet_dashboard_mode,
                "mode_description": "wallet_centric" if wallet_integrated_dashboard.wallet_dashboard_mode else "traditional"
            }
        ).dict()
    except Exception as e:
        logger.error(f"Error toggling wallet dashboard mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_dashboard_router.get("/status", response_model=Dict[str, Any])
async def get_wallet_dashboard_status():
    """
    Get wallet dashboard service status
    Returns current status and configuration of wallet dashboard
    """
    try:
        status = {
            "service": "wallet_integrated_dashboard",
            "status": "operational",
            "wallet_mode": wallet_integrated_dashboard.wallet_dashboard_mode,
            "selected_wallet_id": wallet_integrated_dashboard.selected_wallet_id,
            "wallet_services_initialized": {
                "master_wallet_service": wallet_integrated_dashboard.master_wallet_service is not None,
                "wallet_hierarchy_service": wallet_integrated_dashboard.wallet_hierarchy_service is not None
            },
            "phase": "Phase 1: Wallet Dashboard Supremacy",
            "features": [
                "Master wallet control panel",
                "Fund allocation execution",
                "Fund collection automation",
                "Wallet hierarchy visualization",
                "Fund flow analytics",
                "Performance-based recommendations"
            ]
        }
        
        return APIResponse(
            success=True,
            message="Wallet dashboard status retrieved successfully",
            data=status
        ).dict()
        
    except Exception as e:
        logger.error(f"Error getting wallet dashboard status: {e}")
        raise HTTPException(status_code=500, detail=str(e))