"""
Agent Coordination Service - Phase 2 Implementation
Unified coordination system for CrewAI and AutoGen agent frameworks
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Literal, Union
from loguru import logger
from pydantic import BaseModel, Field
from enum import Enum
import uuid

# Import agent frameworks
from ..agents.crew_analysis import run_trading_analysis_crew
from ..agents.autogen_setup import run_trading_analysis_autogen, get_autogen_system_status
from ..services.agent_trading_bridge import AgentTradingBridge, TradingSignal
from ..services.trading_safety_service import TradingSafetyService
from ..services.agent_performance_service import AgentPerformanceService

class FrameworkType(str, Enum):
    """Supported agent frameworks"""
    CREWAI = "crewai"
    AUTOGEN = "autogen"

class AnalysisRequest(BaseModel):
    """Analysis request from coordination layer"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    framework: FrameworkType
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    requested_by: Optional[str] = None
    timeout_seconds: int = 120
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AnalysisResult(BaseModel):
    """Analysis result from agent frameworks"""
    request_id: str
    symbol: str
    framework: FrameworkType
    success: bool
    recommendation: Optional[str] = None
    confidence: Optional[float] = None
    signals: List[TradingSignal] = Field(default_factory=list)
    analysis_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CoordinationTask(BaseModel):
    """Coordination task for multi-agent collaboration"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: Literal["analysis", "consensus", "execution", "monitoring"]
    symbol: str
    involved_frameworks: List[FrameworkType]
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    results: List[AnalysisResult] = Field(default_factory=list)
    consensus_reached: bool = False
    final_recommendation: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class AgentCoordinationService:
    """
    Unified coordination service for managing multiple agent frameworks
    Orchestrates CrewAI and AutoGen agents for collaborative trading decisions
    """
    
    def __init__(
        self,
        trading_bridge: AgentTradingBridge,
        safety_service: TradingSafetyService,
        performance_service: AgentPerformanceService
    ):
        self.trading_bridge = trading_bridge
        self.safety_service = safety_service
        self.performance_service = performance_service
        
        # Framework status tracking
        self.framework_status: Dict[FrameworkType, Dict[str, Any]] = {
            FrameworkType.CREWAI: {"status": "unknown", "last_check": None},
            FrameworkType.AUTOGEN: {"status": "unknown", "last_check": None}
        }
        
        # Active tasks and results
        self.active_tasks: Dict[str, CoordinationTask] = {}
        self.completed_tasks: List[CoordinationTask] = []
        self.analysis_cache: Dict[str, AnalysisResult] = {}
        
        # Coordination settings
        self.default_timeout = 120
        self.consensus_threshold = 0.7  # 70% agreement for consensus
        self.max_concurrent_tasks = 10
        
        logger.info("AgentCoordinationService initialized")
        
        # Check framework availability
        asyncio.create_task(self._check_framework_status())
    
    async def _check_framework_status(self):
        """Check the status of available agent frameworks"""
        
        # Check AutoGen
        try:
            autogen_status = get_autogen_system_status()
            self.framework_status[FrameworkType.AUTOGEN] = {
                "status": "online" if autogen_status.get("system_status") == "online" else "offline",
                "last_check": datetime.now(timezone.utc),
                "details": autogen_status
            }
        except Exception as e:
            self.framework_status[FrameworkType.AUTOGEN] = {
                "status": "error",
                "last_check": datetime.now(timezone.utc),
                "error": str(e)
            }
        
        # Check CrewAI (basic availability check)
        try:
            # This is a simple check - in production you might ping the crew services
            self.framework_status[FrameworkType.CREWAI] = {
                "status": "online",  # Assume online if import works
                "last_check": datetime.now(timezone.utc),
                "details": {"note": "CrewAI framework assumed available"}
            }
        except Exception as e:
            self.framework_status[FrameworkType.CREWAI] = {
                "status": "error",
                "last_check": datetime.now(timezone.utc),
                "error": str(e)
            }
        
        logger.info(f"Framework status check completed: {self.framework_status}")
    
    async def analyze_symbol(
        self,
        symbol: str,
        framework: Optional[FrameworkType] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: str = "medium",
        timeout_seconds: int = None
    ) -> AnalysisResult:
        """
        Analyze a symbol using specified framework or best available
        """
        
        # Determine framework
        if framework is None:
            framework = await self._select_best_framework()
        
        # Create analysis request
        request = AnalysisRequest(
            symbol=symbol,
            framework=framework,
            context=context or {},
            priority=priority,
            timeout_seconds=timeout_seconds or self.default_timeout
        )
        
        logger.info(f"Starting analysis for {symbol} using {framework.value}")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Execute analysis based on framework
            if framework == FrameworkType.CREWAI:
                result = await self._run_crewai_analysis(request)
            elif framework == FrameworkType.AUTOGEN:
                result = await self._run_autogen_analysis(request)
            else:
                raise ValueError(f"Unsupported framework: {framework}")
            
            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.execution_time_seconds = execution_time
            
            # Cache result
            cache_key = f"{symbol}_{framework.value}_{hash(json.dumps(context or {}, sort_keys=True))}"
            self.analysis_cache[cache_key] = result
            
            logger.info(f"Analysis completed for {symbol} in {execution_time:.2f}s: {result.recommendation}")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed for {symbol} using {framework.value}: {e}", exc_info=True)
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return AnalysisResult(
                request_id=request.request_id,
                symbol=symbol,
                framework=framework,
                success=False,
                error_message=str(e),
                execution_time_seconds=execution_time
            )
    
    async def _run_crewai_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """Run analysis using CrewAI framework"""
        
        try:
            # Run CrewAI analysis
            crew_result = await run_trading_analysis_crew(
                symbol=request.symbol,
                analysis_context=request.context
            )
            
            # Convert CrewAI result to standardized format
            analysis_data = crew_result if isinstance(crew_result, dict) else {"raw_result": str(crew_result)}
            
            # Extract recommendation and confidence if available
            recommendation = analysis_data.get("final_recommendation", "No clear recommendation")
            confidence = analysis_data.get("confidence", 0.5)
            
            # Generate trading signals if analysis is positive
            signals = []
            if "buy" in recommendation.lower() or "bullish" in recommendation.lower():
                signal = TradingSignal(
                    agent_id="crewai_coordinator",
                    symbol=request.symbol,
                    action="buy",
                    quantity=100.0,  # Default quantity - should be calculated based on risk
                    confidence=confidence,
                    strategy="crewai_analysis",
                    metadata={"source": "crewai", "analysis": analysis_data}
                )
                signals.append(signal)
            
            return AnalysisResult(
                request_id=request.request_id,
                symbol=request.symbol,
                framework=FrameworkType.CREWAI,
                success=True,
                recommendation=recommendation,
                confidence=confidence,
                signals=signals,
                analysis_data=analysis_data
            )
            
        except Exception as e:
            raise Exception(f"CrewAI analysis failed: {e}")
    
    async def _run_autogen_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """Run analysis using AutoGen framework"""
        
        try:
            # Run AutoGen analysis
            autogen_result = await run_trading_analysis_autogen(
                symbol=request.symbol,
                context=request.context
            )
            
            # Convert AutoGen result to standardized format
            analysis_data = autogen_result if isinstance(autogen_result, dict) else {"raw_result": str(autogen_result)}
            
            # Extract recommendation and confidence
            recommendation = analysis_data.get("recommendation", "No recommendation")
            confidence = analysis_data.get("confidence", 0.5)
            
            # Generate trading signals if analysis is positive
            signals = []
            if recommendation.upper() == "BUY":
                signal = TradingSignal(
                    agent_id="autogen_coordinator",
                    symbol=request.symbol,
                    action="buy",
                    quantity=analysis_data.get("position_size", 100.0),
                    price_target=analysis_data.get("entry_price"),
                    stop_loss=analysis_data.get("stop_loss"),
                    take_profit=analysis_data.get("take_profit"),
                    confidence=confidence,
                    strategy="autogen_analysis",
                    metadata={"source": "autogen", "analysis": analysis_data}
                )
                signals.append(signal)
            
            return AnalysisResult(
                request_id=request.request_id,
                symbol=request.symbol,
                framework=FrameworkType.AUTOGEN,
                success=True,
                recommendation=recommendation,
                confidence=confidence,
                signals=signals,
                analysis_data=analysis_data
            )
            
        except Exception as e:
            raise Exception(f"AutoGen analysis failed: {e}")
    
    async def _select_best_framework(self) -> FrameworkType:
        """Select the best available framework based on status and performance"""
        
        await self._check_framework_status()
        
        # Check which frameworks are online
        online_frameworks = [
            framework for framework, status in self.framework_status.items()
            if status.get("status") == "online"
        ]
        
        if not online_frameworks:
            logger.warning("No frameworks are online, defaulting to CrewAI")
            return FrameworkType.CREWAI
        
        # For now, prefer AutoGen if available, otherwise CrewAI
        if FrameworkType.AUTOGEN in online_frameworks:
            return FrameworkType.AUTOGEN
        else:
            return online_frameworks[0]
    
    async def run_consensus_analysis(
        self,
        symbol: str,
        context: Optional[Dict[str, Any]] = None,
        frameworks: Optional[List[FrameworkType]] = None
    ) -> CoordinationTask:
        """
        Run analysis using multiple frameworks and reach consensus
        """
        
        # Default to all available frameworks
        if frameworks is None:
            frameworks = [f for f, status in self.framework_status.items() 
                         if status.get("status") == "online"]
        
        if not frameworks:
            raise ValueError("No frameworks available for consensus analysis")
        
        # Create coordination task
        task = CoordinationTask(
            task_type="consensus",
            symbol=symbol,
            involved_frameworks=frameworks,
            status="running"
        )
        
        self.active_tasks[task.task_id] = task
        
        logger.info(f"Starting consensus analysis for {symbol} using frameworks: {[f.value for f in frameworks]}")
        
        try:
            # Run analysis on all frameworks concurrently
            analysis_tasks = [
                self.analyze_symbol(symbol, framework, context)
                for framework in frameworks
            ]
            
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Process results
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Framework {frameworks[i].value} failed: {result}")
                elif result.success:
                    successful_results.append(result)
                    task.results.append(result)
            
            # Reach consensus
            if successful_results:
                consensus = await self._reach_consensus(successful_results)
                task.consensus_reached = consensus is not None
                task.final_recommendation = consensus
                task.status = "completed"
            else:
                task.status = "failed"
                logger.error(f"All frameworks failed for consensus analysis of {symbol}")
            
            task.completed_at = datetime.now(timezone.utc)
            
            # Move to completed tasks
            self.completed_tasks.append(task)
            del self.active_tasks[task.task_id]
            
            logger.info(f"Consensus analysis completed for {symbol}: consensus={task.consensus_reached}")
            return task
            
        except Exception as e:
            task.status = "failed"
            task.completed_at = datetime.now(timezone.utc)
            logger.error(f"Consensus analysis failed for {symbol}: {e}", exc_info=True)
            return task
    
    async def _reach_consensus(self, results: List[AnalysisResult]) -> Optional[Dict[str, Any]]:
        """Reach consensus from multiple analysis results"""
        
        if not results:
            return None
        
        # Extract recommendations
        recommendations = [r.recommendation for r in results if r.recommendation]
        confidences = [r.confidence for r in results if r.confidence is not None]
        
        if not recommendations:
            return None
        
        # Simple majority voting for now
        buy_votes = sum(1 for rec in recommendations if "buy" in rec.lower() or "bullish" in rec.lower())
        sell_votes = sum(1 for rec in recommendations if "sell" in rec.lower() or "bearish" in rec.lower())
        hold_votes = len(recommendations) - buy_votes - sell_votes
        
        total_votes = len(recommendations)
        max_votes = max(buy_votes, sell_votes, hold_votes)
        
        # Check if consensus threshold is met
        if max_votes / total_votes < self.consensus_threshold:
            logger.info(f"No consensus reached: buy={buy_votes}, sell={sell_votes}, hold={hold_votes}")
            return None
        
        # Determine consensus recommendation
        if max_votes == buy_votes:
            consensus_action = "BUY"
        elif max_votes == sell_votes:
            consensus_action = "SELL"
        else:
            consensus_action = "HOLD"
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Aggregate analysis data
        aggregated_data = {
            "framework_results": {r.framework.value: r.analysis_data for r in results},
            "voting_summary": {
                "buy_votes": buy_votes,
                "sell_votes": sell_votes, 
                "hold_votes": hold_votes,
                "total_votes": total_votes,
                "consensus_threshold": self.consensus_threshold
            }
        }
        
        consensus = {
            "action": consensus_action,
            "confidence": avg_confidence,
            "consensus_strength": max_votes / total_votes,
            "supporting_frameworks": len(results),
            "analysis_data": aggregated_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Consensus reached: {consensus_action} with {avg_confidence:.2f} confidence")
        return consensus
    
    async def execute_trading_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """Execute a trading signal through the coordination layer"""
        
        # Safety validation
        is_safe, rejection_reason = await self.safety_service.validate_trade_safety(
            agent_id=signal.agent_id,
            symbol=signal.symbol,
            quantity=signal.quantity,
            price=signal.price_target
        )
        
        if not is_safe:
            logger.warning(f"Trading signal rejected by safety service: {rejection_reason}")
            return {
                "success": False,
                "signal_id": signal.signal_id,
                "error": f"Safety rejection: {rejection_reason}"
            }
        
        # Execute through trading bridge
        try:
            execution_result = await self.trading_bridge.process_agent_signal(signal)
            
            # Record trade with performance service
            if execution_result.status in ["filled", "partially_filled"]:
                await self.performance_service.record_trade_entry(
                    trade_id=execution_result.execution_id,
                    agent_id=signal.agent_id,
                    symbol=signal.symbol,
                    side=signal.action,
                    quantity=signal.quantity,
                    entry_price=execution_result.average_fill_price or signal.price_target or 0.0,
                    strategy=signal.strategy,
                    confidence=signal.confidence,
                    metadata=signal.metadata
                )
            
            return {
                "success": True,
                "signal_id": signal.signal_id,
                "execution_result": execution_result.model_dump()
            }
            
        except Exception as e:
            logger.error(f"Trading signal execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "signal_id": signal.signal_id,
                "error": str(e)
            }
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """Get comprehensive coordination service status"""
        return {
            "service_status": "online",
            "framework_status": self.framework_status,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "cached_analyses": len(self.analysis_cache),
            "configuration": {
                "default_timeout": self.default_timeout,
                "consensus_threshold": self.consensus_threshold,
                "max_concurrent_tasks": self.max_concurrent_tasks
            },
            "last_status_check": datetime.now(timezone.utc).isoformat()
        }
    
    def get_task_status(self, task_id: str) -> Optional[CoordinationTask]:
        """Get status of a specific coordination task"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return task
        
        return None

# Factory function for service registry
def create_agent_coordination_service(
    trading_bridge: AgentTradingBridge,
    safety_service: TradingSafetyService,
    performance_service: AgentPerformanceService
) -> AgentCoordinationService:
    """Factory function to create agent coordination service"""
    return AgentCoordinationService(trading_bridge, safety_service, performance_service)