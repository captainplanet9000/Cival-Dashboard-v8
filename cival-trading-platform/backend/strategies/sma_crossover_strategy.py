"""
SMA Crossover Strategy Module.

This module implements a Simple Moving Average (SMA) crossover trading strategy.
It generates buy signals when the fast SMA crosses above the slow SMA,
and sell signals when the fast SMA crosses below the slow SMA.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
import pandas as pd
import numpy as np
from loguru import logger

from .base_strategy import BaseStrategy
from ..models.trading_strategy import SignalType, TimeFrame

class SMACrossoverStrategy(BaseStrategy):
    """
    Simple Moving Average (SMA) Crossover Strategy.
    
    This strategy generates:
    - BUY signals when the fast SMA crosses above the slow SMA
    - SELL signals when the fast SMA crosses below the slow SMA
    - HOLD signals when there is no crossover
    
    Default parameters:
    - fast_period: 20 (days/periods for the faster moving average)
    - slow_period: 50 (days/periods for the slower moving average)
    - signal_threshold: 0.0 (minimum difference between SMAs to generate a signal)
    """
    
    def __init__(
        self,
        strategy_id: Optional[str] = None,
        strategy_name: str = "SMA Crossover Strategy",
        parameters: Dict[str, Any] = None,
        description: str = "Simple Moving Average crossover strategy generating signals based on fast and slow SMA crossovers",
        metadata: Dict[str, Any] = None
    ):
        """
        Initialize the SMA Crossover strategy.
        
        Args:
            strategy_id: Unique identifier for the strategy instance.
            strategy_name: Human-readable name for the strategy.
            parameters: Strategy-specific parameters (fast_period, slow_period, signal_threshold).
            description: Detailed description of the strategy.
            metadata: Additional metadata about the strategy.
        """
        # Set default parameters if not provided
        default_params = {
            "fast_period": 20,
            "slow_period": 50,
            "signal_threshold": 0.0  # Minimum difference between SMAs to generate a signal
        }
        
        parameters = parameters or {}
        for key, default_value in default_params.items():
            if key not in parameters:
                parameters[key] = default_value
        
        # Validate parameters
        if parameters["fast_period"] >= parameters["slow_period"]:
            logger.warning(f"Fast period ({parameters['fast_period']}) should be less than slow period ({parameters['slow_period']}). Adjusting.")
            parameters["fast_period"] = max(5, parameters["slow_period"] // 2)
        
        # Initialize the base strategy
        super().__init__(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_type="sma_crossover",
            parameters=parameters,
            description=description,
            metadata=metadata
        )
        
        logger.info(f"Initialized SMA Crossover strategy with fast_period={self.parameters['fast_period']}, "
                   f"slow_period={self.parameters['slow_period']}, signal_threshold={self.parameters['signal_threshold']}")
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the SMA indicators on the provided DataFrame.
        
        Args:
            df: DataFrame with market data.
            
        Returns:
            DataFrame with additional SMA columns.
        """
        fast_period = self.parameters["fast_period"]
        slow_period = self.parameters["slow_period"]
        
        # Calculate SMAs
        df = df.copy()
        df['fast_sma'] = df['close'].rolling(window=fast_period).mean()
        df['slow_sma'] = df['close'].rolling(window=slow_period).mean()
        
        # Calculate SMA difference and crossover
        df['sma_diff'] = df['fast_sma'] - df['slow_sma']
        df['crossover'] = np.sign(df['sma_diff']).diff()
        
        return df
    
    def _generate_signal_internal(self, symbol: str, timeframe: Union[str, TimeFrame]) -> Tuple[SignalType, Optional[float], Dict[str, Any]]:
        """
        Generate a trading signal based on SMA crossover.
        
        Args:
            symbol: The trading symbol to generate a signal for.
            timeframe: The timeframe to use for signal generation.
            
        Returns:
            Tuple containing:
            - SignalType: The type of signal (BUY, SELL, HOLD)
            - Optional[float]: Confidence level (0-100)
            - Dict[str, Any]: Additional metadata about the signal
        """
        key = f"{symbol}_{timeframe}"
        if key not in self._market_data:
            raise ValueError(f"No market data available for {symbol} {timeframe}")
        
        # Get market data and calculate indicators
        df = self._market_data[key]
        df = self._calculate_indicators(df)
        
        # Default to HOLD
        signal_type = SignalType.HOLD
        confidence = 50.0
        
        # Check for recent crossover
        last_crossover = df['crossover'].iloc[-1] if not df.empty else 0
        last_diff = df['sma_diff'].iloc[-1] if not df.empty else 0
        threshold = self.parameters["signal_threshold"]
        
        metadata = {
            "fast_sma": float(df['fast_sma'].iloc[-1]) if not df.empty and not pd.isna(df['fast_sma'].iloc[-1]) else None,
            "slow_sma": float(df['slow_sma'].iloc[-1]) if not df.empty and not pd.isna(df['slow_sma'].iloc[-1]) else None,
            "sma_diff": float(last_diff) if not pd.isna(last_diff) else None,
            "last_crossover": float(last_crossover) if not pd.isna(last_crossover) else None,
            "parameters": {
                "fast_period": self.parameters["fast_period"],
                "slow_period": self.parameters["slow_period"],
                "signal_threshold": self.parameters["signal_threshold"]
            }
        }
        
        # Generate signal based on crossover and threshold
        if last_crossover > 0 and abs(last_diff) > threshold:
            # Fast SMA crossed above slow SMA
            signal_type = SignalType.BUY
            # Higher confidence with larger difference
            confidence = min(90.0, 50.0 + (abs(last_diff) / (df['close'].iloc[-1] if not df.empty else 1)) * 1000)
        elif last_crossover < 0 and abs(last_diff) > threshold:
            # Fast SMA crossed below slow SMA
            signal_type = SignalType.SELL
            # Higher confidence with larger difference
            confidence = min(90.0, 50.0 + (abs(last_diff) / (df['close'].iloc[-1] if not df.empty else 1)) * 1000)
        else:
            # No crossover or below threshold
            # If fast SMA is above slow SMA, a weak buy signal
            if last_diff > 0:
                confidence = 50.0 + min(20.0, (last_diff / (df['close'].iloc[-1] if not df.empty else 1)) * 500)
            # If fast SMA is below slow SMA, a weak sell signal
            elif last_diff < 0:
                confidence = 50.0 - min(20.0, (abs(last_diff) / (df['close'].iloc[-1] if not df.empty else 1)) * 500)
        
        logger.debug(f"SMA Crossover strategy generated {signal_type} signal with confidence {confidence:.2f} for {symbol} {timeframe}")
        return signal_type, confidence, metadata
    
    def optimize_parameters(self, symbol: str, timeframe: Union[str, TimeFrame], optimization_metric: str = "win_rate") -> Dict[str, Any]:
        """
        Optimize strategy parameters for a specific symbol and timeframe.
        
        Args:
            symbol: The trading symbol to optimize for.
            timeframe: The timeframe to use for optimization.
            optimization_metric: The metric to optimize for (default: "win_rate").
            
        Returns:
            Dict with optimized parameters.
        """
        key = f"{symbol}_{timeframe}"
        if key not in self._market_data:
            raise ValueError(f"No market data available for {symbol} {timeframe}")
        
        # In a real implementation, this would run a grid search or other optimization
        # For now, we just return the current parameters
        logger.info(f"Optimizing SMA Crossover parameters for {symbol} {timeframe}")
        
        # Simple optimization for demonstration
        best_params = self.parameters.copy()
        best_metric = 0.0
        
        # Try a few parameter combinations
        fast_periods = [5, 10, 20, 30]
        slow_periods = [20, 50, 100, 200]
        
        for fast_period in fast_periods:
            for slow_period in slow_periods:
                if fast_period >= slow_period:
                    continue
                    
                # Set test parameters
                test_params = self.parameters.copy()
                test_params["fast_period"] = fast_period
                test_params["slow_period"] = slow_period
                
                # Calculate metric (simplified)
                # In a real implementation, this would involve backtesting
                metric = self._calculate_test_metric(symbol, timeframe, test_params)
                
                # Update best parameters if better
                if metric > best_metric:
                    best_metric = metric
                    best_params = test_params
        
        logger.info(f"Optimized parameters: fast_period={best_params['fast_period']}, "
                   f"slow_period={best_params['slow_period']}, metric={best_metric:.4f}")
        
        # Update the strategy parameters
        self.parameters = best_params
        return best_params
    
    def _calculate_test_metric(self, symbol: str, timeframe: Union[str, TimeFrame], test_params: Dict[str, Any]) -> float:
        """
        Calculate a test metric for parameter optimization.
        
        Args:
            symbol: The trading symbol.
            timeframe: The timeframe.
            test_params: Parameters to test.
            
        Returns:
            Float value of the metric (higher is better).
        """
        # This is a simplified metric calculation for demonstration
        # In a real implementation, this would involve backtesting
        
        key = f"{symbol}_{timeframe}"
        df = self._market_data[key].copy()
        
        # Calculate SMAs with test parameters
        fast_period = test_params["fast_period"]
        slow_period = test_params["slow_period"]
        
        df['fast_sma'] = df['close'].rolling(window=fast_period).mean()
        df['slow_sma'] = df['close'].rolling(window=slow_period).mean()
        df['sma_diff'] = df['fast_sma'] - df['slow_sma']
        df['crossover'] = np.sign(df['sma_diff']).diff()
        
        # Drop NaN values
        df = df.dropna()
        
        if len(df) < 10:
            return 0.0
        
        # Count crossovers
        buy_signals = (df['crossover'] > 0).sum()
        sell_signals = (df['crossover'] < 0).sum()
        total_signals = buy_signals + sell_signals
        
        if total_signals == 0:
            return 0.0
        
        # Calculate a simple metric based on price movement after signals
        # This is very simplified and for demonstration only
        correct_buys = 0
        correct_sells = 0
        
        for i in range(len(df) - 1):
            if df['crossover'].iloc[i] > 0:  # Buy signal
                # Check if price increased in the next period
                if df['close'].iloc[i + 1] > df['close'].iloc[i]:
                    correct_buys += 1
            elif df['crossover'].iloc[i] < 0:  # Sell signal
                # Check if price decreased in the next period
                if df['close'].iloc[i + 1] < df['close'].iloc[i]:
                    correct_sells += 1
        
        # Calculate win rate
        win_rate = (correct_buys + correct_sells) / max(1, total_signals)
        
        # Prefer strategies with more signals (within reason)
        signal_factor = min(1.0, total_signals / 20)
        
        # Combine metrics
        metric = win_rate * signal_factor
        
        return metric
