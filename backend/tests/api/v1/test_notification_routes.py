"""
Notification Route Tests

This module contains tests for notification-related API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationChannel
)
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.tests.utils.utils import get_superuser_token_headers
from app.tests.utils.notification import create_random_notification
from app.tests.utils.user import create_random_user

pytestmark = pytest.mark.asyncio

async def test_create_notification(
    client: AsyncClient,
    superuser_token_headers: Dict[str, str],
    db: AsyncSession
) -> None:
    """Test creating a notification."""
    user = await create_random_user(db)
    data = {
        "title": "Test Notification",
        "message": "This is a test notification",
        "category": NotificationCategory.SYSTEM,
        "priority": NotificationPriority.MEDIUM,
        "channels": [NotificationChannel.IN_APP],
        "user_id": str(user.id)
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/notifications",
        headers=superuser_token_headers,
        json=data
    )
    
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == data["title"]
    assert content["message"] == data["message"]
    assert content["category"] == data["category"]
    assert content["priority"] == data["priority"]
    assert content["channels"] == data["channels"]
    assert content["user_id"] == str(user.id)
    assert "id" in content
    assert "created_at" in content
    assert "updated_at" in content

async def test_get_notifications(
    client: AsyncClient,
    db: AsyncSession,
    normal_user_token_headers: Dict[str, str]
) -> None:
    """Test getting user notifications."""
    user = await create_random_user(db)
    # Create some notifications
    notifications = []
    for _ in range(3):
        notification = await create_random_notification(db, user_id=user.id)
        notifications.append(notification)
    
    response = await client.get(
        f"{settings.API_V1_STR}/notifications",
        headers=normal_user_token_headers
    )
    
    assert response.status_code == 200
    content = response.json()
    assert "items" in content
    assert "total" in content
    assert "unread_count" in content
    assert len(content["items"]) == 3
    assert content["total"] == 3

async def test_get_unread_notifications(
    client: AsyncClient,
    db: AsyncSession,
    normal_user_token_headers: Dict[str, str]
) -> None:
    """Test getting unread notifications."""
    user = await create_random_user(db)
    # Create some notifications
    for _ in range(3):
        await create_random_notification(db, user_id=user.id, is_read=False)
    await create_random_notification(db, user_id=user.id, is_read=True)
    
    response = await client.get(
        f"{settings.API_V1_STR}/notifications/unread",
        headers=normal_user_token_headers
    )
    
    assert response.status_code == 200
    content = response.json()
    assert len(content["items"]) == 3
    assert all(not item["is_read"] for item in content["items"])

async def test_get_notification(
    client: AsyncClient,
    db: AsyncSession,
    normal_user_token_headers: Dict[str, str]
) -> None:
    """Test getting a specific notification."""
    user = await create_random_user(db)
    notification = await create_random_notification(db, user_id=user.id)
    
    response = await client.get(
        f"{settings.API_V1_STR}/notifications/{notification.id}",
        headers=normal_user_token_headers
    )
    
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(notification.id)
    assert content["title"] == notification.title
    assert content["message"] == notification.message

async def test_get_notification_not_found(
    client: AsyncClient,
    normal_user_token_headers: Dict[str, str]
) -> None:
    """Test getting a non-existent notification."""
    response = await client.get(
        f"{settings.API_V1_STR}/notifications/{uuid4()}",
        headers=normal_user_token_headers
    )
    
    assert response.status_code == 404

async def test_mark_notification_as_read(
    client: AsyncClient,
    db: AsyncSession,
    normal_user_token_headers: Dict[str, str]
) -> None:
    """Test marking a notification as read."""
    user = await create_random_user(db)
    notification = await create_random_notification(db, user_id=user.id, is_read=False)
    
    response = await client.post(
        f"{settings.API_V1_STR}/notifications/{notification.id}/read",
        headers=normal_user_token_headers
    )
    
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(notification.id)
    assert content["is_read"] is True
    assert "read_at" in content

async def test_mark_all_notifications_as_read(
    client: AsyncClient,
    db: AsyncSession,
    normal_user_token_headers: Dict[str, str]
) -> None:
    """Test marking all notifications as read."""
    user = await create_random_user(db)
    # Create some notifications
    for _ in range(3):
        await create_random_notification(db, user_id=user.id, is_read=False)
    
    response = await client.post(
        f"{settings.API_V1_STR}/notifications/read-all",
        headers=normal_user_token_headers
    )
    
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 3

async def test_get_notification_preferences(
    client: AsyncClient,
    db: AsyncSession,
    normal_user_token_headers: Dict[str, str]
) -> None:
    """Test getting notification preferences."""
    response = await client.get(
        f"{settings.API_V1_STR}/notifications/preferences",
        headers=normal_user_token_headers
    )
    
    assert response.status_code == 200
    content = response.json()
    assert "email_enabled" in content
    assert "sms_enabled" in content
    assert "push_enabled" in content
    assert "in_app_enabled" in content

async def test_unauthorized_access(
    client: AsyncClient
) -> None:
    """Test accessing endpoints without authentication."""
    endpoints = [
        f"{settings.API_V1_STR}/notifications",
        f"{settings.API_V1_STR}/notifications/unread",
        f"{settings.API_V1_STR}/notifications/{uuid4()}",
        f"{settings.API_V1_STR}/notifications/{uuid4()}/read",
        f"{settings.API_V1_STR}/notifications/read-all",
        f"{settings.API_V1_STR}/notifications/preferences"
    ]
    
    for endpoint in endpoints:
        response = await client.get(endpoint)
        assert response.status_code == 401

async def test_filter_notifications(
    client: AsyncClient,
    db: AsyncSession,
    normal_user_token_headers: Dict[str, str]
) -> None:
    """Test filtering notifications."""
    user = await create_random_user(db)
    # Create notifications with different categories and priorities
    await create_random_notification(
        db,
        user_id=user.id,
        category=NotificationCategory.SYSTEM,
        priority=NotificationPriority.HIGH
    )
    await create_random_notification(
        db,
        user_id=user.id,
        category=NotificationCategory.TRANSACTIONAL,
        priority=NotificationPriority.MEDIUM
    )
    
    # Test category filter
    response = await client.get(
        f"{settings.API_V1_STR}/notifications?category=SYSTEM",
        headers=normal_user_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["items"]) == 1
    assert content["items"][0]["category"] == "SYSTEM"
    
    # Test priority filter
    response = await client.get(
        f"{settings.API_V1_STR}/notifications?priority=HIGH",
        headers=normal_user_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["items"]) == 1
    assert content["items"][0]["priority"] == "HIGH"
    
    # Test date filter
    start_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
    response = await client.get(
        f"{settings.API_V1_STR}/notifications?start_date={start_date}",
        headers=normal_user_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["items"]) == 2

async def test_pagination(
    client: AsyncClient,
    db: AsyncSession,
    normal_user_token_headers: Dict[str, str]
) -> None:
    """Test notification pagination."""
    user = await create_random_user(db)
    # Create multiple notifications
    for _ in range(15):
        await create_random_notification(db, user_id=user.id)
    
    # Test first page
    response = await client.get(
        f"{settings.API_V1_STR}/notifications?skip=0&limit=10",
        headers=normal_user_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["items"]) == 10
    assert content["total"] == 15
    assert content["page"] == 1
    assert content["size"] == 10
    
    # Test second page
    response = await client.get(
        f"{settings.API_V1_STR}/notifications?skip=10&limit=10",
        headers=normal_user_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["items"]) == 5
    assert content["total"] == 15
    assert content["page"] == 2
    assert content["size"] == 10 
