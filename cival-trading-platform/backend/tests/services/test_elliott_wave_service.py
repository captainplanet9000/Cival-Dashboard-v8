import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig, AgentConfigBase
from python_ai_services.models.market_data_models import Kline
from python_ai_services.models.event_bus_models import Event, MarketInsightEventPayload
from python_ai_services.models.learning_models import LearningLogEntry # Added for specific log check
from python_ai_services.services.market_data_service import MarketDataService
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.services.learning_data_logger_service import LearningDataLoggerService
from python_ai_services.services.elliott_wave_service import ElliottWaveTechnicalService

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

@pytest_asyncio.fixture
def elliott_wave_params() -> AgentStrategyConfig.ElliottWaveParams:
    return AgentStrategyConfig.ElliottWaveParams(
        impulse_wave_min_candles=3,
        impulse_wave_min_total_change_pct=2.0,
        correction_fib_levels=[0.5],
        min_wave_3_extension_pct_of_wave_1=161.8
    )

@pytest_asyncio.fixture
def agent_config(elliott_wave_params: AgentStrategyConfig.ElliottWaveParams) -> AgentConfigOutput:
    base_config = AgentConfigBase(
        name="EWTestAgent",
        strategy=AgentStrategyConfig(
            strategy_name="elliott_wave",
            elliott_wave_params=elliott_wave_params,
            watched_symbols=["TEST/USD"]
        ),
        risk_config=AgentRiskConfig(max_capital_allocation_usd=1000, risk_per_trade_percentage=0.01, max_loss_per_trade_percentage_balance=0.01, max_concurrent_open_trades=1, max_exposure_per_asset_usd=1), # Added missing required fields
        execution_provider="paper"
    )
    return AgentConfigOutput(
        **base_config.model_dump(),
        agent_id="ew_agent_test_id",
        user_id="test_user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_heartbeat=datetime.now(timezone.utc),
        message="Online"
    )

@pytest_asyncio.fixture
def ew_service(
    agent_config: AgentConfigOutput,
    mock_market_data_service: AsyncMock,
    mock_event_bus_service: AsyncMock,
    mock_learning_logger_service: AsyncMock,
) -> ElliottWaveTechnicalService:
    return ElliottWaveTechnicalService(
        agent_config=agent_config,
        market_data_service=mock_market_data_service,
        event_bus_service=mock_event_bus_service,
        learning_logger_service=mock_learning_logger_service,
    )

def create_klines(prices: List[float], start_time: Optional[datetime] = None) -> List[Kline]:
    if start_time is None:
        start_time = datetime.now(timezone.utc) - timedelta(minutes=len(prices))
    klines = []
    for i, price in enumerate(prices):
        klines.append(Kline(
            timestamp=start_time + timedelta(minutes=i),
            open=price, high=price + 0.5, low=price - 0.5, close=price, volume=1000
        ))
    return klines

@pytest.mark.asyncio
async def test_find_significant_moves_no_moves(ew_service: ElliottWaveTechnicalService):
    klines = create_klines([10, 10.1, 10, 10.1, 10])
    moves = await ew_service._find_significant_moves(klines, 3, 5.0)
    assert len(moves) == 0

@pytest.mark.asyncio
async def test_find_significant_moves_upward_move(ew_service: ElliottWaveTechnicalService):
    klines = create_klines([10, 11, 12, 13, 12.5])
    moves = await ew_service._find_significant_moves(klines,
                                                     ew_service.params.impulse_wave_min_candles,
                                                     ew_service.params.impulse_wave_min_total_change_pct)
    assert len(moves) == 1
    assert moves[0]["type"] == "up"
    assert moves[0]["start_idx"] == 0
    assert moves[0]["end_idx"] == 3
    assert moves[0]["start_price"] == Decimal("10")
    assert moves[0]["end_price"] == Decimal("13")

@pytest.mark.asyncio
async def test_find_significant_moves_downward_move(ew_service: ElliottWaveTechnicalService):
    klines = create_klines([13, 12, 11, 10, 10.5])
    moves = await ew_service._find_significant_moves(klines,
                                                     ew_service.params.impulse_wave_min_candles,
                                                     ew_service.params.impulse_wave_min_total_change_pct)
    down_move_found = any(m["type"] == "down" and m["start_idx"] == 0 and m["end_idx"] == 3 for m in moves)
    assert down_move_found

@pytest.mark.asyncio
async def test_analyze_symbol_no_wave1(ew_service: ElliottWaveTechnicalService, mock_event_bus_service: AsyncMock):
    klines = create_klines([10, 10.1, 10.2, 10.1, 10.3, 10.2])
    await ew_service.analyze_symbol("TEST/USD", klines)
    mock_event_bus_service.publish.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_symbol_identifies_wave1_up_then_wave2_correction(ew_service: ElliottWaveTechnicalService, mock_event_bus_service: AsyncMock):
    prices = [10, 11, 12, 13, 12.5, 11.5, 11.6, 11.7]
    klines = create_klines(prices)
    await ew_service.analyze_symbol("TEST/USD", klines)

    published_event_found = False
    for call_args in mock_event_bus_service.publish.call_args_list:
        event_arg: Event = call_args[0][0]
        if event_arg.message_type == "MarketInsightEvent":
            payload = MarketInsightEventPayload(**event_arg.payload)
            if payload.insight_type == "ElliottWave_Potential_W2_Correction":
                assert payload.symbol == "TEST/USD"
                assert "Wave 1 (up)" in payload.content
                assert payload.metadata["fib_level"] == 0.5
                published_event_found = True
                break
    assert published_event_found

@pytest.mark.asyncio
async def test_analyze_symbol_identifies_wave1_down_then_wave2_correction(ew_service: ElliottWaveTechnicalService, mock_event_bus_service: AsyncMock):
    prices = [13, 12, 11, 10, 10.5, 11.5, 11.4, 11.3]
    klines = create_klines(prices)
    await ew_service.analyze_symbol("TEST/USD", klines)

    published_event_found = False
    for call_args in mock_event_bus_service.publish.call_args_list:
        event_arg: Event = call_args[0][0]
        if event_arg.message_type == "MarketInsightEvent":
            payload = MarketInsightEventPayload(**event_arg.payload)
            if payload.insight_type == "ElliottWave_Potential_W2_Correction":
                assert payload.symbol == "TEST/USD"
                assert "Wave 1 (down)" in payload.content
                assert payload.metadata["fib_level"] == 0.5
                published_event_found = True
                break
    assert published_event_found

@pytest.mark.asyncio
async def test_run_analysis_for_symbol_calls_market_data(ew_service: ElliottWaveTechnicalService, mock_market_data_service: AsyncMock):
    mock_market_data_service.get_historical_klines.return_value = create_klines([10,11,12,13,11.5])
    await ew_service.run_analysis_for_symbol("TEST/USD", "1h", 30)
    mock_market_data_service.get_historical_klines.assert_called_once()

@pytest.mark.asyncio
async def test_logging_called(ew_service: ElliottWaveTechnicalService, mock_learning_logger_service: AsyncMock):
    klines = create_klines([10, 11, 12, 13, 12.5, 11.5, 11.6, 11.7])
    await ew_service.analyze_symbol("TEST/USD", klines)

    assert mock_learning_logger_service.log_entry.call_count >= 2
    analysis_started_logged = any(call_arg[0][0].event_type == "AnalysisStarted" for call_arg in mock_learning_logger_service.log_entry.call_args_list)
    potential_w2_logged = any(call_arg[0][0].event_type == "PotentialWave2Insight" for call_arg in mock_learning_logger_service.log_entry.call_args_list)
    assert analysis_started_logged
    assert potential_w2_logged
