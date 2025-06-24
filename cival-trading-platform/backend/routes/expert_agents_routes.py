"""
Expert Agents API Routes
RESTful API endpoints for specialized expert agent management
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from ..services.expert_agent_integration_service import ExpertAgentIntegrationService
from ..models.specialized_expert_agents import ExpertAgentType, LearningPhase, DecisionConfidence
from ..core.database_manager import DatabaseManager

# Initialize router
router = APIRouter(prefix="/api/v1/expert-agents", tags=["Expert Agents"])

# Request/Response Models
class CreateExpertAgentRequest(BaseModel):
    agent_type: ExpertAgentType = Field(..., description="Type of expert agent to create")
    name: Optional[str] = Field(None, description="Custom name for the agent")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration parameters")

class AnalyzeSymbolRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol to analyze")
    market_data: Dict[str, Any] = Field(..., description="Market data for analysis")
    agent_types: Optional[List[ExpertAgentType]] = Field(None, description="Specific agent types to use")

class AssignGoalRequest(BaseModel):
    goal_type: str = Field(..., description="Type of goal (accuracy, profit, learning)")
    target_value: float = Field(..., description="Target value to achieve")
    measurement_period: str = Field(default="daily", description="Measurement period")
    deadline: Optional[datetime] = Field(None, description="Goal deadline")

class UpdatePerformanceRequest(BaseModel):
    decision_correct: bool = Field(..., description="Whether the decision was correct")
    trade_profitable: Optional[bool] = Field(None, description="Whether the trade was profitable")

class LearningDataRequest(BaseModel):
    learning_data: Dict[str, Any] = Field(..., description="Learning experience data")

class CoordinationConfigRequest(BaseModel):
    consensus_threshold: Optional[float] = Field(None, ge=0, le=1, description="Consensus threshold")
    weight_by_performance: Optional[bool] = Field(None, description="Weight by performance")

# Dependency to get expert agent service
async def get_expert_agent_service() -> ExpertAgentIntegrationService:
    """Get expert agent integration service"""
    db_manager = DatabaseManager()
    return ExpertAgentIntegrationService(db_manager)

# Expert Agent Management Endpoints

@router.post("/create")
async def create_expert_agent(
    request: CreateExpertAgentRequest,
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Create a new expert agent"""
    
    try:
        # Add name to config if provided
        config = request.config.copy()
        if request.name:
            config["name"] = request.name
        
        result = await service.create_expert_agent(request.agent_type, config)
        
        if result.get("success"):
            return JSONResponse(content=result, status_code=201)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_agents_status(
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Get status of all expert agents"""
    
    try:
        result = await service.get_agent_status()
        
        if result.get("success") is False:
            return JSONResponse(content=result, status_code=400)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{agent_id}")
async def get_agent_status(
    agent_id: str = Path(..., description="Expert agent ID"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Get status of a specific expert agent"""
    
    try:
        result = await service.get_agent_status(agent_id)
        
        if result.get("success") is False:
            return JSONResponse(content=result, status_code=404)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{agent_id}")
async def delete_expert_agent(
    agent_id: str = Path(..., description="Expert agent ID"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Delete an expert agent"""
    
    try:
        # Remove agent from active agents
        if agent_id in service.active_agents:
            del service.active_agents[agent_id]
        
        if agent_id in service.expert_coordinator.expert_agents:
            del service.expert_coordinator.expert_agents[agent_id]
        
        if agent_id in service.performance_metrics:
            del service.performance_metrics[agent_id]
        
        if agent_id in service.agent_goals:
            del service.agent_goals[agent_id]
        
        return {
            "success": True,
            "agent_id": agent_id,
            "message": "Expert agent deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analysis Endpoints

@router.post("/analyze")
async def analyze_symbol(
    request: AnalyzeSymbolRequest,
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Get expert analysis for a trading symbol"""
    
    try:
        result = await service.analyze_symbol(
            request.symbol,
            request.market_data,
            request.agent_types
        )
        
        if result.get("success") is False:
            return JSONResponse(content=result, status_code=400)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyze/{symbol}")
async def quick_analyze_symbol(
    symbol: str = Path(..., description="Trading symbol"),
    agent_types: Optional[str] = Query(None, description="Comma-separated agent types"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Quick analysis with minimal market data"""
    
    try:
        # Parse agent types if provided
        agent_type_list = None
        if agent_types:
            agent_type_list = [ExpertAgentType(t.strip()) for t in agent_types.split(",")]
        
        # Create minimal market data
        market_data = {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": 100.0,  # Mock price
            "volume": 1000000  # Mock volume
        }
        
        result = await service.analyze_symbol(symbol, market_data, agent_type_list)
        
        if result.get("success") is False:
            return JSONResponse(content=result, status_code=400)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Goal Management Endpoints

@router.post("/goals/{agent_id}")
async def assign_goal_to_agent(
    agent_id: str = Path(..., description="Expert agent ID"),
    request: AssignGoalRequest = Body(...),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Assign a goal to an expert agent"""
    
    try:
        goal_config = request.dict()
        result = await service.assign_goal_to_agent(agent_id, goal_config)
        
        if result.get("success"):
            return JSONResponse(content=result, status_code=201)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/goals/{agent_id}")
async def get_agent_goals(
    agent_id: str = Path(..., description="Expert agent ID"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Get goals for an expert agent"""
    
    try:
        if agent_id not in service.agent_goals:
            return {"agent_id": agent_id, "goals": []}
        
        goals = service.agent_goals[agent_id]
        goals_data = [
            {
                "goal_id": goal.goal_id,
                "goal_type": goal.goal_type,
                "target_value": goal.target_value,
                "current_value": goal.current_value,
                "completion_rate": goal.completion_rate,
                "is_active": goal.is_active,
                "is_completed": goal.is_completed,
                "created_at": goal.created_at.isoformat(),
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
                "completed_at": goal.completed_at.isoformat() if goal.completed_at else None
            }
            for goal in goals
        ]
        
        return {
            "agent_id": agent_id,
            "total_goals": len(goals),
            "active_goals": len([g for g in goals if g.is_active]),
            "completed_goals": len([g for g in goals if g.is_completed]),
            "goals": goals_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Performance Management Endpoints

@router.post("/performance/{agent_id}")
async def update_agent_performance(
    agent_id: str = Path(..., description="Expert agent ID"),
    request: UpdatePerformanceRequest = Body(...),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Update agent performance metrics"""
    
    try:
        result = await service.update_agent_performance(
            agent_id,
            request.decision_correct,
            request.trade_profitable
        )
        
        if result.get("success"):
            return result
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/{agent_id}")
async def get_agent_performance(
    agent_id: str = Path(..., description="Expert agent ID"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Get agent performance metrics"""
    
    try:
        if agent_id not in service.performance_metrics:
            raise HTTPException(status_code=404, detail="Agent performance metrics not found")
        
        metrics = service.performance_metrics[agent_id]
        
        return {
            "agent_id": agent_id,
            "performance": metrics.dict(),
            "last_updated": metrics.last_updated.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Learning Endpoints

@router.post("/learning/{agent_id}")
async def trigger_learning_cycle(
    agent_id: str = Path(..., description="Expert agent ID"),
    request: LearningDataRequest = Body(...),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Trigger a learning cycle for an agent"""
    
    try:
        result = await service.trigger_learning_cycle(agent_id, request.learning_data)
        
        if result.get("success"):
            return result
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/learning/{agent_id}")
async def get_agent_learning_status(
    agent_id: str = Path(..., description="Expert agent ID"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Get agent learning status and memory"""
    
    try:
        if agent_id not in service.active_agents:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent = service.active_agents[agent_id]
        
        learning_status = {
            "agent_id": agent_id,
            "learning_phase": getattr(agent, 'learning_phase', LearningPhase.LEARNING).value,
            "learning_cycles_completed": getattr(agent, 'learning_cycles_completed', 0),
            "expertise_level": getattr(agent, 'expertise_level', 0.5),
        }
        
        # Add memory information if available
        if hasattr(agent, 'memory'):
            learning_status.update({
                "memory": {
                    "short_term_size": len(agent.memory.short_term),
                    "medium_term_patterns": len(agent.memory.medium_term),
                    "episodic_memories": len(agent.memory.episodic),
                    "long_term_knowledge": list(agent.memory.long_term.keys()) if agent.memory.long_term else []
                }
            })
        
        return learning_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Optimization Endpoints

@router.post("/optimize/{agent_id}")
async def optimize_agent_parameters(
    agent_id: str = Path(..., description="Expert agent ID"),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Optimize agent parameters based on performance"""
    
    try:
        result = await service.optimize_agent_parameters(agent_id)
        
        if result.get("success"):
            return result
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Coordination Endpoints

@router.get("/coordination/status")
async def get_coordination_status(
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Get agent coordination status"""
    
    try:
        coordinator = service.expert_coordinator
        
        return {
            "coordinator_id": coordinator.coordinator_id,
            "total_experts": len(coordinator.expert_agents),
            "consensus_threshold": coordinator.consensus_threshold,
            "weight_by_performance": coordinator.weight_by_performance,
            "expert_agents": [
                {
                    "agent_id": agent_id,
                    "agent_type": agent.agent_type.value,
                    "name": agent.name,
                    "expertise_level": getattr(agent, 'expertise_level', 0.5)
                }
                for agent_id, agent in coordinator.expert_agents.items()
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/coordination/configure")
async def configure_coordination(
    request: CoordinationConfigRequest = Body(...),
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Configure agent coordination parameters"""
    
    try:
        coordinator = service.expert_coordinator
        
        # Update configuration
        if request.consensus_threshold is not None:
            coordinator.consensus_threshold = request.consensus_threshold
        
        if request.weight_by_performance is not None:
            coordinator.weight_by_performance = request.weight_by_performance
        
        return {
            "success": True,
            "message": "Coordination configuration updated",
            "configuration": {
                "consensus_threshold": coordinator.consensus_threshold,
                "weight_by_performance": coordinator.weight_by_performance
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Utility Endpoints

@router.get("/types")
async def get_expert_agent_types() -> Dict[str, Any]:
    """Get available expert agent types"""
    
    return {
        "agent_types": [
            {
                "type": agent_type.value,
                "name": agent_type.value.replace("_", " ").title(),
                "description": f"{agent_type.value.replace('_', ' ').title()} strategy expert"
            }
            for agent_type in ExpertAgentType
        ]
    }

@router.get("/learning-phases")
async def get_learning_phases() -> Dict[str, Any]:
    """Get available learning phases"""
    
    return {
        "learning_phases": [
            {
                "phase": phase.value,
                "name": phase.value.title(),
                "description": f"Agent in {phase.value} phase"
            }
            for phase in LearningPhase
        ]
    }

@router.get("/confidence-levels")
async def get_confidence_levels() -> Dict[str, Any]:
    """Get available confidence levels"""
    
    return {
        "confidence_levels": [
            {
                "level": conf.value,
                "name": conf.value.replace("_", " ").title(),
                "range": {
                    "very_low": "0-20%",
                    "low": "20-40%",
                    "medium": "40-60%",
                    "high": "60-80%",
                    "very_high": "80-100%"
                }.get(conf.value, "Unknown")
            }
            for conf in DecisionConfidence
        ]
    }

# Analytics Endpoints

@router.get("/analytics/summary")
async def get_analytics_summary(
    service: ExpertAgentIntegrationService = Depends(get_expert_agent_service)
) -> Dict[str, Any]:
    """Get comprehensive analytics summary for all expert agents"""
    
    try:
        total_agents = len(service.active_agents)
        total_decisions = sum(metrics.total_decisions for metrics in service.performance_metrics.values())
        average_accuracy = sum(metrics.accuracy_rate for metrics in service.performance_metrics.values()) / total_agents if total_agents > 0 else 0
        
        # Agent type breakdown
        agent_type_breakdown = {}
        for agent in service.active_agents.values():
            agent_type = agent.agent_type.value
            if agent_type not in agent_type_breakdown:
                agent_type_breakdown[agent_type] = {"count": 0, "total_accuracy": 0}
            agent_type_breakdown[agent_type]["count"] += 1
            if agent.agent_id in service.performance_metrics:
                agent_type_breakdown[agent_type]["total_accuracy"] += service.performance_metrics[agent.agent_id].accuracy_rate
        
        # Calculate average accuracy per type
        for agent_type, data in agent_type_breakdown.items():
            data["average_accuracy"] = data["total_accuracy"] / data["count"] if data["count"] > 0 else 0
            del data["total_accuracy"]  # Remove intermediate calculation
        
        # Goal statistics
        total_goals = sum(len(goals) for goals in service.agent_goals.values())
        active_goals = sum(len([g for g in goals if g.is_active]) for goals in service.agent_goals.values())
        completed_goals = sum(len([g for g in goals if g.is_completed]) for goals in service.agent_goals.values())
        
        return {
            "summary": {
                "total_agents": total_agents,
                "total_decisions": total_decisions,
                "average_accuracy": round(average_accuracy, 3),
                "total_goals": total_goals,
                "active_goals": active_goals,
                "completed_goals": completed_goals,
                "goal_completion_rate": completed_goals / total_goals if total_goals > 0 else 0
            },
            "agent_type_breakdown": agent_type_breakdown,
            "coordination_stats": {
                "consensus_threshold": service.expert_coordinator.consensus_threshold,
                "weight_by_performance": service.expert_coordinator.weight_by_performance
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))