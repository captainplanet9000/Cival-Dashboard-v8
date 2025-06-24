# This file makes the 'tools' directory a Python package.
# Custom tools for CrewAI agents can be defined in modules within this package.

from .market_data_tools import (
    get_historical_price_data_tool,
    get_current_quote_tool,
    search_symbols_tool,
    HistoricalPriceRequest,
    QuoteRequest,
    SymbolSearchRequest
)
from .technical_analysis_tools import (
    calculate_sma_tool,
    calculate_ema_tool,
    calculate_rsi_tool,
    calculate_macd_tool,
    TAIndicatorRequest
)
from .risk_assessment_tools import (
    calculate_position_size_tool,
    check_trade_risk_limit_tool,
    PositionSizeRequest,
    RiskCheckRequest
)
from .agent_analysis_tools import (
    historical_stock_prices,
    current_stock_quote,
    search_stock_symbols,
    sma_calculation_tool,
    ema_calculation_tool,
    rsi_calculation_tool,
    macd_calculation_tool,
    HistoricalDataArgs,
    CurrentQuoteArgs,
    SymbolSearchArgs,
    SMAArgs,
    # EMAArgs uses SMAArgs, no need to export EMAArgs explicitly if it's identical
    # RSIArgs uses SMAArgs, no need to export RSIArgs explicitly if it's identical
    MACDArgs
)

__all__ = [
    # Market Data Tools
    "get_historical_price_data_tool",
    "get_current_quote_tool",
    "search_symbols_tool",
    "HistoricalPriceRequest",
    "QuoteRequest",
    "SymbolSearchRequest",
    # Technical Analysis Tools
    "calculate_sma_tool",
    "calculate_ema_tool",
    "calculate_rsi_tool",
    "calculate_macd_tool",
    "TAIndicatorRequest",
    # Risk Assessment Tools
    "calculate_position_size_tool",
    "check_trade_risk_limit_tool",
    "PositionSizeRequest",
    "RiskCheckRequest",
    # Agent Analysis Tools (CrewAI compatible)
    "historical_stock_prices",
    "current_stock_quote",
    "search_stock_symbols",
    "sma_calculation_tool",
    "ema_calculation_tool",
    "rsi_calculation_tool",
    "macd_calculation_tool",
    "HistoricalDataArgs",
    "CurrentQuoteArgs",
    "SymbolSearchArgs",
    "SMAArgs",
    "MACDArgs"
]
