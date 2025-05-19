"""
Admin Service

This module provides services for admin operations and user management.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.admin import AdminUser, AdminAuditLog, AdminScope
from app.models.user import User
from app.schemas.admin import AuditLogFilter, PaginatedAuditLogs

# Initialize logger
logger = get_logger(__name__)

class AdminService:
    """Service for admin operations and user management."""
    
    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
    
    async def get_admin_user(self, user_id: UUID) -> Optional[AdminUser]:
        """
        Get admin user by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            AdminUser instance or None
        """
        result = await self.db.execute(
            select(AdminUser)
            .where(AdminUser.user_id == user_id)
            .options(selectinload(AdminUser.audit_logs))
        )
        return result.scalar_one_or_none()
    
    async def create_admin_user(
        self,
        user_id: UUID,
        roles: List[str],
        scopes: List[str],
        request: Request
    ) -> AdminUser:
        """
        Create a new admin user.
        
        Args:
            user_id: User ID
            roles: List of admin roles
            scopes: List of admin scopes
            request: FastAPI request object
            
        Returns:
            Created AdminUser instance
            
        Raises:
            HTTPException: If user already has admin access
        """
        # Check if user exists
        user = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        if not user.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Check if admin user exists
        existing = await self.get_admin_user(user_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="User already has admin access"
            )
        
        # Create admin user
        admin_user = AdminUser(
            user_id=user_id,
            roles=roles,
            scopes=scopes
        )
        
        self.db.add(admin_user)
        await self.db.commit()
        await self.db.refresh(admin_user)
        
        # Log creation
        await self.log_admin_action(
            admin_id=admin_user.id,
            action="create_admin",
            resource_type="admin_user",
            resource_id=admin_user.id,
            details=f"Created admin user with roles: {roles}",
            request=request
        )
        
        return admin_user
    
    async def update_admin_user(
        self,
        admin_id: UUID,
        roles: List[str],
        scopes: List[str],
        is_active: bool,
        request: Request
    ) -> AdminUser:
        """
        Update admin user.
        
        Args:
            admin_id: Admin user ID
            roles: List of admin roles
            scopes: List of admin scopes
            is_active: Whether admin is active
            request: FastAPI request object
            
        Returns:
            Updated AdminUser instance
            
        Raises:
            HTTPException: If admin user not found
        """
        # Get admin user
        admin_user = await self.db.execute(
            select(AdminUser).where(AdminUser.id == admin_id)
        )
        admin_user = admin_user.scalar_one_or_none()
        if not admin_user:
            raise HTTPException(
                status_code=404,
                detail="Admin user not found"
            )
        
        # Update fields
        admin_user.roles = roles
        admin_user.scopes = scopes
        admin_user.is_active = is_active
        
        await self.db.commit()
        await self.db.refresh(admin_user)
        
        # Log update
        await self.log_admin_action(
            admin_id=admin_user.id,
            action="update_admin",
            resource_type="admin_user",
            resource_id=admin_user.id,
            details=f"Updated admin user with roles: {roles}",
            request=request
        )
        
        return admin_user
    
    async def get_user_details(self, user_id: UUID) -> dict:
        """
        Get detailed user information.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user details
            
        Raises:
            HTTPException: If user not found
        """
        # Get user with related data
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.kyc_profile),
                selectinload(User.linked_accounts),
                selectinload(User.transactions)
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Get recent transactions
        recent_txns = await self.db.execute(
            select(User.transactions)
            .where(User.id == user_id)
            .order_by(User.transactions.created_at.desc())
            .limit(5)
        )
        
        return {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "kyc_status": user.kyc_profile.status if user.kyc_profile else "pending",
            "created_at": user.created_at,
            "last_login": user.last_login,
            "linked_accounts": [
                {
                    "id": acc.id,
                    "type": acc.type,
                    "status": acc.status
                }
                for acc in user.linked_accounts
            ],
            "recent_transactions": [
                {
                    "id": txn.id,
                    "type": txn.type,
                    "amount": txn.amount,
                    "status": txn.status,
                    "created_at": txn.created_at
                }
                for txn in recent_txns.scalars().all()
            ]
        }
    
    async def freeze_user(
        self,
        user_id: UUID,
        admin_id: UUID,
        request: Request
    ) -> None:
        """
        Freeze user account.
        
        Args:
            user_id: User ID
            admin_id: Admin user ID
            request: FastAPI request object
            
        Raises:
            HTTPException: If user not found
        """
        # Get user
        user = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Update user
        user.is_active = False
        await self.db.commit()
        
        # Log action
        await self.log_admin_action(
            admin_id=admin_id,
            action="freeze_user",
            resource_type="user",
            resource_id=user_id,
            details="User account frozen",
            request=request
        )
    
    async def resend_notification(
        self,
        user_id: UUID,
        notification_type: str,
        template_data: Optional[dict],
        admin_id: UUID,
        request: Request
    ) -> None:
        """
        Resend notification to user.
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            template_data: Template variables
            admin_id: Admin user ID
            request: FastAPI request object
            
        Raises:
            HTTPException: If user not found
        """
        # Get user
        user = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # TODO: Implement notification sending
        # This would integrate with your notification service
        
        # Log action
        await self.log_admin_action(
            admin_id=admin_id,
            action="resend_notification",
            resource_type="user",
            resource_id=user_id,
            details=f"Resent {notification_type} notification",
            request=request
        )
    
    async def get_audit_logs(
        self,
        filters: AuditLogFilter
    ) -> PaginatedAuditLogs:
        """
        Get paginated audit logs with filters.
        
        Args:
            filters: Audit log filters
            
        Returns:
            Paginated audit logs
        """
        # Build query
        query = select(AdminAuditLog)
        
        # Apply filters
        conditions = []
        if filters.admin_id:
            conditions.append(AdminAuditLog.admin_id == filters.admin_id)
        if filters.action:
            conditions.append(AdminAuditLog.action == filters.action)
        if filters.resource_type:
            conditions.append(AdminAuditLog.resource_type == filters.resource_type)
        if filters.resource_id:
            conditions.append(AdminAuditLog.resource_id == filters.resource_id)
        if filters.start_date:
            conditions.append(AdminAuditLog.created_at >= filters.start_date)
        if filters.end_date:
            conditions.append(AdminAuditLog.created_at <= filters.end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Apply pagination
        query = query.order_by(AdminAuditLog.created_at.desc())
        query = query.offset((filters.page - 1) * filters.page_size)
        query = query.limit(filters.page_size)
        
        # Execute query
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        # Calculate pagination info
        total_pages = (total + filters.page_size - 1) // filters.page_size
        
        return PaginatedAuditLogs(
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
            has_next=filters.page < total_pages,
            has_prev=filters.page > 1,
            items=logs
        )
    
    async def log_admin_action(
        self,
        admin_id: UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID],
        details: Optional[str],
        request: Request
    ) -> AdminAuditLog:
        """
        Log admin action to audit trail.
        
        Args:
            admin_id: Admin user ID
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource ID
            details: Additional details
            request: FastAPI request object
            
        Returns:
            Created AdminAuditLog instance
        """
        log = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown")
        )
        
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        
        logger.info(
            f"Admin action logged",
            extra={
                "admin_id": admin_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id
            }
        )
        
        return log 