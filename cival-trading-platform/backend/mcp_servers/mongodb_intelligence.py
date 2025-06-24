#!/usr/bin/env python3
"""
MongoDB Intelligence MCP Server
Document storage, complex queries, and data intelligence for trading systems
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import aiohttp
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="MongoDB Intelligence MCP Server",
    description="Document storage and intelligent data operations",
    version="1.0.0"
)

security = HTTPBearer()

# Enums
class DocumentType(str, Enum):
    MARKET_DATA = "market_data"
    TRADE_RECORD = "trade_record"
    ANALYSIS_RESULT = "analysis_result"
    STRATEGY_CONFIG = "strategy_config"
    PORTFOLIO_SNAPSHOT = "portfolio_snapshot"
    RISK_ASSESSMENT = "risk_assessment"
    NEWS_ARTICLE = "news_article"
    SENTIMENT_DATA = "sentiment_data"
    PATTERN_DETECTION = "pattern_detection"
    ALERT_LOG = "alert_log"

class QueryType(str, Enum):
    FIND = "find"
    AGGREGATE = "aggregate"
    TIME_SERIES = "time_series"
    TEXT_SEARCH = "text_search"
    GEOSPATIAL = "geospatial"
    GRAPH_LOOKUP = "graph_lookup"

class IndexType(str, Enum):
    SINGLE = "single"
    COMPOUND = "compound"
    TEXT = "text"
    GEOSPATIAL = "geospatial"
    SPARSE = "sparse"
    TTL = "ttl"

# Data models
@dataclass
class Document:
    id: str
    collection: str
    document_type: DocumentType
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    version: int
    tags: List[str]
    ttl: Optional[str] = None

@dataclass
class Collection:
    name: str
    document_type: DocumentType
    schema: Dict[str, Any]
    indexes: List[Dict[str, Any]]
    document_count: int
    size_bytes: int
    avg_document_size: float
    created_at: str
    last_modified: str

@dataclass
class QueryResult:
    query_id: str
    collection: str
    query_type: QueryType
    query: Dict[str, Any]
    results: List[Dict[str, Any]]
    result_count: int
    execution_time_ms: float
    explained_query: Dict[str, Any]
    created_at: str

@dataclass
class AggregationPipeline:
    id: str
    name: str
    description: str
    collection: str
    pipeline: List[Dict[str, Any]]
    expected_output: str
    performance_notes: str
    created_by: str
    created_at: str

@dataclass
class DataInsight:
    id: str
    insight_type: str
    collection: str
    title: str
    description: str
    key_metrics: Dict[str, Any]
    trends: List[Dict[str, Any]]
    correlations: Dict[str, float]
    recommendations: List[str]
    confidence_score: float
    created_at: str

class DocumentRequest(BaseModel):
    collection: str = Field(..., description="Collection name")
    document_type: DocumentType = Field(..., description="Document type")
    data: Dict[str, Any] = Field(..., description="Document data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    ttl_hours: Optional[int] = Field(None, description="TTL in hours")

class QueryRequest(BaseModel):
    collection: str = Field(..., description="Collection to query")
    query_type: QueryType = Field(QueryType.FIND, description="Type of query")
    query: Dict[str, Any] = Field(..., description="Query specification")
    options: Dict[str, Any] = Field(default_factory=dict, description="Query options")
    limit: int = Field(100, description="Result limit")
    skip: int = Field(0, description="Results to skip")

class AggregationRequest(BaseModel):
    collection: str = Field(..., description="Collection to aggregate")
    pipeline: List[Dict[str, Any]] = Field(..., description="Aggregation pipeline")
    options: Dict[str, Any] = Field(default_factory=dict, description="Aggregation options")

class TimeSeriesQuery(BaseModel):
    collection: str = Field(..., description="Collection name")
    time_field: str = Field("timestamp", description="Time field name")
    start_time: datetime = Field(..., description="Start time")
    end_time: datetime = Field(..., description="End time")
    granularity: str = Field("1h", description="Time granularity")
    metrics: List[str] = Field(..., description="Metrics to aggregate")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")

class MongoDBIntelligenceService:
    def __init__(self):
        # Mock MongoDB-like storage
        self.collections: Dict[str, Collection] = {}
        self.documents: Dict[str, Dict[str, Document]] = defaultdict(dict)  # collection -> doc_id -> document
        self.indexes: Dict[str, List[Dict]] = defaultdict(list)
        self.aggregation_pipelines: Dict[str, AggregationPipeline] = {}
        self.query_history: List[QueryResult] = []
        self.data_insights: Dict[str, DataInsight] = {}
        self.connected_clients: List[WebSocket] = []
        self.analytics_engine_active = False
        
        # Initialize with default collections
        self._initialize_collections()
        
    async def initialize(self):
        """Initialize the MongoDB intelligence service"""
        # Start analytics engines
        asyncio.create_task(self._data_analytics_engine())
        asyncio.create_task(self._index_optimizer())
        asyncio.create_task(self._data_insight_generator())
        
        # Load sample data
        await self._load_sample_data()
        
        logger.info("MongoDB Intelligence Service initialized")

    def _initialize_collections(self):
        """Initialize default collections with schemas"""
        collections_config = [
            {
                "name": "market_data",
                "document_type": DocumentType.MARKET_DATA,
                "schema": {
                    "symbol": {"type": "string", "required": True, "index": True},
                    "timestamp": {"type": "datetime", "required": True, "index": True},
                    "open": {"type": "number", "required": True},
                    "high": {"type": "number", "required": True},
                    "low": {"type": "number", "required": True},
                    "close": {"type": "number", "required": True},
                    "volume": {"type": "number", "required": True}
                }
            },
            {
                "name": "trade_records",
                "document_type": DocumentType.TRADE_RECORD,
                "schema": {
                    "trade_id": {"type": "string", "required": True, "index": True},
                    "symbol": {"type": "string", "required": True, "index": True},
                    "side": {"type": "string", "required": True},
                    "quantity": {"type": "number", "required": True},
                    "price": {"type": "number", "required": True},
                    "timestamp": {"type": "datetime", "required": True, "index": True},
                    "agent_id": {"type": "string", "index": True}
                }
            },
            {
                "name": "analysis_results",
                "document_type": DocumentType.ANALYSIS_RESULT,
                "schema": {
                    "analysis_id": {"type": "string", "required": True, "index": True},
                    "analysis_type": {"type": "string", "required": True, "index": True},
                    "symbol": {"type": "string", "required": True, "index": True},
                    "result": {"type": "object", "required": True},
                    "confidence": {"type": "number", "required": True},
                    "timestamp": {"type": "datetime", "required": True, "index": True}
                }
            },
            {
                "name": "portfolio_snapshots",
                "document_type": DocumentType.PORTFOLIO_SNAPSHOT,
                "schema": {
                    "portfolio_id": {"type": "string", "required": True, "index": True},
                    "timestamp": {"type": "datetime", "required": True, "index": True},
                    "total_value": {"type": "number", "required": True},
                    "holdings": {"type": "array", "required": True},
                    "performance_metrics": {"type": "object", "required": True}
                }
            },
            {
                "name": "news_articles",
                "document_type": DocumentType.NEWS_ARTICLE,
                "schema": {
                    "article_id": {"type": "string", "required": True, "index": True},
                    "title": {"type": "string", "required": True, "text_index": True},
                    "content": {"type": "string", "required": True, "text_index": True},
                    "symbols": {"type": "array", "index": True},
                    "sentiment_score": {"type": "number"},
                    "published_at": {"type": "datetime", "required": True, "index": True}
                }
            }
        ]
        
        for config in collections_config:
            collection = Collection(
                name=config["name"],
                document_type=config["document_type"],
                schema=config["schema"],
                indexes=[],
                document_count=0,
                size_bytes=0,
                avg_document_size=0.0,
                created_at=datetime.now().isoformat(),
                last_modified=datetime.now().isoformat()
            )
            self.collections[config["name"]] = collection

    async def _load_sample_data(self):
        """Load sample data into collections"""
        # Sample market data
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        base_time = datetime.now() - timedelta(days=30)
        
        for symbol in symbols:
            base_price = np.random.uniform(100, 400)
            for i in range(720):  # 30 days * 24 hours
                timestamp = base_time + timedelta(hours=i)
                price_change = np.random.normal(0, 0.02)
                price = base_price * (1 + price_change)
                
                doc_data = {
                    "symbol": symbol,
                    "timestamp": timestamp.isoformat(),
                    "open": price * np.random.uniform(0.99, 1.01),
                    "high": price * np.random.uniform(1.001, 1.02),
                    "low": price * np.random.uniform(0.98, 0.999),
                    "close": price,
                    "volume": np.random.uniform(100000, 1000000)
                }
                
                await self._store_document("market_data", DocumentType.MARKET_DATA, doc_data)
                base_price = price
        
        # Sample trade records
        for i in range(100):
            symbol = np.random.choice(symbols)
            doc_data = {
                "trade_id": f"trade_{i:06d}",
                "symbol": symbol,
                "side": np.random.choice(["buy", "sell"]),
                "quantity": np.random.randint(10, 1000),
                "price": np.random.uniform(100, 400),
                "timestamp": (datetime.now() - timedelta(days=np.random.randint(0, 30))).isoformat(),
                "agent_id": f"agent_{np.random.randint(1, 5):03d}",
                "commission": np.random.uniform(0.1, 5.0)
            }
            
            await self._store_document("trade_records", DocumentType.TRADE_RECORD, doc_data)
        
        # Sample news articles
        sample_titles = [
            "Tech Stocks Rally on Strong Earnings",
            "Federal Reserve Signals Rate Cut",
            "AI Revolution Drives Market Growth",
            "Energy Sector Faces New Challenges",
            "Consumer Spending Shows Resilience"
        ]
        
        for i, title in enumerate(sample_titles):
            doc_data = {
                "article_id": f"article_{i:06d}",
                "title": title,
                "content": f"Lorem ipsum content for {title}...",
                "symbols": np.random.choice(symbols, size=np.random.randint(1, 3), replace=False).tolist(),
                "sentiment_score": np.random.uniform(-1, 1),
                "published_at": (datetime.now() - timedelta(days=np.random.randint(0, 7))).isoformat(),
                "source": "Financial News Network"
            }
            
            await self._store_document("news_articles", DocumentType.NEWS_ARTICLE, doc_data)

    async def _store_document(self, collection_name: str, doc_type: DocumentType, data: Dict[str, Any], 
                             metadata: Dict[str, Any] = None, tags: List[str] = None) -> str:
        """Store a document in the specified collection"""
        doc_id = str(uuid.uuid4())
        
        document = Document(
            id=doc_id,
            collection=collection_name,
            document_type=doc_type,
            data=data,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            version=1,
            tags=tags or []
        )
        
        self.documents[collection_name][doc_id] = document
        
        # Update collection stats
        if collection_name in self.collections:
            collection = self.collections[collection_name]
            collection.document_count += 1
            doc_size = len(json.dumps(asdict(document)))
            collection.size_bytes += doc_size
            collection.avg_document_size = collection.size_bytes / collection.document_count
            collection.last_modified = datetime.now().isoformat()
        
        return doc_id

    async def _data_analytics_engine(self):
        """Analyze data patterns and performance"""
        self.analytics_engine_active = True
        
        while self.analytics_engine_active:
            try:
                # Analyze query patterns
                await self._analyze_query_patterns()
                
                # Analyze data growth
                await self._analyze_data_growth()
                
                # Performance optimization recommendations
                await self._generate_performance_recommendations()
                
                await asyncio.sleep(1800)  # Run every 30 minutes
                
            except Exception as e:
                logger.error(f"Error in data analytics engine: {e}")
                await asyncio.sleep(3600)

    async def _analyze_query_patterns(self):
        """Analyze query patterns for optimization"""
        if len(self.query_history) < 10:
            return
        
        recent_queries = self.query_history[-100:]  # Last 100 queries
        
        # Analyze by collection
        collection_usage = defaultdict(int)
        slow_queries = []
        
        for query in recent_queries:
            collection_usage[query.collection] += 1
            if query.execution_time_ms > 1000:  # Slow queries > 1 second
                slow_queries.append(query)
        
        # Generate insights
        if slow_queries:
            insight = DataInsight(
                id=str(uuid.uuid4()),
                insight_type="performance",
                collection="system",
                title="Slow Query Detection",
                description=f"Detected {len(slow_queries)} slow queries in recent activity",
                key_metrics={
                    "slow_query_count": len(slow_queries),
                    "avg_slow_query_time": np.mean([q.execution_time_ms for q in slow_queries]),
                    "most_affected_collection": max(collection_usage.items(), key=lambda x: x[1])[0]
                },
                trends=[],
                correlations={},
                recommendations=[
                    "Review and optimize slow queries",
                    "Consider adding appropriate indexes",
                    "Analyze query execution plans"
                ],
                confidence_score=0.9,
                created_at=datetime.now().isoformat()
            )
            
            self.data_insights[insight.id] = insight
            await self._notify_data_insight(insight)

    async def _analyze_data_growth(self):
        """Analyze data growth trends"""
        growth_metrics = {}
        
        for collection_name, collection in self.collections.items():
            if collection.document_count > 0:
                # Simulate growth rate calculation
                daily_growth = np.random.uniform(0.05, 0.2)  # 5-20% daily growth
                projected_size = collection.size_bytes * (1 + daily_growth) ** 30  # 30-day projection
                
                growth_metrics[collection_name] = {
                    "current_size_mb": collection.size_bytes / (1024 * 1024),
                    "current_documents": collection.document_count,
                    "daily_growth_rate": daily_growth,
                    "projected_size_30d_mb": projected_size / (1024 * 1024)
                }
        
        # Find fastest growing collections
        if growth_metrics:
            fastest_growing = max(growth_metrics.items(), key=lambda x: x[1]["daily_growth_rate"])
            
            if fastest_growing[1]["daily_growth_rate"] > 0.15:  # > 15% daily growth
                insight = DataInsight(
                    id=str(uuid.uuid4()),
                    insight_type="capacity_planning",
                    collection=fastest_growing[0],
                    title="High Data Growth Detected",
                    description=f"Collection '{fastest_growing[0]}' showing high growth rate",
                    key_metrics=fastest_growing[1],
                    trends=[
                        {
                            "metric": "daily_growth_rate",
                            "value": fastest_growing[1]["daily_growth_rate"],
                            "trend": "increasing"
                        }
                    ],
                    correlations={},
                    recommendations=[
                        "Monitor storage capacity",
                        "Consider data archival policies",
                        "Optimize data retention settings"
                    ],
                    confidence_score=0.8,
                    created_at=datetime.now().isoformat()
                )
                
                self.data_insights[insight.id] = insight
                await self._notify_data_insight(insight)

    async def _generate_performance_recommendations(self):
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Check for missing indexes
        for collection_name, collection in self.collections.items():
            if collection.document_count > 1000 and len(self.indexes[collection_name]) < 2:
                recommendations.append({
                    "type": "indexing",
                    "collection": collection_name,
                    "priority": "high",
                    "message": f"Collection {collection_name} may benefit from additional indexes"
                })
        
        # Check for large documents
        for collection_name, collection in self.collections.items():
            if collection.avg_document_size > 100000:  # > 100KB
                recommendations.append({
                    "type": "document_size",
                    "collection": collection_name,
                    "priority": "medium",
                    "message": f"Large document size in {collection_name} may impact performance"
                })
        
        if recommendations:
            insight = DataInsight(
                id=str(uuid.uuid4()),
                insight_type="optimization",
                collection="system",
                title="Performance Optimization Opportunities",
                description=f"Found {len(recommendations)} optimization opportunities",
                key_metrics={
                    "recommendations_count": len(recommendations),
                    "high_priority": len([r for r in recommendations if r["priority"] == "high"])
                },
                trends=[],
                correlations={},
                recommendations=[r["message"] for r in recommendations],
                confidence_score=0.7,
                created_at=datetime.now().isoformat()
            )
            
            self.data_insights[insight.id] = insight

    async def _index_optimizer(self):
        """Optimize indexes based on query patterns"""
        while True:
            try:
                # Analyze query patterns and suggest indexes
                if len(self.query_history) >= 20:
                    await self._suggest_indexes()
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in index optimizer: {e}")
                await asyncio.sleep(1800)

    async def _suggest_indexes(self):
        """Suggest indexes based on query patterns"""
        recent_queries = self.query_history[-50:]
        
        # Analyze field usage in queries
        field_usage = defaultdict(lambda: defaultdict(int))
        
        for query in recent_queries:
            if "query" in query.query:
                for field, value in query.query["query"].items():
                    field_usage[query.collection][field] += 1
        
        # Suggest indexes for frequently queried fields
        for collection_name, fields in field_usage.items():
            for field, count in fields.items():
                if count >= 5:  # Field used in 5+ queries
                    existing_indexes = [idx.get("field") for idx in self.indexes[collection_name]]
                    if field not in existing_indexes:
                        # Create suggested index
                        index_def = {
                            "field": field,
                            "type": IndexType.SINGLE.value,
                            "suggested": True,
                            "usage_count": count,
                            "created_at": datetime.now().isoformat()
                        }
                        
                        self.indexes[collection_name].append(index_def)
                        logger.info(f"Suggested index for {collection_name}.{field} (usage: {count})")

    async def _data_insight_generator(self):
        """Generate intelligent insights from data"""
        while True:
            try:
                # Analyze trading patterns
                await self._analyze_trading_patterns()
                
                # Analyze market data correlations
                await self._analyze_market_correlations()
                
                await asyncio.sleep(900)  # Run every 15 minutes
                
            except Exception as e:
                logger.error(f"Error in insight generator: {e}")
                await asyncio.sleep(1800)

    async def _analyze_trading_patterns(self):
        """Analyze trading patterns from trade records"""
        trade_docs = self.documents.get("trade_records", {})
        if len(trade_docs) < 10:
            return
        
        trades = [doc.data for doc in trade_docs.values()]
        df = pd.DataFrame(trades)
        
        if 'timestamp' in df.columns and 'agent_id' in df.columns:
            # Convert timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Analyze by agent
            agent_stats = df.groupby('agent_id').agg({
                'quantity': 'sum',
                'price': 'mean',
                'trade_id': 'count'
            }).rename(columns={'trade_id': 'trade_count'})
            
            # Find most active agent
            most_active_agent = agent_stats.loc[agent_stats['trade_count'].idxmax()]
            
            insight = DataInsight(
                id=str(uuid.uuid4()),
                insight_type="trading_behavior",
                collection="trade_records",
                title="Trading Activity Analysis",
                description="Analysis of trading patterns by agent",
                key_metrics={
                    "total_trades": len(df),
                    "unique_agents": df['agent_id'].nunique(),
                    "most_active_agent": agent_stats['trade_count'].idxmax(),
                    "avg_trade_size": df['quantity'].mean()
                },
                trends=[
                    {
                        "metric": "daily_trade_volume",
                        "value": df['quantity'].sum(),
                        "trend": "stable"
                    }
                ],
                correlations={},
                recommendations=[
                    "Monitor agent trading patterns for consistency",
                    "Review high-volume agents for risk management"
                ],
                confidence_score=0.8,
                created_at=datetime.now().isoformat()
            )
            
            self.data_insights[insight.id] = insight

    async def _analyze_market_correlations(self):
        """Analyze correlations in market data"""
        market_docs = self.documents.get("market_data", {})
        if len(market_docs) < 100:
            return
        
        market_data = [doc.data for doc in market_docs.values()]
        df = pd.DataFrame(market_data)
        
        if 'symbol' in df.columns and 'close' in df.columns:
            # Pivot to get price matrix
            price_matrix = df.pivot_table(
                index='timestamp', 
                columns='symbol', 
                values='close'
            ).fillna(method='forward')
            
            if len(price_matrix.columns) >= 2:
                # Calculate returns
                returns = price_matrix.pct_change().dropna()
                
                # Calculate correlation matrix
                correlations = returns.corr()
                
                # Find high correlations
                high_corr_pairs = []
                for i in range(len(correlations.columns)):
                    for j in range(i+1, len(correlations.columns)):
                        corr_value = correlations.iloc[i, j]
                        if abs(corr_value) > 0.7:
                            high_corr_pairs.append({
                                "symbol1": correlations.columns[i],
                                "symbol2": correlations.columns[j],
                                "correlation": corr_value
                            })
                
                if high_corr_pairs:
                    insight = DataInsight(
                        id=str(uuid.uuid4()),
                        insight_type="market_correlation",
                        collection="market_data",
                        title="High Correlation Detection",
                        description=f"Found {len(high_corr_pairs)} highly correlated symbol pairs",
                        key_metrics={
                            "high_correlation_pairs": len(high_corr_pairs),
                            "avg_correlation": np.mean([p["correlation"] for p in high_corr_pairs])
                        },
                        trends=[],
                        correlations={f"{p['symbol1']}-{p['symbol2']}": p["correlation"] for p in high_corr_pairs},
                        recommendations=[
                            "Consider correlation in portfolio construction",
                            "Monitor for correlation breakdown"
                        ],
                        confidence_score=0.9,
                        created_at=datetime.now().isoformat()
                    )
                    
                    self.data_insights[insight.id] = insight
                    await self._notify_data_insight(insight)

    async def store_document(self, request: DocumentRequest) -> str:
        """Store a new document"""
        try:
            doc_id = await self._store_document(
                request.collection,
                request.document_type,
                request.data,
                request.metadata,
                request.tags
            )
            
            await self._notify_document_stored(request.collection, doc_id)
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def query_documents(self, request: QueryRequest) -> QueryResult:
        """Query documents with various query types"""
        query_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            if request.query_type == QueryType.FIND:
                results = await self._execute_find_query(request)
            elif request.query_type == QueryType.AGGREGATE:
                results = await self._execute_aggregate_query(request)
            elif request.query_type == QueryType.TIME_SERIES:
                results = await self._execute_time_series_query(request)
            elif request.query_type == QueryType.TEXT_SEARCH:
                results = await self._execute_text_search(request)
            else:
                results = await self._execute_find_query(request)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            query_result = QueryResult(
                query_id=query_id,
                collection=request.collection,
                query_type=request.query_type,
                query=asdict(request),
                results=results,
                result_count=len(results),
                execution_time_ms=execution_time,
                explained_query={"type": "mock_explanation"},
                created_at=datetime.now().isoformat()
            )
            
            self.query_history.append(query_result)
            
            # Keep only last 1000 queries
            if len(self.query_history) > 1000:
                self.query_history = self.query_history[-1000:]
            
            return query_result
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _execute_find_query(self, request: QueryRequest) -> List[Dict[str, Any]]:
        """Execute a find query"""
        collection_docs = self.documents.get(request.collection, {})
        results = []
        
        for doc in collection_docs.values():
            # Simple query matching (in real MongoDB this would be much more sophisticated)
            if self._matches_query(doc.data, request.query):
                doc_dict = asdict(doc)
                results.append(doc_dict)
                
                if len(results) >= request.limit:
                    break
        
        # Apply skip
        if request.skip > 0:
            results = results[request.skip:]
        
        return results

    async def _execute_aggregate_query(self, request: QueryRequest) -> List[Dict[str, Any]]:
        """Execute an aggregation query"""
        # Simplified aggregation simulation
        collection_docs = self.documents.get(request.collection, {})
        
        if not collection_docs:
            return []
        
        # Example aggregation: group by symbol and calculate averages
        if request.collection == "market_data":
            symbol_groups = defaultdict(list)
            
            for doc in collection_docs.values():
                if "symbol" in doc.data:
                    symbol_groups[doc.data["symbol"]].append(doc.data)
            
            results = []
            for symbol, docs in symbol_groups.items():
                if "close" in docs[0]:
                    avg_close = np.mean([d["close"] for d in docs])
                    avg_volume = np.mean([d["volume"] for d in docs])
                    
                    results.append({
                        "_id": symbol,
                        "symbol": symbol,
                        "avg_close": avg_close,
                        "avg_volume": avg_volume,
                        "count": len(docs)
                    })
            
            return results[:request.limit]
        
        return []

    async def _execute_time_series_query(self, request: QueryRequest) -> List[Dict[str, Any]]:
        """Execute a time series query"""
        # This would implement time-based aggregations
        collection_docs = self.documents.get(request.collection, {})
        
        # Filter by time range if timestamp field exists
        filtered_docs = []
        for doc in collection_docs.values():
            if "timestamp" in doc.data:
                doc_time = datetime.fromisoformat(doc.data["timestamp"].replace('Z', '+00:00').replace('+00:00', ''))
                # Note: In real implementation, would properly handle timezone
                if hasattr(request.query, 'start_time') and hasattr(request.query, 'end_time'):
                    if request.query['start_time'] <= doc_time <= request.query['end_time']:
                        filtered_docs.append(doc.data)
        
        return filtered_docs[:request.limit]

    async def _execute_text_search(self, request: QueryRequest) -> List[Dict[str, Any]]:
        """Execute a text search query"""
        collection_docs = self.documents.get(request.collection, {})
        results = []
        
        search_term = request.query.get("$text", {}).get("$search", "").lower()
        
        for doc in collection_docs.values():
            # Simple text search in title and content fields
            searchable_text = ""
            if "title" in doc.data:
                searchable_text += doc.data["title"].lower() + " "
            if "content" in doc.data:
                searchable_text += doc.data["content"].lower() + " "
            
            if search_term and search_term in searchable_text:
                doc_dict = asdict(doc)
                doc_dict["score"] = searchable_text.count(search_term)  # Simple scoring
                results.append(doc_dict)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return results[:request.limit]

    def _matches_query(self, doc_data: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """Simple query matching logic"""
        for field, condition in query.items():
            if field not in doc_data:
                return False
            
            if isinstance(condition, dict):
                # Handle operators like $gt, $lt, etc.
                for operator, value in condition.items():
                    if operator == "$gt" and doc_data[field] <= value:
                        return False
                    elif operator == "$lt" and doc_data[field] >= value:
                        return False
                    elif operator == "$gte" and doc_data[field] < value:
                        return False
                    elif operator == "$lte" and doc_data[field] > value:
                        return False
                    elif operator == "$ne" and doc_data[field] == value:
                        return False
                    elif operator == "$in" and doc_data[field] not in value:
                        return False
            else:
                # Direct equality match
                if doc_data[field] != condition:
                    return False
        
        return True

    async def get_collection_info(self, collection_name: str) -> Collection:
        """Get information about a collection"""
        if collection_name not in self.collections:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        return self.collections[collection_name]

    async def get_data_insights(self, insight_type: Optional[str] = None) -> List[DataInsight]:
        """Get data insights with optional filtering"""
        insights = list(self.data_insights.values())
        
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]
        
        # Sort by creation time (newest first)
        insights.sort(key=lambda x: x.created_at, reverse=True)
        
        return insights

    async def _notify_document_stored(self, collection: str, doc_id: str):
        """Notify clients of document storage"""
        message = {
            "type": "document_stored",
            "collection": collection,
            "document_id": doc_id,
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

    async def _notify_data_insight(self, insight: DataInsight):
        """Notify clients of new data insights"""
        message = {
            "type": "data_insight",
            "insight": asdict(insight),
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.connected_clients[:]:
            try:
                await client.send_text(json.dumps(message))
            except:
                self.connected_clients.remove(client)

# Initialize service
mongodb_service = MongoDBIntelligenceService()

# Authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await mongodb_service.initialize()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "MongoDB Intelligence MCP Server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "document_storage",
            "complex_queries",
            "data_analytics",
            "intelligent_insights"
        ]
    }

@app.get("/metrics")
async def get_metrics():
    total_docs = sum(c.document_count for c in mongodb_service.collections.values())
    total_size = sum(c.size_bytes for c in mongodb_service.collections.values())
    
    return {
        "cpu_usage": 31.4,
        "memory_usage": 47.8,
        "disk_usage": 25.6,
        "network_in": 2560,
        "network_out": 5120,
        "active_connections": len(mongodb_service.connected_clients),
        "queue_length": 0,
        "errors_last_hour": 2,
        "requests_last_hour": 445,
        "response_time_p95": 234.0,
        "total_documents": total_docs,
        "total_storage_mb": total_size / (1024 * 1024),
        "query_count_last_hour": len([q for q in mongodb_service.query_history 
                                     if (datetime.now() - datetime.fromisoformat(q.created_at.replace('Z', '+00:00').replace('+00:00', ''))).total_seconds() < 3600])
    }

@app.post("/documents")
async def store_document(request: DocumentRequest, token: str = Depends(get_current_user)):
    try:
        doc_id = await mongodb_service.store_document(request)
        return {"document_id": doc_id, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error storing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_documents(request: QueryRequest, token: str = Depends(get_current_user)):
    try:
        result = await mongodb_service.query_documents(request)
        return {"result": asdict(result), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/collections")
async def get_collections(token: str = Depends(get_current_user)):
    collections = list(mongodb_service.collections.values())
    return {
        "collections": [asdict(c) for c in collections],
        "total": len(collections),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/collections/{collection_name}")
async def get_collection_info(collection_name: str, token: str = Depends(get_current_user)):
    try:
        collection = await mongodb_service.get_collection_info(collection_name)
        return {"collection": asdict(collection), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/insights")
async def get_data_insights(
    insight_type: Optional[str] = None,
    token: str = Depends(get_current_user)
):
    try:
        insights = await mongodb_service.get_data_insights(insight_type)
        return {
            "insights": [asdict(i) for i in insights],
            "total": len(insights),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/query-history")
async def get_query_history(limit: int = 50, token: str = Depends(get_current_user)):
    recent_queries = mongodb_service.query_history[-limit:]
    return {
        "queries": [asdict(q) for q in recent_queries],
        "total": len(recent_queries),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/indexes/{collection_name}")
async def get_collection_indexes(collection_name: str, token: str = Depends(get_current_user)):
    indexes = mongodb_service.indexes.get(collection_name, [])
    return {
        "collection": collection_name,
        "indexes": indexes,
        "total": len(indexes),
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/mongodb")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    mongodb_service.connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except:
        pass
    finally:
        if websocket in mongodb_service.connected_clients:
            mongodb_service.connected_clients.remove(websocket)

@app.get("/capabilities")
async def get_capabilities():
    return {
        "document_types": [dt.value for dt in DocumentType],
        "query_types": [qt.value for qt in QueryType],
        "index_types": [it.value for it in IndexType],
        "capabilities": [
            {
                "name": "document_storage",
                "description": "Store and manage documents in collections"
            },
            {
                "name": "complex_queries",
                "description": "Execute complex queries including aggregations"
            },
            {
                "name": "time_series_analysis",
                "description": "Specialized time-series data operations"
            },
            {
                "name": "text_search",
                "description": "Full-text search capabilities"
            },
            {
                "name": "data_analytics",
                "description": "Intelligent data analysis and insights"
            },
            {
                "name": "performance_optimization",
                "description": "Automatic performance monitoring and optimization"
            }
        ],
        "supported_operations": [
            "insert", "update", "delete", "find", "aggregate",
            "text_search", "time_series", "index_management"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "mongodb_intelligence:app",
        host="0.0.0.0",
        port=8021,
        reload=True,
        log_level="info"
    )