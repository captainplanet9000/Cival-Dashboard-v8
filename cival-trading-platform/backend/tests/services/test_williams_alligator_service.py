import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from typing import List, Dict, Any, Optional

from python_ai_services.services.williams_alligator_service import WilliamsAlligatorTechnicalService
from python_ai_services.services.market_data_service import MarketDataService
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig
# Import WilliamsAlligatorParams from its definition location
from python_ai_services.models.agent_models import AgentStrategyConfig # WilliamsAlligatorParams is nested
from python_ai_services.models.event_bus_models import Event, TradeSignalEventPayload
from datetime import datetime, timezone, timedelta


@pytest_asyncio.fixture
def mock_event_bus() -> EventBusService:
    service = AsyncMock(spec=EventBusService)
    service.publish = AsyncMock()
    return service

@pytest_asyncio.fixture
def mock_market_data_service() -> MarketDataService:
    service = AsyncMock(spec=MarketDataService)
    service.get_historical_klines = AsyncMock()
    return service

def create_wa_agent_config(
    agent_id: str,
    params_override: Optional[Dict[str, Any]] = None, # For testing with specific WA params
    use_default_wa_params: bool = False # To test fallback to default
) -> AgentConfigOutput:

    wa_params = None
    if not use_default_wa_params:
        actual_params_data = {
            "jaw_period": 13, "jaw_shift": 8,
            "teeth_period": 8, "teeth_shift": 5,
            "lips_period": 5, "lips_shift": 3
        }
        if params_override:
            actual_params_data.update(params_override)
        wa_params = AgentStrategyConfig.WilliamsAlligatorParams(**actual_params_data)

    strategy_config = AgentStrategyConfig(
        strategy_name="WilliamsAlligator",
        parameters={},
        williams_alligator_params=wa_params # Can be None if use_default_wa_params is True
    )
    return AgentConfigOutput(
        agent_id=agent_id,
        name=f"WA_Agent_{agent_id}",
        strategy=strategy_config,
        risk_config=MagicMock(), # Not directly used by this service's analysis part
        agent_type="WilliamsAlligatorTechnicalAgent"
    )

# Helper to generate klines for Alligator tests
def generate_alligator_klines(count: int, price_pattern: List[float]) -> List[Dict[str, Any]]:
    klines = []
    base_time = datetime.now(timezone.utc) - timedelta(days=count)
    if len(price_pattern) < count: # Cycle through pattern if shorter
        price_pattern = (price_pattern * ((count // len(price_pattern)) + 1))[:count]

    for i in range(count):
        ts = base_time + timedelta(days=i)
        price = price_pattern[i]
        klines.append({
            "timestamp": int(ts.timestamp() * 1000),
            "open": price - 0.5, "high": price + 1, "low": price - 1, "close": price, "volume": 1000 + i
        })
    return klines

# --- Test Cases ---

@pytest.mark.asyncio
async def test_wa_service_init_params(mock_event_bus, mock_market_data_service):
    # Test with specific params
    agent_config_custom = create_wa_agent_config("agent_custom", params_override={"jaw_period": 21})
    service_custom = WilliamsAlligatorTechnicalService(agent_config_custom, mock_event_bus, mock_market_data_service)
    assert service_custom.params.jaw_period == 21
    assert service_custom.params.lips_period == 5 # Default if not overridden

    # Test fallback to default params
    agent_config_default = create_wa_agent_config("agent_default", use_default_wa_params=True)
    service_default = WilliamsAlligatorTechnicalService(agent_config_default, mock_event_bus, mock_market_data_service)
    default_model_params = AgentStrategyConfig.WilliamsAlligatorParams()
    assert service_default.params.jaw_period == default_model_params.jaw_period


@pytest.mark.asyncio
async def test_calculate_sma(mock_event_bus, mock_market_data_service):
    # Service instance needed to access _calculate_sma, though it's not async or dependent on instance state here
    agent_config = create_wa_agent_config("sma_test_agent")
    service = WilliamsAlligatorTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    data = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    period = 3
    sma = service._calculate_sma(data, period)
    expected_sma = [None, None, 11.0, 12.0, 13.0, 14.0] # (10+11+12)/3=11, (11+12+13)/3=12 ...
    assert sma == expected_sma

    # Test with insufficient data
    sma_short = service._calculate_sma([10.0, 11.0], 3)
    assert sma_short == [None, None]

    # Test with empty data
    sma_empty = service._calculate_sma([], 3)
    assert sma_empty == []


@pytest.mark.asyncio
async def test_analyze_insufficient_kline_data(mock_event_bus, mock_market_data_service):
    agent_config = create_wa_agent_config("agent_insufficient")
    service = WilliamsAlligatorTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    # Default params: jaw(13,8), teeth(8,5), lips(5,3). Max period = 13, max shift = 8.
    # Required data points = 13 + 8 + 2 = 23
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=generate_alligator_klines(20, [100]*20))

    await service.analyze_symbol_and_generate_signal("BTC/USD")
    mock_event_bus.publish.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_sma_calculation_results_in_nones(mock_event_bus, mock_market_data_service):
    # This can happen if klines are fetched, but not enough for the longest SMA + shift to produce non-None values at the end
    agent_config = create_wa_agent_config("agent_sma_nones", params_override={"jaw_period": 20, "jaw_shift": 10}) # Long jaw
    service = WilliamsAlligatorTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    # Required data = 20 (jaw_period) + 10 (jaw_shift) + 2 = 32
    # If we provide exactly 32, the shifted jaw_prev might still be None if SMA starts with many Nones.
    # The _calculate_sma pads with (period-1) Nones. So jaw_sma_unshifted[0] to jaw_sma_unshifted[18] are None for period 20.
    # jaw_sma_unshifted[19] is first value.
    # idx_jaw_current = 31 - 10 = 21. jaw_sma_unshifted[21] is available.
    # idx_jaw_prev = 20. jaw_sma_unshifted[20] is available.
    # This test setup should pass the "None in [...]" check IF _calculate_sma works correctly with min_periods=period.

    # Let's test a case where one of the SMAs becomes None due to not enough *initial* data for its period.
    # e.g. if get_historical_klines returned data shorter than one of the periods.
    # This is mostly covered by the main length check, but this tests the None check in shifted values.
    klines_just_enough_for_shortest_sma = generate_alligator_klines(service.params.lips_period + service.params.lips_shift + 1, [100.0]*(service.params.lips_period + service.params.lips_shift +1))
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=klines_just_enough_for_shortest_sma)

    await service.analyze_symbol_and_generate_signal("BTC/USD")
    mock_event_bus.publish.assert_not_called() # Should return due to None in SMAs for longer periods


@pytest.mark.asyncio
async def test_analyze_generates_buy_signal(mock_event_bus, mock_market_data_service):
    agent_config = create_wa_agent_config("agent_buy_sig")
    service = WilliamsAlligatorTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    # Prices pattern: initial low, then lines tangle, then bullish breakout
    # Lips (5,3), Teeth (8,5), Jaw (13,8)
    # For buy: Lips > Teeth > Jaw, Lips_prev <= Teeth_prev, Price > Lips
    prices = ([100]*15 +  # Initial data for SMAs to settle
              [100, 99, 98, 97, 96] + # Jaw moves down
              [97, 98, 99, 100, 101] + # Teeth moves up, Lips moves up faster
              [102, 103, 104, 105, 106, 107, 108]) # Bullish trend, price breakout

    # Ensure enough data points: max_period (13) + max_shift (8) + 2 = 23. Let's use 30.
    klines = generate_alligator_klines(30, prices)
    # Manually adjust last kline to ensure breakout for test predictability
    klines[-1]['close'] = 110 # Current price
    klines[-1]['high'] = 111
    # We need to ensure the SMA values reflect the desired crossover and ordering.
    # This might require crafting the entire kline series more carefully or mocking SMA calculation.
    # For now, let's assume the generated klines + SMA logic will work.
    # A better way for complex indicator tests is to mock the _calculate_sma or the final SMA values.

    # Simplified: Mock final SMA values to force a buy signal
    service._calculate_sma = MagicMock()
    # Jaw (13,8), Teeth (8,5), Lips (5,3)
    # Example: current: Lips=105, Teeth=103, Jaw=100 (bullish order)
    #          prev:    Lips=102, Teeth=103 (lips just crossed teeth)
    # Price = 110 (above all lines)

    # Unshifted SMAs (length of klines = 30)
    # Last value is at index 29
    # jaw_current = sma_jaw[29-8=21], teeth_current = sma_teeth[29-5=24], lips_current = sma_lips[29-3=26]
    # jaw_prev = sma_jaw[20], teeth_prev = sma_teeth[23], lips_prev = sma_lips[25]

    sma_jaw_mock = ([None]*12 + list(range(90, 90+18))) # len 30, jaw_period 13
    sma_teeth_mock = ([None]*7 + list(range(95, 95+23)))# len 30, teeth_period 8
    sma_lips_mock = ([None]*4 + list(range(100, 100+26)))# len 30, lips_period 5

    # Override specific values to create the crossover scenario
    # lips_current = 105, lips_prev = 102
    sma_lips_mock[26] = 105.0 # lips_current
    sma_lips_mock[25] = 102.0 # lips_prev
    # teeth_current = 103, teeth_prev = 103
    sma_teeth_mock[24] = 103.0 # teeth_current
    sma_teeth_mock[23] = 103.0 # teeth_prev
    # jaw_current = 100, jaw_prev = 99
    sma_jaw_mock[21] = 100.0 # jaw_current
    sma_jaw_mock[20] = 99.0  # jaw_prev

    def sma_side_effect(data, period):
        if period == service.params.jaw_period: return sma_jaw_mock
        if period == service.params.teeth_period: return sma_teeth_mock
        if period == service.params.lips_period: return sma_lips_mock
        return [None]*len(data)
    service._calculate_sma.side_effect = sma_side_effect
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=klines)


    await service.analyze_symbol_and_generate_signal("BUY/SIG")
    mock_event_bus.publish.assert_called_once()
    event: Event = mock_event_bus.publish.call_args[0][0]
    assert event.message_type == "TradeSignalEvent"
    payload = TradeSignalEventPayload(**event.payload)
    assert payload.action == "buy"
    assert payload.price_target == 110 # Current price
    assert payload.stop_loss is not None


@pytest.mark.asyncio
async def test_analyze_no_signal(mock_event_bus, mock_market_data_service):
    agent_config = create_wa_agent_config("agent_no_sig")
    service = WilliamsAlligatorTechnicalService(agent_config, mock_event_bus, mock_market_data_service)

    # Prices pattern: lines tangled or bearish, no clear signal
    prices = [100, 101, 100, 102, 101, 100, 99, 100] * 5 # Repeat to get enough length
    klines = generate_alligator_klines(30, prices)
    klines[-1]['close'] = 100 # Current price in middle of tangle
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=klines)

    # Mock SMA values to ensure no signal condition
    service._calculate_sma = MagicMock()
    sma_val = [100.0] * 30 # All SMAs are 100, no crossover, no order
    def sma_side_effect_no_signal(data, period): return sma_val
    service._calculate_sma.side_effect = sma_side_effect_no_signal

    await service.analyze_symbol_and_generate_signal("NO/SIG")
    mock_event_bus.publish.assert_not_called()

# Need Optional from typing for helper
from typing import Optional
from datetime import datetime, timezone, timedelta # For helper
