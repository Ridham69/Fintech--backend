"""
Abuse Logger Service

This module provides services for logging and tracking abuse attempts.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.audit_log import AuditLog, AuditLogType
from app.models.user import User
from app.services.notification import NotificationService

logger = get_logger(__name__)

class AbuseLogger:
    """Service for logging abuse attempts."""
    
    def __init__(
        self,
        db: AsyncSession,
        notification_service: Optional[NotificationService] = None
    ):
        """Initialize service."""
        self.db = db
        self.notification_service = notification_service
    
    async def log_abuse(
        self,
        user_id: UUID,
        endpoint: str,
        ip: str,
        user_agent: Optional[str],
        tier: str,
        limit: int,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Log an abuse attempt.
        
        Args:
            user_id: User ID
            endpoint: API endpoint
            ip: IP address
            user_agent: User agent string
            tier: User tier
            limit: Rate limit that was exceeded
            metadata: Additional metadata
        """
        try:
            # Get user details
            user = await self.db.execute(
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.audit_logs))
            )
            user = user.scalar_one_or_none()
            
            if not user:
                logger.warning(f"Attempted to log abuse for non-existent user: {user_id}")
                return
            
            # Create audit log
            audit_log = AuditLog(
                user_id=user_id,
                type=AuditLogType.RATE_LIMIT_EXCEEDED,
                ip_address=ip,
                user_agent=user_agent,
                metadata={
                    "endpoint": endpoint,
                    "tier": tier,
                    "limit": limit,
                    **(metadata or {})
                }
            )
            
            self.db.add(audit_log)
            await self.db.commit()
            
            # Log to application logs
            logger.warning(
                f"Rate limit exceeded",
                extra={
                    "user_id": user_id,
                    "email": user.email,
                    "endpoint": endpoint,
                    "tier": tier,
                    "limit": limit,
                    "ip": ip
                }
            )
            
            # Check for suspicious patterns
            await self._check_suspicious_patterns(user, audit_log)
            
            # Send notification if configured
            if self.notification_service:
                await self._send_notification(user, audit_log)
                
        except Exception as e:
            logger.error(f"Error logging abuse: {str(e)}")
            # Don't raise - we don't want to break the request flow
    
    async def _check_suspicious_patterns(
        self,
        user: User,
        audit_log: AuditLog
    ) -> None:
        """
        Check for suspicious patterns in abuse attempts.
        
        Args:
            user: User instance
            audit_log: Current audit log
        """
        # Get recent abuse logs for user
        recent_logs = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.user_id == user.id,
                AuditLog.type == AuditLogType.RATE_LIMIT_EXCEEDED,
                AuditLog.created_at >= datetime.utcnow() - timedelta(hours=1)
            )
            .order_by(AuditLog.created_at.desc())
        )
        recent_logs = recent_logs.scalars().all()
        
        # Check for rapid succession violations
        if len(recent_logs) >= 5:
            logger.warning(
                f"Multiple rate limit violations in short time",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "violation_count": len(recent_logs),
                    "time_window": "1 hour"
                }
            )
            
            # Update audit log with pattern detection
            audit_log.metadata["suspicious_pattern"] = "rapid_succession"
            await self.db.commit()
    
    async def _send_notification(
        self,
        user: User,
        audit_log: AuditLog
    ) -> None:
        """
        Send notification about abuse attempt.
        
        Args:
            user: User instance
            audit_log: Current audit log
        """
        try:
            await self.notification_service.send_notification(
                user_id=user.id,
                notification_type="abuse_detected",
                title="Suspicious Activity Detected",
                message=(
                    f"Multiple rate limit violations detected for your account. "
                    f"If this was not you, please contact support immediately."
                ),
                metadata={
                    "audit_log_id": audit_log.id,
                    "endpoint": audit_log.metadata["endpoint"],
                    "ip": audit_log.ip_address
                }
            )
        except Exception as e:
            logger.error(f"Error sending abuse notification: {str(e)}") 
