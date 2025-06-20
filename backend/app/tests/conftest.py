"""
Test configuration and fixtures.
"""
import os
import asyncio
from typing import AsyncGenerator, Generator
import pytest
import prometheus_client
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import uuid
import logging
from urllib.parse import urlparse

from app.core.settings import settings
from app.db.base import Base
from app.main import create_application
from app.models.user import User
from app.auth.utils import hash_password

# Use Postgres test DB from env or fallback
TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine():
    # Parse the DB URL to check the DB name only
    parsed = urlparse(TEST_DATABASE_URL)
    db_name = parsed.path.lstrip("/")
    assert db_name == "test_db", f"Bad DB name in URL: {TEST_DATABASE_URL}"
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

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

@pytest.fixture
async def test_user(db: AsyncSession):
    """Create a test user with a unique UUID-based email and id."""
    user = User(
        id=str(uuid.uuid4()),
        email=f"user-{uuid.uuid4()}@example.com",
        full_name="Test User",
        hashed_password=hash_password("SecurePass123!"),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    db_url = os.getenv("DATABASE_URL")
    logging.warning(f"PYTEST: Using DATABASE_URL = {db_url}")
    if db_url and "test_user" in db_url and not db_url.endswith("/test_db"):
        raise RuntimeError("DATABASE_URL is misconfigured: references 'test_user' as DB name!")
