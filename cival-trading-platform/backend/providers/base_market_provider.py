"""
Base Market Data Provider Interface
Abstract base class for all market data providers with standardized interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import asyncio
from loguru import logger

from python_ai_services.models.enhanced_market_data_models import (
    PriceData, OHLCV, MarketQuote, OrderBookSnapshot, Trade,
    TechnicalIndicators, MarketOverview, ProviderStatus,
    MarketDataProvider, AssetType, TimeFrame
)

class MarketDataProviderError(Exception):
    """Base exception for market data provider errors"""
    pass

class RateLimitError(MarketDataProviderError):
    """Raised when rate limits are exceeded"""
    pass

class APIError(MarketDataProviderError):
    """Raised when API returns an error"""
    pass

class BaseMarketDataProvider(ABC):
    """
    Abstract base class for all market data providers
    Defines the standard interface that all providers must implement
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.api_key = api_key
        self.config = config or {}
        self.rate_limiter = self._setup_rate_limiter()
        self.status = ProviderStatus(
            provider=self.get_provider_name(),
            is_active=True,
            last_update=datetime.utcnow(),
            request_count=0,
            error_count=0
        )
        
    @abstractmethod
    def get_provider_name(self) -> MarketDataProvider:
        """Return the provider name enum"""
        pass
    
    @abstractmethod
    def get_supported_assets(self) -> List[AssetType]:
        """Return list of supported asset types"""
        pass
    
    @abstractmethod
    def get_supported_timeframes(self) -> List[TimeFrame]:
        """Return list of supported timeframes"""
        pass
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> PriceData:
        """Get real-time quote for a symbol"""
        pass
    
    @abstractmethod
    async def get_quotes(self, symbols: List[str]) -> List[PriceData]:
        """Get real-time quotes for multiple symbols"""
        pass
    
    @abstractmethod
    async def get_historical_data(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        start_time: datetime,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[OHLCV]:
        """Get historical OHLCV data"""
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBookSnapshot:
        """Get order book snapshot"""
        pass
    
    @abstractmethod
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        pass
    
    @abstractmethod
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols by name or ticker"""
        pass
    
    # Optional methods that providers can override
    
    async def get_market_overview(self) -> Optional[MarketOverview]:
        """Get overall market overview (optional)"""
        return None
    
    async def get_detailed_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get detailed quote with fundamentals (optional)"""
        return None
    
    async def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol exists and is tradeable"""
        try:
            await self.get_quote(symbol)
            return True
        except Exception:
            return False
    
    async def get_available_symbols(self) -> List[str]:
        """Get list of all available symbols (optional)"""
        return []
    
    # Rate limiting and error handling
    
    def _setup_rate_limiter(self) -> Dict[str, Any]:
        """Setup rate limiting configuration"""
        return {
            "requests_per_minute": self.config.get("requests_per_minute", 60),
            "requests_per_day": self.config.get("requests_per_day", 1000),
            "last_request_time": datetime.utcnow(),
            "request_count_minute": 0,
            "request_count_day": 0,
            "daily_reset_time": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        }
    
    async def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits"""
        now = datetime.utcnow()
        
        # Reset daily counter if needed
        if now >= self.rate_limiter["daily_reset_time"] + timedelta(days=1):
            self.rate_limiter["request_count_day"] = 0
            self.rate_limiter["daily_reset_time"] = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Reset minute counter if needed
        if now >= self.rate_limiter["last_request_time"] + timedelta(minutes=1):
            self.rate_limiter["request_count_minute"] = 0
        
        # Check limits
        if self.rate_limiter["request_count_minute"] >= self.rate_limiter["requests_per_minute"]:
            logger.warning(f"{self.get_provider_name()}: Rate limit exceeded (per minute)")
            return False
        
        if self.rate_limiter["request_count_day"] >= self.rate_limiter["requests_per_day"]:
            logger.warning(f"{self.get_provider_name()}: Rate limit exceeded (per day)")
            return False
        
        return True
    
    async def _record_request(self, success: bool = True):
        """Record a request for rate limiting and status tracking"""
        now = datetime.utcnow()
        self.rate_limiter["last_request_time"] = now
        self.rate_limiter["request_count_minute"] += 1
        self.rate_limiter["request_count_day"] += 1
        
        self.status.request_count += 1
        self.status.last_update = now
        
        if not success:
            self.status.error_count += 1
    
    async def _make_request_with_retry(
        self, 
        request_func, 
        max_retries: int = 3, 
        backoff_factor: float = 1.0
    ) -> Any:
        """Make request with automatic retry and rate limiting"""
        
        if not await self._check_rate_limit():
            raise RateLimitError(f"Rate limit exceeded for {self.get_provider_name()}")
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                await self._record_request(success=True)
                return await request_func()
                
            except Exception as e:
                last_exception = e
                await self._record_request(success=False)
                
                logger.warning(f"{self.get_provider_name()} request failed (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = backoff_factor * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"{self.get_provider_name()} request failed after {max_retries} attempts")
        
        raise last_exception
    
    def get_status(self) -> ProviderStatus:
        """Get current provider status"""
        return self.status
    
    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            # Try to get a quote for a common symbol
            test_symbols = ["AAPL", "BTC-USD", "EURUSD"]
            
            for symbol in test_symbols:
                try:
                    await self.get_quote(symbol)
                    self.status.is_active = True
                    self.status.status_message = "Healthy"
                    return True
                except Exception:
                    continue
            
            self.status.is_active = False
            self.status.status_message = "Failed health check"
            return False
            
        except Exception as e:
            self.status.is_active = False
            self.status.status_message = f"Health check error: {str(e)}"
            return False
    
    # Utility methods for data conversion
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol format for the provider"""
        return symbol.upper().replace("-", "").replace("_", "")
    
    def _convert_timeframe(self, timeframe: TimeFrame) -> str:
        """Convert standard timeframe to provider-specific format"""
        # Default implementation - providers should override
        return timeframe.value
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime"""
        # Default implementation - providers should override
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception:
            return datetime.utcnow()

class ProviderManager:
    """
    Manager for multiple market data providers
    Handles provider selection, failover, and load balancing
    """
    
    def __init__(self):
        self.providers: Dict[MarketDataProvider, BaseMarketDataProvider] = {}
        self.primary_provider: Optional[MarketDataProvider] = None
        self.fallback_order: List[MarketDataProvider] = []
    
    def register_provider(self, provider: BaseMarketDataProvider, is_primary: bool = False):
        """Register a market data provider"""
        provider_name = provider.get_provider_name()
        self.providers[provider_name] = provider
        
        if is_primary or not self.primary_provider:
            self.primary_provider = provider_name
        
        if provider_name not in self.fallback_order:
            self.fallback_order.append(provider_name)
        
        logger.info(f"Registered provider: {provider_name}")
    
    async def get_quote(self, symbol: str) -> PriceData:
        """Get quote with automatic failover"""
        return await self._execute_with_failover("get_quote", symbol)
    
    async def get_quotes(self, symbols: List[str]) -> List[PriceData]:
        """Get multiple quotes with automatic failover"""
        return await self._execute_with_failover("get_quotes", symbols)
    
    async def get_historical_data(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        start_time: datetime,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[OHLCV]:
        """Get historical data with automatic failover"""
        return await self._execute_with_failover(
            "get_historical_data", 
            symbol, 
            timeframe, 
            start_time, 
            end_time, 
            limit
        )
    
    async def _execute_with_failover(self, method_name: str, *args, **kwargs) -> Any:
        """Execute method with automatic provider failover"""
        providers_to_try = [self.primary_provider] + [
            p for p in self.fallback_order if p != self.primary_provider
        ]
        
        last_exception = None
        
        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                continue
                
            provider = self.providers[provider_name]
            
            if not provider.status.is_active:
                continue
            
            try:
                method = getattr(provider, method_name)
                return await method(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Provider {provider_name} failed for {method_name}: {e}")
                continue
        
        raise MarketDataProviderError(f"All providers failed for {method_name}: {last_exception}")
    
    async def health_check_all(self) -> Dict[MarketDataProvider, bool]:
        """Perform health check on all providers"""
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                results[provider_name] = await provider.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {provider_name}: {e}")
                results[provider_name] = False
        
        return results
    
    def get_provider_status(self) -> Dict[MarketDataProvider, ProviderStatus]:
        """Get status of all providers"""
        return {name: provider.get_status() for name, provider in self.providers.items()}