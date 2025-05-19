"""
Payment schemas for API request/response validation.

This module provides Pydantic models for payment-related operations,
including input validation, response formatting, and type safety.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, UUID4, Field, validator, ConfigDict, AnyHttpUrl
from pydantic.types import constr, condecimal

class PaymentProvider(str, Enum):
    """Payment provider enumeration."""
    RAZORPAY = "RAZORPAY"
    STRIPE = "STRIPE"
    CASHFREE = "CASHFREE"
    PAYTM = "PAYTM"
    PHONEPE = "PHONEPE"
    GPAY = "GPAY"

class PaymentMethod(str, Enum):
    """Payment method enumeration."""
    UPI = "UPI"
    NETBANKING = "NETBANKING"
    CARD = "CARD"
    WALLET = "WALLET"
    EMI = "EMI"
    PAYPAL = "PAYPAL"

class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    INITIATED = "INITIATED"
    REQUIRES_PAYMENT_METHOD = "REQUIRES_PAYMENT_METHOD"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    REQUIRES_ACTION = "REQUIRES_ACTION"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

class PaymentIntentBase(BaseModel):
    """Base payment intent schema with common fields."""
    
    amount: condecimal(gt=Decimal('0'), decimal_places=2) = Field(
        ...,
        description="Payment amount (must be positive)",
        example=1000.00
    )
    currency: constr(min_length=3, max_length=3) = Field(
        default="INR",
        description="ISO 4217 currency code",
        example="INR"
    )
    provider: PaymentProvider = Field(
        ...,
        description="Payment service provider"
    )
    payment_method: Optional[PaymentMethod] = Field(
        None,
        description="Preferred payment method"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Payment description",
        example="Investment deposit"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional payment data"
    )

    @validator('currency')
    def validate_currency(cls, v: str) -> str:
        """Validate and normalize currency code."""
        return v.upper()

class PaymentIntentCreate(PaymentIntentBase):
    """Schema for creating a new payment intent."""
    
    return_url: Optional[AnyHttpUrl] = Field(
        None,
        description="URL to redirect after payment"
    )
    webhook_url: Optional[AnyHttpUrl] = Field(
        None,
        description="URL for payment webhooks"
    )
    sandbox: Optional[bool] = Field(
        True,
        description="Whether to use sandbox mode"
    )

class PaymentIntentUpdate(BaseModel):
    """Schema for updating a payment intent."""
    
    status: PaymentStatus = Field(
        ...,
        description="New payment status"
    )
    error_message: Optional[str] = Field(
        None,
        max_length=1000,
        description="Error message if payment failed"
    )
    provider_intent_id: Optional[str] = Field(
        None,
        description="Provider-specific intent ID"
    )

class PaymentIntentResponse(PaymentIntentBase):
    """Schema for payment intent response."""
    
    id: UUID4 = Field(..., description="Payment intent ID")
    user_id: UUID4 = Field(..., description="User ID")
    status: PaymentStatus = Field(..., description="Current status")
    provider_intent_id: Optional[str] = Field(
        None,
        description="Provider-specific intent ID"
    )
    sandbox: bool = Field(..., description="Whether in sandbox mode")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    expires_at: Optional[datetime] = Field(None, description="Expiry timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)

class PaymentIntentList(BaseModel):
    """Schema for list of payment intents."""
    
    items: list[PaymentIntentResponse]
    total: int = Field(..., description="Total number of payment intents")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    
    model_config = ConfigDict(from_attributes=True)

class PaymentMethodConfig(BaseModel):
    """Schema for payment method configuration."""
    
    method: PaymentMethod
    enabled: bool = Field(..., description="Whether method is enabled")
    min_amount: condecimal(decimal_places=2) = Field(
        ...,
        description="Minimum amount allowed"
    )
    max_amount: condecimal(decimal_places=2) = Field(
        ...,
        description="Maximum amount allowed"
    )
    supported_currencies: list[str] = Field(
        ...,
        description="Supported currency codes"
    )
    provider_config: Dict[str, Any] = Field(
        ...,
        description="Provider-specific configuration"
    )
    
    model_config = ConfigDict(from_attributes=True)

class PaymentProviderConfig(BaseModel):
    """Schema for payment provider configuration."""
    
    provider: PaymentProvider
    is_enabled: bool = Field(..., description="Whether provider is enabled")
    supported_methods: list[PaymentMethodConfig] = Field(
        ...,
        description="Supported payment methods"
    )
    webhook_secret: Optional[str] = Field(None, description="Webhook secret key")
    sandbox_config: Dict[str, Any] = Field(
        ...,
        description="Sandbox configuration"
    )
    production_config: Dict[str, Any] = Field(
        ...,
        description="Production configuration"
    )
    
    model_config = ConfigDict(from_attributes=True) 