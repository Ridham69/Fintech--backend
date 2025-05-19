"""
Webhook Schemas

This module defines Pydantic models for webhook validation and responses.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.webhooks import WebhookStatus

class WebhookBase(BaseModel):
    """Base schema for webhook data."""
    
    provider: str = Field(..., min_length=1, max_length=50)
    event_type: str = Field(..., min_length=1, max_length=100)
    payload: Dict[str, Any] = Field(...)
    headers: Dict[str, str] = Field(...)
    signature: str = Field(..., min_length=1, max_length=255)
    signature_type: str = Field(..., pattern="^(hmac|rsa)$")

class WebhookCreate(WebhookBase):
    """Schema for creating a webhook event."""
    
    pass

class WebhookResponse(WebhookBase):
    """Schema for webhook response."""
    
    id: UUID
    status: WebhookStatus
    received_at: datetime
    processed_at: Optional[datetime] = None
    attempts: int
    max_attempts: int
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class WebhookRetry(BaseModel):
    """Schema for webhook retry request."""
    
    webhook_id: UUID
    max_attempts: Optional[int] = Field(default=3, ge=1, le=10)

class WebhookVerification(BaseModel):
    """Schema for webhook verification result."""
    
    is_valid: bool
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

@field_validator("headers")
def validate_headers(cls, v: Dict[str, str]) -> Dict[str, str]:
    """Validate required headers."""
    required_headers = {
        "x-webhook-signature",
        "x-webhook-timestamp",
        "content-type"
    }
    missing = required_headers - set(k.lower() for k in v.keys())
    if missing:
        raise ValueError(f"Missing required headers: {missing}")
    return v 