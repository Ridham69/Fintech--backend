"""
Linked Account Routes Tests

This module contains tests for linked account API endpoints.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.linked_accounts import LinkedAccount, AccountType
from app.models.user import User
from app.services.linked_accounts import LinkedAccountService

# Test data
TEST_USER_ID = uuid4()
TEST_ACCOUNT_ID = uuid4()
TEST_ACCOUNT_TYPE = AccountType.BANK
TEST_PROVIDER = "SBI"
TEST_ACCOUNT_NUMBER = "XXXX1234"
TEST_ACCOUNT_REF = "ref_123"

@pytest.fixture
def mock_request():
    """Mock FastAPI request."""
    request = Request({"type": "http", "method": "POST", "path": "/test"})
    request.client = type("Client", (), {"host": "127.0.0.1"})
    request.headers = {"user-agent": "test-agent"}
    return request

@pytest.fixture
async def test_user(test_db: AsyncSession):
    """Create test user."""
    user = User(
        id=TEST_USER_ID,
        email="test@example.com",
        is_active=True,
        is_verified=True
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user

@pytest.fixture
async def test_account(test_db: AsyncSession, test_user: User):
    """Create test linked account."""
    account = LinkedAccount(
        id=TEST_ACCOUNT_ID,
        user_id=test_user.id,
        account_type=TEST_ACCOUNT_TYPE,
        provider=TEST_PROVIDER,
        account_number_masked=TEST_ACCOUNT_NUMBER,
        account_ref_id=TEST_ACCOUNT_REF,
        is_primary=True,
        is_active=True
    )
    test_db.add(account)
    await test_db.commit()
    await test_db.refresh(account)
    return account

@pytest.mark.asyncio
async def test_create_linked_account(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User
):
    """Test creating a linked account."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    account_data = {
        "account_type": AccountType.UPI,
        "provider": "Google Pay",
        "account_number_masked": "XXXX5678",
        "account_ref_id": "ref_456",
        "is_primary": False
    }
    
    # Act
    response = await test_client.post(
        "/linked-accounts",
        headers={"Authorization": f"Bearer {token}"},
        json=account_data
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["account_type"] == account_data["account_type"]
    assert data["provider"] == account_data["provider"]
    assert data["account_number_masked"] == account_data["account_number_masked"]
    assert data["account_ref_id"] == account_data["account_ref_id"]
    assert data["is_primary"] == account_data["is_primary"]
    assert data["is_active"] is True

@pytest.mark.asyncio
async def test_list_linked_accounts(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User,
    test_account: LinkedAccount
):
    """Test listing linked accounts."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    
    # Act
    response = await test_client.get(
        "/linked-accounts",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(test_account.id)
    assert data["items"][0]["account_type"] == test_account.account_type
    assert data["items"][0]["provider"] == test_account.provider

@pytest.mark.asyncio
async def test_update_linked_account(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User,
    test_account: LinkedAccount
):
    """Test updating a linked account."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    update_data = {
        "is_primary": False,
        "is_active": False
    }
    
    # Act
    response = await test_client.patch(
        f"/linked-accounts/{test_account.id}",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["is_primary"] == update_data["is_primary"]
    assert data["is_active"] == update_data["is_active"]

@pytest.mark.asyncio
async def test_delete_linked_account(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User,
    test_account: LinkedAccount
):
    """Test deleting a linked account."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    
    # First update to not primary
    await test_client.patch(
        f"/linked-accounts/{test_account.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_primary": False}
    )
    
    # Act
    response = await test_client.delete(
        f"/linked-accounts/{test_account.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert response.status_code == 204
    
    # Verify account is deleted
    account = await test_db.execute(
        select(LinkedAccount).where(LinkedAccount.id == test_account.id)
    )
    assert account.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_duplicate_account(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User,
    test_account: LinkedAccount
):
    """Test creating duplicate account."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    account_data = {
        "account_type": test_account.account_type,
        "provider": test_account.provider,
        "account_number_masked": test_account.account_number_masked,
        "account_ref_id": test_account.account_ref_id,
        "is_primary": False
    }
    
    # Act
    response = await test_client.post(
        "/linked-accounts",
        headers={"Authorization": f"Bearer {token}"},
        json=account_data
    )
    
    # Assert
    assert response.status_code == 400
    assert "already linked" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_primary_account(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User,
    test_account: LinkedAccount
):
    """Test deleting primary account."""
    # Arrange
    token = "test_token"  # In real test, create valid JWT
    
    # Act
    response = await test_client.delete(
        f"/linked-accounts/{test_account.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert response.status_code == 400
    assert "Cannot delete primary account" in response.json()["detail"]

@pytest.mark.asyncio
async def test_unauthorized_access(
    test_app: FastAPI,
    test_client: AsyncClient,
    test_db: AsyncSession,
    test_user: User
):
    """Test unauthorized access to endpoints."""
    # Arrange
    token = "invalid_token"
    
    # Act & Assert
    # Try to create account
    response = await test_client.post(
        "/linked-accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={}
    )
    assert response.status_code == 401
    
    # Try to list accounts
    response = await test_client.get(
        "/linked-accounts",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    
    # Try to update account
    response = await test_client.patch(
        f"/linked-accounts/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
        json={}
    )
    assert response.status_code == 401
    
    # Try to delete account
    response = await test_client.delete(
        f"/linked-accounts/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401 