"""
Real-time Alerting and Notification Service - Phase 5 Implementation
Comprehensive alerting system for trading operations and risk management
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Literal, Callable
from loguru import logger
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum
import uuid
from collections import defaultdict, deque

class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertCategory(str, Enum):
    """Alert categories"""
    TRADING = "trading"
    RISK = "risk"
    PERFORMANCE = "performance"
    SYSTEM = "system"
    MARKET = "market"
    AGENT = "agent"
    PORTFOLIO = "portfolio"

class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"
    SLACK = "slack"
    DISCORD = "discord"
    PUSH = "push"

class AlertRule(BaseModel):
    """Alert rule configuration"""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: AlertCategory
    severity: AlertSeverity
    
    # Trigger conditions
    condition_type: str  # "threshold", "change", "pattern", "custom"
    condition_parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Notification settings
    notification_channels: List[NotificationChannel] = Field(default_factory=list)
    notification_throttle_minutes: int = 15  # Minimum time between notifications
    
    # Targeting
    target_agents: List[str] = Field(default_factory=list)  # Empty = all agents
    target_symbols: List[str] = Field(default_factory=list)  # Empty = all symbols
    
    # Rule status
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

class Alert(BaseModel):
    """Alert instance"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str
    title: str
    message: str
    category: AlertCategory
    severity: AlertSeverity
    
    # Context
    agent_id: Optional[str] = None
    symbol: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Status
    status: Literal["active", "acknowledged", "resolved"] = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Delivery tracking
    notifications_sent: List[str] = Field(default_factory=list)
    delivery_attempts: int = 0

class NotificationTemplate(BaseModel):
    """Notification message template"""
    template_id: str
    category: AlertCategory
    severity: AlertSeverity
    channel: NotificationChannel
    
    subject_template: str
    body_template: str
    
    # Channel-specific formatting
    formatting_options: Dict[str, Any] = Field(default_factory=dict)

@dataclass
class NotificationHistory:
    """Notification delivery history"""
    alert_id: str
    channel: NotificationChannel
    recipient: str
    status: str  # "sent", "failed", "delivered", "opened"
    timestamp: datetime
    error_message: Optional[str] = None

class AlertingService:
    """
    Real-time alerting and notification service for trading operations
    """
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_history: List[NotificationHistory] = []
        self.notification_templates: Dict[str, NotificationTemplate] = {}
        
        # Alert monitoring
        self.alert_processors: Dict[str, Callable] = {}
        self.notification_handlers: Dict[NotificationChannel, Callable] = {}
        self.alert_queue: asyncio.Queue = asyncio.Queue()
        
        # Configuration
        self.max_alerts_per_minute = 100
        self.alert_retention_days = 30
        self.notification_retry_attempts = 3
        self.notification_timeout_seconds = 30
        
        # Rate limiting
        self.alert_rate_limiter: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Initialize default templates and processors
        self._initialize_default_templates()
        self._initialize_alert_processors()
        
        # Start background services
        self.service_active = True
        self._start_alerting_services()
        
        logger.info("AlertingService initialized with real-time monitoring")
    
    def _start_alerting_services(self):
        """Start background alerting services"""
        asyncio.create_task(self._alert_processing_loop())
        asyncio.create_task(self._alert_monitoring_loop())
        asyncio.create_task(self._cleanup_loop())
    
    async def _alert_processing_loop(self):
        """Main alert processing loop"""
        while self.service_active:
            try:
                # Process alerts from queue
                alert = await asyncio.wait_for(self.alert_queue.get(), timeout=1.0)
                await self._process_alert(alert)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in alert processing loop: {e}", exc_info=True)
    
    async def _alert_monitoring_loop(self):
        """Monitor system conditions and trigger alerts"""
        while self.service_active:
            try:
                await self._check_all_alert_rules()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(30)
    
    async def _cleanup_loop(self):
        """Cleanup old alerts and notifications"""
        while self.service_active:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Cleanup every hour
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                await asyncio.sleep(3600)
    
    def _initialize_default_templates(self):
        """Initialize default notification templates"""
        
        # Trading alert templates
        self.notification_templates["trading_execution_failure"] = NotificationTemplate(
            template_id="trading_execution_failure",
            category=AlertCategory.TRADING,
            severity=AlertSeverity.ERROR,
            channel=NotificationChannel.DASHBOARD,
            subject_template="Trading Execution Failure - {symbol}",
            body_template="Agent {agent_id} failed to execute trade for {symbol}. Error: {error_message}"
        )
        
        # Risk alert templates
        self.notification_templates["risk_limit_breach"] = NotificationTemplate(
            template_id="risk_limit_breach",
            category=AlertCategory.RISK,
            severity=AlertSeverity.WARNING,
            subject_template="Risk Limit Breach - {agent_id}",
            body_template="Agent {agent_id} has breached risk limits. Current exposure: {exposure}, Limit: {limit}"
        )
        
        # Performance alert templates
        self.notification_templates["performance_degradation"] = NotificationTemplate(
            template_id="performance_degradation",
            category=AlertCategory.PERFORMANCE,
            severity=AlertSeverity.WARNING,
            subject_template="Performance Degradation - {agent_id}",
            body_template="Agent {agent_id} performance has degraded. Win rate: {win_rate}, Drawdown: {drawdown}"
        )
        
        # System alert templates
        self.notification_templates["system_error"] = NotificationTemplate(
            template_id="system_error",
            category=AlertCategory.SYSTEM,
            severity=AlertSeverity.CRITICAL,
            channel=NotificationChannel.DASHBOARD,
            subject_template="System Error - {service_name}",
            body_template="Critical system error in {service_name}: {error_message}"
        )
    
    def _initialize_alert_processors(self):
        """Initialize alert condition processors"""
        
        self.alert_processors["threshold"] = self._process_threshold_condition
        self.alert_processors["change"] = self._process_change_condition
        self.alert_processors["pattern"] = self._process_pattern_condition
        self.alert_processors["custom"] = self._process_custom_condition
    
    async def create_alert_rule(self, rule: AlertRule) -> str:
        """Create a new alert rule"""
        
        # Validate rule
        if not rule.name or not rule.condition_type:
            raise ValueError("Alert rule must have name and condition type")
        
        # Store rule
        self.alert_rules[rule.rule_id] = rule
        
        logger.info(f"Created alert rule: {rule.name} ({rule.rule_id})")
        return rule.rule_id
    
    async def trigger_alert(
        self,
        rule_id: str,
        title: str,
        message: str,
        agent_id: Optional[str] = None,
        symbol: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Manually trigger an alert"""
        
        rule = self.alert_rules.get(rule_id)
        if not rule:
            raise ValueError(f"Alert rule {rule_id} not found")
        
        # Check rate limiting
        if not await self._check_rate_limit(rule_id):
            logger.warning(f"Alert rate limit exceeded for rule {rule_id}")
            return ""
        
        # Create alert
        alert = Alert(
            rule_id=rule_id,
            title=title,
            message=message,
            category=rule.category,
            severity=rule.severity,
            agent_id=agent_id,
            symbol=symbol,
            data=data or {}
        )
        
        # Add to queue for processing
        await self.alert_queue.put(alert)
        
        logger.info(f"Triggered alert: {title} (Rule: {rule_id})")
        return alert.alert_id
    
    async def _process_alert(self, alert: Alert):
        """Process an alert through the notification pipeline"""
        
        try:
            # Store alert
            self.active_alerts[alert.alert_id] = alert
            self.alert_history.append(alert)
            
            # Update rule statistics
            rule = self.alert_rules.get(alert.rule_id)
            if rule:
                rule.last_triggered = alert.created_at
                rule.trigger_count += 1
                
                # Send notifications
                for channel in rule.notification_channels:
                    await self._send_notification(alert, channel)
            
            # Keep history manageable
            if len(self.alert_history) > 10000:
                self.alert_history = self.alert_history[-5000:]
            
            logger.info(f"Processed alert: {alert.title} ({alert.alert_id})")
            
        except Exception as e:
            logger.error(f"Error processing alert {alert.alert_id}: {e}", exc_info=True)
    
    async def _send_notification(self, alert: Alert, channel: NotificationChannel):
        """Send notification through specified channel"""
        
        try:
            # Get template
            template_key = f"{alert.category.value}_{alert.severity.value}"
            template = self.notification_templates.get(
                template_key, 
                self.notification_templates.get("default")
            )
            
            if not template:
                logger.warning(f"No template found for {template_key}")
                return
            
            # Format message
            formatted_message = await self._format_notification(alert, template)
            
            # Send through channel
            handler = self.notification_handlers.get(channel)
            if handler:
                success = await handler(alert, formatted_message)
                status = "sent" if success else "failed"
            else:
                # Default dashboard notification
                success = await self._send_dashboard_notification(alert, formatted_message)
                status = "sent" if success else "failed"
            
            # Record delivery
            notification_history = NotificationHistory(
                alert_id=alert.alert_id,
                channel=channel,
                recipient="system",  # Would be actual recipient in production
                status=status,
                timestamp=datetime.now(timezone.utc)
            )
            
            self.notification_history.append(notification_history)
            alert.notifications_sent.append(channel.value)
            alert.delivery_attempts += 1
            
            logger.debug(f"Sent notification for alert {alert.alert_id} via {channel.value}")
            
        except Exception as e:
            logger.error(f"Failed to send notification for alert {alert.alert_id} via {channel.value}: {e}")
    
    async def _format_notification(self, alert: Alert, template: NotificationTemplate) -> Dict[str, str]:
        """Format notification message using template"""
        
        # Prepare template variables
        variables = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value,
            "category": alert.category.value,
            "agent_id": alert.agent_id or "N/A",
            "symbol": alert.symbol or "N/A",
            "timestamp": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            **alert.data
        }
        
        # Format templates
        try:
            subject = template.subject_template.format(**variables)
            body = template.body_template.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable {e} in template, using fallback")
            subject = alert.title
            body = alert.message
        
        return {
            "subject": subject,
            "body": body,
            "formatted_data": variables
        }
    
    async def _send_dashboard_notification(self, alert: Alert, formatted_message: Dict[str, str]) -> bool:
        """Send notification to dashboard (default handler)"""
        
        try:
            # In a real implementation, this would integrate with the dashboard WebSocket
            logger.info(f"Dashboard notification: {formatted_message['subject']}")
            return True
        except Exception as e:
            logger.error(f"Dashboard notification failed: {e}")
            return False
    
    async def _check_rate_limit(self, rule_id: str) -> bool:
        """Check if alert is within rate limits"""
        
        now = datetime.now(timezone.utc)
        rate_window = self.alert_rate_limiter[rule_id]
        
        # Remove old entries
        while rate_window and (now - rate_window[0]).total_seconds() > 60:
            rate_window.popleft()
        
        # Check limit
        if len(rate_window) >= self.max_alerts_per_minute:
            return False
        
        # Add current alert
        rate_window.append(now)
        return True
    
    async def _check_all_alert_rules(self):
        """Check all active alert rules for trigger conditions"""
        
        for rule in self.alert_rules.values():
            if not rule.is_active:
                continue
            
            try:
                await self._check_alert_rule(rule)
            except Exception as e:
                logger.error(f"Error checking alert rule {rule.rule_id}: {e}")
    
    async def _check_alert_rule(self, rule: AlertRule):
        """Check a specific alert rule for trigger conditions"""
        
        processor = self.alert_processors.get(rule.condition_type)
        if not processor:
            logger.warning(f"No processor for condition type: {rule.condition_type}")
            return
        
        try:
            # Check throttling
            if rule.last_triggered:
                time_since_last = (datetime.now(timezone.utc) - rule.last_triggered).total_seconds()
                if time_since_last < rule.notification_throttle_minutes * 60:
                    return
            
            # Process condition
            should_trigger, context = await processor(rule)
            
            if should_trigger:
                await self.trigger_alert(
                    rule_id=rule.rule_id,
                    title=context.get("title", rule.name),
                    message=context.get("message", rule.description),
                    agent_id=context.get("agent_id"),
                    symbol=context.get("symbol"),
                    data=context.get("data", {})
                )
                
        except Exception as e:
            logger.error(f"Error processing alert rule {rule.rule_id}: {e}")
    
    async def _process_threshold_condition(self, rule: AlertRule) -> Tuple[bool, Dict[str, Any]]:
        """Process threshold-based alert condition"""
        
        params = rule.condition_parameters
        metric = params.get("metric")
        threshold = params.get("threshold")
        operator = params.get("operator", "gt")  # gt, lt, eq, gte, lte
        
        if not metric or threshold is None:
            return False, {}
        
        # Get current metric value (placeholder - would integrate with actual metrics)
        current_value = await self._get_metric_value(metric, rule.target_agents, rule.target_symbols)
        
        if current_value is None:
            return False, {}
        
        # Check threshold
        triggered = False
        if operator == "gt":
            triggered = current_value > threshold
        elif operator == "lt":
            triggered = current_value < threshold
        elif operator == "gte":
            triggered = current_value >= threshold
        elif operator == "lte":
            triggered = current_value <= threshold
        elif operator == "eq":
            triggered = abs(current_value - threshold) < 0.001
        
        context = {
            "title": f"{metric} threshold exceeded",
            "message": f"{metric} is {current_value}, threshold is {threshold}",
            "data": {
                "metric": metric,
                "current_value": current_value,
                "threshold": threshold,
                "operator": operator
            }
        }
        
        return triggered, context
    
    async def _process_change_condition(self, rule: AlertRule) -> Tuple[bool, Dict[str, Any]]:
        """Process change-based alert condition"""
        
        params = rule.condition_parameters
        metric = params.get("metric")
        change_threshold = params.get("change_threshold")
        time_window_minutes = params.get("time_window_minutes", 60)
        
        if not metric or change_threshold is None:
            return False, {}
        
        # Get historical metric values
        current_value = await self._get_metric_value(metric, rule.target_agents, rule.target_symbols)
        historical_value = await self._get_historical_metric_value(
            metric, rule.target_agents, rule.target_symbols, time_window_minutes
        )
        
        if current_value is None or historical_value is None:
            return False, {}
        
        # Calculate change
        if historical_value == 0:
            change = float('inf') if current_value != 0 else 0
        else:
            change = abs((current_value - historical_value) / historical_value)
        
        triggered = change > change_threshold
        
        context = {
            "title": f"{metric} changed significantly",
            "message": f"{metric} changed by {change:.2%} in {time_window_minutes} minutes",
            "data": {
                "metric": metric,
                "current_value": current_value,
                "historical_value": historical_value,
                "change_percentage": change,
                "threshold": change_threshold
            }
        }
        
        return triggered, context
    
    async def _process_pattern_condition(self, rule: AlertRule) -> Tuple[bool, Dict[str, Any]]:
        """Process pattern-based alert condition"""
        # Placeholder for pattern detection
        return False, {}
    
    async def _process_custom_condition(self, rule: AlertRule) -> Tuple[bool, Dict[str, Any]]:
        """Process custom alert condition"""
        # Placeholder for custom conditions
        return False, {}
    
    async def _get_metric_value(self, metric: str, agents: List[str], symbols: List[str]) -> Optional[float]:
        """Get current metric value (placeholder for real integration)"""
        # This would integrate with actual services to get metrics
        # For now, return placeholder values
        if metric == "win_rate":
            return 0.65
        elif metric == "drawdown":
            return 0.05
        elif metric == "volatility":
            return 0.20
        elif metric == "pnl":
            return 1500.0
        return None
    
    async def _get_historical_metric_value(
        self, metric: str, agents: List[str], symbols: List[str], minutes_ago: int
    ) -> Optional[float]:
        """Get historical metric value"""
        # Placeholder for historical data
        current = await self._get_metric_value(metric, agents, symbols)
        if current is not None:
            return current * 0.9  # Simulate 10% change
        return None
    
    async def _cleanup_old_data(self):
        """Clean up old alerts and notifications"""
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.alert_retention_days)
        
        # Clean up alert history
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.created_at > cutoff_date
        ]
        
        # Clean up notification history
        self.notification_history = [
            notif for notif in self.notification_history
            if notif.timestamp > cutoff_date
        ]
        
        # Clean up resolved active alerts
        resolved_alerts = [
            alert_id for alert_id, alert in self.active_alerts.items()
            if alert.status == "resolved" and alert.resolved_at and alert.resolved_at < cutoff_date
        ]
        
        for alert_id in resolved_alerts:
            del self.active_alerts[alert_id]
        
        logger.debug(f"Cleaned up {len(resolved_alerts)} old alerts")
    
    async def acknowledge_alert(self, alert_id: str, user_id: str = "system") -> bool:
        """Acknowledge an active alert"""
        
        alert = self.active_alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.now(timezone.utc)
        
        logger.info(f"Alert {alert_id} acknowledged by {user_id}")
        return True
    
    async def resolve_alert(self, alert_id: str, user_id: str = "system") -> bool:
        """Resolve an active alert"""
        
        alert = self.active_alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = "resolved"
        alert.resolved_at = datetime.now(timezone.utc)
        
        logger.info(f"Alert {alert_id} resolved by {user_id}")
        return True
    
    async def get_active_alerts(self, category: Optional[AlertCategory] = None, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts with optional filtering"""
        
        alerts = list(self.active_alerts.values())
        
        if category:
            alerts = [a for a in alerts if a.category == category]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Sort by severity and creation time
        severity_order = {
            AlertSeverity.EMERGENCY: 5,
            AlertSeverity.CRITICAL: 4,
            AlertSeverity.ERROR: 3,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 1
        }
        
        alerts.sort(key=lambda x: (severity_order.get(x.severity, 0), x.created_at), reverse=True)
        return alerts
    
    async def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return self.alert_history[-limit:] if limit else self.alert_history
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get alerting service status"""
        
        alert_counts = defaultdict(int)
        for alert in self.active_alerts.values():
            alert_counts[f"{alert.category.value}_{alert.severity.value}"] += 1
        
        rule_stats = {
            "total_rules": len(self.alert_rules),
            "active_rules": len([r for r in self.alert_rules.values() if r.is_active]),
            "rules_by_category": defaultdict(int)
        }
        
        for rule in self.alert_rules.values():
            rule_stats["rules_by_category"][rule.category.value] += 1
        
        return {
            "service_status": "active" if self.service_active else "inactive",
            "active_alerts": len(self.active_alerts),
            "alert_history_count": len(self.alert_history),
            "notification_history_count": len(self.notification_history),
            "alert_breakdown": dict(alert_counts),
            "rule_statistics": rule_stats,
            "configuration": {
                "max_alerts_per_minute": self.max_alerts_per_minute,
                "alert_retention_days": self.alert_retention_days,
                "notification_retry_attempts": self.notification_retry_attempts
            },
            "last_update": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_alerting_service() -> AlertingService:
    """Factory function to create alerting service"""
    return AlertingService()