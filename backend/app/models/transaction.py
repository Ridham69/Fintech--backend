"""
Transaction model for financial operations.

This module defines the Transaction model and related enums for handling
financial transactions in the system. It includes:
- UUID-based identification
- Status tracking
- Transaction types
- Amount handling with currency
- Idempotency support
- Audit fields
- Relationships to User and other models
"""
from app.models.types import GUID

import uuid
from datetime import datetime
from enum import Enum as PythonEnum # Added import
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Boolean, 
    Numeric, Index, CheckConstraint, event
)
from app.models.types import GUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base
from app.models.audit_mixin import AuditMixin
# from app.models.user import User # Removed to break circular import
from .payment import PaymentIntent # Added for relationship type hinting


class TransactionStatus(str, PythonEnum): # Changed base class
    """Transaction status enum."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"

class TransactionType(str, PythonEnum): # Changed base class
    """Transaction type enum."""
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class PaymentMethod(str, PythonEnum): # Changed base class
    """Payment method enum."""
    UPI = "UPI"
    NETBANKING = "NETBANKING"
    CARD = "CARD"
    WALLET = "WALLET"
    NEFT = "NEFT"
    RTGS = "RTGS"
    IMPS = "IMPS"

class Transaction(Base, AuditMixin):
    """
    Transaction model for financial operations.
    
    Attributes:
        id (UUID): Primary key
        user_id (UUID): Foreign key to user
        amount (Decimal): Transaction amount
        currency (str): Currency code (ISO 4217)
        status (TransactionStatus): Current status
        type (TransactionType): Transaction type
        payment_method (PaymentMethod): Payment method used
        description (str): Transaction description
        reference_id (str): External reference for idempotency
        metadata (dict): Additional transaction data
        is_settled (bool): Settlement status
        settled_at (datetime): Settlement timestamp
        failure_reason (str): Reason for failure if applicable
        reversal_reason (str): Reason for reversal if applicable
        parent_id (UUID): Parent transaction for refunds/reversals
    """
    
    __tablename__ = "transactions"
    
    # Primary key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(String(3), default="INR")
    status = Column(
        Enum(*[ts.value for ts in TransactionStatus], native_enum=False), # Explicit values
        default=TransactionStatus.PENDING.value, # Use .value for default
        nullable=False
    )
    type = Column(Enum(*[tt.value for tt in TransactionType], native_enum=False), nullable=False) # Explicit values
    payment_method = Column(Enum(*[pm.value for pm in PaymentMethod], native_enum=False), nullable=True) # Explicit values
    
    # Description and reference
    description = Column(String(500), nullable=True)
    reference_id = Column(String(100), unique=True, nullable=True)
    # Renamed 'metadata' to 'meta_data' to avoid SQLAlchemy reserved name conflict
    meta_data = Column("metadata", JSONB, nullable=True)
    
    # Settlement tracking
    is_settled = Column(Boolean, default=False, nullable=False)
    settled_at = Column(DateTime, nullable=True)
    
    # Failure and reversal tracking
    failure_reason = Column(String(500), nullable=True)
    reversal_reason = Column(String(500), nullable=True)
    
    # Self-referential relationship for refunds/reversals
    parent_id = Column(
        GUID(),
        ForeignKey("transactions.id"),
        nullable=True
    )
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    payment_intent = relationship("PaymentIntent", back_populates="transactions") # Added relationship
    linked_account = relationship("LinkedAccount", back_populates="transactions") # Ensure this line is present
    child_transactions = relationship(
        "Transaction",
        backref="parent_transaction",
        remote_side=[id]
    )
    
    # Foreign Keys
    payment_intent_id = Column(GUID(), ForeignKey("payment_intents.id"), nullable=True, index=True) # Added FK column
    # Ensure linked_account_id FK is present (it was in the read file, so this part of search should match)
    linked_account_id = Column(GUID(), ForeignKey("linked_accounts.id"), nullable=True, index=True) 

    # Indexes
    __table_args__ = (
        Index("ix_transactions_user_id", "user_id"),
        Index("ix_transactions_reference_id", "reference_id"),
        Index("ix_transactions_status", "status"),
        Index("ix_transactions_created_at", "created_at"),
        # Ensure amount is positive
        CheckConstraint("amount >= 0", name="ck_transaction_amount_positive"),
        # Ensure valid currency code
        CheckConstraint("length(currency) = 3", name="ck_currency_code_length")
    )
    
    @validates("amount")
    def validate_amount(self, key: str, amount: Decimal) -> Decimal:
        """Validate transaction amount."""
        if amount <= 0:
            raise ValueError("Transaction amount must be positive")
        return amount
    
    @validates("currency")
    def validate_currency(self, key: str, currency: str) -> str:
        """Validate currency code."""
        if len(currency) != 3:
            raise ValueError("Currency code must be 3 characters (ISO 4217)")
        return currency.upper()
    
    @hybrid_property
    def is_reversible(self) -> bool:
        """Check if transaction can be reversed."""
        return (
            self.status == TransactionStatus.SUCCESS and
            not self.is_settled and
            not self.parent_id
        )
    
    @hybrid_property
    def is_refundable(self) -> bool:
        """Check if transaction can be refunded."""
        return (
            self.status == TransactionStatus.SUCCESS and
            self.is_settled and
            not self.parent_id
        )
    
    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, "
            f"user_id={self.user_id}, "
            f"amount={self.amount} {self.currency}, "
            f"type={self.type}, "
            f"status={self.status})>"
        )

@event.listens_for(Transaction, "before_update")
def update_settlement_timestamp(mapper, connection, target):
    """Update settled_at timestamp when transaction is settled."""
    if target.is_settled and not target.settled_at:
        target.settled_at = datetime.utcnow() 
