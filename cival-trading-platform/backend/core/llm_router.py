"""
LLM Router Service
Intelligent routing of LLM requests to optimal providers based on task complexity, cost, and performance
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass
import os

from ..services.llm_integration_service import LLMProvider, LLMTaskType

logger = logging.getLogger(__name__)

@dataclass
class RoutingDecision:
    """Result of routing decision"""
    primary_provider: LLMProvider
    fallback_provider: Optional[LLMProvider]
    reasoning: str
    estimated_cost: float
    estimated_time: float

class LLMRouter:
    """
    Intelligent LLM provider routing based on:
    - Task complexity
    - Cost optimization
    - Provider performance
    - Rate limits
    - Agent preferences
    """
    
    def __init__(self):
        self.provider_performance: Dict[LLMProvider, Dict[str, float]] = {}
        self.cost_tracking: Dict[str, float] = {}  # Daily cost tracking
        self.rate_limits: Dict[LLMProvider, Dict[str, int]] = {}
        
        # Cost optimization settings
        self.cost_optimization_enabled = os.getenv("COST_OPTIMIZATION_ENABLED", "true").lower() == "true"
        self.max_daily_cost = float(os.getenv("MAX_DAILY_LLM_COST", "50.0"))
        self.default_provider = self._parse_provider(os.getenv("DEFAULT_LLM_PROVIDER", "gemini"))
        self.high_complexity_provider = self._parse_provider(os.getenv("HIGH_COMPLEXITY_PROVIDER", "openrouter"))
        
        # Agent LLM preferences
        self.agent_llm_mapping = {
            "marcus_trend_follower": {
                "primary": LLMProvider.OPENROUTER_CLAUDE,  # Pattern analysis
                "secondary": LLMProvider.GOOGLE_GEMINI,
                "tools": LLMProvider.GEMINI_FLASH
            },
            "alex_arbitrage": {
                "primary": LLMProvider.OPENROUTER_GPT4,  # Complex calculations
                "secondary": LLMProvider.GEMINI_FLASH,
                "tools": LLMProvider.GEMINI_FLASH
            },
            "sophia_mean_reversion": {
                "primary": LLMProvider.GOOGLE_GEMINI,  # Cost-effective
                "secondary": LLMProvider.GEMINI_FLASH,
                "tools": LLMProvider.GEMINI_FLASH
            },
            "riley_risk_manager": {
                "primary": LLMProvider.GEMINI_FLASH,  # Fast decisions
                "secondary": LLMProvider.OPENROUTER_GPT4,
                "tools": LLMProvider.GEMINI_FLASH
            }
        }
        
        logger.info("LLMRouter initialized with cost optimization and agent preferences")
    
    def _parse_provider(self, provider_string: str) -> LLMProvider:
        """Parse provider string to enum"""
        provider_map = {
            "gemini": LLMProvider.GOOGLE_GEMINI,
            "gemini_flash": LLMProvider.GEMINI_FLASH,
            "openrouter": LLMProvider.OPENROUTER_GPT4,
            "openai": LLMProvider.OPENAI_GPT4,
            "claude": LLMProvider.ANTHROPIC_CLAUDE
        }
        return provider_map.get(provider_string.lower(), LLMProvider.GOOGLE_GEMINI)
    
    async def select_provider(
        self,
        task_type: LLMTaskType,
        complexity: int = 5,
        agent_id: Optional[str] = None,
        cost_budget: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> RoutingDecision:
        """
        Select optimal LLM provider based on multiple factors
        
        Args:
            task_type: Type of LLM task
            complexity: Task complexity (1-10 scale)
            agent_id: Agent making the request
            cost_budget: Available budget for this request
            context: Additional context for routing decision
        """
        try:
            # Check daily cost limits
            today = datetime.now(timezone.utc).date().isoformat()
            daily_cost = self.cost_tracking.get(today, 0.0)
            
            # Agent-specific routing
            if agent_id and agent_id in self.agent_llm_mapping:
                agent_prefs = self.agent_llm_mapping[agent_id]
                
                # For tool calling, always use fast/free model
                if task_type == LLMTaskType.AGENT_COMMUNICATION or "tool" in str(context or {}):
                    return RoutingDecision(
                        primary_provider=agent_prefs["tools"],
                        fallback_provider=LLMProvider.GOOGLE_GEMINI,
                        reasoning=f"Tool calling for agent {agent_id}",
                        estimated_cost=0.0,
                        estimated_time=2.0
                    )
                
                # For complex analysis, use agent's primary
                if complexity >= 7:
                    return RoutingDecision(
                        primary_provider=agent_prefs["primary"],
                        fallback_provider=agent_prefs["secondary"],
                        reasoning=f"High complexity task for agent {agent_id}",
                        estimated_cost=0.01,
                        estimated_time=5.0
                    )
                
                # For routine tasks, use secondary
                return RoutingDecision(
                    primary_provider=agent_prefs["secondary"],
                    fallback_provider=agent_prefs["tools"],
                    reasoning=f"Routine task for agent {agent_id}",
                    estimated_cost=0.0,
                    estimated_time=3.0
                )
            
            # Cost optimization routing
            if self.cost_optimization_enabled:
                remaining_budget = self.max_daily_cost - daily_cost
                
                # If budget is low, use free models
                if remaining_budget < 5.0 or (cost_budget and cost_budget < 0.01):
                    return RoutingDecision(
                        primary_provider=LLMProvider.GEMINI_FLASH,
                        fallback_provider=LLMProvider.GOOGLE_GEMINI,
                        reasoning="Cost optimization - using free models",
                        estimated_cost=0.0,
                        estimated_time=2.0
                    )
                
                # For high complexity, use premium models if budget allows
                if complexity >= 8 and remaining_budget > 1.0:
                    return RoutingDecision(
                        primary_provider=LLMProvider.OPENROUTER_GPT4,
                        fallback_provider=LLMProvider.OPENROUTER_CLAUDE,
                        reasoning="High complexity task with available budget",
                        estimated_cost=0.03,
                        estimated_time=8.0
                    )
            
            # Task-specific routing
            if task_type == LLMTaskType.TRADING_DECISION:
                if complexity >= 7:
                    return RoutingDecision(
                        primary_provider=LLMProvider.OPENROUTER_CLAUDE,
                        fallback_provider=LLMProvider.GOOGLE_GEMINI,
                        reasoning="Complex trading decision requires advanced reasoning",
                        estimated_cost=0.02,
                        estimated_time=6.0
                    )
                else:
                    return RoutingDecision(
                        primary_provider=LLMProvider.GOOGLE_GEMINI,
                        fallback_provider=LLMProvider.GEMINI_FLASH,
                        reasoning="Standard trading decision",
                        estimated_cost=0.0,
                        estimated_time=3.0
                    )
            
            elif task_type == LLMTaskType.MARKET_ANALYSIS:
                return RoutingDecision(
                    primary_provider=LLMProvider.OPENROUTER_LLAMA,
                    fallback_provider=LLMProvider.GOOGLE_GEMINI,
                    reasoning="Market analysis benefits from open-source models",
                    estimated_cost=0.001,
                    estimated_time=4.0
                )
            
            elif task_type == LLMTaskType.RISK_ASSESSMENT:
                return RoutingDecision(
                    primary_provider=LLMProvider.GEMINI_FLASH,
                    fallback_provider=LLMProvider.GOOGLE_GEMINI,
                    reasoning="Risk assessment needs fast response",
                    estimated_cost=0.0,
                    estimated_time=1.5
                )
            
            # Default routing
            return RoutingDecision(
                primary_provider=self.default_provider,
                fallback_provider=LLMProvider.GEMINI_FLASH,
                reasoning="Default routing",
                estimated_cost=0.0,
                estimated_time=3.0
            )
            
        except Exception as e:
            logger.error(f"Provider selection failed: {e}")
            # Safe fallback
            return RoutingDecision(
                primary_provider=LLMProvider.GEMINI_FLASH,
                fallback_provider=LLMProvider.GOOGLE_GEMINI,
                reasoning="Fallback due to routing error",
                estimated_cost=0.0,
                estimated_time=3.0
            )
    
    async def update_performance(
        self,
        provider: LLMProvider,
        response_time: float,
        success: bool,
        cost: float
    ):
        """Update provider performance metrics"""
        if provider not in self.provider_performance:
            self.provider_performance[provider] = {
                "avg_response_time": 0.0,
                "success_rate": 1.0,
                "total_requests": 0,
                "total_cost": 0.0
            }
        
        perf = self.provider_performance[provider]
        perf["total_requests"] += 1
        perf["total_cost"] += cost
        
        # Update average response time
        perf["avg_response_time"] = (
            (perf["avg_response_time"] * (perf["total_requests"] - 1) + response_time) /
            perf["total_requests"]
        )
        
        # Update success rate
        if success:
            perf["success_rate"] = (
                (perf["success_rate"] * (perf["total_requests"] - 1) + 1.0) /
                perf["total_requests"]
            )
        else:
            perf["success_rate"] = (
                (perf["success_rate"] * (perf["total_requests"] - 1)) /
                perf["total_requests"]
            )
        
        # Track daily costs
        today = datetime.now(timezone.utc).date().isoformat()
        if today not in self.cost_tracking:
            self.cost_tracking[today] = 0.0
        self.cost_tracking[today] += cost
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary"""
        today = datetime.now(timezone.utc).date().isoformat()
        return {
            "daily_cost": self.cost_tracking.get(today, 0.0),
            "daily_limit": self.max_daily_cost,
            "remaining_budget": self.max_daily_cost - self.cost_tracking.get(today, 0.0),
            "total_tracked_days": len(self.cost_tracking),
            "provider_performance": self.provider_performance
        }
    
    def assess_complexity(self, prompt: str, task_type: LLMTaskType, context: Optional[Dict] = None) -> int:
        """
        Assess task complexity on a 1-10 scale
        """
        complexity = 5  # Base complexity
        
        # Prompt length factor
        if len(prompt) > 1000:
            complexity += 2
        elif len(prompt) > 500:
            complexity += 1
        
        # Task type factor
        complexity_map = {
            LLMTaskType.NATURAL_LANGUAGE_QUERY: 3,
            LLMTaskType.AGENT_COMMUNICATION: 4,
            LLMTaskType.MARKET_ANALYSIS: 6,
            LLMTaskType.TRADING_DECISION: 7,
            LLMTaskType.RISK_ASSESSMENT: 6,
            LLMTaskType.PORTFOLIO_OPTIMIZATION: 8,
            LLMTaskType.STRATEGY_GENERATION: 9,
            LLMTaskType.PERFORMANCE_ANALYSIS: 7
        }
        
        task_complexity = complexity_map.get(task_type, 5)
        complexity = max(complexity, task_complexity)
        
        # Context complexity
        if context:
            if len(str(context)) > 2000:
                complexity += 1
            if "historical_data" in context:
                complexity += 1
            if "multi_asset" in context:
                complexity += 1
        
        # Keywords that indicate complexity
        high_complexity_keywords = [
            "optimize", "strategy", "backtesting", "correlation", "regression",
            "machine learning", "neural network", "portfolio theory", "derivatives"
        ]
        
        prompt_lower = prompt.lower()
        for keyword in high_complexity_keywords:
            if keyword in prompt_lower:
                complexity += 1
        
        return min(max(complexity, 1), 10)  # Clamp between 1-10
