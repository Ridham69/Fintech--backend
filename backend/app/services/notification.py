"""
Notification Service

This module provides notification-related business logic and operations,
including creation, retrieval, and management of notifications.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationChannel
)
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate
)
from app.services.email import send_email
from app.services.sms import send_sms
from app.services.push import send_push_notification
from app.utils.logging import logger

class NotificationService:
    """Service class for notification operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: UUID,
        payload: NotificationCreate,
        background_tasks: Optional[List[Any]] = None
    ) -> Notification:
        """
        Create a new notification for a user.
        
        Args:
            user_id: The ID of the user to notify
            payload: The notification data
            background_tasks: Optional list of background tasks to add to
            
        Returns:
            The created notification
            
        Raises:
            ValidationError: If the notification data is invalid
        """
        try:
            # Get user preferences
            user_prefs = await self.get_user_preferences(user_id)
            
            # Check if notification should be sent based on preferences
            if not self._should_send_notification(payload.category, user_prefs):
                logger.info(f"Notification skipped due to user preferences: {user_id}")
                return None
            
            # Create notification
            notification = Notification(
                user_id=user_id,
                title=payload.title,
                message=payload.message,
                category=payload.category,
                priority=payload.priority,
                channels=payload.channels,
                metadata=payload.metadata
            )
            
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)
            
            # Queue background tasks for different channels
            if background_tasks is not None:
                if NotificationChannel.EMAIL in payload.channels and payload.email_to:
                    background_tasks.append(
                        send_email(
                            to_email=payload.email_to,
                            subject=payload.title,
                            body=payload.message
                        )
                    )
                
                if NotificationChannel.SMS in payload.channels and payload.sms_to:
                    background_tasks.append(
                        send_sms(
                            to_number=payload.sms_to,
                            message=payload.message
                        )
                    )
                
                if NotificationChannel.PUSH in payload.channels and payload.push_token:
                    background_tasks.append(
                        send_push_notification(
                            token=payload.push_token,
                            title=payload.title,
                            body=payload.message
                        )
                    )
            
            logger.info(
                f"Created notification for user {user_id}",
                extra={
                    "notification_id": notification.id,
                    "category": notification.category,
                    "channels": notification.channels
                }
            )
            
            return notification
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to create notification: {str(e)}",
                extra={"user_id": user_id, "error": str(e)}
            )
            raise ValidationError(f"Failed to create notification: {str(e)}")

    async def get_user_notifications(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        only_unread: bool = False,
        category: Optional[NotificationCategory] = None,
        priority: Optional[NotificationPriority] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get notifications for a user with filtering options.
        
        Args:
            user_id: The user ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            only_unread: Filter for unread notifications only
            category: Filter by notification category
            priority: Filter by notification priority
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Dictionary containing notifications and metadata
        """
        try:
            # Build base query
            query = select(Notification).where(Notification.user_id == user_id)
            
            # Apply filters
            if only_unread:
                query = query.where(Notification.is_read == False)
            if category:
                query = query.where(Notification.category == category)
            if priority:
                query = query.where(Notification.priority == priority)
            if start_date:
                query = query.where(Notification.created_at >= start_date)
            if end_date:
                query = query.where(Notification.created_at <= end_date)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total = await self.db.scalar(count_query)
            
            # Apply pagination and ordering
            query = query.order_by(desc(Notification.created_at))
            query = query.offset(skip).limit(limit)
            
            # Execute query
            result = await self.db.execute(query)
            notifications = result.scalars().all()
            
            # Get unread count
            unread_query = select(func.count()).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
            unread_count = await self.db.scalar(unread_query)
            
            return {
                "items": notifications,
                "total": total,
                "unread_count": unread_count,
                "page": skip // limit + 1,
                "size": limit
            }
            
        except Exception as e:
            logger.error(
                f"Failed to fetch notifications: {str(e)}",
                extra={"user_id": user_id, "error": str(e)}
            )
            raise ValidationError(f"Failed to fetch notifications: {str(e)}")

    async def mark_notification_as_read(
        self,
        notification_id: UUID,
        user_id: UUID
    ) -> Optional[Notification]:
        """
        Mark a notification as read.
        
        Args:
            notification_id: The notification ID
            user_id: The user ID
            
        Returns:
            The updated notification or None if not found
        """
        try:
            notification = await self.get_notification(notification_id, user_id)
            if not notification:
                return None
            
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(notification)
            
            logger.info(
                f"Marked notification as read",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_id
                }
            )
            
            return notification
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to mark notification as read: {str(e)}",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            raise ValidationError(f"Failed to mark notification as read: {str(e)}")

    async def mark_all_as_read(
        self,
        user_id: UUID,
        category: Optional[NotificationCategory] = None
    ) -> int:
        """
        Mark all notifications as read for a user.
        
        Args:
            user_id: The user ID
            category: Optional category filter
            
        Returns:
            Number of notifications marked as read
        """
        try:
            query = select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
            
            if category:
                query = query.where(Notification.category == category)
            
            result = await self.db.execute(query)
            notifications = result.scalars().all()
            
            now = datetime.utcnow()
            for notification in notifications:
                notification.is_read = True
                notification.read_at = now
            
            await self.db.commit()
            
            logger.info(
                f"Marked all notifications as read",
                extra={
                    "user_id": user_id,
                    "category": category,
                    "count": len(notifications)
                }
            )
            
            return len(notifications)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to mark all notifications as read: {str(e)}",
                extra={"user_id": user_id, "error": str(e)}
            )
            raise ValidationError(f"Failed to mark all notifications as read: {str(e)}")

    async def get_notification(
        self,
        notification_id: UUID,
        user_id: UUID
    ) -> Optional[Notification]:
        """
        Get a specific notification.
        
        Args:
            notification_id: The notification ID
            user_id: The user ID
            
        Returns:
            The notification or None if not found
        """
        try:
            query = select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(
                f"Failed to fetch notification: {str(e)}",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            raise ValidationError(f"Failed to fetch notification: {str(e)}")

    async def get_user_preferences(
        self,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get notification preferences for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            User's notification preferences or None if not found
        """
        try:
            query = select(User.notification_preferences).where(User.id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(
                f"Failed to fetch user preferences: {str(e)}",
                extra={"user_id": user_id, "error": str(e)}
            )
            raise ValidationError(f"Failed to fetch user preferences: {str(e)}")

    def _should_send_notification(
        self,
        category: NotificationCategory,
        preferences: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Check if notification should be sent based on user preferences.
        
        Args:
            category: The notification category
            preferences: User's notification preferences
            
        Returns:
            True if notification should be sent, False otherwise
        """
        if not preferences:
            return True
            
        category_enabled = preferences.get(f"{category.value.lower()}_enabled", True)
        if not category_enabled:
            return False
            
        # Check quiet hours
        if self._is_quiet_hours(preferences):
            return False
            
        return True

    def _is_quiet_hours(self, preferences: Dict[str, Any]) -> bool:
        """
        Check if current time is within quiet hours.
        
        Args:
            preferences: User's notification preferences
            
        Returns:
            True if current time is within quiet hours, False otherwise
        """
        if not preferences.get("quiet_hours_start") or not preferences.get("quiet_hours_end"):
            return False
            
        now = datetime.utcnow().time()
        start = datetime.strptime(preferences["quiet_hours_start"], "%H:%M").time()
        end = datetime.strptime(preferences["quiet_hours_end"], "%H:%M").time()
        
        return start <= now <= end 