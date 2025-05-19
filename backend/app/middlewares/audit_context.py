"""
Audit Context Middleware

This module provides middleware for capturing request metadata.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

class AuditContextMiddleware(BaseHTTPMiddleware):
    """Middleware for capturing request metadata for audit logging."""
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: set[str] = {"/health", "/metrics", "/docs", "/redoc"}
    ):
        """
        Initialize middleware.
        
        Args:
            app: ASGI application
            exclude_paths: Set of paths to exclude from audit logging
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths
        
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and capture metadata.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response from next handler
        """
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
            
        try:
            # Capture request metadata
            request.state.audit_metadata = {
                "ip_address": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params)
            }
            
            # Process request
            response = await call_next(request)
            
            # Add response metadata
            request.state.audit_metadata.update({
                "status_code": response.status_code
            })
            
            return response
            
        except Exception as e:
            logger.error(
                "Error in audit context middleware",
                exc_info=True,
                extra={
                    "path": request.url.path,
                    "error": str(e)
                }
            )
            raise 