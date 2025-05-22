"""
Transaction API endpoints.

This module provides REST API endpoints for managing transactions,
including creation, listing, and retrieval of transaction records.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.settings import settings
from app.crud import transaction as transaction_crud
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionList,
    TransactionResponse,
    TransactionStats,
    TransactionType
)
from app.core.logging import logger
from app.core.rate_limit import rate_limit
from app.core.dependencies import get_correlation_id

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"]
)

@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(limit=settings.rate_limit.PAYMENT_RATE_LIMIT))]
)
async def create_transaction(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    transaction: TransactionCreate,
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Create a new transaction.
    
    Args:
        transaction: Transaction details
        current_user: Authenticated user
        db: Database session
        correlation_id: Request correlation ID
    
    Returns:
        Created transaction
    
    Raises:
        HTTPException: If transaction creation fails
    """
    logger.info(
        "Creating transaction",
        extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "amount": str(transaction.amount),
            "type": transaction.type
        }
    )
    
    # Validate user can perform transaction
    if not current_user.can_initiate_payment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User cannot initiate transactions"
        )
    
    try:
        db_transaction = await transaction_crud.create_transaction(
            db=db,
            user_id=current_user.id,
            transaction=transaction
        )
        return db_transaction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/",
    response_model=TransactionList
)
async def list_transactions(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    transaction_type: Optional[TransactionType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    List user transactions with filtering and pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        transaction_type: Filter by transaction type
        start_date: Filter by start date
        end_date: Filter by end date
        current_user: Authenticated user
        db: Database session
    
    Returns:
        List of transactions
    """
    transactions = await transaction_crud.get_user_transactions(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date
    )
    
    total = await transaction_crud.get_transaction_count(
        db=db,
        user_id=current_user.id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date
    )
    
    return TransactionList(
        items=transactions,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )

@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse
)
async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific transaction.
    
    Args:
        transaction_id: Transaction UUID
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Transaction details
    
    Raises:
        HTTPException: If transaction not found or unauthorized
    """
    transaction = await transaction_crud.get_transaction(
        db=db,
        transaction_id=transaction_id
    )
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Verify user owns transaction or is admin
    if transaction.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this transaction"
        )
    
    return transaction

@router.get(
    "/stats/summary",
    response_model=TransactionStats
)
async def get_transaction_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Get transaction statistics for the user.
    
    Args:
        start_date: Filter by start date
        end_date: Filter by end date
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Transaction statistics
    """
    return await transaction_crud.get_transaction_stats(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )

@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user)]
)
async def delete_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a transaction (admin only).
    
    Args:
        transaction_id: Transaction UUID
        current_user: Authenticated user
        db: Database session
    
    Raises:
        HTTPException: If not authorized or transaction not found
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete transactions"
        )
    
    transaction = await transaction_crud.get_transaction(
        db=db,
        transaction_id=transaction_id
    )
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    await transaction_crud.delete_transaction(
        db=db,
        transaction_id=transaction_id
    ) 
