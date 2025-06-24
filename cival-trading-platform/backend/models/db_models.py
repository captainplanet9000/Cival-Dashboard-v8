from sqlalchemy import Column, String, Boolean, DateTime, Text, Float, ForeignKey # Added Float, ForeignKey
# For SQLAlchemy's built-in JSON type, if available and preferred over Text for JSON strings:
# from sqlalchemy import JSON as DB_JSON_TYPE
from python_ai_services.core.database import Base # Adjusted import path
from datetime import datetime, timezone # Ensure timezone for defaults
import uuid # Added for OrderDB primary key default

# Note: AgentStrategyConfig etc. are Pydantic models.
# They will be serialized to JSON strings before storing in Text columns.

class AgentConfigDB(Base):
    __tablename__ = "agent_configs"

    agent_id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    agent_type = Column(String, default="GenericAgent")
    parent_agent_id = Column(String, nullable=True, index=True)
    is_active = Column(Boolean, default=False)

    # Store complex Pydantic models or dicts as JSON strings using Text type.
    # SQLAlchemy's JSON type can be used if the DB backend has good JSON support (e.g., PostgreSQL).
    # For broader compatibility (including older SQLite), Text + manual json.dumps/loads is robust.

    # Stores Pydantic AgentStrategyConfig model as a JSON string
    strategy_config_json = Column(Text, default="{}")

    # Stores Pydantic AgentConfigOutput.hyperliquid_config (Dict[str,str]) as JSON string
    hyperliquid_config_json = Column(Text, nullable=True)

    # Stores Pydantic AgentConfigOutput.operational_parameters (Dict[str,Any]) as JSON string
    operational_parameters_json = Column(Text, default="{}")

    # Stores Pydantic AgentRiskConfig model as a JSON string
    risk_config_json = Column(Text, default="{}")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TradeFillDB(Base):
    __tablename__ = "trade_fills"

    fill_id = Column(String, primary_key=True, index=True) # From TradeFillData.fill_id
    agent_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow) # Consider timezone.utc for default
    asset = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False) # "buy" or "sell"
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    fee_currency = Column(String, nullable=True)
    exchange_order_id = Column(String, nullable=True, index=True)
    exchange_trade_id = Column(String, nullable=True, index=True) # Exchange's own fill/trade ID


class OrderDB(Base):
    __tablename__ = "orders"

    internal_order_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, nullable=False, index=True)
    timestamp_created = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    timestamp_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    asset = Column(String, nullable=False)
    side = Column(String, nullable=False) # "buy" or "sell"
    order_type = Column(String, nullable=False) # "market", "limit", etc.
    quantity = Column(Float, nullable=False)
    limit_price = Column(Float, nullable=True)

    status = Column(String, nullable=False, index=True, default="PENDING_SUBMISSION")
    # PENDING_SUBMISSION, SUBMITTED_TO_EXCHANGE, ACCEPTED_BY_EXCHANGE, REJECTED_BY_EXCHANGE,
    # PARTIALLY_FILLED, FILLED, CANCELED, ERROR

    exchange_order_id = Column(String, nullable=True, index=True)
    client_order_id = Column(String, nullable=True, index=True) # e.g., cloid from Hyperliquid

    error_message = Column(Text, nullable=True)
    # Store list of fill_ids as a JSON string
    associated_fill_ids_json = Column(Text, default="[]")

    # For direct parameters from original request if needed for reconstruction or audit
    raw_order_params_json = Column(Text, nullable=True)
    strategy_name = Column(String, nullable=True) # From trade_params


class PortfolioSnapshotDB(Base):
    __tablename__ = "portfolio_snapshots"
    snapshot_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agent_configs.agent_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    total_equity_usd = Column(Float, nullable=False)
