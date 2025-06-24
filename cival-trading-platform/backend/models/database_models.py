"""
SQLAlchemy Database Models for Wallet-Farm-Goal Integration
Complete database models matching Supabase schema
"""

from sqlalchemy import Column, String, Text, Integer, Decimal, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class FarmDB(Base):
    """Farm management table"""
    __tablename__ = 'farms'
    
    farm_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    farm_type = Column(String(100), nullable=False)  # 'trend_following', 'breakout', 'price_action'
    configuration = Column(JSONB, nullable=False, default={})
    wallet_address = Column(String(255))
    total_allocated_usd = Column(Decimal(20, 8), default=0)
    performance_metrics = Column(JSONB, default={})
    risk_metrics = Column(JSONB, default={})
    agent_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent_assignments = relationship("AgentFarmAssignmentDB", back_populates="farm", cascade="all, delete-orphan")
    goal_assignments = relationship("FarmGoalAssignmentDB", back_populates="farm", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_farms_farm_type', 'farm_type'),
        Index('idx_farms_is_active', 'is_active'),
        Index('idx_farms_created_at', 'created_at'),
    )

class GoalDB(Base):
    """Goal management table"""
    __tablename__ = 'goals'
    
    goal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    goal_type = Column(String(100), nullable=False)  # 'trade_volume', 'profit_target', 'strategy_performance'
    target_criteria = Column(JSONB, nullable=False)  # {"trades": 200, "profit_per_trade": 5}
    current_progress = Column(JSONB, default={})
    assigned_entities = Column(JSONB, default=[])  # [{"type": "farm", "id": "..."}, {"type": "agent", "id": "..."}]
    completion_status = Column(String(50), default='active')  # 'active', 'completed', 'failed', 'paused'
    completion_percentage = Column(Decimal(5, 2), default=0)
    wallet_allocation_usd = Column(Decimal(20, 8), default=0)
    priority = Column(Integer, default=1)  # 1-10 priority scale
    deadline = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    farm_assignments = relationship("FarmGoalAssignmentDB", back_populates="goal", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_goals_goal_type', 'goal_type'),
        Index('idx_goals_completion_status', 'completion_status'),
        Index('idx_goals_priority', 'priority'),
        Index('idx_goals_deadline', 'deadline'),
    )

class MasterWalletDB(Base):
    """Master wallet table"""
    __tablename__ = 'master_wallets'
    
    wallet_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    configuration = Column(JSONB, nullable=False, default={})
    addresses = Column(JSONB, default=[])  # Multi-chain addresses
    balances = Column(JSONB, default={})  # Current balances by asset
    total_value_usd = Column(Decimal(20, 8), default=0)
    performance_metrics = Column(JSONB, default={})
    risk_settings = Column(JSONB, default={})
    auto_distribution_enabled = Column(Boolean, default=True)
    emergency_stop_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    fund_allocations = relationship("FundAllocationDB", back_populates="wallet", cascade="all, delete-orphan")
    transactions = relationship("WalletTransactionDB", back_populates="wallet", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_master_wallets_is_active', 'is_active'),
        Index('idx_master_wallets_total_value', 'total_value_usd'),
    )

class FundAllocationDB(Base):
    """Fund allocation table"""
    __tablename__ = 'fund_allocations'
    
    allocation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('master_wallets.wallet_id', ondelete='CASCADE'), nullable=False)
    target_type = Column(String(50), nullable=False)  # 'agent', 'farm', 'goal'
    target_id = Column(UUID(as_uuid=True), nullable=False)
    target_name = Column(String(255))
    allocated_amount_usd = Column(Decimal(20, 8), nullable=False)
    allocated_percentage = Column(Decimal(5, 2))
    current_value_usd = Column(Decimal(20, 8))
    initial_allocation_usd = Column(Decimal(20, 8))
    total_pnl = Column(Decimal(20, 8), default=0)
    unrealized_pnl = Column(Decimal(20, 8), default=0)
    realized_pnl = Column(Decimal(20, 8), default=0)
    performance_metrics = Column(JSONB, default={})
    allocation_method = Column(String(100))  # 'manual', 'performance_based', 'equal_weight'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    wallet = relationship("MasterWalletDB", back_populates="fund_allocations")
    
    # Indexes
    __table_args__ = (
        Index('idx_fund_allocations_wallet_id', 'wallet_id'),
        Index('idx_fund_allocations_target_type', 'target_type'),
        Index('idx_fund_allocations_target_id', 'target_id'),
        Index('idx_fund_allocations_is_active', 'is_active'),
    )

class WalletTransactionDB(Base):
    """Wallet transaction table"""
    __tablename__ = 'wallet_transactions'
    
    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey('master_wallets.wallet_id', ondelete='CASCADE'))
    transaction_type = Column(String(100), nullable=False)
    amount = Column(Decimal(20, 8), nullable=False)
    asset_symbol = Column(String(20))
    amount_usd = Column(Decimal(20, 8))
    from_entity = Column(String(255))
    to_entity = Column(String(255))
    from_address = Column(String(255))
    to_address = Column(String(255))
    blockchain_data = Column(JSONB, default={})  # tx_hash, block_number, gas_used, etc.
    status = Column(String(50), default='pending')
    error_message = Column(Text)
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True))
    
    # Relationships
    wallet = relationship("MasterWalletDB", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index('idx_wallet_transactions_wallet_id', 'wallet_id'),
        Index('idx_wallet_transactions_transaction_type', 'transaction_type'),
        Index('idx_wallet_transactions_status', 'status'),
        Index('idx_wallet_transactions_created_at', 'created_at'),
    )

class AgentFarmAssignmentDB(Base):
    """Agent-Farm assignment table"""
    __tablename__ = 'agent_farm_assignments'
    
    assignment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), nullable=False)
    farm_id = Column(UUID(as_uuid=True), ForeignKey('farms.farm_id', ondelete='CASCADE'), nullable=False)
    role = Column(String(100))  # 'primary', 'secondary', 'specialist', 'coordinator'
    allocated_funds_usd = Column(Decimal(20, 8), default=0)
    performance_contribution = Column(JSONB, default={})
    assignment_weight = Column(Decimal(3, 2), default=1.0)  # How much this agent contributes to farm
    is_active = Column(Boolean, default=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    farm = relationship("FarmDB", back_populates="agent_assignments")
    
    # Indexes
    __table_args__ = (
        Index('idx_agent_farm_assignments_agent_id', 'agent_id'),
        Index('idx_agent_farm_assignments_farm_id', 'farm_id'),
        Index('idx_agent_farm_assignments_is_active', 'is_active'),
    )

class FarmGoalAssignmentDB(Base):
    """Farm-Goal assignment table"""
    __tablename__ = 'farm_goal_assignments'
    
    assignment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey('farms.farm_id', ondelete='CASCADE'), nullable=False)
    goal_id = Column(UUID(as_uuid=True), ForeignKey('goals.goal_id', ondelete='CASCADE'), nullable=False)
    contribution_weight = Column(Decimal(3, 2), default=1.0)  # How much this farm contributes to goal
    target_metrics = Column(JSONB, default={})
    current_metrics = Column(JSONB, default={})
    progress_percentage = Column(Decimal(5, 2), default=0)
    is_active = Column(Boolean, default=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    farm = relationship("FarmDB", back_populates="goal_assignments")
    goal = relationship("GoalDB", back_populates="farm_assignments")
    
    # Indexes
    __table_args__ = (
        Index('idx_farm_goal_assignments_farm_id', 'farm_id'),
        Index('idx_farm_goal_assignments_goal_id', 'goal_id'),
        Index('idx_farm_goal_assignments_is_active', 'is_active'),
    )

# Enhanced Agent Configuration Model (extending existing)
class AgentConfigDB(Base):
    """Enhanced agent configuration with wallet integration"""
    __tablename__ = 'agent_configs'
    
    # Existing columns (from previous schema)
    agent_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    strategy_config = Column(Text)  # JSON string
    risk_config = Column(Text)  # JSON string
    execution_provider = Column(String, default='paper')
    agent_type = Column(String, default='GenericAgent')
    parent_agent_id = Column(String)
    operational_parameters = Column(Text)  # JSON string
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # New wallet integration columns
    wallet_address = Column(String(255))
    allocated_funds_usd = Column(Decimal(20, 8), default=0)
    farm_id = Column(UUID(as_uuid=True), ForeignKey('farms.farm_id'))
    assigned_goals = Column(JSONB, default=[])
    wallet_performance = Column(JSONB, default={})
    
    # Indexes
    __table_args__ = (
        Index('idx_agent_configs_farm_id', 'farm_id'),
        Index('idx_agent_configs_is_active', 'is_active'),
        Index('idx_agent_configs_agent_type', 'agent_type'),
    )

# Database session and connection management
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import os

class DatabaseManager:
    """Enhanced database manager for wallet-farm-goal integration"""
    
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///agents_prod.db')
        
        # Create engine
        if self.database_url.startswith('postgresql'):
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
        else:
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                echo=False
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session with context manager"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_sync_session(self):
        """Get synchronous database session"""
        return self.SessionLocal()

# Database utility functions
def get_database_manager():
    """Get database manager instance"""
    return DatabaseManager()

def init_database():
    """Initialize database with all tables"""
    db_manager = get_database_manager()
    db_manager.create_tables()
    return db_manager

# Export all models
__all__ = [
    'Base',
    'FarmDB',
    'GoalDB',
    'MasterWalletDB',
    'FundAllocationDB',
    'WalletTransactionDB',
    'AgentFarmAssignmentDB',
    'FarmGoalAssignmentDB',
    'AgentConfigDB',
    'DatabaseManager',
    'get_database_manager',
    'init_database'
]