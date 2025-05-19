"""
Referral Triggers

This module provides triggers for the referral system.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.tasks.referral import check_referral_rewards, check_referral_abuse

async def on_kyc_completed(
    db: AsyncSession,
    user_id: UUID,
    kyc_status: str
) -> None:
    """
    Trigger when user completes KYC.
    
    Args:
        db: Database session
        user_id: User ID
        kyc_status: KYC status
    """
    try:
        # Check referral rewards
        await check_referral_rewards.delay(str(user_id))
        
    except Exception as e:
        logger.exception(f"Error in KYC completion trigger: {str(e)}")

async def on_first_transaction(
    db: AsyncSession,
    user_id: UUID,
    transaction_id: UUID,
    amount: float
) -> None:
    """
    Trigger when user makes first transaction.
    
    Args:
        db: Database session
        user_id: User ID
        transaction_id: Transaction ID
        amount: Transaction amount
    """
    try:
        # Check referral rewards
        await check_referral_rewards.delay(str(user_id))
        
    except Exception as e:
        logger.exception(f"Error in first transaction trigger: {str(e)}")

async def on_referral_created(
    db: AsyncSession,
    referral_id: UUID,
    inviter_id: UUID,
    invitee_id: UUID,
    ip_address: Optional[str] = None,
    device_fingerprint: Optional[str] = None
) -> None:
    """
    Trigger when new referral is created.
    
    Args:
        db: Database session
        referral_id: Referral ID
        inviter_id: Inviter's user ID
        invitee_id: Invitee's user ID
        ip_address: Optional IP address
        device_fingerprint: Optional device fingerprint
    """
    try:
        # Check for abuse
        await check_referral_abuse.delay(str(referral_id))
        
    except Exception as e:
        logger.exception(f"Error in referral creation trigger: {str(e)}")

async def on_user_created(
    db: AsyncSession,
    user_id: UUID,
    referral_code: Optional[str] = None,
    ip_address: Optional[str] = None,
    device_fingerprint: Optional[str] = None
) -> None:
    """
    Trigger when new user is created.
    
    Args:
        db: Database session
        user_id: User ID
        referral_code: Optional referral code
        ip_address: Optional IP address
        device_fingerprint: Optional device fingerprint
    """
    try:
        if referral_code:
            # Register referral
            from app.services.referral import ReferralService
            service = ReferralService(db)
            
            await service.register_invite(
                inviter_code=referral_code,
                invitee_user_id=user_id,
                ip_address=ip_address,
                device_fingerprint=device_fingerprint
            )
        
    except Exception as e:
        logger.exception(f"Error in user creation trigger: {str(e)}") 