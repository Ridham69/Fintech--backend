"""
Database Package

This package contains database connection and session management.
"""

from typing import Callable

from fastapi import FastAPI

from app.core.logging import get_logger
from app.db.base import Base
from app.db.session import check_db_connection, engine, get_db, get_db_context

# Initialize logger
logger = get_logger(__name__)

async def init_db() -> None:
    """
    Initialize database connection and verify health.
    
    Raises:
        RuntimeError: If database connection fails
    """
    try:
        logger.info("[DB INIT] Starting database initialization")
        
        if not await check_db_connection():
            raise RuntimeError("Failed to connect to database")
            
        logger.info("[DB INIT] Database initialization successful")
        
    except Exception as e:
        logger.critical(
            "[DB INIT] Database initialization failed",
            exc_info=True,
            extra={"error": str(e)}
        )
        raise

def init_app(app: FastAPI) -> None:
    """
    Initialize database with FastAPI lifecycle events.
    
    Args:
        app: FastAPI application instance
    """
    async def startup() -> None:
        """Run database initialization on startup."""
        logger.info("[DB INIT] Running database startup checks")
        await init_db()

    async def shutdown() -> None:
        """Close database connections on shutdown."""
        logger.info("[DB INIT] Closing database connections")
        await engine.dispose()

    # Register event handlers
    app.add_event_handler("startup", startup)
    app.add_event_handler("shutdown", shutdown)

# Export commonly used components
__all__ = [
    "Base",
    "engine",
    "get_db",
    "get_db_context",
    "init_app",
    "init_db"
] 