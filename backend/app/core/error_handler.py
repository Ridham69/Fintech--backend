"""
Error Handling Module

This module provides a comprehensive error handling system for the fintech application with:
- Custom exception hierarchy
- Standardized error responses
- Request validation handling
- Logging integration
- Metrics tracking
- Security-aware error details
"""

from datetime import datetime
from typing import Any, Dict, Optional, Type

import prometheus_client
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from app.core import settings
from app.core.logging import get_logger, correlation_id

# Initialize logger
logger = get_logger(__name__)

# Prometheus metrics for error tracking
ERROR_COUNTER = prometheus_client.Counter(
    "api_errors_total",
    "Total count of API errors",
    ["error_type", "endpoint", "status_code"]
)

class ErrorResponse(BaseModel):
    """Standardized error response model."""
    timestamp: str
    status_code: int
    message: str
    error_code: str
    correlation_id: str
    path: str
    details: Optional[Dict[str, Any]] = None

class AppException(Exception):
    """Base exception class for all application errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        extra: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.extra = extra or {}
        super().__init__(message)

class InvalidCredentialsException(AppException):
    """Raised when authentication credentials are invalid."""
    
    def __init__(
        self,
        message: str = "Invalid credentials provided",
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_CREDENTIALS",
            extra=extra
        )

class PermissionDeniedException(AppException):
    """Raised when user lacks required permissions."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED",
            extra=extra
        )

class ResourceNotFoundException(AppException):
    """Raised when requested resource is not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            extra=extra
        )

class ConflictException(AppException):
    """Raised when there's a conflict with existing resource."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
            extra=extra
        )

class RateLimitException(AppException):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            extra=extra
        )

class ServiceUnavailableException(AppException):
    """Raised when a required service is unavailable."""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            extra=extra
        )

class ValidationException(AppException):
    """Raised when request validation fails."""
    
    def __init__(
        self,
        message: str = "Validation error",
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            extra=extra
        )

def create_error_response(
    request: Request,
    status_code: int,
    message: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """
    Create a standardized error response.
    
    Args:
        request: FastAPI request object
        status_code: HTTP status code
        message: Error message
        error_code: Error code for client identification
        details: Optional additional error details
    
    Returns:
        Standardized error response
    """
    return ErrorResponse(
        timestamp=datetime.utcnow().isoformat(),
        status_code=status_code,
        message=message,
        error_code=error_code,
        correlation_id=correlation_id.get(),
        path=str(request.url.path),
        details=details
    )

async def handle_app_exception(
    request: Request,
    exc: AppException
) -> JSONResponse:
    """Handle custom application exceptions."""
    # Log the error with context
    logger.error(
        f"Application error: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "extra": exc.extra
        },
        exc_info=exc if settings.ENVIRONMENT == "development" else None
    )

    # Track metric
    ERROR_COUNTER.labels(
        error_type=exc.__class__.__name__,
        endpoint=request.url.path,
        status_code=exc.status_code
    ).inc()

    # Create response
    error_response = create_error_response(
        request=request,
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.extra if settings.ENVIRONMENT == "development" else None
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

async def handle_validation_error(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    # Create detailed error message
    error_details = []
    for error in exc.errors():
        error_details.append({
            "loc": " -> ".join(str(x) for x in error["loc"]),
            "msg": error["msg"],
            "type": error["type"]
        })

    # Log the validation error
    logger.warning(
        "Request validation failed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "validation_errors": error_details
        }
    )

    # Track metric
    ERROR_COUNTER.labels(
        error_type="ValidationError",
        endpoint=request.url.path,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    ).inc()

    # Create response
    error_response = create_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Request validation failed",
        error_code="VALIDATION_ERROR",
        details={"errors": error_details} if settings.ENVIRONMENT == "development" else None
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )

async def handle_http_exception(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """Handle HTTP exceptions."""
    # Log the error
    logger.error(
        f"HTTP error: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )

    # Track metric
    ERROR_COUNTER.labels(
        error_type="HTTPException",
        endpoint=request.url.path,
        status_code=exc.status_code
    ).inc()

    # Create response
    error_response = create_error_response(
        request=request,
        status_code=exc.status_code,
        message=str(exc.detail),
        error_code=f"HTTP_{exc.status_code}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

async def handle_generic_exception(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle any unhandled exceptions."""
    # Log the error with full traceback
    logger.critical(
        f"Unhandled error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )

    # Track metric
    ERROR_COUNTER.labels(
        error_type=exc.__class__.__name__,
        endpoint=request.url.path,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    ).inc()

    # Create sanitized response
    error_response = create_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred" if settings.ENVIRONMENT != "development" else str(exc),
        error_code="INTERNAL_SERVER_ERROR"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Register handlers for custom exceptions
    app.add_exception_handler(AppException, handle_app_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_generic_exception)

    logger.info("Exception handlers registered successfully") 

# Alias for compatibility with code expecting a generic handler
handle_exception = handle_generic_exception

__all__ = [
    "AppException",
    "InvalidCredentialsException",
    "PermissionDeniedException",
    "ResourceNotFoundException",
    "ConflictException",
    "RateLimitException",
    "ServiceUnavailableException",
    "ValidationException",
    "handle_app_exception",
    "handle_validation_error",
    "handle_http_exception",
    "handle_generic_exception",
    "handle_exception",
    "register_exception_handlers",
]
