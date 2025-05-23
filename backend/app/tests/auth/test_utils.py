"""Tests for authentication utilities."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from jose import jwt

print("JWT_SECRET_KEY:", repr(settings.auth.JWT_SECRET_KEY.get_secret_value()))
from app.auth.utils import (
    hash_password,
    verify_password,
    create_token_payload,
    create_token,
    verify_token,
    blacklist_token
)
from app.models.user import User, UserRole
from app.auth.exceptions import TokenExpiredError, TokenBlacklistedError
from app.core.settings import settings


@pytest.fixture
def test_user():
    """Create a test user instance."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        role=UserRole.USER,
        tenant_id=uuid.uuid4()
    )


@pytest.fixture
def test_password():
    """Test password fixture."""
    return "SecurePassword123!"


def test_password_hashing(test_password):
    """Test password hashing and verification."""
    # Hash password
    hashed = hash_password(test_password)
    assert hashed != test_password
    
    # Verify password
    is_valid, needs_rehash = verify_password(test_password, hashed)
    assert is_valid
    assert not needs_rehash
    
    # Verify wrong password
    is_valid, _ = verify_password("wrong_password", hashed)
    assert not is_valid


def test_token_payload_creation(test_user):
    """Test JWT token payload creation."""
    device_id = "test_device"
    
    # Test access token payload
    access_payload = create_token_payload(
        test_user,
        token_type="access",
        device_id=device_id
    )
    assert access_payload["sub"] == str(test_user.id)
    assert access_payload["role"] == test_user.role
    assert access_payload["tenant_id"] == str(test_user.tenant_id)
    assert access_payload["type"] == "access"
    assert access_payload["device_id"] == device_id
    
    # Test refresh token payload
    refresh_payload = create_token_payload(
        test_user,
        token_type="refresh",
        device_id=device_id
    )
    assert refresh_payload["type"] == "refresh"
    
    # Verify expiry times
    access_exp = datetime.fromtimestamp(access_payload["exp"])
    refresh_exp = datetime.fromtimestamp(refresh_payload["exp"])
    assert access_exp < refresh_exp


def test_token_creation_and_verification(test_user):
    """Test JWT token creation and verification."""
    payload = create_token_payload(test_user)
    token = create_token(payload)
    
    # Verify token can be decoded
    decoded = jwt.decode(
        token,
        settings.auth.JWT_SECRET_KEY.get_secret_value(),
        algorithms=["HS256"]
    )
    assert decoded["sub"] == str(test_user.id)
    assert decoded["role"] == test_user.role


@pytest.mark.asyncio
async def test_token_verification():
    """Test token verification with expiry and blacklist checks."""
    # Create expired token
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.utcnow() - timedelta(hours=1),
        "type": "access"
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.auth.JWT_SECRET_KEY.get_secret_value(),
        algorithm="HS256"
    )
    
    # Test expired token
    with pytest.raises(TokenExpiredError):
        await verify_token(expired_token)
    
    # Test blacklisted token
    valid_payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "type": "access",
        "jti": str(uuid.uuid4())
    }
    valid_token = jwt.encode(
        valid_payload,
        settings.auth.JWT_SECRET_KEY.get_secret_value(),
        algorithm="HS256"
    )
    
    # Mock Redis to simulate blacklisted token
    with patch("app.auth.utils.get_redis") as mock_redis:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = "1"  # Token is blacklisted
        mock_redis.return_value = redis_mock
        
        with pytest.raises(TokenBlacklistedError):
            await verify_token(valid_token)


@pytest.mark.asyncio
async def test_token_blacklisting():
    """Test token blacklisting functionality."""
    token = jwt.encode(
        {
            "jti": str(uuid.uuid4()),
            "exp": datetime.utcnow() + timedelta(hours=1)
        },
        settings.auth.JWT_SECRET_KEY.get_secret_value(),
        algorithm="HS256"
    )
    
    # Mock Redis for blacklisting
    with patch("app.auth.utils.get_redis") as mock_redis:
        redis_mock = AsyncMock()
        mock_redis.return_value = redis_mock
        
        await blacklist_token(token)
        
        # Verify Redis was called with correct parameters
        redis_mock.setex.assert_called_once()
