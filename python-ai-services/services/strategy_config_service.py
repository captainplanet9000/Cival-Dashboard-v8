import uuid
from typing import Optional, List, Dict, Any
from supabase import Client as SupabaseClient
from pydantic import ValidationError # For validating update data if it's a dict
from datetime import datetime, timezone
from logging import getLogger

# Assuming StrategyConfig is importable from models.strategy_models
# Adjust path if necessary based on actual project structure.
from ..models.strategy_models import StrategyConfig, BaseStrategyConfig, PerformanceMetrics, StrategyPerformanceTeaser # Add StrategyPerformanceTeaser
from ..models.trading_history_models import TradeRecord # Add TradeRecord
# Also import specific param models if needed for validation during update, though StrategyConfig handles it.

logger = getLogger(__name__)

class StrategyConfigServiceError(Exception):
    """Base exception for StrategyConfigService errors."""
    pass

class StrategyConfigNotFoundError(StrategyConfigServiceError):
    """Raised when a strategy configuration is not found."""
    pass

class StrategyConfigCreationError(StrategyConfigServiceError):
    """Raised when creating a strategy configuration fails."""
    pass

class StrategyConfigUpdateError(StrategyConfigServiceError):
    """Raised when updating a strategy configuration fails."""
    pass

class StrategyConfigDeletionError(StrategyConfigServiceError):
    """Raised when deleting a strategy configuration fails."""
    pass


class StrategyConfigService:
    TABLE_NAME = "strategy_configurations"

    def __init__(self, supabase_client: SupabaseClient):
        self.supabase = supabase_client
        logger.info("StrategyConfigService initialized.")

    async def create_strategy_config(self, user_id: uuid.UUID, config_data: StrategyConfig) -> StrategyConfig:
        """
        Creates a new strategy configuration for a user.
        The config_data should be a valid StrategyConfig Pydantic model instance.
        """
        logger.info(f"Attempting to create strategy config for user {user_id}, name: {config_data.strategy_name}")

        # Pydantic model_dump converts UUIDs to strings by default if `by_alias=True` or if schema expects string.
        # Ensure strategy_id is a string if it's generated by default_factory=uuid.uuid4
        # and the DB column is expecting a string representation of UUID.
        # Supabase client typically handles UUID objects correctly for UUID columns.
        record_to_insert = config_data.model_dump(exclude_none=True)
        record_to_insert["user_id"] = str(user_id) # Ensure user_id is string for DB if column is not UUID type

        # If strategy_id is part of model and is UUID, ensure it's str if DB expects str.
        # However, if DB column is UUID type, passing UUID object is fine.
        # model_dump() should handle this correctly based on schema or by_alias.
        # For safety, if 'strategy_id' is in record_to_insert and is a UUID object,
        # and your DB column for strategy_id is TEXT/VARCHAR, convert it.
        # If DB column is UUID, this conversion is not strictly necessary.
        # if 'strategy_id' in record_to_insert and isinstance(record_to_insert['strategy_id'], uuid.UUID):
        #    record_to_insert['strategy_id'] = str(record_to_insert['strategy_id'])


        try:
            response = await self.supabase.table(self.TABLE_NAME) \
                .insert(record_to_insert) \
                .select("*") \
                .execute()

            if response.error: # Check for explicit error object first
                err_msg = response.error.message
                logger.error(f"Supabase error creating strategy config for user {user_id}: {err_msg} (Details: {response.error.details if hasattr(response.error, 'details') else 'N/A'})")
                raise StrategyConfigCreationError(f"Failed to create strategy config due to Supabase error: {err_msg}")

            if response.data and len(response.data) > 0:
                logger.info(f"Strategy config created successfully with ID: {response.data[0]['strategy_id']}")
                return StrategyConfig(**response.data[0])
            else: # Should not happen if no error and insert was successful, select * should return data.
                raise StrategyConfigCreationError("Failed to create strategy config: No data returned from insert operation, though no explicit error was reported.")
        except StrategyConfigCreationError: # Re-raise our specific error
            raise
        except Exception as e:
            logger.error(f"Unexpected database error creating strategy config for user {user_id}: {e}", exc_info=True)
            raise StrategyConfigCreationError(f"Unexpected database error: {str(e)}")


    async def get_strategy_config(self, strategy_id: uuid.UUID, user_id: uuid.UUID) -> Optional[StrategyConfig]:
        """Retrieves a specific strategy configuration by its ID, ensuring user ownership."""
        logger.debug(f"Fetching strategy config ID {strategy_id} for user {user_id}")
        try:
            response = await self.supabase.table(self.TABLE_NAME) \
                .select("*") \
                .eq("strategy_id", str(strategy_id)) \
                .eq("user_id", str(user_id)) \
                .maybe_single() \
                .execute()

            if response.error:
                logger.warning(f"Error fetching strategy config ID {strategy_id} for user {user_id}: {response.error.message}")
                return None # Or raise an error depending on desired behavior for "not found due to error"

            if response.data:
                return StrategyConfig(**response.data)
            return None # Not found, but no DB error
        except Exception as e:
            logger.error(f"Database error fetching strategy config ID {strategy_id}: {e}", exc_info=True)
            raise StrategyConfigServiceError(f"Database error fetching strategy config: {str(e)}")

    async def get_strategy_configs_by_user(self, user_id: uuid.UUID) -> List[StrategyConfig]:
        """Retrieves all strategy configurations for a specific user."""
        logger.debug(f"Fetching all strategy configs for user {user_id}")
        try:
            response = await self.supabase.table(self.TABLE_NAME) \
                .select("*") \
                .eq("user_id", str(user_id)) \
                .order("created_at", desc=True) \
                .execute()
            if response.error:
                logger.error(f"Error fetching strategy configs for user {user_id}: {response.error.message}")
                return [] # Return empty list on error, or raise
            return [StrategyConfig(**item) for item in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Database error fetching strategy configs for user {user_id}: {e}", exc_info=True)
            raise StrategyConfigServiceError(f"Database error fetching configs for user: {str(e)}")

    async def update_strategy_config(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
        update_payload: Dict[str, Any]
    ) -> StrategyConfig:
        logger.info(f"Attempting to update strategy config ID {strategy_id} for user {user_id}")

        # It's critical to ensure that `user_id` in the query matches the one trying to update.
        # The `get_strategy_config` call isn't strictly necessary if the update query includes user_id match,
        # but it's a good pre-check or can be used to get the full existing object for merging.
        # For this implementation, we'll rely on the update query's .eq("user_id", str(user_id)) for ownership.

        update_data = update_payload.copy()
        # Prevent update of primary key, user_id, or creation timestamp
        update_data.pop("strategy_id", None)
        update_data.pop("user_id", None)
        update_data.pop("created_at", None)
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        if not update_data or all(k == "updated_at" for k in update_data): # Check if only updated_at is there
            raise ValueError("No valid fields provided for update beyond timestamp.")

        # If 'parameters' are part of update_data, ensure they are valid for the existing strategy_type.
        # This requires fetching the existing strategy_type if 'parameters' is in update_data
        # and 'strategy_type' is not being changed in the same payload to something incompatible.
        # StrategyConfig Pydantic model's validator handles this if we construct a full model.
        # For partial updates using a dict, this validation is manual or less strict here.
        # A robust way: fetch, merge, validate with Pydantic, then save.
        # For now, assume payload is valid for the existing strategy_type if 'parameters' is updated.

        try:
            response = await self.supabase.table(self.TABLE_NAME) \
                .update(update_data) \
                .eq("strategy_id", str(strategy_id)) \
                .eq("user_id", str(user_id)) \
                .select("*") \
                .execute()

            if response.error:
                err_msg = response.error.message
                logger.error(f"Supabase error updating strategy config ID {strategy_id}: {err_msg}")
                # Check for specific error codes that might indicate "not found" vs. other errors
                # e.g. PostgREST error codes. For now, general update error.
                raise StrategyConfigUpdateError(f"Failed to update strategy config {strategy_id} due to Supabase error: {err_msg}")

            if response.data and len(response.data) > 0:
                logger.info(f"Strategy config ID {strategy_id} updated successfully.")
                return StrategyConfig(**response.data[0])
            else:
                # If no error but no data, it means the .eq filters found no matching row.
                raise StrategyConfigNotFoundError(f"Strategy configuration {strategy_id} not found for user {user_id}, or no data returned after update.")
        except (StrategyConfigUpdateError, StrategyConfigNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Unexpected database error updating strategy config ID {strategy_id}: {e}", exc_info=True)
            raise StrategyConfigUpdateError(f"Unexpected database error during update: {str(e)}")


    async def delete_strategy_config(self, strategy_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Deletes a strategy configuration, ensuring user ownership."""
        logger.info(f"Attempting to delete strategy config ID {strategy_id} for user {user_id}")

        # The .delete().eq("user_id", ...) ensures user ownership at DB level.
        # An additional fetch (like get_strategy_config) first is a pre-check but not strictly required for security
        # if RLS is also in place or the delete query is precise.
        # For this example, we'll proceed directly with a user-scoped delete.

        try:
            response = await self.supabase.table(self.TABLE_NAME) \
                .delete() \
                .eq("strategy_id", str(strategy_id)) \
                .eq("user_id", str(user_id)) \
                .execute()

            if response.error:
                err_msg = response.error.message
                logger.error(f"Supabase error deleting strategy config ID {strategy_id}: {err_msg}")
                raise StrategyConfigDeletionError(f"Failed to delete strategy config {strategy_id} due to Supabase error: {err_msg}")

            # Supabase delete by default returns list of deleted records if select() is used,
            # or a count if `count` option is specified. If no select/count, data might be empty on success.
            # We need to check if any rows were actually deleted.
            # The `execute()` for delete usually doesn't have data unless `select()` was chained.
            # A common pattern is to check if an error occurred. If not, assume success.
            # If you need to confirm a row was deleted, you might need to adjust based on Supabase client version
            # or do a pre-check (as the prompt's version did).
            # For now, if no error, assume success.
            # If response.count is available and 0, it means not found. (Requires count='exact' typically)
            # if hasattr(response, 'count') and response.count == 0:
            #    raise StrategyConfigNotFoundError(f"Strategy configuration {strategy_id} not found for user {user_id} to delete.")

            logger.info(f"Strategy config ID {strategy_id} for user {user_id} processed for deletion (if it existed and was owned).")
            # No specific data is typically returned on delete if select() is not used.
            # If an error occurs (like RLS violation or DB error), response.error will be set.
        except StrategyConfigDeletionError:
            raise
        except Exception as e:
            logger.error(f"Database error deleting strategy config ID {strategy_id}: {e}", exc_info=True)
            raise StrategyConfigDeletionError(f"Database error during deletion: {str(e)}")

    async def get_latest_performance_metrics(self, strategy_id: uuid.UUID, user_id: uuid.UUID) -> Optional[PerformanceMetrics]:
        """Retrieves the most recent performance metrics for a given strategy owned by the user."""
        logger.debug(f"Fetching latest performance metrics for strategy ID {strategy_id}, user {user_id}")
        try:
            # First, verify the strategy config exists and belongs to the user
            strategy_config = await self.get_strategy_config(strategy_id, user_id)
            if not strategy_config:
                logger.warning(f"Strategy config {strategy_id} not found for user {user_id}. Cannot fetch performance.")
                return None

            response = await self.supabase.table("strategy_results") \
                .select("*") \
                .eq("strategy_id", str(strategy_id)) \
                .order("generated_at", desc=True) \
                .limit(1) \
                .maybe_single() \
                .execute()

            if response.error:
                logger.warning(f"Error fetching performance metrics for strategy {strategy_id}: {response.error.message}")
                # Depending on the error, might raise or return None.
                # If it's a query error vs. just no data, behavior might differ.
                return None # For now, return None on any DB error during fetch for this sub-resource.

            if response.data:
                return PerformanceMetrics(**response.data)
            return None # No performance metrics found
        except Exception as e:
            logger.error(f"Database error fetching performance metrics for strategy ID {strategy_id}: {e}", exc_info=True)
            raise StrategyConfigServiceError(f"Database error fetching performance metrics: {str(e)}")

    async def get_trade_history_for_strategy(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[TradeRecord]:
        """Retrieves trade history associated with a specific strategy owned by the user."""
        logger.debug(f"Fetching trade history for strategy ID {strategy_id}, user {user_id}, limit {limit}, offset {offset}")
        try:
            strategy_config = await self.get_strategy_config(strategy_id, user_id)
            if not strategy_config:
                logger.warning(f"Strategy config {strategy_id} not found for user {user_id}. Cannot fetch trade history.")
                return []

            response = await self.supabase.table("trading_history") \
                .select("*") \
                .eq("strategy_id", str(strategy_id)) \
                .eq("user_id", str(user_id)) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .offset(offset) \
                .execute()

            if response.error:
                logger.error(f"Error fetching trade history for strategy {strategy_id}: {response.error.message}")
                return [] # Return empty list on error

            return [TradeRecord(**item) for item in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Database error fetching trade history for strategy ID {strategy_id}: {e}", exc_info=True)
            raise StrategyConfigServiceError(f"Database error fetching trade history: {str(e)}")

    async def get_all_user_strategies_with_performance_teasers(self, user_id: uuid.UUID) -> List[StrategyPerformanceTeaser]:
        """
        Retrieves all strategy configurations for a user, augmented with key teaser info
        from their latest performance metrics record using a batch query for efficiency.
        """
        logger.debug(f"Fetching all strategy configs with performance teasers for user {user_id} (optimized)")

        strategy_configs = await self.get_strategy_configs_by_user(user_id)
        if not strategy_configs:
            return []

        strategy_ids = [str(config.strategy_id) for config in strategy_configs]
        latest_metrics_map: Dict[str, PerformanceMetrics] = {}

        if strategy_ids:
            try:
                # Using a common table expression (CTE) with ROW_NUMBER() to get the latest metric per strategy_id
                # This SQL is specific to PostgreSQL. Supabase uses PostgreSQL.
                # Note: Supabase Python client's .execute() on a raw query might not parse into Postgrest VRL.
                # It's often better to use RPC or a view if complex raw SQL is needed repeatedly.
                # For this, we can try to construct it with the query builder if possible, or use rpc.
                # A direct .execute() on raw SQL might be possible with some client versions or configurations.
                # However, a simpler (though potentially less performant than pure SQL window function) way
                # is to fetch all relevant metrics and process in Python if direct window functions are hard with the query builder.
                #
                # Let's try a filter and sort, then group in Python. This is less ideal than a window function.
                # response_metrics = await self.supabase.table("strategy_results")                 #     .select("*")                 #     .in_("strategy_id", strategy_ids)                 #     .order("generated_at", desc=True)                 #     .execute()
                # if response_metrics.data:
                #     for metric_data in response_metrics.data:
                #         strat_id = str(metric_data["strategy_id"])
                #         if strat_id not in latest_metrics_map: # Keep only the first one (latest)
                #             latest_metrics_map[strat_id] = PerformanceMetrics(**metric_data)
                #
                # The above approach is not guaranteed to be the "latest" if multiple metrics for same strategy_id
                # exist and are not perfectly ordered before Python processing if limit per group isn't applied.
                #
                # A more robust way with Supabase query builder if direct window functions are not easy:
                # Fetch all metrics for the given strategy_ids, then process in Python to find the latest for each.
                # This is what the previous N+1 loop effectively did, but N calls vs 1 larger call.
                # The N+1 solution is to get all relevant metrics then process in Python.

                # Corrected approach for batch fetching latest metrics:
                # This still fetches all metrics for the strategy_ids and then python-side finds latest.
                # True optimization would be a window function via rpc or a view.
                # For now, this reduces N DB calls to 1 DB call + Python processing.

                all_metrics_response = await self.supabase.table("strategy_results") \
                    .select("*") \
                    .in_("strategy_id", strategy_ids) \
                    .order("strategy_id").order("generated_at", desc=True) \
                    .execute()

                if all_metrics_response.error:
                    logger.error(f"DB error fetching all performance metrics for strategies {strategy_ids}: {all_metrics_response.error.message}")
                elif all_metrics_response.data:
                    temp_metrics_map: Dict[str, PerformanceMetrics] = {}
                    for metric_data in all_metrics_response.data:
                        strat_id = str(metric_data["strategy_id"])
                        # Since data is ordered by strategy_id then generated_at desc,
                        # the first one we encounter for each strategy_id is the latest.
                        if strat_id not in temp_metrics_map:
                            temp_metrics_map[strat_id] = PerformanceMetrics(**metric_data)
                    latest_metrics_map = temp_metrics_map

            except Exception as e:
                logger.error(f"Error batch fetching performance metrics for strategies {strategy_ids}: {e}", exc_info=True)
                # Continue without metrics if batch fetch fails, teasers will have None for metric fields.

        teasers: List[StrategyPerformanceTeaser] = []
        for config in strategy_configs:
            latest_metrics = latest_metrics_map.get(str(config.strategy_id))

            teaser_data = {
                "strategy_id": config.strategy_id,
                "strategy_name": config.strategy_name,
                "strategy_type": config.strategy_type,
                "is_active": config.is_active,
                "symbols": config.symbols,
                "timeframe": config.timeframe,
                "latest_performance_record_timestamp": None,
                "latest_net_profit_percentage": None,
                "latest_sharpe_ratio": None,
                "latest_sortino_ratio": None,
                "latest_max_drawdown_percentage": None,
                "total_trades_from_latest_metrics": None
            }
            if latest_metrics:
                teaser_data["latest_performance_record_timestamp"] = latest_metrics.generated_at
                teaser_data["latest_net_profit_percentage"] = latest_metrics.net_profit_percentage
                teaser_data["latest_sharpe_ratio"] = latest_metrics.sharpe_ratio
                teaser_data["latest_sortino_ratio"] = latest_metrics.sortino_ratio
                teaser_data["latest_max_drawdown_percentage"] = latest_metrics.max_drawdown_percentage
                if latest_metrics.trade_stats:
                    teaser_data["total_trades_from_latest_metrics"] = latest_metrics.trade_stats.total_trades

            teasers.append(StrategyPerformanceTeaser(**teaser_data))

        return teasers
