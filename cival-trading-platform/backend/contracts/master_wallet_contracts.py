"""
Smart Contract Integration - Phase 6
Autonomous wallet operations with smart contract support
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from decimal import Decimal
import json
from dataclasses import dataclass

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
import hexbytes

from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

@dataclass
class ContractConfig:
    """Smart contract configuration"""
    contract_address: str
    abi: List[Dict]
    chain_id: int
    chain_name: str
    gas_limit: int = 21000
    gas_price_multiplier: float = 1.1

@dataclass
class TransactionRequest:
    """Transaction request for smart contract interaction"""
    contract_address: str
    function_name: str
    parameters: List[Any]
    value_wei: int = 0
    gas_limit: Optional[int] = None
    gas_price: Optional[int] = None
    nonce: Optional[int] = None

@dataclass
class TransactionResult:
    """Result of smart contract transaction"""
    transaction_hash: str
    status: str  # 'pending', 'confirmed', 'failed'
    gas_used: int
    effective_gas_price: int
    block_number: Optional[int] = None
    contract_address: Optional[str] = None
    logs: List[Dict] = None

class MasterWalletSmartContractService:
    """
    Smart contract service for master wallet operations
    Handles autonomous execution, multi-signature, and risk management
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # Web3 connections by chain
        self.web3_connections: Dict[str, Web3] = {}
        
        # Contract configurations
        self.contract_configs: Dict[str, ContractConfig] = {}
        
        # Wallet accounts (in production, use secure key management)
        self.accounts: Dict[str, LocalAccount] = {}
        
        # Transaction monitoring
        self.pending_transactions: Dict[str, TransactionRequest] = {}
        
        # Smart contract ABIs (simplified versions for demo)
        self.master_wallet_abi = [
            {
                "inputs": [
                    {"name": "_agents", "type": "address[]"},
                    {"name": "_amounts", "type": "uint256[]"}
                ],
                "name": "distributeFunds",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_from", "type": "address"},
                    {"name": "_amount", "type": "uint256"}
                ],
                "name": "collectFunds",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "emergencyStop",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_agent", "type": "address"}
                ],
                "name": "getAgentBalance",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        self.multisig_abi = [
            {
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"},
                    {"name": "_data", "type": "bytes"}
                ],
                "name": "submitTransaction",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_transactionId", "type": "uint256"}
                ],
                "name": "confirmTransaction",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_transactionId", "type": "uint256"}
                ],
                "name": "executeTransaction",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        
        logger.info("MasterWalletSmartContractService initialized")
    
    async def initialize(self):
        """Initialize smart contract service"""
        try:
            # Initialize Web3 connections
            await self._initialize_web3_connections()
            
            # Load contract configurations
            await self._load_contract_configurations()
            
            # Initialize wallet accounts
            await self._initialize_wallet_accounts()
            
            # Start transaction monitoring
            asyncio.create_task(self._transaction_monitoring_loop())
            
            logger.info("MasterWalletSmartContractService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MasterWalletSmartContractService: {e}")
            raise
    
    async def _initialize_web3_connections(self):
        """Initialize Web3 connections for supported chains"""
        chain_configs = {
            "ethereum": {
                "rpc_url": "https://eth.llamarpc.com",
                "chain_id": 1
            },
            "polygon": {
                "rpc_url": "https://polygon.llamarpc.com", 
                "chain_id": 137
            },
            "bsc": {
                "rpc_url": "https://bsc.llamarpc.com",
                "chain_id": 56
            },
            "arbitrum": {
                "rpc_url": "https://arb1.arbitrum.io/rpc",
                "chain_id": 42161
            }
        }
        
        for chain_name, config in chain_configs.items():
            try:
                web3 = Web3(Web3.HTTPProvider(config["rpc_url"]))
                
                # Add POA middleware for BSC and Polygon
                if chain_name in ["bsc", "polygon"]:
                    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                if web3.is_connected():
                    self.web3_connections[chain_name] = web3
                    logger.info(f"Connected to {chain_name} (Chain ID: {config['chain_id']})")
                else:
                    logger.warning(f"Failed to connect to {chain_name}")
                    
            except Exception as e:
                logger.error(f"Error connecting to {chain_name}: {e}")
    
    async def _load_contract_configurations(self):
        """Load smart contract configurations"""
        try:
            # Load from database if available
            if self.supabase:
                response = self.supabase.table('smart_contracts').select('*').eq('is_active', True).execute()
                
                for contract_data in response.data:
                    config = ContractConfig(
                        contract_address=contract_data['contract_address'],
                        abi=json.loads(contract_data['abi']),
                        chain_id=contract_data['chain_id'],
                        chain_name=contract_data['chain_name'],
                        gas_limit=contract_data.get('gas_limit', 21000),
                        gas_price_multiplier=contract_data.get('gas_price_multiplier', 1.1)
                    )
                    
                    self.contract_configs[f"{contract_data['contract_type']}:{contract_data['chain_name']}"] = config
            
            # Add default configurations if not in database
            await self._add_default_contract_configs()
            
        except Exception as e:
            logger.error(f"Failed to load contract configurations: {e}")
    
    async def _add_default_contract_configs(self):
        """Add default contract configurations"""
        try:
            # Example master wallet contract addresses (these would be deployed contracts)
            default_configs = {
                "master_wallet:ethereum": ContractConfig(
                    contract_address="0x742d35Cc6610C7532C8bb9B5A33e6B2e7B5C4A6b",  # Example address
                    abi=self.master_wallet_abi,
                    chain_id=1,
                    chain_name="ethereum",
                    gas_limit=300000
                ),
                "master_wallet:polygon": ContractConfig(
                    contract_address="0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # Example address
                    abi=self.master_wallet_abi,
                    chain_id=137,
                    chain_name="polygon",
                    gas_limit=300000
                ),
                "multisig:ethereum": ContractConfig(
                    contract_address="0x12345678901234567890123456789012345678901",  # Example address
                    abi=self.multisig_abi,
                    chain_id=1,
                    chain_name="ethereum",
                    gas_limit=200000
                )
            }
            
            self.contract_configs.update(default_configs)
            
        except Exception as e:
            logger.error(f"Failed to add default contract configs: {e}")
    
    async def _initialize_wallet_accounts(self):
        """Initialize wallet accounts for signing transactions"""
        try:
            # In production, load from secure key management system
            # For demo, we'll use environment variables or generate keys
            
            # Master wallet account (in production, use HSM or secure storage)
            master_private_key = "0x" + "0" * 64  # Placeholder - replace with actual key management
            master_account = Account.from_key(master_private_key)
            self.accounts["master"] = master_account
            
            # Agent accounts would be generated as needed
            logger.info("Wallet accounts initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet accounts: {e}")
    
    async def distribute_funds_to_agents(self, chain_name: str, agent_addresses: List[str], 
                                       amounts: List[Decimal]) -> TransactionResult:
        """Distribute funds to multiple agents via smart contract"""
        try:
            if len(agent_addresses) != len(amounts):
                raise ValueError("Agent addresses and amounts lists must have same length")
            
            # Get contract configuration
            contract_key = f"master_wallet:{chain_name}"
            if contract_key not in self.contract_configs:
                raise ValueError(f"Master wallet contract not configured for {chain_name}")
            
            config = self.contract_configs[contract_key]
            web3 = self.web3_connections[chain_name]
            
            # Create contract instance
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(config.contract_address),
                abi=config.abi
            )
            
            # Convert amounts to Wei
            amounts_wei = [web3.to_wei(amount, 'ether') for amount in amounts]
            
            # Build transaction
            transaction_request = TransactionRequest(
                contract_address=config.contract_address,
                function_name="distributeFunds",
                parameters=[agent_addresses, amounts_wei],
                gas_limit=config.gas_limit
            )
            
            # Execute transaction
            result = await self._execute_contract_transaction(web3, contract, transaction_request)
            
            logger.info(f"Distributed funds to {len(agent_addresses)} agents on {chain_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to distribute funds to agents: {e}")
            raise
    
    async def collect_funds_from_agent(self, chain_name: str, agent_address: str, 
                                     amount: Decimal) -> TransactionResult:
        """Collect funds from an agent via smart contract"""
        try:
            contract_key = f"master_wallet:{chain_name}"
            if contract_key not in self.contract_configs:
                raise ValueError(f"Master wallet contract not configured for {chain_name}")
            
            config = self.contract_configs[contract_key]
            web3 = self.web3_connections[chain_name]
            
            # Create contract instance
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(config.contract_address),
                abi=config.abi
            )
            
            # Convert amount to Wei
            amount_wei = web3.to_wei(amount, 'ether')
            
            # Build transaction
            transaction_request = TransactionRequest(
                contract_address=config.contract_address,
                function_name="collectFunds",
                parameters=[agent_address, amount_wei],
                gas_limit=config.gas_limit
            )
            
            # Execute transaction
            result = await self._execute_contract_transaction(web3, contract, transaction_request)
            
            logger.info(f"Collected {amount} from agent {agent_address} on {chain_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to collect funds from agent: {e}")
            raise
    
    async def emergency_stop(self, chain_name: str) -> TransactionResult:
        """Execute emergency stop on master wallet contract"""
        try:
            contract_key = f"master_wallet:{chain_name}"
            if contract_key not in self.contract_configs:
                raise ValueError(f"Master wallet contract not configured for {chain_name}")
            
            config = self.contract_configs[contract_key]
            web3 = self.web3_connections[chain_name]
            
            # Create contract instance
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(config.contract_address),
                abi=config.abi
            )
            
            # Build transaction
            transaction_request = TransactionRequest(
                contract_address=config.contract_address,
                function_name="emergencyStop",
                parameters=[],
                gas_limit=config.gas_limit
            )
            
            # Execute transaction
            result = await self._execute_contract_transaction(web3, contract, transaction_request)
            
            logger.warning(f"Emergency stop executed on {chain_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute emergency stop: {e}")
            raise
    
    async def get_agent_balance(self, chain_name: str, agent_address: str) -> Decimal:
        """Get agent balance from smart contract"""
        try:
            contract_key = f"master_wallet:{chain_name}"
            if contract_key not in self.contract_configs:
                raise ValueError(f"Master wallet contract not configured for {chain_name}")
            
            config = self.contract_configs[contract_key]
            web3 = self.web3_connections[chain_name]
            
            # Create contract instance
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(config.contract_address),
                abi=config.abi
            )
            
            # Call view function
            balance_wei = contract.functions.getAgentBalance(agent_address).call()
            balance_eth = web3.from_wei(balance_wei, 'ether')
            
            return Decimal(str(balance_eth))
            
        except Exception as e:
            logger.error(f"Failed to get agent balance: {e}")
            return Decimal("0")
    
    async def submit_multisig_transaction(self, chain_name: str, to_address: str, 
                                        value: Decimal, data: bytes = b'') -> int:
        """Submit transaction to multisig wallet"""
        try:
            contract_key = f"multisig:{chain_name}"
            if contract_key not in self.contract_configs:
                raise ValueError(f"Multisig contract not configured for {chain_name}")
            
            config = self.contract_configs[contract_key]
            web3 = self.web3_connections[chain_name]
            
            # Create contract instance
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(config.contract_address),
                abi=config.abi
            )
            
            # Convert value to Wei
            value_wei = web3.to_wei(value, 'ether')
            
            # Build transaction
            transaction_request = TransactionRequest(
                contract_address=config.contract_address,
                function_name="submitTransaction",
                parameters=[to_address, value_wei, data],
                gas_limit=config.gas_limit
            )
            
            # Execute transaction
            result = await self._execute_contract_transaction(web3, contract, transaction_request)
            
            # Parse transaction ID from logs (simplified)
            transaction_id = 0  # Would parse from transaction receipt logs
            
            logger.info(f"Submitted multisig transaction {transaction_id} on {chain_name}")
            return transaction_id
            
        except Exception as e:
            logger.error(f"Failed to submit multisig transaction: {e}")
            raise
    
    async def confirm_multisig_transaction(self, chain_name: str, transaction_id: int) -> TransactionResult:
        """Confirm multisig transaction"""
        try:
            contract_key = f"multisig:{chain_name}"
            if contract_key not in self.contract_configs:
                raise ValueError(f"Multisig contract not configured for {chain_name}")
            
            config = self.contract_configs[contract_key]
            web3 = self.web3_connections[chain_name]
            
            # Create contract instance
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(config.contract_address),
                abi=config.abi
            )
            
            # Build transaction
            transaction_request = TransactionRequest(
                contract_address=config.contract_address,
                function_name="confirmTransaction",
                parameters=[transaction_id],
                gas_limit=config.gas_limit
            )
            
            # Execute transaction
            result = await self._execute_contract_transaction(web3, contract, transaction_request)
            
            logger.info(f"Confirmed multisig transaction {transaction_id} on {chain_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to confirm multisig transaction: {e}")
            raise
    
    async def _execute_contract_transaction(self, web3: Web3, contract: Any, 
                                         request: TransactionRequest) -> TransactionResult:
        """Execute a smart contract transaction"""
        try:
            # Get master account for signing
            master_account = self.accounts.get("master")
            if not master_account:
                raise ValueError("Master account not available")
            
            # Get current gas price
            gas_price = web3.eth.gas_price
            if request.gas_price:
                gas_price = request.gas_price
            
            # Get nonce
            nonce = web3.eth.get_transaction_count(master_account.address)
            if request.nonce:
                nonce = request.nonce
            
            # Build transaction data
            function = getattr(contract.functions, request.function_name)
            transaction_data = function(*request.parameters).build_transaction({
                'from': master_account.address,
                'gas': request.gas_limit or 300000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'value': request.value_wei
            })
            
            # Sign transaction
            signed_txn = web3.eth.account.sign_transaction(transaction_data, master_account.key)
            
            # Send transaction
            tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            # Store for monitoring
            self.pending_transactions[tx_hash_hex] = request
            
            # Create initial result
            result = TransactionResult(
                transaction_hash=tx_hash_hex,
                status="pending",
                gas_used=0,
                effective_gas_price=gas_price
            )
            
            logger.info(f"Submitted transaction {tx_hash_hex}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute contract transaction: {e}")
            raise
    
    async def _transaction_monitoring_loop(self):
        """Monitor pending transactions"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                completed_transactions = []
                
                for tx_hash, request in self.pending_transactions.items():
                    try:
                        # Check all chains for this transaction
                        for chain_name, web3 in self.web3_connections.items():
                            try:
                                receipt = web3.eth.get_transaction_receipt(tx_hash)
                                if receipt:
                                    # Transaction found and confirmed
                                    result = TransactionResult(
                                        transaction_hash=tx_hash,
                                        status="confirmed" if receipt.status == 1 else "failed",
                                        gas_used=receipt.gasUsed,
                                        effective_gas_price=receipt.effectiveGasPrice,
                                        block_number=receipt.blockNumber,
                                        logs=receipt.logs
                                    )
                                    
                                    await self._handle_transaction_completion(tx_hash, result)
                                    completed_transactions.append(tx_hash)
                                    break
                                    
                            except Exception:
                                # Transaction not found on this chain, continue
                                continue
                                
                    except Exception as e:
                        logger.error(f"Error checking transaction {tx_hash}: {e}")
                
                # Remove completed transactions
                for tx_hash in completed_transactions:
                    self.pending_transactions.pop(tx_hash, None)
                    
            except Exception as e:
                logger.error(f"Error in transaction monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _handle_transaction_completion(self, tx_hash: str, result: TransactionResult):
        """Handle completed transaction"""
        try:
            # Update database
            if self.supabase:
                transaction_data = {
                    "transaction_hash": tx_hash,
                    "status": result.status,
                    "gas_used": result.gas_used,
                    "effective_gas_price": result.effective_gas_price,
                    "block_number": result.block_number,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }
                
                self.supabase.table('smart_contract_transactions').upsert(transaction_data).execute()
            
            # Cache result in Redis
            if self.redis:
                await self.redis.setex(
                    f"transaction_result:{tx_hash}",
                    3600,  # 1 hour TTL
                    json.dumps({
                        "status": result.status,
                        "gas_used": result.gas_used,
                        "block_number": result.block_number
                    })
                )
            
            logger.info(f"Transaction {tx_hash} completed with status: {result.status}")
            
        except Exception as e:
            logger.error(f"Failed to handle transaction completion: {e}")
    
    async def get_transaction_status(self, tx_hash: str) -> Optional[TransactionResult]:
        """Get status of a transaction"""
        try:
            # Check cache first
            if self.redis:
                cached_result = await self.redis.get(f"transaction_result:{tx_hash}")
                if cached_result:
                    data = json.loads(cached_result)
                    return TransactionResult(
                        transaction_hash=tx_hash,
                        status=data["status"],
                        gas_used=data["gas_used"],
                        effective_gas_price=0,
                        block_number=data.get("block_number")
                    )
            
            # Check pending transactions
            if tx_hash in self.pending_transactions:
                return TransactionResult(
                    transaction_hash=tx_hash,
                    status="pending",
                    gas_used=0,
                    effective_gas_price=0
                )
            
            # Check database
            if self.supabase:
                response = self.supabase.table('smart_contract_transactions')\
                    .select('*').eq('transaction_hash', tx_hash).single().execute()
                
                if response.data:
                    data = response.data
                    return TransactionResult(
                        transaction_hash=tx_hash,
                        status=data["status"],
                        gas_used=data["gas_used"],
                        effective_gas_price=data["effective_gas_price"],
                        block_number=data.get("block_number")
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return None
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        return {
            "service": "master_wallet_smart_contract_service",
            "status": "running",
            "web3_connections": len(self.web3_connections),
            "contract_configs": len(self.contract_configs),
            "pending_transactions": len(self.pending_transactions),
            "wallet_accounts": len(self.accounts),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_master_wallet_smart_contract_service():
    """Factory function to create MasterWalletSmartContractService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = MasterWalletSmartContractService(redis_client, supabase_client)
    return service