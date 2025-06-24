"""
MCP Integration Service
Handles Model Context Protocol tool execution and management
"""

import asyncio
import logging
import uuid
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path

from models.mcp_models import (
    MCPTool, MCPToolUsage, MCPExecutionRequest, MCPExecutionResult,
    MCPExecutionStatus, MCPAuditLog, MCPToolRegistry, MCPMetrics,
    create_default_tool_registry, DEFAULT_MCP_TOOLS
)

logger = logging.getLogger(__name__)

class MCPIntegrationService:
    """
    Comprehensive MCP Integration Service
    Manages MCP tool registration, execution, and monitoring
    """
    
    def __init__(self):
        self.tool_registry: MCPToolRegistry = create_default_tool_registry()
        self.active_executions: Dict[str, MCPExecutionResult] = {}
        self.execution_history: List[MCPAuditLog] = []
        self.metrics = MCPMetrics()
        self.tool_usage: Dict[str, MCPToolUsage] = {}
        
        # Initialize tool usage tracking
        for tool_id in self.tool_registry.tools.keys():
            self.tool_usage[tool_id] = MCPToolUsage(tool_id=tool_id)
        
        # MCP server connections (would be actual MCP clients in production)
        self.mcp_servers = {
            'railway': self._create_mock_railway_client(),
            'supabase': self._create_mock_supabase_client(),
            'n8n': self._create_mock_n8n_client(),
            'browser': self._create_mock_browser_client(),
            'ib': self._create_mock_ib_client()
        }
        
        logger.info(f"🔧 MCP Integration Service initialized with {len(self.tool_registry.tools)} tools")
    
    async def initialize(self):
        """Initialize the MCP service"""
        # Update metrics
        await self._update_metrics()
        
        # Test tool connections
        await self._test_tool_connections()
        
        logger.info("✅ MCP Integration Service ready")
    
    async def get_available_tools(self, agent_id: Optional[str] = None) -> List[MCPTool]:
        """Get all available MCP tools, optionally filtered by agent permissions"""
        tools = []
        
        for tool in self.tool_registry.tools.values():
            if tool.enabled and tool.status.value == "available":
                # TODO: Add agent permission checking
                tools.append(tool)
        
        return tools
    
    async def get_tool_categories(self) -> Dict[str, List[str]]:
        """Get MCP tools organized by category"""
        return {
            category.value: tool_ids 
            for category, tool_ids in self.tool_registry.categories.items()
        }
    
    async def call_tool(self, agent_id: str, tool_id: str, parameters: Dict[str, Any]) -> Any:
        """Execute MCP tool with given parameters"""
        if tool_id not in self.tool_registry.tools:
            raise ValueError(f"Tool {tool_id} not found")
        
        tool = self.tool_registry.tools[tool_id]
        if not tool.enabled:
            raise ValueError(f"Tool {tool_id} is disabled")
        
        # Create execution request
        request = MCPExecutionRequest(
            tool_id=tool_id,
            parameters=parameters,
            agent_id=agent_id
        )
        
        # Execute tool
        result = await self._execute_tool(request)
        
        # Update usage statistics
        await self._update_tool_usage(tool_id, result.status)
        
        # Log execution
        await self._log_execution(request, result)
        
        if result.status == MCPExecutionStatus.SUCCESS:
            return result.result
        else:
            raise Exception(f"Tool execution failed: {result.error}")
    
    async def execute_tool(self, tool_id: str, parameters: Dict[str, Any], agent_id: Optional[str] = None) -> Any:
        """Execute MCP tool (alias for call_tool)"""
        return await self.call_tool(agent_id or "system", tool_id, parameters)
    
    async def _execute_tool(self, request: MCPExecutionRequest) -> MCPExecutionResult:
        """Internal tool execution method"""
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Create execution result
        result = MCPExecutionResult(
            execution_id=execution_id,
            tool_id=request.tool_id,
            status=MCPExecutionStatus.RUNNING,
            start_time=start_time,
            agent_id=request.agent_id
        )
        
        # Store active execution
        self.active_executions[execution_id] = result
        
        try:
            # Route to appropriate executor
            if request.tool_id.startswith('railway_'):
                result.result = await self._execute_railway_tool(request)
            elif request.tool_id.startswith('supabase_'):
                result.result = await self._execute_supabase_tool(request)
            elif request.tool_id.startswith('n8n_'):
                result.result = await self._execute_n8n_tool(request)
            elif request.tool_id.startswith('browser_'):
                result.result = await self._execute_browser_tool(request)
            elif request.tool_id.startswith('ib_'):
                result.result = await self._execute_ib_tool(request)
            else:
                raise ValueError(f"Unknown tool type: {request.tool_id}")
            
            result.status = MCPExecutionStatus.SUCCESS
            
        except asyncio.TimeoutError:
            result.status = MCPExecutionStatus.TIMEOUT
            result.error = "Tool execution timed out"
            
        except Exception as e:
            result.status = MCPExecutionStatus.FAILED
            result.error = str(e)
            logger.error(f"❌ Tool execution failed for {request.tool_id}: {e}")
        
        finally:
            # Update execution result
            result.end_time = datetime.utcnow()
            result.duration = (result.end_time - result.start_time).total_seconds()
            
            # Remove from active executions
            self.active_executions.pop(execution_id, None)
        
        return result
    
    async def _execute_railway_tool(self, request: MCPExecutionRequest) -> Any:
        """Execute Railway MCP tools"""
        tool_id = request.tool_id
        params = request.parameters
        
        if tool_id == 'railway_deploy':
            # Simulate Railway deployment
            service_name = params.get('service_name')
            environment = params.get('environment', 'production')
            
            # Mock deployment process
            await asyncio.sleep(2)  # Simulate deployment time
            
            return {
                'deployment_id': f"dep_{uuid.uuid4().hex[:8]}",
                'service_name': service_name,
                'environment': environment,
                'status': 'deployed',
                'url': f"https://{service_name}-{environment}.railway.app",
                'deployed_at': datetime.utcnow().isoformat()
            }
            
        elif tool_id == 'railway_logs':
            # Simulate log fetching
            service_id = params.get('service_id')
            lines = params.get('lines', 100)
            
            await asyncio.sleep(1)
            
            return {
                'service_id': service_id,
                'logs': [
                    f"[{datetime.utcnow().isoformat()}] INFO: Service started",
                    f"[{datetime.utcnow().isoformat()}] INFO: Database connected",
                    f"[{datetime.utcnow().isoformat()}] INFO: API server listening on port 8000"
                ][:lines]
            }
        
        raise ValueError(f"Unknown Railway tool: {tool_id}")
    
    async def _execute_supabase_tool(self, request: MCPExecutionRequest) -> Any:
        """Execute Supabase MCP tools"""
        tool_id = request.tool_id
        params = request.parameters
        
        if tool_id == 'supabase_query':
            # Simulate database query
            query = params.get('query')
            query_params = params.get('params', {})
            
            await asyncio.sleep(0.5)
            
            # Mock query results based on query type
            if 'SELECT' in query.upper():
                return {
                    'data': [
                        {'id': 1, 'name': 'Agent 1', 'status': 'active'},
                        {'id': 2, 'name': 'Agent 2', 'status': 'paused'}
                    ],
                    'count': 2
                }
            else:
                return {
                    'success': True,
                    'affected_rows': 1
                }
                
        elif tool_id == 'supabase_realtime':
            # Simulate realtime subscription
            table = params.get('table')
            event = params.get('event', '*')
            
            return {
                'subscription_id': f"sub_{uuid.uuid4().hex[:8]}",
                'table': table,
                'event': event,
                'status': 'subscribed'
            }
        
        raise ValueError(f"Unknown Supabase tool: {tool_id}")
    
    async def _execute_n8n_tool(self, request: MCPExecutionRequest) -> Any:
        """Execute N8N automation tools"""
        tool_id = request.tool_id
        params = request.parameters
        
        if tool_id == 'n8n_workflow_execute':
            # Simulate workflow execution
            workflow_id = params.get('workflow_id')
            input_data = params.get('input_data', {})
            
            await asyncio.sleep(3)  # Simulate workflow execution time
            
            return {
                'execution_id': f"exec_{uuid.uuid4().hex[:8]}",
                'workflow_id': workflow_id,
                'status': 'success',
                'output': {
                    'processed_signals': 5,
                    'orders_placed': 2,
                    'profit_generated': 124.56
                },
                'executed_at': datetime.utcnow().isoformat()
            }
            
        elif tool_id == 'n8n_workflow_status':
            # Simulate status check
            execution_id = params.get('execution_id')
            
            return {
                'execution_id': execution_id,
                'status': 'completed',
                'progress': 100,
                'start_time': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                'end_time': datetime.utcnow().isoformat()
            }
        
        raise ValueError(f"Unknown N8N tool: {tool_id}")
    
    async def _execute_browser_tool(self, request: MCPExecutionRequest) -> Any:
        """Execute Browser automation tools"""
        tool_id = request.tool_id
        params = request.parameters
        
        if tool_id == 'browser_scrape':
            # Simulate web scraping
            url = params.get('url')
            selector = params.get('selector')
            
            await asyncio.sleep(2)
            
            return {
                'url': url,
                'data': {
                    'title': 'Market Analysis Dashboard',
                    'price': '$65,432.10',
                    'change': '+2.4%',
                    'volume': '1.2M',
                    'scraped_at': datetime.utcnow().isoformat()
                },
                'selector': selector,
                'success': True
            }
            
        elif tool_id == 'browser_screenshot':
            # Simulate screenshot
            url = params.get('url')
            viewport = params.get('viewport', {'width': 1920, 'height': 1080})
            
            await asyncio.sleep(1)
            
            return {
                'url': url,
                'screenshot_path': f"/tmp/screenshot_{uuid.uuid4().hex[:8]}.png",
                'viewport': viewport,
                'file_size': 245760,
                'captured_at': datetime.utcnow().isoformat()
            }
        
        raise ValueError(f"Unknown Browser tool: {tool_id}")
    
    async def _execute_ib_tool(self, request: MCPExecutionRequest) -> Any:
        """Execute Interactive Brokers tools"""
        tool_id = request.tool_id
        params = request.parameters
        
        if tool_id == 'ib_market_data':
            # Simulate market data request
            symbol = params.get('symbol')
            data_type = params.get('data_type', 'snapshot')
            
            await asyncio.sleep(0.3)
            
            return {
                'symbol': symbol,
                'price': 65432.10,
                'bid': 65431.50,
                'ask': 65432.50,
                'volume': 1234567,
                'change': 2.4,
                'change_percent': 0.037,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        elif tool_id == 'ib_place_order':
            # Simulate order placement
            symbol = params.get('symbol')
            action = params.get('action')
            quantity = params.get('quantity')
            order_type = params.get('order_type', 'MKT')
            
            await asyncio.sleep(0.5)
            
            return {
                'order_id': f"ord_{uuid.uuid4().hex[:8]}",
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'order_type': order_type,
                'status': 'filled',
                'fill_price': 65432.10,
                'commission': 1.00,
                'placed_at': datetime.utcnow().isoformat()
            }
        
        raise ValueError(f"Unknown IB tool: {tool_id}")
    
    async def _update_tool_usage(self, tool_id: str, status: MCPExecutionStatus):
        """Update tool usage statistics"""
        if tool_id not in self.tool_usage:
            self.tool_usage[tool_id] = MCPToolUsage(tool_id=tool_id)
        
        usage = self.tool_usage[tool_id]
        usage.total_calls += 1
        usage.last_used = datetime.utcnow()
        
        if status == MCPExecutionStatus.SUCCESS:
            usage.successful_calls += 1
        else:
            usage.failed_calls += 1
    
    async def _log_execution(self, request: MCPExecutionRequest, result: MCPExecutionResult):
        """Log tool execution for audit"""
        audit_log = MCPAuditLog(
            id=str(uuid.uuid4()),
            execution_id=result.execution_id,
            tool_id=request.tool_id,
            agent_id=request.agent_id,
            action=f"execute_{request.tool_id}",
            parameters=request.parameters,
            result_summary=str(result.result)[:200] if result.result else None,
            status=result.status,
            duration=result.duration
        )
        
        self.execution_history.append(audit_log)
        
        # Keep only last 1000 executions
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    async def get_audit_log(self, limit: int = 100, offset: int = 0) -> List[MCPAuditLog]:
        """Get execution audit log"""
        return self.execution_history[offset:offset + limit]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get MCP execution statistics"""
        await self._update_metrics()
        
        return {
            'metrics': self.metrics.dict(),
            'tool_usage': {tool_id: usage.dict() for tool_id, usage in self.tool_usage.items()},
            'active_executions': len(self.active_executions),
            'tool_registry': {
                'total_tools': self.tool_registry.total_tools,
                'enabled_tools': self.tool_registry.enabled_tools,
                'categories': {cat.value: len(tools) for cat, tools in self.tool_registry.categories.items()}
            }
        }
    
    async def _update_metrics(self):
        """Update system metrics"""
        total_executions = sum(usage.total_calls for usage in self.tool_usage.values())
        successful_executions = sum(usage.successful_calls for usage in self.tool_usage.values())
        failed_executions = sum(usage.failed_calls for usage in self.tool_usage.values())
        
        self.metrics.total_executions = total_executions
        self.metrics.successful_executions = successful_executions
        self.metrics.failed_executions = failed_executions
        self.metrics.tools_available = len([t for t in self.tool_registry.tools.values() if t.status.value == "available"])
        self.metrics.tools_enabled = len([t for t in self.tool_registry.tools.values() if t.enabled])
        self.metrics.active_executions = len(self.active_executions)
        
        if total_executions > 0:
            self.metrics.success_rate = (successful_executions / total_executions) * 100
            self.metrics.error_rate = (failed_executions / total_executions) * 100
    
    async def _test_tool_connections(self):
        """Test MCP tool connections"""
        for server_name, client in self.mcp_servers.items():
            try:
                # Test connection (in real implementation, this would ping the MCP server)
                await asyncio.sleep(0.1)  # Simulate connection test
                logger.info(f"✅ {server_name} MCP server connection OK")
            except Exception as e:
                logger.error(f"❌ {server_name} MCP server connection failed: {e}")
    
    def _create_mock_railway_client(self):
        """Create mock Railway MCP client"""
        return {"type": "railway", "status": "connected"}
    
    def _create_mock_supabase_client(self):
        """Create mock Supabase MCP client"""
        return {"type": "supabase", "status": "connected"}
    
    def _create_mock_n8n_client(self):
        """Create mock N8N MCP client"""
        return {"type": "n8n", "status": "connected"}
    
    def _create_mock_browser_client(self):
        """Create mock Browser MCP client"""
        return {"type": "browser", "status": "connected"}
    
    def _create_mock_ib_client(self):
        """Create mock Interactive Brokers MCP client"""
        return {"type": "ib", "status": "connected"}

# Service factory
def create_mcp_integration_service() -> MCPIntegrationService:
    """Create and configure MCP integration service"""
    return MCPIntegrationService()