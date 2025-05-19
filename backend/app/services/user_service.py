"""
User Service Module

This module handles user-related business logic.
"""

from datetime import datetime
from typing import Optional

from app.core.logging import get_logger
from app.email import email_service
from app.models.user import User
from app.schemas.user import UserCreate

# Initialize logger
logger = get_logger(__name__)

async def register_user(user_data: UserCreate) -> User:
    """
    Register a new user and send welcome email.
    
    Args:
        user_data: User registration data
        
    Returns:
        Created user instance
        
    Raises:
        ValueError: If email already registered
    """
    try:
        # Create user (existing logic)
        user = User(**user_data.dict())
        # ... existing user creation logic ...
        
        # Send welcome email
        await email_service.send_email(
            to_emails=user.email,
            subject="Welcome to AutoInvest!",
            template_name="registration.html",
            template_data={
                "user": user,
                "verification_url": f"https://app.autoinvest.com/verify/{user.verification_token}",
                "year": datetime.now().year
            }
        )
        
        logger.info(
            "User registered successfully",
            extra={
                "user_id": user.id,
                "email": user.email
            }
        )
        
        return user
        
    except Exception as e:
        logger.error(
            "Failed to register user",
            exc_info=True,
            extra={
                "email": user_data.email,
                "error": str(e)
            }
        )
        raise 