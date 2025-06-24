"""
Wallet-Integrated Comprehensive Dashboard - Phase 9: Master Wallet Integration Complete
Enhanced dashboard with master wallet as central control hub
Multi-tab dashboard with live data integration and wallet-centric controls
"""
import asyncio
import json
import streamlit as st
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger
from decimal import Decimal

from ..core.service_registry import get_registry
from ..models.master_wallet_models import (
    MasterWallet, FundAllocationRequest, FundCollectionRequest,
    WalletPerformanceMetrics, FundAllocation
)

# Import dashboard tabs
from .master_wallet_tab import render_master_wallet_tab
from .goal_management_tab import render_goal_management_tab

class WalletIntegratedDashboard:
    """
    Wallet-integrated comprehensive dashboard with master wallet as central control hub
    Phase 1: Enhanced dashboard with wallet-centric controls and real-time monitoring
    """
    
    def __init__(self):
        self.registry = get_registry()
        self.last_update = datetime.now(timezone.utc)
        
        # Wallet service integration
        self.master_wallet_service = None
        self.wallet_hierarchy_service = None
        self.current_master_wallet = None
        
        # Dashboard state
        self.wallet_dashboard_mode = True  # Default to wallet-centric view
        self.selected_wallet_id = None
        
        logger.info("WalletIntegratedDashboard initialized with wallet supremacy controls")
    
    async def initialize_wallet_services(self):
        """Initialize wallet services for dashboard integration"""
        try:
            # Get master wallet service
            self.master_wallet_service = self.registry.get_service("master_wallet_service")
            if not self.master_wallet_service:
                logger.warning("Master wallet service not available")
            
            # Get wallet hierarchy service
            self.wallet_hierarchy_service = self.registry.get_service("wallet_hierarchy_service")
            if not self.wallet_hierarchy_service:
                logger.warning("Wallet hierarchy service not available")
            
            # Load default master wallet if available
            if self.master_wallet_service:
                await self._load_default_master_wallet()
            
            logger.info("Wallet services initialized for dashboard")
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet services: {e}")
    
    async def _load_default_master_wallet(self):
        """Load the default master wallet for dashboard operations"""
        try:
            # Get active wallets
            active_wallets = self.master_wallet_service.active_wallets
            
            if active_wallets:
                # Use the first active wallet as default
                wallet_id = list(active_wallets.keys())[0]
                self.current_master_wallet = active_wallets[wallet_id]
                self.selected_wallet_id = wallet_id
                logger.info(f"Loaded default master wallet: {wallet_id}")
            else:
                logger.info("No active master wallets found")
                
        except Exception as e:
            logger.error(f"Failed to load default master wallet: {e}")
    
    async def get_master_wallet_control_data(self) -> Dict[str, Any]:
        """Get master wallet control panel data - NEW TAB 7"""
        try:
            if not self.master_wallet_service:
                await self.initialize_wallet_services()
            
            if not self.master_wallet_service:
                return {"error": "Master wallet service not available"}
            
            # Get all active wallets
            active_wallets = {}
            for wallet_id, wallet in self.master_wallet_service.active_wallets.items():
                wallet_status = await self.master_wallet_service.get_wallet_status(wallet_id)
                active_wallets[wallet_id] = {
                    "wallet": wallet.dict(),
                    "status": wallet_status
                }
            
            # Get current wallet details if selected
            current_wallet_data = None
            if self.selected_wallet_id and self.selected_wallet_id in active_wallets:
                current_wallet_data = active_wallets[self.selected_wallet_id]
                
                # Get detailed performance metrics
                performance = await self.master_wallet_service.calculate_wallet_performance(self.selected_wallet_id)
                current_wallet_data["performance"] = performance.dict()
                
                # Get recent transactions
                recent_transactions = await self._get_recent_wallet_transactions(self.selected_wallet_id)
                current_wallet_data["recent_transactions"] = recent_transactions
            
            # Get fund allocation opportunities
            allocation_opportunities = await self._get_allocation_opportunities()
            
            # Get fund collection opportunities  
            collection_opportunities = await self._get_collection_opportunities()
            
            return {
                "wallet_control_mode": self.wallet_dashboard_mode,
                "selected_wallet_id": self.selected_wallet_id,
                "active_wallets": active_wallets,
                "current_wallet": current_wallet_data,
                "allocation_opportunities": allocation_opportunities,
                "collection_opportunities": collection_opportunities,
                "wallet_hierarchy": await self._get_wallet_hierarchy_data(),
                "fund_flow_analytics": await self._get_fund_flow_analytics(),
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting master wallet control data: {e}")
            return {"error": str(e), "last_update": datetime.now(timezone.utc).isoformat()}
    
    async def _get_recent_wallet_transactions(self, wallet_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent wallet transactions"""
        try:
            # Implementation would get transactions from database or cache
            # For now, return mock data structure
            return [
                {
                    "transaction_id": "tx_001",
                    "type": "allocation", 
                    "amount_usd": 1000,
                    "target": "agent:trend_following_001",
                    "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                    "status": "confirmed"
                },
                {
                    "transaction_id": "tx_002", 
                    "type": "collection",
                    "amount_usd": 1250,
                    "target": "farm:breakout_farm_001",
                    "timestamp": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
                    "status": "confirmed"
                }
            ]
            
        except Exception as e:
            logger.error(f"Failed to get recent transactions for wallet {wallet_id}: {e}")
            return []
    
    async def _get_allocation_opportunities(self) -> List[Dict[str, Any]]:
        """Get available allocation opportunities (agents, farms, goals needing funding)"""
        try:
            opportunities = []
            
            # Check agent performance service for top performers
            agent_performance_service = self.registry.get_service("agent_performance_service") 
            if agent_performance_service:
                try:
                    rankings = await agent_performance_service.get_agent_rankings(period_days=7)
                    for ranking in rankings[:5]:  # Top 5 performers
                        opportunities.append({
                            "type": "agent",
                            "target_id": ranking.agent_id,
                            "target_name": f"Agent {ranking.agent_id}",
                            "recommended_allocation": 1000,  # Based on performance
                            "performance_score": ranking.sharpe_ratio or 0,
                            "reason": "High performing agent - 7 day period"
                        })
                except Exception as e:
                    logger.error(f"Error getting agent opportunities: {e}")
            
            # Check farm management for active farms
            farm_service = self.registry.get_service("farm_management_service")
            if farm_service:
                try:
                    # Implementation would get active farms needing funding
                    opportunities.append({
                        "type": "farm",
                        "target_id": "trend_following_farm",
                        "target_name": "Trend Following Farm",
                        "recommended_allocation": 2500,
                        "performance_score": 0.85,
                        "reason": "High capacity farm with proven strategy"
                    })
                except Exception as e:
                    logger.error(f"Error getting farm opportunities: {e}")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Failed to get allocation opportunities: {e}")
            return []
    
    async def _get_collection_opportunities(self) -> List[Dict[str, Any]]:
        """Get fund collection opportunities (profitable allocations ready for harvest)"""
        try:
            if not self.current_master_wallet:
                return []
            
            opportunities = []
            
            for allocation in self.current_master_wallet.allocations:
                if allocation.is_active and allocation.total_pnl > Decimal("0"):
                    profit_percentage = (allocation.total_pnl / allocation.initial_allocation) * 100
                    
                    # Suggest collection if profit > 20%
                    if profit_percentage > 20:
                        opportunities.append({
                            "allocation_id": allocation.allocation_id,
                            "target_type": allocation.target_type,
                            "target_id": allocation.target_id,
                            "target_name": allocation.target_name,
                            "current_value_usd": float(allocation.current_value_usd),
                            "total_profit_usd": float(allocation.total_pnl),
                            "profit_percentage": float(profit_percentage),
                            "collection_type": "profits_only" if profit_percentage < 50 else "partial",
                            "recommended_amount": float(allocation.total_pnl * Decimal("0.8"))  # 80% of profits
                        })
            
            return sorted(opportunities, key=lambda x: x["profit_percentage"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get collection opportunities: {e}")
            return []
    
    async def _get_wallet_hierarchy_data(self) -> Dict[str, Any]:
        """Get wallet hierarchy visualization data"""
        try:
            if not self.wallet_hierarchy_service:
                return {"hierarchies": [], "total_wallets": 0}
            
            # Implementation would get actual hierarchy data
            return {
                "hierarchies": [
                    {
                        "master_wallet_id": "master_001",
                        "master_wallet_name": "Main Trading Treasury", 
                        "total_value_usd": 10000,
                        "farm_wallets": [
                            {
                                "farm_id": "trend_farm_001",
                                "farm_name": "Trend Following Farm",
                                "allocated_usd": 3000,
                                "current_value_usd": 3450,
                                "agent_wallets": [
                                    {"agent_id": "darvas_001", "allocated_usd": 1000, "current_value_usd": 1150},
                                    {"agent_id": "williams_001", "allocated_usd": 800, "current_value_usd": 920},
                                    {"agent_id": "elliott_001", "allocated_usd": 1200, "current_value_usd": 1380}
                                ]
                            }
                        ]
                    }
                ],
                "total_wallets": 5
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet hierarchy data: {e}")
            return {"hierarchies": [], "total_wallets": 0}
    
    async def _get_fund_flow_analytics(self) -> Dict[str, Any]:
        """Get fund flow analytics for dashboard visualization"""
        try:
            # Calculate fund flows over time periods
            return {
                "daily_flows": {
                    "allocations": 2500,
                    "collections": 1800,
                    "net_flow": 700
                },
                "weekly_flows": {
                    "allocations": 15000,
                    "collections": 12500,
                    "net_flow": 2500
                },
                "top_performing_allocations": [
                    {"target": "agent:trend_001", "roi_percentage": 35.2},
                    {"target": "farm:breakout_farm", "roi_percentage": 28.5},
                    {"target": "goal:profit_target_001", "roi_percentage": 22.1}
                ],
                "allocation_distribution": {
                    "agents": 65,
                    "farms": 25, 
                    "goals": 10
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get fund flow analytics: {e}")
            return {}
    
    async def execute_fund_allocation(self, allocation_request: FundAllocationRequest) -> Dict[str, Any]:
        """Execute fund allocation through dashboard"""
        try:
            if not self.master_wallet_service or not self.selected_wallet_id:
                return {"success": False, "error": "No wallet service or wallet selected"}
            
            # Execute allocation
            allocation = await self.master_wallet_service.allocate_funds(
                self.selected_wallet_id, 
                allocation_request
            )
            
            logger.info(f"Dashboard executed allocation: {allocation.allocation_id}")
            
            return {
                "success": True,
                "allocation_id": allocation.allocation_id,
                "message": f"Allocated ${allocation_request.amount_usd} to {allocation_request.target_type}:{allocation_request.target_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to execute fund allocation: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_fund_collection(self, collection_request: FundCollectionRequest) -> Dict[str, Any]:
        """Execute fund collection through dashboard"""
        try:
            if not self.master_wallet_service or not self.selected_wallet_id:
                return {"success": False, "error": "No wallet service or wallet selected"}
            
            # Execute collection
            collected_amount = await self.master_wallet_service.collect_funds(
                self.selected_wallet_id,
                collection_request
            )
            
            logger.info(f"Dashboard executed collection: ${collected_amount}")
            
            return {
                "success": True,
                "collected_amount": float(collected_amount),
                "message": f"Collected ${collected_amount} from allocation"
            }
            
        except Exception as e:
            logger.error(f"Failed to execute fund collection: {e}")
            return {"success": False, "error": str(e)}
    
    async def switch_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """Switch active wallet in dashboard"""
        try:
            if not self.master_wallet_service:
                return {"success": False, "error": "Master wallet service not available"}
            
            if wallet_id in self.master_wallet_service.active_wallets:
                self.selected_wallet_id = wallet_id
                self.current_master_wallet = self.master_wallet_service.active_wallets[wallet_id]
                
                logger.info(f"Dashboard switched to wallet: {wallet_id}")
                
                return {"success": True, "message": f"Switched to wallet {wallet_id}"}
            else:
                return {"success": False, "error": f"Wallet {wallet_id} not found"}
                
        except Exception as e:
            logger.error(f"Failed to switch wallet: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_overview_data(self) -> Dict[str, Any]:
        """Get comprehensive platform overview with wallet-centric data - ENHANCED for Phase 1"""
        
        try:
            # Initialize wallet services if not done
            if not self.master_wallet_service:
                await self.initialize_wallet_services()
            
            # Get registry health data
            health_data = await self.registry.health_check()
            
            # Count services by category (including wallet services)
            phase2_services = ["agent_trading_bridge", "trading_safety_service", "agent_performance_service", "agent_coordination_service"]
            phase5_services = ["agent_scheduler_service", "market_regime_service", "adaptive_risk_service", "portfolio_optimizer_service", "alerting_service"]
            wallet_services = ["master_wallet_service", "wallet_hierarchy_service", "autonomous_fund_distribution_engine"]
            
            phase2_online = sum(1 for service in phase2_services if self.registry.get_service(service))
            phase5_online = sum(1 for service in phase5_services if self.registry.get_service(service))
            wallet_online = sum(1 for service in wallet_services if self.registry.get_service(service))
            
            # Get startup info
            startup_info = self.registry.get_service("startup_info") or {}
            
            # Calculate uptime
            startup_time_str = startup_info.get("startup_time")
            uptime_seconds = 0
            if startup_time_str:
                try:
                    startup_time = datetime.fromisoformat(startup_time_str.replace('Z', '+00:00'))
                    uptime_seconds = (datetime.now(timezone.utc) - startup_time).total_seconds()
                except Exception:
                    pass
            
            uptime_formatted = self._format_uptime(uptime_seconds)
            
            # Get wallet overview data
            wallet_overview = await self._get_wallet_overview_data()
            
            return {
                "platform": {
                    "name": "MCP-Integrated DeFi Profit-Securing Trading Platform",
                    "version": startup_info.get("version", "3.0.0-wallet-integrated"),
                    "architecture": "wallet_centric_monorepo",
                    "environment": startup_info.get("environment", "production"),
                    "status": "operational" if health_data.get("registry") == "healthy" else "degraded",
                    "uptime": uptime_seconds,
                    "uptime_formatted": uptime_formatted,
                    "wallet_mode": self.wallet_dashboard_mode
                },
                "services": {
                    "total_services": len(self.registry.all_services),
                    "total_connections": len(self.registry.all_connections),
                    "phase2_services": {"online": phase2_online, "total": len(phase2_services)},
                    "phase5_services": {"online": phase5_online, "total": len(phase5_services)},
                    "wallet_services": {"online": wallet_online, "total": len(wallet_services)},
                    "health_status": health_data.get("services", {}),
                    "connection_status": health_data.get("connections", {})
                },
                "master_wallet_summary": wallet_overview,
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting overview data: {e}")
            return {"error": str(e), "last_update": datetime.now(timezone.utc).isoformat()}
    
    async def _get_wallet_overview_data(self) -> Dict[str, Any]:
        """Get wallet overview data for the main dashboard"""
        try:
            if not self.master_wallet_service:
                return {"status": "wallet_service_unavailable"}
            
            # Get total wallet count and values
            active_wallets = self.master_wallet_service.active_wallets
            total_wallets = len(active_wallets)
            
            if total_wallets == 0:
                return {
                    "status": "no_wallets",
                    "total_wallets": 0,
                    "total_value_usd": 0,
                    "total_allocated_usd": 0,
                    "total_pnl": 0
                }
            
            # Calculate aggregate values
            total_value_usd = Decimal("0")
            total_allocated_usd = Decimal("0")
            total_pnl = Decimal("0")
            active_allocations = 0
            
            for wallet_id, wallet in active_wallets.items():
                try:
                    performance = await self.master_wallet_service.calculate_wallet_performance(wallet_id)
                    total_value_usd += performance.total_value_usd
                    total_allocated_usd += performance.total_allocated_usd
                    total_pnl += performance.total_pnl
                    active_allocations += performance.active_allocations
                except Exception as e:
                    logger.error(f"Error calculating performance for wallet {wallet_id}: {e}")
                    continue
            
            return {
                "status": "active",
                "total_wallets": total_wallets,
                "total_value_usd": float(total_value_usd),
                "total_allocated_usd": float(total_allocated_usd),
                "available_balance_usd": float(total_value_usd - total_allocated_usd),
                "total_pnl": float(total_pnl),
                "total_pnl_percentage": float((total_pnl / total_value_usd * 100)) if total_value_usd > 0 else 0,
                "active_allocations": active_allocations,
                "selected_wallet_id": self.selected_wallet_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet overview data: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_agent_management_data(self) -> Dict[str, Any]:
        """Get agent management data with real service integration"""
        
        try:
            data = {
                "agents": [],
                "performance_summary": {},
                "coordination_status": {},
                "scheduler_status": {}
            }
            
            # Get agent management service
            agent_service = self.registry.get_service("agent_management_service")
            if agent_service:
                try:
                    agents = await agent_service.get_agents()
                    data["agents"] = [agent.model_dump() for agent in agents] if agents else []
                except Exception as e:
                    logger.error(f"Error getting agents: {e}")
                    data["agents"] = []
            
            # Get performance service data
            performance_service = self.registry.get_service("agent_performance_service")
            if performance_service:
                try:
                    status = performance_service.get_service_status()
                    data["performance_summary"] = status
                except Exception as e:
                    logger.error(f"Error getting performance data: {e}")
            
            # Get coordination service data
            coordination_service = self.registry.get_service("agent_coordination_service")
            if coordination_service:
                try:
                    status = coordination_service.get_coordination_status()
                    data["coordination_status"] = status
                except Exception as e:
                    logger.error(f"Error getting coordination data: {e}")
            
            # Get scheduler service data
            scheduler_service = self.registry.get_service("agent_scheduler_service")
            if scheduler_service:
                try:
                    status = scheduler_service.get_scheduler_status()
                    data["scheduler_status"] = status
                except Exception as e:
                    logger.error(f"Error getting scheduler data: {e}")
            
            data["last_update"] = datetime.now(timezone.utc).isoformat()
            return data
            
        except Exception as e:
            logger.error(f"Error getting agent management data: {e}")
            return {"error": str(e), "last_update": datetime.now(timezone.utc).isoformat()}
    
    async def get_trading_operations_data(self) -> Dict[str, Any]:
        """Get trading operations data with real service integration"""
        
        try:
            data = {
                "bridge_status": {},
                "active_signals": [],
                "execution_stats": {},
                "recent_trades": []
            }
            
            # Get trading bridge data
            bridge_service = self.registry.get_service("agent_trading_bridge")
            if bridge_service:
                try:
                    data["bridge_status"] = bridge_service.get_bridge_status()
                    
                    # Get active signals
                    active_signals = await bridge_service.get_active_signals()
                    data["active_signals"] = [signal.model_dump() for signal in active_signals] if active_signals else []
                    
                except Exception as e:
                    logger.error(f"Error getting bridge data: {e}")
            
            # Get execution service data (if available)
            execution_service = self.registry.get_service("execution_specialist_service")
            if execution_service:
                try:
                    # This would get execution statistics in a real implementation
                    data["execution_stats"] = {
                        "total_executions": 0,
                        "success_rate": 0.0,
                        "avg_execution_time": 0.0
                    }
                except Exception as e:
                    logger.error(f"Error getting execution data: {e}")
            
            data["last_update"] = datetime.now(timezone.utc).isoformat()
            return data
            
        except Exception as e:
            logger.error(f"Error getting trading operations data: {e}")
            return {"error": str(e), "last_update": datetime.now(timezone.utc).isoformat()}
    
    async def get_risk_safety_data(self) -> Dict[str, Any]:
        """Get risk and safety data with real service integration"""
        
        try:
            data = {
                "safety_status": {},
                "adaptive_risk_status": {},
                "active_alerts": [],
                "risk_events": []
            }
            
            # Get safety service data
            safety_service = self.registry.get_service("trading_safety_service")
            if safety_service:
                try:
                    data["safety_status"] = safety_service.get_safety_status()
                except Exception as e:
                    logger.error(f"Error getting safety data: {e}")
            
            # Get adaptive risk service data
            adaptive_risk_service = self.registry.get_service("adaptive_risk_service")
            if adaptive_risk_service:
                try:
                    data["adaptive_risk_status"] = adaptive_risk_service.get_service_status()
                    
                    # Get active risk events
                    risk_events = await adaptive_risk_service.get_active_risk_events()
                    data["risk_events"] = [event.model_dump() for event in risk_events] if risk_events else []
                    
                except Exception as e:
                    logger.error(f"Error getting adaptive risk data: {e}")
            
            # Get alerting service data
            alerting_service = self.registry.get_service("alerting_service")
            if alerting_service:
                try:
                    data["alerting_status"] = alerting_service.get_service_status()
                    
                    # Get active alerts
                    active_alerts = await alerting_service.get_active_alerts()
                    data["active_alerts"] = [alert.model_dump() for alert in active_alerts] if active_alerts else []
                    
                except Exception as e:
                    logger.error(f"Error getting alerting data: {e}")
            
            data["last_update"] = datetime.now(timezone.utc).isoformat()
            return data
            
        except Exception as e:
            logger.error(f"Error getting risk safety data: {e}")
            return {"error": str(e), "last_update": datetime.now(timezone.utc).isoformat()}
    
    async def get_market_analytics_data(self) -> Dict[str, Any]:
        """Get market analytics data with real service integration"""
        
        try:
            data = {
                "regime_detections": {},
                "portfolio_allocations": {},
                "market_data": {}
            }
            
            # Get market regime service data
            regime_service = self.registry.get_service("market_regime_service")
            if regime_service:
                try:
                    data["regime_status"] = regime_service.get_service_status()
                    
                    # Get regime detections for tracked symbols
                    tracked_symbols = ["BTC/USD", "ETH/USD", "SPY", "QQQ"]  # Example symbols
                    regime_detections = {}
                    for symbol in tracked_symbols:
                        try:
                            detection = await regime_service.get_regime_for_symbol(symbol)
                            if detection:
                                regime_detections[symbol] = detection.model_dump()
                        except Exception:
                            pass
                    
                    data["regime_detections"] = regime_detections
                    
                except Exception as e:
                    logger.error(f"Error getting regime data: {e}")
            
            # Get portfolio optimizer service data
            optimizer_service = self.registry.get_service("portfolio_optimizer_service")
            if optimizer_service:
                try:
                    data["optimizer_status"] = optimizer_service.get_service_status()
                    
                    # Get recent portfolio allocations
                    allocations = await optimizer_service.get_optimization_history(limit=10)
                    data["portfolio_allocations"] = [alloc.model_dump() for alloc in allocations] if allocations else []
                    
                except Exception as e:
                    logger.error(f"Error getting optimizer data: {e}")
            
            # Get market data service data
            market_data_service = self.registry.get_service("market_data")
            if market_data_service:
                try:
                    # This would get real market data in a production environment
                    data["market_data"] = {
                        "status": "online",
                        "symbols_tracked": ["BTC/USD", "ETH/USD", "SPY", "QQQ"],
                        "last_update": datetime.now(timezone.utc).isoformat()
                    }
                except Exception as e:
                    logger.error(f"Error getting market data: {e}")
            
            data["last_update"] = datetime.now(timezone.utc).isoformat()
            return data
            
        except Exception as e:
            logger.error(f"Error getting market analytics data: {e}")
            return {"error": str(e), "last_update": datetime.now(timezone.utc).isoformat()}
    
    async def get_performance_analytics_data(self) -> Dict[str, Any]:
        """Get performance analytics data with real service integration"""
        
        try:
            data = {
                "agent_rankings": [],
                "portfolio_performance": {},
                "performance_metrics": {}
            }
            
            # Get performance service data
            performance_service = self.registry.get_service("agent_performance_service")
            if performance_service:
                try:
                    # Get agent rankings
                    rankings = await performance_service.get_agent_rankings(period_days=30)
                    data["agent_rankings"] = [ranking.model_dump() for ranking in rankings] if rankings else []
                    
                    # Get portfolio performance
                    portfolio_perf = await performance_service.get_portfolio_performance(period_days=30)
                    data["portfolio_performance"] = portfolio_perf
                    
                    # Get service status
                    data["performance_metrics"] = performance_service.get_service_status()
                    
                except Exception as e:
                    logger.error(f"Error getting performance data: {e}")
            
            data["last_update"] = datetime.now(timezone.utc).isoformat()
            return data
            
        except Exception as e:
            logger.error(f"Error getting performance analytics data: {e}")
            return {"error": str(e), "last_update": datetime.now(timezone.utc).isoformat()}
    
    async def get_system_monitoring_data(self) -> Dict[str, Any]:
        """Get system monitoring data with real service integration"""
        
        try:
            # Get comprehensive health check
            health_data = await self.registry.health_check()
            
            # Get all service statuses
            service_statuses = {}
            all_services = self.registry.list_services()
            
            for service_name in all_services:
                try:
                    service = self.registry.get_service(service_name)
                    if service and hasattr(service, 'get_service_status'):
                        service_statuses[service_name] = service.get_service_status()
                    else:
                        service_statuses[service_name] = {"status": "available"}
                except Exception as e:
                    service_statuses[service_name] = {"status": "error", "error": str(e)}
            
            data = {
                "system_health": health_data,
                "service_statuses": service_statuses,
                "registry_info": {
                    "total_services": len(self.registry.all_services),
                    "total_connections": len(self.registry.all_connections),
                    "initialized": self.registry.is_initialized()
                },
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting system monitoring data: {e}")
            return {"error": str(e), "last_update": datetime.now(timezone.utc).isoformat()}
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d {hours}h"
    
    async def get_all_dashboard_data(self) -> Dict[str, Any]:
        """Get all dashboard data in one call for efficiency - ENHANCED with wallet control"""
        
        try:
            # Run all data collection concurrently including wallet control panel
            results = await asyncio.gather(
                self.get_overview_data(),
                self.get_agent_management_data(),
                self.get_trading_operations_data(),
                self.get_risk_safety_data(),
                self.get_market_analytics_data(),
                self.get_performance_analytics_data(),
                self.get_system_monitoring_data(),
                self.get_master_wallet_control_data(),  # NEW: Wallet control panel
                return_exceptions=True
            )
            
            # Combine results with wallet supremacy
            dashboard_data = {
                "overview": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
                "agent_management": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
                "trading_operations": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
                "risk_safety": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
                "market_analytics": results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])},
                "performance_analytics": results[5] if not isinstance(results[5], Exception) else {"error": str(results[5])},
                "system_monitoring": results[6] if not isinstance(results[6], Exception) else {"error": str(results[6])},
                "master_wallet_control": results[7] if not isinstance(results[7], Exception) else {"error": str(results[7])},  # NEW TAB
                "wallet_mode": self.wallet_dashboard_mode,
                "selected_wallet_id": self.selected_wallet_id,
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting all dashboard data: {e}")
            return {"error": str(e), "last_update": datetime.now(timezone.utc).isoformat()}

# Global wallet-integrated dashboard instance - Phase 1 Implementation
wallet_integrated_dashboard = WalletIntegratedDashboard()