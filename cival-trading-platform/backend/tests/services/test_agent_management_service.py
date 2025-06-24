import pytest
import pytest_asyncio
from datetime import datetime, timezone
import uuid
import json
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List # Added List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from python_ai_services.core.database import Base
from python_ai_services.models.db_models import AgentConfigDB

from python_ai_services.models.agent_models import (
    AgentConfigInput,
    AgentStrategyConfig,
    AgentRiskConfig,
    AgentUpdateRequest,
    AgentConfigOutput,
    AgentStatus
)
from python_ai_services.services.agent_management_service import AgentManagementService
import asyncio

# --- Test Database Setup ---
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)

@pytest_asyncio.fixture
async def service(db_session: Session) -> AgentManagementService:
    def test_session_factory():
        # This factory will be called by the service for each DB operation.
        # For tests, we want it to use the session managed by the db_session fixture.
        # However, the db_session fixture yields a single session for the test's duration.
        # If service methods close the session, the factory must provide a new one from TestSessionLocal.
        # The service is written to get a new session per method call.
        return TestSessionLocal()

    service_instance = AgentManagementService(session_factory=TestSessionLocal)
    await service_instance._load_existing_statuses_from_db()
    return service_instance

# Helper to create agent input for tests
def create_sample_agent_input(
    name: str = "Test Agent",
    agent_type: str = "GenericAgent",
    parent_id: Optional[str] = None,
    op_params: Optional[Dict[str, Any]] = None,
    risk_config_override: Optional[Dict[str, Any]] = None,
    strategy_params_override: Optional[Dict[str, Any]] = None, # For specific strategy params like darvas, etc.
    watched_symbols: Optional[List[str]] = None
) -> AgentConfigInput:

    strategy_details: Dict[str, Any] = {
        "strategy_name": "test_strat",
        "parameters": {"param1": 10},
        "watched_symbols": watched_symbols if watched_symbols is not None else ["BTC/USD"],
    }
    if strategy_params_override: # Merge specific strategy params if provided
        strategy_details.update(strategy_params_override)
    strategy_conf = AgentStrategyConfig(**strategy_details)

    risk_conf_data = {"max_capital_allocation_usd": 1000.0, "risk_per_trade_percentage": 0.01}
    if risk_config_override:
        risk_conf_data.update(risk_config_override)
    risk_conf = AgentRiskConfig(**risk_conf_data)

    return AgentConfigInput(
        name=name,
        strategy=strategy_conf,
        risk_config=risk_conf,
        execution_provider="paper",
        agent_type=agent_type,
        parent_agent_id=parent_id,
        operational_parameters=op_params if op_params else {"op_key": "op_value"}
    )

# --- CRUD Tests ---
@pytest.mark.asyncio
async def test_create_agent(service: AgentManagementService, db_session: Session):
    agent_input = create_sample_agent_input(
        risk_config_override={"stop_loss_percentage": 0.05},
        strategy_params_override={"darvas_params": {"lookback_period": 30}}
    )
    created_agent_pydantic = await service.create_agent(agent_input)

    assert isinstance(created_agent_pydantic, AgentConfigOutput)
    assert created_agent_pydantic.name == "Test Agent"
    agent_id = created_agent_pydantic.agent_id
    assert created_agent_pydantic.risk_config.max_capital_allocation_usd == 1000.0
    assert created_agent_pydantic.risk_config.stop_loss_percentage == 0.05
    assert created_agent_pydantic.strategy.darvas_params is not None
    assert created_agent_pydantic.strategy.darvas_params.lookback_period == 30 #type: ignore

    db_record = db_session.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
    assert db_record is not None
    risk_config_in_db = json.loads(db_record.risk_config_json)
    assert risk_config_in_db["max_capital_allocation_usd"] == 1000.0
    assert risk_config_in_db["stop_loss_percentage"] == 0.05
    strategy_in_db = json.loads(db_record.strategy_config_json)
    assert strategy_in_db["darvas_params"]["lookback_period"] == 30

@pytest.mark.asyncio
async def test_get_agent(service: AgentManagementService):
    agent_input = create_sample_agent_input(name="Get Me Agent", risk_config_override={"take_profit_percentage": 0.1})
    created_agent_pydantic = await service.create_agent(agent_input)

    retrieved_agent = await service.get_agent(created_agent_pydantic.agent_id)
    assert retrieved_agent is not None
    assert retrieved_agent.agent_id == created_agent_pydantic.agent_id
    assert retrieved_agent.name == "Get Me Agent"
    assert retrieved_agent.risk_config.take_profit_percentage == 0.1

@pytest.mark.asyncio
async def test_update_agent(service: AgentManagementService):
    agent_input = create_sample_agent_input("Initial DB Name", op_params={"op1": "val1", "op2": "val2"})
    created_agent = await service.create_agent(agent_input)
    agent_id = created_agent.agent_id

    update_payload = AgentUpdateRequest(
        name="Updated DB Name",
        description="New DB Desc",
        risk_config=AgentRiskConfig(max_capital_allocation_usd=2000, risk_per_trade_percentage=0.02),
        operational_parameters={"op1": "new_val1", "op3": "val3"},
        strategy=AgentStrategyConfig(
            strategy_name="updated_strat",
            parameters={"param1": 20},
            watched_symbols=["ETH/USD"],
            darvas_params=AgentStrategyConfig.DarvasStrategyParams(lookback_period=50)
        )
    )

    updated_agent = await service.update_agent(agent_id, update_payload)

    assert updated_agent is not None
    assert updated_agent.name == "Updated DB Name"
    assert updated_agent.operational_parameters == {"op1": "new_val1", "op2": "val2", "op3": "val3"} # op2 remains
    assert updated_agent.risk_config.max_capital_allocation_usd == 2000
    assert updated_agent.strategy.strategy_name == "updated_strat"
    assert updated_agent.strategy.parameters == {"param1": 20} # Original param1 updated
    assert updated_agent.strategy.watched_symbols == ["ETH/USD"]
    assert updated_agent.strategy.darvas_params is not None
    assert updated_agent.strategy.darvas_params.lookback_period == 50

@pytest.mark.asyncio
async def test_update_agent_is_active_updates_status(service: AgentManagementService, db_session: Session):
    created_agent = await service.create_agent(create_sample_agent_input("StatusUpdateAgent"))
    agent_id = created_agent.agent_id
    assert created_agent.is_active is False
    initial_status = await service.get_agent_status(agent_id)
    assert initial_status is not None
    assert initial_status.status == "stopped"

    # Update is_active to True
    await service.update_agent(agent_id, AgentUpdateRequest(is_active=True))
    updated_status_true = await service.get_agent_status(agent_id)
    assert updated_status_true is not None
    assert updated_status_true.status == "running"
    db_agent_true = db_session.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
    assert db_agent_true is not None
    assert db_agent_true.is_active is True

    # Update is_active to False
    await service.update_agent(agent_id, AgentUpdateRequest(is_active=False))
    updated_status_false = await service.get_agent_status(agent_id)
    assert updated_status_false is not None
    assert updated_status_false.status == "stopped"
    db_agent_false = db_session.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
    assert db_agent_false is not None
    assert db_agent_false.is_active is False


@pytest.mark.asyncio
async def test_load_agent_with_invalid_risk_config_json(service: AgentManagementService, db_session: Session):
    agent_id = str(uuid.uuid4())
    db_agent = AgentConfigDB(
        agent_id=agent_id, name="InvalidRiskAgent",
        strategy_config_json=AgentStrategyConfig(strategy_name="s", parameters={}).model_dump_json(),
        risk_config_json="{'this_is': 'not_a_valid_risk_config_json_because_single_quotes'}",
        operational_parameters_json="{}",
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    db_session.add(db_agent)
    db_session.commit()

    loaded_agent = await service.get_agent(agent_id)
    assert loaded_agent is not None
    default_risk_config = AgentRiskConfig(max_capital_allocation_usd=0, risk_per_trade_percentage=0.01)
    assert loaded_agent.risk_config.max_capital_allocation_usd == default_risk_config.max_capital_allocation_usd
    assert loaded_agent.risk_config.risk_per_trade_percentage == default_risk_config.risk_per_trade_percentage

@pytest.mark.asyncio
async def test_load_agent_with_missing_risk_config_json_field(service: AgentManagementService, db_session: Session):
    agent_id = str(uuid.uuid4())
    db_agent_no_risk = AgentConfigDB(
        agent_id=agent_id, name="NoRiskJsonAgent",
        strategy_config_json=AgentStrategyConfig(strategy_name="s", parameters={}).model_dump_json(),
        risk_config_json=None,
        operational_parameters_json="{}",
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    db_session.add(db_agent_no_risk)
    db_session.commit()

    loaded_agent = await service.get_agent(agent_id)
    assert loaded_agent is not None
    # The service's _db_to_pydantic creates default AgentRiskConfig if json string is None or "{}".
    # Default values from AgentRiskConfig model itself are used.
    default_values = AgentRiskConfig() # Gets Pydantic defaults
    assert loaded_agent.risk_config.max_capital_allocation_usd == default_values.max_capital_allocation_usd
    assert loaded_agent.risk_config.risk_per_trade_percentage == default_values.risk_per_trade_percentage


# Keep other tests like delete, start, stop, get_child_agents, status, heartbeat as they are generally compatible.
# The main change was ensuring risk_config is part of the data flow and testing its specific (de)serialization.

@pytest.mark.asyncio
async def test_delete_agent(service: AgentManagementService): # Already compatible
    created_agent = await service.create_agent(create_sample_agent_input("To Delete DB"))
    agent_id = created_agent.agent_id
    assert await service.get_agent(agent_id) is not None
    deleted = await service.delete_agent(agent_id)
    assert deleted is True
    assert await service.get_agent(agent_id) is None
    assert await service.get_agent_status(agent_id) is None

@pytest.mark.asyncio
async def test_start_agent(service: AgentManagementService, db_session: Session): # Already compatible
    created_agent = await service.create_agent(create_sample_agent_input("Startable DB Agent"))
    agent_id = created_agent.agent_id
    assert not created_agent.is_active
    start_status = await service.start_agent(agent_id)
    assert start_status.status == "running"
    db_record = db_session.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
    assert db_record is not None
    assert db_record.is_active is True

@pytest.mark.asyncio
async def test_stop_agent(service: AgentManagementService, db_session: Session): # Already compatible
    created_agent = await service.create_agent(create_sample_agent_input("Stoppable DB Agent"))
    agent_id = created_agent.agent_id
    await service.start_agent(agent_id)
    stop_status = await service.stop_agent(agent_id)
    assert stop_status.status == "stopped"
    db_record = db_session.query(AgentConfigDB).filter(AgentConfigDB.agent_id == agent_id).first()
    assert db_record is not None
    assert db_record.is_active is False

@pytest.mark.asyncio
async def test_get_child_agents(service: AgentManagementService): # Already compatible
    parent_agent_obj = await service.create_agent(create_sample_agent_input(name="ActualParent"))
    actual_parent_id = parent_agent_obj.agent_id
    child1_input = create_sample_agent_input(name="ChildDB1", parent_id=actual_parent_id)
    await service.create_agent(child1_input)
    child2_input = create_sample_agent_input(name="ChildDB2", parent_id=actual_parent_id)
    await service.create_agent(child2_input)
    await service.create_agent(create_sample_agent_input(name="UnrelatedDBAgent"))
    child_agents = await service.get_child_agents(actual_parent_id)
    assert len(child_agents) == 2
    child_names = {agent.name for agent in child_agents}
    assert "ChildDB1" in child_names
    assert "ChildDB2" in child_names

@pytest.mark.asyncio
async def test_load_existing_statuses_from_db(service: AgentManagementService, db_session: Session): # Already compatible
    agent1_id = str(uuid.uuid4())
    db_agent1 = AgentConfigDB(agent_id=agent1_id, name="DB Agent 1", is_active=True, strategy_config_json="{}", operational_parameters_json="{}", risk_config_json="{}")
    agent2_id = str(uuid.uuid4())
    db_agent2 = AgentConfigDB(agent_id=agent2_id, name="DB Agent 2", is_active=False, strategy_config_json="{}", operational_parameters_json="{}", risk_config_json="{}")
    db_session.add_all([db_agent1, db_agent2])
    db_session.commit()
    await service._load_existing_statuses_from_db()
    status1 = service._agent_statuses.get(agent1_id)
    assert status1 is not None
    assert status1.status == "stopped"
    status2 = service._agent_statuses.get(agent2_id)
    assert status2 is not None
    assert status2.status == "stopped"

@pytest.mark.asyncio
async def test_get_agent_status_db_check(service: AgentManagementService, db_session: Session): # Already compatible
    agent_id = str(uuid.uuid4())
    risk_config_for_db = AgentRiskConfig(max_capital_allocation_usd=100, risk_per_trade_percentage=0.01)
    db_agent = AgentConfigDB(agent_id=agent_id, name="DB Status Test", is_active=True, strategy_config_json="{}", operational_parameters_json="{}", risk_config_json=risk_config_for_db.model_dump_json())
    db_session.add(db_agent)
    db_session.commit()
    status = await service.get_agent_status(agent_id)
    assert status is not None
    assert status.status == "running"
    assert "Status initialized from DB is_active field" in status.message #type: ignore

@pytest.mark.asyncio
async def test_update_agent_heartbeat_db(service: AgentManagementService): # Already compatible
    created_agent = await service.create_agent(create_sample_agent_input("Heartbeat DB Agent"))
    agent_id = created_agent.agent_id
    await service.start_agent(agent_id)
    initial_status = await service.get_agent_status(agent_id)
    assert initial_status is not None
    initial_heartbeat = initial_status.last_heartbeat
    await asyncio.sleep(0.01)
    result = await service.update_agent_heartbeat(agent_id)
    assert result is True
    updated_status = await service.get_agent_status(agent_id)
    assert updated_status is not None
    assert updated_status.last_heartbeat > initial_heartbeat
    assert updated_status.status == "running"

