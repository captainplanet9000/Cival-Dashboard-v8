"""
Phase 4: Real-Time Wallet Event Streaming - Live Wallet Event Broadcasting
Real-time event streaming for wallet operations and cross-service coordination
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import uuid

from ..core.service_registry import get_registry
from ..models.master_wallet_models import FundAllocation, WalletTransaction

logger = logging.getLogger(__name__)

class WalletEventType(Enum):
    """Wallet event types for streaming"""
    WALLET_CREATED = "wallet_created"
    WALLET_UPDATED = "wallet_updated"
    WALLET_DEACTIVATED = "wallet_deactivated"
    FUNDS_ALLOCATED = "funds_allocated"
    FUNDS_COLLECTED = "funds_collected"
    FUNDS_TRANSFERRED = "funds_transferred"
    BALANCE_UPDATED = "balance_updated"
    PERFORMANCE_CALCULATED = "performance_calculated"
    ALLOCATION_CREATED = "allocation_created"
    ALLOCATION_UPDATED = "allocation_updated"
    ALLOCATION_COMPLETED = "allocation_completed"
    EMERGENCY_STOP = "emergency_stop"
    DISTRIBUTION_TRIGGERED = "distribution_triggered"
    RISK_THRESHOLD_EXCEEDED = "risk_threshold_exceeded"

class WalletEvent:
    """Wallet event model for streaming"""
    
    def __init__(self, event_type: WalletEventType, wallet_id: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.wallet_id = wallet_id
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)
        self.processed = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "wallet_id": self.wallet_id,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)

class WalletEventStreamingService:
    """
    Real-time wallet event streaming service
    Phase 4: Live event broadcasting and subscription management
    """
    
    def __init__(self):
        self.registry = get_registry()
        self.master_wallet_service = None
        self.wallet_coordination_service = None
        
        # Event streaming infrastructure
        self.event_subscribers: Dict[str, Set[Callable]] = {}  # event_type -> callbacks
        self.wallet_subscribers: Dict[str, Set[Callable]] = {}  # wallet_id -> callbacks
        self.global_subscribers: Set[Callable] = set()
        
        # Event queue and processing
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.event_history: List[WalletEvent] = []
        self.max_history_size = 10000
        
        # Event processing state
        self.streaming_active = False
        self.event_processing_active = False
        
        # Performance metrics
        self.streaming_metrics = {
            "events_processed": 0,
            "events_queued": 0,
            "subscribers_count": 0,
            "processing_errors": 0
        }
        
        logger.info("WalletEventStreamingService initialized")
    
    async def initialize(self):
        """Initialize wallet event streaming service"""
        try:
            # Get required services
            self.master_wallet_service = self.registry.get_service("master_wallet_service")
            self.wallet_coordination_service = self.registry.get_service("wallet_coordination_service")
            
            if not self.master_wallet_service:
                logger.error("Master wallet service not available for event streaming")
                return
            
            # Start event processing loops
            asyncio.create_task(self._event_processing_loop())
            asyncio.create_task(self._event_monitoring_loop())
            asyncio.create_task(self._wallet_monitoring_loop())
            
            # Initialize event hooks in wallet service
            await self._setup_wallet_service_hooks()
            
            self.streaming_active = True
            self.event_processing_active = True
            
            logger.info("Wallet event streaming service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet event streaming: {e}")
            raise
    
    async def _setup_wallet_service_hooks(self):
        """Set up event hooks in the master wallet service"""
        try:
            # Hook into wallet service methods to capture events
            if hasattr(self.master_wallet_service, 'set_event_callback'):
                await self.master_wallet_service.set_event_callback(self.emit_event)
            
            # Monitor wallet service for state changes
            logger.info("Event hooks set up in master wallet service")
            
        except Exception as e:
            logger.error(f"Failed to set up wallet service hooks: {e}")
    
    async def emit_event(self, event_type: WalletEventType, wallet_id: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """
        Emit a wallet event to the streaming system
        Main entry point for event creation
        """
        try:
            event = WalletEvent(event_type, wallet_id, data, metadata)
            
            # Add to queue for processing
            await self.event_queue.put(event)
            self.streaming_metrics["events_queued"] += 1
            
            logger.debug(f"Emitted event: {event_type.value} for wallet {wallet_id}")
            
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
    
    async def subscribe_to_events(self, callback: Callable, event_types: Optional[List[WalletEventType]] = None, wallet_ids: Optional[List[str]] = None):
        """
        Subscribe to wallet events
        Phase 4: Flexible subscription management
        """
        try:
            if event_types:
                # Subscribe to specific event types
                for event_type in event_types:
                    event_type_str = event_type.value
                    if event_type_str not in self.event_subscribers:
                        self.event_subscribers[event_type_str] = set()
                    self.event_subscribers[event_type_str].add(callback)
            
            if wallet_ids:
                # Subscribe to specific wallets
                for wallet_id in wallet_ids:
                    if wallet_id not in self.wallet_subscribers:
                        self.wallet_subscribers[wallet_id] = set()
                    self.wallet_subscribers[wallet_id].add(callback)
            
            if not event_types and not wallet_ids:
                # Subscribe to all events
                self.global_subscribers.add(callback)
            
            self._update_subscriber_count()
            logger.info(f"Added event subscriber with {len(event_types or [])} event types and {len(wallet_ids or [])} wallets")
            
        except Exception as e:
            logger.error(f"Failed to add event subscriber: {e}")
    
    async def unsubscribe_from_events(self, callback: Callable):
        """Remove callback from all subscriptions"""
        try:
            # Remove from global subscribers
            self.global_subscribers.discard(callback)
            
            # Remove from event type subscribers
            for subscribers in self.event_subscribers.values():
                subscribers.discard(callback)
            
            # Remove from wallet subscribers
            for subscribers in self.wallet_subscribers.values():
                subscribers.discard(callback)
            
            self._update_subscriber_count()
            logger.info("Removed event subscriber")
            
        except Exception as e:
            logger.error(f"Failed to remove event subscriber: {e}")
    
    async def _event_processing_loop(self):
        """Main event processing loop"""
        while self.event_processing_active:
            try:
                # Get event from queue (with timeout)
                try:
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process the event
                await self._process_event(event)
                
                # Mark task as done
                self.event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                self.streaming_metrics["processing_errors"] += 1
                await asyncio.sleep(1)
    
    async def _process_event(self, event: WalletEvent):
        """Process a single wallet event"""
        try:
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)
            
            # Notify subscribers
            await self._notify_subscribers(event)
            
            # Handle specific event processing
            await self._handle_event_processing(event)
            
            # Mark as processed
            event.processed = True
            self.streaming_metrics["events_processed"] += 1
            
            logger.debug(f"Processed event {event.event_id}: {event.event_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")
            self.streaming_metrics["processing_errors"] += 1
    
    async def _notify_subscribers(self, event: WalletEvent):
        """Notify all relevant subscribers of the event"""
        try:
            callbacks_to_notify = set()
            
            # Add global subscribers
            callbacks_to_notify.update(self.global_subscribers)
            
            # Add event type subscribers
            event_type_subscribers = self.event_subscribers.get(event.event_type.value, set())
            callbacks_to_notify.update(event_type_subscribers)
            
            # Add wallet-specific subscribers
            wallet_subscribers = self.wallet_subscribers.get(event.wallet_id, set())
            callbacks_to_notify.update(wallet_subscribers)
            
            # Notify all callbacks
            for callback in callbacks_to_notify:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")
            
        except Exception as e:
            logger.error(f"Failed to notify subscribers: {e}")
    
    async def _handle_event_processing(self, event: WalletEvent):
        """Handle specific event processing logic"""
        try:
            event_type = event.event_type
            
            if event_type == WalletEventType.FUNDS_ALLOCATED:
                await self._handle_allocation_event(event)
            elif event_type == WalletEventType.FUNDS_COLLECTED:
                await self._handle_collection_event(event)
            elif event_type == WalletEventType.PERFORMANCE_CALCULATED:
                await self._handle_performance_event(event)
            elif event_type == WalletEventType.RISK_THRESHOLD_EXCEEDED:
                await self._handle_risk_event(event)
            elif event_type == WalletEventType.EMERGENCY_STOP:
                await self._handle_emergency_event(event)
            
        except Exception as e:
            logger.error(f"Failed to handle event processing for {event.event_type.value}: {e}")
    
    async def _handle_allocation_event(self, event: WalletEvent):
        """Handle fund allocation events"""
        try:
            allocation_data = event.data.get("allocation", {})
            
            # Trigger cross-service coordination if coordination service is available
            if self.wallet_coordination_service:
                # Notify coordination service of allocation
                if hasattr(self.wallet_coordination_service, 'handle_allocation_event'):
                    await self.wallet_coordination_service.handle_allocation_event(event)
            
            # Trigger analytics update
            await self._trigger_analytics_update(event.wallet_id, "allocation_created")
            
        except Exception as e:
            logger.error(f"Failed to handle allocation event: {e}")
    
    async def _handle_collection_event(self, event: WalletEvent):
        """Handle fund collection events"""
        try:
            # Trigger cross-service coordination
            if self.wallet_coordination_service:
                if hasattr(self.wallet_coordination_service, 'handle_collection_event'):
                    await self.wallet_coordination_service.handle_collection_event(event)
            
            # Trigger analytics update
            await self._trigger_analytics_update(event.wallet_id, "funds_collected")
            
        except Exception as e:
            logger.error(f"Failed to handle collection event: {e}")
    
    async def _handle_performance_event(self, event: WalletEvent):
        """Handle performance calculation events"""
        try:
            performance_data = event.data.get("performance", {})
            
            # Check for significant performance changes
            total_pnl_percentage = performance_data.get("total_pnl_percentage", 0)
            
            # Trigger notifications for significant performance milestones
            if abs(total_pnl_percentage) >= 10:  # 10% gain or loss
                await self.emit_event(
                    WalletEventType.RISK_THRESHOLD_EXCEEDED,
                    event.wallet_id,
                    {
                        "reason": "significant_performance_change",
                        "pnl_percentage": total_pnl_percentage,
                        "performance": performance_data
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to handle performance event: {e}")
    
    async def _handle_risk_event(self, event: WalletEvent):
        """Handle risk threshold exceeded events"""
        try:
            risk_data = event.data
            reason = risk_data.get("reason", "unknown")
            
            # Log critical risk event
            logger.warning(f"Risk threshold exceeded for wallet {event.wallet_id}: {reason}")
            
            # Trigger emergency protocols if severe
            if reason in ["significant_loss", "emergency_stop"]:
                # Could trigger automatic protective measures
                pass
            
        except Exception as e:
            logger.error(f"Failed to handle risk event: {e}")
    
    async def _handle_emergency_event(self, event: WalletEvent):
        """Handle emergency stop events"""
        try:
            emergency_data = event.data
            logger.critical(f"EMERGENCY STOP event for wallet {event.wallet_id}: {emergency_data}")
            
            # Broadcast to all services
            await self._broadcast_emergency_notification(event)
            
        except Exception as e:
            logger.error(f"Failed to handle emergency event: {e}")
    
    async def _broadcast_emergency_notification(self, event: WalletEvent):
        """Broadcast emergency notification to all services"""
        try:
            emergency_notification = {
                "type": "emergency_stop",
                "wallet_id": event.wallet_id,
                "event_data": event.data,
                "timestamp": event.timestamp.isoformat()
            }
            
            # Notify all registered services
            all_services = self.registry.list_services()
            
            for service_name in all_services:
                try:
                    service = self.registry.get_service(service_name)
                    if service and hasattr(service, 'handle_emergency_notification'):
                        await service.handle_emergency_notification(emergency_notification)
                except Exception as e:
                    logger.error(f"Failed to notify {service_name} of emergency: {e}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast emergency notification: {e}")
    
    async def _trigger_analytics_update(self, wallet_id: str, event_type: str):
        """Trigger analytics service to update wallet data"""
        try:
            analytics_service = self.registry.get_service("performance_analytics_service")
            if analytics_service:
                if hasattr(analytics_service, 'trigger_wallet_update'):
                    await analytics_service.trigger_wallet_update(wallet_id, event_type)
            
        except Exception as e:
            logger.error(f"Failed to trigger analytics update: {e}")
    
    async def _event_monitoring_loop(self):
        """Monitor event streaming health and performance"""
        while self.streaming_active:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Update metrics
                self.streaming_metrics["events_queued"] = self.event_queue.qsize()
                
                # Check for queue backup
                if self.event_queue.qsize() > 1000:
                    logger.warning(f"Event queue backup detected: {self.event_queue.qsize()} events queued")
                
                # Log performance metrics periodically
                if self.streaming_metrics["events_processed"] % 100 == 0 and self.streaming_metrics["events_processed"] > 0:
                    logger.info(f"Event streaming metrics: {self.streaming_metrics}")
                
            except Exception as e:
                logger.error(f"Error in event monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _wallet_monitoring_loop(self):
        """Monitor wallet state changes and emit events"""
        previous_wallet_states = {}
        
        while self.streaming_active:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                if not self.master_wallet_service:
                    continue
                
                # Check for wallet state changes
                current_wallets = self.master_wallet_service.active_wallets
                
                for wallet_id, wallet in current_wallets.items():
                    previous_state = previous_wallet_states.get(wallet_id)
                    
                    if previous_state is None:
                        # New wallet detected
                        await self.emit_event(
                            WalletEventType.WALLET_CREATED,
                            wallet_id,
                            {"wallet": wallet.dict()}
                        )
                    else:
                        # Check for wallet updates
                        if wallet.config.updated_at != previous_state.get("updated_at"):
                            await self.emit_event(
                                WalletEventType.WALLET_UPDATED,
                                wallet_id,
                                {"wallet": wallet.dict()}
                            )
                    
                    # Update previous state
                    previous_wallet_states[wallet_id] = {
                        "updated_at": wallet.config.updated_at,
                        "is_active": wallet.is_active,
                        "allocation_count": len(wallet.allocations)
                    }
                
            except Exception as e:
                logger.error(f"Error in wallet monitoring loop: {e}")
                await asyncio.sleep(30)
    
    def _update_subscriber_count(self):
        """Update subscriber count metric"""
        total_subscribers = len(self.global_subscribers)
        total_subscribers += sum(len(subs) for subs in self.event_subscribers.values())
        total_subscribers += sum(len(subs) for subs in self.wallet_subscribers.values())
        
        self.streaming_metrics["subscribers_count"] = total_subscribers
    
    async def get_event_history(self, wallet_id: Optional[str] = None, event_types: Optional[List[WalletEventType]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get event history with optional filtering"""
        try:
            filtered_events = self.event_history
            
            # Filter by wallet_id
            if wallet_id:
                filtered_events = [event for event in filtered_events if event.wallet_id == wallet_id]
            
            # Filter by event types
            if event_types:
                event_type_values = [et.value for et in event_types]
                filtered_events = [event for event in filtered_events if event.event_type.value in event_type_values]
            
            # Sort by timestamp (newest first) and limit
            filtered_events = sorted(filtered_events, key=lambda e: e.timestamp, reverse=True)[:limit]
            
            return [event.to_dict() for event in filtered_events]
            
        except Exception as e:
            logger.error(f"Failed to get event history: {e}")
            return []
    
    async def get_streaming_status(self) -> Dict[str, Any]:
        """Get current streaming service status"""
        return {
            "service": "wallet_event_streaming_service",
            "status": "active" if self.streaming_active else "inactive",
            "event_processing_active": self.event_processing_active,
            "metrics": self.streaming_metrics,
            "queue_size": self.event_queue.qsize(),
            "history_size": len(self.event_history),
            "subscriber_breakdown": {
                "global": len(self.global_subscribers),
                "event_type": len(self.event_subscribers),
                "wallet_specific": len(self.wallet_subscribers)
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

# Factory function for service registry
def create_wallet_event_streaming_service():
    """Factory function to create WalletEventStreamingService instance"""
    return WalletEventStreamingService()