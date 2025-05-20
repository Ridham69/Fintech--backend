from typing import Any, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):
    """
    Base application exception for custom error handling.
    """
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        message: str = "An unexpected error occurred.",
        details: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        self.message = message
        self.details = details
        super().__init__(
            status_code=status_code,
            detail={"message": message, "details": details},
            headers=headers,
        )


class UnauthorizedException(AppException):
    def __init__(
        self,
        message: str = "Unauthorized.",
        details: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            details=details,
            headers=headers,
        )


class ForbiddenException(AppException):
    def __init__(
        self,
        message: str = "Forbidden.",
        details: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            details=details,
            headers=headers,
        )


class NotFoundException(AppException):
    def __init__(
        self,
        message: str = "Resource not found.",
        details: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            details=details,
            headers=headers,
        )


class ConflictException(AppException):
    def __init__(
        self,
        message: str = "Conflict.",
        details: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            message=message,
            details=details,
            headers=headers,
        )


class RateLimitException(AppException):
    def __init__(
        self,
        message: str = "Too many requests.",
        details: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=message,
            details=details,
            headers=headers,
        )


class InternalServerError(AppException):
    def __init__(
        self,
        message: str = "Internal server error.",
        details: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            details=details,
            headers=headers,
        )


class ValidationError(AppException):
    def __init__(
        self,
        message: str = "Validation failed.",
        details: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=message,
            details=details,
            headers=headers,
        )


class NotFoundError(AppException):
    def __init__(
        self,
        message: str = "Resource not found.",
        details: Optional[Any] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            details=details,
            headers=headers,
        )
