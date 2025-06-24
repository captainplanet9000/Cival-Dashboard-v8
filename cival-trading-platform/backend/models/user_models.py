from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone

class UserPreferences(BaseModel):
    """
    Represents user-specific application preferences.
    The 'preferences' field is a flexible JSONB store for various settings.
    """
    user_id: uuid.UUID = Field(..., description="The user ID these preferences belong to. This will be the primary key.")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="A dictionary holding various user preferences, e.g., theme, notification settings, default filters.")
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the last update to preferences.")

    class Config:
        from_attributes = True
        validate_assignment = True
        # extra = 'forbid' # Default is 'ignore' for Pydantic v2 if not set.
                         # 'forbid' would prevent any fields not explicitly defined here.
                         # Since 'preferences' is a Dict[str, Any], 'forbid' on the main model
                         # primarily affects top-level fields, not the contents of the dict itself
                         # unless a more specific model is used for the dict's value type.
                         # For a generic preferences JSONB, current config is fine.
