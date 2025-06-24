"""
MCP (Model Context Protocol) Models
Data models for MCP tool execution and management
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class MCPToolCategory(str, Enum):
    """MCP Tool Categories"""
    DEPLOYMENT = "deployment"
    DATABASE = "database"
    AUTOMATION = "automation"
    DEVELOPMENT = "development"
    TRADING = "trading"
    ANALYSIS = "analysis"

class MCPToolStatus(str, Enum):
    """MCP Tool Status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    EXECUTING = "executing"

class MCPExecutionStatus(str, Enum):
    """MCP Execution Status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class MCPPermission(BaseModel):
    """MCP Tool Permission"""
    resource: str
    action: str
    conditions: Optional[Dict[str, Any]] = None

class MCPParameter(BaseModel):
    """MCP Tool Parameter Definition"""
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    validation: Optional[Dict[str, Any]] = None

class MCPTool(BaseModel):
    """MCP Tool Definition"""
    id: str
    name: str
    category: MCPToolCategory
    description: str
    version: str = "1.0.0"
    parameters: List[MCPParameter] = []
    permissions: List[MCPPermission] = []
    status: MCPToolStatus = MCPToolStatus.AVAILABLE
    enabled: bool = True
    usage_stats: Optional['MCPToolUsage'] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MCPToolUsage(BaseModel):
    """MCP Tool Usage Statistics"""
    tool_id: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    average_response_time: float = 0.0
    last_used: Optional[datetime] = None
    daily_calls: int = 0
    monthly_calls: int = 0

class MCPExecutionRequest(BaseModel):
    """MCP Tool Execution Request"""
    tool_id: str
    parameters: Dict[str, Any] = {}
    agent_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timeout: int = 30  # seconds
    priority: int = 1  # 1-10, 10 being highest
    metadata: Dict[str, Any] = {}

class MCPExecutionResult(BaseModel):
    """MCP Tool Execution Result"""
    execution_id: str
    tool_id: str
    status: MCPExecutionStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    logs: List[str] = []
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # seconds
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

class MCPAuditLog(BaseModel):
    """MCP Tool Execution Audit Log"""
    id: str
    execution_id: str
    tool_id: str
    agent_id: Optional[str] = None
    action: str
    parameters: Dict[str, Any]
    result_summary: Optional[str] = None
    status: MCPExecutionStatus
    duration: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    ip_address: Optional[str] = None

class MCPToolRegistry(BaseModel):
    """MCP Tool Registry"""
    tools: Dict[str, MCPTool] = {}
    categories: Dict[MCPToolCategory, List[str]] = {}
    total_tools: int = 0
    enabled_tools: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class MCPMetrics(BaseModel):
    """MCP System Metrics"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_response_time: float = 0.0
    tools_available: int = 0
    tools_enabled: int = 0
    active_executions: int = 0
    executions_today: int = 0
    executions_this_hour: int = 0
    success_rate: float = 0.0
    error_rate: float = 0.0
    uptime: str = "0s"

# Predefined MCP Tools
RAILWAY_MCP_TOOLS = [
    MCPTool(
        id="railway_deploy",
        name="Railway Deploy",
        category=MCPToolCategory.DEPLOYMENT,
        description="Deploy application to Railway platform",
        parameters=[
            MCPParameter(name="service_name", type="string", description="Service name", required=True),
            MCPParameter(name="environment", type="string", description="Environment", default="production"),
            MCPParameter(name="build_command", type="string", description="Build command", required=False)
        ],
        permissions=[
            MCPPermission(resource="railway", action="deploy"),
            MCPPermission(resource="environment", action="read")
        ]
    ),
    MCPTool(
        id="railway_logs",
        name="Railway Logs",
        category=MCPToolCategory.DEVELOPMENT,
        description="Fetch logs from Railway deployment",
        parameters=[
            MCPParameter(name="service_id", type="string", description="Service ID", required=True),
            MCPParameter(name="lines", type="integer", description="Number of lines", default=100)
        ]
    )
]

SUPABASE_MCP_TOOLS = [
    MCPTool(
        id="supabase_query",
        name="Supabase Query",
        category=MCPToolCategory.DATABASE,
        description="Execute SQL query on Supabase database",
        parameters=[
            MCPParameter(name="query", type="string", description="SQL query", required=True),
            MCPParameter(name="params", type="object", description="Query parameters", default={})
        ],
        permissions=[
            MCPPermission(resource="database", action="read"),
            MCPPermission(resource="database", action="write")
        ]
    ),
    MCPTool(
        id="supabase_realtime",
        name="Supabase Realtime",
        category=MCPToolCategory.DATABASE,
        description="Subscribe to real-time changes",
        parameters=[
            MCPParameter(name="table", type="string", description="Table name", required=True),
            MCPParameter(name="event", type="string", description="Event type", default="*")
        ]
    )
]

N8N_MCP_TOOLS = [
    MCPTool(
        id="n8n_workflow_execute",
        name="Execute N8N Workflow",
        category=MCPToolCategory.AUTOMATION,
        description="Execute N8N workflow for trading automation",
        parameters=[
            MCPParameter(name="workflow_id", type="string", description="Workflow ID", required=True),
            MCPParameter(name="input_data", type="object", description="Input data", default={})
        ],
        permissions=[
            MCPPermission(resource="n8n", action="execute"),
            MCPPermission(resource="trading", action="read")
        ]
    ),
    MCPTool(
        id="n8n_workflow_status",
        name="N8N Workflow Status",
        category=MCPToolCategory.AUTOMATION,
        description="Get status of N8N workflow execution",
        parameters=[
            MCPParameter(name="execution_id", type="string", description="Execution ID", required=True)
        ]
    )
]

BROWSER_MCP_TOOLS = [
    MCPTool(
        id="browser_scrape",
        name="Browser Scrape",
        category=MCPToolCategory.ANALYSIS,
        description="Scrape web data for market analysis",
        parameters=[
            MCPParameter(name="url", type="string", description="URL to scrape", required=True),
            MCPParameter(name="selector", type="string", description="CSS selector", required=False),
            MCPParameter(name="wait_for", type="string", description="Wait for element", required=False)
        ],
        permissions=[
            MCPPermission(resource="browser", action="navigate"),
            MCPPermission(resource="network", action="request")
        ]
    ),
    MCPTool(
        id="browser_screenshot",
        name="Browser Screenshot",
        category=MCPToolCategory.ANALYSIS,
        description="Take screenshot of web page",
        parameters=[
            MCPParameter(name="url", type="string", description="URL to screenshot", required=True),
            MCPParameter(name="viewport", type="object", description="Viewport size", default={"width": 1920, "height": 1080})
        ]
    )
]

IB_MCP_TOOLS = [
    MCPTool(
        id="ib_market_data",
        name="IB Market Data",
        category=MCPToolCategory.TRADING,
        description="Get market data from Interactive Brokers",
        parameters=[
            MCPParameter(name="symbol", type="string", description="Trading symbol", required=True),
            MCPParameter(name="data_type", type="string", description="Data type", default="snapshot")
        ],
        permissions=[
            MCPPermission(resource="ib", action="market_data"),
            MCPPermission(resource="trading", action="read")
        ]
    ),
    MCPTool(
        id="ib_place_order",
        name="IB Place Order",
        category=MCPToolCategory.TRADING,
        description="Place order through Interactive Brokers",
        parameters=[
            MCPParameter(name="symbol", type="string", description="Trading symbol", required=True),
            MCPParameter(name="action", type="string", description="Buy/Sell", required=True),
            MCPParameter(name="quantity", type="number", description="Order quantity", required=True),
            MCPParameter(name="order_type", type="string", description="Order type", default="MKT")
        ],
        permissions=[
            MCPPermission(resource="ib", action="place_order"),
            MCPPermission(resource="trading", action="write")
        ]
    )
]

# Complete tool registry
DEFAULT_MCP_TOOLS = (
    RAILWAY_MCP_TOOLS + 
    SUPABASE_MCP_TOOLS + 
    N8N_MCP_TOOLS + 
    BROWSER_MCP_TOOLS + 
    IB_MCP_TOOLS
)

def create_default_tool_registry() -> MCPToolRegistry:
    """Create default MCP tool registry with all available tools"""
    registry = MCPToolRegistry()
    
    for tool in DEFAULT_MCP_TOOLS:
        registry.tools[tool.id] = tool
        
        if tool.category not in registry.categories:
            registry.categories[tool.category] = []
        registry.categories[tool.category].append(tool.id)
    
    registry.total_tools = len(registry.tools)
    registry.enabled_tools = len([t for t in registry.tools.values() if t.enabled])
    
    return registry