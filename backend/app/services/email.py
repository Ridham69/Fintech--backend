"""
Email Service Module

This module provides high-level email dispatch functionality,
including templated emails for various system events.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from loguru import logger

from app.core.config import settings
from app.core.exceptions import EmailError
from app.models.user import User
from app.utils.email import (
    send_email_async,
    send_verification_email,
    send_password_reset_email,
    send_notification_email
)

class EmailService:
    """Service for handling email-related operations."""
    
    @staticmethod
    async def send_welcome_email(user: User) -> bool:
        """
        Send welcome email to new user.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            template_data = {
                "user_name": user.full_name or user.email,
                "login_url": f"{settings.FRONTEND_URL}/login",
                "support_email": settings.SUPPORT_EMAIL
            }
            
            return await send_email_async(
                subject=f"Welcome to {settings.APP_NAME}!",
                recipient=user.email,
                body=f"Welcome to {settings.APP_NAME}! We're excited to have you on board.",
                template_name="welcome",
                template_data=template_data
            )
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            raise EmailError(f"Failed to send welcome email: {str(e)}")
    
    @staticmethod
    async def send_kyc_status_email(
        user: User,
        status: str,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send KYC status update email.
        
        Args:
            user: User instance
            status: KYC status
            additional_info: Additional information (optional)
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            template_data = {
                "user_name": user.full_name or user.email,
                "status": status,
                "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
                "support_email": settings.SUPPORT_EMAIL,
                **(additional_info or {})
            }
            
            return await send_email_async(
                subject=f"KYC Status Update - {status}",
                recipient=user.email,
                body=f"Your KYC status has been updated to: {status}",
                template_name="kyc_status",
                template_data=template_data
            )
        except Exception as e:
            logger.error(f"Failed to send KYC status email: {str(e)}")
            raise EmailError(f"Failed to send KYC status email: {str(e)}")
    
    @staticmethod
    async def send_investment_alert(
        user: User,
        investment_id: UUID,
        alert_type: str,
        details: Dict[str, Any]
    ) -> bool:
        """
        Send investment alert email.
        
        Args:
            user: User instance
            investment_id: Investment ID
            alert_type: Type of alert
            details: Alert details
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            template_data = {
                "user_name": user.full_name or user.email,
                "alert_type": alert_type,
                "investment_url": f"{settings.FRONTEND_URL}/investments/{investment_id}",
                "timestamp": datetime.utcnow().isoformat(),
                **details
            }
            
            return await send_email_async(
                subject=f"Investment Alert: {alert_type}",
                recipient=user.email,
                body=f"Investment Alert: {alert_type}\n\nDetails: {details}",
                template_name="investment_alert",
                template_data=template_data
            )
        except Exception as e:
            logger.error(f"Failed to send investment alert: {str(e)}")
            raise EmailError(f"Failed to send investment alert: {str(e)}")
    
    @staticmethod
    async def send_transaction_receipt(
        user: User,
        transaction_id: UUID,
        transaction_type: str,
        amount: float,
        currency: str,
        status: str,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send transaction receipt email.
        
        Args:
            user: User instance
            transaction_id: Transaction ID
            transaction_type: Type of transaction
            amount: Transaction amount
            currency: Transaction currency
            status: Transaction status
            additional_info: Additional information (optional)
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            template_data = {
                "user_name": user.full_name or user.email,
                "transaction_id": str(transaction_id),
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": currency,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "transaction_url": f"{settings.FRONTEND_URL}/transactions/{transaction_id}",
                **(additional_info or {})
            }
            
            return await send_email_async(
                subject=f"Transaction Receipt - {transaction_type}",
                recipient=user.email,
                body=f"Transaction Receipt\n\nType: {transaction_type}\nAmount: {amount} {currency}\nStatus: {status}",
                template_name="transaction_receipt",
                template_data=template_data
            )
        except Exception as e:
            logger.error(f"Failed to send transaction receipt: {str(e)}")
            raise EmailError(f"Failed to send transaction receipt: {str(e)}")
    
    @staticmethod
    async def send_security_alert(
        user: User,
        alert_type: str,
        details: Dict[str, Any]
    ) -> bool:
        """
        Send security alert email.
        
        Args:
            user: User instance
            alert_type: Type of security alert
            details: Alert details
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            template_data = {
                "user_name": user.full_name or user.email,
                "alert_type": alert_type,
                "timestamp": datetime.utcnow().isoformat(),
                "security_url": f"{settings.FRONTEND_URL}/security",
                "support_email": settings.SUPPORT_EMAIL,
                **details
            }
            
            return await send_email_async(
                subject=f"Security Alert: {alert_type}",
                recipient=user.email,
                body=f"Security Alert: {alert_type}\n\nDetails: {details}",
                template_name="security_alert",
                template_data=template_data
            )
        except Exception as e:
            logger.error(f"Failed to send security alert: {str(e)}")
            raise EmailError(f"Failed to send security alert: {str(e)}")
    
    @staticmethod
    async def send_system_notification(
        user: User,
        title: str,
        message: str,
        priority: str = "normal",
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send system notification email.
        
        Args:
            user: User instance
            title: Notification title
            message: Notification message
            priority: Notification priority
            additional_info: Additional information (optional)
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            template_data = {
                "user_name": user.full_name or user.email,
                "title": title,
                "message": message,
                "priority": priority,
                "timestamp": datetime.utcnow().isoformat(),
                "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
                **(additional_info or {})
            }
            
            return await send_notification_email(
                email=user.email,
                title=title,
                message=message,
                template_data=template_data
            )
        except Exception as e:
            logger.error(f"Failed to send system notification: {str(e)}")
            raise EmailError(f"Failed to send system notification: {str(e)}")

# --- Module-level export for compatibility ---
send_email = send_email_async

__all__ = ["EmailService", "send_email"]
