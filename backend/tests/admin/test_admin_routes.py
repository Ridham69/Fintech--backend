"""
Admin Routes Tests

This module contains tests for admin API endpoints.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.admin import AdminUser, AdminRole, AdminScope
from app.models.user import User
from app.services.admin_service import AdminService

# Test data
TEST_USER_ID = uuid4()
TEST_ADMIN_ID = uuid4()
TEST_ADMIN_ROLES = [AdminRole.SUPPORT]
TEST_ADMIN_SCOPES = [AdminScope.READ_USERS, AdminScope.ACT_FREEZE]

@pytest.fixture
def mock_request():
    """Mock FastAPI request."""
    request = Request({"type": "http", "method": "POST", "path": "/test"})
    request.client = type("Client", (), {"host": "127.0.0.1"})
    request.headers = {"user-agent": "test-agent"}
    return request

@pytest.fixture
async def test_admin(test_db: AsyncSession):
    """Create test admin user."""
    admin = AdminUser(
        id=TEST_ADMIN_ID,
        user_id=TEST_USER_ID,
        roles=TEST_ADMIN_ROLES,
        scopes=TEST_ADMIN_SCOPES,
        is_active=True
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin

@pytest.fixture
async def test_user(test_db: AsyncSession):
    """Create test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        is_active=True
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user

@pytest.mark.asyncio
async def test_get_user_details(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_admin: AdminUser,
    test_user: User
):
    """Test getting user details."""
    # Arrange
    # Create JWT token
    token = "test_token"  # In real test, create valid JWT
    
    # Act
    response = await test_client.get(
        f"/admin/users/{test_user.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["is_active"] == test_user.is_active

@pytest.mark.asyncio
async def test_freeze_user(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_admin: AdminUser,
    test_user: User
):
    """Test freezing user account."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    
    # Act
    response = await test_client.post(
        f"/admin/users/{test_user.id}/freeze",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert response.status_code == 204
    
    # Verify user is frozen
    user = await test_db.execute(
        select(User).where(User.id == test_user.id)
    )
    user = user.scalar_one_or_none()
    assert not user.is_active

@pytest.mark.asyncio
async def test_resend_notification(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_admin: AdminUser,
    test_user: User
):
    """Test resending notification."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    notification_data = {
        "notification_type": "kyc_reminder",
        "template_data": {"name": "Test User"},
        "force": True
    }
    
    # Act
    response = await test_client.post(
        f"/admin/users/{test_user.id}/resend-notification",
        headers={"Authorization": f"Bearer {token}"},
        json=notification_data
    )
    
    # Assert
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_get_audit_logs(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_admin: AdminUser
):
    """Test getting audit logs."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    
    # Create some audit logs
    service = AdminService(test_db)
    await service.log_admin_action(
        admin_id=test_admin.id,
        action="test_action",
        resource_type="test_resource",
        resource_id=uuid4(),
        details="Test action",
        request=Request({"type": "http", "method": "GET", "path": "/test"})
    )
    
    # Act
    response = await test_client.get(
        "/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["items"]) > 0
    assert data["items"][0]["action"] == "test_action"

@pytest.mark.asyncio
async def test_create_admin(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_admin: AdminUser
):
    """Test creating admin user."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    admin_data = {
        "user_id": str(uuid4()),
        "roles": [AdminRole.SUPPORT],
        "scopes": [AdminScope.READ_USERS],
        "is_active": True
    }
    
    # Act
    response = await test_client.post(
        "/admin/admins",
        headers={"Authorization": f"Bearer {token}"},
        json=admin_data
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == admin_data["user_id"]
    assert data["roles"] == admin_data["roles"]
    assert data["scopes"] == admin_data["scopes"]

@pytest.mark.asyncio
async def test_update_admin(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_admin: AdminUser
):
    """Test updating admin user."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    admin_data = {
        "roles": [AdminRole.COMPLIANCE],
        "scopes": [AdminScope.READ_USERS, AdminScope.READ_KYC],
        "is_active": True
    }
    
    # Act
    response = await test_client.put(
        f"/admin/admins/{test_admin.id}",
        headers={"Authorization": f"Bearer {token}"},
        json=admin_data
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["roles"] == admin_data["roles"]
    assert data["scopes"] == admin_data["scopes"]

@pytest.mark.asyncio
async def test_unauthorized_access(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User
):
    """Test unauthorized access to admin endpoints."""
    # Arrange
    token = "invalid_token"
    
    # Act & Assert
    # Try to get user details
    response = await test_client.get(
        f"/admin/users/{test_user.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    
    # Try to freeze user
    response = await test_client.post(
        f"/admin/users/{test_user.id}/freeze",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    
    # Try to get audit logs
    response = await test_client.get(
        "/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_insufficient_permissions(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_admin: AdminUser,
    test_user: User
):
    """Test access with insufficient permissions."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    
    # Update admin to have only read scope
    test_admin.scopes = [AdminScope.READ_USERS]
    await test_db.commit()
    
    # Act & Assert
    # Try to freeze user (requires ACT_FREEZE scope)
    response = await test_client.post(
        f"/admin/users/{test_user.id}/freeze",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403 