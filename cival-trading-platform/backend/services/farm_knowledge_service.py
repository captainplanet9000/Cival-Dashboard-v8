"""
Farm Knowledge Service - Phase 8
Comprehensive knowledge management for trading resources, SOPs, and agent learning
"""

import asyncio
import logging
import json
import uuid
import hashlib
import mimetypes
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
import aiofiles
import openai
from sqlalchemy import text

# Import models
from ..models.farm_knowledge_models import (
    FarmResource, ResourceAccessLog, ResourceLearningPath, AgentKnowledgeProfile,
    KnowledgeRecommendation, TradingResourceType, AccessLevel, ProcessingStatus,
    ContentFormat, ResourceSearchRequest, ResourceSearchResponse, 
    AgentKnowledgeRequest, CreateResourceRequest, ResourceUsageAnalytics,
    KnowledgeSystemMetrics, ResourceMetadata
)
from ..core.service_registry import get_registry
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class FarmKnowledgeService:
    """
    Comprehensive farm knowledge service for trading resources and agent learning
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # Knowledge management
        self.resources: Dict[str, FarmResource] = {}
        self.access_logs: List[ResourceAccessLog] = []
        self.agent_profiles: Dict[str, AgentKnowledgeProfile] = {}
        self.learning_paths: Dict[str, ResourceLearningPath] = {}
        
        # AI and processing
        self.openai_client = None
        self.processing_enabled = True
        self.ai_recommendations_enabled = True
        
        # File storage configuration
        self.storage_base_path = Path("data/farm_knowledge")
        self.storage_base_path.mkdir(parents=True, exist_ok=True)
        
        # Background tasks
        self.processing_tasks = []
        
        logger.info("FarmKnowledgeService initialized")
    
    async def initialize(self):
        """Initialize the farm knowledge service"""
        try:
            # Initialize AI clients
            await self._initialize_ai_clients()
            
            # Load existing resources from database
            await self._load_resources_from_database()
            
            # Load agent knowledge profiles
            await self._load_agent_profiles()
            
            # Start background processing tasks
            await self._start_background_tasks()
            
            logger.info("FarmKnowledgeService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize FarmKnowledgeService: {e}")
            raise
    
    async def _initialize_ai_clients(self):
        """Initialize AI clients for content processing"""
        try:
            # Initialize OpenAI for content analysis
            openai_api_key = self.registry.get_config("OPENAI_API_KEY")
            if openai_api_key:
                self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
                logger.info("OpenAI client initialized for content processing")
            else:
                logger.warning("OpenAI API key not found - AI processing disabled")
                self.processing_enabled = False
                
        except Exception as e:
            logger.error(f"Failed to initialize AI clients: {e}")
            self.processing_enabled = False
    
    async def create_resource(self, request: CreateResourceRequest, created_by: str) -> FarmResource:
        """Create a new farm knowledge resource"""
        
        try:
            # Generate resource ID
            resource_id = str(uuid.uuid4())
            
            # Determine content format from file data or metadata
            content_format = self._determine_content_format(request)
            
            # Store file if provided
            file_path = ""
            file_size = 0
            
            if request.file_data:
                file_path, file_size = await self._store_file_data(
                    resource_id, request.file_data, content_format
                )
            elif request.file_url:
                file_path, file_size = await self._download_and_store_file(
                    resource_id, request.file_url, content_format
                )
            
            # Create resource
            resource = FarmResource(
                resource_id=resource_id,
                resource_type=request.resource_type,
                content_format=content_format,
                title=request.title,
                description=request.description,
                file_path=file_path,
                file_size=file_size,
                content_type=self._get_content_type(content_format),
                original_filename=f"{request.title}.{content_format.value}",
                metadata=request.metadata,
                tags=request.tags,
                access_level=request.access_level,
                created_by=created_by,
                processing_status=ProcessingStatus.PENDING if request.auto_process else ProcessingStatus.PROCESSED
            )
            
            # Save to database
            await self._save_resource_to_database(resource)
            
            # Add to local cache
            self.resources[resource_id] = resource
            
            # Queue for processing if auto-processing is enabled
            if request.auto_process and self.processing_enabled:
                asyncio.create_task(self._process_resource(resource_id))
            
            # Cache in Redis
            if self.redis:
                await self.redis.setex(
                    f"farm_resource:{resource_id}",
                    3600,
                    json.dumps(resource.model_dump(), default=str)
                )
            
            logger.info(f"Created farm resource: {resource.title} ({resource_id})")
            return resource
            
        except Exception as e:
            logger.error(f"Failed to create resource: {e}")
            raise
    
    async def search_resources(self, request: ResourceSearchRequest, agent_id: str = None) -> ResourceSearchResponse:
        """Search farm knowledge resources"""
        
        try:
            # Build search criteria
            search_criteria = {
                "query": request.query,
                "resource_types": request.resource_types,
                "access_level": request.access_level,
                "tags": request.tags,
                "content_format": request.content_format,
                "limit": request.limit,
                "offset": request.offset
            }
            
            # Perform database search
            search_results = await self._search_database(search_criteria)
            
            # Filter results based on access permissions
            if agent_id:
                search_results = await self._filter_by_agent_access(search_results, agent_id)
            
            # Log search access
            if agent_id:
                await self._log_search_access(agent_id, request.query)
            
            # Get AI recommendations if enabled
            recommendations = []
            if self.ai_recommendations_enabled and agent_id:
                recommendations = await self._get_search_recommendations(agent_id, request.query)
            
            # Create response
            response = ResourceSearchResponse(
                total_count=len(search_results),
                results=search_results[:request.limit],
                search_metadata={
                    "query": request.query,
                    "search_time": datetime.now(timezone.utc).isoformat(),
                    "agent_id": agent_id
                },
                recommendations=recommendations
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to search resources: {e}")
            raise
    
    async def get_resource_by_id(self, resource_id: str) -> Optional[FarmResource]:
        """Get a specific resource by ID"""
        
        try:
            # Check local cache first
            if resource_id in self.resources:
                return self.resources[resource_id]
            
            # Check Redis cache
            if self.redis:
                cached_data = await self.redis.get(f"farm_resource:{resource_id}")
                if cached_data:
                    resource_data = json.loads(cached_data)
                    resource = FarmResource(**resource_data)
                    self.resources[resource_id] = resource
                    return resource
            
            # Load from database
            resource = await self._load_resource_from_database(resource_id)
            if resource:
                self.resources[resource_id] = resource
                
                # Cache in Redis
                if self.redis:
                    await self.redis.setex(
                        f"farm_resource:{resource_id}",
                        3600,
                        json.dumps(resource.model_dump(), default=str)
                    )
            
            return resource
            
        except Exception as e:
            logger.error(f"Failed to get resource {resource_id}: {e}")
            return None
    
    async def get_resource_content(self, resource_id: str, agent_id: str) -> Optional[str]:
        """Get the content of a specific resource"""
        
        try:
            # Get resource
            resource = await self.get_resource_by_id(resource_id)
            if not resource:
                return None
            
            # Check access permissions
            if not await self.check_agent_access(agent_id, resource_id):
                logger.warning(f"Agent {agent_id} denied access to resource {resource_id}")
                return None
            
            # Log access
            await self.log_resource_access(ResourceAccessLog(
                resource_id=resource_id,
                agent_id=agent_id,
                access_type="read",
                access_method="direct",
                accessed_at=datetime.now(timezone.utc)
            ))
            
            # Return extracted text if available
            if resource.extracted_text:
                return resource.extracted_text
            
            # Try to extract content from file
            if resource.file_path:
                content = await self._extract_content_from_file(resource.file_path, resource.content_format)
                if content:
                    # Update resource with extracted content
                    resource.extracted_text = content
                    await self._update_resource_in_database(resource)
                    return content
            
            # Fallback to summary or description
            return resource.summary or resource.description or "Content not available"
            
        except Exception as e:
            logger.error(f"Failed to get resource content: {e}")
            return None
    
    async def check_agent_access(self, agent_id: str, resource_id: str) -> bool:
        """Check if an agent has access to a specific resource"""
        
        try:
            resource = await self.get_resource_by_id(resource_id)
            if not resource:
                return False
            
            # Public resources are accessible to all
            if resource.access_level == AccessLevel.PUBLIC:
                return True
            
            # Check agent-specific restrictions
            if resource.access_level == AccessLevel.AGENT_ONLY:
                return agent_id in resource.restricted_to_agents
            
            # Check restricted access
            if resource.access_level == AccessLevel.RESTRICTED:
                return agent_id in resource.restricted_to_agents
            
            # Admin-only resources require special permissions
            if resource.access_level == AccessLevel.ADMIN_ONLY:
                # Check if agent has admin permissions
                agent_service = self.registry.get_service("agent_management_service")
                if agent_service:
                    agent_info = await agent_service.get_agent(agent_id)
                    return getattr(agent_info, 'is_admin', False)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check agent access: {e}")
            return False
    
    async def log_resource_access(self, access_log: ResourceAccessLog):
        """Log resource access for analytics and tracking"""
        
        try:
            # Add to local logs
            self.access_logs.append(access_log)
            
            # Save to database
            if self.supabase:
                log_dict = access_log.model_dump()
                log_dict["accessed_at"] = access_log.accessed_at.isoformat()
                
                self.supabase.table('resource_access_log').insert(log_dict).execute()
            
            # Update resource usage count
            resource = self.resources.get(access_log.resource_id)
            if resource:
                resource.usage_count += 1
                resource.last_accessed = access_log.accessed_at
                
                # Add agent to popular_with_agents if not already there
                if access_log.agent_id and access_log.agent_id not in resource.popular_with_agents:
                    resource.popular_with_agents.append(access_log.agent_id)
                
                # Update in database
                await self._update_resource_usage_stats(resource)
            
        except Exception as e:
            logger.error(f"Failed to log resource access: {e}")
    
    async def get_contextual_sops(self, search_criteria: Dict[str, Any]) -> List[FarmResource]:
        """Get contextual standard operating procedures"""
        
        try:
            # Build specific search for SOPs
            sop_search = ResourceSearchRequest(
                query=f"{search_criteria.get('strategy_context', '')} {search_criteria.get('situation_context', '')}",
                resource_types=[TradingResourceType.SOPS],
                limit=10
            )
            
            search_results = await self.search_resources(sop_search, search_criteria.get("agent_id"))
            
            # Filter and rank by relevance
            relevant_sops = []
            for resource in search_results.results:
                # Calculate relevance score based on tags and content
                relevance_score = self._calculate_sop_relevance(resource, search_criteria)
                if relevance_score > 0.3:  # Minimum relevance threshold
                    relevant_sops.append((resource, relevance_score))
            
            # Sort by relevance score
            relevant_sops.sort(key=lambda x: x[1], reverse=True)
            
            return [sop[0] for sop in relevant_sops[:5]]  # Return top 5
            
        except Exception as e:
            logger.error(f"Failed to get contextual SOPs: {e}")
            return []
    
    async def get_market_research(self, search_criteria: Dict[str, Any]) -> List[FarmResource]:
        """Get relevant market research documents"""
        
        try:
            # Build search query for market research
            query_parts = []
            
            if search_criteria.get("symbol"):
                query_parts.append(search_criteria["symbol"])
            
            if search_criteria.get("timeframe"):
                query_parts.append(search_criteria["timeframe"])
            
            if search_criteria.get("research_type"):
                query_parts.append(search_criteria["research_type"])
            
            query = " ".join(query_parts)
            
            research_search = ResourceSearchRequest(
                query=query,
                resource_types=[TradingResourceType.RESEARCH],
                limit=10
            )
            
            search_results = await self.search_resources(research_search, search_criteria.get("agent_id"))
            
            # Filter by recency if specified
            recency = search_criteria.get("recency", "latest")
            if recency == "week":
                cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=1)
            elif recency == "month":
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            else:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)
            
            recent_research = [
                resource for resource in search_results.results
                if resource.created_at >= cutoff_date
            ]
            
            return recent_research[:5]  # Return top 5
            
        except Exception as e:
            logger.error(f"Failed to get market research: {e}")
            return []
    
    async def get_learning_resources(self, learning_request: Dict[str, Any]) -> List[FarmResource]:
        """Get learning resources for agent skill development"""
        
        try:
            agent_id = learning_request["agent_id"]
            skill_area = learning_request["skill_area"]
            current_level = learning_request.get("current_level", "intermediate")
            
            # Get agent's knowledge profile
            agent_profile = await self._get_or_create_agent_profile(agent_id)
            
            # Search for relevant learning resources
            learning_search = ResourceSearchRequest(
                query=skill_area,
                resource_types=[
                    TradingResourceType.TRADING_BOOKS,
                    TradingResourceType.TRAINING,
                    TradingResourceType.DOCUMENTATION
                ],
                limit=20
            )
            
            search_results = await self.search_resources(learning_search, agent_id)
            
            # Filter by difficulty level and agent's current knowledge
            suitable_resources = []
            
            for resource in search_results.results:
                # Check if resource matches agent's level
                resource_level = getattr(resource.metadata, 'difficulty_level', 'intermediate')
                
                if self._is_suitable_learning_level(current_level, resource_level):
                    # Check if agent hasn't already completed this resource
                    if resource.resource_id not in agent_profile.completed_resources:
                        suitable_resources.append(resource)
            
            # Sort by estimated learning value
            suitable_resources.sort(key=lambda r: self._calculate_learning_value(r, agent_profile), reverse=True)
            
            return suitable_resources[:10]
            
        except Exception as e:
            logger.error(f"Failed to get learning resources: {e}")
            return []
    
    async def get_ai_recommendations(self, recommendation_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get AI-powered resource recommendations"""
        
        try:
            if not self.ai_recommendations_enabled or not self.openai_client:
                return []
            
            agent_id = recommendation_request["agent_id"]
            recommendation_type = recommendation_request.get("recommendation_type", "performance_improvement")
            
            # Get agent's knowledge profile and recent performance
            agent_profile = await self._get_or_create_agent_profile(agent_id)
            performance_context = recommendation_request.get("performance_context", {})
            
            # Generate AI recommendations based on type
            if recommendation_type == "skill_gap":
                recommendations = await self._generate_skill_gap_recommendations(agent_profile, performance_context)
            elif recommendation_type == "performance_improvement":
                recommendations = await self._generate_performance_recommendations(agent_profile, performance_context)
            elif recommendation_type == "goal_related":
                goal_context = recommendation_request.get("current_goal")
                recommendations = await self._generate_goal_recommendations(agent_profile, goal_context)
            else:
                recommendations = await self._generate_general_recommendations(agent_profile)
            
            return recommendations[:recommendation_request.get("max_recommendations", 5)]
            
        except Exception as e:
            logger.error(f"Failed to get AI recommendations: {e}")
            return []
    
    async def get_public_resources(self, limit: int = 50) -> List[FarmResource]:
        """Get public resources for MCP server listing"""
        
        try:
            public_resources = [
                resource for resource in self.resources.values()
                if resource.access_level == AccessLevel.PUBLIC
            ]
            
            # Sort by usage count and recency
            public_resources.sort(
                key=lambda r: (r.usage_count, r.created_at),
                reverse=True
            )
            
            return public_resources[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get public resources: {e}")
            return []
    
    async def notify_goal_created(self, goal_id: str, knowledge_resources: List[str]):
        """Handle notification when a goal is created with knowledge resources"""
        
        try:
            # Update resource usage for goal-related resources
            for resource_id in knowledge_resources:
                resource = self.resources.get(resource_id)
                if resource:
                    # Update metadata to track goal associations
                    if "goal_associations" not in resource.metadata.__dict__:
                        resource.metadata.__dict__["goal_associations"] = []
                    
                    resource.metadata.__dict__["goal_associations"].append(goal_id)
                    
                    # Update in database
                    await self._update_resource_in_database(resource)
            
            logger.info(f"Updated resource associations for goal {goal_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle goal creation notification: {e}")
    
    # Private helper methods
    
    def _determine_content_format(self, request: CreateResourceRequest) -> ContentFormat:
        """Determine content format from request"""
        
        # Check if explicitly provided in metadata
        if hasattr(request.metadata, 'content_format'):
            return ContentFormat(request.metadata.content_format)
        
        # Infer from title or filename
        title_lower = request.title.lower()
        
        if any(ext in title_lower for ext in ['.pdf']):
            return ContentFormat.PDF
        elif any(ext in title_lower for ext in ['.txt', '.md']):
            return ContentFormat.TXT
        elif any(ext in title_lower for ext in ['.csv']):
            return ContentFormat.CSV
        elif any(ext in title_lower for ext in ['.json']):
            return ContentFormat.JSON
        elif any(ext in title_lower for ext in ['.xlsx', '.xls']):
            return ContentFormat.XLSX
        elif any(ext in title_lower for ext in ['.docx', '.doc']):
            return ContentFormat.DOCX
        else:
            # Default based on resource type
            if request.resource_type == TradingResourceType.TRADING_BOOKS:
                return ContentFormat.PDF
            elif request.resource_type == TradingResourceType.SOPS:
                return ContentFormat.MD
            else:
                return ContentFormat.TXT
    
    def _get_content_type(self, content_format: ContentFormat) -> str:
        """Get MIME content type from format"""
        
        content_type_map = {
            ContentFormat.PDF: "application/pdf",
            ContentFormat.EPUB: "application/epub+zip",
            ContentFormat.TXT: "text/plain",
            ContentFormat.MD: "text/markdown",
            ContentFormat.CSV: "text/csv",
            ContentFormat.JSON: "application/json",
            ContentFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ContentFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        
        return content_type_map.get(content_format, "application/octet-stream")
    
    async def _store_file_data(self, resource_id: str, file_data: str, content_format: ContentFormat) -> tuple[str, int]:
        """Store file data and return path and size"""
        
        import base64
        
        # Decode base64 file data
        file_bytes = base64.b64decode(file_data)
        
        # Create storage path
        file_path = self.storage_base_path / f"{resource_id}.{content_format.value}"
        
        # Write file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_bytes)
        
        return str(file_path), len(file_bytes)
    
    async def _download_and_store_file(self, resource_id: str, file_url: str, content_format: ContentFormat) -> tuple[str, int]:
        """Download file from URL and store locally"""
        
        import aiohttp
        
        # Create storage path
        file_path = self.storage_base_path / f"{resource_id}.{content_format.value}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    file_bytes = await response.read()
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(file_bytes)
                    
                    return str(file_path), len(file_bytes)
                else:
                    raise ValueError(f"Failed to download file from {file_url}: HTTP {response.status}")
    
    async def _extract_content_from_file(self, file_path: str, content_format: ContentFormat) -> Optional[str]:
        """Extract text content from file"""
        
        try:
            if content_format in [ContentFormat.TXT, ContentFormat.MD]:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    return await f.read()
            
            elif content_format == ContentFormat.JSON:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    data = json.loads(await f.read())
                    return json.dumps(data, indent=2)
            
            elif content_format == ContentFormat.CSV:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    return await f.read()
            
            elif content_format == ContentFormat.PDF:
                # PDF extraction would require PyPDF2 or similar
                # For now, return placeholder
                return "PDF content extraction not implemented yet"
            
            else:
                return "Content extraction not supported for this format"
                
        except Exception as e:
            logger.error(f"Failed to extract content from {file_path}: {e}")
            return None
    
    def _calculate_sop_relevance(self, resource: FarmResource, search_criteria: Dict) -> float:
        """Calculate relevance score for SOP based on search criteria"""
        
        score = 0.0
        
        # Check tags for strategy and situation matches
        strategy_context = search_criteria.get("strategy_context", "").lower()
        situation_context = search_criteria.get("situation_context", "").lower()
        
        if strategy_context:
            for tag in resource.tags:
                if strategy_context in tag.lower():
                    score += 0.4
        
        if situation_context:
            for tag in resource.tags:
                if situation_context in tag.lower():
                    score += 0.3
        
        # Check title and description
        title_desc = f"{resource.title} {resource.description or ''}".lower()
        
        if strategy_context and strategy_context in title_desc:
            score += 0.2
        
        if situation_context and situation_context in title_desc:
            score += 0.1
        
        return min(score, 1.0)
    
    def _is_suitable_learning_level(self, agent_level: str, resource_level: str) -> bool:
        """Check if resource difficulty is suitable for agent level"""
        
        level_hierarchy = {
            "beginner": 1,
            "intermediate": 2,
            "advanced": 3
        }
        
        agent_numeric = level_hierarchy.get(agent_level, 2)
        resource_numeric = level_hierarchy.get(resource_level, 2)
        
        # Allow resources at same level or one level above
        return resource_numeric <= agent_numeric + 1
    
    def _calculate_learning_value(self, resource: FarmResource, agent_profile: AgentKnowledgeProfile) -> float:
        """Calculate learning value of resource for specific agent"""
        
        value = 0.5  # Base value
        
        # Higher value for resources in areas where agent has lower competency
        for area, competency in agent_profile.knowledge_areas.items():
            if area in resource.tags or area in resource.title.lower():
                # Lower competency = higher learning value
                value += (1.0 - competency) * 0.3
        
        # Higher value for resources that aren't too basic or too advanced
        resource_level = getattr(resource.metadata, 'difficulty_level', 'intermediate')
        if resource_level == 'intermediate':
            value += 0.2
        
        # Higher value for highly rated resources
        if resource.usage_count > 10:
            value += 0.1
        
        return min(value, 1.0)
    
    async def _generate_skill_gap_recommendations(self, agent_profile: AgentKnowledgeProfile, performance_context: Dict) -> List[Dict]:
        """Generate recommendations based on skill gaps"""
        
        # Identify skill areas with low competency
        low_competency_areas = [
            area for area, competency in agent_profile.knowledge_areas.items()
            if competency < 0.6
        ]
        
        recommendations = []
        
        for area in low_competency_areas[:3]:  # Top 3 skill gaps
            # Find resources for this skill area
            search_request = ResourceSearchRequest(
                query=area,
                resource_types=[TradingResourceType.TRAINING, TradingResourceType.TRADING_BOOKS],
                limit=5
            )
            
            search_results = await self.search_resources(search_request)
            
            for resource in search_results.results[:2]:  # Top 2 per area
                recommendations.append({
                    "resource": resource,
                    "reason": f"Improve competency in {area}",
                    "confidence": 0.8,
                    "estimated_impact": f"Could improve {area} skills by 20-30%"
                })
        
        return recommendations
    
    async def _generate_performance_recommendations(self, agent_profile: AgentKnowledgeProfile, performance_context: Dict) -> List[Dict]:
        """Generate recommendations based on performance context"""
        
        recommendations = []
        
        # Analyze performance issues
        if performance_context.get("recent_losses", 0) > 3:
            # Recommend risk management resources
            risk_search = ResourceSearchRequest(
                query="risk management",
                resource_types=[TradingResourceType.SOPS, TradingResourceType.TRAINING],
                limit=3
            )
            
            risk_results = await self.search_resources(risk_search)
            
            for resource in risk_results.results:
                recommendations.append({
                    "resource": resource,
                    "reason": "Recent losses indicate need for better risk management",
                    "confidence": 0.9,
                    "estimated_impact": "Could reduce future losses by 15-25%"
                })
        
        return recommendations
    
    async def _generate_goal_recommendations(self, agent_profile: AgentKnowledgeProfile, goal_context: str) -> List[Dict]:
        """Generate recommendations based on current goal"""
        
        if not goal_context:
            return []
        
        # Search for resources related to the goal
        goal_search = ResourceSearchRequest(
            query=goal_context,
            limit=5
        )
        
        goal_results = await self.search_resources(goal_search)
        
        recommendations = []
        for resource in goal_results.results:
            recommendations.append({
                "resource": resource,
                "reason": f"Relevant to current goal: {goal_context}",
                "confidence": 0.7,
                "estimated_impact": "Direct support for goal achievement"
            })
        
        return recommendations
    
    async def _generate_general_recommendations(self, agent_profile: AgentKnowledgeProfile) -> List[Dict]:
        """Generate general recommendations for continuous learning"""
        
        # Get trending resources
        trending_resources = sorted(
            self.resources.values(),
            key=lambda r: r.usage_count,
            reverse=True
        )[:5]
        
        recommendations = []
        for resource in trending_resources:
            if resource.resource_id not in agent_profile.completed_resources:
                recommendations.append({
                    "resource": resource,
                    "reason": "Popular resource among other agents",
                    "confidence": 0.6,
                    "estimated_impact": "General knowledge improvement"
                })
        
        return recommendations
    
    async def _get_or_create_agent_profile(self, agent_id: str) -> AgentKnowledgeProfile:
        """Get or create agent knowledge profile"""
        
        if agent_id in self.agent_profiles:
            return self.agent_profiles[agent_id]
        
        # Try to load from database
        profile = await self._load_agent_profile_from_database(agent_id)
        
        if not profile:
            # Create new profile
            profile = AgentKnowledgeProfile(agent_id=agent_id)
            await self._save_agent_profile_to_database(profile)
        
        self.agent_profiles[agent_id] = profile
        return profile
    
    # Database operations (simplified - would use actual Supabase operations)
    
    async def _save_resource_to_database(self, resource: FarmResource):
        """Save resource to database"""
        # Implementation would use Supabase client
        pass
    
    async def _load_resource_from_database(self, resource_id: str) -> Optional[FarmResource]:
        """Load resource from database"""
        # Implementation would use Supabase client
        return None
    
    async def _search_database(self, search_criteria: Dict) -> List[FarmResource]:
        """Search database for resources"""
        # Implementation would use Supabase full-text search
        return list(self.resources.values())[:search_criteria.get("limit", 10)]
    
    async def _load_resources_from_database(self):
        """Load all resources from database"""
        # Implementation would use Supabase client
        pass
    
    async def _load_agent_profiles(self):
        """Load agent profiles from database"""
        # Implementation would use Supabase client
        pass
    
    async def _update_resource_in_database(self, resource: FarmResource):
        """Update resource in database"""
        # Implementation would use Supabase client
        pass
    
    async def _save_agent_profile_to_database(self, profile: AgentKnowledgeProfile):
        """Save agent profile to database"""
        # Implementation would use Supabase client
        pass
    
    async def _load_agent_profile_from_database(self, agent_id: str) -> Optional[AgentKnowledgeProfile]:
        """Load agent profile from database"""
        # Implementation would use Supabase client
        return None
    
    async def _update_resource_usage_stats(self, resource: FarmResource):
        """Update resource usage statistics in database"""
        # Implementation would use Supabase client
        pass
    
    async def _filter_by_agent_access(self, resources: List[FarmResource], agent_id: str) -> List[FarmResource]:
        """Filter resources based on agent access permissions"""
        
        accessible_resources = []
        
        for resource in resources:
            if await self.check_agent_access(agent_id, resource.resource_id):
                accessible_resources.append(resource)
        
        return accessible_resources
    
    async def _log_search_access(self, agent_id: str, query: str):
        """Log search access for analytics"""
        
        access_log = ResourceAccessLog(
            resource_id="search",
            agent_id=agent_id,
            access_type="search",
            access_method="api",
            trading_context=f"Search query: {query}",
            accessed_at=datetime.now(timezone.utc)
        )
        
        await self.log_resource_access(access_log)
    
    async def _get_search_recommendations(self, agent_id: str, query: str) -> List[KnowledgeRecommendation]:
        """Get AI recommendations based on search query"""
        
        # This would use AI to suggest related resources
        return []
    
    async def _start_background_tasks(self):
        """Start background processing tasks"""
        
        # Resource processing task
        processing_task = asyncio.create_task(self._resource_processing_loop())
        self.processing_tasks.append(processing_task)
        
        # Analytics update task
        analytics_task = asyncio.create_task(self._analytics_update_loop())
        self.processing_tasks.append(analytics_task)
    
    async def _resource_processing_loop(self):
        """Background resource processing loop"""
        
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Process pending resources
                pending_resources = [
                    r for r in self.resources.values()
                    if r.processing_status == ProcessingStatus.PENDING
                ]
                
                for resource in pending_resources:
                    await self._process_resource(resource.resource_id)
                
            except Exception as e:
                logger.error(f"Error in resource processing loop: {e}")
                await asyncio.sleep(60)
    
    async def _analytics_update_loop(self):
        """Background analytics update loop"""
        
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                
                # Update usage analytics
                await self._update_usage_analytics()
                
            except Exception as e:
                logger.error(f"Error in analytics update loop: {e}")
                await asyncio.sleep(1800)
    
    async def _process_resource(self, resource_id: str):
        """Process a resource for content extraction and indexing"""
        
        try:
            resource = self.resources.get(resource_id)
            if not resource:
                return
            
            resource.processing_status = ProcessingStatus.PROCESSING
            
            # Extract content if not already done
            if not resource.extracted_text and resource.file_path:
                content = await self._extract_content_from_file(resource.file_path, resource.content_format)
                if content:
                    resource.extracted_text = content
            
            # Generate summary using AI if available
            if resource.extracted_text and self.processing_enabled and not resource.summary:
                summary = await self._generate_content_summary(resource.extracted_text)
                if summary:
                    resource.summary = summary
            
            # Extract key concepts
            if resource.extracted_text and not resource.key_concepts:
                key_concepts = await self._extract_key_concepts(resource.extracted_text)
                resource.key_concepts = key_concepts
            
            resource.processing_status = ProcessingStatus.PROCESSED
            
            # Update in database
            await self._update_resource_in_database(resource)
            
            logger.info(f"Processed resource: {resource.title}")
            
        except Exception as e:
            logger.error(f"Failed to process resource {resource_id}: {e}")
            if resource_id in self.resources:
                self.resources[resource_id].processing_status = ProcessingStatus.ERROR
    
    async def _generate_content_summary(self, content: str) -> Optional[str]:
        """Generate AI summary of content"""
        
        if not self.openai_client or len(content) < 100:
            return None
        
        try:
            # Truncate content if too long
            max_content_length = 3000
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a trading knowledge expert. Summarize the following trading-related content in 2-3 sentences, focusing on key insights and practical applications."
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this content:\n\n{content}"
                    }
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate content summary: {e}")
            return None
    
    async def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts from content"""
        
        if not self.openai_client or len(content) < 100:
            return []
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract 5-10 key trading concepts, terms, or strategies from the following content. Return as a JSON array of strings."
                    },
                    {
                        "role": "user",
                        "content": f"Extract key concepts from:\n\n{content[:2000]}"
                    }
                ],
                max_tokens=150,
                temperature=0.2
            )
            
            concepts_text = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                concepts = json.loads(concepts_text)
                if isinstance(concepts, list):
                    return concepts[:10]  # Limit to 10 concepts
            except json.JSONDecodeError:
                # Fallback: split by lines or commas
                concepts = [c.strip() for c in concepts_text.replace('\n', ',').split(',')]
                return [c for c in concepts if c][:10]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to extract key concepts: {e}")
            return []
    
    async def _update_usage_analytics(self):
        """Update resource usage analytics"""
        
        try:
            # Calculate analytics for each resource
            for resource in self.resources.values():
                # Get recent access logs for this resource
                recent_accesses = [
                    log for log in self.access_logs
                    if log.resource_id == resource.resource_id
                    and log.accessed_at >= datetime.now(timezone.utc) - timedelta(days=30)
                ]
                
                # Update usage metrics
                if recent_accesses:
                    unique_agents = len(set(log.agent_id for log in recent_accesses if log.agent_id))
                    avg_duration = sum(log.duration_seconds or 0 for log in recent_accesses) / len(recent_accesses)
                    
                    # Store analytics (would update database)
                    analytics = ResourceUsageAnalytics(
                        resource_id=resource.resource_id,
                        total_accesses=len(recent_accesses),
                        unique_agents=unique_agents,
                        average_session_duration=avg_duration,
                        most_accessed_sections=[],
                        effectiveness_metrics={},
                        temporal_usage_pattern={},
                        correlation_with_performance=None
                    )
            
            logger.info("Updated resource usage analytics")
            
        except Exception as e:
            logger.error(f"Failed to update usage analytics: {e}")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        
        return {
            "service": "farm_knowledge_service",
            "status": "running",
            "processing_enabled": self.processing_enabled,
            "ai_recommendations_enabled": self.ai_recommendations_enabled,
            "total_resources": len(self.resources),
            "processing_tasks_running": len([task for task in self.processing_tasks if not task.done()]),
            "agent_profiles": len(self.agent_profiles),
            "recent_accesses": len([log for log in self.access_logs if log.accessed_at >= datetime.now(timezone.utc) - timedelta(hours=24)]),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_farm_knowledge_service():
    """Factory function to create FarmKnowledgeService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = FarmKnowledgeService(redis_client, supabase_client)
    return service