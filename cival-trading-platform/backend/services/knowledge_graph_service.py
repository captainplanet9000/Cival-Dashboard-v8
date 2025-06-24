"""
Knowledge Graph Service for Trading Farm Brain
Builds relationships between strategies, trades, agents, and market conditions
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.service_registry import ServiceRegistry
from database.async_pool import db_pool
from models.farm_models import (
    StrategyArchiveData, TradeArchiveData, 
    AgentDecisionData, AgentMemoryData
)


class KnowledgeGraphService:
    """
    Builds and queries a knowledge graph of trading relationships
    """
    
    def __init__(self):
        self.service_registry = ServiceRegistry()
        self.graph = nx.DiGraph()
        self.entity_embeddings = {}
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self._initialized = False
        
    async def initialize(self):
        """Initialize the knowledge graph from archived data"""
        if self._initialized:
            return
            
        await self._build_graph()
        self._initialized = True
        
    async def _build_graph(self):
        """Build the knowledge graph from Trading Farm Brain data"""
        async with db_pool.get_connection() as conn:
            # Load all entities
            strategies = await self._load_strategies(conn)
            trades = await self._load_trades(conn)
            decisions = await self._load_decisions(conn)
            agents = await self._load_agents(conn)
            
            # Build nodes
            await self._build_strategy_nodes(strategies)
            await self._build_trade_nodes(trades)
            await self._build_decision_nodes(decisions)
            await self._build_agent_nodes(agents)
            
            # Build relationships
            await self._build_relationships(conn)
            
            # Create embeddings for similarity search
            await self._create_embeddings()
            
    async def _load_strategies(self, conn) -> List[Dict]:
        """Load all archived strategies"""
        query = """
            SELECT strategy_id, strategy_name, strategy_type, 
                   parameters, performance_metrics, created_at
            FROM farm_strategy_archive
            ORDER BY created_at DESC
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
        
    async def _load_trades(self, conn) -> List[Dict]:
        """Load all archived trades"""
        query = """
            SELECT trade_id, strategy_id, agent_id, symbol, 
                   entry_price, exit_price, net_pnl, trade_metadata,
                   entry_time, exit_time
            FROM farm_trade_archive
            ORDER BY entry_time DESC
            LIMIT 10000
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
        
    async def _load_decisions(self, conn) -> List[Dict]:
        """Load all agent decisions"""
        query = """
            SELECT decision_id, agent_id, decision_type, symbol,
                   confidence_score, reasoning, decision_metadata,
                   decision_time
            FROM farm_agent_decisions
            ORDER BY decision_time DESC
            LIMIT 10000
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
        
    async def _load_agents(self, conn) -> List[Dict]:
        """Load unique agents"""
        query = """
            SELECT DISTINCT agent_id, 
                   COUNT(DISTINCT trade_id) as trade_count,
                   SUM(net_pnl) as total_pnl,
                   AVG(confidence_score) as avg_confidence
            FROM farm_trade_archive t
            LEFT JOIN farm_agent_decisions d ON t.agent_id = d.agent_id
            GROUP BY agent_id
        """
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
        
    async def _build_strategy_nodes(self, strategies: List[Dict]):
        """Build strategy nodes in the graph"""
        for strategy in strategies:
            node_id = f"strategy_{strategy['strategy_id']}"
            self.graph.add_node(
                node_id,
                type='strategy',
                name=strategy['strategy_name'],
                strategy_type=strategy['strategy_type'],
                parameters=strategy['parameters'],
                performance=strategy['performance_metrics'],
                created_at=strategy['created_at'].isoformat()
            )
            
    async def _build_trade_nodes(self, trades: List[Dict]):
        """Build trade nodes in the graph"""
        for trade in trades:
            node_id = f"trade_{trade['trade_id']}"
            self.graph.add_node(
                node_id,
                type='trade',
                symbol=trade['symbol'],
                pnl=float(trade['net_pnl']),
                entry_price=float(trade['entry_price']),
                exit_price=float(trade['exit_price']),
                metadata=trade['trade_metadata'],
                entry_time=trade['entry_time'].isoformat(),
                exit_time=trade['exit_time'].isoformat() if trade['exit_time'] else None
            )
            
    async def _build_decision_nodes(self, decisions: List[Dict]):
        """Build decision nodes in the graph"""
        for decision in decisions:
            node_id = f"decision_{decision['decision_id']}"
            self.graph.add_node(
                node_id,
                type='decision',
                decision_type=decision['decision_type'],
                symbol=decision['symbol'],
                confidence=float(decision['confidence_score']),
                reasoning=decision['reasoning'],
                metadata=decision['decision_metadata'],
                time=decision['decision_time'].isoformat()
            )
            
    async def _build_agent_nodes(self, agents: List[Dict]):
        """Build agent nodes in the graph"""
        for agent in agents:
            node_id = f"agent_{agent['agent_id']}"
            self.graph.add_node(
                node_id,
                type='agent',
                agent_id=agent['agent_id'],
                trade_count=int(agent['trade_count']),
                total_pnl=float(agent['total_pnl']) if agent['total_pnl'] else 0,
                avg_confidence=float(agent['avg_confidence']) if agent['avg_confidence'] else 0
            )
            
    async def _build_relationships(self, conn):
        """Build relationships between nodes"""
        # Strategy -> Trade relationships
        query = """
            SELECT DISTINCT trade_id, strategy_id, agent_id
            FROM farm_trade_archive
            WHERE strategy_id IS NOT NULL
        """
        rows = await conn.fetch(query)
        for row in rows:
            strategy_node = f"strategy_{row['strategy_id']}"
            trade_node = f"trade_{row['trade_id']}"
            agent_node = f"agent_{row['agent_id']}"
            
            if self.graph.has_node(strategy_node) and self.graph.has_node(trade_node):
                self.graph.add_edge(strategy_node, trade_node, relationship='executed')
                
            if self.graph.has_node(agent_node) and self.graph.has_node(trade_node):
                self.graph.add_edge(agent_node, trade_node, relationship='performed')
                
        # Decision -> Trade relationships
        query = """
            SELECT d.decision_id, t.trade_id
            FROM farm_agent_decisions d
            JOIN farm_trade_archive t ON d.agent_id = t.agent_id
                AND d.symbol = t.symbol
                AND ABS(EXTRACT(EPOCH FROM (t.entry_time - d.decision_time))) < 300
        """
        rows = await conn.fetch(query)
        for row in rows:
            decision_node = f"decision_{row['decision_id']}"
            trade_node = f"trade_{row['trade_id']}"
            
            if self.graph.has_node(decision_node) and self.graph.has_node(trade_node):
                self.graph.add_edge(decision_node, trade_node, relationship='resulted_in')
                
    async def _create_embeddings(self):
        """Create text embeddings for nodes"""
        texts = []
        node_ids = []
        
        for node_id, data in self.graph.nodes(data=True):
            # Create text representation of node
            text_parts = [data['type']]
            
            if data['type'] == 'strategy':
                text_parts.extend([
                    data.get('name', ''),
                    data.get('strategy_type', ''),
                    json.dumps(data.get('parameters', {}))
                ])
            elif data['type'] == 'trade':
                text_parts.extend([
                    data.get('symbol', ''),
                    f"pnl_{data.get('pnl', 0)}",
                    json.dumps(data.get('metadata', {}))
                ])
            elif data['type'] == 'decision':
                text_parts.extend([
                    data.get('decision_type', ''),
                    data.get('symbol', ''),
                    data.get('reasoning', ''),
                    f"confidence_{data.get('confidence', 0)}"
                ])
            elif data['type'] == 'agent':
                text_parts.extend([
                    data.get('agent_id', ''),
                    f"trades_{data.get('trade_count', 0)}",
                    f"pnl_{data.get('total_pnl', 0)}"
                ])
                
            text = ' '.join(str(part) for part in text_parts)
            texts.append(text)
            node_ids.append(node_id)
            
        if texts:
            # Create TF-IDF embeddings
            embeddings = self.vectorizer.fit_transform(texts)
            
            for i, node_id in enumerate(node_ids):
                self.entity_embeddings[node_id] = embeddings[i]
                
    async def search_similar_entities(
        self, 
        query: str, 
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for entities similar to the query"""
        if not self.entity_embeddings:
            return []
            
        # Transform query to embedding
        query_embedding = self.vectorizer.transform([query])
        
        # Calculate similarities
        similarities = []
        for node_id, embedding in self.entity_embeddings.items():
            if entity_type and not node_id.startswith(entity_type):
                continue
                
            similarity = cosine_similarity(query_embedding, embedding)[0][0]
            similarities.append((node_id, similarity))
            
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results with node data
        results = []
        for node_id, score in similarities[:limit]:
            node_data = dict(self.graph.nodes[node_id])
            node_data['similarity_score'] = score
            node_data['node_id'] = node_id
            results.append(node_data)
            
        return results
        
    async def find_strategy_patterns(self) -> List[Dict[str, Any]]:
        """Find patterns in successful strategies"""
        patterns = []
        
        # Find strategies with highest win rates
        strategy_performance = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0})
        
        for node_id, data in self.graph.nodes(data=True):
            if data['type'] != 'strategy':
                continue
                
            # Get all trades for this strategy
            trades = []
            for successor in self.graph.successors(node_id):
                if self.graph.nodes[successor]['type'] == 'trade':
                    trades.append(self.graph.nodes[successor])
                    
            if len(trades) >= 5:  # Minimum trades for pattern
                wins = sum(1 for t in trades if t['pnl'] > 0)
                losses = len(trades) - wins
                total_pnl = sum(t['pnl'] for t in trades)
                
                win_rate = wins / len(trades) if trades else 0
                
                if win_rate > 0.6:  # Successful pattern
                    patterns.append({
                        'strategy_id': node_id,
                        'strategy_name': data.get('name', 'Unknown'),
                        'strategy_type': data.get('strategy_type', 'Unknown'),
                        'parameters': data.get('parameters', {}),
                        'win_rate': win_rate,
                        'total_trades': len(trades),
                        'total_pnl': total_pnl,
                        'avg_pnl': total_pnl / len(trades) if trades else 0
                    })
                    
        # Sort by win rate
        patterns.sort(key=lambda x: x['win_rate'], reverse=True)
        
        return patterns[:20]  # Top 20 patterns
        
    async def find_agent_specializations(self) -> Dict[str, Dict[str, Any]]:
        """Find what each agent specializes in"""
        specializations = {}
        
        for node_id, data in self.graph.nodes(data=True):
            if data['type'] != 'agent':
                continue
                
            agent_id = data['agent_id']
            
            # Analyze trades
            symbol_stats = defaultdict(lambda: {'count': 0, 'pnl': 0, 'win_rate': 0})
            time_stats = defaultdict(lambda: {'count': 0, 'pnl': 0})
            
            for successor in self.graph.successors(node_id):
                if self.graph.nodes[successor]['type'] == 'trade':
                    trade = self.graph.nodes[successor]
                    symbol = trade['symbol']
                    
                    symbol_stats[symbol]['count'] += 1
                    symbol_stats[symbol]['pnl'] += trade['pnl']
                    
                    # Time analysis
                    if trade.get('entry_time'):
                        hour = datetime.fromisoformat(trade['entry_time']).hour
                        time_stats[hour]['count'] += 1
                        time_stats[hour]['pnl'] += trade['pnl']
                        
            # Find specialization
            if symbol_stats:
                best_symbol = max(symbol_stats.items(), 
                                key=lambda x: x[1]['pnl'])[0]
                best_hour = max(time_stats.items(), 
                              key=lambda x: x[1]['count'])[0] if time_stats else None
                
                specializations[agent_id] = {
                    'preferred_symbol': best_symbol,
                    'symbol_performance': dict(symbol_stats),
                    'preferred_trading_hour': best_hour,
                    'time_distribution': dict(time_stats),
                    'total_pnl': data['total_pnl'],
                    'trade_count': data['trade_count']
                }
                
        return specializations
        
    async def find_decision_trade_correlations(self) -> List[Dict[str, Any]]:
        """Find correlations between decision confidence and trade outcomes"""
        correlations = []
        
        # Analyze decision -> trade relationships
        for edge in self.graph.edges():
            if self.graph.nodes[edge[0]]['type'] == 'decision' and \
               self.graph.nodes[edge[1]]['type'] == 'trade':
                
                decision = self.graph.nodes[edge[0]]
                trade = self.graph.nodes[edge[1]]
                
                correlations.append({
                    'decision_type': decision['decision_type'],
                    'confidence': decision['confidence'],
                    'symbol': decision['symbol'],
                    'trade_pnl': trade['pnl'],
                    'success': trade['pnl'] > 0
                })
                
        # Group by confidence buckets
        confidence_buckets = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0})
        
        for corr in correlations:
            bucket = int(corr['confidence'] * 10) / 10  # Round to nearest 0.1
            if corr['success']:
                confidence_buckets[bucket]['wins'] += 1
            else:
                confidence_buckets[bucket]['losses'] += 1
            confidence_buckets[bucket]['total_pnl'] += corr['trade_pnl']
            
        # Calculate win rates per bucket
        results = []
        for confidence, stats in confidence_buckets.items():
            total = stats['wins'] + stats['losses']
            if total > 0:
                results.append({
                    'confidence_level': confidence,
                    'win_rate': stats['wins'] / total,
                    'total_trades': total,
                    'avg_pnl': stats['total_pnl'] / total
                })
                
        results.sort(key=lambda x: x['confidence_level'])
        
        return results
        
    async def get_entity_timeline(
        self, 
        entity_id: str, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get timeline of related activities for an entity"""
        timeline = []
        
        if entity_id not in self.graph:
            return timeline
            
        # Get all connected nodes
        connected = set()
        connected.update(self.graph.predecessors(entity_id))
        connected.update(self.graph.successors(entity_id))
        
        # Build timeline
        for node_id in connected:
            node = self.graph.nodes[node_id]
            
            # Extract timestamp
            timestamp = None
            if node['type'] == 'trade':
                timestamp = node.get('entry_time')
            elif node['type'] == 'decision':
                timestamp = node.get('time')
            elif node['type'] == 'strategy':
                timestamp = node.get('created_at')
                
            if timestamp:
                timeline.append({
                    'timestamp': timestamp,
                    'entity_type': node['type'],
                    'entity_id': node_id,
                    'details': self._extract_entity_details(node)
                })
                
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Filter by date range
        cutoff = datetime.now() - timedelta(days=days)
        timeline = [
            event for event in timeline 
            if datetime.fromisoformat(event['timestamp']) > cutoff
        ]
        
        return timeline
        
    def _extract_entity_details(self, node: Dict) -> Dict:
        """Extract relevant details from a node"""
        if node['type'] == 'trade':
            return {
                'symbol': node.get('symbol'),
                'pnl': node.get('pnl'),
                'entry_price': node.get('entry_price'),
                'exit_price': node.get('exit_price')
            }
        elif node['type'] == 'decision':
            return {
                'decision_type': node.get('decision_type'),
                'symbol': node.get('symbol'),
                'confidence': node.get('confidence'),
                'reasoning': node.get('reasoning')
            }
        elif node['type'] == 'strategy':
            return {
                'name': node.get('name'),
                'strategy_type': node.get('strategy_type')
            }
        elif node['type'] == 'agent':
            return {
                'agent_id': node.get('agent_id'),
                'total_pnl': node.get('total_pnl'),
                'trade_count': node.get('trade_count')
            }
        return {}
        
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get overall knowledge graph statistics"""
        stats = {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': {},
            'relationship_types': {},
            'connected_components': nx.number_weakly_connected_components(self.graph),
            'average_degree': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() if self.graph.number_of_nodes() > 0 else 0
        }
        
        # Count node types
        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            stats['node_types'][node_type] = stats['node_types'].get(node_type, 0) + 1
            
        # Count relationship types
        for u, v, data in self.graph.edges(data=True):
            rel_type = data.get('relationship', 'unknown')
            stats['relationship_types'][rel_type] = stats['relationship_types'].get(rel_type, 0) + 1
            
        return stats