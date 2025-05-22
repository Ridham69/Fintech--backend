"""JWT token generation and validation with Redis blacklisting."""
import logging
from datetime import datetime, timedelta
import uuid
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
import redis.asyncio as redis

from app.core.config import settings
from app.schemas.user import TokenPayload
from .exceptions import TokenBlacklistedError, TokenExpiredError, TokenValidationError

logger = logging.getLogger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Redis connection for token blacklisting
redis_client: Optional[redis.Redis] = None

async def get_redis() -> redis.Redis:
    """Get Redis connection."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client

def create_token_pair(
    user_id: uuid.UUID,
    device_id: Optional[str] = None
) -> Tuple[str, str]:
    """
    Create access and refresh token pair.
    
    Args:
        user_id: User's UUID
        device_id: Optional device identifier
        
    Returns:
        Tuple[str, str]: Access token and refresh token
    """
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())
    
    # Common payload data
    now = datetime.utcnow()
    payload_common = {
        "sub": str(user_id),
        "iat": now,
        "iss": settings.JWT_ISSUER,
        "device_id": device_id
    }
    
    # Access token - short lived
    access_token = jwt.encode(
        {
            **payload_common,
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            "jti": access_jti,
            "type": "access"
        },
        settings.auth.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    # Refresh token - long lived
    refresh_token = jwt.encode(
        {
            **payload_common,
            "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            "jti": refresh_jti,
            "type": "refresh"
        },
        settings.auth.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    logger.info(f"[AUTH] Generated token pair for user {user_id}")
    return access_token, refresh_token

async def verify_token(token: str, token_type: str = "access") -> TokenPayload:
    """
    Verify JWT token and check blacklist.
    
    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenPayload: Decoded token payload
        
    Raises:
        TokenExpiredError: If token has expired
        TokenBlacklistedError: If token is blacklisted
        TokenValidationError: For other validation errors
    """
    try:
        payload = jwt.decode(
            token,
            settings.auth.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        # Verify token type
        if token_data.type != token_type:
            raise TokenValidationError(f"Invalid token type. Expected {token_type}")
            
        # Check expiration
        if datetime.fromtimestamp(token_data.exp) < datetime.utcnow():
            raise TokenExpiredError()
            
        # Check blacklist
        redis = await get_redis()
        is_blacklisted = await redis.get(f"blacklist:{token_data.jti}")
        if is_blacklisted:
            raise TokenBlacklistedError()
            
        return token_data
        
    except JWTError as e:
        logger.error("[AUTH] JWT validation failed", exc_info=e)
        raise TokenValidationError("Invalid token")
    except ValidationError as e:
        logger.error("[AUTH] Token payload validation failed", exc_info=e)
        raise TokenValidationError("Invalid token payload")

async def blacklist_token(token: str) -> None:
    """
    Add token to blacklist in Redis.
    
    Args:
        token: JWT token to blacklist
    """
    try:
        # Decode without verification to get expiry
        payload = jwt.get_unverified_claims(token)
        token_data = TokenPayload(**payload)
        
        # Calculate TTL
        expires_at = datetime.fromtimestamp(token_data.exp)
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        
        if ttl > 0:
            redis = await get_redis()
            await redis.setex(
                f"blacklist:{token_data.jti}",
                ttl,
                "1"
            )
            logger.info(f"[AUTH] Token {token_data.jti} blacklisted")
            
    except Exception as e:
        logger.error("[AUTH] Failed to blacklist token", exc_info=e)
        raise

async def get_current_user_id(
    token: str = Depends(oauth2_scheme)
) -> uuid.UUID:
    """
    FastAPI dependency to get current user ID from token.
    
    Args:
        token: JWT token from request
        
    Returns:
        UUID: Current user's ID
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        token_data = await verify_token(token)
        return uuid.UUID(token_data.sub)
    except (TokenExpiredError, TokenBlacklistedError, TokenValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        ) 
