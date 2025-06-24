"""
Alpha Vantage Market Data Provider
Premium real-time and historical financial data with your paid API key
"""

import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import json
from loguru import logger

from python_ai_services.providers.base_market_provider import BaseMarketDataProvider, APIError, RateLimitError
from python_ai_services.models.enhanced_market_data_models import (
    PriceData, OHLCV, MarketQuote, OrderBookSnapshot, Trade,
    MarketDataProvider, AssetType, TimeFrame
)

class AlphaVantageProvider(BaseMarketDataProvider):
    """Alpha Vantage provider for premium market data"""
    
    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(api_key=api_key, config=config or {})
        self.base_url = "https://www.alphavantage.co/query"
        self.session = None
        
        # Configure rate limits (adjust based on your plan)
        self.config.setdefault("requests_per_minute", 75)  # Premium plan
        self.config.setdefault("requests_per_day", 75000)   # Premium plan
        
    def get_provider_name(self) -> MarketDataProvider:
        return MarketDataProvider.ALPHA_VANTAGE
    
    def get_supported_assets(self) -> List[AssetType]:
        return [
            AssetType.STOCK,
            AssetType.FOREX,
            AssetType.CRYPTO,
            AssetType.COMMODITY
        ]
    
    def get_supported_timeframes(self) -> List[TimeFrame]:
        return [
            TimeFrame.M1,
            TimeFrame.M5,
            TimeFrame.M15,
            TimeFrame.M30,
            TimeFrame.H1,
            TimeFrame.D1,
            TimeFrame.W1,
            TimeFrame.MN1
        ]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_api_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Make API request to Alpha Vantage"""
        params["apikey"] = self.api_key
        
        session = await self._get_session()
        
        async def request_func():
            async with session.get(self.base_url, params=params) as response:
                if response.status == 429:
                    raise RateLimitError("Alpha Vantage rate limit exceeded")
                elif response.status != 200:
                    raise APIError(f"Alpha Vantage API error: {response.status}")
                
                data = await response.json()
                
                # Check for API errors
                if "Error Message" in data:
                    raise APIError(f"Alpha Vantage error: {data['Error Message']}")
                elif "Note" in data:
                    raise RateLimitError(f"Alpha Vantage rate limit: {data['Note']}")
                
                return data
        
        return await self._make_request_with_retry(request_func)
    
    def _determine_asset_type(self, symbol: str) -> AssetType:
        """Determine asset type from symbol"""
        symbol_upper = symbol.upper()
        
        # Forex patterns (pairs)
        if len(symbol) == 6 and symbol.isalpha():
            return AssetType.FOREX
        
        # Crypto patterns
        crypto_symbols = ["BTC", "ETH", "ADA", "DOT", "LTC", "XRP", "BCH", "LINK", "DOGE"]
        if any(crypto in symbol_upper for crypto in crypto_symbols):
            return AssetType.CRYPTO
        
        # Default to stock
        return AssetType.STOCK
    
    async def get_quote(self, symbol: str) -> PriceData:
        """Get real-time quote"""
        try:
            asset_type = self._determine_asset_type(symbol)
            
            if asset_type == AssetType.FOREX:
                params = {
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": symbol[:3],
                    "to_currency": symbol[3:]
                }
            elif asset_type == AssetType.CRYPTO:
                params = {
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": symbol,
                    "to_currency": "USD"
                }
            else:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol
                }
            
            data = await self._make_api_request(params)
            
            if asset_type in [AssetType.FOREX, AssetType.CRYPTO]:
                rate_data = data.get("Realtime Currency Exchange Rate", {})
                
                current_price = Decimal(rate_data.get("5. Exchange Rate", "0"))
                bid_price = Decimal(rate_data.get("8. Bid Price", str(current_price)))
                ask_price = Decimal(rate_data.get("9. Ask Price", str(current_price)))
                
                return PriceData(
                    symbol=symbol,
                    price=current_price,
                    bid=bid_price,
                    ask=ask_price,
                    timestamp=datetime.utcnow(),
                    provider=self.get_provider_name(),
                    asset_type=asset_type
                )
            else:
                quote_data = data.get("Global Quote", {})
                
                current_price = Decimal(quote_data.get("05. price", "0"))
                change = Decimal(quote_data.get("09. change", "0"))
                change_percent = Decimal(quote_data.get("10. change percent", "0%").rstrip("%"))
                volume = Decimal(quote_data.get("06. volume", "0"))
                high = Decimal(quote_data.get("03. high", "0"))
                low = Decimal(quote_data.get("04. low", "0"))
                
                return PriceData(
                    symbol=symbol,
                    price=current_price,
                    volume=volume,
                    change=change,
                    change_percent=change_percent,
                    high_24h=high,
                    low_24h=low,
                    timestamp=datetime.utcnow(),
                    provider=self.get_provider_name(),
                    asset_type=asset_type
                )
                
        except Exception as e:
            logger.error(f"Alpha Vantage get_quote error for {symbol}: {e}")
            raise APIError(f"Failed to get quote for {symbol}: {e}")
    
    async def get_quotes(self, symbols: List[str]) -> List[PriceData]:
        """Get multiple quotes (sequential due to API limitations)"""
        quotes = []
        
        # Alpha Vantage doesn't support batch requests, so we make sequential calls
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to get quote for {symbol}: {e}")
                continue
        
        return quotes
    
    async def get_historical_data(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        start_time: datetime,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[OHLCV]:
        """Get historical OHLCV data"""
        try:
            asset_type = self._determine_asset_type(symbol)
            
            # Map timeframes to Alpha Vantage functions
            if timeframe in [TimeFrame.M1, TimeFrame.M5, TimeFrame.M15, TimeFrame.M30]:
                if asset_type == AssetType.STOCK:
                    function = "TIME_SERIES_INTRADAY"
                    interval_map = {
                        TimeFrame.M1: "1min",
                        TimeFrame.M5: "5min", 
                        TimeFrame.M15: "15min",
                        TimeFrame.M30: "30min"
                    }
                    params = {
                        "function": function,
                        "symbol": symbol,
                        "interval": interval_map[timeframe]
                    }
                else:
                    # Crypto intraday
                    function = "CRYPTO_INTRADAY"
                    interval_map = {
                        TimeFrame.M1: "1min",
                        TimeFrame.M5: "5min",
                        TimeFrame.M15: "15min", 
                        TimeFrame.M30: "30min"
                    }
                    params = {
                        "function": function,
                        "symbol": symbol,
                        "market": "USD",
                        "interval": interval_map[timeframe]
                    }
            elif timeframe == TimeFrame.D1:
                if asset_type == AssetType.STOCK:
                    params = {
                        "function": "TIME_SERIES_DAILY",
                        "symbol": symbol
                    }
                else:
                    params = {
                        "function": "DIGITAL_CURRENCY_DAILY",
                        "symbol": symbol,
                        "market": "USD"
                    }
            elif timeframe == TimeFrame.W1:
                params = {
                    "function": "TIME_SERIES_WEEKLY",
                    "symbol": symbol
                }
            elif timeframe == TimeFrame.MN1:
                params = {
                    "function": "TIME_SERIES_MONTHLY", 
                    "symbol": symbol
                }
            else:
                raise APIError(f"Unsupported timeframe: {timeframe}")
            
            data = await self._make_api_request(params)
            
            # Parse the response based on function type
            time_series_key = None
            for key in data.keys():
                if "Time Series" in key or "Time Series" in key:
                    time_series_key = key
                    break
            
            if not time_series_key:
                raise APIError(f"No time series data found for {symbol}")
            
            time_series = data[time_series_key]
            ohlcv_data = []
            
            for timestamp_str, values in time_series.items():
                timestamp = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
                
                # Filter by date range
                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue
                
                # Handle different value key formats
                if "1. open" in values:
                    # Standard format
                    open_price = Decimal(values["1. open"])
                    high_price = Decimal(values["2. high"])
                    low_price = Decimal(values["3. low"])
                    close_price = Decimal(values["4. close"])
                    volume = Decimal(values["5. volume"])
                elif "1a. open (USD)" in values:
                    # Crypto format
                    open_price = Decimal(values["1a. open (USD)"])
                    high_price = Decimal(values["2a. high (USD)"])
                    low_price = Decimal(values["3a. low (USD)"])
                    close_price = Decimal(values["4a. close (USD)"])
                    volume = Decimal(values["5. volume"])
                else:
                    continue
                
                ohlcv_data.append(OHLCV(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                    provider=self.get_provider_name()
                ))
            
            # Sort by timestamp and apply limit
            ohlcv_data.sort(key=lambda x: x.timestamp)
            if limit:
                ohlcv_data = ohlcv_data[-limit:]
            
            return ohlcv_data
            
        except Exception as e:
            logger.error(f"Alpha Vantage get_historical_data error for {symbol}: {e}")
            raise APIError(f"Failed to get historical data for {symbol}: {e}")
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBookSnapshot:
        """Alpha Vantage doesn't provide order book data"""
        raise APIError("Order book data not available through Alpha Vantage")
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Alpha Vantage doesn't provide trade data"""
        raise APIError("Trade data not available through Alpha Vantage")
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols"""
        try:
            params = {
                "function": "SYMBOL_SEARCH",
                "keywords": query
            }
            
            data = await self._make_api_request(params)
            
            results = []
            best_matches = data.get("bestMatches", [])
            
            for match in best_matches:
                results.append({
                    "symbol": match.get("1. symbol", ""),
                    "name": match.get("2. name", ""),
                    "type": match.get("3. type", ""),
                    "region": match.get("4. region", ""),
                    "currency": match.get("8. currency", "")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Alpha Vantage search_symbols error: {e}")
            return []
    
    async def get_detailed_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get detailed quote with company overview"""
        try:
            # Get basic quote
            price_data = await self.get_quote(symbol)
            
            # Get company overview for additional details
            params = {
                "function": "OVERVIEW",
                "symbol": symbol
            }
            
            overview_data = await self._make_api_request(params)
            
            return MarketQuote(
                symbol=symbol,
                name=overview_data.get("Name", symbol),
                price=price_data.price,
                bid=price_data.bid,
                ask=price_data.ask,
                volume=price_data.volume,
                market_cap=Decimal(overview_data.get("MarketCapitalization", "0")) if overview_data.get("MarketCapitalization") != "None" else None,
                pe_ratio=Decimal(overview_data.get("PERatio", "0")) if overview_data.get("PERatio") != "None" else None,
                high_52w=Decimal(overview_data.get("52WeekHigh", "0")) if overview_data.get("52WeekHigh") != "None" else None,
                low_52w=Decimal(overview_data.get("52WeekLow", "0")) if overview_data.get("52WeekLow") != "None" else None,
                dividend_yield=Decimal(overview_data.get("DividendYield", "0")) if overview_data.get("DividendYield") != "None" else None,
                timestamp=datetime.utcnow(),
                provider=self.get_provider_name(),
                asset_type=self._determine_asset_type(symbol)
            )
            
        except Exception as e:
            logger.error(f"Alpha Vantage get_detailed_quote error for {symbol}: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session and not self.session.closed:
            await self.session.close()