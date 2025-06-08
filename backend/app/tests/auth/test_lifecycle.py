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
        email=f"{uuid.uuid4()}@example.com",  # Use unique email per test
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
    app.include_router(auth.router, prefix="/api/v1/auth")
    return app


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncClient:
    """AsyncClient using the test app with auth routes."""
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


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
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "SecurePass123!",
            "device_id": device_id
        }
    )
    assert login_response.status_code == 200, login_response.text
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    
    # 2. Access protected endpoint
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_response.status_code == 200, me_response.text
    user_data = me_response.json()
    assert user_data["email"] == test_user.email
    
    # 3. Refresh token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 200, refresh_response.text
    new_tokens = refresh_response.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    
    # 4. Verify old refresh token is blacklisted
    with patch("app.auth.utils.get_redis", new_callable=AsyncMock) as mock_redis:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = "1"  # Token is blacklisted
        mock_redis.return_value = redis_mock
        
        old_refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert old_refresh_response.status_code == 401, old_refresh_response.text
    
    # 5. Logout
    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert logout_response.status_code == 204, logout_response.text
    
    # 6. Verify logged out token is rejected
    me_response_after_logout = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert me_response_after_logout.status_code == 401, me_response_after_logout.text


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
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401, response.text
    
    # Verify account is locked
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "SecurePass123!"  # Correct password
        }
    )
    assert response.status_code == 401, response.text
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
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "SecurePass123!",
                "device_id": device_id
            }
        )
        assert response.status_code == 200, response.text
        tokens.append(response.json())
    
    # Verify both sessions are valid
    for token in tokens:
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )
        assert me_response.status_code == 200, me_response.text
    
    # Logout all sessions
    logout_all_response = await client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {tokens[0]['access_token']}"},
        json={"refresh_token": tokens[0]["refresh_token"]}
    )
    assert logout_all_response.status_code == 204, logout_all_response.text
    
    # Verify all sessions are invalidated
    for token in tokens:
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token['access_token']}"}
        )
        assert me_response.status_code == 401, me_response.text
