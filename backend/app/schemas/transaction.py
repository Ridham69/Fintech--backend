"""
Transaction schemas for API request/response validation.

This module provides Pydantic models for transaction-related operations,
including input validation, response formatting, and type safety.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, UUID4, Field, validator, ConfigDict
from pydantic.types import constr, condecimal

class TransactionType(str, Enum):
    """Transaction type enumeration."""
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    AUTO_INVEST = "AUTO_INVEST"
    REFUND = "REFUND"
    REVERSAL = "REVERSAL"

class TransactionStatus(str, Enum):
    """Transaction status enumeration."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"

class TransactionBase(BaseModel):
    """Base transaction schema with common fields."""
    
    amount: condecimal(gt=Decimal('0'), decimal_places=2) = Field(
        ...,
        description="Transaction amount (must be positive)",
        example=100.50
    )
    currency: constr(min_length=3, max_length=3) = Field(
        default="INR",
        description="ISO 4217 currency code",
        example="INR"
    )
    type: TransactionType = Field(
        ...,
        description="Type of transaction"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Transaction description",
        example="Investment in Mutual Fund XYZ"
    )
    reference_id: Optional[str] = Field(
        None,
        max_length=100,
        description="External reference ID for idempotency"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional transaction data"
    )

    @validator('currency')
    def validate_currency(cls, v: str) -> str:
        """Validate and normalize currency code."""
        return v.upper()

class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""
    
    payment_method: Optional[str] = Field(
        None,
        description="Payment method used",
        example="UPI"
    )

class TransactionUpdate(BaseModel):
    """Schema for updating a transaction."""
    
    status: TransactionStatus = Field(
        ...,
        description="New transaction status"
    )
    error_message: Optional[str] = Field(
        None,
        max_length=500,
        description="Error message if transaction failed"
    )

class TransactionResponse(TransactionBase):
    """Schema for transaction response."""
    
    id: UUID4 = Field(..., description="Transaction ID")
    user_id: UUID4 = Field(..., description="User ID")
    status: TransactionStatus = Field(..., description="Current status")
    payment_method: Optional[str] = Field(None, description="Payment method used")
    is_settled: bool = Field(..., description="Settlement status")
    settled_at: Optional[datetime] = Field(None, description="Settlement timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)

class TransactionList(BaseModel):
    """Schema for list of transactions."""
    
    items: list[TransactionResponse]
    total: int = Field(..., description="Total number of transactions")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    
    model_config = ConfigDict(from_attributes=True)

class TransactionStats(BaseModel):
    """Schema for transaction statistics."""
    
    total_credit: condecimal(decimal_places=2) = Field(
        ...,
        description="Total credit amount"
    )
    total_debit: condecimal(decimal_places=2) = Field(
        ...,
        description="Total debit amount"
    )
    current_balance: condecimal(decimal_places=2) = Field(
        ...,
        description="Current balance"
    )
    pending_credit: condecimal(decimal_places=2) = Field(
        ...,
        description="Pending credit amount"
    )
    pending_debit: condecimal(decimal_places=2) = Field(
        ...,
        description="Pending debit amount"
    )
    transaction_count: int = Field(
        ...,
        description="Total number of transactions"
    )
    
    model_config = ConfigDict(from_attributes=True) 