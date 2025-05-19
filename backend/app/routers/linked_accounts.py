"""
Linked Account Router

This module provides endpoints for managing linked accounts.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_verified_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.linked_accounts import (
    LinkedAccountCreate,
    LinkedAccountUpdate,
    LinkedAccountResponse,
    LinkedAccountList
)
from app.services.linked_accounts import LinkedAccountService

router = APIRouter(prefix="/linked-accounts", tags=["linked-accounts"])

@router.post("", response_model=LinkedAccountResponse)
async def create_linked_account(
    account_data: LinkedAccountCreate,
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new linked account.
    
    Args:
        account_data: Account data
        request: FastAPI request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created linked account
    """
    service = LinkedAccountService(db)
    return await service.create_linked_account(
        current_user.id,
        account_data,
        request
    )

@router.get("", response_model=LinkedAccountList)
async def list_linked_accounts(
    active_only: bool = True,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all linked accounts for current user.
    
    Args:
        active_only: Whether to return only active accounts
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of linked accounts
    """
    service = LinkedAccountService(db)
    accounts = await service.get_user_accounts(
        current_user.id,
        active_only
    )
    return LinkedAccountList(
        items=accounts,
        total=len(accounts)
    )

@router.patch("/{account_id}", response_model=LinkedAccountResponse)
async def update_linked_account(
    account_id: UUID,
    update_data: LinkedAccountUpdate,
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a linked account.
    
    Args:
        account_id: Account ID
        update_data: Update data
        request: FastAPI request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated linked account
    """
    service = LinkedAccountService(db)
    return await service.update_linked_account(
        account_id,
        current_user.id,
        update_data,
        request
    )

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_linked_account(
    account_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a linked account.
    
    Args:
        account_id: Account ID
        request: FastAPI request
        current_user: Current authenticated user
        db: Database session
    """
    service = LinkedAccountService(db)
    await service.delete_linked_account(
        account_id,
        current_user.id,
        request
    ) 