"""
Polygon.io Market Data Provider
High-frequency streaming real-time and historical data with your API key
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
    MarketDataProvider, AssetType, TimeFrame, OrderBookLevel
)

class PolygonProvider(BaseMarketDataProvider):
    """Polygon.io provider for high-frequency market data"""
    
    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(api_key=api_key, config=config or {})
        self.base_url = "https://api.polygon.io"
        self.session = None
        
        # Configure rate limits based on your plan
        self.config.setdefault("requests_per_minute", 1000)  # Adjust based on your plan
        self.config.setdefault("requests_per_day", 100000)   # Adjust based on your plan
        
    def get_provider_name(self) -> MarketDataProvider:
        return MarketDataProvider.POLYGON
    
    def get_supported_assets(self) -> List[AssetType]:
        return [
            AssetType.STOCK,
            AssetType.FOREX,
            AssetType.CRYPTO,
            AssetType.INDEX,
            AssetType.OPTION
        ]
    
    def get_supported_timeframes(self) -> List[TimeFrame]:
        return [
            TimeFrame.M1,
            TimeFrame.M5,
            TimeFrame.M15,
            TimeFrame.M30,
            TimeFrame.H1,
            TimeFrame.D1
        ]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_api_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make API request to Polygon.io"""
        if params is None:
            params = {}
        
        params["apikey"] = self.api_key
        url = f"{self.base_url}{endpoint}"
        
        session = await self._get_session()
        
        async def request_func():
            async with session.get(url, params=params) as response:
                if response.status == 429:
                    raise RateLimitError("Polygon.io rate limit exceeded")
                elif response.status == 403:
                    raise APIError("Polygon.io API access forbidden - check your subscription")
                elif response.status != 200:
                    raise APIError(f"Polygon.io API error: {response.status}")
                
                data = await response.json()
                
                # Check for API errors
                if data.get("status") == "ERROR":
                    raise APIError(f"Polygon.io error: {data.get('error', 'Unknown error')}")
                
                return data
        
        return await self._make_request_with_retry(request_func)
    
    def _determine_asset_type(self, symbol: str) -> AssetType:
        """Determine asset type from symbol"""
        symbol_upper = symbol.upper()
        
        # Crypto patterns
        if "X:" in symbol:
            return AssetType.CRYPTO
        
        # Forex patterns
        if "C:" in symbol:
            return AssetType.FOREX
        
        # Options patterns
        if "O:" in symbol:
            return AssetType.OPTION
        
        # Index patterns
        if symbol_upper.startswith("I:"):
            return AssetType.INDEX
        
        # Default to stock
        return AssetType.STOCK
    
    def _format_symbol_for_api(self, symbol: str, asset_type: AssetType) -> str:
        """Format symbol for Polygon API"""
        if asset_type == AssetType.CRYPTO:
            if not symbol.startswith("X:"):
                return f"X:{symbol.replace('-', '')}"
        elif asset_type == AssetType.FOREX:
            if not symbol.startswith("C:"):
                return f"C:{symbol}"
        elif asset_type == AssetType.INDEX:
            if not symbol.startswith("I:"):
                return f"I:{symbol}"
        
        return symbol.upper()
    
    async def get_quote(self, symbol: str) -> PriceData:
        """Get real-time quote"""
        try:
            asset_type = self._determine_asset_type(symbol)
            formatted_symbol = self._format_symbol_for_api(symbol, asset_type)
            
            if asset_type == AssetType.CRYPTO:
                endpoint = f"/v1/last/crypto/{formatted_symbol}"
            elif asset_type == AssetType.FOREX:
                endpoint = f"/v1/last/forex/{formatted_symbol}"
            else:
                endpoint = f"/v2/last/trade/{formatted_symbol}"
            
            data = await self._make_api_request(endpoint)
            
            if asset_type == AssetType.CRYPTO:
                last_data = data.get("last", {})
                price = Decimal(str(last_data.get("price", 0)))
                
                return PriceData(
                    symbol=symbol,
                    price=price,
                    volume=Decimal(str(last_data.get("size", 0))),
                    timestamp=datetime.fromtimestamp(last_data.get("timestamp", 0) / 1000) if last_data.get("timestamp") else datetime.utcnow(),
                    provider=self.get_provider_name(),
                    asset_type=asset_type
                )
            
            elif asset_type == AssetType.FOREX:
                last_data = data.get("last", {})
                price = Decimal(str(last_data.get("bid", 0)))
                ask = Decimal(str(last_data.get("ask", 0)))
                
                return PriceData(
                    symbol=symbol,
                    price=price,
                    bid=price,
                    ask=ask,
                    timestamp=datetime.fromtimestamp(last_data.get("timestamp", 0) / 1000) if last_data.get("timestamp") else datetime.utcnow(),
                    provider=self.get_provider_name(),
                    asset_type=asset_type
                )
            
            else:  # Stocks
                results = data.get("results", {})
                price = Decimal(str(results.get("p", 0)))  # price
                volume = Decimal(str(results.get("s", 0)))  # size
                
                return PriceData(
                    symbol=symbol,
                    price=price,
                    volume=volume,
                    timestamp=datetime.fromtimestamp(results.get("t", 0) / 1000) if results.get("t") else datetime.utcnow(),
                    provider=self.get_provider_name(),
                    asset_type=asset_type
                )
                
        except Exception as e:
            logger.error(f"Polygon get_quote error for {symbol}: {e}")
            raise APIError(f"Failed to get quote for {symbol}: {e}")
    
    async def get_quotes(self, symbols: List[str]) -> List[PriceData]:
        """Get multiple quotes"""
        quotes = []
        
        # Group symbols by asset type for batch processing
        stock_symbols = []
        crypto_symbols = []
        forex_symbols = []
        
        for symbol in symbols:
            asset_type = self._determine_asset_type(symbol)
            if asset_type == AssetType.CRYPTO:
                crypto_symbols.append(symbol)
            elif asset_type == AssetType.FOREX:
                forex_symbols.append(symbol)
            else:
                stock_symbols.append(symbol)
        
        # Process each group
        if stock_symbols:
            try:
                # Polygon supports batch requests for stocks
                symbols_param = ",".join(stock_symbols)
                endpoint = f"/v2/snapshot/locale/us/markets/stocks/tickers"
                params = {"tickers": symbols_param}
                
                data = await self._make_api_request(endpoint, params)
                
                for ticker_data in data.get("results", []):
                    ticker = ticker_data.get("ticker", "")
                    if ticker in stock_symbols:
                        last_quote = ticker_data.get("lastQuote", {})
                        last_trade = ticker_data.get("lastTrade", {})
                        day = ticker_data.get("day", {})
                        
                        price = Decimal(str(last_trade.get("p", 0)))
                        volume = Decimal(str(day.get("v", 0)))
                        change = Decimal(str(day.get("c", 0)))
                        
                        quotes.append(PriceData(
                            symbol=ticker,
                            price=price,
                            bid=Decimal(str(last_quote.get("b", price))),
                            ask=Decimal(str(last_quote.get("a", price))),
                            volume=volume,
                            change=change,
                            high_24h=Decimal(str(day.get("h", 0))),
                            low_24h=Decimal(str(day.get("l", 0))),
                            timestamp=datetime.utcnow(),
                            provider=self.get_provider_name(),
                            asset_type=AssetType.STOCK
                        ))
                        
            except Exception as e:
                logger.warning(f"Batch stock quotes failed: {e}")
                # Fallback to individual requests
                for symbol in stock_symbols:
                    try:
                        quote = await self.get_quote(symbol)
                        quotes.append(quote)
                    except Exception:
                        continue
        
        # Process crypto and forex individually (Polygon doesn't support batch for these)
        for symbol in crypto_symbols + forex_symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
                await asyncio.sleep(0.01)  # Small delay to respect rate limits
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
            formatted_symbol = self._format_symbol_for_api(symbol, asset_type)
            
            if end_time is None:
                end_time = datetime.utcnow()
            
            # Convert timeframe to Polygon format
            timespan_map = {
                TimeFrame.M1: "minute",
                TimeFrame.M5: "minute", 
                TimeFrame.M15: "minute",
                TimeFrame.M30: "minute",
                TimeFrame.H1: "hour",
                TimeFrame.D1: "day"
            }
            
            multiplier_map = {
                TimeFrame.M1: 1,
                TimeFrame.M5: 5,
                TimeFrame.M15: 15, 
                TimeFrame.M30: 30,
                TimeFrame.H1: 1,
                TimeFrame.D1: 1
            }
            
            timespan = timespan_map.get(timeframe, "day")
            multiplier = multiplier_map.get(timeframe, 1)
            
            # Format dates for API
            start_date = start_time.strftime("%Y-%m-%d")
            end_date = end_time.strftime("%Y-%m-%d")
            
            # Build endpoint based on asset type
            if asset_type == AssetType.CRYPTO:
                endpoint = f"/v2/aggs/ticker/{formatted_symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}"
            else:
                endpoint = f"/v2/aggs/ticker/{formatted_symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}"
            
            params = {}
            if limit:
                params["limit"] = str(limit)
            
            data = await self._make_api_request(endpoint, params)
            
            ohlcv_data = []
            results = data.get("results", [])
            
            for bar in results:
                timestamp = datetime.fromtimestamp(bar.get("t", 0) / 1000)
                
                ohlcv_data.append(OHLCV(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=Decimal(str(bar.get("o", 0))),
                    high=Decimal(str(bar.get("h", 0))),
                    low=Decimal(str(bar.get("l", 0))),
                    close=Decimal(str(bar.get("c", 0))),
                    volume=Decimal(str(bar.get("v", 0))),
                    provider=self.get_provider_name()
                ))
            
            return ohlcv_data
            
        except Exception as e:
            logger.error(f"Polygon get_historical_data error for {symbol}: {e}")
            raise APIError(f"Failed to get historical data for {symbol}: {e}")
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBookSnapshot:
        """Get order book snapshot (limited support)"""
        try:
            asset_type = self._determine_asset_type(symbol)
            
            if asset_type != AssetType.CRYPTO:
                raise APIError("Order book only available for crypto assets on Polygon")
            
            formatted_symbol = self._format_symbol_for_api(symbol, asset_type)
            endpoint = f"/v1/last_quote/crypto/{formatted_symbol}"
            
            data = await self._make_api_request(endpoint)
            
            last_quote = data.get("last", {})
            bid_price = Decimal(str(last_quote.get("bid", 0)))
            ask_price = Decimal(str(last_quote.get("ask", 0)))
            
            # Polygon doesn't provide full order book, so we create a simple one
            bids = [OrderBookLevel(price=bid_price, quantity=Decimal("1.0"))] if bid_price > 0 else []
            asks = [OrderBookLevel(price=ask_price, quantity=Decimal("1.0"))] if ask_price > 0 else []
            
            spread = ask_price - bid_price if bid_price > 0 and ask_price > 0 else Decimal("0")
            mid_price = (bid_price + ask_price) / 2 if bid_price > 0 and ask_price > 0 else Decimal("0")
            
            return OrderBookSnapshot(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                bids=bids,
                asks=asks,
                spread=spread,
                mid_price=mid_price,
                provider=self.get_provider_name()
            )
            
        except Exception as e:
            logger.error(f"Polygon get_orderbook error for {symbol}: {e}")
            raise APIError(f"Failed to get order book for {symbol}: {e}")
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        try:
            asset_type = self._determine_asset_type(symbol)
            formatted_symbol = self._format_symbol_for_api(symbol, asset_type)
            
            if asset_type == AssetType.CRYPTO:
                endpoint = f"/v1/historic/crypto/{formatted_symbol}"
            else:
                endpoint = f"/v2/ticks/stocks/trades/{formatted_symbol}"
                
            params = {"limit": str(min(limit, 50000))}  # Polygon limit
            
            data = await self._make_api_request(endpoint, params)
            
            trades = []
            results = data.get("results", [])
            
            for trade_data in results[-limit:]:  # Get most recent trades
                if asset_type == AssetType.CRYPTO:
                    price = Decimal(str(trade_data.get("price", 0)))
                    size = Decimal(str(trade_data.get("size", 0)))
                    timestamp = datetime.fromtimestamp(trade_data.get("timestamp", 0) / 1000)
                else:
                    price = Decimal(str(trade_data.get("p", 0)))
                    size = Decimal(str(trade_data.get("s", 0)))
                    timestamp = datetime.fromtimestamp(trade_data.get("t", 0) / 1000000)  # nanoseconds
                
                trades.append(Trade(
                    symbol=symbol,
                    timestamp=timestamp,
                    price=price,
                    quantity=size,
                    side="UNKNOWN",  # Polygon doesn't always provide side
                    provider=self.get_provider_name()
                ))
            
            return trades
            
        except Exception as e:
            logger.error(f"Polygon get_recent_trades error for {symbol}: {e}")
            raise APIError(f"Failed to get recent trades for {symbol}: {e}")
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols"""
        try:
            endpoint = "/v3/reference/tickers"
            params = {
                "search": query,
                "limit": "20"
            }
            
            data = await self._make_api_request(endpoint, params)
            
            results = []
            for ticker in data.get("results", []):
                results.append({
                    "symbol": ticker.get("ticker", ""),
                    "name": ticker.get("name", ""),
                    "type": ticker.get("type", ""),
                    "market": ticker.get("market", ""),
                    "currency": ticker.get("currency_name", "")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Polygon search_symbols error: {e}")
            return []
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session and not self.session.closed:
            await self.session.close()