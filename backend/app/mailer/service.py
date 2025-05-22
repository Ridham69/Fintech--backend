"""
Email Service Module

This module handles email dispatch using configured SMTP provider.
Supports both plain text and HTML templates with Jinja2.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Union

from jinja2 import Environment, FileSystemLoader
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.core.settings import settings

# Initialize logger
logger = get_logger(__name__)

# Initialize Jinja2 environment
template_dir = Path(__file__).parent / "templates"
env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=True
)

class EmailService:
    """Service for sending transactional emails."""
    
    def __init__(self):
        """Initialize email service with configuration."""
        self.smtp_host = settings.external.SMTP_HOST
        self.smtp_port = settings.external.SMTP_PORT
        self.smtp_user = settings.external.SMTP_USER
        self.smtp_password = settings.external.SMTP_PASSWORD.get_secret_value()
        self.from_email = settings.external.SMTP_FROM_EMAIL
        
    async def _send_smtp(
        self,
        to_emails: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> None:
        """
        Send email via SMTP asynchronously.
        
        Args:
            to_emails: Recipient email(s)
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            
        Raises:
            smtplib.SMTPException: If email sending fails
        """
        if isinstance(to_emails, str):
            to_emails = [to_emails]
            
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = ", ".join(to_emails)
        
        # Add plain text part
        msg.attach(MIMEText(body, "plain"))
        
        # Add HTML part if provided
        if html_body:
            msg.attach(MIMEText(html_body, "html"))
            
        # Send email in thread pool to avoid blocking
        await asyncio.to_thread(
            self._send_message,
            to_emails,
            msg
        )
        
    def _send_message(self, to_emails: List[str], msg: MIMEMultipart) -> None:
        """
        Send email message via SMTP.
        
        Args:
            to_emails: List of recipient emails
            msg: Email message to send
            
        Raises:
            smtplib.SMTPException: If email sending fails
        """
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def send_email(
        self,
        to_emails: Union[str, List[str]],
        subject: str,
        template_name: Optional[str] = None,
        template_data: Optional[Dict] = None,
        body: Optional[str] = None,
        html_body: Optional[str] = None
    ) -> None:
        """
        Send email with optional template rendering.
        
        Args:
            to_emails: Recipient email(s)
            subject: Email subject
            template_name: Optional Jinja2 template name
            template_data: Optional template data
            body: Optional plain text body
            html_body: Optional HTML body
            
        Raises:
            ValueError: If neither template nor body provided
            smtplib.SMTPException: If email sending fails
        """
        try:
            # Render template if provided
            if template_name:
                template = env.get_template(template_name)
                rendered = template.render(**(template_data or {}))
                body = rendered
                html_body = rendered
                
            if not body and not html_body:
                raise ValueError("Either template or body must be provided")
                
            await self._send_smtp(to_emails, subject, body, html_body)
            
            logger.info(
                "Email sent successfully",
                extra={
                    "to": to_emails,
                    "subject": subject,
                    "template": template_name
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to send email",
                exc_info=True,
                extra={
                    "to": to_emails,
                    "subject": subject,
                    "template": template_name,
                    "error": str(e)
                }
            )
            raise

# Create singleton instance
email_service = EmailService() 
