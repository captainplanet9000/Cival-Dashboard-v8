import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from python_ai_services.services.risk_manager_service import RiskManagerService
from python_ai_services.services.agent_management_service import AgentManagementService
from python_ai_services.models.agent_models import AgentConfigOutput, AgentRiskConfig, AgentStrategyConfig
from python_ai_services.models.event_bus_models import TradeSignalEventPayload, RiskAssessmentResponseData

from python_ai_services.services.trading_data_service import TradingDataService # Added
from python_ai_services.models.dashboard_models import PortfolioSummary, AssetPositionSummary # Added

@pytest_asyncio.fixture
def mock_agent_service() -> AgentManagementService:
    return AsyncMock(spec=AgentManagementService)

@pytest_asyncio.fixture
def mock_trading_data_service() -> TradingDataService: # Added
    service = AsyncMock(spec=TradingDataService)
    service.get_portfolio_summary = AsyncMock()
    return service

@pytest_asyncio.fixture
def risk_service(
    mock_agent_service: AgentManagementService,
    mock_trading_data_service: TradingDataService # Added
) -> RiskManagerService:
    return RiskManagerService(
        agent_service=mock_agent_service,
        trading_data_service=mock_trading_data_service # Pass it
    )

# Helper to create AgentConfigOutput for tests
def create_test_agent_config_for_risk( # Updated to include new risk params
    agent_id: str,
    max_capital_allocation: float = 10000.0, # For max trade value check
    risk_per_trade_percentage_balance: Optional[float] = None,
    max_concurrent_trades: Optional[int] = None,
    max_asset_exposure_usd: Optional[float] = None,
    allowed_symbols_list: Optional[list[str]] = None,
    other_op_params: Optional[dict] = None
) -> AgentConfigOutput:
    op_params = {}
    if allowed_symbols_list:
        op_params["allowed_symbols"] = allowed_symbols_list
    if other_op_params:
        op_params.update(other_op_params)

    return AgentConfigOutput(
        agent_id=agent_id,
        name=f"RiskTestAgent {agent_id}",
        strategy=AgentStrategyConfig(strategy_name="test_strat", parameters={}),
        risk_config=AgentRiskConfig( # Updated to include new fields
            max_capital_allocation_usd=max_capital_allocation,
            risk_per_trade_percentage=0.01, # Base overall risk, not used by new checks directly
            max_loss_per_trade_percentage_balance=risk_per_trade_percentage_balance,
            max_concurrent_open_trades=max_concurrent_trades,
            max_exposure_per_asset_usd=max_asset_exposure_usd
        ),
        operational_parameters=op_params,
        # Default other fields for AgentConfigOutput
        agent_type="GenericAgent",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

# Helper to create TradeSignalEventPayload
def create_test_trade_signal(
    symbol: str, action: str = "buy", quantity: float = 1.0, price: float = 100.0,
    stop_loss: Optional[float] = None, strategy: str = "test_strat"
) -> TradeSignalEventPayload:
    return TradeSignalEventPayload(
        symbol=symbol,
        action=action, #type: ignore
        quantity=quantity,
        price_target=price,
        stop_loss=stop_loss,
        strategy_name=strategy
    )

# Helper to create PortfolioSummary
def create_test_portfolio_summary(
    account_value: float = 10000.0,
    open_positions: Optional[List[AssetPositionSummary]] = None
) -> PortfolioSummary:
    if open_positions is None:
        open_positions = []
    return PortfolioSummary(
        agent_id="test_agent_portfolio", # This agent_id is for the portfolio itself
        timestamp=datetime.now(timezone.utc),
        account_value_usd=account_value,
        total_pnl_usd=100.0, # Example
        open_positions=open_positions
    )


@pytest.mark.asyncio
async def test_assess_trade_risk_agent_not_found(risk_service: RiskManagerService, mock_agent_service: MagicMock):
    mock_agent_service.get_agent = AsyncMock(return_value=None)
    trade_signal = create_test_trade_signal("BTC/USD")

    assessment = await risk_service.assess_trade_risk("unknown_agent", trade_signal)

    assert assessment.signal_approved is False
    assert "Agent config for unknown_agent not found" in assessment.rejection_reason #type: ignore
    mock_agent_service.get_agent.assert_called_once_with("unknown_agent")

@pytest.mark.asyncio
async def test_assess_trade_risk_signal_missing_data(risk_service: RiskManagerService, mock_agent_service: MagicMock):
    agent_id = "agent_signal_missing_data"
    agent_config = create_test_agent_config_for_risk(agent_id)
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    # Signal missing quantity
    trade_signal_no_qty = TradeSignalEventPayload(symbol="ETH/USD", action="buy", price_target=3000.0, strategy_name="s1") # type: ignore
    assessment_no_qty = await risk_service.assess_trade_risk(agent_id, trade_signal_no_qty)
    assert assessment_no_qty.signal_approved is False
    assert "missing quantity or price_target" in assessment_no_qty.rejection_reason # type: ignore

    # Signal missing price_target
    trade_signal_no_price = TradeSignalEventPayload(symbol="ETH/USD", action="buy", quantity=1.0, strategy_name="s1") # type: ignore
    assessment_no_price = await risk_service.assess_trade_risk(agent_id, trade_signal_no_price)
    assert assessment_no_price.signal_approved is False
    assert "missing quantity or price_target" in assessment_no_price.rejection_reason # type: ignore


@pytest.mark.asyncio
async def test_assess_trade_risk_exceeds_max_capital(risk_service: RiskManagerService, mock_agent_service: MagicMock):
    agent_id = "agent_exceeds_cap"
    # max_capital_allocation_usd is interpreted as max trade value by current RiskManagerService logic
    agent_config = create_test_agent_config_for_risk(agent_id, max_capital_allocation=500.0)
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    # Trade value = 10 * 60 = 600 USD, which is > 500 USD
    trade_signal = create_test_trade_signal("BTC/USD", quantity=10.0, price=60.0)

    assessment = await risk_service.assess_trade_risk(agent_id, trade_signal)

    assert assessment.signal_approved is False
    assert "exceeds agent's max capital allocation per trade" in assessment.rejection_reason # type: ignore

@pytest.mark.asyncio
async def test_assess_trade_risk_symbol_not_in_whitelist(risk_service: RiskManagerService, mock_agent_service: MagicMock):
    agent_id = "agent_symbol_not_allowed"
    allowed = ["BTC/USD", "ETH/USD"]
    agent_config = create_test_agent_config_for_risk(agent_id, allowed_symbols_list=allowed)
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    trade_signal = create_test_trade_signal("ADA/USD") # ADA/USD is not in whitelist
    assessment = await risk_service.assess_trade_risk(agent_id, trade_signal)

    assert assessment.signal_approved is False
    assert "not in allowed list" in assessment.rejection_reason # type: ignore

    # Test with hyphenated symbol in whitelist
    trade_signal_hyphen = create_test_trade_signal("SOL-USD") # Normalization should handle this
    agent_config_hyphen_whitelist = create_test_agent_config_for_risk(agent_id, allowed_symbols_list=["SOL/USD"])
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config_hyphen_whitelist)
    assessment_hyphen = await risk_service.assess_trade_risk(agent_id, trade_signal_hyphen)
    assert assessment_hyphen.signal_approved is True


@pytest.mark.asyncio
async def test_assess_trade_risk_approved_no_specific_limits_hit(risk_service: RiskManagerService, mock_agent_service: MagicMock):
    agent_id = "agent_approved_trade"
    # Config with high capital limit and no symbol whitelist (or symbol is in it)
    agent_config = create_test_agent_config_for_risk(
        agent_id,
        max_capital_allocation=20000.0,
        allowed_symbols_list=["XRP/USD"]
    )
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    # Trade value = 2 * 0.5 = 1.0 USD, well within 20000
    # Symbol XRP/USD is in whitelist
    trade_signal = create_test_trade_signal("XRP/USD", quantity=2.0, price=0.50)

    assessment = await risk_service.assess_trade_risk(agent_id, trade_signal)

    assert assessment.signal_approved is True
    assert assessment.rejection_reason is None

@pytest.mark.asyncio
async def test_assess_trade_risk_zero_max_capital_allocation_skips_check(risk_service: RiskManagerService, mock_agent_service: MagicMock):
    agent_id = "agent_zero_max_cap"
    # If max_capital_allocation_usd is 0 or not positive, this check should be skipped
    agent_config = create_test_agent_config_for_risk(agent_id, max_capital_allocation=0)
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    trade_signal = create_test_trade_signal("ANY/USD", quantity=1000.0, price=100.0) # Very large trade
    assessment = await risk_service.assess_trade_risk(agent_id, trade_signal)

    assert assessment.signal_approved is True # Approved because the max capital check was skipped

@pytest.mark.asyncio
async def test_assess_trade_risk_empty_whitelist_allows_all_symbols(risk_service: RiskManagerService, mock_agent_service: MagicMock):
    agent_id = "agent_empty_whitelist"
    # No 'allowed_symbols' in operational_parameters means check is skipped
    agent_config = create_test_agent_config_for_risk(agent_id, allowed_symbols_list=None)
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    trade_signal = create_test_trade_signal("ANY/SYMB", quantity=1.0, price=10.0)
    assessment = await risk_service.assess_trade_risk(agent_id, trade_signal)

    assert assessment.signal_approved is True


# --- Tests for new risk rules ---

@pytest.mark.asyncio
async def test_assess_risk_max_loss_per_trade_percentage_balance_exceeded(
    risk_service: RiskManagerService, mock_agent_service: MagicMock, mock_trading_data_service: MagicMock
):
    agent_id = "agent_max_loss_exceeded"
    agent_config = create_test_agent_config_for_risk(agent_id, max_loss_per_trade_percentage_balance=0.01) # 1% risk
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    portfolio = create_test_portfolio_summary(account_value=10000.0) # Balance 10k USD
    mock_trading_data_service.get_portfolio_summary = AsyncMock(return_value=portfolio)

    # Max allowed loss = 1% of 10k = 100 USD
    # Signal: Price 100, SL 90 (Loss per unit 10), Qty 11. Total potential loss = 110 USD > 100 USD
    trade_signal = create_test_trade_signal("XYZ/USD", quantity=11.0, price=100.0, stop_loss=90.0)

    assessment = await risk_service.assess_trade_risk(agent_id, trade_signal)
    assert assessment.signal_approved is False
    assert "Potential loss" in assessment.rejection_reason and "exceeds max allowed risk per trade" in assessment.rejection_reason #type: ignore

@pytest.mark.asyncio
async def test_assess_risk_max_loss_per_trade_no_portfolio_rejects(
    risk_service: RiskManagerService, mock_agent_service: MagicMock, mock_trading_data_service: MagicMock
):
    agent_id = "agent_max_loss_no_portfolio"
    agent_config = create_test_agent_config_for_risk(agent_id, max_loss_per_trade_percentage_balance=0.01)
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)
    mock_trading_data_service.get_portfolio_summary = AsyncMock(return_value=None) # Portfolio unavailable

    trade_signal = create_test_trade_signal("ABC/USD", quantity=1, price=100, stop_loss=90)
    assessment = await risk_service.assess_trade_risk(agent_id, trade_signal)
    assert assessment.signal_approved is False
    assert "Portfolio data unavailable" in assessment.rejection_reason and "Max Loss % Balance" in assessment.rejection_reason #type: ignore

@pytest.mark.asyncio
async def test_assess_risk_max_concurrent_open_trades_exceeded(
    risk_service: RiskManagerService, mock_agent_service: MagicMock, mock_trading_data_service: MagicMock
):
    agent_id = "agent_max_concurrent_exceeded"
    agent_config = create_test_agent_config_for_risk(agent_id, max_concurrent_trades=2)
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    open_positions = [
        AssetPositionSummary(asset="BTC/USD", size=0.1, entry_price=50000),
        AssetPositionSummary(asset="ETH/USD", size=1.0, entry_price=3000)
    ] # Already 2 open positions on distinct assets
    portfolio = create_test_portfolio_summary(open_positions=open_positions)
    mock_trading_data_service.get_portfolio_summary = AsyncMock(return_value=portfolio)

    # Signal for a new asset
    trade_signal = create_test_trade_signal("ADA/USD", quantity=100.0, price=1.0)

    assessment = await risk_service.assess_trade_risk(agent_id, trade_signal)
    assert assessment.signal_approved is False
    assert "exceed max concurrent open positions limit" in assessment.rejection_reason #type: ignore

@pytest.mark.asyncio
async def test_assess_risk_max_exposure_per_asset_usd_exceeded(
    risk_service: RiskManagerService, mock_agent_service: MagicMock, mock_trading_data_service: MagicMock
):
    agent_id = "agent_max_exposure_exceeded"
    asset_symbol = "BTC/USD"
    agent_config = create_test_agent_config_for_risk(agent_id, max_asset_exposure_usd=6000.0)
    mock_agent_service.get_agent = AsyncMock(return_value=agent_config)

    # Existing position: 0.1 BTC @ current_price (assume $50000 for simplicity in test setup) = $5000 exposure
    open_positions = [
        AssetPositionSummary(asset=asset_symbol, size=0.1, entry_price=48000, current_price=50000.0)
    ]
    portfolio = create_test_portfolio_summary(open_positions=open_positions)
    mock_trading_data_service.get_portfolio_summary = AsyncMock(return_value=portfolio)

    # New trade: buy 0.03 BTC @ $51000. Notional = $1530
    # Current exposure (0.1 * 50000 = 5000).
    # Prospective size = 0.1 + 0.03 = 0.13. Prospective notional = 0.13 * 51000 = 6630 USD
    # This exceeds 6000 USD limit.
    trade_signal = create_test_trade_signal(asset_symbol, action="buy", quantity=0.03, price=51000.0)

    assessment = await risk_service.assess_trade_risk(agent_id, trade_signal)
    assert assessment.signal_approved is False
    assert "Prospective notional exposure" in assessment.rejection_reason and "exceed max limit" in assessment.rejection_reason #type: ignore


# Need Optional and List for type hints in helper
from typing import Optional, List
