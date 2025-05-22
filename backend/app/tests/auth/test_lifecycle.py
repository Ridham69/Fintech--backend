"""Test complete authentication lifecycle."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.auth.utils import hash_password
from app.core.config import settings


@pytest.fixture
async def test_user(db: AsyncSession):
    """Create a test user in the database."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        hashed_password=hash_password("SecurePass123!"),
        role=UserRole.USER,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def test_app(app: FastAPI):
    """Get test application with auth routes."""
    from app.api.routes import auth
    app.include_router(auth.router)
    return app


@pytest.mark.asyncio
async def test_auth_lifecycle(
    test_app: FastAPI,
    test_user: User,
    client: AsyncClient,
    db: AsyncSession
):
    """Test complete authentication lifecycle."""
    device_id = "test_device"
    
    # 1. Login
    login_response = await client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "SecurePass123!",
            "device_id": device_id
        }
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    
    # 2. Access protected endpoint
    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_response.status_code == 200
    user_data = me_response.json()
    assert user_data["email"] == test_user.email
    
    # 3. Refresh token
    refresh_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    
    # 4. Verify old refresh token is blacklisted
    with patch("app.auth.utils.get_redis") as mock_redis:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = "1"  # Token is blacklisted
        mock_redis.return_value = redis_mock
        
        old_refresh_response = await client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert old_refresh_response.status_code == 401
    
    # 5. Logout
    logout_response = await client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert logout_response.status_code == 204
    
    # 6. Verify logged out token is rejected
    me_response_after_logout = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert me_response_after_logout.status_code == 401


@pytest.mark.asyncio
async def test_failed_login_attempts(
    test_app: FastAPI,
    test_user: User,
    client: AsyncClient,
    db: AsyncSession
):
    """Test account lockout after failed login attempts."""
    # Attempt multiple failed logins
    for _ in range(settings.auth.MAX_LOGIN_ATTEMPTS):
        response = await client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401
    
    # Verify account is locked
    response = await client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "SecurePass123!"  # Correct password
        }
    )
    assert response.status_code == 401
    assert "Account is locked" in response.json()["detail"]


@pytest.mark.asyncio
async def test_concurrent_sessions(
    test_app: FastAPI,
    test_user: User,
    client: AsyncClient
):
    """Test handling of concurrent sessions from different devices."""
    # Login from two different devices
    devices = ["device1", "device2"]
    tokens = []
    
    for device_id in devices:
        response = await client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "SecurePass123!",
                "device_id": device_id
            }
        )
        assert response.status_code == 200
        tokens.append(response.json())
    
    # Verify both sessions are valid
    for token in tokens:
        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )
        assert me_response.status_code == 200
    
    # Logout all sessions
    logout_all_response = await client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {tokens[0]['access_token']}"},
        json={"refresh_token": tokens[0]["refresh_token"]}
    )
    assert logout_all_response.status_code == 204
    
    # Verify all sessions are invalidated
    for token in tokens:
        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )
        assert me_response.status_code == 401 
