"""
Notification models.

This module defines the database models for user notifications,
including in-app and email notifications with support for
different categories and delivery channels.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, relationship

from app.core.database import Base
from app.models.user import User

class NotificationCategory(str, Enum):
    """Enum for notification categories."""
    
    SYSTEM = "SYSTEM"  # System notifications (maintenance, updates)
    TRANSACTIONAL = "TRANSACTIONAL"  # Transaction-related notifications
    PROMOTIONAL = "PROMOTIONAL"  # Marketing and promotional notifications
    SECURITY = "SECURITY"  # Security-related notifications
    INVESTMENT = "INVESTMENT"  # Investment-related notifications

class NotificationPriority(str, Enum):
    """Enum for notification priorities."""
    
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class NotificationChannel(str, Enum):
    """Enum for notification delivery channels."""
    
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"

class Notification(Base):
    """Model for user notifications."""
    
    __tablename__ = "notifications"
    
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    user_id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    title: Mapped[str] = Column(String(255), nullable=False)
    message: Mapped[str] = Column(Text, nullable=False)
    category: Mapped[str] = Column(
        SQLEnum(NotificationCategory),
        nullable=False,
        default=NotificationCategory.SYSTEM
    )
    priority: Mapped[str] = Column(
        SQLEnum(NotificationPriority),
        nullable=False,
        default=NotificationPriority.MEDIUM
    )
    channels: Mapped[list[str]] = Column(
        JSON,
        nullable=False,
        default=list
    )
    is_read: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    meta_info: Mapped[Optional[dict]] = Column(JSON, name="metadata")
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "title",
            "created_at",
            name="uq_notification_user_title_time"
        ),
    )

class NotificationPreference(Base):
    """Model for user notification preferences."""
    
    __tablename__ = "notification_preferences"
    
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    user_id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    email_enabled: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    sms_enabled: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    push_enabled: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    in_app_enabled: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    
    # Category-specific preferences
    system_enabled: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    transactional_enabled: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    promotional_enabled: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    security_enabled: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    investment_enabled: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    
    # Quiet hours
    quiet_hours_start: Mapped[Optional[int]] = Column(String(5))  # HH:MM format
    quiet_hours_end: Mapped[Optional[int]] = Column(String(5))  # HH:MM format
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user = relationship("User", back_populates="notification_preferences") 
