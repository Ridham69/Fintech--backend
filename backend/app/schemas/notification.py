"""
Notification schemas.

This module defines Pydantic models for notification-related data validation
and serialization, including request/response models and internal processing.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    EmailStr,
    HttpUrl
)

from app.models.notification import (
    NotificationCategory,
    NotificationChannel,
    NotificationPriority
)

class NotificationTemplate(BaseModel):
    """Base schema for notification templates."""
    
    template_id: str = Field(..., min_length=1, max_length=100)
    title_template: str = Field(..., min_length=1, max_length=255)
    message_template: str = Field(..., min_length=1)
    category: NotificationCategory
    priority: NotificationPriority = NotificationPriority.MEDIUM
    channels: List[NotificationChannel] = Field(default=[NotificationChannel.IN_APP])
    required_params: List[str] = Field(default_factory=list)
    metadata: Optional[dict] = None

class NotificationBase(BaseModel):
    """Base schema for notification data."""
    
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    category: NotificationCategory = Field(default=NotificationCategory.SYSTEM)
    priority: NotificationPriority = Field(default=NotificationPriority.MEDIUM)
    channels: List[NotificationChannel] = Field(default=[NotificationChannel.IN_APP])
    metadata: Optional[dict] = None
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate notification title."""
        if len(v.strip()) == 0:
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate notification message."""
        if len(v.strip()) == 0:
            raise ValueError("Message cannot be empty or whitespace")
        return v.strip()

class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""
    
    user_id: UUID
    template_id: Optional[str] = None
    template_params: Optional[dict] = None
    email_to: Optional[EmailStr] = None
    sms_to: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    push_token: Optional[str] = None
    action_url: Optional[HttpUrl] = None
    
    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: List[NotificationChannel], values: dict) -> List[NotificationChannel]:
        """Validate notification channels and required fields."""
        if not v:
            raise ValueError("At least one notification channel must be specified")
        
        # Validate channel-specific fields
        if NotificationChannel.EMAIL in v and not values.get("email_to"):
            raise ValueError("Email address required for email notifications")
        if NotificationChannel.SMS in v and not values.get("sms_to"):
            raise ValueError("Phone number required for SMS notifications")
        if NotificationChannel.PUSH in v and not values.get("push_token"):
            raise ValueError("Push token required for push notifications")
        
        return v
    
    @model_validator(mode="after")
    def validate_template(self) -> "NotificationCreate":
        """Validate template usage."""
        if self.template_id and not self.template_params:
            raise ValueError("Template parameters required when using template_id")
        return self

class NotificationUpdate(BaseModel):
    """Schema for updating a notification."""
    
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    
    @model_validator(mode="after")
    def validate_read_status(self) -> "NotificationUpdate":
        """Validate read status and timestamp."""
        if self.is_read and not self.read_at:
            self.read_at = datetime.utcnow()
        return self

class NotificationResponse(NotificationBase):
    """Schema for notification response."""
    
    id: UUID
    user_id: UUID
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    action_url: Optional[HttpUrl]
    
    model_config = ConfigDict(from_attributes=True)

class NotificationList(BaseModel):
    """Schema for paginated list of notifications."""
    
    items: List[NotificationResponse]
    total: int
    page: int
    size: int
    unread_count: int

class NotificationPreferenceBase(BaseModel):
    """Base schema for notification preferences."""
    
    email_enabled: bool = Field(default=True)
    sms_enabled: bool = Field(default=False)
    push_enabled: bool = Field(default=True)
    in_app_enabled: bool = Field(default=True)
    
    # Category-specific preferences
    system_enabled: bool = Field(default=True)
    transactional_enabled: bool = Field(default=True)
    promotional_enabled: bool = Field(default=True)
    security_enabled: bool = Field(default=True)
    investment_enabled: bool = Field(default=True)
    
    # Quiet hours
    quiet_hours_start: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    
    # Channel-specific settings
    email_frequency: str = Field(default="IMMEDIATE", pattern="^(IMMEDIATE|DAILY|WEEKLY)$")
    sms_frequency: str = Field(default="IMMEDIATE", pattern="^(IMMEDIATE|DAILY|WEEKLY)$")
    push_frequency: str = Field(default="IMMEDIATE", pattern="^(IMMEDIATE|DAILY|WEEKLY)$")
    
    # Language preferences
    preferred_language: str = Field(default="en", min_length=2, max_length=5)
    
    @model_validator(mode="after")
    def validate_quiet_hours(self) -> "NotificationPreferenceBase":
        """Validate quiet hours if provided."""
        if (self.quiet_hours_start and not self.quiet_hours_end) or (
            self.quiet_hours_end and not self.quiet_hours_start
        ):
            raise ValueError("Both start and end times must be provided for quiet hours")
        return self

class NotificationPreferenceCreate(NotificationPreferenceBase):
    """Schema for creating notification preferences."""
    pass

class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preferences."""
    
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    
    # Category-specific preferences
    system_enabled: Optional[bool] = None
    transactional_enabled: Optional[bool] = None
    promotional_enabled: Optional[bool] = None
    security_enabled: Optional[bool] = None
    investment_enabled: Optional[bool] = None
    
    # Quiet hours
    quiet_hours_start: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    
    # Channel-specific settings
    email_frequency: Optional[str] = Field(None, pattern="^(IMMEDIATE|DAILY|WEEKLY)$")
    sms_frequency: Optional[str] = Field(None, pattern="^(IMMEDIATE|DAILY|WEEKLY)$")
    push_frequency: Optional[str] = Field(None, pattern="^(IMMEDIATE|DAILY|WEEKLY)$")
    
    # Language preferences
    preferred_language: Optional[str] = Field(None, min_length=2, max_length=5)
    
    @model_validator(mode="after")
    def validate_quiet_hours(self) -> "NotificationPreferenceUpdate":
        """Validate quiet hours if provided."""
        if (self.quiet_hours_start and not self.quiet_hours_end) or (
            self.quiet_hours_end and not self.quiet_hours_start
        ):
            raise ValueError("Both start and end times must be provided for quiet hours")
        return self

class NotificationPreferenceResponse(NotificationPreferenceBase):
    """Schema for notification preferences response."""
    
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
