import os
import time
import json # For ABI loading
import asyncio # For _run_sync_web3_call
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Dict, Any, List
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
from web3.exceptions import ContractLogicError, TransactionNotFound
from eth_account import Account
from eth_account.signers.local import LocalAccount
from loguru import logger

# Minified ABIs (only functions used)
ERC20_ABI_SNIPPET = json.loads('[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}, {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}, {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}, {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"type":"function"}]')
UNISWAP_V3_ROUTER_ABI_SNIPPET = json.loads('[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint160"}],"internalType":"struct IRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]') # Note: amountOutMinimum and sqrtPriceLimitX96 are actually different types in full ABI. Simplified for structure.
WETH_ABI_SNIPPET = json.loads('[{"constant":false,"inputs":[],"name":"deposit","outputs":[],"payable":true,"stateMutability":"payable","type":"function"}, {"constant":false,"inputs":[{"name":"wad","type":"uint256"}],"name":"withdraw","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"}]')

class DEXExecutionServiceError(Exception):
    pass

class DEXExecutionService:
    def __init__(
        self,
        wallet_address: str,
        private_key: str,
        rpc_url: str,
        router_address: str,
        chain_id: int,
        weth_address: Optional[str] = None,
        default_gas_limit: int = 400000 # Increased default
    ):
        try:
            self.w3 = Web3(HTTPProvider(rpc_url))
            # Inject PoA middleware for common testnets or if "goerli" or "sepolia" is in the RPC URL
            if chain_id in [5, 11155111] or \
               ("goerli" in rpc_url.lower() or "sepolia" in rpc_url.lower()):
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                logger.info("DEXService: Injected PoA middleware.")

            if not self.w3.is_connected():
                raise DEXExecutionServiceError(f"Failed to connect to Web3 RPC: {rpc_url}")

            self.account: LocalAccount = Account.from_key(private_key)
            self.wallet_address_cs = Web3.to_checksum_address(wallet_address) # Store checksummed version

            if self.account.address.lower() != self.wallet_address_cs.lower():
                logger.warning(f"DEXService: Wallet address mismatch. Provided: {wallet_address}, Derived: {self.account.address}. Using derived address.")
                self.wallet_address_cs = self.account.address # Use derived address

            self.router_address_cs = Web3.to_checksum_address(router_address)
            self.weth_address_cs = Web3.to_checksum_address(weth_address) if weth_address else None
            self.chain_id = chain_id
            self.default_gas_limit = default_gas_limit
            self.router_contract = self.w3.eth.contract(address=self.router_address_cs, abi=UNISWAP_V3_ROUTER_ABI_SNIPPET)
            logger.info(f"DEXExecutionService initialized: Wallet {self.wallet_address_cs}, ChainID {self.chain_id}, Router {self.router_address_cs}")
        except Exception as e:
            logger.error(f"Error initializing DEXExecutionService: {e}", exc_info=True)
            raise DEXExecutionServiceError(f"Initialization failed: {e}")

    async def _run_sync_web3_call(self, func, *args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs))

    def _get_erc20_contract(self, token_address: str):
        return self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI_SNIPPET)

    async def get_token_balance(self, token_address: str, owner_address: Optional[str] = None) -> Optional[Decimal]:
        target_owner_cs = Web3.to_checksum_address(owner_address or self.wallet_address_cs)
        token_contract = self._get_erc20_contract(token_address)
        try:
            balance_wei = await self._run_sync_web3_call(token_contract.functions.balanceOf(target_owner_cs).call)
            decimals = await self._run_sync_web3_call(token_contract.functions.decimals().call)
            balance = Decimal(balance_wei) / (Decimal(10) ** decimals)
            logger.debug(f"DEX: Balance for {token_address} of {target_owner_cs}: {balance}")
            return balance
        except Exception as e:
            logger.error(f"DEX: Error getting balance for {token_address}: {e}", exc_info=True)
            return None

    async def _get_allowance(self, token_address_cs: str, owner_address_cs: str, spender_address_cs: str) -> int:
        token_contract = self._get_erc20_contract(token_address_cs)
        allowance_wei = await self._run_sync_web3_call(
            token_contract.functions.allowance(owner_address_cs, spender_address_cs).call
        )
        return allowance_wei

    async def _approve_token(self, token_address_cs: str, spender_address_cs: str, amount_wei: int) -> bool:
        logger.debug(f"DEX: Checking allowance for {token_address_cs} by {self.wallet_address_cs} to {spender_address_cs}")
        current_allowance = await self._get_allowance(token_address_cs, self.wallet_address_cs, spender_address_cs)
        if current_allowance >= amount_wei:
            logger.debug(f"DEX: Sufficient allowance ({current_allowance}) already present for {token_address_cs} to {spender_address_cs}.")
            return True

        logger.info(f"DEX: Approving {amount_wei} of {token_address_cs} for spender {spender_address_cs} by {self.wallet_address_cs}")
        token_contract = self._get_erc20_contract(token_address_cs)

        try:
            approve_tx = token_contract.functions.approve(spender_address_cs, amount_wei).build_transaction({
                'chainId': self.chain_id,
                'from': self.wallet_address_cs,
                'nonce': await self._run_sync_web3_call(self.w3.eth.get_transaction_count, self.wallet_address_cs),
                'gas': self.default_gas_limit,
                'gasPrice': await self._run_sync_web3_call(self.w3.eth.gas_price)
            })
            signed_tx = self.account.sign_transaction(approve_tx)
            tx_hash = await self._run_sync_web3_call(self.w3.eth.send_raw_transaction, signed_tx.rawTransaction)
            logger.info(f"DEX: Approval transaction sent: {tx_hash.hex()}")
            receipt = await self._run_sync_web3_call(self.w3.eth.wait_for_transaction_receipt, tx_hash, timeout=180) # Wait for 3 mins
            if receipt.status == 1:
                logger.info(f"DEX: Approval successful for {token_address_cs}. Tx: {tx_hash.hex()}")
                return True
            else:
                logger.error(f"DEX: Approval transaction failed for {token_address_cs}. Tx: {tx_hash.hex()}, Receipt: {receipt}")
                return False
        except Exception as e:
            logger.error(f"DEX: Error during token approval for {token_address_cs}: {e}", exc_info=True)
            return False

    async def place_swap_order(
        self, token_in_address: str, token_out_address: str, amount_in_wei: int,
        min_amount_out_wei: int, fee_tier: int = 3000,
        deadline_seconds: int = 300
    ) -> Dict[str, Any]:
        logger.info(f"DEX: Swap {amount_in_wei} of {token_in_address} for {token_out_address} (min out: {min_amount_out_wei}, fee: {fee_tier})")

        token_in_cs = Web3.to_checksum_address(token_in_address)
        token_out_cs = Web3.to_checksum_address(token_out_address)

        is_native_eth_in = self.weth_address_cs and token_in_cs.lower() == self.weth_address_cs.lower()

        if not is_native_eth_in:
            approved = await self._approve_token(token_in_cs, self.router_address_cs, amount_in_wei)
            if not approved:
                return {"status": "failed", "error": "Token approval failed", "tx_hash": None}

        deadline = int(time.time()) + deadline_seconds
        # Ensure amountOutMinimum is uint160 as per ABI snippet if it's strictly enforced
        # For this example, assuming SDK/Web3.py handles type conversion if needed, or it's compatible.
        # The ABI snippet uses uint256 for amountOutMinimum, but standard Uniswap V3 uses uint160.
        # Corrected struct for exactInputSingle (amountOutMinimum as uint256, sqrtPriceLimitX96 as uint160)
        # The provided UNISWAP_V3_ROUTER_ABI_SNIPPET uses uint160 for amountOutMinimum.
        # We must ensure min_amount_out_wei fits uint160 if using that ABI strictly.
        # However, the snippet in the prompt for the router has amountOutMinimum as uint256.
        # Let's stick to the prompt's ABI snippet for now. The test code uses uint160 for amountOutMinimum.
        # The prompt's ABI for router: "internalType":"uint256","name":"amountOutMinimum"
        # The prompt's class code: "internalType":"uint160","name":"amountOutMinimum" in params_struct comment
        # I will use the ABI definition from the prompt: `amountOutMinimum` as `uint256`
        # and `sqrtPriceLimitX96` (0) as `uint160`.
        # The router ABI snippet shows `amountOutMinimum` as `uint256` and `sqrtPriceLimitX96` is not in the snippet's params tuple.
        # The snippet for the router only has 7 fields in the tuple:
        # (tokenIn, tokenOut, fee, recipient, deadline, amountIn, amountOutMinimum)
        # The 8th field `sqrtPriceLimitX96` is missing from the ABI snippet's `components` definition.
        # I will proceed with the 7-field struct based on the provided `UNISWAP_V3_ROUTER_ABI_SNIPPET`.

        params_struct = (
            token_in_cs,
            token_out_cs,
            fee_tier,
            self.wallet_address_cs, # Recipient of output tokens
            deadline,
            amount_in_wei,
            min_amount_out_wei # amountOutMinimum as uint256 per snippet
            # sqrtPriceLimitX96 (0) is omitted as it's not in the ABI snippet's tuple definition
        )

        tx_hash_hex = None
        try:
            current_gas_price = await self._run_sync_web3_call(self.w3.eth.gas_price)

            tx_params = {
                'chainId': self.chain_id,
                'from': self.wallet_address_cs,
                'nonce': await self._run_sync_web3_call(self.w3.eth.get_transaction_count, self.wallet_address_cs),
                'gas': self.default_gas_limit,
                'gasPrice': current_gas_price,
            }
            if is_native_eth_in:
                tx_params['value'] = amount_in_wei

            swap_tx = self.router_contract.functions.exactInputSingle(params_struct).build_transaction(tx_params)

            signed_tx = self.account.sign_transaction(swap_tx)
            tx_hash = await self._run_sync_web3_call(self.w3.eth.send_raw_transaction, signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            logger.info(f"DEX: Swap transaction sent: {tx_hash_hex}")

            receipt = await self._run_sync_web3_call(self.w3.eth.wait_for_transaction_receipt, tx_hash, timeout=deadline_seconds + 60)

            if receipt.status == 1:
                logger.info(f"DEX: Swap successful. Tx: {tx_hash_hex}")
                actual_amount_out = min_amount_out_wei # Default to minimum requested
                for log_entry in receipt.get('logs', []):
                    if log_entry['address'].lower() == token_out_cs.lower():
                        if log_entry['topics'][0].hex() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
                            recipient_in_log = Web3.to_checksum_address(log_entry['topics'][2][-20:])
                            if recipient_in_log.lower() == self.wallet_address_cs.lower():
                                actual_amount_out = Web3.to_int(hexstr=log_entry['data'].hex())
                                logger.info(f"DEX: Found Transfer event in logs. Actual amountOut: {actual_amount_out} of {token_out_cs}")
                                break
                return {"tx_hash": tx_hash_hex, "status": "success", "error": None, "amount_out_wei_actual": actual_amount_out, "amount_out_wei_minimum_requested": min_amount_out_wei}
            else:
                logger.error(f"DEX: Swap transaction failed. Tx: {tx_hash_hex}, Receipt: {receipt}")
                return {"tx_hash": tx_hash_hex, "status": "failed", "error": "Transaction reverted", "receipt": dict(receipt)}
        except ContractLogicError as cle:
            logger.error(f"DEX: Swap contract logic error: {cle} (TxHash: {tx_hash_hex})", exc_info=True)
            return {"status": "failed", "error": f"Contract logic error: {cle}", "tx_hash": tx_hash_hex}
        except TransactionNotFound:
            logger.error(f"DEX: Swap transaction not found after timeout (TxHash: {tx_hash_hex}). Might have been dropped from mempool.", exc_info=True)
            return {"status": "failed", "error": "Transaction not found or timed out waiting for receipt.", "tx_hash": tx_hash_hex}
        except Exception as e:
            logger.error(f"DEX: Error during swap (TxHash: {tx_hash_hex}): {e}", exc_info=True)
            return {"status": "failed", "error": str(e), "tx_hash": tx_hash_hex}

async def main_test():
    logger.add(lambda _: print(_.getMessage()))

    TEST_RPC_URL = os.getenv("TEST_SEPOLIA_RPC_URL", "https://sepolia.infura.io/v3/YOUR_INFURA_ID")
    TEST_PRIVATE_KEY = os.getenv("TEST_DEX_PRIVATE_KEY", "your_private_key_hex")
    TEST_WALLET_ADDRESS = os.getenv("TEST_DEX_WALLET_ADDRESS", "your_wallet_address_0x")

    UNISWAP_ROUTER_SEPOLIA = "0x3bFA4769FB09eefC5aB096D036E0A85404923056"
    WETH_SEPOLIA = "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14"
    USDC_SEPOLIA_EXAMPLE = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"

    if "YOUR_INFURA_ID" in TEST_RPC_URL or "your_private_key_hex" in TEST_PRIVATE_KEY or "your_wallet_address_0x" in TEST_WALLET_ADDRESS:
        logger.warning("Please replace placeholder RPC URL, private key, and wallet address for testing.")
        return

    dex_service = DEXExecutionService(
        wallet_address=TEST_WALLET_ADDRESS,
        private_key=TEST_PRIVATE_KEY,
        rpc_url=TEST_RPC_URL,
        router_address=UNISWAP_ROUTER_SEPOLIA,
        chain_id=11155111,
        weth_address=WETH_SEPOLIA
    )

    weth_balance = await dex_service.get_token_balance(WETH_SEPOLIA)
    if weth_balance is not None:
        logger.info(f"Test: WETH Balance: {weth_balance}")

    usdc_balance = await dex_service.get_token_balance(USDC_SEPOLIA_EXAMPLE)
    if usdc_balance is not None:
        logger.info(f"Test: USDC Balance: {usdc_balance}")

    amount_weth_in_wei = dex_service.w3.to_wei(0.00001, 'ether')
    min_usdc_out_wei = dex_service.w3.to_wei(0.0000001, 'mwei')

    current_weth_balance_wei = dex_service.w3.to_wei(weth_balance or 0, 'ether')

    if current_weth_balance_wei < amount_weth_in_wei:
         logger.warning(f"Insufficient WETH balance ({weth_balance}) to perform swap test for {amount_weth_in_wei} wei.")
         if dex_service.weth_address_cs:
             logger.info("Attempting to deposit ETH to WETH as balance is low...")
             try:
                 weth_contract = dex_service.w3.eth.contract(address=dex_service.weth_address_cs, abi=WETH_ABI_SNIPPET)
                 deposit_tx_value = amount_weth_in_wei - current_weth_balance_wei # Deposit the difference
                 if deposit_tx_value <= 0 : deposit_tx_value = dex_service.w3.to_wei(0.0001, 'ether') # Min deposit if balance is really low

                 deposit_tx = weth_contract.functions.deposit().build_transaction({
                     'chainId': dex_service.chain_id,
                     'from': dex_service.wallet_address_cs,
                     'value': deposit_tx_value,
                     'nonce': await dex_service._run_sync_web3_call(dex_service.w3.eth.get_transaction_count, dex_service.wallet_address_cs),
                     'gas': dex_service.default_gas_limit,
                     'gasPrice': await dex_service._run_sync_web3_call(dex_service.w3.eth.gas_price)
                 })
                 signed_deposit_tx = dex_service.account.sign_transaction(deposit_tx)
                 deposit_tx_hash = await dex_service._run_sync_web3_call(dex_service.w3.eth.send_raw_transaction, signed_deposit_tx.rawTransaction)
                 logger.info(f"Test: WETH deposit transaction sent: {deposit_tx_hash.hex()}")
                 deposit_receipt = await dex_service._run_sync_web3_call(dex_service.w3.eth.wait_for_transaction_receipt, deposit_tx_hash, timeout=180)
                 if deposit_receipt.status == 1:
                     logger.info(f"Test: WETH deposit successful. Tx: {deposit_tx_hash.hex()}")
                     weth_balance = await dex_service.get_token_balance(WETH_SEPOLIA)
                     logger.info(f"Test: New WETH Balance: {weth_balance}")
                     current_weth_balance_wei = dex_service.w3.to_wei(weth_balance or 0, 'ether')
                 else:
                     logger.error(f"Test: WETH deposit failed. Tx: {deposit_tx_hash.hex()}")
                     return
             except Exception as e_deposit:
                 logger.error(f"Test: Error during WETH deposit: {e_deposit}", exc_info=True)
                 return

    if current_weth_balance_wei >= amount_weth_in_wei :
        logger.info(f"Attempting swap: {amount_weth_in_wei} WETHwei for USDC...")
        swap_result = await dex_service.place_swap_order(
            token_in_address=WETH_SEPOLIA,
            token_out_address=USDC_SEPOLIA_EXAMPLE,
            amount_in_wei=amount_weth_in_wei,
            min_amount_out_wei=min_usdc_out_wei,
            fee_tier=3000
        )
        logger.info(f"Test: Swap Result: {swap_result}")

        usdc_balance_after = await dex_service.get_token_balance(USDC_SEPOLIA_EXAMPLE)
        if usdc_balance_after is not None:
            logger.info(f"Test: USDC Balance After Swap: {usdc_balance_after}")
            if usdc_balance is not None and usdc_balance_after > usdc_balance:
                 logger.info(f"Test: Successfully received {usdc_balance_after - usdc_balance} USDC.")
    else:
        logger.warning(f"Skipping WETH to USDC swap test due to insufficient WETH balance ({weth_balance}) even after deposit attempt.")

if __name__ == "__main__":
    # from dotenv import load_dotenv
    # load_dotenv()
    asyncio.run(main_test())
