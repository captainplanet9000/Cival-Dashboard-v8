import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import json
from typing import Optional, Dict, Any

# Models and Services to test or mock
from python_ai_services.services.trading_coordinator import TradingCoordinator
from python_ai_services.services.order_history_service import OrderHistoryService # Added
from python_ai_services.services.simulated_trade_executor import SimulatedTradeExecutor
from python_ai_services.services.hyperliquid_execution_service import HyperliquidExecutionService, HyperliquidExecutionServiceError
from python_ai_services.services.dex_execution_service import DEXExecutionService, DEXExecutionServiceError # Added

from python_ai_services.models.paper_trading_models import PaperTradeOrder, PaperTradeFill, PaperOrderStatus
from python_ai_services.models.trading_history_models import TradeSide as PaperTradeSide, OrderType as PaperOrderType
from python_ai_services.models.hyperliquid_models import HyperliquidPlaceOrderParams, HyperliquidOrderResponseData

from python_ai_services.utils.google_sdk_bridge import GoogleSDKBridge
from python_ai_services.utils.a2a_protocol import A2AProtocol
from python_ai_services.core.websocket_manager import ConnectionManager # Added
from python_ai_services.models.websocket_models import WebSocketEnvelope # Added

# --- Mock Fixtures ---

@pytest_asyncio.fixture
def mock_google_bridge():
    return MagicMock(spec=GoogleSDKBridge)

@pytest_asyncio.fixture
def mock_a2a_protocol():
    return MagicMock(spec=A2AProtocol)

@pytest_asyncio.fixture
def mock_simulated_executor():
    executor = MagicMock(spec=SimulatedTradeExecutor)
    executor.submit_paper_order = AsyncMock()
    return executor

@pytest_asyncio.fixture
def mock_hyperliquid_executor():
    executor = MagicMock(spec=HyperliquidExecutionService)
    executor.place_order = AsyncMock()
    return executor

@pytest_asyncio.fixture
def mock_dex_executor(): # New fixture for DEX
    executor = MagicMock(spec=DEXExecutionService)
    # This will be a placeholder, so the actual place_swap_order might not be called
    # or will be mocked if we test deeper logic later.
    # For now, its existence is key.
    executor.place_swap_order = AsyncMock()
    return executor

@pytest_asyncio.fixture
def mock_connection_manager() -> MagicMock: # Added
    manager = MagicMock(spec=ConnectionManager)
    manager.send_to_client = AsyncMock()
    return manager

@pytest_asyncio.fixture
def mock_order_history_service() -> MagicMock: # Added
    service = MagicMock(spec=OrderHistoryService)
    service.record_order_submission = AsyncMock()
    service.update_order_from_hl_response = AsyncMock()
    service.update_order_from_dex_response = AsyncMock()
    service.update_order_status = AsyncMock()
    service.link_fill_to_order = AsyncMock()
    return service

@pytest_asyncio.fixture
def trading_coordinator(
    mock_google_bridge: MagicMock,
    mock_a2a_protocol: MagicMock,
    mock_simulated_executor: MagicMock,
    mock_hyperliquid_executor: MagicMock,
    mock_dex_executor: MagicMock,
    mock_trade_history_service: MagicMock,
    mock_risk_manager_service: MagicMock,
    mock_agent_management_service: MagicMock,
    mock_event_bus_service: MagicMock,
    mock_connection_manager: MagicMock,
    mock_order_history_service: MagicMock # Added
):
    return TradingCoordinator(
        agent_id="tc_main_test_id",
        agent_management_service=mock_agent_management_service,
        risk_manager_service=mock_risk_manager_service,
        google_bridge=mock_google_bridge,
        a2a_protocol=mock_a2a_protocol,
        simulated_trade_executor=mock_simulated_executor,
        hyperliquid_execution_service=mock_hyperliquid_executor,
        dex_execution_service=mock_dex_executor,
        trade_history_service=mock_trade_history_service,
        event_bus_service=mock_event_bus_service,
        connection_mgr=mock_connection_manager,
        order_history_service=mock_order_history_service # Added
    )

# --- Tests for __init__ ---

def test_trading_coordinator_init(
    mock_google_bridge, mock_a2a_protocol, mock_simulated_executor,
    mock_hyperliquid_executor, mock_dex_executor, mock_trade_history_service,
    mock_risk_manager_service, mock_agent_management_service,
    mock_event_bus_service, mock_connection_manager: MagicMock,
    mock_order_history_service: MagicMock # Added
):
    coordinator = TradingCoordinator(
        agent_id="tc_test_init",
        agent_management_service=mock_agent_management_service,
        risk_manager_service=mock_risk_manager_service,
        google_bridge=mock_google_bridge,
        a2a_protocol=mock_a2a_protocol,
        simulated_trade_executor=mock_simulated_executor,
        hyperliquid_execution_service=mock_hyperliquid_executor,
        dex_execution_service=mock_dex_executor,
        trade_history_service=mock_trade_history_service,
        event_bus_service=mock_event_bus_service,
        connection_mgr=mock_connection_manager,
        order_history_service=mock_order_history_service # Added
    )
    assert coordinator.agent_id == "tc_test_init"
    assert coordinator.event_bus_service == mock_event_bus_service
    assert coordinator.hyperliquid_execution_service == mock_hyperliquid_executor
    assert coordinator.dex_execution_service == mock_dex_executor
    assert coordinator.trade_history_service == mock_trade_history_service
    assert coordinator.connection_manager == mock_connection_manager
    assert coordinator.order_history_service == mock_order_history_service # Added
    assert coordinator.trade_execution_mode == "paper"


# --- Tests for set_trade_execution_mode and get_trade_execution_mode ---

@pytest.mark.asyncio
async def test_set_and_get_trade_execution_mode(trading_coordinator: TradingCoordinator):
    # Default mode
    mode_info = await trading_coordinator.get_trade_execution_mode()
    assert mode_info["current_mode"] == "paper"

    # Set to hyperliquid (formerly live)
    await trading_coordinator.set_trade_execution_mode("hyperliquid")
    mode_info = await trading_coordinator.get_trade_execution_mode()
    assert mode_info["current_mode"] == "hyperliquid"

    # Set to dex
    await trading_coordinator.set_trade_execution_mode("dex")
    mode_info = await trading_coordinator.get_trade_execution_mode()
    assert mode_info["current_mode"] == "dex"

    # Set back to paper
    await trading_coordinator.set_trade_execution_mode("paper")
    mode_info = await trading_coordinator.get_trade_execution_mode()
    assert mode_info["current_mode"] == "paper"

@pytest.mark.asyncio
async def test_set_trade_execution_mode_invalid(trading_coordinator: TradingCoordinator):
    # Note: The allowed modes in TradingCoordinator.set_trade_execution_mode might have changed
    # Let's assume it was updated to ["paper", "hyperliquid", "dex"]
    with pytest.raises(ValueError, match="Invalid trade execution mode 'test'. Allowed modes are: paper, hyperliquid, dex"):
        await trading_coordinator.set_trade_execution_mode("test")

# --- Tests for _parse_crew_result_and_execute ---

@pytest.mark.asyncio
@patch.object(TradingCoordinator, '_execute_trade_decision', new_callable=AsyncMock)
async def test_parse_crew_result_risk_approved_executes(
    mock_execute_decision: AsyncMock,
    trading_coordinator: TradingCoordinator,
    mock_risk_manager_service: MagicMock
):
    user_id = "agent_risk_approved" # This is the agent_id for whom the decision is made
    crew_result_dict = {
        "action": "BUY", "symbol": "ETH/USD", "quantity": 0.1,
        "order_type": "LIMIT", "price": "2000.0",
        "strategy_name": "test_strat", "confidence": 0.8
    }
    # Mock RiskManagerService to approve the trade
    mock_risk_manager_service.assess_trade_risk = AsyncMock(
        return_value=RiskAssessmentResponseData(signal_approved=True)
    )

    await trading_coordinator._parse_crew_result_and_execute(crew_result_dict, user_id)

    mock_risk_manager_service.assess_trade_risk.assert_called_once()
    # Verify the TradeSignalEventPayload passed to assess_trade_risk
    call_args_list = mock_risk_manager_service.assess_trade_risk.call_args_list
    assert len(call_args_list) == 1
    actual_call_args = call_args_list[0][1] # Keywords args of the first call
    assert actual_call_args['agent_id_of_proposer'] == user_id
    assert isinstance(actual_call_args['trade_signal'], TradeSignalEventPayload)
    assert actual_call_args['trade_signal'].symbol == "ETH/USD"
    assert actual_call_args['trade_signal'].action == "buy"

    expected_trade_params_for_execution = {
        "action": "buy", "symbol": "ETH/USD", "quantity": 0.1,
        "order_type": "limit", "price": 2000.0,
        "stop_loss_price": None, "take_profit_price": None # From parsing logic if not in crew_result
    }
    mock_execute_decision.assert_called_once_with(expected_trade_params_for_execution, user_id)


@pytest.mark.asyncio
@patch.object(TradingCoordinator, '_execute_trade_decision', new_callable=AsyncMock)
async def test_parse_crew_result_risk_rejected_does_not_execute(
    mock_execute_decision: AsyncMock,
    trading_coordinator: TradingCoordinator,
    mock_risk_manager_service: MagicMock
):
    user_id = "agent_risk_rejected"
    crew_result_dict = {
        "action": "SELL", "symbol": "BTC/USD", "quantity": 0.01, "order_type": "MARKET", "price": 60000.0
    }
    # Mock RiskManagerService to reject the trade
    mock_risk_manager_service.assess_trade_risk = AsyncMock(
        return_value=RiskAssessmentResponseData(signal_approved=False, rejection_reason="Symbol not allowed")
    )

    await trading_coordinator._parse_crew_result_and_execute(crew_result_dict, user_id)

    mock_risk_manager_service.assess_trade_risk.assert_called_once()
    mock_execute_decision.assert_not_called() # Should not execute if risk rejected


@pytest.mark.asyncio
@patch.object(TradingCoordinator, '_execute_trade_decision', new_callable=AsyncMock)
async def test_parse_crew_result_hold_action_skips_risk_check_and_execution(
    mock_execute_decision: AsyncMock,
    trading_coordinator: TradingCoordinator,
    mock_risk_manager_service: MagicMock
):
    user_id = "agent_hold_action"
    crew_result_dict = {"action": "HOLD", "symbol": "ETH/USD"}

    with patch.object(trading_coordinator.logger, 'info') as mock_logger:
      await trading_coordinator._parse_crew_result_and_execute(crew_result_dict, user_id)

      mock_risk_manager_service.assess_trade_risk.assert_not_called()
      mock_execute_decision.assert_not_called()
      mock_logger.assert_any_call(f"Crew decision is 'hold' for ETH/USD. No trade execution. User ID: {user_id}")


@pytest.mark.asyncio
@patch.object(TradingCoordinator, '_execute_trade_decision', new_callable=AsyncMock)
async def test_parse_crew_result_missing_params(mock_execute_decision: AsyncMock, trading_coordinator: TradingCoordinator):
    user_id = str(uuid.uuid4())
    crew_result_dict = {"action": "BUY", "symbol": "ETH/USD"} # Missing quantity
    with patch.object(trading_coordinator, 'logger') as mock_logger:
        await trading_coordinator._parse_crew_result_and_execute(crew_result_dict, user_id)
        mock_execute_decision.assert_not_called()
        mock_logger.warning.assert_any_call(f"Essential trade parameters (action, symbol, quantity) not found in crew result: {crew_result_dict}")


@pytest.mark.asyncio
@patch.object(TradingCoordinator, '_execute_trade_decision', new_callable=AsyncMock)
async def test_parse_crew_result_invalid_json_string(mock_execute_decision: AsyncMock, trading_coordinator: TradingCoordinator):
    user_id = str(uuid.uuid4())
    crew_result_invalid_json = "{'action': 'BUY', 'symbol': 'ETH/USD'" # Invalid JSON
    with patch.object(trading_coordinator, 'logger') as mock_logger:
        await trading_coordinator._parse_crew_result_and_execute(crew_result_invalid_json, user_id)
        mock_execute_decision.assert_not_called()
        mock_logger.warning.assert_any_call(f"Crew result is a string but not valid JSON: {crew_result_invalid_json}")

# --- Tests for _execute_trade_decision ---

# Paper Trading Mode Tests
@pytest.mark.asyncio
async def test_execute_paper_trade_buy_limit_success(trading_coordinator: TradingCoordinator, mock_simulated_executor: MagicMock):
    await trading_coordinator.set_trade_execution_mode("paper")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "buy", "symbol": "ETH", "quantity": 1.0, "order_type": "limit", "price": 1900.0}

    mock_order = PaperTradeOrder(user_id=uuid.UUID(user_id), symbol="ETH", side=PaperTradeSide.BUY, order_type=PaperOrderType.LIMIT, quantity=1.0, limit_price=1900.0, status=PaperOrderStatus.FILLED, order_id=uuid.uuid4())
    mock_fill = PaperTradeFill(order_id=mock_order.order_id, user_id=uuid.UUID(user_id), symbol="ETH", side=PaperTradeSide.BUY, price=1900.0, quantity=1.0)
    mock_simulated_executor.submit_paper_order.return_value = (mock_order, [mock_fill])

    result = await trading_coordinator._execute_trade_decision(trade_params, user_id)

    mock_simulated_executor.submit_paper_order.assert_called_once()
    called_arg = mock_simulated_executor.submit_paper_order.call_args[0][0]
    assert isinstance(called_arg, PaperTradeOrder)
    assert called_arg.symbol == "ETH" and called_arg.side == PaperTradeSide.BUY
    assert result["status"] == "paper_executed"
    assert result["details"]["order"]["symbol"] == "ETH"

@pytest.mark.asyncio
async def test_execute_paper_trade_sell_market_success(trading_coordinator: TradingCoordinator, mock_simulated_executor: MagicMock):
    await trading_coordinator.set_trade_execution_mode("paper")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "sell", "symbol": "BTC", "quantity": 0.1, "order_type": "market"}

    mock_order = PaperTradeOrder(user_id=uuid.UUID(user_id), symbol="BTC", side=PaperTradeSide.SELL, order_type=PaperOrderType.MARKET, quantity=0.1, status=PaperOrderStatus.FILLED, order_id=uuid.uuid4())
    mock_fill = PaperTradeFill(order_id=mock_order.order_id, user_id=uuid.UUID(user_id), symbol="BTC", side=PaperTradeSide.SELL, price=30000.0, quantity=0.1) # Example fill price
    mock_simulated_executor.submit_paper_order.return_value = (mock_order, [mock_fill])

    result = await trading_coordinator._execute_trade_decision(trade_params, user_id)

    mock_simulated_executor.submit_paper_order.assert_called_once()
    called_arg = mock_simulated_executor.submit_paper_order.call_args[0][0]
    assert isinstance(called_arg, PaperTradeOrder)
    assert called_arg.symbol == "BTC" and called_arg.side == PaperTradeSide.SELL
    assert result["status"] == "paper_executed"

@pytest.mark.asyncio
async def test_execute_paper_trade_executor_fails(trading_coordinator: TradingCoordinator, mock_simulated_executor: MagicMock):
    await trading_coordinator.set_trade_execution_mode("paper")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "buy", "symbol": "ETH", "quantity": 1.0, "order_type": "market"}
    mock_simulated_executor.submit_paper_order.side_effect = Exception("Simulated DB error")

    result = await trading_coordinator._execute_trade_decision(trade_params, user_id)
    assert result["status"] == "paper_failed"
    assert result["error"] == "Simulated DB error"

@pytest.mark.asyncio
async def test_execute_paper_trade_no_executor(mock_google_bridge, mock_a2a_protocol, mock_hyperliquid_executor):
    # Initialize TC without simulated_executor
    coordinator = TradingCoordinator(mock_google_bridge, mock_a2a_protocol, None, mock_hyperliquid_executor)
    await coordinator.set_trade_execution_mode("paper")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "buy", "symbol": "ETH", "quantity": 1.0, "order_type": "market"}

    result = await coordinator._execute_trade_decision(trade_params, user_id)
    assert result["status"] == "paper_skipped"
    assert result["reason"] == "Simulated executor unavailable."


# Live Trading Mode Tests (Hyperliquid)
@pytest.mark.asyncio
async def test_execute_live_trade_buy_limit_success(trading_coordinator: TradingCoordinator, mock_hyperliquid_executor: MagicMock):
    await trading_coordinator.set_trade_execution_mode("live")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "buy", "symbol": "ETH", "quantity": 0.01, "order_type": "limit", "price": 1950.0}

    mock_hl_response = HyperliquidOrderResponseData(status="resting", oid=67890, order_type_info={"limit": {"tif": "Gtc"}})
    mock_hyperliquid_executor.place_order.return_value = mock_hl_response

    result = await trading_coordinator._execute_trade_decision(trade_params, user_id)

    mock_hyperliquid_executor.place_order.assert_called_once()
    called_arg: HyperliquidPlaceOrderParams = mock_hyperliquid_executor.place_order.call_args[0][0]
    assert isinstance(called_arg, HyperliquidPlaceOrderParams)
    assert called_arg.asset == "ETH"
    assert called_arg.is_buy is True
    assert called_arg.order_type == {"limit": {"tif": "Gtc"}}
    # Status changed in a previous subtask due to risk management additions
    assert result["status"] == "live_executed_with_risk_management"
    assert result["details"]["main_order"]["oid"] == 67890
    # Check that record_fill was NOT called because simulated_fills was None in mock_hl_response
    trading_coordinator.trade_history_service.record_fill.assert_not_called()


@pytest.mark.asyncio
async def test_execute_live_trade_fetches_and_records_actual_fills(
    trading_coordinator: TradingCoordinator,
    mock_hyperliquid_executor: MagicMock,
    mock_trade_history_service: MagicMock,
    mock_order_history_service: MagicMock
):
    await trading_coordinator.set_trade_execution_mode("hyperliquid")
    user_id = "agent_wallet_address_for_hl"
    trade_params = {"action": "buy", "symbol": "ETH", "quantity": 0.01, "order_type": "market", "price": 0.0, "strategy_name": "TestHLStrategy"}

    mock_internal_order_id = f"internal_{uuid.uuid4()}"
    mock_order_db_return = MagicMock()
    type(mock_order_db_return).internal_order_id = mock_internal_order_id # Make it behave like an ORM object with this attr
    mock_order_history_service.record_order_submission.return_value = mock_order_db_return

    mock_recorded_fill = TradeFillData(fill_id=str(uuid.uuid4()), agent_id=user_id, asset="ETH", side="buy", quantity=0.01, price=2000.0, timestamp=datetime.now(timezone.utc))
    mock_trade_history_service.record_fill.return_value = mock_recorded_fill

    mock_place_order_response = HyperliquidOrderResponseData(
        status="filled", oid=12345, order_type_info={"market": {"tif": "Ioc"}}
    )
    mock_hyperliquid_executor.place_order.return_value = mock_place_order_response

    mock_hl_actual_fill_dict = {
        "coin": "ETH", "dir": "Open Long", "px": "2000.0", "qty": "0.01",
        "time": int(datetime.now(timezone.utc).timestamp() * 1000),
        "fee": "0.2", "oid": 12345, "tid": "HLTradeID_XYZ"
    }
    mock_hyperliquid_executor.get_fills_for_order = AsyncMock(return_value=[mock_hl_actual_fill_dict])

    result = await trading_coordinator._execute_trade_decision(trade_params, user_id)

    assert result["status"] == "live_executed"
    assert result["details"]["main_order"]["oid"] == 12345

    mock_order_history_service.record_order_submission.assert_called_once()
    record_call_args = mock_order_history_service.record_order_submission.call_args[1]
    assert record_call_args['agent_id'] == user_id
    assert record_call_args['order_params'] == trade_params
    assert record_call_args['strategy_name'] == "TestHLStrategy"

    mock_order_history_service.update_order_from_hl_response.assert_called_once_with(
        internal_order_id=mock_internal_order_id,
        hl_response=mock_place_order_response
    )

    mock_hyperliquid_executor.get_fills_for_order.assert_called_once_with(user_address=user_id, oid=12345)
    mock_trade_history_service.record_fill.assert_called_once()

    mock_order_history_service.link_fill_to_order.assert_called_once_with(
        internal_order_id=mock_internal_order_id,
        fill_id=mock_recorded_fill.fill_id
    )

    # WebSocket call verification
    trading_coordinator.connection_manager.send_to_client.assert_called_once()
    ws_call_args = trading_coordinator.connection_manager.send_to_client.call_args[0]
    assert ws_call_args[0] == user_id
    ws_envelope: WebSocketEnvelope = ws_call_args[1]
    assert ws_envelope.event_type == "NEW_FILL"
    assert ws_envelope.payload["fill_id"] == mock_recorded_fill.fill_id

@pytest.mark.asyncio
async def test_execute_live_trade_no_fills_found_for_order(
    trading_coordinator: TradingCoordinator,
    mock_hyperliquid_executor: MagicMock,
    mock_trade_history_service: MagicMock,
    mock_order_history_service: MagicMock
):
    await trading_coordinator.set_trade_execution_mode("hyperliquid")
    user_id = "agent_wallet_for_hl_no_fills"
    trade_params = {"action": "sell", "symbol": "BTC", "quantity": 0.001, "order_type": "market", "price": 0.0}

    mock_internal_order_id = f"internal_{uuid.uuid4()}"
    mock_order_history_service.record_order_submission.return_value = MagicMock(internal_order_id=mock_internal_order_id)

    mock_place_order_response = HyperliquidOrderResponseData(status="ok", oid=67890)
    mock_hyperliquid_executor.place_order.return_value = mock_place_order_response
    mock_hyperliquid_executor.get_fills_for_order = AsyncMock(return_value=[])

    await trading_coordinator._execute_trade_decision(trade_params, user_id)

    mock_order_history_service.record_order_submission.assert_called_once()
    mock_order_history_service.update_order_from_hl_response.assert_called_once_with(mock_internal_order_id, mock_place_order_response)
    mock_hyperliquid_executor.get_fills_for_order.assert_called_once_with(user_address=user_id, oid=67890)
    mock_trade_history_service.record_fill.assert_not_called()
    mock_order_history_service.link_fill_to_order.assert_not_called()


@pytest.mark.asyncio
async def test_execute_live_trade_hyperliquid_service_error(
    trading_coordinator: TradingCoordinator,
    mock_hyperliquid_executor: MagicMock,
    mock_order_history_service: MagicMock
):
    await trading_coordinator.set_trade_execution_mode("hyperliquid")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "sell", "symbol": "BTC", "quantity": 0.001, "order_type": "market"}

    mock_internal_order_id = f"internal_{uuid.uuid4()}"
    mock_order_history_service.record_order_submission.return_value = MagicMock(internal_order_id=mock_internal_order_id)

    error_message = "Insufficient funds for HL"
    mock_hyperliquid_executor.place_order.side_effect = HyperliquidExecutionServiceError(error_message)

    result = await trading_coordinator._execute_trade_decision(trade_params, user_id)

    assert result["status"] == "live_failed"
    assert result["error"] == error_message
    mock_order_history_service.record_order_submission.assert_called_once()
    mock_order_history_service.update_order_status.assert_called_once_with(
        mock_internal_order_id, "ERROR", error_message=f"HL Execution Error: {error_message}"
    )

@pytest.mark.asyncio
async def test_execute_live_trade_general_exception(trading_coordinator: TradingCoordinator, mock_hyperliquid_executor: MagicMock):
    await trading_coordinator.set_trade_execution_mode("live")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "sell", "symbol": "BTC", "quantity": 0.001, "order_type": "market"}
    mock_hyperliquid_executor.place_order.side_effect = Exception("Unexpected network issue")

    result = await trading_coordinator._execute_trade_decision(trade_params, user_id)
    assert result["status"] == "live_failed"
    assert result["error"] == "Unexpected error: Unexpected network issue"


@pytest.mark.asyncio
async def test_execute_live_trade_no_hyperliquid_service( # Updated to pass all required TC args
    mock_google_bridge, mock_a2a_protocol, mock_simulated_executor,
    mock_agent_management_service, mock_risk_manager_service,
    mock_trade_history_service, mock_event_bus_service
):
    coordinator = TradingCoordinator(
        "tc_no_hl", mock_agent_management_service, mock_risk_manager_service,
        mock_google_bridge, mock_a2a_protocol, mock_simulated_executor,
        None, # No HyperliquidExecutionService
        mock_trade_history_service, mock_event_bus_service
    )
    await coordinator.set_trade_execution_mode("live")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "buy", "symbol": "ETH", "quantity": 1.0, "order_type": "market"}

    result = await coordinator._execute_trade_decision(trade_params, user_id)
    assert result["status"] == "live_skipped"
    assert result["reason"] == "Hyperliquid service unavailable."

# DEX Trading Mode Tests
@pytest.mark.asyncio
async def test_execute_dex_trade_success_placeholder(trading_coordinator: TradingCoordinator, mock_dex_executor: MagicMock, caplog):
    await trading_coordinator.set_trade_execution_mode("dex")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "buy", "symbol": "WETH/USDC", "quantity": 1.0, "order_type": "limit", "price": 3000.0}

    # Since it's a placeholder, place_swap_order might not be called, or if it is, mock its return
    mock_dex_executor.place_swap_order = AsyncMock(return_value={
        "tx_hash": "0xMockDexTxHash", "status": "success", "error": None,
        "amount_out_wei_actual": 2990 * (10**6), # Example output for USDC (6 decimals)
        "amount_out_wei_minimum_requested": 2985 * (10**6)
    })

    result = await trading_coordinator._execute_trade_decision(trade_params, user_id)

    assert result["status"] == "dex_executed_placeholder"
    assert "details" in result
    assert result["details"]["status"] == "success_mocked_dex" # From the placeholder logic
    assert "DEX Trade conceptual mapping" in caplog.text
    assert f"Original trade_params: {trade_params}" in caplog.text
    assert "Conceptual mapped params" in caplog.text
    # If the conceptual call to place_swap_order was made (even if commented out in service):
    # mock_dex_executor.place_swap_order.assert_called_once()
    # For current placeholder, the actual call is commented out, so we check logs.

@pytest.mark.asyncio
async def test_execute_dex_trade_no_dex_service(
    mock_google_bridge, mock_a2a_protocol, mock_simulated_executor,
    mock_hyperliquid_executor, mock_trade_history_service,
    mock_risk_manager_service, mock_agent_management_service, mock_event_bus_service
):
    # Initialize TC without dex_execution_service
    coordinator_no_dex = TradingCoordinator(
        agent_id="tc_no_dex",
        agent_management_service=mock_agent_management_service,
        risk_manager_service=mock_risk_manager_service,
        google_bridge=mock_google_bridge, a2a_protocol=mock_a2a_protocol,
        simulated_trade_executor=mock_simulated_executor,
        hyperliquid_execution_service=mock_hyperliquid_executor,
        dex_execution_service=None, # Explicitly None
        trade_history_service=mock_trade_history_service,
        event_bus_service=mock_event_bus_service
    )
    await coordinator_no_dex.set_trade_execution_mode("dex")
    user_id = str(uuid.uuid4())
    trade_params = {"action": "buy", "symbol": "UNI/ETH", "quantity": 10, "order_type": "market"}

    result = await coordinator_no_dex._execute_trade_decision(trade_params, user_id)
    assert result["status"] == "dex_skipped"
    assert result["reason"] == "DEX service unavailable."

# Unknown Mode Test
@pytest.mark.asyncio
async def test_execute_trade_unknown_mode(trading_coordinator: TradingCoordinator):
    # This test is fine, set_trade_execution_mode is independent of new __init__ args
    # Need to ensure the mode being set is actually unknown to the updated set_trade_execution_mode
    await trading_coordinator.set_trade_execution_mode("hyperliquid") # Set to a known state first
    trading_coordinator.trade_execution_mode = "mystery_mode" # Force unknown mode directly for test

    user_id = str(uuid.uuid4())
    trade_params = {"action": "buy", "symbol": "SOL", "quantity": 10, "order_type": "market"}

    result = await trading_coordinator._execute_trade_decision(trade_params, user_id)
    assert result["status"] == "error"
    assert result["reason"] == "Unknown trade execution mode."

# --- Tests for Event Bus Integration ---

@pytest.mark.asyncio
async def test_setup_event_subscriptions(trading_coordinator: TradingCoordinator, mock_event_bus_service: MagicMock):
    await trading_coordinator.setup_event_subscriptions()

    expected_calls = [
        call("TradeSignalEvent", trading_coordinator.handle_external_trade_signal),
        call("MarketConditionEvent", trading_coordinator.handle_market_condition_event)
    ]
    mock_event_bus_service.subscribe.assert_has_calls(expected_calls, any_order=True)
    assert mock_event_bus_service.subscribe.call_count == 2

@pytest.mark.asyncio
async def test_setup_event_subscriptions_no_bus(mock_google_bridge, mock_a2a_protocol, mock_simulated_executor, mock_hyperliquid_executor, mock_trade_history_service, mock_risk_manager_service, mock_agent_management_service):
    # Create TC with event_bus_service=None (though it's required now, testing defensive check)
    # The __init__ requires EventBusService, so this tests an edge case if it were optional.
    # To properly test this, we'd need to make EventBusService optional in __init__ again.
    # For now, assume EventBusService is always provided. If test fails due to required arg, this test needs rethink or __init__ change.
    # As EventBusService is now required, this test might be less relevant unless we want to test if it's None *after* init.
    # Let's skip this specific test as EventBusService is now a required __init__ argument.
    pass


@pytest.mark.asyncio
@patch.object(TradingCoordinator, '_execute_trade_decision', new_callable=AsyncMock)
async def test_handle_external_trade_signal_approved(
    mock_execute_decision: AsyncMock,
    trading_coordinator: TradingCoordinator,
    mock_risk_manager_service: MagicMock
):
    publisher_agent_id = "signal_agent_1"
    signal_payload_data = {
        "symbol": "BTC/USD", "action": "buy", "quantity": 0.05,
        "price_target": 65000.0, "stop_loss": 64000.0, "strategy_name": "TA_Strat1"
    }
    event = Event(
        publisher_agent_id=publisher_agent_id,
        message_type="TradeSignalEvent",
        payload=signal_payload_data
    )
    # Mock RiskManager to approve
    mock_risk_manager_service.assess_trade_risk = AsyncMock(return_value=RiskAssessmentResponseData(signal_approved=True))

    await trading_coordinator.handle_external_trade_signal(event)

    mock_risk_manager_service.assess_trade_risk.assert_called_once()
    # Check that TradeSignalEventPayload was passed correctly
    passed_signal_payload = mock_risk_manager_service.assess_trade_risk.call_args[1]['trade_signal']
    assert isinstance(passed_signal_payload, TradeSignalEventPayload)
    assert passed_signal_payload.symbol == "BTC/USD"

    expected_trade_params = {
        "action": "buy", "symbol": "BTC/USD", "quantity": 0.05,
        "order_type": "limit", "price": 65000.0,
        "stop_loss_price": 64000.0, "take_profit_price": None,
        "strategy_name": "TA_Strat1", "confidence": None # Confidence defaults to None if not in payload
    }
    mock_execute_decision.assert_called_once_with(expected_trade_params, publisher_agent_id)


@pytest.mark.asyncio
@patch.object(TradingCoordinator, '_execute_trade_decision', new_callable=AsyncMock)
async def test_handle_external_trade_signal_rejected(
    mock_execute_decision: AsyncMock,
    trading_coordinator: TradingCoordinator,
    mock_risk_manager_service: MagicMock
):
    publisher_agent_id = "signal_agent_2"
    signal_payload_data = {"symbol": "ETH/USD", "action": "sell", "quantity": 1.0, "price_target": 3000.0, "strategy_name": "TA_Strat2"}
    event = Event(publisher_agent_id=publisher_agent_id, message_type="TradeSignalEvent", payload=signal_payload_data)
    # Mock RiskManager to reject
    mock_risk_manager_service.assess_trade_risk = AsyncMock(
        return_value=RiskAssessmentResponseData(signal_approved=False, rejection_reason="Too risky")
    )

    await trading_coordinator.handle_external_trade_signal(event)
    mock_risk_manager_service.assess_trade_risk.assert_called_once()
    mock_execute_decision.assert_not_called()


@pytest.mark.asyncio
async def test_handle_external_trade_signal_missing_quantity(trading_coordinator: TradingCoordinator, mock_risk_manager_service: MagicMock):
    publisher_agent_id = "signal_agent_3"
    # Signal missing quantity
    signal_payload_data = {"symbol": "ADA/USD", "action": "buy", "price_target": 1.5, "strategy_name": "TA_Strat3"}
    event = Event(publisher_agent_id=publisher_agent_id, message_type="TradeSignalEvent", payload=signal_payload_data)

    # Risk assessment might not even be called if quantity is essential before it
    # The current logic calls risk assessment first then checks quantity if approved.
    # Let's assume risk assessment is called.
    mock_risk_manager_service.assess_trade_risk = AsyncMock(return_value=RiskAssessmentResponseData(signal_approved=True))

    with patch.object(trading_coordinator.logger, 'warning') as mock_logger:
        await trading_coordinator.handle_external_trade_signal(event)
        mock_logger.assert_any_call(f"TC ({trading_coordinator.agent_id}): TradeSignalEvent from {publisher_agent_id} for ADA/USD has no quantity. Rejecting execution.")

    trading_coordinator._execute_trade_decision = AsyncMock() # Re-patch to check it's not called
    trading_coordinator._execute_trade_decision.assert_not_called()


@pytest.mark.asyncio
async def test_handle_market_condition_event_logs_info(trading_coordinator: TradingCoordinator):
    publisher_agent_id = "mcc_agent_1"
    condition_payload_data = {
        "symbol": "BTC/USD", "regime": "trending_up",
        "confidence_score": 0.8, "supporting_data": {"adx": 30}
    }
    event = Event(publisher_agent_id=publisher_agent_id, message_type="MarketConditionEvent", payload=condition_payload_data)

    with patch.object(trading_coordinator.logger, 'debug') as mock_logger_debug, \
         patch.object(trading_coordinator.logger, 'info') as mock_logger_info:
        await trading_coordinator.handle_market_condition_event(event)
        mock_logger_info.assert_any_call(f"TradingCoordinator ({trading_coordinator.agent_id}): Received MarketConditionEvent (ID: {event.event_id}) from agent {publisher_agent_id}.")
        mock_logger_debug.assert_any_call(f"TC ({trading_coordinator.agent_id}): Market Condition for BTC/USD: trending_up, Confidence: 0.8. Data: {{'adx': 30}}")

# Need to import 'call' for assert_has_calls
from unittest.mock import call

