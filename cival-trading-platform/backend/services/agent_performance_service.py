"""
Agent Performance Service - Phase 2 Implementation
Tracks and analyzes AI agent trading performance with comprehensive metrics
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Literal
from loguru import logger
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

class TradeRecord(BaseModel):
    """Individual trade record"""
    trade_id: str
    agent_id: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    strategy: str
    confidence: float
    pnl_usd: Optional[float] = None
    fees_usd: float = 0.0
    status: Literal["open", "closed", "cancelled"]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PerformanceMetrics(BaseModel):
    """Performance metrics for an agent"""
    agent_id: str
    period_start: datetime
    period_end: datetime
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # PnL metrics
    total_pnl_usd: float = 0.0
    gross_profit_usd: float = 0.0
    gross_loss_usd: float = 0.0
    net_profit_usd: float = 0.0
    average_win_usd: float = 0.0
    average_loss_usd: float = 0.0
    profit_factor: float = 0.0
    
    # Risk metrics
    max_drawdown_usd: float = 0.0
    max_drawdown_percentage: float = 0.0
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    
    # Efficiency metrics
    average_trade_duration_hours: float = 0.0
    trades_per_day: float = 0.0
    volume_traded_usd: float = 0.0
    fees_paid_usd: float = 0.0
    
    # Strategy performance
    best_strategy: Optional[str] = None
    worst_strategy: Optional[str] = None
    strategy_performance: Dict[str, float] = Field(default_factory=dict)
    
    # Recent performance
    last_7_days_pnl: float = 0.0
    last_30_days_pnl: float = 0.0
    current_streak: int = 0  # Positive for winning streak, negative for losing
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentRanking(BaseModel):
    """Agent ranking information"""
    agent_id: str
    rank: int
    score: float
    total_pnl_usd: float
    win_rate: float
    sharpe_ratio: Optional[float] = None
    risk_adjusted_return: float = 0.0

@dataclass
class PerformanceTracker:
    """Real-time performance tracking for an agent"""
    agent_id: str
    trades: List[TradeRecord] = field(default_factory=list)
    daily_pnl: deque = field(default_factory=lambda: deque(maxlen=365))  # Last 365 days
    running_pnl: float = 0.0
    peak_pnl: float = 0.0
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class AgentPerformanceService:
    """
    Comprehensive agent performance tracking and analytics service
    """
    
    def __init__(self):
        self.performance_trackers: Dict[str, PerformanceTracker] = {}
        self.trade_records: List[TradeRecord] = []
        self.performance_cache: Dict[str, PerformanceMetrics] = {}
        self.cache_expiry_minutes = 5  # Cache metrics for 5 minutes
        
        logger.info("AgentPerformanceService initialized")
    
    async def record_trade_entry(
        self,
        trade_id: str,
        agent_id: str,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        strategy: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TradeRecord:
        """Record a new trade entry"""
        
        trade = TradeRecord(
            trade_id=trade_id,
            agent_id=agent_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=datetime.now(timezone.utc),
            strategy=strategy,
            confidence=confidence,
            status="open",
            metadata=metadata or {}
        )
        
        self.trade_records.append(trade)
        
        # Initialize tracker if needed
        if agent_id not in self.performance_trackers:
            self.performance_trackers[agent_id] = PerformanceTracker(agent_id=agent_id)
        
        tracker = self.performance_trackers[agent_id]
        tracker.trades.append(trade)
        tracker.last_updated = datetime.now(timezone.utc)
        
        # Invalidate cache
        self.performance_cache.pop(agent_id, None)
        
        logger.info(f"Recorded trade entry for agent {agent_id}: {side} {quantity} {symbol} @ {entry_price}")
        return trade
    
    async def record_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        fees_usd: float = 0.0,
        exit_time: Optional[datetime] = None
    ) -> Optional[TradeRecord]:
        """Record trade exit and calculate PnL"""
        
        # Find the trade
        trade = None
        for t in self.trade_records:
            if t.trade_id == trade_id:
                trade = t
                break
        
        if not trade:
            logger.warning(f"Trade {trade_id} not found for exit recording")
            return None
        
        if trade.status != "open":
            logger.warning(f"Trade {trade_id} is not open (status: {trade.status})")
            return None
        
        # Update trade record
        trade.exit_price = exit_price
        trade.exit_time = exit_time or datetime.now(timezone.utc)
        trade.fees_usd = fees_usd
        trade.status = "closed"
        
        # Calculate PnL
        if trade.side == "buy":
            pnl = (exit_price - trade.entry_price) * trade.quantity
        else:  # sell
            pnl = (trade.entry_price - exit_price) * trade.quantity
        
        trade.pnl_usd = pnl - fees_usd
        
        # Update performance tracker
        tracker = self.performance_trackers[trade.agent_id]
        tracker.running_pnl += trade.pnl_usd
        
        # Update drawdown tracking
        if tracker.running_pnl > tracker.peak_pnl:
            tracker.peak_pnl = tracker.running_pnl
            tracker.current_drawdown = 0.0
        else:
            tracker.current_drawdown = tracker.peak_pnl - tracker.running_pnl
            if tracker.current_drawdown > tracker.max_drawdown:
                tracker.max_drawdown = tracker.current_drawdown
        
        # Add to daily PnL tracking
        today = datetime.now(timezone.utc).date()
        if not tracker.daily_pnl or tracker.daily_pnl[-1][0] != today:
            tracker.daily_pnl.append((today, trade.pnl_usd))
        else:
            # Update today's PnL
            current_date, current_pnl = tracker.daily_pnl[-1]
            tracker.daily_pnl[-1] = (current_date, current_pnl + trade.pnl_usd)
        
        tracker.last_updated = datetime.now(timezone.utc)
        
        # Invalidate cache
        self.performance_cache.pop(trade.agent_id, None)
        
        logger.info(f"Recorded trade exit for agent {trade.agent_id}: {trade.trade_id} PnL: ${trade.pnl_usd:.2f}")
        return trade
    
    async def get_agent_performance(
        self, 
        agent_id: str, 
        period_days: int = 30,
        force_refresh: bool = False
    ) -> Optional[PerformanceMetrics]:
        """Get comprehensive performance metrics for an agent"""
        
        # Check cache
        cache_key = f"{agent_id}_{period_days}"
        if not force_refresh and cache_key in self.performance_cache:
            cached_metrics = self.performance_cache[cache_key]
            cache_age = datetime.now(timezone.utc) - cached_metrics.timestamp
            if cache_age.total_seconds() < self.cache_expiry_minutes * 60:
                return cached_metrics
        
        if agent_id not in self.performance_trackers:
            return None
        
        tracker = self.performance_trackers[agent_id]
        
        # Filter trades by period
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
        period_trades = [
            trade for trade in tracker.trades
            if trade.entry_time >= cutoff_date and trade.status == "closed"
        ]
        
        if not period_trades:
            return None
        
        # Calculate metrics
        metrics = await self._calculate_performance_metrics(
            agent_id, period_trades, period_days, tracker
        )
        
        # Cache the results
        self.performance_cache[cache_key] = metrics
        
        return metrics
    
    async def _calculate_performance_metrics(
        self,
        agent_id: str,
        trades: List[TradeRecord],
        period_days: int,
        tracker: PerformanceTracker
    ) -> PerformanceMetrics:
        """Calculate detailed performance metrics"""
        
        period_start = datetime.now(timezone.utc) - timedelta(days=period_days)
        period_end = datetime.now(timezone.utc)
        
        # Basic trade statistics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl_usd and t.pnl_usd > 0])
        losing_trades = len([t for t in trades if t.pnl_usd and t.pnl_usd < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # PnL calculations
        pnls = [t.pnl_usd for t in trades if t.pnl_usd is not None]
        total_pnl_usd = sum(pnls)
        gross_profit_usd = sum(pnl for pnl in pnls if pnl > 0)
        gross_loss_usd = abs(sum(pnl for pnl in pnls if pnl < 0))
        net_profit_usd = total_pnl_usd
        
        # Average win/loss
        winning_pnls = [pnl for pnl in pnls if pnl > 0]
        losing_pnls = [pnl for pnl in pnls if pnl < 0]
        average_win_usd = statistics.mean(winning_pnls) if winning_pnls else 0.0
        average_loss_usd = abs(statistics.mean(losing_pnls)) if losing_pnls else 0.0
        
        # Profit factor
        profit_factor = gross_profit_usd / gross_loss_usd if gross_loss_usd > 0 else 0.0
        
        # Risk metrics
        max_drawdown_usd = tracker.max_drawdown
        max_drawdown_percentage = (max_drawdown_usd / tracker.peak_pnl * 100) if tracker.peak_pnl > 0 else 0.0
        
        # Calculate Sharpe and Sortino ratios
        sharpe_ratio = None
        sortino_ratio = None
        if len(pnls) > 1:
            returns_std = statistics.stdev(pnls)
            if returns_std > 0:
                sharpe_ratio = statistics.mean(pnls) / returns_std
                
                # Sortino ratio (downside deviation)
                negative_returns = [pnl for pnl in pnls if pnl < 0]
                if negative_returns:
                    downside_std = statistics.stdev(negative_returns)
                    if downside_std > 0:
                        sortino_ratio = statistics.mean(pnls) / downside_std
        
        # Efficiency metrics
        durations = []
        for trade in trades:
            if trade.exit_time and trade.entry_time:
                duration = (trade.exit_time - trade.entry_time).total_seconds() / 3600  # hours
                durations.append(duration)
        
        average_trade_duration_hours = statistics.mean(durations) if durations else 0.0
        trades_per_day = total_trades / period_days if period_days > 0 else 0.0
        volume_traded_usd = sum(t.quantity * t.entry_price for t in trades)
        fees_paid_usd = sum(t.fees_usd for t in trades)
        
        # Strategy performance
        strategy_pnls = defaultdict(list)
        for trade in trades:
            if trade.pnl_usd is not None:
                strategy_pnls[trade.strategy].append(trade.pnl_usd)
        
        strategy_performance = {
            strategy: sum(pnls) for strategy, pnls in strategy_pnls.items()
        }
        
        best_strategy = max(strategy_performance, key=strategy_performance.get) if strategy_performance else None
        worst_strategy = min(strategy_performance, key=strategy_performance.get) if strategy_performance else None
        
        # Recent performance
        last_7_days_pnl = sum(
            t.pnl_usd for t in trades
            if t.pnl_usd and t.entry_time >= datetime.now(timezone.utc) - timedelta(days=7)
        )
        last_30_days_pnl = sum(
            t.pnl_usd for t in trades
            if t.pnl_usd and t.entry_time >= datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        # Current streak
        current_streak = self._calculate_current_streak(trades)
        
        return PerformanceMetrics(
            agent_id=agent_id,
            period_start=period_start,
            period_end=period_end,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl_usd=total_pnl_usd,
            gross_profit_usd=gross_profit_usd,
            gross_loss_usd=gross_loss_usd,
            net_profit_usd=net_profit_usd,
            average_win_usd=average_win_usd,
            average_loss_usd=average_loss_usd,
            profit_factor=profit_factor,
            max_drawdown_usd=max_drawdown_usd,
            max_drawdown_percentage=max_drawdown_percentage,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            average_trade_duration_hours=average_trade_duration_hours,
            trades_per_day=trades_per_day,
            volume_traded_usd=volume_traded_usd,
            fees_paid_usd=fees_paid_usd,
            best_strategy=best_strategy,
            worst_strategy=worst_strategy,
            strategy_performance=strategy_performance,
            last_7_days_pnl=last_7_days_pnl,
            last_30_days_pnl=last_30_days_pnl,
            current_streak=current_streak
        )
    
    def _calculate_current_streak(self, trades: List[TradeRecord]) -> int:
        """Calculate current winning/losing streak"""
        if not trades:
            return 0
        
        # Sort by exit time (most recent first)
        sorted_trades = sorted(
            [t for t in trades if t.pnl_usd is not None and t.exit_time],
            key=lambda x: x.exit_time,
            reverse=True
        )
        
        if not sorted_trades:
            return 0
        
        streak = 0
        last_was_win = sorted_trades[0].pnl_usd > 0
        
        for trade in sorted_trades:
            is_win = trade.pnl_usd > 0
            if is_win == last_was_win:
                streak += 1 if is_win else -1
            else:
                break
        
        return streak
    
    async def get_agent_rankings(self, period_days: int = 30) -> List[AgentRanking]:
        """Get agent performance rankings"""
        rankings = []
        
        for agent_id in self.performance_trackers.keys():
            metrics = await self.get_agent_performance(agent_id, period_days)
            if metrics and metrics.total_trades > 0:
                
                # Calculate composite score
                score = self._calculate_performance_score(metrics)
                
                rankings.append(AgentRanking(
                    agent_id=agent_id,
                    rank=0,  # Will be set after sorting
                    score=score,
                    total_pnl_usd=metrics.total_pnl_usd,
                    win_rate=metrics.win_rate,
                    sharpe_ratio=metrics.sharpe_ratio,
                    risk_adjusted_return=metrics.total_pnl_usd / max(metrics.max_drawdown_usd, 1.0)
                ))
        
        # Sort by score and assign ranks
        rankings.sort(key=lambda x: x.score, reverse=True)
        for i, ranking in enumerate(rankings):
            ranking.rank = i + 1
        
        return rankings
    
    def _calculate_performance_score(self, metrics: PerformanceMetrics) -> float:
        """Calculate composite performance score"""
        # Weighted scoring based on multiple factors
        pnl_score = max(0, metrics.total_pnl_usd / 1000.0)  # Normalize to thousands
        win_rate_score = metrics.win_rate * 100
        profit_factor_score = min(metrics.profit_factor * 10, 50)  # Cap at 50
        sharpe_score = (metrics.sharpe_ratio * 20) if metrics.sharpe_ratio else 0
        
        # Penalty for high drawdown
        drawdown_penalty = max(0, metrics.max_drawdown_percentage - 10) * 2
        
        score = (pnl_score * 0.3 + 
                win_rate_score * 0.25 + 
                profit_factor_score * 0.2 + 
                sharpe_score * 0.25 - 
                drawdown_penalty)
        
        return max(0, score)
    
    async def get_portfolio_performance(self, period_days: int = 30) -> Dict[str, Any]:
        """Get overall portfolio performance across all agents"""
        all_metrics = []
        
        for agent_id in self.performance_trackers.keys():
            metrics = await self.get_agent_performance(agent_id, period_days)
            if metrics:
                all_metrics.append(metrics)
        
        if not all_metrics:
            return {"error": "No performance data available"}
        
        # Aggregate metrics
        total_pnl = sum(m.total_pnl_usd for m in all_metrics)
        total_trades = sum(m.total_trades for m in all_metrics)
        total_winning = sum(m.winning_trades for m in all_metrics)
        total_volume = sum(m.volume_traded_usd for m in all_metrics)
        total_fees = sum(m.fees_paid_usd for m in all_metrics)
        
        overall_win_rate = total_winning / total_trades if total_trades > 0 else 0.0
        
        # Best and worst performing agents
        best_agent = max(all_metrics, key=lambda x: x.total_pnl_usd)
        worst_agent = min(all_metrics, key=lambda x: x.total_pnl_usd)
        
        return {
            "portfolio_performance": {
                "total_pnl_usd": total_pnl,
                "total_trades": total_trades,
                "overall_win_rate": overall_win_rate,
                "total_volume_usd": total_volume,
                "total_fees_usd": total_fees,
                "active_agents": len(all_metrics),
                "period_days": period_days
            },
            "best_performer": {
                "agent_id": best_agent.agent_id,
                "pnl_usd": best_agent.total_pnl_usd,
                "win_rate": best_agent.win_rate
            },
            "worst_performer": {
                "agent_id": worst_agent.agent_id,
                "pnl_usd": worst_agent.total_pnl_usd, 
                "win_rate": worst_agent.win_rate
            }
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get performance service status"""
        return {
            "service_status": "online",
            "tracked_agents": len(self.performance_trackers),
            "total_trade_records": len(self.trade_records),
            "cached_metrics": len(self.performance_cache),
            "last_updated": max(
                (tracker.last_updated for tracker in self.performance_trackers.values()),
                default=datetime.now(timezone.utc)
            ).isoformat()
        }

# Factory function for service registry
def create_agent_performance_service() -> AgentPerformanceService:
    """Factory function to create agent performance service"""
    return AgentPerformanceService()