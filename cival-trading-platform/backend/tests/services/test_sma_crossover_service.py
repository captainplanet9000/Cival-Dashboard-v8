import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import List, Optional, Literal # Added Literal
from datetime import datetime, timezone, timedelta
import pandas as pd

from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig, AgentConfigBase
from python_ai_services.models.market_data_models import Kline
from python_ai_services.models.event_bus_models import Event, TradeSignalEventPayload
from python_ai_services.models.learning_models import LearningLogEntry
from python_ai_services.services.market_data_service import MarketDataService
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.services.learning_data_logger_service import LearningDataLoggerService
from python_ai_services.services.sma_crossover_service import SMACrossoverTechnicalService

# --- Fixtures ---

@pytest_asyncio.fixture
def mock_market_data_service() -> AsyncMock:
    return AsyncMock(spec=MarketDataService)

@pytest_asyncio.fixture
def mock_event_bus_service() -> AsyncMock:
    return AsyncMock(spec=EventBusService)

@pytest_asyncio.fixture
def mock_learning_logger_service() -> AsyncMock:
    return AsyncMock(spec=LearningDataLoggerService)

def create_sma_agent_config(
    short_window: int,
    long_window: int,
    sma_type: Literal["SMA", "EMA"] = "SMA"
) -> AgentConfigOutput:
    params = AgentStrategyConfig.SMACrossoverParams(
        short_window=short_window, long_window=long_window, sma_type=sma_type
    )
    base_config = AgentConfigBase(
        name="SMACrossoverTestAgent",
        strategy=AgentStrategyConfig(
            strategy_name="sma_crossover",
            sma_crossover_params=params,
            watched_symbols=["TEST/USD"],
            parameters={} # Ensure parameters is not None
        ),
        risk_config=AgentRiskConfig(max_capital_allocation_usd=1000, risk_per_trade_percentage=0.01, max_loss_per_trade_percentage_balance=0.01, max_concurrent_open_trades=1,max_exposure_per_asset_usd=1),
        execution_provider="paper"
    )
    return AgentConfigOutput(
        **base_config.model_dump(),
        agent_id="sma_agent_test_id", user_id="test_user", is_active=True,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        last_heartbeat=datetime.now(timezone.utc), message="Online"
    )

@pytest_asyncio.fixture
def sma_service(
    mock_market_data_service: AsyncMock,
    mock_event_bus_service: AsyncMock,
    mock_learning_logger_service: AsyncMock,
) -> SMACrossoverTechnicalService:
    agent_config = create_sma_agent_config(short_window=5, long_window=10)
    return SMACrossoverTechnicalService(
        agent_config=agent_config,
        market_data_service=mock_market_data_service,
        event_bus_service=mock_event_bus_service,
        learning_logger_service=mock_learning_logger_service,
    )

def create_klines_for_sma(prices: List[float], start_time: Optional[datetime] = None) -> List[Kline]:
    if start_time is None:
        start_time = datetime.now(timezone.utc) - timedelta(minutes=len(prices))
    return [Kline(timestamp=start_time + timedelta(minutes=i), open=p, high=p, low=p, close=p, volume=100) for i, p in enumerate(prices)]

@pytest.mark.asyncio
async def test_sma_calculation(sma_service: SMACrossoverTechnicalService):
    prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0] # Floats for consistency
    df = pd.DataFrame({'close': prices})
    sma5 = sma_service._calculate_sma(df['close'], 5)
    assert len(sma5.dropna()) == 2
    assert sma5.iloc[-1] == pytest.approx(13.0) # (11+12+13+14+15)/5 = 13

@pytest.mark.asyncio
async def test_ema_calculation(sma_service: SMACrossoverTechnicalService):
    prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    df = pd.DataFrame({'close': prices})
    ema5 = sma_service._calculate_ema(df['close'], 5)
    assert len(ema5) == len(prices)
    assert ema5.iloc[-1] > ema5.iloc[0]

@pytest.mark.asyncio
async def test_no_signal_if_not_enough_data(sma_service: SMACrossoverTechnicalService, mock_market_data_service: AsyncMock, mock_event_bus_service: AsyncMock):
    mock_market_data_service.get_historical_klines.return_value = create_klines_for_sma([10.0]*8) # Use float
    await sma_service.analyze_symbol_and_generate_signal("TEST/USD")
    mock_event_bus_service.publish.assert_not_called()

@pytest.mark.asyncio
async def test_golden_cross_buy_signal_sma(mock_market_data_service: AsyncMock, mock_event_bus_service: AsyncMock, mock_learning_logger_service: AsyncMock):
    agent_config_buy = create_sma_agent_config(short_window=2, long_window=4, sma_type="SMA")
    service_buy = SMACrossoverTechnicalService(agent_config_buy, mock_market_data_service, mock_event_bus_service, mock_learning_logger_service)
    prices_buy = [10.0,10.0,10.0,10.0,  9.0, 9.0, 12.0,13.0]
    mock_market_data_service.get_historical_klines.return_value = create_klines_for_sma(prices_buy)

    await service_buy.analyze_symbol_and_generate_signal("TEST/USD")

    mock_event_bus_service.publish.assert_called_once()
    event_arg: Event = mock_event_bus_service.publish.call_args[0][0]
    assert event_arg.message_type == "TradeSignalEvent"
    payload = TradeSignalEventPayload(**event_arg.payload)
    assert payload.signal_type == "buy"
    assert payload.price_at_signal == 13.0

@pytest.mark.asyncio
async def test_death_cross_sell_signal_ema(mock_market_data_service: AsyncMock, mock_event_bus_service: AsyncMock, mock_learning_logger_service: AsyncMock):
    agent_config_sell = create_sma_agent_config(short_window=2, long_window=4, sma_type="EMA")
    service_sell = SMACrossoverTechnicalService(agent_config_sell, mock_market_data_service, mock_event_bus_service, mock_learning_logger_service)
    prices_sell = [10.0,11.0,12.0,13.0, 11.0,9.0,8.0,7.0]
    mock_market_data_service.get_historical_klines.return_value = create_klines_for_sma(prices_sell)

    await service_sell.analyze_symbol_and_generate_signal("TEST/USD")

    mock_event_bus_service.publish.assert_called_once()
    event_arg: Event = mock_event_bus_service.publish.call_args[0][0]
    assert event_arg.message_type == "TradeSignalEvent"
    payload = TradeSignalEventPayload(**event_arg.payload)
    assert payload.signal_type == "sell"
    assert payload.price_at_signal == 7.0

@pytest.mark.asyncio
async def test_no_signal_when_no_crossover(sma_service: SMACrossoverTechnicalService, mock_market_data_service: AsyncMock, mock_event_bus_service: AsyncMock):
    prices_no_cross = [10,11,12,13,14,15,16,17,18,19,20] # Trending up, no crossover for 5/10
    mock_market_data_service.get_historical_klines.return_value = create_klines_for_sma(prices_no_cross)
    await sma_service.analyze_symbol_and_generate_signal("TEST/USD")
    mock_event_bus_service.publish.assert_not_called()

@pytest.mark.asyncio
async def test_logging_called_on_signal(mock_market_data_service: AsyncMock, mock_event_bus_service: AsyncMock, mock_learning_logger_service: AsyncMock):
    agent_config = create_sma_agent_config(short_window=2, long_window=4, sma_type="SMA")
    service = SMACrossoverTechnicalService(agent_config, mock_market_data_service, mock_event_bus_service, mock_learning_logger_service)
    prices_buy = [10.0,10.0,10.0,10.0,  9.0, 9.0, 12.0,13.0]
    mock_market_data_service.get_historical_klines.return_value = create_klines_for_sma(prices_buy)

    await service.analyze_symbol_and_generate_signal("TEST/USD")

    # AnalysisStarted, TradeSignalPublished
    assert mock_learning_logger_service.log_entry.call_count >= 2
    assert any(call[0][0].event_type == "TradeSignalPublished" for call in mock_learning_logger_service.log_entry.call_args_list)

@pytest.mark.asyncio
async def test_logging_called_on_no_signal(sma_service: SMACrossoverTechnicalService, mock_market_data_service: AsyncMock, mock_learning_logger_service: AsyncMock):
    prices_no_cross = [10,11,12,13,14,15,16,17,18,19,20]
    mock_market_data_service.get_historical_klines.return_value = create_klines_for_sma(prices_no_cross)
    await sma_service.analyze_symbol_and_generate_signal("TEST/USD")

    # AnalysisStarted, NoSignal
    assert mock_learning_logger_service.log_entry.call_count >= 2
    assert any(call[0][0].event_type == "NoSignal" for call in mock_learning_logger_service.log_entry.call_args_list)
