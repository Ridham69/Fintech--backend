"""
Investment models.

This module defines the database models for investment funds,
user investments, and investment transactions.
"""
from app.models.types import GUID
from app.models.types import GUID

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint
)
from app.models.types import GUID as PGUUID
from sqlalchemy.orm import Mapped, relationship

from app.core.database import Base
from app.models.user import User
from app.models.transaction import Transaction

class InvestmentFund(Base):
    """Model for investment funds (e.g., mutual funds, ETFs)."""
    
    __tablename__ = "investment_funds"
    
    id: Mapped[UUID] = Column(
        GUID(),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = Column(String(255), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    external_id: Mapped[str] = Column(String(100), nullable=False, unique=True)
    current_nav: Mapped[Decimal] = Column(Float(precision=10, scale=4), nullable=False)
    last_updated: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    investments = relationship("UserInvestment", back_populates="fund")
    transactions = relationship("InvestmentTransaction", back_populates="fund")
    
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_investment_fund_external_id"),
    )

class UserInvestment(Base):
    """Model for user's investments in funds."""
    
    __tablename__ = "user_investments"
    
    id: Mapped[UUID] = Column(
        GUID(),
        primary_key=True,
        default=uuid4
    )
    user_id: Mapped[UUID] = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    investment_fund_id: Mapped[UUID] = Column(
        GUID(),
        ForeignKey("investment_funds.id", ondelete="CASCADE"),
        nullable=False
    )
    amount_invested: Mapped[Decimal] = Column(
        Float(precision=10, scale=2),
        nullable=False,
        default=0
    )
    units_held: Mapped[Decimal] = Column(
        Float(precision=10, scale=4),
        nullable=False,
        default=0
    )
    last_transaction_id: Mapped[Optional[UUID]] = Column(
        GUID(),
        ForeignKey("transactions.id")
    )
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user = relationship("User", back_populates="investments")
    fund = relationship("InvestmentFund", back_populates="investments")
    last_transaction = relationship("Transaction")
    
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "investment_fund_id",
            name="uq_user_investment_fund"
        ),
    )

class InvestmentTransaction(Base):
    """Model for investment transactions (buy/sell/rebalance)."""
    
    __tablename__ = "investment_transactions"
    
    id: Mapped[UUID] = Column(
        GUID(),
        primary_key=True,
        default=uuid4
    )
    user_id: Mapped[UUID] = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    investment_fund_id: Mapped[UUID] = Column(
        GUID(),
        ForeignKey("investment_funds.id", ondelete="CASCADE"),
        nullable=False
    )
    transaction_type: Mapped[str] = Column(
        Enum("BUY", "SELL", "REBALANCE", name="investment_transaction_type"),
        nullable=False
    )
    units: Mapped[Decimal] = Column(
        Float(precision=10, scale=4),
        nullable=False
    )
    amount: Mapped[Decimal] = Column(
        Float(precision=10, scale=2),
        nullable=False
    )
    nav_at_time: Mapped[Decimal] = Column(
        Float(precision=10, scale=4),
        nullable=False
    )
    related_txn_id: Mapped[Optional[UUID]] = Column(
        GUID(),
        ForeignKey("transactions.id")
    )
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relationships
    user = relationship("User")
    fund = relationship("InvestmentFund", back_populates="transactions")
    related_transaction = relationship("Transaction") 
