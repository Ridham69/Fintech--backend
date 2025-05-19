"""
Security module for IP-based protection and rate limiting.
"""
from datetime import datetime, timedelta
from typing import Optional, Set
import ipaddress
from fastapi import Request, HTTPException
from redis.asyncio import Redis

from app.core.settings import settings
from app.auth.utils import get_redis

class IPSecurity:
    """IP-based security features."""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self._suspicious_ips: Set[str] = set()
        self._blocked_ips: Set[str] = set()
    
    async def initialize(self):
        """Initialize Redis connection."""
        self.redis = await get_redis()
    
    def is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    async def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked."""
        if not self.redis:
            await self.initialize()
        return bool(await self.redis.get(f"blocked_ip:{ip}"))
    
    async def block_ip(self, ip: str, duration: int = 3600) -> None:
        """Block an IP address."""
        if not self.redis:
            await self.initialize()
        await self.redis.setex(f"blocked_ip:{ip}", duration, "1")
        self._blocked_ips.add(ip)
    
    async def unblock_ip(self, ip: str) -> None:
        """Unblock an IP address."""
        if not self.redis:
            await self.initialize()
        await self.redis.delete(f"blocked_ip:{ip}")
        self._blocked_ips.discard(ip)
    
    async def record_failed_attempt(self, ip: str) -> int:
        """Record failed login attempt."""
        if not self.redis:
            await self.initialize()
            
        key = f"failed_attempts:{ip}"
        attempts = await self.redis.incr(key)
        
        if attempts == 1:
            await self.redis.expire(key, 3600)  # 1 hour window
        
        if attempts >= settings.rate_limit.AUTH_RATE_LIMIT:
            await self.block_ip(ip)
            
        return attempts
    
    async def clear_failed_attempts(self, ip: str) -> None:
        """Clear failed login attempts."""
        if not self.redis:
            await self.initialize()
        await self.redis.delete(f"failed_attempts:{ip}")

class RateLimiter:
    """Rate limiting implementation."""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        self.redis = await get_redis()
    
    async def is_rate_limited(
        self,
        key: str,
        limit: int,
        window: int = 60
    ) -> bool:
        """
        Check if request should be rate limited.
        
        Args:
            key: Rate limit key (e.g. IP or user ID)
            limit: Maximum requests per window
            window: Time window in seconds
            
        Returns:
            bool: True if rate limited
        """
        if not self.redis:
            await self.initialize()
            
        current = await self.redis.incr(f"ratelimit:{key}")
        
        if current == 1:
            await self.redis.expire(f"ratelimit:{key}", window)
            
        return current > limit
    
    async def get_remaining(self, key: str) -> int:
        """Get remaining requests in window."""
        if not self.redis:
            await self.initialize()
            
        count = await self.redis.get(f"ratelimit:{key}")
        if not count:
            return settings.rate_limit.RATE_LIMIT_PER_MINUTE
            
        return max(0, settings.rate_limit.RATE_LIMIT_PER_MINUTE - int(count))

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    if request.url.path in settings.rate_limit.RATE_LIMIT_EXCLUDE_PATHS:
        return await call_next(request)
        
    limiter = RateLimiter()
    client_ip = request.client.host
    
    # Get appropriate rate limit based on endpoint
    if "/auth/" in request.url.path:
        limit = settings.rate_limit.AUTH_RATE_LIMIT
    elif "/investment/" in request.url.path:
        limit = settings.rate_limit.INVESTMENT_RATE_LIMIT
    elif "/payment/" in request.url.path:
        limit = settings.rate_limit.PAYMENT_RATE_LIMIT
    else:
        limit = settings.rate_limit.RATE_LIMIT_PER_MINUTE
    
    if await limiter.is_rate_limited(client_ip, limit):
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )
    
    response = await call_next(request)
    remaining = await limiter.get_remaining(client_ip)
    
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Limit"] = str(limit)
    
    return response

# Global instances
ip_security = IPSecurity()
rate_limiter = RateLimiter() 