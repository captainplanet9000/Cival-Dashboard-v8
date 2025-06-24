"""
Enhanced Goal Management Models - Phase 8
LLM-integrated goal creation, tracking, and completion with knowledge system integration
"""

from typing import Dict, List, Optional, Any, Literal, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import uuid
import json

# Enhanced Goal Types with LLM Integration
class EnhancedGoalType(str, Enum):
    """Enhanced goal types with AI-powered categorization"""
    PROFIT_TARGET = "profit_target"
    TRADE_COUNT = "trade_count"
    WIN_RATE = "win_rate"
    PORTFOLIO_VALUE = "portfolio_value"
    RISK_MANAGEMENT = "risk_management"
    STRATEGY_PERFORMANCE = "strategy_performance"
    TIME_BASED = "time_based"
    COLLABORATIVE = "collaborative"
    LEARNING_BASED = "learning_based"
    KNOWLEDGE_ACQUISITION = "knowledge_acquisition"
    SKILL_DEVELOPMENT = "skill_development"
    ADAPTIVE_OPTIMIZATION = "adaptive_optimization"

class GoalComplexity(str, Enum):
    """Goal complexity levels for AI analysis"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"

class LLMProvider(str, Enum):
    """Supported LLM providers for goal processing"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENROUTER = "openrouter"

class GoalCreationMethod(str, Enum):
    """Methods of goal creation"""
    NATURAL_LANGUAGE = "natural_language"
    STRUCTURED_INPUT = "structured_input"
    AI_SUGGESTED = "ai_suggested"
    TEMPLATE_BASED = "template_based"
    PERFORMANCE_DRIVEN = "performance_driven"

# LLM Integration Models

class LLMAnalysisRequest(BaseModel):
    """Request for LLM analysis of natural language goal input"""
    natural_language_input: str
    user_context: Optional[Dict[str, Any]] = None
    agent_context: Optional[List[str]] = None
    trading_context: Optional[Dict[str, Any]] = None
    preferred_provider: LLMProvider = LLMProvider.OPENAI
    analysis_depth: Literal["basic", "detailed", "comprehensive"] = "detailed"

class LLMAnalysisResponse(BaseModel):
    """Response from LLM analysis of goal input"""
    parsed_goal: Dict[str, Any]
    goal_type: EnhancedGoalType
    complexity_assessment: GoalComplexity
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    # Extracted components
    target_value: Optional[Decimal] = None
    timeframe: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    
    # AI insights
    feasibility_assessment: str
    risk_factors: List[str] = Field(default_factory=list)
    recommended_strategies: List[str] = Field(default_factory=list)
    required_knowledge: List[str] = Field(default_factory=list)
    
    # Resource recommendations
    suggested_resources: List[str] = Field(default_factory=list)
    learning_requirements: List[str] = Field(default_factory=list)
    
    # Metadata
    provider_used: LLMProvider
    processing_time_ms: int
    model_version: Optional[str] = None
    tokens_used: Optional[int] = None

class GoalPrediction(BaseModel):
    """AI-powered goal completion predictions"""
    goal_id: str
    prediction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Prediction metrics
    completion_probability: float = Field(ge=0.0, le=1.0)
    estimated_completion_date: Optional[datetime] = None
    confidence_interval: Dict[str, float] = Field(default_factory=dict)
    
    # Factors analysis
    success_factors: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    blocking_factors: List[str] = Field(default_factory=list)
    
    # Recommendations
    acceleration_strategies: List[str] = Field(default_factory=list)
    mitigation_strategies: List[str] = Field(default_factory=list)
    resource_needs: List[str] = Field(default_factory=list)
    
    # Model metadata
    model_version: str
    prediction_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_quality_score: float = Field(ge=0.0, le=1.0)
    
class GoalOptimizationSuggestion(BaseModel):
    """AI-generated optimization suggestions for goals"""
    suggestion_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str
    suggestion_type: Literal["target_adjustment", "strategy_change", "resource_addition", "timeline_modification", "approach_optimization"]
    
    # Suggestion details
    current_approach: str
    suggested_approach: str
    expected_improvement: str
    implementation_effort: Literal["low", "medium", "high"]
    
    # Impact analysis
    probability_improvement: float = Field(ge=0.0, le=1.0)
    estimated_time_savings: Optional[timedelta] = None
    estimated_performance_gain: Optional[float] = None
    
    # Implementation
    implementation_steps: List[str] = Field(default_factory=list)
    required_resources: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ai_confidence: float = Field(ge=0.0, le=1.0)

# Enhanced Goal Models

class EnhancedGoal(BaseModel):
    """Enhanced goal model with LLM integration and knowledge system"""
    goal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_name: str
    goal_type: EnhancedGoalType
    description: str
    
    # Core goal attributes
    target_value: Decimal
    current_value: Decimal = Decimal("0")
    progress_percentage: float = 0.0
    status: Literal["pending", "active", "in_progress", "completed", "failed", "cancelled", "paused"] = "pending"
    priority: int = Field(ge=1, le=5, default=3)
    complexity: GoalComplexity = GoalComplexity.MODERATE
    
    # Creation context
    creation_method: GoalCreationMethod
    natural_language_input: Optional[str] = None
    llm_analysis: Optional[LLMAnalysisResponse] = None
    
    # Timeline
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Assignments
    assigned_agents: List[str] = Field(default_factory=list)
    assigned_farms: List[str] = Field(default_factory=list)
    created_by: str
    
    # Knowledge integration
    knowledge_resources: List[str] = Field(default_factory=list)
    required_competencies: List[str] = Field(default_factory=list)
    learning_prerequisites: List[str] = Field(default_factory=list)
    
    # AI enhancements
    ai_predictions: List[GoalPrediction] = Field(default_factory=list)
    optimization_suggestions: List[GoalOptimizationSuggestion] = Field(default_factory=list)
    auto_adjustments_enabled: bool = True
    
    # Success criteria
    success_criteria: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    completion_validation: Dict[str, Any] = Field(default_factory=dict)
    
    # Collaboration features
    shared_with_users: List[str] = Field(default_factory=list)
    collaboration_type: Optional[Literal["individual", "team", "farm", "global"]] = "individual"
    dependencies: List[str] = Field(default_factory=list)  # Other goal IDs
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None

class GoalMilestone(BaseModel):
    """Milestones within a goal for tracking progress"""
    milestone_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str
    name: str
    description: str
    target_value: Decimal
    target_percentage: float = Field(ge=0.0, le=100.0)
    
    # Status
    status: Literal["pending", "in_progress", "completed", "skipped"] = "pending"
    completed_at: Optional[datetime] = None
    actual_value: Optional[Decimal] = None
    
    # AI features
    auto_detection: bool = True
    completion_criteria: List[str] = Field(default_factory=list)
    
    # Order and dependencies
    sequence_order: int = 1
    depends_on: List[str] = Field(default_factory=list)  # Other milestone IDs
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EnhancedGoalProgress(BaseModel):
    """Enhanced progress tracking with AI insights"""
    progress_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Progress metrics
    current_value: Decimal
    progress_percentage: float
    velocity: float = 0.0  # Progress per day
    acceleration: float = 0.0  # Change in velocity
    
    # Predictions
    estimated_completion: Optional[datetime] = None
    completion_probability: Optional[float] = None
    
    # Context
    milestones_achieved: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    knowledge_applied: List[str] = Field(default_factory=list)
    agents_contributed: List[str] = Field(default_factory=list)
    
    # Performance factors
    market_conditions: Optional[str] = None
    strategy_effectiveness: Optional[float] = None
    resource_utilization: Optional[float] = None
    
    # AI insights
    progress_insights: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    risk_alerts: List[str] = Field(default_factory=list)

class GoalCompletion(BaseModel):
    """Enhanced goal completion with comprehensive analysis"""
    completion_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str
    completion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Completion metrics
    final_value: Decimal
    achievement_percentage: float
    success_rating: float = Field(ge=0.0, le=1.0)
    
    # Performance analysis
    total_profit: Decimal = Decimal("0")
    total_trades: int = 0
    completion_time_days: int
    average_daily_progress: float = 0.0
    
    # Contributors
    contributing_agents: List[str] = Field(default_factory=list)
    contributing_farms: List[str] = Field(default_factory=list)
    knowledge_utilized: List[str] = Field(default_factory=list)
    
    # Success factors analysis
    success_factors: List[str] = Field(default_factory=list)
    challenges_overcome: List[str] = Field(default_factory=list)
    lessons_learned: List[str] = Field(default_factory=list)
    
    # Performance metrics
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    efficiency_score: Optional[float] = None
    innovation_score: Optional[float] = None
    
    # AI analysis
    completion_analysis: Optional[str] = None
    predicted_vs_actual: Dict[str, Any] = Field(default_factory=dict)
    model_accuracy_assessment: Optional[float] = None
    
    # Future recommendations
    future_goal_suggestions: List[str] = Field(default_factory=list)
    improvement_recommendations: List[str] = Field(default_factory=list)

# Request/Response Models

class CreateEnhancedGoalRequest(BaseModel):
    """Request to create an enhanced goal with LLM processing"""
    natural_language_input: Optional[str] = None
    structured_goal: Optional[Dict[str, Any]] = None
    creation_method: GoalCreationMethod = GoalCreationMethod.NATURAL_LANGUAGE
    
    # LLM preferences
    llm_provider: LLMProvider = LLMProvider.OPENAI
    enable_ai_analysis: bool = True
    enable_predictions: bool = True
    enable_optimization: bool = True
    
    # Context
    user_context: Optional[Dict[str, Any]] = None
    trading_context: Optional[Dict[str, Any]] = None
    agent_context: Optional[List[str]] = None
    
    # Assignment preferences
    auto_assign_agents: bool = True
    preferred_agents: Optional[List[str]] = None
    auto_assign_resources: bool = True
    
    # Collaboration
    collaboration_type: Literal["individual", "team", "farm", "global"] = "individual"
    share_with_users: Optional[List[str]] = None

class GoalAnalyticsRequest(BaseModel):
    """Request for goal analytics and insights"""
    goal_ids: Optional[List[str]] = None
    user_id: Optional[str] = None
    date_range: Optional[Dict[str, datetime]] = None
    include_predictions: bool = True
    include_recommendations: bool = True
    analytics_depth: Literal["summary", "detailed", "comprehensive"] = "detailed"

class GoalAnalyticsResponse(BaseModel):
    """Comprehensive goal analytics response"""
    summary_metrics: Dict[str, Any]
    goal_performance: List[Dict[str, Any]]
    trend_analysis: Dict[str, Any]
    success_patterns: List[str]
    improvement_opportunities: List[str]
    ai_insights: List[str]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NaturalLanguageGoalInput(BaseModel):
    """Natural language input for goal creation"""
    input_text: str = Field(min_length=10, max_length=1000)
    context_hints: Optional[List[str]] = None
    preferred_timeframe: Optional[str] = None
    risk_tolerance: Optional[Literal["low", "medium", "high"]] = None
    complexity_preference: Optional[GoalComplexity] = None
    
    @validator('input_text')
    def validate_input_text(cls, v):
        # Basic validation for meaningful goal input
        common_goal_keywords = ['profit', 'trade', 'earn', 'make', 'achieve', 'reach', 'target', 'goal', 'want', 'need']
        if not any(keyword in v.lower() for keyword in common_goal_keywords):
            raise ValueError('Input should describe a trading or performance goal')
        return v

class GoalRecommendationEngine(BaseModel):
    """AI-powered goal recommendation system"""
    user_id: str
    recommendation_type: Literal["performance_based", "knowledge_gap", "trending", "collaborative", "adaptive"]
    
    # Context for recommendations
    current_performance: Optional[Dict[str, Any]] = None
    knowledge_profile: Optional[Dict[str, Any]] = None
    trading_history: Optional[Dict[str, Any]] = None
    
    # Recommendation parameters
    max_recommendations: int = Field(default=5, le=20)
    difficulty_preference: Optional[GoalComplexity] = None
    timeframe_preference: Optional[str] = None

class GoalCollaborationRequest(BaseModel):
    """Request for collaborative goal features"""
    goal_id: str
    collaboration_action: Literal["share", "invite", "join", "leave", "transfer"]
    target_users: Optional[List[str]] = None
    target_agents: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    message: Optional[str] = None

# Export all enhanced models
__all__ = [
    "EnhancedGoalType", "GoalComplexity", "LLMProvider", "GoalCreationMethod",
    "LLMAnalysisRequest", "LLMAnalysisResponse", "GoalPrediction", "GoalOptimizationSuggestion",
    "EnhancedGoal", "GoalMilestone", "EnhancedGoalProgress", "GoalCompletion",
    "CreateEnhancedGoalRequest", "GoalAnalyticsRequest", "GoalAnalyticsResponse",
    "NaturalLanguageGoalInput", "GoalRecommendationEngine", "GoalCollaborationRequest"
]