"""FastAPI dependencies for authentication and authorization."""
import logging
from typing import Annotated, Optional, List
from uuid import UUID

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from app.db.session import get_db
from app.models.user import User, UserRole
from app.crud.user import get_user_by_id
from .utils import verify_token
from .exceptions import (
    TokenValidationError,
    TokenExpiredError,
    TokenBlacklistedError,
    InactiveUserError,
    UnverifiedUserError
)
from app.core.settings import settings
from app.models.admin import AdminUser, AdminScope
from app.services.admin_service import AdminService

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
    scopes={
        "user": "Standard user access",
        "admin": "Administrator access",
        "support": "Customer support access"
    }
)

# Initialize security scheme
security = HTTPBearer()

async def get_current_user(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user.
    
    Args:
        security_scopes: Required security scopes
        token: JWT access token
        db: Database session
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Verify token and get payload
        payload = await verify_token(token, expected_type="access")
        user_id = UUID(payload["sub"])
        
        # Get user from database
        user = await get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Check required scopes
        if security_scopes.scopes:
            user_scopes = _get_user_scopes(user.role)
            for scope in security_scopes.scopes:
                if scope not in user_scopes:
                    logger.warning(
                        f"[AUTH] Insufficient permissions for user {user.id}. "
                        f"Required: {scope}, Has: {user_scopes}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions",
                        headers={"WWW-Authenticate": security_scopes.scope_str},
                    )
        
        return user
        
    except (TokenValidationError, TokenExpiredError, TokenBlacklistedError) as e:
        logger.warning(f"[AUTH] Token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        InactiveUserError: If user is inactive
    """
    if not current_user.is_active:
        raise InactiveUserError()
    return current_user


async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Get current verified user.
    
    Args:
        current_user: Current active user
        
    Returns:
        User: Current verified user
        
    Raises:
        UnverifiedUserError: If user is not verified
    """
    if not current_user.is_verified:
        raise UnverifiedUserError()
    return current_user


def get_admin_user(
    current_user: Annotated[User, Security(get_current_verified_user, scopes=["admin"])]
) -> User:
    """
    Get current admin user.
    
    Args:
        current_user: Current verified user with admin scope
        
    Returns:
        User: Current admin user
    """
    return current_user


def get_support_user(
    current_user: Annotated[User, Security(get_current_verified_user, scopes=["support"])]
) -> User:
    """
    Get current support user.
    
    Args:
        current_user: Current verified user with support scope
        
    Returns:
        User: Current support user
    """
    return current_user


def _get_user_scopes(role: UserRole) -> list[str]:
    """
    Get allowed scopes for user role.
    
    Args:
        role: User role
        
    Returns:
        list[str]: List of allowed scopes
    """
    base_scopes = ["user"]
    
    if role == UserRole.ADMIN:
        return base_scopes + ["admin", "support"]
    elif role == UserRole.SUPPORT:
        return base_scopes + ["support"]
    else:
        return base_scopes


async def get_current_admin(
    required_scopes: List[AdminScope],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """
    Get current admin user with required scopes.
    
    Args:
        required_scopes: List of required admin scopes
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        AdminUser instance
        
    Raises:
        HTTPException: If token is invalid or admin lacks required scopes
    """
    try:
        # Decode JWT token
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.auth.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.auth.JWT_ALGORITHM]
        )
        
        # Get user ID from token
        user_id: UUID = UUID(payload.get("sub"))
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Get admin user
        admin_service = AdminService(db)
        admin_user = await admin_service.get_admin_user(user_id)
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not an admin"
            )
        
        # Check if admin is active
        if not admin_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account is disabled"
            )
        
        # Check required scopes
        if not admin_user.has_all_scopes(required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return admin_user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

async def get_current_admin_read(
    admin: AdminUser = Depends(lambda: get_current_admin([AdminScope.READ_USERS]))
) -> AdminUser:
    """Get current admin with read scope."""
    return admin

async def get_current_admin_act(
    admin: AdminUser = Depends(lambda: get_current_admin([AdminScope.ACT_FREEZE]))
) -> AdminUser:
    """Get current admin with action scope."""
    return admin

async def get_current_super_admin(
    admin: AdminUser = Depends(lambda: get_current_admin([AdminScope.ACT_SYSTEM]))
) -> AdminUser:
    """Get current super admin."""
    return admin 
