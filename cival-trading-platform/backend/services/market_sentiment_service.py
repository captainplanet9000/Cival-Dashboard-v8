"""
Market Sentiment Analysis Service
Advanced sentiment analysis using multiple data sources and LLM processing
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from loguru import logger
import json
import re

from python_ai_services.models.enhanced_market_data_models import MarketSentiment, MarketAlert
from python_ai_services.services.enhanced_market_data_service import EnhancedMarketDataService

class MarketSentimentService:
    """
    Market Sentiment Analysis Service
    Analyzes market sentiment from multiple sources including news, social media, and technical indicators
    """
    
    def __init__(self, market_data_service: EnhancedMarketDataService):
        self.market_data_service = market_data_service
        self.sentiment_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Sentiment data sources
        self.data_sources = {
            "fear_greed_index": True,
            "crypto_sentiment": True,
            "technical_sentiment": True,
            "social_sentiment": False,  # Requires additional APIs
            "news_sentiment": False     # Requires news APIs
        }
    
    async def get_market_sentiment(self, symbol: str) -> Optional[MarketSentiment]:
        """Get comprehensive market sentiment for a symbol"""
        try:
            # Check cache first
            cache_key = f"sentiment_{symbol}"
            if cache_key in self.sentiment_cache:
                cached_data = self.sentiment_cache[cache_key]
                if (datetime.utcnow() - cached_data["timestamp"]).total_seconds() < self.cache_ttl:
                    return cached_data["sentiment"]
            
            # Calculate sentiment from multiple sources
            sentiment_scores = []
            confidence_scores = []
            
            # Technical sentiment from indicators
            technical_sentiment = await self._get_technical_sentiment(symbol)
            if technical_sentiment is not None:
                sentiment_scores.append(technical_sentiment)
                confidence_scores.append(0.7)
            
            # Fear & Greed Index (for broader market)
            if symbol in ["SPY", "QQQ", "BTC-USD", "ETH-USD"]:
                fear_greed = await self._get_fear_greed_sentiment(symbol)
                if fear_greed is not None:
                    sentiment_scores.append(fear_greed)
                    confidence_scores.append(0.6)
            
            # Volume-based sentiment
            volume_sentiment = await self._get_volume_sentiment(symbol)
            if volume_sentiment is not None:
                sentiment_scores.append(volume_sentiment)
                confidence_scores.append(0.5)
            
            # Price action sentiment
            price_sentiment = await self._get_price_action_sentiment(symbol)
            if price_sentiment is not None:
                sentiment_scores.append(price_sentiment)
                confidence_scores.append(0.6)
            
            if not sentiment_scores:
                return None
            
            # Calculate weighted average sentiment
            weighted_sentiment = sum(score * weight for score, weight in zip(sentiment_scores, confidence_scores))
            total_weight = sum(confidence_scores)
            final_sentiment = weighted_sentiment / total_weight if total_weight > 0 else 0
            
            # Calculate overall confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            sentiment = MarketSentiment(
                symbol=symbol,
                sentiment_score=Decimal(str(round(final_sentiment, 3))),
                fear_greed_index=None,  # Would be populated from actual API
                social_sentiment=None,   # Would be populated from social APIs
                news_sentiment=None,     # Would be populated from news APIs
                timestamp=datetime.utcnow(),
                confidence=Decimal(str(round(avg_confidence, 3)))
            )
            
            # Cache the result
            self.sentiment_cache[cache_key] = {
                "sentiment": sentiment,
                "timestamp": datetime.utcnow()
            }
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Error getting market sentiment for {symbol}: {e}")
            return None
    
    async def _get_technical_sentiment(self, symbol: str) -> Optional[float]:
        """Calculate sentiment from technical indicators"""
        try:
            # Get technical indicators
            indicators = await self.market_data_service.get_technical_analysis(symbol)
            if not indicators:
                return None
            
            sentiment_factors = []
            
            # RSI sentiment
            if indicators.rsi is not None:
                rsi = float(indicators.rsi)
                if rsi < 30:
                    sentiment_factors.append(-0.7)  # Oversold (bearish short-term, bullish contrarian)
                elif rsi > 70:
                    sentiment_factors.append(-0.5)  # Overbought (bearish)
                elif 40 <= rsi <= 60:
                    sentiment_factors.append(0.0)   # Neutral
                elif 30 <= rsi <= 40:
                    sentiment_factors.append(0.3)   # Moderately bullish
                elif 60 <= rsi <= 70:
                    sentiment_factors.append(0.5)   # Bullish
            
            # MACD sentiment
            if indicators.macd is not None and indicators.macd_signal is not None:
                macd_diff = float(indicators.macd) - float(indicators.macd_signal)
                if macd_diff > 0:
                    sentiment_factors.append(0.4)   # Bullish crossover
                else:
                    sentiment_factors.append(-0.4)  # Bearish crossover
            
            # Moving Average sentiment
            if indicators.sma_20 is not None and indicators.sma_50 is not None:
                sma_20 = float(indicators.sma_20)
                sma_50 = float(indicators.sma_50)
                if sma_20 > sma_50:
                    sentiment_factors.append(0.5)   # Golden cross (bullish)
                else:
                    sentiment_factors.append(-0.5)  # Death cross (bearish)
            
            # Bollinger Bands sentiment
            if all([indicators.bollinger_upper, indicators.bollinger_middle, indicators.bollinger_lower]):
                # This would need current price for proper calculation
                # For now, we'll use a neutral sentiment
                sentiment_factors.append(0.0)
            
            if not sentiment_factors:
                return None
            
            # Average the sentiment factors
            avg_sentiment = sum(sentiment_factors) / len(sentiment_factors)
            
            # Normalize to -1 to 1 range
            return max(-1.0, min(1.0, avg_sentiment))
            
        except Exception as e:
            logger.error(f"Error calculating technical sentiment for {symbol}: {e}")
            return None
    
    async def _get_fear_greed_sentiment(self, symbol: str) -> Optional[float]:
        """Get Fear & Greed Index sentiment (simplified implementation)"""
        try:
            # This would integrate with CNN Fear & Greed Index API
            # For now, we'll calculate a simplified version based on market conditions
            
            # Get recent price action
            historical_data = await self.market_data_service.get_historical_data(symbol, days=30)
            if not historical_data or len(historical_data) < 20:
                return None
            
            # Calculate volatility
            prices = [float(candle.close) for candle in historical_data]
            returns = [(prices[i] / prices[i-1]) - 1 for i in range(1, len(prices))]
            volatility = sum(abs(r) for r in returns) / len(returns)
            
            # Calculate trend
            recent_return = (prices[-1] / prices[-10]) - 1 if len(prices) >= 10 else 0
            
            # Simple fear/greed calculation
            if volatility > 0.03 and recent_return < -0.05:
                return -0.6  # High fear
            elif volatility > 0.02 and recent_return < 0:
                return -0.3  # Moderate fear
            elif volatility < 0.01 and recent_return > 0.05:
                return 0.6   # Greed
            elif recent_return > 0.02:
                return 0.3   # Moderate greed
            else:
                return 0.0   # Neutral
            
        except Exception as e:
            logger.error(f"Error calculating fear/greed sentiment for {symbol}: {e}")
            return None
    
    async def _get_volume_sentiment(self, symbol: str) -> Optional[float]:
        """Calculate sentiment from volume patterns"""
        try:
            # Get recent volume data
            historical_data = await self.market_data_service.get_historical_data(symbol, days=20)
            if not historical_data or len(historical_data) < 10:
                return None
            
            volumes = [float(candle.volume) for candle in historical_data]
            prices = [float(candle.close) for candle in historical_data]
            
            # Calculate average volume
            avg_volume = sum(volumes[-10:]) / 10
            recent_volume = volumes[-1]
            
            # Calculate price change
            price_change = (prices[-1] / prices[-2]) - 1 if len(prices) >= 2 else 0
            
            # Volume sentiment logic
            if recent_volume > avg_volume * 1.5:  # High volume
                if price_change > 0.02:  # Price up on high volume (bullish)
                    return 0.7
                elif price_change < -0.02:  # Price down on high volume (bearish)
                    return -0.7
                else:
                    return 0.0  # High volume, no clear direction
            elif recent_volume < avg_volume * 0.5:  # Low volume
                return -0.2  # Low volume generally bearish
            else:
                return 0.0  # Normal volume
            
        except Exception as e:
            logger.error(f"Error calculating volume sentiment for {symbol}: {e}")
            return None
    
    async def _get_price_action_sentiment(self, symbol: str) -> Optional[float]:
        """Calculate sentiment from price action patterns"""
        try:
            # Get recent price data
            historical_data = await self.market_data_service.get_historical_data(symbol, days=10)
            if not historical_data or len(historical_data) < 5:
                return None
            
            closes = [float(candle.close) for candle in historical_data]
            highs = [float(candle.high) for candle in historical_data]
            lows = [float(candle.low) for candle in historical_data]
            
            sentiment_factors = []
            
            # Recent trend
            short_trend = (closes[-1] / closes[-3]) - 1 if len(closes) >= 3 else 0
            medium_trend = (closes[-1] / closes[-5]) - 1 if len(closes) >= 5 else 0
            
            sentiment_factors.append(short_trend * 10)  # Amplify short-term moves
            sentiment_factors.append(medium_trend * 5)  # Medium-term trend
            
            # Higher highs and higher lows (bullish pattern)
            if len(closes) >= 4:
                recent_highs = highs[-3:]
                recent_lows = lows[-3:]
                
                if all(recent_highs[i] >= recent_highs[i-1] for i in range(1, len(recent_highs))):
                    sentiment_factors.append(0.3)  # Higher highs
                
                if all(recent_lows[i] >= recent_lows[i-1] for i in range(1, len(recent_lows))):
                    sentiment_factors.append(0.3)  # Higher lows
            
            # Price position in recent range
            recent_high = max(highs[-5:]) if len(highs) >= 5 else highs[-1]
            recent_low = min(lows[-5:]) if len(lows) >= 5 else lows[-1]
            current_price = closes[-1]
            
            if recent_high != recent_low:
                price_position = (current_price - recent_low) / (recent_high - recent_low)
                sentiment_factors.append((price_position - 0.5) * 0.4)  # -0.2 to +0.2
            
            if not sentiment_factors:
                return None
            
            # Average and normalize
            avg_sentiment = sum(sentiment_factors) / len(sentiment_factors)
            return max(-1.0, min(1.0, avg_sentiment))
            
        except Exception as e:
            logger.error(f"Error calculating price action sentiment for {symbol}: {e}")
            return None
    
    async def get_market_sentiment_overview(self, symbols: List[str]) -> Dict[str, MarketSentiment]:
        """Get sentiment overview for multiple symbols"""
        try:
            results = {}
            
            # Process symbols in batches to avoid overwhelming APIs
            batch_size = 5
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                
                # Get sentiment for each symbol in batch
                batch_tasks = [self.get_market_sentiment(symbol) for symbol in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process results
                for symbol, result in zip(batch, batch_results):
                    if isinstance(result, MarketSentiment):
                        results[symbol] = result
                    elif isinstance(result, Exception):
                        logger.warning(f"Error getting sentiment for {symbol}: {result}")
                    # None results are ignored
                
                # Small delay between batches
                if i + batch_size < len(symbols):
                    await asyncio.sleep(0.5)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting market sentiment overview: {e}")
            return {}
    
    async def detect_sentiment_alerts(self, symbols: List[str]) -> List[MarketAlert]:
        """Detect significant sentiment changes that warrant alerts"""
        try:
            alerts = []
            
            sentiment_overview = await self.get_market_sentiment_overview(symbols)
            
            for symbol, sentiment in sentiment_overview.items():
                try:
                    # Check for extreme sentiment
                    if sentiment.sentiment_score <= Decimal("-0.7"):
                        alerts.append(MarketAlert(
                            alert_id=f"sentiment_extreme_bearish_{symbol}_{int(datetime.utcnow().timestamp())}",
                            symbol=symbol,
                            alert_type="SENTIMENT_EXTREME",
                            message=f"Extreme bearish sentiment detected for {symbol} ({sentiment.sentiment_score:.2f})",
                            severity="HIGH",
                            timestamp=datetime.utcnow(),
                            data={
                                "sentiment_score": float(sentiment.sentiment_score),
                                "confidence": float(sentiment.confidence),
                                "direction": "bearish"
                            }
                        ))
                    
                    elif sentiment.sentiment_score >= Decimal("0.7"):
                        alerts.append(MarketAlert(
                            alert_id=f"sentiment_extreme_bullish_{symbol}_{int(datetime.utcnow().timestamp())}",
                            symbol=symbol,
                            alert_type="SENTIMENT_EXTREME",
                            message=f"Extreme bullish sentiment detected for {symbol} ({sentiment.sentiment_score:.2f})",
                            severity="HIGH",
                            timestamp=datetime.utcnow(),
                            data={
                                "sentiment_score": float(sentiment.sentiment_score),
                                "confidence": float(sentiment.confidence),
                                "direction": "bullish"
                            }
                        ))
                    
                    # Check for high confidence sentiment with moderate strength
                    elif sentiment.confidence >= Decimal("0.8") and abs(sentiment.sentiment_score) >= Decimal("0.4"):
                        direction = "bullish" if sentiment.sentiment_score > 0 else "bearish"
                        alerts.append(MarketAlert(
                            alert_id=f"sentiment_high_confidence_{symbol}_{int(datetime.utcnow().timestamp())}",
                            symbol=symbol,
                            alert_type="SENTIMENT_SIGNAL",
                            message=f"High confidence {direction} sentiment for {symbol} ({sentiment.sentiment_score:.2f})",
                            severity="MEDIUM",
                            timestamp=datetime.utcnow(),
                            data={
                                "sentiment_score": float(sentiment.sentiment_score),
                                "confidence": float(sentiment.confidence),
                                "direction": direction
                            }
                        ))
                
                except Exception as e:
                    logger.warning(f"Error processing sentiment alert for {symbol}: {e}")
                    continue
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error detecting sentiment alerts: {e}")
            return []
    
    def clear_cache(self):
        """Clear sentiment cache"""
        self.sentiment_cache.clear()
        logger.info("Sentiment cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.sentiment_cache),
            "cache_ttl": self.cache_ttl,
            "data_sources": self.data_sources,
            "last_cleared": datetime.utcnow().isoformat()
        }