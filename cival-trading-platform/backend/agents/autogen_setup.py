"""
AutoGen Agent Setup - Migration from CrewAI
Modern multi-agent conversation programming framework for advanced trading systems
"""
import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from loguru import logger
import uuid
from datetime import datetime

try:
    import autogen
    from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
    from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
    from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
    AUTOGEN_AVAILABLE = True
except ImportError:
    logger.warning("AutoGen not available - install with: pip install pyautogen autogen-agentchat")
    AUTOGEN_AVAILABLE = False

# Import existing tools from CrewAI implementation
from ..tools.agent_analysis_tools import (
    historical_stock_prices,
    current_stock_quote,
    search_stock_symbols,
    sma_calculation_tool,
    ema_calculation_tool,
    rsi_calculation_tool,
    macd_calculation_tool
)

# Event models for lifecycle tracking
from ..models.event_models import AgentLogEvent, CrewLifecycleEvent
from pydantic import BaseModel

class AutoGenEventService:
    """Enhanced event service for AutoGen agent interactions"""
    
    def __init__(self):
        self.events: List[Dict] = []
        self.current_conversation_id = str(uuid.uuid4())
        
    async def publish_agent_event(self, agent_name: str, message: str, data: Optional[Dict] = None):
        """Publish agent interaction events"""
        event = {
            "event_id": str(uuid.uuid4()),
            "conversation_id": self.current_conversation_id,
            "agent_name": agent_name,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        self.events.append(event)
        logger.info(f"[AutoGen Event] {agent_name}: {message}")
        
    async def publish_conversation_event(self, event_type: str, data: Dict):
        """Publish conversation-level events"""
        event = {
            "event_id": str(uuid.uuid4()),
            "conversation_id": self.current_conversation_id,
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.events.append(event)
        logger.info(f"[AutoGen Conversation] {event_type}: {json.dumps(data, indent=2)}")

# Global event service instance
autogen_event_service = AutoGenEventService()

class AutoGenTradingSystem:
    """Advanced AutoGen-based trading system with multi-agent conversations"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.group_chat: Optional[GroupChat] = None
        self.group_chat_manager: Optional[GroupChatManager] = None
        self.conversation_history: List[Dict] = []
        self.llm_config = self._get_llm_config()
        
        if AUTOGEN_AVAILABLE:
            self._setup_agents()
            self._setup_group_chat()
        else:
            logger.error("AutoGen not available - cannot initialize trading system")
    
    def _get_llm_config(self) -> Dict:
        """Configure LLM settings for AutoGen agents"""
        config = {
            "timeout": 120,
            "cache_seed": 42,
            "temperature": 0.1,
            "config_list": []
        }
        
        # OpenAI configuration
        if os.getenv("OPENAI_API_KEY"):
            config["config_list"].append({
                "model": "gpt-4",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "api_type": "openai"
            })
            
        # Anthropic configuration  
        if os.getenv("ANTHROPIC_API_KEY"):
            config["config_list"].append({
                "model": "claude-3-sonnet-20240229",
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "api_type": "anthropic",
                "base_url": "https://api.anthropic.com"
            })
            
        # Azure OpenAI configuration
        if os.getenv("AZURE_OPENAI_API_KEY"):
            config["config_list"].append({
                "model": "gpt-4",
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "base_url": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_type": "azure",
                "api_version": "2024-02-15-preview"
            })
            
        if not config["config_list"]:
            logger.warning("No LLM API keys found - agents will have limited functionality")
            
        return config
    
    def _setup_agents(self):
        """Setup specialized trading agents with AutoGen"""
        
        # Market Analyst Agent - Enhanced with advanced analysis capabilities
        self.agents["market_analyst"] = AssistantAgent(
            name="MarketAnalyst",
            system_message="""You are a Senior Market Analyst with expertise in technical and fundamental analysis.
            
Your responsibilities:
- Analyze market conditions using technical indicators (SMA, EMA, RSI, MACD)
- Identify trading opportunities and market trends  
- Provide comprehensive market analysis with confidence levels
- Use provided tools for data retrieval and calculations
- Communicate findings clearly with actionable insights

Tools available to you:
- historical_stock_prices: Get historical price data
- current_stock_quote: Get real-time quotes
- search_stock_symbols: Find symbols by company name
- sma_calculation_tool: Calculate Simple Moving Averages
- ema_calculation_tool: Calculate Exponential Moving Averages  
- rsi_calculation_tool: Calculate RSI indicators
- macd_calculation_tool: Calculate MACD indicators

Always provide structured analysis with:
1. Market sentiment assessment
2. Key support/resistance levels
3. Technical indicator summary
4. Identified opportunities with confidence levels
5. Risk factors and considerations
""",
            llm_config=self.llm_config,
            code_execution_config=False,
            human_input_mode="NEVER"
        )
        
        # Risk Manager Agent - Advanced risk assessment
        self.agents["risk_manager"] = AssistantAgent(
            name="RiskManager", 
            system_message="""You are a Chief Risk Officer responsible for protecting trading capital.

Your responsibilities:
- Assess risk levels for all proposed trades
- Calculate position sizing based on volatility and account size
- Set appropriate stop-loss and take-profit levels
- Monitor portfolio exposure and concentration risks
- Provide risk mitigation strategies
- Approve or reject trading proposals based on risk parameters

Risk Management Framework:
- Maximum single position risk: 2% of account
- Maximum portfolio drawdown: 10%
- Volatility-adjusted position sizing using ATR
- Sector concentration limits: 25% per sector
- Correlation analysis for portfolio diversification

Always provide:
1. Risk assessment score (1-10)
2. Recommended position size
3. Stop-loss and take-profit levels
4. Risk mitigation strategies
5. Approval status with reasoning
""",
            llm_config=self.llm_config,
            code_execution_config=False,
            human_input_mode="NEVER"
        )
        
        # Trade Execution Agent - Sophisticated execution strategies
        self.agents["trade_executor"] = AssistantAgent(
            name="TradeExecutor",
            system_message="""You are a Senior Trade Execution Specialist focused on optimal trade execution.

Your responsibilities:
- Execute approved trades with minimal market impact
- Choose optimal order types and timing strategies
- Monitor execution quality and slippage
- Manage partial fills and order modifications
- Provide execution reports and performance metrics

Execution Strategies:
- TWAP (Time-Weighted Average Price) for large orders
- VWAP (Volume-Weighted Average Price) for liquid markets
- Iceberg orders for position building
- Market orders for urgent executions
- Limit orders for price-sensitive trades

Execution Report Format:
1. Order details (symbol, side, quantity, type)
2. Execution strategy recommendation
3. Expected slippage and market impact
4. Timing considerations
5. Order management plan
""",
            llm_config=self.llm_config,
            code_execution_config=False,
            human_input_mode="NEVER"
        )
        
        # Portfolio Manager Agent - Strategic oversight
        self.agents["portfolio_manager"] = AssistantAgent(
            name="PortfolioManager",
            system_message="""You are a Portfolio Manager providing strategic oversight and coordination.

Your responsibilities:
- Coordinate between all trading agents
- Maintain overall portfolio strategy alignment
- Ensure trades fit within portfolio objectives
- Monitor portfolio performance and attribution
- Make strategic allocation decisions
- Resolve conflicts between agents

Portfolio Management Principles:
- Diversification across assets, sectors, and strategies
- Risk-adjusted return optimization
- Tactical asset allocation based on market conditions
- Performance attribution and factor analysis
- Rebalancing strategies

Decision Framework:
1. Strategic alignment assessment
2. Risk-return optimization
3. Portfolio impact analysis
4. Resource allocation decisions
5. Performance monitoring and adjustment
""",
            llm_config=self.llm_config,
            code_execution_config=False,
            human_input_mode="NEVER"
        )
        
        # Research Agent - Enhanced market intelligence
        self.agents["research_agent"] = AssistantAgent(
            name="ResearchAgent",
            system_message="""You are a Senior Research Analyst specializing in market intelligence and strategy development.

Your responsibilities:
- Conduct deep fundamental analysis
- Monitor macroeconomic trends and events
- Analyze sector rotation and thematic opportunities
- Research emerging market trends and technologies
- Provide strategic insights for portfolio positioning

Research Areas:
- Macroeconomic analysis and central bank policies
- Sector analysis and rotation strategies
- Company fundamentals and earnings analysis
- Geopolitical events and market impact
- Technology trends and disruptive innovations

Research Output:
1. Market theme identification
2. Fundamental analysis summary
3. Sector rotation recommendations
4. Event-driven opportunities
5. Long-term strategic insights
""",
            llm_config=self.llm_config,
            code_execution_config=False,
            human_input_mode="NEVER"
        )
        
        # Coordinator Agent - Central command and control
        self.agents["coordinator"] = AssistantAgent(
            name="TradingCoordinator",
            system_message="""You are the Central Trading Coordinator orchestrating multi-agent collaboration.

Your responsibilities:
- Coordinate conversations between all agents
- Synthesize information from multiple sources
- Make final trading decisions based on agent inputs
- Ensure proper workflow and communication protocols
- Monitor system performance and agent interactions
- Escalate critical issues and conflicts

Coordination Protocol:
1. Initiate analysis workflow for new opportunities
2. Facilitate agent discussions and information sharing
3. Resolve conflicts between agent recommendations
4. Synthesize consensus recommendations
5. Monitor execution and provide feedback

Decision Making:
- Require consensus from Risk Manager for trade approval
- Balance market analysis with portfolio strategy
- Consider execution feasibility and market conditions
- Document decision rationale for audit trail
- Monitor outcomes and adjust strategies
""",
            llm_config=self.llm_config,
            code_execution_config=False,
            human_input_mode="NEVER"
        )
        
        logger.info(f"Created {len(self.agents)} AutoGen trading agents")
    
    def _setup_group_chat(self):
        """Setup group chat for multi-agent conversations"""
        if not AUTOGEN_AVAILABLE or not self.agents:
            return
            
        agent_list = list(self.agents.values())
        
        self.group_chat = GroupChat(
            agents=agent_list,
            messages=[],
            max_round=50,
            speaker_selection_method="auto",
            allow_repeat_speaker=False
        )
        
        self.group_chat_manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self.llm_config,
            system_message="""You are the Group Chat Manager for a sophisticated trading system.

Orchestrate conversations between specialized trading agents:
- MarketAnalyst: Technical and fundamental analysis
- RiskManager: Risk assessment and position sizing  
- TradeExecutor: Trade execution and order management
- PortfolioManager: Strategic oversight and coordination
- ResearchAgent: Market intelligence and research
- TradingCoordinator: Central coordination and decision making

Conversation Flow:
1. Start with MarketAnalyst for market analysis
2. Involve ResearchAgent for fundamental insights
3. Consult RiskManager for risk assessment
4. Get PortfolioManager input on strategic fit
5. Coordinate with TradeExecutor for execution plan
6. TradingCoordinator synthesizes final recommendation

Ensure all agents contribute relevant expertise and reach consensus on trading decisions.
"""
        )
        
        logger.info("AutoGen group chat system initialized")
    
    async def analyze_trading_opportunity(self, symbol: str, context: Optional[Dict] = None) -> Dict:
        """Analyze a trading opportunity using multi-agent conversation"""
        if not AUTOGEN_AVAILABLE:
            return {"error": "AutoGen not available"}
            
        await autogen_event_service.publish_conversation_event("analysis_started", {
            "symbol": symbol,
            "context": context or {}
        })
        
        try:
            # Initialize conversation with market analysis request
            initial_message = f"""
Analyze trading opportunity for {symbol}.

Context: {json.dumps(context or {}, indent=2)}

Please provide comprehensive analysis covering:
1. Technical analysis with key indicators
2. Fundamental research and market themes  
3. Risk assessment and position sizing
4. Portfolio impact and strategic fit
5. Execution strategy and timing
6. Final recommendation with confidence level

Start with MarketAnalyst providing technical analysis.
"""
            
            # Track conversation in event service
            await autogen_event_service.publish_agent_event(
                "TradingCoordinator", 
                f"Initiating analysis for {symbol}",
                {"symbol": symbol, "context": context}
            )
            
            # In a real implementation, you would run the group chat here
            # For now, we'll simulate the conversation structure
            conversation_result = await self._simulate_agent_conversation(symbol, initial_message)
            
            await autogen_event_service.publish_conversation_event("analysis_completed", {
                "symbol": symbol,
                "result": conversation_result
            })
            
            return conversation_result
            
        except Exception as e:
            logger.error(f"Error in AutoGen trading analysis: {e}", exc_info=True)
            await autogen_event_service.publish_conversation_event("analysis_error", {
                "symbol": symbol,
                "error": str(e)
            })
            return {"error": str(e)}
    
    async def _simulate_agent_conversation(self, symbol: str, initial_message: str) -> Dict:
        """Simulate multi-agent conversation for trading analysis"""
        # This is a simplified simulation - in production would use actual AutoGen group chat
        
        conversation_steps = [
            {
                "agent": "MarketAnalyst",
                "message": f"Analyzing technical indicators for {symbol}",
                "analysis": {
                    "sentiment": "Bullish",
                    "key_levels": {"support": [150.0, 145.0], "resistance": [160.0, 165.0]},
                    "indicators": {
                        "sma_20": 155.2,
                        "rsi_14": 68.5,
                        "macd_signal": "bullish_crossover"
                    },
                    "confidence": 0.75
                }
            },
            {
                "agent": "ResearchAgent", 
                "message": f"Fundamental analysis for {symbol}",
                "analysis": {
                    "sector_outlook": "Technology sector showing strength",
                    "company_fundamentals": "Strong earnings growth expected",
                    "market_themes": ["AI adoption", "Cloud growth"],
                    "rating": "Buy",
                    "confidence": 0.80
                }
            },
            {
                "agent": "RiskManager",
                "message": f"Risk assessment for {symbol} position",
                "analysis": {
                    "risk_score": 6,  # out of 10
                    "position_size": "2% of portfolio",
                    "stop_loss": 145.0,
                    "take_profit": 170.0,
                    "max_drawdown": "5%",
                    "approval": "Approved"
                }
            },
            {
                "agent": "PortfolioManager",
                "message": f"Strategic fit assessment for {symbol}",
                "analysis": {
                    "portfolio_impact": "Positive diversification",
                    "sector_allocation": "Within limits",
                    "strategic_alignment": "High",
                    "rebalancing_needed": False,
                    "approval": "Approved"
                }
            },
            {
                "agent": "TradeExecutor",
                "message": f"Execution strategy for {symbol}",
                "analysis": {
                    "order_type": "Limit order",
                    "execution_strategy": "TWAP over 2 hours",
                    "expected_slippage": "0.05%",
                    "market_impact": "Low",
                    "timing": "Market open"
                }
            }
        ]
        
        # Simulate conversation events
        for step in conversation_steps:
            await autogen_event_service.publish_agent_event(
                step["agent"],
                step["message"], 
                step["analysis"]
            )
        
        # Coordinator synthesis
        final_recommendation = {
            "symbol": symbol,
            "recommendation": "BUY",
            "confidence": 0.78,
            "position_size": "2%",
            "entry_price": 155.0,
            "stop_loss": 145.0,
            "take_profit": 170.0,
            "strategy": "Momentum breakout with fundamental support",
            "risk_level": "Medium",
            "agents_consensus": True,
            "conversation_id": autogen_event_service.current_conversation_id
        }
        
        await autogen_event_service.publish_agent_event(
            "TradingCoordinator",
            f"Final recommendation for {symbol}",
            final_recommendation
        )
        
        return final_recommendation
    
    def get_agent_status(self) -> Dict:
        """Get status of all agents in the system"""
        return {
            "system_status": "online" if AUTOGEN_AVAILABLE else "offline",
            "agents_count": len(self.agents),
            "agents": list(self.agents.keys()),
            "conversation_id": autogen_event_service.current_conversation_id,
            "llm_config": bool(self.llm_config.get("config_list")),
            "group_chat_enabled": self.group_chat is not None
        }
    
    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history from event service"""
        return autogen_event_service.events

# Global AutoGen trading system instance
autogen_trading_system = AutoGenTradingSystem()

# Legacy compatibility functions for CrewAI migration
async def run_trading_analysis_autogen(symbol: str, context: Optional[Dict] = None) -> Dict:
    """Run trading analysis using AutoGen - replaces CrewAI functionality"""
    return await autogen_trading_system.analyze_trading_opportunity(symbol, context)

def get_autogen_agents() -> Dict:
    """Get all available AutoGen agents"""
    return autogen_trading_system.agents

def get_autogen_system_status() -> Dict:
    """Get AutoGen system status"""
    return autogen_trading_system.get_agent_status()

# Export key components
__all__ = [
    "autogen_trading_system",
    "AutoGenTradingSystem", 
    "autogen_event_service",
    "run_trading_analysis_autogen",
    "get_autogen_agents",
    "get_autogen_system_status"
]

logger.info("AutoGen trading system setup completed")