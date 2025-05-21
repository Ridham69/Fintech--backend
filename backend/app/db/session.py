"""
Database Session Module

This module manages database connections and sessions with:
- SQLAlchemy engine configuration
- Session factory and dependency injection
- Connection health checks
- Error handling and logging
"""

import contextlib
from typing import AsyncGenerator, Generator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.settings import settings
from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

def create_db_engine():
    """
    Create SQLAlchemy engine with proper configuration.
    
    Returns:
        Engine: Configured SQLAlchemy engine
    """
    try:
        # Mask database password in logs
        log_url = str(settings.db.DATABASE_URL).replace(
            settings.db.POSTGRES_PASSWORD.get_secret_value(),
            "***"
        )
        logger.info(f"Creating database engine for {log_url}")
        
        engine = create_engine(
            str(settings.db.DATABASE_URL),
            echo=settings.app.DEBUG,
            pool_pre_ping=True,
            pool_size=settings.db.POSTGRES_MAX_POOL_SIZE,
            max_overflow=settings.db.POSTGRES_MIN_POOL_SIZE,
            pool_recycle=settings.db.POSTGRES_POOL_RECYCLE,
            future=True
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

def create_async_db_engine():
    """
    Create SQLAlchemy async engine with proper configuration.
    
    Returns:
        AsyncEngine: Configured SQLAlchemy async engine
    """
    try:
        # Mask database password in logs
        log_url = str(settings.db.ASYNC_DATABASE_URL).replace(
            settings.db.POSTGRES_PASSWORD.get_secret_value(),
            "***"
        )
        logger.info(f"Creating async database engine for {log_url}")
        
        async_engine = create_async_engine(
            str(settings.db.ASYNC_DATABASE_URL),
            echo=settings.app.DEBUG,
            pool_pre_ping=True,
            pool_size=settings.db.POSTGRES_MAX_POOL_SIZE,
            max_overflow=settings.db.POSTGRES_MIN_POOL_SIZE,
            pool_recycle=settings.db.POSTGRES_POOL_RECYCLE,
        )
        
        logger.info(
            "Async database engine created successfully",
            extra={
                "pool_size": settings.db.POSTGRES_MAX_POOL_SIZE,
                "max_overflow": settings.db.POSTGRES_MIN_POOL_SIZE,
                "pool_recycle": settings.db.POSTGRES_POOL_RECYCLE
            }
        )
        
        return async_engine
        
    except Exception as e:
        logger.critical(
            "Failed to create async database engine",
            exc_info=True,
            extra={"error": str(e)}
        )
        raise

# Create engine instances
engine = create_db_engine()
async_engine = create_async_db_engine()

# SessionLocal is a factory for new Session objects
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)

# AsyncSessionLocal is a factory for new AsyncSession objects
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False
)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async database sessions.
    
    Yields:
        AsyncSession: Async database session
    
    Example:
        ```python
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            items = result.scalars().all()
            return items
        ```
    """
    session = AsyncSessionLocal()
    
    try:
        logger.debug("Creating new async database session")
        yield session
        await session.commit()
        
    except SQLAlchemyError as e:
        logger.error(
            "Async database session error",
            exc_info=True,
            extra={"error": str(e)}
        )
        await session.rollback()
        raise
        
    finally:
        logger.debug("Closing async database session")
        await session.close()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields:
        Session: Database session
    
    Example:
        ```python
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
        ```
    """
    session = SessionLocal()
    
    try:
        logger.debug("Creating new database session")
        yield session
        session.commit()
        
    except SQLAlchemyError as e:
        logger.error(
            "Database session error",
            exc_info=True,
            extra={"error": str(e)}
        )
        session.rollback()
        raise
        
    finally:
        logger.debug("Closing database session")
        session.close()

@contextlib.asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    
    Yields:
        AsyncSession: Async database session
    
    Example:
        ```python
        async with get_async_db_context() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
        ```
    """
    session = AsyncSessionLocal()
    
    try:
        logger.debug("Creating new async database session (context)")
        yield session
        await session.commit()
        
    except SQLAlchemyError as e:
        logger.error(
            "Async database session error",
            exc_info=True,
            extra={"error": str(e)}
        )
        await session.rollback()
        raise
        
    finally:
        logger.debug("Closing async database session (context)")
        await session.close()

@contextlib.contextmanager
def get_db_context() -> Iterator[Session]:
    """
    Context manager for database sessions.
    
    Yields:
        Session: Database session
    
    Example:
        ```python
        with get_db_context() as db:
            users = db.query(User).all()
        ```
    """
    session = SessionLocal()
    
    try:
        logger.debug("Creating new database session (context)")
        yield session
        session.commit()
        
    except SQLAlchemyError as e:
        logger.error(
            "Database session error",
            exc_info=True,
            extra={"error": str(e)}
        )
        session.rollback()
        raise
        
    finally:
        logger.debug("Closing database session (context)")
        session.close()

async def check_async_db_connection() -> bool:
    """
    Check async database connectivity.
    
    Returns:
        bool: True if connection successful, False otherwise
    
    Example:
        ```python
        @app.get("/health")
        async def health_check():
            db_healthy = await check_async_db_connection()
            return {"database": "healthy" if db_healthy else "unhealthy"}
        ```
    """
    try:
        async with get_async_db_context() as db:
            await db.execute("SELECT 1")
            logger.info("Async database connection check successful")
            return True
            
    except Exception as e:
        logger.error(
            "Async database connection check failed",
            exc_info=True,
            extra={"error": str(e)}
        )
        return False

def check_db_connection() -> bool:
    """
    Check database connectivity.
    
    Returns:
        bool: True if connection successful, False otherwise
    
    Example:
        ```python
        @app.get("/health")
        def health_check():
            db_healthy = check_db_connection()
            return {"database": "healthy" if db_healthy else "unhealthy"}
        ```
    """
    try:
        with get_db_context() as db:
            db.execute("SELECT 1")
            logger.info("Database connection check successful")
            return True
            
    except Exception as e:
        logger.error(
            "Database connection check failed",
            exc_info=True,
            extra={"error": str(e)}
        )
        return False 

__all__ = [
    "SessionLocal", "engine", "get_db", "get_db_context", "check_db_connection",
    "AsyncSessionLocal", "async_engine", "get_async_db", "get_async_db_context", "check_async_db_connection"
]
