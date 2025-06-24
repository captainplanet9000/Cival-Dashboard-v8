import pytest
from unittest.mock import patch, MagicMock
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from python_ai_services.core.factories import get_hyperliquid_execution_service_instance, get_dex_execution_service_instance
from python_ai_services.models.agent_models import AgentConfigOutput, AgentStrategyConfig, AgentRiskConfig, AgentConfigBase
from python_ai_services.services.hyperliquid_execution_service import HyperliquidExecutionService, HyperliquidExecutionServiceError
from python_ai_services.services.dex_execution_service import DEXExecutionService, DEXExecutionServiceError

# --- Helper to create AgentConfigOutput ---
# Using AgentConfigBase fields for simplicity in helper, then constructing AgentConfigOutput
def create_test_agent_config(
    agent_id: str,
    name: str,
    execution_provider: str,
    hyperliquid_config: Optional[Dict[str, str]] = None,
    dex_config: Optional[Dict[str, Any]] = None,
    user_id: str = "test_user",
    is_active: bool = True
) -> AgentConfigOutput:

    base_config = AgentConfigBase(
        name=name,
        description="Test agent " + name,
        strategy=AgentStrategyConfig(strategy_name="test_strat", parameters={}, watched_symbols=["TEST/USD"]),
        risk_config=AgentRiskConfig(
            max_capital_allocation_usd=1000.0,
            risk_per_trade_percentage=0.01,
            max_loss_per_trade_percentage_balance=0.02, # Ensure all required fields are present
            max_concurrent_open_trades=5,
            max_exposure_per_asset_usd=500.0
        ),
        execution_provider=execution_provider, # type: ignore
        hyperliquid_config=hyperliquid_config,
        dex_config=dex_config,
        agent_type="GenericAgent",
        parent_agent_id=None,
        operational_parameters={}
    )

    return AgentConfigOutput(
        **base_config.model_dump(),
        agent_id=agent_id,
        user_id=user_id,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_heartbeat=datetime.now(timezone.utc),
        message="Online"
    )

# --- Tests for get_hyperliquid_execution_service_instance ---

@patch.dict(os.environ, {"TEST_HL_PRIVKEY": "fake_private_key"})
@patch('python_ai_services.core.factories.HyperliquidExecutionService')
def test_get_hl_service_success(MockHLService: MagicMock):
    mock_hl_instance = MagicMock(spec=HyperliquidExecutionService)
    MockHLService.return_value = mock_hl_instance

    config = create_test_agent_config(
        agent_id="hl_agent_01", name="HL Test Agent", execution_provider="hyperliquid",
        hyperliquid_config={
            "wallet_address": "0x123",
            "private_key_env_var_name": "TEST_HL_PRIVKEY",
            "network_mode": "testnet"
        }
    )
    service = get_hyperliquid_execution_service_instance(config)
    assert service == mock_hl_instance
    MockHLService.assert_called_once_with(
        wallet_address="0x123", private_key="fake_private_key", network_mode="testnet"
    )

def test_get_hl_service_wrong_provider():
    config = create_test_agent_config("agent1", "Test", "dex")
    service = get_hyperliquid_execution_service_instance(config)
    assert service is None

def test_get_hl_service_missing_hl_config():
    config = create_test_agent_config("agent1", "Test", "hyperliquid", hyperliquid_config=None)
    service = get_hyperliquid_execution_service_instance(config)
    assert service is None

def test_get_hl_service_missing_wallet_address():
    config = create_test_agent_config(
        "hl_agent_02", "HL Test", "hyperliquid",
        hyperliquid_config={"private_key_env_var_name": "TEST_HL_PRIVKEY"}
    )
    service = get_hyperliquid_execution_service_instance(config)
    assert service is None

def test_get_hl_service_missing_privkey_env_var_name():
    config = create_test_agent_config(
        "hl_agent_03", "HL Test", "hyperliquid",
        hyperliquid_config={"wallet_address": "0x123"}
    )
    service = get_hyperliquid_execution_service_instance(config)
    assert service is None

@patch.dict(os.environ, {}, clear=True) # Ensure env var is not set
def test_get_hl_service_privkey_env_var_not_set():
    config = create_test_agent_config(
        "hl_agent_04", "HL Test", "hyperliquid",
        hyperliquid_config={
            "wallet_address": "0x123",
            "private_key_env_var_name": "UNSET_HL_PRIVKEY"
        }
    )
    service = get_hyperliquid_execution_service_instance(config)
    assert service is None

@patch.dict(os.environ, {"TEST_HL_PRIVKEY": "fake_private_key"})
@patch('python_ai_services.core.factories.HyperliquidExecutionService', side_effect=HyperliquidExecutionServiceError("Init error"))
def test_get_hl_service_init_fails(MockHLService: MagicMock):
    config = create_test_agent_config(
        "hl_agent_05", "HL Test", "hyperliquid",
        hyperliquid_config={
            "wallet_address": "0x123",
            "private_key_env_var_name": "TEST_HL_PRIVKEY"
        }
    )
    service = get_hyperliquid_execution_service_instance(config)
    assert service is None
    MockHLService.assert_called_once()


# --- Tests for get_dex_execution_service_instance ---

@patch.dict(os.environ, {"TEST_DEX_PRIVKEY": "fake_dex_key", "TEST_RPC_URL": "http://localhost:8545"})
@patch('python_ai_services.core.factories.DEXExecutionService')
def test_get_dex_service_success(MockDEXService: MagicMock):
    mock_dex_instance = MagicMock(spec=DEXExecutionService)
    MockDEXService.return_value = mock_dex_instance

    config = create_test_agent_config(
        "dex_agent_01", "DEX Test", "dex",
        dex_config={
            "wallet_address": "0xabc",
            "private_key_env_var_name": "TEST_DEX_PRIVKEY",
            "rpc_url_env_var_name": "TEST_RPC_URL",
            "dex_router_address": "0xrouter",
            "default_chain_id": 1,
            "weth_address": "0xweth",
            "default_gas_limit": 500000
        }
    )
    service = get_dex_execution_service_instance(config)
    assert service == mock_dex_instance
    MockDEXService.assert_called_once_with(
        wallet_address="0xabc", private_key="fake_dex_key", rpc_url="http://localhost:8545",
        router_address="0xrouter", chain_id=1, weth_address="0xweth", default_gas_limit=500000
    )

def test_get_dex_service_wrong_provider():
    config = create_test_agent_config("agent_dx", "Test", "hyperliquid")
    service = get_dex_execution_service_instance(config)
    assert service is None

def test_get_dex_service_missing_dex_config():
    config = create_test_agent_config("agent_dx1", "Test", "dex", dex_config=None)
    service = get_dex_execution_service_instance(config)
    assert service is None

@patch.dict(os.environ, {}, clear=True) # Start with a clean environment for this test
def test_get_dex_service_missing_privkey_env_var():
    config = create_test_agent_config(
        "dex_agent_02", "DEX Test", "dex",
        dex_config={
            "wallet_address": "0xabc", "private_key_env_var_name": "UNSET_DEX_KEY",
            "rpc_url_env_var_name": "TEST_RPC_URL", "dex_router_address": "0xrouter", "default_chain_id": 1
        }
    )
    # Mock only the RPC URL env var for this specific test case
    with patch.dict(os.environ, {"TEST_RPC_URL": "http://localhost:8545"}, clear=True):
        service = get_dex_execution_service_instance(config)
        assert service is None

@patch.dict(os.environ, {}, clear=True) # Start with a clean environment
def test_get_dex_service_missing_rpc_env_var():
    config = create_test_agent_config(
        "dex_agent_03", "DEX Test", "dex",
        dex_config={
            "wallet_address": "0xabc", "private_key_env_var_name": "TEST_DEX_PRIVKEY",
            "rpc_url_env_var_name": "UNSET_RPC_URL", "dex_router_address": "0xrouter", "default_chain_id": 1
        }
    )
    # Mock only the private key env var for this specific test case
    with patch.dict(os.environ, {"TEST_DEX_PRIVKEY": "fake_dex_key"}, clear=True):
        service = get_dex_execution_service_instance(config)
        assert service is None

@patch.dict(os.environ, {"TEST_DEX_PRIVKEY": "fake_dex_key", "TEST_RPC_URL": "http://localhost:8545"})
@patch('python_ai_services.core.factories.DEXExecutionService', side_effect=DEXExecutionServiceError("DEX Init error"))
def test_get_dex_service_init_fails(MockDEXService: MagicMock):
    config = create_test_agent_config(
        "dex_agent_04", "DEX Test", "dex",
        dex_config={
            "wallet_address": "0xabc", "private_key_env_var_name": "TEST_DEX_PRIVKEY",
            "rpc_url_env_var_name": "TEST_RPC_URL", "dex_router_address": "0xrouter", "default_chain_id": 1
        }
    )
    service = get_dex_execution_service_instance(config)
    assert service is None
    MockDEXService.assert_called_once()

def test_get_dex_service_missing_required_config_key():
    config = create_test_agent_config(
        "dex_agent_05", "DEX Test", "dex",
        dex_config={"wallet_address": "0xabc"} # Missing other required keys like private_key_env_var_name etc.
    )
    service = get_dex_execution_service_instance(config)
    assert service is None
