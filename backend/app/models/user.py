"""
User model with payment and transaction management capabilities.

This module defines the User model with relationships to transactions
and payment intents, along with helper methods for financial operations.
"""
from app.models.types import GUID
from app.models.types import GUID

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import enum

from sqlalchemy import Column, String, Boolean, DateTime, Enum, func
from app.models.types import GUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base
from app.models.audit_mixin import AuditMixin

class UserRole(enum.Enum):  # or whatever your base class is
    ADMIN = "admin"
    USER = "user"
    # ...other roles...

class User(Base, AuditMixin):
    """
    User model with payment and transaction capabilities.
    
    Attributes:
        id (UUID): Primary key
        email (str): User's email address
        full_name (str): User's full name
        phone (str): User's phone number
        is_active (bool): Account status
        is_verified (bool): Email verification status
        kyc_verified (bool): KYC verification status
        kyc_data (dict): KYC verification details
        last_login (datetime): Last login timestamp
        preferences (dict): User preferences
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    
    # Status flags
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    kyc_verified = Column(Boolean, default=False, nullable=False)
    
    # Additional data
    kyc_data = Column(JSONB, nullable=True)
    last_login = Column(DateTime, nullable=True)
    preferences = Column(JSONB, nullable=True)
    
    # Relationships with cascade delete
    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete",
        lazy="dynamic"
    )
    
    payment_intents = relationship(
        "PaymentIntent",
        back_populates="user",
        cascade="all, delete",
        lazy="dynamic"
    )
    
    @hybrid_property
    def total_balance(self) -> Decimal:
        """Calculate user's current balance from transactions."""
        from app.models.transaction import TransactionType, TransactionStatus
        
        credits = sum(
            t.amount for t in self.transactions
            if t.type == TransactionType.CREDIT
            and t.status == TransactionStatus.SUCCESS
        ) or Decimal('0')
        
        debits = sum(
            t.amount for t in self.transactions
            if t.type == TransactionType.DEBIT
            and t.status == TransactionStatus.SUCCESS
        ) or Decimal('0')
        
        return credits - debits
    
    @hybrid_property
    def pending_balance(self) -> Decimal:
        """Calculate pending balance from unprocessed transactions."""
        from app.models.transaction import TransactionType, TransactionStatus
        
        pending_credits = sum(
            t.amount for t in self.transactions
            if t.type == TransactionType.CREDIT
            and t.status == TransactionStatus.PENDING
        ) or Decimal('0')
        
        pending_debits = sum(
            t.amount for t in self.transactions
            if t.type == TransactionType.DEBIT
            and t.status == TransactionStatus.PENDING
        ) or Decimal('0')
        
        return pending_credits - pending_debits
    
    def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List["Transaction"]:
        """
        Get user's transactions with filters.
        
        Args:
            start_date: Filter transactions from this date
            end_date: Filter transactions until this date
            transaction_type: Filter by transaction type
            status: Filter by transaction status
            limit: Maximum number of transactions to return
            
        Returns:
            List of filtered transactions
        """
        query = self.transactions
        
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        if end_date:
            query = query.filter(Transaction.created_at <= end_date)
        if transaction_type:
            query = query.filter(Transaction.type == transaction_type)
        if status:
            query = query.filter(Transaction.status == status)
            
        return query.order_by(Transaction.created_at.desc()).limit(limit).all()
    
    def get_payment_intents(
        self,
        status: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 100
    ) -> List["PaymentIntent"]:
        """
        Get user's payment intents with filters.
        
        Args:
            status: Filter by payment status
            provider: Filter by payment provider
            limit: Maximum number of payment intents to return
            
        Returns:
            List of filtered payment intents
        """
        query = self.payment_intents
        
        if status:
            query = query.filter(PaymentIntent.status == status)
        if provider:
            query = query.filter(PaymentIntent.provider == provider)
            
        return query.order_by(PaymentIntent.created_at.desc()).limit(limit).all()
    
    @hybrid_property
    def has_pending_payments(self) -> bool:
        """Check if user has any pending payments."""
        from app.models.payment import PaymentIntentStatus
        
        return self.payment_intents.filter(
            PaymentIntent.status.in_([
                PaymentIntentStatus.INITIATED,
                PaymentIntentStatus.REQUIRES_PAYMENT_METHOD,
                PaymentIntentStatus.REQUIRES_CONFIRMATION,
                PaymentIntentStatus.REQUIRES_ACTION,
                PaymentIntentStatus.PROCESSING
            ])
        ).count() > 0
    
    @hybrid_property
    def can_initiate_payment(self) -> bool:
        """Check if user can initiate new payments."""
        return (
            self.is_active and
            self.is_verified and
            self.kyc_verified and
            not self.has_pending_payments
        )
    
    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, "
            f"email={self.email}, "
            f"full_name={self.full_name}, "
            f"balance={self.total_balance})>"
        )
