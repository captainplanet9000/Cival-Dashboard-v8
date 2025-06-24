import uuid
from typing import Optional, List, Dict, Any
from supabase import Client as SupabaseClient
# from pydantic import ValidationError # Not explicitly used, but good for reference if complex validation needed
from datetime import datetime, timezone
from logging import getLogger
import asyncio # For potential parallelization of sync tool calls

from ..models.watchlist_models import (
    Watchlist, WatchlistCreate, WatchlistItem, WatchlistItemCreate, WatchlistWithItems,
    AddWatchlistItemsRequest, BatchQuotesRequest, BatchQuotesResponse, BatchQuotesResponseItem
)
# Assuming get_current_quote_tool is correctly exposed and importable
from ..tools.market_data_tools import get_current_quote_tool

logger = getLogger(__name__)

class WatchlistServiceError(Exception):
    """Base exception for WatchlistService errors."""
    pass

class WatchlistNotFoundError(WatchlistServiceError):
    pass

class WatchlistItemNotFoundError(WatchlistServiceError):
    pass

class WatchlistOperationForbiddenError(WatchlistServiceError): # For ownership issues
    pass

class WatchlistService:
    WATCHLIST_TABLE = "watchlists"
    WATCHLIST_ITEM_TABLE = "watchlist_items"

    def __init__(self, supabase_client: SupabaseClient):
        self.supabase = supabase_client
        logger.info("WatchlistService initialized.")

    # --- Watchlist CRUD ---
    async def create_watchlist(self, user_id: uuid.UUID, data: WatchlistCreate) -> Watchlist:
        logger.info(f"User {user_id} creating watchlist: {data.name}")
        record = data.model_dump()
        record['user_id'] = str(user_id)
        # Set created_at and updated_at server-side or here if DB doesn't auto-set
        now_utc_iso = datetime.now(timezone.utc).isoformat()
        record['created_at'] = now_utc_iso
        record['updated_at'] = now_utc_iso
        try:
            response = await self.supabase.table(self.WATCHLIST_TABLE).insert(record).select("*").execute()
            if not response.data: # Check for actual data
                err_msg = getattr(response.error, 'message', 'No data returned after insert attempt.') if response.error else 'No data returned after insert attempt.'
                raise WatchlistServiceError(f"Failed to create watchlist: {err_msg}")
            return Watchlist(**response.data[0])
        except Exception as e:
            logger.error(f"DB error creating watchlist for user {user_id}: {e}", exc_info=True)
            raise WatchlistServiceError(f"DB error: {str(e)}")

    async def get_watchlist(self, watchlist_id: uuid.UUID, user_id: uuid.UUID, include_items: bool = False) -> Optional[Watchlist | WatchlistWithItems]:
        logger.debug(f"User {user_id} fetching watchlist: {watchlist_id}, include_items: {include_items}")
        try:
            response = await self.supabase.table(self.WATCHLIST_TABLE).select("*").eq("watchlist_id", str(watchlist_id)).eq("user_id", str(user_id)).maybe_single().execute()
            if not response.data:
                return None # Watchlist not found or not owned by user

            watchlist = Watchlist(**response.data)
            if include_items:
                items = await self.get_items_for_watchlist(watchlist_id, user_id) # This already checks ownership
                return WatchlistWithItems(**watchlist.model_dump(), items=items)
            return watchlist
        except Exception as e:
            logger.error(f"DB error fetching watchlist {watchlist_id} for user {user_id}: {e}", exc_info=True)
            raise WatchlistServiceError(f"DB error: {str(e)}")

    async def get_watchlists_by_user(self, user_id: uuid.UUID) -> List[Watchlist]:
        logger.debug(f"User {user_id} fetching all watchlists")
        try:
            response = await self.supabase.table(self.WATCHLIST_TABLE).select("*").eq("user_id", str(user_id)).order("created_at", desc=True).execute()
            return [Watchlist(**item) for item in response.data] if response.data else []
        except Exception as e:
            logger.error(f"DB error fetching watchlists for user {user_id}: {e}", exc_info=True)
            raise WatchlistServiceError(f"DB error: {str(e)}")

    async def update_watchlist(self, watchlist_id: uuid.UUID, user_id: uuid.UUID, data: WatchlistBase) -> Watchlist:
        logger.info(f"User {user_id} updating watchlist: {watchlist_id}")
        existing_watchlist = await self.get_watchlist(watchlist_id, user_id) # Verifies ownership
        if not existing_watchlist:
            raise WatchlistNotFoundError(f"Watchlist {watchlist_id} not found or not owned by user {user_id}.")

        update_payload = data.model_dump(exclude_unset=True)
        if not update_payload: # If payload is empty after exclude_unset
             logger.warning(f"Update called for watchlist {watchlist_id} with no actual data fields to update.")
             return existing_watchlist # Return existing as no change

        update_payload['updated_at'] = datetime.now(timezone.utc).isoformat()

        try:
            response = await self.supabase.table(self.WATCHLIST_TABLE).update(update_payload).eq("watchlist_id", str(watchlist_id)).eq("user_id", str(user_id)).select("*").execute()
            if not response.data:
                err_msg = getattr(response.error, 'message', 'Update failed: No data returned or record not found.') if response.error else 'Update failed: No data returned or record not found.'
                raise WatchlistServiceError(f"Failed to update watchlist {watchlist_id}: {err_msg}")
            return Watchlist(**response.data[0])
        except Exception as e:
            logger.error(f"DB error updating watchlist {watchlist_id} for user {user_id}: {e}", exc_info=True)
            raise WatchlistServiceError(f"DB error: {str(e)}")

    async def delete_watchlist(self, watchlist_id: uuid.UUID, user_id: uuid.UUID) -> None:
        logger.info(f"User {user_id} deleting watchlist: {watchlist_id}")
        existing_watchlist = await self.get_watchlist(watchlist_id, user_id) # Verifies ownership
        if not existing_watchlist:
            raise WatchlistNotFoundError(f"Watchlist {watchlist_id} not found or not owned by user {user_id}.")
        try:
            # Assuming ON DELETE CASCADE is set in DB for watchlist_items table for this watchlist_id
            await self.supabase.table(self.WATCHLIST_TABLE).delete().eq("watchlist_id", str(watchlist_id)).eq("user_id", str(user_id)).execute()
            logger.info(f"Watchlist {watchlist_id} and its items (if cascade is set) deleted successfully.")
        except Exception as e:
            logger.error(f"DB error deleting watchlist {watchlist_id} for user {user_id}: {e}", exc_info=True)
            raise WatchlistServiceError(f"DB error: {str(e)}")

    # --- Watchlist Item CRUD ---
    async def add_item_to_watchlist(self, watchlist_id: uuid.UUID, user_id: uuid.UUID, item_data: WatchlistItemCreate) -> WatchlistItem:
        logger.info(f"User {user_id} adding item {item_data.symbol} to watchlist {watchlist_id}")
        watchlist = await self.get_watchlist(watchlist_id, user_id) # Verifies ownership
        if not watchlist:
            raise WatchlistNotFoundError(f"Watchlist {watchlist_id} not found for user {user_id}.")

        record = item_data.model_dump()
        record['watchlist_id'] = str(watchlist_id)
        record['user_id'] = str(user_id)
        record['added_at'] = datetime.now(timezone.utc).isoformat()
        try:
            response = await self.supabase.table(self.WATCHLIST_ITEM_TABLE).insert(record).select("*").execute()
            if not response.data:
                err_msg = getattr(response.error, 'message', 'No data returned after insert.') if response.error else 'No data returned after insert.'
                raise WatchlistServiceError(f"Failed to add item to watchlist {watchlist_id}: {err_msg}")
            return WatchlistItem(**response.data[0])
        except Exception as e:
            logger.error(f"DB error adding item to watchlist {watchlist_id}: {e}", exc_info=True)
            if "unique constraint" in str(e).lower() and "user_watchlist_symbol_unique" in str(e).lower(): # More specific check
                 raise WatchlistServiceError(f"Symbol '{item_data.symbol}' already exists in watchlist '{watchlist.name}'.")
            raise WatchlistServiceError(f"DB error adding item: {str(e)}")

    async def add_multiple_items_to_watchlist(self, watchlist_id: uuid.UUID, user_id: uuid.UUID, items_request: AddWatchlistItemsRequest) -> List[WatchlistItem]:
        watchlist = await self.get_watchlist(watchlist_id, user_id) # Verifies ownership
        if not watchlist:
            raise WatchlistNotFoundError(f"Watchlist {watchlist_id} not found for user {user_id}.")

        items_to_create_payload = []
        now_utc_iso = datetime.now(timezone.utc).isoformat()
        if items_request.symbols:
            for symbol_str in items_request.symbols: # Ensure symbol_str is used
                items_to_create_payload.append(WatchlistItemCreate(symbol=symbol_str).model_dump())
        elif items_request.items:
            for item_create_data in items_request.items:
                items_to_create_payload.append(item_create_data.model_dump())

        if not items_to_create_payload:
            return []

        for payload_item in items_to_create_payload:
            payload_item['watchlist_id'] = str(watchlist_id)
            payload_item['user_id'] = str(user_id)
            payload_item['added_at'] = now_utc_iso # Consistent timestamp for batch

        logger.info(f"User {user_id} batch adding {len(items_to_create_payload)} items to watchlist {watchlist_id}")
        try:
            # Note: Supabase insert returning "representation" is default and returns inserted rows.
            response = await self.supabase.table(self.WATCHLIST_ITEM_TABLE).insert(items_to_create_payload).select("*").execute()
            if not response.data: # Should not happen if insert was successful and returned data
                err_msg = getattr(response.error, 'message', 'No data returned after batch insert.') if response.error else 'No data returned after batch insert.'
                raise WatchlistServiceError(f"Failed to batch add items to watchlist {watchlist_id}: {err_msg}")
            return [WatchlistItem(**item) for item in response.data]
        except Exception as e:
            logger.error(f"DB error batch adding items to watchlist {watchlist_id}: {e}", exc_info=True)
            if "unique constraint" in str(e).lower() and "user_watchlist_symbol_unique" in str(e).lower():
                 raise WatchlistServiceError(f"One or more symbols already exist in watchlist '{watchlist.name}'. Batch add partially failed or fully failed.")
            raise WatchlistServiceError(f"DB error batch adding items: {str(e)}")

    async def get_items_for_watchlist(self, watchlist_id: uuid.UUID, user_id: uuid.UUID) -> List[WatchlistItem]:
        logger.debug(f"User {user_id} fetching items for watchlist: {watchlist_id}")
        watchlist = await self.get_watchlist(watchlist_id, user_id) # Verifies ownership
        if not watchlist:
             raise WatchlistNotFoundError(f"Watchlist {watchlist_id} not found or not owned by user {user_id}.")

        try:
            response = await self.supabase.table(self.WATCHLIST_ITEM_TABLE).select("*").eq("watchlist_id", str(watchlist_id)).eq("user_id", str(user_id)).order("added_at", desc=False).execute()
            return [WatchlistItem(**item) for item in response.data] if response.data else []
        except Exception as e:
            logger.error(f"DB error fetching items for watchlist {watchlist_id}: {e}", exc_info=True)
            raise WatchlistServiceError(f"DB error: {str(e)}")

    async def remove_item_from_watchlist(self, item_id: uuid.UUID, user_id: uuid.UUID) -> None:
        logger.info(f"User {user_id} removing item {item_id} from watchlist")
        item_response = await self.supabase.table(self.WATCHLIST_ITEM_TABLE).select("user_id").eq("item_id", str(item_id)).maybe_single().execute()
        if not item_response.data:
            raise WatchlistItemNotFoundError(f"Watchlist item {item_id} not found.")
        if str(user_id) != str(item_response.data['user_id']): # Ensure UUIDs are compared as strings or UUID objects
            raise WatchlistOperationForbiddenError(f"User {user_id} not authorized to delete item {item_id}.")

        try:
            await self.supabase.table(self.WATCHLIST_ITEM_TABLE).delete().eq("item_id", str(item_id)).eq("user_id", str(user_id)).execute()
            logger.info(f"Watchlist item {item_id} deleted successfully.")
        except Exception as e:
            logger.error(f"DB error deleting item {item_id}: {e}", exc_info=True)
            raise WatchlistServiceError(f"DB error: {str(e)}")

    # --- Batch Quotes ---
    async def get_batch_quotes_for_symbols(self, symbols: List[str], provider: str = "yfinance") -> BatchQuotesResponse:
        logger.info(f"Fetching batch quotes for symbols: {symbols} via {provider}")

        # Helper function to run sync tool in executor
        async def fetch_quote_async(symbol_str: str):
            loop = asyncio.get_event_loop()
            try:
                # get_current_quote_tool.func to access the actual function if it's a Langchain tool
                quote_data = await loop.run_in_executor(None, get_current_quote_tool.func if hasattr(get_current_quote_tool, 'func') else get_current_quote_tool, symbol_str, provider)
                if isinstance(quote_data, dict) and "error" in quote_data:
                    return BatchQuotesResponseItem(symbol=symbol_str, error=str(quote_data["error"]))
                elif quote_data is None:
                    return BatchQuotesResponseItem(symbol=symbol_str, error="Failed to fetch quote (None returned).")
                return BatchQuotesResponseItem(symbol=symbol_str, quote_data=quote_data)
            except Exception as e:
                logger.error(f"Exception fetching quote for {symbol_str}: {e}", exc_info=True)
                return BatchQuotesResponseItem(symbol=symbol_str, error=f"Exception: {str(e)}")

        tasks = [fetch_quote_async(s) for s in symbols]
        results = await asyncio.gather(*tasks)

        return BatchQuotesResponse(results=results)
