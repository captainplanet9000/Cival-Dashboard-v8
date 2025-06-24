from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Any
import uuid

class AuthenticatedUser(BaseModel):
    """
    Represents user data extracted from a validated JWT.
    Fields are typically derived from standard JWT claims like 'sub', 'email',
    and custom claims often found in app_metadata or user_metadata for roles.
    """
    id: uuid.UUID = Field(..., description="User ID, typically from the JWT 'sub' (subject) claim.")
    email: Optional[EmailStr] = Field(default=None, description="User's email address, if available in the token.")

    # Roles can be a list of strings. Supabase often stores roles in app_metadata.roles.
    roles: List[str] = Field(default_factory=list, description="List of roles assigned to the user.")

    # You can add other fields that might be present in your JWT claims,
    # e.g., username, full_name, specific permissions, etc.
    # For Supabase, custom data might be in 'user_metadata' or 'app_metadata' claims.
    # For example, if 'app_metadata' contains a 'organization_id':
    # app_metadata: Optional[Dict[str, Any]] = Field(default=None) # Dict needs to be imported if used
    # user_metadata: Optional[Dict[str, Any]] = Field(default=None) # Dict needs to be imported if used

    class Config:
        from_attributes = True
        validate_assignment = True
        extra = 'ignore'

# Example (conceptual, not part of file):
# from typing import Dict # Needed for this example if app_metadata/user_metadata were Dicts
# user_data_from_token = {
#     "sub": "123e4567-e89b-12d3-a456-426614174000", # Standard 'sub' claim for user ID
#     "email": "user@example.com",
#     "app_metadata": {
#         "roles": ["user", "editor"]
#     }
# }
# authenticated_user = AuthenticatedUser(
#     id=user_data_from_token['sub'],
#     email=user_data_from_token.get('email'),
#     roles=user_data_from_token.get('app_metadata', {}).get('roles', [])
# )
# print(authenticated_user.model_dump_json(indent=2))
