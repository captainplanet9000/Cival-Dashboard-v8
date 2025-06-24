import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from python_ai_services.services.darvas_box_service import DarvasBoxTechnicalService
from python_ai_services.services.market_data_service import MarketDataService
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig
# Import DarvasStrategyParams from its definition location
from python_ai_services.models.agent_models import AgentStrategyConfig # DarvasStrategyParams is nested here
from python_ai_services.models.event_bus_models import Event, TradeSignalEventPayload

# --- Fixtures ---
@pytest_asyncio.fixture
def mock_event_bus() -> EventBusService:
    service = AsyncMock(spec=EventBusService)
    service.publish = AsyncMock() # Ensure publish is an AsyncMock
    return service

@pytest_asyncio.fixture
def mock_market_data_service() -> MarketDataService:
    service = AsyncMock(spec=MarketDataService)
    service.get_historical_klines = AsyncMock() # Ensure this is AsyncMock
    return service

def create_darvas_agent_config(
    agent_id: str,
    lookback: int = 20,
    box_min_perc: float = 0.02,
    sl_perc: float = 0.01,
    darvas_params_override: Optional[Dict] = None # For testing missing params
) -> AgentConfigOutput:

    darvas_specific_params = AgentStrategyConfig.DarvasStrategyParams(
        lookback_period=lookback,
        box_range_min_percentage=box_min_perc,
        stop_loss_percentage_from_box_bottom=sl_perc
    )
    if darvas_params_override == "MISSING": # Special value to test None case
        darvas_params_for_strat_config = None
    elif isinstance(darvas_params_override, dict):
        darvas_params_for_strat_config = AgentStrategyConfig.DarvasStrategyParams(**darvas_params_override)
    else:
        darvas_params_for_strat_config = darvas_specific_params

    strategy_config = AgentStrategyConfig(
        strategy_name="DarvasBox",
        parameters={}, # General params, not used by this service directly
        darvas_params=darvas_params_for_strat_config
    )
    return AgentConfigOutput(
        agent_id=agent_id,
        name=f"DarvasAgent_{agent_id}",
        strategy=strategy_config,
        risk_config=AgentRiskConfig(max_capital_allocation_usd=1000, risk_per_trade_percentage=0.01),
        agent_type="DarvasBoxTechnicalAgent" # Important for orchestrator logic
    )

# --- Helper to generate klines ---
def generate_klines(
    count: int, box_top: float = 100.0, box_bottom: float = 95.0,
    breakout: bool = False, current_price_override: Optional[float] = None
) -> List[Dict[str, Any]]:
    klines = []
    for i in range(count):
        k = {
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=count - i)).timestamp() * 1000,
            "open": box_bottom + 1, "high": box_top, "low": box_bottom, "close": box_top -1
        }
        if i == count -1 : # Last candle (current candle)
            if breakout:
                k["high"] = box_top + 5
                k["close"] = box_top + 2 # Breakout
            elif current_price_override is not None:
                 k["close"] = current_price_override
            else:
                k["close"] = box_top -1 # No breakout
        klines.append(k)
    return klines

# --- Test Cases ---

@pytest.mark.asyncio
async def test_darvas_service_init_with_params(mock_event_bus, mock_market_data_service):
    agent_config = create_darvas_agent_config("agent1", lookback=30)
    service = DarvasBoxTechnicalService(agent_config, mock_event_bus, mock_market_data_service)
    assert service.params.lookback_period == 30

@pytest.mark.asyncio
async def test_darvas_service_init_no_darvas_params_uses_defaults(mock_event_bus, mock_market_data_service):
    agent_config = create_darvas_agent_config("agent_no_params", darvas_params_override="MISSING")
    service = DarvasBoxTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    default_params = AgentStrategyConfig.DarvasStrategyParams()
    assert service.params.lookback_period == default_params.lookback_period
    assert service.params.box_range_min_percentage == default_params.box_range_min_percentage

@pytest.mark.asyncio
async def test_analyze_insufficient_data(mock_event_bus, mock_market_data_service):
    agent_config = create_darvas_agent_config("agent_insufficient_data", lookback=20)
    service = DarvasBoxTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    # Market data service returns fewer klines than needed (lookback + confirmation)
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=generate_klines(10)) # Need 20+1=21

    await service.analyze_symbol_and_generate_signal("BTC/USD")
    mock_event_bus.publish.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_breakout_signal_published(mock_event_bus, mock_market_data_service):
    lookback = 20
    agent_config = create_darvas_agent_config("agent_breakout", lookback=lookback)
    service = DarvasBoxTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    # Simulate klines data for a breakout
    # Box top = 100, current close = 102 (breakout)
    klines_data = generate_klines(lookback + 1, box_top=100.0, box_bottom=95.0, breakout=True)
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=klines_data)

    await service.analyze_symbol_and_generate_signal("BTC/USD")

    mock_event_bus.publish.assert_called_once()
    published_event: Event = mock_event_bus.publish.call_args[0][0]
    assert published_event.publisher_agent_id == "agent_breakout"
    assert published_event.message_type == "TradeSignalEvent"
    payload = TradeSignalEventPayload(**published_event.payload)
    assert payload.symbol == "BTC/USD"
    assert payload.action == "buy"
    assert payload.price_target == klines_data[-1]['close'] # Breakout price
    assert payload.stop_loss is not None
    # SL = box_bottom * (1 - stop_loss_percentage_from_box_bottom) = 95 * (1 - 0.01) = 95 * 0.99 = 94.05
    assert payload.stop_loss == pytest.approx(95.0 * (1 - agent_config.strategy.darvas_params.stop_loss_percentage_from_box_bottom)) # type: ignore

@pytest.mark.asyncio
async def test_analyze_no_breakout(mock_event_bus, mock_market_data_service):
    lookback = 20
    agent_config = create_darvas_agent_config("agent_no_breakout", lookback=lookback)
    service = DarvasBoxTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    klines_data = generate_klines(lookback + 1, box_top=100.0, breakout=False, current_price_override=99.0) # Price below box top
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=klines_data)

    await service.analyze_symbol_and_generate_signal("ETH/USD")
    mock_event_bus.publish.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_box_range_too_small(mock_event_bus, mock_market_data_service):
    lookback = 20
    # Min box range 2%, box will be 100-99 (1% range)
    agent_config = create_darvas_agent_config("agent_small_box", lookback=lookback, box_min_perc=0.02)
    service = DarvasBoxTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    # Box top=100, bottom=99. Breakout price=101. Box range = (100-99)/100 = 1%
    klines_data = generate_klines(lookback + 1, box_top=100.0, box_bottom=99.0, breakout=True, current_price_override=101.0)
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=klines_data)

    await service.analyze_symbol_and_generate_signal("ADA/USD")
    mock_event_bus.publish.assert_not_called() # Signal skipped due to small box range

@pytest.mark.asyncio
async def test_analyze_box_range_check_disabled(mock_event_bus, mock_market_data_service):
    lookback = 20
    # Min box range 0% (disabled)
    agent_config = create_darvas_agent_config("agent_box_check_off", lookback=lookback, box_min_perc=0.0)
    service = DarvasBoxTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    klines_data = generate_klines(lookback + 1, box_top=100.0, box_bottom=99.9, breakout=True, current_price_override=101.0) # Very small box
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=klines_data)

    await service.analyze_symbol_and_generate_signal("XRP/USD")
    mock_event_bus.publish.assert_called_once() # Signal should be published as check is off

# Need Optional, List, Dict, Any for helpers and typing
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta # For helper
