"""
Core Module for MCP Trading Platform Monorepo
Provides centralized service registry, database management, and initialization
"""

from .service_registry import registry, get_registry, get_service_dependency, get_connection_dependency
from .database_manager import db_manager, get_database_manager, get_db_session, get_supabase, get_redis, get_async_redis
from .service_initializer import service_initializer, get_service_initializer

__all__ = [
    # Service Registry
    "registry",
    "get_registry", 
    "get_service_dependency",
    "get_connection_dependency",
    
    # Database Manager
    "db_manager",
    "get_database_manager",
    "get_db_session",
    "get_supabase", 
    "get_redis",
    "get_async_redis",
    
    # Service Initializer
    "service_initializer",
    "get_service_initializer"
]