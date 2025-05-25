"""Authentication utilities for password hashing and JWT operations."""
import logging
import uuid
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, VerificationError, VerifyMismatchError
from jose import jwt, JWTError
import redis.asyncio as redis
import pyotp

from app.core.settings import settings
from app.models.user import User, UserRole
from .exceptions import (
    TokenExpiredError,
    TokenValidationError,
    TokenBlacklistedError
)

logger = logging.getLogger(__name__)

# Configure Argon2 with OWASP-recommended parameters
ph = PasswordHasher(
    time_cost=settings.auth.ARGON2_TIME_COST,
    memory_cost=settings.auth.ARGON2_MEMORY_COST,
    parallelism=settings.auth.ARGON2_PARALLELISM,
)

# Redis connection for token blacklisting
redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis connection with lazy initialization."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


def hash_password(password: str) -> str:
    """
    Hash password using Argon2id.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
        
    Raises:
        RuntimeError: If hashing fails
    """
    try:
        return ph.hash(password)
    except HashingError as e:
        logger.error("[AUTH] Password hashing failed", exc_info=e)
        raise RuntimeError("Failed to hash password") from e


def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, bool]:
    """
    Verify a password against a hash.
    Returns (is_valid, needs_rehash)
    """
    try:
        is_valid = ph.verify(hashed_password, plain_password)
        needs_rehash = ph.check_needs_rehash(hashed_password)
        return is_valid, needs_rehash
    except VerificationError:
        # Optionally, fallback to bcrypt if you support it
        try:
            import bcrypt
            is_valid = bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
            # If valid with bcrypt, you may want to rehash with Argon2
            return is_valid, is_valid  # needs_rehash = is_valid
        except Exception as e:
            logger.error("[AUTH] Password verification failed", exc_info=e)
            return False, False
    except Exception as e:
        logger.error("[AUTH] Unexpected error during password verification", exc_info=e)
        return False, False


def create_token_payload(
    user: User,
    token_type: str = "access",
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create JWT token payload.
    
    Args:
        user: User model instance
        token_type: Token type ("access" or "refresh")
        device_id: Optional device identifier
        
    Returns:
        dict: Token payload
    """
    now = datetime.now(timezone.utc)
    if token_type == "access":
        exp = now + timedelta(minutes=15)
    elif token_type == "refresh":
        exp = now + timedelta(days=7)
    else:
        raise ValueError("Invalid token type")

    payload = {
        "sub": str(user.id),
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "type": token_type,
        "device_id": device_id,
        "exp": int(exp.timestamp()),  # <-- Ensure this is an int!
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return payload


def create_token(payload: Dict[str, Any]) -> str:
    """
    Create JWT token from payload.
    
    Args:
        payload: Token payload
        
    Returns:
        str: Encoded JWT token
    """
    return jwt.encode(
        payload,
        settings.auth.JWT_SECRET_KEY,
        algorithm=settings.auth.JWT_ALGORITHM
    )


async def verify_token(
    token: str,
    expected_type: str = "access"
) -> Dict[str, Any]:
    """
    Verify JWT token and check blacklist.
    
    Args:
        token: JWT token
        expected_type: Expected token type
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        TokenExpiredError: If token has expired
        TokenBlacklistedError: If token is blacklisted
        TokenValidationError: For other validation errors
    """
    try:
        payload = jwt.decode(
            token,
            settings.auth.JWT_SECRET_KEY,
            algorithms=[settings.auth.JWT_ALGORITHM]
        )
        
        # Verify token type
        if payload.get("type") != expected_type:
            raise TokenValidationError(f"Invalid token type. Expected {expected_type}")
        
        # Check expiration
        exp = datetime.fromtimestamp(payload["exp"])
        if exp < datetime.utcnow():
            raise TokenExpiredError()
        
        # Check blacklist
        redis = await get_redis()
        is_blacklisted = await redis.get(f"blacklist:{payload['jti']}")
        if is_blacklisted:
            raise TokenBlacklistedError()
        
        return payload
        
    except JWTError as e:
        logger.error("[AUTH] JWT validation failed", exc_info=e)
        raise TokenValidationError("Invalid token")


async def blacklist_token(token: str) -> None:
    """
    Add token to blacklist.
    
    Args:
        token: JWT token to blacklist
    """
    try:
        # Decode without verification to get expiry
        payload = jwt.get_unverified_claims(token)
        exp = datetime.fromtimestamp(payload["exp"])
        ttl = int((exp - datetime.utcnow()).total_seconds())
        
        if ttl > 0:
            redis = await get_redis()
            key = f"blacklist:{payload['jti']}"
            await redis.setex(key, ttl, "1")
            logger.info(f"[AUTH] Token blacklisted: {payload['jti']}")
            
    except Exception as e:
        logger.error("[AUTH] Failed to blacklist token", exc_info=e)
        raise


def create_access_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.auth.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
        "jti": secrets.token_urlsafe(32)
    }
    
    return jwt.encode(
        to_encode,
        settings.auth.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.auth.JWT_ALGORITHM
    )


def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=settings.auth.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_urlsafe(32)
    }
    
    return jwt.encode(
        to_encode,
        settings.auth.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.auth.JWT_ALGORITHM
    )


def generate_totp_secret() -> str:
    """Generate TOTP secret for 2FA."""
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    """Verify TOTP code."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code)


def generate_backup_codes() -> Tuple[list[str], list[str]]:
    """Generate backup codes for 2FA recovery."""
    # Generate 8 backup codes
    plain_codes = [secrets.token_hex(4) for _ in range(8)]
    hashed_codes = [
        base64.b64encode(
            hashlib.sha256(code.encode()).digest()
        ).decode()
        for code in plain_codes
    ]
    return plain_codes, hashed_codes


def verify_backup_code(code: str, hashed_codes: list[str]) -> bool:
    """Verify backup code."""
    code_hash = base64.b64encode(
        hashlib.sha256(code.encode()).digest()
    ).decode()
    return code_hash in hashed_codes


def generate_csrf_token() -> str:
    """Generate CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, session_token: str) -> bool:
    """Verify CSRF token using constant-time comparison."""
    return hmac.compare_digest(token, session_token)
