import pytest
import pytest_asyncio
from typing import List, Dict, Any, Callable, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from datetime import datetime, timezone
import uuid
import json

from python_ai_services.core.database import Base
from python_ai_services.models.db_models import OrderDB
from python_ai_services.models.dashboard_models import OrderLogItem # For testing the Pydantic conversion
from python_ai_services.models.hyperliquid_models import HyperliquidOrderResponseData # For type hint
from python_ai_services.services.order_history_service import OrderHistoryService, OrderHistoryServiceError

# --- In-Memory SQLite Test Database Setup ---
DATABASE_URL_TEST_ORDERS = "sqlite:///:memory:"
engine_test_orders = create_engine(DATABASE_URL_TEST_ORDERS, connect_args={"check_same_thread": False})
TestSessionLocalOrders: Callable[[], Session] = sessionmaker(autocommit=False, autoflush=False, bind=engine_test_orders) # type: ignore

# --- Fixtures ---
@pytest_asyncio.fixture(scope="function")
async def db_session_orders() -> Session: # Renamed to avoid conflict if other db tests are in same scope
    Base.metadata.create_all(bind=engine_test_orders)
    session = TestSessionLocalOrders()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test_orders)

@pytest_asyncio.fixture
async def order_history_service(db_session_orders: Session) -> OrderHistoryService:
    # The service needs a factory (a callable that returns a new session)
    return OrderHistoryService(session_factory=TestSessionLocalOrders)

# --- Helper to create sample order parameters ---
def create_sample_order_params(symbol: str = "BTC/USD", action: str = "buy", quantity: float = 1.0, order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
    return {
        "symbol": symbol, "action": action, "quantity": quantity,
        "order_type": order_type, "price": price, "strategy_name": "TestStrategy"
    }

# --- Test Cases ---

@pytest.mark.asyncio
async def test_record_order_submission(order_history_service: OrderHistoryService, db_session_orders: Session):
    agent_id = "agent_record_order"
    params = create_sample_order_params(symbol="ETH/USD", action="sell", quantity=0.5, order_type="limit", price=3000.0)
    client_oid = str(uuid.uuid4())

    db_order_instance = await order_history_service.record_order_submission(
        agent_id=agent_id, order_params=params, strategy_name="LimitSellStrat", client_order_id=client_oid
    )

    assert db_order_instance is not None
    assert db_order_instance.internal_order_id is not None
    assert db_order_instance.agent_id == agent_id
    assert db_order_instance.asset == "ETH/USD"
    assert db_order_instance.side == "sell"
    assert db_order_instance.order_type == "limit"
    assert db_order_instance.quantity == 0.5
    assert db_order_instance.limit_price == 3000.0
    assert db_order_instance.status == "PENDING_SUBMISSION" # Initial status
    assert db_order_instance.client_order_id == client_oid
    assert db_order_instance.strategy_name == "LimitSellStrat"
    assert json.loads(db_order_instance.raw_order_params_json) == params

    # Verify in DB
    retrieved = db_session_orders.query(OrderDB).filter_by(internal_order_id=db_order_instance.internal_order_id).first()
    assert retrieved is not None
    assert retrieved.asset == "ETH/USD"

@pytest.mark.asyncio
async def test_update_order_from_hl_response_success(order_history_service: OrderHistoryService, db_session_orders: Session):
    # First, record an order
    initial_order = OrderDB(agent_id="agent_hl_update", asset="BTC/USD", side="buy", order_type="market", quantity=0.01, status="PENDING_SUBMISSION")
    db_session_orders.add(initial_order)
    db_session_orders.commit()
    db_session_orders.refresh(initial_order)
    internal_id = initial_order.internal_order_id

    hl_response = HyperliquidOrderResponseData(status="resting", oid=12345, order_type_info={"limit": {"tif": "Gtc"}})

    await order_history_service.update_order_from_hl_response(internal_id, hl_response)

    updated_order = db_session_orders.query(OrderDB).filter_by(internal_order_id=internal_id).first()
    assert updated_order is not None
    assert updated_order.status == "ACCEPTED_BY_EXCHANGE" # "resting" maps to this
    assert updated_order.exchange_order_id == "12345"
    assert updated_order.error_message is None

@pytest.mark.asyncio
async def test_update_order_from_hl_response_error_status(order_history_service: OrderHistoryService, db_session_orders: Session):
    initial_order = OrderDB(agent_id="agent_hl_err", asset="SOL/USD", side="buy", order_type="limit", quantity=10, limit_price=40.0, status="PENDING_SUBMISSION")
    db_session_orders.add(initial_order)
    db_session_orders.commit()
    internal_id = initial_order.internal_order_id

    hl_response_error = HyperliquidOrderResponseData(status="error", oid=None, order_type_info={}) # Example error response
    # Or the error might come via error_str parameter

    await order_history_service.update_order_from_hl_response(internal_id, hl_response_error, error_str="Exchange rejected: insufficient margin")

    updated_order = db_session_orders.query(OrderDB).filter_by(internal_order_id=internal_id).first()
    assert updated_order.status == "ERROR"
    assert updated_order.error_message == "Exchange rejected: insufficient margin"


@pytest.mark.asyncio
async def test_update_order_from_dex_response_success(order_history_service: OrderHistoryService, db_session_orders: Session):
    initial_order = OrderDB(agent_id="agent_dex_update", asset="WETH/USDC", side="buy", order_type="market", quantity=1.0, status="PENDING_SUBMISSION")
    db_session_orders.add(initial_order)
    db_session_orders.commit()
    internal_id = initial_order.internal_order_id

    dex_response = {"status": "success", "tx_hash": "0x123abc", "amount_out_wei_actual": 1000}

    await order_history_service.update_order_from_dex_response(internal_id, dex_response)

    updated_order = db_session_orders.query(OrderDB).filter_by(internal_order_id=internal_id).first()
    assert updated_order.status == "ACCEPTED_BY_EXCHANGE" # Or FILLED if logic changes based on amount_out
    assert updated_order.exchange_order_id == "0x123abc"

@pytest.mark.asyncio
async def test_update_order_status_generic(order_history_service: OrderHistoryService, db_session_orders: Session):
    initial_order = OrderDB(agent_id="agent_generic_update", asset="ADA/USD", side="sell", order_type="limit", quantity=100, limit_price=0.5, status="PENDING_SUBMISSION")
    db_session_orders.add(initial_order)
    db_session_orders.commit()
    internal_id = initial_order.internal_order_id

    await order_history_service.update_order_status(internal_id, "CANCELED", exchange_order_id="ext789")

    updated_order = db_session_orders.query(OrderDB).filter_by(internal_order_id=internal_id).first()
    assert updated_order.status == "CANCELED"
    assert updated_order.exchange_order_id == "ext789"

@pytest.mark.asyncio
async def test_link_fill_to_order(order_history_service: OrderHistoryService, db_session_orders: Session):
    initial_order = OrderDB(agent_id="agent_link_fill", asset="LINK/USD", side="buy", order_type="market", quantity=5, status="ACCEPTED_BY_EXCHANGE")
    db_session_orders.add(initial_order)
    db_session_orders.commit()
    internal_id = initial_order.internal_order_id

    fill_id_1 = str(uuid.uuid4())
    fill_id_2 = str(uuid.uuid4())

    await order_history_service.link_fill_to_order(internal_id, fill_id_1)
    updated_order_1 = db_session_orders.query(OrderDB).filter_by(internal_order_id=internal_id).first()
    assert json.loads(updated_order_1.associated_fill_ids_json) == [fill_id_1]

    await order_history_service.link_fill_to_order(internal_id, fill_id_2)
    updated_order_2 = db_session_orders.query(OrderDB).filter_by(internal_order_id=internal_id).first()
    assert json.loads(updated_order_2.associated_fill_ids_json) == [fill_id_1, fill_id_2]

    # Test linking same fill again (should not duplicate)
    await order_history_service.link_fill_to_order(internal_id, fill_id_1)
    updated_order_3 = db_session_orders.query(OrderDB).filter_by(internal_order_id=internal_id).first()
    assert json.loads(updated_order_3.associated_fill_ids_json) == [fill_id_1, fill_id_2]


@pytest.mark.asyncio
async def test_get_orders_for_agent(order_history_service: OrderHistoryService, db_session_orders: Session):
    agent_id_1 = "agent_get_orders_1"
    agent_id_2 = "agent_get_orders_2"

    # Orders for agent_id_1
    db_session_orders.add(OrderDB(agent_id=agent_id_1, asset="BTC/USD", side="buy", order_type="market", quantity=0.1, status="FILLED", timestamp_created=datetime.now(timezone.utc)-timedelta(hours=2)))
    db_session_orders.add(OrderDB(agent_id=agent_id_1, asset="ETH/USD", side="sell", order_type="limit", quantity=1, limit_price=3000, status="ACCEPTED_BY_EXCHANGE", timestamp_created=datetime.now(timezone.utc)-timedelta(hours=1)))
    # Order for agent_id_2
    db_session_orders.add(OrderDB(agent_id=agent_id_2, asset="SOL/USD", side="buy", order_type="market", quantity=10, status="FILLED"))
    db_session_orders.commit()

    orders_agent1 = await order_history_service.get_orders_for_agent(agent_id_1)
    assert len(orders_agent1) == 2
    assert orders_agent1[0].asset == "ETH/USD" # Newest first by default
    assert orders_agent1[1].asset == "BTC/USD"

    orders_agent1_limit1 = await order_history_service.get_orders_for_agent(agent_id_1, limit=1)
    assert len(orders_agent1_limit1) == 1
    assert orders_agent1_limit1[0].asset == "ETH/USD"

    orders_agent1_status_filled = await order_history_service.get_orders_for_agent(agent_id_1, status_filter="FILLED")
    assert len(orders_agent1_status_filled) == 1
    assert orders_agent1_status_filled[0].asset == "BTC/USD"

    orders_agent1_asc = await order_history_service.get_orders_for_agent(agent_id_1, sort_desc=False)
    assert orders_agent1_asc[0].asset == "BTC/USD" # Oldest first

@pytest.mark.asyncio
async def test_get_order_by_internal_id(order_history_service: OrderHistoryService, db_session_orders: Session):
    order = OrderDB(internal_order_id="test_internal_id_123", agent_id="agent_get_by_id", asset="XRP/USD", side="buy", order_type="market", quantity=1000, status="FILLED")
    db_session_orders.add(order)
    db_session_orders.commit()

    retrieved_order = await order_history_service.get_order_by_internal_id("test_internal_id_123")
    assert retrieved_order is not None
    assert retrieved_order.asset == "XRP/USD"

    not_found_order = await order_history_service.get_order_by_internal_id("non_existent_id")
    assert not_found_order is None

@pytest.mark.asyncio
async def test_db_order_to_pydantic_log_item(order_history_service: OrderHistoryService):
    now = datetime.now(timezone.utc)
    db_order = OrderDB(
        internal_order_id="order_log_test_id", agent_id="agent_log",
        timestamp_created=now - timedelta(minutes=5), timestamp_updated=now,
        asset="TEST/ASSET", side="buy", order_type="limit", quantity=1.5, limit_price=100.0,
        status="PARTIALLY_FILLED", exchange_order_id="ex123", client_order_id="cli456",
        error_message=None, strategy_name="TestStrategyOrderLog"
    )
    # No need to add to DB session for this helper test if not querying

    pydantic_item = order_history_service._db_order_to_pydantic_log_item(db_order)

    assert isinstance(pydantic_item, OrderLogItem)
    assert pydantic_item.internal_order_id == "order_log_test_id"
    assert pydantic_item.agent_id == "agent_log"
    assert pydantic_item.asset == "TEST/ASSET"
    assert pydantic_item.status == "PARTIALLY_FILLED"
    assert pydantic_item.strategy_name == "TestStrategyOrderLog"
    # Check if timestamp_created is used for 'timestamp' field in OrderLogItem
    assert pydantic_item.timestamp_created == db_order.timestamp_created
