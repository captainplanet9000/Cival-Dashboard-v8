import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime, timezone, date # Added date
from typing import List, Dict, Any, Optional

# Models and Services to test/mock
from python_ai_services.services.strategy_config_service import (
    StrategyConfigService,
    StrategyConfigNotFoundError,
    StrategyConfigServiceError,
    StrategyConfigCreationError,
    StrategyConfigUpdateError
)
from python_ai_services.models.strategy_models import (
    StrategyConfig,
    DarvasBoxParams, # Example for parameters
    StrategyTimeframe,
    PerformanceMetrics, # For mocking get_latest_performance_metrics
    TradeStats, # For PerformanceMetrics
    StrategyPerformanceTeaser
)
# from supabase import Client as SupabaseClient # For type hinting mock

# --- Fixtures ---
@pytest_asyncio.fixture
async def mock_supabase_client_scs(): # scs for StrategyConfigService tests
    client = MagicMock()
    # Setup mock chains for typical Supabase calls used by StrategyConfigService
    client.table.return_value.insert.return_value.select.return_value.execute = AsyncMock()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute = AsyncMock()
    client.table.return_value.update.return_value.eq.return_value.eq.return_value.select.return_value.execute = AsyncMock()
    client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute = AsyncMock()
    # For get_latest_performance_metrics call within get_all_user_strategies_with_performance_teasers
    # This chain is: .table("strategy_results").select("*").eq("strategy_id",...).order("generated_at", desc=True).limit(1).maybe_single().execute()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.maybe_single.return_value.execute = AsyncMock()
    return client

@pytest_asyncio.fixture
async def strategy_config_service_instance(mock_supabase_client_scs: MagicMock):
    return StrategyConfigService(supabase_client=mock_supabase_client_scs)

# --- Sample Data ---
def sample_strategy_config_data(user_id: uuid.UUID, strategy_id: Optional[uuid.UUID] = None, name_suffix: str = "") -> Dict:
    # This returns a Dict, simulating data from DB or for Pydantic model creation
    sid = strategy_id or uuid.uuid4()
    return {
        "strategy_id": str(sid), # DB usually returns string UUIDs
        "user_id": str(user_id),
        "strategy_name": f"Test Darvas{name_suffix}",
        "strategy_type": "DarvasBox",
        "description": "Test Darvas Desc",
        "symbols": ["AAPL", "MSFT"],
        "timeframe": StrategyTimeframe("1h").value, # Ensure it's the string value '1h'
        "parameters": DarvasBoxParams().model_dump(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

def sample_performance_metrics_data(strategy_id: uuid.UUID) -> Dict:
    # Returns Dict simulating data from DB for PerformanceMetrics model
    return {
        "strategy_id": str(strategy_id),
        "backtest_id": str(uuid.uuid4()), # Optional, add for completeness
        "live_trading_session_id": None,  # Optional
        "start_date": datetime(2023,1,1, tzinfo=timezone.utc).isoformat(),
        "end_date": datetime(2023,1,31, tzinfo=timezone.utc).isoformat(),
        "initial_capital": 100000.0,
        "final_capital": 105000.0,
        "net_profit": 5000.0,
        "net_profit_percentage": 5.0,
        "max_drawdown_percentage": 2.5,
        "sharpe_ratio": 1.5,
        "sortino_ratio": 2.0,
        "cagr_percentage": None, # Optional
        "volatility_percentage": None, # Optional
        "trade_stats": TradeStats(total_trades=10, winning_trades=7, losing_trades=3, win_rate_percentage=70.0).model_dump(),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

# --- Tests for CRUD operations ---

@pytest.mark.asyncio
async def test_create_strategy_config(strategy_config_service_instance: StrategyConfigService, mock_supabase_client_scs: MagicMock):
    user_id = uuid.uuid4()
    # Create a Pydantic model instance for the input `config_data`
    raw_data_for_model = sample_strategy_config_data(user_id=user_id, name_suffix="_create")
    # Remove fields that StrategyConfig doesn't expect on creation if they are DB-generated (like user_id from DB)
    # StrategyConfig Pydantic model should define what it expects.
    # The service method adds user_id to the record_to_insert.
    # For this test, config_model is the input to the service.
    config_model_input_data = {k: v for k, v in raw_data_for_model.items() if k not in ['user_id', 'created_at', 'updated_at', 'strategy_id']}
    config_model_input_data['parameters'] = DarvasBoxParams(**config_model_input_data['parameters']) # Ensure sub-model
    config_model = StrategyConfig(**config_model_input_data)

    # This is what the DB operation would return (includes strategy_id, user_id, timestamps)
    mock_db_return_data = {
        **config_model.model_dump(mode='json'), # Serializes sub-models like parameters
        "strategy_id": str(uuid.uuid4()), # DB generates this
        "user_id": str(user_id),          # Service adds this before insert
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    mock_supabase_client_scs.table.return_value.insert.return_value.select.return_value.execute.return_value = MagicMock(data=[mock_db_return_data], error=None)

    created_config = await strategy_config_service_instance.create_strategy_config(user_id, config_model)

    assert isinstance(created_config, StrategyConfig)
    assert created_config.strategy_name == config_model.strategy_name
    assert created_config.user_id == user_id # Check if service correctly parses user_id from return

    insert_payload = mock_supabase_client_scs.table.return_value.insert.call_args[0][0]
    assert insert_payload["user_id"] == str(user_id)

@pytest.mark.asyncio
async def test_get_strategy_config_found(strategy_config_service_instance: StrategyConfigService, mock_supabase_client_scs: MagicMock):
    user_id = uuid.uuid4()
    strategy_id = uuid.uuid4()
    mock_data = sample_strategy_config_data(user_id, strategy_id)
    # Ensure parameters is a dict for Pydantic parsing if StrategyConfig expects specific sub-model
    mock_data['parameters'] = DarvasBoxParams(**mock_data['parameters']).model_dump()

    mock_supabase_client_scs.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=mock_data, error=None)

    config = await strategy_config_service_instance.get_strategy_config(strategy_id, user_id)

    assert config is not None
    assert config.strategy_id == strategy_id
    assert config.user_id == user_id

@pytest.mark.asyncio
async def test_get_strategy_config_not_found(strategy_config_service_instance: StrategyConfigService, mock_supabase_client_scs: MagicMock):
    mock_supabase_client_scs.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None, error=None)
    config = await strategy_config_service_instance.get_strategy_config(uuid.uuid4(), uuid.uuid4())
    assert config is None

@pytest.mark.asyncio
async def test_get_strategy_configs_by_user(strategy_config_service_instance: StrategyConfigService, mock_supabase_client_scs: MagicMock):
    user_id = uuid.uuid4()
    mock_data_list = [
        sample_strategy_config_data(user_id, name_suffix="_1"),
        sample_strategy_config_data(user_id, name_suffix="_2")
    ]
    for item in mock_data_list: # Ensure sub-models are dicts for Pydantic parsing from mock DB
        item['parameters'] = DarvasBoxParams(**item['parameters']).model_dump()

    mock_supabase_client_scs.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=mock_data_list, error=None)

    configs = await strategy_config_service_instance.get_strategy_configs_by_user(user_id)
    assert len(configs) == 2
    assert configs[0].strategy_name.endswith("_1")
    assert configs[0].user_id == user_id

@pytest.mark.asyncio
async def test_update_strategy_config(strategy_config_service_instance: StrategyConfigService, mock_supabase_client_scs: MagicMock):
    user_id = uuid.uuid4()
    strategy_id = uuid.uuid4()
    update_payload = {"description": "Updated Description", "is_active": False} # This is Dict[str, Any]

    existing_config_data_dict = sample_strategy_config_data(user_id, strategy_id, name_suffix="_orig_for_update")
    existing_config_data_dict['parameters'] = DarvasBoxParams(**existing_config_data_dict['parameters']).model_dump()

    # Mock for get_strategy_config (ownership check)
    mock_get_execute = mock_supabase_client_scs.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute
    mock_get_execute.return_value = MagicMock(data=existing_config_data_dict, error=None)

    # Mock for update call
    # DB returns the full updated record
    updated_db_data = {**existing_config_data_dict, **update_payload, "updated_at": datetime.now(timezone.utc).isoformat()}
    mock_update_execute = mock_supabase_client_scs.table.return_value.update.return_value.eq.return_value.eq.return_value.select.return_value.execute
    mock_update_execute.return_value = MagicMock(data=[updated_db_data], error=None)

    updated_config = await strategy_config_service_instance.update_strategy_config(strategy_id, user_id, update_payload)

    assert updated_config.description == "Updated Description"
    assert updated_config.is_active is False
    update_call_args = mock_supabase_client_scs.table.return_value.update.call_args[0][0]
    assert "updated_at" in update_call_args
    assert update_call_args["description"] == "Updated Description"

@pytest.mark.asyncio
async def test_delete_strategy_config(strategy_config_service_instance: StrategyConfigService, mock_supabase_client_scs: MagicMock):
    user_id = uuid.uuid4()
    strategy_id = uuid.uuid4()
    existing_config_data = sample_strategy_config_data(user_id, strategy_id, name_suffix="_to_delete")
    existing_config_data['parameters'] = DarvasBoxParams(**existing_config_data['parameters']).model_dump()

    mock_get_execute = mock_supabase_client_scs.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute
    mock_get_execute.return_value = MagicMock(data=existing_config_data, error=None)

    mock_delete_execute = mock_supabase_client_scs.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute
    mock_delete_execute.return_value = MagicMock(error=None)

    await strategy_config_service_instance.delete_strategy_config(strategy_id, user_id)
    mock_delete_execute.assert_called_once()


# --- Tests for get_all_user_strategies_with_performance_teasers ---

@pytest.mark.asyncio
async def test_get_all_user_strategies_with_performance_teasers_success(strategy_config_service_instance: StrategyConfigService, mock_supabase_client_scs: MagicMock):
    user_id = uuid.uuid4()
    strat_id_1 = uuid.uuid4()
    strat_id_2 = uuid.uuid4()

    mock_configs_data_raw = [
        sample_strategy_config_data(user_id, strat_id_1, name_suffix="_s1"),
        sample_strategy_config_data(user_id, strat_id_2, name_suffix="_s2")
    ]
    # Ensure parameters are dicts for Pydantic parsing within the service if needed
    for item in mock_configs_data_raw:
        item['parameters'] = DarvasBoxParams(**item['parameters']).model_dump()

    mock_configs_pydantic = [StrategyConfig(**d) for d in mock_configs_data_raw]

    # Patch the service's own method for this test
    strategy_config_service_instance.get_strategy_configs_by_user = AsyncMock(return_value=mock_configs_pydantic)

    metrics_s1_raw = sample_performance_metrics_data(strat_id_1)
    metrics_s1_pydantic = PerformanceMetrics(**metrics_s1_raw)

    async def mock_get_latest_perf(strategy_id_arg, user_id_arg): # Matches service method signature
        if strategy_id_arg == strat_id_1:
            return metrics_s1_pydantic
        if strategy_id_arg == strat_id_2:
            return None # Simulate no metrics for strat_id_2
        return None
    strategy_config_service_instance.get_latest_performance_metrics = AsyncMock(side_effect=mock_get_latest_perf)

    teasers = await strategy_config_service_instance.get_all_user_strategies_with_performance_teasers(user_id)

    assert len(teasers) == 2
    teaser1 = next(t for t in teasers if t.strategy_id == strat_id_1)
    teaser2 = next(t for t in teasers if t.strategy_id == strat_id_2)

    assert teaser1.strategy_name.endswith("_s1")
    assert teaser1.latest_net_profit_percentage == metrics_s1_pydantic.net_profit_percentage
    assert teaser1.latest_sharpe_ratio == metrics_s1_pydantic.sharpe_ratio
    assert teaser1.total_trades_from_latest_metrics == metrics_s1_pydantic.trade_stats.total_trades
    assert teaser1.symbols == mock_configs_pydantic[0].symbols
    assert teaser1.timeframe == mock_configs_pydantic[0].timeframe


    assert teaser2.strategy_name.endswith("_s2")
    assert teaser2.latest_net_profit_percentage is None
    assert teaser2.latest_sharpe_ratio is None
    assert teaser2.total_trades_from_latest_metrics is None

    assert strategy_config_service_instance.get_strategy_configs_by_user.call_count == 1
    assert strategy_config_service_instance.get_latest_performance_metrics.call_count == 2


@pytest.mark.asyncio
async def test_get_all_user_strategies_with_performance_teasers_no_strategies(strategy_config_service_instance: StrategyConfigService):
    user_id = uuid.uuid4()
    strategy_config_service_instance.get_strategy_configs_by_user = AsyncMock(return_value=[])
    strategy_config_service_instance.get_latest_performance_metrics = AsyncMock()

    teasers = await strategy_config_service_instance.get_all_user_strategies_with_performance_teasers(user_id)

    assert len(teasers) == 0
    strategy_config_service_instance.get_latest_performance_metrics.assert_not_called()

