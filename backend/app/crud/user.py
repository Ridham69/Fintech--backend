"""CRUD operations for user management."""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.user import User
from app.schemas.user import UserCreate
from app.auth.hashing import hash_password

logger = logging.getLogger(__name__)


async def get_user_by_email(
    db: AsyncSession,
    email: str
) -> Optional[User]:
    """
    Get user by email.
    
    Args:
        db: Database session
        email: User's email
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_id(
    db: AsyncSession,
    user_id: UUID
) -> Optional[User]:
    """
    Get user by ID.
    
    Args:
        db: Database session
        user_id: User's UUID
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    user_data: UserCreate
) -> User:
    """
    Create new user.
    
    Args:
        db: Database session
        user_data: User creation data
        
    Returns:
        User: Created user
        
    Raises:
        EmailAlreadyRegisteredError: If email is already registered
    """
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    user = User(
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"[AUTH] Created new user: {user.email}")
    return user


async def update_last_login(
    db: AsyncSession,
    user_id: UUID
) -> None:
    """
    Update user's last login timestamp.
    
    Args:
        db: Database session
        user_id: User's UUID
    """
    query = (
        update(User)
        .where(User.id == user_id)
        .values(
            last_login=db.query(func.now()),
            failed_login_attempts=0
        )
    )
    await db.execute(query)
    await db.commit()


async def increment_failed_attempts(
    db: AsyncSession,
    user_id: UUID
) -> int:
    """
    Increment failed login attempts counter.
    
    Args:
        db: Database session
        user_id: User's UUID
        
    Returns:
        int: New number of failed attempts
    """
    query = (
        update(User)
        .where(User.id == user_id)
        .values(
            failed_login_attempts=User.failed_login_attempts + 1
        )
        .returning(User.failed_login_attempts)
    )
    result = await db.execute(query)
    await db.commit()
    return result.scalar_one()


async def reset_failed_attempts(
    db: AsyncSession,
    user_id: UUID
) -> None:
    """
    Reset failed login attempts counter.
    
    Args:
        db: Database session
        user_id: User's UUID
    """
    query = (
        update(User)
        .where(User.id == user_id)
        .values(failed_login_attempts=0)
    )
    await db.execute(query)
    await db.commit() 
