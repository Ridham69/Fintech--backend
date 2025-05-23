"""Authentication routes for user registration and login."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse
)
from app.auth.service import (
    register_user,
    authenticate_user,
    refresh_auth_token
)
from app.auth.jwt import (
    get_current_user_id,
    blacklist_token,
    oauth2_scheme
)
from app.crud.user import get_user_by_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Register a new user with email and password"
)
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Register a new user.
    
    Args:
        request: FastAPI request object
        user_data: User registration data
        db: Database session
        
    Returns:
        UserResponse: Created user data
    """
    logger.info(
        f"[AUTH] Registration attempt from {request.client.host} "
        f"for email: {user_data.email}"
    )
    
    user = await register_user(user_data, db)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate user and return access and refresh tokens"
)
async def login(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and generate tokens.
    
    Args:
        request: FastAPI request object
        login_data: Login credentials
        db: Database session
        
    Returns:
        TokenResponse: Access and refresh tokens
    """
    logger.info(
        f"[AUTH] Login attempt from {request.client.host} "
        f"for email: {login_data.email}"
    )
    
    # Add client IP to device info if not provided
    if not login_data.device_id:
        login_data.device_id = request.client.host
    
    user, access_token, refresh_token = await authenticate_user(login_data, db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user's data"
)
async def get_current_user(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get current user data.
    
    Args:
        current_user_id: Current user's ID from token
        db: Database session
        
    Returns:
        UserResponse: Current user data
    """
    user = await get_user_by_id(db, current_user_id)
    return UserResponse.model_validate(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh tokens",
    description="Get new access and refresh tokens using refresh token"
)
async def refresh(
    request: Request,
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh authentication tokens.
    
    Args:
        request: FastAPI request object
        refresh_token: Refresh token
        db: Database session
        
    Returns:
        TokenResponse: New access and refresh tokens
    """
    logger.info(f"[AUTH] Token refresh attempt from {request.client.host}")
    return await refresh_auth_token(refresh_token, db)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout",
    description="Logout user by blacklisting current tokens"
)
async def logout(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)]
) -> None:
    """
    Logout user by blacklisting current token.
    
    Args:
        request: FastAPI request object
        token: Current access token
    """
    await blacklist_token(token)
    logger.info(f"[AUTH] Logout from {request.client.host}")


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from all devices",
    description="Logout from all devices by blacklisting all tokens"
)
async def logout_all(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    refresh_token: str
) -> None:
    """
    Logout from all devices by blacklisting all tokens.
    
    Args:
        request: FastAPI request object
        token: Current access token
        refresh_token: Current refresh token
    """
    await blacklist_token(token)
    await blacklist_token(refresh_token)
    logger.info(f"[AUTH] Logout from all devices initiated from {request.client.host}")
