"""
Admin Schemas

This module defines Pydantic models for admin operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.admin import AdminRole, AdminScope

class AdminUserBase(BaseModel):
    """Base schema for admin user data."""
    
    roles: List[AdminRole]
    scopes: List[AdminScope]
    is_active: bool = True

class AdminUserCreate(AdminUserBase):
    """Schema for creating an admin user."""
    
    user_id: UUID

class AdminUserUpdate(AdminUserBase):
    """Schema for updating an admin user."""
    
    pass

class AdminUserResponse(AdminUserBase):
    """Schema for admin user response."""
    
    id: UUID
    user_id: UUID
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AdminAuditLogBase(BaseModel):
    """Base schema for admin audit log data."""
    
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    details: Optional[str]
    ip_address: str
    user_agent: str

class AdminAuditLogCreate(AdminAuditLogBase):
    """Schema for creating an admin audit log."""
    
    admin_id: UUID

class AdminAuditLogResponse(AdminAuditLogBase):
    """Schema for admin audit log response."""
    
    id: UUID
    admin_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLookupResponse(BaseModel):
    """Schema for user lookup response."""
    
    id: UUID
    email: str
    is_active: bool
    kyc_status: str
    created_at: datetime
    last_login: Optional[datetime]
    linked_accounts: List[dict]
    recent_transactions: List[dict]
    
    class Config:
        from_attributes = True

class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""
    
    admin_id: Optional[UUID] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(BaseModel):
    """Base schema for paginated responses."""
    
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

class PaginatedAuditLogs(PaginatedResponse):
    """Schema for paginated audit logs response."""
    
    items: List[AdminAuditLogResponse]

class NotificationRequest(BaseModel):
    """Schema for notification request."""
    
    notification_type: str = Field(..., description="Type of notification to send")
    template_data: Optional[dict] = Field(default=None, description="Template variables")
    force: bool = Field(default=False, description="Force send even if recently sent") 