"""
Trading Safety Service - Phase 2 Implementation
Advanced safety controls and circuit breakers for live trading
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Literal
from loguru import logger
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from collections import defaultdict

class SafetyViolation(BaseModel):
    """Safety violation record"""
    violation_id: str
    violation_type: str
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    agent_id: Optional[str] = None
    symbol: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status"""
    name: str
    status: Literal["closed", "open", "half_open"]
    trigger_count: int
    last_triggered: Optional[datetime] = None
    next_retry: Optional[datetime] = None
    threshold: int
    reset_time_minutes: int

@dataclass
class TradingLimits:
    """Trading limits configuration"""
    max_daily_trades: int = 100
    max_daily_volume_usd: float = 100000.0
    max_position_size_usd: float = 10000.0
    max_concurrent_positions: int = 10
    max_drawdown_percentage: float = 0.05  # 5%
    max_loss_per_hour_usd: float = 1000.0
    emergency_stop_loss_percentage: float = 0.10  # 10%

@dataclass
class AgentLimits:
    """Per-agent trading limits"""
    agent_id: str
    daily_trades: int = 0
    daily_volume_usd: float = 0.0
    concurrent_positions: int = 0
    hourly_loss_usd: float = 0.0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class TradingSafetyService:
    """
    Advanced trading safety service with circuit breakers and risk controls
    """
    
    def __init__(self):
        self.trading_limits = TradingLimits()
        self.agent_limits: Dict[str, AgentLimits] = {}
        self.circuit_breakers: Dict[str, CircuitBreakerStatus] = {}
        self.safety_violations: List[SafetyViolation] = []
        self.emergency_stop_active = False
        self.trading_suspended = False
        
        # Initialize circuit breakers
        self._initialize_circuit_breakers()
        
        # Start monitoring tasks
        self._start_monitoring_tasks()
        
        logger.info("TradingSafetyService initialized with comprehensive safety controls")
    
    def _initialize_circuit_breakers(self):
        """Initialize circuit breaker configurations"""
        breakers = [
            {
                "name": "rapid_loss_breaker",
                "threshold": 5,  # 5 losses in reset period
                "reset_time_minutes": 30
            },
            {
                "name": "high_frequency_breaker", 
                "threshold": 50,  # 50 trades in reset period
                "reset_time_minutes": 60
            },
            {
                "name": "volume_spike_breaker",
                "threshold": 3,  # 3 volume spikes in reset period
                "reset_time_minutes": 15
            },
            {
                "name": "error_rate_breaker",
                "threshold": 10,  # 10 errors in reset period
                "reset_time_minutes": 20
            }
        ]
        
        for breaker in breakers:
            self.circuit_breakers[breaker["name"]] = CircuitBreakerStatus(
                name=breaker["name"],
                status="closed",
                trigger_count=0,
                threshold=breaker["threshold"],
                reset_time_minutes=breaker["reset_time_minutes"]
            )
    
    def _start_monitoring_tasks(self):
        """Start background monitoring tasks"""
        # In a real implementation, these would be async tasks
        # For now, we'll track them as attributes
        self.last_cleanup = datetime.now(timezone.utc)
        self.last_health_check = datetime.now(timezone.utc)
    
    async def validate_trade_safety(
        self, 
        agent_id: str, 
        symbol: str, 
        quantity: float,
        price: Optional[float] = None,
        trade_type: str = "market"
    ) -> tuple[bool, Optional[str]]:
        """
        Comprehensive trade safety validation
        Returns: (is_safe, rejection_reason)
        """
        
        # Check emergency stop
        if self.emergency_stop_active:
            return False, "Emergency stop is active - all trading suspended"
        
        # Check trading suspension
        if self.trading_suspended:
            return False, "Trading is temporarily suspended"
        
        # Check circuit breakers
        for breaker_name, breaker in self.circuit_breakers.items():
            if breaker.status == "open":
                return False, f"Circuit breaker '{breaker_name}' is open"
        
        # Initialize agent limits if not exists
        if agent_id not in self.agent_limits:
            self.agent_limits[agent_id] = AgentLimits(agent_id=agent_id)
        
        agent_limits = self.agent_limits[agent_id]
        
        # Reset daily limits if needed
        if self._should_reset_daily_limits(agent_limits):
            self._reset_daily_limits(agent_limits)
        
        # Calculate trade value
        trade_value_usd = quantity * (price or 0)
        
        # Check daily trade count limit
        if agent_limits.daily_trades >= self.trading_limits.max_daily_trades:
            await self._record_violation(
                "daily_trade_limit",
                "high",
                f"Agent {agent_id} exceeded daily trade limit",
                agent_id=agent_id
            )
            return False, f"Daily trade limit exceeded ({self.trading_limits.max_daily_trades})"
        
        # Check daily volume limit
        if agent_limits.daily_volume_usd + trade_value_usd > self.trading_limits.max_daily_volume_usd:
            await self._record_violation(
                "daily_volume_limit",
                "high", 
                f"Agent {agent_id} would exceed daily volume limit",
                agent_id=agent_id
            )
            return False, f"Daily volume limit would be exceeded"
        
        # Check position size limit
        if trade_value_usd > self.trading_limits.max_position_size_usd:
            await self._record_violation(
                "position_size_limit",
                "medium",
                f"Trade size {trade_value_usd} exceeds limit",
                agent_id=agent_id,
                symbol=symbol
            )
            return False, f"Position size exceeds limit ({self.trading_limits.max_position_size_usd})"
        
        # Check concurrent positions limit
        if agent_limits.concurrent_positions >= self.trading_limits.max_concurrent_positions:
            await self._record_violation(
                "concurrent_positions_limit",
                "medium",
                f"Agent {agent_id} at concurrent position limit",
                agent_id=agent_id
            )
            return False, f"Concurrent positions limit reached ({self.trading_limits.max_concurrent_positions})"
        
        # All safety checks passed
        return True, None
    
    async def record_trade_execution(
        self,
        agent_id: str,
        symbol: str, 
        quantity: float,
        price: float,
        side: str,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Record trade execution for safety monitoring"""
        
        if agent_id not in self.agent_limits:
            self.agent_limits[agent_id] = AgentLimits(agent_id=agent_id)
        
        agent_limits = self.agent_limits[agent_id]
        trade_value_usd = quantity * price
        
        if success:
            # Update limits tracking
            agent_limits.daily_trades += 1
            agent_limits.daily_volume_usd += trade_value_usd
            
            if side.lower() == "buy":
                agent_limits.concurrent_positions += 1
            elif side.lower() == "sell":
                agent_limits.concurrent_positions = max(0, agent_limits.concurrent_positions - 1)
            
            logger.info(f"Recorded successful trade for agent {agent_id}: {side} {quantity} {symbol} @ {price}")
        else:
            # Record failed trade
            await self._record_violation(
                "trade_execution_failure",
                "low",
                f"Trade execution failed: {error_message}",
                agent_id=agent_id,
                symbol=symbol,
                metadata={"error": error_message}
            )
            
            # Trigger error rate circuit breaker
            await self._trigger_circuit_breaker("error_rate_breaker")
    
    async def record_trade_loss(self, agent_id: str, loss_amount_usd: float):
        """Record trading loss for safety monitoring"""
        
        if agent_id not in self.agent_limits:
            self.agent_limits[agent_id] = AgentLimits(agent_id=agent_id)
        
        agent_limits = self.agent_limits[agent_id]
        agent_limits.hourly_loss_usd += loss_amount_usd
        
        # Check for rapid loss circuit breaker
        if loss_amount_usd > 500:  # Significant loss threshold
            await self._trigger_circuit_breaker("rapid_loss_breaker")
        
        # Check hourly loss limit
        if agent_limits.hourly_loss_usd > self.trading_limits.max_loss_per_hour_usd:
            await self._record_violation(
                "hourly_loss_limit",
                "critical",
                f"Agent {agent_id} exceeded hourly loss limit: ${agent_limits.hourly_loss_usd:.2f}",
                agent_id=agent_id
            )
            
            # Suspend trading for this agent
            await self.suspend_agent_trading(agent_id, "Hourly loss limit exceeded")
    
    async def _trigger_circuit_breaker(self, breaker_name: str):
        """Trigger a circuit breaker"""
        if breaker_name not in self.circuit_breakers:
            return
        
        breaker = self.circuit_breakers[breaker_name]
        breaker.trigger_count += 1
        
        if breaker.trigger_count >= breaker.threshold:
            breaker.status = "open"
            breaker.last_triggered = datetime.now(timezone.utc)
            breaker.next_retry = breaker.last_triggered + timedelta(minutes=breaker.reset_time_minutes)
            
            await self._record_violation(
                "circuit_breaker_triggered",
                "critical",
                f"Circuit breaker '{breaker_name}' triggered",
                metadata={"breaker": breaker_name, "count": breaker.trigger_count}
            )
            
            logger.warning(f"Circuit breaker '{breaker_name}' OPENED - trading restricted")
    
    async def _record_violation(
        self,
        violation_type: str,
        severity: str,
        message: str,
        agent_id: Optional[str] = None,
        symbol: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a safety violation"""
        violation = SafetyViolation(
            violation_id=f"viol_{len(self.safety_violations) + 1:06d}",
            violation_type=violation_type,
            severity=severity,
            message=message,
            agent_id=agent_id,
            symbol=symbol,
            metadata=metadata or {}
        )
        
        self.safety_violations.append(violation)
        logger.warning(f"Safety violation [{severity}]: {message}")
        
        # Auto-trigger emergency stop for critical violations
        if severity == "critical":
            critical_count = sum(1 for v in self.safety_violations[-10:] if v.severity == "critical")
            if critical_count >= 3:  # 3 critical violations in last 10
                await self.activate_emergency_stop("Multiple critical safety violations")
    
    def _should_reset_daily_limits(self, agent_limits: AgentLimits) -> bool:
        """Check if daily limits should be reset"""
        now = datetime.now(timezone.utc)
        return (now - agent_limits.last_reset).days >= 1
    
    def _reset_daily_limits(self, agent_limits: AgentLimits):
        """Reset daily limits for an agent"""
        agent_limits.daily_trades = 0
        agent_limits.daily_volume_usd = 0.0
        agent_limits.hourly_loss_usd = 0.0
        agent_limits.last_reset = datetime.now(timezone.utc)
        logger.info(f"Reset daily limits for agent {agent_limits.agent_id}")
    
    async def activate_emergency_stop(self, reason: str):
        """Activate emergency stop - halt all trading"""
        self.emergency_stop_active = True
        await self._record_violation(
            "emergency_stop_activated",
            "critical", 
            f"Emergency stop activated: {reason}",
            metadata={"reason": reason}
        )
        logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")
    
    async def deactivate_emergency_stop(self):
        """Deactivate emergency stop"""
        self.emergency_stop_active = False
        logger.info("Emergency stop deactivated - trading can resume")
    
    async def suspend_trading(self, reason: str):
        """Suspend all trading temporarily"""
        self.trading_suspended = True
        await self._record_violation(
            "trading_suspended",
            "high",
            f"Trading suspended: {reason}",
            metadata={"reason": reason}
        )
        logger.warning(f"Trading suspended: {reason}")
    
    async def resume_trading(self):
        """Resume trading after suspension"""
        self.trading_suspended = False
        logger.info("Trading resumed")
    
    async def suspend_agent_trading(self, agent_id: str, reason: str):
        """Suspend trading for specific agent"""
        # In a real implementation, this would integrate with agent management
        await self._record_violation(
            "agent_trading_suspended",
            "high",
            f"Agent {agent_id} trading suspended: {reason}",
            agent_id=agent_id,
            metadata={"reason": reason}
        )
        logger.warning(f"Agent {agent_id} trading suspended: {reason}")
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get comprehensive safety status"""
        return {
            "emergency_stop_active": self.emergency_stop_active,
            "trading_suspended": self.trading_suspended,
            "circuit_breakers": {
                name: {
                    "status": breaker.status,
                    "trigger_count": breaker.trigger_count,
                    "last_triggered": breaker.last_triggered.isoformat() if breaker.last_triggered else None,
                    "next_retry": breaker.next_retry.isoformat() if breaker.next_retry else None
                }
                for name, breaker in self.circuit_breakers.items()
            },
            "recent_violations": [
                {
                    "violation_id": v.violation_id,
                    "type": v.violation_type,
                    "severity": v.severity,
                    "message": v.message,
                    "timestamp": v.timestamp.isoformat()
                }
                for v in self.safety_violations[-10:]  # Last 10 violations
            ],
            "active_agents": len(self.agent_limits),
            "trading_limits": {
                "max_daily_trades": self.trading_limits.max_daily_trades,
                "max_daily_volume_usd": self.trading_limits.max_daily_volume_usd,
                "max_position_size_usd": self.trading_limits.max_position_size_usd,
                "max_concurrent_positions": self.trading_limits.max_concurrent_positions
            }
        }
    
    def get_agent_safety_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get safety status for specific agent"""
        if agent_id not in self.agent_limits:
            return None
        
        limits = self.agent_limits[agent_id]
        return {
            "agent_id": agent_id,
            "daily_trades": limits.daily_trades,
            "daily_volume_usd": limits.daily_volume_usd,
            "concurrent_positions": limits.concurrent_positions,
            "hourly_loss_usd": limits.hourly_loss_usd,
            "last_reset": limits.last_reset.isoformat(),
            "limits": {
                "max_daily_trades": self.trading_limits.max_daily_trades,
                "max_daily_volume_usd": self.trading_limits.max_daily_volume_usd,
                "max_concurrent_positions": self.trading_limits.max_concurrent_positions,
                "max_loss_per_hour_usd": self.trading_limits.max_loss_per_hour_usd
            }
        }

# Factory function for service registry
def create_trading_safety_service() -> TradingSafetyService:
    """Factory function to create trading safety service"""
    return TradingSafetyService()