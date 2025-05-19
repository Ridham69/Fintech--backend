"""
Audit Log Schema

This module defines the Pydantic schemas for audit logs.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

class AuditLogBase(BaseModel):
    """Base schema for audit logs."""
    
    action: str = Field(..., description="Action performed (e.g., kyc.update, transaction.create)")
    target_table: str = Field(..., description="Table where the action was performed")
    target_id: str = Field(..., description="ID of the affected record")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")

class AuditLogCreate(AuditLogBase):
    """Schema for creating audit logs."""
    
    user_id: Optional[UUID] = Field(None, description="ID of the user who performed the action")
    ip_address: str = Field(..., description="IP address of the actor")
    user_agent: str = Field(..., description="User agent of the actor")

class AuditLogInDB(AuditLogBase):
    """Schema for audit logs in database."""
    
    id: UUID = Field(..., description="Unique identifier for the audit log entry")
    user_id: Optional[UUID] = Field(None, description="ID of the user who performed the action")
    ip_address: str = Field(..., description="IP address of the actor")
    user_agent: str = Field(..., description="User agent of the actor")
    timestamp: datetime = Field(..., description="When the action was performed")
    
    class Config:
        """Pydantic config."""
        
        from_attributes = True

class AuditLogResponse(AuditLogInDB):
    """Schema for audit log responses."""
    
    pass 