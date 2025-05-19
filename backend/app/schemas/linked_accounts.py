"""
Linked Account Schemas

This module defines Pydantic models for linked account operations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.linked_accounts import AccountType

class LinkedAccountBase(BaseModel):
    """Base schema for linked account data."""
    
    account_type: AccountType
    provider: str = Field(..., min_length=1, max_length=100)
    account_number_masked: str = Field(..., min_length=4, max_length=50)
    account_ref_id: str = Field(..., min_length=1, max_length=255)
    is_primary: bool = False
    metadata: Optional[dict] = None

class LinkedAccountCreate(LinkedAccountBase):
    """Schema for creating a linked account."""
    
    pass

class LinkedAccountUpdate(BaseModel):
    """Schema for updating a linked account."""
    
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None

class LinkedAccountResponse(LinkedAccountBase):
    """Schema for linked account response."""
    
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class LinkedAccountList(BaseModel):
    """Schema for list of linked accounts."""
    
    items: list[LinkedAccountResponse]
    total: int

@field_validator("account_number_masked")
def validate_account_number(cls, v: str) -> str:
    """Validate account number format."""
    # Ensure at least last 4 digits are visible
    if len(v) < 4 or not v[-4:].isdigit():
        raise ValueError("Account number must show at least last 4 digits")
    return v 