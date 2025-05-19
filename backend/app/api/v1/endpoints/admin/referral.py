"""
Admin Referral Router

This module provides admin API endpoints for the referral system.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.models.user import User
from app.schemas.referral import (
    ReferralCampaignCreate,
    ReferralCampaignResponse,
    ReferralCampaignUpdate,
    ReferralResponse,
    ReferralUpdate
)
from app.services.referral import ReferralService

router = APIRouter()

@router.get(
    "/referrals",
    response_model=List[ReferralResponse]
)
async def list_referrals(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    campaign_id: Optional[str] = None,
    inviter_id: Optional[UUID] = None,
    invitee_id: Optional[UUID] = None
) -> List[ReferralResponse]:
    """
    List referrals with filters.
    
    Args:
        db: Database session
        current_user: Current admin user
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status
        campaign_id: Filter by campaign ID
        inviter_id: Filter by inviter ID
        invitee_id: Filter by invitee ID
        
    Returns:
        List of referrals
    """
    service = ReferralService(db)
    
    # Get referrals
    referrals = await service.list_referrals(
        skip=skip,
        limit=limit,
        status=status,
        campaign_id=campaign_id,
        inviter_id=inviter_id,
        invitee_id=invitee_id
    )
    
    return [
        ReferralResponse.model_validate(referral)
        for referral in referrals
    ]

@router.get(
    "/referrals/{referral_id}",
    response_model=ReferralResponse
)
async def get_referral(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user),
    referral_id: UUID
) -> ReferralResponse:
    """
    Get referral by ID.
    
    Args:
        db: Database session
        current_user: Current admin user
        referral_id: Referral ID
        
    Returns:
        Referral
        
    Raises:
        HTTPException: If referral not found
    """
    service = ReferralService(db)
    
    # Get referral
    referral = await service.get_referral(referral_id)
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral not found"
        )
    
    return ReferralResponse.model_validate(referral)

@router.patch(
    "/referrals/{referral_id}",
    response_model=ReferralResponse
)
async def update_referral(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user),
    referral_id: UUID,
    data: ReferralUpdate
) -> ReferralResponse:
    """
    Update referral.
    
    Args:
        db: Database session
        current_user: Current admin user
        referral_id: Referral ID
        data: Update data
        
    Returns:
        Updated referral
        
    Raises:
        HTTPException: If referral not found or update fails
    """
    service = ReferralService(db)
    
    try:
        # Update referral
        referral = await service.update_referral(
            referral_id,
            data
        )
        return ReferralResponse.model_validate(referral)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post(
    "/campaigns",
    response_model=ReferralCampaignResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_campaign(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user),
    data: ReferralCampaignCreate
) -> ReferralCampaignResponse:
    """
    Create referral campaign.
    
    Args:
        db: Database session
        current_user: Current admin user
        data: Campaign data
        
    Returns:
        Created campaign
        
    Raises:
        HTTPException: If creation fails
    """
    service = ReferralService(db)
    
    try:
        campaign = await service.create_campaign(data)
        return ReferralCampaignResponse.model_validate(campaign)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/campaigns",
    response_model=List[ReferralCampaignResponse]
)
async def list_campaigns(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user),
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None
) -> List[ReferralCampaignResponse]:
    """
    List referral campaigns.
    
    Args:
        db: Database session
        current_user: Current admin user
        skip: Number of records to skip
        limit: Maximum number of records to return
        is_active: Filter by active status
        
    Returns:
        List of campaigns
    """
    service = ReferralService(db)
    
    # Get campaigns
    campaigns = await service.list_campaigns(
        skip=skip,
        limit=limit,
        is_active=is_active
    )
    
    return [
        ReferralCampaignResponse.model_validate(campaign)
        for campaign in campaigns
    ]

@router.get(
    "/campaigns/{campaign_id}",
    response_model=ReferralCampaignResponse
)
async def get_campaign(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user),
    campaign_id: str
) -> ReferralCampaignResponse:
    """
    Get campaign by ID.
    
    Args:
        db: Database session
        current_user: Current admin user
        campaign_id: Campaign ID
        
    Returns:
        Campaign
        
    Raises:
        HTTPException: If campaign not found
    """
    service = ReferralService(db)
    
    # Get campaign
    campaign = await service.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return ReferralCampaignResponse.model_validate(campaign)

@router.patch(
    "/campaigns/{campaign_id}",
    response_model=ReferralCampaignResponse
)
async def update_campaign(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user),
    campaign_id: str,
    data: ReferralCampaignUpdate
) -> ReferralCampaignResponse:
    """
    Update campaign.
    
    Args:
        db: Database session
        current_user: Current admin user
        campaign_id: Campaign ID
        data: Update data
        
    Returns:
        Updated campaign
        
    Raises:
        HTTPException: If campaign not found or update fails
    """
    service = ReferralService(db)
    
    try:
        # Update campaign
        campaign = await service.update_campaign(
            campaign_id,
            data
        )
        return ReferralCampaignResponse.model_validate(campaign)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 