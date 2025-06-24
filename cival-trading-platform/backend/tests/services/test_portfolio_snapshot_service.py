import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
import uuid
from typing import Callable, List

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from python_ai_services.core.database import Base # Your declarative base
from python_ai_services.models.db_models import PortfolioSnapshotDB
from python_ai_services.models.dashboard_models import PortfolioSnapshotOutput
from python_ai_services.models.event_bus_models import Event
from python_ai_services.services.portfolio_snapshot_service import PortfolioSnapshotService, PortfolioSnapshotServiceError
from python_ai_services.services.event_bus_service import EventBusService # For mocking

# --- In-Memory SQLite Test Database Setup ---
DATABASE_URL_TEST = "sqlite:///:memory:"
engine_test = create_engine(DATABASE_URL_TEST, connect_args={"check_same_thread": False})
TestSessionLocal: Callable[[], Session] = sessionmaker(autocommit=False, autoflush=False, bind=engine_test) # type: ignore

# --- Fixtures ---
@pytest_asyncio.fixture(scope="function")
async def db_session() -> Session:
    Base.metadata.create_all(bind=engine_test)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)

@pytest_asyncio.fixture
def mock_event_bus() -> MagicMock:
    return AsyncMock(spec=EventBusService)

@pytest_asyncio.fixture
def snapshot_service(mock_event_bus: MagicMock) -> PortfolioSnapshotService:
    # The service needs a factory (a callable that returns a new session)
    return PortfolioSnapshotService(session_factory=TestSessionLocal, event_bus=mock_event_bus)

# --- Test Cases ---

@pytest.mark.asyncio
async def test_record_snapshot_success(snapshot_service: PortfolioSnapshotService, db_session: Session, mock_event_bus: MagicMock):
    agent_id = "agent_record_snap"
    equity = 10050.75
    custom_time = datetime.now(timezone.utc) - timedelta(hours=1)

    pydantic_snapshot = await snapshot_service.record_snapshot(agent_id, equity, custom_time)

    assert pydantic_snapshot.agent_id == agent_id
    assert pydantic_snapshot.total_equity_usd == equity
    assert pydantic_snapshot.timestamp == custom_time

    # Verify in DB
    db_record = db_session.query(PortfolioSnapshotDB).filter_by(agent_id=agent_id).first()
    assert db_record is not None
    assert db_record.snapshot_id == pydantic_snapshot.snapshot_id # snapshot_id is auto-generated
    assert db_record.total_equity_usd == equity
    assert db_record.timestamp.replace(tzinfo=timezone.utc) == custom_time # Ensure timezone comparison

    # Verify event bus publish
    mock_event_bus.publish.assert_called_once()
    event_arg: Event = mock_event_bus.publish.call_args[0][0]
    assert event_arg.message_type == "PortfolioSnapshotTakenEvent"
    assert event_arg.publisher_agent_id == agent_id
    assert event_arg.payload["snapshot_id"] == pydantic_snapshot.snapshot_id
    assert event_arg.payload["total_equity_usd"] == equity

@pytest.mark.asyncio
async def test_record_snapshot_default_timestamp(snapshot_service: PortfolioSnapshotService, db_session: Session):
    agent_id = "agent_default_ts"
    equity = 9999.0

    before_call = datetime.now(timezone.utc)
    pydantic_snapshot = await snapshot_service.record_snapshot(agent_id, equity)
    after_call = datetime.now(timezone.utc)

    assert pydantic_snapshot.timestamp >= before_call
    assert pydantic_snapshot.timestamp <= after_call

    db_record = db_session.query(PortfolioSnapshotDB).filter_by(snapshot_id=pydantic_snapshot.snapshot_id).first()
    assert db_record is not None
    assert db_record.timestamp.replace(tzinfo=timezone.utc) == pydantic_snapshot.timestamp

@pytest.mark.asyncio
async def test_record_snapshot_no_event_bus(db_session: Session): # Test without event bus
    agent_id = "agent_no_bus_snap"
    equity = 1000.0
    service_no_bus = PortfolioSnapshotService(session_factory=TestSessionLocal, event_bus=None)

    # Ensure no error if event_bus is None
    await service_no_bus.record_snapshot(agent_id, equity)

    db_record = db_session.query(PortfolioSnapshotDB).filter_by(agent_id=agent_id).first()
    assert db_record is not None
    assert db_record.total_equity_usd == equity


@pytest.mark.asyncio
async def test_get_historical_snapshots_multiple_records(snapshot_service: PortfolioSnapshotService, db_session: Session):
    agent_id = "agent_hist_multi"
    base_time = datetime.now(timezone.utc)

    # Manually add some records to DB for testing get
    snap1_db = PortfolioSnapshotDB(agent_id=agent_id, total_equity_usd=1000.0, timestamp=base_time - timedelta(days=2))
    snap2_db = PortfolioSnapshotDB(agent_id=agent_id, total_equity_usd=1010.0, timestamp=base_time - timedelta(days=1))
    snap3_db = PortfolioSnapshotDB(agent_id=agent_id, total_equity_usd=1005.0, timestamp=base_time)
    # Snapshot for another agent
    snap_other_agent_db = PortfolioSnapshotDB(agent_id="other_agent", total_equity_usd=500.0, timestamp=base_time - timedelta(days=1))

    db_session.add_all([snap1_db, snap2_db, snap3_db, snap_other_agent_db])
    db_session.commit()

    # Test 1: Get all for agent_id, default sort (ascending)
    results_asc = await snapshot_service.get_historical_snapshots(agent_id)
    assert len(results_asc) == 3
    assert results_asc[0].total_equity_usd == 1000.0
    assert results_asc[1].total_equity_usd == 1010.0
    assert results_asc[2].total_equity_usd == 1005.0
    assert results_asc[0].timestamp < results_asc[1].timestamp < results_asc[2].timestamp

    # Test 2: Sort descending
    results_desc = await snapshot_service.get_historical_snapshots(agent_id, sort_ascending=False)
    assert len(results_desc) == 3
    assert results_desc[0].total_equity_usd == 1005.0
    assert results_desc[0].timestamp > results_desc[1].timestamp > results_desc[2].timestamp

    # Test 3: Limit
    results_limit = await snapshot_service.get_historical_snapshots(agent_id, limit=2, sort_ascending=True)
    assert len(results_limit) == 2
    assert results_limit[0].total_equity_usd == 1000.0
    assert results_limit[1].total_equity_usd == 1010.0

    # Test 4: Time filtering (start_time)
    results_start_time = await snapshot_service.get_historical_snapshots(agent_id, start_time=base_time - timedelta(days=1))
    assert len(results_start_time) == 2 # snap2_db and snap3_db
    assert results_start_time[0].total_equity_usd == 1010.0

    # Test 5: Time filtering (end_time)
    results_end_time = await snapshot_service.get_historical_snapshots(agent_id, end_time=base_time - timedelta(days=1))
    assert len(results_end_time) == 2 # snap1_db and snap2_db
    assert results_end_time[1].total_equity_usd == 1010.0

    # Test 6: Time filtering (start_time and end_time)
    results_range = await snapshot_service.get_historical_snapshots(
        agent_id,
        start_time=base_time - timedelta(days=1, hours=1), # Ensure it includes snap2_db
        end_time=base_time - timedelta(hours=1) # Ensure it includes snap2_db but not snap3_db
    )
    assert len(results_range) == 1
    assert results_range[0].total_equity_usd == 1010.0 # Only snap2_db

@pytest.mark.asyncio
async def test_get_historical_snapshots_no_records(snapshot_service: PortfolioSnapshotService):
    results = await snapshot_service.get_historical_snapshots("agent_no_records")
    assert len(results) == 0

# Need to import MagicMock for the mock_event_bus fixture
from unittest.mock import MagicMock
