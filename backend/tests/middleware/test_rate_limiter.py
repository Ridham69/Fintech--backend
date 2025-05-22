"""
Rate Limiter Tests

This module contains tests for the rate limiter middleware.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.rate_limiter import RateLimiterMiddleware
from app.models.user import User
from app.services.abuse_logger import AbuseLogger

# Test data
TEST_USER_ID = uuid4()
TEST_USER_EMAIL = "test@example.com"
TEST_USER_TIER = "basic"

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    class MockRedis:
        def __init__(self):
            self.data: Dict[str, Dict[str, float]] = {}
        
        async def pipeline(self):
            return MockPipeline(self.data)
        
        async def zrange(self, key: str, start: int, end: int, withscores: bool = False):
            if key not in self.data:
                return []
            items = sorted(self.data[key].items(), key=lambda x: x[1])
            if withscores:
                return [(k, v) for k, v in items[start:end]]
            return [k for k, _ in items[start:end]]
        
        async def zcard(self, key: str) -> int:
            return len(self.data.get(key, {}))
    
    class MockPipeline:
        def __init__(self, data: Dict[str, Dict[str, float]]):
            self.data = data
            self.commands = []
        
        async def zremrangebyscore(self, key: str, min_score: float, max_score: float):
            self.commands.append(("zremrangebyscore", key, min_score, max_score))
            if key in self.data:
                self.data[key] = {
                    k: v for k, v in self.data[key].items()
                    if v > max_score
                }
            return self
        
        async def zadd(self, key: str, mapping: Dict[str, float]):
            self.commands.append(("zadd", key, mapping))
            if key not in self.data:
                self.data[key] = {}
            self.data[key].update(mapping)
            return self
        
        async def expire(self, key: str, seconds: int):
            self.commands.append(("expire", key, seconds))
            return self
        
        async def execute(self):
            return [None] * len(self.commands)
    
    return MockRedis()

@pytest.fixture
def mock_abuse_logger():
    """Mock abuse logger."""
    class MockAbuseLogger:
        def __init__(self):
            self.logs = []
        
        async def log_abuse(
            self,
            user_id: UUID,
            endpoint: str,
            ip: str,
            user_agent: Optional[str],
            tier: str,
            limit: int,
            metadata: Optional[dict] = None
        ):
            self.logs.append({
                "user_id": user_id,
                "endpoint": endpoint,
                "ip": ip,
                "user_agent": user_agent,
                "tier": tier,
                "limit": limit,
                "metadata": metadata
            })
    
    return MockAbuseLogger()

@pytest.fixture
def test_user(test_db: AsyncSession):
    """Create test user."""
    user = User(
        id=TEST_USER_ID,
        email=TEST_USER_EMAIL,
        tier=TEST_USER_TIER,
        is_active=True,
        is_verified=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def rate_limiter(
    test_app: FastAPI,
    mock_redis: Redis,
    mock_abuse_logger: AbuseLogger
):
    """Create rate limiter middleware."""
    return RateLimiterMiddleware(
        app=test_app,
        redis=mock_redis,
        abuse_logger=mock_abuse_logger
    )

@pytest.mark.asyncio
async def test_rate_limit_basic(
    test_app: FastAPI,
    test_client: AsyncClient,
    rate_limiter: RateLimiterMiddleware,
    test_user: User
):
    """Test basic rate limiting."""
    # Arrange
    endpoint = "/api/test"
    limit = rate_limiter.tier_limits["basic"]
    
    # Act & Assert
    # Make requests up to limit
    for _ in range(limit):
        response = await test_client.get(
            endpoint,
            headers={"Authorization": f"Bearer test_token"}
        )
        assert response.status_code == 200
    
    # Next request should be rate limited
    response = await test_client.get(
        endpoint,
        headers={"Authorization": f"Bearer test_token"}
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers

@pytest.mark.asyncio
async def test_rate_limit_tiers(
    test_app: FastAPI,
    test_client: AsyncClient,
    rate_limiter: RateLimiterMiddleware,
    test_user: User
):
    """Test rate limits for different tiers."""
    # Arrange
    endpoint = "/api/test"
    tiers = {
        "basic": 30,
        "pro": 100,
        "enterprise": 500
    }
    
    # Test each tier
    for tier, limit in tiers.items():
        # Update user tier
        test_user.tier = tier
        test_app.dependency_overrides[get_current_user] = lambda: test_user
        
        # Make requests up to limit
        for _ in range(limit):
            response = await test_client.get(
                endpoint,
                headers={"Authorization": f"Bearer test_token"}
            )
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = await test_client.get(
            endpoint,
            headers={"Authorization": f"Bearer test_token"}
        )
        assert response.status_code == 429

@pytest.mark.asyncio
async def test_rate_limit_excluded_paths(
    test_app: FastAPI,
    test_client: AsyncClient,
    rate_limiter: RateLimiterMiddleware,
    test_user: User
):
    """Test rate limit exclusion for certain paths."""
    # Arrange
    excluded_paths = {
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json"
    }
    
    # Act & Assert
    for path in excluded_paths:
        # Make many requests to excluded path
        for _ in range(100):
            response = await test_client.get(
                path,
                headers={"Authorization": f"Bearer test_token"}
            )
            assert response.status_code == 200

@pytest.mark.asyncio
async def test_rate_limit_headers(
    test_app: FastAPI,
    test_client: AsyncClient,
    rate_limiter: RateLimiterMiddleware,
    test_user: User
):
    """Test rate limit headers in response."""
    # Arrange
    endpoint = "/api/test"
    limit = rate_limiter.tier_limits["basic"]
    
    # Act
    response = await test_client.get(
        endpoint,
        headers={"Authorization": f"Bearer test_token"}
    )
    
    # Assert
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert int(response.headers["X-RateLimit-Limit"]) == limit
    assert int(response.headers["X-RateLimit-Remaining"]) == limit - 1

@pytest.mark.asyncio
async def test_rate_limit_abuse_logging(
    test_app: FastAPI,
    test_client: AsyncClient,
    rate_limiter: RateLimiterMiddleware,
    mock_abuse_logger: AbuseLogger,
    test_user: User
):
    """Test abuse logging on rate limit exceeded."""
    # Arrange
    endpoint = "/api/test"
    limit = rate_limiter.tier_limits["basic"]
    
    # Act
    # Make requests to exceed limit
    for _ in range(limit + 1):
        await test_client.get(
            endpoint,
            headers={"Authorization": f"Bearer test_token"}
        )
    
    # Assert
    assert len(mock_abuse_logger.logs) == 1
    log = mock_abuse_logger.logs[0]
    assert log["user_id"] == test_user.id
    assert log["endpoint"] == endpoint
    assert log["tier"] == test_user.tier
    assert log["limit"] == limit

@pytest.mark.asyncio
async def test_rate_limit_redis_error(
    test_app: FastAPI,
    test_client: AsyncClient,
    rate_limiter: RateLimiterMiddleware,
    test_user: User
):
    """Test behavior on Redis error."""
    # Arrange
    endpoint = "/api/test"
    
    # Simulate Redis error
    async def mock_redis_error(*args, **kwargs):
        raise Exception("Redis error")
    
    rate_limiter.redis.zcard = mock_redis_error
    
    # Act
    response = await test_client.get(
        endpoint,
        headers={"Authorization": f"Bearer test_token"}
    )
    
    # Assert
    # Should allow request on Redis error
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_rate_limit_sliding_window(
    test_app: FastAPI,
    test_client: AsyncClient,
    rate_limiter: RateLimiterMiddleware,
    test_user: User
):
    """Test sliding window rate limiting."""
    # Arrange
    endpoint = "/api/test"
    limit = rate_limiter.tier_limits["basic"]
    
    # Act & Assert
    # Make requests up to limit
    for _ in range(limit):
        response = await test_client.get(
            endpoint,
            headers={"Authorization": f"Bearer test_token"}
        )
        assert response.status_code == 200
    
    # Wait for window to slide
    await asyncio.sleep(rate_limiter.window_size + 1)
    
    # Should be able to make requests again
    response = await test_client.get(
        endpoint,
        headers={"Authorization": f"Bearer test_token"}
    )
    assert response.status_code == 200 
