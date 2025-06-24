"""
Agent Trading Bridge Service - Phase 2 Implementation
Bridges AI agents to live trading execution with safety controls
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Literal
from loguru import logger
from pydantic import BaseModel, Field

from ..models.execution_models import ExecutionRequest, ExecutionReceipt, TradeParams
from ..models.event_bus_models import TradeSignalEventPayload, RiskAssessmentResponseData
from ..models.agent_models import AgentConfigOutput
from ..services.execution_specialist_service import ExecutionSpecialistService
from ..services.risk_manager_service import RiskManagerService
from ..services.agent_management_service import AgentManagementService

class AgentTradingBridgeError(Exception):
    """Custom exception for agent trading bridge errors"""
    pass

class TradingSignal(BaseModel):
    """Standardized trading signal from agents"""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    symbol: str
    action: Literal["buy", "sell"]
    quantity: float
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0)
    strategy: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutionResult(BaseModel):
    """Result of trade execution through bridge"""
    signal_id: str
    execution_id: str
    status: Literal["pending", "executing", "filled", "partially_filled", "failed", "rejected"]
    message: str
    fills: List[Dict[str, Any]] = Field(default_factory=list)
    total_quantity_filled: float = 0.0
    average_fill_price: Optional[float] = None
    total_fees: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentTradingBridge:
    """
    Bridge service connecting AI agents to live trading execution
    Provides safety controls, risk management, and execution routing
    """
    
    def __init__(
        self,
        execution_service: ExecutionSpecialistService,
        risk_service: RiskManagerService,
        agent_service: AgentManagementService
    ):
        self.execution_service = execution_service
        self.risk_service = risk_service
        self.agent_service = agent_service
        self.active_signals: Dict[str, TradingSignal] = {}
        self.execution_results: Dict[str, ExecutionResult] = {}
        self.bridge_active = True
        
        logger.info("AgentTradingBridge initialized with live execution capabilities")
    
    async def process_agent_signal(self, signal: TradingSignal) -> ExecutionResult:
        """
        Process trading signal from agent through complete execution pipeline
        """
        logger.info(f"Processing trading signal {signal.signal_id} from agent {signal.agent_id}")
        
        try:
            # Store active signal
            self.active_signals[signal.signal_id] = signal
            
            # 1. Validate agent and bridge status
            if not self.bridge_active:
                return ExecutionResult(
                    signal_id=signal.signal_id,
                    execution_id="",
                    status="rejected",
                    message="Agent trading bridge is disabled"
                )
            
            # 2. Get agent configuration
            agent_config = await self.agent_service.get_agent(signal.agent_id)
            if not agent_config:
                return ExecutionResult(
                    signal_id=signal.signal_id,
                    execution_id="",
                    status="rejected",
                    message=f"Agent {signal.agent_id} not found or inactive"
                )
            
            # 3. Risk assessment
            trade_signal_payload = TradeSignalEventPayload(
                symbol=signal.symbol,
                action=signal.action,
                quantity=signal.quantity,
                price_target=signal.price_target,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                confidence=signal.confidence,
                strategy_name=signal.strategy
            )
            
            risk_assessment = await self.risk_service.assess_trade_risk(
                signal.agent_id, 
                trade_signal_payload
            )
            
            if not risk_assessment.signal_approved:
                logger.warning(f"Signal {signal.signal_id} rejected by risk manager: {risk_assessment.rejection_reason}")
                return ExecutionResult(
                    signal_id=signal.signal_id,
                    execution_id="",
                    status="rejected",
                    message=f"Risk rejected: {risk_assessment.rejection_reason}"
                )
            
            # 4. Convert to execution request
            execution_request = self._create_execution_request(signal, agent_config)
            
            # 5. Execute through specialist service
            execution_receipt = await self.execution_service.process_trade_order(execution_request)
            
            # 6. Process execution result
            result = self._process_execution_receipt(signal, execution_receipt)
            
            # Store result
            self.execution_results[signal.signal_id] = result
            
            logger.info(f"Signal {signal.signal_id} processed: {result.status} - {result.message}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing signal {signal.signal_id}: {e}", exc_info=True)
            error_result = ExecutionResult(
                signal_id=signal.signal_id,
                execution_id="",
                status="failed",
                message=f"Bridge error: {str(e)}"
            )
            self.execution_results[signal.signal_id] = error_result
            return error_result
    
    def _create_execution_request(self, signal: TradingSignal, agent_config: AgentConfigOutput) -> ExecutionRequest:
        """Convert agent signal to execution request"""
        
        # Map agent action to trade side
        side = "buy" if signal.action == "buy" else "sell"
        
        # Determine order type based on price target
        order_type = "limit" if signal.price_target else "market"
        
        trade_params = TradeParams(
            symbol=signal.symbol,
            side=side,
            quantity=signal.quantity,
            order_type=order_type,
            price=signal.price_target,
            strategy_name=signal.strategy,
            client_order_id=f"agent_{signal.agent_id}_{signal.signal_id[:8]}"
        )
        
        # Determine preferred exchange from agent config
        preferred_exchange = None
        if agent_config.execution_provider == "hyperliquid":
            preferred_exchange = "hyperliquid"
        elif agent_config.execution_provider == "dex":
            preferred_exchange = "dex_uniswap_v3"
        
        return ExecutionRequest(
            source_agent_id=signal.agent_id,
            trade_params=trade_params,
            preferred_exchange=preferred_exchange,
            execution_preferences={
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "confidence": signal.confidence,
                "strategy": signal.strategy
            }
        )
    
    def _process_execution_receipt(self, signal: TradingSignal, receipt: ExecutionReceipt) -> ExecutionResult:
        """Process execution receipt into standardized result"""
        
        # Map execution status
        status_map = {
            "PENDING_EXECUTION": "pending",
            "ROUTED": "executing", 
            "PARTIALLY_FILLED": "partially_filled",
            "FILLED": "filled",
            "FAILED": "failed",
            "REJECTED_BY_SPECIALIST": "rejected"
        }
        
        status = status_map.get(receipt.execution_status, "failed")
        
        # Process fills
        total_quantity_filled = sum(fill.fill_quantity for fill in receipt.fills)
        total_fees = sum(fill.fee for fill in receipt.fills)
        
        average_fill_price = None
        if receipt.fills:
            weighted_price_sum = sum(fill.fill_price * fill.fill_quantity for fill in receipt.fills)
            if total_quantity_filled > 0:
                average_fill_price = weighted_price_sum / total_quantity_filled
        
        fills_data = [
            {
                "exchange_trade_id": fill.exchange_trade_id,
                "exchange_order_id": fill.exchange_order_id,
                "fill_price": fill.fill_price,
                "fill_quantity": fill.fill_quantity,
                "fee": fill.fee,
                "fee_currency": fill.fee_currency,
                "timestamp": fill.timestamp.isoformat()
            }
            for fill in receipt.fills
        ]
        
        return ExecutionResult(
            signal_id=signal.signal_id,
            execution_id=receipt.request_id,
            status=status,
            message=receipt.message,
            fills=fills_data,
            total_quantity_filled=total_quantity_filled,
            average_fill_price=average_fill_price,
            total_fees=total_fees
        )
    
    async def get_signal_status(self, signal_id: str) -> Optional[ExecutionResult]:
        """Get status of a trading signal"""
        return self.execution_results.get(signal_id)
    
    async def get_active_signals(self, agent_id: Optional[str] = None) -> List[TradingSignal]:
        """Get active signals, optionally filtered by agent"""
        if agent_id:
            return [signal for signal in self.active_signals.values() if signal.agent_id == agent_id]
        return list(self.active_signals.values())
    
    async def cancel_signal(self, signal_id: str) -> bool:
        """Cancel an active trading signal"""
        if signal_id in self.active_signals:
            del self.active_signals[signal_id]
            logger.info(f"Cancelled trading signal {signal_id}")
            return True
        return False
    
    def enable_bridge(self):
        """Enable the trading bridge"""
        self.bridge_active = True
        logger.info("Agent trading bridge enabled")
    
    def disable_bridge(self):
        """Disable the trading bridge for safety"""
        self.bridge_active = False
        logger.warning("Agent trading bridge disabled - no new trades will be processed")
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """Get bridge operational status"""
        return {
            "bridge_active": self.bridge_active,
            "active_signals_count": len(self.active_signals),
            "completed_executions_count": len(self.execution_results),
            "services_status": {
                "execution_service": "online",
                "risk_service": "online", 
                "agent_service": "online"
            }
        }

# Factory function for service registry
def create_agent_trading_bridge(
    execution_service: ExecutionSpecialistService,
    risk_service: RiskManagerService, 
    agent_service: AgentManagementService
) -> AgentTradingBridge:
    """Factory function to create agent trading bridge"""
    return AgentTradingBridge(execution_service, risk_service, agent_service)