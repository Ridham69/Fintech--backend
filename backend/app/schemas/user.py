"""Pydantic schemas for user-related operations."""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base schema for user data."""
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    
    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,  # Argon2 max length
        description="User's password (8-72 characters)"
    )
    confirm_password: str = Field(
        ...,
        description="Password confirmation"
    )
    tenant_id: Optional[UUID] = Field(None, description="Multi-tenant organization ID")
    
    @field_validator("confirm_password")
    def passwords_match(cls, v: str, values: Dict[str, Any]) -> str:
        """Validate that password and confirm_password match."""
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    device_id: Optional[str] = Field(
        None,
        description="Unique device identifier"
    )


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""
    sub: UUID = Field(..., description="Subject (user ID)")
    exp: datetime = Field(..., description="Expiration timestamp")
    iat: datetime = Field(..., description="Issued at timestamp")
    jti: str = Field(..., description="JWT ID")
    type: str = Field(..., description="Token type (access/refresh)")
    role: UserRole = Field(..., description="User role")
    tenant_id: Optional[UUID] = Field(None, description="Multi-tenant organization ID")
    device_id: Optional[str] = Field(None, description="Device identifier")


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class UserResponse(UserBase):
    """Schema for user response data."""
    id: UUID = Field(..., description="User ID")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="Account status")
    is_verified: bool = Field(..., description="Email verification status")
    kyc_verified: bool = Field(..., description="KYC verification status")
    tenant_id: Optional[UUID] = Field(None, description="Multi-tenant organization ID")
    investment_profile: Optional[Dict[str, Any]] = Field(None, description="User's investment preferences")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")


class UserUpdate(BaseModel):
    """Schema for updating user data."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    investment_profile: Optional[Dict[str, Any]] = Field(None)
    is_active: Optional[bool] = Field(None)
    
    model_config = ConfigDict(from_attributes=True) 
