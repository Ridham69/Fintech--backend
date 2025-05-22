"""Custom exceptions for authentication-related errors."""
from fastapi import HTTPException, status


class AuthError(HTTPException):
    """Base class for authentication errors."""
    
    def __init__(self, detail: str):
        """Initialize with status code and WWW-Authenticate header."""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""
    
    def __init__(self):
        super().__init__("Invalid email or password")


class InactiveUserError(AuthError):
    """Raised when user account is inactive."""
    
    def __init__(self):
        super().__init__("User account is inactive")


class UnverifiedUserError(AuthError):
    """Raised when user account is not verified."""
    
    def __init__(self):
        super().__init__("User account is not verified")


class TokenExpiredError(AuthError):
    """Raised when JWT token has expired."""
    
    def __init__(self):
        super().__init__("Token has expired")


class TokenBlacklistedError(AuthError):
    """Raised when JWT token is blacklisted."""
    
    def __init__(self):
        super().__init__("Token has been revoked")


class TokenValidationError(AuthError):
    """Raised when JWT token validation fails."""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)


class AccountLockedError(AuthError):
    """Raised when account is locked due to too many failed attempts."""
    
    def __init__(self, minutes: int):
        super().__init__(
            f"Account is locked due to too many failed attempts. "
            f"Try again in {minutes} minutes"
        )


class PasswordMismatchError(HTTPException):
    """Raised when password confirmation doesn't match."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and confirmation do not match"
        )


class EmailAlreadyRegisteredError(HTTPException):
    """Raised when email is already registered."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered"
        ) 
