"""
Phase 10: Advanced Backtesting and Strategy Validation Service
Comprehensive backtesting engine with Monte Carlo simulation and walk-forward analysis
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import logging
import numpy as np
import pandas as pd
from collections import defaultdict
from contextlib import asynccontextmanager
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

from pydantic import BaseModel, Field
from fastapi import HTTPException

from models.trading_strategy_models import (
    TradingStrategy, StrategyBacktestRequest, StrategyPerformance, TradingSignal,
    TradingPosition, MarketData, PositionSide
)
from services.market_analysis_service import get_market_analysis_service
from services.risk_management_service import get_risk_management_service
from database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


class BacktestResult(BaseModel):
    """Comprehensive backtest result"""
    backtest_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_capital: Decimal
    
    # Performance metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    average_trade: float
    
    # Monthly performance
    monthly_returns: List[float] = Field(default_factory=list)
    
    # Detailed trades
    trades: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Equity curve
    equity_curve: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Drawdown analysis
    drawdown_periods: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Risk metrics
    var_95: float = 0.0
    expected_shortfall: float = 0.0
    
    # Benchmark comparison
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    
    # Execution details
    execution_time: float = 0.0
    commission_paid: Decimal = Decimal("0")
    slippage_cost: Decimal = Decimal("0")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MonteCarloResult(BaseModel):
    """Monte Carlo simulation result"""
    simulation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    num_simulations: int
    confidence_level: float
    
    # Return distribution
    mean_return: float
    std_return: float
    min_return: float
    max_return: float
    percentiles: Dict[str, float] = Field(default_factory=dict)
    
    # Risk metrics
    probability_of_loss: float
    var_confidence: float
    expected_shortfall: float
    
    # Drawdown analysis
    worst_drawdown: float
    avg_drawdown: float
    max_drawdown_duration: int
    
    # Success probabilities
    prob_positive_return: float
    prob_beat_benchmark: float
    prob_target_return: Optional[float] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WalkForwardResult(BaseModel):
    """Walk-forward analysis result"""
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    window_size: int  # months
    step_size: int    # months
    
    # Overall metrics
    out_of_sample_return: float
    in_sample_return: float
    degradation_factor: float  # out-of-sample / in-sample
    
    # Period results
    periods: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Stability metrics
    return_consistency: float
    parameter_stability: float
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BacktestEngine:
    """Core backtesting engine"""
    
    def __init__(self):
        self.commission_rate = 0.001  # 0.1%
        self.slippage_rate = 0.0005   # 0.05%
        
    def run_backtest(
        self,
        strategy: TradingStrategy,
        market_data: List[MarketData],
        request: StrategyBacktestRequest
    ) -> BacktestResult:
        """Run comprehensive backtest"""
        start_time = datetime.now()
        
        # Initialize portfolio
        capital = request.initial_capital
        positions = {}
        trade_history = []
        equity_curve = []
        commission_paid = Decimal("0")
        slippage_cost = Decimal("0")
        
        # Process each data point
        for i, data_point in enumerate(market_data):
            if i < request.warmup_period:
                continue
            
            # Get historical data for signal generation
            historical_data = market_data[max(0, i-100):i+1]
            
            # Generate trading signal
            signal = self._generate_signal_for_backtest(strategy, historical_data, data_point.symbol)
            
            # Execute trades based on signal
            if signal:
                trade_result = self._execute_backtest_trade(
                    signal, data_point, capital, positions, request
                )
                
                if trade_result:
                    trade_history.append(trade_result)
                    capital = trade_result["new_capital"]
                    commission_paid += Decimal(str(trade_result.get("commission", 0)))
                    slippage_cost += Decimal(str(trade_result.get("slippage", 0)))
            
            # Update positions with current prices
            self._update_positions_value(positions, data_point)
            
            # Calculate current portfolio value
            portfolio_value = capital + sum(
                pos["quantity"] * data_point.close for pos in positions.values()
            )
            
            # Record equity point
            equity_curve.append({
                "timestamp": data_point.timestamp.isoformat(),
                "portfolio_value": float(portfolio_value),
                "capital": float(capital),
                "unrealized_pnl": float(portfolio_value - request.initial_capital)
            })
        
        # Calculate final metrics
        final_capital = capital + sum(
            pos["quantity"] * market_data[-1].close for pos in positions.values()
        )
        
        performance_metrics = self._calculate_performance_metrics(
            equity_curve, trade_history, request.initial_capital, final_capital
        )
        
        # Create result
        result = BacktestResult(
            strategy_id=strategy.strategy_id,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            final_capital=final_capital,
            trades=trade_history,
            equity_curve=equity_curve,
            commission_paid=commission_paid,
            slippage_cost=slippage_cost,
            execution_time=(datetime.now() - start_time).total_seconds(),
            **performance_metrics
        )
        
        return result
    
    def _generate_signal_for_backtest(
        self,
        strategy: TradingStrategy,
        historical_data: List[MarketData],
        symbol: str
    ) -> Optional[TradingSignal]:
        """Generate trading signal for backtesting"""
        # Simplified signal generation for backtesting
        if len(historical_data) < 20:
            return None
        
        closes = [float(data.close) for data in historical_data]
        
        # Simple momentum strategy for demonstration
        if strategy.strategy_type.value == "momentum":
            short_ma = np.mean(closes[-5:])
            long_ma = np.mean(closes[-20:])
            
            if short_ma > long_ma * 1.01:  # 1% threshold
                return TradingSignal(
                    strategy_id=strategy.strategy_id,
                    agent_id="backtest_engine",
                    symbol=symbol,
                    signal_type="buy",
                    strength="moderate",
                    confidence=0.7,
                    entry_price=Decimal(str(closes[-1])),
                    position_side=PositionSide.LONG,
                    timeframe="1h",
                    market_condition="bullish"
                )
            elif short_ma < long_ma * 0.99:  # 1% threshold
                return TradingSignal(
                    strategy_id=strategy.strategy_id,
                    agent_id="backtest_engine",
                    symbol=symbol,
                    signal_type="sell",
                    strength="moderate",
                    confidence=0.7,
                    entry_price=Decimal(str(closes[-1])),
                    position_side=PositionSide.SHORT,
                    timeframe="1h",
                    market_condition="bearish"
                )
        
        return None
    
    def _execute_backtest_trade(
        self,
        signal: TradingSignal,
        data_point: MarketData,
        capital: Decimal,
        positions: Dict[str, Any],
        request: StrategyBacktestRequest
    ) -> Optional[Dict[str, Any]]:
        """Execute trade in backtest"""
        # Calculate position size (simplified)
        position_size = min(capital * Decimal("0.1"), Decimal("1000"))  # 10% or $1000 max
        
        if position_size < Decimal("10"):  # Minimum trade size
            return None
        
        # Calculate costs
        commission = position_size * Decimal(str(request.commission))
        slippage = position_size * Decimal(str(request.slippage))
        total_cost = commission + slippage
        
        # Execute trade
        if signal.signal_type == "buy":
            if capital >= position_size + total_cost:
                # Open long position
                new_capital = capital - position_size - total_cost
                
                position_id = str(uuid.uuid4())
                positions[position_id] = {
                    "symbol": signal.symbol,
                    "side": "long",
                    "quantity": position_size / data_point.close,
                    "entry_price": data_point.close,
                    "entry_time": data_point.timestamp,
                    "signal_id": signal.signal_id
                }
                
                return {
                    "trade_id": position_id,
                    "action": "buy",
                    "quantity": float(position_size / data_point.close),
                    "price": float(data_point.close),
                    "timestamp": data_point.timestamp.isoformat(),
                    "commission": float(commission),
                    "slippage": float(slippage),
                    "new_capital": new_capital
                }
        
        elif signal.signal_type == "sell":
            # Close existing long positions or open short
            long_positions = [
                pos_id for pos_id, pos in positions.items()
                if pos["symbol"] == signal.symbol and pos["side"] == "long"
            ]
            
            if long_positions:
                # Close long position
                pos_id = long_positions[0]
                position = positions[pos_id]
                
                exit_value = position["quantity"] * data_point.close
                pnl = exit_value - (position["quantity"] * position["entry_price"])
                new_capital = capital + exit_value - total_cost
                
                del positions[pos_id]
                
                return {
                    "trade_id": pos_id,
                    "action": "sell",
                    "quantity": float(position["quantity"]),
                    "price": float(data_point.close),
                    "timestamp": data_point.timestamp.isoformat(),
                    "pnl": float(pnl),
                    "commission": float(commission),
                    "slippage": float(slippage),
                    "new_capital": new_capital
                }
        
        return None
    
    def _update_positions_value(self, positions: Dict[str, Any], data_point: MarketData):
        """Update position values with current market data"""
        for position in positions.values():
            if position["symbol"] == data_point.symbol:
                position["current_price"] = data_point.close
                position["unrealized_pnl"] = (
                    position["quantity"] * (data_point.close - position["entry_price"])
                )
    
    def _calculate_performance_metrics(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[Dict[str, Any]],
        initial_capital: Decimal,
        final_capital: Decimal
    ) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        if not equity_curve:
            return {}
        
        # Extract returns
        portfolio_values = [point["portfolio_value"] for point in equity_curve]
        returns = []
        for i in range(1, len(portfolio_values)):
            returns.append((portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1])
        
        # Basic metrics
        total_return = float((final_capital - initial_capital) / initial_capital)
        
        # Risk metrics
        if returns:
            volatility = np.std(returns) * np.sqrt(252)  # Annualized
            sharpe_ratio = (np.mean(returns) * 252) / volatility if volatility > 0 else 0
            
            # Downside deviation for Sortino ratio
            negative_returns = [r for r in returns if r < 0]
            downside_deviation = np.std(negative_returns) * np.sqrt(252) if negative_returns else 0
            sortino_ratio = (np.mean(returns) * 252) / downside_deviation if downside_deviation > 0 else 0
        else:
            volatility = 0
            sharpe_ratio = 0
            sortino_ratio = 0
        
        # Drawdown analysis
        running_max = np.maximum.accumulate(portfolio_values)
        drawdowns = (np.array(portfolio_values) - running_max) / running_max
        max_drawdown = abs(np.min(drawdowns))
        
        # Trade statistics
        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]
        
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        avg_win = np.mean([t["pnl"] for t in winning_trades]) if winning_trades else 0
        avg_loss = abs(np.mean([t["pnl"] for t in losing_trades])) if losing_trades else 0
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        
        return {
            "total_return": total_return,
            "annualized_return": total_return * 252 / len(equity_curve) if equity_curve else 0,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": total_return / max_drawdown if max_drawdown > 0 else 0,
            "max_drawdown": max_drawdown,
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "average_trade": np.mean([t.get("pnl", 0) for t in trades]) if trades else 0
        }


class MonteCarloSimulator:
    """Monte Carlo simulation engine"""
    
    def run_simulation(
        self,
        strategy: TradingStrategy,
        historical_results: List[BacktestResult],
        num_simulations: int = 1000,
        time_horizon_days: int = 252
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation"""
        if not historical_results:
            raise ValueError("No historical results provided for simulation")
        
        # Extract historical returns
        all_returns = []
        for result in historical_results:
            if result.equity_curve:
                values = [point["portfolio_value"] for point in result.equity_curve]
                returns = []
                for i in range(1, len(values)):
                    returns.append((values[i] - values[i-1]) / values[i-1])
                all_returns.extend(returns)
        
        if not all_returns:
            raise ValueError("No returns data available for simulation")
        
        # Calculate distribution parameters
        mean_return = np.mean(all_returns)
        std_return = np.std(all_returns)
        
        # Run simulations
        simulation_results = []
        
        for _ in range(num_simulations):
            # Generate random returns
            random_returns = np.random.normal(mean_return, std_return, time_horizon_days)
            
            # Calculate cumulative return
            cumulative_return = np.prod(1 + random_returns) - 1
            simulation_results.append(cumulative_return)
        
        # Calculate statistics
        simulation_results = np.array(simulation_results)
        
        percentiles = {
            "5th": np.percentile(simulation_results, 5),
            "25th": np.percentile(simulation_results, 25),
            "50th": np.percentile(simulation_results, 50),
            "75th": np.percentile(simulation_results, 75),
            "95th": np.percentile(simulation_results, 95)
        }
        
        return MonteCarloResult(
            strategy_id=strategy.strategy_id,
            num_simulations=num_simulations,
            confidence_level=0.95,
            mean_return=float(np.mean(simulation_results)),
            std_return=float(np.std(simulation_results)),
            min_return=float(np.min(simulation_results)),
            max_return=float(np.max(simulation_results)),
            percentiles=percentiles,
            probability_of_loss=float(np.sum(simulation_results < 0) / num_simulations),
            var_confidence=float(np.percentile(simulation_results, 5)),
            expected_shortfall=float(np.mean(simulation_results[simulation_results <= np.percentile(simulation_results, 5)])),
            prob_positive_return=float(np.sum(simulation_results > 0) / num_simulations)
        )


class WalkForwardAnalyzer:
    """Walk-forward analysis engine"""
    
    def run_analysis(
        self,
        strategy: TradingStrategy,
        market_data: List[MarketData],
        window_size: int = 12,  # months
        step_size: int = 3      # months
    ) -> WalkForwardResult:
        """Run walk-forward analysis"""
        periods = []
        
        # Convert to monthly data for analysis
        df = pd.DataFrame([{
            "timestamp": data.timestamp,
            "close": float(data.close),
            "volume": float(data.volume)
        } for data in market_data])
        
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        
        # Resample to monthly
        monthly_data = df.resample("M").last()
        
        start_idx = 0
        while start_idx + window_size < len(monthly_data):
            # In-sample period
            in_sample_end = start_idx + window_size
            in_sample_data = monthly_data.iloc[start_idx:in_sample_end]
            
            # Out-of-sample period
            out_sample_start = in_sample_end
            out_sample_end = min(out_sample_start + step_size, len(monthly_data))
            out_sample_data = monthly_data.iloc[out_sample_start:out_sample_end]
            
            if len(out_sample_data) == 0:
                break
            
            # Calculate returns
            in_sample_return = (in_sample_data["close"].iloc[-1] - in_sample_data["close"].iloc[0]) / in_sample_data["close"].iloc[0]
            out_sample_return = (out_sample_data["close"].iloc[-1] - out_sample_data["close"].iloc[0]) / out_sample_data["close"].iloc[0]
            
            periods.append({
                "period": len(periods) + 1,
                "in_sample_start": in_sample_data.index[0].isoformat(),
                "in_sample_end": in_sample_data.index[-1].isoformat(),
                "out_sample_start": out_sample_data.index[0].isoformat(),
                "out_sample_end": out_sample_data.index[-1].isoformat(),
                "in_sample_return": float(in_sample_return),
                "out_sample_return": float(out_sample_return),
                "degradation": float(out_sample_return / in_sample_return) if in_sample_return != 0 else 0
            })
            
            start_idx += step_size
        
        # Calculate overall metrics
        if periods:
            avg_in_sample = np.mean([p["in_sample_return"] for p in periods])
            avg_out_sample = np.mean([p["out_sample_return"] for p in periods])
            degradation_factor = avg_out_sample / avg_in_sample if avg_in_sample != 0 else 0
            
            # Calculate consistency
            out_sample_returns = [p["out_sample_return"] for p in periods]
            return_consistency = 1 - (np.std(out_sample_returns) / np.mean(out_sample_returns)) if np.mean(out_sample_returns) != 0 else 0
        else:
            avg_in_sample = 0
            avg_out_sample = 0
            degradation_factor = 0
            return_consistency = 0
        
        return WalkForwardResult(
            strategy_id=strategy.strategy_id,
            window_size=window_size,
            step_size=step_size,
            out_of_sample_return=float(avg_out_sample),
            in_sample_return=float(avg_in_sample),
            degradation_factor=float(degradation_factor),
            periods=periods,
            return_consistency=float(max(0, return_consistency)),
            parameter_stability=0.8  # Placeholder
        )


class BacktestingService:
    """
    Advanced backtesting and strategy validation service
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        
        # Engines
        self.backtest_engine = BacktestEngine()
        self.monte_carlo_simulator = MonteCarloSimulator()
        self.walk_forward_analyzer = WalkForwardAnalyzer()
        
        # Results storage
        self.backtest_results: Dict[str, BacktestResult] = {}
        self.monte_carlo_results: Dict[str, MonteCarloResult] = {}
        self.walk_forward_results: Dict[str, WalkForwardResult] = {}
        
        # Performance cache
        self.strategy_performance_cache: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.max_concurrent_backtests = 4
        self.result_retention_days = 90
        self._shutdown = False
        
    async def initialize(self):
        """Initialize the backtesting service"""
        try:
            logger.info("Initializing Backtesting Service...")
            
            # Load existing results
            await self._load_existing_results()
            
            # Start background tasks
            asyncio.create_task(self._result_cleanup_loop())
            
            logger.info("Backtesting Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Backtesting Service: {e}")
            raise
    
    async def run_strategy_backtest(self, request: StrategyBacktestRequest) -> BacktestResult:
        """Run comprehensive strategy backtest"""
        try:
            logger.info(f"Running backtest for strategy {request.strategy_id}")
            
            # Get strategy
            strategy = await self._get_strategy_by_id(request.strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            # Get market data
            market_data = await self._get_market_data_for_backtest(request)
            
            if len(market_data) < 100:
                raise HTTPException(status_code=400, detail="Insufficient market data for backtesting")
            
            # Run backtest
            result = await self._run_backtest_async(strategy, market_data, request)
            
            # Store result
            self.backtest_results[result.backtest_id] = result
            
            # Save to database
            await self._save_backtest_result(result)
            
            # Update strategy performance cache
            await self._update_strategy_performance_cache(strategy.strategy_id, result)
            
            logger.info(f"Backtest completed for strategy {request.strategy_id}: {result.total_return:.2%} return")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to run backtest for strategy {request.strategy_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")
    
    async def run_monte_carlo_simulation(
        self,
        strategy_id: str,
        num_simulations: int = 1000,
        time_horizon_days: int = 252
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation for strategy"""
        try:
            logger.info(f"Running Monte Carlo simulation for strategy {strategy_id}")
            
            # Get strategy
            strategy = await self._get_strategy_by_id(strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            # Get historical backtest results
            historical_results = [
                result for result in self.backtest_results.values()
                if result.strategy_id == strategy_id
            ]
            
            if not historical_results:
                raise HTTPException(status_code=400, detail="No historical backtest results available")
            
            # Run simulation
            result = await self._run_monte_carlo_async(
                strategy, historical_results, num_simulations, time_horizon_days
            )
            
            # Store result
            self.monte_carlo_results[result.simulation_id] = result
            
            # Save to database
            await self._save_monte_carlo_result(result)
            
            logger.info(f"Monte Carlo simulation completed for strategy {strategy_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to run Monte Carlo simulation for strategy {strategy_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Monte Carlo simulation failed: {str(e)}")
    
    async def run_walk_forward_analysis(
        self,
        strategy_id: str,
        start_date: datetime,
        end_date: datetime,
        window_size: int = 12,
        step_size: int = 3
    ) -> WalkForwardResult:
        """Run walk-forward analysis for strategy"""
        try:
            logger.info(f"Running walk-forward analysis for strategy {strategy_id}")
            
            # Get strategy
            strategy = await self._get_strategy_by_id(strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            # Get market data
            market_data = await self._get_market_data_for_period(start_date, end_date)
            
            if len(market_data) < window_size * 30:  # Minimum data requirement
                raise HTTPException(status_code=400, detail="Insufficient market data for walk-forward analysis")
            
            # Run analysis
            result = await self._run_walk_forward_async(strategy, market_data, window_size, step_size)
            
            # Store result
            self.walk_forward_results[result.analysis_id] = result
            
            # Save to database
            await self._save_walk_forward_result(result)
            
            logger.info(f"Walk-forward analysis completed for strategy {strategy_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to run walk-forward analysis for strategy {strategy_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Walk-forward analysis failed: {str(e)}")
    
    async def get_strategy_validation_report(self, strategy_id: str) -> Dict[str, Any]:
        """Get comprehensive strategy validation report"""
        try:
            # Get all results for strategy
            backtest_results = [r for r in self.backtest_results.values() if r.strategy_id == strategy_id]
            monte_carlo_results = [r for r in self.monte_carlo_results.values() if r.strategy_id == strategy_id]
            walk_forward_results = [r for r in self.walk_forward_results.values() if r.strategy_id == strategy_id]
            
            # Calculate aggregate metrics
            if backtest_results:
                avg_return = np.mean([r.total_return for r in backtest_results])
                avg_sharpe = np.mean([r.sharpe_ratio for r in backtest_results])
                avg_max_dd = np.mean([r.max_drawdown for r in backtest_results])
                avg_win_rate = np.mean([r.win_rate for r in backtest_results])
            else:
                avg_return = avg_sharpe = avg_max_dd = avg_win_rate = 0
            
            # Risk assessment
            risk_score = self._calculate_strategy_risk_score(backtest_results, monte_carlo_results)
            
            # Robustness assessment
            robustness_score = self._calculate_robustness_score(walk_forward_results, backtest_results)
            
            # Overall rating
            overall_rating = self._calculate_overall_rating(
                avg_return, avg_sharpe, avg_max_dd, risk_score, robustness_score
            )
            
            return {
                "strategy_id": strategy_id,
                "validation_date": datetime.now(timezone.utc).isoformat(),
                "backtest_summary": {
                    "num_backtests": len(backtest_results),
                    "avg_return": avg_return,
                    "avg_sharpe_ratio": avg_sharpe,
                    "avg_max_drawdown": avg_max_dd,
                    "avg_win_rate": avg_win_rate
                },
                "monte_carlo_summary": {
                    "num_simulations": len(monte_carlo_results),
                    "avg_probability_of_loss": np.mean([r.probability_of_loss for r in monte_carlo_results]) if monte_carlo_results else 0
                },
                "walk_forward_summary": {
                    "num_analyses": len(walk_forward_results),
                    "avg_degradation_factor": np.mean([r.degradation_factor for r in walk_forward_results]) if walk_forward_results else 0
                },
                "risk_assessment": {
                    "risk_score": risk_score,
                    "risk_level": self._get_risk_level(risk_score)
                },
                "robustness_assessment": {
                    "robustness_score": robustness_score,
                    "robustness_level": self._get_robustness_level(robustness_score)
                },
                "overall_rating": {
                    "score": overall_rating,
                    "rating": self._get_overall_rating_label(overall_rating),
                    "recommendation": self._get_strategy_recommendation(overall_rating, risk_score)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate validation report for strategy {strategy_id}: {e}")
            return {"error": str(e)}
    
    # Async execution methods
    
    async def _run_backtest_async(
        self,
        strategy: TradingStrategy,
        market_data: List[MarketData],
        request: StrategyBacktestRequest
    ) -> BacktestResult:
        """Run backtest asynchronously"""
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = loop.run_in_executor(
                executor, self.backtest_engine.run_backtest, strategy, market_data, request
            )
            return await future
    
    async def _run_monte_carlo_async(
        self,
        strategy: TradingStrategy,
        historical_results: List[BacktestResult],
        num_simulations: int,
        time_horizon_days: int
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation asynchronously"""
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = loop.run_in_executor(
                executor, 
                self.monte_carlo_simulator.run_simulation,
                strategy, historical_results, num_simulations, time_horizon_days
            )
            return await future
    
    async def _run_walk_forward_async(
        self,
        strategy: TradingStrategy,
        market_data: List[MarketData],
        window_size: int,
        step_size: int
    ) -> WalkForwardResult:
        """Run walk-forward analysis asynchronously"""
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = loop.run_in_executor(
                executor,
                self.walk_forward_analyzer.run_analysis,
                strategy, market_data, window_size, step_size
            )
            return await future
    
    # Helper methods
    
    def _calculate_strategy_risk_score(
        self,
        backtest_results: List[BacktestResult],
        monte_carlo_results: List[MonteCarloResult]
    ) -> float:
        """Calculate strategy risk score (0-1, lower is better)"""
        if not backtest_results:
            return 1.0
        
        # Factors: max drawdown, volatility, probability of loss
        avg_max_dd = np.mean([r.max_drawdown for r in backtest_results])
        avg_volatility = np.mean([r.volatility for r in backtest_results])
        
        if monte_carlo_results:
            avg_prob_loss = np.mean([r.probability_of_loss for r in monte_carlo_results])
        else:
            avg_prob_loss = 0.5  # Default
        
        # Normalize and combine (0-1 scale)
        dd_score = min(1.0, avg_max_dd / 0.5)  # 50% max drawdown = max risk
        vol_score = min(1.0, avg_volatility / 1.0)  # 100% volatility = max risk
        prob_loss_score = avg_prob_loss
        
        return (dd_score + vol_score + prob_loss_score) / 3
    
    def _calculate_robustness_score(
        self,
        walk_forward_results: List[WalkForwardResult],
        backtest_results: List[BacktestResult]
    ) -> float:
        """Calculate strategy robustness score (0-1, higher is better)"""
        if not walk_forward_results or not backtest_results:
            return 0.5
        
        # Factors: degradation factor, return consistency, number of periods
        avg_degradation = np.mean([r.degradation_factor for r in walk_forward_results])
        avg_consistency = np.mean([r.return_consistency for r in walk_forward_results])
        
        # Degradation factor: 1.0 = perfect, <1.0 = degradation
        degradation_score = min(1.0, max(0.0, avg_degradation))
        
        # Consistency score is already 0-1
        consistency_score = avg_consistency
        
        # Number of backtests (more = better)
        num_backtests_score = min(1.0, len(backtest_results) / 10)  # 10+ backtests = max score
        
        return (degradation_score + consistency_score + num_backtests_score) / 3
    
    def _calculate_overall_rating(
        self,
        avg_return: float,
        avg_sharpe: float,
        avg_max_dd: float,
        risk_score: float,
        robustness_score: float
    ) -> float:
        """Calculate overall strategy rating (0-1, higher is better)"""
        # Performance score
        return_score = min(1.0, max(0.0, (avg_return + 1) / 2))  # -100% to +100% mapped to 0-1
        sharpe_score = min(1.0, max(0.0, avg_sharpe / 3))  # 3.0 Sharpe = max score
        dd_score = 1.0 - min(1.0, avg_max_dd / 0.5)  # Lower drawdown = higher score
        
        performance_score = (return_score + sharpe_score + dd_score) / 3
        
        # Combine all factors
        overall_score = (
            performance_score * 0.4 +
            (1 - risk_score) * 0.3 +  # Invert risk score
            robustness_score * 0.3
        )
        
        return max(0.0, min(1.0, overall_score))
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score < 0.2:
            return "Very Low"
        elif risk_score < 0.4:
            return "Low"
        elif risk_score < 0.6:
            return "Medium"
        elif risk_score < 0.8:
            return "High"
        else:
            return "Very High"
    
    def _get_robustness_level(self, robustness_score: float) -> str:
        """Convert robustness score to robustness level"""
        if robustness_score > 0.8:
            return "Very Robust"
        elif robustness_score > 0.6:
            return "Robust"
        elif robustness_score > 0.4:
            return "Moderate"
        elif robustness_score > 0.2:
            return "Weak"
        else:
            return "Very Weak"
    
    def _get_overall_rating_label(self, overall_rating: float) -> str:
        """Convert overall rating to label"""
        if overall_rating > 0.8:
            return "Excellent"
        elif overall_rating > 0.6:
            return "Good"
        elif overall_rating > 0.4:
            return "Fair"
        elif overall_rating > 0.2:
            return "Poor"
        else:
            return "Very Poor"
    
    def _get_strategy_recommendation(self, overall_rating: float, risk_score: float) -> str:
        """Get strategy recommendation"""
        if overall_rating > 0.7 and risk_score < 0.4:
            return "Recommended for live trading"
        elif overall_rating > 0.5 and risk_score < 0.6:
            return "Consider for live trading with risk controls"
        elif overall_rating > 0.3:
            return "Requires optimization before live trading"
        else:
            return "Not recommended for live trading"
    
    # Background tasks
    
    async def _result_cleanup_loop(self):
        """Clean up old backtest results"""
        while not self._shutdown:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.result_retention_days)
                
                # Remove old results
                old_backtest_ids = [
                    result_id for result_id, result in self.backtest_results.items()
                    if result.created_at < cutoff_date
                ]
                
                for result_id in old_backtest_ids:
                    del self.backtest_results[result_id]
                
                logger.info(f"Cleaned up {len(old_backtest_ids)} old backtest results")
                
                await asyncio.sleep(86400)  # Daily cleanup
                
            except Exception as e:
                logger.error(f"Error in result cleanup loop: {e}")
                await asyncio.sleep(86400)
    
    # Additional helper methods would be implemented here...
    
    async def _get_strategy_by_id(self, strategy_id: str):
        """Get strategy from database"""
        # Implementation would load from Supabase
        return None
    
    async def _get_market_data_for_backtest(self, request: StrategyBacktestRequest) -> List[MarketData]:
        """Get market data for backtesting"""
        # Implementation would fetch from market data provider
        return []
    
    # Additional methods continue here...


# Global service instance
_backtesting_service: Optional[BacktestingService] = None


async def get_backtesting_service() -> BacktestingService:
    """Get the global backtesting service instance"""
    global _backtesting_service
    
    if _backtesting_service is None:
        _backtesting_service = BacktestingService()
        await _backtesting_service.initialize()
    
    return _backtesting_service


@asynccontextmanager
async def backtesting_context():
    """Context manager for backtesting service"""
    service = await get_backtesting_service()
    try:
        yield service
    finally:
        # Service continues running, no cleanup needed here
        pass