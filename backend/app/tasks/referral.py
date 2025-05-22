"""
Referral Tasks

This module provides Celery tasks for the referral system.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import async_session
from app.models.referral import Referral, ReferralStatus
from app.services.referral import ReferralService
from app.services.notification import NotificationService
from app.utils.referral import check_abuse_indicators

@celery_app.task(name="check_referral_rewards")
async def check_referral_rewards(invitee_user_id: UUID) -> None:
    """
    Check and process referral rewards for an invitee.
    
    Args:
        invitee_user_id: Invitee's user ID
    """
    async with async_session() as db:
        service = ReferralService(db)
        
        # Check and reward inviter
        referral = await service.check_and_reward_inviter(invitee_user_id)
        
        if referral:
            # Send notifications
            notification_service = NotificationService(db)
            
            # Notify inviter
            await notification_service.send_notification(
                user_id=referral.inviter_user_id,
                title="Referral Reward Granted",
                message=(
                    f"You've earned {referral.reward_amount} {referral.reward_currency} "
                    f"for your successful referral!"
                ),
                notification_type="referral_reward"
            )
            
            # Notify invitee
            await notification_service.send_notification(
                user_id=referral.invitee_user_id,
                title="Referral Completed",
                message="Your referrer has been rewarded for your signup!",
                notification_type="referral_completed"
            )

@celery_app.task(name="cleanup_expired_referrals")
async def cleanup_expired_referrals() -> None:
    """Clean up expired referrals."""
    async with async_session() as db:
        service = ReferralService(db)
        
        # Get expired referrals
        expired = await service.get_expired_referrals()
        
        for referral in expired:
            # Update status
            referral.status = ReferralStatus.EXPIRED
            referral.updated_at = datetime.utcnow()
            
            # Send notification
            notification_service = NotificationService(db)
            await notification_service.send_notification(
                user_id=referral.inviter_user_id,
                title="Referral Expired",
                message="One of your referrals has expired.",
                notification_type="referral_expired"
            )
        
        await db.commit()

@celery_app.task(name="check_referral_abuse")
async def check_referral_abuse(referral_id: UUID) -> None:
    """
    Check for potential referral abuse.
    
    Args:
        referral_id: Referral ID
    """
    async with async_session() as db:
        service = ReferralService(db)
        
        # Get referral
        referral = await service.get_referral(referral_id)
        if not referral:
            return
        
        # Check for abuse indicators
        is_suspicious = check_abuse_indicators(
            ip_address=referral.ip_address,
            device_fingerprint=referral.device_fingerprint
        )
        
        if is_suspicious:
            # Update status
            referral.status = ReferralStatus.REVOKED
            referral.notes = "Suspicious activity detected"
            referral.updated_at = datetime.utcnow()
            
            # Send notification
            notification_service = NotificationService(db)
            await notification_service.send_notification(
                user_id=referral.inviter_user_id,
                title="Referral Revoked",
                message="One of your referrals has been revoked due to suspicious activity.",
                notification_type="referral_revoked"
            )
            
            await db.commit()

@celery_app.task(name="process_referral_rewards")
async def process_referral_rewards() -> None:
    """Process pending referral rewards."""
    async with async_session() as db:
        service = ReferralService(db)
        
        # Get pending referrals
        pending = await service.get_pending_referrals()
        
        for referral in pending:
            # Check and reward
            await check_referral_rewards.delay(str(referral.invitee_user_id))
            
            # Check for abuse
            await check_referral_abuse.delay(str(referral.id))

@celery_app.task(name="send_referral_reminders")
async def send_referral_reminders() -> None:
    """Send reminders for pending referrals."""
    async with async_session() as db:
        service = ReferralService(db)
        notification_service = NotificationService(db)
        
        # Get pending referrals
        pending = await service.get_pending_referrals()
        
        for referral in pending:
            # Check if reminder should be sent
            if (
                referral.created_at < datetime.utcnow() - timedelta(days=7) and
                not referral.reminder_sent
            ):
                # Send reminder
                await notification_service.send_notification(
                    user_id=referral.inviter_user_id,
                    title="Referral Reminder",
                    message=(
                        "Your referral is still pending. "
                        "Encourage them to complete their profile!"
                    ),
                    notification_type="referral_reminder"
                )
                
                # Update reminder status
                referral.reminder_sent = True
                referral.updated_at = datetime.utcnow()
        
        await db.commit() 
