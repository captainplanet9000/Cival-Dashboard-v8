# This file makes the 'strategies' directory a Python package.
# It contains implementations of various trading strategies.

from .darvas_box import get_darvas_signals, run_darvas_backtest
from .williams_alligator import get_williams_alligator_signals, run_williams_alligator_backtest
from .elliott_wave import get_elliott_wave_signals, run_elliott_wave_backtest
from .heikin_ashi import get_heikin_ashi_signals, run_heikin_ashi_backtest, calculate_heikin_ashi_candles
from .renko import get_renko_signals, run_renko_backtest, calculate_renko_bricks

# SMA Crossover strategy might be missing in this merge, will be handled separately
try:
    from .sma_crossover import get_sma_crossover_signals, run_sma_crossover_backtest
    has_sma_crossover = True
except ImportError:
    has_sma_crossover = False

__all__ = [
    "get_darvas_signals",
    "run_darvas_backtest",
    "get_williams_alligator_signals",
    "run_williams_alligator_backtest",
    "get_elliott_wave_signals",
    "run_elliott_wave_backtest",
    "get_heikin_ashi_signals",
    "run_heikin_ashi_backtest",
    "calculate_heikin_ashi_candles",
    "get_renko_signals",
    "run_renko_backtest",
    "calculate_renko_bricks",
]

# Add SMA crossover functions to __all__ if available
if has_sma_crossover:
    __all__.extend([
        "get_sma_crossover_signals",
        "run_sma_crossover_backtest",
    ])
