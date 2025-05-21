"""
Middleware Module

This module provides production-grade middleware components for:
- Security headers injection
- Request/response logging
- Correlation ID tracking
- Prometheus metrics
- Rate limiting
- Request validation

Each middleware is configurable and integrated with the logging system.
"""

import json
import time
import uuid
from typing import Awaitable, Callable, Dict, Optional, Union, Tuple

import redis.asyncio as aioredis
import prometheus_client
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core import settings
from app.core.error_handler import ValidationException
from app.core.logging import correlation_id, get_logger

# Initialize logger
logger = get_logger(__name__)

# Prometheus metrics
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "endpoint"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "status"]
)

RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Total count of rate limit hits",
    ["ip_address", "endpoint"]
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to inject security headers into responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:;"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            )
        }
        
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
            
        return response

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation ID for request tracing."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.header_name = "X-Correlation-ID"

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Extract or generate correlation ID and attach to context."""
        # Get or generate correlation ID
        correlation_id_value = request.headers.get(
            self.header_name,
            str(uuid.uuid4())
        )
        
        # Set in context var for logging
        correlation_id.set(correlation_id_value)
        
        # Add to request state for other middleware/handlers
        request.state.correlation_id = correlation_id_value
        
        response = await call_next(request)
        
        # Add to response headers
        response.headers[self.header_name] = correlation_id_value
        
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for detailed request/response logging."""

    @staticmethod
    def _sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive information from headers."""
        sanitized = headers.copy()
        sensitive_fields = {
            "authorization",
            "cookie",
            "x-api-key",
            "api-key",
            "password",
            "token"
        }
        
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "***REDACTED***"
                
        return sanitized

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Log request and response details."""
        start_time = time.time()
        
        # Log request
        logger.info(
            "Incoming request",
            extra={
                "correlation_id": getattr(request.state, "correlation_id", None),
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host,
                "headers": self._sanitize_headers(dict(request.headers))
            }
        )
        
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            extra={
                "correlation_id": getattr(request.state, "correlation_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration * 1000,
                "response_headers": self._sanitize_headers(dict(response.headers))
            }
        )
        
        return response

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware for Prometheus metrics collection."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Track request metrics."""
        method = request.method
        path = request.url.path
        
        # Track in-progress requests
        REQUESTS_IN_PROGRESS.labels(
            method=method,
            endpoint=path
        ).inc()
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as exc:
            status_code = 500
            raise exc
            
        finally:
            # Record metrics
            duration = time.time() - start_time
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).observe(duration)
            
            REQUESTS_TOTAL.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).inc()
            
            REQUESTS_IN_PROGRESS.labels(
                method=method,
                endpoint=path
            ).dec()
            
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for IP-based rate limiting using Redis."""

    def __init__(self, app: ASGIApp, redis_pool: aioredis.Redis):
        super().__init__(app)
        self.redis = redis_pool
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE
        self.window = 60  # 1 minute window

    async def _get_remaining_requests(
        self,
        key: str
    ) -> Tuple[int, int]:
        """Get remaining requests for a key."""
        pipeline = self.redis.pipeline()
        now = time.time()
        
        # Clean old requests
        pipeline.zremrangebyscore(key, 0, now - self.window)
        
        # Count requests in current window
        pipeline.zcard(key)
        
        # Add current request
        pipeline.zadd(key, {str(now): now})
        
        # Set expiry
        pipeline.expire(key, self.window)
        
        results = await pipeline.execute()
        return self.rate_limit - results[1], results[1]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Apply rate limiting logic."""
        # Skip rate limiting for certain paths
        if request.url.path in settings.RATE_LIMIT_EXCLUDE_PATHS:
            return await call_next(request)
            
        # Create Redis key
        ip = request.client.host
        key = f"rate_limit:{ip}:{request.url.path}"
        
        # Check rate limit
        remaining, current = await self._get_remaining_requests(key)
        
        if remaining < 0:
            # Log rate limit breach
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "correlation_id": getattr(request.state, "correlation_id", None),
                    "ip_address": ip,
                    "path": request.url.path,
                    "current_requests": current,
                    "limit": self.rate_limit
                }
            )
            
            # Track metric
            RATE_LIMIT_HITS.labels(
                ip_address=ip,
                endpoint=request.url.path
            ).inc()
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "detail": f"Rate limit of {self.rate_limit} requests per minute exceeded"
                }
            )
            
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.window))
        
        return response

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for basic request payload validation."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Validate request payload format."""
        if request.method in {"POST", "PUT", "PATCH"}:
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                try:
                    # Try to parse JSON body
                    await request.json()
                except json.JSONDecodeError as e:
                    logger.warning(
                        "Invalid JSON payload",
                        extra={
                            "correlation_id": getattr(request.state, "correlation_id", None),
                            "path": request.url.path,
                            "method": request.method,
                            "error": str(e)
                        }
                    )
                    
                    raise ValidationException(
                        message="Invalid JSON payload",
                        extra={"error": str(e)}
                    )
                    
        return await call_next(request)

def add_middlewares(
    app: FastAPI,
    redis_pool: aioredis.Redis
) -> None:
    """
    Add all middleware to the FastAPI application in the correct order.
    
    Args:
        app: FastAPI application instance
        redis_pool: Redis connection pool for rate limiting
    """
    # Add middlewares in reverse order (last added = first executed)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(RateLimitMiddleware, redis_pool=redis_pool)
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info("All middleware components registered successfully") 
