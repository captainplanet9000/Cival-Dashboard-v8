"""
Market Data Service
Provides real-time and historical market data functionality
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random
import math
from decimal import Decimal
import aiohttp
import json

from ..core.service_registry import service_registry
from ..core.config import Config
from ..core.redis_manager import RedisManager
from ..core.logging_config import logger
from ..database.connection import DatabaseManager
from ..models.market_data_models import Kline, OrderBookSnapshot, Trade

try:
    from ..utils.hyperliquid_data_fetcher import HyperliquidMarketDataFetcher, HyperliquidMarketDataFetcherError
except ImportError:
    HyperliquidMarketDataFetcher = None
    HyperliquidMarketDataFetcherError = Exception

class MarketDataServiceError(Exception):
    pass

class MarketDataService:
    def __init__(self, fetcher: Optional[HyperliquidMarketDataFetcher] = None):
        self.logger = logger
        self.redis = RedisManager()
        self.db = DatabaseManager()
        self.config = Config()
        self.fetcher = fetcher
        
        # Data providers configuration
        self.providers = {
            'binance': {
                'rest_url': 'https://api.binance.com/api/v3',
                'ws_url': 'wss://stream.binance.com:9443/ws',
                'enabled': True
            },
            'coinbase': {
                'rest_url': 'https://api.coinbase.com/v2',
                'enabled': False
            },
            'kraken': {
                'rest_url': 'https://api.kraken.com/0/public',
                'enabled': False
            }
        }
        
        # Market data cache
        self.cache_ttl = 60  # 1 minute cache for market data
        self.historical_cache_ttl = 3600  # 1 hour cache for historical data
        
        # Initialize with mock data
        self._initialize_mock_data()
        
        if fetcher:
            logger.info("MarketDataService initialized with HyperliquidMarketDataFetcher.")
        else:
            logger.info("MarketDataService initialized without fetcher, using mock data.")

    def _initialize_mock_data(self):
        """Initialize with mock market data"""
        mock_prices = {
            'BTC/USDT': {
                'symbol': 'BTC/USDT',
                'price': 45623.50,
                'change_24h': 2.34,
                'volume_24h': 28456789012,
                'high_24h': 46200.00,
                'low_24h': 44800.00,
                'bid': 45620.00,
                'ask': 45627.00,
                'last_update': datetime.now().isoformat()
            },
            'ETH/USDT': {
                'symbol': 'ETH/USDT',
                'price': 2456.78,
                'change_24h': 3.45,
                'volume_24h': 12345678901,
                'high_24h': 2520.00,
                'low_24h': 2380.00,
                'bid': 2455.00,
                'ask': 2458.00,
                'last_update': datetime.now().isoformat()
            },
            'SOL/USDT': {
                'symbol': 'SOL/USDT',
                'price': 98.45,
                'change_24h': 5.67,
                'volume_24h': 3456789012,
                'high_24h': 102.00,
                'low_24h': 93.00,
                'bid': 98.40,
                'ask': 98.50,
                'last_update': datetime.now().isoformat()
            }
        }
        
        # Store mock data in Redis
        for symbol, data in mock_prices.items():
            cache_key = f"market:price:{symbol}"
            asyncio.create_task(self.redis.set(cache_key, json.dumps(data), self.cache_ttl))
    
    async def get_live_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live price for a symbol"""
        try:
            # Check cache first
            cache_key = f"market:price:{symbol}"
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            
            # Try to fetch from real provider
            if self.providers['binance']['enabled']:
                price_data = await self._fetch_binance_price(symbol)
                if price_data:
                    await self.redis.set(cache_key, json.dumps(price_data), self.cache_ttl)
                    return price_data
            
            # Return mock data as fallback
            return self._generate_mock_price(symbol)
            
        except Exception as e:
            self.logger.error(f"Error getting live price for {symbol}: {e}")
            return self._generate_mock_price(symbol)
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get prices for multiple symbols"""
        prices = {}
        tasks = []
        
        for symbol in symbols:
            tasks.append(self.get_live_price(symbol))
        
        results = await asyncio.gather(*tasks)
        
        for symbol, result in zip(symbols, results):
            if result:
                prices[symbol] = result
        
        return prices
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Get overall market summary"""
        try:
            # Get top symbols
            top_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT']
            prices = await self.get_multiple_prices(top_symbols)
            
            # Calculate market metrics
            total_volume = sum(p.get('volume_24h', 0) for p in prices.values())
            changes = [p.get('change_24h', 0) for p in prices.values()]
            avg_change = sum(changes) / len(changes) if changes else 0
            
            # Get market cap data (mock for now)
            total_market_cap = 1.85e12  # $1.85T
            btc_dominance = 48.5
            
            return {
                'total_market_cap': total_market_cap,
                'total_volume_24h': total_volume,
                'btc_dominance': btc_dominance,
                'average_change_24h': avg_change,
                'top_gainers': await self._get_top_movers('gainers'),
                'top_losers': await self._get_top_movers('losers'),
                'trending': await self._get_trending_symbols(),
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market summary: {e}")
            return self._get_mock_market_summary()
    
    async def get_historical_data(self, symbol: str, interval: str = '1h', 
                                  limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical candlestick data"""
        try:
            cache_key = f"market:historical:{symbol}:{interval}:{limit}"
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            
            # Generate historical data
            data = self._generate_historical_data(symbol, interval, limit)
            await self.redis.set(cache_key, json.dumps(data), self.historical_cache_ttl)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting historical data: {e}")
            return []
    
    async def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Kline]:
        """Get historical klines - compatible with existing interface"""
        logger.info(f"MarketDataService: Fetching klines for {symbol} (interval: {interval}) from {start_time} to {end_time}")

        if not symbol:
            raise MarketDataServiceError("Symbol must be provided for fetching klines.")
        if not interval:
            raise MarketDataServiceError("Interval must be provided for fetching klines.")
        if not start_time or not end_time:
            raise MarketDataServiceError("Start time and end time must be provided for fetching klines.")
        if start_time >= end_time:
            raise MarketDataServiceError("Start time must be before end time.")

        # If we have a fetcher, use it
        if self.fetcher:
            try:
                # Convert datetimes to milliseconds for Hyperliquid API
                start_time_ms = int(start_time.timestamp() * 1000)
                end_time_ms = int(end_time.timestamp() * 1000)
                
                klines = await self.fetcher.get_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time_ms=start_time_ms,
                    end_time_ms=end_time_ms
                )
                logger.info(f"MarketDataService: Successfully fetched {len(klines)} klines for {symbol}.")
                return klines
            except Exception as e:
                logger.error(f"MarketDataService: Error fetching klines: {e}")
                # Fall through to mock data
        
        # Generate mock data as fallback
        historical = await self.get_historical_data(symbol, interval)
        
        # Convert to Kline objects
        klines = []
        for candle in historical:
            klines.append(Kline(
                open_time=int(datetime.fromisoformat(candle['time']).timestamp() * 1000),
                open=candle['open'],
                high=candle['high'],
                low=candle['low'],
                close=candle['close'],
                volume=candle['volume'],
                close_time=int(datetime.fromisoformat(candle['time']).timestamp() * 1000) + 3600000,
                quote_asset_volume=candle['volume'] * candle['close'],
                number_of_trades=int(candle['volume'] / 10),
                taker_buy_base_asset_volume=candle['volume'] * 0.5,
                taker_buy_quote_asset_volume=candle['volume'] * candle['close'] * 0.5
            ))
        
        return klines

    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book for a symbol"""
        try:
            current_price = await self.get_live_price(symbol)
            if not current_price:
                return {}
            
            price = current_price['price']
            
            # Generate order book
            order_book = {
                'symbol': symbol,
                'bids': self._generate_order_book_side(price, 'bid', limit),
                'asks': self._generate_order_book_side(price, 'ask', limit),
                'timestamp': datetime.now().isoformat()
            }
            
            return order_book
            
        except Exception as e:
            self.logger.error(f"Error getting order book: {e}")
            return {}
    
    async def get_current_order_book(self, symbol: str, n_levels: int = 20) -> OrderBookSnapshot:
        """Get order book - compatible with existing interface"""
        logger.info(f"MarketDataService: Fetching order book for {symbol} (top {n_levels} levels)")
        if not symbol:
            raise MarketDataServiceError("Symbol must be provided for fetching order book.")
        
        # If we have a fetcher, use it
        if self.fetcher:
            try:
                order_book = await self.fetcher.get_order_book(symbol=symbol, n_levels=n_levels)
                logger.info(f"MarketDataService: Successfully fetched order book for {symbol}.")
                return order_book
            except Exception as e:
                logger.error(f"MarketDataService: Error fetching order book: {e}")
                # Fall through to mock data
        
        # Generate mock data as fallback
        order_book_data = await self.get_order_book(symbol, n_levels)
        
        # Convert to OrderBookSnapshot
        return OrderBookSnapshot(
            symbol=symbol,
            bids=[(bid['price'], bid['quantity']) for bid in order_book_data.get('bids', [])],
            asks=[(ask['price'], ask['quantity']) for ask in order_book_data.get('asks', [])],
            timestamp=int(datetime.now().timestamp() * 1000)
        )

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades - compatible with existing interface"""
        logger.info(f"MarketDataService: Fetching last {limit} trades for {symbol}")
        if not symbol:
            raise MarketDataServiceError("Symbol must be provided for fetching recent trades.")
        
        # If we have a fetcher, use it
        if self.fetcher:
            try:
                trades = await self.fetcher.get_trades(symbol=symbol, limit=limit)
                logger.info(f"MarketDataService: Successfully fetched {len(trades)} trades for {symbol}.")
                return trades
            except Exception as e:
                logger.error(f"MarketDataService: Error fetching recent trades: {e}")
                # Fall through to mock data
        
        # Generate mock trades as fallback
        trades_data = await self._get_recent_trades_data(symbol, limit)
        
        # Convert to Trade objects
        trades = []
        for trade_data in trades_data:
            trades.append(Trade(
                id=trade_data['id'],
                symbol=symbol,
                price=trade_data['price'],
                quantity=trade_data['quantity'],
                time=int(datetime.fromisoformat(trade_data['time']).timestamp() * 1000),
                is_buyer_maker=trade_data['is_buyer_maker']
            ))
        
        return trades
    
    async def _get_recent_trades_data(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades data for a symbol"""
        try:
            current_price = await self.get_live_price(symbol)
            if not current_price:
                return []
            
            price = current_price['price']
            
            # Generate recent trades
            trades = []
            base_time = datetime.now()
            
            for i in range(limit):
                time_offset = timedelta(seconds=i * random.randint(1, 10))
                trade_time = base_time - time_offset
                
                # Random price variation
                price_variation = price * random.uniform(-0.001, 0.001)
                trade_price = price + price_variation
                
                # Random quantity
                quantity = random.uniform(0.01, 10.0)
                
                trades.append({
                    'id': f"trade_{i}",
                    'price': round(trade_price, 2),
                    'quantity': round(quantity, 6),
                    'time': trade_time.isoformat(),
                    'is_buyer_maker': random.choice([True, False])
                })
            
            return trades
            
        except Exception as e:
            self.logger.error(f"Error getting recent trades: {e}")
            return []
    
    async def calculate_technical_indicators(self, symbol: str, 
                                           indicators: List[str] = None) -> Dict[str, Any]:
        """Calculate technical indicators for a symbol"""
        try:
            if indicators is None:
                indicators = ['RSI', 'MACD', 'BB', 'SMA', 'EMA']
            
            # Get historical data
            historical = await self.get_historical_data(symbol, '1h', 100)
            if not historical:
                return {}
            
            prices = [candle['close'] for candle in historical]
            
            results = {}
            
            # RSI
            if 'RSI' in indicators:
                results['RSI'] = self._calculate_rsi(prices)
            
            # MACD
            if 'MACD' in indicators:
                results['MACD'] = self._calculate_macd(prices)
            
            # Bollinger Bands
            if 'BB' in indicators:
                results['BB'] = self._calculate_bollinger_bands(prices)
            
            # Simple Moving Average
            if 'SMA' in indicators:
                results['SMA'] = {
                    'SMA_20': sum(prices[-20:]) / len(prices[-20:]) if len(prices) >= 20 else 0,
                    'SMA_50': sum(prices[-50:]) / len(prices[-50:]) if len(prices) >= 50 else 0,
                    'SMA_200': sum(prices) / len(prices) if len(prices) >= 200 else None
                }
            
            # Exponential Moving Average
            if 'EMA' in indicators:
                results['EMA'] = {
                    'EMA_12': self._calculate_ema(prices, 12),
                    'EMA_26': self._calculate_ema(prices, 26),
                    'EMA_50': self._calculate_ema(prices, 50)
                }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            return {}
    
    async def get_market_depth(self, symbol: str) -> Dict[str, Any]:
        """Get market depth analysis"""
        try:
            order_book = await self.get_order_book(symbol, 100)
            if not order_book:
                return {}
            
            # Calculate depth metrics
            bid_volume = sum(order['quantity'] for order in order_book['bids'])
            ask_volume = sum(order['quantity'] for order in order_book['asks'])
            
            bid_value = sum(order['price'] * order['quantity'] for order in order_book['bids'])
            ask_value = sum(order['price'] * order['quantity'] for order in order_book['asks'])
            
            return {
                'symbol': symbol,
                'bid_volume': bid_volume,
                'ask_volume': ask_volume,
                'bid_value': bid_value,
                'ask_value': ask_value,
                'bid_ask_ratio': bid_volume / ask_volume if ask_volume > 0 else 0,
                'spread': order_book['asks'][0]['price'] - order_book['bids'][0]['price'] if order_book['asks'] and order_book['bids'] else 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market depth: {e}")
            return {}
    
    async def subscribe_to_price_updates(self, symbols: List[str], callback):
        """Subscribe to real-time price updates"""
        # This would connect to WebSocket in production
        # For now, simulate with periodic updates
        while True:
            try:
                prices = await self.get_multiple_prices(symbols)
                await callback(prices)
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                self.logger.error(f"Error in price subscription: {e}")
                await asyncio.sleep(10)
    
    # Private helper methods
    
    async def _fetch_binance_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch price from Binance API"""
        try:
            # Convert symbol format
            binance_symbol = symbol.replace('/', '')
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.providers['binance']['rest_url']}/ticker/24hr"
                params = {'symbol': binance_symbol}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'symbol': symbol,
                            'price': float(data['lastPrice']),
                            'change_24h': float(data['priceChangePercent']),
                            'volume_24h': float(data['volume']),
                            'high_24h': float(data['highPrice']),
                            'low_24h': float(data['lowPrice']),
                            'bid': float(data['bidPrice']),
                            'ask': float(data['askPrice']),
                            'last_update': datetime.now().isoformat()
                        }
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching Binance price: {e}")
            return None
    
    def _generate_mock_price(self, symbol: str) -> Dict[str, Any]:
        """Generate mock price data"""
        base_prices = {
            'BTC/USDT': 45000,
            'ETH/USDT': 2500,
            'SOL/USDT': 100,
            'BNB/USDT': 350,
            'ADA/USDT': 0.50,
            'DOT/USDT': 7.50,
            'MATIC/USDT': 1.20,
            'LINK/USDT': 15.00
        }
        
        base_price = base_prices.get(symbol, 100)
        variation = random.uniform(-0.05, 0.05)
        price = base_price * (1 + variation)
        
        return {
            'symbol': symbol,
            'price': round(price, 2),
            'change_24h': round(random.uniform(-10, 10), 2),
            'volume_24h': int(random.uniform(1e7, 1e10)),
            'high_24h': round(price * 1.02, 2),
            'low_24h': round(price * 0.98, 2),
            'bid': round(price * 0.9999, 2),
            'ask': round(price * 1.0001, 2),
            'last_update': datetime.now().isoformat()
        }
    
    def _generate_historical_data(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        """Generate historical candlestick data"""
        current_price = self._generate_mock_price(symbol)['price']
        
        # Time intervals in minutes
        interval_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        
        minutes = interval_minutes.get(interval, 60)
        
        candles = []
        current_time = datetime.now()
        
        for i in range(limit):
            time_offset = timedelta(minutes=minutes * i)
            candle_time = current_time - time_offset
            
            # Generate OHLC data with realistic patterns
            volatility = 0.002
            open_price = current_price * (1 + random.uniform(-volatility, volatility))
            close_price = open_price * (1 + random.uniform(-volatility, volatility))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, volatility))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, volatility))
            
            volume = random.uniform(100, 10000)
            
            candles.append({
                'time': candle_time.isoformat(),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': round(volume, 2)
            })
            
            current_price = close_price
        
        return list(reversed(candles))
    
    def _generate_order_book_side(self, base_price: float, side: str, limit: int) -> List[Dict[str, Any]]:
        """Generate order book side (bids or asks)"""
        orders = []
        
        for i in range(limit):
            if side == 'bid':
                price = base_price * (1 - 0.0001 * (i + 1))
            else:
                price = base_price * (1 + 0.0001 * (i + 1))
            
            quantity = random.uniform(0.1, 50.0) * (limit - i) / limit
            
            orders.append({
                'price': round(price, 2),
                'quantity': round(quantity, 6)
            })
        
        return orders
    
    async def _get_top_movers(self, type: str) -> List[Dict[str, Any]]:
        """Get top gainers or losers"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT', 
                   'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 'AVAX/USDT', 'ATOM/USDT']
        
        prices = await self.get_multiple_prices(symbols)
        
        # Sort by change percentage
        sorted_prices = sorted(prices.values(), 
                             key=lambda x: x.get('change_24h', 0), 
                             reverse=(type == 'gainers'))
        
        return sorted_prices[:5]
    
    async def _get_trending_symbols(self) -> List[str]:
        """Get trending symbols based on volume"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT']
        prices = await self.get_multiple_prices(symbols)
        
        # Sort by volume
        sorted_symbols = sorted(prices.items(), 
                              key=lambda x: x[1].get('volume_24h', 0), 
                              reverse=True)
        
        return [symbol for symbol, _ in sorted_symbols[:5]]
    
    def _get_mock_market_summary(self) -> Dict[str, Any]:
        """Get mock market summary"""
        return {
            'total_market_cap': 1.85e12,
            'total_volume_24h': 98.5e9,
            'btc_dominance': 48.5,
            'average_change_24h': 2.34,
            'top_gainers': [],
            'top_losers': [],
            'trending': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
            'last_update': datetime.now().isoformat()
        }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period:
            return 50.0
        
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        seed = deltas[:period+1]
        up = sum([d for d in seed if d >= 0]) / period
        down = -sum([d for d in seed if d < 0]) / period
        rs = up / down if down != 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def _calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """Calculate MACD indicator"""
        if len(prices) < 26:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd = ema_12 - ema_26
        signal = self._calculate_ema([macd], 9)
        histogram = macd - signal
        
        return {
            'macd': round(macd, 2),
            'signal': round(signal, 2),
            'histogram': round(histogram, 2)
        }
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0}
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / len(recent_prices)
        variance = sum((p - sma) ** 2 for p in recent_prices) / len(recent_prices)
        std = math.sqrt(variance)
        
        return {
            'upper': round(sma + (2 * std), 2),
            'middle': round(sma, 2),
            'lower': round(sma - (2 * std), 2)
        }
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA"""
        if len(prices) < period:
            return sum(prices) / len(prices) if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return round(ema, 2)


# Register service
service_registry.register('market_data', MarketDataService)
