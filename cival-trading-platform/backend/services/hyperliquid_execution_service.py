import os
from typing import Optional, List, Dict, Any, Literal
from logging import getLogger
from decimal import Decimal # For precise calculations if needed by SDK or for amounts
import uuid # Required for HyperliquidPlaceOrderParams cloid default_factory

# Import the SDK - this assumes `pip install hyperliquid` was successful
try:
    from hyperliquid.info import Info
    from hyperliquid.exchange import Exchange
    from hyperliquid.utils import constants as HL_CONSTANTS # For URLs
    from hyperliquid.utils.signing import private_key_to_address # For deriving address if needed
except ImportError:
    # Initialize logger here or ensure it's configured at application startup
    # For now, using a basic getLogger if not already configured.
    logger_hl_import = getLogger(__name__)
    logger_hl_import.error("Hyperliquid SDK not found. Please install it: pip install hyperliquid")
    Info, Exchange, HL_CONSTANTS, private_key_to_address = None, None, None, None

from eth_account import Account # Standard library for Ethereum account management
import asyncio # For running sync SDK methods in async context

# Import Pydantic models
from ..models.hyperliquid_models import (
    HyperliquidCredentials, HyperliquidPlaceOrderParams, HyperliquidOrderResponseData,
    HyperliquidOrderStatusInfo, HyperliquidAssetPosition, HyperliquidOpenOrderItem,
    HyperliquidAccountSnapshot, HyperliquidMarginSummary # New/Refined
)
from datetime import datetime, timezone # Ensure datetime and timezone are imported

logger = getLogger(__name__)

class HyperliquidExecutionServiceError(Exception):
    pass

class HyperliquidExecutionService:
    def __init__(self,
                 wallet_address: str,
                 private_key: str,
                 api_url: Optional[str] = None, # Defaults to mainnet if None
                 network_mode: Literal["mainnet", "testnet"] = "mainnet"
                ):
        if not Exchange or not Info or not Account or not HL_CONSTANTS: # Check all required imports
            raise HyperliquidExecutionServiceError("Hyperliquid SDK or eth_account not installed/imported correctly.")

        self.private_key = private_key # Store for creating account object

        try:
            # Create an eth_account object from the private key
            # Account.enable_unaudited_hdwallet_features() # May not be needed for from_key
            self.account = Account.from_key(self.private_key)
        except Exception as e:
            logger.error(f"Invalid private key provided: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Invalid private key: {e}")

        self.wallet_address = self.account.address # Derive address from private key for consistency
        # Log a warning if provided wallet_address doesn't match the one from private_key
        if wallet_address.lower() != self.wallet_address.lower():
            logger.warning(
                f"Provided wallet_address {wallet_address} does not match address "
                f"derived from private_key {self.wallet_address}. Using derived address."
            )

        self.api_url = api_url or (HL_CONSTANTS.MAINNET_API_URL if network_mode == "mainnet" else HL_CONSTANTS.TESTNET_API_URL)

        try:
            self.info_client = Info(self.api_url, skip_ws=True)
            # The Hyperliquid SDK's Exchange class constructor takes an eth_account object as the first argument (the signer).
            self.exchange_client = Exchange(self.account, self.api_url)

            logger.info(f"HyperliquidExecutionService initialized for wallet {self.wallet_address} on {self.api_url}.")
            logger.info("Successfully initialized Hyperliquid Info and Exchange SDK clients.")
        except Exception as e:
            logger.error(f"Failed to initialize Hyperliquid SDK clients (Info or Exchange): {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"SDK Client Initialization error: {e}")

    async def get_user_state(self, user_address: str) -> Dict[str, Any]:
        """
        Fetches the full user state (balances, positions, etc.) from Hyperliquid.
        Note: The user_address here should match self.wallet_address for this service instance.
        """
        # Ensure the requested user_address matches the service's configured wallet address for consistency.
        # Or, allow fetching for any address if the info_client.user_state method is public and doesn't require signing for other users.
        # Typically, user_state is for the authenticated/configured user.
        if user_address.lower() != self.wallet_address.lower():
            logger.warning(f"Request for user_state of {user_address} but service is configured for {self.wallet_address}.")
            # Depending on policy, either raise error or proceed if info_client allows it.
            # For now, let's assume it's intended for the configured wallet.
            # raise HyperliquidExecutionServiceError("Cannot fetch user_state for a different address than configured.")

        logger.info(f"Fetching user state for address: {user_address}")
        if not self.info_client:
            raise HyperliquidExecutionServiceError("Hyperliquid Info client not initialized.")

        try:
            # The SDK's info.user_state() is a synchronous method.
            # To call it from an async method, run it in an executor.
            loop = asyncio.get_event_loop()
            user_state_data = await loop.run_in_executor(None, self.info_client.user_state, user_address)

            if user_state_data:
                logger.debug(f"Successfully fetched user state for {user_address}.")
                # The user_state_data is a complex dictionary.
                # For now, return it directly. Later, it can be mapped to Pydantic models (e.g., HyperliquidAccountSummary).
                return user_state_data
            else:
                logger.warning(f"No user state data returned for {user_address}.")
                return {} # Return empty dict if no data
        except Exception as e:
            logger.error(f"Error fetching user state for {user_address} from Hyperliquid: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Failed to fetch user state: {e}")

    # Placeholder for place_order, cancel_order, etc. - keep them raising NotImplementedError for now.
    async def place_order(self, order_params: HyperliquidPlaceOrderParams) -> HyperliquidOrderResponseData:
        """
        Places an order on Hyperliquid using the Exchange client.
        """
        logger.info(f"Placing Hyperliquid order for asset {order_params.asset}: Buy={order_params.is_buy}, Size={order_params.sz}, LimitPx={order_params.limit_px}, Type={order_params.order_type}")

        if not self.exchange_client:
            logger.error("Hyperliquid Exchange client not initialized. Cannot place order.")
            # This should ideally not happen if __init__ succeeded.
            # Consider if a more specific error or check is needed earlier.
            raise HyperliquidExecutionServiceError("Hyperliquid Exchange client not initialized.")

        try:
            # The Hyperliquid SDK's exchange.order method is synchronous.
            # Call it in an executor from this async service method.
            loop = asyncio.get_event_loop()

            # Ensure cloid is passed as str if SDK expects str, or UUID if it handles it.
            # SDK docs/examples show cloid as optional and can be UUID.
            cloid_to_pass = order_params.cloid if order_params.cloid else None

            # The HL SDK order() method takes:
            # (coin, is_buy, sz, limit_px, order_type_info, reduce_only=False, cloid=None)
            # So, need to pass reduce_only.

            # Corrected call to reflect typical SDK signature for order placement
            # The `order_type` field in `HyperliquidPlaceOrderParams` is already the `order_type_info` dict.
            # The `reduce_only` field is also in `HyperliquidPlaceOrderParams`.

            # The SDK's `order` method returns a dictionary like:
            # {'status': 'ok', 'response': {'type': 'order', 'data': {'statuses': [{'resting': {'oid': 12345}}, ...]}}}
            # or {'status': 'error', 'error': 'message'}
            # We need to parse this to fit HyperliquidOrderResponseData.

            sdk_response_dict = await loop.run_in_executor(
                None,
                lambda: self.exchange_client.order(
                    coin=order_params.asset,
                    is_buy=order_params.is_buy,
                    sz=order_params.sz,
                    limit_px=order_params.limit_px,
                    order_type_info=order_params.order_type, # This is the dict like {"limit": {"tif": "Gtc"}}
                    reduce_only=order_params.reduce_only,
                    cloid=cloid_to_pass
                )
            )

            logger.info(f"Hyperliquid SDK order response: {sdk_response_dict}")

            if isinstance(sdk_response_dict, dict) and sdk_response_dict.get("status") == "ok":
                response_data = sdk_response_dict.get("response", {}).get("data", {})
                statuses = response_data.get("statuses", [])
                if statuses and isinstance(statuses, list) and len(statuses) > 0:
                    # Assuming the first status is relevant for a single order placement.
                    # 'resting', 'filled', etc. are keys within the status dict.
                    first_status_info = statuses[0]
                    order_status_key = next(iter(first_status_info)) # e.g., "resting"
                    oid_info = first_status_info[order_status_key]

                    parsed_response = HyperliquidOrderResponseData(
                        status=order_status_key, # "resting", "filled", etc.
                        oid=oid_info.get("oid") if isinstance(oid_info, dict) else None,
                        order_type_info=order_params.order_type # Echo back the order type sent
                        # simulated_fills field is now removed/commented out from HyperliquidOrderResponseData
                    )
                    # --- SIMULATED FILL GENERATION REMOVED ---
                    logger.info(f"Order placed successfully on Hyperliquid. Status: {parsed_response.status}, OID: {parsed_response.oid}")
                    return parsed_response
                else:
                    logger.error(f"Hyperliquid order placement succeeded (status ok) but no status details found in response: {sdk_response_dict}")
                    raise HyperliquidExecutionServiceError("Order placement ok, but no status details in response.")
            elif isinstance(sdk_response_dict, dict) and sdk_response_dict.get("status") == "error":
                error_message = sdk_response_dict.get("error", "Unknown error from Hyperliquid.")
                logger.error(f"Hyperliquid API error on order placement: {error_message}")
                raise HyperliquidExecutionServiceError(f"Hyperliquid API error: {error_message}")
            else:
                logger.error(f"Unexpected response structure from Hyperliquid SDK on order placement: {sdk_response_dict}")
                raise HyperliquidExecutionServiceError("Unexpected response from Hyperliquid SDK.")

        except HyperliquidExecutionServiceError: # Re-raise our specific errors
            raise
        except Exception as e:
            logger.error(f"Error placing order on Hyperliquid for {order_params.asset}: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Failed to place order: {e}")

    async def cancel_order(self, asset: str, oid: int) -> Dict[str, Any]:
        """
        Cancels an open order on Hyperliquid.
        Args:
            asset: The asset symbol (e.g., "ETH").
            oid: The order ID (integer) to cancel.
        Returns:
            The response dictionary from the Hyperliquid SDK.
        """
        logger.info(f"Attempting to cancel Hyperliquid order OID {oid} for asset {asset}")
        if not self.exchange_client:
            raise HyperliquidExecutionServiceError("Hyperliquid Exchange client not initialized.")

        try:
            loop = asyncio.get_event_loop()
            # SDK's cancel method: cancel(coin: str, oid: int) -> Any
            sdk_response = await loop.run_in_executor(
                None,
                lambda: self.exchange_client.cancel(coin=asset, oid=oid)
            )

            logger.info(f"Hyperliquid SDK cancel_order response for OID {oid}: {sdk_response}")

            # The SDK's cancel typically returns a dict like:
            # {'status': 'ok', 'response': {'type': 'cancel', 'data': {'statuses': ['success']}}}
            # or {'status': 'error', 'error': 'reason'}
            if isinstance(sdk_response, dict) and "status" in sdk_response:
                if sdk_response["status"] == "ok":
                    logger.info(f"Order OID {oid} for asset {asset} canceled successfully on Hyperliquid.")
                else: # status == "error" or other
                    error_message = sdk_response.get("error", f"Cancellation failed with status: {sdk_response['status']}")
                    logger.error(f"Failed to cancel order OID {oid} on Hyperliquid: {error_message}")
                    # We could raise an error here or let the raw response pass through.
                    # For consistency, let's raise if status is not 'ok'.
                    raise HyperliquidExecutionServiceError(f"Hyperliquid API error on cancel: {error_message}")
                return sdk_response # Return the full SDK response dict
            else:
                logger.error(f"Unexpected response structure from Hyperliquid SDK on cancel_order for OID {oid}: {sdk_response}")
                raise HyperliquidExecutionServiceError("Unexpected response from Hyperliquid SDK on cancel.")

        except HyperliquidExecutionServiceError:
            raise
        except Exception as e:
            logger.error(f"Error canceling order OID {oid} for {asset} on Hyperliquid: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Failed to cancel order: {e}")

    async def get_order_status(self, user_address: str, oid: int) -> HyperliquidOrderStatusInfo:
        """
        Fetches the status of a specific order from Hyperliquid.
        Args:
            user_address: The user's wallet address.
            oid: The order ID (integer).
        Returns:
            A HyperliquidOrderStatusInfo Pydantic model.
        """
        # Ensure user_address matches self.wallet_address for consistency with other methods,
        # or if this method is intended for any user's order if public.
        # For now, assume it's for the configured service wallet or any if info_client allows.
        logger.info(f"Fetching order status for OID {oid}, user {user_address}")
        if not self.info_client:
            raise HyperliquidExecutionServiceError("Hyperliquid Info client not initialized.")

        try:
            loop = asyncio.get_event_loop()
            # SDK's info_client method: order_status(user: str, oid: int) -> Any
            # It returns a dict with 'order' object, 'status' string, 'fills' list.
            sdk_response = await loop.run_in_executor(
                None,
                lambda: self.info_client.order_status(user=user_address, oid=oid)
            )
            logger.debug(f"Hyperliquid SDK order_status response for OID {oid}: {str(sdk_response)[:500]}")

            if isinstance(sdk_response, dict) and "order" in sdk_response and "status" in sdk_response:
                # Map to HyperliquidOrderStatusInfo Pydantic model
                # The 'order' field itself is a dict, 'fills' is a list of dicts.
                order_status_info = HyperliquidOrderStatusInfo(
                    order=sdk_response.get("order", {}),
                    status=sdk_response.get("status", "unknown"),
                    fills=sdk_response.get("fills", [])
                )
                logger.info(f"Order status for OID {oid} successfully fetched: {order_status_info.status}")
                return order_status_info
            else:
                logger.error(f"Unexpected response structure from Hyperliquid SDK on get_order_status for OID {oid}: {sdk_response}")
                # Check if it's an error structure like {'error': 'Order not found'}
                if isinstance(sdk_response, dict) and "error" in sdk_response:
                     raise HyperliquidExecutionServiceError(f"Hyperliquid API error: {sdk_response['error']}")
                raise HyperliquidExecutionServiceError("Unexpected response structure for order status.")

        except HyperliquidExecutionServiceError:
            raise
        except Exception as e:
            logger.error(f"Error fetching order status for OID {oid} from Hyperliquid: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Failed to fetch order status: {e}")

    async def get_detailed_account_summary(self, user_address: str) -> Optional[HyperliquidAccountSnapshot]:
        """
        Fetches and parses the user's account state into a structured AccountSnapshot.
        """
        logger.info(f"Fetching detailed account summary for {user_address}")
        if user_address.lower() != self.wallet_address.lower():
            logger.warning(f"Request for account summary of {user_address} but service is for {self.wallet_address}.")
            # Potentially raise error or return None based on desired security/behavior for this method

        user_state_raw = await self.get_user_state(user_address)
        if not user_state_raw:
            logger.warning(f"No raw user state data returned for {user_address} to build account summary.")
            return None

        try:
            # --- Parse Positions ---
            parsed_positions: List[HyperliquidAssetPosition] = []
            raw_asset_contexts = user_state_raw.get("assetPositions")
            if isinstance(raw_asset_contexts, list):
                for asset_context in raw_asset_contexts:
                    if isinstance(asset_context, dict) and "position" in asset_context and isinstance(asset_context["position"], dict):
                        pos_data = asset_context["position"]
                        pos_data["asset"] = asset_context.get("asset")
                        if pos_data.get("szi") != "0": # Only include if size is not zero
                             parsed_positions.append(HyperliquidAssetPosition(**pos_data))

            # --- Parse Open Orders ---
            parsed_open_orders: List[HyperliquidOpenOrderItem] = []
            raw_open_orders = user_state_raw.get("openOrders")
            if isinstance(raw_open_orders, list):
                for order_data in raw_open_orders:
                    if isinstance(order_data, dict):
                        mapped_order_data = {
                            "oid": order_data.get("oid"),
                            "asset": order_data.get("coin"),
                            "side": order_data.get("side"),
                            "limit_px": order_data.get("limitPx"),
                            "sz": order_data.get("sz"),
                            "timestamp": order_data.get("timestamp"),
                            "raw_order_data": order_data
                        }
                        if all(mapped_order_data.get(k) is not None for k in ["oid", "asset", "side", "limit_px", "sz", "timestamp"]):
                            parsed_open_orders.append(HyperliquidOpenOrderItem(**mapped_order_data))
                        else:
                            logger.warning(f"Skipping open order due to missing fields: {order_data}")

            snapshot_timestamp_ms = user_state_raw.get("time", int(datetime.now(timezone.utc).timestamp() * 1000))
            margin_summary_data = user_state_raw.get("crossMarginSummary", {})
            if not margin_summary_data and "spotMarginSummary" in user_state_raw:
                margin_summary_data = user_state_raw.get("spotMarginSummary", {})

            account_snapshot = HyperliquidAccountSnapshot(
                time=snapshot_timestamp_ms,
                totalRawUsd=margin_summary_data.get("totalRawUsd", "0"),
                total_pnl_usd_str=margin_summary_data.get("totalNtlPos", "0"),
                parsed_positions=parsed_positions,
                parsed_open_orders=parsed_open_orders
            )

            logger.info(f"Successfully parsed account snapshot for {user_address}. Positions: {len(parsed_positions)}, Open Orders: {len(parsed_open_orders)}.")
            return account_snapshot

        except Exception as e:
            logger.error(f"Error parsing user_state for {user_address} into Pydantic models: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Failed to parse account snapshot: {e}")

    async def get_all_open_positions(self, user_address: str) -> List[HyperliquidAssetPosition]:
        """Fetches and returns all open positions for the user."""
        logger.info(f"Fetching all open positions for {user_address}")
        snapshot = await self.get_detailed_account_summary(user_address)
        if snapshot:
            return snapshot.parsed_positions
        return []

    async def get_all_open_orders(self, user_address: str) -> List[HyperliquidOpenOrderItem]:
        """Fetches and returns all open orders for the user."""
        logger.info(f"Fetching all open orders for {user_address}")
        snapshot = await self.get_detailed_account_summary(user_address)
        if snapshot:
            return snapshot.parsed_open_orders
        return []

    async def get_asset_contexts(self) -> List[Dict[str, Any]]:
        """Gets meta data for all actively traded assets."""
        logger.info("Attempting to fetch asset contexts (market metadata)...")
        if not self.info_client:
            logger.error("Hyperliquid Info client not initialized. Cannot fetch asset contexts.")
            # Return empty list or raise error, consistent with how other methods handle this.
            # Raising an error is appropriate as this is a prerequisite.
            raise HyperliquidExecutionServiceError("Hyperliquid Info client not initialized.")

        try:
            loop = asyncio.get_event_loop()
            # Call the synchronous self.info_client.meta() in an executor
            asset_contexts = await loop.run_in_executor(None, self.info_client.meta)

            # self.info_client.meta() is expected to return a list of asset context dicts.
            # It could be an empty list if there are no assets or if the API returns it that way.
            if isinstance(asset_contexts, list):
                logger.info(f"Successfully fetched {len(asset_contexts)} asset contexts from Hyperliquid.")
                return asset_contexts
            else:
                # This case handles unexpected return types from meta(), e.g. None or something else.
                logger.error(f"Unexpected data type received from info_client.meta(): {type(asset_contexts)}. Expected list.")
                # Return empty list to maintain type consistency for the method's return signature.
                return []
        except AttributeError as e: # Specifically catch if self.info_client was somehow None despite the check
            logger.error(f"AttributeError: self.info_client might be None or meta attribute missing. Error: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Info client attribute error: {e}")
        except Exception as e: # Catch other potential errors from the info_client.meta() call
            logger.error(f"Failed to fetch asset contexts from Hyperliquid due to an API/SDK error: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"API call to fetch asset contexts failed: {e}")

    async def get_funding_history(self, user_address: str, start_time: int, end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """Gets funding payment history for a user."""
        logger.info(f"Attempting to fetch funding history for {user_address} from timestamp {start_time} to {end_time if end_time else 'latest'}...")
        if not self.info_client:
            logger.error("Hyperliquid Info client not initialized. Cannot fetch funding history.")
            raise HyperliquidExecutionServiceError("Hyperliquid Info client not initialized.")

        try:
            # The SDK's info.funding_history() is a synchronous method.
            # To call it from an async method, run it in an executor.
            loop = asyncio.get_event_loop()
            funding_history_data = await loop.run_in_executor(
                None,
                lambda: self.info_client.funding_history(user_address, start_time, end_time)
            )

            # The SDK returns a list of funding payment dicts.
            # Example: [{'coin': 'BTC', 'time': 1672531200000, 'usdc': '-0.00123', ...}, ...]
            if isinstance(funding_history_data, list):
                logger.info(f"Successfully fetched {len(funding_history_data)} funding history entries for {user_address}.")
                return funding_history_data
            else:
                # This case might indicate an unexpected response type from the SDK.
                logger.warning(f"Received non-list data for funding history from Hyperliquid SDK: {type(funding_history_data)}. Expected list.")
                # Depending on strictness, could raise error or return empty list.
                # Returning empty list for now to maintain type consistency.
                return []
        except Exception as e:
            logger.error(f"Error fetching funding history for {user_address} from Hyperliquid: {e}", exc_info=True)
            # Specific error handling can be added here if certain exceptions from the SDK are known
            raise HyperliquidExecutionServiceError(f"Failed to fetch funding history: {e}")

    async def get_account_margin_summary(self) -> Optional[HyperliquidMarginSummary]:
        """
        Fetches the account's margin summary (cross or spot) for the service's wallet_address.
        """
        logger.info(f"Attempting to fetch account margin summary for {self.wallet_address}...")
        if not self.info_client:
            logger.error("Hyperliquid Info client not initialized. Cannot fetch margin summary.")
            raise HyperliquidExecutionServiceError("Hyperliquid Info client not initialized.")

        try:
            user_state_data = await self.get_user_state(self.wallet_address) # Uses run_in_executor internally
            if not user_state_data:
                logger.warning(f"No user state data returned for {self.wallet_address}, cannot extract margin summary.")
                return None

            margin_summary_raw = user_state_data.get("crossMarginSummary")
            if not margin_summary_raw:
                margin_summary_raw = user_state_data.get("spotMarginSummary") # Fallback to spot if cross is not present
                if margin_summary_raw:
                    logger.info(f"Using spotMarginSummary for {self.wallet_address}.")
                else:
                    logger.warning(f"No crossMarginSummary or spotMarginSummary found for {self.wallet_address} in user state.")
                    return None
            else:
                logger.info(f"Using crossMarginSummary for {self.wallet_address}.")


            # Ensure all required fields for HyperliquidMarginSummary are present or provide defaults
            # The Pydantic model HyperliquidMarginSummary expects:
            # account_value (alias="accountValue")
            # total_raw_usd (alias="totalRawUsd")
            # total_ntl_pos (alias="totalNtlPos")
            # total_margin_used (alias="totalMarginUsed")
            # Optional: total_pnl_on_positions, available_balance_for_new_orders

            # Basic check for essential fields
            required_fields = ["accountValue", "totalRawUsd", "totalNtlPos", "totalMarginUsed"]
            for field in required_fields:
                if field not in margin_summary_raw:
                    logger.error(f"Missing required field '{field}' in margin summary data: {margin_summary_raw}")
                    raise HyperliquidExecutionServiceError(f"Margin summary data is incomplete. Missing: {field}")

            margin_summary = HyperliquidMarginSummary(**margin_summary_raw)
            logger.info(f"Successfully fetched and parsed account margin summary for {self.wallet_address}.")
            return margin_summary

        except HyperliquidExecutionServiceError: # Re-raise our specific errors
            raise
        except Exception as e:
            logger.error(f"Error fetching or parsing account margin summary for {self.wallet_address}: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Failed to get account margin summary: {e}")

    async def get_asset_leverage(self, asset_symbol: str, user_address: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetches leverage settings for a specific asset for a given user_address.
        Defaults to self.wallet_address if user_address is not provided.
        """
        target_address = user_address if user_address else self.wallet_address
        logger.info(f"Attempting to fetch asset leverage for {asset_symbol} for user {target_address}...")

        if not self.info_client:
            logger.error("Hyperliquid Info client not initialized. Cannot fetch asset leverage.")
            raise HyperliquidExecutionServiceError("Hyperliquid Info client not initialized.")

        try:
            user_state_data = await self.get_user_state(target_address) # Uses run_in_executor internally
            if not user_state_data:
                logger.warning(f"No user state data returned for {target_address}, cannot extract asset leverage.")
                return None

            asset_positions = user_state_data.get("assetPositions")
            if not isinstance(asset_positions, list):
                logger.warning(f"No 'assetPositions' list found in user state for {target_address} or it's not a list.")
                return None

            for asset_pos_data in asset_positions:
                if isinstance(asset_pos_data, dict) and \
                   asset_pos_data.get("asset") == asset_symbol and \
                   "position" in asset_pos_data and \
                   isinstance(asset_pos_data["position"], dict):

                    position_details = asset_pos_data["position"]
                    leverage_info = position_details.get("leverage") # Leverage info is usually a dict itself

                    if leverage_info:
                        logger.info(f"Successfully fetched leverage for asset {asset_symbol} for user {target_address}: {leverage_info}")
                        # Example leverage_info: {"type": "cross", "value": 10} or {"type": "isolated", "value": 5}
                        return leverage_info
                    else:
                        logger.info(f"Asset {asset_symbol} found, but no leverage information present in position details for user {target_address}.")
                        return None # No specific leverage info for this asset

            logger.info(f"Asset {asset_symbol} not found in positions for user {target_address}.")
            return None # Asset not found in positions

        except HyperliquidExecutionServiceError: # Re-raise our specific errors
            raise
        except Exception as e:
            logger.error(f"Error fetching asset leverage for {asset_symbol} (user {target_address}): {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Failed to get asset leverage: {e}")

    async def set_asset_leverage(self, asset_symbol: str, leverage: int, is_cross_margin: bool) -> Dict[str, Any]:
        """
        Sets the leverage for a given asset.
        Args:
            asset_symbol: The asset symbol (e.g., "ETH").
            leverage: The desired leverage value (integer).
            is_cross_margin: True for cross-margin, False for isolated.
        Returns:
            A dictionary representing the outcome from the Hyperliquid SDK.
        """
        logger.info(f"Attempting to set leverage for asset {asset_symbol} to {leverage}x {'cross-margin' if is_cross_margin else 'isolated-margin'}...")

        if not self.exchange_client:
            logger.error("Hyperliquid Exchange client not initialized. Cannot set leverage.")
            raise HyperliquidExecutionServiceError("Hyperliquid Exchange client not initialized.")

        if not isinstance(leverage, int) or leverage < 1: # Basic validation
            logger.error(f"Invalid leverage value: {leverage}. Must be a positive integer.")
            raise HyperliquidExecutionServiceError("Invalid leverage value provided.")

        try:
            loop = asyncio.get_event_loop()
            # SDK's update_leverage: update_leverage(coin: str, is_cross_margin: bool, leverage: int)
            sdk_response = await loop.run_in_executor(
                None,
                lambda: self.exchange_client.update_leverage(
                    coin=asset_symbol,
                    is_cross_margin=is_cross_margin,
                    leverage=leverage
                )
            )

            logger.info(f"Hyperliquid SDK set_asset_leverage response for {asset_symbol}: {sdk_response}")

            # Example success: {'status': 'ok', 'response': {'type': 'updateLeverage', 'data': 'Successfully updated margin'}}
            # Example error: {'status': 'error', 'error': 'Leverage too high'}
            if isinstance(sdk_response, dict) and "status" in sdk_response:
                if sdk_response["status"] == "ok":
                    data_field = sdk_response.get("response", {}).get("data")
                    if isinstance(data_field, list) and len(data_field) > 0 and isinstance(data_field[0], dict) and "name" in data_field[0] and "cross" in data_field[0] and "leverage" in data_field[0]:
                        # This seems to be the new response structure as of some SDK versions
                        # e.g. [{'name': 'ETH', 'cross': True, 'leverage': 20}]
                        logger.info(f"Leverage for {asset_symbol} successfully updated to {data_field[0]['leverage']}x, cross_margin={data_field[0]['cross']}.")
                    elif isinstance(data_field, str): # Older response style
                         logger.info(f"Leverage for {asset_symbol} successfully updated. Message: {data_field}")
                    else: # Other potential success structures
                        logger.info(f"Leverage for {asset_symbol} update reported as 'ok', but data format is unexpected: {data_field}")
                else: # status == "error"
                    error_message = sdk_response.get("error", f"Leverage update failed with status: {sdk_response['status']}")
                    logger.error(f"Failed to set leverage for {asset_symbol} on Hyperliquid: {error_message}")
                    raise HyperliquidExecutionServiceError(f"Hyperliquid API error on set_leverage: {error_message}")
                return sdk_response # Return the full SDK response dict
            else:
                logger.error(f"Unexpected response structure from Hyperliquid SDK on set_asset_leverage for {asset_symbol}: {sdk_response}")
                raise HyperliquidExecutionServiceError("Unexpected response from Hyperliquid SDK on set_leverage.")

        except HyperliquidExecutionServiceError: # Re-raise our specific errors
            raise
        except Exception as e:
            logger.error(f"Error setting leverage for {asset_symbol}: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Failed to set asset leverage: {e}")

    # Add other methods as needed: get_balance, get_leverage, modify_leverage, etc.
    # Remember to handle Hyperliquid's specific data types (e.g. numbers as strings)
    # and ensure all private_key interactions are secure and through the SDK's intended mechanisms.
    # The Exchange client setup is critical for any methods that modify state (place/cancel orders, set leverage).

    async def get_fills_for_order(self, user_address: str, oid: int) -> List[Dict[str, Any]]:
        logger.info(f"HLES: Fetching fills for order OID {oid}, user {user_address}")
        if not self.info_client:
            logger.error("HLES: Hyperliquid Info client not initialized. Cannot fetch fills.")
            # Consider raising an error or make behavior consistent with other methods
            return []
            # raise HyperliquidExecutionServiceError("Hyperliquid Info client not initialized.")

        try:
            loop = asyncio.get_event_loop()
            # SDK's info_client method: order_status(user: str, oid: int) -> Any
            # It returns a dict with 'order' object, 'status' string, 'fills' list.
            sdk_response = await loop.run_in_executor(
                None,
                lambda: self.info_client.order_status(user=user_address, oid=oid)
            )
            # logger.debug(f"HLES: Order status response for OID {oid} (for fills): {str(sdk_response)[:500]}")

            if isinstance(sdk_response, dict) and "fills" in sdk_response:
                fills = sdk_response.get("fills")
                if isinstance(fills, list):
                    logger.info(f"HLES: Found {len(fills)} fills for order OID {oid}.")
                    return fills
                else:
                    logger.warning(f"HLES: 'fills' field in order_status response is not a list for OID {oid}. Type: {type(fills)}")
                    return []
            elif isinstance(sdk_response, dict) and "error" in sdk_response: # Check for API error response
                logger.warning(f"HLES: API error when fetching order status for fills (OID {oid}): {sdk_response['error']}")
                return []
            else:
                logger.warning(f"HLES: Unexpected response structure or no fills found for OID {oid} when fetching order status: {sdk_response}")
                return []
        except Exception as e:
            logger.error(f"HLES: Error fetching fills for order OID {oid}: {e}", exc_info=True)
            raise HyperliquidExecutionServiceError(f"Failed to fetch fills for order {oid}: {e}")
