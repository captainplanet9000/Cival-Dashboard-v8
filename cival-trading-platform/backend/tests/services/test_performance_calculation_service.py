import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
import math

from python_ai_services.services.performance_calculation_service import PerformanceCalculationService
from python_ai_services.services.trading_data_service import TradingDataService
from python_ai_services.models.dashboard_models import TradeLogItem
from python_ai_services.models.performance_models import PerformanceMetrics

@pytest_asyncio.fixture
def mock_trading_data_service() -> TradingDataService:
    return MagicMock(spec=TradingDataService)

@pytest_asyncio.fixture
def performance_service(mock_trading_data_service: TradingDataService) -> PerformanceCalculationService:
    return PerformanceCalculationService(trading_data_service=mock_trading_data_service)

def create_mock_trade(pnl: Optional[float], timestamp_offset_days: int, asset: str = "TEST_ASSET") -> TradeLogItem:
    return TradeLogItem(
        trade_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc) - timedelta(days=timestamp_offset_days),
        agent_id="test_agent",
        asset=asset,
        side="buy",
        order_type="market",
        quantity=1.0,
        price=100.0,
        total_value=100.0,
        realized_pnl=pnl
    )

@pytest.mark.asyncio
async def test_calculate_performance_no_trades(
    performance_service: PerformanceCalculationService,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_no_trades"
    mock_trading_data_service.get_trade_history = AsyncMock(return_value=[])

    metrics = await performance_service.calculate_performance_metrics(agent_id)

    assert isinstance(metrics, PerformanceMetrics)
    assert metrics.agent_id == agent_id
    assert metrics.total_trades == 0
    assert metrics.total_net_pnl == 0.0
    assert "No trade history available" in metrics.notes
    mock_trading_data_service.get_trade_history.assert_called_once_with(agent_id, limit=10000)

@pytest.mark.asyncio
async def test_calculate_performance_failed_to_fetch_trades(
    performance_service: PerformanceCalculationService,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_fetch_fail"
    mock_trading_data_service.get_trade_history = AsyncMock(side_effect=Exception("DB Error"))

    metrics = await performance_service.calculate_performance_metrics(agent_id)
    assert metrics.agent_id == agent_id
    assert "Failed to fetch trade history: DB Error" in metrics.notes
    assert metrics.total_trades == 0

@pytest.mark.asyncio
async def test_calculate_performance_with_pnl_data(
    performance_service: PerformanceCalculationService,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_with_pnl"
    trades = [
        create_mock_trade(pnl=10.0, timestamp_offset_days=3), # Win
        create_mock_trade(pnl=-5.0, timestamp_offset_days=2), # Loss
        create_mock_trade(pnl=15.0, timestamp_offset_days=1), # Win
        create_mock_trade(pnl=0.0, timestamp_offset_days=1),  # Neutral
        create_mock_trade(pnl=None, timestamp_offset_days=0, asset="MOCK_COIN") # PnL missing
    ]
    mock_trading_data_service.get_trade_history = AsyncMock(return_value=trades)

    metrics = await performance_service.calculate_performance_metrics(agent_id)

    assert metrics.total_trades == 5
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 1
    assert metrics.neutral_trades == 2 # 0.0 PnL and None PnL
    assert math.isclose(metrics.total_net_pnl, 20.0)
    assert math.isclose(metrics.gross_profit, 25.0)  # 10 + 15
    assert math.isclose(metrics.gross_loss, 5.0)    # abs(-5)

    assert metrics.data_start_time == trades[0].timestamp
    assert metrics.data_end_time == trades[-1].timestamp # latest trade

    # Win rate = winning / (winning + losing)
    assert math.isclose(metrics.win_rate, 2 / 3)
    assert math.isclose(metrics.loss_rate, 1 / 3)

    assert math.isclose(metrics.average_win_amount, 25.0 / 2)
    assert math.isclose(metrics.average_loss_amount, 5.0 / 1)

    # Profit factor = gross_profit / gross_loss
    assert math.isclose(metrics.profit_factor, 25.0 / 5.0)

    assert "Some trades were missing realized PnL" in metrics.notes
    assert "mocked trade history data" in metrics.notes # Due to MOCK_COIN

@pytest.mark.asyncio
async def test_calculate_performance_all_wins(
    performance_service: PerformanceCalculationService,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_all_wins"
    trades = [
        create_mock_trade(pnl=10.0, timestamp_offset_days=1),
        create_mock_trade(pnl=20.0, timestamp_offset_days=0)
    ]
    mock_trading_data_service.get_trade_history = AsyncMock(return_value=trades)
    metrics = await performance_service.calculate_performance_metrics(agent_id)

    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 0
    assert metrics.win_rate == 1.0
    assert metrics.loss_rate == 0.0
    assert metrics.average_loss_amount is None
    assert metrics.profit_factor == float('inf') # Or some representation of infinite/undefined

@pytest.mark.asyncio
async def test_calculate_performance_all_losses(
    performance_service: PerformanceCalculationService,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_all_losses"
    trades = [
        create_mock_trade(pnl=-10.0, timestamp_offset_days=1),
        create_mock_trade(pnl=-20.0, timestamp_offset_days=0)
    ]
    mock_trading_data_service.get_trade_history = AsyncMock(return_value=trades)
    metrics = await performance_service.calculate_performance_metrics(agent_id)

    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 2
    assert metrics.win_rate == 0.0
    assert metrics.loss_rate == 1.0
    assert metrics.average_win_amount is None
    assert metrics.profit_factor == 0.0

@pytest.mark.asyncio
async def test_calculate_performance_no_pnl_data(
    performance_service: PerformanceCalculationService,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_no_pnl"
    trades = [
        create_mock_trade(pnl=None, timestamp_offset_days=1),
        create_mock_trade(pnl=None, timestamp_offset_days=0)
    ]
    mock_trading_data_service.get_trade_history = AsyncMock(return_value=trades)
    metrics = await performance_service.calculate_performance_metrics(agent_id)

    assert metrics.total_trades == 2
    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 0
    assert metrics.neutral_trades == 2
    assert metrics.total_net_pnl == 0.0
    assert metrics.gross_profit is None # Because pnl_data_available will be False
    assert metrics.gross_loss is None   # Same
    assert metrics.win_rate == 0.0 # Based on determined_trades being 0
    assert metrics.loss_rate == 0.0
    assert "Realized PnL data was missing for all trades" in metrics.notes

@pytest.mark.asyncio
async def test_calculate_performance_invalid_pnl_values(
    performance_service: PerformanceCalculationService,
    mock_trading_data_service: MagicMock
):
    agent_id = "agent_invalid_pnl"
    trades = [
        create_mock_trade(pnl=float('nan'), timestamp_offset_days=1),
        create_mock_trade(pnl=float('inf'), timestamp_offset_days=0),
        create_mock_trade(pnl=10.0, timestamp_offset_days=2) # One valid trade
    ]
    mock_trading_data_service.get_trade_history = AsyncMock(return_value=trades)
    metrics = await performance_service.calculate_performance_metrics(agent_id)

    assert metrics.total_trades == 3
    assert metrics.winning_trades == 1 # Only the valid trade
    assert metrics.losing_trades == 0
    assert metrics.neutral_trades == 2 # NaN and Inf PnLs are counted as neutral
    assert math.isclose(metrics.total_net_pnl, 10.0)


# Need uuid for helper
import uuid
