"""
Enhanced Market Data Service
Comprehensive multi-provider market data service with live streaming, technical analysis, and signal generation
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from decimal import Decimal
from loguru import logger
import os

from python_ai_services.providers.base_market_provider import ProviderManager
from python_ai_services.providers.yfinance_provider import YFinanceProvider
from python_ai_services.providers.alpha_vantage_provider import AlphaVantageProvider
from python_ai_services.providers.polygon_provider import PolygonProvider
from python_ai_services.services.technical_analysis_service import TechnicalAnalysisService
from python_ai_services.models.enhanced_market_data_models import (
    PriceData, OHLCV, MarketQuote, MarketOverview, TechnicalIndicators,
    TradingSignal, MarketSentiment, SymbolSummary, PortfolioMarketData,
    MarketDataProvider, TimeFrame, StreamUpdate, MarketAlert
)

class EnhancedMarketDataService:
    """
    Enhanced Market Data Service
    Provides comprehensive market data with multi-provider support, technical analysis, and signal generation
    """
    
    def __init__(self):
        self.provider_manager = ProviderManager()
        self.technical_analysis = TechnicalAnalysisService()
        self.watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "BTC-USD", "ETH-USD", "SPY"]
        self.active_streams = {}
        self.market_cache = {}
        
        # Initialize providers
        self._setup_providers()
        
    def _setup_providers(self):
        """Initialize and register market data providers"""
        try:
            # Always register YFinance as primary (free)
            yfinance_provider = YFinanceProvider()
            self.provider_manager.register_provider(yfinance_provider, is_primary=True)
            logger.info("Registered YFinance provider as primary")
            
            # Register Alpha Vantage if API key available
            alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
            if alpha_vantage_key and alpha_vantage_key != "demo":
                alpha_vantage_provider = AlphaVantageProvider(alpha_vantage_key)
                self.provider_manager.register_provider(alpha_vantage_provider)
                logger.info("Registered Alpha Vantage provider")
            
            # Register Polygon if API key available
            polygon_key = os.getenv("POLYGON_API_KEY")
            if polygon_key:
                polygon_provider = PolygonProvider(polygon_key)
                self.provider_manager.register_provider(polygon_provider)
                logger.info("Registered Polygon.io provider")
            
            # Additional providers can be added here (Finnhub, Twelve Data)
            
        except Exception as e:
            logger.error(f"Error setting up providers: {e}")
    
    async def get_real_time_price(self, symbol: str) -> Optional[PriceData]:
        """Get real-time price for a symbol"""
        try:
            return await self.provider_manager.get_quote(symbol)
        except Exception as e:
            logger.error(f"Error getting real-time price for {symbol}: {e}")
            return None
    
    async def get_multiple_quotes(self, symbols: List[str]) -> List[PriceData]:
        """Get real-time quotes for multiple symbols"""
        try:
            return await self.provider_manager.get_quotes(symbols)
        except Exception as e:
            logger.error(f"Error getting multiple quotes: {e}")
            return []
    
    async def get_historical_data(
        self, 
        symbol: str, 
        timeframe: TimeFrame = TimeFrame.D1,
        days: int = 100
    ) -> List[OHLCV]:
        """Get historical OHLCV data"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            return await self.provider_manager.get_historical_data(
                symbol, timeframe, start_time, end_time
            )
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    async def get_technical_analysis(
        self, 
        symbol: str, 
        timeframe: TimeFrame = TimeFrame.D1
    ) -> Optional[TechnicalIndicators]:
        """Get comprehensive technical analysis for a symbol"""
        try:
            # Get historical data
            historical_data = await self.get_historical_data(symbol, timeframe)
            
            if not historical_data:
                return None
            
            # Calculate technical indicators
            indicators = await self.technical_analysis.calculate_indicators(
                symbol, historical_data, timeframe
            )
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error getting technical analysis for {symbol}: {e}")
            return None
    
    async def generate_trading_signals(
        self, 
        symbol: str, 
        timeframe: TimeFrame = TimeFrame.D1
    ) -> List[TradingSignal]:
        """Generate trading signals for a symbol"""
        try:
            # Get current price and technical indicators
            current_price_data = await self.get_real_time_price(symbol)
            technical_indicators = await self.get_technical_analysis(symbol, timeframe)
            
            if not current_price_data or not technical_indicators:
                return []
            
            # Generate signals
            signals = await self.technical_analysis.generate_trading_signals(
                symbol, technical_indicators, current_price_data.price, timeframe
            )
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating trading signals for {symbol}: {e}")
            return []
    
    async def get_symbol_summary(self, symbol: str) -> Optional[SymbolSummary]:
        """Get comprehensive symbol summary with price, indicators, and signals"""
        try:
            # Get current price
            price_data = await self.get_real_time_price(symbol)
            if not price_data:
                return None
            
            # Get technical analysis
            technical_indicators = await self.get_technical_analysis(symbol)
            
            # Generate signals
            signals = await self.generate_trading_signals(symbol)
            
            # Create market sentiment (simplified for now)
            sentiment = MarketSentiment(
                symbol=symbol,
                sentiment_score=Decimal("0.0"),  # Neutral
                timestamp=datetime.utcnow(),
                confidence=Decimal("0.5")
            )
            
            return SymbolSummary(
                symbol=symbol,
                name=symbol,  # Would be enhanced with actual company names
                current_price=price_data.price,
                change_24h=price_data.change or Decimal("0"),
                change_percent_24h=price_data.change_percent or Decimal("0"),
                volume_24h=price_data.volume or Decimal("0"),
                technical_indicators=technical_indicators or TechnicalIndicators(
                    symbol=symbol, timestamp=datetime.utcnow()
                ),
                signals=signals,
                sentiment=sentiment,
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting symbol summary for {symbol}: {e}")
            return None
    
    async def get_portfolio_market_data(self, symbols: List[str]) -> Optional[PortfolioMarketData]:
        """Get comprehensive portfolio market data"""
        try:
            positions = []
            total_value = Decimal("0")
            total_change = Decimal("0")
            
            # Get data for all symbols
            for symbol in symbols:
                summary = await self.get_symbol_summary(symbol)
                if summary:
                    positions.append(summary)
                    # Assuming 1 share for each symbol for demo
                    total_value += summary.current_price
                    total_change += summary.change_24h
            
            if not positions:
                return None
            
            total_change_percent = (total_change / total_value * 100) if total_value > 0 else Decimal("0")
            
            return PortfolioMarketData(
                total_value=total_value,
                total_change=total_change,
                total_change_percent=total_change_percent,
                positions=positions,
                sector_allocation={},  # Would be enhanced with sector data
                risk_metrics={
                    "volatility": Decimal("0.15"),
                    "beta": Decimal("1.0"),
                    "sharpe_ratio": Decimal("1.2")
                },
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting portfolio market data: {e}")
            return None
    
    async def get_market_overview(self) -> Optional[MarketOverview]:
        """Get overall market overview"""
        try:
            # Get major indices
            major_symbols = ["SPY", "QQQ", "IWM", "DIA"]
            quotes = await self.get_multiple_quotes(major_symbols)
            
            major_indices = {}
            for quote in quotes:
                major_indices[quote.symbol] = quote.price
            
            # Get trending symbols (simplified)
            trending = await self.get_multiple_quotes(self.watchlist[:5])
            trending_symbols = [quote.symbol for quote in trending if quote.change_percent and quote.change_percent > 2]
            
            return MarketOverview(
                timestamp=datetime.utcnow(),
                market_status="OPEN",  # Simplified
                major_indices=major_indices,
                market_sentiment=Decimal("0.1"),  # Slightly bullish
                trending_symbols=trending_symbols,
                top_gainers=trending_symbols[:3],
                top_losers=[],
                sector_performance={
                    "Technology": Decimal("0.015"),
                    "Healthcare": Decimal("-0.005"),
                    "Finance": Decimal("0.008")
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting market overview: {e}")
            return None
    
    async def scan_for_opportunities(self) -> List[MarketAlert]:
        """Scan watchlist for trading opportunities"""
        try:
            alerts = []
            
            for symbol in self.watchlist:
                try:
                    # Get signals for each symbol
                    signals = await self.generate_trading_signals(symbol)
                    
                    for signal in signals:
                        if signal.confidence >= Decimal("0.7"):  # High confidence signals only
                            alert = MarketAlert(
                                alert_id=f"{symbol}_{signal.source}_{int(datetime.utcnow().timestamp())}",
                                symbol=symbol,
                                alert_type="TECHNICAL_SIGNAL",
                                message=f"{signal.signal_type} signal for {symbol}: {signal.reasoning}",
                                severity="HIGH" if signal.confidence >= Decimal("0.8") else "MEDIUM",
                                timestamp=datetime.utcnow(),
                                data={
                                    "signal_type": signal.signal_type,
                                    "confidence": float(signal.confidence),
                                    "source": signal.source,
                                    "risk_score": float(signal.risk_score or 0)
                                }
                            )
                            alerts.append(alert)
                    
                    # Small delay to respect rate limits
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error scanning {symbol}: {e}")
                    continue
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error scanning for opportunities: {e}")
            return []
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all market data providers"""
        try:
            status_dict = self.provider_manager.get_provider_status()
            
            # Convert to JSON-serializable format
            result = {}
            for provider, status in status_dict.items():
                result[provider.value] = {
                    "is_active": status.is_active,
                    "last_update": status.last_update.isoformat(),
                    "request_count": status.request_count,
                    "error_count": status.error_count,
                    "status_message": status.status_message
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting provider status: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            # Check all providers
            provider_health = await self.provider_manager.health_check_all()
            
            # Test a few key symbols
            test_symbols = ["AAPL", "BTC-USD"]
            data_availability = {}
            
            for symbol in test_symbols:
                try:
                    quote = await self.get_real_time_price(symbol)
                    data_availability[symbol] = quote is not None
                except Exception:
                    data_availability[symbol] = False
            
            # Overall health
            healthy_providers = sum(1 for is_healthy in provider_health.values() if is_healthy)
            available_data = sum(1 for is_available in data_availability.values() if is_available)
            
            overall_health = (
                healthy_providers > 0 and 
                available_data >= len(test_symbols) * 0.5  # At least 50% data availability
            )
            
            return {
                "overall_health": overall_health,
                "provider_health": {k.value: v for k, v in provider_health.items()},
                "data_availability": data_availability,
                "active_providers": healthy_providers,
                "total_providers": len(provider_health),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {
                "overall_health": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # WebSocket streaming methods (simplified implementation)
    
    async def start_live_stream(self, symbols: List[str], client_id: str) -> str:
        """Start live price stream for symbols"""
        try:
            stream_id = f"{client_id}_{int(datetime.utcnow().timestamp())}"
            
            # Store stream info
            self.active_streams[stream_id] = {
                "symbols": symbols,
                "client_id": client_id,
                "started_at": datetime.utcnow(),
                "last_update": datetime.utcnow()
            }
            
            # Start background task for streaming
            asyncio.create_task(self._stream_prices(stream_id, symbols))
            
            logger.info(f"Started live stream {stream_id} for {symbols}")
            return stream_id
            
        except Exception as e:
            logger.error(f"Error starting live stream: {e}")
            raise
    
    async def _stream_prices(self, stream_id: str, symbols: List[str]):
        """Background task to stream live prices"""
        try:
            while stream_id in self.active_streams:
                try:
                    # Get current prices
                    quotes = await self.get_multiple_quotes(symbols)
                    
                    # Create stream updates
                    for quote in quotes:
                        update = StreamUpdate(
                            subscription_id=stream_id,
                            symbol=quote.symbol,
                            data_type="price",
                            data=quote,
                            timestamp=datetime.utcnow(),
                            sequence_number=int(datetime.utcnow().timestamp())
                        )
                        
                        # In a real implementation, this would be sent via WebSocket
                        logger.debug(f"Stream update: {quote.symbol} @ {quote.price}")
                    
                    # Update last update time
                    if stream_id in self.active_streams:
                        self.active_streams[stream_id]["last_update"] = datetime.utcnow()
                    
                    # Wait before next update
                    await asyncio.sleep(1)  # 1-second intervals
                    
                except Exception as e:
                    logger.error(f"Error in price streaming: {e}")
                    await asyncio.sleep(5)  # Wait longer on error
                    
        except Exception as e:
            logger.error(f"Stream {stream_id} terminated with error: {e}")
        finally:
            # Clean up
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            logger.info(f"Stream {stream_id} terminated")
    
    async def stop_live_stream(self, stream_id: str) -> bool:
        """Stop live price stream"""
        try:
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
                logger.info(f"Stopped live stream {stream_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error stopping live stream {stream_id}: {e}")
            return False
    
    def get_active_streams(self) -> Dict[str, Any]:
        """Get information about active streams"""
        return {
            stream_id: {
                "symbols": info["symbols"],
                "client_id": info["client_id"],
                "started_at": info["started_at"].isoformat(),
                "last_update": info["last_update"].isoformat(),
                "duration_seconds": (datetime.utcnow() - info["started_at"]).total_seconds()
            }
            for stream_id, info in self.active_streams.items()
        }