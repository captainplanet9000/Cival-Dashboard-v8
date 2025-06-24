from ..models.agent_models import AgentConfigOutput, AgentRiskConfig
from ..models.event_bus_models import TradeSignalEventPayload, RiskAssessmentResponseData
from ..models.dashboard_models import PortfolioSummary, AssetPositionSummary
from ..services.agent_management_service import AgentManagementService
from ..services.trading_data_service import TradingDataService
from typing import Optional, List
from loguru import logger

class RiskManagerService:
    def __init__(self, agent_service: AgentManagementService, trading_data_service: TradingDataService):
        self.agent_service = agent_service
        self.trading_data_service = trading_data_service
        logger.info("RiskManagerService initialized with TradingDataService.")

    async def assess_trade_risk(
        self,
        agent_id_of_proposer: str,
        trade_signal: TradeSignalEventPayload
    ) -> RiskAssessmentResponseData:
        logger.info(f"RiskManager: Assessing trade risk for agent {agent_id_of_proposer}, signal: {trade_signal.symbol} {trade_signal.action} Qty:{trade_signal.quantity} @ Prc:{trade_signal.price_target}, SL:{trade_signal.stop_loss}")

        agent_config = await self.agent_service.get_agent(agent_id_of_proposer)
        if not agent_config:
            logger.warning(f"RiskManager: Agent config for {agent_id_of_proposer} not found.")
            return RiskAssessmentResponseData(signal_approved=False, rejection_reason=f"Agent config for {agent_id_of_proposer} not found.")

        risk_params: AgentRiskConfig = agent_config.risk_config
        op_params: dict = agent_config.operational_parameters

        # Fetch portfolio summary for balance-dependent checks and open positions
        portfolio_summary: Optional[PortfolioSummary] = None
        account_balance_usd: Optional[float] = None
        open_positions_list: List[AssetPositionSummary] = []
        num_open_positions: int = 0

        # Determine if portfolio data is strictly needed by any configured rule
        needs_portfolio_data_for_rule = bool(
            (risk_params.max_loss_per_trade_percentage_balance and trade_signal.stop_loss is not None) or # SL is needed for this check
            risk_params.max_concurrent_open_trades is not None or
            risk_params.max_exposure_per_asset_usd is not None
        )

        can_skip_value_based_risk = trade_signal.quantity is None or trade_signal.price_target is None

        if needs_portfolio_data_for_rule or (risk_params.max_capital_allocation_usd > 0 and not can_skip_value_based_risk) : # Also fetch if max_capital_allocation check will run
            portfolio_summary = await self.trading_data_service.get_portfolio_summary(agent_id_of_proposer)
            if portfolio_summary:
                account_balance_usd = portfolio_summary.account_value_usd
                open_positions_list = portfolio_summary.open_positions
                num_open_positions = len(open_positions_list)
            else:
                # If portfolio data is unavailable and any rule *requires* it, reject.
                rejection_msg_portfolio = f"Portfolio data for agent {agent_id_of_proposer} unavailable for required risk checks."
                if risk_params.max_loss_per_trade_percentage_balance and trade_signal.stop_loss is not None:
                    return RiskAssessmentResponseData(signal_approved=False, rejection_reason=f"{rejection_msg_portfolio} (Max Loss % Balance)")
                if risk_params.max_concurrent_open_trades is not None:
                    return RiskAssessmentResponseData(signal_approved=False, rejection_reason=f"{rejection_msg_portfolio} (Max Concurrent Trades)")
                if risk_params.max_exposure_per_asset_usd is not None:
                     return RiskAssessmentResponseData(signal_approved=False, rejection_reason=f"{rejection_msg_portfolio} (Max Asset Exposure)")
                # If max_capital_allocation_usd is the only one needing it, and it's set, we might also reject here.
                # For now, individual checks will handle missing portfolio if they can.

        # Ensure required signal fields are present if value-based checks are active
        if trade_signal.quantity is None or trade_signal.price_target is None:
            if risk_params.max_capital_allocation_usd > 0 or \
               (risk_params.max_loss_per_trade_percentage_balance and trade_signal.stop_loss is not None) or \
               risk_params.max_exposure_per_asset_usd is not None:
                reason = "Trade signal missing quantity or price_target, essential for value-based risk checks."
                logger.warning(f"RiskManager: {reason} for agent {agent_id_of_proposer}")
                return RiskAssessmentResponseData(signal_approved=False, rejection_reason=reason)

        # Check 1: Max Trade Value (max_capital_allocation_usd interpreted as max value per trade)
        if risk_params.max_capital_allocation_usd > 0 and trade_signal.quantity is not None and trade_signal.price_target is not None:
            trade_value_usd = trade_signal.quantity * trade_signal.price_target
            if trade_value_usd > risk_params.max_capital_allocation_usd:
                reason = f"Proposed trade value {trade_value_usd:.2f} USD exceeds max capital allocation per trade {risk_params.max_capital_allocation_usd:.2f} USD."
                logger.warning(f"RiskManager: {reason} for agent {agent_id_of_proposer}")
                return RiskAssessmentResponseData(signal_approved=False, rejection_reason=reason)

        # Check 2: Symbol Whitelist
        allowed_symbols = op_params.get("allowed_symbols")
        if allowed_symbols and isinstance(allowed_symbols, list) and trade_signal.symbol:
            normalized_signal_symbol = trade_signal.symbol.replace("-", "/")
            normalized_allowed_symbols = [s.replace("-","/") for s in allowed_symbols]
            if normalized_signal_symbol not in normalized_allowed_symbols:
                reason = f"Symbol {trade_signal.symbol} not in allowed list {normalized_allowed_symbols} for agent {agent_id_of_proposer}."
                logger.warning(f"RiskManager: {reason}")
                return RiskAssessmentResponseData(signal_approved=False, rejection_reason=reason)

        # Check 3: Max Loss Per Trade (Percentage of Balance)
        if risk_params.max_loss_per_trade_percentage_balance and \
           trade_signal.stop_loss is not None and \
           trade_signal.quantity is not None and trade_signal.price_target is not None:
            if account_balance_usd is None or account_balance_usd <= 0: # Check balance is positive
                logger.warning(f"RiskManager: Account balance for {agent_id_of_proposer} is zero, negative or unavailable for max loss % check.")
                return RiskAssessmentResponseData(signal_approved=False, rejection_reason="Account balance zero, negative or unavailable for max loss % check.")

            potential_loss_per_unit = abs(trade_signal.price_target - trade_signal.stop_loss)
            total_potential_loss_usd = potential_loss_per_unit * trade_signal.quantity
            max_allowed_loss_for_trade_usd = account_balance_usd * risk_params.max_loss_per_trade_percentage_balance

            if total_potential_loss_usd > max_allowed_loss_for_trade_usd:
                reason = (f"Potential loss {total_potential_loss_usd:.2f} USD exceeds max allowed risk per trade "
                          f"({risk_params.max_loss_per_trade_percentage_balance*100:.2f}% of balance = {max_allowed_loss_for_trade_usd:.2f} USD).")
                logger.warning(f"RiskManager: {reason} for agent {agent_id_of_proposer}")
                return RiskAssessmentResponseData(signal_approved=False, rejection_reason=reason)

        # Check 4: Max Concurrent Open Trades
        if risk_params.max_concurrent_open_trades is not None:
            # This simplistic check assumes the new trade *always* opens a *new distinct* position.
            # It does not account for trades that add to/reduce an existing position for the same asset.
            # A more accurate check would:
            # 1. Check if a position already exists for trade_signal.symbol.
            # 2. If not, then this new trade would increment the count of distinct open positions.
            # For now, using the simpler (num_open_positions + 1) logic.
            current_distinct_assets_with_positions = {pos.asset for pos in open_positions_list if pos.size != 0}

            is_new_asset_position = trade_signal.symbol not in current_distinct_assets_with_positions

            if is_new_asset_position and (len(current_distinct_assets_with_positions) + 1) > risk_params.max_concurrent_open_trades:
                reason = (f"Opening a new position for {trade_signal.symbol} would exceed max concurrent open positions limit of {risk_params.max_concurrent_open_trades} "
                          f"(currently {len(current_distinct_assets_with_positions)} distinct assets with positions).")
                logger.warning(f"RiskManager: {reason} for agent {agent_id_of_proposer}")
                return RiskAssessmentResponseData(signal_approved=False, rejection_reason=reason)

        # Check 5: Max Exposure Per Asset (USD)
        if risk_params.max_exposure_per_asset_usd is not None and \
           trade_signal.quantity is not None and trade_signal.price_target is not None:
            current_asset_exposure_usd = 0.0
            existing_position_size = 0.0

            for pos in open_positions_list:
                if pos.asset == trade_signal.symbol:
                    # Use current_price if available, else entry_price as proxy for existing position value
                    price_to_use = pos.current_price if pos.current_price is not None else pos.entry_price
                    if price_to_use is not None:
                        current_asset_exposure_usd = abs(pos.size * price_to_use)
                        existing_position_size = pos.size # Signed size
                    break

            new_trade_value = trade_signal.quantity * trade_signal.price_target

            # Calculate prospective exposure:
            # If same side, exposure adds. If opposite, it subtracts (or flips).
            prospective_size = existing_position_size
            if trade_signal.action == "buy":
                prospective_size += trade_signal.quantity
            else: # sell
                prospective_size -= trade_signal.quantity

            # Prospective notional exposure using the signal's price target for the new/changed part
            # This is a simplification; a weighted average price might be more accurate for the total position.
            prospective_notional_exposure = abs(prospective_size * trade_signal.price_target)

            if prospective_notional_exposure > risk_params.max_exposure_per_asset_usd:
                reason = (f"Prospective notional exposure for {trade_signal.symbol} ({prospective_notional_exposure:.2f} USD) "
                          f"would exceed max limit of {risk_params.max_exposure_per_asset_usd:.2f} USD. "
                          f"(Current exposure: {current_asset_exposure_usd:.2f}, Existing size: {existing_position_size}, Trade: {trade_signal.action} {trade_signal.quantity})")
                logger.warning(f"RiskManager: {reason} for agent {agent_id_of_proposer}")
                return RiskAssessmentResponseData(signal_approved=False, rejection_reason=reason)

        logger.info(f"RiskManager: Trade signal for {trade_signal.symbol} from agent {agent_id_of_proposer} approved by all active checks.")
        return RiskAssessmentResponseData(signal_approved=True)

