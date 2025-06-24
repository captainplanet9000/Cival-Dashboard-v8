"""
Service Mesh Coordinator
Orchestrates all backend services and manages inter-service communication
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from core.service_registry import ServiceRegistry
from services.mcp_integration_service import MCPIntegrationService
from models.mcp_models import MCPExecutionStatus

logger = logging.getLogger(__name__)

class ServiceStatus(str, Enum):
    """Service status enumeration"""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"

class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ServiceHealth:
    """Service health information"""
    service_name: str
    status: ServiceStatus
    response_time: float
    last_check: datetime
    error_count: int
    uptime_percentage: float
    details: Optional[str] = None

@dataclass
class CoordinationTask:
    """Inter-service coordination task"""
    id: str
    name: str
    priority: TaskPriority
    services_involved: List[str]
    dependencies: List[str]
    payload: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None

class ServiceMeshCoordinator:
    """
    Advanced Service Mesh Coordinator
    Manages service dependencies, health monitoring, and task coordination
    """
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.service_health: Dict[str, ServiceHealth] = {}
        self.coordination_tasks: Dict[str, CoordinationTask] = {}
        self.task_queue: List[CoordinationTask] = []
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.metrics = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'active_tasks': 0,
            'avg_completion_time': 0.0,
            'service_availability': 0.0
        }
        
        # Health check configuration
        self.health_check_interval = 30  # seconds
        self.health_check_timeout = 5    # seconds
        self.max_error_count = 5
        
        # Task processing configuration
        self.max_concurrent_tasks = 10
        self.task_timeout = 300  # 5 minutes
        
        logger.info("🕸️ Service Mesh Coordinator initialized")
    
    async def initialize(self):
        """Initialize the service mesh coordinator"""
        # Start health monitoring
        asyncio.create_task(self._health_monitoring_loop())
        
        # Start task processor
        asyncio.create_task(self._task_processing_loop())
        
        # Initialize service health tracking
        await self._initialize_service_health()
        
        logger.info("✅ Service Mesh Coordinator ready")
    
    async def coordinate_agent_creation(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate complete agent creation across all services"""
        task = CoordinationTask(
            id=f"agent_create_{uuid.uuid4().hex[:8]}",
            name="Create Complete Agent",
            priority=TaskPriority.HIGH,
            services_involved=['agent_persistence', 'mcp_integration', 'vault_integration', 'system_lifecycle'],
            dependencies=[],
            payload=agent_config,
            created_at=datetime.utcnow()
        )
        
        return await self._execute_coordination_task(task, self._handle_agent_creation)
    
    async def coordinate_farm_creation(self, farm_config: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate complete farm creation with multiple agents"""
        task = CoordinationTask(
            id=f"farm_create_{uuid.uuid4().hex[:8]}",
            name="Create Complete Farm",
            priority=TaskPriority.HIGH,
            services_involved=['agent_persistence', 'mcp_integration', 'vault_integration', 'system_lifecycle'],
            dependencies=[],
            payload=farm_config,
            created_at=datetime.utcnow()
        )
        
        return await self._execute_coordination_task(task, self._handle_farm_creation)
    
    async def coordinate_mcp_execution(self, agent_id: str, tool_id: str, parameters: Dict[str, Any]) -> Any:
        """Coordinate MCP tool execution with proper service interaction"""
        task = CoordinationTask(
            id=f"mcp_exec_{uuid.uuid4().hex[:8]}",
            name=f"Execute MCP Tool: {tool_id}",
            priority=TaskPriority.NORMAL,
            services_involved=['mcp_integration', 'agent_persistence'],
            dependencies=[],
            payload={'agent_id': agent_id, 'tool_id': tool_id, 'parameters': parameters},
            created_at=datetime.utcnow()
        )
        
        return await self._execute_coordination_task(task, self._handle_mcp_execution)
    
    async def coordinate_vault_operations(self, vault_config: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate vault operations across DeFi networks"""
        task = CoordinationTask(
            id=f"vault_ops_{uuid.uuid4().hex[:8]}",
            name="Coordinate Vault Operations",
            priority=TaskPriority.NORMAL,
            services_involved=['vault_integration', 'agent_persistence'],
            dependencies=[],
            payload=vault_config,
            created_at=datetime.utcnow()
        )
        
        return await self._execute_coordination_task(task, self._handle_vault_operations)
    
    async def coordinate_system_health_check(self) -> Dict[str, Any]:
        """Coordinate comprehensive system health check"""
        task = CoordinationTask(
            id=f"health_check_{uuid.uuid4().hex[:8]}",
            name="System Health Check",
            priority=TaskPriority.LOW,
            services_involved=list(self.service_registry.services.keys()),
            dependencies=[],
            payload={},
            created_at=datetime.utcnow()
        )
        
        return await self._execute_coordination_task(task, self._handle_system_health_check)
    
    async def _execute_coordination_task(self, task: CoordinationTask, handler: Callable) -> Any:
        """Execute coordination task with proper error handling"""
        try:
            task.started_at = datetime.utcnow()
            task.status = "running"
            
            # Check service dependencies
            await self._verify_service_dependencies(task.services_involved)
            
            # Execute task handler
            result = await asyncio.wait_for(handler(task), timeout=self.task_timeout)
            
            task.completed_at = datetime.utcnow()
            task.status = "completed"
            task.result = result
            
            # Update metrics
            self.metrics['completed_tasks'] += 1
            self._update_completion_time_metric(task)
            
            # Emit completion event
            await self._emit_event('task_completed', {
                'task_id': task.id,
                'result': result,
                'duration': (task.completed_at - task.started_at).total_seconds()
            })
            
            return result
            
        except asyncio.TimeoutError:
            task.status = "timeout"
            task.error = "Task execution timed out"
            self.metrics['failed_tasks'] += 1
            logger.error(f"⏰ Task {task.id} timed out")
            raise
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self.metrics['failed_tasks'] += 1
            logger.error(f"❌ Task {task.id} failed: {e}")
            raise
            
        finally:
            # Store task for audit
            self.coordination_tasks[task.id] = task
    
    async def _handle_agent_creation(self, task: CoordinationTask) -> Dict[str, Any]:
        """Handle agent creation coordination"""
        config = task.payload
        logger.info(f"🤖 Coordinating agent creation: {config.get('name', 'Unknown')}")
        
        # Step 1: Create agent persistence
        agent_service = self.service_registry.get_service('agent_persistence')
        agent_data = await agent_service.createAgent(config)
        agent_id = agent_data['id']
        
        # Step 2: Initialize MCP tools if enabled
        if config.get('enableMCP', False):
            mcp_service = self.service_registry.get_service('mcp_integration')
            await mcp_service.call_tool(
                agent_id, 
                'supabase_query', 
                {'query': f'INSERT INTO agent_mcp_tools (agent_id, enabled) VALUES (\'{agent_id}\', true)'}
            )
        
        # Step 3: Create vault if DeFi enabled
        vault_data = None
        if config.get('enableDeFi', False):
            vault_service = self.service_registry.get_service('vault_integration')
            vault_config = {
                'agentId': agent_id,
                'name': f"{config['name']} Vault",
                'network': config.get('network', 'ethereum'),
                'initialCapital': config.get('initialCapital', 10000)
            }
            vault_data = await vault_service.createVault(vault_config)
        
        # Step 4: Update system lifecycle
        system_service = self.service_registry.get_service('system_lifecycle')
        await system_service.recordAgentCreation(agent_id, config)
        
        return {
            'agent': agent_data,
            'vault': vault_data,
            'mcp_enabled': config.get('enableMCP', False),
            'defi_enabled': config.get('enableDeFi', False),
            'created_at': datetime.utcnow().isoformat()
        }
    
    async def _handle_farm_creation(self, task: CoordinationTask) -> Dict[str, Any]:
        """Handle farm creation coordination"""
        config = task.payload
        logger.info(f"🏭 Coordinating farm creation: {config.get('name', 'Unknown')}")
        
        farm_id = f"farm_{uuid.uuid4().hex[:8]}"
        agent_count = config.get('agentCount', 3)
        agents = []
        
        # Create multiple agents for the farm
        for i in range(agent_count):
            agent_config = {
                'name': f"{config['name']} Agent {i+1}",
                'type': config.get('farmType', 'multi_strategy'),
                'farmId': farm_id,
                'initialCapital': config.get('initialCapital', 10000) / agent_count,
                'strategy': config.get('strategy', 'balanced'),
                'enableDeFi': config.get('enableDeFi', True),
                'enableMCP': config.get('enableMCP', True)
            }
            
            # Create agent through coordination
            agent_task = CoordinationTask(
                id=f"farm_agent_{i}_{uuid.uuid4().hex[:8]}",
                name=f"Create Farm Agent {i+1}",
                priority=TaskPriority.HIGH,
                services_involved=['agent_persistence', 'mcp_integration', 'vault_integration'],
                dependencies=[],
                payload=agent_config,
                created_at=datetime.utcnow()
            )
            
            agent_result = await self._handle_agent_creation(agent_task)
            agents.append(agent_result)
        
        # Create farm record
        farm_data = {
            'id': farm_id,
            'name': config['name'],
            'description': config.get('description', ''),
            'strategy': config.get('strategy', 'balanced'),
            'farmType': config.get('farmType', 'multi_strategy'),
            'agents': agents,
            'status': 'active',
            'createdAt': datetime.utcnow().isoformat(),
            'totalValue': config.get('initialCapital', 10000),
            'agentCount': len(agents)
        }
        
        return farm_data
    
    async def _handle_mcp_execution(self, task: CoordinationTask) -> Any:
        """Handle MCP tool execution coordination"""
        payload = task.payload
        agent_id = payload['agent_id']
        tool_id = payload['tool_id']
        parameters = payload['parameters']
        
        logger.info(f"🔧 Coordinating MCP execution: {tool_id} for agent {agent_id}")
        
        # Get MCP service
        mcp_service = self.service_registry.get_service('mcp_integration')
        
        # Execute tool
        result = await mcp_service.call_tool(agent_id, tool_id, parameters)
        
        # Update agent activity
        agent_service = self.service_registry.get_service('agent_persistence')
        await agent_service.updateAgentActivity(agent_id, {
            'last_mcp_execution': datetime.utcnow().isoformat(),
            'mcp_tool_used': tool_id,
            'mcp_result_summary': str(result)[:100]
        })
        
        return result
    
    async def _handle_vault_operations(self, task: CoordinationTask) -> Dict[str, Any]:
        """Handle vault operations coordination"""
        config = task.payload
        logger.info(f"🏦 Coordinating vault operations")
        
        vault_service = self.service_registry.get_service('vault_integration')
        
        # Execute vault operation based on type
        operation_type = config.get('operation', 'create')
        
        if operation_type == 'create':
            return await vault_service.createVault(config)
        elif operation_type == 'stake':
            return await vault_service.stakeInProtocol(config['vaultId'], config)
        elif operation_type == 'harvest':
            return await vault_service.harvestRewards(config['vaultId'])
        else:
            raise ValueError(f"Unknown vault operation: {operation_type}")
    
    async def _handle_system_health_check(self, task: CoordinationTask) -> Dict[str, Any]:
        """Handle comprehensive system health check"""
        logger.info("🔍 Performing comprehensive system health check")
        
        health_results = {}
        
        # Check each service
        for service_name in task.services_involved:
            try:
                service = self.service_registry.get_service(service_name)
                
                # Basic service availability check
                start_time = time.time()
                
                # Service-specific health checks
                if hasattr(service, 'get_health'):
                    health_info = await service.get_health()
                else:
                    health_info = {'status': 'available', 'details': 'Basic health check passed'}
                
                response_time = (time.time() - start_time) * 1000  # ms
                
                health_results[service_name] = {
                    'status': 'healthy',
                    'response_time': response_time,
                    'details': health_info,
                    'checked_at': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                health_results[service_name] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'checked_at': datetime.utcnow().isoformat()
                }
        
        # Calculate overall health score
        healthy_services = sum(1 for result in health_results.values() if result['status'] == 'healthy')
        health_score = (healthy_services / len(health_results)) * 100
        
        return {
            'overall_health': 'healthy' if health_score >= 80 else 'degraded' if health_score >= 60 else 'unhealthy',
            'health_score': health_score,
            'services': health_results,
            'checked_at': datetime.utcnow().isoformat(),
            'metrics': self.metrics
        }
    
    async def _verify_service_dependencies(self, required_services: List[str]):
        """Verify that required services are available"""
        for service_name in required_services:
            if service_name not in self.service_registry.services:
                raise Exception(f"Required service '{service_name}' not available")
            
            health = self.service_health.get(service_name)
            if health and health.status in [ServiceStatus.FAILED, ServiceStatus.UNHEALTHY]:
                raise Exception(f"Required service '{service_name}' is unhealthy")
    
    async def _health_monitoring_loop(self):
        """Continuous health monitoring loop"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"❌ Health monitoring error: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all services"""
        for service_name, service in self.service_registry.services.items():
            try:
                start_time = time.time()
                
                # Perform health check (timeout after configured seconds)
                health_check = asyncio.create_task(self._check_service_health(service))
                await asyncio.wait_for(health_check, timeout=self.health_check_timeout)
                
                response_time = (time.time() - start_time) * 1000  # ms
                
                # Update health status
                if service_name not in self.service_health:
                    self.service_health[service_name] = ServiceHealth(
                        service_name=service_name,
                        status=ServiceStatus.HEALTHY,
                        response_time=response_time,
                        last_check=datetime.utcnow(),
                        error_count=0,
                        uptime_percentage=100.0
                    )
                else:
                    health = self.service_health[service_name]
                    health.status = ServiceStatus.HEALTHY
                    health.response_time = response_time
                    health.last_check = datetime.utcnow()
                    health.error_count = 0  # Reset error count on success
                
            except asyncio.TimeoutError:
                self._update_service_health_error(service_name, "Health check timeout")
            except Exception as e:
                self._update_service_health_error(service_name, str(e))
    
    async def _check_service_health(self, service):
        """Check individual service health"""
        if hasattr(service, 'health_check'):
            await service.health_check()
        elif hasattr(service, 'get_health'):
            await service.get_health()
        # If no health check method, assume healthy if service exists
    
    def _update_service_health_error(self, service_name: str, error: str):
        """Update service health on error"""
        if service_name not in self.service_health:
            self.service_health[service_name] = ServiceHealth(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time=0,
                last_check=datetime.utcnow(),
                error_count=1,
                uptime_percentage=0.0,
                details=error
            )
        else:
            health = self.service_health[service_name]
            health.error_count += 1
            health.last_check = datetime.utcnow()
            health.details = error
            
            # Update status based on error count
            if health.error_count >= self.max_error_count:
                health.status = ServiceStatus.FAILED
            elif health.error_count >= 3:
                health.status = ServiceStatus.UNHEALTHY
            else:
                health.status = ServiceStatus.DEGRADED
    
    async def _task_processing_loop(self):
        """Task processing loop"""
        while True:
            try:
                # Process pending tasks
                while len(self.running_tasks) < self.max_concurrent_tasks and self.task_queue:
                    task = self.task_queue.pop(0)
                    asyncio_task = asyncio.create_task(self._execute_coordination_task(task, self._get_task_handler(task)))
                    self.running_tasks[task.id] = asyncio_task
                
                # Clean up completed tasks
                completed_task_ids = []
                for task_id, asyncio_task in self.running_tasks.items():
                    if asyncio_task.done():
                        completed_task_ids.append(task_id)
                
                for task_id in completed_task_ids:
                    del self.running_tasks[task_id]
                
                await asyncio.sleep(1)  # Process tasks every second
                
            except Exception as e:
                logger.error(f"❌ Task processing error: {e}")
                await asyncio.sleep(5)
    
    def _get_task_handler(self, task: CoordinationTask) -> Callable:
        """Get appropriate handler for task"""
        if 'agent_create' in task.name.lower():
            return self._handle_agent_creation
        elif 'farm_create' in task.name.lower():
            return self._handle_farm_creation
        elif 'mcp' in task.name.lower():
            return self._handle_mcp_execution
        elif 'vault' in task.name.lower():
            return self._handle_vault_operations
        elif 'health' in task.name.lower():
            return self._handle_system_health_check
        else:
            raise ValueError(f"No handler found for task: {task.name}")
    
    async def _initialize_service_health(self):
        """Initialize service health tracking"""
        for service_name in self.service_registry.services.keys():
            self.service_health[service_name] = ServiceHealth(
                service_name=service_name,
                status=ServiceStatus.INITIALIZING,
                response_time=0,
                last_check=datetime.utcnow(),
                error_count=0,
                uptime_percentage=100.0
            )
    
    def _update_completion_time_metric(self, task: CoordinationTask):
        """Update average completion time metric"""
        if task.completed_at and task.started_at:
            duration = (task.completed_at - task.started_at).total_seconds()
            current_avg = self.metrics['avg_completion_time']
            total_tasks = self.metrics['completed_tasks']
            
            # Calculate new average
            self.metrics['avg_completion_time'] = ((current_avg * (total_tasks - 1)) + duration) / total_tasks
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit coordination event"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"❌ Event handler error for {event_type}: {e}")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def get_service_health(self) -> Dict[str, ServiceHealth]:
        """Get current service health status"""
        return {name: health for name, health in self.service_health.items()}
    
    def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get coordination metrics"""
        self.metrics['active_tasks'] = len(self.running_tasks)
        self.metrics['service_availability'] = self._calculate_service_availability()
        return self.metrics.copy()
    
    def _calculate_service_availability(self) -> float:
        """Calculate overall service availability percentage"""
        if not self.service_health:
            return 0.0
        
        healthy_services = sum(
            1 for health in self.service_health.values() 
            if health.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
        )
        
        return (healthy_services / len(self.service_health)) * 100

# Service factory
def create_service_mesh_coordinator(service_registry: ServiceRegistry) -> ServiceMeshCoordinator:
    """Create and configure service mesh coordinator"""
    return ServiceMeshCoordinator(service_registry)