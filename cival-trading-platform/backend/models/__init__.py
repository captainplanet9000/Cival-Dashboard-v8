# __init__.py for models
from .api_models import (
    TradingAnalysisCrewRequest,
    TradingSignal,
    BaseResponseModel,
    ErrorDetail,
    TradeDecisionAction,
    TradingDecision,
    ExecuteTradeRequest,
    ExecuteTradeResponse,
    RegisterAgentRequest,
    RegisterAgentResponse,
    AgentStatusResponse,
    AgentTradingHistoryResponse,
    TradeExecutionResult,
    SetTradeExecutionModeRequest,
    SetTradeExecutionModeResponse,
    GetTradeExecutionModeResponse
)

from .paper_trading_models import (
    PaperTradeOrder,
    PaperTradeFill,
    PaperAccountSummary
)

from .trading_history_models import (
    TradeSide,
    OrderStatus,
    OrderType,
    TradeRecord,
    TradingHistory
)

from .hyperliquid_models import (
    HyperliquidCredentials,
    HyperliquidPlaceOrderParams,
    HyperliquidOrderResponseData,
    HyperliquidOrderStatusInfo,
    HyperliquidAssetPosition,
    HyperliquidOpenOrderItem,
    HyperliquidMarginSummary,
    HyperliquidAccountSnapshot
)

from .agent_models import (
    AgentStrategyConfig,
    AgentRiskConfig,
    AgentConfigBase,
    AgentConfigInput,
    AgentConfigOutput,
    AgentStatus,
    AgentUpdateRequest
)

from .dashboard_models import (
    AssetPositionSummary,
    PortfolioSummary,
    TradeLogItem,
    OrderLogItem
)

from .performance_models import (
    PerformanceMetrics
)

from .alert_models import (
    AlertCondition,
    AlertConfigBase,
    AlertConfigInput,
    AlertConfigOutput,
    AlertNotification
)

from .simulation_models import ( # Added
    BacktestRequest,
    BacktestResult,
    SimulatedTrade,
    EquityDataPoint
)

from .compliance_models import ( # Added
    ComplianceRule,
    ComplianceCheckRequest,
    ViolatedRuleInfo,
    ComplianceCheckResult
)

from .learning_models import LearningLogEntry # Added
from .websocket_models import WebSocketEnvelope # Added
from .db_models import AgentConfigDB, TradeFillDB, OrderDB # Added TradeFillDB and OrderDB

__all__ = [
    "ExecutionReceipt",
    "ExecutionFillLeg",
    "ExecutionRequest",
    "StrategyDevResponse",
    "StrategyDevRequest",
    # api_models
    "TradingAnalysisCrewRequest", "TradingSignal", "BaseResponseModel", "ErrorDetail",
    "TradeDecisionAction", "TradingDecision", "ExecuteTradeRequest", "ExecuteTradeResponse",
    "RegisterAgentRequest", "RegisterAgentResponse", "AgentStatusResponse",
    "AgentTradingHistoryResponse", "TradeExecutionResult",
    "SetTradeExecutionModeRequest", "SetTradeExecutionModeResponse", "GetTradeExecutionModeResponse",
    # paper_trading_models
    "PaperTradeOrder", "PaperTradeFill", "PaperAccountSummary",
    # trading_history_models
    "TradeSideType", "OrderStatusType", "OrderTypeType",
    "TradeRecord", "TradingHistory", "TradeFillData",
    # hyperliquid_models
    "HyperliquidCredentials", "HyperliquidPlaceOrderParams", "HyperliquidOrderResponseData",
    "HyperliquidOrderStatusInfo", "HyperliquidAssetPosition", "HyperliquidOpenOrderItem",
    "HyperliquidMarginSummary", "HyperliquidAccountSnapshot",
    # agent_models
    "AgentStrategyConfig", "AgentRiskConfig", "AgentConfigBase", "AgentConfigInput",
    "AgentConfigOutput", "AgentStatus", "AgentUpdateRequest",
    "AgentStrategyConfig.DarvasStrategyParams",
    "AgentStrategyConfig.WilliamsAlligatorParams",
    "AgentStrategyConfig.MarketConditionClassifierParams",
    "AgentStrategyConfig.PortfolioOptimizerRule", # For exporting nested models
    "AgentStrategyConfig.PortfolioOptimizerParams",
    "AgentStrategyConfig.NewsAnalysisParams", # Added
    # dashboard_models
    "AssetPositionSummary", "PortfolioSummary", "TradeLogItem", "OrderLogItem", "PortfolioSnapshotOutput", # Added PortfolioSnapshotOutput
    # performance_models
    "PerformanceMetrics",
    # alert_models
    "AlertCondition", "AlertConfigBase", "AlertConfigInput", "AlertConfigOutput", "AlertNotification",
    # simulation_models
    "BacktestRequest", "BacktestResult", "SimulatedTrade", "EquityDataPoint",
    # compliance_models
    "ComplianceRule", "ComplianceCheckRequest", "ViolatedRuleInfo", "ComplianceCheckResult",
    # learning_models
    "LearningLogEntry", # Added
    # websocket_models
    "WebSocketEnvelope", # Added
    # event_bus_models
    "Event", "TradeSignalEventPayload", "MarketInsightEventPayload", "RiskAlertEventPayload",
    "RiskAssessmentRequestData", "RiskAssessmentResponseData", "NewsArticleEventPayload",
    # db_models
    "AgentConfigDB", "TradeFillDB", "OrderDB" # Added TradeFillDB and OrderDB
]

from .market_data_models import Kline, OrderBookLevel, OrderBookSnapshot, Trade

from .strategy_dev_models import StrategyDevRequest, StrategyDevResponse

from .execution_models import ExecutionRequest, ExecutionFillLeg, ExecutionReceipt
