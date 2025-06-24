import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import List
from datetime import datetime, timezone, timedelta

from python_ai_services.services.market_data_service import MarketDataService, MarketDataServiceError
from python_ai_services.utils.hyperliquid_data_fetcher import HyperliquidMarketDataFetcher, HyperliquidMarketDataFetcherError
from python_ai_services.models.market_data_models import Kline, OrderBookSnapshot, OrderBookLevel, Trade

# --- Mocks ---

@pytest_asyncio.fixture
def mock_fetcher() -> MagicMock:
    fetcher = AsyncMock(spec=HyperliquidMarketDataFetcher) # Use AsyncMock for async methods
    # Configure the 'info' attribute if it's accessed directly by the fetcher's constructor or methods
    # For this test structure, we are mocking the fetcher instance itself, so direct info access isn't an issue here.
    return fetcher

@pytest_asyncio.fixture
def market_service(mock_fetcher: MagicMock) -> MarketDataService:
    # Ensure the mock_fetcher passed to MarketDataService is adequate.
    # If MarketDataService's __init__ expects a fully initialized fetcher (with .info),
    # the mock_fetcher might need more setup, or we mock at a higher level.
    # For now, assuming direct pass-through is fine as fetcher methods are mocked.
    return MarketDataService(fetcher=mock_fetcher)

# --- Sample Data ---

def create_sample_klines(count: int) -> List[Kline]:
    return [
        Kline(
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=i),
            open=100.0 + i, high=105.0 + i, low=95.0 + i, close=102.0 + i, volume=1000.0 + i * 10
        ) for i in range(count)
    ]

def create_sample_order_book(symbol: str) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc),
        bids=[OrderBookLevel(price=99.0, quantity=10.0), OrderBookLevel(price=98.0, quantity=5.0)],
        asks=[OrderBookLevel(price=101.0, quantity=12.0), OrderBookLevel(price=102.0, quantity=6.0)]
    )

def create_sample_trades(symbol: str, count: int) -> List[Trade]:
    return [
        Trade(
            trade_id=f"trade_{i}", timestamp=datetime.now(timezone.utc) - timedelta(seconds=i),
            symbol=symbol, price=100.0 + i*0.1, quantity=1.0 + i*0.1, side="buy" if i % 2 == 0 else "sell"
        ) for i in range(count)
    ]

# --- Tests for get_historical_klines ---

@pytest.mark.asyncio
async def test_get_historical_klines_success(market_service: MarketDataService, mock_fetcher: MagicMock):
    symbol = "ETH/USD"
    interval = "1h"
    start_time = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    expected_klines = create_sample_klines(5)

    mock_fetcher.get_klines.return_value = expected_klines

    result = await market_service.get_historical_klines(symbol, interval, start_time, end_time)

    mock_fetcher.get_klines.assert_called_once_with(
        symbol=symbol,
        interval=interval,
        start_time_ms=int(start_time.timestamp() * 1000),
        end_time_ms=int(end_time.timestamp() * 1000)
    )
    assert result == expected_klines
    assert all(isinstance(k, Kline) for k in result)

@pytest.mark.asyncio
async def test_get_historical_klines_fetcher_error(market_service: MarketDataService, mock_fetcher: MagicMock):
    mock_fetcher.get_klines.side_effect = HyperliquidMarketDataFetcherError("Test fetcher error")

    with pytest.raises(MarketDataServiceError, match="Failed to fetch klines for TEST/USD: Test fetcher error"):
        await market_service.get_historical_klines(
            "TEST/USD", "1m", datetime.now(timezone.utc) - timedelta(hours=1), datetime.now(timezone.utc)
        )

@pytest.mark.asyncio
async def test_get_historical_klines_input_validation(market_service: MarketDataService):
    with pytest.raises(MarketDataServiceError, match="Symbol must be provided"):
        await market_service.get_historical_klines("", "1m", datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(hours=1))
    with pytest.raises(MarketDataServiceError, match="Start time must be before end time"):
        await market_service.get_historical_klines("S/U", "1m", datetime.now(timezone.utc), datetime.now(timezone.utc) - timedelta(hours=1))

# --- Tests for get_current_order_book ---

@pytest.mark.asyncio
async def test_get_current_order_book_success(market_service: MarketDataService, mock_fetcher: MagicMock):
    symbol = "BTC/USD"
    n_levels = 10
    expected_ob = create_sample_order_book(symbol)

    mock_fetcher.get_order_book.return_value = expected_ob

    result = await market_service.get_current_order_book(symbol, n_levels)

    mock_fetcher.get_order_book.assert_called_once_with(symbol=symbol, n_levels=n_levels)
    assert result == expected_ob
    assert isinstance(result, OrderBookSnapshot)

@pytest.mark.asyncio
async def test_get_current_order_book_fetcher_error(market_service: MarketDataService, mock_fetcher: MagicMock):
    mock_fetcher.get_order_book.side_effect = HyperliquidMarketDataFetcherError("OB fetch error")

    with pytest.raises(MarketDataServiceError, match="Failed to fetch order book for TEST/OB: OB fetch error"):
        await market_service.get_current_order_book("TEST/OB", 5)

# --- Tests for get_recent_trades ---

@pytest.mark.asyncio
async def test_get_recent_trades_success(market_service: MarketDataService, mock_fetcher: MagicMock):
    symbol = "SOL/USD"
    limit = 50
    expected_trades = create_sample_trades(symbol, limit)

    mock_fetcher.get_trades.return_value = expected_trades

    result = await market_service.get_recent_trades(symbol, limit)

    mock_fetcher.get_trades.assert_called_once_with(symbol=symbol, limit=limit)
    assert result == expected_trades
    assert all(isinstance(t, Trade) for t in result)

@pytest.mark.asyncio
async def test_get_recent_trades_fetcher_error(market_service: MarketDataService, mock_fetcher: MagicMock):
    mock_fetcher.get_trades.side_effect = HyperliquidMarketDataFetcherError("Trades fetch error")

    with pytest.raises(MarketDataServiceError, match="Failed to fetch recent trades for TEST/TRADES: Trades fetch error"):
        await market_service.get_recent_trades("TEST/TRADES", 25)

# --- Test initialization error ---
def test_market_service_init_no_fetcher():
    with pytest.raises(ValueError, match="HyperliquidMarketDataFetcher instance is required."):
        MarketDataService(fetcher=None)
