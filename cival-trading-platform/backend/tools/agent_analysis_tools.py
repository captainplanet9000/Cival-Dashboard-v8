from crewai_tools import BaseTool, tool
from typing import Type, Optional, Any
from pydantic import BaseModel, Field
import pandas as pd # For type hinting and potential use in tool descriptions
import json # For converting dict/list outputs to JSON strings

# Import the underlying tool functions
from .market_data_tools import (
    get_historical_price_data_tool,
    get_current_quote_tool,
    search_symbols_tool,
    HistoricalPriceRequest, # For args schema if needed
    QuoteRequest,
    SymbolSearchRequest
)
from .technical_analysis_tools import (
    calculate_sma_tool,
    calculate_ema_tool,
    calculate_rsi_tool,
    calculate_macd_tool
    # TAIndicatorRequest # Could be used for args schema if tools were more complex
)
from logging import getLogger

logger = getLogger(__name__)

# --- Pydantic Schemas for Tool Arguments (CrewAI uses these for validation and description) ---

class HistoricalDataArgs(BaseModel):
    symbol: str = Field(..., description="The stock symbol (e.g., 'AAPL').")
    start_date: str = Field(..., description="Start date for data (YYYY-MM-DD).")
    end_date: str = Field(..., description="End date for data (YYYY-MM-DD).")
    interval: str = Field(default="1d", description="Data interval (e.g., '1d', '1h').")
    provider: str = Field(default="yfinance", description="Data provider (e.g., 'yfinance').")

class CurrentQuoteArgs(BaseModel):
    symbol: str = Field(..., description="The stock symbol (e.g., 'AAPL').")
    provider: str = Field(default="yfinance", description="Data provider.")

class SymbolSearchArgs(BaseModel):
    query: str = Field(..., description="Search query for symbols or companies.")
    provider: str = Field(default="yfinance", description="Data provider.")
    is_etf: Optional[bool] = Field(default=None, description="Filter for ETFs if True/False.")

class SMAArgs(BaseModel):
    symbol: str = Field(..., description="Stock symbol for SMA calculation.")
    start_date: str = Field(..., description="Start date for data (YYYY-MM-DD).")
    end_date: str = Field(..., description="End date for data (YYYY-MM-DD).")
    window: int = Field(default=20, description="Window period for SMA.")
    # provider: str = Field(default="yfinance", description="Data provider for fetching price data.") # Added provider

class EMAArgs(SMAArgs): # Inherits from SMAArgs, provider included if added to SMAArgs
    pass

class RSIArgs(SMAArgs): # Inherits from SMAArgs, provider included if added to SMAArgs
    pass

class MACDArgs(BaseModel):
    symbol: str = Field(..., description="Stock symbol for MACD calculation.")
    start_date: str = Field(..., description="Start date for data (YYYY-MM-DD).")
    end_date: str = Field(..., description="End date for data (YYYY-MM-DD).")
    # provider: str = Field(default="yfinance", description="Data provider for fetching price data.") # Added provider
    fast_period: int = Field(default=12)
    slow_period: int = Field(default=26)
    signal_period: int = Field(default=9)


# --- CrewAI Tools ---

@tool("Get Historical Stock Prices Tool", args_schema=HistoricalDataArgs)
def historical_stock_prices(symbol: str, start_date: str, end_date: str, interval: str = "1d", provider: str = "yfinance") -> str:
    """
    Fetches historical OHLCV stock price data for a given symbol and date range.
    Returns data as a JSON string of records or an error message.
    """
    logger.info(f"CrewAI Tool: historical_stock_prices called for {symbol} from {start_date} to {end_date}")
    try:
        # Pydantic validation is implicitly handled by CrewAI if args_schema is used.
        # Explicit validation here is redundant if relying on CrewAI's mechanisms.
        # HistoricalDataArgs(symbol=symbol, start_date=start_date, end_date=end_date, interval=interval, provider=provider)
        pass
    except Exception as e: # Should be caught by CrewAI based on args_schema
        return f"Error: Invalid arguments for historical_stock_prices: {e}"

    df = get_historical_price_data_tool(symbol, start_date, end_date, interval, provider)
    if df is not None:
        return df.to_json(orient="records", date_format="iso")
    return "Error: Could not fetch historical data. The symbol might be invalid, dates out of range, or provider issue."

@tool("Get Current Stock Quote Tool", args_schema=CurrentQuoteArgs)
def current_stock_quote(symbol: str, provider: str = "yfinance") -> str:
    """
    Fetches the current stock quote (latest price, volume, etc.) for a symbol.
    Returns data as a JSON string or an error message.
    """
    logger.info(f"CrewAI Tool: current_stock_quote called for {symbol}")
    try:
        # QuoteRequest(symbol=symbol, provider=provider) # Implicitly handled by args_schema
        pass
    except Exception as e:
        return f"Error: Invalid arguments for current_stock_quote: {e}"

    quote_dict = get_current_quote_tool(symbol, provider)
    if quote_dict is not None:
        return json.dumps(quote_dict)
    return "Error: Could not fetch current quote. Symbol might be invalid or provider issue."

@tool("Search Stock Symbols Tool", args_schema=SymbolSearchArgs)
def search_stock_symbols(query: str, provider: str = "yfinance", is_etf: Optional[bool] = None) -> str:
    """
    Searches for stock symbols and company names based on a query.
    Returns a list of findings as a JSON string or an error message.
    """
    logger.info(f"CrewAI Tool: search_stock_symbols called with query: {query}")
    try:
        # SymbolSearchRequest(query=query, provider=provider, is_etf=is_etf) # Implicitly handled
        pass
    except Exception as e:
        return f"Error: Invalid arguments for search_stock_symbols: {e}"

    results_list = search_symbols_tool(query, provider, is_etf)
    if results_list is not None:
        return json.dumps(results_list)
    return "Error: Symbol search failed or returned no results."


@tool("Calculate SMA Tool", args_schema=SMAArgs)
def sma_calculation_tool(symbol: str, start_date: str, end_date: str, window: int = 20, provider: str = "yfinance") -> str:
    """Calculates Simple Moving Average (SMA) for a stock over a period.
    Returns SMA data as a JSON string (orient='split') or an error message."""
    logger.info(f"CrewAI Tool: sma_calculation_tool for {symbol}, window {window}")
    # Provider can be added to SMAArgs if needed, or taken from a default/global config
    price_df = get_historical_price_data_tool(symbol, start_date, end_date, provider=provider)
    if price_df is None:
        return "Error: Could not fetch price data for SMA calculation."
    sma_series = calculate_sma_tool(price_df, window)
    if sma_series is not None:
        return sma_series.to_json(orient="split", date_format="iso")
    return f"Error: Could not calculate SMA for {symbol}."


@tool("Calculate EMA Tool", args_schema=EMAArgs)
def ema_calculation_tool(symbol: str, start_date: str, end_date: str, window: int = 20, provider: str = "yfinance") -> str:
    """Calculates Exponential Moving Average (EMA) for a stock. Returns JSON string."""
    logger.info(f"CrewAI Tool: ema_calculation_tool for {symbol}, window {window}")
    price_df = get_historical_price_data_tool(symbol, start_date, end_date, provider=provider)
    if price_df is None: return "Error: Could not fetch price data for EMA."
    ema_series = calculate_ema_tool(price_df, window)
    if ema_series is not None: return ema_series.to_json(orient="split", date_format="iso")
    return f"Error: Could not calculate EMA for {symbol}."

@tool("Calculate RSI Tool", args_schema=RSIArgs)
def rsi_calculation_tool(symbol: str, start_date: str, end_date: str, window: int = 14, provider: str = "yfinance") -> str:
    """Calculates Relative Strength Index (RSI) for a stock. Returns JSON string."""
    logger.info(f"CrewAI Tool: rsi_calculation_tool for {symbol}, window {window}")
    price_df = get_historical_price_data_tool(symbol, start_date, end_date, provider=provider)
    if price_df is None: return "Error: Could not fetch price data for RSI."
    rsi_series = calculate_rsi_tool(price_df, window)
    if rsi_series is not None: return rsi_series.to_json(orient="split", date_format="iso")
    return f"Error: Could not calculate RSI for {symbol}."

@tool("Calculate MACD Tool", args_schema=MACDArgs)
def macd_calculation_tool(symbol: str, start_date: str, end_date: str,
                          fast_period: int = 12, slow_period: int = 26, signal_period: int = 9,
                          provider: str = "yfinance") -> str:
    """Calculates MACD for a stock. Returns JSON string of DataFrame."""
    logger.info(f"CrewAI Tool: macd_calculation_tool for {symbol}")
    price_df = get_historical_price_data_tool(symbol, start_date, end_date, provider=provider)
    if price_df is None: return "Error: Could not fetch price data for MACD."
    macd_df = calculate_macd_tool(price_df, fast_period, slow_period, signal_period)
    if macd_df is not None: return macd_df.to_json(orient="split", date_format="iso")
    return f"Error: Could not calculate MACD for {symbol}."
