"""
Enhanced Trading Types for PydanticAI Integration
Compatible with existing civil-dashboard TypeScript types
"""
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Trading Decision Types
class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

class MarketCondition(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"

# Request/Response Models
class TradingAnalysisRequest(BaseModel):
    symbol: str = Field(description="Trading symbol (e.g., AAPL)")
    account_id: str = Field(description="Trading account identifier")
    strategy_id: Optional[str] = Field(None, description="Strategy to use")
    market_data: Dict[str, Any] = Field(description="Current market data")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class TradingDecision(BaseModel):
    action: TradeAction = Field(description="Trading action to take")
    symbol: str = Field(description="Trading symbol")
    quantity: int = Field(ge=0, description="Number of shares/units")
    price: Optional[float] = Field(None, ge=0, description="Target price")
    confidence: float = Field(ge=0, le=1, description="Confidence level 0-1")
    risk_level: RiskLevel = Field(description="Risk assessment")
    reasoning: str = Field(description="Explanation for decision")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    timeframe: str = Field(default="1h", description="Decision timeframe")

class MarketAnalysisRequest(BaseModel):
    symbols: List[str] = Field(description="List of symbols to analyze")
    timeframe: str = Field(default="1d", description="Analysis timeframe")
    indicators: List[str] = Field(default=[], description="Technical indicators")
    include_sentiment: bool = Field(default=True, description="Include sentiment analysis")
    depth: str = Field(default="standard", description="Analysis depth: basic, standard, deep")

class MarketAnalysis(BaseModel):
    symbol: str = Field(description="Analyzed symbol")
    condition: MarketCondition = Field(description="Overall market condition")
    trend_direction: str = Field(description="up, down, sideways")
    trend_strength: float = Field(ge=0, le=1, description="Trend strength 0-1")
    volatility: float = Field(ge=0, description="Volatility measure")
    support_levels: List[float] = Field(description="Support price levels")
    resistance_levels: List[float] = Field(description="Resistance price levels")
    indicators: Dict[str, float] = Field(description="Technical indicator values")
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1, description="Sentiment -1 to 1")
    news_impact: Optional[str] = Field(None, description="Recent news impact")
    forecast: str = Field(description="Short-term forecast")

class RiskAssessmentRequest(BaseModel):
    portfolio: Dict[str, float] = Field(description="Portfolio positions")
    timeframe: str = Field(default="1d", description="Risk assessment timeframe")
    confidence_level: float = Field(default=0.95, ge=0.8, le=0.99, description="VaR confidence")
    stress_scenarios: bool = Field(default=True, description="Include stress testing")

class RiskAssessment(BaseModel):
    portfolio_value: float = Field(description="Total portfolio value")
    var_95: float = Field(description="Value at Risk 95%")
    var_99: float = Field(description="Value at Risk 99%")
    expected_shortfall: float = Field(description="Expected shortfall")
    max_drawdown: float = Field(description="Maximum drawdown")
    risk_level: RiskLevel = Field(description="Overall risk level")
    diversification_ratio: float = Field(ge=0, description="Portfolio diversification")
    stress_test_results: Dict[str, float] = Field(description="Stress test outcomes")
    recommendations: List[str] = Field(description="Risk mitigation recommendations")

class VaultOptimizationRequest(BaseModel):
    vault_id: str = Field(description="Vault identifier")
    current_allocation: Dict[str, float] = Field(description="Current asset allocation")
    target_return: Optional[float] = Field(None, description="Target return rate")
    risk_tolerance: RiskLevel = Field(description="Risk tolerance level")
    defi_protocols: List[str] = Field(default=[], description="Available DeFi protocols")
    liquidity_needs: float = Field(default=0.1, ge=0, le=1, description="Liquidity requirement")

class VaultOptimization(BaseModel):
    vault_id: str = Field(description="Vault identifier")
    optimized_allocation: Dict[str, float] = Field(description="Optimized allocation")
    expected_return: float = Field(description="Expected annual return")
    expected_risk: float = Field(description="Expected risk level")
    liquidity_score: float = Field(ge=0, le=1, description="Liquidity score")
    defi_recommendations: List[Dict[str, Any]] = Field(description="DeFi protocol suggestions")
    rebalancing_actions: List[Dict[str, Any]] = Field(description="Required actions")
    cost_analysis: Dict[str, float] = Field(description="Transaction costs")

class StrategyOptimizationRequest(BaseModel):
    strategy_id: str = Field(description="Strategy identifier")
    historical_data: Dict[str, List[Dict]] = Field(description="Historical market data")
    parameters: Dict[str, float] = Field(description="Current strategy parameters")
    optimization_target: str = Field(default="sharpe_ratio", description="Optimization objective")
    backtest_period: str = Field(default="1y", description="Backtesting period")

class StrategyOptimization(BaseModel):
    strategy_id: str = Field(description="Strategy identifier")
    optimized_parameters: Dict[str, float] = Field(description="Optimized parameters")
    backtest_results: Dict[str, float] = Field(description="Backtesting performance")
    parameter_sensitivity: Dict[str, float] = Field(description="Parameter importance")
    improvement_metrics: Dict[str, float] = Field(description="Performance improvements")
    recommendations: List[str] = Field(description="Strategy recommendations")
    risk_metrics: Dict[str, float] = Field(description="Risk analysis")

# A2A Protocol Types
class A2AMessage(BaseModel):
    from_agent: str = Field(description="Source agent ID")
    to_agent: str = Field(description="Target agent ID")
    message_type: str = Field(description="Message type")
    payload: Dict[str, Any] = Field(description="Message payload")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    timestamp: datetime = Field(default_factory=datetime.now)

class A2ABroadcastRequest(BaseModel):
    message_type: str = Field(description="Broadcast message type")
    payload: Dict[str, Any] = Field(description="Broadcast payload")
    target_capabilities: Optional[List[str]] = Field(None, description="Target agent capabilities")
    priority: str = Field(default="normal", description="Message priority")

# Google SDK Integration Types
class VertexDeploymentRequest(BaseModel):
    agent_name: str = Field(description="Agent name for deployment")
    model_name: str = Field(description="Base model name")
    capabilities: List[str] = Field(description="Agent capabilities")
    resource_requirements: Dict[str, Any] = Field(description="Resource requirements")
    environment_variables: Dict[str, str] = Field(default={}, description="Environment config")

# Dependencies for PydanticAI Agents
class TradingDependencies(BaseModel):
    """Dependencies injected into PydanticAI agents"""
    google_bridge: Any = Field(description="Google SDK bridge instance")
    a2a_protocol: Any = Field(description="A2A protocol instance")
    redis_client: Any = Field(description="Redis client")
    market_data_client: Any = Field(description="Market data client")
    trading_client: Any = Field(description="Trading client")
    vault_client: Any = Field(description="Vault client")
    user_id: Optional[str] = Field(None, description="User identifier")
    account_id: Optional[str] = Field(None, description="Account identifier")

    class Config:
        arbitrary_types_allowed = True