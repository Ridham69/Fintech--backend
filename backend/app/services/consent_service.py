"""
Consent Service

This module provides services for managing document versions and user consents.
"""

import hashlib
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.consent import DocumentType, DocumentVersion, UserConsent

# Initialize logger
logger = get_logger(__name__)

class ConsentService:
    """Service for managing document versions and user consents."""
    
    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
    
    async def create_document_version(
        self,
        doc_type: DocumentType,
        version: str,
        content: str
    ) -> DocumentVersion:
        """
        Create a new document version.
        
        Args:
            doc_type: Type of document
            version: Version string (e.g., "v1.1")
            content: Document content
            
        Returns:
            Created DocumentVersion instance
            
        Raises:
            HTTPException: If version already exists
        """
        # Calculate SHA-256 hash of content
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check if version exists
        existing = await self.db.execute(
            select(DocumentVersion)
            .where(
                DocumentVersion.type == doc_type,
                DocumentVersion.version == version
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Version {version} already exists for {doc_type}"
            )
        
        # Create new version
        doc_version = DocumentVersion(
            type=doc_type,
            version=version,
            hash=content_hash,
            content=content
        )
        
        self.db.add(doc_version)
        await self.db.commit()
        await self.db.refresh(doc_version)
        
        logger.info(
            f"Created new document version",
            extra={
                "type": doc_type,
                "version": version,
                "hash": content_hash
            }
        )
        
        return doc_version
    
    async def get_latest_version(
        self,
        doc_type: DocumentType
    ) -> Optional[DocumentVersion]:
        """
        Get the latest version of a document type.
        
        Args:
            doc_type: Type of document
            
        Returns:
            Latest DocumentVersion instance or None
        """
        result = await self.db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.type == doc_type)
            .order_by(DocumentVersion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_active_versions(self) -> List[DocumentVersion]:
        """
        Get the latest version of each document type.
        
        Returns:
            List of latest DocumentVersion instances
        """
        # Subquery to get latest version for each type
        latest_versions = (
            select(
                DocumentVersion.type,
                DocumentVersion.version,
                DocumentVersion.created_at
            )
            .distinct(DocumentVersion.type)
            .order_by(
                DocumentVersion.type,
                DocumentVersion.created_at.desc()
            )
            .subquery()
        )
        
        # Get full document versions
        result = await self.db.execute(
            select(DocumentVersion)
            .join(
                latest_versions,
                (DocumentVersion.type == latest_versions.c.type) &
                (DocumentVersion.version == latest_versions.c.version)
            )
            .options(selectinload(DocumentVersion.consents))
        )
        
        return result.scalars().all()
    
    async def record_user_consent(
        self,
        user_id: UUID,
        doc_type: DocumentType,
        request: Request
    ) -> UserConsent:
        """
        Record user consent to the latest version of a document.
        
        Args:
            user_id: User ID
            doc_type: Type of document
            request: FastAPI request object
            
        Returns:
            Created UserConsent instance
            
        Raises:
            HTTPException: If no active version exists
        """
        # Get latest version
        doc_version = await self.get_latest_version(doc_type)
        if not doc_version:
            raise HTTPException(
                status_code=400,
                detail=f"No active version found for {doc_type}"
            )
        
        # Create consent record
        consent = UserConsent(
            user_id=user_id,
            document_id=doc_version.id,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown")
        )
        
        self.db.add(consent)
        await self.db.commit()
        await self.db.refresh(consent)
        
        logger.info(
            f"Recorded user consent",
            extra={
                "user_id": user_id,
                "doc_type": doc_type,
                "version": doc_version.version
            }
        )
        
        return consent
    
    async def record_all_consents(
        self,
        user_id: UUID,
        request: Request
    ) -> List[UserConsent]:
        """
        Record user consent to all active document versions.
        
        Args:
            user_id: User ID
            request: FastAPI request object
            
        Returns:
            List of created UserConsent instances
        """
        # Get all active versions
        active_versions = await self.get_active_versions()
        
        # Record consent for each
        consents = []
        for doc_version in active_versions:
            consent = UserConsent(
                user_id=user_id,
                document_id=doc_version.id,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown")
            )
            self.db.add(consent)
            consents.append(consent)
        
        await self.db.commit()
        for consent in consents:
            await self.db.refresh(consent)
        
        logger.info(
            f"Recorded all consents for user",
            extra={
                "user_id": user_id,
                "consent_count": len(consents)
            }
        )
        
        return consents
    
    async def get_user_consents(
        self,
        user_id: UUID,
        doc_type: Optional[DocumentType] = None
    ) -> List[UserConsent]:
        """
        Get user's consent records.
        
        Args:
            user_id: User ID
            doc_type: Optional document type filter
            
        Returns:
            List of UserConsent instances
        """
        query = (
            select(UserConsent)
            .join(DocumentVersion)
            .where(UserConsent.user_id == user_id)
            .options(selectinload(UserConsent.document))
        )
        
        if doc_type:
            query = query.where(DocumentVersion.type == doc_type)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def verify_consent(
        self,
        user_id: UUID,
        doc_type: DocumentType
    ) -> bool:
        """
        Verify if user has consented to the latest version.
        
        Args:
            user_id: User ID
            doc_type: Type of document
            
        Returns:
            True if user has consented to latest version
        """
        # Get latest version
        latest = await self.get_latest_version(doc_type)
        if not latest:
            return False
        
        # Check for consent
        result = await self.db.execute(
            select(UserConsent)
            .where(
                UserConsent.user_id == user_id,
                UserConsent.document_id == latest.id
            )
        )
        return result.scalar_one_or_none() is not None 
