"""
Admin User Management Router

This module provides endpoints for admin user management.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin_read, get_current_admin_act, get_current_super_admin
from app.db.session import get_db
from app.models.admin import AdminUser, AdminRole, AdminScope
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminUserResponse,
    UserLookupResponse,
    NotificationRequest,
    PaginatedAuditLogs,
    AuditLogFilter
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users/{user_id}", response_model=UserLookupResponse)
async def get_user_details(
    user_id: UUID,
    admin: AdminUser = Depends(get_current_admin_read),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed user information.
    
    Args:
        user_id: User ID
        admin: Current admin user
        db: Database session
        
    Returns:
        User details with KYC, accounts, and transactions
    """
    service = AdminService(db)
    return await service.get_user_details(user_id)

@router.post("/users/{user_id}/freeze", status_code=status.HTTP_204_NO_CONTENT)
async def freeze_user(
    user_id: UUID,
    request: Request,
    admin: AdminUser = Depends(get_current_admin_act),
    db: AsyncSession = Depends(get_db)
):
    """
    Freeze user account.
    
    Args:
        user_id: User ID
        request: FastAPI request
        admin: Current admin user
        db: Database session
    """
    service = AdminService(db)
    await service.freeze_user(user_id, admin.id, request)

@router.post("/users/{user_id}/resend-notification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_notification(
    user_id: UUID,
    notification: NotificationRequest,
    request: Request,
    admin: AdminUser = Depends(get_current_admin_act),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend notification to user.
    
    Args:
        user_id: User ID
        notification: Notification request
        request: FastAPI request
        admin: Current admin user
        db: Database session
    """
    service = AdminService(db)
    await service.resend_notification(
        user_id,
        notification.notification_type,
        notification.template_data,
        admin.id,
        request
    )

@router.get("/audit-logs", response_model=PaginatedAuditLogs)
async def get_audit_logs(
    filters: AuditLogFilter = Depends(),
    admin: AdminUser = Depends(get_current_admin_read),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated audit logs with filters.
    
    Args:
        filters: Audit log filters
        admin: Current admin user
        db: Database session
        
    Returns:
        Paginated audit logs
    """
    service = AdminService(db)
    return await service.get_audit_logs(filters)

@router.post("/admins", response_model=AdminUserResponse)
async def create_admin(
    admin_data: AdminUserCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create new admin user.
    
    Args:
        admin_data: Admin user data
        request: FastAPI request
        admin: Current super admin
        db: Database session
        
    Returns:
        Created admin user
    """
    service = AdminService(db)
    return await service.create_admin_user(
        admin_data.user_id,
        admin_data.roles,
        admin_data.scopes,
        request
    )

@router.put("/admins/{admin_id}", response_model=AdminUserResponse)
async def update_admin(
    admin_id: UUID,
    admin_data: AdminUserUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update admin user.
    
    Args:
        admin_id: Admin user ID
        admin_data: Admin user data
        request: FastAPI request
        admin: Current super admin
        db: Database session
        
    Returns:
        Updated admin user
    """
    service = AdminService(db)
    return await service.update_admin_user(
        admin_id,
        admin_data.roles,
        admin_data.scopes,
        admin_data.is_active,
        request
    ) 