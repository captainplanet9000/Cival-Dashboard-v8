import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

from python_ai_services.services.market_condition_classifier_service import MarketConditionClassifierService
from python_ai_services.services.market_data_service import MarketDataService
from python_ai_services.services.event_bus_service import EventBusService
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig
from python_ai_services.models.agent_models import AgentStrategyConfig # For MarketConditionClassifierParams
from python_ai_services.models.event_bus_models import Event, MarketConditionEventPayload
from datetime import datetime, timezone, timedelta

# --- Fixtures ---
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

def create_mcc_agent_config(
    agent_id: str,
    params_override: Optional[Dict[str, Any]] = None,
    use_default_mcc_params: bool = False
) -> AgentConfigOutput:
    mcc_params = None
    if not use_default_mcc_params:
        actual_params_data = {
            "adx_period": 14, "ma_short_period": 10, "ma_long_period": 50,
            "bbands_period": 20, "bbands_stddev": 2.0,
            "adx_trend_threshold": 25.0, "ma_slope_threshold": 0.001,
            "bbands_width_volatility_threshold": 0.1, "bbands_width_ranging_threshold": 0.03
        }
        if params_override:
            actual_params_data.update(params_override)
        mcc_params = AgentStrategyConfig.MarketConditionClassifierParams(**actual_params_data)

    strategy_config = AgentStrategyConfig(
        strategy_name="MarketConditionClassifier",
        parameters={},
        market_condition_classifier_params=mcc_params
    )
    return AgentConfigOutput(
        agent_id=agent_id, name=f"MCC_Agent_{agent_id}", strategy=strategy_config,
        risk_config=MagicMock(), agent_type="MarketConditionClassifierAgent"
    )

# Helper to generate klines for MCC tests
def generate_mcc_klines(count: int, base_price: float = 100.0, trend: float = 0, volatility: float = 1.0) -> List[Dict[str, Any]]:
    klines = []
    current_price = base_price
    for i in range(count):
        ts = (datetime.now(timezone.utc) - timedelta(days=count - i)).timestamp() * 1000
        current_price += trend # Apply trend

        open_px = current_price - (volatility / 2  * (0.5 + np.random.rand()/2) )
        close_px = current_price + (volatility / 2 * (0.5 + np.random.rand()/2) )
        high_px = max(open_px, close_px) + (volatility * np.random.rand())
        low_px = min(open_px, close_px) - (volatility * np.random.rand())

        klines.append({
            "timestamp": int(ts), "open": round(open_px,2), "high": round(high_px,2),
            "low": round(low_px,2), "close": round(close_px,2), "volume": 1000 + i*10
        })
    return klines

# --- Test Cases ---

@pytest.mark.asyncio
async def test_mcc_service_init_params(mock_event_bus, mock_market_data_service):
    agent_config_custom = create_mcc_agent_config("agent_custom_mcc", params_override={"adx_period": 20})
    service_custom = MarketConditionClassifierService(agent_config_custom, mock_event_bus, mock_market_data_service)
    assert service_custom.params.adx_period == 20

    agent_config_default = create_mcc_agent_config("agent_default_mcc", use_default_mcc_params=True)
    service_default = MarketConditionClassifierService(agent_config_default, mock_event_bus, mock_market_data_service)
    default_model_params = AgentStrategyConfig.MarketConditionClassifierParams()
    assert service_default.params.adx_period == default_model_params.adx_period

@pytest.mark.asyncio
async def test_mcc_insufficient_kline_data(mock_event_bus, mock_market_data_service):
    agent_config = create_mcc_agent_config("agent_mcc_insufficient")
    service = MarketConditionClassifierService(agent_config, mock_event_bus, mock_market_data_service)
    # Default longest period is ma_long_period = 50. Need 50+ for some calcs.
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=generate_mcc_klines(10, 100))

    await service.analyze_symbol_and_publish_condition("BTC/USD")
    mock_event_bus.publish.assert_not_called()

# Test _calculate_sma (already tested in Williams Alligator, but good for completeness if different)
# Test _calculate_adx_proxy - this is a very rough proxy, so test its behavior rather than accuracy
# Test _calculate_bollinger_bands

@pytest.mark.asyncio
async def test_mcc_calculates_adx_proxy(mock_event_bus, mock_market_data_service):
    agent_config = create_mcc_agent_config("agent_adx_test")
    service = MarketConditionClassifierService(agent_config, mock_event_bus, mock_market_data_service)
    klines = generate_mcc_klines(30, 100, trend=0.1, volatility=2.0) # Some data
    adx_proxy = service._calculate_adx_proxy(
        [k['high'] for k in klines], [k['low'] for k in klines], [k['close'] for k in klines],
        service.params.adx_period
    )
    assert adx_proxy is not None
    assert isinstance(adx_proxy, float)

@pytest.mark.asyncio
async def test_mcc_calculates_bollinger_bands(mock_event_bus, mock_market_data_service):
    agent_config = create_mcc_agent_config("agent_bb_test")
    service = MarketConditionClassifierService(agent_config, mock_event_bus, mock_market_data_service)
    klines = generate_mcc_klines(30, 100, trend=0, volatility=1.0)
    bbands = service._calculate_bollinger_bands(
        [k['close'] for k in klines], service.params.bbands_period, service.params.bbands_stddev
    )
    assert bbands is not None
    assert isinstance(bbands, dict)
    assert "upper" in bbands and "middle" in bbands and "lower" in bbands and "width" in bbands
    if bbands["middle"] is not None: # Check only if middle is calculable
        assert bbands["width"] >= 0


@pytest.mark.asyncio
@patch.object(MarketConditionClassifierService, '_calculate_adx_proxy', return_value=30.0) # Force ADX > threshold
@patch.object(MarketConditionClassifierService, '_calculate_bollinger_bands') # Mock BBands as not primary for this test
async def test_mcc_trending_up_signal(
    mock_bbands: MagicMock, mock_adx: MagicMock,
    mock_event_bus: MagicMock, mock_market_data_service: MagicMock
):
    agent_config = create_mcc_agent_config("agent_trend_up", params_override={"ma_slope_threshold": 0.0001})
    service = MarketConditionClassifierService(agent_config, mock_event_bus, mock_market_data_service)

    # Data: MA short slope positive, MA short > MA long
    # Short MA: 100, 101, 102 (slope > 0). Long MA: 95, 96, 97. Current MA_short > MA_long
    # Need enough data for MA_long (50) + buffer (50) = 100
    prices = [90]*60 + [95,96,97,98,99,100,101,102,103,104]*4 # Creates upward trend for MAs
    klines = generate_mcc_klines(100, price_pattern=prices)
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=klines)
    mock_bbands.return_value = {"width": 0.05} # Assume moderate BB width

    await service.analyze_symbol_and_publish_condition("TREND/UP")

    mock_event_bus.publish.assert_called_once()
    event: Event = mock_event_bus.publish.call_args[0][0]
    assert event.message_type == "MarketConditionEvent"
    payload = MarketConditionEventPayload(**event.payload)
    assert payload.symbol == "TREND/UP"
    assert payload.regime == "trending_up"
    assert payload.confidence_score == 0.7
    assert payload.supporting_data["adx_proxy"] == 30.0
    assert payload.supporting_data["ma_short_slope"] > agent_config.strategy.market_condition_classifier_params.ma_slope_threshold #type: ignore


@pytest.mark.asyncio
@patch.object(MarketConditionClassifierService, '_calculate_adx_proxy', return_value=10.0) # Force ADX < threshold
@patch.object(MarketConditionClassifierService, '_calculate_bollinger_bands')
async def test_mcc_ranging_signal_narrow_bbw(
    mock_bbands: MagicMock, mock_adx: MagicMock,
    mock_event_bus: MagicMock, mock_market_data_service: MagicMock
):
    params = {"bbands_width_ranging_threshold": 0.03}
    agent_config = create_mcc_agent_config("agent_ranging", params_override=params)
    service = MarketConditionClassifierService(agent_config, mock_event_bus, mock_market_data_service)

    klines = generate_mcc_klines(100, price_pattern=[100]*100) # Flat prices for MAs
    mock_market_data_service.get_historical_klines = AsyncMock(return_value=klines)
    mock_bbands.return_value = {"width": 0.02} # Narrow BB width < threshold (0.03)

    await service.analyze_symbol_and_publish_condition("RANGE/NARROW")

    mock_event_bus.publish.assert_called_once()
    event: Event = mock_event_bus.publish.call_args[0][0]
    payload = MarketConditionEventPayload(**event.payload)
    assert payload.regime == "ranging"
    assert payload.confidence_score == 0.7
    assert payload.supporting_data["bb_width"] == 0.02

# Need Optional from typing for helper
from typing import Optional
