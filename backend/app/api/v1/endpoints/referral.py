"""
Referral Router

This module provides API endpoints for the referral system.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.models.user import User
from app.schemas.referral import (
    ReferralCodeCreate,
    ReferralCodeResponse,
    ReferralResponse,
    ReferralStats,
    UseReferralCode
)
from app.services.referral import ReferralService

router = APIRouter()

@router.post(
    "/use-code",
    response_model=ReferralResponse,
    status_code=status.HTTP_201_CREATED
)
async def use_referral_code(
    *,
    request: Request,
    data: UseReferralCode,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> ReferralResponse:
    """
    Use a referral code.
    
    Args:
        request: FastAPI request
        data: Referral code data
        db: Database session
        current_user: Current user
        
    Returns:
        Created referral
        
    Raises:
        HTTPException: If validation fails
    """
    service = ReferralService(db)
    
    try:
        # Get IP address
        ip_address = request.client.host if request.client else None
        
        # Register invite
        referral = await service.register_invite(
            inviter_code=data.code,
            invitee_user_id=current_user.id,
            ip_address=ip_address,
            device_fingerprint=data.device_fingerprint
        )
        
        return ReferralResponse.model_validate(referral)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/my-stats",
    response_model=ReferralStats
)
async def get_referral_stats(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> ReferralStats:
    """
    Get user's referral statistics.
    
    Args:
        db: Database session
        current_user: Current user
        
    Returns:
        Referral statistics
    """
    service = ReferralService(db)
    
    # Get stats
    total, successful, pending, rewards, code = await service.get_referral_stats(
        current_user.id
    )
    
    if not code:
        # Create referral code if user doesn't have one
        code = await service.create_referral_code(
            current_user.id,
            ReferralCodeCreate()
        )
    
    return ReferralStats(
        total_referrals=total,
        successful_referrals=successful,
        pending_referrals=pending,
        total_rewards=rewards,
        referral_code=ReferralCodeResponse.model_validate(code)
    )

@router.get(
    "/my-code",
    response_model=ReferralCodeResponse
)
async def get_referral_code(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> ReferralCodeResponse:
    """
    Get user's referral code.
    
    Args:
        db: Database session
        current_user: Current user
        
    Returns:
        Referral code
        
    Raises:
        HTTPException: If user doesn't have a referral code
    """
    service = ReferralService(db)
    
    # Get referral code
    code = await service.get_referral_code(current_user.id)
    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral code not found"
        )
    
    return ReferralCodeResponse.model_validate(code)

@router.post(
    "/my-code",
    response_model=ReferralCodeResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_referral_code(
    *,
    data: ReferralCodeCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> ReferralCodeResponse:
    """
    Create a referral code for the current user.
    
    Args:
        data: Referral code data
        db: Database session
        current_user: Current user
        
    Returns:
        Created referral code
        
    Raises:
        HTTPException: If user already has a referral code
    """
    service = ReferralService(db)
    
    try:
        code = await service.create_referral_code(
            current_user.id,
            data
        )
        return ReferralCodeResponse.model_validate(code)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/my-referrals",
    response_model=List[ReferralResponse]
)
async def get_referrals(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> List[ReferralResponse]:
    """
    Get user's referrals.
    
    Args:
        db: Database session
        current_user: Current user
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of referrals
    """
    service = ReferralService(db)
    
    # Get referrals
    referrals = await service.get_referrals(
        current_user.id,
        skip=skip,
        limit=limit
    )
    
    return [
        ReferralResponse.model_validate(referral)
        for referral in referrals
    ] 