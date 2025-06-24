"""
Phase 10: Intelligent Market Analysis and Signal Generation Service
Advanced market analysis, signal generation, and trading intelligence
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import logging
import numpy as np
import pandas as pd
from collections import defaultdict, deque
import ta  # Technical Analysis library
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.trading_strategy_models import (
    TradingSignal, TradingStrategy, MarketData, StrategyType, SignalStrength,
    MarketCondition, PositionSide, MarketRegime, SignalGenerationRequest
)
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Technical analysis indicators calculator"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        df = pd.DataFrame({'close': prices})
        rsi = ta.momentum.RSIIndicator(close=df['close'], window=period)
        return float(rsi.rsi().iloc[-1]) if not pd.isna(rsi.rsi().iloc[-1]) else 50.0
    
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow + signal:
            return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
        
        df = pd.DataFrame({'close': prices})
        macd = ta.trend.MACD(close=df['close'], window_fast=fast, window_slow=slow, window_sign=signal)
        
        return {
            "macd": float(macd.macd().iloc[-1]) if not pd.isna(macd.macd().iloc[-1]) else 0.0,
            "signal": float(macd.macd_signal().iloc[-1]) if not pd.isna(macd.macd_signal().iloc[-1]) else 0.0,
            "histogram": float(macd.macd_diff().iloc[-1]) if not pd.isna(macd.macd_diff().iloc[-1]) else 0.0
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            price = prices[-1] if prices else 0.0
            return {"upper": price * 1.02, "middle": price, "lower": price * 0.98}
        
        df = pd.DataFrame({'close': prices})
        bb = ta.volatility.BollingerBands(close=df['close'], window=period, window_dev=std_dev)
        
        return {
            "upper": float(bb.bollinger_hband().iloc[-1]) if not pd.isna(bb.bollinger_hband().iloc[-1]) else prices[-1] * 1.02,
            "middle": float(bb.bollinger_mavg().iloc[-1]) if not pd.isna(bb.bollinger_mavg().iloc[-1]) else prices[-1],
            "lower": float(bb.bollinger_lband().iloc[-1]) if not pd.isna(bb.bollinger_lband().iloc[-1]) else prices[-1] * 0.98
        }
    
    @staticmethod
    def calculate_moving_averages(prices: List[float], periods: List[int] = [20, 50, 200]) -> Dict[str, float]:
        """Calculate multiple moving averages"""
        result = {}
        df = pd.DataFrame({'close': prices})
        
        for period in periods:
            if len(prices) >= period:
                ma = df['close'].rolling(window=period).mean()
                result[f"ma_{period}"] = float(ma.iloc[-1]) if not pd.isna(ma.iloc[-1]) else prices[-1]
            else:
                result[f"ma_{period}"] = prices[-1] if prices else 0.0
        
        return result
    
    @staticmethod
    def calculate_stochastic(highs: List[float], lows: List[float], closes: List[float], k_period: int = 14, d_period: int = 3) -> Dict[str, float]:
        """Calculate Stochastic Oscillator"""
        if len(closes) < k_period:
            return {"k": 50.0, "d": 50.0}
        
        df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
        stoch = ta.momentum.StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], 
                                               window=k_period, smooth_window=d_period)
        
        return {
            "k": float(stoch.stoch().iloc[-1]) if not pd.isna(stoch.stoch().iloc[-1]) else 50.0,
            "d": float(stoch.stoch_signal().iloc[-1]) if not pd.isna(stoch.stoch_signal().iloc[-1]) else 50.0
        }


class MarketAnalysisEngine:
    """Advanced market analysis engine"""
    
    def __init__(self):
        self.technical_indicators = TechnicalIndicators()
        
    def analyze_market_condition(self, market_data: List[MarketData]) -> MarketCondition:
        """Analyze current market condition"""
        if len(market_data) < 20:
            return MarketCondition.SIDEWAYS
        
        # Extract price data
        closes = [float(data.close) for data in market_data[-50:]]
        volumes = [float(data.volume) for data in market_data[-50:]]
        
        # Calculate trend
        short_ma = np.mean(closes[-10:])
        long_ma = np.mean(closes[-30:])
        
        # Calculate volatility
        returns = np.diff(closes) / closes[:-1]
        volatility = np.std(returns) * np.sqrt(24)  # Assuming hourly data
        
        # Determine condition
        if short_ma > long_ma * 1.02:
            if volatility > 0.05:
                return MarketCondition.VOLATILE
            else:
                return MarketCondition.BULLISH
        elif short_ma < long_ma * 0.98:
            if volatility > 0.05:
                return MarketCondition.VOLATILE
            else:
                return MarketCondition.BEARISH
        else:
            if volatility > 0.03:
                return MarketCondition.VOLATILE
            else:
                return MarketCondition.SIDEWAYS
    
    def calculate_signal_strength(self, indicators: Dict[str, Any]) -> SignalStrength:
        """Calculate signal strength based on technical indicators"""
        strength_score = 0
        total_indicators = 0
        
        # RSI strength
        if "rsi" in indicators:
            rsi = indicators["rsi"]
            if rsi > 70 or rsi < 30:
                strength_score += 2
            elif rsi > 60 or rsi < 40:
                strength_score += 1
            total_indicators += 2
        
        # MACD strength
        if "macd" in indicators:
            macd_data = indicators["macd"]
            if isinstance(macd_data, dict):
                if macd_data.get("histogram", 0) > 0:
                    strength_score += 1
                if abs(macd_data.get("macd", 0)) > abs(macd_data.get("signal", 0)):
                    strength_score += 1
            total_indicators += 2
        
        # Bollinger Bands strength
        if "bollinger_bands" in indicators:
            bb = indicators["bollinger_bands"]
            if isinstance(bb, dict) and "current_price" in indicators:
                price = indicators["current_price"]
                if price > bb.get("upper", price):
                    strength_score += 2
                elif price < bb.get("lower", price):
                    strength_score += 2
                elif price > bb.get("middle", price):
                    strength_score += 1
            total_indicators += 2
        
        # Calculate final strength
        if total_indicators == 0:
            return SignalStrength.MODERATE
        
        strength_ratio = strength_score / total_indicators
        
        if strength_ratio >= 0.8:
            return SignalStrength.VERY_STRONG
        elif strength_ratio >= 0.6:
            return SignalStrength.STRONG
        elif strength_ratio >= 0.4:
            return SignalStrength.MODERATE
        elif strength_ratio >= 0.2:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK
    
    def detect_patterns(self, market_data: List[MarketData]) -> List[str]:
        """Detect chart patterns"""
        if len(market_data) < 20:
            return []
        
        patterns = []
        closes = [float(data.close) for data in market_data[-20:]]
        highs = [float(data.high) for data in market_data[-20:]]
        lows = [float(data.low) for data in market_data[-20:]]
        
        # Double top/bottom detection (simplified)
        recent_highs = sorted(highs[-10:], reverse=True)[:2]
        recent_lows = sorted(lows[-10:])[:2]
        
        if len(recent_highs) >= 2 and abs(recent_highs[0] - recent_highs[1]) / recent_highs[0] < 0.02:
            patterns.append("double_top")
        
        if len(recent_lows) >= 2 and abs(recent_lows[0] - recent_lows[1]) / recent_lows[0] < 0.02:
            patterns.append("double_bottom")
        
        # Trend detection
        if closes[-1] > closes[-5] > closes[-10]:
            patterns.append("uptrend")
        elif closes[-1] < closes[-5] < closes[-10]:
            patterns.append("downtrend")
        
        # Breakout detection
        ma_20 = np.mean(closes[-20:])
        if closes[-1] > ma_20 * 1.05:
            patterns.append("upward_breakout")
        elif closes[-1] < ma_20 * 0.95:
            patterns.append("downward_breakout")
        
        return patterns


class SignalGenerator:
    """Trading signal generator for different strategies"""
    
    def __init__(self):
        self.analysis_engine = MarketAnalysisEngine()
        self.technical_indicators = TechnicalIndicators()
    
    async def generate_momentum_signal(
        self,
        strategy: TradingStrategy,
        market_data: List[MarketData],
        symbol: str
    ) -> Optional[TradingSignal]:
        """Generate momentum trading signal"""
        if len(market_data) < 50:
            return None
        
        closes = [float(data.close) for data in market_data[-50:]]
        highs = [float(data.high) for data in market_data[-50:]]
        lows = [float(data.low) for data in market_data[-50:]]
        
        # Calculate indicators
        rsi = self.technical_indicators.calculate_rsi(closes)
        macd = self.technical_indicators.calculate_macd(closes)
        mas = self.technical_indicators.calculate_moving_averages(closes, [20, 50])
        
        current_price = closes[-1]
        ma_20 = mas.get("ma_20", current_price)
        ma_50 = mas.get("ma_50", current_price)
        
        # Momentum signal logic
        signal_type = "hold"
        confidence = 0.5
        position_side = PositionSide.NEUTRAL
        
        # Bullish momentum
        if (current_price > ma_20 > ma_50 and 
            rsi > 50 and rsi < 80 and 
            macd["macd"] > macd["signal"]):
            
            signal_type = "buy"
            position_side = PositionSide.LONG
            confidence = min(0.9, 0.5 + (rsi - 50) / 100 + (macd["histogram"] / current_price) * 1000)
        
        # Bearish momentum  
        elif (current_price < ma_20 < ma_50 and 
              rsi < 50 and rsi > 20 and 
              macd["macd"] < macd["signal"]):
            
            signal_type = "sell"
            position_side = PositionSide.SHORT
            confidence = min(0.9, 0.5 + (50 - rsi) / 100 + abs(macd["histogram"] / current_price) * 1000)
        
        if signal_type == "hold":
            return None
        
        # Calculate technical indicators for signal
        indicators = {
            "rsi": rsi,
            "macd": macd,
            "moving_averages": mas,
            "current_price": current_price
        }
        
        strength = self.analysis_engine.calculate_signal_strength(indicators)
        market_condition = self.analysis_engine.analyze_market_condition(market_data)
        
        # Calculate targets
        atr = self._calculate_atr(highs, lows, closes)
        
        if signal_type == "buy":
            entry_price = Decimal(str(current_price))
            stop_loss = Decimal(str(current_price - (atr * 2)))
            target_price = Decimal(str(current_price + (atr * 3)))
        else:
            entry_price = Decimal(str(current_price))
            stop_loss = Decimal(str(current_price + (atr * 2)))
            target_price = Decimal(str(current_price - (atr * 3)))
        
        return TradingSignal(
            strategy_id=strategy.strategy_id,
            agent_id="momentum_generator",
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            position_side=position_side,
            timeframe="1h",
            market_condition=market_condition,
            technical_indicators=indicators,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=4)
        )
    
    async def generate_mean_reversion_signal(
        self,
        strategy: TradingStrategy,
        market_data: List[MarketData],
        symbol: str
    ) -> Optional[TradingSignal]:
        """Generate mean reversion trading signal"""
        if len(market_data) < 30:
            return None
        
        closes = [float(data.close) for data in market_data[-30:]]
        highs = [float(data.high) for data in market_data[-30:]]
        lows = [float(data.low) for data in market_data[-30:]]
        
        # Calculate indicators
        bb = self.technical_indicators.calculate_bollinger_bands(closes)
        rsi = self.technical_indicators.calculate_rsi(closes)
        stoch = self.technical_indicators.calculate_stochastic(highs, lows, closes)
        
        current_price = closes[-1]
        
        # Mean reversion signal logic
        signal_type = "hold"
        confidence = 0.5
        position_side = PositionSide.NEUTRAL
        
        # Oversold condition (buy signal)
        if (current_price <= bb["lower"] and 
            rsi < 30 and 
            stoch["k"] < 20):
            
            signal_type = "buy"
            position_side = PositionSide.LONG
            confidence = min(0.9, 0.6 + (30 - rsi) / 100 + (20 - stoch["k"]) / 100)
        
        # Overbought condition (sell signal)
        elif (current_price >= bb["upper"] and 
              rsi > 70 and 
              stoch["k"] > 80):
            
            signal_type = "sell"
            position_side = PositionSide.SHORT
            confidence = min(0.9, 0.6 + (rsi - 70) / 100 + (stoch["k"] - 80) / 100)
        
        if signal_type == "hold":
            return None
        
        # Calculate technical indicators for signal
        indicators = {
            "rsi": rsi,
            "bollinger_bands": bb,
            "stochastic": stoch,
            "current_price": current_price
        }
        
        strength = self.analysis_engine.calculate_signal_strength(indicators)
        market_condition = self.analysis_engine.analyze_market_condition(market_data)
        
        # Calculate targets (mean reversion targets toward middle of BB)
        if signal_type == "buy":
            entry_price = Decimal(str(current_price))
            target_price = Decimal(str(bb["middle"]))
            stop_loss = Decimal(str(current_price * 0.95))  # 5% stop loss
        else:
            entry_price = Decimal(str(current_price))
            target_price = Decimal(str(bb["middle"]))
            stop_loss = Decimal(str(current_price * 1.05))  # 5% stop loss
        
        return TradingSignal(
            strategy_id=strategy.strategy_id,
            agent_id="mean_reversion_generator",
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            position_side=position_side,
            timeframe="1h",
            market_condition=market_condition,
            technical_indicators=indicators,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
        )
    
    async def generate_breakout_signal(
        self,
        strategy: TradingStrategy,
        market_data: List[MarketData],
        symbol: str
    ) -> Optional[TradingSignal]:
        """Generate breakout trading signal"""
        if len(market_data) < 40:
            return None
        
        closes = [float(data.close) for data in market_data[-40:]]
        highs = [float(data.high) for data in market_data[-40:]]
        lows = [float(data.low) for data in market_data[-40:]]
        volumes = [float(data.volume) for data in market_data[-40:]]
        
        current_price = closes[-1]
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-20:])
        
        # Calculate support and resistance levels
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        
        resistance = max(recent_highs[:-1])  # Exclude current high
        support = min(recent_lows[:-1])      # Exclude current low
        
        # Volume confirmation
        volume_surge = current_volume > avg_volume * 1.5
        
        signal_type = "hold"
        confidence = 0.5
        position_side = PositionSide.NEUTRAL
        
        # Upward breakout
        if current_price > resistance and volume_surge:
            signal_type = "buy"
            position_side = PositionSide.LONG
            confidence = min(0.9, 0.6 + (current_price - resistance) / resistance)
        
        # Downward breakout
        elif current_price < support and volume_surge:
            signal_type = "sell"
            position_side = PositionSide.SHORT
            confidence = min(0.9, 0.6 + (support - current_price) / support)
        
        if signal_type == "hold":
            return None
        
        # Calculate indicators
        bb = self.technical_indicators.calculate_bollinger_bands(closes)
        mas = self.technical_indicators.calculate_moving_averages(closes)
        
        indicators = {
            "resistance": resistance,
            "support": support,
            "volume_ratio": current_volume / avg_volume,
            "bollinger_bands": bb,
            "moving_averages": mas,
            "current_price": current_price
        }
        
        strength = self.analysis_engine.calculate_signal_strength(indicators)
        market_condition = self.analysis_engine.analyze_market_condition(market_data)
        
        # Calculate targets
        if signal_type == "buy":
            entry_price = Decimal(str(current_price))
            target_price = Decimal(str(current_price + (current_price - support)))
            stop_loss = Decimal(str(resistance * 0.99))
        else:
            entry_price = Decimal(str(current_price))
            target_price = Decimal(str(current_price - (resistance - current_price)))
            stop_loss = Decimal(str(support * 1.01))
        
        return TradingSignal(
            strategy_id=strategy.strategy_id,
            agent_id="breakout_generator",
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            position_side=position_side,
            timeframe="1h",
            market_condition=market_condition,
            technical_indicators=indicators,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=6)
        )
    
    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(closes) < period + 1:
            return abs(max(highs) - min(lows)) / len(highs)
        
        df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
        atr = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=period)
        return float(atr.average_true_range().iloc[-1]) if not pd.isna(atr.average_true_range().iloc[-1]) else 1.0


class MarketAnalysisService:
    """
    Intelligent market analysis and signal generation service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.signal_generator = SignalGenerator()
        self.analysis_engine = MarketAnalysisEngine()
        
        # Signal storage
        self.active_signals: Dict[str, TradingSignal] = {}
        self.signal_history: List[TradingSignal] = []
        
        # Market data cache
        self.market_data_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Analysis state
        self.current_regimes: Dict[str, MarketRegime] = {}
        self.pattern_alerts: Dict[str, List[str]] = defaultdict(list)
        
        # Configuration
        self.signal_generation_interval = 300  # 5 minutes
        self.market_analysis_interval = 900    # 15 minutes
        self.data_fetch_interval = 60          # 1 minute
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the market analysis service"""
        try:
            logger.info("Initializing Market Analysis Service...")
            
            # Load active signals from database
            await self._load_active_signals()
            
            # Load recent market data
            await self._load_recent_market_data()
            
            # Start background tasks
            asyncio.create_task(self._signal_generation_loop())
            asyncio.create_task(self._market_analysis_loop())
            asyncio.create_task(self._data_fetch_loop())
            
            logger.info("Market Analysis Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Market Analysis Service: {e}")
            raise
    
    async def generate_signals(self, request: SignalGenerationRequest) -> List[TradingSignal]:
        """Generate trading signals for strategies and symbols"""
        try:
            logger.info(f"Generating signals for {len(request.strategy_ids)} strategies and {len(request.symbols)} symbols")
            
            signals = []
            
            for strategy_id in request.strategy_ids:
                # Get strategy
                strategy = await self._get_strategy_by_id(strategy_id)
                if not strategy:
                    continue
                
                for symbol in request.symbols:
                    # Get market data
                    market_data = await self._get_market_data(symbol, request.timeframe, request.lookback_period)
                    
                    if len(market_data) < 20:
                        continue
                    
                    # Generate signal based on strategy type
                    signal = await self._generate_signal_for_strategy(strategy, market_data, symbol)
                    
                    if signal and signal.confidence >= request.min_confidence:
                        if signal.strength.value in [s.value for s in SignalStrength if s.value >= request.min_signal_strength.value]:
                            signals.append(signal)
                            
                            # Store signal
                            await self._save_signal_to_database(signal)
                            self.active_signals[signal.signal_id] = signal
            
            # Limit results
            signals = sorted(signals, key=lambda s: s.confidence, reverse=True)[:request.max_signals]
            
            logger.info(f"Generated {len(signals)} signals")
            return signals
            
        except Exception as e:
            logger.error(f"Failed to generate signals: {e}")
            raise HTTPException(status_code=500, detail=f"Signal generation failed: {str(e)}")
    
    async def analyze_market_regime(self, symbols: List[str] = None) -> Dict[str, MarketRegime]:
        """Analyze current market regime for symbols"""
        try:
            if not symbols:
                symbols = ["BTCUSD", "ETHUSD"]  # Default major symbols
            
            regimes = {}
            
            for symbol in symbols:
                market_data = await self._get_market_data(symbol, "1h", 100)
                
                if len(market_data) < 50:
                    continue
                
                # Analyze market condition
                condition = self.analysis_engine.analyze_market_condition(market_data)
                
                # Calculate regime characteristics
                closes = [float(data.close) for data in market_data[-50:]]
                returns = np.diff(closes) / closes[:-1]
                volatility = np.std(returns) * np.sqrt(24)
                
                # Determine trend
                short_ma = np.mean(closes[-10:])
                long_ma = np.mean(closes[-30:])
                
                if short_ma > long_ma * 1.02:
                    trend = "up"
                elif short_ma < long_ma * 0.98:
                    trend = "down"
                else:
                    trend = "sideways"
                
                # Classify volatility
                if volatility > 0.05:
                    vol_level = "high"
                elif volatility > 0.02:
                    vol_level = "medium"
                else:
                    vol_level = "low"
                
                # Create regime
                regime = MarketRegime(
                    regime_name=f"{symbol}_{condition.value}_{vol_level}_volatility",
                    market_condition=condition,
                    volatility_level=vol_level,
                    trend_direction=trend,
                    average_volatility=volatility,
                    confidence=0.8  # Would be calculated more sophisticated in production
                )
                
                regimes[symbol] = regime
                self.current_regimes[symbol] = regime
            
            return regimes
            
        except Exception as e:
            logger.error(f"Failed to analyze market regime: {e}")
            return {}
    
    async def detect_arbitrage_opportunities(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Detect arbitrage opportunities across symbols/exchanges"""
        try:
            opportunities = []
            
            # This is a simplified example - real implementation would 
            # check multiple exchanges and more sophisticated arbitrage types
            
            for i, symbol_a in enumerate(symbols):
                for symbol_b in symbols[i+1:]:
                    # Get latest prices
                    data_a = await self._get_latest_market_data(symbol_a)
                    data_b = await self._get_latest_market_data(symbol_b)
                    
                    if not data_a or not data_b:
                        continue
                    
                    price_a = float(data_a.close)
                    price_b = float(data_b.close)
                    
                    # Simple price differential check
                    if abs(price_a - price_b) / min(price_a, price_b) > 0.01:  # 1% threshold
                        
                        spread = abs(price_a - price_b) / min(price_a, price_b)
                        
                        opportunity = {
                            "type": "spatial",
                            "symbol_pair": [symbol_a, symbol_b],
                            "price_differential": abs(price_a - price_b),
                            "percentage_spread": spread * 100,
                            "expected_profit": min(data_a.volume, data_b.volume) * abs(price_a - price_b) * 0.5,
                            "confidence": 0.7,
                            "detected_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        opportunities.append(opportunity)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Failed to detect arbitrage opportunities: {e}")
            return []
    
    async def get_signal_analytics(self, strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """Get signal generation analytics"""
        try:
            # Filter signals by strategy if specified
            signals = self.signal_history
            if strategy_id:
                signals = [s for s in signals if s.strategy_id == strategy_id]
            
            if not signals:
                return {"error": "No signals found"}
            
            # Calculate analytics
            total_signals = len(signals)
            
            # Signal type distribution
            signal_types = defaultdict(int)
            for signal in signals:
                signal_types[signal.signal_type] += 1
            
            # Strength distribution
            strength_dist = defaultdict(int)
            for signal in signals:
                strength_dist[signal.strength.value] += 1
            
            # Average confidence
            avg_confidence = sum(s.confidence for s in signals) / total_signals
            
            # Recent performance (simplified)
            recent_signals = [s for s in signals if 
                            (datetime.now(timezone.utc) - s.generated_at).days <= 7]
            
            return {
                "total_signals": total_signals,
                "recent_signals": len(recent_signals),
                "signal_type_distribution": dict(signal_types),
                "strength_distribution": dict(strength_dist),
                "average_confidence": round(avg_confidence, 3),
                "active_signals": len(self.active_signals),
                "symbols_covered": len(set(s.symbol for s in signals)),
                "strategies_active": len(set(s.strategy_id for s in signals))
            }
            
        except Exception as e:
            logger.error(f"Failed to get signal analytics: {e}")
            return {"error": str(e)}
    
    # Background service loops
    
    async def _signal_generation_loop(self):
        """Main signal generation loop"""
        while not self._shutdown:
            try:
                # Get active strategies
                strategies = await self._get_active_strategies()
                
                for strategy in strategies:
                    # Get symbols for strategy
                    symbols = strategy.symbols if strategy.symbols else ["BTCUSD", "ETHUSD"]
                    
                    for symbol in symbols[:5]:  # Limit to 5 symbols per strategy
                        try:
                            market_data = await self._get_market_data(symbol, "1h", 100)
                            signal = await self._generate_signal_for_strategy(strategy, market_data, symbol)
                            
                            if signal and signal.confidence >= 0.6:
                                await self._save_signal_to_database(signal)
                                self.active_signals[signal.signal_id] = signal
                                
                        except Exception as e:
                            logger.error(f"Error generating signal for {strategy.name} on {symbol}: {e}")
                
                await asyncio.sleep(self.signal_generation_interval)
                
            except Exception as e:
                logger.error(f"Error in signal generation loop: {e}")
                await asyncio.sleep(self.signal_generation_interval)
    
    async def _market_analysis_loop(self):
        """Market analysis and regime detection loop"""
        while not self._shutdown:
            try:
                # Analyze market regimes
                await self.analyze_market_regime(["BTCUSD", "ETHUSD", "ADAUSD", "SOLUSD"])
                
                # Detect patterns and anomalies
                await self._detect_market_patterns()
                
                await asyncio.sleep(self.market_analysis_interval)
                
            except Exception as e:
                logger.error(f"Error in market analysis loop: {e}")
                await asyncio.sleep(self.market_analysis_interval)
    
    async def _data_fetch_loop(self):
        """Market data fetching loop"""
        while not self._shutdown:
            try:
                # Fetch latest market data for cached symbols
                symbols = list(self.market_data_cache.keys()) or ["BTCUSD", "ETHUSD"]
                
                for symbol in symbols:
                    await self._fetch_latest_market_data(symbol)
                
                await asyncio.sleep(self.data_fetch_interval)
                
            except Exception as e:
                logger.error(f"Error in data fetch loop: {e}")
                await asyncio.sleep(self.data_fetch_interval)
    
    # Helper methods
    
    async def _generate_signal_for_strategy(
        self,
        strategy: TradingStrategy,
        market_data: List[MarketData],
        symbol: str
    ) -> Optional[TradingSignal]:
        """Generate signal based on strategy type"""
        try:
            if strategy.strategy_type == StrategyType.MOMENTUM:
                return await self.signal_generator.generate_momentum_signal(strategy, market_data, symbol)
            elif strategy.strategy_type == StrategyType.MEAN_REVERSION:
                return await self.signal_generator.generate_mean_reversion_signal(strategy, market_data, symbol)
            elif strategy.strategy_type == StrategyType.BREAKOUT:
                return await self.signal_generator.generate_breakout_signal(strategy, market_data, symbol)
            else:
                # Default to momentum for other strategy types
                return await self.signal_generator.generate_momentum_signal(strategy, market_data, symbol)
                
        except Exception as e:
            logger.error(f"Error generating signal for strategy {strategy.name}: {e}")
            return None
    
    # Additional helper methods would be implemented here...
    
    async def _get_strategy_by_id(self, strategy_id: str) -> Optional[TradingStrategy]:
        """Get strategy from database"""
        # Implementation would load from Supabase
        return None
    
    async def _get_market_data(self, symbol: str, timeframe: str, limit: int) -> List[MarketData]:
        """Get market data from cache or external source"""
        # Implementation would fetch from market data provider or cache
        return []
    
    # Additional methods continue here...


# Global service instance
_market_analysis_service: Optional[MarketAnalysisService] = None


async def get_market_analysis_service() -> MarketAnalysisService:
    """Get the global market analysis service instance"""
    global _market_analysis_service
    
    if _market_analysis_service is None:
        _market_analysis_service = MarketAnalysisService()
        await _market_analysis_service.initialize()
    
    return _market_analysis_service


@asynccontextmanager
async def market_analysis_context():
    """Context manager for market analysis service"""
    service = await get_market_analysis_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass