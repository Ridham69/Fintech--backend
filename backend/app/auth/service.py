"""Authentication service with business logic."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, TokenResponse
from app.crud.user import (
    get_user_by_email,
    create_user,
    get_user_by_id,
    update_last_login,
    increment_failed_attempts
)
from .exceptions import (
    InvalidCredentialsError,
    InactiveUserError,
    UnverifiedUserError,
    AccountLockedError,
    PasswordMismatchError,
    EmailAlreadyRegisteredError
)
from .hashing import verify_password
from .jwt import create_token_pair, verify_token, blacklist_token

logger = logging.getLogger(__name__)

# Constants
# MAX_LOGIN_ATTEMPTS = 5 # Replaced by settings.auth.MAX_LOGIN_ATTEMPTS
LOCKOUT_MINUTES = 15


async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        User: Created user
        
    Raises:
        PasswordMismatchError: If passwords don't match
        EmailAlreadyRegisteredError: If email is already registered
    """
    # Validate password match
    if user_data.password != user_data.confirm_password:
        logger.warning("[AUTH] Password mismatch during registration")
        raise PasswordMismatchError()
    
    # Check if email exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        logger.warning(f"[AUTH] Registration attempt with existing email: {user_data.email}")
        raise EmailAlreadyRegisteredError()
    
    # Create user
    user = await create_user(db, user_data)
    logger.info(f"[AUTH] Successfully registered user: {user.email}")
    
    return user


async def authenticate_user(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Tuple[User, str, str]:
    """
    Authenticate user and generate tokens.
    
    Args:
        login_data: Login credentials
        db: Database session
        
    Returns:
        Tuple[User, str, str]: User, access token, and refresh token
        
    Raises:
        InvalidCredentialsError: If credentials are invalid
        InactiveUserError: If user account is inactive
        UnverifiedUserError: If user account is not verified
        AccountLockedError: If account is locked due to too many failed attempts
    """
    # Get user
    user = await get_user_by_email(db, login_data.email)
    if not user:
        logger.warning(f"[AUTH] Login attempt with non-existent email: {login_data.email}")
        raise InvalidCredentialsError()
    
    # Check if account is locked
    if user.failed_login_attempts >= settings.auth.MAX_LOGIN_ATTEMPTS:
        lockout_time = user.last_login + timedelta(minutes=LOCKOUT_MINUTES)
        if datetime.utcnow() < lockout_time:
            remaining_minutes = int((lockout_time - datetime.utcnow()).total_seconds() / 60)
            logger.warning(f"[AUTH] Attempt to login to locked account: {user.email}")
            raise AccountLockedError(remaining_minutes)
    
    # Verify password
    is_valid, needs_rehash = verify_password(login_data.password, user.hashed_password)
    if not is_valid:
        attempts = await increment_failed_attempts(db, user.id)
        logger.warning(f"[AUTH] Failed login attempt for user: {user.email} (attempts: {attempts})")
        raise InvalidCredentialsError()
    
    # Check account status
    if not user.is_active:
        logger.warning(f"[AUTH] Login attempt on inactive account: {user.email}")
        raise InactiveUserError()
    
    if not user.is_verified:
        logger.warning(f"[AUTH] Login attempt on unverified account: {user.email}")
        raise UnverifiedUserError()
    
    # Generate tokens
    access_token, refresh_token = create_token_pair(
        user.id,
        login_data.device_id
    )
    
    # Update last login
    await update_last_login(db, user.id)
    
    logger.info(f"[AUTH] Successful login for user: {user.email}")
    return user, access_token, refresh_token


async def refresh_auth_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh authentication tokens.
    
    Args:
        refresh_token: Refresh token
        db: Database session
        
    Returns:
        TokenResponse: New access and refresh tokens
    """
    # Verify refresh token
    token_data = await verify_token(refresh_token, token_type="refresh")
    
    # Get user
    user = await get_user_by_id(db, UUID(token_data.sub))
    if not user or not user.is_active:
        logger.warning(f"[AUTH] Refresh attempt for invalid/inactive user: {token_data.sub}")
        raise InvalidCredentialsError()
    
    # Generate new tokens
    new_access_token, new_refresh_token = create_token_pair(
        user.id,
        token_data.device_id
    )
    
    # Blacklist old refresh token
    await blacklist_token(refresh_token)
    
    logger.info(f"[AUTH] Refreshed tokens for user: {user.email}")
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    ) 
