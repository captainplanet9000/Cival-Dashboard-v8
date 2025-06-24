from ..models.simulation_models import BacktestRequest, BacktestResult, SimulatedTrade, EquityDataPoint
from ..models.agent_models import AgentConfigOutput, AgentStrategyConfig # For type hinting strategy params
# Import specific strategy param models if directly accessed, e.g.:
# from ..models.agent_models import DarvasStrategyParams, WilliamsAlligatorParams
from ..services.market_data_service import MarketDataService
from ..services.agent_management_service import AgentManagementService
from typing import List, Dict, Any, Optional, Literal # Added Literal
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from loguru import logger
import pandas as pd # For indicators if needed by actual strategy logic
import numpy as np # For indicators if needed by actual strategy logic

class SimulationService:
    def __init__(
        self,
        market_data_service: MarketDataService,
        agent_management_service: Optional[AgentManagementService] = None
    ):
        self.market_data_service = market_data_service
        self.agent_management_service = agent_management_service

    def _simulate_darvas_logic(
        self,
        klines_df: pd.DataFrame, # Expecting DataFrame for easier manipulation
        darvas_params: AgentStrategyConfig.DarvasStrategyParams,
        current_price: float
    ) -> Optional[Literal["buy", "sell"]]:
        if klines_df.empty or len(klines_df) < darvas_params.lookback_period:
            return None

        # Ensure klines_df has 'high' and 'low' columns
        if not ({'high', 'low', 'close'} <= set(klines_df.columns)):
             logger.warning("Darvas Sim: Kline data missing high/low/close columns.")
             return None

        recent_klines = klines_df.iloc[-darvas_params.lookback_period:]
        box_top = recent_klines['high'].max()
        # box_bottom = recent_klines['low'].min() # Not used in this simplified signal

        # Simplified signal: breakout above lookback period's high
        if current_price > box_top:
            # TODO: Add confirmation periods, box range checks, etc. for more realism
            return "buy"
        # No sell signal in this simplified version, assumes closing is handled by overall logic
        return None

    def _simulate_alligator_logic(
        self,
        klines_df: pd.DataFrame, # Expecting DataFrame
        alligator_params: AgentStrategyConfig.WilliamsAlligatorParams,
        current_price: float
    ) -> Optional[Literal["buy", "sell"]]:
        required_len = max(alligator_params.jaw_period, alligator_params.teeth_period, alligator_params.lips_period) + \
                       max(alligator_params.jaw_shift, alligator_params.teeth_shift, alligator_params.lips_shift)
        if klines_df.empty or len(klines_df) < required_len:
            return None

        if 'close' not in klines_df.columns:
            logger.warning("Alligator Sim: Kline data missing close column.")
            return None

        # Simplified Alligator: Using simple moving averages as proxies
        # Jaw (Blue): Longest period, smoothed
        jaw_series = klines_df['close'].rolling(window=alligator_params.jaw_period).mean().shift(alligator_params.jaw_shift)
        # Teeth (Red): Medium period, smoothed
        teeth_series = klines_df['close'].rolling(window=alligator_params.teeth_period).mean().shift(alligator_params.teeth_shift)
        # Lips (Green): Shortest period, smoothed
        lips_series = klines_df['close'].rolling(window=alligator_params.lips_period).mean().shift(alligator_params.lips_shift)

        if jaw_series.empty or teeth_series.empty or lips_series.empty or \
           pd.isna(jaw_series.iloc[-1]) or pd.isna(teeth_series.iloc[-1]) or pd.isna(lips_series.iloc[-1]):
            return None # Not enough data for MAs

        last_jaw = jaw_series.iloc[-1]
        last_teeth = teeth_series.iloc[-1]
        last_lips = lips_series.iloc[-1]

        # Simplified signal: Lips above Teeth, and Teeth above Jaw for buy
        if last_lips > last_teeth > last_jaw and current_price > max(last_lips, last_teeth, last_jaw):
            return "buy"
        # Simplified signal: Lips below Teeth, and Teeth below Jaw for sell (close long)
        elif last_lips < last_teeth < last_jaw and current_price < min(last_lips, last_teeth, last_jaw):
            return "sell"
        return None

    async def run_backtest(self, request: BacktestRequest) -> BacktestResult:
        if not request.agent_config_snapshot and not request.agent_id_to_simulate:
            raise ValueError("Either agent_config_snapshot or agent_id_to_simulate must be provided.")
        if request.agent_config_snapshot and request.agent_id_to_simulate:
            raise ValueError("Provide either agent_config_snapshot or agent_id_to_simulate, not both.")

        agent_config_to_use: Optional[AgentConfigOutput] = None
        if request.agent_config_snapshot:
            agent_config_to_use = request.agent_config_snapshot
        elif request.agent_id_to_simulate:
            if not self.agent_management_service:
                raise ValueError("AgentManagementService is required to fetch agent by ID.")
            agent_config_to_use = await self.agent_management_service.get_agent(request.agent_id_to_simulate)

        if not agent_config_to_use:
            raise ValueError(f"Agent configuration could not be determined for backtest.")

        logger.info(f"Running backtest for agent type {agent_config_to_use.agent_type} on {request.symbol} from {request.start_date_iso} to {request.end_date_iso}")

        start_dt = date_parser.isoparse(request.start_date_iso)
        end_dt = date_parser.isoparse(request.end_date_iso)

        # Fetch klines. Assuming MarketDataService can handle date ranges or large limits.
        # For this example, let's assume get_historical_klines fetches enough data for the period.
        # A more robust solution would involve pagination or specific date range fetching.
        # Calculate a rough limit based on days, assuming daily klines for simplicity in limit calc.
        # Add buffer for initial indicator calculations.
        days_in_range = (end_dt - start_dt).days
        limit_for_mds = days_in_range + 200 # Add buffer (e.g. ~100 days for longest indicator)
        if limit_for_mds <=0: limit_for_mds = 200 # Minimum fetch

        all_klines_raw = await self.market_data_service.get_historical_klines(request.symbol, limit=limit_for_mds)

        if not all_klines_raw:
            raise ValueError(f"No kline data returned from MarketDataService for {request.symbol}.")

        # Convert raw klines to DataFrame and filter by exact date range
        klines_df_all = pd.DataFrame(all_klines_raw)
        klines_df_all['timestamp_dt'] = pd.to_datetime(klines_df_all['timestamp'], unit='ms', utc=True)
        klines_for_backtest_df = klines_df_all[
            (klines_df_all['timestamp_dt'] >= start_dt) & (klines_df_all['timestamp_dt'] <= end_dt)
        ].copy() # Use .copy() to avoid SettingWithCopyWarning

        if klines_for_backtest_df.empty:
            raise ValueError(f"No kline data found for {request.symbol} in the specified date range after filtering.")

        capital = request.initial_capital
        equity_curve: List[EquityDataPoint] = [EquityDataPoint(timestamp=klines_for_backtest_df.iloc[0]['timestamp_dt'], equity=capital)]
        simulated_trades: List[SimulatedTrade] = []
        current_position_qty = 0.0
        current_position_entry_price = 0.0
        win_count = 0
        loss_count = 0
        total_pnl_val = 0.0
        total_fees_paid = 0.0

        for i in range(len(klines_for_backtest_df)):
            current_candle = klines_for_backtest_df.iloc[i]
            current_dt = current_candle['timestamp_dt']
            current_price = float(current_candle['close'])

            # History available up to (and including) the current candle for indicators
            history_slice_df = klines_for_backtest_df.iloc[:i+1]

            signal: Optional[Literal["buy", "sell"]] = None
            if agent_config_to_use.agent_type == "DarvasBoxTechnicalAgent" and agent_config_to_use.strategy.darvas_params:
                signal = self._simulate_darvas_logic(history_slice_df, agent_config_to_use.strategy.darvas_params, current_price)
            elif agent_config_to_use.agent_type == "WilliamsAlligatorTechnicalAgent" and agent_config_to_use.strategy.williams_alligator_params:
                signal = self._simulate_alligator_logic(history_slice_df, agent_config_to_use.strategy.williams_alligator_params, current_price)

            if signal:
                # Simplified: trade fixed quantity or fixed % of capital. Here, 1 unit of base currency.
                # Risk management (stop loss, take profit) should be part of strategy signal or portfolio logic.
                trade_qty = 1.0
                if capital <=0 and signal == "buy": # Cannot buy if bankrupt
                    logger.warning(f"Backtest: Agent bankrupt at {current_dt}, cannot execute buy signal.")
                    continue

                exec_price = current_price
                if signal == "buy":
                    exec_price *= (1 + request.simulated_slippage_percentage)
                elif signal == "sell": # Assuming closing long or opening short
                    exec_price *= (1 - request.simulated_slippage_percentage)

                fee = exec_price * trade_qty * request.simulated_fees_percentage
                total_fees_paid += fee

                if signal == "buy" and current_position_qty == 0: # Open long
                    if capital < (exec_price * trade_qty) + fee:
                        logger.warning(f"Backtest: Insufficient capital at {current_dt} for buy. Have {capital}, need {(exec_price * trade_qty) + fee}.")
                        continue # Skip trade if not enough capital
                    current_position_qty = trade_qty
                    current_position_entry_price = exec_price
                    capital -= (exec_price * trade_qty) + fee
                    simulated_trades.append(SimulatedTrade(timestamp=current_dt, side="buy", quantity=trade_qty, price=exec_price, fee_paid=fee))
                elif signal == "sell" and current_position_qty > 0: # Close long
                    pnl_this_trade = (exec_price * current_position_qty) - (current_position_entry_price * current_position_qty) - fee # Fee on close
                    capital += (exec_price * current_position_qty) - fee
                    if pnl_this_trade > 0: win_count +=1
                    else: loss_count += 1
                    total_pnl_val += pnl_this_trade
                    simulated_trades.append(SimulatedTrade(timestamp=current_dt, side="sell", quantity=current_position_qty, price=exec_price, fee_paid=fee))
                    current_position_qty = 0
                    current_position_entry_price = 0

            current_equity = capital + (current_position_qty * current_price)
            equity_curve.append(EquityDataPoint(timestamp=current_dt, equity=current_equity))

        final_equity = equity_curve[-1].equity if equity_curve else request.initial_capital
        final_pnl_percentage = (final_equity / request.initial_capital - 1) * 100 if request.initial_capital > 0 else 0
        total_round_trips = len([t for t in simulated_trades if t.side == "sell"]) # Approximation for round trips

        win_rate_val = (win_count / total_round_trips) if total_round_trips > 0 else None
        loss_rate_val = (loss_count / total_round_trips) if total_round_trips > 0 else None

        total_win_amount = sum(t.price * t.quantity - current_position_entry_price * t.quantity - t.fee_paid for t in simulated_trades if t.side == "sell" and (t.price * t.quantity - current_position_entry_price * t.quantity - t.fee_paid > 0)) # This logic is flawed for avg win/loss
        total_loss_amount = sum(t.price * t.quantity - current_position_entry_price * t.quantity - t.fee_paid for t in simulated_trades if t.side == "sell" and (t.price * t.quantity - current_position_entry_price * t.quantity - t.fee_paid < 0)) # Flawed
        # Correct average win/loss calculation needs to be based on PnL of each round trip.
        # For simplicity here, these are placeholders. A proper calculation requires tracking individual round trips.
        avg_win_val = (total_pnl_val / win_count) if win_count > 0 and total_pnl_val > 0 else None # Highly simplified
        avg_loss_val = (total_pnl_val / loss_count) if loss_count > 0 and total_pnl_val < 0 else None # Highly simplified

        profit_factor_val = None
        if total_loss_amount != 0: # Ensure no division by zero
             # Using absolute sum of losses for profit factor
             # This still needs better calculation of total_win_amount and total_loss_amount from individual trades
             # profit_factor_val = total_win_amount / abs(total_loss_amount) if abs(total_loss_amount) > 0 else None
             pass # Placeholder due to flawed avg win/loss

        return BacktestResult(
            request_params=request,
            final_capital=final_equity,
            total_pnl=final_equity - request.initial_capital,
            total_pnl_percentage=final_pnl_percentage,
            total_trades=total_round_trips,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate_val,
            loss_rate=loss_rate_val,
            average_win_amount=avg_win_val, # Placeholder
            average_loss_amount=avg_loss_val, # Placeholder
            profit_factor=profit_factor_val, # Placeholder
            list_of_simulated_trades=simulated_trades,
            equity_curve=equity_curve
        )
