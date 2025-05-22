"""
Payment models for handling payment intents and providers.

This module defines the PaymentIntent model and related enums for managing
payment processing through various payment providers. It includes:
- UUID-based identification
- Provider-specific details
- Status tracking
- Sandbox/Production mode
- Audit fields
- Relationships to User and Transaction models
"""
from app.models.types import GUID
from app.models.types import GUID

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Boolean,
    Numeric, Index, CheckConstraint, event, JSON
)
from app.models.types import GUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base
from app.models.audit_mixin import AuditMixin
from app.models.user import User

class PaymentProvider(str, Enum):
    """Supported payment providers."""
    RAZORPAY = "RAZORPAY"
    STRIPE = "STRIPE"
    CASHFREE = "CASHFREE"
    PAYTM = "PAYTM"
    PHONEPE = "PHONEPE"
    GPAY = "GPAY"

class PaymentIntentStatus(str, Enum):
    """Payment intent status enum."""
    INITIATED = "INITIATED"
    REQUIRES_PAYMENT_METHOD = "REQUIRES_PAYMENT_METHOD"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    REQUIRES_ACTION = "REQUIRES_ACTION"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

class PaymentMethod(str, Enum):
    """Payment method types."""
    UPI = "UPI"
    NETBANKING = "NETBANKING"
    CARD = "CARD"
    WALLET = "WALLET"
    EMI = "EMI"
    PAYPAL = "PAYPAL"

class PaymentIntent(Base, AuditMixin):
    """
    Payment Intent model for managing payment processing.
    
    Attributes:
        id (UUID): Primary key
        user_id (UUID): Foreign key to user
        amount (Decimal): Payment amount
        currency (str): Currency code (ISO 4217)
        provider (PaymentProvider): Payment service provider
        provider_intent_id (str): Provider-specific intent ID
        status (PaymentIntentStatus): Current status
        payment_method (PaymentMethod): Selected payment method
        sandbox (bool): Whether in test mode
        metadata (dict): Additional payment data
        error_message (str): Error details if failed
        return_url (str): URL to redirect after payment
        webhook_url (str): URL for payment webhooks
        description (str): Payment description
        expires_at (datetime): Payment intent expiry
    """
    
    __tablename__ = "payment_intents"
    
    # Primary key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    
    # Provider details
    provider = Column(Enum(PaymentProvider), nullable=False)
    provider_intent_id = Column(String(255), unique=True)
    status = Column(
        Enum(PaymentIntentStatus),
        default=PaymentIntentStatus.INITIATED,
        nullable=False
    )
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    
    # Environment
    sandbox = Column(Boolean, default=True, nullable=False)
    
    # Additional details
    metadata = Column(JSONB, nullable=True)
    error_message = Column(String(1000), nullable=True)
    return_url = Column(String(1000), nullable=True)
    webhook_url = Column(String(1000), nullable=True)
    description = Column(String(500), nullable=True)
    
    # Expiry
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payment_intents")
    transactions = relationship("Transaction", back_populates="payment_intent")
    
    # Indexes
    __table_args__ = (
        Index("ix_payment_intents_user_id", "user_id"),
        Index("ix_payment_intents_provider_intent_id", "provider_intent_id"),
        Index("ix_payment_intents_status", "status"),
        Index("ix_payment_intents_created_at", "created_at"),
        # Ensure amount is positive
        CheckConstraint("amount > 0", name="ck_payment_intent_amount_positive"),
        # Ensure valid currency code
        CheckConstraint("length(currency) = 3", name="ck_currency_code_length")
    )
    
    @validates("amount")
    def validate_amount(self, key: str, amount: Decimal) -> Decimal:
        """Validate payment amount."""
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        return amount
    
    @validates("currency")
    def validate_currency(self, key: str, currency: str) -> str:
        """Validate currency code."""
        if len(currency) != 3:
            raise ValueError("Currency code must be 3 characters (ISO 4217)")
        return currency.upper()
    
    @validates("return_url", "webhook_url")
    def validate_url(self, key: str, url: Optional[str]) -> Optional[str]:
        """Validate URL format."""
        if url and not url.startswith(("http://", "https://")):
            raise ValueError(f"{key} must be a valid HTTP(S) URL")
        return url
    
    @hybrid_property
    def is_successful(self) -> bool:
        """Check if payment was successful."""
        return self.status == PaymentIntentStatus.SUCCEEDED
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if payment intent has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @hybrid_property
    def requires_action(self) -> bool:
        """Check if payment requires customer action."""
        return self.status in (
            PaymentIntentStatus.REQUIRES_PAYMENT_METHOD,
            PaymentIntentStatus.REQUIRES_CONFIRMATION,
            PaymentIntentStatus.REQUIRES_ACTION
        )
    
    def get_provider_data(self) -> Dict[str, Any]:
        """Get provider-specific configuration."""
        if self.provider == PaymentProvider.RAZORPAY:
            return {
                "key_id": settings.external.RAZORPAY_KEY_ID.get_secret_value(),
                "amount": int(self.amount * 100),  # Convert to paise
                "currency": self.currency,
                "name": settings.app.TITLE,
                "description": self.description,
                "order_id": self.provider_intent_id,
                "prefill": {
                    "email": self.user.email,
                    "contact": self.user.phone
                }
            }
        # Add other provider configurations as needed
        return {}
    
    def __repr__(self) -> str:
        return (
            f"<PaymentIntent(id={self.id}, "
            f"user_id={self.user_id}, "
            f"amount={self.amount} {self.currency}, "
            f"provider={self.provider}, "
            f"status={self.status})>"
        )

@event.listens_for(PaymentIntent, "before_insert")
def set_expiry(mapper, connection, target):
    """Set expiry timestamp if not provided."""
    if not target.expires_at:
        target.expires_at = datetime.utcnow() + timedelta(minutes=30)  # 30-minute expiry 
