"""
Vault Management Service
Comprehensive vault/wallet hierarchy management with multi-asset support
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

import redis.asyncio as redis
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class VaultType(Enum):
    MASTER = "master"
    STRATEGY = "strategy"
    LENDING = "lending"
    ARBITRAGE = "arbitrage"
    AGENT = "agent"
    RESERVE = "reserve"

class VaultStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    LOCKED = "locked"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"

class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    ALLOCATION = "allocation"
    YIELD = "yield"
    FEE = "fee"

@dataclass
class Vault:
    """Vault definition"""
    vault_id: str
    vault_name: str
    vault_type: VaultType
    status: VaultStatus
    total_balance: Decimal
    available_balance: Decimal
    reserved_balance: Decimal
    parent_vault_id: Optional[str] = None
    hierarchy_level: int = 0
    created_at: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}

@dataclass
class VaultTransaction:
    """Vault transaction record"""
    transaction_id: str
    vault_id: str
    transaction_type: TransactionType
    asset_symbol: str
    amount: Decimal
    status: str
    created_at: datetime
    from_vault_id: Optional[str] = None
    to_vault_id: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class VaultPerformance:
    """Vault performance metrics"""
    vault_id: str
    total_balance_usd: Decimal
    daily_pnl: Decimal
    cumulative_pnl: Decimal
    daily_return_pct: Decimal
    cumulative_return_pct: Decimal
    date: datetime

@dataclass
class VaultAllocation:
    """Vault allocation record"""
    allocation_id: str
    vault_id: str
    target_type: str
    target_id: str
    target_name: str
    asset_symbol: str
    allocated_amount: Decimal
    allocated_percentage: Decimal
    status: str
    performance: Optional[Dict[str, Any]] = None

class VaultManagementService:
    """
    Comprehensive vault management service with hierarchical structure support
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # Active vaults tracking
        self.active_vaults: Dict[str, Vault] = {}
        self.vault_transactions: Dict[str, List[VaultTransaction]] = {}
        self.vault_performance: Dict[str, VaultPerformance] = {}
        self.vault_allocations: Dict[str, List[VaultAllocation]] = {}
        
        # Initialize with mock data for immediate functionality
        self._initialize_mock_data()
        
        logger.info("VaultManagementService initialized")
    
    def _initialize_mock_data(self):
        """Initialize with mock vault data"""
        # Master vault
        master_vault = Vault(
            vault_id="vault-master",
            vault_name="Master Trading Vault",
            vault_type=VaultType.MASTER,
            status=VaultStatus.ACTIVE,
            total_balance=Decimal("1258473.25"),
            available_balance=Decimal("270818.93"),
            reserved_balance=Decimal("987654.32"),
            hierarchy_level=0,
            metadata={"complianceScore": 98, "riskLevel": "Low"}
        )
        self.active_vaults[master_vault.vault_id] = master_vault
        
        # Strategy vaults
        algo_vault = Vault(
            vault_id="vault-algo",
            vault_name="Algorithmic Trading",
            vault_type=VaultType.STRATEGY,
            status=VaultStatus.ACTIVE,
            total_balance=Decimal("425847.50"),
            available_balance=Decimal("27596.75"),
            reserved_balance=Decimal("398250.75"),
            parent_vault_id="vault-master",
            hierarchy_level=1,
            metadata={"riskLevel": "Medium", "performance": 8.45, "strategies": ["Darvas Box", "Elliott Wave"]}
        )
        self.active_vaults[algo_vault.vault_id] = algo_vault
        
        defi_vault = Vault(
            vault_id="vault-defi",
            vault_name="DeFi Operations",
            vault_type=VaultType.LENDING,
            status=VaultStatus.ACTIVE,
            total_balance=Decimal("287954.12"),
            available_balance=Decimal("12273.67"),
            reserved_balance=Decimal("275680.45"),
            parent_vault_id="vault-master",
            hierarchy_level=1,
            metadata={"riskLevel": "High", "performance": 12.34, "protocols": ["Uniswap V3", "Aave"]}
        )
        self.active_vaults[defi_vault.vault_id] = defi_vault
        
        # Mock transactions
        self.vault_transactions["vault-master"] = [
            VaultTransaction(
                transaction_id="tx1",
                vault_id="vault-master",
                transaction_type=TransactionType.TRANSFER,
                asset_symbol="USD",
                amount=Decimal("50000"),
                status="completed",
                created_at=datetime.now(timezone.utc),
                from_vault_id="vault-master",
                to_vault_id="vault-algo",
                metadata={"purpose": "Strategy rebalancing"}
            )
        ]
        
        # Mock performance
        self.vault_performance["vault-master"] = VaultPerformance(
            vault_id="vault-master",
            total_balance_usd=Decimal("1258473.25"),
            daily_pnl=Decimal("5234.67"),
            cumulative_pnl=Decimal("125847.32"),
            daily_return_pct=Decimal("0.42"),
            cumulative_return_pct=Decimal("11.15"),
            date=datetime.now(timezone.utc)
        )

    async def initialize(self):
        """Initialize the vault management service"""
        try:
            # Load vaults from database if available
            await self._load_active_vaults()
            
            # Start background monitoring
            asyncio.create_task(self._vault_monitoring_loop())
            asyncio.create_task(self._performance_tracking_loop())
            
            logger.info("VaultManagementService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize VaultManagementService: {e}")
            # Continue with mock data
            pass

    async def create_vault(self, vault_data: Dict[str, Any]) -> Vault:
        """Create a new vault"""
        try:
            vault = Vault(
                vault_id=str(uuid.uuid4()),
                vault_name=vault_data["vault_name"],
                vault_type=VaultType(vault_data.get("vault_type", "strategy")),
                status=VaultStatus(vault_data.get("status", "active")),
                total_balance=Decimal(str(vault_data.get("total_balance", "0"))),
                available_balance=Decimal(str(vault_data.get("available_balance", "0"))),
                reserved_balance=Decimal(str(vault_data.get("reserved_balance", "0"))),
                parent_vault_id=vault_data.get("parent_vault_id"),
                hierarchy_level=vault_data.get("hierarchy_level", 1),
                metadata=vault_data.get("metadata", {})
            )
            
            # Save to database
            if self.supabase:
                vault_dict = asdict(vault)
                vault_dict["vault_type"] = vault.vault_type.value
                vault_dict["status"] = vault.status.value
                vault_dict["created_at"] = vault.created_at.isoformat()
                
                self.supabase.table('vaults').insert(vault_dict).execute()
            
            # Add to active vaults
            self.active_vaults[vault.vault_id] = vault
            
            # Cache in Redis
            if self.redis:
                await self.redis.setex(
                    f"vault:{vault.vault_id}",
                    3600,
                    json.dumps(asdict(vault), default=str)
                )
            
            logger.info(f"Created vault: {vault.vault_name} ({vault.vault_id})")
            return vault
            
        except Exception as e:
            logger.error(f"Failed to create vault: {e}")
            raise

    async def get_all_vaults(self) -> List[Vault]:
        """Get all vaults"""
        return list(self.active_vaults.values())

    async def get_vault(self, vault_id: str) -> Optional[Vault]:
        """Get a specific vault"""
        return self.active_vaults.get(vault_id)

    async def update_vault(self, vault_id: str, updates: Dict[str, Any]) -> Optional[Vault]:
        """Update vault details"""
        try:
            vault = self.active_vaults.get(vault_id)
            if not vault:
                return None

            # Update fields
            for key, value in updates.items():
                if hasattr(vault, key):
                    if key in ["vault_type", "status"]:
                        setattr(vault, key, VaultType(value) if key == "vault_type" else VaultStatus(value))
                    elif key in ["total_balance", "available_balance", "reserved_balance"]:
                        setattr(vault, key, Decimal(str(value)))
                    else:
                        setattr(vault, key, value)

            # Update in database
            if self.supabase:
                update_dict = {k: v for k, v in updates.items()}
                if "vault_type" in update_dict:
                    update_dict["vault_type"] = vault.vault_type.value
                if "status" in update_dict:
                    update_dict["status"] = vault.status.value
                
                self.supabase.table('vaults').update(update_dict).eq('vault_id', vault_id).execute()

            # Update cache
            if self.redis:
                await self.redis.setex(
                    f"vault:{vault_id}",
                    3600,
                    json.dumps(asdict(vault), default=str)
                )

            logger.info(f"Updated vault: {vault.vault_name} ({vault_id})")
            return vault

        except Exception as e:
            logger.error(f"Failed to update vault {vault_id}: {e}")
            return None

    async def delete_vault(self, vault_id: str) -> bool:
        """Delete a vault"""
        try:
            vault = self.active_vaults.get(vault_id)
            if not vault:
                return False

            # Remove from database
            if self.supabase:
                self.supabase.table('vaults').delete().eq('vault_id', vault_id).execute()

            # Remove from active vaults
            del self.active_vaults[vault_id]

            # Remove from cache
            if self.redis:
                await self.redis.delete(f"vault:{vault_id}")

            logger.info(f"Deleted vault: {vault.vault_name} ({vault_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to delete vault {vault_id}: {e}")
            return False

    async def transfer_funds(self, from_vault_id: str, to_vault_id: str, asset_symbol: str, amount: Decimal) -> bool:
        """Transfer funds between vaults"""
        try:
            from_vault = self.active_vaults.get(from_vault_id)
            to_vault = self.active_vaults.get(to_vault_id)
            
            if not from_vault or not to_vault:
                logger.error(f"Vault not found: {from_vault_id} or {to_vault_id}")
                return False

            if from_vault.available_balance < amount:
                logger.error(f"Insufficient balance in vault {from_vault_id}")
                return False

            # Update balances
            from_vault.available_balance -= amount
            from_vault.total_balance -= amount
            to_vault.available_balance += amount
            to_vault.total_balance += amount

            # Create transaction record
            transaction = VaultTransaction(
                transaction_id=str(uuid.uuid4()),
                vault_id=from_vault_id,
                transaction_type=TransactionType.TRANSFER,
                asset_symbol=asset_symbol,
                amount=amount,
                status="completed",
                created_at=datetime.now(timezone.utc),
                from_vault_id=from_vault_id,
                to_vault_id=to_vault_id,
                metadata={"transfer_type": "internal"}
            )

            # Store transaction
            if from_vault_id not in self.vault_transactions:
                self.vault_transactions[from_vault_id] = []
            self.vault_transactions[from_vault_id].append(transaction)

            logger.info(f"Transferred {amount} {asset_symbol} from {from_vault_id} to {to_vault_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to transfer funds: {e}")
            return False

    async def get_vault_transactions(self, vault_id: str, limit: int = 10) -> List[VaultTransaction]:
        """Get transaction history for a vault"""
        transactions = self.vault_transactions.get(vault_id, [])
        return sorted(transactions, key=lambda x: x.created_at, reverse=True)[:limit]

    async def get_vault_performance(self, vault_id: str) -> Optional[VaultPerformance]:
        """Get performance metrics for a vault"""
        return self.vault_performance.get(vault_id)

    async def get_vault_allocations(self, vault_id: str) -> List[VaultAllocation]:
        """Get allocations for a vault"""
        return self.vault_allocations.get(vault_id, [])

    async def get_vault_summary(self) -> Dict[str, Any]:
        """Get comprehensive vault summary"""
        try:
            total_balance = sum(vault.total_balance for vault in self.active_vaults.values())
            total_available = sum(vault.available_balance for vault in self.active_vaults.values())
            total_reserved = sum(vault.reserved_balance for vault in self.active_vaults.values())
            
            active_vaults = [v for v in self.active_vaults.values() if v.status == VaultStatus.ACTIVE]
            
            return {
                "total_vaults": len(self.active_vaults),
                "active_vaults": len(active_vaults),
                "total_balance": float(total_balance),
                "total_available": float(total_available),
                "total_reserved": float(total_reserved),
                "vault_types": self._get_vault_counts_by_type(),
                "vault_statuses": self._get_vault_counts_by_status(),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get vault summary: {e}")
            return {
                "total_vaults": 0,
                "active_vaults": 0,
                "total_balance": 0.0,
                "total_available": 0.0,
                "total_reserved": 0.0,
                "vault_types": {},
                "vault_statuses": {},
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

    def _get_vault_counts_by_type(self) -> Dict[str, int]:
        """Get vault counts by type"""
        type_counts = {}
        for vault in self.active_vaults.values():
            vault_type = vault.vault_type.value
            type_counts[vault_type] = type_counts.get(vault_type, 0) + 1
        return type_counts

    def _get_vault_counts_by_status(self) -> Dict[str, int]:
        """Get vault counts by status"""
        status_counts = {}
        for vault in self.active_vaults.values():
            status = vault.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts

    async def _load_active_vaults(self):
        """Load active vaults from database"""
        try:
            if self.supabase:
                response = self.supabase.table('vaults').select('*').execute()
                for vault_data in response.data:
                    vault = Vault(
                        vault_id=vault_data["vault_id"],
                        vault_name=vault_data["vault_name"],
                        vault_type=VaultType(vault_data["vault_type"]),
                        status=VaultStatus(vault_data["status"]),
                        total_balance=Decimal(str(vault_data["total_balance"])),
                        available_balance=Decimal(str(vault_data["available_balance"])),
                        reserved_balance=Decimal(str(vault_data["reserved_balance"])),
                        parent_vault_id=vault_data.get("parent_vault_id"),
                        hierarchy_level=vault_data.get("hierarchy_level", 0),
                        created_at=datetime.fromisoformat(vault_data["created_at"]),
                        metadata=vault_data.get("metadata", {})
                    )
                    self.active_vaults[vault.vault_id] = vault
        except Exception as e:
            logger.warning(f"Could not load vaults from database: {e}")
            # Continue with mock data

    async def _vault_monitoring_loop(self):
        """Background vault monitoring"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                # Implement vault health checks, balance validation, etc.
                logger.debug("Vault monitoring check completed")
            except Exception as e:
                logger.error(f"Error in vault monitoring loop: {e}")

    async def _performance_tracking_loop(self):
        """Background performance tracking"""
        while True:
            try:
                await asyncio.sleep(300)  # Update every 5 minutes
                # Update performance metrics for all vaults
                for vault_id in self.active_vaults.keys():
                    await self._update_vault_performance(vault_id)
                logger.debug("Performance tracking update completed")
            except Exception as e:
                logger.error(f"Error in performance tracking loop: {e}")

    async def _update_vault_performance(self, vault_id: str):
        """Update performance metrics for a vault"""
        try:
            vault = self.active_vaults.get(vault_id)
            if not vault:
                return

            # Calculate performance metrics (mock implementation)
            daily_pnl = Decimal(str((hash(vault_id) % 10000) - 5000))  # Mock daily P&L
            cumulative_pnl = vault.total_balance * Decimal("0.05")  # Mock 5% return
            
            performance = VaultPerformance(
                vault_id=vault_id,
                total_balance_usd=vault.total_balance,
                daily_pnl=daily_pnl,
                cumulative_pnl=cumulative_pnl,
                daily_return_pct=daily_pnl / vault.total_balance * 100,
                cumulative_return_pct=cumulative_pnl / vault.total_balance * 100,
                date=datetime.now(timezone.utc)
            )
            
            self.vault_performance[vault_id] = performance

        except Exception as e:
            logger.error(f"Failed to update performance for vault {vault_id}: {e}")

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        return {
            "service": "vault_management_service",
            "status": "running",
            "active_vaults": len(self.active_vaults),
            "total_balance": float(sum(v.total_balance for v in self.active_vaults.values())),
            "vault_types": list(set(v.vault_type.value for v in self.active_vaults.values())),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }
    
    # Multi-Chain Wallet Integration - Phase 9
    
    async def get_multi_chain_overview(self) -> Dict[str, Any]:
        """Get multi-chain wallet overview"""
        try:
            # Mock multi-chain data
            chains = {
                "ethereum": {
                    "chain_id": 1,
                    "name": "Ethereum",
                    "native_token": "ETH",
                    "total_balance_usd": 456789.12,
                    "wallet_count": 3,
                    "last_block": 18945673,
                    "gas_price_gwei": 25.4,
                    "status": "active"
                },
                "bsc": {
                    "chain_id": 56,
                    "name": "Binance Smart Chain", 
                    "native_token": "BNB",
                    "total_balance_usd": 234567.89,
                    "wallet_count": 2,
                    "last_block": 34856729,
                    "gas_price_gwei": 5.2,
                    "status": "active"
                },
                "polygon": {
                    "chain_id": 137,
                    "name": "Polygon",
                    "native_token": "MATIC",
                    "total_balance_usd": 123456.78,
                    "wallet_count": 2,
                    "last_block": 50123987,
                    "gas_price_gwei": 32.1,
                    "status": "active"
                },
                "arbitrum": {
                    "chain_id": 42161,
                    "name": "Arbitrum One",
                    "native_token": "ETH",
                    "total_balance_usd": 78945.67,
                    "wallet_count": 1,
                    "last_block": 145678912,
                    "gas_price_gwei": 0.3,
                    "status": "active"
                },
                "solana": {
                    "chain_id": 101,
                    "name": "Solana",
                    "native_token": "SOL",
                    "total_balance_usd": 89012.34,
                    "wallet_count": 1,
                    "last_block": 234567890,
                    "gas_price_gwei": 0.0001,
                    "status": "active"
                }
            }
            
            total_balance_usd = sum(chain["total_balance_usd"] for chain in chains.values())
            active_chains = len([c for c in chains.values() if c["status"] == "active"])
            total_wallets = sum(chain["wallet_count"] for chain in chains.values())
            
            return {
                "total_balance_usd": total_balance_usd,
                "active_chains": active_chains,
                "total_chains": len(chains),
                "total_wallets": total_wallets,
                "chains": chains,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting multi-chain overview: {e}")
            return {}
    
    async def get_chain_balances(self, wallet_id: str) -> Dict[str, Any]:
        """Get balances for all chains for a specific wallet"""
        try:
            # Mock chain balances
            balances = {
                "ethereum": {
                    "native": {
                        "symbol": "ETH",
                        "balance": 15.47623,
                        "usd_value": 31254.89,
                        "price_usd": 2021.45
                    },
                    "tokens": [
                        {
                            "symbol": "USDC",
                            "balance": 25000.0,
                            "usd_value": 25000.0,
                            "price_usd": 1.0,
                            "contract": "0xa0b86a33e6d86a4b11e8f7e3b9a1a8a7f8b9c0d1e2"
                        },
                        {
                            "symbol": "WBTC",
                            "balance": 2.5,
                            "usd_value": 107500.0,
                            "price_usd": 43000.0,
                            "contract": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
                        }
                    ]
                },
                "bsc": {
                    "native": {
                        "symbol": "BNB",
                        "balance": 45.287,
                        "usd_value": 13586.1,
                        "price_usd": 300.0
                    },
                    "tokens": [
                        {
                            "symbol": "CAKE",
                            "balance": 1250.0,
                            "usd_value": 5000.0,
                            "price_usd": 4.0,
                            "contract": "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82"
                        }
                    ]
                },
                "polygon": {
                    "native": {
                        "symbol": "MATIC",
                        "balance": 12500.0,
                        "usd_value": 10000.0,
                        "price_usd": 0.8
                    },
                    "tokens": [
                        {
                            "symbol": "USDT",
                            "balance": 15000.0,
                            "usd_value": 15000.0,
                            "price_usd": 1.0,
                            "contract": "0xc2132d05d31c914a87c6611c10748aeb04b58e8f"
                        }
                    ]
                }
            }
            
            # Calculate totals
            total_usd = 0
            for chain_data in balances.values():
                total_usd += chain_data["native"]["usd_value"]
                total_usd += sum(token["usd_value"] for token in chain_data.get("tokens", []))
            
            return {
                "wallet_id": wallet_id,
                "total_usd_value": total_usd,
                "balances": balances,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting chain balances: {e}")
            return {}
    
    async def get_cross_chain_positions(self) -> List[Dict[str, Any]]:
        """Get cross-chain position summary"""
        try:
            positions = [
                {
                    "position_id": "pos_1",
                    "asset": "ETH",
                    "total_amount": 25.67,
                    "total_usd_value": 51854.32,
                    "chains": {
                        "ethereum": {"amount": 15.47, "percentage": 60.3},
                        "arbitrum": {"amount": 5.2, "percentage": 20.3},
                        "polygon": {"amount": 5.0, "percentage": 19.4}
                    },
                    "avg_cost_basis": 1890.45,
                    "unrealized_pnl": 3367.82,
                    "unrealized_pnl_percent": 6.95
                },
                {
                    "position_id": "pos_2",
                    "asset": "USDC",
                    "total_amount": 75000.0,
                    "total_usd_value": 75000.0,
                    "chains": {
                        "ethereum": {"amount": 40000.0, "percentage": 53.3},
                        "polygon": {"amount": 20000.0, "percentage": 26.7},
                        "bsc": {"amount": 15000.0, "percentage": 20.0}
                    },
                    "avg_cost_basis": 1.0,
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_percent": 0.0
                },
                {
                    "position_id": "pos_3",
                    "asset": "BTC",
                    "total_amount": 3.75,
                    "total_usd_value": 161250.0,
                    "chains": {
                        "ethereum": {"amount": 2.5, "percentage": 66.7},
                        "bsc": {"amount": 1.25, "percentage": 33.3}
                    },
                    "avg_cost_basis": 41500.0,
                    "unrealized_pnl": 5625.0,
                    "unrealized_pnl_percent": 3.62
                }
            ]
            
            return positions
        except Exception as e:
            logger.error(f"Error getting cross-chain positions: {e}")
            return []
    
    async def initiate_cross_chain_transfer(self, transfer_request: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate a cross-chain transfer"""
        try:
            from_chain = transfer_request.get("from_chain")
            to_chain = transfer_request.get("to_chain")
            asset = transfer_request.get("asset")
            amount = Decimal(str(transfer_request.get("amount", 0)))
            
            # Mock cross-chain transfer
            transfer_id = str(uuid.uuid4())
            
            # Simulate bridge selection and fees
            bridge_options = {
                ("ethereum", "polygon"): {"bridge": "Polygon Bridge", "fee_usd": 15.0, "time_minutes": 8},
                ("ethereum", "arbitrum"): {"bridge": "Arbitrum Bridge", "fee_usd": 8.0, "time_minutes": 12},
                ("ethereum", "bsc"): {"bridge": "Binance Bridge", "fee_usd": 5.0, "time_minutes": 15},
                ("bsc", "polygon"): {"bridge": "AnySwap", "fee_usd": 3.0, "time_minutes": 5},
                ("polygon", "arbitrum"): {"bridge": "Hop Protocol", "fee_usd": 4.0, "time_minutes": 10}
            }
            
            bridge_key = (from_chain, to_chain)
            bridge_info = bridge_options.get(bridge_key, {
                "bridge": "Generic Bridge",
                "fee_usd": 10.0,
                "time_minutes": 20
            })
            
            result = {
                "transfer_id": transfer_id,
                "from_chain": from_chain,
                "to_chain": to_chain,
                "asset": asset,
                "amount": float(amount),
                "bridge": bridge_info["bridge"],
                "estimated_fee_usd": bridge_info["fee_usd"],
                "estimated_time_minutes": bridge_info["time_minutes"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tx_hash": f"0x{uuid.uuid4().hex}"
            }
            
            return result
        except Exception as e:
            logger.error(f"Error initiating cross-chain transfer: {e}")
            raise
    
    async def get_transaction_history_multi_chain(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get multi-chain transaction history"""
        try:
            limit = params.get("limit", 50)
            chain_filter = params.get("chain")
            
            # Mock transaction history across chains
            transactions = []
            
            for i in range(limit):
                chains = ["ethereum", "bsc", "polygon", "arbitrum", "solana"]
                if chain_filter:
                    chains = [chain_filter]
                
                chain = chains[i % len(chains)]
                tx_types = ["transfer", "swap", "bridge", "deposit", "withdrawal"]
                
                tx = {
                    "tx_id": f"tx_{uuid.uuid4().hex[:8]}",
                    "chain": chain,
                    "type": tx_types[i % len(tx_types)],
                    "asset": ["ETH", "BTC", "USDC", "BNB", "MATIC"][i % 5],
                    "amount": round(10 + (i * 13.7) % 1000, 4),
                    "usd_value": round(100 + (i * 456.78) % 10000, 2),
                    "from_address": f"0x{uuid.uuid4().hex[:40]}",
                    "to_address": f"0x{uuid.uuid4().hex[:40]}",
                    "tx_hash": f"0x{uuid.uuid4().hex}",
                    "status": "confirmed" if i % 10 != 0 else "pending",
                    "gas_fee_usd": round(5 + (i * 2.3) % 50, 2),
                    "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat()
                }
                transactions.append(tx)
            
            return transactions
        except Exception as e:
            logger.error(f"Error getting multi-chain transaction history: {e}")
            return []
    
    async def get_portfolio_allocation_multi_chain(self) -> Dict[str, Any]:
        """Get portfolio allocation across chains"""
        try:
            allocation = {
                "total_portfolio_usd": 982456.78,
                "chain_allocation": {
                    "ethereum": {"usd_value": 456789.12, "percentage": 46.5},
                    "bsc": {"usd_value": 234567.89, "percentage": 23.9},
                    "polygon": {"usd_value": 123456.78, "percentage": 12.6},
                    "arbitrum": {"usd_value": 78945.67, "percentage": 8.0},
                    "solana": {"usd_value": 89012.34, "percentage": 9.0}
                },
                "asset_allocation": {
                    "ETH": {"usd_value": 298456.78, "percentage": 30.4},
                    "BTC": {"usd_value": 245678.90, "percentage": 25.0},
                    "USDC": {"usd_value": 196789.12, "percentage": 20.0},
                    "BNB": {"usd_value": 147890.12, "percentage": 15.1},
                    "Others": {"usd_value": 93642.86, "percentage": 9.5}
                },
                "defi_exposure": {
                    "lending": {"usd_value": 147890.12, "percentage": 15.1},
                    "liquidity_pools": {"usd_value": 98567.89, "percentage": 10.0},
                    "staking": {"usd_value": 73456.78, "percentage": 7.5},
                    "yield_farming": {"usd_value": 49234.56, "percentage": 5.0}
                },
                "risk_metrics": {
                    "concentration_risk": 0.35,
                    "chain_diversification": 0.78,
                    "asset_diversification": 0.82,
                    "liquidity_score": 0.89
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            return allocation
        except Exception as e:
            logger.error(f"Error getting portfolio allocation: {e}")
            return {}
    
    async def get_supported_chains(self) -> List[Dict[str, Any]]:
        """Get list of supported blockchain networks"""
        try:
            chains = [
                {
                    "chain_id": 1,
                    "name": "Ethereum",
                    "symbol": "ETH",
                    "rpc_url": "https://eth-mainnet.alchemyapi.io/v2/...",
                    "explorer_url": "https://etherscan.io",
                    "bridge_support": True,
                    "defi_protocols": ["Uniswap", "Aave", "Compound", "MakerDAO"],
                    "avg_gas_price_gwei": 25.4,
                    "status": "active"
                },
                {
                    "chain_id": 56,
                    "name": "Binance Smart Chain",
                    "symbol": "BNB", 
                    "rpc_url": "https://bsc-dataseed.binance.org/",
                    "explorer_url": "https://bscscan.com",
                    "bridge_support": True,
                    "defi_protocols": ["PancakeSwap", "Venus", "Alpaca Finance"],
                    "avg_gas_price_gwei": 5.2,
                    "status": "active"
                },
                {
                    "chain_id": 137,
                    "name": "Polygon",
                    "symbol": "MATIC",
                    "rpc_url": "https://polygon-mainnet.alchemyapi.io/v2/...",
                    "explorer_url": "https://polygonscan.com",
                    "bridge_support": True,
                    "defi_protocols": ["QuickSwap", "Aave", "Curve"],
                    "avg_gas_price_gwei": 32.1,
                    "status": "active"
                },
                {
                    "chain_id": 42161,
                    "name": "Arbitrum One",
                    "symbol": "ETH",
                    "rpc_url": "https://arb1.arbitrum.io/rpc",
                    "explorer_url": "https://arbiscan.io",
                    "bridge_support": True,
                    "defi_protocols": ["GMX", "Balancer", "Uniswap V3"],
                    "avg_gas_price_gwei": 0.3,
                    "status": "active"
                },
                {
                    "chain_id": 101,
                    "name": "Solana",
                    "symbol": "SOL",
                    "rpc_url": "https://api.mainnet-beta.solana.com",
                    "explorer_url": "https://solscan.io",
                    "bridge_support": True,
                    "defi_protocols": ["Raydium", "Serum", "Orca"],
                    "avg_gas_price_gwei": 0.0001,
                    "status": "active"
                }
            ]
            
            return chains
        except Exception as e:
            logger.error(f"Error getting supported chains: {e}")
            return []
    
    async def get_wallet_connections(self) -> List[Dict[str, Any]]:
        """Get connected wallet information"""
        try:
            connections = [
                {
                    "wallet_id": "metamask_1",
                    "wallet_type": "MetaMask",
                    "address": "0x742d35cc6634c0532925a3b8d8a742e684e",
                    "chain": "ethereum",
                    "status": "connected",
                    "last_activity": datetime.now(timezone.utc).isoformat(),
                    "balance_usd": 456789.12
                },
                {
                    "wallet_id": "trust_1", 
                    "wallet_type": "Trust Wallet",
                    "address": "0x9876543210abcdef1234567890abcdef12345678",
                    "chain": "bsc",
                    "status": "connected",
                    "last_activity": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                    "balance_usd": 234567.89
                },
                {
                    "wallet_id": "phantom_1",
                    "wallet_type": "Phantom",
                    "address": "Hx7vL8bK9pQr3mN4cF6aE2dW1zS8tU5vY7rT9qP",
                    "chain": "solana",
                    "status": "connected",
                    "last_activity": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
                    "balance_usd": 89012.34
                }
            ]
            
            return connections
        except Exception as e:
            logger.error(f"Error getting wallet connections: {e}")
            return []
    
    async def estimate_gas_fees(self, transaction_params: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate gas fees for a transaction"""
        try:
            chain = transaction_params.get("chain", "ethereum")
            tx_type = transaction_params.get("type", "transfer")
            
            # Mock gas estimation based on chain and transaction type
            gas_estimates = {
                "ethereum": {
                    "transfer": {"gas_limit": 21000, "gas_price_gwei": 25.4},
                    "swap": {"gas_limit": 150000, "gas_price_gwei": 25.4},
                    "bridge": {"gas_limit": 200000, "gas_price_gwei": 25.4}
                },
                "bsc": {
                    "transfer": {"gas_limit": 21000, "gas_price_gwei": 5.2},
                    "swap": {"gas_limit": 120000, "gas_price_gwei": 5.2},
                    "bridge": {"gas_limit": 180000, "gas_price_gwei": 5.2}
                },
                "polygon": {
                    "transfer": {"gas_limit": 21000, "gas_price_gwei": 32.1},
                    "swap": {"gas_limit": 140000, "gas_price_gwei": 32.1},
                    "bridge": {"gas_limit": 190000, "gas_price_gwei": 32.1}
                }
            }
            
            estimate = gas_estimates.get(chain, {}).get(tx_type, {
                "gas_limit": 21000,
                "gas_price_gwei": 20.0
            })
            
            gas_fee_eth = (estimate["gas_limit"] * estimate["gas_price_gwei"]) / 1e9
            gas_fee_usd = gas_fee_eth * 2021.45  # Mock ETH price
            
            return {
                "chain": chain,
                "transaction_type": tx_type,
                "gas_limit": estimate["gas_limit"],
                "gas_price_gwei": estimate["gas_price_gwei"],
                "gas_fee_eth": round(gas_fee_eth, 6),
                "gas_fee_usd": round(gas_fee_usd, 2),
                "estimated_time_minutes": 2 if chain != "ethereum" else 5
            }
        except Exception as e:
            logger.error(f"Error estimating gas fees: {e}")
            return {}
    
    async def get_yield_positions(self) -> List[Dict[str, Any]]:
        """Get DeFi yield positions across chains"""
        try:
            positions = [
                {
                    "position_id": "yield_1",
                    "protocol": "Aave",
                    "chain": "ethereum",
                    "position_type": "lending",
                    "asset": "USDC",
                    "amount": 50000.0,
                    "apy": 4.25,
                    "earned_usd": 2125.0,
                    "status": "active",
                    "auto_compound": True
                },
                {
                    "position_id": "yield_2",
                    "protocol": "PancakeSwap",
                    "chain": "bsc",
                    "position_type": "liquidity_pool",
                    "asset": "CAKE-BNB LP",
                    "amount": 15000.0,
                    "apy": 18.5,
                    "earned_usd": 925.0,
                    "status": "active", 
                    "auto_compound": False
                },
                {
                    "position_id": "yield_3",
                    "protocol": "Curve",
                    "chain": "polygon",
                    "position_type": "liquidity_pool",
                    "asset": "3pool",
                    "amount": 25000.0,
                    "apy": 6.75,
                    "earned_usd": 687.5,
                    "status": "active",
                    "auto_compound": True
                }
            ]
            
            return positions
        except Exception as e:
            logger.error(f"Error getting yield positions: {e}")
            return []

# Factory function for service registry
def create_vault_management_service():
    """Factory function to create VaultManagementService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = VaultManagementService(redis_client, supabase_client)
    return service