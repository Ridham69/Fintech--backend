"""Email verification utilities."""
import logging
from datetime import datetime, timedelta
from typing import Optional
import uuid

from fastapi import BackgroundTasks
from jinja2 import Environment, PackageLoader
from jose import jwt, JWTError
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# Initialize Jinja2 template environment
env = Environment(
    loader=PackageLoader("app", "templates/email")
)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str
) -> None:
    """
    Send email asynchronously.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        html_content: HTML email content
    """
    try:
        message = MIMEMultipart("alternative")
        message["From"] = settings.external.SMTP_FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        
        message.attach(MIMEText(html_content, "html"))
        
        async with aiosmtplib.SMTP(
            hostname=settings.external.SMTP_HOST,
            port=settings.external.SMTP_PORT,
            use_tls=True
        ) as smtp:
            await smtp.login(
                settings.external.SMTP_USER,
                settings.external.SMTP_PASSWORD.get_secret_value()
            )
            await smtp.send_message(message)
            
        logger.info(f"[EMAIL] Sent email to {to_email}: {subject}")
        
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send email to {to_email}", exc_info=e)
        raise


def create_email_token(user_id: uuid.UUID) -> str:
    """
    Create email verification token.
    
    Args:
        user_id: User ID
        
    Returns:
        str: JWT token for email verification
    """
    expires = datetime.utcnow() + timedelta(hours=24)
    data = {
        "sub": str(user_id),
        "exp": expires,
        "type": "email_verification",
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(
        data,
        settings.auth.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.auth.JWT_ALGORITHM
    )


def verify_email_token(token: str) -> Optional[uuid.UUID]:
    """
    Verify email verification token.
    
    Args:
        token: JWT token
        
    Returns:
        Optional[UUID]: User ID if token is valid
    """
    try:
        payload = jwt.decode(
            token,
            settings.auth.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.auth.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "email_verification":
            return None
            
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            return None
            
        return uuid.UUID(payload["sub"])
        
    except JWTError:
        return None


async def send_verification_email(
    user: User,
    background_tasks: BackgroundTasks
) -> None:
    """
    Send verification email to user.
    
    Args:
        user: User model instance
        background_tasks: FastAPI background tasks
    """
    token = create_email_token(user.id)
    verification_url = f"{settings.app.ROOT_PATH}/auth/verify-email?token={token}"
    
    template = env.get_template("verify_email.html")
    html_content = template.render(
        user_name=user.full_name,
        verification_url=verification_url
    )
    
    background_tasks.add_task(
        send_email,
        user.email,
        "Verify Your Email Address",
        html_content
    )
    
    logger.info(f"[AUTH] Verification email queued for {user.email}")


async def send_login_notification(
    user: User,
    ip_address: str,
    device_id: Optional[str],
    background_tasks: BackgroundTasks
) -> None:
    """
    Send login notification email.
    
    Args:
        user: User model instance
        ip_address: Client IP address
        device_id: Optional device identifier
        background_tasks: FastAPI background tasks
    """
    template = env.get_template("login_notification.html")
    html_content = template.render(
        user_name=user.full_name,
        ip_address=ip_address,
        device_id=device_id or "Unknown",
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    
    background_tasks.add_task(
        send_email,
        user.email,
        "New Login Detected",
        html_content
    )
    
    logger.info(f"[AUTH] Login notification queued for {user.email}") 