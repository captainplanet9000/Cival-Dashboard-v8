import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone
import uuid

from python_ai_services.services.trading_data_service import TradingDataService, HyperliquidServiceFactory
from python_ai_services.services.agent_management_service import AgentManagementService
from python_ai_services.services.hyperliquid_execution_service import HyperliquidExecutionService, HyperliquidExecutionServiceError
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig
from python_ai_services.models.dashboard_models import PortfolioSummary, AssetPositionSummary, TradeLogItem, OrderLogItem
from python_ai_services.models.hyperliquid_models import (
    HyperliquidAccountSnapshot,
    HyperliquidAssetPosition,
    HyperliquidOpenOrderItem,
    HyperliquidMarginSummary
)

# --- Fixtures ---

    return MagicMock(spec=AgentManagementService)

# mock_hles_factory and mock_hles_instance are removed
# We will patch 'get_hyperliquid_execution_service_instance' directly in tests needing it.

from python_ai_services.services.trade_history_service import TradeHistoryService # Added import

@pytest_asyncio.fixture
def mock_trade_history_service() -> TradeHistoryService: # New fixture
    return AsyncMock(spec=TradeHistoryService)

@pytest_asyncio.fixture
def trading_data_service(
    mock_agent_service: AgentManagementService,
    # mock_hles_factory removed
    mock_trade_history_service: TradeHistoryService
) -> TradingDataService:
    # hyperliquid_service_factory is no longer passed to TradingDataService constructor
    return TradingDataService(
        agent_service=mock_agent_service,
        trade_history_service=mock_trade_history_service
    )

# --- Helper Functions ---
def create_mock_agent_config(
    agent_id: str,
    provider: str = "paper",
    # cred_id is no longer used by this helper directly,
    # hyperliquid_config should be set if testing HL provider
    hyperliquid_config: Optional[Dict[str, str]] = None
) -> AgentConfigOutput:
    if provider == "hyperliquid" and hyperliquid_config is None:
        # Provide a default hyperliquid_config if none is given for a hyperliquid agent
        hyperliquid_config = {
            "wallet_address": "0xTestWallet",
            "private_key_env_var_name": "TEST_HL_PRIVKEY_VAR",
            "network_mode": "testnet"
        }

    return AgentConfigOutput(
        agent_id=agent_id,
        name=f"Agent {agent_id}",
        strategy=AgentStrategyConfig(strategy_name="test", parameters={}),
        risk_config=AgentRiskConfig(max_capital_allocation_usd=1000, risk_per_trade_percentage=0.01),
        execution_provider=provider, # type: ignore
        hyperliquid_config=hyperliquid_config, # Use the new field
      # hyperliquid_credentials_id=cred_id, # This field is deprecated
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

# --- Tests for get_portfolio_summary ---

@pytest.mark.asyncio
async def test_get_portfolio_summary_paper_agent(trading_data_service: TradingDataService, mock_agent_service: MagicMock):
    agent_id = "paper_agent_1"
    mock_agent_service.get_agent = AsyncMock(return_value=create_mock_agent_config(agent_id, provider="paper"))

    summary = await trading_data_service.get_portfolio_summary(agent_id)

    assert isinstance(summary, PortfolioSummary)
    assert summary.agent_id == agent_id
    assert summary.account_value_usd == 10000.0 # Mocked data
    assert len(summary.open_positions) > 0
    mock_agent_service.get_agent.assert_called_once_with(agent_id)


@patch('python_ai_services.services.trading_data_service.get_hyperliquid_execution_service_instance')
async def test_get_portfolio_summary_hyperliquid_agent_success(
    mock_get_hles_instance_factory: MagicMock, # Patched factory function
    trading_data_service: TradingDataService,
    mock_agent_service: MagicMock
):
    agent_id = "hl_agent_1"
    # Ensure hyperliquid_config is properly set for the factory to use
    agent_config = create_mock_agent_config(
        agent_id,
        provider="hyperliquid",
        hyperliquid_config={
            "wallet_address": "0xTestWallet",
            "private_key_env_var_name": "TEST_HL_PRIVKEY_VAR",
            "network_mode": "testnet"
        }
    )
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    # Mock HLES instance that the factory will return
    mock_hles_inst = MagicMock(spec=HyperliquidExecutionService)
    mock_hles_inst.wallet_address = "0xTestWallet" # Should match what HLES would have
    mock_get_hles_instance_factory.return_value = mock_hles_inst


    # Mock HLES method responses
    mock_hl_margin_summary = HyperliquidMarginSummary(
        accountValue="12000.50", totalRawUsd="12000.50", totalNtlPos="250.75",
        totalMarginUsed="1500.20", withdrawable="10500.30"
    )
    mock_hl_account_snapshot = HyperliquidAccountSnapshot(
        time=int(datetime.now(timezone.utc).timestamp() * 1000),
        totalRawUsd="12000.50",
        parsed_positions=[
            HyperliquidAssetPosition(asset="ETH", szi="2.0", entry_px="3000.00", unrealized_pnl="200.00", margin_used="600.00"),
            HyperliquidAssetPosition(asset="BTC", szi="0.05", entry_px="60000.00", unrealized_pnl="50.75", margin_used="900.20")
        ]
    )
    mock_hles_inst.get_account_margin_summary = AsyncMock(return_value=mock_hl_margin_summary)
    mock_hles_inst.get_detailed_account_summary = AsyncMock(return_value=mock_hl_account_snapshot)

    summary = await trading_data_service.get_portfolio_summary(agent_id)

    assert isinstance(summary, PortfolioSummary)
    assert summary.agent_id == agent_id
    assert summary.account_value_usd == 12000.50
    assert len(summary.open_positions) == 2

    mock_agent_service.get_agent.assert_called_once_with(agent_id)
    mock_get_hles_instance_factory.assert_called_once_with(agent_config)
    mock_hles_inst.get_account_margin_summary.assert_called_once()
    mock_hles_inst.get_detailed_account_summary.assert_called_once_with(mock_hles_inst.wallet_address)


@patch('python_ai_services.services.trading_data_service.get_hyperliquid_execution_service_instance')
async def test_get_portfolio_summary_hyperliquid_no_hles_instance(
    mock_get_hles_instance_factory: MagicMock,
    trading_data_service: TradingDataService,
    mock_agent_service: MagicMock
):
    agent_id = "hl_agent_no_hles"
    agent_config = create_mock_agent_config(agent_id, provider="hyperliquid") # Default HL config from helper
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    mock_get_hles_instance_factory.return_value = None # Simulate factory failing to create/return HLES

    summary = await trading_data_service.get_portfolio_summary(agent_id)
    assert summary is None
    mock_get_hles_instance_factory.assert_called_once_with(agent_config)


@pytest.mark.asyncio
async def test_get_portfolio_summary_agent_not_found(trading_data_service: TradingDataService, mock_agent_service: MagicMock):
    agent_id = "unknown_agent"
    mock_agent_service.get_agent = AsyncMock(return_value=None)
    summary = await trading_data_service.get_portfolio_summary(agent_id)
    assert summary is None

# --- Tests for get_trade_history (now uses TradeHistoryService) ---

@pytest.mark.asyncio
async def test_get_trade_history_uses_trade_history_service(
    trading_data_service: TradingDataService,
    mock_trade_history_service: MagicMock # Use the new mock fixture
):
    agent_id = "agent_real_trades"
    limit_val = 50
    offset_val = 10

    # Setup mock response from TradeHistoryService
    mock_processed_trades = [
        TradeLogItem(
            agent_id=agent_id, trade_id=str(uuid.uuid4()), timestamp=datetime.now(timezone.utc),
            asset="BTC/USD", side="buy", order_type="market", quantity=1, price=50000, total_value=50000, realized_pnl=100
        )
    ]
    mock_trade_history_service.get_processed_trades = AsyncMock(return_value=mock_processed_trades)

    history = await trading_data_service.get_trade_history(agent_id, limit=limit_val, offset=offset_val)

    assert history == mock_processed_trades
    mock_trade_history_service.get_processed_trades.assert_called_once_with(
        agent_id=agent_id, limit=limit_val, offset=offset_val
    )

@pytest.mark.asyncio
async def test_get_trade_history_service_error_returns_empty(
    trading_data_service: TradingDataService,
    mock_trade_history_service: MagicMock
):
    agent_id = "agent_th_error"
    mock_trade_history_service.get_processed_trades = AsyncMock(side_effect=Exception("Failed to process trades"))

    history = await trading_data_service.get_trade_history(agent_id)
    assert history == [] # Should return empty list on error

# --- Tests for get_open_orders ---

@pytest.mark.asyncio
async def test_get_open_orders_paper_agent(trading_data_service: TradingDataService, mock_agent_service: MagicMock):
    agent_id = "paper_open_orders"
    mock_agent_service.get_agent = AsyncMock(return_value=create_mock_agent_config(agent_id, provider="paper"))

    orders = await trading_data_service.get_open_orders(agent_id)
    assert len(orders) > 0 # Mocked data for paper
    for order in orders:
        assert isinstance(order, OrderLogItem)
        assert order.agent_id == agent_id

@patch('python_ai_services.services.trading_data_service.get_hyperliquid_execution_service_instance')
async def test_get_open_orders_hyperliquid_agent_success(
    mock_get_hles_instance_factory: MagicMock,
    trading_data_service: TradingDataService,
    mock_agent_service: MagicMock
):
    agent_id = "hl_open_orders"
    agent_config = create_mock_agent_config(agent_id, provider="hyperliquid")
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    mock_hles_inst = MagicMock(spec=HyperliquidExecutionService)
    mock_hles_inst.wallet_address = "mock_wallet_for_open_orders_test"
    mock_get_hles_instance_factory.return_value = mock_hles_inst


    mock_hl_orders = [
        HyperliquidOpenOrderItem(oid=123, asset="ETH", side="b", limit_px="2900.0", sz="0.5", timestamp=int(datetime.now(timezone.utc).timestamp()*1000), raw_order_data={}),
        HyperliquidOpenOrderItem(oid=456, asset="BTC", side="s", limit_px="61000.0", sz="0.01", timestamp=int(datetime.now(timezone.utc).timestamp()*1000), raw_order_data={})
    ]
    mock_hles_inst.get_all_open_orders = AsyncMock(return_value=mock_hl_orders)

    open_orders = await trading_data_service.get_open_orders(agent_id)

    assert len(open_orders) == 2
    assert open_orders[0].order_id == "123"
    mock_get_hles_instance_factory.assert_called_once_with(agent_config)
    mock_hles_inst.get_all_open_orders.assert_called_once_with(mock_hles_inst.wallet_address)

@patch('python_ai_services.services.trading_data_service.get_hyperliquid_execution_service_instance')
async def test_get_open_orders_hyperliquid_hles_error(
    mock_get_hles_instance_factory: MagicMock,
    trading_data_service: TradingDataService,
    mock_agent_service: MagicMock
):
    agent_id = "hl_oo_error"
    agent_config = create_mock_agent_config(agent_id, provider="hyperliquid")
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    mock_hles_inst = MagicMock(spec=HyperliquidExecutionService)
    mock_get_hles_instance_factory.return_value = mock_hles_inst
    mock_hles_inst.get_all_open_orders = AsyncMock(side_effect=HyperliquidExecutionServiceError("SDK Down"))

    open_orders = await trading_data_service.get_open_orders(agent_id)
    assert len(open_orders) == 0 # Should return empty list on error

# --- Tests for get_order_history (mocked data) ---

@pytest.mark.asyncio
async def test_get_order_history_mocked(trading_data_service: TradingDataService, mock_agent_service: MagicMock):
    agent_id = "agent_mock_order_hist"
    mock_agent_service.get_agent = AsyncMock(return_value=create_mock_agent_config(agent_id))

    history = await trading_data_service.get_order_history(agent_id, limit=2)
    assert len(history) == 2 # Mock service creates 4, limit applies
    for item in history:
        assert isinstance(item, OrderLogItem)
        assert item.agent_id == agent_id

