"""
Reconciliation Models

This module defines models for reconciliation reports and tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base

class ReconciliationStatus(str, Enum):
    """Status of reconciliation process."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

class ReconciliationReport(Base):
    """Model for reconciliation reports."""
    
    __tablename__ = "reconciliation_reports"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    status: Mapped[ReconciliationStatus] = mapped_column(
        SQLEnum(ReconciliationStatus),
        nullable=False,
        default=ReconciliationStatus.PENDING,
        index=True
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    mismatches: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    total_accounts: Mapped[int] = mapped_column(
        nullable=False,
        default=0
    )
    matched_accounts: Mapped[int] = mapped_column(
        nullable=False,
        default=0
    )
    mismatch_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0
    )
    threshold_exceeded: Mapped[bool] = mapped_column(
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
        return f"<ReconciliationReport {self.provider}:{self.status}>" 