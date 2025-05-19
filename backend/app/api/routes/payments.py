"""
Payment API endpoints.

This module provides REST API endpoints for managing payment intents
and integrating with external payment providers.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.settings import settings
from app.crud import payment as payment_crud
from app.models.user import User
from app.schemas.payment import (
    PaymentIntentCreate,
    PaymentIntentList,
    PaymentIntentResponse,
    PaymentMethodConfig,
    PaymentProviderConfig,
    PaymentStatus
)
from app.core.logging import logger
from app.core.rate_limit import rate_limit
from app.core.dependencies import get_correlation_id
from app.services.payment import get_payment_provider
from app.core.cache import RedisCache

router = APIRouter(
    prefix="/payment-intents",
    tags=["payments"]
)

# Initialize Redis cache for payment state
payment_cache = RedisCache(
    prefix="payment:",
    ttl=3600  # 1 hour TTL for payment state
)

@router.post(
    "/",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(limit=settings.rate_limit.PAYMENT_RATE_LIMIT))]
)
async def create_payment_intent(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payment: PaymentIntentCreate,
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Create a new payment intent.
    
    Args:
        payment: Payment intent details
        current_user: Authenticated user
        db: Database session
        correlation_id: Request correlation ID
    
    Returns:
        Created payment intent with provider details
    
    Raises:
        HTTPException: If payment creation fails
    """
    logger.info(
        "Creating payment intent",
        extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "amount": str(payment.amount),
            "provider": payment.provider
        }
    )
    
    # Validate user can initiate payment
    if not current_user.can_initiate_payment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User cannot initiate payments"
        )
    
    try:
        # Get payment provider service
        provider = get_payment_provider(payment.provider)
        
        # Create payment intent in database
        db_payment = await payment_crud.create_payment_intent(
            db=db,
            user_id=current_user.id,
            payment=payment
        )
        
        # Initialize payment with provider
        provider_data = await provider.create_payment(
            amount=payment.amount,
            currency=payment.currency,
            payment_id=db_payment.id,
            metadata={
                "user_id": str(current_user.id),
                "email": current_user.email,
                "correlation_id": correlation_id
            }
        )
        
        # Update payment with provider data
        db_payment = await payment_crud.update_payment_intent(
            db=db,
            payment_id=db_payment.id,
            provider_intent_id=provider_data["id"],
            provider_data=provider_data
        )
        
        return db_payment
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/{payment_id}",
    response_model=PaymentIntentResponse
)
async def get_payment_intent(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific payment intent.
    
    Args:
        payment_id: Payment intent UUID
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Payment intent details
    
    Raises:
        HTTPException: If payment not found or unauthorized
    """
    payment = await payment_crud.get_payment_intent(
        db=db,
        payment_id=payment_id
    )
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment intent not found"
        )
    
    # Verify user owns payment or is admin
    if payment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this payment"
        )
    
    return payment

@router.post(
    "/{payment_id}/confirm",
    response_model=PaymentIntentResponse
)
async def confirm_payment_intent(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks,
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Confirm a payment intent (webhook endpoint).
    
    Args:
        payment_id: Payment intent UUID
        db: Database session
        background_tasks: Background task queue
        correlation_id: Request correlation ID
    
    Returns:
        Updated payment intent
    
    Raises:
        HTTPException: If payment confirmation fails
    """
    # Get payment intent
    payment = await payment_crud.get_payment_intent(
        db=db,
        payment_id=payment_id
    )
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment intent not found"
        )
    
    # Verify payment can be confirmed
    if payment.status not in [
        PaymentStatus.REQUIRES_CONFIRMATION,
        PaymentStatus.PROCESSING
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment cannot be confirmed"
        )
    
    try:
        # Get payment provider
        provider = get_payment_provider(payment.provider)
        
        # Verify payment with provider
        is_valid = await provider.verify_payment(
            payment_id=payment.provider_intent_id
        )
        
        if not is_valid:
            raise ValueError("Payment verification failed")
        
        # Update payment status
        payment = await payment_crud.update_payment_status(
            db=db,
            payment_id=payment_id,
            status=PaymentStatus.SUCCEEDED
        )
        
        # Queue transaction creation
        background_tasks.add_task(
            payment_crud.create_transaction_from_payment,
            db=db,
            payment_id=payment_id
        )
        
        return payment
        
    except ValueError as e:
        # Mark payment as failed
        await payment_crud.update_payment_status(
            db=db,
            payment_id=payment_id,
            status=PaymentStatus.FAILED,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/",
    response_model=PaymentIntentList
)
async def list_payment_intents(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[PaymentStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    List payment intents with filtering and pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by payment status
        start_date: Filter by start date
        end_date: Filter by end date
        current_user: Authenticated user
        db: Database session
    
    Returns:
        List of payment intents
    """
    payments = await payment_crud.get_user_payment_intents(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
        start_date=start_date,
        end_date=end_date
    )
    
    total = await payment_crud.get_payment_intent_count(
        db=db,
        user_id=current_user.id,
        status=status,
        start_date=start_date,
        end_date=end_date
    )
    
    return PaymentIntentList(
        items=payments,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )

@router.get(
    "/config/providers",
    response_model=list[PaymentProviderConfig]
)
async def get_payment_providers():
    """
    Get available payment provider configurations.
    
    Returns:
        List of payment provider configurations
    """
    providers = []
    
    # Razorpay configuration
    if settings.features.ENABLE_RAZORPAY:
        providers.append(
            PaymentProviderConfig(
                provider="RAZORPAY",
                is_enabled=True,
                supported_methods=[
                    PaymentMethodConfig(
                        method="UPI",
                        enabled=settings.features.ENABLE_UPI,
                        min_amount=1.00,
                        max_amount=100000.00,
                        supported_currencies=["INR"],
                        provider_config={}
                    ),
                    PaymentMethodConfig(
                        method="NETBANKING",
                        enabled=settings.features.ENABLE_NETBANKING,
                        min_amount=100.00,
                        max_amount=500000.00,
                        supported_currencies=["INR"],
                        provider_config={}
                    ),
                    PaymentMethodConfig(
                        method="CARD",
                        enabled=settings.features.ENABLE_CARDS,
                        min_amount=100.00,
                        max_amount=500000.00,
                        supported_currencies=["INR"],
                        provider_config={
                            "supported_networks": ["VISA", "MASTERCARD", "RUPAY"]
                        }
                    )
                ],
                sandbox_config={
                    "key_id": settings.external.RAZORPAY_KEY_ID.get_secret_value()
                },
                production_config={}
            )
        )
    
    return providers 