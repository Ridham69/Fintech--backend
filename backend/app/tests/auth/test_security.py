"""
Test authentication security features.
"""
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.settings import settings
from app.auth.utils import hash_password

@pytest.mark.asyncio
async def test_password_complexity(
    client: AsyncClient,
    db: AsyncSession
):
    """Test password complexity requirements."""
    test_cases = [
        ("short", False),  # Too short
        ("nouppercaseornumber", False),  # No uppercase or number
        ("NOLOWERCASEORNUMBER", False),  # No lowercase or number
        ("NoSpecialChar1", False),  # No special character
        ("Valid@Password123", True),  # Valid password
    ]
    
    for password, should_pass in test_cases:
        response = await client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": password,
                "full_name": "Test User"
            }
        )
        
        if should_pass:
            assert response.status_code == 201
        else:
            assert response.status_code == 422

@pytest.mark.asyncio
async def test_brute_force_protection(
    client: AsyncClient,
    test_user: User
):
    """Test protection against brute force attacks."""
    # Attempt multiple failed logins
    for _ in range(settings.auth.MAX_LOGIN_ATTEMPTS + 1):
        response = await client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!"
            }
        )
    
    # Verify account is temporarily locked
    response = await client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "CorrectPassword123!"
        }
    )
    assert response.status_code == 401
    assert "temporarily locked" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_session_fixation(
    client: AsyncClient,
    test_user: User
):
    """Test protection against session fixation attacks."""
    # Login to get initial session
    login_response = await client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "SecurePass123!"
        }
    )
    assert login_response.status_code == 200
    initial_token = login_response.json()["access_token"]
    
    # Change password
    await client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {initial_token}"},
        json={
            "current_password": "SecurePass123!",
            "new_password": "NewSecurePass123!"
        }
    )
    
    # Verify old session is invalidated
    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {initial_token}"}
    )
    assert me_response.status_code == 401

@pytest.mark.asyncio
async def test_token_refresh_security(
    client: AsyncClient,
    test_user: User
):
    """Test security of token refresh mechanism."""
    # Login to get initial tokens
    login_response = await client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "SecurePass123!"
        }
    )
    tokens = login_response.json()
    
    # Test refresh token reuse
    refresh_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    
    # Attempt to reuse the same refresh token
    reuse_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse_response.status_code == 401

@pytest.mark.asyncio
async def test_csrf_protection(
    client: AsyncClient,
    test_user: User
):
    """Test CSRF protection mechanisms."""
    # Login to get session
    login_response = await client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "SecurePass123!"
        }
    )
    token = login_response.json()["access_token"]
    
    # Attempt request without CSRF token
    response = await client.post(
        "/auth/change-password",
        headers={
            "Authorization": f"Bearer {token}",
            # Missing CSRF token
        },
        json={
            "current_password": "SecurePass123!",
            "new_password": "NewSecurePass123!"
        }
    )
    assert response.status_code == 403 