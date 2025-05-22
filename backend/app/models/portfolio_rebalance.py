"""
Portfolio Rebalancing Models

This module defines models for portfolio rebalancing operations and tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

class RebalanceTriggerType(str, Enum):
    """Type of rebalance trigger."""
    
    DEPOSIT = "deposit"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    THRESHOLD = "threshold"

class RebalanceStatus(str, Enum):
    """Status of rebalance operation."""
    
    PENDING = "pending"
    COMPUTING = "computing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RebalanceLog(Base):
    """Model for rebalance operation logs."""
    
    __tablename__ = "rebalance_logs"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    trigger_type: Mapped[RebalanceTriggerType] = mapped_column(
        SQLEnum(RebalanceTriggerType),
        nullable=False,
        index=True
    )
    status: Mapped[RebalanceStatus] = mapped_column(
        SQLEnum(RebalanceStatus),
        nullable=False,
        default=RebalanceStatus.PENDING,
        index=True
    )
    before_allocations: Mapped[Dict] = mapped_column(
        JSON,
        nullable=False
    )
    after_allocations: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True
    )
    suggested_trades: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True
    )
    executed_trades: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True
    )
    drift_threshold: Mapped[float] = mapped_column(
        nullable=False,
        default=0.05  # 5% default threshold
    )
    max_drift: Mapped[float] = mapped_column(
        nullable=False,
        default=0.0
    )
    total_value: Mapped[float] = mapped_column(
        nullable=False,
        default=0.0
    )
    rebalance_amount: Mapped[float] = mapped_column(
        nullable=False,
        default=0.0
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
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
    
    # Relationships
    user = relationship("User", back_populates="rebalance_logs")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<RebalanceLog {self.user_id}:{self.trigger_type}>" 
