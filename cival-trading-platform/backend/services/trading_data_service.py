from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
import uuid # For mock data generation
from loguru import logger

from ..models.agent_models import AgentConfigOutput
from ..models.dashboard_models import (
    AssetPositionSummary,
    PortfolioSummary,
    TradeLogItem,
    OrderLogItem
)
from ..models.hyperliquid_models import HyperliquidAccountSnapshot, HyperliquidAssetPosition, HyperliquidOpenOrderItem, HyperliquidMarginSummary
from .agent_management_service import AgentManagementService
from .hyperliquid_execution_service import HyperliquidExecutionService, HyperliquidExecutionServiceError

# Define a type for the HyperliquidExecutionService factory - REMOVED
# HyperliquidServiceFactory = Callable[[str], Optional[HyperliquidExecutionService]]

from .trade_history_service import TradeHistoryService # Added import
# Use the new factory
from ..core.factories import get_hyperliquid_execution_service_instance
from .order_history_service import OrderHistoryService # Added
from ..models.db_models import OrderDB # Added for type hinting

class TradingDataService:
    def __init__(
        self,
        agent_service: AgentManagementService,
        trade_history_service: TradeHistoryService,
        order_history_service: OrderHistoryService # Added
    ):
        self.agent_service = agent_service
        self.trade_history_service = trade_history_service
        self.order_history_service = order_history_service # Added
        logger.info("TradingDataService initialized with TradeHistoryService, OrderHistoryService, and HLES factory usage.")

    # _get_hles_instance helper is removed as HLES instantiation will be direct in methods needing it.
    # Or, it can be kept and modified to use the new factory if preferred for DRY.
    # For this refactor, let's try direct usage in methods first.

    def _safe_float(self, value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _map_db_order_to_order_log_item(self, db_order: OrderDB) -> OrderLogItem:
        # Helper to map OrderDB to OrderLogItem Pydantic model
        return OrderLogItem(
            internal_order_id=db_order.internal_order_id,
            agent_id=db_order.agent_id,
            timestamp_created=db_order.timestamp_created,
            timestamp_updated=db_order.timestamp_updated,
            asset=db_order.asset,
            side=db_order.side, # type: ignore
            order_type=db_order.order_type, # type: ignore
            quantity=db_order.quantity,
            limit_price=db_order.limit_price,
            status=db_order.status, # type: ignore
            exchange_order_id=db_order.exchange_order_id,
            client_order_id=db_order.client_order_id,
            error_message=db_order.error_message,
            strategy_name=db_order.strategy_name
            # Note: filled_quantity and avg_fill_price are not directly on OrderDB.
            # These would be calculated by joining/processing fills or from aggregated data.
            # OrderLogItem model might need to make these Optional or they are derived by caller.
        )

    async def get_portfolio_summary(self, agent_id: str) -> Optional[PortfolioSummary]:
        logger.info(f"Fetching portfolio summary for agent {agent_id}.")
        agent_config = await self.agent_service.get_agent(agent_id)
        if not agent_config:
            logger.warning(f"Agent {agent_id} not found for portfolio summary.")
            return None

        now_utc = datetime.now(timezone.utc)

        if agent_config.execution_provider == "hyperliquid":
            # Use new factory directly
            hles = get_hyperliquid_execution_service_instance(agent_config)
            if not hles:
                logger.warning(f"Could not get HLES instance for agent {agent_id} in get_portfolio_summary.")
                return None # Error already logged by factory

            try:
                # We need both account snapshot (for positions) and margin summary (for overall values)
                # The HyperliquidExecutionService.get_detailed_account_summary() returns HyperliquidAccountSnapshot
                # which includes parsed positions and some margin summary fields.
                # Let's assume get_account_margin_summary() gives the most direct HyperliquidMarginSummary.

                hl_margin_summary: Optional[HyperliquidMarginSummary] = await hles.get_account_margin_summary()
                hl_account_snapshot: Optional[HyperliquidAccountSnapshot] = await hles.get_detailed_account_summary(hles.wallet_address)

                if not hl_margin_summary or not hl_account_snapshot:
                    logger.error(f"Failed to fetch complete Hyperliquid data for agent {agent_id}.")
                    return None

                open_positions_summary: List[AssetPositionSummary] = []
                if hl_account_snapshot.parsed_positions:
                    for pos in hl_account_snapshot.parsed_positions:
                        open_positions_summary.append(AssetPositionSummary(
                            asset=pos.asset,
                            size=self._safe_float(pos.szi) or 0.0,
                            entry_price=self._safe_float(pos.entry_px),
                            # current_price: # Needs a separate market data feed
                            unrealized_pnl=self._safe_float(pos.unrealized_pnl),
                            margin_used=self._safe_float(pos.margin_used)
                        ))

                return PortfolioSummary(
                    agent_id=agent_id,
                    timestamp=now_utc,
                    account_value_usd=self._safe_float(hl_margin_summary.account_value) or 0.0,
                    total_pnl_usd=self._safe_float(hl_margin_summary.total_ntl_pos) or 0.0, # totalNtlPos is often used as total PnL
                    available_balance_usd=self._safe_float(hl_margin_summary.available_balance_for_new_orders), # Mapped from 'withdrawable'
                    margin_used_usd=self._safe_float(hl_margin_summary.total_margin_used),
                    open_positions=open_positions_summary
                )

            except HyperliquidExecutionServiceError as e:
                logger.error(f"Hyperliquid service error for agent {agent_id}: {e}", exc_info=True)
                return None
            except Exception as e:
                logger.error(f"Unexpected error fetching Hyperliquid portfolio for agent {agent_id}: {e}", exc_info=True)
                return None

        elif agent_config.execution_provider == "paper":
            logger.info(f"Returning mocked paper portfolio summary for agent {agent_id}.")
            return PortfolioSummary(
                agent_id=agent_id,
                timestamp=now_utc,
                account_value_usd=10000.0,
                total_pnl_usd=150.75,
                available_balance_usd=9800.0,
                margin_used_usd=200.0,
                open_positions=[
                    AssetPositionSummary(asset="PAPER_BTC", size=0.1, entry_price=50000.0, unrealized_pnl=100.0),
                    AssetPositionSummary(asset="PAPER_ETH", size=1.0, entry_price=3000.0, unrealized_pnl=50.75)
                ]
            )
        else:
            logger.warning(f"Unknown execution provider '{agent_config.execution_provider}' for agent {agent_id}.")
            return None

    async def get_trade_history(self, agent_id: str, limit: int = 100, offset: int = 0) -> List[TradeLogItem]:
        logger.info(f"Fetching trade history for agent {agent_id} (limit={limit}, offset={offset}) using TradeHistoryService.")
        # Remove the existing mocked implementation.
        # Call await self.trade_history_service.get_processed_trades(agent_id, limit=limit, offset=offset).
        # Return the result directly.
        try:
            processed_trades = await self.trade_history_service.get_processed_trades(
                agent_id=agent_id, limit=limit, offset=offset
            )
            logger.info(f"Retrieved {len(processed_trades)} processed trades for agent {agent_id} from TradeHistoryService.")
            return processed_trades
        except Exception as e:
            logger.error(f"Error fetching processed trades for agent {agent_id} from TradeHistoryService: {e}", exc_info=True)
            return [] # Return empty list on error, or re-raise depending on desired error handling

    async def get_open_orders(self, agent_id: str) -> List[OrderLogItem]:
        logger.info(f"Fetching open orders for agent {agent_id} from OrderHistoryService.")
        if not self.order_history_service:
            logger.error("OrderHistoryService not available to TradingDataService.")
            return []

        # Define what statuses are considered "open"
        open_statuses = ["PENDING_SUBMISSION", "SUBMITTED_TO_EXCHANGE", "ACCEPTED_BY_EXCHANGE", "PARTIALLY_FILLED"]

        all_open_orders_pydantic: List[OrderLogItem] = []
        for status in open_statuses:
            try:
                # Assuming get_orders_for_agent returns List[OrderDB]
                db_orders: List[OrderDB] = await self.order_history_service.get_orders_for_agent(
                    agent_id=agent_id, status_filter=status, limit=1000, sort_desc=True # Fetch many, sort by newest
                )
                all_open_orders_pydantic.extend([self._map_db_order_to_order_log_item(o) for o in db_orders])
            except Exception as e:
                logger.error(f"Error fetching orders with status {status} for agent {agent_id}: {e}", exc_info=True)

        # Sort by creation time if multiple status fetches occurred, though get_orders_for_agent sorts by created time.
        # If get_orders_for_agent already sorts desc, this might not be strictly needed unless combining results.
        all_open_orders_pydantic.sort(key=lambda x: x.timestamp_created, reverse=True)
        logger.info(f"Retrieved {len(all_open_orders_pydantic)} open orders for agent {agent_id}.")
        return all_open_orders_pydantic

    async def get_order_history(self, agent_id: str, limit: int = 100, offset: int = 0) -> List[OrderLogItem]:
        logger.info(f"Fetching order history for agent {agent_id} (limit={limit}, offset={offset}) from OrderHistoryService.")
        if not self.order_history_service:
            logger.error("OrderHistoryService not available to TradingDataService.")
            return []

        try:
            # Assuming get_orders_for_agent returns List[OrderDB]
            db_orders: List[OrderDB] = await self.order_history_service.get_orders_for_agent(
                agent_id=agent_id, limit=limit, offset=offset, sort_desc=True # Get newest first
            )
            return [self._map_db_order_to_order_log_item(o) for o in db_orders]
        except Exception as e:
            logger.error(f"Error fetching order history for agent {agent_id}: {e}", exc_info=True)
            return []

