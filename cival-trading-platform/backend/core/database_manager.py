"""
Database Connection Manager
Centralized database and cache connection management for the monorepo
"""

import os
import logging
from typing import Optional, Dict, Any
import asyncio

# Database imports
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# External service imports
from supabase import create_client, Client as SupabaseClient
import redis
from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Centralized database and cache connection manager
    Handles Supabase, SQLAlchemy, and Redis connections
    """
    
    def __init__(self):
        self.supabase_client: Optional[SupabaseClient] = None
        self.redis_client: Optional[redis.Redis] = None
        self.async_redis_client: Optional[AsyncRedis] = None
        self.database_engine = None
        self.session_factory = None
        self._initialized = False
    
    async def initialize_connections(self) -> Dict[str, str]:
        """Initialize all database connections"""
        results = {}
        
        # Initialize Supabase
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY")
            
            if supabase_url and supabase_key:
                self.supabase_client = create_client(supabase_url, supabase_key)
                # Test connection with a simple query
                test_result = self.supabase_client.table('users').select('id').limit(1).execute()
                results["supabase"] = "connected"
                logger.info("✅ Supabase connection established")
            else:
                results["supabase"] = "configuration_missing"
                logger.warning("Supabase configuration missing")
        except Exception as e:
            results["supabase"] = f"error: {str(e)}"
            logger.error(f"Supabase connection failed: {e}")
        
        # Initialize Redis
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            
            # Sync Redis client
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            
            # Async Redis client
            self.async_redis_client = AsyncRedis.from_url(redis_url, decode_responses=True)
            await self.async_redis_client.ping()
            
            results["redis"] = "connected"
            logger.info("✅ Redis connections established")
        except Exception as e:
            results["redis"] = f"error: {str(e)}"
            logger.error(f"Redis connection failed: {e}")
        
        # Initialize SQLAlchemy
        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                # Default to SQLite for development
                database_url = "sqlite:///./trading_platform.db"
            
            # Configure engine based on database type
            if database_url.startswith("sqlite"):
                self.database_engine = create_engine(
                    database_url,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                    echo=os.getenv("SQL_ECHO", "").lower() == "true"
                )
            else:
                self.database_engine = create_engine(
                    database_url,
                    echo=os.getenv("SQL_ECHO", "").lower() == "true"
                )
            
            self.session_factory = sessionmaker(bind=self.database_engine)
            
            # Test connection
            with self.database_engine.connect() as conn:
                conn.execute("SELECT 1")
            
            results["database"] = "connected"
            logger.info("✅ Database engine established")
        except Exception as e:
            results["database"] = f"error: {str(e)}"
            logger.error(f"Database connection failed: {e}")
        
        self._initialized = True
        return results
    
    def get_supabase_client(self) -> Optional[SupabaseClient]:
        """Get Supabase client"""
        return self.supabase_client
    
    def get_redis_client(self) -> Optional[redis.Redis]:
        """Get synchronous Redis client"""
        return self.redis_client
    
    def get_async_redis_client(self) -> Optional[AsyncRedis]:
        """Get asynchronous Redis client"""
        return self.async_redis_client
    
    def get_database_engine(self):
        """Get SQLAlchemy engine"""
        return self.database_engine
    
    def get_session_factory(self):
        """Get SQLAlchemy session factory"""
        return self.session_factory
    
    def get_db_session(self) -> Session:
        """Get a new database session"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        return self.session_factory()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all connections"""
        health_status = {}
        
        # Check Supabase
        if self.supabase_client:
            try:
                self.supabase_client.table('users').select('id').limit(1).execute()
                health_status["supabase"] = "healthy"
            except Exception as e:
                health_status["supabase"] = f"unhealthy: {str(e)}"
        else:
            health_status["supabase"] = "not_initialized"
        
        # Check Redis
        if self.redis_client:
            try:
                self.redis_client.ping()
                health_status["redis_sync"] = "healthy"
            except Exception as e:
                health_status["redis_sync"] = f"unhealthy: {str(e)}"
        else:
            health_status["redis_sync"] = "not_initialized"
        
        if self.async_redis_client:
            try:
                await self.async_redis_client.ping()
                health_status["redis_async"] = "healthy"
            except Exception as e:
                health_status["redis_async"] = f"unhealthy: {str(e)}"
        else:
            health_status["redis_async"] = "not_initialized"
        
        # Check Database
        if self.database_engine:
            try:
                with self.database_engine.connect() as conn:
                    conn.execute("SELECT 1")
                health_status["database"] = "healthy"
            except Exception as e:
                health_status["database"] = f"unhealthy: {str(e)}"
        else:
            health_status["database"] = "not_initialized"
        
        return health_status
    
    async def cleanup(self) -> None:
        """Cleanup all connections"""
        logger.info("Starting database cleanup...")
        
        # Close Redis connections
        if self.async_redis_client:
            try:
                await self.async_redis_client.close()
                logger.info("Async Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing async Redis: {e}")
        
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Sync Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing sync Redis: {e}")
        
        # Close database engine
        if self.database_engine:
            try:
                self.database_engine.dispose()
                logger.info("Database engine disposed")
            except Exception as e:
                logger.error(f"Error disposing database engine: {e}")
        
        # Reset all clients
        self.supabase_client = None
        self.redis_client = None
        self.async_redis_client = None
        self.database_engine = None
        self.session_factory = None
        self._initialized = False
        
        logger.info("Database cleanup completed")
    
    def is_initialized(self) -> bool:
        """Check if manager is initialized"""
        return self._initialized

# Global database manager instance
db_manager = DatabaseManager()

def get_database_manager() -> DatabaseManager:
    """Get the global database manager"""
    return db_manager

# FastAPI dependencies for database access
def get_db_session():
    """FastAPI dependency for database session"""
    session = db_manager.get_db_session()
    try:
        yield session
    finally:
        session.close()

def get_supabase():
    """FastAPI dependency for Supabase client"""
    client = db_manager.get_supabase_client()
    if not client:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Supabase not available")
    return client

def get_redis():
    """FastAPI dependency for Redis client"""
    client = db_manager.get_redis_client()
    if not client:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Redis not available")
    return client

def get_async_redis():
    """FastAPI dependency for async Redis client"""
    client = db_manager.get_async_redis_client()
    if not client:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Async Redis not available")
    return client