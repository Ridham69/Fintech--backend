"""
Audit Logging Tests

This module contains tests for the audit logging functionality.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit.logger import AuditLog, log_audit_event, get_audit_logs
from app.middlewares.audit_context import AuditContextMiddleware
from app.models.audit_log import AuditLog as AuditLogModel

# Test data
TEST_USER_ID = uuid4()
TEST_TARGET_ID = uuid4()
TEST_ACTION = "test.action"
TEST_TABLE = "test_table"
TEST_METADATA = {"key": "value"}

@pytest.fixture
def mock_request():
    """Mock FastAPI request."""
    request = Request({"type": "http", "method": "POST", "path": "/test"})
    request.client = type("Client", (), {"host": "127.0.0.1"})
    request.headers = {"user-agent": "test-agent"}
    return request

@pytest.mark.asyncio
async def test_log_audit_event(
    test_db: AsyncSession,
    mock_request: Request
):
    """Test logging an audit event."""
    # Arrange
    user_id = TEST_USER_ID
    action = TEST_ACTION
    target_table = TEST_TABLE
    target_id = str(TEST_TARGET_ID)
    metadata = TEST_METADATA
    
    # Act
    audit_log = await log_audit_event(
        db=test_db,
        action=action,
        target_table=target_table,
        target_id=target_id,
        request=mock_request,
        user_id=user_id,
        metadata=metadata
    )
    
    # Assert
    assert audit_log.id is not None
    assert audit_log.user_id == user_id
    assert audit_log.action == action
    assert audit_log.target_table == target_table
    assert audit_log.target_id == target_id
    assert audit_log.ip_address == "127.0.0.1"
    assert audit_log.user_agent == "test-agent"
    assert audit_log.metadata == metadata
    assert isinstance(audit_log.timestamp, datetime)

@pytest.mark.asyncio
async def test_get_audit_logs(
    test_db: AsyncSession,
    mock_request: Request
):
    """Test querying audit logs."""
    # Arrange
    # Create test logs
    for i in range(3):
        await log_audit_event(
            db=test_db,
            action=f"test.action.{i}",
            target_table=TEST_TABLE,
            target_id=str(uuid4()),
            request=mock_request,
            user_id=TEST_USER_ID,
            metadata={"index": i}
        )
    
    # Act
    logs = await get_audit_logs(
        db=test_db,
        user_id=TEST_USER_ID,
        limit=2
    )
    
    # Assert
    assert len(logs) == 2
    assert all(log.user_id == TEST_USER_ID for log in logs)
    assert logs[0].timestamp > logs[1].timestamp  # Descending order

@pytest.mark.asyncio
async def test_audit_log_filters(
    test_db: AsyncSession,
    mock_request: Request
):
    """Test audit log filtering."""
    # Arrange
    # Create test logs with different actions
    actions = ["action1", "action2", "action3"]
    for action in actions:
        await log_audit_event(
            db=test_db,
            action=action,
            target_table=TEST_TABLE,
            target_id=str(uuid4()),
            request=mock_request,
            user_id=TEST_USER_ID
        )
    
    # Act
    filtered_logs = await get_audit_logs(
        db=test_db,
        action="action2"
    )
    
    # Assert
    assert len(filtered_logs) == 1
    assert filtered_logs[0].action == "action2"

@pytest.mark.asyncio
async def test_audit_context_middleware(
    test_client: AsyncClient
):
    """Test audit context middleware."""
    # Arrange
    app = FastAPI()
    app.add_middleware(AuditContextMiddleware)
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"metadata": request.state.audit_metadata}
    
    # Act
    response = await test_client.get("/test")
    
    # Assert
    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert "ip_address" in metadata
    assert "user_agent" in metadata
    assert "method" in metadata
    assert "path" in metadata

@pytest.mark.asyncio
async def test_audit_log_error_handling(
    test_db: AsyncSession,
    mock_request: Request
):
    """Test error handling in audit logging."""
    # Arrange
    # Simulate database error
    test_db.add = lambda x: 1/0
    
    # Act & Assert
    with pytest.raises(Exception):
        await log_audit_event(
            db=test_db,
            action=TEST_ACTION,
            target_table=TEST_TABLE,
            target_id=str(TEST_TARGET_ID),
            request=mock_request,
            user_id=TEST_USER_ID
        )

@pytest.mark.asyncio
async def test_audit_log_immutability(
    test_db: AsyncSession,
    mock_request: Request
):
    """Test audit log immutability."""
    # Arrange
    audit_log = await log_audit_event(
        db=test_db,
        action=TEST_ACTION,
        target_table=TEST_TABLE,
        target_id=str(TEST_TARGET_ID),
        request=mock_request,
        user_id=TEST_USER_ID
    )
    
    # Act & Assert
    # Attempt to update audit log
    audit_log.action = "modified.action"
    await test_db.commit()
    
    # Verify original value is preserved
    result = await test_db.execute(
        select(AuditLogModel).where(AuditLogModel.id == audit_log.id)
    )
    updated_log = result.scalar_one()
    assert updated_log.action == TEST_ACTION  # Original value 