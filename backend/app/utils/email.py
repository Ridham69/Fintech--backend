"""
Email Utility Module

This module provides email sending functionality using SMTP or third-party services.
Supports both plain text and HTML emails with proper error handling and logging.
"""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Union
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from app.core.config import settings
from app.core.exceptions import EmailError

# Initialize Jinja2 environment for email templates
template_dir = Path(__file__).parent.parent / "templates" / "email"
env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=True
)

async def send_email_async(
    subject: str,
    recipient: Union[str, List[str]],
    body: str,
    html_body: Optional[str] = None,
    template_name: Optional[str] = None,
    template_data: Optional[dict] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    attachments: Optional[List[dict]] = None
) -> bool:
    """
    Send an email asynchronously using SMTP.
    
    Args:
        subject: Email subject
        recipient: Email recipient(s)
        body: Plain text email body
        html_body: HTML email body (optional)
        template_name: Name of the template to use (optional)
        template_data: Data to render in the template (optional)
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
        reply_to: Reply-to address (optional)
        attachments: List of attachments (optional)
        
    Returns:
        bool: True if email was sent successfully
        
    Raises:
        EmailError: If email sending fails
    """
    try:
        # Create message container
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = recipient if isinstance(recipient, str) else ", ".join(recipient)
        
        if cc:
            msg["Cc"] = ", ".join(cc)
        if bcc:
            msg["Bcc"] = ", ".join(bcc)
        if reply_to:
            msg["Reply-To"] = reply_to
            
        # Add plain text body
        msg.attach(MIMEText(body, "plain"))
        
        # Add HTML body if provided
        if html_body:
            msg.attach(MIMEText(html_body, "html"))
        elif template_name:
            # Render template if provided
            template = env.get_template(f"{template_name}.html")
            html_content = template.render(**(template_data or {}))
            msg.attach(MIMEText(html_content, "html"))
            
        # Add attachments if any
        if attachments:
            for attachment in attachments:
                part = MIMEText(attachment["content"], "base64")
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment['filename']}"
                )
                msg.attach(part)
        
        # Send email in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            _send_smtp_email,
            msg,
            recipient,
            cc,
            bcc
        )
        
        logger.info(f"Email sent successfully to {recipient}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise EmailError(f"Failed to send email: {str(e)}")

def _send_smtp_email(
    msg: MIMEMultipart,
    recipient: Union[str, List[str]],
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None
) -> None:
    """
    Send email using SMTP (runs in thread pool).
    
    Args:
        msg: Email message
        recipient: Email recipient(s)
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
        
    Raises:
        EmailError: If email sending fails
    """
    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            # Combine all recipients
            all_recipients = [recipient] if isinstance(recipient, str) else recipient
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
                
            server.send_message(msg, settings.EMAIL_FROM, all_recipients)
            
    except Exception as e:
        logger.error(f"SMTP error: {str(e)}")
        raise EmailError(f"SMTP error: {str(e)}")

async def send_verification_email(
    email: str,
    token: str,
    template_data: Optional[dict] = None
) -> bool:
    """
    Send email verification email.
    
    Args:
        email: Recipient email
        token: Verification token
        template_data: Additional template data (optional)
        
    Returns:
        bool: True if email was sent successfully
    """
    data = {
        "verification_url": f"{settings.FRONTEND_URL}/verify-email?token={token}",
        "app_name": settings.APP_NAME,
        **(template_data or {})
    }
    
    return await send_email_async(
        subject=f"Verify your {settings.APP_NAME} account",
        recipient=email,
        body=f"Please verify your email by visiting: {data['verification_url']}",
        template_name="verification",
        template_data=data
    )

async def send_password_reset_email(
    email: str,
    token: str,
    template_data: Optional[dict] = None
) -> bool:
    """
    Send password reset email.
    
    Args:
        email: Recipient email
        token: Reset token
        template_data: Additional template data (optional)
        
    Returns:
        bool: True if email was sent successfully
    """
    data = {
        "reset_url": f"{settings.FRONTEND_URL}/reset-password?token={token}",
        "app_name": settings.APP_NAME,
        **(template_data or {})
    }
    
    return await send_email_async(
        subject=f"Reset your {settings.APP_NAME} password",
        recipient=email,
        body=f"Reset your password by visiting: {data['reset_url']}",
        template_name="password_reset",
        template_data=data
    )

async def send_notification_email(
    email: str,
    title: str,
    message: str,
    template_data: Optional[dict] = None
) -> bool:
    """
    Send notification email.
    
    Args:
        email: Recipient email
        title: Notification title
        message: Notification message
        template_data: Additional template data (optional)
        
    Returns:
        bool: True if email was sent successfully
    """
    data = {
        "title": title,
        "message": message,
        "app_name": settings.APP_NAME,
        **(template_data or {})
    }
    
    return await send_email_async(
        subject=title,
        recipient=email,
        body=message,
        template_name="notification",
        template_data=data
    ) 
