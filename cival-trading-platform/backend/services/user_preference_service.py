import uuid
from typing import Dict, Any, Optional
from supabase import Client as SupabaseClient
from datetime import datetime, timezone
from logging import getLogger

# Assuming UserPreferences model is importable
from ..models.user_models import UserPreferences

logger = getLogger(__name__)

class UserPreferenceServiceError(Exception):
    """Base exception for UserPreferenceService errors."""
    pass

class UserPreferenceService:
    TABLE_NAME = "user_preferences"

    def __init__(self, supabase_client: SupabaseClient):
        self.supabase = supabase_client
        logger.info("UserPreferenceService initialized.")

    async def get_user_preferences(self, user_id: uuid.UUID) -> UserPreferences:
        """
        Retrieves preferences for a specific user.
        If no preferences exist for the user, returns a UserPreferences object
        with default values (empty preferences dict, current timestamp).
        """
        logger.debug(f"Fetching preferences for user ID {user_id}")
        try:
            response = await self.supabase.table(self.TABLE_NAME) \
                .select("*") \
                .eq("user_id", str(user_id)) \
                .maybe_single() \
                .execute()

            if response.data:
                return UserPreferences(**response.data)
            else:
                # No preferences found, return default structure
                logger.info(f"No preferences found for user {user_id}, returning default.")
                # Ensure the default UserPreferences instance has its last_updated_at set,
                # which the default_factory in the model should handle.
                return UserPreferences(user_id=user_id)
        except Exception as e:
            logger.error(f"Database error fetching preferences for user {user_id}: {e}", exc_info=True)
            raise UserPreferenceServiceError(f"Database error fetching preferences: {str(e)}")

    async def update_user_preferences(self, user_id: uuid.UUID, preferences_payload: Dict[str, Any]) -> UserPreferences:
        """
        Updates (or creates if not exists) the preferences for a specific user.
        The preferences_payload is the dictionary that will become the 'preferences' JSONB field.
        """
        logger.info(f"Updating preferences for user ID {user_id}")

        now_utc = datetime.now(timezone.utc)
        record_to_upsert = {
            "user_id": str(user_id),
            "preferences": preferences_payload,
            "last_updated_at": now_utc.isoformat()
        }

        try:
            response = await self.supabase.table(self.TABLE_NAME) \
                .upsert(record_to_upsert, on_conflict="user_id") \
                .select("*") \
                .execute()

            if response.data and len(response.data) > 0:
                logger.info(f"Preferences updated successfully for user {user_id}")
                # The response.data[0] should already have the correct last_updated_at from the DB
                # if the DB column has a default or on update trigger.
                # If not, the value we sent in record_to_upsert is used.
                return UserPreferences(**response.data[0])
            else:
                # This path might be hit if upsert fails subtly or if RLS prevents returning the row.
                # Check for a specific error from Supabase if possible.
                err_msg = getattr(response.error, 'message', "Upsert operation returned no data or error object") if response.error else "Upsert operation returned no data"
                logger.error(f"Failed to upsert preferences for user {user_id}. Response error: {err_msg}, Response data: {response.data}")
                # Attempt to re-fetch to confirm state, or rely on error.
                # For now, raising an error is safer if data isn't returned as expected.
                # If an insert happened but select didn't return, it's an inconsistent state from client's POV.
                raise UserPreferenceServiceError(f"Failed to upsert preferences: {err_msg}")
        except Exception as e:
            logger.error(f"Database error updating preferences for user {user_id}: {e}", exc_info=True)
            if isinstance(e, UserPreferenceServiceError): # Re-raise if it's already our specific error
                raise
            raise UserPreferenceServiceError(f"Database error updating preferences: {str(e)}")
