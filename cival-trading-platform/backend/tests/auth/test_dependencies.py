import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status, Depends # For Depends in test signature
from fastapi.security import HTTPAuthorizationCredentials

# Module to test
from python_ai_services.auth.dependencies import get_current_active_user, oauth2_scheme
from python_ai_services.models.auth_models import AuthenticatedUser
from jose import jwt, JWTError # For simulating JWT errors

# --- Constants for Testing ---
TEST_SUPABASE_JWT_SECRET = "test_secret_key_for_jwt_validation_longer_than_32_chars"
TEST_SUPABASE_URL = "https://testref.supabase.co"
TEST_ALGORITHM = "HS256"
TEST_EXPECTED_AUDIENCE = "authenticated"
TEST_EXPECTED_ISSUER = f"{TEST_SUPABASE_URL}/auth/v1"

# Helper to create a token (not used in current tests but useful for future)
# def create_test_token(payload: dict, secret: str = TEST_SUPABASE_JWT_SECRET, algorithm: str = TEST_ALGORITHM) -> str:
#    return jwt.encode(payload, secret, algorithm=algorithm)

# --- Tests for get_current_active_user ---

@pytest.mark.asyncio
@patch('python_ai_services.auth.dependencies.os.getenv')
@patch('python_ai_services.auth.dependencies.jwt.decode')
async def test_get_current_active_user_success(mock_jwt_decode: MagicMock, mock_os_getenv: MagicMock):
    # Arrange
    # Ensure SUPABASE_URL is also patched for EXPECTED_ISSUER to be non-None
    def os_getenv_side_effect(key):
        if key == "SUPABASE_JWT_SECRET":
            return TEST_SUPABASE_JWT_SECRET
        if key == "SUPABASE_URL":
            return TEST_SUPABASE_URL
        return None
    mock_os_getenv.side_effect = os_getenv_side_effect

    # Must re-evaluate EXPECTED_ISSUER inside the test or ensure module is reloaded if it's top-level
    # For simplicity, we can assume the dependency function re-evaluates it or it's correctly patched.
    # The dependency function itself constructs EXPECTED_ISSUER from the mocked os.getenv("SUPABASE_URL").

    user_id = uuid.uuid4()
    email = "test@example.com"
    roles = ["user", "editor"]

    decoded_payload = {
        "sub": str(user_id),
        "email": email,
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(), # exp should be int timestamp
        "aud": TEST_EXPECTED_AUDIENCE,
        "iss": TEST_EXPECTED_ISSUER, # This needs to match what the dependency calculates
        "app_metadata": {"roles": roles}
    }
    mock_jwt_decode.return_value = decoded_payload

    mock_auth_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dummy_token_string")

    # Act
    # Need to properly patch the constants if they are defined at module level and used by get_current_active_user
    # The get_current_active_user function re-fetches env vars or uses module-level constants.
    # Patching os.getenv should cover it if the constants are re-evaluated or function uses getenv directly.
    # The current dependency code defines SUPABASE_JWT_SECRET, SUPABASE_URL, EXPECTED_ISSUER at module level.
    # To make os.getenv effective for them, we need to patch where they are defined or reload the module.
    # A simpler way for testing is to ensure the dependency directly calls os.getenv for these values, which it does.

    current_user = await get_current_active_user(token=mock_auth_creds)

    # Assert
    assert isinstance(current_user, AuthenticatedUser)
    assert current_user.id == user_id
    assert current_user.email == email
    assert current_user.roles == roles
    mock_jwt_decode.assert_called_once_with(
        "dummy_token_string", TEST_SUPABASE_JWT_SECRET, algorithms=[TEST_ALGORITHM],
        audience=TEST_EXPECTED_AUDIENCE, issuer=TEST_EXPECTED_ISSUER
    )

@pytest.mark.asyncio
@patch('python_ai_services.auth.dependencies.os.getenv')
async def test_get_current_active_user_missing_jwt_secret(mock_os_getenv: MagicMock):
    mock_os_getenv.side_effect = lambda key: None if key == "SUPABASE_JWT_SECRET" else (TEST_SUPABASE_URL if key == "SUPABASE_URL" else "other_value")
    mock_auth_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dummy")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(token=mock_auth_creds)
    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "missing jwt secret" in exc_info.value.detail.lower()

@pytest.mark.asyncio
@patch('python_ai_services.auth.dependencies.os.getenv')
async def test_get_current_active_user_missing_supabase_url(mock_os_getenv: MagicMock):
    mock_os_getenv.side_effect = lambda key: TEST_SUPABASE_JWT_SECRET if key == "SUPABASE_JWT_SECRET" else (None if key == "SUPABASE_URL" else "other_value")
    mock_auth_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="dummy")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(token=mock_auth_creds)
    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "missing supabase url" in exc_info.value.detail.lower()


@pytest.mark.asyncio
@patch('python_ai_services.auth.dependencies.os.getenv')
@patch('python_ai_services.auth.dependencies.jwt.decode')
async def test_get_current_active_user_jwt_error_expired(mock_jwt_decode: MagicMock, mock_os_getenv: MagicMock):
    mock_os_getenv.side_effect = lambda key: TEST_SUPABASE_JWT_SECRET if key == "SUPABASE_JWT_SECRET" else (TEST_SUPABASE_URL if key == "SUPABASE_URL" else None)
    mock_jwt_decode.side_effect = JWTError("Signature has expired.")
    mock_auth_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired_token")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(token=mock_auth_creds)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Could not validate credentials"

@pytest.mark.asyncio
@patch('python_ai_services.auth.dependencies.os.getenv')
@patch('python_ai_services.auth.dependencies.jwt.decode')
async def test_get_current_active_user_missing_sub_claim(mock_jwt_decode: MagicMock, mock_os_getenv: MagicMock):
    mock_os_getenv.side_effect = lambda key: TEST_SUPABASE_JWT_SECRET if key == "SUPABASE_JWT_SECRET" else (TEST_SUPABASE_URL if key == "SUPABASE_URL" else None)
    decoded_payload_no_sub = {"email": "user@example.com", "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()}
    mock_jwt_decode.return_value = decoded_payload_no_sub
    mock_auth_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_no_sub")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(token=mock_auth_creds)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
@patch('python_ai_services.auth.dependencies.os.getenv')
@patch('python_ai_services.auth.dependencies.jwt.decode')
async def test_get_current_active_user_pydantic_validation_error(mock_jwt_decode: MagicMock, mock_os_getenv: MagicMock):
    mock_os_getenv.side_effect = lambda key: TEST_SUPABASE_JWT_SECRET if key == "SUPABASE_JWT_SECRET" else (TEST_SUPABASE_URL if key == "SUPABASE_URL" else None)

    invalid_user_id_payload = {
        "sub": "not-a-uuid",
        "email": "test@example.com",
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        "aud": TEST_EXPECTED_AUDIENCE,
        "iss": TEST_EXPECTED_ISSUER,
        "app_metadata": {"roles": ["user"]}
    }
    mock_jwt_decode.return_value = invalid_user_id_payload
    mock_auth_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_bad_sub_format")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(token=mock_auth_creds)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid user data structure in token" in exc_info.value.detail
