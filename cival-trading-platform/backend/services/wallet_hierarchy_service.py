"""
Wallet Hierarchy Service - Phase 2 Implementation
Manages Master Wallet → Farm Wallets → Agent Wallets architecture
"""

import uuid
from typing import List, Dict, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from core.database_manager import DatabaseManager
from models.database_models import (
    FarmDB, GoalDB, MasterWalletConfigDB, FundAllocationDB, 
    WalletTransactionDB, AgentFarmAssignmentDB
)


class AllocationMethod(Enum):
    MANUAL = "manual"
    PERFORMANCE_BASED = "performance_based"
    EQUAL_WEIGHT = "equal_weight"
    RISK_ADJUSTED = "risk_adjusted"


class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal" 
    ALLOCATION = "allocation"
    COLLECTION = "collection"
    TRANSFER = "transfer"
    FEE = "fee"
    REWARD = "reward"


@dataclass
class WalletAllocationRequest:
    target_type: str  # 'agent', 'farm', 'goal'
    target_id: str
    amount_usd: Decimal
    allocation_method: AllocationMethod = AllocationMethod.MANUAL
    metadata: Dict[str, Any] = None


@dataclass
class WalletPerformanceMetrics:
    total_value_usd: Decimal
    total_pnl: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    allocation_count: int
    performance_score: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None


class WalletHierarchyService:
    """
    Core service for managing wallet hierarchy and fund allocation
    Handles Master Wallet → Farm Wallets → Agent Wallets flow
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    async def create_master_wallet(
        self, 
        wallet_id: str,
        name: str,
        description: str = "",
        configuration: Dict[str, Any] = None,
        auto_distribution: bool = True
    ) -> str:
        """Create a new master wallet configuration"""
        
        async with self.db_manager.get_session() as session:
            # Check if wallet already has a config
            existing = session.query(MasterWalletConfigDB).filter(
                MasterWalletConfigDB.wallet_id == wallet_id
            ).first()
            
            if existing:
                raise ValueError(f"Master wallet config already exists for wallet {wallet_id}")
            
            # Create master wallet configuration
            master_config = MasterWalletConfigDB(
                wallet_id=wallet_id,
                name=name,
                description=description,
                configuration=configuration or {},
                auto_distribution_enabled=auto_distribution,
                emergency_stop_enabled=False,
                risk_settings={
                    "max_allocation_per_entity": 0.25,
                    "daily_loss_limit": 0.05,
                    "emergency_stop_threshold": 0.15
                },
                performance_metrics={},
                is_active=True
            )
            
            session.add(master_config)
            session.commit()
            session.refresh(master_config)
            
            return str(master_config.config_id)
    
    async def allocate_funds(
        self,
        source_wallet_id: str,
        allocations: List[WalletAllocationRequest]
    ) -> List[str]:
        """Allocate funds from master wallet to farms/agents/goals"""
        
        async with self.db_manager.get_session() as session:
            # Verify master wallet exists and is active
            master_config = session.query(MasterWalletConfigDB).filter(
                and_(
                    MasterWalletConfigDB.wallet_id == source_wallet_id,
                    MasterWalletConfigDB.is_active == True
                )
            ).first()
            
            if not master_config:
                raise ValueError(f"Active master wallet not found: {source_wallet_id}")
            
            # Check if auto distribution is enabled or emergency stop
            if master_config.emergency_stop_enabled:
                raise ValueError("Emergency stop enabled - fund allocation blocked")
            
            allocation_ids = []
            total_allocated = Decimal('0')
            
            for request in allocations:
                # Validate allocation amount
                if request.amount_usd <= 0:
                    raise ValueError(f"Invalid allocation amount: {request.amount_usd}")
                
                total_allocated += request.amount_usd
                
                # Create fund allocation record
                allocation = FundAllocationDB(
                    source_wallet_id=source_wallet_id,
                    target_type=request.target_type,
                    target_id=request.target_id,
                    target_name=self._get_target_name(session, request.target_type, request.target_id),
                    allocated_amount_usd=request.amount_usd,
                    current_value_usd=request.amount_usd,
                    initial_allocation_usd=request.amount_usd,
                    allocation_method=request.allocation_method.value,
                    performance_metrics=request.metadata or {},
                    is_active=True
                )
                
                session.add(allocation)
                session.flush()  # Get the ID
                allocation_ids.append(str(allocation.allocation_id))
                
                # Create transaction record
                transaction = WalletTransactionDB(
                    wallet_id=source_wallet_id,
                    transaction_type=TransactionType.ALLOCATION.value,
                    amount=request.amount_usd,
                    amount_usd=request.amount_usd,
                    from_entity=f"wallet_{source_wallet_id}",
                    to_entity=f"{request.target_type}_{request.target_id}",
                    metadata={
                        "allocation_id": str(allocation.allocation_id),
                        "allocation_method": request.allocation_method.value,
                        **request.metadata or {}
                    },
                    status="confirmed"
                )
                
                session.add(transaction)
            
            session.commit()
            
            # Update master wallet performance metrics
            await self._update_master_wallet_metrics(source_wallet_id)
            
            return allocation_ids
    
    async def get_wallet_hierarchy(self, master_wallet_id: str) -> Dict[str, Any]:
        """Get complete wallet hierarchy structure"""
        
        async with self.db_manager.get_session() as session:
            # Get master wallet config
            master_config = session.query(MasterWalletConfigDB).filter(
                MasterWalletConfigDB.wallet_id == master_wallet_id
            ).first()
            
            if not master_config:
                raise ValueError(f"Master wallet not found: {master_wallet_id}")
            
            # Get all allocations
            allocations = session.query(FundAllocationDB).filter(
                and_(
                    FundAllocationDB.source_wallet_id == master_wallet_id,
                    FundAllocationDB.is_active == True
                )
            ).all()
            
            # Group allocations by type
            hierarchy = {
                "master_wallet": {
                    "config_id": str(master_config.config_id),
                    "wallet_id": master_wallet_id,
                    "name": master_config.name,
                    "description": master_config.description,
                    "auto_distribution_enabled": master_config.auto_distribution_enabled,
                    "emergency_stop_enabled": master_config.emergency_stop_enabled,
                    "performance_metrics": master_config.performance_metrics,
                    "risk_settings": master_config.risk_settings
                },
                "farms": [],
                "agents": [],
                "goals": [],
                "total_allocated_usd": Decimal('0'),
                "allocation_breakdown": {}
            }
            
            for allocation in allocations:
                allocation_data = {
                    "allocation_id": str(allocation.allocation_id),
                    "target_id": allocation.target_id,
                    "target_name": allocation.target_name,
                    "allocated_amount_usd": allocation.allocated_amount_usd,
                    "current_value_usd": allocation.current_value_usd,
                    "total_pnl": allocation.total_pnl,
                    "allocation_method": allocation.allocation_method,
                    "performance_metrics": allocation.performance_metrics,
                    "created_at": allocation.created_at
                }
                
                hierarchy[f"{allocation.target_type}s"].append(allocation_data)
                hierarchy["total_allocated_usd"] += allocation.allocated_amount_usd
                
                # Track allocation breakdown
                if allocation.target_type not in hierarchy["allocation_breakdown"]:
                    hierarchy["allocation_breakdown"][allocation.target_type] = {
                        "count": 0,
                        "total_usd": Decimal('0')
                    }
                
                hierarchy["allocation_breakdown"][allocation.target_type]["count"] += 1
                hierarchy["allocation_breakdown"][allocation.target_type]["total_usd"] += allocation.allocated_amount_usd
            
            return hierarchy
    
    async def collect_funds_from_goal(
        self,
        goal_id: str,
        master_wallet_id: str,
        collection_percentage: float = 1.0
    ) -> str:
        """Collect funds from completed goal back to master wallet"""
        
        async with self.db_manager.get_session() as session:
            # Find goal allocation
            allocation = session.query(FundAllocationDB).filter(
                and_(
                    FundAllocationDB.source_wallet_id == master_wallet_id,
                    FundAllocationDB.target_type == "goal",
                    FundAllocationDB.target_id == goal_id,
                    FundAllocationDB.is_active == True
                )
            ).first()
            
            if not allocation:
                raise ValueError(f"Goal allocation not found: {goal_id}")
            
            # Calculate collection amount
            collection_amount = allocation.current_value_usd * Decimal(str(collection_percentage))
            
            # Create collection transaction
            transaction = WalletTransactionDB(
                wallet_id=master_wallet_id,
                transaction_type=TransactionType.COLLECTION.value,
                amount=collection_amount,
                amount_usd=collection_amount,
                from_entity=f"goal_{goal_id}",
                to_entity=f"wallet_{master_wallet_id}",
                metadata={
                    "allocation_id": str(allocation.allocation_id),
                    "collection_percentage": collection_percentage,
                    "original_allocation": float(allocation.allocated_amount_usd),
                    "pnl": float(allocation.total_pnl)
                },
                status="confirmed"
            )
            
            session.add(transaction)
            
            # Update allocation status if fully collected
            if collection_percentage >= 1.0:
                allocation.is_active = False
            else:
                allocation.current_value_usd -= collection_amount
            
            session.commit()
            session.refresh(transaction)
            
            return str(transaction.transaction_id)
    
    async def get_performance_metrics(self, wallet_id: str) -> WalletPerformanceMetrics:
        """Get comprehensive performance metrics for wallet"""
        
        async with self.db_manager.get_session() as session:
            # Get all active allocations
            allocations = session.query(FundAllocationDB).filter(
                and_(
                    FundAllocationDB.source_wallet_id == wallet_id,
                    FundAllocationDB.is_active == True
                )
            ).all()
            
            if not allocations:
                return WalletPerformanceMetrics(
                    total_value_usd=Decimal('0'),
                    total_pnl=Decimal('0'),
                    unrealized_pnl=Decimal('0'),
                    realized_pnl=Decimal('0'),
                    allocation_count=0,
                    performance_score=0.0
                )
            
            # Calculate metrics
            total_value = sum(a.current_value_usd for a in allocations)
            total_pnl = sum(a.total_pnl for a in allocations)
            unrealized_pnl = sum(a.unrealized_pnl for a in allocations)
            realized_pnl = sum(a.realized_pnl for a in allocations)
            
            # Calculate performance score (simple ROI-based)
            total_initial = sum(a.initial_allocation_usd for a in allocations)
            performance_score = float(total_pnl / total_initial) if total_initial > 0 else 0.0
            
            return WalletPerformanceMetrics(
                total_value_usd=total_value,
                total_pnl=total_pnl,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=realized_pnl,
                allocation_count=len(allocations),
                performance_score=performance_score
            )
    
    async def rebalance_allocations(
        self,
        master_wallet_id: str,
        method: AllocationMethod = AllocationMethod.PERFORMANCE_BASED
    ) -> Dict[str, Any]:
        """Rebalance fund allocations based on performance"""
        
        async with self.db_manager.get_session() as session:
            # Get current allocations
            allocations = session.query(FundAllocationDB).filter(
                and_(
                    FundAllocationDB.source_wallet_id == master_wallet_id,
                    FundAllocationDB.is_active == True
                )
            ).all()
            
            if not allocations:
                return {"message": "No active allocations to rebalance"}
            
            rebalance_results = {
                "method": method.value,
                "allocations_processed": len(allocations),
                "adjustments": [],
                "total_adjustment": Decimal('0')
            }
            
            if method == AllocationMethod.PERFORMANCE_BASED:
                # Sort by performance (PnL ratio)
                allocation_performance = []
                for allocation in allocations:
                    pnl_ratio = float(allocation.total_pnl / allocation.initial_allocation_usd) if allocation.initial_allocation_usd > 0 else 0
                    allocation_performance.append((allocation, pnl_ratio))
                
                # Sort by performance descending
                allocation_performance.sort(key=lambda x: x[1], reverse=True)
                
                # Rebalance: increase allocation to top performers, decrease for poor performers
                total_allocation = sum(a.current_value_usd for a in allocations)
                avg_performance = sum(perf for _, perf in allocation_performance) / len(allocation_performance)
                
                for allocation, performance in allocation_performance:
                    # Calculate adjustment based on performance deviation
                    performance_delta = performance - avg_performance
                    adjustment_factor = min(0.1, abs(performance_delta))  # Max 10% adjustment
                    
                    if performance_delta > 0:  # Above average performance
                        adjustment = allocation.current_value_usd * Decimal(str(adjustment_factor))
                    else:  # Below average performance
                        adjustment = -allocation.current_value_usd * Decimal(str(adjustment_factor))
                    
                    # Apply adjustment
                    new_value = allocation.current_value_usd + adjustment
                    allocation.current_value_usd = max(Decimal('0'), new_value)
                    
                    rebalance_results["adjustments"].append({
                        "allocation_id": str(allocation.allocation_id),
                        "target": f"{allocation.target_type}_{allocation.target_id}",
                        "performance": performance,
                        "adjustment_usd": float(adjustment),
                        "new_value_usd": float(allocation.current_value_usd)
                    })
                    
                    rebalance_results["total_adjustment"] += abs(adjustment)
            
            session.commit()
            return rebalance_results
    
    def _get_target_name(self, session: Session, target_type: str, target_id: str) -> Optional[str]:
        """Get the name of the allocation target"""
        try:
            if target_type == "farm":
                farm = session.query(FarmDB).filter(FarmDB.farm_id == target_id).first()
                return farm.name if farm else f"Farm {target_id[:8]}"
            elif target_type == "goal":
                goal = session.query(GoalDB).filter(GoalDB.goal_id == target_id).first()
                return goal.name if goal else f"Goal {target_id[:8]}"
            elif target_type == "agent":
                return f"Agent {target_id[:8]}"
            else:
                return f"{target_type.title()} {target_id[:8]}"
        except Exception:
            return f"{target_type.title()} {target_id[:8]}"
    
    async def _update_master_wallet_metrics(self, wallet_id: str):
        """Update performance metrics for master wallet"""
        
        async with self.db_manager.get_session() as session:
            config = session.query(MasterWalletConfigDB).filter(
                MasterWalletConfigDB.wallet_id == wallet_id
            ).first()
            
            if not config:
                return
            
            # Get performance metrics
            metrics = await self.get_performance_metrics(wallet_id)
            
            # Update config with latest metrics
            config.performance_metrics = {
                "total_value_usd": float(metrics.total_value_usd),
                "total_pnl": float(metrics.total_pnl),
                "allocation_count": metrics.allocation_count,
                "performance_score": metrics.performance_score,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            session.commit()


class WalletTransactionService:
    """
    Service for managing wallet transactions and history
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_transaction_history(
        self,
        wallet_id: str,
        limit: int = 100,
        transaction_types: List[TransactionType] = None
    ) -> List[Dict[str, Any]]:
        """Get transaction history for wallet"""
        
        async with self.db_manager.get_session() as session:
            query = session.query(WalletTransactionDB).filter(
                WalletTransactionDB.wallet_id == wallet_id
            )
            
            if transaction_types:
                type_values = [t.value for t in transaction_types]
                query = query.filter(WalletTransactionDB.transaction_type.in_(type_values))
            
            transactions = query.order_by(desc(WalletTransactionDB.created_at)).limit(limit).all()
            
            return [
                {
                    "transaction_id": str(tx.transaction_id),
                    "transaction_type": tx.transaction_type,
                    "amount": float(tx.amount),
                    "amount_usd": float(tx.amount_usd) if tx.amount_usd else None,
                    "from_entity": tx.from_entity,
                    "to_entity": tx.to_entity,
                    "status": tx.status,
                    "metadata": tx.metadata,
                    "created_at": tx.created_at,
                    "confirmed_at": tx.confirmed_at
                }
                for tx in transactions
            ]
    
    async def create_transaction(
        self,
        wallet_id: str,
        transaction_type: TransactionType,
        amount: Decimal,
        amount_usd: Decimal = None,
        from_entity: str = None,
        to_entity: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a new wallet transaction"""
        
        async with self.db_manager.get_session() as session:
            transaction = WalletTransactionDB(
                wallet_id=wallet_id,
                transaction_type=transaction_type.value,
                amount=amount,
                amount_usd=amount_usd or amount,
                from_entity=from_entity,
                to_entity=to_entity,
                metadata=metadata or {},
                status="pending"
            )
            
            session.add(transaction)
            session.commit()
            session.refresh(transaction)
            
            return str(transaction.transaction_id)