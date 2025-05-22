"""
Linked Account Service

This module provides services for managing linked accounts.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.linked_accounts import LinkedAccount, AccountType
from app.models.user import User
from app.schemas.linked_accounts import LinkedAccountCreate, LinkedAccountUpdate

# Initialize logger
logger = get_logger(__name__)

class LinkedAccountService:
    """Service for managing linked accounts."""
    
    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
    
    async def create_linked_account(
        self,
        user_id: UUID,
        account_data: LinkedAccountCreate,
        request: Request
    ) -> LinkedAccount:
        """
        Create a new linked account.
        
        Args:
            user_id: User ID
            account_data: Account data
            request: FastAPI request object
            
        Returns:
            Created LinkedAccount instance
            
        Raises:
            HTTPException: If account already exists or validation fails
        """
        # Check if user exists
        user = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        if not user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if account already exists
        existing = await self.db.execute(
            select(LinkedAccount)
            .where(
                and_(
                    LinkedAccount.user_id == user_id,
                    LinkedAccount.account_ref_id == account_data.account_ref_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already linked"
            )
        
        # Handle primary account logic
        if account_data.is_primary:
            await self._unset_primary_account(user_id)
        
        # Create account
        account = LinkedAccount(
            user_id=user_id,
            **account_data.model_dump()
        )
        
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        
        logger.info(
            f"Linked account created",
            extra={
                "user_id": user_id,
                "account_id": account.id,
                "account_type": account.account_type
            }
        )
        
        return account
    
    async def get_user_accounts(
        self,
        user_id: UUID,
        active_only: bool = True
    ) -> List[LinkedAccount]:
        """
        Get all linked accounts for a user.
        
        Args:
            user_id: User ID
            active_only: Whether to return only active accounts
            
        Returns:
            List of LinkedAccount instances
        """
        query = select(LinkedAccount).where(LinkedAccount.user_id == user_id)
        
        if active_only:
            query = query.where(LinkedAccount.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_linked_account(
        self,
        account_id: UUID,
        user_id: UUID,
        update_data: LinkedAccountUpdate,
        request: Request
    ) -> LinkedAccount:
        """
        Update a linked account.
        
        Args:
            account_id: Account ID
            user_id: User ID
            update_data: Update data
            request: FastAPI request object
            
        Returns:
            Updated LinkedAccount instance
            
        Raises:
            HTTPException: If account not found or validation fails
        """
        # Get account
        account = await self.db.execute(
            select(LinkedAccount)
            .where(
                and_(
                    LinkedAccount.id == account_id,
                    LinkedAccount.user_id == user_id
                )
            )
        )
        account = account.scalar_one_or_none()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Linked account not found"
            )
        
        # Handle primary account logic
        if update_data.is_primary and not account.is_primary:
            await self._unset_primary_account(user_id)
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(account, field, value)
        
        await self.db.commit()
        await self.db.refresh(account)
        
        logger.info(
            f"Linked account updated",
            extra={
                "user_id": user_id,
                "account_id": account.id,
                "changes": update_data.model_dump(exclude_unset=True)
            }
        )
        
        return account
    
    async def delete_linked_account(
        self,
        account_id: UUID,
        user_id: UUID,
        request: Request
    ) -> None:
        """
        Delete a linked account.
        
        Args:
            account_id: Account ID
            user_id: User ID
            request: FastAPI request object
            
        Raises:
            HTTPException: If account not found or is primary
        """
        # Get account
        account = await self.db.execute(
            select(LinkedAccount)
            .where(
                and_(
                    LinkedAccount.id == account_id,
                    LinkedAccount.user_id == user_id
                )
            )
        )
        account = account.scalar_one_or_none()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Linked account not found"
            )
        
        # Check if primary
        if account.is_primary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete primary account"
            )
        
        # Delete account
        await self.db.delete(account)
        await self.db.commit()
        
        logger.info(
            f"Linked account deleted",
            extra={
                "user_id": user_id,
                "account_id": account.id
            }
        )
    
    async def _unset_primary_account(self, user_id: UUID) -> None:
        """
        Unset primary flag for all user's accounts.
        
        Args:
            user_id: User ID
        """
        await self.db.execute(
            select(LinkedAccount)
            .where(
                and_(
                    LinkedAccount.user_id == user_id,
                    LinkedAccount.is_primary == True
                )
            )
            .update({"is_primary": False})
        )
        await self.db.commit() 
