#!/usr/bin/env python3
"""
Neo4j Intelligence MCP Server
Graph database operations, relationship analysis, and network intelligence for trading systems
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
import aiohttp
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Neo4j Intelligence MCP Server",
    description="Graph database operations and network intelligence",
    version="1.0.0"
)

security = HTTPBearer()

# Enums
class NodeType(str, Enum):
    SYMBOL = "symbol"
    AGENT = "agent"
    STRATEGY = "strategy"
    PORTFOLIO = "portfolio"
    TRADE = "trade"
    NEWS = "news"
    SECTOR = "sector"
    EXCHANGE = "exchange"
    ANALYST = "analyst"
    COMPANY = "company"

class RelationshipType(str, Enum):
    TRADES = "TRADES"
    OWNS = "OWNS"
    CORRELATES_WITH = "CORRELATES_WITH"
    INFLUENCES = "INFLUENCES"
    BELONGS_TO = "BELONGS_TO"
    MANAGES = "MANAGES"
    ANALYZES = "ANALYZES"
    MENTIONS = "MENTIONS"
    COMPETES_WITH = "COMPETES_WITH"
    DEPENDS_ON = "DEPENDS_ON"

class QueryType(str, Enum):
    CYPHER = "cypher"
    SHORTEST_PATH = "shortest_path"
    NEIGHBORS = "neighbors"
    CENTRALITY = "centrality"
    COMMUNITY = "community"
    PATTERN_MATCH = "pattern_match"
    SUBGRAPH = "subgraph"

class CentralityType(str, Enum):
    DEGREE = "degree"
    BETWEENNESS = "betweenness"
    CLOSENESS = "closeness"
    EIGENVECTOR = "eigenvector"
    PAGERANK = "pagerank"

# Data models
@dataclass
class Node:
    id: str
    node_type: NodeType
    properties: Dict[str, Any]
    labels: List[str]
    created_at: str
    updated_at: str

@dataclass
class Relationship:
    id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    properties: Dict[str, Any]
    strength: float
    created_at: str
    updated_at: str

@dataclass
class GraphPath:
    id: str
    start_node_id: str
    end_node_id: str
    path_length: int
    nodes: List[str]
    relationships: List[str]
    total_weight: float
    path_properties: Dict[str, Any]

@dataclass
class CentralityResult:
    node_id: str
    centrality_type: CentralityType
    score: float
    rank: int
    percentile: float

@dataclass
class Community:
    id: str
    algorithm: str
    nodes: List[str]
    size: int
    modularity: float
    internal_edges: int
    external_edges: int
    cohesion_score: float

@dataclass
class GraphInsight:
    id: str
    insight_type: str
    title: str
    description: str
    affected_nodes: List[str]
    key_relationships: List[str]
    metrics: Dict[str, Any]
    recommendations: List[str]
    confidence: float
    created_at: str

class NodeRequest(BaseModel):
    node_type: NodeType = Field(..., description="Type of node")
    properties: Dict[str, Any] = Field(..., description="Node properties")
    labels: List[str] = Field(default_factory=list, description="Additional labels")

class RelationshipRequest(BaseModel):
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    relationship_type: RelationshipType = Field(..., description="Relationship type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relationship properties")
    strength: float = Field(1.0, description="Relationship strength")

class CypherQuery(BaseModel):
    query: str = Field(..., description="Cypher query string")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    limit: int = Field(100, description="Result limit")

class PathQuery(BaseModel):
    start_node_id: str = Field(..., description="Start node ID")
    end_node_id: str = Field(..., description="End node ID")
    max_depth: int = Field(5, description="Maximum path depth")
    relationship_types: List[RelationshipType] = Field(default_factory=list, description="Allowed relationship types")

class NeighborQuery(BaseModel):
    node_id: str = Field(..., description="Central node ID")
    depth: int = Field(1, description="Neighbor depth")
    relationship_types: List[RelationshipType] = Field(default_factory=list, description="Relationship types to follow")
    limit: int = Field(50, description="Maximum neighbors to return")

class CentralityQuery(BaseModel):
    centrality_type: CentralityType = Field(..., description="Type of centrality to calculate")
    node_filter: Dict[str, Any] = Field(default_factory=dict, description="Node filter criteria")
    relationship_filter: Dict[str, Any] = Field(default_factory=dict, description="Relationship filter criteria")
    limit: int = Field(20, description="Top N results")

class Neo4jIntelligenceService:
    def __init__(self):
        # Graph storage (mock Neo4j-like structure)
        self.nodes: Dict[str, Node] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.node_relationships: Dict[str, List[str]] = defaultdict(list)  # node_id -> relationship_ids
        self.communities: Dict[str, Community] = {}
        self.graph_insights: Dict[str, GraphInsight] = {}
        self.centrality_cache: Dict[str, List[CentralityResult]] = {}
        self.connected_clients: List[WebSocket] = []
        self.analysis_engine_active = False
        
    async def initialize(self):
        """Initialize the Neo4j intelligence service"""
        # Start analysis engines
        asyncio.create_task(self._graph_analysis_engine())
        asyncio.create_task(self._community_detection_engine())
        asyncio.create_task(self._influence_analyzer())
        
        # Load sample graph data
        await self._create_sample_graph()
        
        logger.info("Neo4j Intelligence Service initialized")

    async def _create_sample_graph(self):
        """Create sample graph data for demonstration"""
        # Create symbol nodes
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
        symbol_nodes = {}
        
        for symbol in symbols:
            node_id = await self._create_node(
                NodeType.SYMBOL,
                {
                    "symbol": symbol,
                    "name": f"{symbol} Inc.",
                    "sector": np.random.choice(['Technology', 'Consumer', 'Energy', 'Healthcare']),
                    "market_cap": np.random.uniform(100e9, 3000e9),
                    "price": np.random.uniform(50, 400),
                    "volume": np.random.uniform(1e6, 100e6)
                },
                ["Stock", "PublicCompany"]
            )
            symbol_nodes[symbol] = node_id
        
        # Create agent nodes
        agents = []
        for i in range(5):
            agent_id = await self._create_node(
                NodeType.AGENT,
                {
                    "agent_id": f"agent_{i:03d}",
                    "name": f"Trading Agent {i+1}",
                    "strategy_type": np.random.choice(['momentum', 'mean_reversion', 'arbitrage', 'ml_based']),
                    "risk_level": np.random.choice(['low', 'medium', 'high']),
                    "aum": np.random.uniform(1e6, 100e6),
                    "success_rate": np.random.uniform(0.5, 0.8)
                },
                ["TradingAgent", "AI"]
            )
            agents.append(agent_id)
        
        # Create portfolio nodes
        portfolios = []
        for i in range(3):
            portfolio_id = await self._create_node(
                NodeType.PORTFOLIO,
                {
                    "portfolio_id": f"portfolio_{i:03d}",
                    "name": f"Growth Portfolio {i+1}",
                    "strategy": np.random.choice(['growth', 'value', 'balanced', 'aggressive']),
                    "total_value": np.random.uniform(1e6, 50e6),
                    "risk_score": np.random.uniform(0.2, 0.8),
                    "sharpe_ratio": np.random.uniform(0.5, 2.0)
                },
                ["Portfolio", "Investment"]
            )
            portfolios.append(portfolio_id)
        
        # Create sector nodes
        sectors = ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer']
        sector_nodes = {}
        for sector in sectors:
            node_id = await self._create_node(
                NodeType.SECTOR,
                {
                    "name": sector,
                    "market_cap": np.random.uniform(500e9, 5000e9),
                    "volatility": np.random.uniform(0.15, 0.4),
                    "growth_rate": np.random.uniform(-0.1, 0.3)
                },
                ["Sector", "MarketSegment"]
            )
            sector_nodes[sector] = node_id
        
        # Create relationships
        
        # Agent TRADES Symbol relationships
        for agent_id in agents:
            traded_symbols = np.random.choice(symbols, size=np.random.randint(3, 6), replace=False)
            for symbol in traded_symbols:
                await self._create_relationship(
                    agent_id,
                    symbol_nodes[symbol],
                    RelationshipType.TRADES,
                    {
                        "frequency": np.random.uniform(0.1, 10.0),  # trades per day
                        "avg_volume": np.random.uniform(100, 10000),
                        "success_rate": np.random.uniform(0.4, 0.8),
                        "total_pnl": np.random.uniform(-50000, 200000)
                    },
                    np.random.uniform(0.3, 1.0)
                )
        
        # Portfolio OWNS Symbol relationships
        for portfolio_id in portfolios:
            owned_symbols = np.random.choice(symbols, size=np.random.randint(4, 7), replace=False)
            for symbol in owned_symbols:
                await self._create_relationship(
                    portfolio_id,
                    symbol_nodes[symbol],
                    RelationshipType.OWNS,
                    {
                        "quantity": np.random.uniform(100, 10000),
                        "weight": np.random.uniform(0.05, 0.25),  # portfolio weight
                        "cost_basis": np.random.uniform(50, 400),
                        "unrealized_pnl": np.random.uniform(-10000, 50000)
                    },
                    np.random.uniform(0.1, 0.3)
                )
        
        # Agent MANAGES Portfolio relationships
        for i, portfolio_id in enumerate(portfolios):
            managing_agent = agents[i % len(agents)]
            await self._create_relationship(
                managing_agent,
                portfolio_id,
                RelationshipType.MANAGES,
                {
                    "start_date": "2024-01-01",
                    "performance_fee": np.random.uniform(0.1, 0.3),
                    "management_fee": np.random.uniform(0.01, 0.02)
                },
                1.0
            )
        
        # Symbol BELONGS_TO Sector relationships
        for symbol in symbols:
            symbol_data = self.nodes[symbol_nodes[symbol]].properties
            sector = symbol_data['sector']
            if sector in sector_nodes:
                await self._create_relationship(
                    symbol_nodes[symbol],
                    sector_nodes[sector],
                    RelationshipType.BELONGS_TO,
                    {"classification_date": "2024-01-01"},
                    1.0
                )
        
        # Symbol CORRELATES_WITH Symbol relationships (based on sector similarity)
        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i+1:]:
                symbol1_data = self.nodes[symbol_nodes[symbol1]].properties
                symbol2_data = self.nodes[symbol_nodes[symbol2]].properties
                
                # Higher correlation for same sector
                if symbol1_data['sector'] == symbol2_data['sector']:
                    correlation = np.random.uniform(0.6, 0.9)
                else:
                    correlation = np.random.uniform(-0.3, 0.6)
                
                if abs(correlation) > 0.3:  # Only create relationship if significant
                    await self._create_relationship(
                        symbol_nodes[symbol1],
                        symbol_nodes[symbol2],
                        RelationshipType.CORRELATES_WITH,
                        {
                            "correlation": correlation,
                            "period_days": 252,
                            "confidence": np.random.uniform(0.7, 0.95)
                        },
                        abs(correlation)
                    )
        
        # Create some news nodes and relationships
        news_topics = [
            "Federal Reserve Interest Rate Decision",
            "Quarterly Earnings Reports",
            "AI Technology Breakthrough",
            "Supply Chain Disruption",
            "Regulatory Changes"
        ]
        
        for i, topic in enumerate(news_topics):
            news_id = await self._create_node(
                NodeType.NEWS,
                {
                    "title": topic,
                    "sentiment": np.random.uniform(-1, 1),
                    "impact_score": np.random.uniform(0.1, 1.0),
                    "published_at": (datetime.now() - timedelta(days=np.random.randint(0, 30))).isoformat(),
                    "source": "Financial News Network"
                },
                ["News", "MarketEvent"]
            )
            
            # News INFLUENCES Symbol relationships
            affected_symbols = np.random.choice(symbols, size=np.random.randint(2, 5), replace=False)
            for symbol in affected_symbols:
                await self._create_relationship(
                    news_id,
                    symbol_nodes[symbol],
                    RelationshipType.INFLUENCES,
                    {
                        "impact_magnitude": np.random.uniform(0.1, 0.5),
                        "sentiment_effect": np.random.uniform(-0.3, 0.3),
                        "duration_hours": np.random.uniform(1, 72)
                    },
                    np.random.uniform(0.2, 0.8)
                )

    async def _create_node(self, node_type: NodeType, properties: Dict[str, Any], 
                          labels: List[str] = None) -> str:
        """Create a new node in the graph"""
        node_id = str(uuid.uuid4())
        
        node = Node(
            id=node_id,
            node_type=node_type,
            properties=properties,
            labels=labels or [],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.nodes[node_id] = node
        return node_id

    async def _create_relationship(self, source_id: str, target_id: str, 
                                  relationship_type: RelationshipType,
                                  properties: Dict[str, Any] = None,
                                  strength: float = 1.0) -> str:
        """Create a new relationship in the graph"""
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("Source or target node does not exist")
        
        relationship_id = str(uuid.uuid4())
        
        relationship = Relationship(
            id=relationship_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            properties=properties or {},
            strength=strength,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.relationships[relationship_id] = relationship
        
        # Update adjacency lists
        self.node_relationships[source_id].append(relationship_id)
        self.node_relationships[target_id].append(relationship_id)
        
        return relationship_id

    async def _graph_analysis_engine(self):
        """Analyze graph structure and generate insights"""
        self.analysis_engine_active = True
        
        while self.analysis_engine_active:
            try:
                # Calculate centrality measures
                await self._calculate_centralities()
                
                # Detect influential patterns
                await self._detect_influence_patterns()
                
                # Analyze graph evolution
                await self._analyze_graph_evolution()
                
                await asyncio.sleep(1800)  # Run every 30 minutes
                
            except Exception as e:
                logger.error(f"Error in graph analysis engine: {e}")
                await asyncio.sleep(3600)

    async def _calculate_centralities(self):
        """Calculate various centrality measures"""
        if len(self.nodes) < 3:
            return
        
        # Calculate degree centrality
        degree_centrality = {}
        for node_id in self.nodes:
            degree = len(self.node_relationships[node_id])
            degree_centrality[node_id] = degree
        
        # Normalize and rank
        max_degree = max(degree_centrality.values()) if degree_centrality else 1
        results = []
        
        for i, (node_id, degree) in enumerate(sorted(degree_centrality.items(), 
                                                    key=lambda x: x[1], reverse=True)):
            normalized_score = degree / max_degree
            percentile = (len(degree_centrality) - i) / len(degree_centrality)
            
            result = CentralityResult(
                node_id=node_id,
                centrality_type=CentralityType.DEGREE,
                score=normalized_score,
                rank=i + 1,
                percentile=percentile
            )
            results.append(result)
        
        self.centrality_cache[CentralityType.DEGREE.value] = results
        
        # Simple PageRank simulation
        pagerank_scores = {}
        damping_factor = 0.85
        iterations = 10
        
        # Initialize scores
        initial_score = 1.0 / len(self.nodes)
        for node_id in self.nodes:
            pagerank_scores[node_id] = initial_score
        
        # Iterate
        for _ in range(iterations):
            new_scores = {}
            for node_id in self.nodes:
                score = (1 - damping_factor) / len(self.nodes)
                
                # Add contributions from incoming relationships
                for rel_id in self.node_relationships[node_id]:
                    rel = self.relationships[rel_id]
                    if rel.target_id == node_id:  # Incoming relationship
                        source_degree = len(self.node_relationships[rel.source_id])
                        if source_degree > 0:
                            score += damping_factor * pagerank_scores[rel.source_id] / source_degree
                
                new_scores[node_id] = score
            
            pagerank_scores = new_scores
        
        # Convert to centrality results
        pagerank_results = []
        for i, (node_id, score) in enumerate(sorted(pagerank_scores.items(), 
                                                   key=lambda x: x[1], reverse=True)):
            percentile = (len(pagerank_scores) - i) / len(pagerank_scores)
            
            result = CentralityResult(
                node_id=node_id,
                centrality_type=CentralityType.PAGERANK,
                score=score,
                rank=i + 1,
                percentile=percentile
            )
            pagerank_results.append(result)
        
        self.centrality_cache[CentralityType.PAGERANK.value] = pagerank_results

    async def _detect_influence_patterns(self):
        """Detect influential nodes and patterns"""
        # Find highly connected nodes
        degree_results = self.centrality_cache.get(CentralityType.DEGREE.value, [])
        if not degree_results:
            return
        
        # Top 10% of nodes by degree centrality
        threshold_rank = max(1, len(degree_results) * 0.1)
        influential_nodes = [r.node_id for r in degree_results[:int(threshold_rank)]]
        
        if influential_nodes:
            # Analyze influence patterns
            influence_types = defaultdict(list)
            
            for node_id in influential_nodes:
                node = self.nodes[node_id]
                influence_types[node.node_type.value].append(node_id)
            
            # Generate insight for most influential node type
            if influence_types:
                dominant_type = max(influence_types.items(), key=lambda x: len(x[1]))
                
                insight = GraphInsight(
                    id=str(uuid.uuid4()),
                    insight_type="influence_analysis",
                    title=f"Dominant Influence: {dominant_type[0].title()} Nodes",
                    description=f"{len(dominant_type[1])} {dominant_type[0]} nodes are among the most influential in the network",
                    affected_nodes=dominant_type[1],
                    key_relationships=[],
                    metrics={
                        "influential_node_count": len(influential_nodes),
                        "dominant_type": dominant_type[0],
                        "dominance_ratio": len(dominant_type[1]) / len(influential_nodes)
                    },
                    recommendations=[
                        f"Monitor {dominant_type[0]} nodes for market impact",
                        "Consider influence in risk management",
                        "Track relationship changes for these nodes"
                    ],
                    confidence=0.8,
                    created_at=datetime.now().isoformat()
                )
                
                self.graph_insights[insight.id] = insight
                await self._notify_graph_insight(insight)

    async def _analyze_graph_evolution(self):
        """Analyze how the graph structure evolves"""
        # Simple analysis based on recent relationship creation
        recent_threshold = datetime.now() - timedelta(hours=24)
        recent_relationships = []
        
        for rel in self.relationships.values():
            rel_time = datetime.fromisoformat(rel.created_at.replace('Z', '+00:00').replace('+00:00', ''))
            if rel_time > recent_threshold:
                recent_relationships.append(rel)
        
        if len(recent_relationships) > 5:
            # Analyze relationship types
            rel_type_counts = defaultdict(int)
            for rel in recent_relationships:
                rel_type_counts[rel.relationship_type.value] += 1
            
            most_common_type = max(rel_type_counts.items(), key=lambda x: x[1])
            
            insight = GraphInsight(
                id=str(uuid.uuid4()),
                insight_type="graph_evolution",
                title="Network Growth Pattern Detected",
                description=f"Recent network activity shows {len(recent_relationships)} new relationships",
                affected_nodes=[],
                key_relationships=[rel.id for rel in recent_relationships],
                metrics={
                    "new_relationships_24h": len(recent_relationships),
                    "dominant_relationship_type": most_common_type[0],
                    "growth_rate": len(recent_relationships) / 24  # per hour
                },
                recommendations=[
                    "Monitor rapid relationship formation",
                    "Analyze pattern sustainability",
                    "Consider network density implications"
                ],
                confidence=0.7,
                created_at=datetime.now().isoformat()
            )
            
            self.graph_insights[insight.id] = insight

    async def _community_detection_engine(self):
        """Detect communities in the graph"""
        while True:
            try:
                if len(self.nodes) >= 5:
                    await self._detect_communities()
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in community detection: {e}")
                await asyncio.sleep(1800)

    async def _detect_communities(self):
        """Simple community detection algorithm"""
        # Simple label propagation algorithm simulation
        node_ids = list(self.nodes.keys())
        labels = {node_id: i for i, node_id in enumerate(node_ids)}
        
        # Iterate to propagate labels
        iterations = 10
        for _ in range(iterations):
            new_labels = labels.copy()
            
            for node_id in node_ids:
                # Get neighbor labels
                neighbor_labels = []
                for rel_id in self.node_relationships[node_id]:
                    rel = self.relationships[rel_id]
                    neighbor_id = rel.target_id if rel.source_id == node_id else rel.source_id
                    neighbor_labels.append(labels[neighbor_id])
                
                # Assign most common neighbor label
                if neighbor_labels:
                    label_counts = defaultdict(int)
                    for label in neighbor_labels:
                        label_counts[label] += 1
                    new_labels[node_id] = max(label_counts.items(), key=lambda x: x[1])[0]
            
            labels = new_labels
        
        # Group nodes by community
        communities = defaultdict(list)
        for node_id, label in labels.items():
            communities[label].append(node_id)
        
        # Create community objects
        for i, (label, node_list) in enumerate(communities.items()):
            if len(node_list) >= 2:  # Only communities with 2+ nodes
                # Calculate internal vs external edges
                internal_edges = 0
                external_edges = 0
                
                for node_id in node_list:
                    for rel_id in self.node_relationships[node_id]:
                        rel = self.relationships[rel_id]
                        other_node = rel.target_id if rel.source_id == node_id else rel.source_id
                        
                        if other_node in node_list:
                            internal_edges += 1
                        else:
                            external_edges += 1
                
                # Calculate modularity (simplified)
                total_edges = internal_edges + external_edges
                modularity = (internal_edges / total_edges) if total_edges > 0 else 0
                
                community = Community(
                    id=str(uuid.uuid4()),
                    algorithm="label_propagation",
                    nodes=node_list,
                    size=len(node_list),
                    modularity=modularity,
                    internal_edges=internal_edges // 2,  # Each edge counted twice
                    external_edges=external_edges,
                    cohesion_score=modularity
                )
                
                self.communities[community.id] = community

    async def _influence_analyzer(self):
        """Analyze influence propagation in the network"""
        while True:
            try:
                await self._analyze_influence_cascades()
                
                await asyncio.sleep(2700)  # Run every 45 minutes
                
            except Exception as e:
                logger.error(f"Error in influence analyzer: {e}")
                await asyncio.sleep(3600)

    async def _analyze_influence_cascades(self):
        """Analyze how influence spreads through the network"""
        # Find nodes with high influence relationships
        high_influence_rels = [
            rel for rel in self.relationships.values()
            if rel.relationship_type == RelationshipType.INFLUENCES and rel.strength > 0.5
        ]
        
        if len(high_influence_rels) >= 3:
            # Analyze influence patterns
            influence_sources = defaultdict(int)
            influence_targets = defaultdict(int)
            
            for rel in high_influence_rels:
                influence_sources[rel.source_id] += 1
                influence_targets[rel.target_id] += 1
            
            # Find top influencers and influenced
            top_influencer = max(influence_sources.items(), key=lambda x: x[1]) if influence_sources else None
            most_influenced = max(influence_targets.items(), key=lambda x: x[1]) if influence_targets else None
            
            if top_influencer and most_influenced:
                insight = GraphInsight(
                    id=str(uuid.uuid4()),
                    insight_type="influence_cascade",
                    title="Influence Network Analysis",
                    description="Analysis of influence relationships in the network",
                    affected_nodes=[top_influencer[0], most_influenced[0]],
                    key_relationships=[rel.id for rel in high_influence_rels],
                    metrics={
                        "high_influence_relationships": len(high_influence_rels),
                        "top_influencer_connections": top_influencer[1],
                        "most_influenced_connections": most_influenced[1]
                    },
                    recommendations=[
                        "Monitor top influencer for market impact",
                        "Track influence cascade effects",
                        "Consider influence in decision making"
                    ],
                    confidence=0.85,
                    created_at=datetime.now().isoformat()
                )
                
                self.graph_insights[insight.id] = insight
                await self._notify_graph_insight(insight)

    async def create_node(self, request: NodeRequest) -> str:
        """Create a new node"""
        try:
            node_id = await self._create_node(
                request.node_type,
                request.properties,
                request.labels
            )
            
            await self._notify_node_created(node_id)
            return node_id
            
        except Exception as e:
            logger.error(f"Error creating node: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def create_relationship(self, request: RelationshipRequest) -> str:
        """Create a new relationship"""
        try:
            rel_id = await self._create_relationship(
                request.source_id,
                request.target_id,
                request.relationship_type,
                request.properties,
                request.strength
            )
            
            await self._notify_relationship_created(rel_id)
            return rel_id
            
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def execute_cypher_query(self, request: CypherQuery) -> Dict[str, Any]:
        """Execute a Cypher-like query (simplified)"""
        # This is a simplified implementation
        # In a real system, this would parse and execute actual Cypher
        
        query_lower = request.query.lower()
        results = []
        
        if "match" in query_lower:
            if "node" in query_lower or "symbol" in query_lower:
                # Return all nodes of specified type
                for node in self.nodes.values():
                    if request.limit and len(results) >= request.limit:
                        break
                    results.append({
                        "node": asdict(node),
                        "type": "node"
                    })
            
            if "relationship" in query_lower or "edge" in query_lower:
                # Return relationships
                for rel in self.relationships.values():
                    if request.limit and len(results) >= request.limit:
                        break
                    results.append({
                        "relationship": asdict(rel),
                        "type": "relationship"
                    })
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results),
            "execution_time_ms": np.random.uniform(10, 100)
        }

    async def find_shortest_path(self, request: PathQuery) -> List[GraphPath]:
        """Find shortest path between two nodes"""
        if request.start_node_id not in self.nodes or request.end_node_id not in self.nodes:
            raise HTTPException(status_code=404, detail="Start or end node not found")
        
        # Simple BFS implementation
        queue = deque([(request.start_node_id, [])])
        visited = {request.start_node_id}
        paths = []
        
        while queue and len(paths) < 5:  # Find up to 5 paths
            current_node, path = queue.popleft()
            
            if len(path) >= request.max_depth:
                continue
            
            # Explore neighbors
            for rel_id in self.node_relationships[current_node]:
                rel = self.relationships[rel_id]
                
                # Check relationship type filter
                if request.relationship_types and rel.relationship_type not in request.relationship_types:
                    continue
                
                neighbor = rel.target_id if rel.source_id == current_node else rel.source_id
                
                new_path = path + [rel_id]
                
                if neighbor == request.end_node_id:
                    # Found path
                    path_obj = GraphPath(
                        id=str(uuid.uuid4()),
                        start_node_id=request.start_node_id,
                        end_node_id=request.end_node_id,
                        path_length=len(new_path),
                        nodes=[request.start_node_id] + [rel.target_id if rel.source_id == current_node else rel.source_id for rel in [self.relationships[rid] for rid in new_path]],
                        relationships=new_path,
                        total_weight=sum(self.relationships[rid].strength for rid in new_path),
                        path_properties={}
                    )
                    paths.append(path_obj)
                elif neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, new_path))
        
        return paths

    async def get_neighbors(self, request: NeighborQuery) -> List[Node]:
        """Get neighbors of a node"""
        if request.node_id not in self.nodes:
            raise HTTPException(status_code=404, detail="Node not found")
        
        neighbors = set()
        current_level = {request.node_id}
        
        for depth in range(request.depth):
            next_level = set()
            
            for node_id in current_level:
                for rel_id in self.node_relationships[node_id]:
                    rel = self.relationships[rel_id]
                    
                    # Check relationship type filter
                    if request.relationship_types and rel.relationship_type not in request.relationship_types:
                        continue
                    
                    neighbor = rel.target_id if rel.source_id == node_id else rel.source_id
                    
                    if neighbor != request.node_id:  # Don't include the original node
                        neighbors.add(neighbor)
                        next_level.add(neighbor)
            
            current_level = next_level
            
            if not current_level:
                break
        
        # Convert to Node objects and apply limit
        neighbor_nodes = [self.nodes[node_id] for node_id in neighbors if node_id in self.nodes]
        return neighbor_nodes[:request.limit]

    async def calculate_centrality(self, request: CentralityQuery) -> List[CentralityResult]:
        """Calculate centrality measures"""
        cached_results = self.centrality_cache.get(request.centrality_type.value, [])
        
        if cached_results:
            # Apply filters and limits
            filtered_results = cached_results
            
            if request.node_filter:
                # Simple filtering by node properties
                filtered_results = []
                for result in cached_results:
                    node = self.nodes.get(result.node_id)
                    if node and self._node_matches_filter(node, request.node_filter):
                        filtered_results.append(result)
            
            return filtered_results[:request.limit]
        
        return []

    def _node_matches_filter(self, node: Node, filters: Dict[str, Any]) -> bool:
        """Check if node matches filter criteria"""
        for key, value in filters.items():
            if key in node.properties:
                if node.properties[key] != value:
                    return False
            elif key == "node_type":
                if node.node_type.value != value:
                    return False
        return True

    async def get_communities(self) -> List[Community]:
        """Get detected communities"""
        return list(self.communities.values())

    async def get_graph_insights(self, insight_type: Optional[str] = None) -> List[GraphInsight]:
        """Get graph insights with optional filtering"""
        insights = list(self.graph_insights.values())
        
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]
        
        # Sort by creation time (newest first)
        insights.sort(key=lambda x: x.created_at, reverse=True)
        
        return insights

    async def _notify_node_created(self, node_id: str):
        """Notify clients of node creation"""
        message = {
            "type": "node_created",
            "node_id": node_id,
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

    async def _notify_relationship_created(self, rel_id: str):
        """Notify clients of relationship creation"""
        message = {
            "type": "relationship_created",
            "relationship_id": rel_id,
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

    async def _notify_graph_insight(self, insight: GraphInsight):
        """Notify clients of graph insights"""
        message = {
            "type": "graph_insight",
            "insight": asdict(insight),
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

# Initialize service
neo4j_service = Neo4jIntelligenceService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await neo4j_service.initialize()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Neo4j Intelligence MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "graph_operations",
            "relationship_analysis",
            "centrality_measures",
            "community_detection",
            "path_finding"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    return {
        "cpu_usage": 29.6,
        "memory_usage": 41.2,
        "disk_usage": 19.8,
        "network_in": 1792,
        "network_out": 3584,
        "active_connections": len(neo4j_service.connected_clients),
        "queue_length": 0,
        "errors_last_hour": 0,
        "requests_last_hour": 234,
        "response_time_p95": 89.0,
        "total_nodes": len(neo4j_service.nodes),
        "total_relationships": len(neo4j_service.relationships),
        "graph_density": len(neo4j_service.relationships) / max(1, len(neo4j_service.nodes) * (len(neo4j_service.nodes) - 1))
    }

@app.post("/nodes")
async def create_node(request: NodeRequest, token: str = Depends(get_current_user)):
    try:
        node_id = await neo4j_service.create_node(request)
        return {"node_id": node_id, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error creating node: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/relationships")
async def create_relationship(request: RelationshipRequest, token: str = Depends(get_current_user)):
    try:
        rel_id = await neo4j_service.create_relationship(request)
        return {"relationship_id": rel_id, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/cypher")
async def execute_cypher_query(request: CypherQuery, token: str = Depends(get_current_user)):
    try:
        result = await neo4j_service.execute_cypher_query(request)
        return {"result": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error executing Cypher query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/path")
async def find_shortest_path(request: PathQuery, token: str = Depends(get_current_user)):
    try:
        paths = await neo4j_service.find_shortest_path(request)
        return {
            "paths": [asdict(p) for p in paths],
            "count": len(paths),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error finding path: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/neighbors")
async def get_neighbors(request: NeighborQuery, token: str = Depends(get_current_user)):
    try:
        neighbors = await neo4j_service.get_neighbors(request)
        return {
            "neighbors": [asdict(n) for n in neighbors],
            "count": len(neighbors),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting neighbors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analysis/centrality")
async def calculate_centrality(request: CentralityQuery, token: str = Depends(get_current_user)):
    try:
        results = await neo4j_service.calculate_centrality(request)
        return {
            "centrality_results": [asdict(r) for r in results],
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error calculating centrality: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/communities")
async def get_communities(token: str = Depends(get_current_user)):
    try:
        communities = await neo4j_service.get_communities()
        return {
            "communities": [asdict(c) for c in communities],
            "count": len(communities),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting communities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/insights")
async def get_graph_insights(
    insight_type: Optional[str] = None,
    token: str = Depends(get_current_user)
):
    try:
        insights = await neo4j_service.get_graph_insights(insight_type)
        return {
            "insights": [asdict(i) for i in insights],
            "count": len(insights),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/stats")
async def get_graph_statistics(token: str = Depends(get_current_user)):
    node_type_counts = defaultdict(int)
    relationship_type_counts = defaultdict(int)
    
    for node in neo4j_service.nodes.values():
        node_type_counts[node.node_type.value] += 1
    
    for rel in neo4j_service.relationships.values():
        relationship_type_counts[rel.relationship_type.value] += 1
    
    return {
        "graph_statistics": {
            "total_nodes": len(neo4j_service.nodes),
            "total_relationships": len(neo4j_service.relationships),
            "node_types": dict(node_type_counts),
            "relationship_types": dict(relationship_type_counts),
            "density": len(neo4j_service.relationships) / max(1, len(neo4j_service.nodes) * (len(neo4j_service.nodes) - 1)),
            "average_degree": (2 * len(neo4j_service.relationships)) / max(1, len(neo4j_service.nodes))
        },
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/neo4j")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    neo4j_service.connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except:
        pass
    finally:
        if websocket in neo4j_service.connected_clients:
            neo4j_service.connected_clients.remove(websocket)

@app.get("/capabilities")
async def get_capabilities():
    return {
        "node_types": [nt.value for nt in NodeType],
        "relationship_types": [rt.value for rt in RelationshipType],
        "query_types": [qt.value for qt in QueryType],
        "centrality_types": [ct.value for ct in CentralityType],
        "capabilities": [
            {
                "name": "graph_operations",
                "description": "Create and manage nodes and relationships"
            },
            {
                "name": "cypher_queries",
                "description": "Execute graph queries using Cypher-like syntax"
            },
            {
                "name": "path_analysis",
                "description": "Find shortest paths and analyze connections"
            },
            {
                "name": "centrality_analysis",
                "description": "Calculate network centrality measures"
            },
            {
                "name": "community_detection",
                "description": "Identify communities and clusters in the graph"
            },
            {
                "name": "influence_analysis",
                "description": "Analyze influence propagation and network effects"
            }
        ],
        "algorithms": [
            "shortest_path", "centrality_calculation", "community_detection",
            "influence_analysis", "pattern_matching"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "neo4j_intelligence:app",
        host="0.0.0.0",
        port=8022,
        reload=True,
        log_level="info"
    )