from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

import os

# Import Base from your db.base module
from app.db.base import Base

# You can use environment variables or a settings module for config
DATABASE_URL = os.getenv(
    "DB_URL",
    "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL echo in dev
    pool_pre_ping=True,
    future=True,
)

# Create async sessionmaker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Dependency for FastAPI routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
