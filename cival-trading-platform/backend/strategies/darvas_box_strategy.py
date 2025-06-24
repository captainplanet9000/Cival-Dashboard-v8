"""
Darvas Box Strategy Module.

This module implements the Darvas Box trading strategy developed by Nicolas Darvas.
It identifies boxes formed by price action and generates signals based on breakouts.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
import pandas as pd
import numpy as np
from loguru import logger

from .base_strategy import BaseStrategy
from ..models.trading_strategy import SignalType, TimeFrame

class DarvasBoxStrategy(BaseStrategy):
    """
    Darvas Box Trading Strategy.
    
    This strategy:
    - Identifies "boxes" formed by price highs and lows over a specified period
    - Generates BUY signals when price breaks above the top of a box
    - Generates SELL signals when price breaks below the bottom of a box
    - Generates HOLD signals when price is inside a box
    
    Default parameters:
    - box_period: 5 (days/periods to look back for box formation)
    - volume_threshold: 1.5 (minimum volume increase for valid breakout)
    - breakout_threshold: 0.01 (minimum percentage above/below box for breakout)
    """
    
    def __init__(
        self,
        strategy_id: Optional[str] = None,
        strategy_name: str = "Darvas Box Strategy",
        parameters: Dict[str, Any] = None,
        description: str = "Darvas Box strategy identifying price consolidation boxes and generating signals on breakouts",
        metadata: Dict[str, Any] = None
    ):
        """
        Initialize the Darvas Box strategy.
        
        Args:
            strategy_id: Unique identifier for the strategy instance.
            strategy_name: Human-readable name for the strategy.
            parameters: Strategy-specific parameters (box_period, volume_threshold, breakout_threshold).
            description: Detailed description of the strategy.
            metadata: Additional metadata about the strategy.
        """
        # Set default parameters if not provided
        default_params = {
            "box_period": 5,
            "volume_threshold": 1.5,
            "breakout_threshold": 0.01  # 1% breakout threshold
        }
        
        parameters = parameters or {}
        for key, default_value in default_params.items():
            if key not in parameters:
                parameters[key] = default_value
        
        # Initialize the base strategy
        super().__init__(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_type="darvas_box",
            parameters=parameters,
            description=description,
            metadata=metadata
        )
        
        logger.info(f"Initialized Darvas Box strategy with box_period={self.parameters['box_period']}, "
                   f"volume_threshold={self.parameters['volume_threshold']}, "
                   f"breakout_threshold={self.parameters['breakout_threshold']}")
    
    def _calculate_darvas_boxes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Darvas Boxes on the provided DataFrame.
        
        Args:
            df: DataFrame with market data.
            
        Returns:
            DataFrame with additional Darvas Box columns.
        """
        box_period = self.parameters["box_period"]
        
        # Create a copy of the DataFrame
        df = df.copy()
        
        # Calculate rolling max and min for box tops and bottoms
        df['box_top'] = df['high'].rolling(window=box_period).max()
        df['box_bottom'] = df['low'].rolling(window=box_period).min()
        
        # Calculate volume moving average for volume breakout confirmation
        df['volume_ma'] = df['volume'].rolling(window=box_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # Calculate percentage distance from box top and bottom
        df['distance_from_top'] = (df['close'] - df['box_top']) / df['box_top']
        df['distance_from_bottom'] = (df['close'] - df['box_bottom']) / df['box_bottom']
        
        # Calculate breakout signals
        breakout_threshold = self.parameters["breakout_threshold"]
        volume_threshold = self.parameters["volume_threshold"]
        
        # Top breakout condition (price above box top with volume confirmation)
        df['top_breakout'] = (
            (df['close'] > df['box_top'] * (1 + breakout_threshold)) & 
            (df['volume_ratio'] > volume_threshold)
        )
        
        # Bottom breakout condition (price below box bottom with volume confirmation)
        df['bottom_breakout'] = (
            (df['close'] < df['box_bottom'] * (1 - breakout_threshold)) & 
            (df['volume_ratio'] > volume_threshold)
        )
        
        # Add box state
        conditions = [
            df['top_breakout'],
            df['bottom_breakout'],
            ~df['top_breakout'] & ~df['bottom_breakout']
        ]
        choices = ['top_breakout', 'bottom_breakout', 'inside_box']
        df['box_state'] = np.select(conditions, choices, default='inside_box')
        
        return df
    
    def _generate_signal_internal(self, symbol: str, timeframe: Union[str, TimeFrame]) -> Tuple[SignalType, Optional[float], Dict[str, Any]]:
        """
        Generate a trading signal based on Darvas Box breakouts.
        
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
        
        # Get market data and calculate Darvas Boxes
        df = self._market_data[key]
        df = self._calculate_darvas_boxes(df)
        
        # Default to HOLD
        signal_type = SignalType.HOLD
        confidence = 50.0
        
        # Check for breakouts in recent periods
        if len(df) >= 3:
            latest_state = df['box_state'].iloc[-1]
            prev_state = df['box_state'].iloc[-2]
            
            # Current box state
            if latest_state == 'top_breakout':
                signal_type = SignalType.BUY
                # Higher confidence with larger breakout and higher volume
                volume_factor = min(2.0, float(df['volume_ratio'].iloc[-1]) / self.parameters["volume_threshold"])
                distance_factor = min(2.0, abs(float(df['distance_from_top'].iloc[-1])) / self.parameters["breakout_threshold"])
                confidence = min(90.0, 50.0 + (volume_factor + distance_factor) * 10.0)
            elif latest_state == 'bottom_breakout':
                signal_type = SignalType.SELL
                # Higher confidence with larger breakout and higher volume
                volume_factor = min(2.0, float(df['volume_ratio'].iloc[-1]) / self.parameters["volume_threshold"])
                distance_factor = min(2.0, abs(float(df['distance_from_bottom'].iloc[-1])) / self.parameters["breakout_threshold"])
                confidence = min(90.0, 50.0 + (volume_factor + distance_factor) * 10.0)
            else:
                # Inside box - check if close to breakout
                top_distance = float(df['distance_from_top'].iloc[-1])
                bottom_distance = float(df['distance_from_bottom'].iloc[-1])
                
                if abs(top_distance) < abs(bottom_distance):
                    # Closer to top - weak buy signal
                    signal_type = SignalType.BUY
                    confidence = max(50.0, 70.0 - abs(top_distance) * 100.0)
                else:
                    # Closer to bottom - weak sell signal
                    signal_type = SignalType.SELL
                    confidence = max(50.0, 70.0 - abs(bottom_distance) * 100.0)
        
        # Prepare metadata
        metadata = {
            "box_top": float(df['box_top'].iloc[-1]) if not df.empty and not pd.isna(df['box_top'].iloc[-1]) else None,
            "box_bottom": float(df['box_bottom'].iloc[-1]) if not df.empty and not pd.isna(df['box_bottom'].iloc[-1]) else None,
            "box_state": df['box_state'].iloc[-1] if not df.empty else None,
            "volume_ratio": float(df['volume_ratio'].iloc[-1]) if not df.empty and not pd.isna(df['volume_ratio'].iloc[-1]) else None,
            "parameters": {
                "box_period": self.parameters["box_period"],
                "volume_threshold": self.parameters["volume_threshold"],
                "breakout_threshold": self.parameters["breakout_threshold"]
            }
        }
        
        logger.debug(f"Darvas Box strategy generated {signal_type} signal with confidence {confidence:.2f} for {symbol} {timeframe}")
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
        # For now, we just return the current parameters with a simple optimization
        logger.info(f"Optimizing Darvas Box parameters for {symbol} {timeframe}")
        
        # Simple optimization for demonstration
        best_params = self.parameters.copy()
        best_metric = 0.0
        
        # Try a few parameter combinations
        box_periods = [3, 5, 7, 10]
        volume_thresholds = [1.2, 1.5, 2.0]
        breakout_thresholds = [0.005, 0.01, 0.02]
        
        for box_period in box_periods:
            for volume_threshold in volume_thresholds:
                for breakout_threshold in breakout_thresholds:
                    # Set test parameters
                    test_params = self.parameters.copy()
                    test_params["box_period"] = box_period
                    test_params["volume_threshold"] = volume_threshold
                    test_params["breakout_threshold"] = breakout_threshold
                    
                    # Calculate metric (simplified)
                    # In a real implementation, this would involve backtesting
                    metric = self._calculate_test_metric(symbol, timeframe, test_params)
                    
                    # Update best parameters if better
                    if metric > best_metric:
                        best_metric = metric
                        best_params = test_params
        
        logger.info(f"Optimized parameters: box_period={best_params['box_period']}, "
                  f"volume_threshold={best_params['volume_threshold']}, "
                  f"breakout_threshold={best_params['breakout_threshold']}, "
                  f"metric={best_metric:.4f}")
        
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
        
        # Calculate Darvas Boxes with test parameters
        box_period = test_params["box_period"]
        volume_threshold = test_params["volume_threshold"]
        breakout_threshold = test_params["breakout_threshold"]
        
        # Calculate box tops and bottoms
        df['box_top'] = df['high'].rolling(window=box_period).max()
        df['box_bottom'] = df['low'].rolling(window=box_period).min()
        
        # Calculate volume moving average
        df['volume_ma'] = df['volume'].rolling(window=box_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # Calculate breakout signals
        df['top_breakout'] = (
            (df['close'] > df['box_top'] * (1 + breakout_threshold)) & 
            (df['volume_ratio'] > volume_threshold)
        )
        
        df['bottom_breakout'] = (
            (df['close'] < df['box_bottom'] * (1 - breakout_threshold)) & 
            (df['volume_ratio'] > volume_threshold)
        )
        
        # Drop NaN values
        df = df.dropna()
        
        if len(df) < 10:
            return 0.0
        
        # Count breakouts
        buy_signals = df['top_breakout'].sum()
        sell_signals = df['bottom_breakout'].sum()
        total_signals = buy_signals + sell_signals
        
        if total_signals == 0:
            return 0.0
        
        # Calculate a simple metric based on price movement after signals
        # This is very simplified and for demonstration only
        correct_buys = 0
        correct_sells = 0
        
        for i in range(len(df) - 1):
            if df['top_breakout'].iloc[i]:  # Buy signal
                # Check if price increased in the next few periods
                future_periods = min(5, len(df) - i - 1)
                if future_periods > 0:
                    future_return = (df['close'].iloc[i + future_periods] / df['close'].iloc[i]) - 1
                    if future_return > 0:
                        correct_buys += 1
            
            elif df['bottom_breakout'].iloc[i]:  # Sell signal
                # Check if price decreased in the next few periods
                future_periods = min(5, len(df) - i - 1)
                if future_periods > 0:
                    future_return = (df['close'].iloc[i + future_periods] / df['close'].iloc[i]) - 1
                    if future_return < 0:
                        correct_sells += 1
        
        # Calculate win rate
        win_rate = (correct_buys + correct_sells) / max(1, total_signals)
        
        # Prefer strategies with more signals (within reason)
        signal_factor = min(1.0, total_signals / 20)
        
        # Combine metrics
        metric = win_rate * signal_factor
        
        return metric
