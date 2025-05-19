"""
KYC Service Module

This module handles KYC verification and status updates with email notifications.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import KYCError
from app.core.logging import get_logger
from app.email import email_service
from app.models.user import User
from app.schemas.kyc import KYCStatus
from app.services.auth_service import get_user_by_id
from app.services.email_service import EmailService

# Initialize logger
logger = get_logger(__name__)

async def update_kyc_status(
    user_id: UUID,
    status: KYCStatus,
    additional_info: Optional[Dict[str, Any]] = None,
    db: AsyncSession = None
) -> User:
    """
    Update user's KYC status and send notification email.
    
    Args:
        user_id: User's ID
        status: New KYC status
        additional_info: Additional information for the email (optional)
        db: Database session
        
    Returns:
        Updated User instance
        
    Raises:
        KYCError: If user not found or status update fails
    """
    user = await get_user_by_id(user_id, db)
    if not user:
        raise KYCError("User not found")
    
    # Update KYC status
    user.kyc_status = status
    user.kyc_updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    
    # Send notification email
    try:
        await EmailService.send_kyc_status_email(
            user=user,
            status=status.value,
            additional_info=additional_info
        )
    except Exception as e:
        # Log error but don't fail status update
        logger.error(f"Failed to send KYC status email: {str(e)}")
    
    return user

async def submit_kyc_documents(
    user_id: UUID,
    documents: Dict[str, Any],
    db: AsyncSession
) -> User:
    """
    Submit KYC documents for verification.
    
    Args:
        user_id: User's ID
        documents: KYC documents data
        db: Database session
        
    Returns:
        Updated User instance
        
    Raises:
        KYCError: If user not found or submission fails
    """
    user = await get_user_by_id(user_id, db)
    if not user:
        raise KYCError("User not found")
    
    # Update user's KYC documents
    user.kyc_documents = documents
    user.kyc_status = KYCStatus.PENDING
    user.kyc_submitted_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    
    # Send submission confirmation email
    try:
        await EmailService.send_kyc_status_email(
            user=user,
            status=KYCStatus.PENDING.value,
            additional_info={
                "submission_date": user.kyc_submitted_at.isoformat(),
                "estimated_time": "1-2 business days"
            }
        )
    except Exception as e:
        # Log error but don't fail submission
        logger.error(f"Failed to send KYC submission email: {str(e)}")
    
    return user

async def get_kyc_status(user_id: UUID, db: AsyncSession) -> Dict[str, Any]:
    """
    Get user's KYC status and details.
    
    Args:
        user_id: User's ID
        db: Database session
        
    Returns:
        Dictionary containing KYC status and details
        
    Raises:
        KYCError: If user not found
    """
    user = await get_user_by_id(user_id, db)
    if not user:
        raise KYCError("User not found")
    
    return {
        "status": user.kyc_status,
        "submitted_at": user.kyc_submitted_at,
        "updated_at": user.kyc_updated_at,
        "documents": user.kyc_documents
    }

async def update_kyc_status_with_email(
    kyc: KYCVerification,
    status: str,
    rejection_reasons: Optional[List[str]] = None
) -> KYCVerification:
    """
    Update KYC status and notify user.
    
    Args:
        kyc: KYC verification instance
        status: New status (approved/rejected)
        rejection_reasons: Optional list of rejection reasons
        
    Returns:
        Updated KYC verification instance
        
    Raises:
        ValueError: If status is invalid
    """
    try:
        # Update KYC status (existing logic)
        kyc.status = status
        # ... existing status update logic ...
        
        # Send status update email
        await email_service.send_email(
            to_emails=kyc.user.email,
            subject="KYC Status Update",
            template_name="kyc_status.html",
            template_data={
                "user": kyc.user,
                "status": status,
                "rejection_reasons": rejection_reasons or [],
                "dashboard_url": "https://app.autoinvest.com/dashboard",
                "kyc_update_url": "https://app.autoinvest.com/kyc/update",
                "year": datetime.now().year
            }
        )
        
        logger.info(
            "KYC status updated",
            extra={
                "user_id": kyc.user.id,
                "kyc_id": kyc.id,
                "status": status
            }
        )
        
        return kyc
        
    except Exception as e:
        logger.error(
            "Failed to update KYC status",
            exc_info=True,
            extra={
                "user_id": kyc.user.id,
                "kyc_id": kyc.id,
                "status": status,
                "error": str(e)
            }
        )
        raise 