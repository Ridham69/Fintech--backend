"""
Consent Models

This module defines the SQLAlchemy models for document versions and user consents.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import String, DateTime, Enum as SQLEnum, ForeignKey
from app.models.types import GUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

class DocumentType(str, Enum):
    """Types of legal documents requiring consent."""
    
    TERMS = "terms"
    PRIVACY = "privacy"
    KYC_DISCLOSURE = "kyc_disclosure"
    MARKETING = "marketing"
    COOKIES = "cookies"

class DocumentVersion(Base):
    """Model for versioned legal documents."""
    
    __tablename__ = "document_versions"
    
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, server_default="gen_random_uuid()")
    type: Mapped[DocumentType] = mapped_column(SQLEnum(DocumentType), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    content: Mapped[str] = mapped_column(String, nullable=False)  # Store document content
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        index=True
    )
    
    # Relationships
    consents: Mapped[list["UserConsent"]] = relationship(
        "UserConsent",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """String representation of the document version."""
        return (
            f"<DocumentVersion(id={self.id}, "
            f"type={self.type}, "
            f"version={self.version}, "
            f"created_at={self.created_at})>"
        )

class UserConsent(Base):
    """Model for tracking user consent to document versions."""
    
    __tablename__ = "user_consents"
    
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[UUID] = mapped_column(PGUUID, nullable=False, index=True)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID,
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        index=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Relationships
    document: Mapped[DocumentVersion] = relationship(
        "DocumentVersion",
        back_populates="consents"
    )
    
    def __repr__(self) -> str:
        """String representation of the user consent."""
        return (
            f"<UserConsent(id={self.id}, "
            f"user_id={self.user_id}, "
            f"document_id={self.document_id}, "
            f"accepted_at={self.accepted_at})>"
        ) 
