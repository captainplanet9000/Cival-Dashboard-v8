"""
Phase 8 API Endpoints - Enhanced Goal Management + Farm Knowledge System
RESTful API endpoints for natural language goals and knowledge management
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

# Import models
from ..models.enhanced_goal_models import (
    EnhancedGoal, CreateEnhancedGoalRequest, NaturalLanguageGoalInput,
    GoalAnalyticsRequest, GoalAnalyticsResponse, GoalRecommendationEngine,
    GoalCollaborationRequest, LLMProvider, GoalCreationMethod
)
from ..models.farm_knowledge_models import (
    FarmResource, CreateResourceRequest, ResourceSearchRequest, ResourceSearchResponse,
    AgentKnowledgeRequest, TradingResourceType, AccessLevel, ContentFormat,
    ResourceMetadata, BulkResourceOperation
)

# Import dependencies
from ..auth.dependencies import get_current_active_user
from ..models.auth_models import AuthenticatedUser
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

# Create router for Phase 8 endpoints
router = APIRouter(prefix="/api/v1/phase8", tags=["Phase 8 - Goals & Knowledge"])

def get_enhanced_goal_service():
    """Dependency to get enhanced goal management service"""
    registry = get_registry()
    service = registry.get_service("enhanced_goal_management_service")
    if not service:
        raise HTTPException(status_code=503, detail="Enhanced goal management service not available")
    return service

def get_farm_knowledge_service():
    """Dependency to get farm knowledge service"""
    registry = get_registry()
    service = registry.get_service("farm_knowledge_service")
    if not service:
        raise HTTPException(status_code=503, detail="Farm knowledge service not available")
    return service

# Enhanced Goal Management Endpoints

@router.post("/goals/create-natural", response_model=Dict[str, Any])
async def create_goal_from_natural_language(
    request: CreateEnhancedGoalRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_enhanced_goal_service)
):
    """Create a goal from natural language input using LLM analysis"""
    
    try:
        # Add user context
        if not request.user_context:
            request.user_context = {}
        request.user_context["user_id"] = current_user.user_id
        
        # Create goal using enhanced service
        goal = await goal_service.create_goal_from_natural_language(request)
        
        return {
            "success": True,
            "goal": goal.model_dump(),
            "message": f"Successfully created goal: {goal.goal_name}"
        }
        
    except Exception as e:
        logger.error(f"Failed to create goal from natural language: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/goals/analyze-input", response_model=Dict[str, Any])
async def analyze_natural_language_input(
    input_data: NaturalLanguageGoalInput,
    llm_provider: LLMProvider = LLMProvider.OPENAI,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_enhanced_goal_service)
):
    """Analyze natural language input without creating a goal"""
    
    try:
        # Create analysis request
        from ..models.enhanced_goal_models import LLMAnalysisRequest
        
        analysis_request = LLMAnalysisRequest(
            natural_language_input=input_data.input_text,
            user_context={"user_id": current_user.user_id},
            preferred_provider=llm_provider,
            analysis_depth="detailed"
        )
        
        # Analyze with LLM
        analysis = await goal_service._analyze_goal_with_llm(analysis_request)
        
        return {
            "success": True,
            "analysis": analysis.model_dump(),
            "suggestions": {
                "goal_name": goal_service._generate_goal_name_from_analysis(analysis),
                "complexity": analysis.complexity_assessment.value,
                "feasibility": analysis.feasibility_assessment,
                "estimated_timeframe": analysis.timeframe
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze natural language input: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/goals/{goal_id}/status", response_model=Dict[str, Any])
async def get_enhanced_goal_status(
    goal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_enhanced_goal_service)
):
    """Get comprehensive status of an enhanced goal"""
    
    try:
        status = await goal_service.get_enhanced_goal_status(goal_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        return {
            "success": True,
            "goal_status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get goal status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/goals/active", response_model=Dict[str, Any])
async def get_active_goals(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_enhanced_goal_service)
):
    """Get all active goals for the current user"""
    
    try:
        active_goals = await goal_service.get_all_active_goals()
        
        # Filter goals for current user
        user_goals = [
            goal for goal in active_goals 
            if goal.created_by == current_user.user_id
        ]
        
        return {
            "success": True,
            "active_goals": [goal.model_dump() for goal in user_goals],
            "total_count": len(user_goals)
        }
        
    except Exception as e:
        logger.error(f"Failed to get active goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/goals/analytics", response_model=GoalAnalyticsResponse)
async def get_goal_analytics(
    request: GoalAnalyticsRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_enhanced_goal_service)
):
    """Get comprehensive goal analytics and insights"""
    
    try:
        # Add user filter if not specified
        if not request.user_id:
            request.user_id = current_user.user_id
        
        analytics = await goal_service.get_goal_analytics(request)
        
        return analytics
        
    except Exception as e:
        logger.error(f"Failed to get goal analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/goals/recommendations", response_model=Dict[str, Any])
async def get_goal_recommendations(
    request: GoalRecommendationEngine,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_enhanced_goal_service)
):
    """Get AI-powered goal recommendations"""
    
    try:
        # Ensure user ID matches current user
        request.user_id = current_user.user_id
        
        recommendations = await goal_service.get_goal_recommendations(request)
        
        return {
            "success": True,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get goal recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/goals/{goal_id}/collaborate", response_model=Dict[str, Any])
async def manage_goal_collaboration(
    goal_id: str,
    request: GoalCollaborationRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_enhanced_goal_service)
):
    """Manage goal collaboration features"""
    
    try:
        result = await goal_service.manage_goal_collaboration(goal_id, request, current_user.user_id)
        
        return {
            "success": True,
            "collaboration_result": result,
            "message": f"Goal collaboration {request.collaboration_action} completed"
        }
        
    except Exception as e:
        logger.error(f"Failed to manage goal collaboration: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Farm Knowledge Management Endpoints

@router.post("/knowledge/upload", response_model=Dict[str, Any])
async def upload_knowledge_resource(
    title: str = Form(...),
    description: str = Form(None),
    resource_type: TradingResourceType = Form(...),
    tags: str = Form(""),  # Comma-separated tags
    access_level: AccessLevel = Form(AccessLevel.PUBLIC),
    auto_process: bool = Form(True),
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Upload a new knowledge resource file"""
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Convert to base64 for processing
        import base64
        file_data = base64.b64encode(file_content).decode('utf-8')
        
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Create metadata
        metadata = ResourceMetadata(
            title=title,
            description=description,
            author=current_user.user_id
        )
        
        # Create resource request
        create_request = CreateResourceRequest(
            resource_type=resource_type,
            title=title,
            description=description,
            file_data=file_data,
            metadata=metadata,
            tags=tag_list,
            access_level=access_level,
            auto_process=auto_process
        )
        
        # Create resource
        resource = await knowledge_service.create_resource(create_request, current_user.user_id)
        
        return {
            "success": True,
            "resource": resource.model_dump(),
            "message": f"Successfully uploaded {resource.title}"
        }
        
    except Exception as e:
        logger.error(f"Failed to upload knowledge resource: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/knowledge/create-from-url", response_model=Dict[str, Any])
async def create_resource_from_url(
    request: CreateResourceRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Create a knowledge resource from a URL"""
    
    try:
        resource = await knowledge_service.create_resource(request, current_user.user_id)
        
        return {
            "success": True,
            "resource": resource.model_dump(),
            "message": f"Successfully created resource from URL: {resource.title}"
        }
        
    except Exception as e:
        logger.error(f"Failed to create resource from URL: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/knowledge/search", response_model=ResourceSearchResponse)
async def search_knowledge_resources(
    request: ResourceSearchRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Search farm knowledge resources"""
    
    try:
        # Add user context for personalized results
        results = await knowledge_service.search_resources(request, current_user.user_id)
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to search knowledge resources: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/knowledge/resource/{resource_id}", response_model=Dict[str, Any])
async def get_knowledge_resource(
    resource_id: str,
    include_content: bool = False,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Get a specific knowledge resource"""
    
    try:
        resource = await knowledge_service.get_resource_by_id(resource_id)
        
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        # Check access permissions
        has_access = await knowledge_service.check_agent_access(current_user.user_id, resource_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied to this resource")
        
        response_data = {
            "success": True,
            "resource": resource.model_dump()
        }
        
        # Include content if requested
        if include_content:
            content = await knowledge_service.get_resource_content(resource_id, current_user.user_id)
            response_data["content"] = content
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/resource/{resource_id}/content", response_model=Dict[str, Any])
async def get_resource_content(
    resource_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Get the full content of a knowledge resource"""
    
    try:
        content = await knowledge_service.get_resource_content(resource_id, current_user.user_id)
        
        if content is None:
            raise HTTPException(status_code=404, detail="Resource not found or access denied")
        
        return {
            "success": True,
            "resource_id": resource_id,
            "content": content,
            "accessed_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resource content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/agent-request", response_model=Dict[str, Any])
async def handle_agent_knowledge_request(
    request: AgentKnowledgeRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Handle agent knowledge requests with AI recommendations"""
    
    try:
        # Ensure agent ID is valid (could be current user or authorized agent)
        if request.agent_id != current_user.user_id:
            # Check if user has permission to make requests for this agent
            agent_service = get_registry().get_service("agent_management_service")
            if agent_service:
                has_permission = await agent_service.check_user_agent_permission(
                    current_user.user_id, request.agent_id
                )
                if not has_permission:
                    raise HTTPException(status_code=403, detail="No permission for this agent")
        
        # Process agent knowledge request
        if request.request_type == "search":
            search_request = ResourceSearchRequest(
                query=request.query,
                limit=request.max_results
            )
            results = await knowledge_service.search_resources(search_request, request.agent_id)
            
            return {
                "success": True,
                "request_type": "search",
                "results": results.model_dump()
            }
        
        elif request.request_type == "recommend":
            recommendations = await knowledge_service.get_ai_recommendations({
                "agent_id": request.agent_id,
                "recommendation_type": "performance_improvement",
                "max_recommendations": request.max_results
            })
            
            return {
                "success": True,
                "request_type": "recommend",
                "recommendations": recommendations
            }
        
        elif request.request_type == "learn":
            learning_resources = await knowledge_service.get_learning_resources({
                "agent_id": request.agent_id,
                "skill_area": request.query or "general",
                "current_level": "intermediate"
            })
            
            return {
                "success": True,
                "request_type": "learn",
                "learning_resources": [resource.model_dump() for resource in learning_resources]
            }
        
        else:
            raise HTTPException(status_code=400, detail="Invalid request type")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to handle agent knowledge request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/sops", response_model=Dict[str, Any])
async def get_trading_sops(
    strategy_type: Optional[str] = None,
    situation: Optional[str] = None,
    urgency: str = "medium",
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Get relevant standard operating procedures"""
    
    try:
        search_criteria = {
            "agent_id": current_user.user_id,
            "strategy_type": strategy_type,
            "situation": situation,
            "urgency": urgency
        }
        
        sops = await knowledge_service.get_contextual_sops(search_criteria)
        
        return {
            "success": True,
            "sops": [sop.model_dump() for sop in sops],
            "search_criteria": search_criteria,
            "total_count": len(sops)
        }
        
    except Exception as e:
        logger.error(f"Failed to get trading SOPs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/market-research", response_model=Dict[str, Any])
async def get_market_research(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    research_type: str = "all",
    recency: str = "latest",
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Get relevant market research documents"""
    
    try:
        search_criteria = {
            "agent_id": current_user.user_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "research_type": research_type,
            "recency": recency
        }
        
        research = await knowledge_service.get_market_research(search_criteria)
        
        return {
            "success": True,
            "research_documents": [doc.model_dump() for doc in research],
            "search_criteria": search_criteria,
            "total_count": len(research)
        }
        
    except Exception as e:
        logger.error(f"Failed to get market research: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/bulk-operation", response_model=Dict[str, Any])
async def perform_bulk_resource_operation(
    operation: BulkResourceOperation,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Perform bulk operations on knowledge resources"""
    
    try:
        # Verify user has permission for all resources
        for resource_id in operation.resource_ids:
            has_access = await knowledge_service.check_agent_access(current_user.user_id, resource_id)
            if not has_access:
                raise HTTPException(status_code=403, detail=f"No access to resource {resource_id}")
        
        # Perform bulk operation
        results = await knowledge_service.perform_bulk_operation(operation, current_user.user_id)
        
        return {
            "success": True,
            "operation": operation.operation,
            "affected_resources": len(operation.resource_ids),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform bulk operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Real-time Event Streaming Endpoints

@router.get("/stream/goal-events")
async def stream_goal_events(
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Server-sent events for real-time goal updates"""
    
    async def event_generator():
        registry = get_registry()
        
        while True:
            try:
                # Get goal service
                goal_service = registry.get_service("enhanced_goal_management_service")
                
                if goal_service:
                    # Get user's active goals
                    active_goals = await goal_service.get_all_active_goals()
                    user_goals = [
                        goal for goal in active_goals 
                        if goal.created_by == current_user.user_id
                    ]
                    
                    # Generate event data
                    event_data = {
                        "event_type": "goal_status_update",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": current_user.user_id,
                        "active_goals_count": len(user_goals),
                        "goals": [
                            {
                                "goal_id": goal.goal_id,
                                "name": goal.goal_name,
                                "progress": goal.progress_percentage,
                                "status": goal.status
                            }
                            for goal in user_goals
                        ]
                    }
                    
                    yield {
                        "event": "goal_update",
                        "data": json.dumps(event_data)
                    }
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in goal event stream: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }
                break
    
    return EventSourceResponse(event_generator())

@router.get("/stream/knowledge-events")
async def stream_knowledge_events(
    current_user: AuthenticatedUser = Depends(get_current_active_user)
):
    """Server-sent events for real-time knowledge system updates"""
    
    async def event_generator():
        registry = get_registry()
        
        while True:
            try:
                # Get knowledge service
                knowledge_service = registry.get_service("farm_knowledge_service")
                
                if knowledge_service:
                    # Get service status
                    status = await knowledge_service.get_service_status()
                    
                    # Generate event data
                    event_data = {
                        "event_type": "knowledge_status_update",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": current_user.user_id,
                        "system_status": status
                    }
                    
                    yield {
                        "event": "knowledge_update",
                        "data": json.dumps(event_data)
                    }
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error in knowledge event stream: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }
                break
    
    return EventSourceResponse(event_generator())

# Service Status Endpoints

@router.get("/status/goals", response_model=Dict[str, Any])
async def get_goal_service_status(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_enhanced_goal_service)
):
    """Get enhanced goal management service status"""
    
    try:
        status = await goal_service.get_service_status()
        
        return {
            "success": True,
            "service_status": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get goal service status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/knowledge", response_model=Dict[str, Any])
async def get_knowledge_service_status(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Get farm knowledge service status"""
    
    try:
        status = await knowledge_service.get_service_status()
        
        return {
            "success": True,
            "service_status": status
        }
        
    except Exception as e:
        logger.error(f"Failed to get knowledge service status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/overview", response_model=Dict[str, Any])
async def get_phase8_overview(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    goal_service = Depends(get_enhanced_goal_service),
    knowledge_service = Depends(get_farm_knowledge_service)
):
    """Get comprehensive Phase 8 system overview"""
    
    try:
        # Get service statuses
        goal_status = await goal_service.get_service_status()
        knowledge_status = await knowledge_service.get_service_status()
        
        # Get user's active goals
        active_goals = await goal_service.get_all_active_goals()
        user_goals = [
            goal for goal in active_goals 
            if goal.created_by == current_user.user_id
        ]
        
        # Get available resources count
        public_resources = await knowledge_service.get_public_resources(limit=1000)
        
        overview = {
            "phase8_status": "operational",
            "services": {
                "enhanced_goals": goal_status,
                "farm_knowledge": knowledge_status
            },
            "user_metrics": {
                "active_goals": len(user_goals),
                "available_resources": len(public_resources),
                "llm_enabled": goal_status.get("llm_enabled", False),
                "knowledge_integration": knowledge_status.get("processing_enabled", False)
            },
            "system_capabilities": [
                "Natural language goal creation",
                "AI-powered goal analysis",
                "Knowledge resource management",
                "Agent knowledge access via MCP",
                "Real-time goal tracking",
                "AI recommendations"
            ],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "success": True,
            "overview": overview
        }
        
    except Exception as e:
        logger.error(f"Failed to get Phase 8 overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))