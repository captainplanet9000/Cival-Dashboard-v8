from typing import List, Optional
from datetime import datetime, timezone
from loguru import logger
import math # For checking isnan or isinf

from ..models.dashboard_models import TradeLogItem, PortfolioSnapshotOutput # Added PortfolioSnapshotOutput
from ..models.performance_models import PerformanceMetrics
from .trading_data_service import TradingDataService
from .portfolio_snapshot_service import PortfolioSnapshotService # Added
import numpy as np # Added
import math # For checking isnan or isinf

class PerformanceCalculationService:
    def __init__(self, trading_data_service: TradingDataService, portfolio_snapshot_service: PortfolioSnapshotService): # Added portfolio_snapshot_service
        self.trading_data_service = trading_data_service
        self.portfolio_snapshot_service = portfolio_snapshot_service # Store it
        logger.info("PerformanceCalculationService initialized with TradingDataService and PortfolioSnapshotService.")

    async def calculate_performance_metrics(self, agent_id: str) -> PerformanceMetrics:
        logger.info(f"Calculating performance metrics for agent_id: {agent_id}")

        try:
            # Fetch all trades for calculation. Using a large limit.
            # In a real system, this might need pagination or date range filters.
            trade_history = await self.trading_data_service.get_trade_history(agent_id, limit=10000)
        except Exception as e:
            logger.error(f"Error fetching trade history for agent {agent_id}: {e}", exc_info=True)
            return PerformanceMetrics(
                agent_id=agent_id,
                notes=f"Failed to fetch trade history: {str(e)}"
            )

        if not trade_history:
            logger.warning(f"No trade history found for agent {agent_id}. Returning empty metrics.")
            return PerformanceMetrics(
                agent_id=agent_id,
                notes="No trade history available for calculation."
            )

        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        neutral_trades = 0
        total_net_pnl = 0.0
        current_gross_profit = 0.0
        current_gross_loss = 0.0  # Store as positive sum of losses

        min_timestamp: Optional[datetime] = None
        max_timestamp: Optional[datetime] = None

        pnl_data_available = False

        for trade in trade_history:
            total_trades += 1
            if trade.timestamp:
                if min_timestamp is None or trade.timestamp < min_timestamp:
                    min_timestamp = trade.timestamp
                if max_timestamp is None or trade.timestamp > max_timestamp:
                    max_timestamp = trade.timestamp

            if trade.realized_pnl is not None:
                pnl_data_available = True
                if not (math.isnan(trade.realized_pnl) or math.isinf(trade.realized_pnl)):
                    total_net_pnl += trade.realized_pnl
                    if trade.realized_pnl > 1e-9: # Avoid floating point issues around zero
                        winning_trades += 1
                        current_gross_profit += trade.realized_pnl
                    elif trade.realized_pnl < -1e-9: # Avoid floating point issues around zero
                        losing_trades += 1
                        current_gross_loss += abs(trade.realized_pnl)
                    else:
                        neutral_trades += 1
                else:
                    logger.warning(f"Skipping trade {trade.trade_id} due to invalid PnL value: {trade.realized_pnl}")
                    neutral_trades +=1 # Or handle as error / skip count
            else:
                # If PnL is None, count as neutral or skip based on desired logic
                neutral_trades += 1


        win_rate: Optional[float] = None
        loss_rate: Optional[float] = None
        if total_trades > 0:
            # Calculate rates based on trades where PnL was determined (winning or losing)
            determined_trades = winning_trades + losing_trades
            if determined_trades > 0 :
                win_rate = winning_trades / determined_trades if determined_trades > 0 else 0.0
                loss_rate = losing_trades / determined_trades if determined_trades > 0 else 0.0
            else: # All trades were neutral or PnL was None
                 win_rate = 0.0
                 loss_rate = 0.0


        average_win_amount: Optional[float] = None
        if winning_trades > 0:
            average_win_amount = current_gross_profit / winning_trades

        average_loss_amount: Optional[float] = None
        if losing_trades > 0:
            average_loss_amount = current_gross_loss / losing_trades # current_gross_loss is positive

        profit_factor: Optional[float] = None
        if current_gross_loss > 1e-9: # Avoid division by zero
            profit_factor = current_gross_profit / current_gross_loss
        elif current_gross_profit > 1e-9 and current_gross_loss < 1e-9: # Profits but no losses
            profit_factor = float('inf') # Or a large number, or None, depending on convention

        notes_list = []
        if not pnl_data_available:
            notes_list.append("Realized PnL data was missing for all trades; most metrics will be zero or None.")
        if any(trade.realized_pnl is None for trade in trade_history):
             notes_list.append("Some trades were missing realized PnL; these were treated as neutral.")
        # Since TradeLogItem is mocked in TradingDataService, add a note about it.
        # This check is conceptual as the service itself doesn't know if data was mocked by its dependency.
        # This note should ideally be added if TradingDataService indicates mocked data.
        # For now, we assume it might be mocked.
        if "MOCK_COIN" in (trade_history[0].asset if trade_history else "") or \
           "PAPER_COIN" in (trade_history[0].asset if trade_history else ""):
            notes_list.append("Performance calculated using potentially mocked trade history data.")


        return PerformanceMetrics(
            agent_id=agent_id,
            data_start_time=min_timestamp,
            data_end_time=max_timestamp,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            neutral_trades=neutral_trades,
            win_rate=win_rate,
            loss_rate=loss_rate,
            total_net_pnl=total_net_pnl,
            gross_profit=current_gross_profit if pnl_data_available else None,
            gross_loss=current_gross_loss if pnl_data_available else None,
            average_win_amount=average_win_amount,
            average_loss_amount=average_loss_amount,
            profit_factor=profit_factor,
            # max_drawdown_percentage and sharpe_ratio are placeholders
            notes="; ".join(notes_list) if notes_list else None,
            # Initialize new advanced metric fields, to be populated below
            max_drawdown_percentage=None,
            annualized_sharpe_ratio=None,
            compounding_annual_return_percentage=None,
            annualized_volatility_percentage=None
        )

        # --- Advanced Metrics Calculation using Portfolio Snapshots ---
        snapshots: List[PortfolioSnapshotOutput] = []
        try:
            snapshots = await self.portfolio_snapshot_service.get_historical_snapshots(
                agent_id=agent_id,
                sort_ascending=True,
                limit=None # Fetch all available snapshots for comprehensive calculation
            )
        except Exception as e_snap:
            logger.error(f"PCS: Error fetching snapshots for agent {agent_id}: {e_snap}", exc_info=True)
            metrics.notes = (metrics.notes + "; " if metrics.notes else "") + "Snapshot data unavailable for advanced metrics."
            return metrics

        if len(snapshots) < 2:
            logger.info(f"PCS: Less than 2 snapshots for agent {agent_id}. Cannot calculate advanced portfolio metrics.")
            metrics.notes = (metrics.notes + "; " if metrics.notes else "") + "Advanced metrics (Sharpe, MDD, CAGR, Volatility) require at least 2 portfolio snapshots."
        else:
            equity_series = np.array([s.total_equity_usd for s in snapshots])
            timestamps = [s.timestamp for s in snapshots]

            # Periodic Returns (daily if snapshots are daily)
            periodic_returns = (equity_series[1:] / equity_series[:-1]) - 1

            # Max Drawdown
            peak_equity = equity_series[0]
            max_dd_val = 0.0
            for equity_value in equity_series:
                if equity_value > peak_equity:
                    peak_equity = equity_value
                drawdown = (peak_equity - equity_value) / peak_equity if peak_equity > 0 else 0
                if drawdown > max_dd_val:
                    max_dd_val = drawdown
            metrics.max_drawdown_percentage = max_dd_val * 100 if max_dd_val > 0 else 0.0

            # Time Calculation for Annualization
            first_timestamp = timestamps[0]
            last_timestamp = timestamps[-1]
            duration_seconds = (last_timestamp - first_timestamp).total_seconds()
            duration_days = duration_seconds / (24 * 60 * 60)
            duration_years = duration_days / 365.25

            if duration_years < (1/365.25): # Less than a day's worth of data
                logger.warning(f"PCS: Snapshot duration for agent {agent_id} is less than a day ({duration_days:.2f} days). Annualized metrics might be misleading or None.")
                metrics.notes = (metrics.notes + "; " if metrics.notes else "") + "Short snapshot duration; annualized metrics may be misleading."
                # Set annualized metrics to None if duration is too short for meaningful annualization
                metrics.compounding_annual_return_percentage = None
                metrics.annualized_volatility_percentage = None
                metrics.annualized_sharpe_ratio = None
            else:
                # Compounding Annual Return (CAGR)
                if equity_series[0] != 0: # Avoid division by zero
                    total_return_multiple = equity_series[-1] / equity_series[0]
                    if total_return_multiple > 0: # Avoid issues with log or power of negative numbers
                        metrics.compounding_annual_return_percentage = \
                            ((total_return_multiple ** (1 / duration_years)) - 1) * 100
                    else: # Handle negative total_return_multiple if needed (e.g. -100% if equity becomes <=0)
                        metrics.compounding_annual_return_percentage = -100.0 if equity_series[-1] <=0 else None


                # Annualized Volatility
                if len(periodic_returns) >= 2: # Need at least 2 returns to calculate std dev
                    std_dev_periodic = np.std(periodic_returns, ddof=1) # ddof=1 for sample std dev

                    # Estimate periods per year based on average time between snapshots
                    # This is more robust than assuming daily (252)
                    avg_days_between_snapshots = duration_days / len(periodic_returns) if len(periodic_returns) > 0 else 0
                    periods_per_year = 365.25 / avg_days_between_snapshots if avg_days_between_snapshots > 0 else 252 # Fallback to 252
                    if periods_per_year <=0 : periods_per_year = 252 # Ensure positive

                    metrics.annualized_volatility_percentage = std_dev_periodic * np.sqrt(periods_per_year) * 100

                    # Annualized Sharpe Ratio
                    if metrics.annualized_volatility_percentage is not None and metrics.annualized_volatility_percentage > 1e-9: # Avoid division by zero or near-zero volatility
                        if metrics.compounding_annual_return_percentage is not None:
                            risk_free_rate_annual_percentage = 0.0 # Assume 0%
                            excess_return_percentage = metrics.compounding_annual_return_percentage - risk_free_rate_annual_percentage
                            metrics.annualized_sharpe_ratio = excess_return_percentage / metrics.annualized_volatility_percentage
                        # Fallback to simpler Sharpe if CAGR is None but returns are available
                        elif len(periodic_returns) > 0 :
                            mean_periodic_return = np.mean(periodic_returns)
                            # std_dev_periodic is already calculated
                            if std_dev_periodic > 1e-9:
                                sharpe_periodic = mean_periodic_return / std_dev_periodic # Assuming Rf=0 for periodic
                                metrics.annualized_sharpe_ratio = sharpe_periodic * np.sqrt(periods_per_year)
                    elif metrics.compounding_annual_return_percentage is not None and metrics.compounding_annual_return_percentage > 0 and metrics.annualized_volatility_percentage is not None and metrics.annualized_volatility_percentage < 1e-9 :
                        metrics.annualized_sharpe_ratio = float('inf') # Positive return with zero volatility

        return metrics

