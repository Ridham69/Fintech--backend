"""
Database Session Module

This module manages database connections and sessions with:
- Async SQLAlchemy engine configuration
- Session factory and dependency injection
- Connection health checks
- Error handling and logging
"""

import contextlib
from typing import AsyncGenerator, AsyncIterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from app.core.settings import settings
from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

def create_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine with proper configuration.
    
    Returns:
        AsyncEngine: Configured SQLAlchemy engine
    """
    try:
        # Mask database password in logs
        log_url = str(settings.db.DATABASE_URL).replace(
            settings.db.POSTGRES_PASSWORD.get_secret_value(),
            "***"
        )
        logger.info(f"Creating database engine for {log_url}")
        
        engine = create_async_engine(
            str(settings.db.DATABASE_URL),
            echo=settings.app.DEBUG,
            pool_pre_ping=True,
            pool_size=settings.db.POSTGRES_MAX_POOL_SIZE,
            max_overflow=settings.db.POSTGRES_MIN_POOL_SIZE,
            pool_recycle=settings.db.POSTGRES_POOL_RECYCLE
        )
        
        logger.info(
            "Database engine created successfully",
            extra={
                "pool_size": settings.db.POSTGRES_MAX_POOL_SIZE,
                "max_overflow": settings.db.POSTGRES_MIN_POOL_SIZE,
                "pool_recycle": settings.db.POSTGRES_POOL_RECYCLE
            }
        )
        
        return engine
        
    except Exception as e:
        logger.critical(
            "Failed to create database engine",
            exc_info=True,
            extra={"error": str(e)}
        )
        raise

# Create engine instance
engine = create_engine()

# Exported async sessionmaker for use in dependencies and imports
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields:
        AsyncSession: Database session
    
    Example:
        ```python
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            items = await db.execute(select(Item))
            return items.scalars().all()
        ```
    """
    session = async_session()
    
    try:
        logger.debug("Creating new database session")
        yield session
        
    except SQLAlchemyError as e:
        logger.error(
            "Database session error",
            exc_info=True,
            extra={"error": str(e)}
        )
        await session.rollback()
        raise
        
    finally:
        logger.debug("Closing database session")
        await session.close()

@contextlib.asynccontextmanager
async def get_db_context() -> AsyncIterator[AsyncSession]:
    """
    Context manager for database sessions.
    
    Yields:
        AsyncSession: Database session
    
    Example:
        ```python
        async with get_db_context() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
        ```
    """
    session = async_session()
    
    try:
        logger.debug("Creating new database session (context)")
        yield session
        await session.commit()
        
    except SQLAlchemyError as e:
        logger.error(
            "Database session error",
            exc_info=True,
            extra={"error": str(e)}
        )
        await session.rollback()
        raise
        
    finally:
        logger.debug("Closing database session (context)")
        await session.close()

async def check_db_connection() -> bool:
    """
    Check database connectivity.
    
    Returns:
        bool: True if connection successful, False otherwise
    
    Example:
        ```python
        @app.get("/health")
        async def health_check():
            db_healthy = await check_db_connection()
            return {"database": "healthy" if db_healthy else "unhealthy"}
        ```
    """
    try:
        async with get_db_context() as db:
            await db.execute("SELECT 1")
            logger.info("Database connection check successful")
            return True
            
    except Exception as e:
        logger.error(
            "Database connection check failed",
            exc_info=True,
            extra={"error": str(e)}
        )
        return False 

__all__ = ["async_session", "engine", "get_db", "get_db_context", "check_db_connection"]
