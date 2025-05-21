"""
Database Session Module

This module manages database connections and sessions with:
- SQLAlchemy engine configuration
- Session factory and dependency injection
- Connection health checks
- Error handling and logging
"""

import contextlib
from typing import Generator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

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

# Create engine instance
engine = create_db_engine()

# SessionLocal is a factory for new Session objects
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)

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

__all__ = ["SessionLocal", "engine", "get_db", "get_db_context", "check_db_connection"]
