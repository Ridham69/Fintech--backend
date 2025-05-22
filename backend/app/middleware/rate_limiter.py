"""
Rate Limiter Middleware

This module implements a Redis-backed sliding window rate limiter middleware.
"""

import time
from typing import Callable, Dict, Optional, Set, Tuple
from uuid import UUID

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User
from app.services.abuse_logger import AbuseLogger

logger = get_logger(__name__)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limiter middleware using Redis sliding window."""
    
    def __init__(
        self,
        app: FastAPI,
        redis: Redis,
        abuse_logger: AbuseLogger,
        exclude_paths: Optional[Set[str]] = None
    ):
        """Initialize middleware."""
        super().__init__(app)
        self.redis = redis
        self.abuse_logger = abuse_logger
        self.exclude_paths = exclude_paths or {
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
        
        # Rate limits per tier (requests per minute)
        self.tier_limits = {
            "basic": 30,
            "pro": 100,
            "enterprise": 500
        }
        
        # Window size in seconds
        self.window_size = 60
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request through rate limiter."""
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get user from request state (set by auth middleware)
        user: Optional[User] = getattr(request.state, "user", None)
        if not user:
            return await call_next(request)
        
        # Get rate limit for user's tier
        limit = self.tier_limits.get(user.tier, self.tier_limits["basic"])
        
        # Generate Redis key
        key = f"rate:{user.id}:{request.url.path}"
        
        try:
            # Check rate limit using sliding window
            is_allowed, retry_after = await self._check_rate_limit(key, limit)
            
            if not is_allowed:
                # Log abuse attempt
                await self.abuse_logger.log_abuse(
                    user_id=user.id,
                    endpoint=request.url.path,
                    ip=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                    tier=user.tier,
                    limit=limit
                )
                
                # Return rate limit exceeded response
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(
                await self._get_remaining_requests(key, limit)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}")
            # On Redis error, allow request but log error
            return await call_next(request)
    
    async def _check_rate_limit(
        self,
        key: str,
        limit: int
    ) -> Tuple[bool, int]:
        """
        Check if request is within rate limit using sliding window.
        
        Args:
            key: Redis key
            limit: Maximum requests allowed
            
        Returns:
            Tuple of (is_allowed, retry_after)
        """
        now = int(time.time())
        window_start = now - self.window_size
        
        # Get current window requests
        async with self.redis.pipeline() as pipe:
            # Remove old requests
            await pipe.zremrangebyscore(key, 0, window_start)
            # Count requests in window
            await pipe.zcard(key)
            # Add current request
            await pipe.zadd(key, {str(now): now})
            # Set expiry
            await pipe.expire(key, self.window_size)
            # Execute pipeline
            _, request_count, _, _ = await pipe.execute()
        
        # Check if limit exceeded
        if request_count >= limit:
            # Calculate retry after
            oldest_request = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                retry_after = int(oldest_request[0][1]) + self.window_size - now
            else:
                retry_after = self.window_size
            return False, retry_after
        
        return True, 0
    
    async def _get_remaining_requests(
        self,
        key: str,
        limit: int
    ) -> int:
        """Get remaining requests in current window."""
        request_count = await self.redis.zcard(key)
        return max(0, limit - request_count) 
