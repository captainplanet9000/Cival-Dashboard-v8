"""
Phase 3: Cross-Service Wallet Coordination - Wallet-Aware Service Integration
Makes all platform services wallet-aware with centralized coordination
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from decimal import Decimal
import json

from ..core.service_registry import get_registry
from ..models.master_wallet_models import (
    MasterWallet, FundAllocation, WalletPerformanceMetrics
)

logger = logging.getLogger(__name__)

class WalletCoordinationService:
    """
    Central coordination service that makes all platform services wallet-aware
    Phase 3: Cross-service wallet integration and coordination
    """
    
    def __init__(self):
        self.registry = get_registry()
        self.master_wallet_service = None
        
        # Service coordination state
        self.wallet_aware_services: Dict[str, bool] = {}
        self.service_wallet_mappings: Dict[str, List[str]] = {}
        self.coordination_active = False
        
        # Performance tracking
        self.coordination_metrics: Dict[str, Any] = {}
        
        logger.info("WalletCoordinationService initialized")
    
    async def initialize(self):
        """Initialize wallet coordination across all services"""
        try:
            # Get master wallet service
            self.master_wallet_service = self.registry.get_service("master_wallet_service")
            if not self.master_wallet_service:
                logger.error("Master wallet service not available for coordination")
                return
            
            # Initialize coordination with all platform services
            await self._initialize_service_coordination()
            
            # Start coordination loops
            asyncio.create_task(self._coordination_monitoring_loop())
            asyncio.create_task(self._service_sync_loop())
            
            self.coordination_active = True
            logger.info("Wallet coordination service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet coordination: {e}")
            raise
    
    async def _initialize_service_coordination(self):
        """Initialize wallet coordination with all platform services"""
        try:
            # Get all registered services
            all_services = self.registry.list_services()
            
            # Services that should be wallet-aware
            wallet_aware_service_types = [
                "agent_management_service",
                "agent_performance_service", 
                "agent_coordination_service",
                "farm_management_service",
                "goal_management_service",
                "trading_safety_service",
                "portfolio_optimizer_service",
                "market_analysis_service",
                "risk_management_service",
                "performance_analytics_service"
            ]
            
            for service_name in wallet_aware_service_types:
                if service_name in all_services:
                    await self._integrate_service_with_wallets(service_name)
                    self.wallet_aware_services[service_name] = True
                    logger.info(f"Integrated {service_name} with wallet coordination")
                else:
                    self.wallet_aware_services[service_name] = False
                    logger.warning(f"Service {service_name} not available for wallet integration")
            
            logger.info(f"Wallet coordination initialized for {sum(self.wallet_aware_services.values())} services")
            
        except Exception as e:
            logger.error(f"Failed to initialize service coordination: {e}")
    
    async def _integrate_service_with_wallets(self, service_name: str):
        """Integrate a specific service with wallet awareness"""
        try:
            service = self.registry.get_service(service_name)
            if not service:
                return
            
            # Add wallet context to service if it supports it
            if hasattr(service, 'set_wallet_context'):
                await service.set_wallet_context(self.master_wallet_service)
            
            # Register service for wallet notifications
            if hasattr(service, 'enable_wallet_notifications'):
                await service.enable_wallet_notifications(True)
            
            # Initialize service with current wallet state
            await self._sync_service_with_wallets(service_name)
            
        except Exception as e:
            logger.error(f"Failed to integrate {service_name} with wallets: {e}")
    
    async def _sync_service_with_wallets(self, service_name: str):
        """Synchronize a service with current wallet state"""
        try:
            service = self.registry.get_service(service_name)
            if not service or not self.master_wallet_service:
                return
            
            # Get current wallet state
            active_wallets = self.master_wallet_service.active_wallets
            
            # Sync based on service type
            if service_name == "agent_management_service":
                await self._sync_agent_service_with_wallets(service, active_wallets)
            elif service_name == "farm_management_service":
                await self._sync_farm_service_with_wallets(service, active_wallets)
            elif service_name == "goal_management_service":
                await self._sync_goal_service_with_wallets(service, active_wallets)
            elif service_name == "performance_analytics_service":
                await self._sync_analytics_service_with_wallets(service, active_wallets)
            
        except Exception as e:
            logger.error(f"Failed to sync {service_name} with wallets: {e}")
    
    async def _sync_agent_service_with_wallets(self, agent_service, active_wallets: Dict[str, MasterWallet]):
        """Sync agent management service with wallet allocations"""
        try:
            # Get all agent allocations across wallets
            agent_allocations = {}
            
            for wallet_id, wallet in active_wallets.items():
                for allocation in wallet.allocations:
                    if allocation.target_type == "agent" and allocation.is_active:
                        agent_id = allocation.target_id
                        if agent_id not in agent_allocations:
                            agent_allocations[agent_id] = []
                        
                        agent_allocations[agent_id].append({
                            "wallet_id": wallet_id,
                            "allocation": allocation,
                            "allocated_amount": allocation.allocated_amount_usd,
                            "current_value": allocation.current_value_usd
                        })
            
            # Update agent service with wallet allocation info
            if hasattr(agent_service, 'update_wallet_allocations'):
                await agent_service.update_wallet_allocations(agent_allocations)
            
            logger.debug(f"Synced {len(agent_allocations)} agent allocations with agent service")
            
        except Exception as e:
            logger.error(f"Failed to sync agent service with wallets: {e}")
    
    async def _sync_farm_service_with_wallets(self, farm_service, active_wallets: Dict[str, MasterWallet]):
        """Sync farm management service with wallet allocations"""
        try:
            # Get all farm allocations across wallets
            farm_allocations = {}
            
            for wallet_id, wallet in active_wallets.items():
                for allocation in wallet.allocations:
                    if allocation.target_type == "farm" and allocation.is_active:
                        farm_id = allocation.target_id
                        if farm_id not in farm_allocations:
                            farm_allocations[farm_id] = []
                        
                        farm_allocations[farm_id].append({
                            "wallet_id": wallet_id,
                            "allocation": allocation,
                            "allocated_amount": allocation.allocated_amount_usd,
                            "current_value": allocation.current_value_usd
                        })
            
            # Update farm service with wallet allocation info
            if hasattr(farm_service, 'update_wallet_allocations'):
                await farm_service.update_wallet_allocations(farm_allocations)
            
            logger.debug(f"Synced {len(farm_allocations)} farm allocations with farm service")
            
        except Exception as e:
            logger.error(f"Failed to sync farm service with wallets: {e}")
    
    async def _sync_goal_service_with_wallets(self, goal_service, active_wallets: Dict[str, MasterWallet]):
        """Sync goal management service with wallet allocations"""
        try:
            # Get all goal allocations across wallets
            goal_allocations = {}
            
            for wallet_id, wallet in active_wallets.items():
                for allocation in wallet.allocations:
                    if allocation.target_type == "goal" and allocation.is_active:
                        goal_id = allocation.target_id
                        if goal_id not in goal_allocations:
                            goal_allocations[goal_id] = []
                        
                        goal_allocations[goal_id].append({
                            "wallet_id": wallet_id,
                            "allocation": allocation,
                            "allocated_amount": allocation.allocated_amount_usd,
                            "current_value": allocation.current_value_usd
                        })
            
            # Update goal service with wallet allocation info
            if hasattr(goal_service, 'update_wallet_allocations'):
                await goal_service.update_wallet_allocations(goal_allocations)
            
            logger.debug(f"Synced {len(goal_allocations)} goal allocations with goal service")
            
        except Exception as e:
            logger.error(f"Failed to sync goal service with wallets: {e}")
    
    async def _sync_analytics_service_with_wallets(self, analytics_service, active_wallets: Dict[str, MasterWallet]):
        """Sync performance analytics service with wallet data"""
        try:
            # Prepare wallet performance data for analytics
            wallet_performance_data = {}
            
            for wallet_id, wallet in active_wallets.items():
                try:
                    performance = await self.master_wallet_service.calculate_wallet_performance(wallet_id)
                    
                    wallet_performance_data[wallet_id] = {
                        "performance": performance,
                        "allocations": [alloc for alloc in wallet.allocations if alloc.is_active],
                        "total_value": performance.total_value_usd,
                        "total_pnl": performance.total_pnl
                    }
                    
                except Exception as e:
                    logger.warning(f"Could not get performance for wallet {wallet_id}: {e}")
                    continue
            
            # Update analytics service with wallet performance data
            if hasattr(analytics_service, 'update_wallet_performance_data'):
                await analytics_service.update_wallet_performance_data(wallet_performance_data)
            
            logger.debug(f"Synced performance data for {len(wallet_performance_data)} wallets with analytics service")
            
        except Exception as e:
            logger.error(f"Failed to sync analytics service with wallets: {e}")
    
    async def coordinate_allocation_request(self, wallet_id: str, target_type: str, target_id: str, amount: Decimal) -> Dict[str, Any]:
        """
        Coordinate fund allocation request across services
        Phase 3: Cross-service coordination for allocations
        """
        try:
            coordination_result = {
                "wallet_id": wallet_id,
                "target_type": target_type,
                "target_id": target_id,
                "amount": amount,
                "coordination_steps": [],
                "success": False
            }
            
            # Step 1: Validate with target service
            target_service_name = f"{target_type}_management_service"
            target_service = self.registry.get_service(target_service_name)
            
            if target_service:
                # Check if target can accept the allocation
                if hasattr(target_service, 'validate_allocation_request'):
                    validation_result = await target_service.validate_allocation_request(target_id, amount)
                    coordination_result["coordination_steps"].append({
                        "step": "target_validation",
                        "service": target_service_name,
                        "result": validation_result
                    })
                    
                    if not validation_result.get("valid", False):
                        coordination_result["error"] = "Target validation failed"
                        return coordination_result
            
            # Step 2: Check with risk management
            risk_service = self.registry.get_service("risk_management_service")
            if risk_service:
                if hasattr(risk_service, 'assess_allocation_risk'):
                    risk_assessment = await risk_service.assess_allocation_risk(wallet_id, target_type, target_id, amount)
                    coordination_result["coordination_steps"].append({
                        "step": "risk_assessment",
                        "service": "risk_management_service",
                        "result": risk_assessment
                    })
                    
                    if risk_assessment.get("risk_level", "medium") == "high":
                        coordination_result["error"] = "High risk allocation rejected"
                        return coordination_result
            
            # Step 3: Notify performance analytics
            analytics_service = self.registry.get_service("performance_analytics_service")
            if analytics_service:
                if hasattr(analytics_service, 'pre_allocation_analysis'):
                    analysis = await analytics_service.pre_allocation_analysis(target_type, target_id, amount)
                    coordination_result["coordination_steps"].append({
                        "step": "performance_analysis",
                        "service": "performance_analytics_service", 
                        "result": analysis
                    })
            
            # Step 4: Execute allocation through wallet service
            from ..models.master_wallet_models import FundAllocationRequest
            allocation_request = FundAllocationRequest(
                target_type=target_type,
                target_id=target_id,
                target_name=f"{target_type.title()} {target_id}",
                amount_usd=amount
            )
            
            allocation = await self.master_wallet_service.allocate_funds(wallet_id, allocation_request)
            coordination_result["allocation"] = allocation.dict()
            coordination_result["success"] = True
            
            # Step 5: Post-allocation notifications
            await self._notify_services_of_allocation(wallet_id, allocation)
            coordination_result["coordination_steps"].append({
                "step": "post_allocation_notifications",
                "result": "completed"
            })
            
            logger.info(f"Successfully coordinated allocation: {amount} to {target_type}:{target_id}")
            return coordination_result
            
        except Exception as e:
            logger.error(f"Failed to coordinate allocation request: {e}")
            coordination_result["error"] = str(e)
            return coordination_result
    
    async def coordinate_collection_request(self, wallet_id: str, allocation_id: str, collection_type: str) -> Dict[str, Any]:
        """
        Coordinate fund collection request across services
        Phase 3: Cross-service coordination for collections
        """
        try:
            coordination_result = {
                "wallet_id": wallet_id,
                "allocation_id": allocation_id,
                "collection_type": collection_type,
                "coordination_steps": [],
                "success": False
            }
            
            # Get allocation details
            wallet = self.master_wallet_service.active_wallets.get(wallet_id)
            if not wallet:
                coordination_result["error"] = "Wallet not found"
                return coordination_result
            
            allocation = None
            for alloc in wallet.allocations:
                if alloc.allocation_id == allocation_id:
                    allocation = alloc
                    break
            
            if not allocation:
                coordination_result["error"] = "Allocation not found"
                return coordination_result
            
            # Step 1: Notify target service of upcoming collection
            target_service_name = f"{allocation.target_type}_management_service"
            target_service = self.registry.get_service(target_service_name)
            
            if target_service:
                if hasattr(target_service, 'pre_collection_notification'):
                    notification_result = await target_service.pre_collection_notification(
                        allocation.target_id, allocation_id, collection_type
                    )
                    coordination_result["coordination_steps"].append({
                        "step": "pre_collection_notification",
                        "service": target_service_name,
                        "result": notification_result
                    })
            
            # Step 2: Execute collection through wallet service
            from ..models.master_wallet_models import FundCollectionRequest
            collection_request = FundCollectionRequest(
                allocation_id=allocation_id,
                collection_type=collection_type
            )
            
            collected_amount = await self.master_wallet_service.collect_funds(wallet_id, collection_request)
            coordination_result["collected_amount"] = float(collected_amount)
            coordination_result["success"] = True
            
            # Step 3: Post-collection notifications
            await self._notify_services_of_collection(wallet_id, allocation, collected_amount)
            coordination_result["coordination_steps"].append({
                "step": "post_collection_notifications",
                "result": "completed"
            })
            
            logger.info(f"Successfully coordinated collection: ${collected_amount} from {allocation.target_type}:{allocation.target_id}")
            return coordination_result
            
        except Exception as e:
            logger.error(f"Failed to coordinate collection request: {e}")
            coordination_result["error"] = str(e)
            return coordination_result
    
    async def _notify_services_of_allocation(self, wallet_id: str, allocation: FundAllocation):
        """Notify all relevant services of new allocation"""
        try:
            notification_data = {
                "event_type": "allocation_created",
                "wallet_id": wallet_id,
                "allocation": allocation.dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Notify target service
            target_service_name = f"{allocation.target_type}_management_service"
            target_service = self.registry.get_service(target_service_name)
            if target_service and hasattr(target_service, 'handle_wallet_notification'):
                await target_service.handle_wallet_notification(notification_data)
            
            # Notify analytics service
            analytics_service = self.registry.get_service("performance_analytics_service")
            if analytics_service and hasattr(analytics_service, 'handle_wallet_notification'):
                await analytics_service.handle_wallet_notification(notification_data)
            
            # Notify risk management
            risk_service = self.registry.get_service("risk_management_service")
            if risk_service and hasattr(risk_service, 'handle_wallet_notification'):
                await risk_service.handle_wallet_notification(notification_data)
            
        except Exception as e:
            logger.error(f"Failed to notify services of allocation: {e}")
    
    async def _notify_services_of_collection(self, wallet_id: str, allocation: FundAllocation, collected_amount: Decimal):
        """Notify all relevant services of fund collection"""
        try:
            notification_data = {
                "event_type": "funds_collected",
                "wallet_id": wallet_id,
                "allocation": allocation.dict(),
                "collected_amount": float(collected_amount),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Notify target service
            target_service_name = f"{allocation.target_type}_management_service"
            target_service = self.registry.get_service(target_service_name)
            if target_service and hasattr(target_service, 'handle_wallet_notification'):
                await target_service.handle_wallet_notification(notification_data)
            
            # Notify analytics service
            analytics_service = self.registry.get_service("performance_analytics_service")
            if analytics_service and hasattr(analytics_service, 'handle_wallet_notification'):
                await analytics_service.handle_wallet_notification(notification_data)
            
        except Exception as e:
            logger.error(f"Failed to notify services of collection: {e}")
    
    async def _coordination_monitoring_loop(self):
        """Background task for monitoring service coordination"""
        while self.coordination_active:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Monitor coordination health
                await self._check_coordination_health()
                
                # Update coordination metrics
                await self._update_coordination_metrics()
                
            except Exception as e:
                logger.error(f"Error in coordination monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _service_sync_loop(self):
        """Background task for keeping services synchronized with wallet state"""
        while self.coordination_active:
            try:
                await asyncio.sleep(300)  # Sync every 5 minutes
                
                # Re-sync all wallet-aware services
                for service_name, is_integrated in self.wallet_aware_services.items():
                    if is_integrated:
                        await self._sync_service_with_wallets(service_name)
                
            except Exception as e:
                logger.error(f"Error in service sync loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_coordination_health(self):
        """Check the health of service coordination"""
        try:
            health_status = {
                "coordination_active": self.coordination_active,
                "wallet_service_available": self.master_wallet_service is not None,
                "integrated_services": sum(self.wallet_aware_services.values()),
                "total_services": len(self.wallet_aware_services)
            }
            
            # Check if critical services are responding
            critical_services = ["agent_management_service", "performance_analytics_service"]
            for service_name in critical_services:
                service = self.registry.get_service(service_name)
                health_status[f"{service_name}_available"] = service is not None
            
            self.coordination_metrics["health"] = health_status
            
        except Exception as e:
            logger.error(f"Failed to check coordination health: {e}")
    
    async def _update_coordination_metrics(self):
        """Update coordination performance metrics"""
        try:
            if not self.master_wallet_service:
                return
            
            # Calculate coordination metrics
            active_wallets = len(self.master_wallet_service.active_wallets)
            total_allocations = 0
            
            for wallet in self.master_wallet_service.active_wallets.values():
                total_allocations += len([alloc for alloc in wallet.allocations if alloc.is_active])
            
            metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_wallets": active_wallets,
                "total_active_allocations": total_allocations,
                "integrated_services": sum(self.wallet_aware_services.values()),
                "coordination_uptime": self.coordination_active
            }
            
            self.coordination_metrics["performance"] = metrics
            
        except Exception as e:
            logger.error(f"Failed to update coordination metrics: {e}")
    
    async def get_coordination_status(self) -> Dict[str, Any]:
        """Get current coordination status and metrics"""
        return {
            "service": "wallet_coordination_service",
            "status": "active" if self.coordination_active else "inactive",
            "wallet_aware_services": self.wallet_aware_services,
            "metrics": self.coordination_metrics,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_wallet_coordination_service():
    """Factory function to create WalletCoordinationService instance"""
    return WalletCoordinationService()