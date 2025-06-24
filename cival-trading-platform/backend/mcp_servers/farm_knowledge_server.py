"""
Farm Knowledge MCP Server - Phase 8
Provides agents seamless access to farm knowledge resources, trading books, SOPs, and documentation
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Import our models
from ..models.farm_knowledge_models import (
    FarmResource, ResourceAccessLog, TradingResourceType, 
    ResourceSearchRequest, AgentKnowledgeRequest, ContentFormat,
    AccessLevel, ProcessingStatus
)
from ..core.service_registry import get_registry

logger = logging.getLogger(__name__)

class FarmKnowledgeServer:
    """MCP Server providing agents access to farm knowledge resources"""
    
    def __init__(self):
        self.server = Server("farm-knowledge")
        self.registry = get_registry()
        self.setup_tools()
        self.setup_resources()
        
    def setup_tools(self):
        """Setup MCP tools for agent knowledge access"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List all available knowledge tools for agents"""
            return [
                types.Tool(
                    name="search_knowledge_resources",
                    description="Search farm knowledge resources including trading books, SOPs, strategies, and documentation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for knowledge resources"
                            },
                            "resource_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by resource types (trading_books, sops, strategies, etc.)"
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Agent ID for access logging and personalization"
                            },
                            "max_results": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum number of results to return"
                            },
                            "include_content": {
                                "type": "boolean",
                                "default": False,
                                "description": "Include full content in results"
                            }
                        },
                        "required": ["query", "agent_id"]
                    }
                ),
                
                types.Tool(
                    name="get_resource_content",
                    description="Get the full content of a specific knowledge resource",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "resource_id": {
                                "type": "string",
                                "description": "Unique identifier of the resource"
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Agent ID for access logging"
                            },
                            "access_type": {
                                "type": "string",
                                "enum": ["read", "reference", "learn"],
                                "default": "read",
                                "description": "Type of access for logging purposes"
                            },
                            "context": {
                                "type": "string",
                                "description": "Trading context or reason for accessing this resource"
                            }
                        },
                        "required": ["resource_id", "agent_id"]
                    }
                ),
                
                types.Tool(
                    name="get_trading_sops",
                    description="Get standard operating procedures relevant to specific trading strategies or situations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "strategy_type": {
                                "type": "string",
                                "description": "Trading strategy type (e.g., 'momentum', 'mean_reversion', 'arbitrage')"
                            },
                            "situation": {
                                "type": "string",
                                "description": "Trading situation (e.g., 'risk_management', 'position_sizing', 'emergency_stop')"
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Agent ID for personalized SOPs"
                            },
                            "urgency": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                                "default": "medium"
                            }
                        },
                        "required": ["agent_id"]
                    }
                ),
                
                types.Tool(
                    name="get_market_research",
                    description="Get market research and analysis documents for specific symbols or market conditions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol (e.g., 'BTCUSD', 'ETHUSD')"
                            },
                            "timeframe": {
                                "type": "string",
                                "description": "Analysis timeframe (e.g., '1d', '1w', '1m')"
                            },
                            "research_type": {
                                "type": "string",
                                "enum": ["technical", "fundamental", "sentiment", "all"],
                                "default": "all"
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Agent ID for access logging"
                            },
                            "recency": {
                                "type": "string",
                                "enum": ["latest", "week", "month"],
                                "default": "latest"
                            }
                        },
                        "required": ["agent_id"]
                    }
                ),
                
                types.Tool(
                    name="get_learning_resources",
                    description="Get learning resources and training materials for agent skill development",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "skill_area": {
                                "type": "string",
                                "description": "Skill area to learn (e.g., 'technical_analysis', 'risk_management', 'portfolio_optimization')"
                            },
                            "current_level": {
                                "type": "string",
                                "enum": ["beginner", "intermediate", "advanced"],
                                "description": "Current skill level of the agent"
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Agent ID for personalized recommendations"
                            },
                            "learning_goal": {
                                "type": "string",
                                "description": "Specific learning objective or goal"
                            },
                            "time_available": {
                                "type": "integer",
                                "description": "Available learning time in minutes"
                            }
                        },
                        "required": ["skill_area", "agent_id"]
                    }
                ),
                
                types.Tool(
                    name="log_knowledge_usage",
                    description="Log how knowledge resources were used and their effectiveness",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "resource_id": {
                                "type": "string",
                                "description": "Resource that was used"
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Agent that used the resource"
                            },
                            "usage_type": {
                                "type": "string",
                                "enum": ["applied_successfully", "partially_helpful", "not_applicable", "needs_update"],
                                "description": "How the resource was used"
                            },
                            "effectiveness_rating": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 5,
                                "description": "Effectiveness rating (1-5)"
                            },
                            "trading_outcome": {
                                "type": "object",
                                "description": "Trading results after applying knowledge"
                            },
                            "feedback": {
                                "type": "string",
                                "description": "Detailed feedback on resource utility"
                            }
                        },
                        "required": ["resource_id", "agent_id", "usage_type"]
                    }
                ),
                
                types.Tool(
                    name="get_recommended_resources",
                    description="Get AI-recommended knowledge resources based on agent performance and goals",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Agent ID for personalized recommendations"
                            },
                            "current_goal": {
                                "type": "string",
                                "description": "Current trading goal or objective"
                            },
                            "performance_context": {
                                "type": "object",
                                "description": "Recent performance metrics and challenges"
                            },
                            "recommendation_type": {
                                "type": "string",
                                "enum": ["skill_gap", "performance_improvement", "goal_related", "trending"],
                                "default": "performance_improvement"
                            },
                            "max_recommendations": {
                                "type": "integer",
                                "default": 5,
                                "maximum": 10
                            }
                        },
                        "required": ["agent_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """Handle tool calls from agents"""
            
            try:
                if name == "search_knowledge_resources":
                    return await self._search_knowledge_resources(arguments)
                elif name == "get_resource_content":
                    return await self._get_resource_content(arguments)
                elif name == "get_trading_sops":
                    return await self._get_trading_sops(arguments)
                elif name == "get_market_research":
                    return await self._get_market_research(arguments)
                elif name == "get_learning_resources":
                    return await self._get_learning_resources(arguments)
                elif name == "log_knowledge_usage":
                    return await self._log_knowledge_usage(arguments)
                elif name == "get_recommended_resources":
                    return await self._get_recommended_resources(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Error handling tool call {name}: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    def setup_resources(self):
        """Setup MCP resources for knowledge access"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """List available knowledge resources"""
            resources = []
            
            # Get farm knowledge service
            farm_service = self.registry.get_service("farm_knowledge_service")
            if farm_service:
                try:
                    # Get public resources
                    public_resources = await farm_service.get_public_resources()
                    
                    for resource in public_resources[:20]:  # Limit for performance
                        resources.append(types.Resource(
                            uri=f"knowledge://{resource.resource_id}",
                            name=resource.title,
                            description=resource.description or f"{resource.resource_type} resource",
                            mimeType=resource.content_type
                        ))
                        
                except Exception as e:
                    logger.error(f"Error listing resources: {e}")
            
            return resources
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read knowledge resource content"""
            
            try:
                # Parse resource ID from URI
                if not uri.startswith("knowledge://"):
                    raise ValueError("Invalid knowledge resource URI")
                
                resource_id = uri.replace("knowledge://", "")
                
                # Get farm knowledge service
                farm_service = self.registry.get_service("farm_knowledge_service")
                if not farm_service:
                    raise ValueError("Farm knowledge service not available")
                
                # Get resource content
                resource = await farm_service.get_resource_by_id(resource_id)
                if not resource:
                    raise ValueError(f"Resource {resource_id} not found")
                
                # Return content based on format
                if resource.extracted_text:
                    return resource.extracted_text
                elif resource.summary:
                    return f"Summary: {resource.summary}\n\nKey Concepts: {', '.join(resource.key_concepts)}"
                else:
                    return f"Resource: {resource.title}\nDescription: {resource.description}\nType: {resource.resource_type}"
                    
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                return f"Error reading resource: {str(e)}"
    
    # Tool implementation methods
    
    async def _search_knowledge_resources(self, args: dict) -> list[types.TextContent]:
        """Search farm knowledge resources"""
        
        try:
            farm_service = self.registry.get_service("farm_knowledge_service")
            if not farm_service:
                return [types.TextContent(type="text", text="Farm knowledge service not available")]
            
            # Create search request
            search_request = ResourceSearchRequest(
                query=args["query"],
                resource_types=[TradingResourceType(rt) for rt in args.get("resource_types", [])],
                limit=args.get("max_results", 10),
                include_content=args.get("include_content", False)
            )
            
            # Perform search
            search_results = await farm_service.search_resources(search_request, args["agent_id"])
            
            # Log access
            await self._log_resource_access(
                agent_id=args["agent_id"],
                access_type="search",
                context=f"Search query: {args['query']}"
            )
            
            # Format results
            if not search_results.results:
                return [types.TextContent(type="text", text="No resources found matching your query")]
            
            results_text = f"Found {len(search_results.results)} resources:\n\n"
            
            for i, resource in enumerate(search_results.results, 1):
                results_text += f"{i}. **{resource.title}**\n"
                results_text += f"   Type: {resource.resource_type}\n"
                results_text += f"   Description: {resource.description or 'No description'}\n"
                results_text += f"   Tags: {', '.join(resource.tags) if resource.tags else 'None'}\n"
                results_text += f"   Resource ID: {resource.resource_id}\n"
                
                if args.get("include_content") and resource.summary:
                    results_text += f"   Summary: {resource.summary[:200]}...\n"
                
                results_text += "\n"
            
            return [types.TextContent(type="text", text=results_text)]
            
        except Exception as e:
            logger.error(f"Error searching knowledge resources: {e}")
            return [types.TextContent(type="text", text=f"Search error: {str(e)}")]
    
    async def _get_resource_content(self, args: dict) -> list[types.TextContent]:
        """Get full content of a specific resource"""
        
        try:
            farm_service = self.registry.get_service("farm_knowledge_service")
            if not farm_service:
                return [types.TextContent(type="text", text="Farm knowledge service not available")]
            
            # Get resource
            resource = await farm_service.get_resource_by_id(args["resource_id"])
            if not resource:
                return [types.TextContent(type="text", text="Resource not found")]
            
            # Check access permissions
            agent_id = args["agent_id"]
            if not await farm_service.check_agent_access(agent_id, resource.resource_id):
                return [types.TextContent(type="text", text="Access denied to this resource")]
            
            # Log access
            await self._log_resource_access(
                resource_id=resource.resource_id,
                agent_id=agent_id,
                access_type=args.get("access_type", "read"),
                context=args.get("context", "Direct resource access")
            )
            
            # Return content
            content = ""
            content += f"# {resource.title}\n\n"
            
            if resource.description:
                content += f"**Description:** {resource.description}\n\n"
            
            if resource.metadata:
                metadata = resource.metadata
                if isinstance(metadata, dict):
                    if metadata.get("author"):
                        content += f"**Author:** {metadata['author']}\n"
                    if metadata.get("difficulty_level"):
                        content += f"**Difficulty:** {metadata['difficulty_level']}\n"
                    content += "\n"
            
            if resource.key_concepts:
                content += f"**Key Concepts:** {', '.join(resource.key_concepts)}\n\n"
            
            if resource.extracted_text:
                content += "## Content\n\n"
                content += resource.extracted_text
            elif resource.summary:
                content += "## Summary\n\n"
                content += resource.summary
            else:
                content += "Content not available in text format. This may be a binary file."
            
            return [types.TextContent(type="text", text=content)]
            
        except Exception as e:
            logger.error(f"Error getting resource content: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _get_trading_sops(self, args: dict) -> list[types.TextContent]:
        """Get relevant standard operating procedures"""
        
        try:
            farm_service = self.registry.get_service("farm_knowledge_service")
            if not farm_service:
                return [types.TextContent(type="text", text="Farm knowledge service not available")]
            
            # Build search criteria for SOPs
            search_criteria = {
                "resource_types": [TradingResourceType.SOPS],
                "agent_id": args["agent_id"]
            }
            
            if args.get("strategy_type"):
                search_criteria["strategy_context"] = args["strategy_type"]
            
            if args.get("situation"):
                search_criteria["situation_context"] = args["situation"]
            
            # Get relevant SOPs
            sops = await farm_service.get_contextual_sops(search_criteria)
            
            if not sops:
                return [types.TextContent(type="text", text="No relevant SOPs found")]
            
            # Format SOPs response
            sops_text = "# Relevant Standard Operating Procedures\n\n"
            
            for i, sop in enumerate(sops, 1):
                sops_text += f"## {i}. {sop.title}\n\n"
                
                if sop.description:
                    sops_text += f"**Purpose:** {sop.description}\n\n"
                
                if sop.summary:
                    sops_text += f"**Procedure:**\n{sop.summary}\n\n"
                elif sop.extracted_text:
                    # Take first 500 characters of extracted text
                    sops_text += f"**Procedure:**\n{sop.extracted_text[:500]}...\n\n"
                
                sops_text += f"*Resource ID: {sop.resource_id}*\n\n"
                sops_text += "---\n\n"
            
            # Log access
            await self._log_resource_access(
                agent_id=args["agent_id"],
                access_type="read",
                context=f"SOP request: {args.get('strategy_type', '')} {args.get('situation', '')}"
            )
            
            return [types.TextContent(type="text", text=sops_text)]
            
        except Exception as e:
            logger.error(f"Error getting trading SOPs: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _get_market_research(self, args: dict) -> list[types.TextContent]:
        """Get market research and analysis"""
        
        try:
            farm_service = self.registry.get_service("farm_knowledge_service")
            if not farm_service:
                return [types.TextContent(type="text", text="Farm knowledge service not available")]
            
            # Search for market research
            search_criteria = {
                "resource_types": [TradingResourceType.RESEARCH],
                "agent_id": args["agent_id"]
            }
            
            if args.get("symbol"):
                search_criteria["symbol"] = args["symbol"]
            
            if args.get("timeframe"):
                search_criteria["timeframe"] = args["timeframe"]
            
            if args.get("research_type"):
                search_criteria["research_type"] = args["research_type"]
            
            research = await farm_service.get_market_research(search_criteria)
            
            if not research:
                return [types.TextContent(type="text", text="No relevant market research found")]
            
            # Format research response
            research_text = "# Market Research & Analysis\n\n"
            
            for i, doc in enumerate(research, 1):
                research_text += f"## {i}. {doc.title}\n\n"
                
                if doc.description:
                    research_text += f"**Analysis:** {doc.description}\n\n"
                
                if doc.summary:
                    research_text += f"**Key Findings:**\n{doc.summary}\n\n"
                
                if doc.key_concepts:
                    research_text += f"**Key Concepts:** {', '.join(doc.key_concepts)}\n\n"
                
                research_text += f"*Updated: {doc.last_modified.strftime('%Y-%m-%d %H:%M')}*\n"
                research_text += f"*Resource ID: {doc.resource_id}*\n\n"
                research_text += "---\n\n"
            
            return [types.TextContent(type="text", text=research_text)]
            
        except Exception as e:
            logger.error(f"Error getting market research: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _get_learning_resources(self, args: dict) -> list[types.TextContent]:
        """Get learning resources for skill development"""
        
        try:
            farm_service = self.registry.get_service("farm_knowledge_service")
            if not farm_service:
                return [types.TextContent(type="text", text="Farm knowledge service not available")]
            
            # Get learning path recommendations
            learning_request = {
                "agent_id": args["agent_id"],
                "skill_area": args["skill_area"],
                "current_level": args.get("current_level", "intermediate"),
                "learning_goal": args.get("learning_goal"),
                "time_available": args.get("time_available")
            }
            
            learning_resources = await farm_service.get_learning_resources(learning_request)
            
            if not learning_resources:
                return [types.TextContent(type="text", text="No learning resources found for this skill area")]
            
            # Format learning response
            learning_text = f"# Learning Resources: {args['skill_area']}\n\n"
            
            if args.get("current_level"):
                learning_text += f"**Current Level:** {args['current_level']}\n\n"
            
            if args.get("learning_goal"):
                learning_text += f"**Learning Goal:** {args['learning_goal']}\n\n"
            
            learning_text += "## Recommended Resources\n\n"
            
            for i, resource in enumerate(learning_resources, 1):
                learning_text += f"### {i}. {resource.title}\n\n"
                
                if resource.description:
                    learning_text += f"**Description:** {resource.description}\n\n"
                
                # Estimate reading time
                if hasattr(resource.metadata, 'estimated_read_time') and resource.metadata.estimated_read_time:
                    learning_text += f"**Estimated Time:** {resource.metadata.estimated_read_time} minutes\n\n"
                
                if resource.key_concepts:
                    learning_text += f"**Key Topics:** {', '.join(resource.key_concepts[:5])}\n\n"
                
                learning_text += f"*Resource ID: {resource.resource_id}*\n\n"
            
            return [types.TextContent(type="text", text=learning_text)]
            
        except Exception as e:
            logger.error(f"Error getting learning resources: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _log_knowledge_usage(self, args: dict) -> list[types.TextContent]:
        """Log knowledge usage and effectiveness"""
        
        try:
            farm_service = self.registry.get_service("farm_knowledge_service")
            if not farm_service:
                return [types.TextContent(type="text", text="Farm knowledge service not available")]
            
            # Create usage log
            usage_log = {
                "resource_id": args["resource_id"],
                "agent_id": args["agent_id"],
                "usage_type": args["usage_type"],
                "effectiveness_rating": args.get("effectiveness_rating"),
                "trading_outcome": args.get("trading_outcome"),
                "feedback": args.get("feedback"),
                "logged_at": datetime.now(timezone.utc)
            }
            
            # Save usage log
            await farm_service.log_resource_usage(usage_log)
            
            return [types.TextContent(type="text", text="Knowledge usage logged successfully")]
            
        except Exception as e:
            logger.error(f"Error logging knowledge usage: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _get_recommended_resources(self, args: dict) -> list[types.TextContent]:
        """Get AI-recommended resources"""
        
        try:
            farm_service = self.registry.get_service("farm_knowledge_service")
            if not farm_service:
                return [types.TextContent(type="text", text="Farm knowledge service not available")]
            
            # Get AI recommendations
            recommendation_request = {
                "agent_id": args["agent_id"],
                "current_goal": args.get("current_goal"),
                "performance_context": args.get("performance_context"),
                "recommendation_type": args.get("recommendation_type", "performance_improvement"),
                "max_recommendations": args.get("max_recommendations", 5)
            }
            
            recommendations = await farm_service.get_ai_recommendations(recommendation_request)
            
            if not recommendations:
                return [types.TextContent(type="text", text="No recommendations available at this time")]
            
            # Format recommendations
            rec_text = "# AI-Recommended Knowledge Resources\n\n"
            
            for i, rec in enumerate(recommendations, 1):
                rec_text += f"## {i}. {rec['resource'].title}\n\n"
                rec_text += f"**Recommendation Reason:** {rec['reason']}\n\n"
                rec_text += f"**Confidence:** {rec['confidence']:.1%}\n\n"
                
                if rec.get('estimated_impact'):
                    rec_text += f"**Expected Impact:** {rec['estimated_impact']}\n\n"
                
                rec_text += f"*Resource ID: {rec['resource'].resource_id}*\n\n"
                rec_text += "---\n\n"
            
            return [types.TextContent(type="text", text=rec_text)]
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _log_resource_access(self, agent_id: str, access_type: str, context: str, resource_id: str = None):
        """Log resource access for analytics"""
        
        try:
            farm_service = self.registry.get_service("farm_knowledge_service")
            if farm_service:
                access_log = ResourceAccessLog(
                    resource_id=resource_id or "search",
                    agent_id=agent_id,
                    access_type=access_type,
                    access_method="mcp",
                    trading_context=context,
                    accessed_at=datetime.now(timezone.utc)
                )
                
                await farm_service.log_resource_access(access_log)
                
        except Exception as e:
            logger.warning(f"Failed to log resource access: {e}")

# Server factory function
def create_farm_knowledge_server():
    """Create and return Farm Knowledge MCP server instance"""
    return FarmKnowledgeServer()

# Main server startup
async def main():
    """Main function to run the Farm Knowledge MCP server"""
    
    server = create_farm_knowledge_server()
    
    # Run with stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="farm-knowledge",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())