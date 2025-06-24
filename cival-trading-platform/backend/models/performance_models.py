from pydantic import BaseModel, Field
from typing import Optional, List # List not used here but often is in models
from datetime import datetime, timezone # Added timezone for utcnow

class PerformanceMetrics(BaseModel):
    agent_id: str
    calculation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_start_time: Optional[datetime] = None # Earliest trade timestamp used
    data_end_time: Optional[datetime] = None # Latest trade timestamp used

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    neutral_trades: int = 0 # Trades with PnL around zero

    win_rate: Optional[float] = None
    loss_rate: Optional[float] = None

    total_net_pnl: float = 0.0
    gross_profit: Optional[float] = None # Sum of all positive PnLs
    gross_loss: Optional[float] = None # Sum of absolute values of all negative PnLs (stored as positive)

    average_win_amount: Optional[float] = None
    average_loss_amount: Optional[float] = None

    profit_factor: Optional[float] = None # gross_profit / abs(gross_loss)

    max_drawdown_percentage: Optional[float] = Field(default=None, description="Maximum drawdown percentage from a peak to a subsequent trough in equity.")
    annualized_sharpe_ratio: Optional[float] = Field(default=None, description="Annualized Sharpe ratio, assuming a risk-free rate of 0 and daily periodic returns.")

    # Add new fields:
    compounding_annual_return_percentage: Optional[float] = Field(default=None, description="Compounding Annual Return (CAGR) percentage.")
    annualized_volatility_percentage: Optional[float] = Field(default=None, description="Annualized volatility (standard deviation of returns) percentage.")

    notes: Optional[str] = None

    class Config:
        # For Pydantic v2, use this to allow default_factory with timezone
        # For Pydantic v1, ensure datetime.utcnow is timezone-naive or handle timezone explicitly if needed elsewhere
        # The lambda with datetime.now(timezone.utc) is generally robust.
        pass
