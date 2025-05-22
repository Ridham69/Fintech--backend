"""
Webhook Models

This module defines models for webhook events and processing.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Text
from app.models.types import GUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

class WebhookStatus(str, Enum):
    """Status of webhook processing."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class WebhookEvent(Base):
    """Model for webhook events."""
    
    __tablename__ = "webhook_events"
    
    id: Mapped[UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid4,
        index=True
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    status: Mapped[WebhookStatus] = mapped_column(
        SQLEnum(WebhookStatus),
        nullable=False,
        default=WebhookStatus.PENDING,
        index=True
    )
    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )
    headers: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )
    signature: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    signature_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    result: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<WebhookEvent {self.provider}:{self.event_type}>" 
