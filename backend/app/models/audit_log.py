"""
Audit Log Model

This module defines the SQLAlchemy model for audit logs.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import String, DateTime, JSON
from app.models.types import GUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class AuditLogType(str, Enum):
    """Enum for audit log action types."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    TRANSACTION = "transaction"
    KYC_UPDATE = "kyc_update"
    PASSWORD_CHANGE = "password_change"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    # Add more types as needed for your domain


class AuditLog(Base):
    """Audit log model for tracking system events."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[Optional[UUID]] = mapped_column(PGUUID, index=True)
    action: Mapped[AuditLogType] = mapped_column(String(100), nullable=False, index=True)
    target_table: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        index=True
    )
    meta: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        name="metadata",  # Preserve DB column name as 'metadata'
        nullable=False,
        server_default="'{}'::jsonb"
    )
    
    def __repr__(self) -> str:
        """String representation of the audit log."""
        return (
            f"<AuditLog(id={self.id}, "
            f"action={self.action}, "
            f"target={self.target_table}:{self.target_id}, "
            f"timestamp={self.timestamp})>"
        ) 
