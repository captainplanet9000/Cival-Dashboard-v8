import os
import uuid
from datetime import datetime, timezone # Ensure timezone is imported
from typing import Optional, Dict, Any, List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import ValidationError # For validating AuthenticatedUser model

# Assuming AuthenticatedUser is importable from models.auth_models
# Adjust path if necessary based on actual project structure.
from ..models.auth_models import AuthenticatedUser # This should work given the directory structure
from logging import getLogger

logger = getLogger(__name__)

# --- Configuration (should come from environment variables) ---
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
ALGORITHM = "HS256" # Supabase typically uses HS256 for signed JWTs
EXPECTED_AUDIENCE = "authenticated" # Default Supabase audience for JWTs
# Expected issuer, e.g., https://<your-ref>.supabase.co/auth/v1
EXPECTED_ISSUER = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else None


# Reusable HTTPBearer scheme
oauth2_scheme = HTTPBearer()

async def get_current_active_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
) -> AuthenticatedUser:
    """
    FastAPI dependency to get the current active user from a Supabase JWT.
    Validates the token and extracts user information.
    """
    if SUPABASE_JWT_SECRET is None:
        logger.error("SUPABASE_JWT_SECRET is not configured. Cannot validate JWTs.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # 503 more appropriate for config issue
            detail="Authentication system not configured (missing JWT secret)."
        )
    if EXPECTED_ISSUER is None:
        logger.error("SUPABASE_URL is not configured. Cannot validate JWT issuer.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication system not configured (missing Supabase URL for issuer validation)."
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data_unverified = token.credentials

    try:
        payload = jwt.decode(
            token_data_unverified,
            SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            audience=EXPECTED_AUDIENCE,
            issuer=EXPECTED_ISSUER
        )

        user_id_str: Optional[str] = payload.get("sub")
        email_str: Optional[str] = payload.get("email")
        # exp_timestamp: Optional[int] = payload.get("exp") # Handled by jwt.decode

        if user_id_str is None: # 'exp' is automatically checked by jwt.decode
            logger.warning("JWT missing 'sub' (subject) claim.")
            raise credentials_exception

        app_metadata: Dict[str, Any] = payload.get("app_metadata", {}) # Default to empty dict
        user_roles: List[str] = app_metadata.get("roles", [])

        user_data_for_model = {
            "id": uuid.UUID(user_id_str),
            "email": email_str,
            "roles": user_roles
        }
        authenticated_user = AuthenticatedUser(**user_data_for_model)

        logger.info(f"User {authenticated_user.id} authenticated successfully. Roles: {authenticated_user.roles}")
        return authenticated_user

    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        raise credentials_exception from e
    except ValidationError as e:
        logger.warning(f"AuthenticatedUser model validation error after JWT parsing: {e}")
        # This could be a 500 if the token structure is unexpectedly wrong despite passing JWT validation
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid user data structure in token.", # Avoid leaking detailed validation errors to client
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}", exc_info=True)
        raise credentials_exception from e

