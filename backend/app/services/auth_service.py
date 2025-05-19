"""
Authentication Service Module

This module handles user authentication, registration, and email verification.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthError
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserOut
from app.services.email_service import EmailService
from app.utils.security import hash_password

async def get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
    """
    Get user by email address.
    
    Args:
        email: User's email address
        db: Database session
        
    Returns:
        User instance if found, None otherwise
    """
    return await db.query(User).filter(User.email == email).first()

async def get_user_by_id(user_id: UUID, db: AsyncSession) -> Optional[User]:
    """
    Get user by ID.
    
    Args:
        user_id: User's ID
        db: Database session
        
    Returns:
        User instance if found, None otherwise
    """
    return await db.query(User).filter(User.id == user_id).first()

def create_verification_token(user_id: UUID) -> str:
    """
    Create email verification token.
    
    Args:
        user_id: User's ID
        
    Returns:
        JWT token string
    """
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=24),  # 24 hour expiry
        "type": "email_verification"
    }
    return jwt.encode(
        payload,
        settings.auth.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.auth.JWT_ALGORITHM
    )

async def verify_email_token(token: str, db: AsyncSession) -> User:
    """
    Verify email verification token and activate user.
    
    Args:
        token: Verification token
        db: Database session
        
    Returns:
        Updated User instance
        
    Raises:
        AuthError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.auth.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.auth.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "email_verification":
            raise AuthError("Invalid token type")
            
        user_id = UUID(payload.get("sub"))
        user = await get_user_by_id(user_id, db)
        
        if not user:
            raise AuthError("User not found")
            
        if user.is_verified:
            raise AuthError("Email already verified")
            
        user.is_verified = True
        user.verified_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
        
        return user
        
    except jwt.JWTError:
        raise AuthError("Invalid or expired token")

async def register_user(user_data: UserCreate, db: AsyncSession) -> UserOut:
    """
    Register new user and send verification email.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        Created User instance
        
    Raises:
        HTTPException: If email already registered
    """
    # Check if email already registered
    existing_user = await get_user_by_email(user_data.email, db)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        is_active=True,  # Account active but needs email verification
        is_verified=False,
        role=UserRole.USER
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Send verification email
    try:
        verification_token = create_verification_token(new_user.id)
        await EmailService.send_verification_email(
            email=new_user.email,
            token=verification_token,
            user_name=new_user.full_name
        )
    except Exception as e:
        # Log error but don't fail registration
        logger.error(f"Failed to send verification email: {str(e)}")
    
    return UserOut.from_orm(new_user)

async def resend_verification_email(user_id: UUID, db: AsyncSession) -> bool:
    """
    Resend verification email to user.
    
    Args:
        user_id: User's ID
        db: Database session
        
    Returns:
        True if email was sent successfully
        
    Raises:
        AuthError: If user not found or already verified
    """
    user = await get_user_by_id(user_id, db)
    if not user:
        raise AuthError("User not found")
        
    if user.is_verified:
        raise AuthError("Email already verified")
    
    verification_token = create_verification_token(user.id)
    return await EmailService.send_verification_email(
        email=user.email,
        token=verification_token,
        user_name=user.full_name
    ) 