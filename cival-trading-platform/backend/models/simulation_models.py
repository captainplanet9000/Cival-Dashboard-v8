from pydantic import BaseModel, Field, root_validator
from typing import List, Dict, Any, Optional, Literal # Added Literal
from datetime import datetime
from ..models.agent_models import AgentConfigOutput # For agent_config_snapshot

class BacktestRequest(BaseModel):
    # Option 1: Provide full agent config to test (allows testing unsaved configs)
    agent_config_snapshot: Optional[AgentConfigOutput] = None
    # Option 2: Provide ID of an existing, persisted agent
    agent_id_to_simulate: Optional[str] = None

    symbol: str
    start_date_iso: str # e.g., "2023-01-01T00:00:00Z"
    end_date_iso: str   # e.g., "2023-12-31T23:59:59Z"
    initial_capital: float = Field(gt=0)
    simulated_fees_percentage: float = Field(default=0.001, ge=0) # 0.1% fee
    simulated_slippage_percentage: float = Field(default=0.0005, ge=0) # 0.05% slippage

    @root_validator(pre=False) # Pydantic v1 style root validator
    def check_config_or_id_present_v1(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        config, id_sim = values.get('agent_config_snapshot'), values.get('agent_id_to_simulate')
        if not config and not id_sim:
            raise ValueError("Either agent_config_snapshot or agent_id_to_simulate must be provided.")
        if config and id_sim:
            raise ValueError("Provide either agent_config_snapshot or agent_id_to_simulate, not both.")
        return values

class SimulatedTrade(BaseModel):
    timestamp: datetime
    side: Literal["buy", "sell"]
    quantity: float
    price: float # Execution price including slippage
    fee_paid: float
    # Optional: position_size_after_trade, pnl_of_this_trade (if closing)

class EquityDataPoint(BaseModel):
    timestamp: datetime
    equity: float

class BacktestResult(BaseModel):
    request_params: BacktestRequest
    final_capital: float
    total_pnl: float
    total_pnl_percentage: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Optional[float] = None
    loss_rate: Optional[float] = None
    average_win_amount: Optional[float] = None
    average_loss_amount: Optional[float] = None
    profit_factor: Optional[float] = None
    # max_drawdown: Optional[float] = None # Complex, defer for now
    list_of_simulated_trades: List[SimulatedTrade] = Field(default_factory=list)
    equity_curve: List[EquityDataPoint] = Field(default_factory=list)
    # Optional: Sharpe Ratio, Sortino, etc. - defer for now
