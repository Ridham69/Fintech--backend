"""
Referral Service

This module provides referral and incentive functionality.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.config import settings
from app.models.referral import (
    Referral,
    ReferralCode,
    ReferralCampaign,
    ReferralStatus,
    RewardType
)
from app.models.user import User
from app.models.kyc import KYCStatus
from app.models.transaction import Transaction
from app.schemas.referral import (
    ReferralCodeCreate,
    ReferralCreate,
    ReferralUpdate,
    ReferralCampaignCreate,
    ReferralCampaignUpdate
)
from app.utils.referral import generate_referral_code

class ReferralService:
    """Service for referral and incentive operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize service."""
        self.db = db
    
    async def create_referral_code(
        self,
        user_id: UUID,
        data: ReferralCodeCreate
    ) -> ReferralCode:
        """
        Create a referral code for a user.
        
        Args:
            user_id: User ID
            data: Referral code data
            
        Returns:
            Created ReferralCode
            
        Raises:
            ValueError: If user already has a referral code
        """
        # Check if user already has a referral code
        existing = await self.db.execute(
            select(ReferralCode).where(ReferralCode.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"User already has a referral code: {user_id}")
        
        # Generate unique code if not provided
        if not data.code:
            data.code = await generate_referral_code(self.db)
        
        # Create referral code
        referral_code = ReferralCode(
            user_id=user_id,
            **data.model_dump()
        )
        self.db.add(referral_code)
        await self.db.commit()
        await self.db.refresh(referral_code)
        
        return referral_code
    
    async def get_referral_code(
        self,
        code: str
    ) -> Optional[ReferralCode]:
        """
        Get referral code by code.
        
        Args:
            code: Referral code
            
        Returns:
            ReferralCode if found, None otherwise
        """
        result = await self.db.execute(
            select(ReferralCode)
            .where(ReferralCode.code == code)
            .options(selectinload(ReferralCode.user))
        )
        return result.scalar_one_or_none()
    
    async def register_invite(
        self,
        inviter_code: str,
        invitee_user_id: UUID,
        ip_address: Optional[str] = None,
        device_fingerprint: Optional[str] = None
    ) -> Referral:
        """
        Register a new referral.
        
        Args:
            inviter_code: Inviter's referral code
            invitee_user_id: Invitee's user ID
            ip_address: Optional IP address
            device_fingerprint: Optional device fingerprint
            
        Returns:
            Created Referral
            
        Raises:
            ValueError: If validation fails
        """
        # Get inviter's referral code
        referral_code = await self.get_referral_code(inviter_code)
        if not referral_code:
            raise ValueError(f"Invalid referral code: {inviter_code}")
        
        if not referral_code.is_active:
            raise ValueError(f"Referral code is inactive: {inviter_code}")
        
        if referral_code.expires_at and referral_code.expires_at < datetime.utcnow():
            raise ValueError(f"Referral code has expired: {inviter_code}")
        
        if (
            referral_code.max_uses is not None and
            referral_code.current_uses >= referral_code.max_uses
        ):
            raise ValueError(f"Referral code has reached max uses: {inviter_code}")
        
        # Get active campaign
        campaign = await self._get_active_campaign()
        if not campaign:
            raise ValueError("No active referral campaign")
        
        # Check if invitee already has a referral
        existing = await self.db.execute(
            select(Referral).where(Referral.invitee_user_id == invitee_user_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"User already has a referral: {invitee_user_id}")
        
        # Create referral
        referral = Referral(
            inviter_user_id=referral_code.user_id,
            invitee_user_id=invitee_user_id,
            reward_type=campaign.reward_type,
            reward_amount=campaign.reward_amount,
            reward_currency=campaign.reward_currency,
            campaign_id=campaign.id,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
            status=ReferralStatus.PENDING
        )
        self.db.add(referral)
        
        # Update referral code usage
        referral_code.current_uses += 1
        
        await self.db.commit()
        await self.db.refresh(referral)
        
        return referral
    
    async def check_and_reward_inviter(
        self,
        invitee_user_id: UUID
    ) -> Optional[Referral]:
        """
        Check and reward inviter if conditions are met.
        
        Args:
            invitee_user_id: Invitee's user ID
            
        Returns:
            Updated Referral if rewarded, None otherwise
        """
        # Get referral
        referral = await self.db.execute(
            select(Referral)
            .where(Referral.invitee_user_id == invitee_user_id)
            .options(selectinload(Referral.inviter))
        )
        referral = referral.scalar_one_or_none()
        
        if not referral or referral.status != ReferralStatus.PENDING:
            return None
        
        # Get campaign
        campaign = await self.db.get(ReferralCampaign, referral.campaign_id)
        if not campaign or not campaign.is_active:
            return None
        
        # Check KYC status
        if campaign.min_invitee_kyc:
            kyc = await self.db.execute(
                select(User)
                .where(
                    and_(
                        User.id == invitee_user_id,
                        User.kyc_status == KYCStatus.VERIFIED
                    )
                )
            )
            if not kyc.scalar_one_or_none():
                return None
        
        # Check transaction
        if campaign.min_invitee_transaction:
            transaction = await self.db.execute(
                select(Transaction)
                .where(
                    and_(
                        Transaction.user_id == invitee_user_id,
                        Transaction.status == "completed"
                    )
                )
                .order_by(Transaction.created_at.desc())
            )
            transaction = transaction.scalar_one_or_none()
            
            if not transaction:
                return None
            
            if (
                campaign.min_transaction_amount and
                transaction.amount < campaign.min_transaction_amount
            ):
                return None
        
        # Check max referrals per user
        if campaign.max_referrals_per_user:
            count = await self.db.execute(
                select(func.count())
                .select_from(Referral)
                .where(
                    and_(
                        Referral.inviter_user_id == referral.inviter_user_id,
                        Referral.status == ReferralStatus.REWARDED
                    )
                )
            )
            if count.scalar() >= campaign.max_referrals_per_user:
                return None
        
        # Update referral status
        referral.status = ReferralStatus.REWARDED
        referral.rewarded_at = datetime.utcnow()
        
        # Grant reward
        await self._grant_reward(referral)
        
        await self.db.commit()
        await self.db.refresh(referral)
        
        return referral
    
    async def get_referral_stats(
        self,
        user_id: UUID
    ) -> Tuple[int, int, int, float, ReferralCode]:
        """
        Get user's referral statistics.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (total_referrals, successful_referrals,
                     pending_referrals, total_rewards, referral_code)
        """
        # Get referral code
        referral_code = await self.db.execute(
            select(ReferralCode)
            .where(ReferralCode.user_id == user_id)
        )
        referral_code = referral_code.scalar_one_or_none()
        
        if not referral_code:
            return 0, 0, 0, 0.0, None
        
        # Get referral counts
        counts = await self.db.execute(
            select(
                func.count().label("total"),
                func.sum(
                    case(
                        (Referral.status == ReferralStatus.REWARDED, 1),
                        else_=0
                    )
                ).label("successful"),
                func.sum(
                    case(
                        (Referral.status == ReferralStatus.PENDING, 1),
                        else_=0
                    )
                ).label("pending")
            )
            .select_from(Referral)
            .where(Referral.inviter_user_id == user_id)
        )
        counts = counts.first()
        
        # Get total rewards
        rewards = await self.db.execute(
            select(func.sum(Referral.reward_amount))
            .select_from(Referral)
            .where(
                and_(
                    Referral.inviter_user_id == user_id,
                    Referral.status == ReferralStatus.REWARDED
                )
            )
        )
        total_rewards = rewards.scalar() or 0.0
        
        return (
            counts.total or 0,
            counts.successful or 0,
            counts.pending or 0,
            total_rewards,
            referral_code
        )
    
    async def _get_active_campaign(self) -> Optional[ReferralCampaign]:
        """Get active referral campaign."""
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(ReferralCampaign)
            .where(
                and_(
                    ReferralCampaign.is_active == True,
                    ReferralCampaign.starts_at <= now,
                    or_(
                        ReferralCampaign.ends_at == None,
                        ReferralCampaign.ends_at > now
                    )
                )
            )
            .order_by(ReferralCampaign.starts_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def _grant_reward(self, referral: Referral) -> None:
        """
        Grant reward to inviter.
        
        Args:
            referral: Referral to grant reward for
        """
        try:
            if referral.reward_type == RewardType.BONUS_CASH:
                # Add bonus cash to wallet
                await self._add_bonus_cash(
                    referral.inviter_user_id,
                    referral.reward_amount,
                    referral.reward_currency
                )
            elif referral.reward_type == RewardType.BONUS_INVESTMENT:
                # Add bonus investment
                await self._add_bonus_investment(
                    referral.inviter_user_id,
                    referral.reward_amount,
                    referral.reward_currency
                )
            elif referral.reward_type == RewardType.PREMIUM_UNLOCK:
                # Unlock premium features
                await self._unlock_premium(referral.inviter_user_id)
            
        except Exception as e:
            logger.exception(f"Error granting reward: {str(e)}")
            raise
    
    async def _add_bonus_cash(
        self,
        user_id: UUID,
        amount: float,
        currency: str
    ) -> None:
        """Add bonus cash to user's wallet."""
        # TODO: Implement wallet service integration
        pass
    
    async def _add_bonus_investment(
        self,
        user_id: UUID,
        amount: float,
        currency: str
    ) -> None:
        """Add bonus investment to user's portfolio."""
        # TODO: Implement investment service integration
        pass
    
    async def _unlock_premium(self, user_id: UUID) -> None:
        """Unlock premium features for user."""
        # TODO: Implement premium features service integration
        pass 
