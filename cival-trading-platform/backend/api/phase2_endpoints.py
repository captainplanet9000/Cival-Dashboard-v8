"""
Phase 2 API Endpoints - Agent Trading Integration
New endpoints for agent trading bridge, safety controls, and performance tracking
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..core.service_registry import get_service_dependency
from ..services.agent_trading_bridge import AgentTradingBridge, TradingSignal, ExecutionResult
from ..services.trading_safety_service import TradingSafetyService
from ..services.agent_performance_service import AgentPerformanceService
from ..services.agent_coordination_service import AgentCoordinationService, AnalysisRequest, FrameworkType
from ..auth.dependencies import get_current_active_user
from ..models.auth_models import AuthenticatedUser

# Create router for Phase 2 endpoints
router = APIRouter(prefix="/api/v1/agent-trading", tags=["Agent Trading"])

# Request/Response models for API
class TradingSignalRequest(BaseModel):
    """Request model for submitting trading signals"""
    agent_id: str
    symbol: str
    action: str  # "buy" or "sell"
    quantity: float
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0)
    strategy: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SafetyStatusResponse(BaseModel):
    """Response model for safety status"""
    emergency_stop_active: bool
    trading_suspended: bool
    circuit_breakers: Dict[str, Any]
    recent_violations: List[Dict[str, Any]]
    active_agents: int
    trading_limits: Dict[str, Any]

class PerformanceResponse(BaseModel):
    """Response model for agent performance"""
    agent_id: str
    total_trades: int
    win_rate: float
    total_pnl_usd: float
    sharpe_ratio: Optional[float]
    max_drawdown_percentage: float
    last_7_days_pnl: float
    current_streak: int

class AnalysisRequestModel(BaseModel):
    """Request model for agent analysis"""
    symbol: str
    framework: Optional[str] = None  # "crewai" or "autogen" 
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"
    timeout_seconds: int = 120

# Agent Trading Bridge Endpoints
@router.post("/signals/submit", response_model=ExecutionResult)
async def submit_trading_signal(
    signal_request: TradingSignalRequest,
    bridge: AgentTradingBridge = Depends(get_service_dependency("agent_trading_bridge")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Submit a trading signal from an AI agent for execution"""
    
    # Convert request to TradingSignal
    signal = TradingSignal(
        agent_id=signal_request.agent_id,
        symbol=signal_request.symbol,
        action=signal_request.action,
        quantity=signal_request.quantity,
        price_target=signal_request.price_target,
        stop_loss=signal_request.stop_loss,
        take_profit=signal_request.take_profit,
        confidence=signal_request.confidence,
        strategy=signal_request.strategy,
        metadata=signal_request.metadata
    )
    
    # Process through bridge
    result = await bridge.process_agent_signal(signal)
    return result

@router.get("/signals/status/{signal_id}", response_model=Optional[ExecutionResult])
async def get_signal_status(
    signal_id: str,
    bridge: AgentTradingBridge = Depends(get_service_dependency("agent_trading_bridge")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get status of a trading signal"""
    result = await bridge.get_signal_status(signal_id)
    if not result:
        raise HTTPException(status_code=404, detail="Signal not found")
    return result

@router.get("/signals/active")
async def get_active_signals(
    agent_id: Optional[str] = None,
    bridge: AgentTradingBridge = Depends(get_service_dependency("agent_trading_bridge")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get active trading signals"""
    signals = await bridge.get_active_signals(agent_id)
    return {"signals": signals, "count": len(signals)}

@router.delete("/signals/{signal_id}")
async def cancel_signal(
    signal_id: str,
    bridge: AgentTradingBridge = Depends(get_service_dependency("agent_trading_bridge")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Cancel an active trading signal"""
    success = await bridge.cancel_signal(signal_id)
    if not success:
        raise HTTPException(status_code=404, detail="Signal not found or already processed")
    return {"message": "Signal cancelled", "signal_id": signal_id}

@router.get("/bridge/status")
async def get_bridge_status(
    bridge: AgentTradingBridge = Depends(get_service_dependency("agent_trading_bridge")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get agent trading bridge status"""
    return bridge.get_bridge_status()

@router.post("/bridge/enable")
async def enable_bridge(
    bridge: AgentTradingBridge = Depends(get_service_dependency("agent_trading_bridge")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Enable the agent trading bridge"""
    bridge.enable_bridge()
    return {"message": "Agent trading bridge enabled"}

@router.post("/bridge/disable")
async def disable_bridge(
    bridge: AgentTradingBridge = Depends(get_service_dependency("agent_trading_bridge")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Disable the agent trading bridge for safety"""
    bridge.disable_bridge()
    return {"message": "Agent trading bridge disabled"}

# Trading Safety Endpoints
@router.get("/safety/status", response_model=SafetyStatusResponse)
async def get_safety_status(
    safety_service: TradingSafetyService = Depends(get_service_dependency("trading_safety_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get comprehensive trading safety status"""
    status = safety_service.get_safety_status()
    return SafetyStatusResponse(**status)

@router.get("/safety/agent/{agent_id}")
async def get_agent_safety_status(
    agent_id: str,
    safety_service: TradingSafetyService = Depends(get_service_dependency("trading_safety_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get safety status for specific agent"""
    status = safety_service.get_agent_safety_status(agent_id)
    if not status:
        raise HTTPException(status_code=404, detail="Agent not found")
    return status

@router.post("/safety/emergency-stop")
async def activate_emergency_stop(
    reason: str,
    safety_service: TradingSafetyService = Depends(get_service_dependency("trading_safety_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Activate emergency stop - halt all trading"""
    await safety_service.activate_emergency_stop(reason)
    return {"message": "Emergency stop activated", "reason": reason}

@router.post("/safety/emergency-stop/deactivate")
async def deactivate_emergency_stop(
    safety_service: TradingSafetyService = Depends(get_service_dependency("trading_safety_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Deactivate emergency stop"""
    await safety_service.deactivate_emergency_stop()
    return {"message": "Emergency stop deactivated"}

@router.post("/safety/suspend")
async def suspend_trading(
    reason: str,
    safety_service: TradingSafetyService = Depends(get_service_dependency("trading_safety_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Suspend all trading temporarily"""
    await safety_service.suspend_trading(reason)
    return {"message": "Trading suspended", "reason": reason}

@router.post("/safety/resume")
async def resume_trading(
    safety_service: TradingSafetyService = Depends(get_service_dependency("trading_safety_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Resume trading after suspension"""
    await safety_service.resume_trading()
    return {"message": "Trading resumed"}

# Agent Performance Endpoints
@router.get("/performance/{agent_id}", response_model=Optional[PerformanceResponse])
async def get_agent_performance(
    agent_id: str,
    period_days: int = 30,
    performance_service: AgentPerformanceService = Depends(get_service_dependency("agent_performance_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get comprehensive performance metrics for an agent"""
    metrics = await performance_service.get_agent_performance(agent_id, period_days)
    if not metrics:
        raise HTTPException(status_code=404, detail="Performance data not found")
    
    return PerformanceResponse(
        agent_id=metrics.agent_id,
        total_trades=metrics.total_trades,
        win_rate=metrics.win_rate,
        total_pnl_usd=metrics.total_pnl_usd,
        sharpe_ratio=metrics.sharpe_ratio,
        max_drawdown_percentage=metrics.max_drawdown_percentage,
        last_7_days_pnl=metrics.last_7_days_pnl,
        current_streak=metrics.current_streak
    )

@router.get("/performance/rankings")
async def get_agent_rankings(
    period_days: int = 30,
    performance_service: AgentPerformanceService = Depends(get_service_dependency("agent_performance_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get agent performance rankings"""
    rankings = await performance_service.get_agent_rankings(period_days)
    return {"rankings": rankings, "count": len(rankings), "period_days": period_days}

@router.get("/performance/portfolio")
async def get_portfolio_performance(
    period_days: int = 30,
    performance_service: AgentPerformanceService = Depends(get_service_dependency("agent_performance_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get overall portfolio performance across all agents"""
    portfolio = await performance_service.get_portfolio_performance(period_days)
    return portfolio

@router.post("/performance/trade-entry")
async def record_trade_entry(
    trade_id: str,
    agent_id: str,
    symbol: str,
    side: str,
    quantity: float,
    entry_price: float,
    strategy: str,
    confidence: float,
    metadata: Dict[str, Any] = None,
    performance_service: AgentPerformanceService = Depends(get_service_dependency("agent_performance_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Record a new trade entry for performance tracking"""
    trade = await performance_service.record_trade_entry(
        trade_id, agent_id, symbol, side, quantity, entry_price, strategy, confidence, metadata
    )
    return {"message": "Trade entry recorded", "trade": trade.model_dump()}

@router.post("/performance/trade-exit")
async def record_trade_exit(
    trade_id: str,
    exit_price: float,
    fees_usd: float = 0.0,
    performance_service: AgentPerformanceService = Depends(get_service_dependency("agent_performance_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Record trade exit and calculate PnL"""
    trade = await performance_service.record_trade_exit(trade_id, exit_price, fees_usd)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"message": "Trade exit recorded", "trade": trade.model_dump()}

# Agent Coordination Endpoints
@router.post("/analysis/single")
async def analyze_symbol(
    request: AnalysisRequestModel,
    coordination_service: AgentCoordinationService = Depends(get_service_dependency("agent_coordination_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Analyze a symbol using specified framework or best available"""
    framework = FrameworkType(request.framework) if request.framework else None
    
    result = await coordination_service.analyze_symbol(
        symbol=request.symbol,
        framework=framework,
        context=request.context,
        priority=request.priority,
        timeout_seconds=request.timeout_seconds
    )
    
    return result.model_dump()

@router.post("/analysis/consensus")
async def run_consensus_analysis(
    request: AnalysisRequestModel,
    frameworks: Optional[List[str]] = None,
    coordination_service: AgentCoordinationService = Depends(get_service_dependency("agent_coordination_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Run analysis using multiple frameworks and reach consensus"""
    framework_types = None
    if frameworks:
        framework_types = [FrameworkType(f) for f in frameworks]
    
    task = await coordination_service.run_consensus_analysis(
        symbol=request.symbol,
        context=request.context,
        frameworks=framework_types
    )
    
    return task.model_dump()

@router.get("/analysis/task/{task_id}")
async def get_task_status(
    task_id: str,
    coordination_service: AgentCoordinationService = Depends(get_service_dependency("agent_coordination_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get status of a coordination task"""
    task = coordination_service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump()

@router.post("/signals/execute")
async def execute_trading_signal_via_coordination(
    signal_request: TradingSignalRequest,
    coordination_service: AgentCoordinationService = Depends(get_service_dependency("agent_coordination_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Execute a trading signal through the coordination layer"""
    signal = TradingSignal(
        agent_id=signal_request.agent_id,
        symbol=signal_request.symbol,
        action=signal_request.action,
        quantity=signal_request.quantity,
        price_target=signal_request.price_target,
        stop_loss=signal_request.stop_loss,
        take_profit=signal_request.take_profit,
        confidence=signal_request.confidence,
        strategy=signal_request.strategy,
        metadata=signal_request.metadata
    )
    
    result = await coordination_service.execute_trading_signal(signal)
    return result

@router.get("/coordination/status")
async def get_coordination_status(
    coordination_service: AgentCoordinationService = Depends(get_service_dependency("agent_coordination_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get comprehensive coordination service status"""
    return coordination_service.get_coordination_status()

# Service Status Endpoint
@router.get("/status")
async def get_phase2_status(
    bridge: AgentTradingBridge = Depends(get_service_dependency("agent_trading_bridge")),
    safety_service: TradingSafetyService = Depends(get_service_dependency("trading_safety_service")),
    performance_service: AgentPerformanceService = Depends(get_service_dependency("agent_performance_service")),
    coordination_service: AgentCoordinationService = Depends(get_service_dependency("agent_coordination_service")),
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Get comprehensive Phase 2 agent trading status"""
    return {
        "phase2_status": "operational",
        "bridge": bridge.get_bridge_status(),
        "safety": safety_service.get_safety_status(),
        "performance": performance_service.get_service_status(),
        "coordination": coordination_service.get_coordination_status(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }