"""
Notification Test Utilities

This module provides utility functions for testing notification-related functionality.
"""

import random
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationChannel
)

async def create_random_notification(
    db: AsyncSession,
    *,
    user_id: UUID,
    title: Optional[str] = None,
    message: Optional[str] = None,
    category: Optional[NotificationCategory] = None,
    priority: Optional[NotificationPriority] = None,
    channels: Optional[list[NotificationChannel]] = None,
    is_read: bool = False,
    read_at: Optional[datetime] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None
) -> Notification:
    """
    Create a random notification for testing.
    
    Args:
        db: Database session
        user_id: User ID
        title: Notification title (optional)
        message: Notification message (optional)
        category: Notification category (optional)
        priority: Notification priority (optional)
        channels: Notification channels (optional)
        is_read: Whether notification is read (optional)
        read_at: When notification was read (optional)
        created_at: Creation timestamp (optional)
        updated_at: Last update timestamp (optional)
        
    Returns:
        Created notification
    """
    now = datetime.utcnow()
    
    notification = Notification(
        id=uuid4(),
        user_id=user_id,
        title=title or f"Test Notification {random.randint(1000, 9999)}",
        message=message or f"Test message {random.randint(1000, 9999)}",
        category=category or random.choice(list(NotificationCategory)),
        priority=priority or random.choice(list(NotificationPriority)),
        channels=channels or [NotificationChannel.IN_APP],
        is_read=is_read,
        read_at=read_at if is_read else None,
        created_at=created_at or now,
        updated_at=updated_at or now
    )
    
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    
    return notification

async def create_notification_batch(
    db: AsyncSession,
    user_id: UUID,
    count: int,
    **kwargs
) -> list[Notification]:
    """
    Create a batch of random notifications.
    
    Args:
        db: Database session
        user_id: User ID
        count: Number of notifications to create
        **kwargs: Additional arguments for create_random_notification
        
    Returns:
        List of created notifications
    """
    notifications = []
    for _ in range(count):
        notification = await create_random_notification(
            db,
            user_id=user_id,
            **kwargs
        )
        notifications.append(notification)
    return notifications

async def get_notification_by_id(
    db: AsyncSession,
    notification_id: UUID
) -> Optional[Notification]:
    """
    Get a notification by ID.
    
    Args:
        db: Database session
        notification_id: Notification ID
        
    Returns:
        Notification if found, None otherwise
    """
    return await db.get(Notification, notification_id)

async def get_user_notifications(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> list[Notification]:
    """
    Get notifications for a user.
    
    Args:
        db: Database session
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of notifications
    """
    query = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_unread_notifications(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> list[Notification]:
    """
    Get unread notifications for a user.
    
    Args:
        db: Database session
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of unread notifications
    """
    query = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

async def mark_notification_as_read(
    db: AsyncSession,
    notification_id: UUID,
    user_id: UUID
) -> Optional[Notification]:
    """
    Mark a notification as read.
    
    Args:
        db: Database session
        notification_id: Notification ID
        user_id: User ID
        
    Returns:
        Updated notification if found, None otherwise
    """
    notification = await get_notification_by_id(db, notification_id)
    if not notification or notification.user_id != user_id:
        return None
        
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(notification)
    
    return notification

async def mark_all_notifications_as_read(
    db: AsyncSession,
    user_id: UUID
) -> int:
    """
    Mark all notifications as read for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Number of notifications marked as read
    """
    now = datetime.utcnow()
    result = await db.execute(
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        .update({
            "is_read": True,
            "read_at": now,
            "updated_at": now
        })
    )
    await db.commit()
    return result.rowcount 
