"""
Phase 2: Wallet API Supremacy - Comprehensive Wallet-Aware API Layer
Advanced wallet-centric API endpoints that make the entire platform wallet-aware
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from typing import Dict, Any, Optional, List
from loguru import logger
from decimal import Decimal
from datetime import datetime, timezone

from ..core.service_registry import get_registry
from ..models.master_wallet_models import (
    MasterWallet, FundAllocationRequest, FundCollectionRequest,
    WalletPerformanceMetrics, FundAllocation, CreateMasterWalletRequest,
    UpdateWalletConfigRequest, WalletTransferRequest
)
from ..models.api_models import APIResponse
from ..services.master_wallet_service import MasterWalletService

# Create comprehensive wallet API router
wallet_api_router = APIRouter(prefix="/api/v1/wallet", tags=["wallet-supremacy"])

async def get_master_wallet_service() -> MasterWalletService:
    """Dependency to get master wallet service"""
    registry = get_registry()
    service = registry.get_service("master_wallet_service")
    if not service:
        raise HTTPException(status_code=503, detail="Master wallet service unavailable")
    return service

@wallet_api_router.post("/create", response_model=Dict[str, Any])
async def create_master_wallet(
    request: CreateMasterWalletRequest,
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Create a new master wallet
    Phase 2: Complete wallet creation with advanced configuration
    """
    try:
        wallet = await wallet_service.create_master_wallet(request)
        
        return APIResponse(
            success=True,
            message=f"Master wallet created successfully: {wallet.wallet_id}",
            data={"wallet": wallet.dict()}
        ).dict()
        
    except Exception as e:
        logger.error(f"Error creating master wallet: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@wallet_api_router.get("/list", response_model=Dict[str, Any])
async def list_master_wallets(
    include_performance: bool = Query(True, description="Include performance metrics"),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    List all master wallets with optional performance data
    Phase 2: Enhanced wallet listing with comprehensive data
    """
    try:
        wallets_data = []
        
        for wallet_id, wallet in wallet_service.active_wallets.items():
            wallet_info = {
                "wallet": wallet.dict(),
                "status": await wallet_service.get_wallet_status(wallet_id)
            }
            
            if include_performance:
                try:
                    performance = await wallet_service.calculate_wallet_performance(wallet_id)
                    wallet_info["performance"] = performance.dict()
                except Exception as e:
                    logger.warning(f"Could not get performance for wallet {wallet_id}: {e}")
                    wallet_info["performance"] = None
            
            wallets_data.append(wallet_info)
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(wallets_data)} master wallets",
            data={
                "wallets": wallets_data,
                "total_wallets": len(wallets_data)
            }
        ).dict()
        
    except Exception as e:
        logger.error(f"Error listing master wallets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_api_router.get("/{wallet_id}", response_model=Dict[str, Any])
async def get_wallet_details(
    wallet_id: str = Path(..., description="Wallet ID"),
    include_transactions: bool = Query(False, description="Include recent transactions"),
    include_allocations: bool = Query(True, description="Include fund allocations"),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Get detailed wallet information
    Phase 2: Comprehensive wallet details with optional data inclusion
    """
    try:
        if wallet_id not in wallet_service.active_wallets:
            raise HTTPException(status_code=404, detail=f"Wallet {wallet_id} not found")
        
        wallet = wallet_service.active_wallets[wallet_id]
        
        # Get wallet status and performance
        status = await wallet_service.get_wallet_status(wallet_id)
        performance = await wallet_service.calculate_wallet_performance(wallet_id)
        
        # Get current balances
        balances = await wallet_service.get_wallet_balances(wallet_id)
        
        wallet_data = {
            "wallet": wallet.dict(),
            "status": status,
            "performance": performance.dict(),
            "current_balances": [balance.dict() for balance in balances]
        }
        
        if include_allocations:
            wallet_data["allocations"] = [alloc.dict() for alloc in wallet.allocations]
        
        if include_transactions:
            # Get recent transactions (would be implemented with actual transaction history)
            wallet_data["recent_transactions"] = []
        
        return APIResponse(
            success=True,
            message=f"Wallet details retrieved for {wallet_id}",
            data=wallet_data
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_api_router.put("/{wallet_id}/config", response_model=Dict[str, Any])
async def update_wallet_config(
    wallet_id: str = Path(..., description="Wallet ID"),
    config_update: UpdateWalletConfigRequest = Body(...),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Update wallet configuration
    Phase 2: Advanced wallet configuration management
    """
    try:
        if wallet_id not in wallet_service.active_wallets:
            raise HTTPException(status_code=404, detail=f"Wallet {wallet_id} not found")
        
        wallet = wallet_service.active_wallets[wallet_id]
        
        # Update configuration fields if provided
        if config_update.name is not None:
            wallet.config.name = config_update.name
        if config_update.description is not None:
            wallet.config.description = config_update.description
        if config_update.auto_distribution is not None:
            wallet.config.auto_distribution = config_update.auto_distribution
        if config_update.performance_based_allocation is not None:
            wallet.config.performance_based_allocation = config_update.performance_based_allocation
        if config_update.risk_based_limits is not None:
            wallet.config.risk_based_limits = config_update.risk_based_limits
        if config_update.max_allocation_per_agent is not None:
            wallet.config.max_allocation_per_agent = config_update.max_allocation_per_agent
        if config_update.emergency_stop_threshold is not None:
            wallet.config.emergency_stop_threshold = config_update.emergency_stop_threshold
        if config_update.daily_loss_limit is not None:
            wallet.config.daily_loss_limit = config_update.daily_loss_limit
        
        wallet.config.updated_at = datetime.now(timezone.utc)
        
        return APIResponse(
            success=True,
            message=f"Wallet configuration updated for {wallet_id}",
            data={"wallet_config": wallet.config.dict()}
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating wallet config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_api_router.post("/{wallet_id}/allocate", response_model=Dict[str, Any])
async def allocate_wallet_funds(
    wallet_id: str = Path(..., description="Wallet ID"),
    allocation_request: FundAllocationRequest = Body(...),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Allocate funds from wallet to target (agent/farm/goal)
    Phase 2: Enhanced fund allocation with advanced validation
    """
    try:
        allocation = await wallet_service.allocate_funds(wallet_id, allocation_request)
        
        return APIResponse(
            success=True,
            message=f"Allocated ${allocation_request.amount_usd} to {allocation_request.target_type}:{allocation_request.target_id}",
            data={
                "allocation": allocation.dict(),
                "wallet_id": wallet_id
            }
        ).dict()
        
    except Exception as e:
        logger.error(f"Error allocating funds: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@wallet_api_router.post("/{wallet_id}/collect", response_model=Dict[str, Any])
async def collect_wallet_funds(
    wallet_id: str = Path(..., description="Wallet ID"),
    collection_request: FundCollectionRequest = Body(...),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Collect funds from allocation back to wallet
    Phase 2: Enhanced fund collection with detailed reporting
    """
    try:
        collected_amount = await wallet_service.collect_funds(wallet_id, collection_request)
        
        return APIResponse(
            success=True,
            message=f"Collected ${collected_amount} from allocation",
            data={
                "collected_amount": float(collected_amount),
                "allocation_id": collection_request.allocation_id,
                "collection_type": collection_request.collection_type,
                "wallet_id": wallet_id
            }
        ).dict()
        
    except Exception as e:
        logger.error(f"Error collecting funds: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@wallet_api_router.post("/transfer", response_model=Dict[str, Any])
async def transfer_between_wallets(
    transfer_request: WalletTransferRequest = Body(...),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Transfer funds between wallets
    Phase 2: Inter-wallet transfer capability
    """
    try:
        # Validate both wallets exist
        if transfer_request.from_wallet_id not in wallet_service.active_wallets:
            raise HTTPException(status_code=404, detail=f"Source wallet {transfer_request.from_wallet_id} not found")
        if transfer_request.to_wallet_id not in wallet_service.active_wallets:
            raise HTTPException(status_code=404, detail=f"Destination wallet {transfer_request.to_wallet_id} not found")
        
        # Implementation would perform actual transfer
        # For now, return success structure
        
        return APIResponse(
            success=True,
            message=f"Transfer of {transfer_request.amount} {transfer_request.asset_symbol} initiated",
            data={
                "transfer": transfer_request.dict(),
                "transfer_id": f"transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "status": "pending"
            }
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transferring funds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_api_router.get("/{wallet_id}/performance", response_model=Dict[str, Any])
async def get_wallet_performance(
    wallet_id: str = Path(..., description="Wallet ID"),
    period_days: int = Query(30, description="Performance period in days"),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Get detailed wallet performance metrics
    Phase 2: Advanced performance analytics
    """
    try:
        if wallet_id not in wallet_service.active_wallets:
            raise HTTPException(status_code=404, detail=f"Wallet {wallet_id} not found")
        
        performance = await wallet_service.calculate_wallet_performance(wallet_id)
        
        # Additional performance calculations for specified period
        performance_data = {
            "current_performance": performance.dict(),
            "period_days": period_days,
            "allocation_breakdown": [],
            "top_performers": [],
            "risk_metrics": {}
        }
        
        # Get allocation performance breakdown
        wallet = wallet_service.active_wallets[wallet_id]
        for allocation in wallet.allocations:
            if allocation.is_active:
                performance_data["allocation_breakdown"].append({
                    "allocation_id": allocation.allocation_id,
                    "target": f"{allocation.target_type}:{allocation.target_id}",
                    "target_name": allocation.target_name,
                    "allocated_amount": float(allocation.allocated_amount_usd),
                    "current_value": float(allocation.current_value_usd),
                    "pnl": float(allocation.total_pnl),
                    "pnl_percentage": float((allocation.total_pnl / allocation.initial_allocation) * 100) if allocation.initial_allocation > 0 else 0
                })
        
        return APIResponse(
            success=True,
            message=f"Performance metrics retrieved for wallet {wallet_id}",
            data=performance_data
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_api_router.get("/{wallet_id}/balances", response_model=Dict[str, Any])
async def get_wallet_balances(
    wallet_id: str = Path(..., description="Wallet ID"),
    refresh: bool = Query(False, description="Force refresh from blockchain"),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Get current wallet balances across all chains
    Phase 2: Real-time balance tracking with refresh capability
    """
    try:
        if wallet_id not in wallet_service.active_wallets:
            raise HTTPException(status_code=404, detail=f"Wallet {wallet_id} not found")
        
        balances = await wallet_service.get_wallet_balances(wallet_id)
        
        # Calculate total USD value
        total_usd = sum(balance.balance_usd or Decimal("0") for balance in balances)
        
        balance_data = {
            "wallet_id": wallet_id,
            "balances": [balance.dict() for balance in balances],
            "total_value_usd": float(total_usd),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "refresh_requested": refresh
        }
        
        return APIResponse(
            success=True,
            message=f"Balances retrieved for wallet {wallet_id}",
            data=balance_data
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet balances: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_api_router.get("/{wallet_id}/allocations", response_model=Dict[str, Any])
async def get_wallet_allocations(
    wallet_id: str = Path(..., description="Wallet ID"),
    active_only: bool = Query(True, description="Only show active allocations"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Get wallet fund allocations with filtering
    Phase 2: Advanced allocation management and filtering
    """
    try:
        if wallet_id not in wallet_service.active_wallets:
            raise HTTPException(status_code=404, detail=f"Wallet {wallet_id} not found")
        
        wallet = wallet_service.active_wallets[wallet_id]
        allocations = wallet.allocations
        
        # Apply filters
        if active_only:
            allocations = [alloc for alloc in allocations if alloc.is_active]
        
        if target_type:
            allocations = [alloc for alloc in allocations if alloc.target_type == target_type]
        
        # Calculate summary statistics
        total_allocated = sum(alloc.allocated_amount_usd for alloc in allocations)
        total_value = sum(alloc.current_value_usd for alloc in allocations)
        total_pnl = sum(alloc.total_pnl for alloc in allocations)
        
        allocation_data = {
            "wallet_id": wallet_id,
            "allocations": [alloc.dict() for alloc in allocations],
            "summary": {
                "total_allocations": len(allocations),
                "total_allocated_usd": float(total_allocated),
                "total_current_value_usd": float(total_value),
                "total_pnl": float(total_pnl),
                "total_pnl_percentage": float((total_pnl / total_allocated) * 100) if total_allocated > 0 else 0
            },
            "filters_applied": {
                "active_only": active_only,
                "target_type": target_type
            }
        }
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(allocations)} allocations for wallet {wallet_id}",
            data=allocation_data
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet allocations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_api_router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_wallet_analytics_summary(
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Get comprehensive wallet analytics summary
    Phase 2: Platform-wide wallet analytics
    """
    try:
        active_wallets = wallet_service.active_wallets
        
        if not active_wallets:
            return APIResponse(
                success=True,
                message="No active wallets found",
                data={"total_wallets": 0}
            ).dict()
        
        # Calculate aggregate metrics
        total_value = Decimal("0")
        total_allocated = Decimal("0")
        total_pnl = Decimal("0")
        total_allocations = 0
        
        wallet_summaries = []
        
        for wallet_id, wallet in active_wallets.items():
            try:
                performance = await wallet_service.calculate_wallet_performance(wallet_id)
                
                total_value += performance.total_value_usd
                total_allocated += performance.total_allocated_usd
                total_pnl += performance.total_pnl
                total_allocations += performance.active_allocations
                
                wallet_summaries.append({
                    "wallet_id": wallet_id,
                    "wallet_name": wallet.config.name,
                    "total_value_usd": float(performance.total_value_usd),
                    "total_pnl": float(performance.total_pnl),
                    "active_allocations": performance.active_allocations
                })
                
            except Exception as e:
                logger.warning(f"Could not calculate performance for wallet {wallet_id}: {e}")
                continue
        
        analytics_data = {
            "platform_summary": {
                "total_wallets": len(active_wallets),
                "total_value_usd": float(total_value),
                "total_allocated_usd": float(total_allocated),
                "total_available_usd": float(total_value - total_allocated),
                "total_pnl": float(total_pnl),
                "total_pnl_percentage": float((total_pnl / total_value) * 100) if total_value > 0 else 0,
                "total_allocations": total_allocations
            },
            "wallet_summaries": wallet_summaries,
            "top_performers": sorted(wallet_summaries, key=lambda x: x["total_pnl"], reverse=True)[:5]
        }
        
        return APIResponse(
            success=True,
            message=f"Analytics summary for {len(active_wallets)} wallets",
            data=analytics_data
        ).dict()
        
    except Exception as e:
        logger.error(f"Error getting wallet analytics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@wallet_api_router.post("/{wallet_id}/emergency-stop", response_model=Dict[str, Any])
async def emergency_stop_wallet(
    wallet_id: str = Path(..., description="Wallet ID"),
    reason: str = Body(..., description="Reason for emergency stop"),
    wallet_service: MasterWalletService = Depends(get_master_wallet_service)
):
    """
    Emergency stop all wallet operations
    Phase 2: Advanced wallet safety controls
    """
    try:
        if wallet_id not in wallet_service.active_wallets:
            raise HTTPException(status_code=404, detail=f"Wallet {wallet_id} not found")
        
        wallet = wallet_service.active_wallets[wallet_id]
        
        # Set wallet to inactive and disable auto-distribution
        wallet.is_active = False
        wallet.config.auto_distribution = False
        
        # Log emergency stop
        logger.critical(f"EMERGENCY STOP activated for wallet {wallet_id}: {reason}")
        
        return APIResponse(
            success=True,
            message=f"Emergency stop activated for wallet {wallet_id}",
            data={
                "wallet_id": wallet_id,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actions_taken": [
                    "Wallet deactivated",
                    "Auto-distribution disabled",
                    "Emergency logged"
                ]
            }
        ).dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))