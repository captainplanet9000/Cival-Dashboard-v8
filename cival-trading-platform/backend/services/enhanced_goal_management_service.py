"""
Enhanced Goal Management Service - Phase 8
LLM-integrated goal creation, tracking, and completion with knowledge system integration
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import openai
import anthropic
from dataclasses import asdict

# Import models
from ..models.enhanced_goal_models import (
    EnhancedGoal, EnhancedGoalType, GoalComplexity, LLMProvider,
    GoalCreationMethod, LLMAnalysisRequest, LLMAnalysisResponse,
    GoalPrediction, GoalOptimizationSuggestion, EnhancedGoalProgress,
    GoalCompletion, CreateEnhancedGoalRequest, NaturalLanguageGoalInput,
    GoalMilestone, GoalAnalyticsRequest, GoalAnalyticsResponse
)
from ..models.farm_knowledge_models import (
    TradingResourceType, FarmResource, ResourceSearchRequest,
    KnowledgeRecommendation, GoalKnowledgeRequirement
)
from ..core.service_registry import get_registry
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class EnhancedGoalManagementService:
    """
    Enhanced goal management service with LLM integration and knowledge system
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # LLM clients
        self.openai_client = None
        self.anthropic_client = None
        
        # Active goals and tracking
        self.active_goals: Dict[str, EnhancedGoal] = {}
        self.goal_progress: Dict[str, List[EnhancedGoalProgress]] = {}
        self.completed_goals: Dict[str, GoalCompletion] = {}
        self.goal_predictions: Dict[str, List[GoalPrediction]] = {}
        
        # LLM and knowledge integration
        self.llm_enabled = True
        self.knowledge_integration_enabled = True
        
        # Background tasks
        self.monitoring_tasks = []
        
        logger.info("EnhancedGoalManagementService initialized with LLM and knowledge integration")
    
    async def initialize(self):
        """Initialize the enhanced goal management service"""
        try:
            # Initialize LLM clients
            await self._initialize_llm_clients()
            
            # Load active goals from database
            await self._load_active_goals()
            
            # Start background monitoring tasks
            await self._start_background_tasks()
            
            logger.info("EnhancedGoalManagementService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize EnhancedGoalManagementService: {e}")
            raise
    
    async def _initialize_llm_clients(self):
        """Initialize LLM clients for goal processing"""
        try:
            # Initialize OpenAI client
            openai_api_key = self.registry.get_config("OPENAI_API_KEY")
            if openai_api_key:
                self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
                logger.info("OpenAI client initialized")
            
            # Initialize Anthropic client
            anthropic_api_key = self.registry.get_config("ANTHROPIC_API_KEY")
            if anthropic_api_key:
                self.anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
                logger.info("Anthropic client initialized")
            
            if not self.openai_client and not self.anthropic_client:
                logger.warning("No LLM clients available - natural language processing disabled")
                self.llm_enabled = False
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {e}")
            self.llm_enabled = False
    
    async def create_goal_from_natural_language(self, request: CreateEnhancedGoalRequest) -> EnhancedGoal:
        """Create a goal from natural language input using LLM analysis"""
        
        try:
            if not request.natural_language_input:
                raise ValueError("Natural language input is required")
            
            # Analyze natural language input with LLM
            llm_analysis = None
            if self.llm_enabled and request.enable_ai_analysis:
                analysis_request = LLMAnalysisRequest(
                    natural_language_input=request.natural_language_input,
                    user_context=request.user_context,
                    agent_context=request.agent_context,
                    trading_context=request.trading_context,
                    preferred_provider=request.llm_provider
                )
                
                llm_analysis = await self._analyze_goal_with_llm(analysis_request)
            
            # Extract goal components from LLM analysis
            goal_data = self._extract_goal_data_from_analysis(llm_analysis, request)
            
            # Search for relevant knowledge resources
            knowledge_resources = []
            if self.knowledge_integration_enabled and request.auto_assign_resources:
                knowledge_resources = await self._find_relevant_knowledge_resources(
                    goal_data, request.natural_language_input
                )
            
            # Create enhanced goal
            goal = EnhancedGoal(
                goal_name=goal_data.get("goal_name", "AI-Generated Goal"),
                goal_type=goal_data.get("goal_type", EnhancedGoalType.PROFIT_TARGET),
                description=goal_data.get("description", request.natural_language_input),
                target_value=Decimal(str(goal_data.get("target_value", 100))),
                complexity=goal_data.get("complexity", GoalComplexity.MODERATE),
                creation_method=request.creation_method,
                natural_language_input=request.natural_language_input,
                llm_analysis=llm_analysis,
                knowledge_resources=knowledge_resources,
                created_by=request.user_context.get("user_id", "system"),
                success_criteria=goal_data.get("success_criteria", []),
                collaboration_type=request.collaboration_type
            )
            
            # Auto-assign agents if requested
            if request.auto_assign_agents:
                goal.assigned_agents = await self._auto_assign_agents(goal, request.preferred_agents)
            
            # Generate initial predictions if enabled
            if request.enable_predictions:
                initial_prediction = await self._generate_goal_prediction(goal)
                if initial_prediction:
                    goal.ai_predictions = [initial_prediction]
            
            # Generate optimization suggestions if enabled
            if request.enable_optimization:
                optimization_suggestions = await self._generate_optimization_suggestions(goal)
                goal.optimization_suggestions = optimization_suggestions
            
            # Save goal to database
            await self._save_goal_to_database(goal)
            
            # Add to active goals
            self.active_goals[goal.goal_id] = goal
            self.goal_progress[goal.goal_id] = []
            
            # Cache in Redis
            if self.redis:
                await self.redis.setex(
                    f"enhanced_goal:{goal.goal_id}",
                    3600,
                    json.dumps(goal.model_dump(), default=str)
                )
            
            # Publish goal creation event
            await self._publish_goal_event("goal_created", goal)
            
            logger.info(f"Created enhanced goal: {goal.goal_name} ({goal.goal_id})")
            return goal
            
        except Exception as e:
            logger.error(f"Failed to create goal from natural language: {e}")
            raise
    
    async def _analyze_goal_with_llm(self, request: LLMAnalysisRequest) -> LLMAnalysisResponse:
        """Analyze natural language goal input with LLM"""
        
        try:
            start_time = datetime.now()
            
            # Choose LLM provider
            if request.preferred_provider == LLMProvider.OPENAI and self.openai_client:
                analysis = await self._analyze_with_openai(request)
            elif request.preferred_provider == LLMProvider.ANTHROPIC and self.anthropic_client:
                analysis = await self._analyze_with_anthropic(request)
            else:
                # Fallback to available provider
                if self.openai_client:
                    analysis = await self._analyze_with_openai(request)
                elif self.anthropic_client:
                    analysis = await self._analyze_with_anthropic(request)
                else:
                    raise ValueError("No LLM providers available")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            analysis.processing_time_ms = int(processing_time)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze goal with LLM: {e}")
            raise
    
    async def _analyze_with_openai(self, request: LLMAnalysisRequest) -> LLMAnalysisResponse:
        """Analyze goal using OpenAI"""
        
        # Create comprehensive prompt for goal analysis
        system_prompt = """You are an expert trading goal analyst. Analyze the user's natural language input and extract structured goal information.

Return a JSON response with the following structure:
{
    "goal_type": "one of: profit_target, trade_count, win_rate, portfolio_value, risk_management, strategy_performance, time_based, collaborative, learning_based, knowledge_acquisition, skill_development",
    "target_value": numeric_value,
    "timeframe": "time_period",
    "complexity": "simple, moderate, complex, or advanced",
    "confidence_score": 0.0-1.0,
    "feasibility_assessment": "assessment_text",
    "success_criteria": ["criterion1", "criterion2"],
    "constraints": ["constraint1", "constraint2"],
    "risk_factors": ["risk1", "risk2"],
    "recommended_strategies": ["strategy1", "strategy2"],
    "required_knowledge": ["knowledge1", "knowledge2"]
}"""
        
        user_prompt = f"""Analyze this trading goal: "{request.natural_language_input}"
        
Additional context:
- User context: {request.user_context}
- Agent context: {request.agent_context}
- Trading context: {request.trading_context}

Provide detailed analysis focusing on feasibility, required knowledge, and success factors."""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # Parse response
            content = response.choices[0].message.content
            parsed_data = json.loads(content)
            
            # Create LLM analysis response
            return LLMAnalysisResponse(
                parsed_goal=parsed_data,
                goal_type=EnhancedGoalType(parsed_data.get("goal_type", "profit_target")),
                complexity_assessment=GoalComplexity(parsed_data.get("complexity", "moderate")),
                confidence_score=parsed_data.get("confidence_score", 0.8),
                target_value=Decimal(str(parsed_data.get("target_value", 100))),
                timeframe=parsed_data.get("timeframe"),
                constraints=parsed_data.get("constraints", []),
                success_criteria=parsed_data.get("success_criteria", []),
                feasibility_assessment=parsed_data.get("feasibility_assessment", ""),
                risk_factors=parsed_data.get("risk_factors", []),
                recommended_strategies=parsed_data.get("recommended_strategies", []),
                required_knowledge=parsed_data.get("required_knowledge", []),
                provider_used=LLMProvider.OPENAI,
                model_version="gpt-4-1106-preview",
                tokens_used=response.usage.total_tokens
            )
            
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            raise
    
    async def _analyze_with_anthropic(self, request: LLMAnalysisRequest) -> LLMAnalysisResponse:
        """Analyze goal using Anthropic Claude"""
        
        prompt = f"""Analyze this trading goal and return structured information in JSON format:

Goal: "{request.natural_language_input}"

Context:
- User: {request.user_context}
- Agents: {request.agent_context}
- Trading: {request.trading_context}

Please analyze and return JSON with these fields:
- goal_type: (profit_target, trade_count, win_rate, etc.)
- target_value: numeric value
- timeframe: time period
- complexity: (simple, moderate, complex, advanced)
- confidence_score: 0.0-1.0
- feasibility_assessment: detailed assessment
- success_criteria: list of success criteria
- constraints: list of constraints
- risk_factors: list of risks
- recommended_strategies: list of strategies
- required_knowledge: list of knowledge areas

Focus on practical trading considerations and realistic assessments."""
        
        try:
            response = await self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            content = response.content[0].text
            # Extract JSON from response (Claude sometimes adds explanatory text)
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_content = content[json_start:json_end]
            
            parsed_data = json.loads(json_content)
            
            # Create LLM analysis response
            return LLMAnalysisResponse(
                parsed_goal=parsed_data,
                goal_type=EnhancedGoalType(parsed_data.get("goal_type", "profit_target")),
                complexity_assessment=GoalComplexity(parsed_data.get("complexity", "moderate")),
                confidence_score=parsed_data.get("confidence_score", 0.8),
                target_value=Decimal(str(parsed_data.get("target_value", 100))),
                timeframe=parsed_data.get("timeframe"),
                constraints=parsed_data.get("constraints", []),
                success_criteria=parsed_data.get("success_criteria", []),
                feasibility_assessment=parsed_data.get("feasibility_assessment", ""),
                risk_factors=parsed_data.get("risk_factors", []),
                recommended_strategies=parsed_data.get("recommended_strategies", []),
                required_knowledge=parsed_data.get("required_knowledge", []),
                provider_used=LLMProvider.ANTHROPIC,
                model_version="claude-3-sonnet-20240229",
                tokens_used=response.usage.input_tokens + response.usage.output_tokens
            )
            
        except Exception as e:
            logger.error(f"Anthropic analysis failed: {e}")
            raise
    
    async def _find_relevant_knowledge_resources(self, goal_data: Dict, natural_input: str) -> List[str]:
        """Find relevant knowledge resources for the goal"""
        
        try:
            farm_service = self.registry.get_service("farm_knowledge_service")
            if not farm_service:
                return []
            
            # Search for relevant resources based on goal content
            search_queries = [
                natural_input,
                goal_data.get("goal_type", ""),
                " ".join(goal_data.get("recommended_strategies", [])),
                " ".join(goal_data.get("required_knowledge", []))
            ]
            
            relevant_resources = []
            
            for query in search_queries:
                if not query:
                    continue
                    
                search_request = ResourceSearchRequest(
                    query=query,
                    resource_types=[
                        TradingResourceType.TRADING_BOOKS,
                        TradingResourceType.SOPS,
                        TradingResourceType.STRATEGIES,
                        TradingResourceType.TRAINING
                    ],
                    limit=5
                )
                
                search_results = await farm_service.search_resources(search_request)
                
                for resource in search_results.results:
                    if resource.resource_id not in relevant_resources:
                        relevant_resources.append(resource.resource_id)
            
            return relevant_resources[:10]  # Limit to top 10 resources
            
        except Exception as e:
            logger.error(f"Failed to find relevant knowledge resources: {e}")
            return []
    
    async def _extract_goal_data_from_analysis(self, llm_analysis: Optional[LLMAnalysisResponse], request: CreateEnhancedGoalRequest) -> Dict[str, Any]:
        """Extract goal data from LLM analysis or structured input"""
        
        if llm_analysis:
            return {
                "goal_name": self._generate_goal_name_from_analysis(llm_analysis),
                "goal_type": llm_analysis.goal_type,
                "description": llm_analysis.feasibility_assessment,
                "target_value": llm_analysis.target_value or Decimal("100"),
                "complexity": llm_analysis.complexity_assessment,
                "success_criteria": llm_analysis.success_criteria,
                "timeframe": llm_analysis.timeframe
            }
        elif request.structured_goal:
            return request.structured_goal
        else:
            # Fallback for when LLM is not available
            return {
                "goal_name": f"Goal from: {request.natural_language_input[:50]}...",
                "goal_type": EnhancedGoalType.PROFIT_TARGET,
                "description": request.natural_language_input,
                "target_value": Decimal("100"),
                "complexity": GoalComplexity.MODERATE,
                "success_criteria": [],
                "timeframe": "1 week"
            }
    
    def _generate_goal_name_from_analysis(self, analysis: LLMAnalysisResponse) -> str:
        """Generate a concise goal name from LLM analysis"""
        
        goal_type = analysis.goal_type.value.replace("_", " ").title()
        target_value = analysis.target_value
        timeframe = analysis.timeframe or "short-term"
        
        if analysis.goal_type == EnhancedGoalType.PROFIT_TARGET:
            return f"Profit Target: ${target_value} ({timeframe})"
        elif analysis.goal_type == EnhancedGoalType.TRADE_COUNT:
            return f"Trade Volume: {target_value} trades ({timeframe})"
        elif analysis.goal_type == EnhancedGoalType.WIN_RATE:
            return f"Win Rate: {target_value}% ({timeframe})"
        else:
            return f"{goal_type} Goal ({timeframe})"
    
    async def _auto_assign_agents(self, goal: EnhancedGoal, preferred_agents: Optional[List[str]]) -> List[str]:
        """Auto-assign agents to goal based on capabilities and preferences"""
        
        try:
            agent_service = self.registry.get_service("agent_management_service")
            if not agent_service:
                return preferred_agents or []
            
            # Get available agents
            available_agents = await agent_service.get_available_agents()
            
            if preferred_agents:
                # Filter preferred agents that are available
                assigned_agents = [
                    agent_id for agent_id in preferred_agents 
                    if any(agent.agent_id == agent_id for agent in available_agents)
                ]
            else:
                # Auto-select based on goal type and agent capabilities
                suitable_agents = []
                
                for agent in available_agents:
                    agent_capabilities = getattr(agent, 'capabilities', [])
                    goal_type_str = goal.goal_type.value
                    
                    # Match agents based on goal type
                    if (goal_type_str in agent_capabilities or
                        any(cap in goal_type_str for cap in agent_capabilities)):
                        suitable_agents.append(agent.agent_id)
                
                assigned_agents = suitable_agents[:3]  # Limit to 3 agents
            
            return assigned_agents
            
        except Exception as e:
            logger.error(f"Failed to auto-assign agents: {e}")
            return preferred_agents or []
    
    async def _generate_goal_prediction(self, goal: EnhancedGoal) -> Optional[GoalPrediction]:
        """Generate AI-powered goal completion prediction"""
        
        try:
            # Get historical performance data
            performance_service = self.registry.get_service("agent_performance_service")
            if not performance_service:
                return None
            
            # Analyze historical goal completion patterns
            historical_data = await performance_service.get_goal_completion_history(
                goal_type=goal.goal_type,
                complexity=goal.complexity,
                agent_ids=goal.assigned_agents
            )
            
            # Calculate completion probability based on historical data
            if historical_data:
                completion_rate = historical_data.get("completion_rate", 0.5)
                avg_completion_time = historical_data.get("avg_completion_time_days", 7)
            else:
                # Default estimates
                completion_rate = 0.7
                avg_completion_time = 7
            
            # Adjust based on goal complexity
            complexity_adjustment = {
                GoalComplexity.SIMPLE: 1.2,
                GoalComplexity.MODERATE: 1.0,
                GoalComplexity.COMPLEX: 0.8,
                GoalComplexity.ADVANCED: 0.6
            }
            
            adjusted_probability = min(completion_rate * complexity_adjustment[goal.complexity], 1.0)
            estimated_completion = datetime.now(timezone.utc) + timedelta(days=avg_completion_time)
            
            # Generate success and risk factors
            success_factors = [
                "Clear target and timeline defined",
                "Relevant knowledge resources assigned",
                "Experienced agents assigned"
            ]
            
            risk_factors = [
                "Market volatility may impact results",
                "Dependent on agent performance consistency"
            ]
            
            if goal.llm_analysis:
                success_factors.extend(goal.llm_analysis.success_criteria[:3])
                risk_factors.extend(goal.llm_analysis.risk_factors[:3])
            
            prediction = GoalPrediction(
                goal_id=goal.goal_id,
                completion_probability=adjusted_probability,
                estimated_completion_date=estimated_completion,
                confidence_interval={"lower": adjusted_probability - 0.1, "upper": adjusted_probability + 0.1},
                success_factors=success_factors,
                risk_factors=risk_factors,
                model_version="enhanced_goal_predictor_v1.0",
                data_quality_score=0.8 if historical_data else 0.6
            )
            
            return prediction
            
        except Exception as e:
            logger.error(f"Failed to generate goal prediction: {e}")
            return None
    
    async def _generate_optimization_suggestions(self, goal: EnhancedGoal) -> List[GoalOptimizationSuggestion]:
        """Generate optimization suggestions for the goal"""
        
        try:
            suggestions = []
            
            # Analyze goal for optimization opportunities
            if goal.complexity == GoalComplexity.COMPLEX:
                suggestions.append(GoalOptimizationSuggestion(
                    goal_id=goal.goal_id,
                    suggestion_type="target_adjustment",
                    current_approach=f"Target: {goal.target_value}",
                    suggested_approach="Consider breaking into smaller milestones",
                    expected_improvement="Improved tracking and motivation",
                    implementation_effort="low",
                    probability_improvement=0.8,
                    implementation_steps=[
                        "Create 3-5 intermediate milestones",
                        "Set milestone completion rewards",
                        "Track progress more frequently"
                    ],
                    ai_confidence=0.9
                ))
            
            # Knowledge-based suggestions
            if len(goal.knowledge_resources) < 3:
                suggestions.append(GoalOptimizationSuggestion(
                    goal_id=goal.goal_id,
                    suggestion_type="resource_addition",
                    current_approach=f"{len(goal.knowledge_resources)} knowledge resources assigned",
                    suggested_approach="Add more relevant learning resources",
                    expected_improvement="Better informed trading decisions",
                    implementation_effort="low",
                    probability_improvement=0.7,
                    implementation_steps=[
                        "Search for relevant trading books",
                        "Add SOPs for goal-related strategies",
                        "Include market research documents"
                    ],
                    ai_confidence=0.8
                ))
            
            # Agent assignment suggestions
            if len(goal.assigned_agents) < 2:
                suggestions.append(GoalOptimizationSuggestion(
                    goal_id=goal.goal_id,
                    suggestion_type="approach_optimization",
                    current_approach=f"{len(goal.assigned_agents)} agent(s) assigned",
                    suggested_approach="Assign additional agents for redundancy",
                    expected_improvement="Reduced single-point-of-failure risk",
                    implementation_effort="medium",
                    probability_improvement=0.6,
                    implementation_steps=[
                        "Identify agents with complementary skills",
                        "Assign backup agents",
                        "Set up agent coordination protocols"
                    ],
                    ai_confidence=0.7
                ))
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate optimization suggestions: {e}")
            return []
    
    async def _save_goal_to_database(self, goal: EnhancedGoal):
        """Save enhanced goal to database"""
        
        try:
            if self.supabase:
                goal_dict = goal.model_dump()
                
                # Convert enum values to strings
                goal_dict["goal_type"] = goal.goal_type.value
                goal_dict["complexity"] = goal.complexity.value
                goal_dict["creation_method"] = goal.creation_method.value
                
                # Convert datetime objects
                goal_dict["created_at"] = goal.created_at.isoformat()
                goal_dict["last_updated"] = goal.last_updated.isoformat()
                if goal.target_date:
                    goal_dict["target_date"] = goal.target_date.isoformat()
                
                # Convert Decimal to float
                goal_dict["target_value"] = float(goal.target_value)
                goal_dict["current_value"] = float(goal.current_value)
                
                # Store LLM analysis as JSON
                if goal.llm_analysis:
                    goal_dict["llm_analysis"] = goal.llm_analysis.model_dump()
                
                # Store predictions and suggestions as JSON
                goal_dict["ai_predictions"] = [pred.model_dump() for pred in goal.ai_predictions]
                goal_dict["optimization_suggestions"] = [sug.model_dump() for sug in goal.optimization_suggestions]
                
                # Insert into database
                result = self.supabase.table('goals').insert(goal_dict).execute()
                
                if result.data:
                    logger.info(f"Goal saved to database: {goal.goal_id}")
                else:
                    logger.error(f"Failed to save goal to database: {result}")
                    
        except Exception as e:
            logger.error(f"Database save failed for goal {goal.goal_id}: {e}")
            raise
    
    async def _publish_goal_event(self, event_type: str, goal: EnhancedGoal):
        """Publish goal events for other services"""
        
        try:
            event_data = {
                "event_type": event_type,
                "goal_id": goal.goal_id,
                "goal_name": goal.goal_name,
                "goal_type": goal.goal_type.value,
                "target_value": float(goal.target_value),
                "assigned_agents": goal.assigned_agents,
                "knowledge_resources": goal.knowledge_resources,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Publish to Redis if available
            if self.redis:
                await self.redis.publish("goal_events", json.dumps(event_data, default=str))
            
            # Notify other services
            farm_service = self.registry.get_service("farm_knowledge_service")
            if farm_service and event_type == "goal_created":
                await farm_service.notify_goal_created(goal.goal_id, goal.knowledge_resources)
            
            agent_service = self.registry.get_service("agent_management_service")
            if agent_service and goal.assigned_agents:
                for agent_id in goal.assigned_agents:
                    await agent_service.assign_goal_to_agent(agent_id, goal.goal_id)
            
        except Exception as e:
            logger.error(f"Failed to publish goal event: {e}")
    
    async def _load_active_goals(self):
        """Load active goals from database"""
        
        try:
            if self.supabase:
                response = self.supabase.table('goals').select('*')\
                    .in_('status', ['pending', 'active', 'in_progress'])\
                    .execute()
                
                for goal_data in response.data:
                    try:
                        # Convert database record back to EnhancedGoal
                        goal = self._convert_db_record_to_goal(goal_data)
                        self.active_goals[goal.goal_id] = goal
                        self.goal_progress[goal.goal_id] = []
                        
                    except Exception as e:
                        logger.error(f"Failed to load goal {goal_data.get('goal_id')}: {e}")
                
                logger.info(f"Loaded {len(self.active_goals)} active enhanced goals")
                
        except Exception as e:
            logger.error(f"Failed to load active goals: {e}")
    
    def _convert_db_record_to_goal(self, goal_data: Dict) -> EnhancedGoal:
        """Convert database record to EnhancedGoal object"""
        
        # Convert string values back to enums
        goal_data["goal_type"] = EnhancedGoalType(goal_data["goal_type"])
        goal_data["complexity"] = GoalComplexity(goal_data.get("complexity", "moderate"))
        goal_data["creation_method"] = GoalCreationMethod(goal_data.get("creation_method", "natural_language"))
        
        # Convert string dates back to datetime
        goal_data["created_at"] = datetime.fromisoformat(goal_data["created_at"])
        goal_data["last_updated"] = datetime.fromisoformat(goal_data["last_updated"])
        if goal_data.get("target_date"):
            goal_data["target_date"] = datetime.fromisoformat(goal_data["target_date"])
        if goal_data.get("completed_at"):
            goal_data["completed_at"] = datetime.fromisoformat(goal_data["completed_at"])
        
        # Convert numeric values to Decimal
        goal_data["target_value"] = Decimal(str(goal_data["target_value"]))
        goal_data["current_value"] = Decimal(str(goal_data["current_value"]))
        
        # Convert JSON fields back to objects
        if goal_data.get("llm_analysis"):
            goal_data["llm_analysis"] = LLMAnalysisResponse(**goal_data["llm_analysis"])
        
        if goal_data.get("ai_predictions"):
            goal_data["ai_predictions"] = [GoalPrediction(**pred) for pred in goal_data["ai_predictions"]]
        
        if goal_data.get("optimization_suggestions"):
            goal_data["optimization_suggestions"] = [GoalOptimizationSuggestion(**sug) for sug in goal_data["optimization_suggestions"]]
        
        return EnhancedGoal(**goal_data)
    
    async def _start_background_tasks(self):
        """Start background monitoring and optimization tasks"""
        
        try:
            # Goal monitoring task
            monitoring_task = asyncio.create_task(self._goal_monitoring_loop())
            self.monitoring_tasks.append(monitoring_task)
            
            # Prediction update task
            prediction_task = asyncio.create_task(self._prediction_update_loop())
            self.monitoring_tasks.append(prediction_task)
            
            # Optimization suggestion task
            optimization_task = asyncio.create_task(self._optimization_suggestion_loop())
            self.monitoring_tasks.append(optimization_task)
            
            logger.info("Background tasks started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start background tasks: {e}")
    
    async def _goal_monitoring_loop(self):
        """Background goal monitoring loop"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                for goal_id, goal in self.active_goals.items():
                    try:
                        # Update goal progress
                        current_value = await self._calculate_current_goal_value(goal_id)
                        if current_value != goal.current_value:
                            await self._update_goal_progress(goal_id, current_value)
                        
                        # Check for completion
                        if goal.progress_percentage >= 100.0 and goal.status != "completed":
                            await self._complete_enhanced_goal(goal_id)
                        
                        # Check for expiration
                        if goal.target_date and datetime.now(timezone.utc) > goal.target_date:
                            if goal.status not in ["completed", "failed"]:
                                await self._expire_goal(goal_id)
                        
                    except Exception as e:
                        logger.error(f"Error monitoring goal {goal_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in goal monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _prediction_update_loop(self):
        """Update goal predictions periodically"""
        
        while True:
            try:
                await asyncio.sleep(3600)  # Update every hour
                
                for goal_id, goal in self.active_goals.items():
                    try:
                        # Generate updated prediction
                        new_prediction = await self._generate_goal_prediction(goal)
                        if new_prediction:
                            goal.ai_predictions.append(new_prediction)
                            # Keep only last 5 predictions
                            goal.ai_predictions = goal.ai_predictions[-5:]
                            
                            # Update in database
                            await self._update_goal_predictions(goal_id, goal.ai_predictions)
                        
                    except Exception as e:
                        logger.error(f"Error updating predictions for goal {goal_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in prediction update loop: {e}")
                await asyncio.sleep(1800)  # Retry in 30 minutes
    
    async def _optimization_suggestion_loop(self):
        """Generate optimization suggestions periodically"""
        
        while True:
            try:
                await asyncio.sleep(21600)  # Every 6 hours
                
                for goal_id, goal in self.active_goals.items():
                    try:
                        # Generate new optimization suggestions
                        new_suggestions = await self._generate_optimization_suggestions(goal)
                        if new_suggestions:
                            goal.optimization_suggestions.extend(new_suggestions)
                            # Keep only recent suggestions
                            goal.optimization_suggestions = goal.optimization_suggestions[-10:]
                            
                            # Update in database
                            await self._update_goal_suggestions(goal_id, goal.optimization_suggestions)
                        
                    except Exception as e:
                        logger.error(f"Error updating suggestions for goal {goal_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in optimization suggestion loop: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def get_enhanced_goal_status(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive enhanced goal status"""
        
        try:
            goal = self.active_goals.get(goal_id)
            if not goal:
                # Check completed goals
                completion = self.completed_goals.get(goal_id)
                if completion:
                    return {
                        "goal_id": goal_id,
                        "status": "completed",
                        "completion_data": completion.model_dump()
                    }
                return None
            
            # Get latest progress
            latest_progress = None
            if goal_id in self.goal_progress and self.goal_progress[goal_id]:
                latest_progress = self.goal_progress[goal_id][-1]
            
            # Get latest prediction
            latest_prediction = None
            if goal.ai_predictions:
                latest_prediction = goal.ai_predictions[-1]
            
            return {
                "goal_id": goal_id,
                "name": goal.goal_name,
                "type": goal.goal_type.value,
                "status": goal.status,
                "progress_percentage": goal.progress_percentage,
                "current_value": float(goal.current_value),
                "target_value": float(goal.target_value),
                "complexity": goal.complexity.value,
                "creation_method": goal.creation_method.value,
                "assigned_agents": goal.assigned_agents,
                "knowledge_resources": goal.knowledge_resources,
                "latest_progress": latest_progress.model_dump() if latest_progress else None,
                "latest_prediction": latest_prediction.model_dump() if latest_prediction else None,
                "optimization_suggestions": [s.model_dump() for s in goal.optimization_suggestions[-3:]],
                "llm_analysis": goal.llm_analysis.model_dump() if goal.llm_analysis else None,
                "created_at": goal.created_at.isoformat(),
                "target_date": goal.target_date.isoformat() if goal.target_date else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get enhanced goal status: {e}")
            return None
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get enhanced service status and metrics"""
        
        return {
            "service": "enhanced_goal_management_service",
            "status": "running",
            "llm_enabled": self.llm_enabled,
            "knowledge_integration_enabled": self.knowledge_integration_enabled,
            "active_goals": len(self.active_goals),
            "completed_goals": len(self.completed_goals),
            "background_tasks_running": len([task for task in self.monitoring_tasks if not task.done()]),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_enhanced_goal_management_service():
    """Factory function to create EnhancedGoalManagementService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = EnhancedGoalManagementService(redis_client, supabase_client)
    return service