"""
Portfolio Rebalancing Models

This module defines models for portfolio rebalancing operations and tracking.
"""
from app.models.types import GUID
from app.models.types import GUID

from datetime import datetime
from enum import Enum as PythonEnum # Changed import
from typing import Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, JSON, String, Text
from app.models.types import GUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base # Changed import

class RebalanceTriggerType(str, PythonEnum): # Changed base class
    """Type of rebalance trigger."""
    
    DEPOSIT = "deposit"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    THRESHOLD = "threshold"

class RebalanceStatus(str, PythonEnum): # Changed base class
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
        GUID(),
        primary_key=True,
        default=uuid4,
        index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    trigger_type: Mapped[RebalanceTriggerType] = mapped_column(
        SQLEnum(*[rtt.value for rtt in RebalanceTriggerType], native_enum=False), # Applied Enum fix
        nullable=False,
        index=True
    )
    status: Mapped[RebalanceStatus] = mapped_column(
        SQLEnum(*[rs.value for rs in RebalanceStatus], native_enum=False), # Applied Enum fix
        nullable=False,
        default=RebalanceStatus.PENDING.value, # Use .value for default
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
