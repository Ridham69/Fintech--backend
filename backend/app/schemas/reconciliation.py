"""
Reconciliation Schemas

This module defines Pydantic models for reconciliation validation and responses.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.reconciliation import ReconciliationStatus

class MismatchDetail(BaseModel):
    """Schema for mismatch details."""
    
    account_id: str
    internal_balance: float
    external_balance: float
    difference: float
    last_updated: datetime
    details: Optional[Dict] = None

class ReconciliationReportBase(BaseModel):
    """Base schema for reconciliation report."""
    
    provider: str = Field(..., min_length=1, max_length=50)
    status: ReconciliationStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    mismatches: Dict[str, MismatchDetail] = Field(default_factory=dict)
    error: Optional[str] = None
    total_accounts: int = Field(default=0, ge=0)
    matched_accounts: int = Field(default=0, ge=0)
    mismatch_count: int = Field(default=0, ge=0)
    threshold_exceeded: bool = Field(default=False)

class ReconciliationReportCreate(ReconciliationReportBase):
    """Schema for creating a reconciliation report."""
    
    pass

class ReconciliationReportResponse(ReconciliationReportBase):
    """Schema for reconciliation report response."""
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReconciliationSummary(BaseModel):
    """Schema for reconciliation summary."""
    
    provider: str
    status: ReconciliationStatus
    total_accounts: int
    matched_accounts: int
    mismatch_count: int
    threshold_exceeded: bool
    last_run: datetime
    error: Optional[str] = None

class ReconciliationTrigger(BaseModel):
    """Schema for triggering reconciliation."""
    
    provider: Optional[str] = None
    force: bool = Field(default=False)
    threshold: Optional[float] = Field(default=None, ge=0) 
