"""
Master Wallet Service - Phase 6
Hierarchical fund management with autonomous allocation and rebalancing
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

class MasterWalletService:
    """
    Comprehensive Master Wallet Service
    Manages hierarchical wallet system with autonomous fund distribution
    """
    
    def __init__(self):
        self.master_wallets: Dict[str, Any] = {}
        self.farm_wallets: Dict[str, Any] = {}
        self.agent_wallets: Dict[str, Any] = {}
        self.wallet_hierarchy: Dict[str, Any] = {}
        self.active_rebalances: Dict[str, Any] = {}
        self.transaction_history: List[Any] = []
        
        # Performance tracking
        self.performance_cache: Dict[str, Any] = {}
        self.risk_cache: Dict[str, Any] = {}
        
        # Auto-management settings
        self.auto_rebalance_enabled = True
        self.auto_profit_collection_enabled = True
        self.rebalance_interval = 3600  # 1 hour
        self.performance_calculation_interval = 300  # 5 minutes
        
        logger.info("🏦 Master Wallet Service initialized")
    
    async def initialize(self):
        """Initialize the master wallet service"""
        # Start background tasks
        asyncio.create_task(self._auto_rebalance_loop())
        asyncio.create_task(self._performance_calculation_loop())
        asyncio.create_task(self._profit_collection_loop())
        
        logger.info("✅ Master Wallet Service ready")
    
    async def create_master_wallet(self, name: str, initial_capital: Decimal, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new master wallet"""
        try:
            wallet_id = f"master_{uuid.uuid4().hex[:8]}"
            
            # Create master wallet
            master_wallet = {
                "id": wallet_id,
                "name": name,
                "type": "master",
                "status": "active",
                "balance": {
                    "total": initial_capital,
                    "available": initial_capital,
                    "allocated": Decimal('0'),
                    "reserved": initial_capital * Decimal('0.15'),  # 15% reserve
                    "currency": "USD"
                },
                "performance": {
                    "total_pnl": Decimal('0'),
                    "daily_pnl": Decimal('0'),
                    "roi": Decimal('0'),
                    "sharpe_ratio": Decimal('0'),
                    "max_drawdown": Decimal('0'),
                    "total_trades": 0
                },
                "farm_wallets": [],
                "total_farms": 0,
                "active_farms": 0,
                "emergency_reserve_percentage": Decimal('15'),
                "max_farm_allocation": Decimal('75'),
                "auto_rebalance_enabled": True,
                "rebalance_threshold": Decimal('10'),
                "profit_collection_threshold": Decimal('15'),
                "total_profit_collected": Decimal('0'),
                "created_at": datetime.utcnow(),
                "last_rebalance": None,
                "last_profit_collection": None
            }
            
            # Apply custom configuration if provided
            if config:
                for key, value in config.items():
                    if key in master_wallet:
                        master_wallet[key] = value
            
            # Store wallet
            self.master_wallets[wallet_id] = master_wallet
            
            # Initialize wallet hierarchy
            self.wallet_hierarchy[wallet_id] = {
                "master_wallet": master_wallet,
                "farm_wallets": {},
                "agent_wallets": {},
                "total_hierarchy_value": initial_capital,
                "last_hierarchy_update": datetime.utcnow(),
                "auto_management_enabled": True
            }
            
            # Log creation
            await self._log_transaction({
                "id": str(uuid.uuid4()),
                "wallet_id": wallet_id,
                "transaction_type": "deposit",
                "amount": initial_capital,
                "description": f"Initial capital for master wallet: {name}",
                "status": "completed",
                "created_at": datetime.utcnow(),
                "metadata": {"creation": True, "initial_capital": str(initial_capital)}
            })
            
            logger.info(f"🏦 Created master wallet: {name} with ${initial_capital}")
            return master_wallet
            
        except Exception as e:
            logger.error(f"❌ Failed to create master wallet: {e}")
            raise
    
    async def create_farm_wallet(self, master_wallet_id: str, name: str, strategy_type: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new farm wallet under a master wallet"""
        try:
            if master_wallet_id not in self.master_wallets:
                raise ValueError(f"Master wallet {master_wallet_id} not found")
            
            master_wallet = self.master_wallets[master_wallet_id]
            hierarchy = self.wallet_hierarchy[master_wallet_id]
            
            farm_id = f"farm_{uuid.uuid4().hex[:8]}"
            
            # Create farm wallet
            farm_wallet = {
                "id": farm_id,
                "name": name,
                "type": "farm",
                "status": "active",
                "strategy_type": strategy_type,
                "parent_wallet_id": master_wallet_id,
                "balance": {
                    "total": Decimal('0'),
                    "available": Decimal('0'),
                    "allocated": Decimal('0'),
                    "currency": "USD"
                },
                "performance": {
                    "total_pnl": Decimal('0'),
                    "daily_pnl": Decimal('0'),
                    "roi": Decimal('0'),
                    "farm_efficiency_score": Decimal('0'),
                    "coordination_score": Decimal('0')
                },
                "agent_wallets": [],
                "total_agents": 0,
                "active_agents": 0,
                "max_agents": 8,
                "min_agent_capital": Decimal('500'),
                "max_agent_capital": Decimal('5000'),
                "farm_risk_limit": Decimal('15'),
                "max_daily_loss": Decimal('3'),
                "stop_loss_enabled": True,
                "created_at": datetime.utcnow()
            }
            
            # Apply custom configuration
            if config:
                for key, value in config.items():
                    if key in farm_wallet:
                        farm_wallet[key] = value
            
            # Add to hierarchy
            self.farm_wallets[farm_id] = farm_wallet
            hierarchy["farm_wallets"][farm_id] = farm_wallet
            
            # Update master wallet
            master_wallet["farm_wallets"].append(farm_id)
            master_wallet["total_farms"] += 1
            master_wallet["active_farms"] += 1
            
            # Allocate initial capital to farm
            await self._allocate_capital_to_farm(master_wallet_id, farm_id, Decimal('10000'))  # Default allocation
            
            logger.info(f"🏭 Created farm wallet: {name} ({strategy_type}) under master {master_wallet_id}")
            return farm_wallet
            
        except Exception as e:
            logger.error(f"❌ Failed to create farm wallet: {e}")
            raise
    
    async def create_agent_wallet(self, farm_wallet_id: str, agent_id: str, strategy_name: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new agent wallet under a farm wallet"""
        try:
            if farm_wallet_id not in self.farm_wallets:
                raise ValueError(f"Farm wallet {farm_wallet_id} not found")
            
            farm_wallet = self.farm_wallets[farm_wallet_id]
            
            agent_wallet_id = f"agent_{uuid.uuid4().hex[:8]}"
            
            # Create agent wallet
            agent_wallet = {
                "id": agent_wallet_id,
                "name": f"Agent {agent_id}",
                "type": "agent",
                "status": "active",
                "agent_id": agent_id,
                "strategy_name": strategy_name,
                "farm_wallet_id": farm_wallet_id,
                "parent_wallet_id": farm_wallet_id,
                "balance": {
                    "total": Decimal('0'),
                    "available": Decimal('0'),
                    "currency": "USD"
                },
                "performance": {
                    "total_pnl": Decimal('0'),
                    "daily_pnl": Decimal('0'),
                    "roi": Decimal('0'),
                    "agent_efficiency": Decimal('0')
                },
                "max_position_size": Decimal('2000'),
                "leverage": Decimal('1'),
                "stop_loss": Decimal('2'),
                "take_profit": Decimal('4'),
                "daily_trade_limit": 30,
                "max_open_positions": 3,
                "trades_today": 0,
                "open_positions": 0,
                "last_trade": None,
                "last_profit": None,
                "created_at": datetime.utcnow()
            }
            
            # Apply custom configuration
            if config:
                for key, value in config.items():
                    if key in agent_wallet:
                        agent_wallet[key] = value
            
            # Add to farm
            self.agent_wallets[agent_wallet_id] = agent_wallet
            farm_wallet["agent_wallets"].append(agent_wallet_id)
            farm_wallet["total_agents"] += 1
            farm_wallet["active_agents"] += 1
            
            # Update hierarchy
            master_wallet_id = farm_wallet["parent_wallet_id"]
            if master_wallet_id in self.wallet_hierarchy:
                hierarchy = self.wallet_hierarchy[master_wallet_id]
                hierarchy["agent_wallets"][agent_wallet_id] = agent_wallet
            
            # Allocate initial capital to agent
            await self._allocate_capital_to_agent(farm_wallet_id, agent_wallet_id, Decimal('2000'))  # Default allocation
            
            logger.info(f"🤖 Created agent wallet for agent {agent_id} under farm {farm_wallet_id}")
            return agent_wallet
            
        except Exception as e:
            logger.error(f"❌ Failed to create agent wallet: {e}")
            raise
    
    async def allocate_funds_to_farms(self, master_wallet_id: str, allocation_strategy: str = "performance_based") -> Dict[str, Any]:
        """Allocate funds from master wallet to farms"""
        try:
            if master_wallet_id not in self.master_wallets:
                raise ValueError(f"Master wallet {master_wallet_id} not found")
            
            master_wallet = self.master_wallets[master_wallet_id]
            hierarchy = self.wallet_hierarchy[master_wallet_id]
            
            # Calculate available capital for allocation
            available_capital = master_wallet["balance"]["available"]
            emergency_reserve = available_capital * (master_wallet["emergency_reserve_percentage"] / 100)
            allocatable_capital = available_capital - emergency_reserve
            
            if allocatable_capital <= 0:
                return {"message": "No capital available for allocation", "allocated": Decimal('0')}
            
            # Get farm performance for allocation decisions
            farm_allocations = await self._calculate_farm_allocations(
                master_wallet_id, allocatable_capital, allocation_strategy
            )
            
            total_allocated = Decimal('0')
            allocation_results = []
            
            # Execute allocations
            for farm_id, allocation_amount in farm_allocations.items():
                if allocation_amount > 0:
                    result = await self._allocate_capital_to_farm(master_wallet_id, farm_id, allocation_amount)
                    allocation_results.append(result)
                    total_allocated += allocation_amount
            
            # Update master wallet
            master_wallet["balance"]["available"] -= total_allocated
            master_wallet["balance"]["allocated"] += total_allocated
            
            logger.info(f"💰 Allocated ${total_allocated} from master wallet {master_wallet_id} to {len(farm_allocations)} farms")
            
            return {
                "total_allocated": total_allocated,
                "farms_allocated": len(farm_allocations),
                "allocation_strategy": allocation_strategy,
                "results": allocation_results
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to allocate funds to farms: {e}")
            raise
    
    async def rebalance_portfolio(self, master_wallet_id: str, force: bool = False) -> Dict[str, Any]:
        """Rebalance the entire wallet hierarchy"""
        try:
            if master_wallet_id not in self.master_wallets:
                raise ValueError(f"Master wallet {master_wallet_id} not found")
            
            master_wallet = self.master_wallets[master_wallet_id]
            
            # Check if rebalance is needed
            if not force and not await self._should_rebalance(master_wallet_id):
                return {"message": "Rebalance not needed", "rebalanced": False}
            
            # Create rebalance operation
            rebalance_op = {
                "id": str(uuid.uuid4()),
                "master_wallet_id": master_wallet_id,
                "trigger_reason": "performance_deviation" if not force else "manual",
                "started_at": datetime.utcnow(),
                "status": "in_progress"
            }
            
            # Calculate optimal allocations
            current_allocations = await self._get_current_allocations(master_wallet_id)
            target_allocations = await self._calculate_optimal_allocations(master_wallet_id)
            
            # Execute rebalancing transactions
            movements = []
            total_moved = Decimal('0')
            
            for wallet_id, target_pct in target_allocations.items():
                current_pct = current_allocations.get(wallet_id, Decimal('0'))
                deviation = target_pct - current_pct
                
                if abs(deviation) > master_wallet["rebalance_threshold"]:
                    movement_amount = (deviation / 100) * master_wallet["balance"]["total"]
                    
                    if movement_amount > 0:  # Need to allocate more
                        transaction = await self._move_capital_to_wallet(master_wallet_id, wallet_id, movement_amount)
                    else:  # Need to collect some capital
                        transaction = await self._collect_capital_from_wallet(wallet_id, master_wallet_id, abs(movement_amount))
                    
                    movements.append(transaction)
                    total_moved += abs(movement_amount)
            
            # Complete rebalance operation
            rebalance_op["actual_movements"] = movements
            rebalance_op["total_amount_moved"] = total_moved
            rebalance_op["completed_at"] = datetime.utcnow()
            rebalance_op["status"] = "completed"
            
            # Update master wallet
            master_wallet["last_rebalance"] = datetime.utcnow()
            
            # Store operation
            self.active_rebalances[rebalance_op["id"]] = rebalance_op
            
            logger.info(f"⚖️ Rebalanced portfolio for master wallet {master_wallet_id}: ${total_moved} moved across {len(movements)} transactions")
            
            return {
                "rebalanced": True,
                "total_amount_moved": total_moved,
                "transactions": len(movements),
                "rebalance_id": rebalance_op["id"]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to rebalance portfolio: {e}")
            raise
    
    async def collect_profits(self, master_wallet_id: str, threshold_percentage: Optional[Decimal] = None) -> Dict[str, Any]:
        """Collect profits from performing wallets back to master wallet"""
        try:
            if master_wallet_id not in self.master_wallets:
                raise ValueError(f"Master wallet {master_wallet_id} not found")
            
            master_wallet = self.master_wallets[master_wallet_id]
            hierarchy = self.wallet_hierarchy[master_wallet_id]
            
            threshold = threshold_percentage or master_wallet["profit_collection_threshold"]
            total_collected = Decimal('0')
            collections = []
            
            # Collect from farms
            for farm_id, farm_wallet in hierarchy["farm_wallets"].items():
                farm_performance = await self._calculate_wallet_performance(farm_id)
                if farm_performance["roi"] >= threshold:
                    profit_amount = farm_wallet["balance"]["total"] * (farm_performance["roi"] / 100)
                    if profit_amount > 0:
                        transaction = await self._collect_capital_from_wallet(farm_id, master_wallet_id, profit_amount)
                        collections.append({"wallet_id": farm_id, "amount": profit_amount, "transaction": transaction})
                        total_collected += profit_amount
            
            # Collect from agents (via their farms)
            for agent_id, agent_wallet in hierarchy["agent_wallets"].items():
                agent_performance = await self._calculate_wallet_performance(agent_id)
                if agent_performance["roi"] >= threshold:
                    profit_amount = agent_wallet["balance"]["total"] * (agent_performance["roi"] / 100)
                    if profit_amount > 0:
                        # Collect to farm first, then farm to master
                        farm_id = agent_wallet["farm_wallet_id"]
                        transaction = await self._collect_capital_from_wallet(agent_id, farm_id, profit_amount)
                        collections.append({"wallet_id": agent_id, "amount": profit_amount, "transaction": transaction})
                        total_collected += profit_amount
            
            # Update master wallet
            master_wallet["balance"]["available"] += total_collected
            master_wallet["total_profit_collected"] += total_collected
            master_wallet["last_profit_collection"] = datetime.utcnow()
            
            logger.info(f"💰 Collected ${total_collected} in profits from {len(collections)} wallets to master {master_wallet_id}")
            
            return {
                "total_collected": total_collected,
                "wallets_collected": len(collections),
                "threshold_used": threshold,
                "collections": collections
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to collect profits: {e}")
            raise
    
    async def get_wallet_hierarchy(self, master_wallet_id: str) -> Dict[str, Any]:
        """Get complete wallet hierarchy"""
        if master_wallet_id not in self.wallet_hierarchy:
            raise ValueError(f"Wallet hierarchy {master_wallet_id} not found")
        
        hierarchy = self.wallet_hierarchy[master_wallet_id]
        
        # Update hierarchy metrics
        await self._update_hierarchy_metrics(hierarchy)
        
        return hierarchy
    
    async def get_wallet_performance(self, wallet_id: str) -> Dict[str, Any]:
        """Get wallet performance metrics"""
        return await self._calculate_wallet_performance(wallet_id)
    
    async def get_wallet_analytics(self, master_wallet_id: str) -> Dict[str, Any]:
        """Get comprehensive wallet analytics"""
        try:
            hierarchy = await self.get_wallet_hierarchy(master_wallet_id)
            master_wallet = hierarchy["master_wallet"]
            
            # Calculate portfolio-level analytics
            total_value = hierarchy["total_hierarchy_value"]
            total_allocated = master_wallet["balance"]["allocated"]
            allocation_percentage = (total_allocated / total_value * 100) if total_value > 0 else Decimal('0')
            
            # Farm analytics
            farm_analytics = {}
            for farm_id, farm_wallet in hierarchy["farm_wallets"].items():
                farm_performance = await self._calculate_wallet_performance(farm_id)
                farm_analytics[farm_id] = {
                    "name": farm_wallet["name"],
                    "strategy": farm_wallet["strategy_type"],
                    "agents": farm_wallet["total_agents"],
                    "value": farm_wallet["balance"]["total"],
                    "performance": farm_performance,
                    "efficiency": farm_wallet["performance"]["farm_efficiency_score"]
                }
            
            # Agent analytics
            agent_analytics = {}
            for agent_id, agent_wallet in hierarchy["agent_wallets"].items():
                agent_performance = await self._calculate_wallet_performance(agent_id)
                agent_analytics[agent_id] = {
                    "name": agent_wallet["name"],
                    "strategy": agent_wallet["strategy_name"],
                    "farm": agent_wallet["farm_wallet_id"],
                    "value": agent_wallet["balance"]["total"],
                    "performance": agent_performance,
                    "efficiency": agent_wallet["performance"]["agent_efficiency"]
                }
            
            # Risk analytics
            portfolio_risk = await self._calculate_portfolio_risk(master_wallet_id)
            
            return {
                "master_wallet": {
                    "id": master_wallet_id,
                    "name": master_wallet["name"],
                    "total_value": total_value,
                    "allocated_percentage": allocation_percentage,
                    "emergency_reserve": master_wallet["balance"]["total"] * (master_wallet["emergency_reserve_percentage"] / 100),
                    "performance": master_wallet["performance"]
                },
                "farms": farm_analytics,
                "agents": agent_analytics,
                "risk_metrics": portfolio_risk,
                "summary": {
                    "total_farms": len(hierarchy["farm_wallets"]),
                    "total_agents": len(hierarchy["agent_wallets"]),
                    "total_profit_collected": master_wallet["total_profit_collected"],
                    "last_rebalance": master_wallet["last_rebalance"],
                    "auto_management": master_wallet["auto_rebalance_enabled"]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get wallet analytics: {e}")
            raise
    
    # Private helper methods
    
    async def _calculate_farm_allocations(self, master_wallet_id: str, total_capital: Decimal, strategy: str) -> Dict[str, Decimal]:
        """Calculate optimal farm allocations based on strategy"""
        hierarchy = self.wallet_hierarchy[master_wallet_id]
        allocations = {}
        
        if strategy == "equal":
            # Equal allocation across all farms
            farm_count = len(hierarchy["farm_wallets"])
            if farm_count > 0:
                equal_amount = total_capital / farm_count
                for farm_id in hierarchy["farm_wallets"].keys():
                    allocations[farm_id] = equal_amount
        
        elif strategy == "performance_based":
            # Allocate based on performance scores
            farm_scores = {}
            total_score = Decimal('0')
            
            for farm_id in hierarchy["farm_wallets"].keys():
                performance = await self._calculate_wallet_performance(farm_id)
                score = performance["roi"] + performance.get("sharpe_ratio", Decimal('0'))  # Simple scoring
                farm_scores[farm_id] = max(score, Decimal('0.1'))  # Minimum score
                total_score += farm_scores[farm_id]
            
            # Allocate proportionally
            for farm_id, score in farm_scores.items():
                allocation_pct = score / total_score if total_score > 0 else Decimal('0')
                allocations[farm_id] = total_capital * allocation_pct
        
        return allocations
    
    async def _allocate_capital_to_farm(self, master_wallet_id: str, farm_wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """Allocate capital from master wallet to farm wallet"""
        master_wallet = self.master_wallets[master_wallet_id]
        farm_wallet = self.farm_wallets[farm_wallet_id]
        
        # Create transaction
        transaction = {
            "id": str(uuid.uuid4()),
            "wallet_id": master_wallet_id,
            "transaction_type": "allocation",
            "amount": amount,
            "description": f"Capital allocation to farm {farm_wallet['name']}",
            "from_wallet_id": master_wallet_id,
            "to_wallet_id": farm_wallet_id,
            "status": "completed",
            "created_at": datetime.utcnow(),
            "metadata": {"allocation_type": "farm", "strategy": farm_wallet["strategy_type"]}
        }
        
        # Update balances
        master_wallet["balance"]["available"] -= amount
        master_wallet["balance"]["allocated"] += amount
        farm_wallet["balance"]["total"] += amount
        farm_wallet["balance"]["available"] += amount
        
        # Log transaction
        await self._log_transaction(transaction)
        
        return transaction
    
    async def _allocate_capital_to_agent(self, farm_wallet_id: str, agent_wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """Allocate capital from farm wallet to agent wallet"""
        farm_wallet = self.farm_wallets[farm_wallet_id]
        agent_wallet = self.agent_wallets[agent_wallet_id]
        
        # Create transaction
        transaction = {
            "id": str(uuid.uuid4()),
            "wallet_id": farm_wallet_id,
            "transaction_type": "allocation",
            "amount": amount,
            "description": f"Capital allocation to agent {agent_wallet['name']}",
            "from_wallet_id": farm_wallet_id,
            "to_wallet_id": agent_wallet_id,
            "status": "completed",
            "created_at": datetime.utcnow(),
            "metadata": {"allocation_type": "agent", "strategy": agent_wallet["strategy_name"]}
        }
        
        # Update balances
        farm_wallet["balance"]["available"] -= amount
        farm_wallet["balance"]["allocated"] += amount
        agent_wallet["balance"]["total"] += amount
        agent_wallet["balance"]["available"] += amount
        
        # Log transaction
        await self._log_transaction(transaction)
        
        return transaction
    
    async def _move_capital_to_wallet(self, from_wallet_id: str, to_wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """Move capital between wallets"""
        transaction = {
            "id": str(uuid.uuid4()),
            "wallet_id": from_wallet_id,
            "transaction_type": "rebalance",
            "amount": amount,
            "description": f"Rebalance: Move capital from {from_wallet_id} to {to_wallet_id}",
            "from_wallet_id": from_wallet_id,
            "to_wallet_id": to_wallet_id,
            "status": "completed",
            "created_at": datetime.utcnow()
        }
        
        await self._log_transaction(transaction)
        return transaction
    
    async def _collect_capital_from_wallet(self, from_wallet_id: str, to_wallet_id: str, amount: Decimal) -> Dict[str, Any]:
        """Collect capital from a wallet"""
        transaction = {
            "id": str(uuid.uuid4()),
            "wallet_id": to_wallet_id,
            "transaction_type": "profit_collection",
            "amount": amount,
            "description": f"Profit collection from {from_wallet_id}",
            "from_wallet_id": from_wallet_id,
            "to_wallet_id": to_wallet_id,
            "status": "completed",
            "created_at": datetime.utcnow()
        }
        
        await self._log_transaction(transaction)
        return transaction
    
    async def _calculate_wallet_performance(self, wallet_id: str) -> Dict[str, Any]:
        """Calculate performance metrics for a wallet"""
        # Check cache first
        if wallet_id in self.performance_cache:
            cached = self.performance_cache[wallet_id]
            if (datetime.utcnow() - cached.get("last_calculated", datetime.utcnow())).seconds < 300:  # 5 minute cache
                return cached
        
        # Calculate new performance metrics
        performance = {
            "total_pnl": Decimal('0'),
            "daily_pnl": Decimal('0'),
            "roi": Decimal('0'),
            "sharpe_ratio": Decimal('0'),
            "max_drawdown": Decimal('0'),
            "total_trades": 0,
            "last_calculated": datetime.utcnow()
        }
        
        # Get wallet
        wallet = None
        if wallet_id in self.master_wallets:
            wallet = self.master_wallets[wallet_id]
        elif wallet_id in self.farm_wallets:
            wallet = self.farm_wallets[wallet_id]
        elif wallet_id in self.agent_wallets:
            wallet = self.agent_wallets[wallet_id]
        
        if wallet:
            # Calculate basic metrics (simplified for mock implementation)
            balance = wallet["balance"]["total"]
            performance["roi"] = Decimal('5.5')  # Mock 5.5% ROI
            performance["total_pnl"] = balance * (performance["roi"] / 100)
            performance["sharpe_ratio"] = Decimal('1.2')  # Mock Sharpe ratio
            performance["max_drawdown"] = Decimal('2.1')  # Mock max drawdown
            
            # Calculate from transaction history
            wallet_transactions = [t for t in self.transaction_history if t.get("wallet_id") == wallet_id]
            performance["total_trades"] = len(wallet_transactions)
        
        # Cache the result
        self.performance_cache[wallet_id] = performance
        return performance
    
    async def _calculate_portfolio_risk(self, master_wallet_id: str) -> Dict[str, Any]:
        """Calculate portfolio-level risk metrics"""
        # Mock risk calculation
        return {
            "risk_score": Decimal('45'),  # Medium risk
            "var_95": Decimal('0.05'),   # 5% VaR
            "expected_shortfall": Decimal('0.08'),
            "correlation_risk": Decimal('0.3'),
            "concentration_risk": Decimal('0.25'),
            "last_assessed": datetime.utcnow()
        }
    
    async def _should_rebalance(self, master_wallet_id: str) -> bool:
        """Check if portfolio should be rebalanced"""
        master_wallet = self.master_wallets[master_wallet_id]
        
        if not master_wallet["auto_rebalance_enabled"]:
            return False
        
        # Check time since last rebalance
        if master_wallet["last_rebalance"]:
            time_since_rebalance = datetime.utcnow() - master_wallet["last_rebalance"]
            if time_since_rebalance.seconds < self.rebalance_interval:
                return False
        
        return True  # Simplified - would check performance deviations
    
    async def _get_current_allocations(self, master_wallet_id: str) -> Dict[str, Decimal]:
        """Get current allocation percentages"""
        hierarchy = self.wallet_hierarchy[master_wallet_id]
        total_value = hierarchy["total_hierarchy_value"]
        
        allocations = {}
        for farm_id, farm_wallet in hierarchy["farm_wallets"].items():
            allocation_pct = (farm_wallet["balance"]["total"] / total_value * 100) if total_value > 0 else Decimal('0')
            allocations[farm_id] = allocation_pct
        
        return allocations
    
    async def _calculate_optimal_allocations(self, master_wallet_id: str) -> Dict[str, Decimal]:
        """Calculate optimal allocation percentages"""
        # Use performance-based allocation as default
        return await self._calculate_farm_allocations(
            master_wallet_id, 
            Decimal('100'),  # Use percentage
            "performance_based"
        )
    
    async def _update_hierarchy_metrics(self, hierarchy: Dict[str, Any]):
        """Update hierarchy-level metrics"""
        total_value = hierarchy["master_wallet"]["balance"]["total"]
        
        for farm_wallet in hierarchy["farm_wallets"].values():
            total_value += farm_wallet["balance"]["total"]
        
        for agent_wallet in hierarchy["agent_wallets"].values():
            total_value += agent_wallet["balance"]["total"]
        
        hierarchy["total_hierarchy_value"] = total_value
        hierarchy["last_hierarchy_update"] = datetime.utcnow()
    
    async def _log_transaction(self, transaction: Dict[str, Any]):
        """Log a wallet transaction"""
        transaction["processed_at"] = datetime.utcnow()
        self.transaction_history.append(transaction)
        
        # Keep only last 10,000 transactions
        if len(self.transaction_history) > 10000:
            self.transaction_history = self.transaction_history[-10000:]
    
    # Background task loops
    
    async def _auto_rebalance_loop(self):
        """Background task for automatic rebalancing"""
        while True:
            try:
                await asyncio.sleep(self.rebalance_interval)
                
                if self.auto_rebalance_enabled:
                    for master_wallet_id in self.master_wallets.keys():
                        if await self._should_rebalance(master_wallet_id):
                            await self.rebalance_portfolio(master_wallet_id)
                            
            except Exception as e:
                logger.error(f"❌ Auto-rebalance error: {e}")
    
    async def _performance_calculation_loop(self):
        """Background task for performance calculations"""
        while True:
            try:
                await asyncio.sleep(self.performance_calculation_interval)
                
                # Update performance for all wallets
                all_wallet_ids = (
                    list(self.master_wallets.keys()) + 
                    list(self.farm_wallets.keys()) + 
                    list(self.agent_wallets.keys())
                )
                
                for wallet_id in all_wallet_ids:
                    await self._calculate_wallet_performance(wallet_id)
                    
            except Exception as e:
                logger.error(f"❌ Performance calculation error: {e}")
    
    async def _profit_collection_loop(self):
        """Background task for automatic profit collection"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                if self.auto_profit_collection_enabled:
                    for master_wallet_id in self.master_wallets.keys():
                        await self.collect_profits(master_wallet_id)
                        
            except Exception as e:
                logger.error(f"❌ Profit collection error: {e}")

# Service factory
def create_master_wallet_service() -> MasterWalletService:
    """Create and configure master wallet service"""
    return MasterWalletService()