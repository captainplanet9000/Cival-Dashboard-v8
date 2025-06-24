import os
from typing import Optional, Dict
# Correcting import path based on typical project structure if services are peers to core
# If agent_models is in a top-level 'models' dir and 'core' is a peer to 'services' and 'models'
# then it would be from ..models.agent_models import AgentConfigOutput
# Assuming 'python_ai_services' is the root package available in PYTHONPATH:
from python_ai_services.models.agent_models import AgentConfigOutput
from python_ai_services.services.hyperliquid_execution_service import HyperliquidExecutionService, HyperliquidExecutionServiceError
from python_ai_services.services.dex_execution_service import DEXExecutionService, DEXExecutionServiceError
from loguru import logger

def get_hyperliquid_execution_service_instance(
    agent_config: AgentConfigOutput
) -> Optional[HyperliquidExecutionService]:
    """
    Creates an instance of HyperliquidExecutionService based on agent configuration.
    Credentials (private key) are fetched from an environment variable specified in the config.
    """
    if agent_config.execution_provider != "hyperliquid" or not agent_config.hyperliquid_config:
        logger.debug(f"Agent {agent_config.agent_id} ({agent_config.name}) is not configured for Hyperliquid or lacks hyperliquid_config.")
        return None

    wallet_address = agent_config.hyperliquid_config.get("wallet_address")
    private_key_env_var = agent_config.hyperliquid_config.get("private_key_env_var_name")
    # Default to 'mainnet' if not specified in config
    network_mode_str = agent_config.hyperliquid_config.get("network_mode", "mainnet")


    if not wallet_address:
        logger.error(f"HL Factory: Agent {agent_config.agent_id}: Missing 'wallet_address' in hyperliquid_config.")
        return None
    if not private_key_env_var:
        logger.error(f"HL Factory: Agent {agent_config.agent_id}: Missing 'private_key_env_var_name' in hyperliquid_config.")
        return None

    private_key = os.getenv(private_key_env_var)
    if not private_key:
        logger.error(f"HL Factory: Agent {agent_config.agent_id}: Environment variable '{private_key_env_var}' for private key is not set or is empty.")
        return None

    if network_mode_str not in ["mainnet", "testnet"]:
        logger.warning(f"HL Factory: Invalid network_mode '{network_mode_str}' in hyperliquid_config for agent {agent_config.agent_id}. Defaulting to 'mainnet'.")
        network_mode_str = "mainnet"

    try:
        service_instance = HyperliquidExecutionService(
            wallet_address=wallet_address,
            private_key=private_key,
            network_mode=network_mode_str # type: ignore
        )
        logger.info(f"HL Factory: Successfully created HyperliquidExecutionService instance for agent {agent_config.agent_id} on {network_mode_str}.")
        return service_instance
    except HyperliquidExecutionServiceError as e:
        logger.error(f"HL Factory: Agent {agent_config.agent_id}: Failed to initialize HyperliquidExecutionService: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"HL Factory: Agent {agent_config.agent_id}: Unexpected error creating HyperliquidExecutionService: {e}", exc_info=True)
        return None

# Moved DEXExecutionService and DEXExecutionServiceError import to the top of the file in the prompt
# but if it's not there, it would need to be:
# from ..services.dex_execution_service import DEXExecutionService, DEXExecutionServiceError

def get_dex_execution_service_instance(
    agent_config: AgentConfigOutput
) -> Optional[DEXExecutionService]:
    """
    Creates an instance of DEXExecutionService based on agent configuration.
    Credentials (private key, RPC URL) are fetched from environment variables specified in dex_config.
    Other parameters like router address, WETH address, chain ID are taken directly from dex_config.
    """
    if agent_config.execution_provider != "dex" or not agent_config.dex_config:
        logger.debug(f"DEX Factory: Agent {agent_config.agent_id} ({agent_config.name}) is not 'dex' provider or lacks dex_config.")
        return None

    logger.info(f"DEX Factory: Attempting to create DEXExecutionService for agent {agent_config.agent_id}")

    required_keys = ["wallet_address", "private_key_env_var_name", "rpc_url_env_var_name", "dex_router_address", "default_chain_id"]
    for key in required_keys:
        if key not in agent_config.dex_config:
            logger.error(f"DEX Factory: Agent {agent_config.agent_id}: Missing required key '{key}' in dex_config.")
            return None

    wallet_address = agent_config.dex_config["wallet_address"]
    private_key_env_var = agent_config.dex_config["private_key_env_var_name"]
    rpc_url_env_var = agent_config.dex_config["rpc_url_env_var_name"]
    router_address = agent_config.dex_config["dex_router_address"]
    chain_id = int(agent_config.dex_config["default_chain_id"]) # Ensure int

    weth_address = agent_config.dex_config.get("weth_address") # Optional
    default_gas_limit = int(agent_config.dex_config.get("default_gas_limit", 300000)) # Optional with default

    private_key = os.getenv(private_key_env_var)
    rpc_url = os.getenv(rpc_url_env_var)

    if not private_key:
        logger.error(f"DEX Factory: Agent {agent_config.agent_id}: Env var '{private_key_env_var}' for DEX private key not set or empty.")
        return None
    if not rpc_url:
        logger.error(f"DEX Factory: Agent {agent_config.agent_id}: Env var '{rpc_url_env_var}' for RPC URL not set or empty.")
        return None

    try:
        service_instance = DEXExecutionService(
            wallet_address=str(wallet_address),
            private_key=private_key,
            rpc_url=rpc_url,
            router_address=str(router_address),
            chain_id=chain_id,
            weth_address=str(weth_address) if weth_address else None,
            default_gas_limit=default_gas_limit
        )
        logger.info(f"DEX Factory: Successfully created DEXExecutionService for agent {agent_config.agent_id} on chain ID {chain_id}.")
        return service_instance
    except DEXExecutionServiceError as e: # Catch specific error from DEX service init
        logger.error(f"DEX Factory: Agent {agent_config.agent_id}: Failed to initialize DEXExecutionService: {e}", exc_info=True)
        return None
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"DEX Factory: Agent {agent_config.agent_id}: Unexpected error creating DEXExecutionService: {e}", exc_info=True)
        return None
