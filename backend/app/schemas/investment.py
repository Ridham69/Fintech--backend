"""
Investment schemas.

This module defines Pydantic models for investment-related data validation
and serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator
)

class InvestmentFundBase(BaseModel):
    """Base schema for investment fund data."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    external_id: str = Field(..., min_length=1, max_length=100)
    current_nav: Decimal = Field(..., ge=0, decimal_places=4)
    last_updated: datetime

class InvestmentFundCreate(InvestmentFundBase):
    """Schema for creating a new investment fund."""
    
    @field_validator("current_nav")
    @classmethod
    def validate_nav(cls, v: Decimal) -> Decimal:
        """Validate NAV is positive and has correct precision."""
        if v <= 0:
            raise ValueError("NAV must be positive")
        return round(v, 4)

class InvestmentFundUpdate(BaseModel):
    """Schema for updating an investment fund."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    current_nav: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    last_updated: Optional[datetime] = None
    
    @field_validator("current_nav")
    @classmethod
    def validate_nav(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate NAV is positive and has correct precision."""
        if v is not None:
            if v <= 0:
                raise ValueError("NAV must be positive")
            return round(v, 4)
        return v

class InvestmentFundResponse(InvestmentFundBase):
    """Schema for investment fund response."""
    
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserInvestmentBase(BaseModel):
    """Base schema for user investment data."""
    
    investment_fund_id: UUID
    amount_invested: Decimal = Field(..., ge=0, decimal_places=2)
    units_held: Decimal = Field(..., ge=0, decimal_places=4)

class UserInvestmentCreate(UserInvestmentBase):
    """Schema for creating a new user investment."""
    
    @model_validator(mode="after")
    def validate_investment(self) -> "UserInvestmentCreate":
        """Validate investment amount and units."""
        if self.amount_invested <= 0:
            raise ValueError("Investment amount must be positive")
        if self.units_held <= 0:
            raise ValueError("Units held must be positive")
        return self

class UserInvestmentUpdate(BaseModel):
    """Schema for updating a user investment."""
    
    amount_invested: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    units_held: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    last_transaction_id: Optional[UUID] = None
    
    @model_validator(mode="after")
    def validate_investment(self) -> "UserInvestmentUpdate":
        """Validate investment amount and units."""
        if self.amount_invested is not None and self.amount_invested <= 0:
            raise ValueError("Investment amount must be positive")
        if self.units_held is not None and self.units_held <= 0:
            raise ValueError("Units held must be positive")
        return self

class UserInvestmentResponse(UserInvestmentBase):
    """Schema for user investment response."""
    
    id: UUID
    user_id: UUID
    last_transaction_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InvestmentTransactionBase(BaseModel):
    """Base schema for investment transaction data."""
    
    investment_fund_id: UUID
    transaction_type: str = Field(..., pattern="^(BUY|SELL|REBALANCE)$")
    units: Decimal = Field(..., decimal_places=4)
    amount: Decimal = Field(..., decimal_places=2)
    nav_at_time: Decimal = Field(..., ge=0, decimal_places=4)
    related_txn_id: Optional[UUID] = None

class InvestmentTransactionCreate(InvestmentTransactionBase):
    """Schema for creating a new investment transaction."""
    
    @model_validator(mode="after")
    def validate_transaction(self) -> "InvestmentTransactionCreate":
        """Validate transaction amounts and units."""
        if self.transaction_type == "BUY":
            if self.units <= 0:
                raise ValueError("Buy units must be positive")
            if self.amount <= 0:
                raise ValueError("Buy amount must be positive")
        elif self.transaction_type == "SELL":
            if self.units >= 0:
                raise ValueError("Sell units must be negative")
            if self.amount >= 0:
                raise ValueError("Sell amount must be negative")
        elif self.transaction_type == "REBALANCE":
            if self.units == 0:
                raise ValueError("Rebalance units cannot be zero")
            if self.amount == 0:
                raise ValueError("Rebalance amount cannot be zero")
        
        # Validate NAV calculation
        calculated_nav = abs(self.amount / self.units)
        if abs(calculated_nav - self.nav_at_time) > Decimal("0.0001"):
            raise ValueError("NAV calculation mismatch")
        
        return self

class InvestmentTransactionResponse(InvestmentTransactionBase):
    """Schema for investment transaction response."""
    
    id: UUID
    user_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InvestmentTransactionList(BaseModel):
    """Schema for paginated list of investment transactions."""
    
    items: list[InvestmentTransactionResponse]
    total: int
    page: int
    size: int 