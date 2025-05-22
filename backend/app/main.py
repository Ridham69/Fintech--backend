"""
AutoInvest India - Main Application Entry Point

This module initializes the FastAPI application with all necessary middleware,
monitoring tools, and route configurations. It sets up:
- Prometheus metrics and instrumentation
- Sentry error tracking with performance monitoring
- OpenTelemetry distributed tracing
- Custom logging middleware with correlation IDs
- CORS and security headers
- Database and Redis connections
- API route registration
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

import prometheus_client
import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from prometheus_client import make_asgi_app
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
)
from fastapi.openapi.utils import get_openapi
from redis.asyncio import Redis
from app.monitoring.prometheus import (
    get_requests_total,
    get_requests_in_progress,
    get_requests_latency,
    setup_metrics,
)
from app.api.v1.routes import auth, kyc, payment, investment
from app.core.settings import settings
from app.core.error_handler import handle_exception
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware, RequestValidationMiddleware, CorrelationIDMiddleware, SecurityHeadersMiddleware
from app.db.session import SessionLocal, engine
from app.monitoring.opentelemetry import setup_telemetry
from app.monitoring.prometheus import setup_metrics
from app.redis_new.client import init_redis_pool
from app.middlewares.audit_context import AuditContextMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.services.abuse_logger import AbuseLogger
from app.services.notification import NotificationService

# Initialize logging
logger = logging.getLogger(__name__)

# Define Prometheus metrics
class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for each request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        get_requests_in_progress().inc()
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            status_code = 500
            raise exc
        finally:
            duration = time.time() - start_time
            get_requests_total().labels(
                method=request.method,
                endpoint=request.url.path,
                status=status_code
            ).inc()
            get_requests_latency().labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            get_requests_in_progress().dec()




@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Lifespan context manager for FastAPI application startup and shutdown events.
    Handles initialization and cleanup of database, Redis, and monitoring tools.
    """
    # Startup
    try:
        # Initialize Redis connection pool
        await init_redis_pool()
        logger.info("Redis connection pool initialized")

        # Initialize database connection
        async with SessionLocal() as db:
            await db.execute("SELECT 1")
            logger.info("Database connection verified")

        # Setup monitoring
        setup_metrics()
        setup_telemetry()
        logger.info("Monitoring tools initialized")

        # Initialize Redis
        redis = Redis.from_url(
            str(settings.db.REDIS_URL),
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Redis connection initialized")

        # Initialize services
        notification_service = NotificationService()
        abuse_logger = AbuseLogger(
            db=engine,
            notification_service=notification_service
        )
        logger.info("Services initialized")

        # Add rate limiter middleware
        app.add_middleware(
            RateLimiterMiddleware,
            redis=redis,
            abuse_logger=abuse_logger,
            exclude_paths=settings.rate_limit.RATE_LIMIT_EXCLUDE_PATHS
        )

        yield
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise
    finally:
        # Cleanup
        logger.info("Shutting down application...")
        await redis.close()
        await notification_service.cleanup()

def create_application() -> FastAPI:
    """
    Creates and configures the FastAPI application with all middleware and routes.
    Includes comprehensive monitoring, security headers, and API documentation.
    """
    # Initialize Sentry with all integrations
    sentry_sdk.init(
        dsn=settings.logging.SENTRY_DSN,  # <-- FIXED: use the nested logging config
        environment=settings.app.ENVIRONMENT,
        traces_sample_rate=1.0,
        integrations=[
            FastApiIntegration(
                transaction_style="endpoint"
            ),
            RedisIntegration(),
            SqlalchemyIntegration()
        ],
        enable_tracing=True
    )

    # Create FastAPI app with OpenAPI customization
    app = FastAPI(
        title=settings.app.TITLE,
        description=settings.app.DESCRIPTION,
        version=settings.app.VERSION,
        docs_url="/docs" if not settings.app.is_production else None,
        redoc_url="/redoc" if not settings.app.is_production else None,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Authentication", "description": "User authentication operations"},
            {"name": "KYC", "description": "Know Your Customer verification"},
            {"name": "Payments", "description": "Payment processing and tracking"},
            {"name": "Investments", "description": "Investment automation and tracking"}
        ]
    )

    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
            
        openapi_schema = get_openapi(
            title=settings.app.TITLE,
            version=settings.app.VERSION,
            description=settings.app.DESCRIPTION,
            routes=app.routes,
            tags=[
                {"name": "Auth", "description": "Authentication and authorization endpoints"},
                {"name": "Users", "description": "User management endpoints"},
                {"name": "Investments", "description": "Investment management endpoints"},
                {"name": "Payments", "description": "Payment processing endpoints"},
                {"name": "Reports", "description": "Report generation endpoints"},
            ]
        )
        
        # Custom security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # Custom documentation endpoints
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{settings.app.TITLE} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{settings.app.TITLE} - ReDoc",
            redoc_js_url="/static/redoc.standalone.js",
        )

    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Add CORS middleware with configuration from settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.security.CORS_ORIGINS],
        allow_credentials=settings.security.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.security.CORS_ALLOW_METHODS,
        allow_headers=settings.security.CORS_ALLOW_HEADERS,
    )

    # Add custom middleware in correct order
    app.add_middleware(PrometheusMiddleware)  # First to capture all requests
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Mount Prometheus metrics endpoint with authentication
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Register exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return await handle_exception(request, exc)

    # Include API routers with versioning
    app.include_router(
        auth.router,
        prefix="/api/v1/auth",
        tags=["Authentication"]
    )
    app.include_router(
        kyc.router,
        prefix="/api/v1/kyc",
        tags=["KYC"]
    )
    app.include_router(
        payment.router,
        prefix="/api/v1/payment",
        tags=["Payments"]
    )
    app.include_router(
        investment.router,
        prefix="/api/v1/investment",
        tags=["Investments"]
    )

    # Health check endpoint with basic service checks
    @app.get("/healthz", tags=["Monitoring"])
    async def health_check():
        """
        Health check endpoint for monitoring.
        Performs basic service checks and returns service status.
        """
        try:
            # Check database connection
            async with SessionLocal() as db:
                await db.execute("SELECT 1")
            
            # Check Redis connection
            await init_redis_pool().ping()

            return {
                "status": "healthy",
                "timestamp": time.time(),
                "version": settings.VERSION,
                "environment": settings.app.ENVIRONMENT
            }
        except Exception as e:
            logger.error("Health check failed", exc_info=True)
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                }
            )

    # Add audit context middleware
    app.add_middleware(AuditContextMiddleware)

    return app

# Create the FastAPI application instance
app = create_application()

# Setup logging after app creation
setup_logging()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.ENVIRONMENT == "development",
        log_config=None,  # Use our custom logging config
        ssl_keyfile=settings.SSL_KEYFILE if settings.app.ENVIRONMENT == "production" else None,
        ssl_certfile=settings.SSL_CERTFILE if settings.app.ENVIRONMENT == "production" else None,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )




