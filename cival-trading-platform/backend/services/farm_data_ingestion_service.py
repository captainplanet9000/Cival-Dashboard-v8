"""
Farm Data Ingestion Service
Connects existing trading systems to the Trading Farm Brain archive
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from services.trading_farm_brain_service import (
    get_trading_farm_brain_service,
    StrategyArchiveData,
    TradeArchiveData,
    AgentDecisionArchiveData,
    AgentMemoryData
)

# Import existing services to extract data from
from services.paper_trading_service import get_paper_trading_service
from services.backtesting_service import get_backtesting_service
from services.agent_coordination_service import get_agent_coordination_service
from services.strategy_coordination_service import get_strategy_coordination_service
from services.memory_service import get_memory_service

logger = logging.getLogger(__name__)


class FarmDataIngestionService:
    """
    Service to ingest data from existing trading systems into the Farm Brain
    """
    
    def __init__(self):
        self.farm_brain = None
        self.paper_trading = None
        self.backtesting = None
        self.agent_coordination = None
        self.strategy_coordination = None
        self.memory_service = None
        
        # Ingestion state tracking
        self.last_ingestion_timestamps = {}
        self.ingestion_stats = {
            "strategies_ingested": 0,
            "trades_ingested": 0,
            "decisions_ingested": 0,
            "memories_ingested": 0
        }
        
    async def initialize(self):
        """Initialize all service connections"""
        try:
            self.farm_brain = await get_trading_farm_brain_service()
            
            # Initialize existing services
            try:
                self.paper_trading = await get_paper_trading_service()
                logger.info("✅ Connected to Paper Trading Service")
            except Exception as e:
                logger.warning(f"Paper Trading Service not available: {e}")
                
            try:
                self.backtesting = await get_backtesting_service()
                logger.info("✅ Connected to Backtesting Service")
            except Exception as e:
                logger.warning(f"Backtesting Service not available: {e}")
                
            try:
                self.agent_coordination = await get_agent_coordination_service()
                logger.info("✅ Connected to Agent Coordination Service")
            except Exception as e:
                logger.warning(f"Agent Coordination Service not available: {e}")
                
            try:
                self.strategy_coordination = await get_strategy_coordination_service()
                logger.info("✅ Connected to Strategy Coordination Service")
            except Exception as e:
                logger.warning(f"Strategy Coordination Service not available: {e}")
                
            try:
                self.memory_service = await get_memory_service()
                logger.info("✅ Connected to Memory Service")
            except Exception as e:
                logger.warning(f"Memory Service not available: {e}")
                
            logger.info("Farm Data Ingestion Service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Farm Data Ingestion Service: {e}")
            raise
    
    # ==========================================
    # STRATEGY INGESTION
    # ==========================================
    
    async def ingest_strategies_from_existing_systems(self) -> int:
        """Ingest strategies from all existing systems"""
        strategies_count = 0
        
        # Ingest from strategy coordination service
        if self.strategy_coordination:
            try:
                # Get all registered strategies
                strategies = getattr(self.strategy_coordination, 'registered_strategies', {})
                
                for strategy_id, strategy_data in strategies.items():
                    await self._ingest_strategy(strategy_id, strategy_data, "strategy_coordination")
                    strategies_count += 1
                    
                logger.info(f"Ingested {len(strategies)} strategies from Strategy Coordination")
                
            except Exception as e:
                logger.error(f"Failed to ingest strategies from coordination service: {e}")
        
        # Ingest from backtesting results
        if self.backtesting:
            try:
                # Get strategy performance data from backtesting
                backtest_results = getattr(self.backtesting, 'backtest_results', {})
                
                for result_id, result in backtest_results.items():
                    if hasattr(result, 'strategy_id'):
                        await self._ingest_strategy_from_backtest(result)
                        strategies_count += 1
                        
                logger.info(f"Ingested strategy data from {len(backtest_results)} backtest results")
                
            except Exception as e:
                logger.error(f"Failed to ingest strategies from backtesting: {e}")
        
        self.ingestion_stats["strategies_ingested"] = strategies_count
        return strategies_count
    
    async def _ingest_strategy(self, strategy_id: str, strategy_data: Dict[str, Any], source: str):
        """Ingest a single strategy"""
        try:
            archive_data = StrategyArchiveData(
                strategy_id=strategy_id,
                strategy_name=strategy_data.get("name", strategy_id),
                strategy_type=strategy_data.get("type", "unknown"),
                version_number=strategy_data.get("version", 1),
                strategy_code=strategy_data.get("code", {}),
                parameters=strategy_data.get("parameters", {}),
                entry_conditions=strategy_data.get("entry_conditions", []),
                exit_conditions=strategy_data.get("exit_conditions", []),
                risk_rules=strategy_data.get("risk_rules", []),
                created_by=f"{source}_ingestion",
                market_conditions=strategy_data.get("market_conditions", {}),
                asset_classes=strategy_data.get("asset_classes", []),
                timeframes=strategy_data.get("timeframes", []),
                description=f"Ingested from {source}",
                tags=[source, "ingested"]
            )
            
            await self.farm_brain.archive_strategy(archive_data)
            logger.debug(f"Successfully ingested strategy: {strategy_id}")
            
        except Exception as e:
            logger.error(f"Failed to ingest strategy {strategy_id}: {e}")
    
    # ==========================================
    # TRADE INGESTION
    # ==========================================
    
    async def ingest_trades_from_paper_trading(self) -> int:
        """Ingest trades from paper trading system"""
        if not self.paper_trading:
            return 0
            
        trades_count = 0
        
        try:
            # Get paper trading accounts
            accounts = getattr(self.paper_trading, 'paper_accounts', {})
            
            for account_id, account in accounts.items():
                # Get trade history from account
                trade_history = getattr(account, 'trade_history', [])
                
                for trade in trade_history:
                    await self._ingest_paper_trade(trade, account_id)
                    trades_count += 1
            
            logger.info(f"Ingested {trades_count} trades from Paper Trading")
            
        except Exception as e:
            logger.error(f"Failed to ingest trades from paper trading: {e}")
        
        self.ingestion_stats["trades_ingested"] += trades_count
        return trades_count
    
    async def ingest_trades_from_backtesting(self) -> int:
        """Ingest trades from backtesting results"""
        if not self.backtesting:
            return 0
            
        trades_count = 0
        
        try:
            # Get backtest results
            backtest_results = getattr(self.backtesting, 'backtest_results', {})
            
            for result_id, result in backtest_results.items():
                # Extract trades from backtest result
                trades = getattr(result, 'trades', [])
                
                for trade in trades:
                    await self._ingest_backtest_trade(trade, result.strategy_id, result_id)
                    trades_count += 1
            
            logger.info(f"Ingested {trades_count} trades from Backtesting")
            
        except Exception as e:
            logger.error(f"Failed to ingest trades from backtesting: {e}")
        
        self.ingestion_stats["trades_ingested"] += trades_count
        return trades_count
    
    async def _ingest_paper_trade(self, trade: Dict[str, Any], account_id: str):
        """Ingest a single paper trade"""
        try:
            trade_data = TradeArchiveData(
                trade_id=trade.get("trade_id", f"paper_{account_id}_{trade.get('id', '')}"),
                strategy_id=trade.get("strategy_id"),
                agent_id=trade.get("agent_id", account_id),
                symbol=trade.get("symbol", ""),
                side=trade.get("side", ""),
                quantity=Decimal(str(trade.get("quantity", 0))),
                entry_price=Decimal(str(trade.get("entry_price", 0))),
                exit_price=Decimal(str(trade.get("exit_price", 0))) if trade.get("exit_price") else None,
                entry_time=self._parse_datetime(trade.get("entry_time")),
                exit_time=self._parse_datetime(trade.get("exit_time")) if trade.get("exit_time") else None,
                gross_pnl=Decimal(str(trade.get("pnl", 0))),
                fees_paid=Decimal(str(trade.get("fees", 0))),
                net_pnl=Decimal(str(trade.get("net_pnl", trade.get("pnl", 0)))),
                entry_market_data=trade.get("market_data", {}),
                entry_reasoning=trade.get("reasoning", ""),
                confidence_level=Decimal(str(trade.get("confidence", 0.5))),
                trade_type="paper",
                decision_factors=trade.get("decision_factors", {})
            )
            
            await self.farm_brain.archive_trade(trade_data)
            logger.debug(f"Successfully ingested paper trade: {trade_data.trade_id}")
            
        except Exception as e:
            logger.error(f"Failed to ingest paper trade: {e}")
    
    async def _ingest_backtest_trade(self, trade: Dict[str, Any], strategy_id: str, backtest_id: str):
        """Ingest a single backtest trade"""
        try:
            trade_data = TradeArchiveData(
                trade_id=trade.get("trade_id", f"backtest_{backtest_id}_{trade.get('id', '')}"),
                strategy_id=strategy_id,
                agent_id=f"backtest_engine_{backtest_id}",
                symbol=trade.get("symbol", ""),
                side=trade.get("action", ""),
                quantity=Decimal(str(trade.get("quantity", 0))),
                entry_price=Decimal(str(trade.get("price", 0))),
                exit_price=Decimal(str(trade.get("exit_price", 0))) if trade.get("exit_price") else None,
                entry_time=self._parse_datetime(trade.get("timestamp")),
                exit_time=self._parse_datetime(trade.get("exit_time")) if trade.get("exit_time") else None,
                gross_pnl=Decimal(str(trade.get("pnl", 0))),
                fees_paid=Decimal(str(trade.get("commission", 0))),
                net_pnl=Decimal(str(trade.get("pnl", 0))) - Decimal(str(trade.get("commission", 0))),
                entry_market_data={"backtest_data": trade.get("market_data", {})},
                entry_reasoning="Backtest execution",
                trade_type="backtest",
                decision_factors={"backtest_id": backtest_id}
            )
            
            await self.farm_brain.archive_trade(trade_data)
            logger.debug(f"Successfully ingested backtest trade: {trade_data.trade_id}")
            
        except Exception as e:
            logger.error(f"Failed to ingest backtest trade: {e}")
    
    # ==========================================
    # AGENT DECISION INGESTION
    # ==========================================
    
    async def ingest_agent_decisions(self) -> int:
        """Ingest agent decisions from coordination services"""
        decisions_count = 0
        
        if self.agent_coordination:
            try:
                # Get completed tasks/decisions
                completed_tasks = getattr(self.agent_coordination, 'completed_tasks', [])
                
                for task in completed_tasks:
                    await self._ingest_agent_decision_from_task(task)
                    decisions_count += 1
                
                logger.info(f"Ingested {decisions_count} decisions from Agent Coordination")
                
            except Exception as e:
                logger.error(f"Failed to ingest agent decisions: {e}")
        
        self.ingestion_stats["decisions_ingested"] += decisions_count
        return decisions_count
    
    async def _ingest_agent_decision_from_task(self, task: Dict[str, Any]):
        """Ingest agent decision from coordination task"""
        try:
            decision_data = AgentDecisionArchiveData(
                decision_id=task.get("task_id", ""),
                agent_id=task.get("agent_id", "unknown"),
                decision_type=task.get("task_type", "analysis"),
                symbol=task.get("symbol", ""),
                decision_time=self._parse_datetime(task.get("created_at")),
                market_data=task.get("market_data", {}),
                reasoning=task.get("reasoning", ""),
                confidence_score=Decimal(str(task.get("confidence", 0.5))),
                recommended_action=task.get("results", {}),
                executed=task.get("status") == "completed",
                execution_details=task.get("execution_details", {})
            )
            
            await self.farm_brain.archive_agent_decision(decision_data)
            logger.debug(f"Successfully ingested agent decision: {decision_data.decision_id}")
            
        except Exception as e:
            logger.error(f"Failed to ingest agent decision: {e}")
    
    # ==========================================
    # MEMORY INGESTION
    # ==========================================
    
    async def ingest_agent_memories(self) -> int:
        """Ingest agent memories from memory service"""
        if not self.memory_service:
            return 0
            
        memories_count = 0
        
        try:
            # Get all agent memories
            memories = getattr(self.memory_service, 'agent_memories', {})
            
            for agent_id, agent_memories in memories.items():
                for memory_key, memory_data in agent_memories.items():
                    await self._ingest_agent_memory(agent_id, memory_key, memory_data)
                    memories_count += 1
            
            logger.info(f"Ingested {memories_count} memories from Memory Service")
            
        except Exception as e:
            logger.error(f"Failed to ingest agent memories: {e}")
        
        self.ingestion_stats["memories_ingested"] += memories_count
        return memories_count
    
    async def _ingest_agent_memory(self, agent_id: str, memory_key: str, memory_data: Dict[str, Any]):
        """Ingest a single agent memory"""
        try:
            memory_archive = AgentMemoryData(
                agent_id=agent_id,
                memory_type=memory_data.get("type", "general"),
                memory_key=memory_key,
                memory_data=memory_data.get("content", memory_data),
                created_context=memory_data.get("context", {}),
                importance_score=Decimal(str(memory_data.get("importance", 0.5)))
            )
            
            await self.farm_brain.persist_agent_memory(memory_archive)
            logger.debug(f"Successfully ingested memory: {agent_id}:{memory_key}")
            
        except Exception as e:
            logger.error(f"Failed to ingest agent memory {agent_id}:{memory_key}: {e}")
    
    # ==========================================
    # FULL INGESTION WORKFLOW
    # ==========================================
    
    async def run_full_ingestion(self) -> Dict[str, int]:
        """Run complete data ingestion from all systems"""
        logger.info("Starting full data ingestion workflow...")
        
        # Reset stats
        self.ingestion_stats = {
            "strategies_ingested": 0,
            "trades_ingested": 0,
            "decisions_ingested": 0,
            "memories_ingested": 0
        }
        
        try:
            # Phase 1: Ingest strategies
            logger.info("Phase 1: Ingesting strategies...")
            await self.ingest_strategies_from_existing_systems()
            
            # Phase 2: Ingest trades
            logger.info("Phase 2: Ingesting trades...")
            await self.ingest_trades_from_paper_trading()
            await self.ingest_trades_from_backtesting()
            
            # Phase 3: Ingest decisions
            logger.info("Phase 3: Ingesting agent decisions...")
            await self.ingest_agent_decisions()
            
            # Phase 4: Ingest memories
            logger.info("Phase 4: Ingesting agent memories...")
            await self.ingest_agent_memories()
            
            logger.info(f"Full ingestion completed: {self.ingestion_stats}")
            
        except Exception as e:
            logger.error(f"Full ingestion failed: {e}")
            
        return self.ingestion_stats
    
    async def run_incremental_ingestion(self) -> Dict[str, int]:
        """Run incremental ingestion for new data only"""
        logger.info("Starting incremental data ingestion...")
        
        # This would check timestamps and only ingest new data
        # Implementation depends on how existing services track data changes
        
        return await self.run_full_ingestion()  # Simplified for now
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    def _parse_datetime(self, dt_str: Any) -> datetime:
        """Parse datetime from various formats"""
        if isinstance(dt_str, datetime):
            return dt_str
        elif isinstance(dt_str, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except:
                try:
                    # Try timestamp
                    return datetime.fromtimestamp(float(dt_str), tz=timezone.utc)
                except:
                    # Default to now
                    return datetime.now(timezone.utc)
        else:
            return datetime.now(timezone.utc)
    
    async def get_ingestion_status(self) -> Dict[str, Any]:
        """Get current ingestion status"""
        return {
            "service_connections": {
                "farm_brain": self.farm_brain is not None,
                "paper_trading": self.paper_trading is not None,
                "backtesting": self.backtesting is not None,
                "agent_coordination": self.agent_coordination is not None,
                "strategy_coordination": self.strategy_coordination is not None,
                "memory_service": self.memory_service is not None
            },
            "ingestion_stats": self.ingestion_stats,
            "last_ingestion_timestamps": self.last_ingestion_timestamps
        }


# Global service instance
_farm_ingestion_service: Optional[FarmDataIngestionService] = None


async def get_farm_ingestion_service() -> FarmDataIngestionService:
    """Get the global farm ingestion service instance"""
    global _farm_ingestion_service
    
    if _farm_ingestion_service is None:
        _farm_ingestion_service = FarmDataIngestionService()
        await _farm_ingestion_service.initialize()
    
    return _farm_ingestion_service