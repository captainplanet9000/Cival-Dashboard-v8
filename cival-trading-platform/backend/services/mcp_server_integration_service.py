"""
MCP Server Integration Service - Phase 17
Model Context Protocol server integration for enhanced AI model capabilities
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
import subprocess
import psutil
import requests

import redis.asyncio as redis
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class MCPServerType(Enum):
    GITHUB = "github"
    SUPABASE = "supabase"
    RAILWAY = "railway"
    VERCEL = "vercel"
    FILESYSTEM = "filesystem"
    BROWSER = "browser"
    MEMORY = "memory"
    POSTGRES = "postgres"

class MCPConnectionStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"
    UNKNOWN = "unknown"

class MCPCapability(Enum):
    TOOLS = "tools"
    RESOURCES = "resources"
    PROMPTS = "prompts"
    COMPLETION = "completion"
    LOGGING = "logging"

@dataclass
class MCPServer:
    """MCP server configuration and status"""
    server_id: str
    name: str
    server_type: MCPServerType
    command: str
    args: List[str]
    capabilities: List[MCPCapability]
    status: MCPConnectionStatus
    pid: Optional[int] = None
    port: Optional[int] = None
    health_check_url: Optional[str] = None
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = None

@dataclass
class MCPRequest:
    """MCP protocol request"""
    request_id: str
    server_id: str
    method: str
    params: Dict[str, Any]
    timestamp: datetime
    timeout: int = 30

@dataclass
class MCPResponse:
    """MCP protocol response"""
    request_id: str
    server_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None
    duration_ms: Optional[float] = None

@dataclass
class MCPTool:
    """Available MCP tool"""
    tool_id: str
    server_id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    category: str
    metadata: Dict[str, Any] = None

class MCPServerIntegrationService:
    """
    Comprehensive MCP server integration for enhanced AI capabilities
    """
    
    def __init__(self, redis_client=None, supabase_client=None):
        self.registry = get_registry()
        self.redis = redis_client
        self.supabase = supabase_client
        
        # MCP server management
        self.servers: Dict[str, MCPServer] = {}
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.available_tools: Dict[str, MCPTool] = {}
        
        # Request tracking
        self.pending_requests: Dict[str, MCPRequest] = {}
        self.request_history: List[MCPResponse] = []
        
        # Server configurations
        self.server_configs = {
            "github": {
                "name": "GitHub MCP",
                "command": "uvx",
                "args": ["mcp-server-github"],
                "capabilities": [MCPCapability.TOOLS, MCPCapability.RESOURCES],
                "tools": ["create_repository", "get_file", "search_repositories", "create_issue"],
                "health_endpoint": "/health"
            },
            "supabase": {
                "name": "Supabase MCP", 
                "command": "node",
                "args": ["@supabase-community/supabase-mcp/dist/index.js"],
                "capabilities": [MCPCapability.TOOLS, MCPCapability.RESOURCES],
                "tools": ["sql_query", "rpc_call", "storage_upload", "realtime_subscribe"],
                "health_endpoint": "/health"
            },
            "railway": {
                "name": "Railway MCP",
                "command": "uvx",
                "args": ["@mh8974/railway-mcp"],
                "capabilities": [MCPCapability.TOOLS],
                "tools": ["deploy_service", "get_deployments", "check_logs", "update_variables"],
                "health_endpoint": "/railway/health"
            },
            "filesystem": {
                "name": "Filesystem MCP",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/"],
                "capabilities": [MCPCapability.TOOLS, MCPCapability.RESOURCES],
                "tools": ["read_file", "write_file", "list_directory", "create_directory"],
                "health_endpoint": "/fs/health"
            },
            "browser": {
                "name": "Browser Tools MCP",
                "command": "uvx",
                "args": ["@diulela/browser-tools-mcp"],
                "capabilities": [MCPCapability.TOOLS],
                "tools": ["navigate", "click", "type", "screenshot", "get_page_content"],
                "health_endpoint": "/browser/health"
            },
            "memory": {
                "name": "Memory MCP",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "capabilities": [MCPCapability.RESOURCES, MCPCapability.TOOLS],
                "tools": ["store_memory", "retrieve_memory", "search_memories", "delete_memory"],
                "health_endpoint": "/memory/health"
            }
        }
        
        # Initialize mock data
        self._initialize_mock_data()
        
        logger.info("MCPServerIntegrationService initialized")
    
    def _initialize_mock_data(self):
        """Initialize with mock MCP server data"""
        # Create mock MCP servers
        for server_key, config in self.server_configs.items():
            server_id = f"mcp_{server_key}"
            server = MCPServer(
                server_id=server_id,
                name=config["name"],
                server_type=MCPServerType(server_key if hasattr(MCPServerType, server_key.upper()) else "github"),
                command=config["command"],
                args=config["args"],
                capabilities=[cap for cap in config["capabilities"]],
                status=MCPConnectionStatus.CONNECTED,
                pid=12000 + hash(server_key) % 10000,
                port=8000 + hash(server_key) % 1000,
                health_check_url=f"http://localhost:{8000 + hash(server_key) % 1000}{config['health_endpoint']}",
                last_health_check=datetime.now(timezone.utc) - timedelta(minutes=5),
                metadata={
                    "version": "1.0.0",
                    "uptime_seconds": 3600 + hash(server_key) % 7200,
                    "requests_handled": 100 + hash(server_key) % 1000,
                    "tools_count": len(config["tools"])
                }
            )
            self.servers[server_id] = server
            
            # Create mock tools for each server
            for tool_name in config["tools"]:
                tool = MCPTool(
                    tool_id=f"{server_id}_{tool_name}",
                    server_id=server_id,
                    name=tool_name,
                    description=f"{tool_name.replace('_', ' ').title()} tool from {config['name']}",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "input": {"type": "string", "description": f"Input for {tool_name}"}
                        },
                        "required": ["input"]
                    },
                    category=server_key,
                    metadata={"usage_count": hash(tool_name) % 100}
                )
                self.available_tools[tool.tool_id] = tool
        
        # Create mock request history
        for i in range(5):
            response = MCPResponse(
                request_id=f"req_{i+1}",
                server_id=list(self.servers.keys())[i % len(self.servers)],
                success=i < 4,  # One failed request
                result={"data": f"Mock result {i+1}"} if i < 4 else None,
                error="Connection timeout" if i >= 4 else None,
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=i*10),
                duration_ms=50.0 + i*10
            )
            self.request_history.append(response)

    async def initialize(self):
        """Initialize the MCP server integration service"""
        try:
            # Discover available MCP servers
            await self._discover_mcp_servers()
            
            # Load server configurations from database if available
            await self._load_server_configurations()
            
            # Start background monitoring
            asyncio.create_task(self._server_health_monitoring_loop())
            asyncio.create_task(self._tool_discovery_loop())
            asyncio.create_task(self._connection_management_loop())
            
            logger.info("MCPServerIntegrationService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCPServerIntegrationService: {e}")
            pass  # Continue with mock data

    async def start_mcp_server(self, server_id: str) -> Dict[str, Any]:
        """Start an MCP server"""
        try:
            server = self.servers.get(server_id)
            if not server:
                raise ValueError(f"Server {server_id} not found")
            
            if server.status == MCPConnectionStatus.CONNECTED:
                return {"status": "already_running", "pid": server.pid}
            
            # Start the server process
            process = await asyncio.create_subprocess_exec(
                server.command,
                *server.args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Update server status
            server.status = MCPConnectionStatus.CONNECTING
            server.pid = process.pid
            
            # Wait for server to be ready
            await asyncio.sleep(2)
            
            # Check if server is healthy
            is_healthy = await self._check_server_health(server_id)
            if is_healthy:
                server.status = MCPConnectionStatus.CONNECTED
                server.last_health_check = datetime.now(timezone.utc)
            else:
                server.status = MCPConnectionStatus.ERROR
            
            result = {
                "server_id": server_id,
                "status": server.status.value,
                "pid": server.pid,
                "command": f"{server.command} {' '.join(server.args)}",
                "health_check": is_healthy
            }
            
            logger.info(f"Started MCP server: {server_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to start MCP server {server_id}: {e}")
            if server_id in self.servers:
                self.servers[server_id].status = MCPConnectionStatus.ERROR
            raise

    async def stop_mcp_server(self, server_id: str) -> Dict[str, Any]:
        """Stop an MCP server"""
        try:
            server = self.servers.get(server_id)
            if not server:
                raise ValueError(f"Server {server_id} not found")
            
            if server.status == MCPConnectionStatus.DISCONNECTED:
                return {"status": "already_stopped"}
            
            # Stop the server process
            if server.pid:
                try:
                    process = psutil.Process(server.pid)
                    process.terminate()
                    
                    # Wait for process to terminate
                    try:
                        process.wait(timeout=10)
                    except psutil.TimeoutExpired:
                        process.kill()
                        
                except psutil.NoSuchProcess:
                    pass  # Process already stopped
            
            # Update server status
            server.status = MCPConnectionStatus.DISCONNECTED
            server.pid = None
            
            result = {
                "server_id": server_id,
                "status": "stopped",
                "stopped_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Stopped MCP server: {server_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to stop MCP server {server_id}: {e}")
            raise

    async def call_mcp_tool(self, 
                          tool_id: str,
                          parameters: Dict[str, Any],
                          timeout: int = 30) -> MCPResponse:
        """Call an MCP tool with parameters"""
        try:
            tool = self.available_tools.get(tool_id)
            if not tool:
                raise ValueError(f"Tool {tool_id} not found")
            
            server = self.servers.get(tool.server_id)
            if not server:
                raise ValueError(f"Server {tool.server_id} not found")
            
            if server.status != MCPConnectionStatus.CONNECTED:
                raise ValueError(f"Server {tool.server_id} is not connected")
            
            request_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)
            
            # Create request
            request = MCPRequest(
                request_id=request_id,
                server_id=tool.server_id,
                method="tools/call",
                params={
                    "name": tool.name,
                    "arguments": parameters
                },
                timestamp=start_time,
                timeout=timeout
            )
            
            self.pending_requests[request_id] = request
            
            # Mock execution - in real implementation, this would call the actual MCP server
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Generate mock response based on tool type
            mock_result = await self._generate_mock_tool_result(tool, parameters)
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds() * 1000
            
            response = MCPResponse(
                request_id=request_id,
                server_id=tool.server_id,
                success=True,
                result=mock_result,
                timestamp=end_time,
                duration_ms=duration
            )
            
            # Store response
            self.request_history.append(response)
            self.pending_requests.pop(request_id, None)
            
            # Update tool usage
            if tool.metadata:
                tool.metadata["usage_count"] = tool.metadata.get("usage_count", 0) + 1
            
            logger.info(f"Called MCP tool: {tool_id} in {duration:.2f}ms")
            return response
            
        except Exception as e:
            # Create error response
            response = MCPResponse(
                request_id=request_id if 'request_id' in locals() else str(uuid.uuid4()),
                server_id=tool.server_id if 'tool' in locals() else "unknown",
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc)
            )
            self.request_history.append(response)
            logger.error(f"Failed to call MCP tool {tool_id}: {e}")
            return response

    async def get_available_tools(self, server_id: str = None) -> List[MCPTool]:
        """Get list of available MCP tools"""
        tools = list(self.available_tools.values())
        
        if server_id:
            tools = [t for t in tools if t.server_id == server_id]
        
        return sorted(tools, key=lambda x: x.name)

    async def get_server_status(self, server_id: str = None) -> Dict[str, Any]:
        """Get comprehensive MCP server status"""
        try:
            if server_id:
                server = self.servers.get(server_id)
                if not server:
                    return {"error": f"Server {server_id} not found"}
                
                # Get server-specific metrics
                tools_count = len([t for t in self.available_tools.values() if t.server_id == server_id])
                recent_requests = [r for r in self.request_history if r.server_id == server_id]
                
                return {
                    "server_info": {
                        "server_id": server.server_id,
                        "name": server.name,
                        "type": server.server_type.value,
                        "status": server.status.value,
                        "pid": server.pid,
                        "port": server.port,
                        "uptime_seconds": server.metadata.get("uptime_seconds", 0) if server.metadata else 0
                    },
                    "capabilities": [cap.value for cap in server.capabilities],
                    "tools": {
                        "total_tools": tools_count,
                        "available_tools": [t.name for t in self.available_tools.values() if t.server_id == server_id]
                    },
                    "performance": {
                        "total_requests": len(recent_requests),
                        "successful_requests": len([r for r in recent_requests if r.success]),
                        "failed_requests": len([r for r in recent_requests if not r.success]),
                        "avg_response_time_ms": sum(r.duration_ms for r in recent_requests if r.duration_ms) / len(recent_requests) if recent_requests else 0
                    },
                    "health": {
                        "last_check": server.last_health_check.isoformat() if server.last_health_check else None,
                        "health_url": server.health_check_url,
                        "is_healthy": server.status == MCPConnectionStatus.CONNECTED
                    }
                }
            else:
                # Overall status
                total_servers = len(self.servers)
                connected_servers = len([s for s in self.servers.values() if s.status == MCPConnectionStatus.CONNECTED])
                total_tools = len(self.available_tools)
                
                return {
                    "overview": {
                        "total_servers": total_servers,
                        "connected_servers": connected_servers,
                        "disconnected_servers": total_servers - connected_servers,
                        "total_tools": total_tools,
                        "connection_rate": connected_servers / total_servers if total_servers > 0 else 0
                    },
                    "servers": {
                        server_id: {
                            "name": server.name,
                            "type": server.server_type.value,
                            "status": server.status.value,
                            "tools_count": len([t for t in self.available_tools.values() if t.server_id == server_id])
                        } for server_id, server in self.servers.items()
                    },
                    "request_metrics": {
                        "total_requests": len(self.request_history),
                        "successful_requests": len([r for r in self.request_history if r.success]),
                        "failed_requests": len([r for r in self.request_history if not r.success]),
                        "pending_requests": len(self.pending_requests)
                    },
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get server status: {e}")
            return {"error": str(e)}

    async def get_mcp_analytics(self) -> Dict[str, Any]:
        """Get comprehensive MCP analytics dashboard"""
        try:
            # Server analytics
            server_types = {}
            for server in self.servers.values():
                server_type = server.server_type.value
                if server_type not in server_types:
                    server_types[server_type] = {"count": 0, "connected": 0}
                server_types[server_type]["count"] += 1
                if server.status == MCPConnectionStatus.CONNECTED:
                    server_types[server_type]["connected"] += 1
            
            # Tool analytics
            tool_categories = {}
            for tool in self.available_tools.values():
                category = tool.category
                if category not in tool_categories:
                    tool_categories[category] = {"count": 0, "usage": 0}
                tool_categories[category]["count"] += 1
                tool_categories[category]["usage"] += tool.metadata.get("usage_count", 0) if tool.metadata else 0
            
            # Performance analytics
            recent_requests = [r for r in self.request_history if r.timestamp and r.timestamp > datetime.now(timezone.utc) - timedelta(hours=24)]
            
            hourly_stats = {}
            for request in recent_requests:
                hour = request.timestamp.hour
                if hour not in hourly_stats:
                    hourly_stats[hour] = {"total": 0, "successful": 0, "failed": 0}
                hourly_stats[hour]["total"] += 1
                if request.success:
                    hourly_stats[hour]["successful"] += 1
                else:
                    hourly_stats[hour]["failed"] += 1
            
            return {
                "server_analytics": {
                    "total_servers": len(self.servers),
                    "server_types": server_types,
                    "connection_health": sum(1 for s in self.servers.values() if s.status == MCPConnectionStatus.CONNECTED) / len(self.servers) if self.servers else 0,
                    "average_uptime": sum(s.metadata.get("uptime_seconds", 0) for s in self.servers.values() if s.metadata) / len(self.servers) if self.servers else 0
                },
                "tool_analytics": {
                    "total_tools": len(self.available_tools),
                    "tool_categories": tool_categories,
                    "most_used_tools": sorted(
                        [(t.name, t.metadata.get("usage_count", 0)) for t in self.available_tools.values() if t.metadata],
                        key=lambda x: x[1], reverse=True
                    )[:10]
                },
                "request_analytics": {
                    "total_requests": len(self.request_history),
                    "recent_requests_24h": len(recent_requests),
                    "success_rate": len([r for r in recent_requests if r.success]) / len(recent_requests) if recent_requests else 0,
                    "avg_response_time_ms": sum(r.duration_ms for r in recent_requests if r.duration_ms) / len(recent_requests) if recent_requests else 0,
                    "hourly_distribution": hourly_stats
                },
                "error_analytics": {
                    "common_errors": [
                        {"error": "Connection timeout", "count": 5},
                        {"error": "Invalid parameters", "count": 3},
                        {"error": "Server unavailable", "count": 2}
                    ],
                    "error_rate_by_server": {
                        server_id: len([r for r in self.request_history if r.server_id == server_id and not r.success]) / len([r for r in self.request_history if r.server_id == server_id]) if [r for r in self.request_history if r.server_id == server_id] else 0
                        for server_id in self.servers.keys()
                    }
                },
                "capacity_metrics": {
                    "concurrent_connections": len(self.active_connections),
                    "pending_requests": len(self.pending_requests),
                    "queue_health": "good" if len(self.pending_requests) < 10 else "warning" if len(self.pending_requests) < 50 else "critical"
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get MCP analytics: {e}")
            return {}

    async def _discover_mcp_servers(self):
        """Discover available MCP servers on the system"""
        try:
            # Check for installed MCP servers
            mcp_commands = ["uvx", "npx", "node"]
            for command in mcp_commands:
                try:
                    result = await asyncio.create_subprocess_exec(
                        command, "--help",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await result.wait()
                    logger.debug(f"Found MCP command: {command}")
                except FileNotFoundError:
                    logger.debug(f"MCP command not found: {command}")
                    
        except Exception as e:
            logger.warning(f"MCP server discovery failed: {e}")

    async def _load_server_configurations(self):
        """Load server configurations from database"""
        try:
            if self.supabase:
                response = self.supabase.table('mcp_servers').select('*').execute()
                for server_data in response.data:
                    # Load server from database
                    pass
        except Exception as e:
            logger.warning(f"Could not load server configurations: {e}")

    async def _check_server_health(self, server_id: str) -> bool:
        """Check if an MCP server is healthy"""
        try:
            server = self.servers.get(server_id)
            if not server or not server.health_check_url:
                return False
            
            # Mock health check - in real implementation, make HTTP request
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            logger.warning(f"Health check failed for server {server_id}: {e}")
            return False

    async def _generate_mock_tool_result(self, tool: MCPTool, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock results for tool calls"""
        tool_name = tool.name.lower()
        
        if "github" in tool_name or "repository" in tool_name:
            return {
                "repository": {
                    "name": "mock-repo",
                    "url": "https://github.com/user/mock-repo",
                    "created": True
                },
                "status": "success"
            }
        elif "file" in tool_name:
            return {
                "file_path": parameters.get("path", "/mock/file.txt"),
                "content": "Mock file content",
                "size_bytes": 1024,
                "modified": datetime.now(timezone.utc).isoformat()
            }
        elif "sql" in tool_name or "database" in tool_name:
            return {
                "query_result": [
                    {"id": 1, "name": "Mock Record 1"},
                    {"id": 2, "name": "Mock Record 2"}
                ],
                "rows_affected": 2,
                "execution_time_ms": 45.7
            }
        elif "deploy" in tool_name:
            return {
                "deployment_id": "dep_" + str(uuid.uuid4()),
                "status": "deployed",
                "url": "https://mock-deployment.railway.app",
                "build_time_ms": 120000
            }
        else:
            return {
                "tool": tool.name,
                "parameters": parameters,
                "result": "Mock tool execution successful",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _server_health_monitoring_loop(self):
        """Background server health monitoring"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                for server_id in self.servers.keys():
                    is_healthy = await self._check_server_health(server_id)
                    server = self.servers[server_id]
                    server.last_health_check = datetime.now(timezone.utc)
                    
                    if is_healthy and server.status == MCPConnectionStatus.ERROR:
                        server.status = MCPConnectionStatus.CONNECTED
                    elif not is_healthy and server.status == MCPConnectionStatus.CONNECTED:
                        server.status = MCPConnectionStatus.ERROR
                        
                logger.debug("Server health monitoring completed")
            except Exception as e:
                logger.error(f"Error in server health monitoring: {e}")

    async def _tool_discovery_loop(self):
        """Background tool discovery"""
        while True:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes
                # Rediscover available tools
                await self._discover_available_tools()
                logger.debug("Tool discovery completed")
            except Exception as e:
                logger.error(f"Error in tool discovery: {e}")

    async def _connection_management_loop(self):
        """Background connection management"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                # Clean up old requests
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
                self.request_history = [r for r in self.request_history if r.timestamp and r.timestamp > cutoff_time]
                logger.debug("Connection management completed")
            except Exception as e:
                logger.error(f"Error in connection management: {e}")

    async def _discover_available_tools(self):
        """Discover tools from connected servers"""
        # Mock tool discovery - in real implementation, query each server for available tools
        pass

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        connected_servers = len([s for s in self.servers.values() if s.status == MCPConnectionStatus.CONNECTED])
        
        return {
            "service": "mcp_server_integration_service",
            "status": "running",
            "servers_total": len(self.servers),
            "servers_connected": connected_servers,
            "tools_available": len(self.available_tools),
            "pending_requests": len(self.pending_requests),
            "last_health_check": max((s.last_health_check for s in self.servers.values() if s.last_health_check), default=None),
            "last_update": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_mcp_server_integration_service():
    """Factory function to create MCPServerIntegrationService instance"""
    registry = get_registry()
    redis_client = registry.get_connection("redis")
    supabase_client = registry.get_connection("supabase")
    
    service = MCPServerIntegrationService(redis_client, supabase_client)
    return service