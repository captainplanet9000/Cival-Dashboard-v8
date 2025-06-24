"""
Core Service Registry for Dependency Injection
Centralized service and connection management for the monorepo
"""

import logging
from typing import Dict, Any, Optional, Callable
import asyncio
from contextlib import asynccontextmanager

# Import all services for auto-registration
from services.mcp_integration_service import create_mcp_integration_service
from services.service_mesh_coordinator import create_service_mesh_coordinator

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """
    Centralized registry for managing services and connections
    Provides dependency injection and lifecycle management
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._connections: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._initialized = False
    
    def register_connection(self, name: str, connection: Any) -> None:
        """Register a database/cache connection"""
        self._connections[name] = connection
        logger.info(f"Registered connection: {name}")
    
    def register_service(self, name: str, service: Any) -> None:
        """Register a service instance"""
        self._services[name] = service
        logger.info(f"Registered service: {name}")
    
    def register_service_factory(self, name: str, factory: Callable) -> None:
        """Register a factory function for lazy service initialization"""
        self._factories[name] = factory
        logger.info(f"Registered service factory: {name}")
    
    def get_connection(self, name: str) -> Optional[Any]:
        """Get a connection by name"""
        connection = self._connections.get(name)
        if not connection:
            logger.warning(f"Connection '{name}' not found")
        return connection
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a service by name, creating it from factory if needed"""
        # Check if service already exists
        if name in self._services:
            return self._services[name]
        
        # Check if factory exists to create service
        if name in self._factories:
            logger.info(f"Creating service '{name}' from factory")
            service = self._factories[name]()
            self._services[name] = service
            return service
        
        logger.warning(f"Service '{name}' not found")
        return None
    
    def list_services(self) -> list:
        """List all available services"""
        available = list(self._services.keys()) + list(self._factories.keys())
        return sorted(set(available))
    
    def list_connections(self) -> list:
        """List all available connections"""
        return sorted(self._connections.keys())
    
    @property
    def all_services(self) -> Dict[str, Any]:
        """Get all initialized services"""
        return self._services.copy()
    
    @property 
    def all_connections(self) -> Dict[str, Any]:
        """Get all connections"""
        return self._connections.copy()
    
    def is_initialized(self) -> bool:
        """Check if registry is initialized"""
        return self._initialized
    
    def mark_initialized(self) -> None:
        """Mark registry as initialized"""
        self._initialized = True
        logger.info("Service registry marked as initialized")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all services and connections"""
        health_status = {
            "registry": "healthy",
            "services": {},
            "connections": {},
            "summary": {
                "total_services": len(self._services),
                "total_connections": len(self._connections),
                "total_factories": len(self._factories)
            }
        }
        
        # Check services
        for name, service in self._services.items():
            try:
                if hasattr(service, 'health_check'):
                    status = await service.health_check()
                    health_status["services"][name] = status
                else:
                    health_status["services"][name] = "available"
            except Exception as e:
                health_status["services"][name] = f"error: {str(e)}"
                logger.error(f"Health check failed for service {name}: {e}")
        
        # Check connections
        for name, connection in self._connections.items():
            try:
                if name == "redis" and hasattr(connection, 'ping'):
                    await connection.ping()
                    health_status["connections"][name] = "connected"
                elif name == "supabase":
                    # Simple health check for Supabase
                    result = connection.table('users').select('id').limit(1).execute()
                    health_status["connections"][name] = "connected"
                else:
                    health_status["connections"][name] = "available"
            except Exception as e:
                health_status["connections"][name] = f"error: {str(e)}"
                logger.error(f"Health check failed for connection {name}: {e}")
        
        return health_status
    
    async def cleanup(self) -> None:
        """Cleanup all connections and services"""
        logger.info("Starting registry cleanup...")
        
        # Cleanup services with cleanup methods
        for name, service in self._services.items():
            try:
                if hasattr(service, 'cleanup'):
                    await service.cleanup()
                    logger.info(f"Cleaned up service: {name}")
            except Exception as e:
                logger.error(f"Error cleaning up service {name}: {e}")
        
        # Cleanup connections
        for name, connection in self._connections.items():
            try:
                if name == "redis" and hasattr(connection, 'close'):
                    if asyncio.iscoroutinefunction(connection.close):
                        await connection.close()
                    else:
                        connection.close()
                    logger.info(f"Closed connection: {name}")
            except Exception as e:
                logger.error(f"Error closing connection {name}: {e}")
        
        self._services.clear()
        self._connections.clear()
        self._factories.clear()
        self._initialized = False
        logger.info("Registry cleanup completed")
    
    async def initialize_all_services(self):
        """Initialize all services for the monorepo integration"""
        logger.info("🚀 Initializing all services for monorepo integration...")
        
        try:
            # Step 1: Register core services
            self._register_core_services()
            
            # Step 2: Register MCP integration service
            self.register_service_factory("mcp_integration", create_mcp_integration_service)
            
            # Step 3: Register service mesh coordinator (depends on registry)
            def create_coordinator():
                return create_service_mesh_coordinator(self)
            self.register_service_factory("service_mesh_coordinator", create_coordinator)
            
            # Step 4: Initialize all services
            await self._initialize_services_in_order()
            
            # Step 5: Register phase-specific services
            self._register_phase_services()
            
            self.mark_initialized()
            logger.info("✅ All services initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            raise
    
    def _register_core_services(self):
        """Register core services with mock implementations"""
        
        # Mock Agent Persistence Service
        class MockAgentPersistenceService:
            async def createAgent(self, config):
                import uuid
                from datetime import datetime
                return {
                    'id': f"agent_{uuid.uuid4().hex[:8]}",
                    'name': config.get('name', 'Unknown Agent'),
                    'type': config.get('type', 'default'),
                    'status': 'active',
                    'config': config,
                    'createdAt': datetime.utcnow().isoformat()
                }
            
            async def getAllAgents(self):
                return []
            
            async def getAgent(self, agent_id):
                return {'id': agent_id, 'name': 'Mock Agent', 'status': 'active'}
            
            async def getAgentData(self, agent_id):
                return {'agent_id': agent_id, 'data': {}}
            
            async def getAgentTodos(self, agent_id):
                return []
            
            async def updateAgentActivity(self, agent_id, activity):
                return {'success': True}
        
        # Mock Vault Integration Service
        class MockVaultIntegrationService:
            async def createVault(self, config):
                import uuid
                from datetime import datetime
                return {
                    'id': f"vault_{uuid.uuid4().hex[:8]}",
                    'agentId': config.get('agentId'),
                    'name': config.get('name', 'Mock Vault'),
                    'network': config.get('network', 'ethereum'),
                    'address': f"0x{uuid.uuid4().hex[:40]}",
                    'createdAt': datetime.utcnow().isoformat()
                }
            
            async def getAllVaults(self):
                return []
            
            async def getAgentVault(self, agent_id):
                return {'agentId': agent_id, 'vaults': []}
            
            async def getVaultPositions(self, vault_id):
                return []
            
            async def stakeInProtocol(self, vault_id, request):
                return {'success': True, 'vaultId': vault_id}
            
            async def harvestRewards(self, vault_id):
                return {'success': True, 'rewards': 0}
            
            async def getVaultAnalytics(self):
                return {'totalValue': 0, 'totalVaults': 0}
        
        # Mock System Lifecycle Service
        class MockSystemLifecycleService:
            def __init__(self, registry):
                self.registry = registry
            
            async def createCompleteAgent(self, config):
                # Coordinate with other services
                agent_service = self.registry.get_service('agent_persistence')
                agent_data = await agent_service.createAgent(config)
                
                result = {
                    'agent': agent_data,
                    'services_activated': ['agent_persistence'],
                    'success': True
                }
                
                # Add vault if DeFi enabled
                if config.get('enableDeFi', False):
                    vault_service = self.registry.get_service('vault_integration')
                    vault_data = await vault_service.createVault({
                        'agentId': agent_data['id'],
                        'name': f"{config['name']} Vault"
                    })
                    result['vault'] = vault_data
                    result['services_activated'].append('vault_integration')
                
                return result
            
            async def createFarm(self, config):
                import uuid
                return {
                    'id': f"farm_{uuid.uuid4().hex[:8]}",
                    'name': config.get('name', 'Mock Farm'),
                    'agents': [],
                    'status': 'active'
                }
            
            async def recordAgentCreation(self, agent_id, config):
                return {'recorded': True}
            
            async def getSystemHealth(self):
                return {
                    'overall': 'healthy',
                    'services': {
                        'agent_persistence': {'status': 'healthy'},
                        'mcp_integration': {'status': 'healthy'},
                        'vault_integration': {'status': 'healthy'}
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            async def getSystemMetrics(self):
                return {
                    'total_agents': 0,
                    'active_agents': 0,
                    'total_vaults': 0,
                    'uptime': '100%'
                }
        
        # Register services
        self.register_service("agent_persistence", MockAgentPersistenceService())
        self.register_service("vault_integration", MockVaultIntegrationService())
        
        def create_system_lifecycle():
            return MockSystemLifecycleService(self)
        self.register_service_factory("system_lifecycle", create_system_lifecycle)
        
        logger.info("🔧 Core services registered")
    
    async def _initialize_services_in_order(self):
        """Initialize services in dependency order"""
        service_order = [
            "agent_persistence",
            "vault_integration", 
            "mcp_integration",
            "system_lifecycle",
            "service_mesh_coordinator",
            "master_wallet_service",
            "farm_management_service",
            "farm_coordination_service",
            "farm_performance_service",
            "real_time_trading_orchestrator",
            "multi_agent_farm_trading"
        ]
        
        for service_name in service_order:
            try:
                service = self.get_service(service_name)
                if service and hasattr(service, 'initialize'):
                    await service.initialize()
                    logger.info(f"✅ Initialized service: {service_name}")
                else:
                    logger.info(f"✅ Service available: {service_name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {service_name}: {e}")
                # Continue with other services
    
    def _register_phase_services(self):
        """Register additional phase services"""
        try:
            register_agent_trading_services()
        except ImportError:
            logger.info("⚠️ Phase 2 agent trading services not available")
        
        try:
            register_phase5_services()
        except ImportError:
            logger.info("⚠️ Phase 5 services not available")
        
        try:
            register_autonomous_services()
        except ImportError:
            logger.info("⚠️ Autonomous services not available")
        
        try:
            register_real_time_trading_services()
        except ImportError:
            logger.info("⚠️ Real-time trading services not available")
    
    async def cleanup_all_services(self):
        """Cleanup all services"""
        await self.cleanup()
    
    @property
    def services(self) -> Dict[str, Any]:
        """Get all services (for compatibility)"""
        return self._services

# Import and register Phase 2 agent trading services
def register_agent_trading_services():
    """Register Phase 2 agent trading integration services"""
    from services.agent_trading_bridge import create_agent_trading_bridge
    from services.trading_safety_service import create_trading_safety_service
    from services.agent_performance_service import create_agent_performance_service
    from services.agent_coordination_service import create_agent_coordination_service
    
    # Register safety service first (no dependencies)
    registry.register_service_factory("trading_safety_service", create_trading_safety_service)
    
    # Register performance service (no dependencies)
    registry.register_service_factory("agent_performance_service", create_agent_performance_service)
    
    # Register agent trading bridge (requires execution, risk, agent services)
    def create_bridge():
        execution_service = registry.get_service("execution_specialist_service")
        risk_service = registry.get_service("risk_manager_service")
        agent_service = registry.get_service("agent_management_service")
        return create_agent_trading_bridge(execution_service, risk_service, agent_service)
    
    registry.register_service_factory("agent_trading_bridge", create_bridge)
    
    # Register coordination service (requires bridge, safety, performance)
    def create_coordination():
        bridge = registry.get_service("agent_trading_bridge")
        safety = registry.get_service("trading_safety_service")
        performance = registry.get_service("agent_performance_service")
        return create_agent_coordination_service(bridge, safety, performance)
    
    registry.register_service_factory("agent_coordination_service", create_coordination)
    
    logger.info("Registered Phase 2 agent trading services")

# Import and register Phase 5 advanced services
def register_phase5_services():
    """Register Phase 5 advanced agent operations and analytics services"""
    from services.agent_scheduler_service import create_agent_scheduler_service
    from services.market_regime_service import create_market_regime_service
    from services.adaptive_risk_service import create_adaptive_risk_service
    from services.portfolio_optimizer_service import create_portfolio_optimizer_service
    from services.alerting_service import create_alerting_service
    
    # Register standalone services
    registry.register_service_factory("agent_scheduler_service", create_agent_scheduler_service)
    registry.register_service_factory("market_regime_service", create_market_regime_service)
    registry.register_service_factory("adaptive_risk_service", create_adaptive_risk_service)
    registry.register_service_factory("portfolio_optimizer_service", create_portfolio_optimizer_service)
    registry.register_service_factory("alerting_service", create_alerting_service)
    
    logger.info("Registered Phase 5 advanced services")

# Import and register Phase 6-8 autonomous services
def register_autonomous_services():
    """Register Phase 6-8 autonomous services (Master Wallet, Farms, Goals)"""
    try:
        from services.master_wallet_service import create_master_wallet_service
        registry.register_service_factory("master_wallet_service", create_master_wallet_service)
        logger.info("Registered Phase 6: Master Wallet Service")
    except ImportError:
        logger.info("⚠️ Phase 6 Master Wallet Service not available")
    
    try:
        from services.farm_management_service import create_farm_management_service
        from services.farm_coordination_service import create_farm_coordination_service  
        from services.farm_performance_service import create_farm_performance_service
        
        registry.register_service_factory("farm_management_service", create_farm_management_service)
        registry.register_service_factory("farm_coordination_service", create_farm_coordination_service)
        registry.register_service_factory("farm_performance_service", create_farm_performance_service)
        logger.info("Registered Phase 7: Farm Management Services")
    except ImportError:
        logger.info("⚠️ Phase 7 Farm Services not available")
    
    try:
        from services.goal_management_service import create_goal_management_service
        registry.register_service_factory("goal_management_service", create_goal_management_service)
        logger.info("Registered Phase 8: Goal Management Service")
    except ImportError:
        logger.info("⚠️ Phase 8 Goal Management Service not available")
    
    logger.info("Registered Phase 6-8 autonomous services")

# Import and register real-time trading services
def register_real_time_trading_services():
    """Register real-time trading orchestration services"""
    try:
        from services.real_time_trading_orchestrator import create_real_time_trading_orchestrator
        
        def create_orchestrator():
            # Get required services
            exchange_service = registry.get_service("multi_exchange_integration")
            risk_service = registry.get_service("advanced_risk_management")
            agent_coordinator = registry.get_service("autonomous_agent_coordinator")
            trading_orchestrator = registry.get_service("advanced_trading_orchestrator")
            
            return create_real_time_trading_orchestrator(
                exchange_service,
                risk_service,
                agent_coordinator,
                trading_orchestrator
            )
        
        registry.register_service_factory("real_time_trading_orchestrator", create_orchestrator)
        logger.info("Registered Real-Time Trading Orchestrator")
    except ImportError:
        logger.info("⚠️ Real-time trading orchestrator not available")
    
    # Register Multi-Agent Farm Trading Coordinator
    try:
        from services.multi_agent_farm_trading_coordinator import create_multi_agent_farm_trading_coordinator
        
        def create_farm_trading_coordinator():
            # Get required services
            farm_coordination = registry.get_service("farm_coordination_service")
            trading_orchestrator = registry.get_service("real_time_trading_orchestrator")
            farm_performance = registry.get_service("farm_performance_service")
            master_wallet = registry.get_service("master_wallet_service")
            
            return create_multi_agent_farm_trading_coordinator(
                farm_coordination,
                trading_orchestrator,
                farm_performance,
                master_wallet
            )
        
        registry.register_service_factory("multi_agent_farm_trading", create_farm_trading_coordinator)
        logger.info("Registered Multi-Agent Farm Trading Coordinator")
    except ImportError:
        logger.info("⚠️ Multi-agent farm trading coordinator not available")

# Global registry instance
registry = ServiceRegistry()

def get_registry() -> ServiceRegistry:
    """Get the global service registry"""
    return registry

# Dependency injection helpers for FastAPI
def get_service_dependency(service_name: str):
    """Create a FastAPI dependency for a service"""
    def dependency():
        service = registry.get_service(service_name)
        if not service:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503, 
                detail=f"Service '{service_name}' is not available"
            )
        return service
    
    dependency.__name__ = f"get_{service_name}_service"
    return dependency

def get_connection_dependency(connection_name: str):
    """Create a FastAPI dependency for a connection"""
    def dependency():
        connection = registry.get_connection(connection_name)
        if not connection:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503, 
                detail=f"Connection '{connection_name}' is not available"
            )
        return connection
    
    dependency.__name__ = f"get_{connection_name}_connection"
    return dependency

# Context manager for service lifecycle
@asynccontextmanager
async def service_lifecycle():
    """Context manager for service lifecycle management"""
    try:
        logger.info("Starting service lifecycle")
        yield registry
    finally:
        logger.info("Ending service lifecycle")
        await registry.cleanup()