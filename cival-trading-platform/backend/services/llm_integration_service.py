"""
Phase 10: LLM Integration Service
Advanced language model integration for autonomous trading system
Supports multiple LLM providers with unified interface and intelligent routing
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import hashlib
from decimal import Decimal

import openai
import anthropic
from transformers import pipeline
import tiktoken
import redis.asyncio as redis
import google.generativeai as genai
import httpx
import os

from ..core.service_registry import get_registry
from ..core.llm_router import LLMRouter
from ..models.llm_models import (
    LLMRequest, LLMResponse, ConversationContext, 
    AgentCommunication, TradingDecision, MarketAnalysis
)

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT35 = "openai_gpt35"
    ANTHROPIC_CLAUDE = "anthropic_claude"
    HUGGINGFACE_LOCAL = "huggingface_local"
    GOOGLE_GEMINI = "google_gemini"
    GEMINI_FLASH = "gemini_flash"
    OPENROUTER_GPT4 = "openrouter_gpt4"
    OPENROUTER_CLAUDE = "openrouter_claude"
    OPENROUTER_LLAMA = "openrouter_llama"
    OPENROUTER_MISTRAL = "openrouter_mistral"

class LLMTaskType(Enum):
    """Types of LLM tasks"""
    MARKET_ANALYSIS = "market_analysis"
    TRADING_DECISION = "trading_decision"
    RISK_ASSESSMENT = "risk_assessment"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    AGENT_COMMUNICATION = "agent_communication"
    GOAL_PLANNING = "goal_planning"
    STRATEGY_GENERATION = "strategy_generation"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    NATURAL_LANGUAGE_QUERY = "natural_language_query"

@dataclass
class LLMConfig:
    """LLM provider configuration"""
    provider: LLMProvider
    model_name: str
    api_key: Optional[str]
    endpoint: Optional[str]
    max_tokens: int
    temperature: float
    timeout: int
    cost_per_token: float
    rate_limit_rpm: int
    rate_limit_tpm: int

@dataclass
class AgentPersonality:
    """Agent personality configuration for communication"""
    agent_id: str
    name: str
    role: str
    trading_style: str
    risk_tolerance: float
    communication_style: str
    expertise_areas: List[str]
    personality_traits: Dict[str, float]
    system_prompt: str

@dataclass
class ConversationMessage:
    """Individual conversation message"""
    message_id: str
    sender_id: str
    recipient_id: str
    content: str
    message_type: str
    timestamp: datetime
    context: Dict[str, Any]
    response_to: Optional[str] = None

class LLMIntegrationService:
    """
    Advanced LLM integration service for autonomous trading system
    Phase 10: Multi-provider support with intelligent routing and agent communication
    """
    
    def __init__(self, redis_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        
        # Service dependencies
        self.event_service = None
        self.market_data_service = None
        self.portfolio_service = None
        self.goal_service = None
        
        # LLM providers
        self.providers: Dict[LLMProvider, Any] = {}
        self.provider_configs: Dict[LLMProvider, LLMConfig] = {}
        
        # Agent personalities
        self.agent_personalities: Dict[str, AgentPersonality] = {}
        
        # Conversation management
        self.active_conversations: Dict[str, List[ConversationMessage]] = {}
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        
        # Performance tracking
        self.provider_performance: Dict[LLMProvider, Dict[str, Any]] = {}
        self.token_usage: Dict[str, int] = {}
        self.cost_tracking: Dict[str, float] = {}
        
        # Rate limiting
        self.rate_limiters: Dict[LLMProvider, Dict[str, Any]] = {}
        
        # Caching
        self.response_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize LLM router
        self.router = LLMRouter()
        
        logger.info("LLMIntegrationService Phase 10 initialized")
    
    async def initialize(self):
        """Initialize the LLM integration service"""
        try:
            # Get required services
            self.event_service = self.registry.get_service("wallet_event_streaming_service")
            self.market_data_service = self.registry.get_service("market_data_service")
            self.portfolio_service = self.registry.get_service("portfolio_management_service")
            self.goal_service = self.registry.get_service("intelligent_goal_service")
            
            # Initialize LLM providers
            await self._initialize_providers()
            
            # Load agent personalities
            await self._load_agent_personalities()
            
            # Start background tasks
            asyncio.create_task(self._conversation_manager())
            asyncio.create_task(self._performance_monitor())
            asyncio.create_task(self._cache_cleanup())
            
            logger.info("LLMIntegrationService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLMIntegrationService: {e}")
            raise
    
    async def _initialize_providers(self):
        """Initialize all LLM providers"""
        try:
            # OpenAI GPT-4
            if openai.api_key:
                self.providers[LLMProvider.OPENAI_GPT4] = openai
                self.provider_configs[LLMProvider.OPENAI_GPT4] = LLMConfig(
                    provider=LLMProvider.OPENAI_GPT4,
                    model_name="gpt-4-turbo-preview",
                    api_key=openai.api_key,
                    endpoint="https://api.openai.com/v1",
                    max_tokens=4096,
                    temperature=0.7,
                    timeout=60,
                    cost_per_token=0.00003,
                    rate_limit_rpm=500,
                    rate_limit_tpm=30000
                )
            
            # Anthropic Claude
            try:
                claude_client = anthropic.Anthropic()
                self.providers[LLMProvider.ANTHROPIC_CLAUDE] = claude_client
                self.provider_configs[LLMProvider.ANTHROPIC_CLAUDE] = LLMConfig(
                    provider=LLMProvider.ANTHROPIC_CLAUDE,
                    model_name="claude-3-opus-20240229",
                    api_key=None,  # Set via environment
                    endpoint="https://api.anthropic.com",
                    max_tokens=4096,
                    temperature=0.7,
                    timeout=60,
                    cost_per_token=0.000015,
                    rate_limit_rpm=200,
                    rate_limit_tpm=20000
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic Claude: {e}")
            
            # Local HuggingFace models
            try:
                self.providers[LLMProvider.HUGGINGFACE_LOCAL] = pipeline(
                    "text-generation",
                    model="microsoft/DialoGPT-medium",
                    device=-1  # CPU
                )
                self.provider_configs[LLMProvider.HUGGINGFACE_LOCAL] = LLMConfig(
                    provider=LLMProvider.HUGGINGFACE_LOCAL,
                    model_name="microsoft/DialoGPT-medium",
                    api_key=None,
                    endpoint=None,
                    max_tokens=1024,
                    temperature=0.8,
                    timeout=30,
                    cost_per_token=0.0,  # Free local model
                    rate_limit_rpm=1000,
                    rate_limit_tpm=50000
                )
            except Exception as e:
                logger.warning(f"Failed to initialize HuggingFace local model: {e}")
            
            # Google Gemini
            try:
                google_api_key = os.getenv("GOOGLE_API_KEY")
                if google_api_key and google_api_key != "your_google_gemini_api_key_here":
                    genai.configure(api_key=google_api_key)
                    gemini_model = genai.GenerativeModel('gemini-pro')
                    self.providers[LLMProvider.GOOGLE_GEMINI] = gemini_model
                    self.provider_configs[LLMProvider.GOOGLE_GEMINI] = LLMConfig(
                        provider=LLMProvider.GOOGLE_GEMINI,
                        model_name="gemini-pro",
                        api_key=google_api_key,
                        endpoint="https://generativelanguage.googleapis.com",
                        max_tokens=8192,
                        temperature=0.7,
                        timeout=30,
                        cost_per_token=0.0,  # Free tier
                        rate_limit_rpm=60,
                        rate_limit_tpm=32000
                    )
                    
                    # Gemini Flash (faster, cheaper model)
                    gemini_flash = genai.GenerativeModel('gemini-1.5-flash')
                    self.providers[LLMProvider.GEMINI_FLASH] = gemini_flash
                    self.provider_configs[LLMProvider.GEMINI_FLASH] = LLMConfig(
                        provider=LLMProvider.GEMINI_FLASH,
                        model_name="gemini-1.5-flash",
                        api_key=google_api_key,
                        endpoint="https://generativelanguage.googleapis.com",
                        max_tokens=8192,
                        temperature=0.7,
                        timeout=15,
                        cost_per_token=0.0,  # Free tier
                        rate_limit_rpm=120,
                        rate_limit_tpm=64000
                    )
                    logger.info("Google Gemini models initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Gemini: {e}")
            
            # OpenRouter Integration
            try:
                openrouter_key = os.getenv("OPENROUTER_API_KEY")
                if openrouter_key:
                    # OpenRouter GPT-4
                    self.providers[LLMProvider.OPENROUTER_GPT4] = "openrouter_client"
                    self.provider_configs[LLMProvider.OPENROUTER_GPT4] = LLMConfig(
                        provider=LLMProvider.OPENROUTER_GPT4,
                        model_name="openai/gpt-4-turbo-preview",
                        api_key=openrouter_key,
                        endpoint="https://openrouter.ai/api/v1",
                        max_tokens=4096,
                        temperature=0.7,
                        timeout=60,
                        cost_per_token=0.00003,
                        rate_limit_rpm=500,
                        rate_limit_tpm=30000
                    )
                    
                    # OpenRouter Claude
                    self.providers[LLMProvider.OPENROUTER_CLAUDE] = "openrouter_client"
                    self.provider_configs[LLMProvider.OPENROUTER_CLAUDE] = LLMConfig(
                        provider=LLMProvider.OPENROUTER_CLAUDE,
                        model_name="anthropic/claude-3-opus",
                        api_key=openrouter_key,
                        endpoint="https://openrouter.ai/api/v1",
                        max_tokens=4096,
                        temperature=0.7,
                        timeout=60,
                        cost_per_token=0.000015,
                        rate_limit_rpm=200,
                        rate_limit_tpm=20000
                    )
                    
                    # OpenRouter Llama
                    self.providers[LLMProvider.OPENROUTER_LLAMA] = "openrouter_client"
                    self.provider_configs[LLMProvider.OPENROUTER_LLAMA] = LLMConfig(
                        provider=LLMProvider.OPENROUTER_LLAMA,
                        model_name="meta-llama/llama-3-70b-instruct",
                        api_key=openrouter_key,
                        endpoint="https://openrouter.ai/api/v1",
                        max_tokens=4096,
                        temperature=0.7,
                        timeout=60,
                        cost_per_token=0.0000009,
                        rate_limit_rpm=300,
                        rate_limit_tpm=25000
                    )
                    
                    # OpenRouter Mistral
                    self.providers[LLMProvider.OPENROUTER_MISTRAL] = "openrouter_client"
                    self.provider_configs[LLMProvider.OPENROUTER_MISTRAL] = LLMConfig(
                        provider=LLMProvider.OPENROUTER_MISTRAL,
                        model_name="mistralai/mixtral-8x7b-instruct",
                        api_key=openrouter_key,
                        endpoint="https://openrouter.ai/api/v1",
                        max_tokens=4096,
                        temperature=0.7,
                        timeout=45,
                        cost_per_token=0.0000006,
                        rate_limit_rpm=400,
                        rate_limit_tpm=35000
                    )
                    logger.info("OpenRouter models initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenRouter: {e}")
            
            logger.info(f"Initialized {len(self.providers)} LLM providers")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM providers: {e}")
            raise
    
    async def _load_agent_personalities(self):
        """Load agent personality configurations"""
        try:
            # Define agent personalities for different trading strategies
            personalities = [
                AgentPersonality(
                    agent_id="trend_follower_001",
                    name="Marcus Momentum",
                    role="Trend Following Specialist",
                    trading_style="aggressive_momentum",
                    risk_tolerance=0.7,
                    communication_style="confident_analytical",
                    expertise_areas=["trend_analysis", "momentum_indicators", "breakout_patterns"],
                    personality_traits={
                        "confidence": 0.8,
                        "risk_seeking": 0.7,
                        "analytical": 0.9,
                        "collaborative": 0.6
                    },
                    system_prompt="""You are Marcus Momentum, a trend-following trading specialist. 
                    You excel at identifying and riding market trends. You're confident in your analysis 
                    but always back decisions with data. You communicate clearly and decisively, 
                    focusing on momentum indicators and trend strength."""
                ),
                
                AgentPersonality(
                    agent_id="arbitrage_bot_003",
                    name="Alex Arbitrage",
                    role="Arbitrage Opportunity Hunter",
                    trading_style="risk_neutral_arbitrage",
                    risk_tolerance=0.3,
                    communication_style="precise_mathematical",
                    expertise_areas=["price_discrepancies", "cross_exchange_analysis", "statistical_arbitrage"],
                    personality_traits={
                        "confidence": 0.9,
                        "risk_seeking": 0.2,
                        "analytical": 0.95,
                        "collaborative": 0.8
                    },
                    system_prompt="""You are Alex Arbitrage, a precision-focused arbitrage specialist. 
                    You identify riYOUR_OPENAI_API_KEY_HERE profit opportunities across markets. You communicate with 
                    mathematical precision and always quantify potential returns and risks. 
                    You're highly collaborative and share insights freely."""
                ),
                
                AgentPersonality(
                    agent_id="mean_reversion_002",
                    name="Sophia Reversion",
                    role="Mean Reversion Strategist",
                    trading_style="conservative_mean_reversion",
                    risk_tolerance=0.4,
                    communication_style="thoughtful_cautious",
                    expertise_areas=["oversold_conditions", "support_resistance", "statistical_mean_reversion"],
                    personality_traits={
                        "confidence": 0.6,
                        "risk_seeking": 0.3,
                        "analytical": 0.8,
                        "collaborative": 0.9
                    },
                    system_prompt="""You are Sophia Reversion, a thoughtful mean reversion strategist. 
                    You identify when assets are oversold or overbought and likely to revert to mean. 
                    You're cautious and methodical, always considering multiple scenarios. 
                    You communicate thoughtfully and seek input from other agents."""
                ),
                
                AgentPersonality(
                    agent_id="risk_manager_007",
                    name="Riley Risk",
                    role="Portfolio Risk Manager",
                    trading_style="defensive_risk_management",
                    risk_tolerance=0.2,
                    communication_style="authoritative_protective",
                    expertise_areas=["portfolio_risk", "volatility_analysis", "correlation_monitoring"],
                    personality_traits={
                        "confidence": 0.7,
                        "risk_seeking": 0.1,
                        "analytical": 0.9,
                        "collaborative": 0.7
                    },
                    system_prompt="""You are Riley Risk, the portfolio's guardian and risk manager. 
                    Your primary goal is protecting capital and managing downside risk. 
                    You communicate authoritatively when risks are detected and work to 
                    keep the portfolio within safe parameters. You're analytical and protective."""
                )
            ]
            
            for personality in personalities:
                self.agent_personalities[personality.agent_id] = personality
            
            logger.info(f"Loaded {len(personalities)} agent personalities")
            
        except Exception as e:
            logger.error(f"Failed to load agent personalities: {e}")
    
    async def process_llm_request(
        self,
        request: LLMRequest,
        preferred_provider: Optional[LLMProvider] = None,
        agent_id: Optional[str] = None
    ) -> LLMResponse:
        """Process an LLM request with intelligent provider selection"""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                logger.info(f"Returning cached response for request {request.request_id}")
                return cached_response
            
            # Select optimal provider
            provider = await self._select_optimal_provider(request, preferred_provider, agent_id)
            
            # Process request
            response = await self._process_with_provider(provider, request)
            
            # Cache response
            await self._cache_response(cache_key, response)
            
            # Track usage and performance
            await self._track_usage(provider, request, response)
            
            # Emit event
            if self.event_service:
                await self.event_service.emit_event({
                    'event_type': 'llm.request_processed',
                    'request_id': request.request_id,
                    'provider': provider.value,
                    'task_type': request.task_type.value,
                    'tokens_used': response.tokens_used,
                    'processing_time': response.processing_time,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to process LLM request {request.request_id}: {e}")
            raise
    
    async def _select_optimal_provider(
        self,
        request: LLMRequest,
        preferred_provider: Optional[LLMProvider] = None,
        agent_id: Optional[str] = None
    ) -> LLMProvider:
        """Select the optimal LLM provider using intelligent routing"""
        try:
            if preferred_provider and preferred_provider in self.providers:
                return preferred_provider
            
            # Assess task complexity
            complexity = self.router.assess_complexity(
                request.prompt, 
                request.task_type, 
                request.context
            )
            
            # Get routing decision
            routing_decision = await self.router.select_provider(
                task_type=request.task_type,
                complexity=complexity,
                agent_id=agent_id,
                context=request.context
            )
            
            # Check if primary provider is available
            if routing_decision.primary_provider in self.providers:
                logger.info(f"Selected {routing_decision.primary_provider.value}: {routing_decision.reasoning}")
                return routing_decision.primary_provider
            
            # Fallback to secondary provider
            if routing_decision.fallback_provider and routing_decision.fallback_provider in self.providers:
                logger.info(f"Fallback to {routing_decision.fallback_provider.value}")
                return routing_decision.fallback_provider
            
            # Emergency fallback - use any available provider
            available_providers = list(self.providers.keys())
            if available_providers:
                provider = available_providers[0]
                logger.warning(f"Emergency fallback to {provider.value}")
                return provider
            
            raise ValueError("No LLM providers available")
            
        except Exception as e:
            logger.error(f"Failed to select optimal provider: {e}")
            # Final fallback
            if LLMProvider.GOOGLE_GEMINI in self.providers:
                return LLMProvider.GOOGLE_GEMINI
            elif LLMProvider.GEMINI_FLASH in self.providers:
                return LLMProvider.GEMINI_FLASH
            raise
    
    async def _process_with_provider(
        self,
        provider: LLMProvider,
        request: LLMRequest
    ) -> LLMResponse:
        """Process request with specific provider"""
        try:
            start_time = datetime.now(timezone.utc)
            
            if provider == LLMProvider.OPENAI_GPT4:
                response = await self._process_openai(request, "gpt-4-turbo-preview")
            elif provider == LLMProvider.ANTHROPIC_CLAUDE:
                response = await self._process_anthropic(request)
            elif provider == LLMProvider.HUGGINGFACE_LOCAL:
                response = await self._process_huggingface(request)
            elif provider == LLMProvider.GOOGLE_GEMINI:
                response = await self._process_gemini(request, "gemini-pro")
            elif provider == LLMProvider.GEMINI_FLASH:
                response = await self._process_gemini(request, "gemini-1.5-flash")
            elif provider in [LLMProvider.OPENROUTER_GPT4, LLMProvider.OPENROUTER_CLAUDE, 
                            LLMProvider.OPENROUTER_LLAMA, LLMProvider.OPENROUTER_MISTRAL]:
                response = await self._process_openrouter(request, provider)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return LLMResponse(
                request_id=request.request_id,
                provider=provider,
                content=response['content'],
                tokens_used=response.get('tokens_used', 0),
                processing_time=processing_time,
                confidence_score=response.get('confidence_score', 0.8),
                metadata=response.get('metadata', {}),
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to process with provider {provider}: {e}")
            raise
    
    async def _process_openai(self, request: LLMRequest, model: str) -> Dict[str, Any]:
        """Process request with OpenAI"""
        try:
            messages = [
                {"role": "system", "content": request.system_prompt or "You are a helpful AI assistant for trading analysis."},
                {"role": "user", "content": request.prompt}
            ]
            
            if request.context:
                context_message = f"Context: {json.dumps(request.context, indent=2)}"
                messages.insert(-1, {"role": "user", "content": context_message})
            
            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens or 2048,
                temperature=request.temperature or 0.7,
                timeout=30
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            return {
                'content': content,
                'tokens_used': tokens_used,
                'confidence_score': 0.85,
                'metadata': {
                    'model': model,
                    'finish_reason': response.choices[0].finish_reason
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI processing failed: {e}")
            raise
    
    async def _process_anthropic(self, request: LLMRequest) -> Dict[str, Any]:
        """Process request with Anthropic Claude"""
        try:
            client = self.providers[LLMProvider.ANTHROPIC_CLAUDE]
            
            prompt = request.prompt
            if request.context:
                prompt = f"Context: {json.dumps(request.context, indent=2)}\n\n{prompt}"
            
            if request.system_prompt:
                prompt = f"{request.system_prompt}\n\n{prompt}"
            
            response = await client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=request.max_tokens or 2048,
                temperature=request.temperature or 0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            return {
                'content': content,
                'tokens_used': tokens_used,
                'confidence_score': 0.9,
                'metadata': {
                    'model': 'claude-3-opus-20240229',
                    'stop_reason': response.stop_reason
                }
            }
            
        except Exception as e:
            logger.error(f"Anthropic processing failed: {e}")
            raise
    
    async def _process_huggingface(self, request: LLMRequest) -> Dict[str, Any]:
        """Process request with local HuggingFace model"""
        try:
            generator = self.providers[LLMProvider.HUGGINGFACE_LOCAL]
            
            prompt = request.prompt
            if request.context:
                prompt = f"Context: {json.dumps(request.context, indent=2)}\n\n{prompt}"
            
            response = generator(
                prompt,
                max_length=request.max_tokens or 1024,
                temperature=request.temperature or 0.8,
                num_return_sequences=1,
                pad_token_id=generator.tokenizer.eos_token_id
            )
            
            content = response[0]['generated_text']
            # Remove the original prompt from the response
            if content.startswith(prompt):
                content = content[len(prompt):].strip()
            
            return {
                'content': content,
                'tokens_used': len(content.split()),  # Approximate token count
                'confidence_score': 0.7,
                'metadata': {
                    'model': 'microsoft/DialoGPT-medium',
                    'local_processing': True
                }
            }
            
        except Exception as e:
            logger.error(f"HuggingFace processing failed: {e}")
            raise
    
    async def _process_gemini(self, request: LLMRequest, model_name: str) -> Dict[str, Any]:
        """Process request with Google Gemini"""
        try:
            if model_name == "gemini-pro":
                model = self.providers[LLMProvider.GOOGLE_GEMINI]
            else:
                model = self.providers[LLMProvider.GEMINI_FLASH]
            
            # Prepare the prompt
            prompt = request.prompt
            if request.system_prompt:
                prompt = f"{request.system_prompt}\n\n{prompt}"
            if request.context:
                context_str = json.dumps(request.context, indent=2)
                prompt = f"Context: {context_str}\n\n{prompt}"
            
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        max_output_tokens=request.max_tokens or 4096,
                        temperature=request.temperature or 0.7,
                    )
                )
            )
            
            content = response.text if response.text else "No response generated"
            
            return {
                'content': content,
                'tokens_used': len(content.split()) * 1.3,  # Approximate token count
                'confidence_score': 0.85,
                'metadata': {
                    'model': model_name,
                    'provider': 'google_gemini',
                    'cost': 0.0  # Free tier
                }
            }
            
        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
            raise
    
    async def _process_openrouter(self, request: LLMRequest, provider: LLMProvider) -> Dict[str, Any]:
        """Process request with OpenRouter"""
        try:
            config = self.provider_configs[provider]
            
            # Prepare messages
            messages = [
                {"role": "system", "content": request.system_prompt or "You are a helpful AI assistant for trading analysis."},
                {"role": "user", "content": request.prompt}
            ]
            
            if request.context:
                context_message = f"Context: {json.dumps(request.context, indent=2)}"
                messages.insert(-1, {"role": "user", "content": context_message})
            
            # Make API call to OpenRouter
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{config.endpoint}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://cival-trading-platform.com",
                        "X-Title": "Cival Trading Platform"
                    },
                    json={
                        "model": config.model_name,
                        "messages": messages,
                        "max_tokens": request.max_tokens or config.max_tokens,
                        "temperature": request.temperature or config.temperature,
                        "top_p": 1,
                        "frequency_penalty": 0,
                        "presence_penalty": 0
                    },
                    timeout=config.timeout
                )
                
                if response.status_code != 200:
                    raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
                
                result = response.json()
                
                if 'choices' not in result or not result['choices']:
                    raise Exception("No response from OpenRouter")
                
                content = result['choices'][0]['message']['content']
                tokens_used = result.get('usage', {}).get('total_tokens', 0)
                
                return {
                    'content': content,
                    'tokens_used': tokens_used,
                    'confidence_score': 0.9,
                    'metadata': {
                        'model': config.model_name,
                        'provider': 'openrouter',
                        'cost': tokens_used * config.cost_per_token,
                        'usage': result.get('usage', {})
                    }
                }
                
        except Exception as e:
            logger.error(f"OpenRouter processing failed for {provider}: {e}")
            raise
    
    async def start_agent_conversation(
        self,
        conversation_id: str,
        participants: List[str],
        topic: str,
        context: Dict[str, Any]
    ) -> str:
        """Start a multi-agent conversation"""
        try:
            # Create conversation context
            conversation_context = ConversationContext(
                conversation_id=conversation_id,
                participants=participants,
                topic=topic,
                context=context,
                created_at=datetime.now(timezone.utc)
            )
            
            self.conversation_contexts[conversation_id] = conversation_context
            self.active_conversations[conversation_id] = []
            
            # Generate opening message
            opening_prompt = f"""
            You are facilitating a conversation between trading agents on the topic: {topic}
            
            Participants: {', '.join([self.agent_personalities.get(p, AgentPersonality(agent_id=p, name=p, role='Unknown', trading_style='', risk_tolerance=0.5, communication_style='', expertise_areas=[], personality_traits={}, system_prompt='')).name for p in participants])}
            
            Context: {json.dumps(context, indent=2)}
            
            Generate an opening statement that sets the stage for productive discussion.
            """
            
            request = LLMRequest(
                request_id=f"conversation_start_{conversation_id}",
                task_type=LLMTaskType.AGENT_COMMUNICATION,
                prompt=opening_prompt,
                context=context
            )
            
            response = await self.process_llm_request(request)
            
            # Create opening message
            opening_message = ConversationMessage(
                message_id=f"msg_{conversation_id}_000",
                sender_id="system",
                recipient_id="all",
                content=response.content,
                message_type="conversation_start",
                timestamp=datetime.now(timezone.utc),
                context=context
            )
            
            self.active_conversations[conversation_id].append(opening_message)
            
            # Emit event
            if self.event_service:
                await self.event_service.emit_event({
                    'event_type': 'conversation.started',
                    'conversation_id': conversation_id,
                    'participants': participants,
                    'topic': topic,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            logger.info(f"Started conversation {conversation_id} with {len(participants)} participants")
            return conversation_id
            
        except Exception as e:
            logger.error(f"Failed to start agent conversation: {e}")
            raise
    
    async def send_agent_message(
        self,
        conversation_id: str,
        sender_id: str,
        content: str,
        message_type: str = "discussion",
        context: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """Send a message in an agent conversation"""
        try:
            if conversation_id not in self.active_conversations:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Get agent personality
            personality = self.agent_personalities.get(sender_id)
            if personality:
                # Enhance message with agent personality
                enhanced_prompt = f"""
                {personality.system_prompt}
                
                Current conversation context: {self.conversation_contexts[conversation_id].topic}
                
                Recent messages: {json.dumps([msg.content for msg in self.active_conversations[conversation_id][-3:]], indent=2)}
                
                Your message content: {content}
                
                Respond in character as {personality.name}, keeping your {personality.communication_style} style 
                and expertise in {', '.join(personality.expertise_areas)}.
                """
                
                request = LLMRequest(
                    request_id=f"agent_msg_{sender_id}_{len(self.active_conversations[conversation_id])}",
                    task_type=LLMTaskType.AGENT_COMMUNICATION,
                    prompt=enhanced_prompt,
                    context=context or {},
                    system_prompt=personality.system_prompt
                )
                
                response = await self.process_llm_request(request)
                enhanced_content = response.content
            else:
                enhanced_content = content
            
            # Create message
            message = ConversationMessage(
                message_id=f"msg_{conversation_id}_{len(self.active_conversations[conversation_id]):03d}",
                sender_id=sender_id,
                recipient_id="all",
                content=enhanced_content,
                message_type=message_type,
                timestamp=datetime.now(timezone.utc),
                context=context or {}
            )
            
            # Add to conversation
            self.active_conversations[conversation_id].append(message)
            
            # Emit event
            if self.event_service:
                await self.event_service.emit_event({
                    'event_type': 'conversation.message_sent',
                    'conversation_id': conversation_id,
                    'sender_id': sender_id,
                    'message_id': message.message_id,
                    'message_type': message_type,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to send agent message: {e}")
            raise
    
    async def generate_trading_analysis(
        self,
        market_data: Dict[str, Any],
        portfolio_data: Dict[str, Any],
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive trading analysis using LLM"""
        try:
            # Get agent personality if specified
            personality = self.agent_personalities.get(agent_id) if agent_id else None
            
            analysis_prompt = f"""
            Analyze the current market conditions and provide trading recommendations.
            
            Market Data:
            {json.dumps(market_data, indent=2)}
            
            Portfolio Data:
            {json.dumps(portfolio_data, indent=2)}
            
            Provide analysis in the following format:
            1. Market Overview
            2. Key Opportunities
            3. Risk Assessment
            4. Specific Recommendations
            5. Position Sizing Suggestions
            
            Be specific and actionable in your recommendations.
            """
            
            request = LLMRequest(
                request_id=f"trading_analysis_{agent_id}_{int(datetime.now().timestamp())}",
                task_type=LLMTaskType.MARKET_ANALYSIS,
                prompt=analysis_prompt,
                context={
                    'market_data': market_data,
                    'portfolio_data': portfolio_data,
                    'agent_id': agent_id
                },
                system_prompt=personality.system_prompt if personality else None
            )
            
            response = await self.process_llm_request(request)
            
            return {
                'analysis': response.content,
                'confidence': response.confidence_score,
                'agent_id': agent_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'tokens_used': response.tokens_used
            }
            
        except Exception as e:
            logger.error(f"Failed to generate trading analysis: {e}")
            raise
    
    async def _generate_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for request"""
        content = f"{request.task_type.value}:{request.prompt}:{json.dumps(request.context, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _get_cached_response(self, cache_key: str) -> Optional[LLMResponse]:
        """Get cached response if available"""
        try:
            if self.redis:
                cached_data = await self.redis.get(f"llm_cache:{cache_key}")
                if cached_data:
                    data = json.loads(cached_data)
                    return LLMResponse(**data)
            
            return self.response_cache.get(cache_key)
            
        except Exception as e:
            logger.error(f"Failed to get cached response: {e}")
            return None
    
    async def _cache_response(self, cache_key: str, response: LLMResponse):
        """Cache response"""
        try:
            response_data = asdict(response)
            response_data['timestamp'] = response.timestamp.isoformat()
            
            if self.redis:
                await self.redis.setex(
                    f"llm_cache:{cache_key}",
                    self.cache_ttl,
                    json.dumps(response_data, default=str)
                )
            
            # Also cache in memory
            self.response_cache[cache_key] = response
            
        except Exception as e:
            logger.error(f"Failed to cache response: {e}")
    
    async def _track_usage(self, provider: LLMProvider, request: LLMRequest, response: LLMResponse):
        """Track usage statistics"""
        try:
            # Update token usage
            self.token_usage[provider.value] = self.token_usage.get(provider.value, 0) + response.tokens_used
            
            # Update cost tracking
            config = self.provider_configs.get(provider)
            if config:
                cost = response.tokens_used * config.cost_per_token
                self.cost_tracking[provider.value] = self.cost_tracking.get(provider.value, 0.0) + cost
            
            # Update performance metrics
            if provider not in self.provider_performance:
                self.provider_performance[provider] = {
                    'total_requests': 0,
                    'total_tokens': 0,
                    'avg_response_time': 0.0,
                    'error_rate': 0.0
                }
            
            perf = self.provider_performance[provider]
            perf['total_requests'] += 1
            perf['total_tokens'] += response.tokens_used
            perf['avg_response_time'] = (
                (perf['avg_response_time'] * (perf['total_requests'] - 1) + response.processing_time) /
                perf['total_requests']
            )
            
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
    
    async def _conversation_manager(self):
        """Background task for managing conversations"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Clean up old conversations
                current_time = datetime.now(timezone.utc)
                conversations_to_remove = []
                
                for conv_id, context in self.conversation_contexts.items():
                    if (current_time - context.created_at).total_seconds() > 3600:  # 1 hour
                        conversations_to_remove.append(conv_id)
                
                for conv_id in conversations_to_remove:
                    del self.conversation_contexts[conv_id]
                    del self.active_conversations[conv_id]
                    logger.info(f"Cleaned up conversation {conv_id}")
                
            except Exception as e:
                logger.error(f"Error in conversation manager: {e}")
    
    async def _performance_monitor(self):
        """Background task for monitoring provider performance"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Log performance metrics
                for provider, metrics in self.provider_performance.items():
                    logger.info(
                        f"Provider {provider.value}: "
                        f"{metrics['total_requests']} requests, "
                        f"{metrics['total_tokens']} tokens, "
                        f"{metrics['avg_response_time']:.2f}s avg response time"
                    )
                
                # Log cost metrics
                total_cost = sum(self.cost_tracking.values())
                logger.info(f"Total LLM costs: ${total_cost:.4f}")
                
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
    
    async def _cache_cleanup(self):
        """Background task for cache cleanup"""
        while True:
            try:
                await asyncio.sleep(600)  # Check every 10 minutes
                
                # Clean up in-memory cache
                current_time = datetime.now(timezone.utc)
                keys_to_remove = []
                
                for key, response in self.response_cache.items():
                    if (current_time - response.timestamp).total_seconds() > self.cache_ttl:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.response_cache[key]
                
                logger.info(f"Cleaned up {len(keys_to_remove)} cache entries")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and health metrics"""
        return {
            "service": "llm_integration_service",
            "status": "running",
            "providers": list(self.providers.keys()),
            "active_conversations": len(self.active_conversations),
            "agent_personalities": len(self.agent_personalities),
            "total_token_usage": sum(self.token_usage.values()),
            "total_costs": sum(self.cost_tracking.values()),
            "cache_size": len(self.response_cache),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_llm_integration_service():
    """Factory function to create LLMIntegrationService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    
    service = LLMIntegrationService(redis_client)
    return service