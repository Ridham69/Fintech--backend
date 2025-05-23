"""
Test configuration and fixtures.
"""
import os
os.environ["AUTH__JWT_SECRET_KEY"] = "dummy_jwt_secret_for_tests"
import asyncio
from typing import AsyncGenerator, Generator
import pytest
import prometheus_client
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


from app.core.settings import settings
from app.db.base import Base
from app.main import create_application

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
def app() -> FastAPI:
    """Create a test application instance."""
    app = create_application()
    return app

@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client."""
    async with AsyncClient(
        app=app,
        base_url="http://test",
        headers={"Content-Type": "application/json"}
    ) as client:
        yield client

@pytest.fixture
def test_settings():
    """Override settings for testing."""
    original_settings = settings.copy()
    settings.app.ENVIRONMENT = "test"
    settings.app.DEBUG = True
    yield settings
    settings = original_settings

@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """Unregister all Prometheus metrics before each test to avoid duplicate timeseries errors."""
    collectors = list(prometheus_client.REGISTRY._names_to_collectors.values())
    for collector in collectors:
        try:
            prometheus_client.REGISTRY.unregister(collector)
        except KeyError:
            pass
