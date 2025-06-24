"""
Base Strategy Module.

This module defines the BaseStrategy abstract class that all trading strategies must inherit from.
It provides common functionality and a standardized interface for strategy implementation.
"""

import abc
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
import pandas as pd
import numpy as np
from loguru import logger
import uuid

from ..models.trading_strategy import (
    TradingStrategy, TradingSignal, SignalType, 
    OHLCVData, TimeFrame, TechnicalIndicatorValue
)

class BaseStrategy(abc.ABC):
    """
    Abstract base class for all trading strategies.
    
    This class defines the interface that all trading strategies must implement.
    It provides common functionality for handling market data, generating signals,
    and tracking performance metrics.
    """
    
    def __init__(
        self,
        strategy_id: Optional[str] = None,
        strategy_name: str = "Unnamed Strategy",
        strategy_type: str = "base",
        parameters: Dict[str, Any] = None,
        description: str = "",
        metadata: Dict[str, Any] = None
    ):
        """
        Initialize the base strategy.
        
        Args:
            strategy_id: Unique identifier for the strategy instance.
            strategy_name: Human-readable name for the strategy.
            strategy_type: Type of strategy (e.g., "sma_crossover", "darvas_box").
            parameters: Strategy-specific parameters.
            description: Detailed description of the strategy.
            metadata: Additional metadata about the strategy.
        """
        self.strategy_id = strategy_id or str(uuid.uuid4())
        self.strategy_name = strategy_name
        self.strategy_type = strategy_type
        self.parameters = parameters or {}
        self.description = description
        self.metadata = metadata or {}
        
        # Market data cache
        self._market_data: Dict[str, pd.DataFrame] = {}
        
        # Performance tracking
        self.signals: List[TradingSignal] = []
        self.performance_metrics: Dict[str, Any] = {
            "total_signals": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "hold_signals": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
        }
        
        logger.info(f"Initialized {self.strategy_type} strategy: {self.strategy_name} (ID: {self.strategy_id})")

    def to_model(self) -> TradingStrategy:
        """
        Convert the strategy instance to a TradingStrategy model.
        
        Returns:
            TradingStrategy: The model representation of this strategy.
        """
        return TradingStrategy(
            id=uuid.UUID(self.strategy_id) if isinstance(self.strategy_id, str) else self.strategy_id,
            name=self.strategy_name,
            type=self.strategy_type,
            description=self.description,
            parameters=self.parameters,
            is_active=True,
            metadata=self.metadata
        )
    
    @classmethod
    def from_model(cls, model: TradingStrategy) -> 'BaseStrategy':
        """
        Create a strategy instance from a TradingStrategy model.
        
        Args:
            model: The TradingStrategy model to convert.
            
        Returns:
            BaseStrategy: A new instance of the strategy.
        """
        return cls(
            strategy_id=str(model.id),
            strategy_name=model.name,
            strategy_type=model.type,
            parameters=model.parameters,
            description=model.description or "",
            metadata=model.metadata or {}
        )
    
    def add_market_data(self, symbol: str, timeframe: Union[str, TimeFrame], data: Union[pd.DataFrame, List[Dict[str, Any]], List[OHLCVData]]) -> None:
        """
        Add market data for a symbol and timeframe.
        
        Args:
            symbol: The trading symbol (e.g., "AAPL", "BTC/USD").
            timeframe: The timeframe of the data (e.g., "1h", "1d").
            data: Market data as DataFrame or list of dictionaries/OHLCVData objects.
        """
        key = f"{symbol}_{timeframe}"
        
        if isinstance(data, list):
            if not data:
                logger.warning(f"Empty data list provided for {symbol} {timeframe}")
                return
                
            if isinstance(data[0], dict):
                df = pd.DataFrame(data)
            elif isinstance(data[0], OHLCVData):
                df = pd.DataFrame([d.dict() for d in data])
            else:
                raise ValueError(f"Unsupported data type in list: {type(data[0])}")
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        
        # Ensure standard column names
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            raise ValueError(f"Missing required columns: {missing}")
        
        # Set timestamp as index if not already
        if 'timestamp' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        
        # Ensure numeric types for OHLCV data
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        self._market_data[key] = df
        logger.info(f"Added market data for {symbol} {timeframe}: {len(df)} rows")
    
    def get_market_data(self, symbol: str, timeframe: Union[str, TimeFrame]) -> Optional[pd.DataFrame]:
        """
        Get market data for a symbol and timeframe.
        
        Args:
            symbol: The trading symbol (e.g., "AAPL", "BTC/USD").
            timeframe: The timeframe of the data (e.g., "1h", "1d").
            
        Returns:
            DataFrame with market data if available, None otherwise.
        """
        key = f"{symbol}_{timeframe}"
        return self._market_data.get(key)
    
    def clear_market_data(self) -> None:
        """Clear all cached market data."""
        self._market_data.clear()
        logger.info("Cleared all market data from strategy cache")
    
    def generate_signal(self, symbol: str, timeframe: Union[str, TimeFrame], confidence: Optional[float] = None) -> TradingSignal:
        """
        Generate a trading signal for a symbol and timeframe.
        
        This method calls the strategy-specific _generate_signal_internal method
        and tracks the signal in the performance metrics.
        
        Args:
            symbol: The trading symbol to generate a signal for.
            timeframe: The timeframe to use for signal generation.
            confidence: Optional confidence level override.
            
        Returns:
            TradingSignal: The generated trading signal.
        """
        # Ensure we have market data
        key = f"{symbol}_{timeframe}"
        if key not in self._market_data:
            raise ValueError(f"No market data available for {symbol} {timeframe}")
        
        # Generate the signal using the strategy-specific implementation
        signal_type, signal_confidence, metadata = self._generate_signal_internal(symbol, timeframe)
        
        # Use the provided confidence if specified
        if confidence is not None:
            signal_confidence = confidence
        
        # Get the current price from the most recent market data
        df = self._market_data[key]
        current_price = float(df['close'].iloc[-1]) if not df.empty else None
        
        # Create the signal object
        signal = TradingSignal(
            strategy_id=uuid.UUID(self.strategy_id) if isinstance(self.strategy_id, str) else self.strategy_id,
            symbol=symbol,
            timeframe=str(timeframe),
            signal=signal_type,
            confidence=signal_confidence,
            price=current_price,
            metadata=metadata
        )
        
        # Track the signal for performance metrics
        self.signals.append(signal)
        self.performance_metrics["total_signals"] += 1
        if signal_type == SignalType.BUY:
            self.performance_metrics["buy_signals"] += 1
        elif signal_type == SignalType.SELL:
            self.performance_metrics["sell_signals"] += 1
        else:  # HOLD
            self.performance_metrics["hold_signals"] += 1
        
        logger.info(f"Generated {signal_type} signal for {symbol} {timeframe} with confidence {signal_confidence}")
        return signal
    
    @abc.abstractmethod
    def _generate_signal_internal(self, symbol: str, timeframe: Union[str, TimeFrame]) -> Tuple[SignalType, Optional[float], Dict[str, Any]]:
        """
        Strategy-specific signal generation logic.
        
        This method must be implemented by each strategy subclass.
        
        Args:
            symbol: The trading symbol to generate a signal for.
            timeframe: The timeframe to use for signal generation.
            
        Returns:
            Tuple containing:
            - SignalType: The type of signal (BUY, SELL, HOLD)
            - Optional[float]: Confidence level (0-100)
            - Dict[str, Any]: Additional metadata about the signal
        """
        pass
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics for the strategy.
        
        Returns:
            Dict with performance metrics.
        """
        # This is a basic implementation that should be enhanced in real usage
        if not self.signals:
            return self.performance_metrics
        
        # Calculate win rate based on signals (simplified)
        # In a real implementation, this would be based on actual trades
        self.performance_metrics["win_rate"] = 0.0
        
        logger.info(f"Calculated performance metrics for {self.strategy_name}")
        return self.performance_metrics
    
    def __repr__(self) -> str:
        """String representation of the strategy."""
        return f"{self.strategy_type.capitalize()}Strategy(name='{self.strategy_name}', id='{self.strategy_id}')"
