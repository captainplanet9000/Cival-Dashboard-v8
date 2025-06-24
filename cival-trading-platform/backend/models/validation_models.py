from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date, timezone
import uuid

# Assuming PerformanceMetrics is importable if it's to be embedded directly
# For now, we'll make metrics_validated a Dict to avoid direct dependency in this file,
# or assume it can be imported. Let's try importing for better typing.
try:
    from .strategy_models import PerformanceMetrics
except ImportError:
    # This is a fallback type. If PerformanceMetrics is not found,
    # validated_metrics_summary will be a Dict.
    # In a well-structured project, this import should succeed.
    PerformanceMetrics = Dict[str, Any]

ValidationStatus = Literal["PASS", "FAIL", "WARN", "NOT_APPLICABLE", "PENDING"]

class ValidationCheckResult(BaseModel):
    check_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    check_name: str = Field(..., description="Name of the validation check performed (e.g., 'P&L Consistency', 'Sharpe Ratio Plausibility').")
    status: ValidationStatus = Field(default="PENDING", description="Outcome of the validation check.")
    expected_value_or_range: Optional[str] = Field(default=None, description="The expected value or range for this check (as a string for flexibility).")
    actual_value: Optional[str] = Field(default=None, description="The actual value observed (as a string).")
    message: Optional[str] = Field(default=None, description="Details or notes about the validation check outcome.")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional structured data for the check.")

class ValidationReport(BaseModel):
    report_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for this validation report.")
    strategy_config_id: uuid.UUID = Field(..., description="ID of the StrategyConfig that was backtested.")

    strategy_name: str = Field(..., description="Name of the strategy validated.")
    symbol: str = Field(..., description="Symbol on which the strategy was validated.")
    period_start_date: date = Field(..., description="Start date of the backtest period.")
    period_end_date: date = Field(..., description="End date of the backtest period.")

    # Store a summary or the full metrics that were validated.
    validated_metrics_summary: PerformanceMetrics | Dict[str, Any] = Field(..., description="The performance metrics snapshot that was subjected to validation.")

    validation_checks: List[ValidationCheckResult] = Field(default_factory=list, description="List of individual validation checks performed.")

    overall_validation_status: ValidationStatus = Field(default="PENDING", description="Overall outcome of the validation for this backtest run.")
    report_generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when this validation report was generated.")
    notes: Optional[str] = Field(default=None, description="Overall notes or summary for this validation report.")

    class Config:
        from_attributes = True
        validate_assignment = True
        extra = 'forbid'
