"""
Eliza AI Integration Service - Phase 16
Advanced AI assistant integration for conversational trading intelligence
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

import redis.asyncio as redis
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class ConversationMode(Enum):
    TRADING_ASSISTANT = "trading_assistant"
    MARKET_ANALYSIS = "market_analysis"
    STRATEGY_ADVISOR = "strategy_advisor"
    RISK_COUNSELOR = "risk_counselor"
    EDUCATION_TUTOR = "education_tutor"
    GENERAL_CHAT = "general_chat"

class MessageType(Enum):
    USER_QUERY = "user_query"
    AI_RESPONSE = "ai_response"
    SYSTEM_UPDATE = "system_update"
    TRADE_SUGGESTION = "trade_suggestion"
    RISK_ALERT = "risk_alert"
    MARKET_INSIGHT = "market_insight"

class ElizaPersonality(Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    ANALYTICAL = "analytical"
    CAUTIOUS = "cautious"
    AGGRESSIVE = "aggressive"
    EDUCATIONAL = "educational"

@dataclass
class ConversationMessage:
    """Individual conversation message"""
    message_id: str
    conversation_id: str
    message_type: MessageType
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    confidence_score: Optional[float] = None

@dataclass
class ConversationSession:
    """Conversation session context"""
    session_id: str
    user_id: str
    mode: ConversationMode
    personality: ElizaPersonality
    context: Dict[str, Any]
    message_history: List[ConversationMessage]
    created_at: datetime
    last_activity: datetime
    is_active: bool

@dataclass
class AIInsight:
    """AI-generated insight or suggestion"""
    insight_id: str
    category: str
    title: str
    content: str
    confidence: float
    supporting_data: Dict[str, Any]
    recommended_actions: List[str]
    risk_level: str
    created_at: datetime

class ElizaAIIntegrationService:
    """
    Comprehensive Eliza AI integration for trading intelligence
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # Conversation management
        self.active_sessions: Dict[str, ConversationSession] = {}
        self.conversation_context: Dict[str, Dict[str, Any]] = {}
        
        # AI capabilities
        self.ai_models = {
            "conversation": "gpt-4-turbo",
            "analysis": "claude-3-opus", 
            "strategy": "gpt-4",
            "risk": "claude-3-sonnet"
        }
        
        # Personality configurations
        self.personality_configs = {
            ElizaPersonality.PROFESSIONAL: {
                "tone": "formal, precise, data-driven",
                "response_style": "structured, analytical",
                "risk_tolerance": "moderate",
                "communication_style": "direct, factual"
            },
            ElizaPersonality.FRIENDLY: {
                "tone": "warm, approachable, encouraging",
                "response_style": "conversational, supportive",
                "risk_tolerance": "moderate",
                "communication_style": "empathetic, patient"
            },
            ElizaPersonality.ANALYTICAL: {
                "tone": "technical, detailed, precise",
                "response_style": "deep analysis, data-heavy",
                "risk_tolerance": "conservative",
                "communication_style": "methodical, thorough"
            },
            ElizaPersonality.CAUTIOUS: {
                "tone": "careful, risk-aware, measured",
                "response_style": "conservative recommendations",
                "risk_tolerance": "low", 
                "communication_style": "warning-focused, protective"
            },
            ElizaPersonality.AGGRESSIVE: {
                "tone": "confident, action-oriented, bold",
                "response_style": "decisive recommendations",
                "risk_tolerance": "high",
                "communication_style": "assertive, opportunity-focused"
            },
            ElizaPersonality.EDUCATIONAL: {
                "tone": "teaching, explanatory, patient",
                "response_style": "step-by-step explanations",
                "risk_tolerance": "moderate",
                "communication_style": "instructional, encouraging"
            }
        }
        
        # Initialize mock data
        self._initialize_mock_data()
        
        logger.info("ElizaAIIntegrationService initialized")
    
    def _initialize_mock_data(self):
        """Initialize with mock conversation data"""
        # Create sample conversation sessions
        mock_sessions = [
            {
                "user_id": "user_1",
                "mode": ConversationMode.TRADING_ASSISTANT,
                "personality": ElizaPersonality.PROFESSIONAL,
                "context": {
                    "portfolio_value": 125000,
                    "risk_tolerance": "moderate",
                    "trading_experience": "intermediate",
                    "preferred_assets": ["BTC", "ETH", "SPY"]
                }
            },
            {
                "user_id": "user_2", 
                "mode": ConversationMode.MARKET_ANALYSIS,
                "personality": ElizaPersonality.ANALYTICAL,
                "context": {
                    "focus_markets": ["crypto", "stocks"],
                    "analysis_timeframe": "daily",
                    "notification_preferences": ["significant_moves", "pattern_alerts"]
                }
            }
        ]
        
        for i, session_data in enumerate(mock_sessions):
            session_id = f"session_{i+1}"
            session = ConversationSession(
                session_id=session_id,
                user_id=session_data["user_id"],
                mode=session_data["mode"],
                personality=session_data["personality"],
                context=session_data["context"],
                message_history=[],
                created_at=datetime.now(timezone.utc) - timedelta(hours=i*2),
                last_activity=datetime.now(timezone.utc) - timedelta(minutes=i*10),
                is_active=True
            )
            self.active_sessions[session_id] = session
            
            # Add some mock message history
            mock_messages = self._generate_mock_conversation(session_id, session_data["mode"])
            session.message_history.extend(mock_messages)

    def _generate_mock_conversation(self, session_id: str, mode: ConversationMode) -> List[ConversationMessage]:
        """Generate mock conversation history"""
        messages = []
        
        if mode == ConversationMode.TRADING_ASSISTANT:
            mock_exchanges = [
                ("Hello! Can you help me analyze my portfolio performance?", "Hello! I'd be happy to help analyze your portfolio. Based on your current holdings, I can see you have a well-diversified mix of crypto and traditional assets. Your portfolio has gained 8.4% this month, outperforming the market. Would you like me to dive deeper into any specific positions?"),
                ("What's your take on Bitcoin's recent price action?", "Bitcoin has shown strong momentum recently, breaking above the $67,000 resistance level with good volume confirmation. The technical indicators suggest continued upward potential, but I'd recommend watching for profit-taking around $70,000. Given your moderate risk tolerance, consider taking partial profits if we reach that level."),
                ("Should I increase my crypto allocation?", "Based on your current 30% crypto allocation and moderate risk profile, I'd suggest being cautious about increasing exposure significantly. The crypto market remains volatile. If you're comfortable with the risk, a gradual increase to 35% could be reasonable, but ensure you maintain proper diversification across assets.")
            ]
        elif mode == ConversationMode.MARKET_ANALYSIS:
            mock_exchanges = [
                ("What are the key market trends today?", "Today's market is showing mixed signals. Crypto markets are up 3.2% led by BTC and ETH strength, while traditional markets are slightly down due to inflation concerns. Key levels to watch: BTC $67,500 resistance, SPY $545 support. Volume patterns suggest institutional accumulation in crypto."),
                ("Any pattern alerts for me?", "I've detected a bull flag formation completing on ETH/USD on the 4-hour chart. Price target suggests potential move to $4,200. Also seeing a descending triangle on SPY that could resolve either direction - watch for breakout confirmation above $547 or breakdown below $540."),
                ("What's driving the market sentiment?", "Current sentiment is cautiously optimistic. Key drivers include: 1) Improving inflation data, 2) Strong corporate earnings, 3) Increasing institutional crypto adoption. However, geopolitical tensions and Fed policy uncertainty remain headwinds. The fear/greed index is at 72 (greed territory).")
            ]
        else:
            mock_exchanges = [
                ("Hi there!", "Hello! I'm here to help with your trading and investment questions. How can I assist you today?"),
                ("Thanks for your help!", "You're very welcome! I'm always here when you need insights or analysis. Feel free to ask anytime!")
            ]
        
        for i, (user_msg, ai_msg) in enumerate(mock_exchanges):
            # User message
            user_message = ConversationMessage(
                message_id=f"{session_id}_msg_{i*2+1}",
                conversation_id=session_id,
                message_type=MessageType.USER_QUERY,
                content=user_msg,
                metadata={"source": "user_input"},
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=(len(mock_exchanges)-i)*5),
                user_id="user_1"
            )
            messages.append(user_message)
            
            # AI response
            ai_message = ConversationMessage(
                message_id=f"{session_id}_msg_{i*2+2}",
                conversation_id=session_id,
                message_type=MessageType.AI_RESPONSE,
                content=ai_msg,
                metadata={
                    "model": "gpt-4-turbo",
                    "processing_time_ms": 1200 + i*200,
                    "confidence": 0.87 + i*0.03
                },
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=(len(mock_exchanges)-i)*5-1),
                confidence_score=0.87 + i*0.03
            )
            messages.append(ai_message)
        
        return messages

    async def initialize(self):
        """Initialize the Eliza AI integration service"""
        try:
            # Load conversation history from database if available
            await self._load_conversation_data()
            
            # Start background processing
            asyncio.create_task(self._conversation_monitoring_loop())
            asyncio.create_task(self._insight_generation_loop())
            asyncio.create_task(self._context_refresh_loop())
            
            logger.info("ElizaAIIntegrationService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ElizaAIIntegrationService: {e}")
            pass  # Continue with mock data

    async def start_conversation(self, 
                                user_id: str,
                                mode: ConversationMode = ConversationMode.TRADING_ASSISTANT,
                                personality: ElizaPersonality = ElizaPersonality.PROFESSIONAL,
                                context: Dict[str, Any] = None) -> ConversationSession:
        """Start a new conversation session"""
        try:
            session_id = str(uuid.uuid4())
            
            session = ConversationSession(
                session_id=session_id,
                user_id=user_id,
                mode=mode,
                personality=personality,
                context=context or {},
                message_history=[],
                created_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                is_active=True
            )
            
            self.active_sessions[session_id] = session
            
            # Generate welcome message
            welcome_message = await self._generate_welcome_message(session)
            session.message_history.append(welcome_message)
            
            # Save to database if available
            if self.supabase:
                session_dict = asdict(session)
                session_dict["mode"] = session.mode.value
                session_dict["personality"] = session.personality.value
                session_dict["created_at"] = session.created_at.isoformat()
                session_dict["last_activity"] = session.last_activity.isoformat()
                
                self.supabase.table('conversation_sessions').insert(session_dict).execute()
            
            logger.info(f"Started conversation session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            raise

    async def send_message(self, 
                          session_id: str,
                          message: str,
                          user_id: str,
                          message_type: MessageType = MessageType.USER_QUERY) -> ConversationMessage:
        """Send a message in a conversation"""
        try:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            
            # Create user message
            user_message = ConversationMessage(
                message_id=str(uuid.uuid4()),
                conversation_id=session_id,
                message_type=message_type,
                content=message,
                metadata={"source": "user_input"},
                timestamp=datetime.now(timezone.utc),
                user_id=user_id
            )
            
            session.message_history.append(user_message)
            session.last_activity = datetime.now(timezone.utc)
            
            # Generate AI response
            ai_response = await self._generate_ai_response(session, user_message)
            session.message_history.append(ai_response)
            
            # Update conversation context
            await self._update_conversation_context(session, user_message, ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def get_conversation_history(self, session_id: str) -> List[ConversationMessage]:
        """Get conversation message history"""
        try:
            if session_id not in self.active_sessions:
                return []
            
            return self.active_sessions[session_id].message_history
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    async def get_ai_insights(self, 
                            categories: List[str] = None,
                            limit: int = 10) -> List[AIInsight]:
        """Get AI-generated insights and recommendations"""
        try:
            # Generate mock insights
            mock_insights = [
                {
                    "category": "market_analysis",
                    "title": "Bitcoin Bullish Momentum Continuation",
                    "content": "Technical analysis indicates Bitcoin is forming a bull flag pattern on the 4-hour chart. The pattern suggests potential upside to $72,000 level. Volume profile shows strong support at current levels with institutional accumulation patterns visible.",
                    "confidence": 0.84,
                    "supporting_data": {
                        "price_target": 72000,
                        "probability": 0.74,
                        "timeframe": "5-7 days",
                        "indicators": ["bull_flag", "volume_profile", "rsi_divergence"]
                    },
                    "recommended_actions": [
                        "Consider long position with tight stop-loss",
                        "Monitor volume confirmation on breakout",
                        "Set profit targets at $70K and $72K"
                    ],
                    "risk_level": "medium"
                },
                {
                    "category": "portfolio_optimization",
                    "title": "Rebalancing Opportunity Detected",
                    "content": "Your portfolio allocation has drifted from target weights due to crypto outperformance. Current allocation: 35% crypto (target: 30%), 45% stocks (target: 50%), 20% bonds (target: 20%). Consider rebalancing to lock in gains and maintain risk profile.",
                    "confidence": 0.91,
                    "supporting_data": {
                        "current_allocation": {"crypto": 35, "stocks": 45, "bonds": 20},
                        "target_allocation": {"crypto": 30, "stocks": 50, "bonds": 20},
                        "drift_percentage": 8.3,
                        "last_rebalance": "45 days ago"
                    },
                    "recommended_actions": [
                        "Sell 5% of crypto positions",
                        "Increase stock allocation by 5%",
                        "Consider tax implications of rebalancing"
                    ],
                    "risk_level": "low"
                },
                {
                    "category": "risk_management",
                    "title": "Correlation Risk Alert",
                    "content": "Detected increased correlation between your tech stock and crypto holdings (correlation: 0.78, up from 0.45 last month). This reduces diversification benefits and increases portfolio risk during market stress events.",
                    "confidence": 0.89,
                    "supporting_data": {
                        "current_correlation": 0.78,
                        "historical_correlation": 0.45,
                        "affected_positions": ["ARKK", "NVDA", "BTC", "ETH"],
                        "risk_increase": "23%"
                    },
                    "recommended_actions": [
                        "Consider reducing exposure to growth tech",
                        "Add defensive positions (utilities, healthcare)",
                        "Monitor correlation metrics weekly"
                    ],
                    "risk_level": "medium"
                },
                {
                    "category": "trading_opportunity",
                    "title": "Ethereum Layer 2 Momentum",
                    "content": "Layer 2 solutions showing strong adoption metrics with 40% increase in transaction volume. Arbitrum and Optimism TVL growing rapidly. This could drive Ethereum price appreciation as network usage increases.",
                    "confidence": 0.76,
                    "supporting_data": {
                        "l2_volume_growth": 0.40,
                        "tvl_increase": "67%",
                        "top_protocols": ["Arbitrum", "Optimism", "Polygon"],
                        "eth_price_correlation": 0.65
                    },
                    "recommended_actions": [
                        "Consider ETH long position",
                        "Research L2 token opportunities",
                        "Monitor gas fee trends"
                    ],
                    "risk_level": "medium"
                },
                {
                    "category": "education",
                    "title": "Options Strategy Educational Content",
                    "content": "Based on your trading patterns, you might benefit from learning about covered call strategies. Your large stock positions could generate additional income through systematic covered call writing, especially in sideways markets.",
                    "confidence": 0.82,
                    "supporting_data": {
                        "suitable_positions": ["SPY", "AAPL", "MSFT"],
                        "potential_income": "2-4% monthly",
                        "risk_level": "low",
                        "market_conditions": "neutral_to_bullish"
                    },
                    "recommended_actions": [
                        "Study covered call basics",
                        "Practice with paper trading",
                        "Start with single position"
                    ],
                    "risk_level": "low"
                }
            ]
            
            insights = []
            for i, insight_data in enumerate(mock_insights):
                if categories and insight_data["category"] not in categories:
                    continue
                    
                insight = AIInsight(
                    insight_id=f"insight_{i+1}",
                    category=insight_data["category"],
                    title=insight_data["title"],
                    content=insight_data["content"],
                    confidence=insight_data["confidence"],
                    supporting_data=insight_data["supporting_data"],
                    recommended_actions=insight_data["recommended_actions"],
                    risk_level=insight_data["risk_level"],
                    created_at=datetime.now(timezone.utc) - timedelta(hours=i)
                )
                insights.append(insight)
            
            return insights[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get AI insights: {e}")
            return []

    async def get_conversation_analytics(self) -> Dict[str, Any]:
        """Get analytics about conversations and AI performance"""
        try:
            total_sessions = len(self.active_sessions)
            active_sessions = sum(1 for s in self.active_sessions.values() if s.is_active)
            
            # Mode distribution
            mode_distribution = {}
            for session in self.active_sessions.values():
                mode = session.mode.value
                mode_distribution[mode] = mode_distribution.get(mode, 0) + 1
            
            # Personality distribution 
            personality_distribution = {}
            for session in self.active_sessions.values():
                personality = session.personality.value
                personality_distribution[personality] = personality_distribution.get(personality, 0) + 1
            
            # Message statistics
            total_messages = sum(len(s.message_history) for s in self.active_sessions.values())
            ai_messages = sum(1 for s in self.active_sessions.values() 
                            for m in s.message_history if m.message_type == MessageType.AI_RESPONSE)
            user_messages = total_messages - ai_messages
            
            # Average confidence scores
            confidence_scores = [m.confidence_score for s in self.active_sessions.values() 
                               for m in s.message_history 
                               if m.confidence_score is not None]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            return {
                "conversation_metrics": {
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "total_messages": total_messages,
                    "user_messages": user_messages,
                    "ai_messages": ai_messages,
                    "average_confidence": round(avg_confidence, 3)
                },
                "mode_distribution": mode_distribution,
                "personality_distribution": personality_distribution,
                "engagement_metrics": {
                    "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
                    "avg_session_duration_minutes": 45.7,  # Mock
                    "user_satisfaction_score": 4.2,  # Mock
                    "response_time_ms": 1247  # Mock
                },
                "ai_performance": {
                    "response_accuracy": 0.89,
                    "user_feedback_positive": 0.86,
                    "knowledge_coverage": 0.92,
                    "conversation_completion_rate": 0.78
                },
                "popular_topics": [
                    {"topic": "Bitcoin Analysis", "frequency": 45},
                    {"topic": "Portfolio Review", "frequency": 38},
                    {"topic": "Risk Assessment", "frequency": 29}, 
                    {"topic": "Strategy Optimization", "frequency": 22},
                    {"topic": "Market Outlook", "frequency": 18}
                ],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation analytics: {e}")
            return {}

    async def _generate_welcome_message(self, session: ConversationSession) -> ConversationMessage:
        """Generate a welcome message for new sessions"""
        personality_config = self.personality_configs[session.personality]
        
        welcome_content = {
            ConversationMode.TRADING_ASSISTANT: f"Hello! I'm your AI trading assistant. I'm here to help you analyze markets, review your portfolio, and make informed trading decisions. Based on your profile, I can see you have {session.context.get('trading_experience', 'some')} trading experience. How can I help you today?",
            ConversationMode.MARKET_ANALYSIS: f"Welcome to market analysis mode! I'll help you stay on top of market trends, identify opportunities, and understand what's driving price movements. I can analyze technical patterns, sentiment, and provide real-time market insights. What would you like to explore?",
            ConversationMode.STRATEGY_ADVISOR: f"I'm your strategy advisor, ready to help optimize your trading approach. Whether you want to refine existing strategies or explore new ones, I can provide data-driven recommendations tailored to your risk profile. What's your current focus?",
            ConversationMode.RISK_COUNSELOR: f"As your risk counselor, I'm here to help you understand and manage portfolio risk. I can analyze your exposure, identify potential risks, and suggest protective measures. Let's ensure your portfolio is properly positioned. How can I assist?",
            ConversationMode.EDUCATION_TUTOR: f"Welcome to your personal trading education session! I'm here to explain concepts, answer questions, and help you build stronger trading knowledge. Whether you're a beginner or looking to advance your skills, I'll adapt to your learning pace. What would you like to learn about?",
            ConversationMode.GENERAL_CHAT: f"Hello! I'm here to chat about markets, trading, and investing. Feel free to ask me anything - from basic concepts to advanced strategies. I'll do my best to provide helpful, accurate information. What's on your mind?"
        }
        
        content = welcome_content.get(session.mode, "Hello! How can I help you today?")
        
        return ConversationMessage(
            message_id=str(uuid.uuid4()),
            conversation_id=session.session_id,
            message_type=MessageType.AI_RESPONSE,
            content=content,
            metadata={
                "type": "welcome_message",
                "personality": session.personality.value,
                "mode": session.mode.value
            },
            timestamp=datetime.now(timezone.utc),
            confidence_score=1.0
        )

    async def _generate_ai_response(self, 
                                  session: ConversationSession, 
                                  user_message: ConversationMessage) -> ConversationMessage:
        """Generate AI response to user message"""
        # Mock AI response generation
        response_templates = {
            ConversationMode.TRADING_ASSISTANT: [
                "Based on current market conditions and your portfolio, I recommend focusing on {analysis}. The risk-reward ratio looks favorable for {opportunity}.",
                "Looking at the technical indicators, {symbol} is showing {pattern}. Given your risk tolerance, consider {recommendation}.",
                "Your portfolio performance has been {performance}. I suggest {suggestion} to optimize your allocation."
            ],
            ConversationMode.MARKET_ANALYSIS: [
                "The market is currently showing {trend} with key resistance at {level}. Volume patterns suggest {outlook}.",
                "I'm seeing {pattern} formation on {timeframe} which typically indicates {prediction}. Key levels to watch: {levels}.",
                "Market sentiment is {sentiment} driven by {factors}. This creates {opportunity_type} opportunities in {sectors}."
            ],
            ConversationMode.STRATEGY_ADVISOR: [
                "For your trading style, I recommend implementing {strategy} with {parameters}. This approach has shown {performance} in similar market conditions.",
                "Based on your historical performance, consider adjusting {aspect} to improve {metric}. The expected improvement is {estimate}.",
                "Your current strategy is performing {assessment}. To enhance results, focus on {enhancement} and monitor {indicators}."
            ]
        }
        
        templates = response_templates.get(session.mode, ["I understand your question. Let me analyze this and provide a helpful response."])
        template = templates[hash(user_message.content) % len(templates)]
        
        # Fill template with contextual data
        response_content = template.format(
            analysis="strong momentum patterns",
            opportunity="BTC long position",
            symbol="BTCUSD",
            pattern="bullish flag formation",
            recommendation="a small position with tight stops",
            performance="solid with 8.4% gains",
            suggestion="rebalancing your crypto allocation",
            trend="mixed signals",
            level="$67,500",
            outlook="continued volatility",
            timeframe="4-hour chart", 
            prediction="upward breakout",
            levels="$67,500 resistance, $65,000 support",
            sentiment="cautiously optimistic",
            factors="improving fundamentals and technical strength",
            opportunity_type="swing trading",
            sectors="technology and crypto",
            strategy="momentum trading with RSI confirmation",
            parameters="14-period RSI and volume filters",
            aspect="position sizing",
            metric="risk-adjusted returns",
            estimate="10-15%",
            assessment="well within target parameters",
            enhancement="entry timing",
            indicators="volume and momentum divergence"
        )
        
        return ConversationMessage(
            message_id=str(uuid.uuid4()),
            conversation_id=session.session_id,
            message_type=MessageType.AI_RESPONSE,
            content=response_content,
            metadata={
                "model": self.ai_models["conversation"],
                "processing_time_ms": 1200,
                "personality": session.personality.value,
                "tokens_used": 150
            },
            timestamp=datetime.now(timezone.utc),
            confidence_score=0.87
        )

    async def _update_conversation_context(self, 
                                         session: ConversationSession,
                                         user_message: ConversationMessage,
                                         ai_response: ConversationMessage):
        """Update conversation context based on messages"""
        # Extract key topics and entities from conversation
        user_content = user_message.content.lower()
        
        # Update context based on message content
        if "bitcoin" in user_content or "btc" in user_content:
            session.context["discussed_assets"] = session.context.get("discussed_assets", [])
            if "BTC" not in session.context["discussed_assets"]:
                session.context["discussed_assets"].append("BTC")
        
        if "portfolio" in user_content:
            session.context["last_portfolio_discussion"] = datetime.now(timezone.utc).isoformat()
        
        if "risk" in user_content:
            session.context["risk_concerns"] = session.context.get("risk_concerns", 0) + 1

    async def _load_conversation_data(self):
        """Load conversation data from database"""
        try:
            if self.supabase:
                response = self.supabase.table('conversation_sessions').select('*').eq('is_active', True).execute()
                for session_data in response.data:
                    # Reconstruct session object
                    session = ConversationSession(
                        session_id=session_data["session_id"],
                        user_id=session_data["user_id"],
                        mode=ConversationMode(session_data["mode"]),
                        personality=ElizaPersonality(session_data["personality"]),
                        context=session_data["context"],
                        message_history=[],
                        created_at=datetime.fromisoformat(session_data["created_at"]),
                        last_activity=datetime.fromisoformat(session_data["last_activity"]),
                        is_active=session_data["is_active"]
                    )
                    self.active_sessions[session.session_id] = session
        except Exception as e:
            logger.warning(f"Could not load conversation data from database: {e}")

    async def _conversation_monitoring_loop(self):
        """Background conversation monitoring"""
        while True:
            try:
                await asyncio.sleep(300)  # Monitor every 5 minutes
                await self._cleanup_inactive_sessions()
                logger.debug("Conversation monitoring completed")
            except Exception as e:
                logger.error(f"Error in conversation monitoring loop: {e}")

    async def _insight_generation_loop(self):
        """Background insight generation"""
        while True:
            try:
                await asyncio.sleep(3600)  # Generate insights every hour
                await self._generate_periodic_insights()
                logger.debug("Insight generation completed")
            except Exception as e:
                logger.error(f"Error in insight generation loop: {e}")

    async def _context_refresh_loop(self):
        """Background context refresh"""
        while True:
            try:
                await asyncio.sleep(1800)  # Refresh context every 30 minutes
                await self._refresh_conversation_contexts()
                logger.debug("Context refresh completed")
            except Exception as e:
                logger.error(f"Error in context refresh loop: {e}")

    async def _cleanup_inactive_sessions(self):
        """Clean up inactive conversation sessions"""
        current_time = datetime.now(timezone.utc)
        inactive_threshold = timedelta(hours=24)
        
        for session_id, session in list(self.active_sessions.items()):
            if current_time - session.last_activity > inactive_threshold:
                session.is_active = False
                logger.info(f"Marked session {session_id} as inactive")

    async def _generate_periodic_insights(self):
        """Generate periodic AI insights"""
        # Mock periodic insight generation
        logger.debug("Generated periodic insights")

    async def _refresh_conversation_contexts(self):
        """Refresh conversation contexts with latest data"""
        # Mock context refresh
        logger.debug("Refreshed conversation contexts")

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        return {
            "service": "eliza_ai_integration_service",
            "status": "running",
            "active_sessions": len([s for s in self.active_sessions.values() if s.is_active]),
            "total_sessions": len(self.active_sessions),
            "ai_models": self.ai_models,
            "personality_types": len(self.personality_configs),
            "conversation_modes": len(ConversationMode),
            "last_update": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_eliza_ai_integration_service():
    """Factory function to create ElizaAIIntegrationService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = ElizaAIIntegrationService(redis_client, supabase_client)
    return service