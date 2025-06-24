#!/usr/bin/env python3
"""
Octagon Intelligence MCP Server
Advanced analytics, pattern recognition, and intelligent insights for trading
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import aiohttp
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from collections import defaultdict, deque
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Octagon Intelligence MCP Server",
    description="Advanced analytics and intelligent insights for trading operations",
    version="1.0.0"
)

security = HTTPBearer()

# Enums
class AnalysisType(str, Enum):
    PATTERN_RECOGNITION = "pattern_recognition"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    PREDICTIVE_MODELING = "predictive_modeling"
    ANOMALY_DETECTION = "anomaly_detection"
    CORRELATION_ANALYSIS = "correlation_analysis"
    MARKET_REGIME_DETECTION = "market_regime_detection"
    STRESS_TESTING = "stress_testing"
    SCENARIO_ANALYSIS = "scenario_analysis"

class InsightType(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"
    TRENDING = "trending"
    REVERSAL = "reversal"
    BREAKOUT = "breakout"
    CONSOLIDATION = "consolidation"

class ConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class PatternType(str, Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    VOLUME = "volume"
    VOLATILITY = "volatility"
    INTER_MARKET = "inter_market"

# Data models
@dataclass
class AnalysisResult:
    id: str
    analysis_type: AnalysisType
    symbol: str
    timeframe: str
    created_at: str
    confidence: ConfidenceLevel
    insight_type: InsightType
    summary: str
    details: Dict[str, Any]
    recommendations: List[str]
    risk_factors: List[str]
    supporting_evidence: List[Dict[str, Any]]
    expiry_time: Optional[str] = None
    agent_id: Optional[str] = None

@dataclass
class Pattern:
    id: str
    pattern_type: PatternType
    name: str
    symbol: str
    timeframe: str
    detected_at: str
    confidence: float
    strength: float
    completion_probability: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    expected_duration: Optional[int]  # hours
    historical_accuracy: float
    description: str
    key_levels: List[float]

@dataclass
class MarketInsight:
    id: str
    title: str
    category: str
    priority: str  # low, medium, high, critical
    created_at: str
    symbols_affected: List[str]
    market_impact: str
    insight_type: InsightType
    confidence: ConfidenceLevel
    summary: str
    detailed_analysis: str
    actionable_recommendations: List[str]
    time_sensitivity: str  # immediate, short_term, medium_term, long_term
    supporting_data: Dict[str, Any]

@dataclass
class PredictiveModel:
    id: str
    model_name: str
    model_type: str
    symbol: str
    target_variable: str
    features: List[str]
    accuracy_score: float
    last_training: str
    prediction_horizon: int  # hours
    confidence_interval: Tuple[float, float]
    feature_importance: Dict[str, float]
    backtest_results: Dict[str, Any]

class AnalysisRequest(BaseModel):
    analysis_type: AnalysisType = Field(..., description="Type of analysis to perform")
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field("1h", description="Analysis timeframe")
    lookback_period: int = Field(100, description="Lookback period in units")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")
    agent_id: Optional[str] = Field(None, description="Agent ID requesting analysis")

class PatternSearchRequest(BaseModel):
    symbols: List[str] = Field(..., description="Symbols to search")
    pattern_types: List[PatternType] = Field(..., description="Pattern types to detect")
    timeframes: List[str] = Field(["1h", "4h", "1d"], description="Timeframes to analyze")
    min_confidence: float = Field(0.7, description="Minimum confidence threshold")

class PredictionRequest(BaseModel):
    symbol: str = Field(..., description="Symbol to predict")
    target_variable: str = Field("price", description="Variable to predict")
    prediction_horizon: int = Field(24, description="Prediction horizon in hours")
    model_type: str = Field("ensemble", description="Model type to use")

class OctagonIntelligenceService:
    def __init__(self):
        self.analysis_results: Dict[str, AnalysisResult] = {}
        self.detected_patterns: Dict[str, List[Pattern]] = defaultdict(list)
        self.market_insights: Dict[str, MarketInsight] = {}
        self.predictive_models: Dict[str, PredictiveModel] = {}
        self.market_data_cache: Dict[str, pd.DataFrame] = {}
        self.sentiment_data: Dict[str, Dict] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self.connected_clients: List[WebSocket] = []
        self.analysis_engine_active = False
        
    async def initialize(self):
        """Initialize the intelligence service"""
        # Start analysis engines
        asyncio.create_task(self._pattern_detection_engine())
        asyncio.create_task(self._market_insight_generator())
        asyncio.create_task(self._predictive_model_updater())
        asyncio.create_task(self._sentiment_analyzer())
        
        # Initialize mock data
        await self._initialize_mock_data()
        
        logger.info("Octagon Intelligence Service initialized")

    async def _initialize_mock_data(self):
        """Initialize with mock market data and historical patterns"""
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'SPY', 'QQQ', 'BTC-USD']
        
        # Generate mock price data
        for symbol in symbols:
            dates = pd.date_range(start='2024-01-01', end='2024-12-11', freq='H')
            np.random.seed(hash(symbol) % 2**32)
            
            # Generate realistic price series with trends and volatility
            base_price = np.random.uniform(50, 400)
            returns = np.random.normal(0.0001, 0.02, len(dates))  # Small positive drift
            
            # Add some trending periods
            trend_periods = np.random.choice(len(dates), size=int(len(dates) * 0.1), replace=False)
            for period in trend_periods:
                if period + 24 < len(dates):
                    returns[period:period+24] += np.random.normal(0.002, 0.001, 24)
            
            prices = base_price * np.exp(np.cumsum(returns))
            
            # Create DataFrame with OHLCV data
            self.market_data_cache[symbol] = pd.DataFrame({
                'timestamp': dates,
                'open': prices * np.random.uniform(0.99, 1.01, len(dates)),
                'high': prices * np.random.uniform(1.001, 1.02, len(dates)),
                'low': prices * np.random.uniform(0.98, 0.999, len(dates)),
                'close': prices,
                'volume': np.random.uniform(100000, 1000000, len(dates))
            })
        
        # Initialize sentiment data
        for symbol in symbols:
            self.sentiment_data[symbol] = {
                'overall_sentiment': np.random.uniform(-1, 1),
                'sentiment_trend': np.random.choice(['improving', 'declining', 'stable']),
                'news_volume': np.random.randint(5, 50),
                'social_mentions': np.random.randint(100, 5000),
                'last_update': datetime.now().isoformat()
            }
        
        # Generate sample predictive models
        for symbol in ['AAPL', 'MSFT', 'SPY']:
            model = PredictiveModel(
                id=str(uuid.uuid4()),
                model_name=f"{symbol}_Price_Predictor",
                model_type="ensemble",
                symbol=symbol,
                target_variable="price",
                features=['sma_20', 'rsi', 'volume', 'sentiment', 'vix'],
                accuracy_score=np.random.uniform(0.65, 0.85),
                last_training=datetime.now().isoformat(),
                prediction_horizon=24,
                confidence_interval=(0.1, 0.9),
                feature_importance={
                    'sma_20': 0.25,
                    'rsi': 0.20,
                    'volume': 0.15,
                    'sentiment': 0.20,
                    'vix': 0.20
                },
                backtest_results={
                    'total_predictions': 1000,
                    'correct_direction': 720,
                    'avg_error': 0.032,
                    'max_error': 0.15,
                    'profit_factor': 1.4
                }
            )
            self.predictive_models[symbol] = model

    async def _pattern_detection_engine(self):
        """Continuously detect patterns in market data"""
        self.analysis_engine_active = True
        
        while self.analysis_engine_active:
            try:
                for symbol in self.market_data_cache:
                    await self._detect_technical_patterns(symbol)
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in pattern detection engine: {e}")
                await asyncio.sleep(600)

    async def _detect_technical_patterns(self, symbol: str):
        """Detect technical patterns for a symbol"""
        if symbol not in self.market_data_cache:
            return
        
        df = self.market_data_cache[symbol]
        if len(df) < 50:
            return
        
        # Simple pattern detection examples
        patterns = []
        
        # Moving Average Crossover
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        recent_data = df.tail(10)
        if len(recent_data) >= 2:
            current_cross = recent_data['sma_20'].iloc[-1] > recent_data['sma_50'].iloc[-1]
            previous_cross = recent_data['sma_20'].iloc[-2] > recent_data['sma_50'].iloc[-2]
            
            if current_cross and not previous_cross:
                # Golden cross
                pattern = Pattern(
                    id=str(uuid.uuid4()),
                    pattern_type=PatternType.TECHNICAL,
                    name="Golden Cross",
                    symbol=symbol,
                    timeframe="1h",
                    detected_at=datetime.now().isoformat(),
                    confidence=0.8,
                    strength=0.75,
                    completion_probability=0.9,
                    target_price=recent_data['close'].iloc[-1] * 1.05,
                    stop_loss=recent_data['close'].iloc[-1] * 0.98,
                    expected_duration=72,
                    historical_accuracy=0.72,
                    description="20-period SMA crossed above 50-period SMA, indicating potential uptrend",
                    key_levels=[recent_data['sma_20'].iloc[-1], recent_data['sma_50'].iloc[-1]]
                )
                patterns.append(pattern)
        
        # RSI Divergence
        df['rsi'] = self._calculate_rsi(df['close'])
        if len(df) >= 20:
            recent_rsi = df['rsi'].tail(20)
            recent_prices = df['close'].tail(20)
            
            # Simple divergence detection
            if (recent_prices.iloc[-1] > recent_prices.iloc[-10] and 
                recent_rsi.iloc[-1] < recent_rsi.iloc[-10]):
                
                pattern = Pattern(
                    id=str(uuid.uuid4()),
                    pattern_type=PatternType.TECHNICAL,
                    name="Bearish RSI Divergence",
                    symbol=symbol,
                    timeframe="1h",
                    detected_at=datetime.now().isoformat(),
                    confidence=0.7,
                    strength=0.65,
                    completion_probability=0.75,
                    target_price=recent_prices.iloc[-1] * 0.95,
                    stop_loss=recent_prices.iloc[-1] * 1.02,
                    expected_duration=48,
                    historical_accuracy=0.68,
                    description="Price making higher highs while RSI making lower highs",
                    key_levels=[recent_rsi.iloc[-1]]
                )
                patterns.append(pattern)
        
        # Volume Spike
        df['volume_sma'] = df['volume'].rolling(20).mean()
        if df['volume'].iloc[-1] > df['volume_sma'].iloc[-1] * 1.5:
            pattern = Pattern(
                id=str(uuid.uuid4()),
                pattern_type=PatternType.VOLUME,
                name="Volume Spike",
                symbol=symbol,
                timeframe="1h",
                detected_at=datetime.now().isoformat(),
                confidence=0.6,
                strength=0.8,
                completion_probability=0.6,
                target_price=None,
                stop_loss=None,
                expected_duration=12,
                historical_accuracy=0.55,
                description=f"Volume {df['volume'].iloc[-1]/df['volume_sma'].iloc[-1]:.1f}x above average",
                key_levels=[df['volume'].iloc[-1], df['volume_sma'].iloc[-1]]
            )
            patterns.append(pattern)
        
        # Store patterns
        self.detected_patterns[symbol] = patterns
        
        # Notify if significant patterns found
        if patterns:
            await self._notify_pattern_detection(symbol, patterns)

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    async def _market_insight_generator(self):
        """Generate market insights from analysis"""
        while True:
            try:
                # Generate insights based on patterns and market conditions
                await self._generate_market_insights()
                
                await asyncio.sleep(600)  # Generate every 10 minutes
                
            except Exception as e:
                logger.error(f"Error in insight generator: {e}")
                await asyncio.sleep(900)

    async def _generate_market_insights(self):
        """Generate comprehensive market insights"""
        # Cross-market analysis
        tech_symbols = ['AAPL', 'MSFT', 'GOOGL']
        tech_patterns = []
        
        for symbol in tech_symbols:
            if symbol in self.detected_patterns:
                tech_patterns.extend(self.detected_patterns[symbol])
        
        # If multiple tech stocks show similar patterns
        if len(tech_patterns) >= 2:
            bullish_patterns = [p for p in tech_patterns if 'golden' in p.name.lower() or 'breakout' in p.name.lower()]
            bearish_patterns = [p for p in tech_patterns if 'bearish' in p.name.lower() or 'divergence' in p.name.lower()]
            
            if len(bullish_patterns) >= 2:
                insight = MarketInsight(
                    id=str(uuid.uuid4()),
                    title="Technology Sector Bullish Momentum",
                    category="sector_analysis",
                    priority="high",
                    created_at=datetime.now().isoformat(),
                    symbols_affected=tech_symbols,
                    market_impact="positive",
                    insight_type=InsightType.BULLISH,
                    confidence=ConfidenceLevel.HIGH,
                    summary="Multiple technology stocks showing bullish technical patterns",
                    detailed_analysis="Technical analysis reveals synchronized bullish signals across major tech stocks, suggesting sector-wide momentum.",
                    actionable_recommendations=[
                        "Consider increasing technology sector allocation",
                        "Monitor for continuation patterns",
                        "Set stop losses below key support levels"
                    ],
                    time_sensitivity="short_term",
                    supporting_data={
                        "patterns_detected": len(bullish_patterns),
                        "avg_confidence": np.mean([p.confidence for p in bullish_patterns]),
                        "sector_correlation": 0.75
                    }
                )
                
                self.market_insights[insight.id] = insight
                await self._notify_market_insight(insight)
        
        # Volatility analysis
        volatilities = {}
        for symbol in self.market_data_cache:
            df = self.market_data_cache[symbol]
            if len(df) >= 20:
                returns = df['close'].pct_change().dropna()
                volatilities[symbol] = returns.rolling(20).std().iloc[-1] * np.sqrt(24)  # Annualized hourly vol
        
        if volatilities:
            avg_vol = np.mean(list(volatilities.values()))
            high_vol_symbols = [s for s, v in volatilities.items() if v > avg_vol * 1.5]
            
            if len(high_vol_symbols) >= 3:
                insight = MarketInsight(
                    id=str(uuid.uuid4()),
                    title="Elevated Market Volatility Alert",
                    category="risk_analysis",
                    priority="medium",
                    created_at=datetime.now().isoformat(),
                    symbols_affected=high_vol_symbols,
                    market_impact="neutral",
                    insight_type=InsightType.VOLATILE,
                    confidence=ConfidenceLevel.MEDIUM,
                    summary=f"{len(high_vol_symbols)} symbols showing elevated volatility",
                    detailed_analysis="Multiple assets exhibiting above-average volatility, suggesting increased market uncertainty.",
                    actionable_recommendations=[
                        "Reduce position sizes in high volatility assets",
                        "Consider volatility-based position sizing",
                        "Monitor risk management parameters closely"
                    ],
                    time_sensitivity="immediate",
                    supporting_data={
                        "symbols_count": len(high_vol_symbols),
                        "avg_volatility": avg_vol,
                        "volatility_threshold": avg_vol * 1.5
                    }
                )
                
                self.market_insights[insight.id] = insight
                await self._notify_market_insight(insight)

    async def _predictive_model_updater(self):
        """Update predictive models periodically"""
        while True:
            try:
                for symbol, model in self.predictive_models.items():
                    await self._update_model_predictions(symbol, model)
                
                await asyncio.sleep(3600)  # Update every hour
                
            except Exception as e:
                logger.error(f"Error in model updater: {e}")
                await asyncio.sleep(1800)

    async def _update_model_predictions(self, symbol: str, model: PredictiveModel):
        """Update model predictions"""
        if symbol not in self.market_data_cache:
            return
        
        df = self.market_data_cache[symbol]
        current_price = df['close'].iloc[-1]
        
        # Simple prediction simulation
        # In real implementation, this would use actual ML models
        price_change = np.random.normal(0, 0.02)  # 2% volatility
        sentiment_factor = self.sentiment_data.get(symbol, {}).get('overall_sentiment', 0) * 0.01
        
        predicted_price = current_price * (1 + price_change + sentiment_factor)
        
        # Update model with new prediction
        model.confidence_interval = (
            predicted_price * 0.95,
            predicted_price * 1.05
        )
        
        # Simulate accuracy update
        if np.random.random() > 0.1:  # 90% of predictions are "good"
            model.accuracy_score = min(0.95, model.accuracy_score + 0.001)
        else:
            model.accuracy_score = max(0.5, model.accuracy_score - 0.01)

    async def _sentiment_analyzer(self):
        """Analyze sentiment data"""
        while True:
            try:
                for symbol in self.sentiment_data:
                    # Simulate sentiment updates
                    current_sentiment = self.sentiment_data[symbol]['overall_sentiment']
                    sentiment_change = np.random.normal(0, 0.1)
                    new_sentiment = np.clip(current_sentiment + sentiment_change, -1, 1)
                    
                    self.sentiment_data[symbol]['overall_sentiment'] = new_sentiment
                    self.sentiment_data[symbol]['last_update'] = datetime.now().isoformat()
                    
                    # Determine trend
                    if sentiment_change > 0.05:
                        self.sentiment_data[symbol]['sentiment_trend'] = 'improving'
                    elif sentiment_change < -0.05:
                        self.sentiment_data[symbol]['sentiment_trend'] = 'declining'
                    else:
                        self.sentiment_data[symbol]['sentiment_trend'] = 'stable'
                
                await asyncio.sleep(1800)  # Update every 30 minutes
                
            except Exception as e:
                logger.error(f"Error in sentiment analyzer: {e}")
                await asyncio.sleep(3600)

    async def perform_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """Perform specified analysis type"""
        analysis_id = str(uuid.uuid4())
        
        if request.analysis_type == AnalysisType.PATTERN_RECOGNITION:
            result = await self._perform_pattern_analysis(analysis_id, request)
        elif request.analysis_type == AnalysisType.SENTIMENT_ANALYSIS:
            result = await self._perform_sentiment_analysis(analysis_id, request)
        elif request.analysis_type == AnalysisType.PREDICTIVE_MODELING:
            result = await self._perform_predictive_analysis(analysis_id, request)
        elif request.analysis_type == AnalysisType.ANOMALY_DETECTION:
            result = await self._perform_anomaly_analysis(analysis_id, request)
        elif request.analysis_type == AnalysisType.CORRELATION_ANALYSIS:
            result = await self._perform_correlation_analysis(analysis_id, request)
        else:
            # Default analysis
            result = await self._perform_general_analysis(analysis_id, request)
        
        self.analysis_results[analysis_id] = result
        await self._notify_analysis_complete(result)
        
        return result

    async def _perform_pattern_analysis(self, analysis_id: str, request: AnalysisRequest) -> AnalysisResult:
        """Perform pattern recognition analysis"""
        symbol = request.symbol
        patterns = self.detected_patterns.get(symbol, [])
        
        if not patterns:
            insight_type = InsightType.NEUTRAL
            confidence = ConfidenceLevel.LOW
            summary = "No significant patterns detected"
            recommendations = ["Continue monitoring for pattern development"]
        else:
            # Analyze pattern strength
            avg_confidence = np.mean([p.confidence for p in patterns])
            bullish_patterns = [p for p in patterns if 'golden' in p.name.lower() or 'bullish' in p.name.lower()]
            bearish_patterns = [p for p in patterns if 'bearish' in p.name.lower() or 'divergence' in p.name.lower()]
            
            if len(bullish_patterns) > len(bearish_patterns):
                insight_type = InsightType.BULLISH
            elif len(bearish_patterns) > len(bullish_patterns):
                insight_type = InsightType.BEARISH
            else:
                insight_type = InsightType.NEUTRAL
            
            if avg_confidence > 0.8:
                confidence = ConfidenceLevel.HIGH
            elif avg_confidence > 0.6:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW
            
            summary = f"Detected {len(patterns)} patterns with {avg_confidence:.1%} average confidence"
            recommendations = [f"Monitor {p.name} pattern for {symbol}" for p in patterns[:3]]
        
        return AnalysisResult(
            id=analysis_id,
            analysis_type=request.analysis_type,
            symbol=symbol,
            timeframe=request.timeframe,
            created_at=datetime.now().isoformat(),
            confidence=confidence,
            insight_type=insight_type,
            summary=summary,
            details={
                'patterns_detected': len(patterns),
                'pattern_details': [asdict(p) for p in patterns],
                'analysis_parameters': request.parameters
            },
            recommendations=recommendations,
            risk_factors=["Pattern failure risk", "Market condition changes"],
            supporting_evidence=[{'type': 'technical_patterns', 'count': len(patterns)}],
            agent_id=request.agent_id
        )

    async def _perform_sentiment_analysis(self, analysis_id: str, request: AnalysisRequest) -> AnalysisResult:
        """Perform sentiment analysis"""
        symbol = request.symbol
        sentiment_data = self.sentiment_data.get(symbol, {})
        
        overall_sentiment = sentiment_data.get('overall_sentiment', 0)
        sentiment_trend = sentiment_data.get('sentiment_trend', 'stable')
        
        if overall_sentiment > 0.3:
            insight_type = InsightType.BULLISH
            confidence = ConfidenceLevel.HIGH if overall_sentiment > 0.6 else ConfidenceLevel.MEDIUM
        elif overall_sentiment < -0.3:
            insight_type = InsightType.BEARISH
            confidence = ConfidenceLevel.HIGH if overall_sentiment < -0.6 else ConfidenceLevel.MEDIUM
        else:
            insight_type = InsightType.NEUTRAL
            confidence = ConfidenceLevel.MEDIUM
        
        summary = f"Sentiment score: {overall_sentiment:.2f}, trend: {sentiment_trend}"
        
        recommendations = []
        if sentiment_trend == 'improving':
            recommendations.append("Positive sentiment momentum supports long positions")
        elif sentiment_trend == 'declining':
            recommendations.append("Declining sentiment suggests caution")
        else:
            recommendations.append("Monitor for sentiment inflection points")
        
        return AnalysisResult(
            id=analysis_id,
            analysis_type=request.analysis_type,
            symbol=symbol,
            timeframe=request.timeframe,
            created_at=datetime.now().isoformat(),
            confidence=confidence,
            insight_type=insight_type,
            summary=summary,
            details={
                'sentiment_score': overall_sentiment,
                'sentiment_trend': sentiment_trend,
                'news_volume': sentiment_data.get('news_volume', 0),
                'social_mentions': sentiment_data.get('social_mentions', 0)
            },
            recommendations=recommendations,
            risk_factors=["Sentiment volatility", "News event risks"],
            supporting_evidence=[{'type': 'sentiment_data', 'score': overall_sentiment}],
            agent_id=request.agent_id
        )

    async def _perform_predictive_analysis(self, analysis_id: str, request: AnalysisRequest) -> AnalysisResult:
        """Perform predictive modeling analysis"""
        symbol = request.symbol
        model = self.predictive_models.get(symbol)
        
        if not model:
            return AnalysisResult(
                id=analysis_id,
                analysis_type=request.analysis_type,
                symbol=symbol,
                timeframe=request.timeframe,
                created_at=datetime.now().isoformat(),
                confidence=ConfidenceLevel.LOW,
                insight_type=InsightType.NEUTRAL,
                summary="No predictive model available for this symbol",
                details={'error': 'No model found'},
                recommendations=["Train predictive model for this symbol"],
                risk_factors=["No prediction capability"],
                supporting_evidence=[],
                agent_id=request.agent_id
            )
        
        # Generate prediction
        current_price = self.market_data_cache[symbol]['close'].iloc[-1]
        predicted_price = (model.confidence_interval[0] + model.confidence_interval[1]) / 2
        price_change = (predicted_price - current_price) / current_price
        
        if price_change > 0.02:
            insight_type = InsightType.BULLISH
        elif price_change < -0.02:
            insight_type = InsightType.BEARISH
        else:
            insight_type = InsightType.NEUTRAL
        
        if model.accuracy_score > 0.8:
            confidence = ConfidenceLevel.HIGH
        elif model.accuracy_score > 0.6:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW
        
        summary = f"Model predicts {price_change:+.1%} price change with {model.accuracy_score:.1%} accuracy"
        
        return AnalysisResult(
            id=analysis_id,
            analysis_type=request.analysis_type,
            symbol=symbol,
            timeframe=request.timeframe,
            created_at=datetime.now().isoformat(),
            confidence=confidence,
            insight_type=insight_type,
            summary=summary,
            details={
                'current_price': current_price,
                'predicted_price': predicted_price,
                'price_change_percent': price_change * 100,
                'model_accuracy': model.accuracy_score,
                'confidence_interval': model.confidence_interval,
                'feature_importance': model.feature_importance
            },
            recommendations=[
                f"Target price: ${predicted_price:.2f}",
                f"Confidence interval: ${model.confidence_interval[0]:.2f} - ${model.confidence_interval[1]:.2f}"
            ],
            risk_factors=["Model prediction error", "Market regime changes"],
            supporting_evidence=[{'type': 'predictive_model', 'accuracy': model.accuracy_score}],
            agent_id=request.agent_id
        )

    async def _perform_anomaly_analysis(self, analysis_id: str, request: AnalysisRequest) -> AnalysisResult:
        """Perform anomaly detection analysis"""
        symbol = request.symbol
        df = self.market_data_cache.get(symbol)
        
        if df is None or len(df) < 50:
            return AnalysisResult(
                id=analysis_id,
                analysis_type=request.analysis_type,
                symbol=symbol,
                timeframe=request.timeframe,
                created_at=datetime.now().isoformat(),
                confidence=ConfidenceLevel.LOW,
                insight_type=InsightType.NEUTRAL,
                summary="Insufficient data for anomaly detection",
                details={'error': 'Insufficient data'},
                recommendations=["Collect more historical data"],
                risk_factors=["Data quality issues"],
                supporting_evidence=[],
                agent_id=request.agent_id
            )
        
        # Simple anomaly detection based on Z-score
        returns = df['close'].pct_change().dropna()
        z_scores = np.abs((returns - returns.mean()) / returns.std())
        
        recent_z_score = z_scores.iloc[-1]
        anomaly_threshold = 2.5
        
        anomalies_detected = len(z_scores[z_scores > anomaly_threshold])
        
        if recent_z_score > anomaly_threshold:
            insight_type = InsightType.VOLATILE
            confidence = ConfidenceLevel.HIGH
            summary = f"Current price movement is anomalous (Z-score: {recent_z_score:.2f})"
        elif anomalies_detected > len(z_scores) * 0.05:  # More than 5% anomalies
            insight_type = InsightType.VOLATILE
            confidence = ConfidenceLevel.MEDIUM
            summary = f"High anomaly frequency detected: {anomalies_detected} anomalies in recent data"
        else:
            insight_type = InsightType.NEUTRAL
            confidence = ConfidenceLevel.MEDIUM
            summary = "No significant anomalies detected in recent price action"
        
        return AnalysisResult(
            id=analysis_id,
            analysis_type=request.analysis_type,
            symbol=symbol,
            timeframe=request.timeframe,
            created_at=datetime.now().isoformat(),
            confidence=confidence,
            insight_type=insight_type,
            summary=summary,
            details={
                'recent_z_score': recent_z_score,
                'anomaly_threshold': anomaly_threshold,
                'total_anomalies': anomalies_detected,
                'anomaly_percentage': (anomalies_detected / len(z_scores)) * 100
            },
            recommendations=[
                "Monitor for continued anomalous behavior" if recent_z_score > anomaly_threshold else "Continue normal monitoring"
            ],
            risk_factors=["Anomalous market behavior", "Increased volatility risk"],
            supporting_evidence=[{'type': 'statistical_analysis', 'z_score': recent_z_score}],
            agent_id=request.agent_id
        )

    async def _perform_correlation_analysis(self, analysis_id: str, request: AnalysisRequest) -> AnalysisResult:
        """Perform correlation analysis"""
        symbol = request.symbol
        
        # Calculate correlations with other symbols
        correlations = {}
        base_returns = None
        
        if symbol in self.market_data_cache:
            base_returns = self.market_data_cache[symbol]['close'].pct_change().dropna()
        
        if base_returns is None or len(base_returns) < 20:
            return AnalysisResult(
                id=analysis_id,
                analysis_type=request.analysis_type,
                symbol=symbol,
                timeframe=request.timeframe,
                created_at=datetime.now().isoformat(),
                confidence=ConfidenceLevel.LOW,
                insight_type=InsightType.NEUTRAL,
                summary="Insufficient data for correlation analysis",
                details={'error': 'Insufficient data'},
                recommendations=["Collect more historical data"],
                risk_factors=["Data quality issues"],
                supporting_evidence=[],
                agent_id=request.agent_id
            )
        
        for other_symbol, other_df in self.market_data_cache.items():
            if other_symbol != symbol:
                other_returns = other_df['close'].pct_change().dropna()
                if len(other_returns) >= len(base_returns):
                    # Align data
                    min_length = min(len(base_returns), len(other_returns))
                    correlation = np.corrcoef(
                        base_returns.iloc[-min_length:],
                        other_returns.iloc[-min_length:]
                    )[0, 1]
                    correlations[other_symbol] = correlation
        
        # Find highest correlations
        high_correlations = {k: v for k, v in correlations.items() if abs(v) > 0.5}
        avg_correlation = np.mean(list(correlations.values())) if correlations else 0
        
        if abs(avg_correlation) > 0.6:
            insight_type = InsightType.TRENDING
            confidence = ConfidenceLevel.HIGH
        elif abs(avg_correlation) > 0.3:
            insight_type = InsightType.NEUTRAL
            confidence = ConfidenceLevel.MEDIUM
        else:
            insight_type = InsightType.NEUTRAL
            confidence = ConfidenceLevel.LOW
        
        summary = f"Average correlation: {avg_correlation:.2f}, {len(high_correlations)} high correlations"
        
        return AnalysisResult(
            id=analysis_id,
            analysis_type=request.analysis_type,
            symbol=symbol,
            timeframe=request.timeframe,
            created_at=datetime.now().isoformat(),
            confidence=confidence,
            insight_type=insight_type,
            summary=summary,
            details={
                'correlations': correlations,
                'high_correlations': high_correlations,
                'average_correlation': avg_correlation
            },
            recommendations=[
                f"Strong correlation with {max(correlations.items(), key=lambda x: abs(x[1]))[0]}" if correlations else "No significant correlations"
            ],
            risk_factors=["Correlation breakdown risk", "Systematic risk"],
            supporting_evidence=[{'type': 'correlation_analysis', 'avg_correlation': avg_correlation}],
            agent_id=request.agent_id
        )

    async def _perform_general_analysis(self, analysis_id: str, request: AnalysisRequest) -> AnalysisResult:
        """Perform general analysis"""
        return AnalysisResult(
            id=analysis_id,
            analysis_type=request.analysis_type,
            symbol=request.symbol,
            timeframe=request.timeframe,
            created_at=datetime.now().isoformat(),
            confidence=ConfidenceLevel.MEDIUM,
            insight_type=InsightType.NEUTRAL,
            summary="General analysis completed",
            details={'analysis_type': request.analysis_type.value},
            recommendations=["Review analysis parameters"],
            risk_factors=["General market risks"],
            supporting_evidence=[],
            agent_id=request.agent_id
        )

    async def search_patterns(self, request: PatternSearchRequest) -> List[Pattern]:
        """Search for patterns across multiple symbols"""
        all_patterns = []
        
        for symbol in request.symbols:
            if symbol in self.detected_patterns:
                symbol_patterns = self.detected_patterns[symbol]
                
                # Filter by pattern type and confidence
                filtered_patterns = [
                    p for p in symbol_patterns
                    if p.pattern_type in request.pattern_types and p.confidence >= request.min_confidence
                ]
                
                all_patterns.extend(filtered_patterns)
        
        # Sort by confidence
        all_patterns.sort(key=lambda x: x.confidence, reverse=True)
        
        return all_patterns

    async def get_market_insights(self, category: Optional[str] = None, priority: Optional[str] = None) -> List[MarketInsight]:
        """Get market insights with optional filtering"""
        insights = list(self.market_insights.values())
        
        if category:
            insights = [i for i in insights if i.category == category]
        
        if priority:
            insights = [i for i in insights if i.priority == priority]
        
        # Sort by creation time (newest first)
        insights.sort(key=lambda x: x.created_at, reverse=True)
        
        return insights

    async def _notify_pattern_detection(self, symbol: str, patterns: List[Pattern]):
        """Notify clients of pattern detection"""
        message = {
            "type": "pattern_detection",
            "symbol": symbol,
            "patterns": [asdict(p) for p in patterns],
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

    async def _notify_market_insight(self, insight: MarketInsight):
        """Notify clients of market insights"""
        message = {
            "type": "market_insight",
            "insight": asdict(insight),
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

    async def _notify_analysis_complete(self, result: AnalysisResult):
        """Notify clients of completed analysis"""
        message = {
            "type": "analysis_complete",
            "result": asdict(result),
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

# Initialize service
octagon_service = OctagonIntelligenceService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await octagon_service.initialize()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Octagon Intelligence MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "pattern_recognition",
            "sentiment_analysis",
            "predictive_modeling",
            "anomaly_detection",
            "market_insights"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    return {
        "cpu_usage": 38.7,
        "memory_usage": 52.3,
        "disk_usage": 22.1,
        "network_in": 3072,
        "network_out": 6144,
        "active_connections": len(octagon_service.connected_clients),
        "queue_length": 0,
        "errors_last_hour": 1,
        "requests_last_hour": 312,
        "response_time_p95": 156.0
    }

@app.post("/analysis")
async def perform_analysis(request: AnalysisRequest, token: str = Depends(get_current_user)):
    try:
        result = await octagon_service.perform_analysis(request)
        return {"result": asdict(result), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error performing analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/{analysis_id}")
async def get_analysis_result(analysis_id: str, token: str = Depends(get_current_user)):
    result = octagon_service.analysis_results.get(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return {"result": asdict(result), "timestamp": datetime.now().isoformat()}

@app.post("/patterns/search")
async def search_patterns(request: PatternSearchRequest, token: str = Depends(get_current_user)):
    try:
        patterns = await octagon_service.search_patterns(request)
        return {
            "patterns": [asdict(p) for p in patterns],
            "total": len(patterns),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error searching patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patterns/{symbol}")
async def get_symbol_patterns(symbol: str, token: str = Depends(get_current_user)):
    patterns = octagon_service.detected_patterns.get(symbol, [])
    return {
        "symbol": symbol,
        "patterns": [asdict(p) for p in patterns],
        "total": len(patterns),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/insights")
async def get_market_insights(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    token: str = Depends(get_current_user)
):
    try:
        insights = await octagon_service.get_market_insights(category, priority)
        return {
            "insights": [asdict(i) for i in insights],
            "total": len(insights),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def get_predictive_models(token: str = Depends(get_current_user)):
    models = list(octagon_service.predictive_models.values())
    return {
        "models": [asdict(m) for m in models],
        "total": len(models),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/sentiment/{symbol}")
async def get_sentiment_data(symbol: str, token: str = Depends(get_current_user)):
    sentiment = octagon_service.sentiment_data.get(symbol)
    if not sentiment:
        raise HTTPException(status_code=404, detail="Sentiment data not found")
    return {"symbol": symbol, "sentiment": sentiment, "timestamp": datetime.now().isoformat()}

@app.websocket("/ws/intelligence")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    octagon_service.connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except:
        pass
    finally:
        if websocket in octagon_service.connected_clients:
            octagon_service.connected_clients.remove(websocket)

@app.get("/capabilities")
async def get_capabilities():
    return {
        "analysis_types": [at.value for at in AnalysisType],
        "pattern_types": [pt.value for pt in PatternType],
        "insight_types": [it.value for it in InsightType],
        "capabilities": [
            {
                "name": "pattern_recognition",
                "description": "Detect technical and fundamental patterns in market data"
            },
            {
                "name": "sentiment_analysis",
                "description": "Analyze market sentiment from multiple sources"
            },
            {
                "name": "predictive_modeling",
                "description": "Generate price and trend predictions using ML models"
            },
            {
                "name": "anomaly_detection",
                "description": "Identify unusual market behavior and outliers"
            },
            {
                "name": "market_insights",
                "description": "Generate actionable insights from comprehensive analysis"
            }
        ],
        "supported_timeframes": ["1m", "5m", "15m", "1h", "4h", "1d", "1w"],
        "confidence_levels": [cl.value for cl in ConfidenceLevel]
    }

if __name__ == "__main__":
    uvicorn.run(
        "octagon_intelligence:app",
        host="0.0.0.0",
        port=8020,
        reload=True,
        log_level="info"
    )