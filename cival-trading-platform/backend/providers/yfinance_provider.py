"""
YFinance Market Data Provider
Free real-time and historical data for stocks, crypto, forex using Yahoo Finance
"""

import yfinance as yf
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import pandas as pd
from loguru import logger

from python_ai_services.providers.base_market_provider import BaseMarketDataProvider, APIError
from python_ai_services.models.enhanced_market_data_models import (
    PriceData, OHLCV, MarketQuote, OrderBookSnapshot, Trade,
    MarketDataProvider, AssetType, TimeFrame
)

class YFinanceProvider(BaseMarketDataProvider):
    """YFinance provider for free market data"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(api_key=None, config=config or {})
        self.session = None
        
    def get_provider_name(self) -> MarketDataProvider:
        return MarketDataProvider.YFINANCE
    
    def get_supported_assets(self) -> List[AssetType]:
        return [
            AssetType.STOCK,
            AssetType.CRYPTO,
            AssetType.FOREX,
            AssetType.INDEX,
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
    
    def _convert_timeframe(self, timeframe: TimeFrame) -> str:
        """Convert TimeFrame to yfinance interval"""
        mapping = {
            TimeFrame.M1: "1m",
            TimeFrame.M5: "5m",
            TimeFrame.M15: "15m",
            TimeFrame.M30: "30m",
            TimeFrame.H1: "1h",
            TimeFrame.D1: "1d",
            TimeFrame.W1: "1wk",
            TimeFrame.MN1: "1mo"
        }
        return mapping.get(timeframe, "1d")
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for yfinance"""
        # Handle crypto symbols
        if symbol.upper().endswith("USD"):
            return f"{symbol[:-3]}-USD"
        elif symbol.upper().endswith("USDT"):
            return f"{symbol[:-4]}-USD"
        elif symbol.upper().startswith("BTC") or symbol.upper().startswith("ETH"):
            if "-" not in symbol:
                return f"{symbol}-USD"
        
        return symbol.upper()
    
    def _determine_asset_type(self, symbol: str) -> AssetType:
        """Determine asset type from symbol"""
        symbol_upper = symbol.upper()
        
        # Crypto patterns
        crypto_patterns = ["-USD", "-BTC", "-ETH", "BTC", "ETH", "ADA", "SOL", "DOGE"]
        if any(pattern in symbol_upper for pattern in crypto_patterns):
            return AssetType.CRYPTO
        
        # Forex patterns
        forex_patterns = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
        if any(pattern in symbol_upper for pattern in forex_patterns):
            return AssetType.FOREX
        
        # Index patterns
        index_patterns = ["^", "SPY", "QQQ", "IWM", "DIA"]
        if any(pattern in symbol_upper for pattern in index_patterns):
            return AssetType.INDEX
        
        # Default to stock
        return AssetType.STOCK
    
    async def get_quote(self, symbol: str) -> PriceData:
        """Get real-time quote"""
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            
            # Use asyncio to run the synchronous yfinance call
            ticker = await asyncio.get_event_loop().run_in_executor(
                None, yf.Ticker, normalized_symbol
            )
            
            # Get current data
            info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: ticker.info
            )
            
            # Get recent price data
            hist = await asyncio.get_event_loop().run_in_executor(
                None, lambda: ticker.history(period="1d", interval="1m")
            )
            
            if hist.empty:
                raise APIError(f"No data available for {symbol}")
            
            latest = hist.iloc[-1]
            current_price = latest['Close']
            
            # Calculate change
            if len(hist) > 1:
                prev_close = hist.iloc[-2]['Close']
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
            else:
                change = 0
                change_percent = 0
            
            return PriceData(
                symbol=symbol,
                price=Decimal(str(current_price)),
                bid=Decimal(str(info.get('bid', current_price))),
                ask=Decimal(str(info.get('ask', current_price))),
                volume=Decimal(str(latest.get('Volume', 0))),
                change=Decimal(str(change)),
                change_percent=Decimal(str(change_percent)),
                high_24h=Decimal(str(hist['High'].max())),
                low_24h=Decimal(str(hist['Low'].min())),
                timestamp=datetime.utcnow(),
                provider=self.get_provider_name(),
                asset_type=self._determine_asset_type(symbol)
            )
            
        except Exception as e:
            logger.error(f"YFinance get_quote error for {symbol}: {e}")
            raise APIError(f"Failed to get quote for {symbol}: {e}")
    
    async def get_quotes(self, symbols: List[str]) -> List[PriceData]:
        """Get multiple quotes efficiently"""
        try:
            # Normalize all symbols
            normalized_symbols = [self._normalize_symbol(s) for s in symbols]
            symbol_map = dict(zip(normalized_symbols, symbols))
            
            # Download data for all symbols at once
            data = await asyncio.get_event_loop().run_in_executor(
                None, lambda: yf.download(
                    normalized_symbols, 
                    period="1d", 
                    interval="1m",
                    group_by='ticker',
                    progress=False
                )
            )
            
            quotes = []
            
            for norm_symbol, orig_symbol in symbol_map.items():
                try:
                    if len(normalized_symbols) == 1:
                        symbol_data = data
                    else:
                        symbol_data = data[norm_symbol]
                    
                    if symbol_data.empty:
                        continue
                    
                    latest = symbol_data.iloc[-1]
                    current_price = latest['Close']
                    
                    # Calculate change
                    if len(symbol_data) > 1:
                        prev_close = symbol_data.iloc[-2]['Close']
                        change = current_price - prev_close
                        change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
                    else:
                        change = 0
                        change_percent = 0
                    
                    quotes.append(PriceData(
                        symbol=orig_symbol,
                        price=Decimal(str(current_price)),
                        volume=Decimal(str(latest.get('Volume', 0))),
                        change=Decimal(str(change)),
                        change_percent=Decimal(str(change_percent)),
                        high_24h=Decimal(str(symbol_data['High'].max())),
                        low_24h=Decimal(str(symbol_data['Low'].min())),
                        timestamp=datetime.utcnow(),
                        provider=self.get_provider_name(),
                        asset_type=self._determine_asset_type(orig_symbol)
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to process {orig_symbol}: {e}")
                    continue
            
            return quotes
            
        except Exception as e:
            logger.error(f"YFinance get_quotes error: {e}")
            raise APIError(f"Failed to get quotes: {e}")
    
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
            normalized_symbol = self._normalize_symbol(symbol)
            interval = self._convert_timeframe(timeframe)
            
            # Calculate period if end_time not provided
            if end_time is None:
                end_time = datetime.utcnow()
            
            # Get data using yfinance
            ticker = yf.Ticker(normalized_symbol)
            hist = await asyncio.get_event_loop().run_in_executor(
                None, lambda: ticker.history(
                    start=start_time.date(),
                    end=end_time.date(),
                    interval=interval
                )
            )
            
            if hist.empty:
                return []
            
            # Apply limit if specified
            if limit:
                hist = hist.tail(limit)
            
            ohlcv_data = []
            for timestamp, row in hist.iterrows():
                ohlcv_data.append(OHLCV(
                    symbol=symbol,
                    timestamp=timestamp.to_pydatetime(),
                    open=Decimal(str(row['Open'])),
                    high=Decimal(str(row['High'])),
                    low=Decimal(str(row['Low'])),
                    close=Decimal(str(row['Close'])),
                    volume=Decimal(str(row['Volume'])),
                    provider=self.get_provider_name()
                ))
            
            return ohlcv_data
            
        except Exception as e:
            logger.error(f"YFinance get_historical_data error for {symbol}: {e}")
            raise APIError(f"Failed to get historical data for {symbol}: {e}")
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBookSnapshot:
        """YFinance doesn't provide order book data"""
        raise APIError("Order book data not available through YFinance")
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """YFinance doesn't provide trade data"""
        raise APIError("Trade data not available through YFinance")
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols (limited functionality)"""
        try:
            # YFinance doesn't have a direct search API
            # We'll provide a basic implementation for common symbols
            common_symbols = {
                "apple": {"symbol": "AAPL", "name": "Apple Inc."},
                "microsoft": {"symbol": "MSFT", "name": "Microsoft Corporation"},
                "google": {"symbol": "GOOGL", "name": "Alphabet Inc."},
                "amazon": {"symbol": "AMZN", "name": "Amazon.com Inc."},
                "tesla": {"symbol": "TSLA", "name": "Tesla Inc."},
                "bitcoin": {"symbol": "BTC-USD", "name": "Bitcoin USD"},
                "ethereum": {"symbol": "ETH-USD", "name": "Ethereum USD"},
                "spy": {"symbol": "SPY", "name": "SPDR S&P 500 ETF"},
                "qqq": {"symbol": "QQQ", "name": "Invesco QQQ Trust"}
            }
            
            query_lower = query.lower()
            results = []
            
            for key, value in common_symbols.items():
                if query_lower in key or query_lower in value["symbol"].lower():
                    results.append(value)
            
            return results
            
        except Exception as e:
            logger.error(f"YFinance search_symbols error: {e}")
            return []
    
    async def get_detailed_quote(self, symbol: str) -> Optional[MarketQuote]:
        """Get detailed quote with fundamentals"""
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            ticker = yf.Ticker(normalized_symbol)
            
            # Get info and current price
            info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: ticker.info
            )
            
            hist = await asyncio.get_event_loop().run_in_executor(
                None, lambda: ticker.history(period="1d")
            )
            
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            volume = hist['Volume'].iloc[-1]
            
            return MarketQuote(
                symbol=symbol,
                name=info.get('longName', symbol),
                price=Decimal(str(current_price)),
                bid=Decimal(str(info.get('bid', current_price))),
                ask=Decimal(str(info.get('ask', current_price))),
                volume=Decimal(str(volume)),
                market_cap=Decimal(str(info.get('marketCap', 0))) if info.get('marketCap') else None,
                pe_ratio=Decimal(str(info.get('trailingPE', 0))) if info.get('trailingPE') else None,
                high_52w=Decimal(str(info.get('fiftyTwoWeekHigh', 0))) if info.get('fiftyTwoWeekHigh') else None,
                low_52w=Decimal(str(info.get('fiftyTwoWeekLow', 0))) if info.get('fiftyTwoWeekLow') else None,
                dividend_yield=Decimal(str(info.get('dividendYield', 0))) if info.get('dividendYield') else None,
                timestamp=datetime.utcnow(),
                provider=self.get_provider_name(),
                asset_type=self._determine_asset_type(symbol)
            )
            
        except Exception as e:
            logger.error(f"YFinance get_detailed_quote error for {symbol}: {e}")
            return None