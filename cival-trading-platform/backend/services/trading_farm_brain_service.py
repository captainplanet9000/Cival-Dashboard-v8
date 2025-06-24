"""
Trading Farm Brain Service - Core Archive and Analytics Engine
Comprehensive service for storing, retrieving, and analyzing all trading data
"""

import asyncio
import uuid
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
import logging

from pydantic import BaseModel, Field
from fastapi import HTTPException

# Database imports
from database.supabase_client import get_supabase_client
import redis.asyncio as redis

# Model imports
from models.trading_strategy_models import TradingStrategy, TradingSignal
from models.agent_models import AgentDecision, AgentPerformanceMetrics

logger = logging.getLogger(__name__)


class StrategyArchiveData(BaseModel):
    """Data model for archiving strategies"""
    strategy_id: str
    strategy_name: str
    strategy_type: str
    version_number: int = 1
    parent_strategy_id: Optional[str] = None
    strategy_code: Dict[str, Any]
    parameters: Dict[str, Any]
    entry_conditions: List[str]
    exit_conditions: List[str]
    risk_rules: List[str]
    created_by: str
    market_conditions: Optional[Dict[str, Any]] = None
    asset_classes: List[str] = []
    timeframes: List[str] = []
    tags: List[str] = []
    description: Optional[str] = None
    notes: Dict[str, Any] = {}


class TradeArchiveData(BaseModel):
    """Data model for archiving trades"""
    trade_id: str
    strategy_id: Optional[str] = None
    agent_id: str
    symbol: str
    side: str  # buy/sell/long/short
    quantity: Decimal
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    gross_pnl: Decimal = Decimal("0")
    fees_paid: Decimal = Decimal("0")
    net_pnl: Decimal = Decimal("0")
    pnl_percentage: Decimal = Decimal("0")
    entry_market_data: Dict[str, Any]
    exit_market_data: Optional[Dict[str, Any]] = None
    entry_reasoning: Optional[str] = None
    exit_reasoning: Optional[str] = None
    confidence_level: Optional[Decimal] = None
    decision_factors: Dict[str, Any] = {}
    trade_type: str = "paper"  # paper, live, backtest
    exchange: Optional[str] = None
    order_types: Dict[str, Any] = {}
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    max_risk: Optional[Decimal] = None


class AgentDecisionArchiveData(BaseModel):
    """Data model for archiving agent decisions"""
    decision_id: str
    agent_id: str
    agent_version: Optional[str] = None
    strategy_id: Optional[str] = None
    decision_type: str  # entry, exit, hold, rebalance
    symbol: str
    decision_time: datetime
    market_data: Dict[str, Any]
    technical_indicators: Dict[str, Any] = {}
    fundamental_data: Dict[str, Any] = {}
    sentiment_data: Dict[str, Any] = {}
    news_events: List[Dict[str, Any]] = []
    reasoning: str
    confidence_score: Optional[Decimal] = None
    alternative_considered: List[Dict[str, Any]] = []
    risk_assessment: Dict[str, Any] = {}
    recommended_action: Dict[str, Any]
    expected_outcome: Dict[str, Any] = {}
    position_sizing: Dict[str, Any] = {}
    executed: bool = False
    execution_delay_ms: Optional[int] = None
    execution_details: Dict[str, Any] = {}


class DailySummaryData(BaseModel):
    """Data model for daily summary"""
    trading_date: date
    total_pnl: Decimal = Decimal("0")
    total_trades: int = 0
    winning_trades: int = 0
    gross_revenue: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    active_agents: int = 0
    best_performing_agent: Optional[str] = None
    worst_performing_agent: Optional[str] = None
    agent_performance: Dict[str, Any] = {}
    active_strategies: int = 0
    best_performing_strategy: Optional[str] = None
    strategy_performance: Dict[str, Any] = {}
    market_conditions: Dict[str, Any] = {}
    volatility_index: Optional[Decimal] = None
    market_sentiment: Optional[str] = None
    max_drawdown: Decimal = Decimal("0")
    var_95: Decimal = Decimal("0")
    sharpe_ratio: Decimal = Decimal("0")
    significant_events: List[Dict[str, Any]] = []
    alerts_triggered: int = 0


class AgentMemoryData(BaseModel):
    """Data model for agent memory persistence"""
    agent_id: str
    memory_type: str  # hot, warm, cold, semantic
    memory_key: str
    memory_data: Dict[str, Any]
    memory_embedding: Optional[List[float]] = None
    created_context: Dict[str, Any] = {}
    expires_at: Optional[datetime] = None
    importance_score: Decimal = Decimal("0.5")


class TradingFarmBrainService:
    """
    Core service for the Trading Farm Brain archive system
    Handles comprehensive storage, retrieval, and analysis of all trading data
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
        
    async def initialize(self):
        """Initialize the service"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("✅ Trading Farm Brain Service initialized")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
            
    # ==========================================
    # STRATEGY ARCHIVAL
    # ==========================================
    
    async def archive_strategy(self, strategy_data: StrategyArchiveData) -> str:
        """Archive a complete strategy with all metadata"""
        try:
            # Convert to database format
            db_data = {
                "strategy_id": strategy_data.strategy_id,
                "strategy_name": strategy_data.strategy_name,
                "strategy_type": strategy_data.strategy_type,
                "version_number": strategy_data.version_number,
                "parent_strategy_id": strategy_data.parent_strategy_id,
                "strategy_code": strategy_data.strategy_code,
                "parameters": strategy_data.parameters,
                "entry_conditions": strategy_data.entry_conditions,
                "exit_conditions": strategy_data.exit_conditions,
                "risk_rules": strategy_data.risk_rules,
                "created_by": strategy_data.created_by,
                "market_conditions": strategy_data.market_conditions or {},
                "asset_classes": strategy_data.asset_classes,
                "timeframes": strategy_data.timeframes,
                "tags": strategy_data.tags,
                "description": strategy_data.description,
                "notes": strategy_data.notes
            }
            
            result = await self.supabase.table("farm_strategy_archive").insert(db_data).execute()
            
            if result.data:
                strategy_id = result.data[0]["id"]
                logger.info(f"Archived strategy: {strategy_data.strategy_name} ({strategy_id})")
                
                # Cache in Redis for quick access
                if self.redis_client:
                    cache_key = f"strategy_archive:{strategy_data.strategy_id}"
                    await self.redis_client.setex(cache_key, 3600, json.dumps(db_data, default=str))
                
                return strategy_id
            else:
                raise HTTPException(status_code=500, detail="Failed to archive strategy")
                
        except Exception as e:
            logger.error(f"Failed to archive strategy {strategy_data.strategy_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Archive failed: {str(e)}")
    
    async def update_strategy_performance(self, strategy_id: str, performance_data: Dict[str, Any]) -> bool:
        """Update strategy performance metrics"""
        try:
            update_data = {
                "total_trades": performance_data.get("total_trades", 0),
                "winning_trades": performance_data.get("winning_trades", 0),
                "total_pnl": float(performance_data.get("total_pnl", 0)),
                "max_drawdown": float(performance_data.get("max_drawdown", 0)),
                "sharpe_ratio": float(performance_data.get("sharpe_ratio", 0)),
                "win_rate": float(performance_data.get("win_rate", 0))
            }
            
            result = await self.supabase.table("farm_strategy_archive")\
                .update(update_data)\
                .eq("strategy_id", strategy_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update strategy performance {strategy_id}: {e}")
            return False
    
    # ==========================================
    # TRADE ARCHIVAL
    # ==========================================
    
    async def archive_trade(self, trade_data: TradeArchiveData) -> str:
        """Archive a complete trade with full context"""
        try:
            # Enrich trade data with additional context
            enriched_trade = await self._enrich_trade_data(trade_data)
            
            # Convert to database format
            db_data = {
                "trade_id": enriched_trade.trade_id,
                "strategy_id": enriched_trade.strategy_id,
                "agent_id": enriched_trade.agent_id,
                "symbol": enriched_trade.symbol,
                "side": enriched_trade.side,
                "quantity": float(enriched_trade.quantity),
                "entry_price": float(enriched_trade.entry_price),
                "exit_price": float(enriched_trade.exit_price) if enriched_trade.exit_price else None,
                "entry_time": enriched_trade.entry_time.isoformat(),
                "exit_time": enriched_trade.exit_time.isoformat() if enriched_trade.exit_time else None,
                "duration_seconds": enriched_trade.duration_seconds,
                "gross_pnl": float(enriched_trade.gross_pnl),
                "fees_paid": float(enriched_trade.fees_paid),
                "net_pnl": float(enriched_trade.net_pnl),
                "pnl_percentage": float(enriched_trade.pnl_percentage),
                "entry_market_data": enriched_trade.entry_market_data,
                "exit_market_data": enriched_trade.exit_market_data,
                "entry_reasoning": enriched_trade.entry_reasoning,
                "exit_reasoning": enriched_trade.exit_reasoning,
                "confidence_level": float(enriched_trade.confidence_level) if enriched_trade.confidence_level else None,
                "decision_factors": enriched_trade.decision_factors,
                "trade_type": enriched_trade.trade_type,
                "exchange": enriched_trade.exchange,
                "order_types": enriched_trade.order_types,
                "stop_loss": float(enriched_trade.stop_loss) if enriched_trade.stop_loss else None,
                "take_profit": float(enriched_trade.take_profit) if enriched_trade.take_profit else None,
                "max_risk": float(enriched_trade.max_risk) if enriched_trade.max_risk else None
            }
            
            result = await self.supabase.table("farm_trade_archive").insert(db_data).execute()
            
            if result.data:
                trade_id = result.data[0]["id"]
                logger.info(f"Archived trade: {enriched_trade.trade_id} ({enriched_trade.symbol})")
                
                # Update daily summary
                await self._update_daily_summary(enriched_trade.entry_time.date(), enriched_trade)
                
                # Update strategy performance
                if enriched_trade.strategy_id:
                    await self._update_strategy_from_trade(enriched_trade.strategy_id, enriched_trade)
                
                return trade_id
            else:
                raise HTTPException(status_code=500, detail="Failed to archive trade")
                
        except Exception as e:
            logger.error(f"Failed to archive trade {trade_data.trade_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Archive failed: {str(e)}")
    
    async def _enrich_trade_data(self, trade_data: TradeArchiveData) -> TradeArchiveData:
        """Enrich trade data with additional context and calculations"""
        # Calculate duration if exit time is available
        if trade_data.exit_time and trade_data.entry_time:
            duration = trade_data.exit_time - trade_data.entry_time
            trade_data.duration_seconds = int(duration.total_seconds())
        
        # Calculate PnL if exit price is available
        if trade_data.exit_price and trade_data.entry_price:
            if trade_data.side.lower() in ["buy", "long"]:
                trade_data.gross_pnl = (trade_data.exit_price - trade_data.entry_price) * trade_data.quantity
            else:  # sell, short
                trade_data.gross_pnl = (trade_data.entry_price - trade_data.exit_price) * trade_data.quantity
            
            trade_data.net_pnl = trade_data.gross_pnl - trade_data.fees_paid
            
            if trade_data.entry_price > 0:
                trade_data.pnl_percentage = (trade_data.net_pnl / (trade_data.entry_price * trade_data.quantity)) * 100
        
        return trade_data
    
    # ==========================================
    # AGENT DECISION ARCHIVAL
    # ==========================================
    
    async def archive_agent_decision(self, decision_data: AgentDecisionArchiveData) -> str:
        """Archive agent decision with complete reasoning"""
        try:
            # Convert to database format
            db_data = {
                "decision_id": decision_data.decision_id,
                "agent_id": decision_data.agent_id,
                "agent_version": decision_data.agent_version,
                "strategy_id": decision_data.strategy_id,
                "decision_type": decision_data.decision_type,
                "symbol": decision_data.symbol,
                "decision_time": decision_data.decision_time.isoformat(),
                "market_data": decision_data.market_data,
                "technical_indicators": decision_data.technical_indicators,
                "fundamental_data": decision_data.fundamental_data,
                "sentiment_data": decision_data.sentiment_data,
                "news_events": decision_data.news_events,
                "reasoning": decision_data.reasoning,
                "confidence_score": float(decision_data.confidence_score) if decision_data.confidence_score else None,
                "alternative_considered": decision_data.alternative_considered,
                "risk_assessment": decision_data.risk_assessment,
                "recommended_action": decision_data.recommended_action,
                "expected_outcome": decision_data.expected_outcome,
                "position_sizing": decision_data.position_sizing,
                "executed": decision_data.executed,
                "execution_delay_ms": decision_data.execution_delay_ms,
                "execution_details": decision_data.execution_details
            }
            
            result = await self.supabase.table("farm_agent_decisions").insert(db_data).execute()
            
            if result.data:
                decision_id = result.data[0]["id"]
                logger.info(f"Archived decision: {decision_data.decision_id} ({decision_data.agent_id})")
                
                # Store in agent memory for learning
                await self._store_decision_memory(decision_data)
                
                return decision_id
            else:
                raise HTTPException(status_code=500, detail="Failed to archive decision")
                
        except Exception as e:
            logger.error(f"Failed to archive decision {decision_data.decision_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Archive failed: {str(e)}")
    
    # ==========================================
    # AGENT MEMORY PERSISTENCE
    # ==========================================
    
    async def persist_agent_memory(self, memory_data: AgentMemoryData) -> str:
        """Persist agent memory for Railway deployment"""
        try:
            # Convert to database format
            db_data = {
                "agent_id": memory_data.agent_id,
                "memory_type": memory_data.memory_type,
                "memory_key": memory_data.memory_key,
                "memory_data": memory_data.memory_data,
                "memory_embedding": memory_data.memory_embedding,
                "created_context": memory_data.created_context,
                "expires_at": memory_data.expires_at.isoformat() if memory_data.expires_at else None,
                "importance_score": float(memory_data.importance_score)
            }
            
            # Upsert to handle updates
            result = await self.supabase.table("farm_agent_memory")\
                .upsert(db_data, on_conflict="agent_id,memory_type,memory_key")\
                .execute()
            
            if result.data:
                memory_id = result.data[0]["id"]
                logger.info(f"Persisted memory: {memory_data.agent_id}:{memory_data.memory_key}")
                
                # Cache in Redis for fast access
                if self.redis_client:
                    cache_key = f"agent_memory:{memory_data.agent_id}:{memory_data.memory_key}"
                    await self.redis_client.setex(cache_key, 86400, json.dumps(memory_data.memory_data, default=str))
                
                return memory_id
            else:
                raise HTTPException(status_code=500, detail="Failed to persist memory")
                
        except Exception as e:
            logger.error(f"Failed to persist memory for {memory_data.agent_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Memory persistence failed: {str(e)}")
    
    async def get_agent_memory(self, agent_id: str, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve agent memory"""
        try:
            query = self.supabase.table("farm_agent_memory").select("*").eq("agent_id", agent_id)
            
            if memory_type:
                query = query.eq("memory_type", memory_type)
            
            result = await query.order("importance_score", desc=True).limit(100).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get agent memory for {agent_id}: {e}")
            return []
    
    # ==========================================
    # CALENDAR AND DAILY SUMMARY
    # ==========================================
    
    async def get_calendar_data(self, month: int, year: int) -> List[Dict[str, Any]]:
        """Get calendar data for dashboard"""
        try:
            start_date = f"{year}-{month:02d}-01"
            # Get last day of month
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{month + 1:02d}-01"
            
            result = await self.supabase.table("farm_daily_summary")\
                .select("*")\
                .gte("trading_date", start_date)\
                .lt("trading_date", end_date)\
                .order("trading_date")\
                .execute()
            
            # Fill in missing dates with zero data
            calendar_data = self._fill_calendar_gaps(result.data if result.data else [], month, year)
            
            return calendar_data
            
        except Exception as e:
            logger.error(f"Failed to get calendar data for {year}-{month}: {e}")
            return []
    
    async def get_daily_performance(self, target_date: str) -> Dict[str, Any]:
        """Get detailed daily performance data"""
        try:
            # Get daily summary
            summary_result = await self.supabase.table("farm_daily_summary")\
                .select("*")\
                .eq("trading_date", target_date)\
                .execute()
            
            # Get all trades for the day
            trades_result = await self.supabase.table("farm_trade_archive")\
                .select("*")\
                .gte("entry_time", f"{target_date} 00:00:00+00")\
                .lte("entry_time", f"{target_date} 23:59:59+00")\
                .order("entry_time")\
                .execute()
            
            # Get agent decisions
            decisions_result = await self.supabase.table("farm_agent_decisions")\
                .select("*")\
                .gte("decision_time", f"{target_date} 00:00:00+00")\
                .lte("decision_time", f"{target_date} 23:59:59+00")\
                .order("decision_time")\
                .execute()
            
            # Calculate detailed metrics
            agent_performance = await self._calculate_agent_daily_performance(target_date)
            strategy_performance = await self._calculate_strategy_daily_performance(target_date)
            
            return {
                "date": target_date,
                "summary": summary_result.data[0] if summary_result.data else None,
                "trades": trades_result.data if trades_result.data else [],
                "decisions": decisions_result.data if decisions_result.data else [],
                "agent_performance": agent_performance,
                "strategy_performance": strategy_performance,
                "trade_count": len(trades_result.data) if trades_result.data else 0,
                "decision_count": len(decisions_result.data) if decisions_result.data else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get daily performance for {target_date}: {e}")
            return {"error": str(e)}
    
    async def _update_daily_summary(self, trading_date: date, trade_data: TradeArchiveData):
        """Update daily summary with new trade data"""
        try:
            date_str = trading_date.isoformat()
            
            # Get existing summary
            existing = await self.supabase.table("farm_daily_summary")\
                .select("*")\
                .eq("trading_date", date_str)\
                .execute()
            
            if existing.data:
                # Update existing summary
                summary = existing.data[0]
                summary["total_trades"] += 1
                summary["total_pnl"] = float(summary.get("total_pnl", 0)) + float(trade_data.net_pnl)
                summary["gross_revenue"] = float(summary.get("gross_revenue", 0)) + float(trade_data.gross_pnl)
                summary["total_fees"] = float(summary.get("total_fees", 0)) + float(trade_data.fees_paid)
                summary["net_profit"] = float(summary.get("net_profit", 0)) + float(trade_data.net_pnl)
                
                if trade_data.net_pnl > 0:
                    summary["winning_trades"] += 1
                
                await self.supabase.table("farm_daily_summary")\
                    .update(summary)\
                    .eq("trading_date", date_str)\
                    .execute()
            else:
                # Create new summary
                new_summary = DailySummaryData(
                    trading_date=trading_date,
                    total_trades=1,
                    winning_trades=1 if trade_data.net_pnl > 0 else 0,
                    total_pnl=trade_data.net_pnl,
                    gross_revenue=trade_data.gross_pnl,
                    total_fees=trade_data.fees_paid,
                    net_profit=trade_data.net_pnl,
                    active_agents=1
                )
                
                await self.supabase.table("farm_daily_summary")\
                    .insert(new_summary.dict())\
                    .execute()
                
        except Exception as e:
            logger.error(f"Failed to update daily summary for {trading_date}: {e}")
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    async def _store_decision_memory(self, decision_data: AgentDecisionArchiveData):
        """Store decision in agent memory for learning"""
        try:
            memory_data = AgentMemoryData(
                agent_id=decision_data.agent_id,
                memory_type="decision",
                memory_key=f"decision_{decision_data.decision_id}",
                memory_data={
                    "decision_id": decision_data.decision_id,
                    "decision_type": decision_data.decision_type,
                    "symbol": decision_data.symbol,
                    "reasoning": decision_data.reasoning,
                    "confidence_score": float(decision_data.confidence_score) if decision_data.confidence_score else None,
                    "outcome": decision_data.expected_outcome
                },
                importance_score=decision_data.confidence_score or Decimal("0.5")
            )
            
            await self.persist_agent_memory(memory_data)
            
        except Exception as e:
            logger.error(f"Failed to store decision memory: {e}")
    
    def _fill_calendar_gaps(self, existing_data: List[Dict], month: int, year: int) -> List[Dict[str, Any]]:
        """Fill missing dates in calendar data with zero values"""
        from calendar import monthrange
        
        # Get number of days in month
        _, days_in_month = monthrange(year, month)
        
        # Create lookup of existing data
        existing_lookup = {item["trading_date"]: item for item in existing_data}
        
        calendar_data = []
        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            
            if date_str in existing_lookup:
                calendar_data.append(existing_lookup[date_str])
            else:
                # Create empty day
                calendar_data.append({
                    "trading_date": date_str,
                    "total_pnl": 0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "active_agents": 0,
                    "net_profit": 0
                })
        
        return calendar_data
    
    async def _calculate_agent_daily_performance(self, date: str) -> Dict[str, Any]:
        """Calculate agent performance for a specific day"""
        try:
            # Get all trades for the day grouped by agent
            result = await self.supabase.table("farm_trade_archive")\
                .select("agent_id, net_pnl, trade_id")\
                .gte("entry_time", f"{date} 00:00:00+00")\
                .lte("entry_time", f"{date} 23:59:59+00")\
                .execute()
            
            if not result.data:
                return {}
            
            # Group by agent
            agent_performance = {}
            for trade in result.data:
                agent_id = trade["agent_id"]
                if agent_id not in agent_performance:
                    agent_performance[agent_id] = {
                        "pnl": 0,
                        "trades": 0,
                        "winning_trades": 0
                    }
                
                agent_performance[agent_id]["pnl"] += float(trade["net_pnl"])
                agent_performance[agent_id]["trades"] += 1
                if float(trade["net_pnl"]) > 0:
                    agent_performance[agent_id]["winning_trades"] += 1
            
            # Calculate win rates
            for agent_id, perf in agent_performance.items():
                if perf["trades"] > 0:
                    perf["win_rate"] = perf["winning_trades"] / perf["trades"]
                else:
                    perf["win_rate"] = 0
            
            return agent_performance
            
        except Exception as e:
            logger.error(f"Failed to calculate agent daily performance: {e}")
            return {}
    
    async def _calculate_strategy_daily_performance(self, date: str) -> Dict[str, Any]:
        """Calculate strategy performance for a specific day"""
        try:
            # Get all trades for the day grouped by strategy
            result = await self.supabase.table("farm_trade_archive")\
                .select("strategy_id, net_pnl, trade_id")\
                .gte("entry_time", f"{date} 00:00:00+00")\
                .lte("entry_time", f"{date} 23:59:59+00")\
                .execute()
            
            if not result.data:
                return {}
            
            # Group by strategy
            strategy_performance = {}
            for trade in result.data:
                strategy_id = trade["strategy_id"]
                if not strategy_id:
                    continue
                    
                if strategy_id not in strategy_performance:
                    strategy_performance[strategy_id] = {
                        "pnl": 0,
                        "trades": 0,
                        "winning_trades": 0
                    }
                
                strategy_performance[strategy_id]["pnl"] += float(trade["net_pnl"])
                strategy_performance[strategy_id]["trades"] += 1
                if float(trade["net_pnl"]) > 0:
                    strategy_performance[strategy_id]["winning_trades"] += 1
            
            # Calculate win rates
            for strategy_id, perf in strategy_performance.items():
                if perf["trades"] > 0:
                    perf["win_rate"] = perf["winning_trades"] / perf["trades"]
                else:
                    perf["win_rate"] = 0
            
            return strategy_performance
            
        except Exception as e:
            logger.error(f"Failed to calculate strategy daily performance: {e}")
            return {}
    
    async def _update_strategy_from_trade(self, strategy_id: str, trade_data: TradeArchiveData):
        """Update strategy performance from trade data"""
        try:
            # This would update the strategy archive with latest trade results
            # Implementation depends on how you want to track strategy performance
            pass
        except Exception as e:
            logger.error(f"Failed to update strategy from trade: {e}")


# Global service instance
_trading_farm_brain_service: Optional[TradingFarmBrainService] = None


async def get_trading_farm_brain_service() -> TradingFarmBrainService:
    """Get the global trading farm brain service instance"""
    global _trading_farm_brain_service
    
    if _trading_farm_brain_service is None:
        _trading_farm_brain_service = TradingFarmBrainService()
        await _trading_farm_brain_service.initialize()
    
    return _trading_farm_brain_service