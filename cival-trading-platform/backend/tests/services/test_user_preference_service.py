import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from python_ai_services.services.user_preference_service import UserPreferenceService, UserPreferenceServiceError
from python_ai_services.models.user_models import UserPreferences

@pytest_asyncio.fixture
async def mock_supabase_client_ups(): # ups for UserPreferenceService
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock()
    client.table.return_value.upsert.return_value.select.return_value.execute = AsyncMock() # Corrected: select() is typically called after upsert for returning data
    return client

@pytest_asyncio.fixture
async def user_preference_service(mock_supabase_client_ups: MagicMock):
    return UserPreferenceService(supabase_client=mock_supabase_client_ups)

@pytest.mark.asyncio
async def test_get_user_preferences_found(user_preference_service: UserPreferenceService, mock_supabase_client_ups: MagicMock):
    user_id = uuid.uuid4()
    db_data = {"user_id": str(user_id), "preferences": {"theme": "dark"}, "last_updated_at": datetime.now(timezone.utc).isoformat()}
    # Simulate the structure of the Supabase response object
    mock_supabase_client_ups.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=db_data, error=None)

    prefs = await user_preference_service.get_user_preferences(user_id)

    assert isinstance(prefs, UserPreferences)
    assert prefs.user_id == user_id
    assert prefs.preferences == {"theme": "dark"}
    mock_supabase_client_ups.table.return_value.select.return_value.eq.assert_called_once_with("user_id", str(user_id))

@pytest.mark.asyncio
async def test_get_user_preferences_not_found_returns_default(user_preference_service: UserPreferenceService, mock_supabase_client_ups: MagicMock):
    user_id = uuid.uuid4()
    # Simulate Supabase returning no data
    mock_supabase_client_ups.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None, error=None)

    prefs = await user_preference_service.get_user_preferences(user_id)

    assert isinstance(prefs, UserPreferences)
    assert prefs.user_id == user_id
    assert prefs.preferences == {} # Default empty dict
    assert isinstance(prefs.last_updated_at, datetime) # Check default last_updated_at

@pytest.mark.asyncio
async def test_update_user_preferences_success(user_preference_service: UserPreferenceService, mock_supabase_client_ups: MagicMock):
    user_id = uuid.uuid4()
    new_prefs_payload = {"notifications": {"email": True}}

    # Mock the return value of upsert().select().execute()
    # The actual Supabase client returns a list of dictionaries in the 'data' attribute of the response object
    db_return_data = {"user_id": str(user_id), "preferences": new_prefs_payload, "last_updated_at": datetime.now(timezone.utc).isoformat()}
    mock_supabase_client_ups.table.return_value.upsert.return_value.select.return_value.execute.return_value = MagicMock(data=[db_return_data], error=None)

    updated_prefs = await user_preference_service.update_user_preferences(user_id, new_prefs_payload)

    assert isinstance(updated_prefs, UserPreferences)
    assert updated_prefs.user_id == user_id
    assert updated_prefs.preferences == new_prefs_payload

    # Check the payload sent to upsert
    # The first argument to call_args is a tuple of positional arguments
    called_with_payload = mock_supabase_client_ups.table.return_value.upsert.call_args[0][0]
    assert called_with_payload["user_id"] == str(user_id)
    assert called_with_payload["preferences"] == new_prefs_payload
    assert "last_updated_at" in called_with_payload
    # Ensure last_updated_at is a datetime string
    assert isinstance(datetime.fromisoformat(called_with_payload["last_updated_at"].replace("Z", "+00:00")), datetime)

    mock_supabase_client_ups.table.return_value.upsert.assert_called_once_with(
        called_with_payload,
        on_conflict="user_id"
    )
    # Verify that select() was called after upsert, as per Supabase-py behavior for returning data
    mock_supabase_client_ups.table.return_value.upsert.return_value.select.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_preferences_db_error(user_preference_service: UserPreferenceService, mock_supabase_client_ups: MagicMock):
    user_id = uuid.uuid4()
    new_prefs_payload = {"theme": "light"}

    # Simulate a Supabase error response
    mock_error_response = MagicMock()
    mock_error_response.message = "DB upsert failed" # This matches what Supabase error objects might have
    mock_supabase_client_ups.table.return_value.upsert.return_value.select.return_value.execute.return_value = MagicMock(data=None, error=mock_error_response)

    with pytest.raises(UserPreferenceServiceError, match="Failed to upsert preferences: DB upsert failed"):
        await user_preference_service.update_user_preferences(user_id, new_prefs_payload)

@pytest.mark.asyncio
async def test_update_user_preferences_no_data_returned(user_preference_service: UserPreferenceService, mock_supabase_client_ups: MagicMock):
    user_id = uuid.uuid4()
    new_prefs_payload = {"theme": "blue"}
    # Simulate Supabase returning no data and no error (should not happen with SELECT after UPSERT if successful)
    mock_supabase_client_ups.table.return_value.upsert.return_value.select.return_value.execute.return_value = MagicMock(data=[], error=None) # Empty list

    with pytest.raises(UserPreferenceServiceError, match="No data returned after upsert operation."):
        await user_preference_service.update_user_preferences(user_id, new_prefs_payload)
