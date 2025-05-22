"""
Notification Routes

This module provides FastAPI routes for notification-related operations,
including fetching and managing notifications.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.notification import (
    NotificationResponse,
    NotificationList,
    NotificationPreferenceResponse
)
from app.services.notification import NotificationService
from app.models.notification import NotificationCategory, NotificationPriority

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get(
    "",
    response_model=NotificationList,
    summary="Get user notifications",
    description="Retrieve notifications for the current user with optional filtering"
)
async def get_notifications(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    only_unread: bool = Query(False, description="Filter for unread notifications only"),
    category: Optional[NotificationCategory] = Query(None, description="Filter by notification category"),
    priority: Optional[NotificationPriority] = Query(None, description="Filter by notification priority"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date")
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch notifications"
        )

@router.get(
    "/unread",
    response_model=NotificationList,
    summary="Get unread notifications",
    description="Retrieve only unread notifications for the current user"
)
async def get_unread_notifications(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return")
) -> NotificationList:
    """
    Get unread notifications for the current user.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of unread notifications with metadata
        
    Raises:
        HTTPException: If fetching notifications fails
    """
    try:
        service = NotificationService(db)
        return await service.get_user_notifications(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            only_unread=True
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch unread notifications"
        )

@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get specific notification",
    description="Retrieve details of a specific notification"
)
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        return notification
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch notification"
        )

@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
    description="Mark a specific notification as read"
)
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        return notification
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )

@router.post(
    "/read-all",
    response_model=dict,
    summary="Mark all notifications as read",
    description="Mark all notifications as read for the current user"
)
async def mark_all_as_read(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    category: Optional[NotificationCategory] = Query(None, description="Optional category filter")
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark all notifications as read"
        )

@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Get notification preferences",
    description="Get notification preferences for the current user"
)
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification preferences not found"
            )
        return preferences
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch notification preferences"
        ) 
