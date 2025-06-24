"""
Market Regime Detection Service - Phase 5 Implementation
Advanced market regime detection using machine learning and technical indicators
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Literal, Tuple
from loguru import logger
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum
import asyncio
from collections import deque
import json

class MarketRegime(str, Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    RECOVERY = "recovery"
    UNDETERMINED = "undetermined"

class RegimeConfidence(str, Enum):
    """Confidence levels for regime detection"""
    VERY_LOW = "very_low"      # < 0.3
    LOW = "low"                # 0.3 - 0.5
    MEDIUM = "medium"          # 0.5 - 0.7
    HIGH = "high"              # 0.7 - 0.85
    VERY_HIGH = "very_high"    # > 0.85

class RegimeDetection(BaseModel):
    """Market regime detection result"""
    symbol: str
    regime: MarketRegime
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: RegimeConfidence
    timeframe: str = "1d"
    
    # Supporting indicators
    trend_strength: float = 0.0
    volatility_level: float = 0.0
    momentum_score: float = 0.0
    volume_profile: str = "normal"
    
    # Technical indicators
    indicators: Dict[str, float] = Field(default_factory=dict)
    
    # Metadata
    detection_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_points_used: int = 0
    regime_duration_days: Optional[float] = None

class RegimeChange(BaseModel):
    """Market regime change event"""
    symbol: str
    previous_regime: MarketRegime
    new_regime: MarketRegime
    change_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float
    trigger_indicators: List[str] = Field(default_factory=list)

@dataclass
class MarketData:
    """Market data structure for regime analysis"""
    symbol: str
    prices: deque  # OHLCV data
    volumes: deque
    timestamps: deque
    indicators: Dict[str, deque]

class MarketRegimeService:
    """
    Advanced market regime detection using multiple technical indicators and ML
    """
    
    def __init__(self):
        self.regime_history: Dict[str, List[RegimeDetection]] = {}
        self.current_regimes: Dict[str, RegimeDetection] = {}
        self.regime_changes: List[RegimeChange] = []
        self.market_data: Dict[str, MarketData] = {}
        
        # Configuration
        self.lookback_periods = {
            "short": 20,    # 20 periods
            "medium": 50,   # 50 periods  
            "long": 200     # 200 periods
        }
        
        self.regime_thresholds = {
            "trend_strength": 0.6,
            "volatility_high": 0.75,
            "volatility_low": 0.25,
            "momentum_strong": 0.7,
            "volume_spike": 2.0
        }
        
        # Start background monitoring
        self.monitoring_active = True
        self._start_regime_monitoring()
        
        logger.info("MarketRegimeService initialized with advanced detection algorithms")
    
    def _start_regime_monitoring(self):
        """Start background regime monitoring"""
        asyncio.create_task(self._regime_monitoring_loop())
    
    async def _regime_monitoring_loop(self):
        """Main regime monitoring loop"""
        while self.monitoring_active:
            try:
                await self._update_all_regime_detections()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in regime monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def add_market_data(self, symbol: str, ohlcv_data: List[Dict[str, Any]]):
        """Add market data for regime analysis"""
        
        if symbol not in self.market_data:
            self.market_data[symbol] = MarketData(
                symbol=symbol,
                prices=deque(maxlen=500),  # Keep last 500 data points
                volumes=deque(maxlen=500),
                timestamps=deque(maxlen=500),
                indicators={}
            )
        
        market_data = self.market_data[symbol]
        
        for data_point in ohlcv_data:
            # Add OHLCV data
            market_data.prices.append({
                'open': data_point.get('open', 0),
                'high': data_point.get('high', 0),
                'low': data_point.get('low', 0),
                'close': data_point.get('close', 0)
            })
            market_data.volumes.append(data_point.get('volume', 0))
            market_data.timestamps.append(data_point.get('timestamp', datetime.now(timezone.utc)))
        
        # Calculate indicators after adding data
        await self._calculate_indicators(symbol)
        
        logger.debug(f"Added {len(ohlcv_data)} data points for {symbol}")
    
    async def _calculate_indicators(self, symbol: str):
        """Calculate technical indicators for regime detection"""
        
        market_data = self.market_data[symbol]
        if len(market_data.prices) < self.lookback_periods["short"]:
            return  # Not enough data
        
        prices = list(market_data.prices)
        volumes = list(market_data.volumes)
        
        # Convert to pandas for easier calculation
        df = pd.DataFrame(prices)
        df['volume'] = volumes
        
        # Initialize indicator storage
        for indicator in ['sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi', 'atr', 'bb_upper', 'bb_lower', 'macd', 'adx']:
            if indicator not in market_data.indicators:
                market_data.indicators[indicator] = deque(maxlen=500)
        
        # Calculate Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR (Average True Range)
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['prev_close']),
                abs(df['low'] - df['prev_close'])
            )
        )
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
        bb_std_dev = df['close'].rolling(window=bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std_dev * bb_std)
        df['bb_lower'] = df['bb_middle'] - (bb_std_dev * bb_std)
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # ADX (Directional Movement Index)
        df['dm_plus'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                                np.maximum(df['high'] - df['high'].shift(1), 0), 0)
        df['dm_minus'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                                 np.maximum(df['low'].shift(1) - df['low'], 0), 0)
        
        df['di_plus'] = 100 * (df['dm_plus'].rolling(window=14).mean() / df['atr'])
        df['di_minus'] = 100 * (df['dm_minus'].rolling(window=14).mean() / df['atr'])
        df['dx'] = 100 * abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus'])
        df['adx'] = df['dx'].rolling(window=14).mean()
        
        # Store latest values
        latest_row = df.iloc[-1]
        for indicator in market_data.indicators.keys():
            if indicator in latest_row and not pd.isna(latest_row[indicator]):
                market_data.indicators[indicator].append(float(latest_row[indicator]))
    
    async def detect_regime(self, symbol: str, timeframe: str = "1d") -> Optional[RegimeDetection]:
        """Detect current market regime for a symbol"""
        
        if symbol not in self.market_data:
            logger.warning(f"No market data available for {symbol}")
            return None
        
        market_data = self.market_data[symbol]
        if len(market_data.prices) < self.lookback_periods["medium"]:
            logger.warning(f"Insufficient data for regime detection: {symbol}")
            return None
        
        # Get recent price data
        recent_prices = list(market_data.prices)[-self.lookback_periods["medium"]:]
        recent_indicators = {
            key: list(values)[-self.lookback_periods["medium"]:] if values else []
            for key, values in market_data.indicators.items()
        }
        
        # Calculate regime features
        regime_features = await self._calculate_regime_features(recent_prices, recent_indicators)
        
        # Classify regime
        regime, confidence = await self._classify_regime(regime_features)
        
        # Determine confidence level
        confidence_level = self._get_confidence_level(confidence)
        
        # Calculate additional metrics
        trend_strength = regime_features.get('trend_strength', 0.0)
        volatility_level = regime_features.get('volatility_level', 0.0)
        momentum_score = regime_features.get('momentum_score', 0.0)
        volume_profile = regime_features.get('volume_profile', 'normal')
        
        # Create detection result
        detection = RegimeDetection(
            symbol=symbol,
            regime=regime,
            confidence=confidence,
            confidence_level=confidence_level,
            timeframe=timeframe,
            trend_strength=trend_strength,
            volatility_level=volatility_level,
            momentum_score=momentum_score,
            volume_profile=volume_profile,
            indicators=regime_features.get('raw_indicators', {}),
            data_points_used=len(recent_prices)
        )
        
        # Calculate regime duration if this is a continuation
        if symbol in self.current_regimes:
            previous = self.current_regimes[symbol]
            if previous.regime == regime:
                time_diff = detection.detection_time - previous.detection_time
                detection.regime_duration_days = time_diff.total_seconds() / 86400  # Convert to days
        
        # Check for regime changes
        await self._check_regime_change(symbol, detection)
        
        # Store current regime
        self.current_regimes[symbol] = detection
        
        # Add to history
        if symbol not in self.regime_history:
            self.regime_history[symbol] = []
        self.regime_history[symbol].append(detection)
        
        # Keep only recent history (last 100 detections)
        if len(self.regime_history[symbol]) > 100:
            self.regime_history[symbol] = self.regime_history[symbol][-100:]
        
        logger.debug(f"Detected regime for {symbol}: {regime.value} (confidence: {confidence:.3f})")
        return detection
    
    async def _calculate_regime_features(self, prices: List[Dict], indicators: Dict[str, List]) -> Dict[str, Any]:
        """Calculate features used for regime classification"""
        
        closes = [p['close'] for p in prices]
        highs = [p['high'] for p in prices]
        lows = [p['low'] for p in prices]
        
        features = {}
        
        # Trend features
        if len(closes) >= 20:
            sma_20 = np.mean(closes[-20:])
            sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else sma_20
            
            current_price = closes[-1]
            trend_strength = (current_price - sma_50) / sma_50 if sma_50 > 0 else 0
            
            # Trend direction consistency
            price_changes = np.diff(closes[-20:])
            positive_changes = np.sum(price_changes > 0)
            trend_consistency = positive_changes / len(price_changes) if len(price_changes) > 0 else 0.5
            
            features['trend_strength'] = trend_strength
            features['trend_consistency'] = trend_consistency
            features['price_vs_sma20'] = (current_price - sma_20) / sma_20 if sma_20 > 0 else 0
            features['sma20_vs_sma50'] = (sma_20 - sma_50) / sma_50 if sma_50 > 0 else 0
        
        # Volatility features
        if len(closes) >= 20:
            returns = np.diff(np.log(closes[-20:]))
            volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
            
            # ATR-based volatility
            if 'atr' in indicators and indicators['atr']:
                atr_volatility = indicators['atr'][-1] / closes[-1] if closes[-1] > 0 else 0
                features['atr_volatility'] = atr_volatility
            
            features['volatility_level'] = volatility
            features['volatility_percentile'] = self._calculate_percentile(volatility, returns)
        
        # Momentum features
        if 'rsi' in indicators and indicators['rsi']:
            rsi = indicators['rsi'][-1]
            features['rsi'] = rsi
            features['rsi_momentum'] = (rsi - 50) / 50  # Normalized momentum
        
        if 'macd' in indicators and indicators['macd']:
            macd = indicators['macd'][-1]
            features['macd'] = macd
            features['momentum_score'] = np.tanh(macd / closes[-1]) if closes[-1] > 0 else 0
        
        # ADX for trend strength
        if 'adx' in indicators and indicators['adx']:
            adx = indicators['adx'][-1]
            features['adx'] = adx
            features['trend_strength_adx'] = min(adx / 50, 1.0)  # Normalized ADX
        
        # Bollinger Bands position
        if 'bb_upper' in indicators and 'bb_lower' in indicators:
            if indicators['bb_upper'] and indicators['bb_lower']:
                bb_upper = indicators['bb_upper'][-1]
                bb_lower = indicators['bb_lower'][-1]
                bb_position = (closes[-1] - bb_lower) / (bb_upper - bb_lower) if bb_upper > bb_lower else 0.5
                features['bb_position'] = bb_position
        
        # Volume analysis
        if len(prices) >= 20:
            # This would require volume data integration
            features['volume_profile'] = 'normal'  # Placeholder
        
        # Raw indicators for storage
        features['raw_indicators'] = {
            key: values[-1] if values else 0 
            for key, values in indicators.items()
        }
        
        return features
    
    def _calculate_percentile(self, value: float, data_series: np.ndarray) -> float:
        """Calculate percentile of value within data series"""
        if len(data_series) == 0:
            return 0.5
        return (np.sum(data_series <= value) / len(data_series))
    
    async def _classify_regime(self, features: Dict[str, Any]) -> Tuple[MarketRegime, float]:
        """Classify market regime based on calculated features"""
        
        # Get key features with defaults
        trend_strength = features.get('trend_strength', 0.0)
        volatility_level = features.get('volatility_level', 0.0)
        trend_consistency = features.get('trend_consistency', 0.5)
        momentum_score = features.get('momentum_score', 0.0)
        adx = features.get('adx', 20.0)
        rsi = features.get('rsi', 50.0)
        
        # Regime classification logic
        confidence_factors = []
        
        # High volatility regimes
        if volatility_level > self.regime_thresholds['volatility_high']:
            if abs(trend_strength) > 0.3:
                regime = MarketRegime.VOLATILE
                confidence_factors.append(min(volatility_level / self.regime_thresholds['volatility_high'], 1.0))
            else:
                regime = MarketRegime.RANGING
                confidence_factors.append(0.6)
        
        # Low volatility regimes
        elif volatility_level < self.regime_thresholds['volatility_low']:
            regime = MarketRegime.LOW_VOLATILITY
            confidence_factors.append(1.0 - volatility_level / self.regime_thresholds['volatility_low'])
        
        # Trending regimes
        elif abs(trend_strength) > self.regime_thresholds['trend_strength'] and adx > 25:
            if trend_strength > 0:
                regime = MarketRegime.TRENDING_UP
            else:
                regime = MarketRegime.TRENDING_DOWN
            
            confidence_factors.append(min(abs(trend_strength) / self.regime_thresholds['trend_strength'], 1.0))
            confidence_factors.append(min(adx / 50, 1.0))
            confidence_factors.append(abs(trend_consistency - 0.5) * 2)  # Distance from neutral
        
        # Breakout/Breakdown detection
        elif abs(momentum_score) > self.regime_thresholds['momentum_strong']:
            if momentum_score > 0 and rsi > 70:
                regime = MarketRegime.BREAKOUT
            elif momentum_score < 0 and rsi < 30:
                regime = MarketRegime.BREAKDOWN
            else:
                regime = MarketRegime.VOLATILE
            
            confidence_factors.append(min(abs(momentum_score) / self.regime_thresholds['momentum_strong'], 1.0))
        
        # Recovery regime
        elif trend_strength > 0.2 and rsi > 40 and rsi < 60 and momentum_score > 0.1:
            regime = MarketRegime.RECOVERY
            confidence_factors.append(0.7)
        
        # Ranging market
        elif abs(trend_strength) < 0.2 and volatility_level < 0.5:
            regime = MarketRegime.RANGING
            confidence_factors.append(1.0 - abs(trend_strength) / 0.2)
        
        # Default to undetermined
        else:
            regime = MarketRegime.UNDETERMINED
            confidence_factors.append(0.3)
        
        # Calculate overall confidence
        confidence = np.mean(confidence_factors) if confidence_factors else 0.5
        confidence = max(0.1, min(0.95, confidence))  # Bound between 0.1 and 0.95
        
        return regime, confidence
    
    def _get_confidence_level(self, confidence: float) -> RegimeConfidence:
        """Convert numeric confidence to categorical level"""
        if confidence < 0.3:
            return RegimeConfidence.VERY_LOW
        elif confidence < 0.5:
            return RegimeConfidence.LOW
        elif confidence < 0.7:
            return RegimeConfidence.MEDIUM
        elif confidence < 0.85:
            return RegimeConfidence.HIGH
        else:
            return RegimeConfidence.VERY_HIGH
    
    async def _check_regime_change(self, symbol: str, new_detection: RegimeDetection):
        """Check for regime changes and record them"""
        
        if symbol not in self.current_regimes:
            return  # First detection
        
        previous = self.current_regimes[symbol]
        
        # Check if regime has changed
        if previous.regime != new_detection.regime:
            # Require minimum confidence for regime changes
            if new_detection.confidence >= 0.6:
                change = RegimeChange(
                    symbol=symbol,
                    previous_regime=previous.regime,
                    new_regime=new_detection.regime,
                    confidence=new_detection.confidence,
                    trigger_indicators=self._identify_trigger_indicators(previous, new_detection)
                )
                
                self.regime_changes.append(change)
                
                # Keep only recent changes (last 100)
                if len(self.regime_changes) > 100:
                    self.regime_changes = self.regime_changes[-100:]
                
                logger.info(f"Regime change detected for {symbol}: {previous.regime.value} → {new_detection.regime.value} (confidence: {new_detection.confidence:.3f})")
    
    def _identify_trigger_indicators(self, previous: RegimeDetection, current: RegimeDetection) -> List[str]:
        """Identify which indicators triggered the regime change"""
        triggers = []
        
        # Check for significant changes in key indicators
        prev_indicators = previous.indicators
        curr_indicators = current.indicators
        
        for indicator in ['rsi', 'macd', 'adx']:
            if indicator in prev_indicators and indicator in curr_indicators:
                prev_val = prev_indicators[indicator]
                curr_val = curr_indicators[indicator]
                
                # Check for significant change (>20% relative change)
                if abs(curr_val - prev_val) / max(abs(prev_val), 1) > 0.2:
                    triggers.append(indicator)
        
        # Check trend strength change
        if abs(current.trend_strength - previous.trend_strength) > 0.3:
            triggers.append('trend_strength')
        
        # Check volatility change
        if abs(current.volatility_level - previous.volatility_level) > 0.2:
            triggers.append('volatility')
        
        return triggers
    
    async def _update_all_regime_detections(self):
        """Update regime detections for all tracked symbols"""
        
        for symbol in self.market_data.keys():
            try:
                await self.detect_regime(symbol)
            except Exception as e:
                logger.error(f"Error updating regime for {symbol}: {e}")
    
    async def get_regime_for_symbol(self, symbol: str) -> Optional[RegimeDetection]:
        """Get current regime for a specific symbol"""
        return self.current_regimes.get(symbol)
    
    async def get_regime_history(self, symbol: str, limit: int = 50) -> List[RegimeDetection]:
        """Get regime history for a symbol"""
        history = self.regime_history.get(symbol, [])
        return history[-limit:] if limit else history
    
    async def get_recent_regime_changes(self, symbol: Optional[str] = None, limit: int = 20) -> List[RegimeChange]:
        """Get recent regime changes"""
        changes = self.regime_changes
        
        if symbol:
            changes = [c for c in changes if c.symbol == symbol]
        
        return changes[-limit:] if limit else changes
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get market regime service status"""
        
        regime_summary = {}
        for regime in MarketRegime:
            count = sum(1 for detection in self.current_regimes.values() if detection.regime == regime)
            regime_summary[regime.value] = count
        
        return {
            "service_status": "active" if self.monitoring_active else "inactive",
            "tracked_symbols": len(self.market_data),
            "current_regimes": regime_summary,
            "total_regime_changes": len(self.regime_changes),
            "detection_coverage": {
                symbol: len(data.prices) for symbol, data in self.market_data.items()
            },
            "last_update": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_market_regime_service() -> MarketRegimeService:
    """Factory function to create market regime service"""
    return MarketRegimeService()