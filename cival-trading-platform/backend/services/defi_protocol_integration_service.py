"""
DeFi Protocol Integration Service - Phase 11
Comprehensive DeFi protocol integration for yield farming, liquidity provision, and staking
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

class ProtocolType(Enum):
    DEX = "dex"
    LENDING = "lending" 
    YIELD_FARMING = "yield_farming"
    LIQUID_STAKING = "liquid_staking"
    DERIVATIVES = "derivatives"
    SYNTHETIC = "synthetic"
    INSURANCE = "insurance"

class PositionType(Enum):
    LIQUIDITY_POOL = "liquidity_pool"
    LENDING_DEPOSIT = "lending_deposit"
    BORROWING_POSITION = "borrowing_position"
    STAKING_POSITION = "staking_position"
    YIELD_FARM = "yield_farm"
    DERIVATIVE_POSITION = "derivative_position"

class PositionStatus(Enum):
    ACTIVE = "active"
    PENDING = "pending"
    WITHDRAWN = "withdrawn"
    LIQUIDATED = "liquidated"
    EXPIRED = "expired"

@dataclass
class DeFiProtocol:
    """DeFi protocol definition"""
    protocol_id: str
    name: str
    protocol_type: ProtocolType
    chain: str
    tvl_usd: Decimal
    base_apy: float
    reward_apy: float
    total_apy: float
    contract_address: str
    risk_score: float
    audit_status: str
    last_updated: datetime
    metadata: Dict[str, Any]

@dataclass 
class DeFiPosition:
    """DeFi position tracking"""
    position_id: str
    user_wallet: str
    protocol_id: str
    position_type: PositionType
    status: PositionStatus
    asset_symbol: str
    amount_deposited: Decimal
    current_value_usd: Decimal
    rewards_earned_usd: Decimal
    unrealized_pnl_usd: Decimal
    entry_timestamp: datetime
    last_harvest: Optional[datetime] = None
    auto_compound: bool = True
    metadata: Dict[str, Any] = None

@dataclass
class YieldOpportunity:
    """Yield farming opportunity"""
    opportunity_id: str
    protocol_name: str
    pool_name: str
    asset_pair: str
    chain: str
    apy: float
    tvl_usd: Decimal
    minimum_deposit: Decimal
    risk_score: float
    impermanent_loss_risk: float
    lock_period_days: int
    auto_compound: bool
    rewards_tokens: List[str]

class DeFiProtocolIntegrationService:
    """
    Comprehensive DeFi protocol integration service
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # Active protocol tracking
        self.supported_protocols: Dict[str, DeFiProtocol] = {}
        self.active_positions: Dict[str, DeFiPosition] = {}
        self.yield_opportunities: Dict[str, YieldOpportunity] = {}
        
        # Protocol configurations
        self.protocol_configs = {
            "ethereum": {
                "uniswap_v3": {
                    "name": "Uniswap V3",
                    "type": ProtocolType.DEX,
                    "contract": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                    "base_apy": 5.2,
                    "risk_score": 0.15
                },
                "aave": {
                    "name": "Aave",
                    "type": ProtocolType.LENDING,
                    "contract": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
                    "base_apy": 3.8,
                    "risk_score": 0.12
                },
                "compound": {
                    "name": "Compound",
                    "type": ProtocolType.LENDING,
                    "contract": "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B",
                    "base_apy": 3.2,
                    "risk_score": 0.14
                },
                "lido": {
                    "name": "Lido",
                    "type": ProtocolType.LIQUID_STAKING,
                    "contract": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
                    "base_apy": 4.1,
                    "risk_score": 0.08
                }
            },
            "polygon": {
                "quickswap": {
                    "name": "QuickSwap",
                    "type": ProtocolType.DEX,
                    "contract": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
                    "base_apy": 8.5,
                    "risk_score": 0.25
                },
                "aave_polygon": {
                    "name": "Aave Polygon",
                    "type": ProtocolType.LENDING,
                    "contract": "0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf",
                    "base_apy": 6.2,
                    "risk_score": 0.18
                }
            },
            "bsc": {
                "pancakeswap": {
                    "name": "PancakeSwap",
                    "type": ProtocolType.DEX,
                    "contract": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
                    "base_apy": 12.3,
                    "risk_score": 0.35
                },
                "venus": {
                    "name": "Venus",
                    "type": ProtocolType.LENDING,
                    "contract": "0xfD36E2c2a6789Db23113685031d7F16329158384",
                    "base_apy": 8.7,
                    "risk_score": 0.28
                }
            }
        }
        
        # Initialize mock data
        self._initialize_mock_data()
        
        logger.info("DeFiProtocolIntegrationService initialized")
    
    def _initialize_mock_data(self):
        """Initialize with mock DeFi data"""
        # Create mock protocols
        for chain, protocols in self.protocol_configs.items():
            for protocol_key, config in protocols.items():
                protocol = DeFiProtocol(
                    protocol_id=f"{chain}_{protocol_key}",
                    name=config["name"],
                    protocol_type=config["type"],
                    chain=chain,
                    tvl_usd=Decimal(str(10000000 + hash(protocol_key) % 500000000)),
                    base_apy=config["base_apy"],
                    reward_apy=config["base_apy"] * 0.3,
                    total_apy=config["base_apy"] * 1.3,
                    contract_address=config["contract"],
                    risk_score=config["risk_score"],
                    audit_status="audited" if config["risk_score"] < 0.2 else "reviewed",
                    last_updated=datetime.now(timezone.utc),
                    metadata={"category": config["type"].value, "auto_compound": True}
                )
                self.supported_protocols[protocol.protocol_id] = protocol
        
        # Create mock positions
        mock_positions = [
            {
                "protocol_id": "ethereum_uniswap_v3",
                "asset_symbol": "ETH/USDC",
                "amount_deposited": Decimal("50000.0"),
                "position_type": PositionType.LIQUIDITY_POOL
            },
            {
                "protocol_id": "ethereum_aave", 
                "asset_symbol": "USDC",
                "amount_deposited": Decimal("25000.0"),
                "position_type": PositionType.LENDING_DEPOSIT
            },
            {
                "protocol_id": "polygon_quickswap",
                "asset_symbol": "MATIC/USDT",
                "amount_deposited": Decimal("15000.0"),
                "position_type": PositionType.YIELD_FARM
            }
        ]
        
        for i, pos_data in enumerate(mock_positions):
            position = DeFiPosition(
                position_id=f"pos_{i+1}",
                user_wallet="0x742d35cc6634c0532925a3b8d8a742e684e",
                protocol_id=pos_data["protocol_id"],
                position_type=pos_data["position_type"],
                status=PositionStatus.ACTIVE,
                asset_symbol=pos_data["asset_symbol"],
                amount_deposited=pos_data["amount_deposited"],
                current_value_usd=pos_data["amount_deposited"] * Decimal("1.05"),
                rewards_earned_usd=pos_data["amount_deposited"] * Decimal("0.03"),
                unrealized_pnl_usd=pos_data["amount_deposited"] * Decimal("0.08"),
                entry_timestamp=datetime.now(timezone.utc) - timedelta(days=30-i*10),
                last_harvest=datetime.now(timezone.utc) - timedelta(days=7),
                auto_compound=True,
                metadata={"risk_level": "medium", "auto_harvest": True}
            )
            self.active_positions[position.position_id] = position

    async def initialize(self):
        """Initialize the DeFi protocol integration service"""
        try:
            # Load protocols from database if available
            await self._load_protocols()
            
            # Load active positions
            await self._load_positions()
            
            # Start background monitoring
            asyncio.create_task(self._protocol_monitoring_loop())
            asyncio.create_task(self._yield_optimization_loop())
            asyncio.create_task(self._auto_compound_loop())
            
            logger.info("DeFiProtocolIntegrationService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize DeFiProtocolIntegrationService: {e}")
            pass  # Continue with mock data

    async def get_supported_protocols(self, chain: str = None) -> List[DeFiProtocol]:
        """Get list of supported DeFi protocols"""
        protocols = list(self.supported_protocols.values())
        
        if chain:
            protocols = [p for p in protocols if p.chain.lower() == chain.lower()]
        
        return sorted(protocols, key=lambda x: x.total_apy, reverse=True)

    async def get_protocol_details(self, protocol_id: str) -> Optional[DeFiProtocol]:
        """Get detailed information about a specific protocol"""
        return self.supported_protocols.get(protocol_id)

    async def discover_yield_opportunities(self, 
                                        min_apy: float = 5.0,
                                        max_risk_score: float = 0.5,
                                        chains: List[str] = None) -> List[YieldOpportunity]:
        """Discover yield farming opportunities based on criteria"""
        try:
            opportunities = []
            
            # Filter protocols based on criteria
            protocols = await self.get_supported_protocols()
            
            if chains:
                protocols = [p for p in protocols if p.chain in chains]
            
            for protocol in protocols:
                if protocol.total_apy >= min_apy and protocol.risk_score <= max_risk_score:
                    # Generate yield opportunities for this protocol
                    if protocol.protocol_type == ProtocolType.DEX:
                        # Generate LP opportunities
                        asset_pairs = ["ETH/USDC", "BTC/ETH", "MATIC/USDT", "BNB/BUSD"]
                        for pair in asset_pairs:
                            opportunity = YieldOpportunity(
                                opportunity_id=f"{protocol.protocol_id}_{pair.replace('/', '_').lower()}",
                                protocol_name=protocol.name,
                                pool_name=f"{pair} Pool",
                                asset_pair=pair,
                                chain=protocol.chain,
                                apy=protocol.total_apy + (hash(pair) % 10) * 0.5,
                                tvl_usd=protocol.tvl_usd * Decimal("0.1"),
                                minimum_deposit=Decimal("100.0"),
                                risk_score=protocol.risk_score,
                                impermanent_loss_risk=0.15 + (hash(pair) % 10) * 0.01,
                                lock_period_days=0,
                                auto_compound=True,
                                rewards_tokens=[protocol.name.split()[0]]
                            )
                            opportunities.append(opportunity)
                    
                    elif protocol.protocol_type == ProtocolType.LENDING:
                        # Generate lending opportunities
                        assets = ["USDC", "ETH", "WBTC", "DAI"]
                        for asset in assets:
                            opportunity = YieldOpportunity(
                                opportunity_id=f"{protocol.protocol_id}_{asset.lower()}",
                                protocol_name=protocol.name,
                                pool_name=f"{asset} Lending",
                                asset_pair=asset,
                                chain=protocol.chain,
                                apy=protocol.total_apy + (hash(asset) % 5) * 0.2,
                                tvl_usd=protocol.tvl_usd * Decimal("0.2"),
                                minimum_deposit=Decimal("50.0"),
                                risk_score=protocol.risk_score * 0.8,  # Lending generally lower risk
                                impermanent_loss_risk=0.0,  # No IL risk in lending
                                lock_period_days=0,
                                auto_compound=True,
                                rewards_tokens=[protocol.name.split()[0]]
                            )
                            opportunities.append(opportunity)
            
            # Sort by APY
            opportunities.sort(key=lambda x: x.apy, reverse=True)
            
            return opportunities[:20]  # Return top 20 opportunities
            
        except Exception as e:
            logger.error(f"Failed to discover yield opportunities: {e}")
            return []

    async def enter_position(self, 
                           protocol_id: str,
                           position_type: PositionType,
                           asset_symbol: str,
                           amount: Decimal,
                           wallet_address: str,
                           auto_compound: bool = True) -> DeFiPosition:
        """Enter a new DeFi position"""
        try:
            protocol = self.supported_protocols.get(protocol_id)
            if not protocol:
                raise ValueError(f"Protocol {protocol_id} not found")
            
            position_id = str(uuid.uuid4())
            
            position = DeFiPosition(
                position_id=position_id,
                user_wallet=wallet_address,
                protocol_id=protocol_id,
                position_type=position_type,
                status=PositionStatus.PENDING,
                asset_symbol=asset_symbol,
                amount_deposited=amount,
                current_value_usd=amount,  # Initial value
                rewards_earned_usd=Decimal("0"),
                unrealized_pnl_usd=Decimal("0"),
                entry_timestamp=datetime.now(timezone.utc),
                auto_compound=auto_compound,
                metadata={
                    "entry_apy": protocol.total_apy,
                    "entry_price": 1.0,  # Mock price
                    "expected_daily_yield": float(amount) * protocol.total_apy / 365 / 100
                }
            )
            
            # Simulate position entry
            await asyncio.sleep(0.1)  # Simulate blockchain transaction
            position.status = PositionStatus.ACTIVE
            
            # Store position
            self.active_positions[position_id] = position
            
            # Update in database if available
            if self.supabase:
                position_dict = asdict(position)
                position_dict["position_type"] = position.position_type.value
                position_dict["status"] = position.status.value
                position_dict["entry_timestamp"] = position.entry_timestamp.isoformat()
                
                self.supabase.table('defi_positions').insert(position_dict).execute()
            
            logger.info(f"Entered DeFi position: {position_id} on {protocol.name}")
            return position
            
        except Exception as e:
            logger.error(f"Failed to enter DeFi position: {e}")
            raise

    async def exit_position(self, position_id: str) -> Dict[str, Any]:
        """Exit a DeFi position"""
        try:
            position = self.active_positions.get(position_id)
            if not position:
                raise ValueError(f"Position {position_id} not found")
            
            if position.status != PositionStatus.ACTIVE:
                raise ValueError(f"Position {position_id} is not active")
            
            # Calculate final returns
            exit_value = position.current_value_usd + position.rewards_earned_usd
            total_return = exit_value - position.amount_deposited
            return_percentage = (total_return / position.amount_deposited) * 100
            
            # Update position status
            position.status = PositionStatus.WITHDRAWN
            
            # Create exit summary
            exit_summary = {
                "position_id": position_id,
                "exit_timestamp": datetime.now(timezone.utc).isoformat(),
                "initial_deposit": float(position.amount_deposited),
                "final_value": float(exit_value),
                "total_return": float(total_return),
                "return_percentage": float(return_percentage),
                "rewards_earned": float(position.rewards_earned_usd),
                "time_in_position_days": (datetime.now(timezone.utc) - position.entry_timestamp).days,
                "annualized_return": float(return_percentage) * 365 / max((datetime.now(timezone.utc) - position.entry_timestamp).days, 1)
            }
            
            # Update database
            if self.supabase:
                self.supabase.table('defi_positions').update({
                    "status": position.status.value,
                    "exit_timestamp": exit_summary["exit_timestamp"],
                    "exit_summary": exit_summary
                }).eq('position_id', position_id).execute()
            
            logger.info(f"Exited DeFi position: {position_id} with {return_percentage:.2f}% return")
            return exit_summary
            
        except Exception as e:
            logger.error(f"Failed to exit DeFi position: {e}")
            raise

    async def harvest_rewards(self, position_id: str) -> Dict[str, Any]:
        """Harvest rewards from a DeFi position"""
        try:
            position = self.active_positions.get(position_id)
            if not position:
                raise ValueError(f"Position {position_id} not found")
            
            if position.status != PositionStatus.ACTIVE:
                raise ValueError(f"Position {position_id} is not active")
            
            # Calculate pending rewards
            days_since_last_harvest = 7  # Mock
            if position.last_harvest:
                days_since_last_harvest = (datetime.now(timezone.utc) - position.last_harvest).days
            
            protocol = self.supported_protocols.get(position.protocol_id)
            daily_yield_rate = protocol.total_apy / 365 / 100 if protocol else 0.05 / 365
            
            pending_rewards = position.current_value_usd * Decimal(str(daily_yield_rate)) * days_since_last_harvest
            
            # Harvest rewards
            position.rewards_earned_usd += pending_rewards
            position.last_harvest = datetime.now(timezone.utc)
            
            if position.auto_compound:
                position.current_value_usd += pending_rewards
            
            harvest_result = {
                "position_id": position_id,
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "rewards_harvested": float(pending_rewards),
                "total_rewards_earned": float(position.rewards_earned_usd),
                "auto_compounded": position.auto_compound,
                "new_position_value": float(position.current_value_usd)
            }
            
            logger.info(f"Harvested rewards for position {position_id}: {float(pending_rewards):.2f} USD")
            return harvest_result
            
        except Exception as e:
            logger.error(f"Failed to harvest rewards: {e}")
            raise

    async def get_portfolio_overview(self, wallet_address: str = None) -> Dict[str, Any]:
        """Get comprehensive DeFi portfolio overview"""
        try:
            positions = list(self.active_positions.values())
            
            if wallet_address:
                positions = [p for p in positions if p.user_wallet == wallet_address]
            
            active_positions = [p for p in positions if p.status == PositionStatus.ACTIVE]
            
            total_deposited = sum(p.amount_deposited for p in active_positions)
            total_current_value = sum(p.current_value_usd for p in active_positions)
            total_rewards = sum(p.rewards_earned_usd for p in active_positions)
            total_unrealized_pnl = sum(p.unrealized_pnl_usd for p in active_positions)
            
            # Calculate portfolio metrics
            portfolio_return = ((total_current_value + total_rewards) - total_deposited) / total_deposited * 100 if total_deposited > 0 else 0
            
            # Group by protocol
            protocol_breakdown = {}
            for position in active_positions:
                protocol = self.supported_protocols.get(position.protocol_id)
                protocol_name = protocol.name if protocol else "Unknown"
                
                if protocol_name not in protocol_breakdown:
                    protocol_breakdown[protocol_name] = {
                        "total_value": 0,
                        "positions": 0,
                        "rewards_earned": 0
                    }
                
                protocol_breakdown[protocol_name]["total_value"] += float(position.current_value_usd)
                protocol_breakdown[protocol_name]["positions"] += 1
                protocol_breakdown[protocol_name]["rewards_earned"] += float(position.rewards_earned_usd)
            
            # Group by chain
            chain_breakdown = {}
            for position in active_positions:
                protocol = self.supported_protocols.get(position.protocol_id)
                chain = protocol.chain if protocol else "Unknown"
                
                if chain not in chain_breakdown:
                    chain_breakdown[chain] = {
                        "total_value": 0,
                        "positions": 0,
                        "percentage": 0
                    }
                
                chain_breakdown[chain]["total_value"] += float(position.current_value_usd)
                chain_breakdown[chain]["positions"] += 1
            
            # Calculate percentages
            for chain_data in chain_breakdown.values():
                chain_data["percentage"] = (chain_data["total_value"] / float(total_current_value)) * 100 if total_current_value > 0 else 0
            
            return {
                "portfolio_summary": {
                    "total_deposited": float(total_deposited),
                    "total_current_value": float(total_current_value),
                    "total_rewards_earned": float(total_rewards),
                    "total_unrealized_pnl": float(total_unrealized_pnl),
                    "portfolio_return_percentage": float(portfolio_return),
                    "active_positions": len(active_positions),
                    "protocols_used": len(protocol_breakdown),
                    "chains_used": len(chain_breakdown)
                },
                "protocol_breakdown": protocol_breakdown,
                "chain_breakdown": chain_breakdown,
                "risk_metrics": {
                    "average_risk_score": sum(self.supported_protocols[p.protocol_id].risk_score for p in active_positions if p.protocol_id in self.supported_protocols) / len(active_positions) if active_positions else 0,
                    "diversification_score": min(len(protocol_breakdown) / 5.0, 1.0),  # Max score at 5+ protocols
                    "chain_diversification": len(chain_breakdown)
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio overview: {e}")
            return {}

    async def get_position_details(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific position"""
        try:
            position = self.active_positions.get(position_id)
            if not position:
                return None
            
            protocol = self.supported_protocols.get(position.protocol_id)
            
            position_dict = asdict(position)
            position_dict["position_type"] = position.position_type.value
            position_dict["status"] = position.status.value
            position_dict["entry_timestamp"] = position.entry_timestamp.isoformat()
            position_dict["last_harvest"] = position.last_harvest.isoformat() if position.last_harvest else None
            
            # Add protocol information
            if protocol:
                position_dict["protocol_info"] = {
                    "name": protocol.name,
                    "type": protocol.protocol_type.value,
                    "chain": protocol.chain,
                    "current_apy": protocol.total_apy,
                    "risk_score": protocol.risk_score,
                    "contract_address": protocol.contract_address
                }
            
            # Calculate performance metrics
            days_in_position = (datetime.now(timezone.utc) - position.entry_timestamp).days
            if days_in_position > 0:
                daily_return = float(position.unrealized_pnl_usd) / days_in_position
                annualized_return = daily_return * 365 / float(position.amount_deposited) * 100
            else:
                daily_return = 0
                annualized_return = 0
            
            position_dict["performance"] = {
                "days_in_position": days_in_position,
                "daily_return_usd": daily_return,
                "annualized_return_percentage": annualized_return,
                "total_return_percentage": float(position.unrealized_pnl_usd + position.rewards_earned_usd) / float(position.amount_deposited) * 100
            }
            
            return position_dict
            
        except Exception as e:
            logger.error(f"Failed to get position details: {e}")
            return None

    async def get_analytics_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive DeFi analytics for dashboard"""
        try:
            # Protocol analytics
            total_protocols = len(self.supported_protocols)
            active_protocols = sum(1 for p in self.supported_protocols.values() if any(pos.protocol_id == p.protocol_id for pos in self.active_positions.values()))
            
            # Performance analytics
            active_positions = [p for p in self.active_positions.values() if p.status == PositionStatus.ACTIVE]
            
            total_tvl = sum(p.tvl_usd for p in self.supported_protocols.values())
            avg_apy = sum(p.total_apy for p in self.supported_protocols.values()) / len(self.supported_protocols)
            
            # Risk analytics
            avg_risk_score = sum(p.risk_score for p in self.supported_protocols.values()) / len(self.supported_protocols)
            
            # Position analytics
            position_types = {}
            for position in active_positions:
                pos_type = position.position_type.value
                if pos_type not in position_types:
                    position_types[pos_type] = {"count": 0, "total_value": 0}
                position_types[pos_type]["count"] += 1
                position_types[pos_type]["total_value"] += float(position.current_value_usd)
            
            return {
                "protocol_analytics": {
                    "total_protocols_supported": total_protocols,
                    "active_protocols": active_protocols,
                    "total_tvl_usd": float(total_tvl),
                    "average_apy": avg_apy,
                    "average_risk_score": avg_risk_score
                },
                "position_analytics": {
                    "total_positions": len(active_positions),
                    "position_types": position_types,
                    "total_value_locked": sum(float(p.current_value_usd) for p in active_positions),
                    "total_rewards_earned": sum(float(p.rewards_earned_usd) for p in active_positions)
                },
                "chain_distribution": {
                    chain: len([p for p in self.supported_protocols.values() if p.chain == chain])
                    for chain in set(p.chain for p in self.supported_protocols.values())
                },
                "opportunity_metrics": {
                    "high_yield_opportunities": len([p for p in self.supported_protocols.values() if p.total_apy > 10]),
                    "low_risk_opportunities": len([p for p in self.supported_protocols.values() if p.risk_score < 0.2]),
                    "audited_protocols": len([p for p in self.supported_protocols.values() if p.audit_status == "audited"])
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get analytics dashboard: {e}")
            return {}

    async def _load_protocols(self):
        """Load protocols from database"""
        try:
            if self.supabase:
                response = self.supabase.table('defi_protocols').select('*').execute()
                for protocol_data in response.data:
                    protocol = DeFiProtocol(
                        protocol_id=protocol_data["protocol_id"],
                        name=protocol_data["name"],
                        protocol_type=ProtocolType(protocol_data["protocol_type"]),
                        chain=protocol_data["chain"],
                        tvl_usd=Decimal(str(protocol_data["tvl_usd"])),
                        base_apy=protocol_data["base_apy"],
                        reward_apy=protocol_data["reward_apy"],
                        total_apy=protocol_data["total_apy"],
                        contract_address=protocol_data["contract_address"],
                        risk_score=protocol_data["risk_score"],
                        audit_status=protocol_data["audit_status"],
                        last_updated=datetime.fromisoformat(protocol_data["last_updated"]),
                        metadata=protocol_data.get("metadata", {})
                    )
                    self.supported_protocols[protocol.protocol_id] = protocol
        except Exception as e:
            logger.warning(f"Could not load protocols from database: {e}")

    async def _load_positions(self):
        """Load active positions from database"""
        try:
            if self.supabase:
                response = self.supabase.table('defi_positions').select('*').eq('status', 'active').execute()
                for position_data in response.data:
                    position = DeFiPosition(
                        position_id=position_data["position_id"],
                        user_wallet=position_data["user_wallet"],
                        protocol_id=position_data["protocol_id"],
                        position_type=PositionType(position_data["position_type"]),
                        status=PositionStatus(position_data["status"]),
                        asset_symbol=position_data["asset_symbol"],
                        amount_deposited=Decimal(str(position_data["amount_deposited"])),
                        current_value_usd=Decimal(str(position_data["current_value_usd"])),
                        rewards_earned_usd=Decimal(str(position_data["rewards_earned_usd"])),
                        unrealized_pnl_usd=Decimal(str(position_data["unrealized_pnl_usd"])),
                        entry_timestamp=datetime.fromisoformat(position_data["entry_timestamp"]),
                        last_harvest=datetime.fromisoformat(position_data["last_harvest"]) if position_data.get("last_harvest") else None,
                        auto_compound=position_data.get("auto_compound", True),
                        metadata=position_data.get("metadata", {})
                    )
                    self.active_positions[position.position_id] = position
        except Exception as e:
            logger.warning(f"Could not load positions from database: {e}")

    async def _protocol_monitoring_loop(self):
        """Background protocol monitoring"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._update_protocol_data()
                logger.debug("Protocol monitoring check completed")
            except Exception as e:
                logger.error(f"Error in protocol monitoring loop: {e}")

    async def _yield_optimization_loop(self):
        """Background yield optimization"""
        while True:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes
                await self._optimize_yields()
                logger.debug("Yield optimization check completed")
            except Exception as e:
                logger.error(f"Error in yield optimization loop: {e}")

    async def _auto_compound_loop(self):
        """Background auto-compounding"""
        while True:
            try:
                await asyncio.sleep(86400)  # Check daily
                await self._auto_compound_positions()
                logger.debug("Auto-compound check completed")
            except Exception as e:
                logger.error(f"Error in auto-compound loop: {e}")

    async def _update_protocol_data(self):
        """Update protocol data from external sources"""
        # Mock implementation - in real scenario, fetch from DeFi data providers
        for protocol in self.supported_protocols.values():
            # Simulate APY fluctuations
            base_apy = self.protocol_configs.get(protocol.chain, {}).get(protocol.protocol_id.split('_')[1], {}).get("base_apy", 5.0)
            protocol.base_apy = base_apy + (hash(str(datetime.now().hour)) % 100) * 0.01
            protocol.total_apy = protocol.base_apy * 1.3
            protocol.last_updated = datetime.now(timezone.utc)

    async def _optimize_yields(self):
        """Analyze and suggest yield optimizations"""
        # Check for better opportunities
        for position in self.active_positions.values():
            if position.status == PositionStatus.ACTIVE:
                current_protocol = self.supported_protocols.get(position.protocol_id)
                if current_protocol:
                    # Find better opportunities
                    better_protocols = [
                        p for p in self.supported_protocols.values()
                        if p.chain == current_protocol.chain and 
                        p.total_apy > current_protocol.total_apy * 1.1 and
                        p.risk_score <= current_protocol.risk_score * 1.2
                    ]
                    
                    if better_protocols:
                        logger.info(f"Found better yield opportunity for position {position.position_id}")

    async def _auto_compound_positions(self):
        """Auto-compound positions that have pending rewards"""
        for position in self.active_positions.values():
            if position.status == PositionStatus.ACTIVE and position.auto_compound:
                # Check if rewards should be harvested
                days_since_harvest = 7
                if position.last_harvest:
                    days_since_harvest = (datetime.now(timezone.utc) - position.last_harvest).days
                
                if days_since_harvest >= 7:  # Auto-compound weekly
                    try:
                        await self.harvest_rewards(position.position_id)
                        logger.info(f"Auto-compounded position {position.position_id}")
                    except Exception as e:
                        logger.error(f"Failed to auto-compound position {position.position_id}: {e}")

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        active_positions = len([p for p in self.active_positions.values() if p.status == PositionStatus.ACTIVE])
        total_tvl = sum(float(p.current_value_usd) for p in self.active_positions.values() if p.status == PositionStatus.ACTIVE)
        
        return {
            "service": "defi_protocol_integration_service",
            "status": "running",
            "supported_protocols": len(self.supported_protocols),
            "active_positions": active_positions,
            "total_tvl_usd": total_tvl,
            "chains_supported": list(set(p.chain for p in self.supported_protocols.values())),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_defi_protocol_integration_service():
    """Factory function to create DeFiProtocolIntegrationService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = DeFiProtocolIntegrationService(redis_client, supabase_client)
    return service