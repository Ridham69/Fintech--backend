"""
Consent System Tests

This module contains tests for the consent management system.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.consent import DocumentType, DocumentVersion, UserConsent
from app.services.consent_service import ConsentService

# Test data
TEST_USER_ID = uuid4()
TEST_CONTENT = "Test document content"
TEST_VERSION = "v1.0"

@pytest.fixture
def mock_request():
    """Mock FastAPI request."""
    request = Request({"type": "http", "method": "POST", "path": "/test"})
    request.client = type("Client", (), {"host": "127.0.0.1"})
    request.headers = {"user-agent": "test-agent"}
    return request

@pytest.mark.asyncio
async def test_create_document_version(
    test_db: AsyncSession
):
    """Test creating a new document version."""
    # Arrange
    service = ConsentService(test_db)
    doc_type = DocumentType.TERMS
    
    # Act
    doc_version = await service.create_document_version(
        doc_type=doc_type,
        version=TEST_VERSION,
        content=TEST_CONTENT
    )
    
    # Assert
    assert doc_version.id is not None
    assert doc_version.type == doc_type
    assert doc_version.version == TEST_VERSION
    assert len(doc_version.hash) == 64  # SHA-256 hash length
    assert doc_version.content == TEST_CONTENT
    assert isinstance(doc_version.created_at, datetime)

@pytest.mark.asyncio
async def test_duplicate_version(
    test_db: AsyncSession
):
    """Test creating duplicate document version."""
    # Arrange
    service = ConsentService(test_db)
    doc_type = DocumentType.TERMS
    
    # Create first version
    await service.create_document_version(
        doc_type=doc_type,
        version=TEST_VERSION,
        content=TEST_CONTENT
    )
    
    # Act & Assert
    with pytest.raises(Exception) as exc:
        await service.create_document_version(
            doc_type=doc_type,
            version=TEST_VERSION,
            content="Different content"
        )
    assert "already exists" in str(exc.value)

@pytest.mark.asyncio
async def test_record_user_consent(
    test_db: AsyncSession,
    mock_request: Request
):
    """Test recording user consent."""
    # Arrange
    service = ConsentService(test_db)
    doc_type = DocumentType.TERMS
    
    # Create document version
    doc_version = await service.create_document_version(
        doc_type=doc_type,
        version=TEST_VERSION,
        content=TEST_CONTENT
    )
    
    # Act
    consent = await service.record_user_consent(
        user_id=TEST_USER_ID,
        doc_type=doc_type,
        request=mock_request
    )
    
    # Assert
    assert consent.id is not None
    assert consent.user_id == TEST_USER_ID
    assert consent.document_id == doc_version.id
    assert consent.ip_address == "127.0.0.1"
    assert consent.user_agent == "test-agent"
    assert isinstance(consent.accepted_at, datetime)

@pytest.mark.asyncio
async def test_record_all_consents(
    test_db: AsyncSession,
    mock_request: Request
):
    """Test recording consent to all active documents."""
    # Arrange
    service = ConsentService(test_db)
    
    # Create versions for different document types
    for doc_type in DocumentType:
        await service.create_document_version(
            doc_type=doc_type,
            version=TEST_VERSION,
            content=f"Content for {doc_type}"
        )
    
    # Act
    consents = await service.record_all_consents(
        user_id=TEST_USER_ID,
        request=mock_request
    )
    
    # Assert
    assert len(consents) == len(DocumentType)
    assert all(consent.user_id == TEST_USER_ID for consent in consents)
    assert all(consent.ip_address == "127.0.0.1" for consent in consents)
    assert all(consent.user_agent == "test-agent" for consent in consents)

@pytest.mark.asyncio
async def test_get_user_consents(
    test_db: AsyncSession,
    mock_request: Request
):
    """Test retrieving user consents."""
    # Arrange
    service = ConsentService(test_db)
    doc_type = DocumentType.TERMS
    
    # Create version and record consent
    await service.create_document_version(
        doc_type=doc_type,
        version=TEST_VERSION,
        content=TEST_CONTENT
    )
    await service.record_user_consent(
        user_id=TEST_USER_ID,
        doc_type=doc_type,
        request=mock_request
    )
    
    # Act
    consents = await service.get_user_consents(
        user_id=TEST_USER_ID,
        doc_type=doc_type
    )
    
    # Assert
    assert len(consents) == 1
    consent = consents[0]
    assert consent.user_id == TEST_USER_ID
    assert consent.document.type == doc_type
    assert consent.document.version == TEST_VERSION

@pytest.mark.asyncio
async def test_verify_consent(
    test_db: AsyncSession,
    mock_request: Request
):
    """Test consent verification."""
    # Arrange
    service = ConsentService(test_db)
    doc_type = DocumentType.TERMS
    
    # Create version
    await service.create_document_version(
        doc_type=doc_type,
        version=TEST_VERSION,
        content=TEST_CONTENT
    )
    
    # Act & Assert
    # Before consent
    assert not await service.verify_consent(TEST_USER_ID, doc_type)
    
    # After consent
    await service.record_user_consent(
        user_id=TEST_USER_ID,
        doc_type=doc_type,
        request=mock_request
    )
    assert await service.verify_consent(TEST_USER_ID, doc_type)

@pytest.mark.asyncio
async def test_get_latest_version(
    test_db: AsyncSession
):
    """Test getting latest document version."""
    # Arrange
    service = ConsentService(test_db)
    doc_type = DocumentType.TERMS
    
    # Create multiple versions
    versions = ["v1.0", "v1.1", "v2.0"]
    for version in versions:
        await service.create_document_version(
            doc_type=doc_type,
            version=version,
            content=f"Content for {version}"
        )
    
    # Act
    latest = await service.get_latest_version(doc_type)
    
    # Assert
    assert latest is not None
    assert latest.version == "v2.0"  # Latest version

@pytest.mark.asyncio
async def test_get_active_versions(
    test_db: AsyncSession
):
    """Test getting all active document versions."""
    # Arrange
    service = ConsentService(test_db)
    
    # Create versions for each document type
    for doc_type in DocumentType:
        await service.create_document_version(
            doc_type=doc_type,
            version=TEST_VERSION,
            content=f"Content for {doc_type}"
        )
    
    # Act
    active_versions = await service.get_active_versions()
    
    # Assert
    assert len(active_versions) == len(DocumentType)
    assert all(version.version == TEST_VERSION for version in active_versions)
    assert {version.type for version in active_versions} == set(DocumentType) 