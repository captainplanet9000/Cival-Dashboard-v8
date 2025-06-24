from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base # For older SQLAlchemy versions or compatibility
# For SQLAlchemy 2.0 style, can use from sqlalchemy.orm import DeclarativeBase
# Using declarative_base for wider compatibility as per prompt's initial suggestion style.
import os
# Import DB models to ensure they are registered with Base.metadata
from python_ai_services.models.db_models import AgentConfigDB, TradeFillDB, OrderDB, PortfolioSnapshotDB # Added PortfolioSnapshotDB


# SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent_configs.db")
# Using a file for persistence outside tests. In-memory for tests will be handled by test setup.
DEFAULT_DB_URL = "sqlite:///./agents_prod.db" # Default file-based DB for the application
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} # Needed only for SQLite when used with multiple threads (like FastAPI)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def create_db_and_tables():
    """Creates database tables based on Base metadata."""
    try:
        Base.metadata.create_all(bind=engine)
        print(f"Database tables created successfully for DB at: {SQLALCHEMY_DATABASE_URL}") # Using print for direct feedback
    except Exception as e:
        print(f"Error creating database tables: {e}") # Using print for direct feedback
        raise

def get_db():
    """FastAPI dependency to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

