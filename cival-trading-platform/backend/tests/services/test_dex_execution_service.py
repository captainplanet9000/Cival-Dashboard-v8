import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock
from decimal import Decimal

from web3 import Web3
from web3.exceptions import ContractLogicError, TransactionNotFound
from eth_account.signers.local import LocalAccount

# Module to test
from python_ai_services.services.dex_execution_service import DEXExecutionService, DEXExecutionServiceError

# Default valid parameters for initialization
DEFAULT_WALLET_ADDRESS = "0x1234567890123456789012345678901234567890"
DEFAULT_PRIVATE_KEY = "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
DEFAULT_RPC_URL = "http://localhost:8545"
DEFAULT_ROUTER_ADDRESS = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D" # Uniswap V2 Router for example
DEFAULT_CHAIN_ID = 1
DEFAULT_WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

@pytest.fixture
def mock_web3_provider():
    mock = MagicMock(spec=Web3)
    # Mock connection
    mock.is_connected = MagicMock(return_value=True)
    # Mock eth module and its methods
    mock.eth = MagicMock()
    mock.eth.contract = MagicMock() # This will be called to create contract instances
    # For _run_sync_web3_call, the direct functions on eth need to be AsyncMock if awaited directly
    # or regular MagicMock if they are passed as callables.
    # Based on DEXExecutionService, these are wrapped, so MagicMock is fine for the functions themselves.
    mock.eth.get_transaction_count = MagicMock(return_value=1)
    mock.eth.gas_price = MagicMock(return_value=Web3.to_wei(50, 'gwei'))
    mock.eth.send_raw_transaction = MagicMock(return_value=b'tx_hash_bytes')
    # wait_for_transaction_receipt needs to be a callable that returns a dict
    mock.eth.wait_for_transaction_receipt = MagicMock(return_value={"status": 1, "transactionHash": b"tx_hash_bytes", "logs": []})

    # Mock middleware
    mock.middleware_onion = MagicMock()
    mock.middleware_onion.inject = MagicMock()
    # Mock to_checksum_address (it's a static/class method on Web3 often)
    Web3.to_checksum_address = MagicMock(side_effect=lambda x: x) # Pass through
    return mock

@pytest.fixture
def mock_account():
    mock = MagicMock(spec=LocalAccount)
    mock.address = DEFAULT_WALLET_ADDRESS
    mock.sign_transaction = MagicMock(return_value=MagicMock(rawTransaction=b'signed_tx_bytes'))
    return mock

@pytest.fixture
@patch('python_ai_services.services.dex_execution_service.Web3', new_callable=MagicMock)
@patch('python_ai_services.services.dex_execution_service.Account.from_key')
def dex_service(mock_from_key, mock_web3_constructor, mock_web3_provider, mock_account):
    mock_web3_constructor.return_value = mock_web3_provider
    mock_from_key.return_value = mock_account

    # Mock the contract instances that would be created in __init__ or _get_erc20_contract
    mock_router_contract_instance = MagicMock()
    mock_erc20_contract_instance = MagicMock()

    # Configure mock_web3_provider.eth.contract to return the appropriate mock contract instance
    def contract_side_effect(address, abi):
        if address == Web3.to_checksum_address(DEFAULT_ROUTER_ADDRESS):
            return mock_router_contract_instance
        return mock_erc20_contract_instance # For any other address, return the erc20 mock

    mock_web3_provider.eth.contract.side_effect = contract_side_effect

    service = DEXExecutionService(
        wallet_address=DEFAULT_WALLET_ADDRESS,
        private_key=DEFAULT_PRIVATE_KEY,
        rpc_url=DEFAULT_RPC_URL,
        router_address=DEFAULT_ROUTER_ADDRESS,
        chain_id=DEFAULT_CHAIN_ID,
        weth_address=DEFAULT_WETH_ADDRESS
    )
    # Ensure service instances are the mocks
    service.w3 = mock_web3_provider
    service.account = mock_account
    # These are now critical for tests to interact with the "contracts"
    service.router_contract = mock_router_contract_instance
    # service._get_erc20_contract will use the side_effect configured above
    return service

# --- __init__ Tests ---
def test_dex_service_initialization_success(dex_service, mock_web3_provider, mock_account):
    assert dex_service.w3 == mock_web3_provider
    assert dex_service.account == mock_account
    assert dex_service.wallet_address_cs == DEFAULT_WALLET_ADDRESS # Assuming checksum mock passes through
    assert dex_service.router_address_cs == DEFAULT_ROUTER_ADDRESS
    assert dex_service.chain_id == DEFAULT_CHAIN_ID
    mock_web3_provider.middleware_onion.inject.assert_not_called()

@patch('python_ai_services.services.dex_execution_service.Web3')
@patch('python_ai_services.services.dex_execution_service.Account.from_key')
def test_dex_service_initialization_poa_middleware_injected(mock_from_key, mock_web3_constructor):
    mock_w3_instance = MagicMock()
    mock_w3_instance.is_connected.return_value = True
    mock_w3_instance.middleware_onion = MagicMock()
    mock_w3_instance.middleware_onion.inject = MagicMock()
    mock_web3_constructor.return_value = mock_w3_instance
    mock_from_key.return_value = MagicMock(address=DEFAULT_WALLET_ADDRESS)
    Web3.to_checksum_address = MagicMock(side_effect=lambda x: x)


    DEXExecutionService(
        wallet_address=DEFAULT_WALLET_ADDRESS, private_key="pk", rpc_url="http://goerli-rpc.com",
        router_address=DEFAULT_ROUTER_ADDRESS, chain_id=5
    )
    mock_w3_instance.middleware_onion.inject.assert_called_once()

@patch('python_ai_services.services.dex_execution_service.Web3')
def test_dex_service_initialization_connection_error(mock_web3_constructor):
    mock_w3_instance = MagicMock()
    mock_w3_instance.is_connected.return_value = False
    mock_web3_constructor.return_value = mock_w3_instance
    Web3.to_checksum_address = MagicMock(side_effect=lambda x: x)
    with pytest.raises(DEXExecutionServiceError, match="Failed to connect to Web3 RPC"):
        DEXExecutionService(
            wallet_address=DEFAULT_WALLET_ADDRESS, private_key="pk", rpc_url="rpc",
            router_address="router", chain_id=1
        )

@patch('python_ai_services.services.dex_execution_service.Web3')
@patch('python_ai_services.services.dex_execution_service.Account.from_key')
def test_dex_service_wallet_address_mismatch_warning(mock_from_key, mock_web3_constructor, caplog):
    mock_w3_instance = MagicMock()
    mock_w3_instance.is_connected.return_value = True
    mock_web3_constructor.return_value = mock_w3_instance
    Web3.to_checksum_address = MagicMock(side_effect=lambda x: x)

    derived_address = "0xDerivedAddress"
    mock_account_instance = MagicMock(address=derived_address)
    mock_from_key.return_value = mock_account_instance

    service = DEXExecutionService(
        wallet_address="0xProvidedButDifferentAddress", private_key="pk", rpc_url="rpc",
        router_address="router", chain_id=1
    )
    assert service.wallet_address_cs == derived_address
    assert "Wallet address mismatch" in caplog.text


# --- get_token_balance Tests ---
@pytest.mark.asyncio
async def test_get_token_balance_success(dex_service):
    mock_token_contract = dex_service.w3.eth.contract.side_effect(address="0xTokenAddress", abi=None) # Get the mock erc20 instance

    # Configure return values for the mocked contract's functions
    # The functions themselves are MagicMocks, their `call` method needs to be an AsyncMock for `await`
    balance_func_mock = MagicMock()
    balance_func_mock.call = AsyncMock(return_value=1000 * (10**18))
    mock_token_contract.functions.balanceOf = MagicMock(return_value=balance_func_mock)

    decimals_func_mock = MagicMock()
    decimals_func_mock.call = AsyncMock(return_value=18)
    mock_token_contract.functions.decimals = MagicMock(return_value=decimals_func_mock)

    balance = await dex_service.get_token_balance("0xTokenAddress")
    assert balance == Decimal("1000.0")
    dex_service.w3.eth.contract.assert_any_call(address="0xTokenAddress", abi=dex_service.ERC20_ABI_SNIPPET)


@pytest.mark.asyncio
async def test_get_token_balance_failure(dex_service, caplog):
    mock_token_contract = dex_service.w3.eth.contract.side_effect(address="0xTokenAddress", abi=None)

    balance_func_mock = MagicMock()
    balance_func_mock.call = AsyncMock(side_effect=Exception("RPC Error"))
    mock_token_contract.functions.balanceOf = MagicMock(return_value=balance_func_mock)

    decimals_func_mock = MagicMock()
    decimals_func_mock.call = AsyncMock(return_value=18) # Assume decimals call succeeds or is not reached
    mock_token_contract.functions.decimals = MagicMock(return_value=decimals_func_mock)

    balance = await dex_service.get_token_balance("0xTokenAddress")
    assert balance is None
    assert "Error getting balance for 0xTokenAddress: RPC Error" in caplog.text

# --- _approve_token Tests ---
@pytest.mark.asyncio
async def test_approve_token_sufficient_allowance(dex_service, caplog):
    # Mock _get_allowance to return a high value
    dex_service._get_allowance = AsyncMock(return_value=Web3.to_wei(1000, 'ether'))

    approved = await dex_service._approve_token("0xToken", "0xSpender", Web3.to_wei(500, 'ether'))
    assert approved is True
    assert "Sufficient allowance" in caplog.text
    # Ensure send_raw_transaction was NOT called
    dex_service.w3.eth.send_raw_transaction.assert_not_called()


@pytest.mark.asyncio
async def test_approve_token_approval_needed_success(dex_service):
    dex_service._get_allowance = AsyncMock(return_value=Web3.to_wei(10, 'ether')) # Insufficient

    # Mock the contract interaction for approve tx
    mock_token_contract = dex_service.w3.eth.contract.side_effect(address="0xToken", abi=None)
    approve_func_mock = MagicMock()
    approve_func_mock.build_transaction = MagicMock(return_value={'gas': 200000, 'gasPrice': Web3.to_wei(50, 'gwei')}) # Dummy tx dict
    mock_token_contract.functions.approve = MagicMock(return_value=approve_func_mock)

    dex_service.w3.eth.wait_for_transaction_receipt = AsyncMock(return_value={"status": 1, "transactionHash": b"tx_hash_bytes"})

    approved = await dex_service._approve_token("0xToken", "0xSpender", Web3.to_wei(100, 'ether'))
    assert approved is True
    dex_service.w3.eth.send_raw_transaction.assert_called_once()

@pytest.mark.asyncio
async def test_approve_token_approval_needed_tx_failed(dex_service, caplog):
    dex_service._get_allowance = AsyncMock(return_value=Web3.to_wei(10, 'ether'))
    mock_token_contract = dex_service.w3.eth.contract.side_effect(address="0xToken", abi=None)
    approve_func_mock = MagicMock()
    approve_func_mock.build_transaction = MagicMock(return_value={})
    mock_token_contract.functions.approve = MagicMock(return_value=approve_func_mock)
    dex_service.w3.eth.wait_for_transaction_receipt = AsyncMock(return_value={"status": 0, "transactionHash": b"tx_hash_bytes"})

    approved = await dex_service._approve_token("0xToken", "0xSpender", Web3.to_wei(100, 'ether'))
    assert approved is False
    assert "Approval transaction failed" in caplog.text

@pytest.mark.asyncio
async def test_approve_token_approval_exception(dex_service, caplog):
    dex_service._get_allowance = AsyncMock(return_value=Web3.to_wei(10, 'ether'))
    mock_token_contract = dex_service.w3.eth.contract.side_effect(address="0xToken", abi=None)
    approve_func_mock = MagicMock()
    # Simulate error during transaction building or sending
    approve_func_mock.build_transaction = MagicMock(side_effect=Exception("Build Error"))
    mock_token_contract.functions.approve = MagicMock(return_value=approve_func_mock)

    approved = await dex_service._approve_token("0xToken", "0xSpender", Web3.to_wei(100, 'ether'))
    assert approved is False
    assert "Error during token approval" in caplog.text
    assert "Build Error" in caplog.text


# --- place_swap_order Tests ---
TOKEN_IN_ADDR = DEFAULT_WETH_ADDRESS
TOKEN_OUT_ADDR = "0xDA0xTOKEN000000000000000000000000000000001"
AMOUNT_IN_WEI = Web3.to_wei(1, 'ether')
MIN_AMOUNT_OUT_WEI = Web3.to_wei(2000, 'ether')

@pytest.mark.asyncio
async def test_place_swap_order_native_eth_success(dex_service):
    # Router contract's exactInputSingle function mock
    exact_input_single_mock = MagicMock()
    exact_input_single_mock.build_transaction = MagicMock(return_value={'gas': 300000, 'gasPrice': Web3.to_wei(50, 'gwei'), 'value': AMOUNT_IN_WEI})
    dex_service.router_contract.functions.exactInputSingle = MagicMock(return_value=exact_input_single_mock)

    dex_service.w3.eth.wait_for_transaction_receipt = AsyncMock(
        return_value={"status": 1, "transactionHash": b"tx_hash_bytes", "logs": []}
    )
    dex_service._approve_token = AsyncMock()

    result = await dex_service.place_swap_order(
        token_in_address=TOKEN_IN_ADDR,
        token_out_address=TOKEN_OUT_ADDR,
        amount_in_wei=AMOUNT_IN_WEI,
        min_amount_out_wei=MIN_AMOUNT_OUT_WEI
    )
    assert result["status"] == "success"
    assert result["tx_hash"] is not None
    dex_service._approve_token.assert_not_called()

    build_tx_call_args = exact_input_single_mock.build_transaction.call_args
    assert build_tx_call_args[0][0]['value'] == AMOUNT_IN_WEI


@pytest.mark.asyncio
async def test_place_swap_order_erc20_success_with_approval(dex_service):
    erc20_token_in = "0xERC20TOKENIN000000000000000000000000000001"
    dex_service._approve_token = AsyncMock(return_value=True)

    exact_input_single_mock = MagicMock()
    exact_input_single_mock.build_transaction = MagicMock(return_value={'gas': 300000, 'gasPrice': Web3.to_wei(50, 'gwei')}) # No 'value' for ERC20
    dex_service.router_contract.functions.exactInputSingle = MagicMock(return_value=exact_input_single_mock)

    dex_service.w3.eth.wait_for_transaction_receipt = AsyncMock(
        return_value={"status": 1, "transactionHash": b"tx_hash_bytes", "logs": []}
    )

    result = await dex_service.place_swap_order(
        token_in_address=erc20_token_in,
        token_out_address=TOKEN_OUT_ADDR,
        amount_in_wei=AMOUNT_IN_WEI,
        min_amount_out_wei=MIN_AMOUNT_OUT_WEI
    )
    assert result["status"] == "success"
    dex_service._approve_token.assert_called_once_with(
        erc20_token_in,
        dex_service.router_address_cs,
        AMOUNT_IN_WEI
    )
    build_tx_call_args = exact_input_single_mock.build_transaction.call_args
    assert 'value' not in build_tx_call_args[0][0] or build_tx_call_args[0][0]['value'] == 0


@pytest.mark.asyncio
async def test_place_swap_order_approval_failed(dex_service):
    erc20_token_in = "0xERC20TOKENIN000000000000000000000000000001"
    dex_service._approve_token = AsyncMock(return_value=False)

    result = await dex_service.place_swap_order(
        token_in_address=erc20_token_in,
        token_out_address=TOKEN_OUT_ADDR,
        amount_in_wei=AMOUNT_IN_WEI,
        min_amount_out_wei=MIN_AMOUNT_OUT_WEI
    )
    assert result["status"] == "failed"
    assert result["error"] == "Token approval failed"
    dex_service.w3.eth.send_raw_transaction.assert_not_called()

@pytest.mark.asyncio
async def test_place_swap_order_tx_reverted(dex_service):
    dex_service._approve_token = AsyncMock(return_value=True)
    exact_input_single_mock = MagicMock()
    exact_input_single_mock.build_transaction = MagicMock(return_value={})
    dex_service.router_contract.functions.exactInputSingle = MagicMock(return_value=exact_input_single_mock)

    mock_receipt = {"status": 0, "transactionHash": b"tx_hash_bytes", "logs": []}
    dex_service.w3.eth.wait_for_transaction_receipt = AsyncMock(return_value=mock_receipt)

    result = await dex_service.place_swap_order(
        token_in_address=TOKEN_IN_ADDR,
        token_out_address=TOKEN_OUT_ADDR,
        amount_in_wei=AMOUNT_IN_WEI,
        min_amount_out_wei=MIN_AMOUNT_OUT_WEI
    )
    assert result["status"] == "failed"
    assert result["error"] == "Transaction reverted"
    assert result["receipt"] == mock_receipt

@pytest.mark.asyncio
async def test_place_swap_order_contract_logic_error(dex_service):
    dex_service._approve_token = AsyncMock(return_value=True)
    exact_input_single_mock = MagicMock()
    exact_input_single_mock.build_transaction = MagicMock(
        side_effect=ContractLogicError("execution reverted: UniswapV2Router: INSUFFICIENT_OUTPUT_AMOUNT")
    )
    dex_service.router_contract.functions.exactInputSingle = MagicMock(return_value=exact_input_single_mock)

    result = await dex_service.place_swap_order(
        token_in_address=TOKEN_IN_ADDR,
        token_out_address=TOKEN_OUT_ADDR,
        amount_in_wei=AMOUNT_IN_WEI,
        min_amount_out_wei=MIN_AMOUNT_OUT_WEI
    )
    assert result["status"] == "failed"
    assert "Contract logic error" in result["error"]
    assert "INSUFFICIENT_OUTPUT_AMOUNT" in result["error"]

@pytest.mark.asyncio
async def test_place_swap_order_transaction_not_found(dex_service):
    dex_service._approve_token = AsyncMock(return_value=True)
    exact_input_single_mock = MagicMock()
    exact_input_single_mock.build_transaction = MagicMock(return_value={})
    dex_service.router_contract.functions.exactInputSingle = MagicMock(return_value=exact_input_single_mock)
    dex_service.w3.eth.wait_for_transaction_receipt = AsyncMock(side_effect=TransactionNotFound("Tx not found"))

    result = await dex_service.place_swap_order(
        token_in_address=TOKEN_IN_ADDR,
        token_out_address=TOKEN_OUT_ADDR,
        amount_in_wei=AMOUNT_IN_WEI,
        min_amount_out_wei=MIN_AMOUNT_OUT_WEI
    )
    assert result["status"] == "failed"
    assert "Transaction not found or timed out" in result["error"]

@pytest.mark.asyncio
async def test_place_swap_order_parses_amount_out_from_logs(dex_service):
    dex_service._approve_token = AsyncMock(return_value=True)

    exact_input_single_mock = MagicMock()
    exact_input_single_mock.build_transaction = MagicMock(return_value={})
    dex_service.router_contract.functions.exactInputSingle = MagicMock(return_value=exact_input_single_mock)

    event_signature_hex = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    # Ensure recipient_padded uses the correct DEFAULT_WALLET_ADDRESS from the fixture scope
    recipient_padded_hex = "0x000000000000000000000000" + DEFAULT_WALLET_ADDRESS[2:]
    actual_amount_out_wei = Web3.to_wei(2500, 'ether')

    mock_log_entry = {
        'address': TOKEN_OUT_ADDR, # Checksummed by fixture
        'topics': [
            bytes.fromhex(event_signature_hex[2:]),
            bytes.fromhex("000000000000000000000000" + DEFAULT_ROUTER_ADDRESS[2:]),
            bytes.fromhex(recipient_padded_hex[2:])
        ],
        'data': "0x" + actual_amount_out_wei.to_bytes(32, 'big').hex(),
        'blockNumber': 1, 'transactionHash': b'tx_hash', 'transactionIndex': 0,
        'blockHash': b'block_hash', 'logIndex': 0, 'removed': False
    }
    dex_service.w3.eth.wait_for_transaction_receipt = AsyncMock(
        return_value={"status": 1, "transactionHash": b"tx_hash_bytes", "logs": [mock_log_entry]}
    )

    result = await dex_service.place_swap_order(
        token_in_address=TOKEN_IN_ADDR,
        token_out_address=TOKEN_OUT_ADDR,
        amount_in_wei=AMOUNT_IN_WEI,
        min_amount_out_wei=MIN_AMOUNT_OUT_WEI
    )
    assert result["status"] == "success"
    assert result["amount_out_wei_actual"] == actual_amount_out_wei
    assert result["amount_out_wei_minimum_requested"] == MIN_AMOUNT_OUT_WEI

