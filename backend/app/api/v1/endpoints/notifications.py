"""
Notification API endpoints.

This module provides FastAPI routes for notification-related operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationList,
    NotificationPreferenceCreate,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate
)
from app.services.notification import NotificationService
from app.models.notification import NotificationCategory, NotificationPriority

router = APIRouter()

@router.post("", response_model=NotificationResponse)
async def create_notification(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    notification_in: NotificationCreate,
    background_tasks: BackgroundTasks
) -> NotificationResponse:
    """
    Create a new notification.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        notification_in: Notification data
        background_tasks: Background tasks manager
        
    Returns:
        Created notification
        
    Raises:
        HTTPException: If notification creation fails
    """
    try:
        service = NotificationService(db)
        notification = await service.create_notification(
            user_id=current_user.id,
            payload=notification_in,
            background_tasks=background_tasks
        )
        return notification
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=NotificationList)
async def get_notifications(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    only_unread: bool = False,
    category: Optional[NotificationCategory] = None,
    priority: Optional[NotificationPriority] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> NotificationList:
    """
    Get user notifications with filtering options.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        skip: Number of records to skip
        limit: Maximum number of records to return
        only_unread: Filter for unread notifications only
        category: Filter by notification category
        priority: Filter by notification priority
        start_date: Filter by start date
        end_date: Filter by end date
        
    Returns:
        List of notifications with metadata
        
    Raises:
        HTTPException: If fetching notifications fails
    """
    try:
        service = NotificationService(db)
        return await service.get_user_notifications(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            only_unread=only_unread,
            category=category,
            priority=priority,
            start_date=start_date,
            end_date=end_date
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    notification_id: UUID
) -> NotificationResponse:
    """
    Get a specific notification.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        notification_id: Notification ID
        
    Returns:
        Notification details
        
    Raises:
        HTTPException: If notification not found or fetching fails
    """
    try:
        service = NotificationService(db)
        notification = await service.get_notification(
            notification_id=notification_id,
            user_id=current_user.id
        )
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        return notification
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    notification_id: UUID
) -> NotificationResponse:
    """
    Mark a notification as read.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        notification_id: Notification ID
        
    Returns:
        Updated notification
        
    Raises:
        HTTPException: If notification not found or update fails
    """
    try:
        service = NotificationService(db)
        notification = await service.mark_notification_as_read(
            notification_id=notification_id,
            user_id=current_user.id
        )
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        return notification
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/read-all", response_model=dict)
async def mark_all_as_read(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    category: Optional[NotificationCategory] = None
) -> dict:
    """
    Mark all notifications as read.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        category: Optional category filter
        
    Returns:
        Number of notifications marked as read
        
    Raises:
        HTTPException: If update fails
    """
    try:
        service = NotificationService(db)
        count = await service.mark_all_as_read(
            user_id=current_user.id,
            category=category
        )
        return {"count": count}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
) -> NotificationPreferenceResponse:
    """
    Get user notification preferences.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        User's notification preferences
        
    Raises:
        HTTPException: If preferences not found or fetching fails
    """
    try:
        service = NotificationService(db)
        preferences = await service.get_user_preferences(current_user.id)
        if not preferences:
            raise HTTPException(status_code=404, detail="Notification preferences not found")
        return preferences
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preferences", response_model=NotificationPreferenceResponse)
async def create_preferences(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    preferences_in: NotificationPreferenceCreate
) -> NotificationPreferenceResponse:
    """
    Create user notification preferences.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        preferences_in: Notification preferences data
        
    Returns:
        Created notification preferences
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        service = NotificationService(db)
        preferences = await service.create_user_preferences(
            user_id=current_user.id,
            preferences=preferences_in
        )
        return preferences
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    preferences_in: NotificationPreferenceUpdate
) -> NotificationPreferenceResponse:
    """
    Update user notification preferences.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        preferences_in: Updated notification preferences
        
    Returns:
        Updated notification preferences
        
    Raises:
        HTTPException: If update fails
    """
    try:
        service = NotificationService(db)
        preferences = await service.update_user_preferences(
            user_id=current_user.id,
            preferences=preferences_in
        )
        if not preferences:
            raise HTTPException(status_code=404, detail="Notification preferences not found")
        return preferences
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
