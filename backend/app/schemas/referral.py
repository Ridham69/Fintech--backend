"""
Referral Schemas

This module defines Pydantic schemas for the referral system.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.models.referral import ReferralStatus, RewardType

class ReferralCodeBase(BaseModel):
    """Base schema for referral code."""
    
    code: str = Field(..., min_length=6, max_length=10)
    is_active: bool = True
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None

class ReferralCodeCreate(ReferralCodeBase):
    """Schema for creating a referral code."""
    pass

class ReferralCodeUpdate(ReferralCodeBase):
    """Schema for updating a referral code."""
    pass

class ReferralCodeResponse(ReferralCodeBase):
    """Schema for referral code response."""
    
    id: UUID
    user_id: UUID
    current_uses: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReferralBase(BaseModel):
    """Base schema for referral."""
    
    inviter_user_id: UUID
    invitee_user_id: UUID
    reward_type: RewardType
    reward_amount: float = Field(..., gt=0)
    reward_currency: str = Field(..., min_length=3, max_length=3)
    campaign_id: Optional[str] = None
    notes: Optional[str] = None

class ReferralCreate(ReferralBase):
    """Schema for creating a referral."""
    pass

class ReferralUpdate(BaseModel):
    """Schema for updating a referral."""
    
    status: Optional[ReferralStatus] = None
    reward_type: Optional[RewardType] = None
    reward_amount: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None

class ReferralResponse(ReferralBase):
    """Schema for referral response."""
    
    id: UUID
    status: ReferralStatus
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None
    created_at: datetime
    rewarded_at: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReferralStats(BaseModel):
    """Schema for referral statistics."""
    
    total_referrals: int
    successful_referrals: int
    pending_referrals: int
    total_rewards: float
    referral_code: ReferralCodeResponse
    
    class Config:
        from_attributes = True

class ReferralCampaignBase(BaseModel):
    """Base schema for referral campaign."""
    
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    reward_type: RewardType
    reward_amount: float = Field(..., gt=0)
    reward_currency: str = Field(..., min_length=3, max_length=3)
    min_invitee_kyc: bool = True
    min_invitee_transaction: bool = True
    min_transaction_amount: Optional[float] = Field(None, gt=0)
    max_referrals_per_user: Optional[int] = Field(None, gt=0)
    is_active: bool = True
    starts_at: datetime
    ends_at: Optional[datetime] = None
    
    @validator("ends_at")
    def validate_ends_at(cls, v: Optional[datetime], values: dict) -> Optional[datetime]:
        """Validate ends_at is after starts_at."""
        if v and "starts_at" in values and v <= values["starts_at"]:
            raise ValueError("ends_at must be after starts_at")
        return v

class ReferralCampaignCreate(ReferralCampaignBase):
    """Schema for creating a referral campaign."""
    pass

class ReferralCampaignUpdate(BaseModel):
    """Schema for updating a referral campaign."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    reward_type: Optional[RewardType] = None
    reward_amount: Optional[float] = Field(None, gt=0)
    min_invitee_kyc: Optional[bool] = None
    min_invitee_transaction: Optional[bool] = None
    min_transaction_amount: Optional[float] = Field(None, gt=0)
    max_referrals_per_user: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    ends_at: Optional[datetime] = None

class ReferralCampaignResponse(ReferralCampaignBase):
    """Schema for referral campaign response."""
    
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UseReferralCode(BaseModel):
    """Schema for using a referral code."""
    
    code: str = Field(..., min_length=6, max_length=10)
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None 