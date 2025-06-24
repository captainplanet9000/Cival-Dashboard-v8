from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime, timezone
import uuid

class AlertCondition(BaseModel):
    metric: Literal[
        "account_value_usd",
        "total_pnl_usd",
        "open_position_unrealized_pnl",
        "available_balance_usd",
        "margin_used_usd"
    ]
    operator: Literal["<", "<=", ">", ">=", "=="]
    threshold: float
    asset_symbol: Optional[str] = None # Required if metric is open_position_unrealized_pnl

    @validator('asset_symbol', always=True)
    def asset_symbol_required_for_position_metric(cls, v, values):
        if values.get('metric') == "open_position_unrealized_pnl" and v is None:
            raise ValueError("asset_symbol is required for 'open_position_unrealized_pnl' metric")
        return v

class AlertConfigBase(BaseModel):
    name: str
    conditions: List[AlertCondition] # Assumed AND logic for multiple conditions
    notification_channels: List[Literal["log", "email_placeholder", "webhook_placeholder"]]
    target_email: Optional[str] = None
    target_webhook_url: Optional[str] = None
    is_enabled: bool = True
    cooldown_seconds: int = 300 # Min seconds before re-triggering same alert

    @validator('target_email', always=True)
    def email_required_for_email_channel(cls, v, values):
        if "email_placeholder" in values.get('notification_channels', []) and v is None:
            raise ValueError("target_email is required if 'email_placeholder' is in notification_channels")
        return v

    @validator('target_webhook_url', always=True)
    def webhook_url_required_for_webhook_channel(cls, v, values):
        if "webhook_placeholder" in values.get('notification_channels', []) and v is None:
            raise ValueError("target_webhook_url is required if 'webhook_placeholder' is in notification_channels")
        return v

class AlertConfigInput(AlertConfigBase):
    pass

class AlertConfigOutput(AlertConfigBase):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str # To be set by service based on path param
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AlertNotification(BaseModel):
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alert_id: str
    alert_name: str
    agent_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str
    triggered_conditions_details: List[Dict[str, Any]] # e.g. {"metric": "account_value_usd", "operator": "<", "threshold": 1000, "current_value": 950}
