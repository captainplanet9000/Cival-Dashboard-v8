"""
Expert Agents API Routes
Endpoints for managing and interacting with specialized expert agents
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from services.expert_agent_integration_service import (
    get_expert_agent_integration_service,
    ExpertAgentIntegrationService
)
from models.specialized_expert_agents import BaseExpertAgent

router = APIRouter(prefix="/api/v1/expert-agents", tags=["expert-agents"])


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class CreateExpertAgentRequest(BaseModel):
    """Request to create a new expert agent"""
    agent_type: str = Field(..., description="Type of expert agent (DarvasBoxExpert, ElliottWaveExpert, etc.)")
    name: str = Field(..., description="Name for the expert agent")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration parameters")


class ExpertAgentResponse(BaseModel):
    """Response containing expert agent details"""
    agent_id: str
    agent_type: str
    name: str
    version: str
    is_active: bool
    total_decisions: int
    success_rate: float
    sharpe_ratio: float
    max_drawdown: float
    created_at: datetime


class MarketAnalysisRequest(BaseModel):
    """Request for market analysis"""
    symbol: str = Field(..., description="Trading symbol to analyze")
    timeframe: str = Field(default="H1", description="Timeframe for analysis")
    include_history: bool = Field(default=True, description="Include historical data in analysis")
    price_history: Optional[List[Dict[str, Any]]] = Field(None, description="Optional price history data")
    market_data: Dict[str, Any] = Field(default_factory=dict, description="Additional market data")


class ExpertAnalysisResponse(BaseModel):
    """Individual expert analysis response"""
    agent_type: str
    recommendation: str
    confidence: float
    reasoning: str
    additional_data: Dict[str, Any] = Field(default_factory=dict)


class CoordinatedAnalysisResponse(BaseModel):
    """Coordinated analysis response from all experts"""
    analysis_id: str
    symbol: str
    timestamp: datetime
    expert_analyses: Dict[str, ExpertAnalysisResponse]
    coordinated_decision: Dict[str, Any]
    recommendation: str
    confidence: float
    risk_assessment: Optional[Dict[str, Any]] = None


class ExpertPerformanceResponse(BaseModel):
    """Expert agent performance metrics"""
    agent_id: str
    name: str
    agent_type: str
    total_decisions: int
    success_rate: float
    sharpe_ratio: float
    max_drawdown: float
    cumulative_pnl: float
    learning_progress: int
    last_decision_time: Optional[datetime] = None


class CollectivePerformanceResponse(BaseModel):
    """Collective performance of all expert agents"""
    total_experts: int
    active_experts: int
    expert_performance: Dict[str, ExpertPerformanceResponse]
    collective_metrics: Dict[str, Any]
    weight_distribution: Dict[str, float]


# ==========================================
# EXPERT AGENT MANAGEMENT ENDPOINTS
# ==========================================

@router.post("/create", response_model=ExpertAgentResponse)
async def create_expert_agent(
    request: CreateExpertAgentRequest,
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Create a new specialized expert agent"""
    try:
        agent = await service.create_expert_agent(request.agent_type, request.config)
        
        return ExpertAgentResponse(
            agent_id=agent.agent_id,
            agent_type=agent.agent_type,
            name=agent.name,
            version=agent.version,
            is_active=agent.is_active,
            total_decisions=agent.total_decisions,
            success_rate=(agent.successful_decisions / max(agent.total_decisions, 1)) * 100,
            sharpe_ratio=agent.sharpe_ratio,
            max_drawdown=agent.max_drawdown,
            created_at=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=List[ExpertAgentResponse])
async def list_expert_agents(
    active_only: bool = Query(False, description="Filter for active agents only"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """List all expert agents"""
    try:
        agents = []
        
        for agent_id, agent in service.expert_agents.items():
            # Apply filters
            if active_only and not agent.is_active:
                continue
            if agent_type and agent.agent_type != agent_type:
                continue
            
            agents.append(ExpertAgentResponse(
                agent_id=agent.agent_id,
                agent_type=agent.agent_type,
                name=agent.name,
                version=agent.version,
                is_active=agent.is_active,
                total_decisions=agent.total_decisions,
                success_rate=(agent.successful_decisions / max(agent.total_decisions, 1)) * 100,
                sharpe_ratio=agent.sharpe_ratio,
                max_drawdown=agent.max_drawdown,
                created_at=datetime.now()
            ))
        
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=Dict[str, Any])
async def get_expert_agent_details(
    agent_id: str,
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Get detailed information about a specific expert agent"""
    try:
        if agent_id not in service.expert_agents:
            raise HTTPException(status_code=404, detail="Expert agent not found")
        
        agent = service.expert_agents[agent_id]
        
        return {
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type,
            "name": agent.name,
            "version": agent.version,
            "is_active": agent.is_active,
            "performance": {
                "total_decisions": agent.total_decisions,
                "successful_decisions": agent.successful_decisions,
                "success_rate": (agent.successful_decisions / max(agent.total_decisions, 1)) * 100,
                "cumulative_pnl": float(agent.cumulative_pnl),
                "sharpe_ratio": agent.sharpe_ratio,
                "max_drawdown": agent.max_drawdown
            },
            "knowledge_domain": agent.knowledge_domain.dict(),
            "learning_mechanism": {
                "algorithm": agent.learning_mechanism.learning_algorithm,
                "adaptation_rate": agent.learning_mechanism.adaptation_rate,
                "exploration_rate": agent.learning_mechanism.exploration_rate,
                "experience_count": len(agent.learning_mechanism.experience_buffer),
                "success_patterns": len(agent.learning_mechanism.success_patterns),
                "failure_patterns": len(agent.learning_mechanism.failure_patterns)
            },
            "decision_framework": agent.decision_framework.dict(),
            "memory_system": {
                "short_term_entries": len(agent.memory_system.short_term_memory),
                "medium_term_entries": len(agent.memory_system.medium_term_memory),
                "long_term_entries": len(agent.memory_system.long_term_memory),
                "episodic_memories": len(agent.memory_system.episodic_memory),
                "learning_rate": agent.memory_system.learning_rate
            },
            "current_positions": agent.current_positions,
            "last_decision_time": agent.last_decision_time
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}/activate")
async def activate_expert_agent(
    agent_id: str,
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Activate an expert agent"""
    try:
        if agent_id not in service.expert_agents:
            raise HTTPException(status_code=404, detail="Expert agent not found")
        
        agent = service.expert_agents[agent_id]
        agent.is_active = True
        
        return {"message": f"Expert agent {agent.name} activated", "agent_id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}/deactivate")
async def deactivate_expert_agent(
    agent_id: str,
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Deactivate an expert agent"""
    try:
        if agent_id not in service.expert_agents:
            raise HTTPException(status_code=404, detail="Expert agent not found")
        
        agent = service.expert_agents[agent_id]
        agent.is_active = False
        
        return {"message": f"Expert agent {agent.name} deactivated", "agent_id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# MARKET ANALYSIS ENDPOINTS
# ==========================================

@router.post("/analyze", response_model=CoordinatedAnalysisResponse)
async def analyze_market(
    request: MarketAnalysisRequest,
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Perform coordinated market analysis using all active expert agents"""
    try:
        # Prepare market data
        market_data = request.market_data
        market_data["symbol"] = request.symbol
        market_data["timeframe"] = request.timeframe
        
        if request.price_history:
            market_data["price_history"] = request.price_history
        
        # Perform analysis
        analysis = await service.analyze_market(request.symbol, market_data)
        
        # Convert to response format
        expert_analyses = {}
        for agent_id, agent_analysis in analysis["expert_analyses"].items():
            expert_analyses[agent_id] = ExpertAnalysisResponse(
                agent_type=agent_analysis.get("agent_type", "unknown"),
                recommendation=agent_analysis.get("recommendation", "hold"),
                confidence=agent_analysis.get("confidence", 0.0),
                reasoning=agent_analysis.get("reasoning", ""),
                additional_data={
                    k: v for k, v in agent_analysis.items()
                    if k not in ["agent_type", "recommendation", "confidence", "reasoning"]
                }
            )
        
        return CoordinatedAnalysisResponse(
            analysis_id=analysis["analysis_id"],
            symbol=analysis["symbol"],
            timestamp=analysis["timestamp"],
            expert_analyses=expert_analyses,
            coordinated_decision=analysis["coordinated_decision"],
            recommendation=analysis["recommendation"],
            confidence=analysis["confidence"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{analysis_id}")
async def get_analysis_details(
    analysis_id: str,
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Get details of a specific analysis"""
    try:
        if analysis_id not in service.active_analyses:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return service.active_analyses[analysis_id]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# PERFORMANCE MONITORING ENDPOINTS
# ==========================================

@router.get("/performance/summary", response_model=CollectivePerformanceResponse)
async def get_performance_summary(
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Get performance summary for all expert agents"""
    try:
        summary = await service.get_expert_performance_summary()
        
        # Convert to response format
        expert_performance = {}
        for agent_id, perf in summary["expert_performance"].items():
            expert_performance[agent_id] = ExpertPerformanceResponse(
                agent_id=agent_id,
                name=perf["name"],
                agent_type=perf["type"],
                total_decisions=perf["total_decisions"],
                success_rate=perf["success_rate"],
                sharpe_ratio=perf["sharpe_ratio"],
                max_drawdown=perf["max_drawdown"],
                cumulative_pnl=float(summary["collective_metrics"]["total_pnl"]) / max(len(summary["expert_performance"]), 1),
                learning_progress=perf["learning_progress"]
            )
        
        return CollectivePerformanceResponse(
            total_experts=summary["total_experts"],
            active_experts=summary["active_experts"],
            expert_performance=expert_performance,
            collective_metrics=summary["collective_metrics"],
            weight_distribution=service.agent_coordinator.weight_distribution
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/optimize-weights")
async def optimize_expert_weights(
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Optimize expert agent weights based on recent performance"""
    try:
        await service.optimize_expert_weights()
        
        return {
            "message": "Expert weights optimized successfully",
            "new_weights": service.agent_coordinator.weight_distribution
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{agent_id}/history")
async def get_agent_performance_history(
    agent_id: str,
    days: int = Query(30, description="Number of days of history"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Get performance history for a specific expert agent"""
    try:
        if agent_id not in service.expert_agents:
            raise HTTPException(status_code=404, detail="Expert agent not found")
        
        agent = service.expert_agents[agent_id]
        
        # Get performance history from learning mechanism
        performance_history = agent.learning_mechanism.performance_history[-days:]
        
        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "agent_type": agent.agent_type,
            "history": performance_history,
            "current_metrics": {
                "success_rate": (agent.successful_decisions / max(agent.total_decisions, 1)) * 100,
                "sharpe_ratio": agent.sharpe_ratio,
                "max_drawdown": agent.max_drawdown,
                "cumulative_pnl": float(agent.cumulative_pnl)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# LEARNING AND MEMORY ENDPOINTS
# ==========================================

@router.get("/{agent_id}/memory")
async def get_agent_memory(
    agent_id: str,
    memory_type: str = Query("all", description="Type of memory to retrieve (short_term, medium_term, long_term, all)"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Get memory contents for a specific expert agent"""
    try:
        if agent_id not in service.expert_agents:
            raise HTTPException(status_code=404, detail="Expert agent not found")
        
        agent = service.expert_agents[agent_id]
        memory_system = agent.memory_system
        
        if memory_type == "all":
            return {
                "short_term_memory": memory_system.short_term_memory,
                "medium_term_memory": memory_system.medium_term_memory,
                "long_term_memory": memory_system.long_term_memory,
                "episodic_memory": memory_system.episodic_memory,
                "semantic_memory": memory_system.semantic_memory
            }
        elif memory_type == "short_term":
            return {"short_term_memory": memory_system.short_term_memory}
        elif memory_type == "medium_term":
            return {"medium_term_memory": memory_system.medium_term_memory}
        elif memory_type == "long_term":
            return {"long_term_memory": memory_system.long_term_memory}
        else:
            raise HTTPException(status_code=400, detail="Invalid memory type")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/trigger-learning")
async def trigger_agent_learning(
    agent_id: str,
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Manually trigger learning process for an expert agent"""
    try:
        if agent_id not in service.expert_agents:
            raise HTTPException(status_code=404, detail="Expert agent not found")
        
        agent = service.expert_agents[agent_id]
        await service._trigger_agent_learning(agent)
        
        return {
            "message": f"Learning triggered for {agent.name}",
            "learning_stats": {
                "experience_buffer_size": len(agent.learning_mechanism.experience_buffer),
                "success_patterns": len(agent.learning_mechanism.success_patterns),
                "failure_patterns": len(agent.learning_mechanism.failure_patterns),
                "adaptation_rate": agent.learning_mechanism.adaptation_rate
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# COORDINATION SETTINGS ENDPOINTS
# ==========================================

@router.get("/coordination/settings")
async def get_coordination_settings(
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Get current coordination settings"""
    try:
        coordinator = service.agent_coordinator
        
        return {
            "coordination_mode": coordinator.coordination_mode,
            "consensus_threshold": coordinator.consensus_threshold,
            "weight_distribution": coordinator.weight_distribution,
            "active_agents": len(coordinator.expert_agents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/coordination/settings")
async def update_coordination_settings(
    coordination_mode: Optional[str] = Query(None, description="Coordination mode (consensus, weighted, hierarchical, dynamic)"),
    consensus_threshold: Optional[float] = Query(None, ge=0.5, le=1.0, description="Consensus threshold"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_integration_service)
):
    """Update coordination settings"""
    try:
        coordinator = service.agent_coordinator
        
        if coordination_mode:
            if coordination_mode not in ["consensus", "weighted", "hierarchical", "dynamic"]:
                raise HTTPException(status_code=400, detail="Invalid coordination mode")
            coordinator.coordination_mode = coordination_mode
        
        if consensus_threshold is not None:
            coordinator.consensus_threshold = consensus_threshold
        
        return {
            "message": "Coordination settings updated",
            "new_settings": {
                "coordination_mode": coordinator.coordination_mode,
                "consensus_threshold": coordinator.consensus_threshold
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))