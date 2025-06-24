"""
Phase 5: Wallet-Agent Coordination Integration - Advanced Agent-Wallet Synergy
Deep integration between wallet operations and autonomous trading agents
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json

from ..core.service_registry import get_registry
from ..models.master_wallet_models import FundAllocation, WalletPerformanceMetrics
from ..services.wallet_event_streaming_service import WalletEventType

logger = logging.getLogger(__name__)

class AgentPerformanceProfile:
    """Agent performance profile for wallet allocation decisions"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.sharpe_ratio = Decimal("0")
        self.max_drawdown = Decimal("0")
        self.win_rate = Decimal("0")
        self.total_trades = 0
        self.avg_return = Decimal("0")
        self.risk_score = Decimal("0")
        self.consistency_score = Decimal("0")
        self.market_correlation = Decimal("0")
        self.allocation_efficiency = Decimal("0")
        self.last_updated = datetime.now(timezone.utc)

class WalletAgentCoordinationService:
    """
    Advanced coordination service between wallet operations and autonomous trading agents
    Phase 5: Deep integration for optimal fund allocation and agent performance optimization
    """
    
    def __init__(self):
        self.registry = get_registry()
        
        # Core services
        self.master_wallet_service = None
        self.wallet_coordination_service = None
        self.wallet_event_streaming_service = None
        
        # Agent services
        self.agent_management_service = None
        self.agent_performance_service = None
        self.agent_coordination_service = None
        
        # Coordination state
        self.agent_profiles: Dict[str, AgentPerformanceProfile] = {}
        self.wallet_agent_allocations: Dict[str, Dict[str, List[FundAllocation]]] = {}  # wallet_id -> agent_id -> allocations
        self.performance_thresholds = {
            "minimum_sharpe": Decimal("0.5"),
            "maximum_drawdown": Decimal("0.15"),
            "minimum_win_rate": Decimal("0.55"),
            "minimum_trades": 10
        }
        
        # Coordination metrics
        self.coordination_metrics = {
            "total_agent_allocations": 0,
            "active_agents": 0,
            "average_agent_performance": Decimal("0"),
            "total_allocated_to_agents": Decimal("0"),
            "agent_rebalancing_events": 0
        }
        
        self.coordination_active = False
        
        logger.info("WalletAgentCoordinationService initialized")
    
    async def initialize(self):
        """Initialize wallet-agent coordination service"""
        try:
            # Get core services
            self.master_wallet_service = self.registry.get_service("master_wallet_service")
            self.wallet_coordination_service = self.registry.get_service("wallet_coordination_service")
            self.wallet_event_streaming_service = self.registry.get_service("wallet_event_streaming_service")
            
            # Get agent services
            self.agent_management_service = self.registry.get_service("agent_management_service")
            self.agent_performance_service = self.registry.get_service("agent_performance_service")
            self.agent_coordination_service = self.registry.get_service("agent_coordination_service")
            
            if not self.master_wallet_service:
                logger.error("Master wallet service not available for agent coordination")
                return
            
            # Initialize agent profiles
            await self._initialize_agent_profiles()
            
            # Set up event streaming subscriptions
            if self.wallet_event_streaming_service:
                await self._setup_event_subscriptions()
            
            # Start coordination loops
            asyncio.create_task(self._agent_performance_monitoring_loop())
            asyncio.create_task(self._allocation_optimization_loop())
            asyncio.create_task(self._agent_rebalancing_loop())
            
            self.coordination_active = True
            logger.info("Wallet-agent coordination service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet-agent coordination: {e}")
            raise
    
    async def _initialize_agent_profiles(self):
        """Initialize performance profiles for all active agents"""
        try:
            if not self.agent_management_service:
                return
            
            # Get all active agents
            if hasattr(self.agent_management_service, 'get_agents'):
                agents = await self.agent_management_service.get_agents()
                
                for agent in agents:
                    agent_id = agent.agent_id if hasattr(agent, 'agent_id') else str(agent)
                    profile = AgentPerformanceProfile(agent_id)
                    
                    # Initialize with current performance data
                    await self._update_agent_profile(profile)
                    
                    self.agent_profiles[agent_id] = profile
            
            logger.info(f"Initialized {len(self.agent_profiles)} agent performance profiles")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent profiles: {e}")
    
    async def _setup_event_subscriptions(self):
        """Set up subscriptions to relevant wallet events"""
        try:
            # Subscribe to allocation and collection events
            relevant_events = [
                WalletEventType.FUNDS_ALLOCATED,
                WalletEventType.FUNDS_COLLECTED,
                WalletEventType.PERFORMANCE_CALCULATED
            ]
            
            await self.wallet_event_streaming_service.subscribe_to_events(
                self._handle_wallet_event,
                event_types=relevant_events
            )
            
            logger.info("Set up wallet event subscriptions for agent coordination")
            
        except Exception as e:
            logger.error(f"Failed to set up event subscriptions: {e}")
    
    async def _handle_wallet_event(self, event):
        """Handle wallet events for agent coordination"""
        try:
            if event.event_type == WalletEventType.FUNDS_ALLOCATED:
                await self._handle_allocation_event(event)
            elif event.event_type == WalletEventType.FUNDS_COLLECTED:
                await self._handle_collection_event(event)
            elif event.event_type == WalletEventType.PERFORMANCE_CALCULATED:
                await self._handle_performance_event(event)
            
        except Exception as e:
            logger.error(f"Failed to handle wallet event: {e}")
    
    async def _handle_allocation_event(self, event):
        """Handle fund allocation events affecting agents"""
        try:
            allocation_data = event.data.get("allocation", {})
            target_type = allocation_data.get("target_type")
            
            if target_type == "agent":
                agent_id = allocation_data.get("target_id")
                wallet_id = event.wallet_id
                
                # Update agent allocation tracking
                if wallet_id not in self.wallet_agent_allocations:
                    self.wallet_agent_allocations[wallet_id] = {}
                
                if agent_id not in self.wallet_agent_allocations[wallet_id]:
                    self.wallet_agent_allocations[wallet_id][agent_id] = []
                
                # Create allocation object
                allocation = FundAllocation(**allocation_data)
                self.wallet_agent_allocations[wallet_id][agent_id].append(allocation)
                
                # Notify agent of new allocation
                await self._notify_agent_of_allocation(agent_id, allocation)
                
                # Update coordination metrics
                self.coordination_metrics["total_agent_allocations"] += 1
                self.coordination_metrics["total_allocated_to_agents"] += allocation.allocated_amount_usd
                
                logger.info(f"Processed agent allocation: ${allocation.allocated_amount_usd} to agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle allocation event: {e}")
    
    async def _handle_collection_event(self, event):
        """Handle fund collection events affecting agents"""
        try:
            allocation_data = event.data.get("allocation", {})
            target_type = allocation_data.get("target_type")
            
            if target_type == "agent":
                agent_id = allocation_data.get("target_id")
                collected_amount = event.data.get("collected_amount", 0)
                
                # Notify agent of fund collection
                await self._notify_agent_of_collection(agent_id, collected_amount)
                
                logger.info(f"Processed agent collection: ${collected_amount} from agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle collection event: {e}")
    
    async def _handle_performance_event(self, event):
        """Handle performance calculation events"""
        try:
            wallet_id = event.wallet_id
            
            # Update agent profiles based on wallet performance
            await self._update_agent_profiles_from_wallet_performance(wallet_id)
            
        except Exception as e:
            logger.error(f"Failed to handle performance event: {e}")
    
    async def _notify_agent_of_allocation(self, agent_id: str, allocation: FundAllocation):
        """Notify agent of new fund allocation"""
        try:
            if self.agent_management_service:
                notification = {
                    "event_type": "fund_allocation",
                    "agent_id": agent_id,
                    "allocation_id": allocation.allocation_id,
                    "amount_usd": float(allocation.allocated_amount_usd),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                if hasattr(self.agent_management_service, 'notify_agent'):
                    await self.agent_management_service.notify_agent(agent_id, notification)
            
        except Exception as e:
            logger.error(f"Failed to notify agent {agent_id} of allocation: {e}")
    
    async def _notify_agent_of_collection(self, agent_id: str, collected_amount: float):
        """Notify agent of fund collection"""
        try:
            if self.agent_management_service:
                notification = {
                    "event_type": "fund_collection",
                    "agent_id": agent_id,
                    "collected_amount": collected_amount,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                if hasattr(self.agent_management_service, 'notify_agent'):
                    await self.agent_management_service.notify_agent(agent_id, notification)
            
        except Exception as e:
            logger.error(f"Failed to notify agent {agent_id} of collection: {e}")
    
    async def _update_agent_profile(self, profile: AgentPerformanceProfile):
        """Update agent performance profile with latest data"""
        try:
            if not self.agent_performance_service:
                return
            
            agent_id = profile.agent_id
            
            # Get performance data from agent performance service
            if hasattr(self.agent_performance_service, 'get_agent_performance'):
                performance_data = await self.agent_performance_service.get_agent_performance(agent_id)
                
                if performance_data:
                    profile.sharpe_ratio = Decimal(str(performance_data.get("sharpe_ratio", 0)))
                    profile.max_drawdown = Decimal(str(performance_data.get("max_drawdown", 0)))
                    profile.win_rate = Decimal(str(performance_data.get("win_rate", 0)))
                    profile.total_trades = performance_data.get("total_trades", 0)
                    profile.avg_return = Decimal(str(performance_data.get("avg_return", 0)))
                    profile.risk_score = Decimal(str(performance_data.get("risk_score", 0)))
                    profile.consistency_score = Decimal(str(performance_data.get("consistency_score", 0)))
                    profile.market_correlation = Decimal(str(performance_data.get("market_correlation", 0)))
                    profile.last_updated = datetime.now(timezone.utc)
            
            # Calculate allocation efficiency based on wallet allocations
            await self._calculate_allocation_efficiency(profile)
            
        except Exception as e:
            logger.error(f"Failed to update agent profile for {profile.agent_id}: {e}")
    
    async def _calculate_allocation_efficiency(self, profile: AgentPerformanceProfile):
        """Calculate how efficiently the agent uses allocated funds"""
        try:
            agent_id = profile.agent_id
            total_allocated = Decimal("0")
            total_current_value = Decimal("0")
            
            # Calculate across all wallet allocations for this agent
            for wallet_allocations in self.wallet_agent_allocations.values():
                if agent_id in wallet_allocations:
                    for allocation in wallet_allocations[agent_id]:
                        if allocation.is_active:
                            total_allocated += allocation.allocated_amount_usd
                            total_current_value += allocation.current_value_usd
            
            if total_allocated > 0:
                efficiency = (total_current_value - total_allocated) / total_allocated * 100
                profile.allocation_efficiency = efficiency
            else:
                profile.allocation_efficiency = Decimal("0")
            
        except Exception as e:
            logger.error(f"Failed to calculate allocation efficiency for agent {profile.agent_id}: {e}")
    
    async def _update_agent_profiles_from_wallet_performance(self, wallet_id: str):
        """Update agent profiles based on wallet performance data"""
        try:
            if wallet_id not in self.wallet_agent_allocations:
                return
            
            # Update profiles for all agents with allocations from this wallet
            for agent_id in self.wallet_agent_allocations[wallet_id]:
                if agent_id in self.agent_profiles:
                    await self._update_agent_profile(self.agent_profiles[agent_id])
            
        except Exception as e:
            logger.error(f"Failed to update agent profiles from wallet {wallet_id} performance: {e}")
    
    async def recommend_agent_allocation(self, wallet_id: str, available_amount: Decimal) -> List[Dict[str, Any]]:
        """
        Recommend optimal agent allocations based on performance profiles
        Phase 5: AI-driven allocation recommendations
        """
        try:
            recommendations = []
            
            # Get qualified agents (meet minimum performance thresholds)
            qualified_agents = await self._get_qualified_agents()
            
            if not qualified_agents:
                return recommendations
            
            # Sort agents by performance score
            sorted_agents = sorted(
                qualified_agents,
                key=lambda agent_id: self._calculate_agent_score(self.agent_profiles[agent_id]),
                reverse=True
            )
            
            # Allocate funds based on performance-weighted distribution
            total_score = sum(self._calculate_agent_score(self.agent_profiles[agent_id]) for agent_id in sorted_agents)
            
            for agent_id in sorted_agents[:5]:  # Top 5 agents
                profile = self.agent_profiles[agent_id]
                agent_score = self._calculate_agent_score(profile)
                
                # Calculate allocation percentage based on score
                allocation_percentage = agent_score / total_score
                recommended_amount = available_amount * allocation_percentage
                
                # Minimum allocation threshold
                if recommended_amount >= Decimal("100"):
                    recommendations.append({
                        "agent_id": agent_id,
                        "recommended_amount": float(recommended_amount),
                        "allocation_percentage": float(allocation_percentage * 100),
                        "performance_score": float(agent_score),
                        "sharpe_ratio": float(profile.sharpe_ratio),
                        "win_rate": float(profile.win_rate),
                        "max_drawdown": float(profile.max_drawdown),
                        "allocation_efficiency": float(profile.allocation_efficiency),
                        "reasoning": self._generate_allocation_reasoning(profile)
                    })
            
            logger.info(f"Generated {len(recommendations)} agent allocation recommendations for wallet {wallet_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate agent allocation recommendations: {e}")
            return []
    
    async def _get_qualified_agents(self) -> List[str]:
        """Get agents that meet minimum performance thresholds"""
        qualified_agents = []
        
        for agent_id, profile in self.agent_profiles.items():
            if (profile.sharpe_ratio >= self.performance_thresholds["minimum_sharpe"] and
                profile.max_drawdown <= self.performance_thresholds["maximum_drawdown"] and
                profile.win_rate >= self.performance_thresholds["minimum_win_rate"] and
                profile.total_trades >= self.performance_thresholds["minimum_trades"]):
                
                qualified_agents.append(agent_id)
        
        return qualified_agents
    
    def _calculate_agent_score(self, profile: AgentPerformanceProfile) -> Decimal:
        """Calculate composite performance score for agent"""
        try:
            # Weighted scoring algorithm
            score = (
                profile.sharpe_ratio * Decimal("0.3") +
                (Decimal("1") - profile.max_drawdown) * Decimal("0.2") +
                profile.win_rate * Decimal("0.2") +
                profile.consistency_score * Decimal("0.15") +
                profile.allocation_efficiency * Decimal("0.01") * Decimal("0.15")  # Convert percentage to decimal
            )
            
            return max(score, Decimal("0"))
            
        except Exception as e:
            logger.error(f"Failed to calculate agent score: {e}")
            return Decimal("0")
    
    def _generate_allocation_reasoning(self, profile: AgentPerformanceProfile) -> str:
        """Generate human-readable reasoning for allocation recommendation"""
        reasons = []
        
        if profile.sharpe_ratio > Decimal("1.0"):
            reasons.append("excellent risk-adjusted returns")
        elif profile.sharpe_ratio > Decimal("0.7"):
            reasons.append("good risk-adjusted returns")
        
        if profile.win_rate > Decimal("0.6"):
            reasons.append("high win rate")
        
        if profile.max_drawdown < Decimal("0.1"):
            reasons.append("low drawdown risk")
        
        if profile.allocation_efficiency > Decimal("10"):
            reasons.append("efficient fund utilization")
        
        if not reasons:
            reasons.append("meets minimum performance criteria")
        
        return f"Recommended due to {', '.join(reasons)}"
    
    async def execute_agent_rebalancing(self, wallet_id: str) -> Dict[str, Any]:
        """
        Execute agent rebalancing based on performance
        Phase 5: Automatic rebalancing for optimal performance
        """
        try:
            rebalancing_result = {
                "wallet_id": wallet_id,
                "rebalancing_actions": [],
                "total_reallocated": Decimal("0"),
                "success": False
            }
            
            if wallet_id not in self.wallet_agent_allocations:
                rebalancing_result["error"] = "No agent allocations found for wallet"
                return rebalancing_result
            
            # Identify underperforming agents
            underperforming_agents = await self._identify_underperforming_agents(wallet_id)
            
            # Collect funds from underperforming agents
            collected_funds = Decimal("0")
            for agent_id, collection_amount in underperforming_agents.items():
                try:
                    # Find allocation to collect from
                    allocations = self.wallet_agent_allocations[wallet_id][agent_id]
                    for allocation in allocations:
                        if allocation.is_active and allocation.total_pnl < Decimal("0"):
                            # Execute collection
                            from ..models.master_wallet_models import FundCollectionRequest
                            collection_request = FundCollectionRequest(
                                allocation_id=allocation.allocation_id,
                                collection_type="partial",
                                amount_usd=collection_amount
                            )
                            
                            collected = await self.master_wallet_service.collect_funds(wallet_id, collection_request)
                            collected_funds += collected
                            
                            rebalancing_result["rebalancing_actions"].append({
                                "action": "collection",
                                "agent_id": agent_id,
                                "amount": float(collected),
                                "reason": "underperformance"
                            })
                            break
                            
                except Exception as e:
                    logger.error(f"Failed to collect from agent {agent_id}: {e}")
                    continue
            
            # Reallocate to top-performing agents
            if collected_funds > Decimal("100"):
                recommendations = await self.recommend_agent_allocation(wallet_id, collected_funds)
                
                for recommendation in recommendations[:3]:  # Top 3 recommendations
                    try:
                        # Execute allocation
                        from ..models.master_wallet_models import FundAllocationRequest
                        allocation_request = FundAllocationRequest(
                            target_type="agent",
                            target_id=recommendation["agent_id"],
                            target_name=f"Agent {recommendation['agent_id']}",
                            amount_usd=Decimal(str(recommendation["recommended_amount"]))
                        )
                        
                        allocation = await self.master_wallet_service.allocate_funds(wallet_id, allocation_request)
                        
                        rebalancing_result["rebalancing_actions"].append({
                            "action": "allocation",
                            "agent_id": recommendation["agent_id"],
                            "amount": float(allocation.allocated_amount_usd),
                            "reason": "high_performance"
                        })
                        
                    except Exception as e:
                        logger.error(f"Failed to allocate to agent {recommendation['agent_id']}: {e}")
                        continue
            
            rebalancing_result["total_reallocated"] = float(collected_funds)
            rebalancing_result["success"] = True
            self.coordination_metrics["agent_rebalancing_events"] += 1
            
            logger.info(f"Executed agent rebalancing for wallet {wallet_id}: ${collected_funds} reallocated")
            return rebalancing_result
            
        except Exception as e:
            logger.error(f"Failed to execute agent rebalancing: {e}")
            rebalancing_result["error"] = str(e)
            return rebalancing_result
    
    async def _identify_underperforming_agents(self, wallet_id: str) -> Dict[str, Decimal]:
        """Identify agents underperforming and calculate collection amounts"""
        underperforming = {}
        
        try:
            if wallet_id not in self.wallet_agent_allocations:
                return underperforming
            
            for agent_id, allocations in self.wallet_agent_allocations[wallet_id].items():
                if agent_id in self.agent_profiles:
                    profile = self.agent_profiles[agent_id]
                    
                    # Check if agent is underperforming
                    is_underperforming = (
                        profile.sharpe_ratio < self.performance_thresholds["minimum_sharpe"] or
                        profile.max_drawdown > self.performance_thresholds["maximum_drawdown"] or
                        profile.win_rate < self.performance_thresholds["minimum_win_rate"]
                    )
                    
                    if is_underperforming:
                        # Calculate amount to collect (reduce allocation by 50%)
                        total_allocation = sum(
                            alloc.current_value_usd for alloc in allocations 
                            if alloc.is_active and alloc.total_pnl < Decimal("0")
                        )
                        
                        if total_allocation > Decimal("100"):
                            collection_amount = total_allocation * Decimal("0.5")
                            underperforming[agent_id] = collection_amount
            
            return underperforming
            
        except Exception as e:
            logger.error(f"Failed to identify underperforming agents: {e}")
            return underperforming
    
    async def _agent_performance_monitoring_loop(self):
        """Background task for monitoring agent performance"""
        while self.coordination_active:
            try:
                await asyncio.sleep(300)  # Update every 5 minutes
                
                # Update all agent profiles
                for profile in self.agent_profiles.values():
                    await self._update_agent_profile(profile)
                
                # Update coordination metrics
                await self._update_coordination_metrics()
                
            except Exception as e:
                logger.error(f"Error in agent performance monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _allocation_optimization_loop(self):
        """Background task for allocation optimization"""
        while self.coordination_active:
            try:
                await asyncio.sleep(900)  # Check every 15 minutes
                
                # Check for optimization opportunities
                if self.master_wallet_service:
                    for wallet_id in self.master_wallet_service.active_wallets:
                        await self._check_allocation_optimization_opportunities(wallet_id)
                
            except Exception as e:
                logger.error(f"Error in allocation optimization loop: {e}")
                await asyncio.sleep(300)
    
    async def _agent_rebalancing_loop(self):
        """Background task for automatic agent rebalancing"""
        while self.coordination_active:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Execute rebalancing for wallets with auto-distribution enabled
                if self.master_wallet_service:
                    for wallet_id, wallet in self.master_wallet_service.active_wallets.items():
                        if wallet.config.auto_distribution and wallet.config.performance_based_allocation:
                            await self.execute_agent_rebalancing(wallet_id)
                
            except Exception as e:
                logger.error(f"Error in agent rebalancing loop: {e}")
                await asyncio.sleep(1800)
    
    async def _check_allocation_optimization_opportunities(self, wallet_id: str):
        """Check for allocation optimization opportunities"""
        try:
            # Implementation would analyze current allocations and identify optimization opportunities
            pass
            
        except Exception as e:
            logger.error(f"Failed to check allocation optimization for wallet {wallet_id}: {e}")
    
    async def _update_coordination_metrics(self):
        """Update coordination performance metrics"""
        try:
            # Calculate metrics
            total_allocations = sum(
                len(allocations) for wallet_allocations in self.wallet_agent_allocations.values()
                for allocations in wallet_allocations.values()
            )
            
            active_agents = len([
                agent_id for agent_id, profile in self.agent_profiles.items()
                if profile.total_trades > 0
            ])
            
            avg_performance = Decimal("0")
            if self.agent_profiles:
                total_score = sum(
                    self._calculate_agent_score(profile) for profile in self.agent_profiles.values()
                )
                avg_performance = total_score / len(self.agent_profiles)
            
            self.coordination_metrics.update({
                "total_agent_allocations": total_allocations,
                "active_agents": active_agents,
                "average_agent_performance": float(avg_performance),
                "last_updated": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to update coordination metrics: {e}")
    
    async def get_coordination_status(self) -> Dict[str, Any]:
        """Get current wallet-agent coordination status"""
        return {
            "service": "wallet_agent_coordination_service",
            "status": "active" if self.coordination_active else "inactive",
            "agent_profiles_count": len(self.agent_profiles),
            "wallet_agent_mappings": len(self.wallet_agent_allocations),
            "coordination_metrics": self.coordination_metrics,
            "performance_thresholds": {k: float(v) for k, v in self.performance_thresholds.items()},
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_wallet_agent_coordination_service():
    """Factory function to create WalletAgentCoordinationService instance"""
    return WalletAgentCoordinationService()