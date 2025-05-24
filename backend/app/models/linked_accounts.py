"""
Linked Account Models

This module defines models for linked external accounts and wallets.
"""
from app.models.types import GUID
from app.models.types import GUID

from datetime import datetime
from enum import Enum as PythonEnum # Changed import
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from app.models.types import GUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base # Changed import

class AccountType(str, PythonEnum): # Changed base class
    """Types of linked accounts."""
    
    BANK = "bank"
    UPI = "upi"
    CARD = "card"
    WALLET = "wallet"

class LinkedAccount(Base):
    """Model for linked external accounts."""
    
    __tablename__ = "linked_accounts"
    
    id: Mapped[UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid4,
        index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    account_type: Mapped[AccountType] = mapped_column(
        SQLEnum(*[at.value for at in AccountType], native_enum=False), # Applied Enum fix
        nullable=False
    )
    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    account_number_masked: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    account_ref_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    # Renamed 'metadata' to 'meta_data' to avoid SQLAlchemy reserved name conflict
    meta_data: Mapped[Optional[dict]] = mapped_column(
        "metadata", # Specify the database column name
        Text,
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
    user = relationship("User", back_populates="linked_accounts")
    transactions = relationship("Transaction", back_populates="linked_account")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<LinkedAccount {self.account_type}:{self.provider}>" 
