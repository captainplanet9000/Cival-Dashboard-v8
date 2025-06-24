"""
Phase 6-8 Autonomous Trading System API Endpoints
Master Wallet, Farm Management, Goal System, and Smart Contract APIs
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..core.service_registry import get_service_dependency
from ..auth.dependencies import get_current_active_user
from ..models.auth_models import AuthenticatedUser

logger = logging.getLogger(__name__)

# Create router for autonomous trading endpoints
router = APIRouter(prefix="/api/v1/autonomous", tags=["Autonomous Trading System"])

# =============================================================================
# MASTER WALLET API ENDPOINTS
# =============================================================================

class WalletCreateRequest(BaseModel):
    """Request model for creating a master wallet"""
    wallet_name: str = Field(..., description="Name of the wallet")
    description: Optional[str] = Field(None, description="Wallet description")
    supported_chains: List[str] = Field(default=["ethereum", "polygon", "bsc"], description="Supported blockchain networks")
    auto_distribution: bool = Field(True, description="Enable automatic fund distribution")
    max_allocation_per_agent: float = Field(0.25, description="Maximum allocation percentage per agent")
    risk_tolerance: float = Field(0.7, description="Risk tolerance (0.0-1.0)")

class AllocationRequest(BaseModel):
    """Request model for fund allocation"""
    target_type: str = Field(..., description="Type of target (agent, farm, goal)")
    target_id: str = Field(..., description="Target ID")
    amount_usd: float = Field(..., description="Amount to allocate in USD")

@router.post("/wallets")
async def create_master_wallet(
    wallet_request: WalletCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    fund_engine = Depends(get_service_dependency("autonomous_fund_distribution_engine"))
):
    """Create a new master wallet"""
    try:
        wallet = await fund_engine.create_master_wallet(wallet_request.dict())
        logger.info(f"Created master wallet {wallet['wallet_id']} for user {current_user.user_id}")
        return wallet
    except Exception as e:
        logger.error(f"Failed to create master wallet: {e}")
        raise HTTPException(status_code=500, detail=f"Wallet creation failed: {str(e)}")

@router.get("/wallets")
async def get_master_wallets(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    fund_engine = Depends(get_service_dependency("autonomous_fund_distribution_engine"))
):
    """Get all master wallets"""
    try:
        wallets = await fund_engine.get_all_wallets()
        return {"wallets": wallets, "user_id": current_user.user_id}
    except Exception as e:
        logger.error(f"Failed to get wallets: {e}")
        raise HTTPException(status_code=500, detail=f"Wallet retrieval failed: {str(e)}")

@router.get("/wallets/{wallet_id}")
async def get_wallet_details(
    wallet_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    fund_engine = Depends(get_service_dependency("autonomous_fund_distribution_engine"))
):
    """Get detailed wallet information"""
    try:
        wallet = await fund_engine.get_wallet_details(wallet_id)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        return wallet
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get wallet details: {e}")
        raise HTTPException(status_code=500, detail=f"Wallet retrieval failed: {str(e)}")

@router.post("/wallets/{wallet_id}/allocate")
async def allocate_funds(
    wallet_id: str,
    allocation_request: AllocationRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    fund_engine = Depends(get_service_dependency("autonomous_fund_distribution_engine"))
):
    """Allocate funds to a target (agent, farm, or goal)"""
    try:
        allocation = await fund_engine.allocate_funds(
            wallet_id=wallet_id,
            target_type=allocation_request.target_type,
            target_id=allocation_request.target_id,
            amount=Decimal(str(allocation_request.amount_usd))
        )
        logger.info(f"Allocated ${allocation_request.amount_usd} from wallet {wallet_id} to {allocation_request.target_type} {allocation_request.target_id}")
        return allocation
    except Exception as e:
        logger.error(f"Failed to allocate funds: {e}")
        raise HTTPException(status_code=500, detail=f"Fund allocation failed: {str(e)}")

@router.post("/wallets/{wallet_id}/distribute")
async def execute_autonomous_distribution(
    wallet_id: str,
    background_tasks: BackgroundTasks,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    fund_engine = Depends(get_service_dependency("autonomous_fund_distribution_engine"))
):
    """Execute autonomous fund distribution"""
    try:
        # Run distribution in background
        background_tasks.add_task(fund_engine.execute_autonomous_distribution, wallet_id)
        
        return {
            "message": "Autonomous distribution initiated",
            "wallet_id": wallet_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to execute autonomous distribution: {e}")
        raise HTTPException(status_code=500, detail=f"Distribution failed: {str(e)}")

# =============================================================================
# FARM MANAGEMENT API ENDPOINTS
# =============================================================================

class FarmCreateRequest(BaseModel):
    """Request model for creating a farm"""
    name: str = Field(..., description="Farm name")
    type: str = Field(..., description="Farm type (trend_following, breakout, etc.)")
    description: Optional[str] = Field(None, description="Farm description")
    max_agents: int = Field(10, description="Maximum number of agents")
    use_template: Optional[str] = Field(None, description="Template to use")
    strategy_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Strategy configuration")

class AgentAssignmentRequest(BaseModel):
    """Request model for assigning agent to farm"""
    agent_id: str = Field(..., description="Agent ID to assign")
    role: str = Field("primary", description="Agent role (primary, support, specialist)")

@router.post("/farms")
async def create_farm(
    farm_request: FarmCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    farm_service = Depends(get_service_dependency("farm_management_service"))
):
    """Create a new agent farm"""
    try:
        farm = await farm_service.create_farm(farm_request.dict())
        logger.info(f"Created farm {farm.farm_id} for user {current_user.user_id}")
        return {
            "farm_id": farm.farm_id,
            "name": farm.farm_name,
            "type": farm.farm_type.value,
            "status": farm.status.value,
            "max_agents": farm.max_agents,
            "created_at": farm.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to create farm: {e}")
        raise HTTPException(status_code=500, detail=f"Farm creation failed: {str(e)}")

@router.get("/farms")
async def get_farms(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    farm_service = Depends(get_service_dependency("farm_management_service"))
):
    """Get all farms"""
    try:
        farms = await farm_service.get_all_active_farms()
        return {
            "farms": [
                {
                    "farm_id": farm.farm_id,
                    "name": farm.farm_name,
                    "type": farm.farm_type.value,
                    "status": farm.status.value,
                    "current_agents": farm.current_agents,
                    "max_agents": farm.max_agents
                }
                for farm in farms
            ],
            "user_id": current_user.user_id
        }
    except Exception as e:
        logger.error(f"Failed to get farms: {e}")
        raise HTTPException(status_code=500, detail=f"Farm retrieval failed: {str(e)}")

@router.get("/farms/{farm_id}")
async def get_farm_status(
    farm_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    farm_service = Depends(get_service_dependency("farm_management_service"))
):
    """Get detailed farm status"""
    try:
        farm_status = await farm_service.get_farm_status(farm_id)
        if not farm_status:
            raise HTTPException(status_code=404, detail="Farm not found")
        return farm_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get farm status: {e}")
        raise HTTPException(status_code=500, detail=f"Farm status retrieval failed: {str(e)}")

@router.post("/farms/{farm_id}/agents")
async def assign_agent_to_farm(
    farm_id: str,
    assignment_request: AgentAssignmentRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    farm_service = Depends(get_service_dependency("farm_management_service"))
):
    """Assign an agent to a farm"""
    try:
        assignment = await farm_service.assign_agent_to_farm(
            farm_id=farm_id,
            agent_id=assignment_request.agent_id,
            role=assignment_request.role
        )
        logger.info(f"Assigned agent {assignment_request.agent_id} to farm {farm_id}")
        return {
            "assignment_id": assignment.assignment_id,
            "farm_id": farm_id,
            "agent_id": assignment.agent_id,
            "role": assignment.role,
            "assigned_at": assignment.assigned_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to assign agent to farm: {e}")
        raise HTTPException(status_code=500, detail=f"Agent assignment failed: {str(e)}")

@router.delete("/farms/{farm_id}/agents/{agent_id}")
async def remove_agent_from_farm(
    farm_id: str,
    agent_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    farm_service = Depends(get_service_dependency("farm_management_service"))
):
    """Remove an agent from a farm"""
    try:
        success = await farm_service.remove_agent_from_farm(farm_id, agent_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove agent from farm")
        
        logger.info(f"Removed agent {agent_id} from farm {farm_id}")
        return {"message": "Agent removed from farm successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove agent from farm: {e}")
        raise HTTPException(status_code=500, detail=f"Agent removal failed: {str(e)}")

@router.post("/farms/{farm_id}/activate")
async def activate_farm(
    farm_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    farm_service = Depends(get_service_dependency("farm_management_service"))
):
    """Activate a farm"""
    try:
        success = await farm_service.activate_farm(farm_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to activate farm")
        
        logger.info(f"Activated farm {farm_id}")
        return {"message": "Farm activated successfully", "farm_id": farm_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate farm: {e}")
        raise HTTPException(status_code=500, detail=f"Farm activation failed: {str(e)}")

@router.post("/farms/{farm_id}/pause")
async def pause_farm(
    farm_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    farm_service = Depends(get_service_dependency("farm_management_service"))
):
    """Pause a farm"""
    try:
        success = await farm_service.pause_farm(farm_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to pause farm")
        
        logger.info(f"Paused farm {farm_id}")
        return {"message": "Farm paused successfully", "farm_id": farm_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause farm: {e}")
        raise HTTPException(status_code=500, detail=f"Farm pause failed: {str(e)}")

# =============================================================================
# GOAL MANAGEMENT API ENDPOINTS
# =============================================================================

class GoalCreateRequest(BaseModel):
    """Request model for creating a goal"""
    goal_name: str = Field(..., description="Goal name")
    goal_type: str = Field(..., description="Goal type (profit_target, trade_count, etc.)")
    description: Optional[str] = Field(None, description="Goal description")
    target_value: float = Field(..., description="Target value to achieve")
    priority: int = Field(2, description="Goal priority (1-5)")
    target_date: Optional[datetime] = Field(None, description="Target completion date")

@router.post("/goals")
async def create_goal(
    goal_request: GoalCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_service_dependency("goal_management_service"))
):
    """Create a new goal"""
    try:
        goal = await goal_service.create_goal(goal_request.dict())
        logger.info(f"Created goal {goal.goal_id} for user {current_user.user_id}")
        return {
            "goal_id": goal.goal_id,
            "name": goal.goal_name,
            "type": goal.goal_type.value,
            "status": goal.status.value,
            "target_value": float(goal.target_value),
            "progress_percentage": float(goal.progress_percentage),
            "created_at": goal.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to create goal: {e}")
        raise HTTPException(status_code=500, detail=f"Goal creation failed: {str(e)}")

@router.get("/goals")
async def get_goals(
    status: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_service_dependency("goal_management_service"))
):
    """Get all goals"""
    try:
        goals = await goal_service.get_all_active_goals()
        
        # Filter by status if provided
        if status:
            goals = [goal for goal in goals if goal.status.value == status]
        
        return {
            "goals": [
                {
                    "goal_id": goal.goal_id,
                    "name": goal.goal_name,
                    "type": goal.goal_type.value,
                    "status": goal.status.value,
                    "target_value": float(goal.target_value),
                    "current_value": float(goal.current_value),
                    "progress_percentage": float(goal.progress_percentage),
                    "priority": goal.priority.value
                }
                for goal in goals
            ],
            "user_id": current_user.user_id
        }
    except Exception as e:
        logger.error(f"Failed to get goals: {e}")
        raise HTTPException(status_code=500, detail=f"Goal retrieval failed: {str(e)}")

@router.get("/goals/{goal_id}")
async def get_goal_status(
    goal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_service_dependency("goal_management_service"))
):
    """Get detailed goal status"""
    try:
        goal_status = await goal_service.get_goal_status(goal_id)
        if not goal_status:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get goal status: {e}")
        raise HTTPException(status_code=500, detail=f"Goal status retrieval failed: {str(e)}")

@router.post("/goals/{goal_id}/assign-agent")
async def assign_agent_to_goal(
    goal_id: str,
    agent_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_service_dependency("goal_management_service"))
):
    """Assign an agent to a goal"""
    try:
        success = await goal_service.assign_agent_to_goal(goal_id, agent_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to assign agent to goal")
        
        logger.info(f"Assigned agent {agent_id} to goal {goal_id}")
        return {"message": "Agent assigned to goal successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign agent to goal: {e}")
        raise HTTPException(status_code=500, detail=f"Agent assignment failed: {str(e)}")

@router.post("/goals/{goal_id}/complete")
async def complete_goal(
    goal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_service_dependency("goal_management_service"))
):
    """Manually complete a goal"""
    try:
        completion = await goal_service.complete_goal(goal_id)
        if not completion:
            raise HTTPException(status_code=400, detail="Failed to complete goal")
        
        logger.info(f"Completed goal {goal_id}")
        return {
            "message": "Goal completed successfully",
            "completion_data": completion
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete goal: {e}")
        raise HTTPException(status_code=500, detail=f"Goal completion failed: {str(e)}")

# =============================================================================
# SMART CONTRACT API ENDPOINTS
# =============================================================================

@router.get("/contracts/status")
async def get_contract_status(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    contract_service = Depends(get_service_dependency("master_wallet_contracts"))
):
    """Get smart contract service status"""
    try:
        status = await contract_service.get_service_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get contract status: {e}")
        raise HTTPException(status_code=500, detail=f"Contract status retrieval failed: {str(e)}")

@router.get("/contracts/{chain_name}/transactions")
async def get_chain_transactions(
    chain_name: str,
    limit: int = 10,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    contract_service = Depends(get_service_dependency("master_wallet_contracts"))
):
    """Get recent transactions for a blockchain"""
    try:
        transactions = await contract_service.get_recent_transactions(chain_name, limit)
        return {"chain_name": chain_name, "transactions": transactions}
    except Exception as e:
        logger.error(f"Failed to get chain transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Transaction retrieval failed: {str(e)}")

# =============================================================================
# SYSTEM STATUS AND MONITORING
# =============================================================================

@router.get("/status")
async def get_autonomous_system_status(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    fund_engine = Depends(get_service_dependency("autonomous_fund_distribution_engine")),
    farm_service = Depends(get_service_dependency("farm_management_service")),
    goal_service = Depends(get_service_dependency("goal_management_service")),
    contract_service = Depends(get_service_dependency("master_wallet_contracts"))
):
    """Get comprehensive autonomous system status"""
    try:
        # Get status from all services
        fund_status = await fund_engine.get_service_status()
        farm_status = await farm_service.get_service_status()
        goal_status = await goal_service.get_service_status()
        contract_status = await contract_service.get_service_status()
        
        return {
            "autonomous_system_status": "operational",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "fund_distribution": fund_status,
                "farm_management": farm_status,
                "goal_management": goal_status,
                "smart_contracts": contract_status
            }
        }
    except Exception as e:
        logger.error(f"Failed to get autonomous system status: {e}")
        raise HTTPException(status_code=500, detail=f"System status retrieval failed: {str(e)}")