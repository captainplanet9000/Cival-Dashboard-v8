"""
Master Wallet Data Models - Phase 6
Comprehensive wallet management for autonomous trading agents
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone
from decimal import Decimal
import uuid

class WalletAddress(BaseModel):
    """Wallet address with chain information"""
    address: str = Field(..., description="Wallet address")
    chain_id: int = Field(..., description="Blockchain chain ID")
    chain_name: str = Field(..., description="Blockchain name (ETH, BSC, Polygon, etc.)")
    is_active: bool = Field(default=True, description="Whether address is active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WalletBalance(BaseModel):
    """Wallet balance for specific asset"""
    asset_symbol: str = Field(..., description="Asset symbol (ETH, USDC, BTC, etc.)")
    balance: Decimal = Field(..., description="Current balance")
    balance_usd: Optional[Decimal] = Field(None, description="USD value of balance")
    locked_balance: Decimal = Field(default=Decimal("0"), description="Locked/reserved balance")
    available_balance: Decimal = Field(..., description="Available balance for trading")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('available_balance', always=True)
    def calculate_available_balance(cls, v, values):
        """Calculate available balance"""
        balance = values.get('balance', Decimal("0"))
        locked = values.get('locked_balance', Decimal("0"))
        return balance - locked

class MasterWalletConfig(BaseModel):
    """Master wallet configuration"""
    wallet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Wallet name/identifier")
    description: Optional[str] = Field(None, description="Wallet description")
    
    # Multi-chain configuration
    primary_chain: str = Field(default="ethereum", description="Primary blockchain")
    supported_chains: List[str] = Field(default_factory=lambda: ["ethereum", "polygon", "bsc"])
    
    # Fund management settings
    auto_distribution: bool = Field(default=True, description="Enable automatic fund distribution")
    performance_based_allocation: bool = Field(default=True, description="Use performance-based allocation")
    risk_based_limits: bool = Field(default=True, description="Apply risk-based position limits")
    
    # Safety settings
    max_allocation_per_agent: Decimal = Field(default=Decimal("0.1"), description="Max % of funds per agent")
    emergency_stop_threshold: Decimal = Field(default=Decimal("0.2"), description="Emergency stop at % loss")
    daily_loss_limit: Decimal = Field(default=Decimal("0.05"), description="Daily loss limit %")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FundAllocation(BaseModel):
    """Fund allocation to agent/farm/goal"""
    allocation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Allocation target
    target_type: Literal["agent", "farm", "goal"] = Field(..., description="Allocation target type")
    target_id: str = Field(..., description="Target ID (agent_id, farm_id, goal_id)")
    target_name: str = Field(..., description="Target name for display")
    
    # Allocation details
    allocated_amount_usd: Decimal = Field(..., description="Allocated amount in USD")
    allocated_percentage: Decimal = Field(..., description="Percentage of total funds")
    current_value_usd: Decimal = Field(..., description="Current value in USD")
    
    # Performance tracking
    initial_allocation: Decimal = Field(..., description="Initial allocation amount")
    total_pnl: Decimal = Field(default=Decimal("0"), description="Total P&L")
    unrealized_pnl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L")
    
    # Risk metrics
    max_drawdown: Decimal = Field(default=Decimal("0"), description="Maximum drawdown")
    current_drawdown: Decimal = Field(default=Decimal("0"), description="Current drawdown")
    risk_score: Optional[float] = Field(None, description="Risk score (0-100)")
    
    # Status
    is_active: bool = Field(default=True, description="Whether allocation is active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FundDistributionRule(BaseModel):
    """Rules for automatic fund distribution"""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_name: str = Field(..., description="Rule name")
    
    # Trigger conditions
    trigger_type: Literal["performance", "time", "event", "manual"] = Field(..., description="Trigger type")
    trigger_conditions: Dict[str, Any] = Field(default_factory=dict, description="Trigger conditions")
    
    # Distribution logic
    distribution_method: Literal["equal", "performance_weighted", "risk_adjusted", "custom"] = Field(
        default="performance_weighted", description="Distribution method"
    )
    distribution_parameters: Dict[str, Any] = Field(default_factory=dict, description="Distribution parameters")
    
    # Constraints
    min_allocation_usd: Decimal = Field(default=Decimal("100"), description="Minimum allocation per target")
    max_allocation_usd: Optional[Decimal] = Field(None, description="Maximum allocation per target")
    max_targets: Optional[int] = Field(None, description="Maximum number of targets")
    
    # Status
    is_active: bool = Field(default=True, description="Whether rule is active")
    priority: int = Field(default=1, description="Rule priority (1-10)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WalletTransaction(BaseModel):
    """Wallet transaction record"""
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Transaction details
    transaction_type: Literal["deposit", "withdrawal", "allocation", "collection", "transfer", "fee"] = Field(
        ..., description="Transaction type"
    )
    amount: Decimal = Field(..., description="Transaction amount")
    asset_symbol: str = Field(..., description="Asset symbol")
    amount_usd: Optional[Decimal] = Field(None, description="USD value at time of transaction")
    
    # Source and destination
    from_address: Optional[str] = Field(None, description="Source address")
    to_address: Optional[str] = Field(None, description="Destination address")
    from_entity: Optional[str] = Field(None, description="Source entity (agent_id, farm_id, etc.)")
    to_entity: Optional[str] = Field(None, description="Destination entity")
    
    # Blockchain details
    chain_id: Optional[int] = Field(None, description="Blockchain chain ID")
    tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    block_number: Optional[int] = Field(None, description="Block number")
    gas_used: Optional[Decimal] = Field(None, description="Gas used")
    gas_price: Optional[Decimal] = Field(None, description="Gas price")
    
    # Status and metadata
    status: Literal["pending", "confirmed", "failed", "cancelled"] = Field(default="pending")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")

class WalletPerformanceMetrics(BaseModel):
    """Wallet performance metrics"""
    wallet_id: str = Field(..., description="Wallet ID")
    
    # Performance metrics
    total_value_usd: Decimal = Field(..., description="Total wallet value in USD")
    total_pnl: Decimal = Field(..., description="Total P&L")
    total_pnl_percentage: Decimal = Field(..., description="Total P&L percentage")
    
    # Time-based performance
    daily_pnl: Decimal = Field(default=Decimal("0"), description="Daily P&L")
    weekly_pnl: Decimal = Field(default=Decimal("0"), description="Weekly P&L")
    monthly_pnl: Decimal = Field(default=Decimal("0"), description="Monthly P&L")
    
    # Risk metrics
    max_drawdown: Decimal = Field(default=Decimal("0"), description="Maximum drawdown")
    current_drawdown: Decimal = Field(default=Decimal("0"), description="Current drawdown")
    volatility: Optional[Decimal] = Field(None, description="Portfolio volatility")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio")
    
    # Activity metrics
    total_trades: int = Field(default=0, description="Total number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")
    win_rate: Decimal = Field(default=Decimal("0"), description="Win rate percentage")
    
    # Allocation metrics
    active_allocations: int = Field(default=0, description="Number of active allocations")
    total_allocated_usd: Decimal = Field(default=Decimal("0"), description="Total allocated amount")
    available_balance_usd: Decimal = Field(default=Decimal("0"), description="Available balance")
    
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MasterWallet(BaseModel):
    """Complete master wallet model"""
    wallet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    config: MasterWalletConfig = Field(..., description="Wallet configuration")
    
    # Wallet addresses
    addresses: List[WalletAddress] = Field(default_factory=list, description="Wallet addresses")
    
    # Current balances
    balances: List[WalletBalance] = Field(default_factory=list, description="Current balances")
    
    # Active allocations
    allocations: List[FundAllocation] = Field(default_factory=list, description="Active fund allocations")
    
    # Distribution rules
    distribution_rules: List[FundDistributionRule] = Field(
        default_factory=list, description="Fund distribution rules"
    )
    
    # Performance metrics
    performance: Optional[WalletPerformanceMetrics] = Field(None, description="Performance metrics")
    
    # Status
    is_active: bool = Field(default=True, description="Whether wallet is active")
    last_distribution: Optional[datetime] = Field(None, description="Last distribution timestamp")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request/Response models for API

class CreateMasterWalletRequest(BaseModel):
    """Request to create a new master wallet"""
    config: MasterWalletConfig = Field(..., description="Wallet configuration")
    initial_addresses: Optional[List[WalletAddress]] = Field(None, description="Initial wallet addresses")
    initial_balances: Optional[List[WalletBalance]] = Field(None, description="Initial balances")

class UpdateWalletConfigRequest(BaseModel):
    """Request to update wallet configuration"""
    name: Optional[str] = None
    description: Optional[str] = None
    auto_distribution: Optional[bool] = None
    performance_based_allocation: Optional[bool] = None
    risk_based_limits: Optional[bool] = None
    max_allocation_per_agent: Optional[Decimal] = None
    emergency_stop_threshold: Optional[Decimal] = None
    daily_loss_limit: Optional[Decimal] = None

class FundAllocationRequest(BaseModel):
    """Request to allocate funds"""
    target_type: Literal["agent", "farm", "goal"] = Field(..., description="Allocation target type")
    target_id: str = Field(..., description="Target ID")
    target_name: str = Field(..., description="Target name")
    amount_usd: Decimal = Field(..., description="Amount to allocate in USD")
    allocation_method: Literal["fixed", "percentage"] = Field(default="fixed", description="Allocation method")

class FundCollectionRequest(BaseModel):
    """Request to collect funds from allocation"""
    allocation_id: str = Field(..., description="Allocation ID to collect from")
    collection_type: Literal["partial", "full", "profits_only"] = Field(..., description="Collection type")
    amount_usd: Optional[Decimal] = Field(None, description="Amount to collect (for partial)")

class WalletTransferRequest(BaseModel):
    """Request to transfer funds between wallets"""
    from_wallet_id: str = Field(..., description="Source wallet ID")
    to_wallet_id: str = Field(..., description="Destination wallet ID")
    asset_symbol: str = Field(..., description="Asset to transfer")
    amount: Decimal = Field(..., description="Amount to transfer")
    transfer_reason: Optional[str] = Field(None, description="Reason for transfer")

# Response models

class MasterWalletResponse(BaseModel):
    """Master wallet response"""
    wallet: MasterWallet = Field(..., description="Master wallet data")
    status: str = Field(default="success", description="Response status")
    message: Optional[str] = Field(None, description="Response message")

class WalletBalanceResponse(BaseModel):
    """Wallet balance response"""
    wallet_id: str = Field(..., description="Wallet ID")
    balances: List[WalletBalance] = Field(..., description="Current balances")
    total_value_usd: Decimal = Field(..., description="Total value in USD")
    last_updated: datetime = Field(..., description="Last update timestamp")

class AllocationResponse(BaseModel):
    """Fund allocation response"""
    allocation: FundAllocation = Field(..., description="Allocation details")
    transaction_id: Optional[str] = Field(None, description="Transaction ID if applicable")
    status: str = Field(default="success", description="Response status")
    message: Optional[str] = Field(None, description="Response message")

class WalletPerformanceResponse(BaseModel):
    """Wallet performance response"""
    wallet_id: str = Field(..., description="Wallet ID")
    performance: WalletPerformanceMetrics = Field(..., description="Performance metrics")
    allocations_performance: List[FundAllocation] = Field(..., description="Individual allocation performance")
    status: str = Field(default="success", description="Response status")