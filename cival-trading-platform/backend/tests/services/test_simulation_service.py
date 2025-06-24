import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from dateutil import parser as date_parser # For parsing ISO strings in tests

from python_ai_services.services.simulation_service import SimulationService, SimulationServiceError
from python_ai_services.models.simulation_models import BacktestRequest, BacktestResult, SimulatedTrade, EquityDataPoint
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig
# Import specific strategy param models if directly accessed by tests
# from python_ai_services.models.agent_models import DarvasStrategyParams

from python_ai_services.services.market_data_service import MarketDataService
from python_ai_services.services.agent_management_service import AgentManagementService

# --- Fixtures ---

@pytest_asyncio.fixture
def mock_market_data_service():
    service = AsyncMock(spec=MarketDataService)
    service.get_historical_klines = AsyncMock()
    return service

@pytest_asyncio.fixture
def mock_agent_management_service():
    service = AsyncMock(spec=AgentManagementService)
    service.get_agent = AsyncMock()
    return service

@pytest_asyncio.fixture
def simulation_service(mock_market_data_service, mock_agent_management_service):
    return SimulationService(
        market_data_service=mock_market_data_service,
        agent_management_service=mock_agent_management_service
    )

# Helper to create a basic AgentConfigOutput for testing
def create_test_agent_config(
    agent_id: str = "sim_agent_1",
    agent_type: str = "DarvasBoxTechnicalAgent", # Default to a known simulatable type
    darvas_lookback: int = 20, # Example param
    # Add other strategy params as needed for tests
) -> AgentConfigOutput:

    darvas_params_config = None
    if agent_type == "DarvasBoxTechnicalAgent":
        darvas_params_config = AgentStrategyConfig.DarvasStrategyParams(lookback_period=darvas_lookback)

    return AgentConfigOutput(
        agent_id=agent_id,
        name=f"SimAgent {agent_id}",
        agent_type=agent_type,
        strategy=AgentStrategyConfig(
            strategy_name="sim_strat",
            parameters={}, # General params
            darvas_params=darvas_params_config,
            # williams_alligator_params=... if testing Alligator
        ),
        risk_config=AgentRiskConfig(max_capital_allocation_usd=10000, risk_per_trade_percentage=0.01),
        is_active=True,
        # execution_provider, hyperliquid_config, dex_config not directly used by SimulationService logic
    )

# Helper to create sample kline data
def create_sample_klines(
    start_dt: datetime,
    num_candles: int,
    price_increment: float = 1.0,
    start_price: float = 100.0
) -> List[Dict[str, Any]]:
    klines = []
    current_price = start_price
    current_dt = start_dt
    for i in range(num_candles):
        klines.append({
            "timestamp": int(current_dt.timestamp() * 1000),
            "open": current_price,
            "high": current_price + price_increment / 2,
            "low": current_price - price_increment / 2,
            "close": current_price + price_increment if i % 2 == 0 else current_price - price_increment / 2, # Zigzag
            "volume": 1000 + i * 10
        })
        current_price += price_increment
        current_dt += timedelta(days=1)
    return klines

# --- Test Cases for run_backtest ---

@pytest.mark.asyncio
async def test_run_backtest_validation_no_agent_info(simulation_service: SimulationService):
    request = BacktestRequest(
        symbol="BTC/USD", start_date_iso="2023-01-01T00:00:00Z", end_date_iso="2023-01-10T00:00:00Z",
        initial_capital=10000
        # Missing agent_config_snapshot and agent_id_to_simulate
    )
    with pytest.raises(ValueError, match="Either agent_config_snapshot or agent_id_to_simulate must be provided"):
        await simulation_service.run_backtest(request)

@pytest.mark.asyncio
async def test_run_backtest_validation_both_agent_info(simulation_service: SimulationService):
    test_config = create_test_agent_config()
    request = BacktestRequest(
        agent_config_snapshot=test_config,
        agent_id_to_simulate="some_id", # Providing both
        symbol="BTC/USD", start_date_iso="2023-01-01T00:00:00Z", end_date_iso="2023-01-10T00:00:00Z",
        initial_capital=10000
    )
    with pytest.raises(ValueError, match="Provide either agent_config_snapshot or agent_id_to_simulate, not both"):
        await simulation_service.run_backtest(request)

@pytest.mark.asyncio
async def test_run_backtest_agent_id_ams_not_configured(simulation_service: SimulationService):
    simulation_service.agent_management_service = None # Ensure AMS is None
    request = BacktestRequest(
        agent_id_to_simulate="agent1",
        symbol="BTC/USD", start_date_iso="2023-01-01T00:00:00Z", end_date_iso="2023-01-10T00:00:00Z",
        initial_capital=10000
    )
    with pytest.raises(SimulationServiceError, match="AgentManagementService is required to fetch agent by ID"):
        await simulation_service.run_backtest(request)

@pytest.mark.asyncio
async def test_run_backtest_agent_id_not_found(simulation_service: SimulationService, mock_agent_management_service: MagicMock):
    mock_agent_management_service.get_agent.return_value = None
    request = BacktestRequest(
        agent_id_to_simulate="unknown_agent",
        symbol="BTC/USD", start_date_iso="2023-01-01T00:00:00Z", end_date_iso="2023-01-10T00:00:00Z",
        initial_capital=10000
    )
    with pytest.raises(SimulationServiceError, match="Agent configuration could not be determined"):
        await simulation_service.run_backtest(request)
    mock_agent_management_service.get_agent.assert_called_once_with("unknown_agent")


@pytest.mark.asyncio
async def test_run_backtest_no_kline_data_in_range(simulation_service: SimulationService, mock_market_data_service: MagicMock):
    agent_config = create_test_agent_config()
    start_iso = "2023-01-01T00:00:00Z"
    end_iso = "2023-01-05T00:00:00Z"

    # MarketDataService returns klines outside the requested range
    outside_range_dt = date_parser.isoparse(start_iso) - timedelta(days=10)
    mock_klines = create_sample_klines(outside_range_dt, 5) # 5 candles before start_date
    mock_market_data_service.get_historical_klines.return_value = mock_klines

    request = BacktestRequest(
        agent_config_snapshot=agent_config, symbol="TEST/USD",
        start_date_iso=start_iso, end_date_iso=end_iso, initial_capital=1000
    )

    result = await simulation_service.run_backtest(request)

    # Expecting an empty result set as per current SimulationService logic
    assert result.total_trades == 0
    assert result.final_capital == request.initial_capital
    assert len(result.equity_curve) == 1
    assert result.equity_curve[0].equity == request.initial_capital
    mock_market_data_service.get_historical_klines.assert_called_once()


@pytest.mark.asyncio
async def test_run_backtest_darvas_buy_and_hold_profitable(simulation_service: SimulationService, mock_market_data_service: MagicMock):
    agent_config = create_test_agent_config(agent_type="DarvasBoxTechnicalAgent", darvas_lookback=5)
    start_dt = date_parser.isoparse("2023-01-01T00:00:00Z")

    # Create klines: initial flat, then a breakout, then price continues to rise
    klines = []
    # Initial period (lookback_period for Darvas = 5)
    for i in range(5):
        klines.append({"timestamp": int((start_dt + timedelta(days=i)).timestamp()*1000), "open": 100, "high": 102, "low": 98, "close": 100, "volume": 100})
    # Breakout candle (day 6, index 5)
    klines.append({"timestamp": int((start_dt + timedelta(days=5)).timestamp()*1000), "open": 100, "high": 105, "low": 99, "close": 104, "volume": 150}) # Breakout, Darvas buys at 104
    # Price rises further (days 7-10)
    for i in range(6, 10):
         klines.append({"timestamp": int((start_dt + timedelta(days=i)).timestamp()*1000), "open": 104+i-5, "high": 106+i-5, "low": 102+i-5, "close": 105+i-5, "volume": 120})

    mock_market_data_service.get_historical_klines.return_value = klines

    request = BacktestRequest(
        agent_config_snapshot=agent_config, symbol="BTC/USD",
        start_date_iso=(start_dt).isoformat().replace("+00:00", "Z"),
        end_date_iso=(start_dt + timedelta(days=9)).isoformat().replace("+00:00", "Z"), # End of data
        initial_capital=10000,
        simulated_fees_percentage=0.001, # 0.1%
        simulated_slippage_percentage=0.0005 # 0.05%
    )

    result = await simulation_service.run_backtest(request)

    assert len(result.list_of_simulated_trades) == 1 # Only one buy, no sell signal in simplified Darvas
    buy_trade = result.list_of_simulated_trades[0]
    assert buy_trade.side == "buy"

    # Expected buy price: 104 (close of breakout) * (1 + slippage)
    expected_buy_price = 104 * (1 + request.simulated_slippage_percentage)
    assert buy_trade.price == pytest.approx(expected_buy_price)
    assert buy_trade.quantity == 1.0 # Default qty

    expected_fee = expected_buy_price * 1.0 * request.simulated_fees_percentage
    assert buy_trade.fee_paid == pytest.approx(expected_fee)

    # Capital after buy: initial_capital - (exec_price * qty) - fee
    capital_after_buy = request.initial_capital - (expected_buy_price * 1.0) - expected_fee

    # Final equity: capital_after_buy + (position_qty * last_close_price)
    last_close_price = klines[-1]['close']
    expected_final_equity = capital_after_buy + (1.0 * last_close_price)

    assert result.final_capital == pytest.approx(expected_final_equity)
    assert result.total_pnl == pytest.approx(expected_final_equity - request.initial_capital)
    assert result.total_trades == 0 # No sell trades, so 0 round trips
    assert result.winning_trades == 0
    assert result.losing_trades == 0
    assert len(result.equity_curve) == 10 # 10 days of data
    assert result.equity_curve[0].equity == request.initial_capital
    # Equity at breakout candle (after buy)
    # current_dt for breakout candle: start_dt + timedelta(days=5)
    # equity_curve index 5 should reflect capital after buy + MTM of position with close of that day
    # MTM for that day: capital_after_buy + (1.0 * 104)
    assert result.equity_curve[5].equity == pytest.approx(capital_after_buy + (1.0 * 104))
    assert result.equity_curve[-1].equity == pytest.approx(expected_final_equity)

@pytest.mark.asyncio
async def test_run_backtest_insufficient_capital_for_buy(simulation_service: SimulationService, mock_market_data_service: MagicMock):
    agent_config = create_test_agent_config(agent_type="DarvasBoxTechnicalAgent", darvas_lookback=2)
    start_dt = date_parser.isoparse("2023-01-01T00:00:00Z")

    klines = [ # Breakout on 3rd candle
        {"timestamp": int((start_dt + timedelta(days=0)).timestamp()*1000), "open": 10, "high": 12, "low": 8, "close": 10, "volume": 100},
        {"timestamp": int((start_dt + timedelta(days=1)).timestamp()*1000), "open": 10, "high": 12, "low": 8, "close": 10, "volume": 100},
        {"timestamp": int((start_dt + timedelta(days=2)).timestamp()*1000), "open": 10, "high": 15, "low": 9, "close": 14, "volume": 150}, # Buy signal
    ]
    mock_market_data_service.get_historical_klines.return_value = klines

    request = BacktestRequest(
        agent_config_snapshot=agent_config, symbol="TINY/USD",
        start_date_iso=(start_dt).isoformat().replace("+00:00", "Z"),
        end_date_iso=(start_dt + timedelta(days=2)).isoformat().replace("+00:00", "Z"),
        initial_capital=10, # Very low capital, less than price of 1 unit (14) + fees
        simulated_fees_percentage=0.01, simulated_slippage_percentage=0.00
    )

    result = await simulation_service.run_backtest(request)
    assert len(result.list_of_simulated_trades) == 0 # Buy should be skipped
    assert result.final_capital == request.initial_capital
    assert result.total_pnl == 0

# TODO: Add tests for WilliamsAlligator logic if it becomes more complex
# TODO: Add tests for sell logic and round trip P&L calculation when implemented more fully
# TODO: Test for date parsing errors in request
# TODO: Test for empty klines from market_data_service (should raise error or return empty result)
