from typing import List, Dict, Any
from datetime import datetime, timezone
from hyperliquid.info import Info
from hyperliquid.utils.types import L2BookMsg, TradeMsg, Kline as SdkKline # Assuming these are the relevant types from SDK
from python_ai_services.models.market_data_models import Kline, OrderBookLevel, OrderBookSnapshot, Trade
from loguru import logger
import time # For converting timestamps

# Helper to convert HL timestamps (ms) to datetime
def hl_ms_to_datetime(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)

class HyperliquidMarketDataFetcherError(Exception):
    pass

class HyperliquidMarketDataFetcher:
    def __init__(self, base_url: str = "https://api.hyperliquid.xyz"):
        try:
            self.info = Info(base_url, skip_ws=True) # Skip WebSocket for pure data fetching
            logger.info("Hyperliquid Info client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Hyperliquid Info client: {e}")
            # Depending on desired behavior, could raise an error or set self.info to None
            # For now, let's allow it to be None and handle in methods
            self.info = None
            raise HyperliquidMarketDataFetcherError(f"Failed to initialize Hyperliquid Info client: {e}")

    def _ensure_info_client(self):
        if not self.info:
            raise HyperliquidMarketDataFetcherError("Hyperliquid Info client is not initialized.")

    async def get_klines(self, symbol: str, interval: str, start_time_ms: int, end_time_ms: int) -> List[Kline]:
        self._ensure_info_client()
        logger.debug(f"Fetching klines for {symbol}, interval {interval}, from {start_time_ms} to {end_time_ms}")
        try:
            # The SDK's candles method might take coin name (e.g., "ETH")
            # and interval (e.g., "1m", "1h", "1d")
            # Need to map our symbol (e.g., "ETH/USD") to coin if necessary
            # For now, assuming symbol is the coin name.
            sdk_klines: List[SdkKline] = await self.info.candles(
                coin=symbol,
                interval=interval,
                startTime=start_time_ms,
                endTime=end_time_ms
            )

            klines_data = []
            for sdk_kline in sdk_klines:
                # Assuming SdkKline has fields: t (timestamp_ms), o, h, l, c, v
                # Timestamp 't' from SDK is usually the start of the interval
                klines_data.append(Kline(
                    timestamp=hl_ms_to_datetime(sdk_kline['t']),
                    open=float(sdk_kline['o']),
                    high=float(sdk_kline['h']),
                    low=float(sdk_kline['l']),
                    close=float(sdk_kline['c']),
                    volume=float(sdk_kline['v'])
                ))
            logger.info(f"Successfully fetched {len(klines_data)} klines for {symbol} interval {interval}.")
            return klines_data
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol} from Hyperliquid: {e}")
            # Consider specific error handling for rate limits, invalid symbols, etc.
            raise HyperliquidMarketDataFetcherError(f"Error fetching klines: {e}")


    async def get_order_book(self, symbol: str, n_levels: int = 20) -> OrderBookSnapshot:
        self._ensure_info_client()
        logger.debug(f"Fetching order book for {symbol} (top {n_levels} levels)")
        try:
            # SDK's l2_book method for a given coin (symbol)
            l2_book_data: L2BookMsg = await self.info.l2_book(coin=symbol)

            bids = []
            asks = []

            # Process bids (typically highest price first from SDK)
            if 'levels' in l2_book_data and len(l2_book_data['levels']) > 0:
                for level_data in l2_book_data['levels'][0][:n_levels]: # levels[0] for bids
                    bids.append(OrderBookLevel(price=float(level_data['px']), quantity=float(level_data['sz'])))

            # Process asks (typically lowest price first from SDK)
            if 'levels' in l2_book_data and len(l2_book_data['levels']) > 1:
                for level_data in l2_book_data['levels'][1][:n_levels]: # levels[1] for asks
                    asks.append(OrderBookLevel(price=float(level_data['px']), quantity=float(level_data['sz'])))

            snapshot_timestamp = hl_ms_to_datetime(l2_book_data.get('time', int(time.time() * 1000)))

            logger.info(f"Successfully fetched order book for {symbol}. Bids: {len(bids)}, Asks: {len(asks)}")
            return OrderBookSnapshot(
                symbol=symbol,
                timestamp=snapshot_timestamp,
                bids=bids,
                asks=asks
            )
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol} from Hyperliquid: {e}")
            raise HyperliquidMarketDataFetcherError(f"Error fetching order book: {e}")

    async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        self._ensure_info_client()
        logger.debug(f"Fetching last {limit} trades for {symbol}")
        try:
            # SDK's trades method for a given coin
            sdk_trades: List[TradeMsg] = await self.info.trades(coin=symbol, limit=limit)

            trades_data = []
            for sdk_trade in sdk_trades:
                # Assuming TradeMsg has fields: time (ms), price, size, side ('B' or 'S'), hash (trade_id)
                trades_data.append(Trade(
                    trade_id=sdk_trade['hash'],
                    timestamp=hl_ms_to_datetime(sdk_trade['time']),
                    symbol=symbol, # SDK trades are per coin, symbol context is from call
                    price=float(sdk_trade['px']),
                    quantity=float(sdk_trade['sz']),
                    side="buy" if sdk_trade['side'] == 'B' else "sell"
                ))
            logger.info(f"Successfully fetched {len(trades_data)} trades for {symbol}.")
            return trades_data
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol} from Hyperliquid: {e}")
            raise HyperliquidMarketDataFetcherError(f"Error fetching trades: {e}")
