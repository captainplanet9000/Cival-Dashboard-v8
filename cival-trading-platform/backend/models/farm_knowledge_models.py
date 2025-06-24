"""
Farm Knowledge Models - Phase 8
Comprehensive models for trading resources, knowledge management, and agent access
"""

from typing import Dict, List, Optional, Any, Literal, Union
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import uuid
import json

class TradingResourceType(str, Enum):
    """Types of trading resources in the farm knowledge system"""
    TRADING_BOOKS = "trading_books"
    SOPS = "standard_operating_procedures"
    STRATEGIES = "trading_strategies"
    MARKET_DATA = "market_data"
    RESEARCH = "market_research"
    TRAINING = "agent_training"
    LOGS = "trading_logs"
    ALERTS = "alert_configurations"
    BACKTESTS = "strategy_backtests"
    DOCUMENTATION = "technical_documentation"

class AccessLevel(str, Enum):
    """Access levels for farm resources"""
    PUBLIC = "public"
    RESTRICTED = "restricted"
    AGENT_ONLY = "agent_only"
    ADMIN_ONLY = "admin_only"

class ProcessingStatus(str, Enum):
    """Processing status for uploaded resources"""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    INDEXED = "indexed"
    ERROR = "error"
    FAILED = "failed"

class ContentFormat(str, Enum):
    """Supported content formats"""
    PDF = "pdf"
    EPUB = "epub"
    TXT = "txt"
    MD = "md"
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    DOCX = "docx"
    IMAGE = "image"
    VIDEO = "video"

@dataclass
class ResourceMetadata:
    """Metadata for farm knowledge resources"""
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    trading_context: List[str] = field(default_factory=list)
    difficulty_level: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    estimated_read_time: Optional[int] = None  # minutes
    language: str = "en"

class FarmResource(BaseModel):
    """Comprehensive farm knowledge resource model"""
    resource_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resource_type: TradingResourceType
    content_format: ContentFormat
    title: str
    description: Optional[str] = None
    file_path: str
    file_size: int
    content_type: str
    original_filename: str
    
    # Metadata and categorization
    metadata: ResourceMetadata
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    
    # Access control
    access_level: AccessLevel = AccessLevel.PUBLIC
    restricted_to_agents: List[str] = Field(default_factory=list)
    restricted_to_users: List[str] = Field(default_factory=list)
    
    # Processing and indexing
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    key_concepts: List[str] = Field(default_factory=list)
    vector_embeddings: Optional[Dict[str, Any]] = None
    
    # Usage tracking
    usage_count: int = 0
    last_accessed: Optional[datetime] = None
    popular_with_agents: List[str] = Field(default_factory=list)
    
    # System fields
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_by: Optional[str] = None
    
    # MCP and AI access
    mcp_accessible: bool = True
    ai_searchable: bool = True
    auto_suggest: bool = True
    
    # Content analysis
    sentiment_score: Optional[float] = None
    complexity_score: Optional[float] = None
    relevance_scores: Dict[str, float] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

class ResourceAccessLog(BaseModel):
    """Log of agent/user access to farm resources"""
    access_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    access_type: Literal["read", "download", "search", "reference", "learn"] = "read"
    access_method: Literal["mcp", "api", "ui", "direct"] = "api"
    
    # Context of access
    trading_context: Optional[str] = None  # What trading activity prompted this access
    goal_id: Optional[str] = None  # If accessed in context of a goal
    session_id: Optional[str] = None
    
    # Access details
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_seconds: Optional[int] = None
    pages_viewed: Optional[List[int]] = None
    content_extracted: Optional[str] = None
    
    # Usage metrics
    was_helpful: Optional[bool] = None
    usage_rating: Optional[int] = None  # 1-5 rating
    notes: Optional[str] = None

class ResourceLearningPath(BaseModel):
    """Learning paths created from farm resources"""
    path_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    path_name: str
    description: str
    target_skill_level: Literal["beginner", "intermediate", "advanced"]
    estimated_duration_hours: int
    
    # Path structure
    resources_sequence: List[str]  # Ordered list of resource_ids
    prerequisites: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    
    # Agent assignment
    assigned_agents: List[str] = Field(default_factory=list)
    completion_tracking: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Path metadata
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class AgentKnowledgeProfile(BaseModel):
    """Agent's knowledge profile and learning progress"""
    agent_id: str
    knowledge_areas: Dict[str, float] = Field(default_factory=dict)  # Area -> competency score
    completed_resources: List[str] = Field(default_factory=list)
    in_progress_resources: List[str] = Field(default_factory=list)
    favorite_resources: List[str] = Field(default_factory=list)
    
    # Learning metrics
    total_learning_time_hours: float = 0.0
    resources_completed_count: int = 0
    average_comprehension_score: float = 0.0
    learning_velocity: float = 0.0  # Resources per week
    
    # Preferences
    preferred_content_types: List[ContentFormat] = Field(default_factory=list)
    preferred_difficulty_level: Optional[str] = None
    learning_schedule_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    # Performance correlation
    knowledge_to_performance_correlation: Dict[str, float] = Field(default_factory=dict)
    last_performance_update: Optional[datetime] = None
    
    # System fields
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class KnowledgeRecommendation(BaseModel):
    """AI-powered knowledge recommendations for agents"""
    recommendation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    resource_id: str
    recommendation_type: Literal["skill_gap", "performance_improvement", "goal_related", "trending", "collaborative"]
    
    # Recommendation details
    reason: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    estimated_impact: Optional[str] = None
    
    # Context
    triggered_by: Optional[str] = None  # What triggered this recommendation
    goal_context: Optional[str] = None
    performance_context: Optional[Dict[str, Any]] = None
    
    # Recommendation lifecycle
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    status: Literal["pending", "viewed", "accepted", "rejected", "expired"] = "pending"
    agent_feedback: Optional[str] = None

# Enhanced Goal Models with Knowledge Integration

class GoalKnowledgeRequirement(BaseModel):
    """Knowledge requirements for goal achievement"""
    requirement_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str
    knowledge_area: str
    required_competency_level: float = Field(ge=0.0, le=1.0)
    recommended_resources: List[str] = Field(default_factory=list)
    is_critical: bool = False
    estimated_learning_time_hours: Optional[float] = None

class GoalResourceAssignment(BaseModel):
    """Assignment of knowledge resources to goals"""
    assignment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str
    resource_id: str
    assignment_type: Literal["required", "recommended", "supplementary", "reference"]
    assigned_by: str  # user_id or "system" for AI assignments
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Usage tracking
    agent_completion_status: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    effectiveness_rating: Optional[float] = None

# Request/Response Models for APIs

class CreateResourceRequest(BaseModel):
    """Request model for creating a new farm resource"""
    resource_type: TradingResourceType
    title: str
    description: Optional[str] = None
    file_data: Optional[str] = None  # Base64 encoded file data
    file_url: Optional[str] = None   # URL to download file
    metadata: ResourceMetadata
    tags: List[str] = Field(default_factory=list)
    access_level: AccessLevel = AccessLevel.PUBLIC
    auto_process: bool = True

class ResourceSearchRequest(BaseModel):
    """Request model for searching farm resources"""
    query: str
    resource_types: Optional[List[TradingResourceType]] = None
    access_level: Optional[List[AccessLevel]] = None
    tags: Optional[List[str]] = None
    content_format: Optional[List[ContentFormat]] = None
    agent_id: Optional[str] = None
    limit: int = Field(default=20, le=100)
    offset: int = Field(default=0, ge=0)
    include_content: bool = False

class ResourceSearchResponse(BaseModel):
    """Response model for resource search"""
    total_count: int
    results: List[FarmResource]
    search_metadata: Dict[str, Any]
    recommendations: Optional[List[KnowledgeRecommendation]] = None

class AgentKnowledgeRequest(BaseModel):
    """Request model for agent knowledge access"""
    agent_id: str
    request_type: Literal["search", "recommend", "learn", "reference"]
    query: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    goal_id: Optional[str] = None
    max_results: int = Field(default=10, le=50)

class BulkResourceOperation(BaseModel):
    """Model for bulk operations on resources"""
    operation: Literal["update_tags", "change_access", "bulk_process", "bulk_delete"]
    resource_ids: List[str]
    operation_data: Dict[str, Any]
    performed_by: str

# Analytics and Reporting Models

class ResourceUsageAnalytics(BaseModel):
    """Analytics for resource usage patterns"""
    resource_id: str
    total_accesses: int
    unique_agents: int
    average_session_duration: float
    most_accessed_sections: List[str]
    effectiveness_metrics: Dict[str, float]
    temporal_usage_pattern: Dict[str, int]  # Hour/day patterns
    correlation_with_performance: Optional[float] = None

class KnowledgeSystemMetrics(BaseModel):
    """Overall knowledge system metrics"""
    total_resources: int
    resources_by_type: Dict[TradingResourceType, int]
    total_agent_accesses: int
    average_learning_time_per_agent: float
    most_popular_resources: List[str]
    knowledge_gap_analysis: Dict[str, Any]
    system_effectiveness_score: float
    last_calculated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Export all models for use in other modules
__all__ = [
    "TradingResourceType", "AccessLevel", "ProcessingStatus", "ContentFormat",
    "ResourceMetadata", "FarmResource", "ResourceAccessLog", "ResourceLearningPath",
    "AgentKnowledgeProfile", "KnowledgeRecommendation", "GoalKnowledgeRequirement",
    "GoalResourceAssignment", "CreateResourceRequest", "ResourceSearchRequest",
    "ResourceSearchResponse", "AgentKnowledgeRequest", "BulkResourceOperation",
    "ResourceUsageAnalytics", "KnowledgeSystemMetrics"
]