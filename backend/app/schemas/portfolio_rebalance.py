"""
Portfolio Rebalancing Schemas

This module defines Pydantic models for portfolio rebalancing validation and responses.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.portfolio_rebalance import RebalanceStatus, RebalanceTriggerType

class AssetAllocation(BaseModel):
    """Schema for asset allocation."""
    
    asset_id: str
    current_allocation: float
    target_allocation: float
    drift: float
    value: float
    units: float

class RebalanceTrade(BaseModel):
    """Schema for rebalance trade."""
    
    asset_id: str
    action: str  # "buy" or "sell"
    units: float
    value: float
    current_allocation: float
    target_allocation: float

class RebalanceSummary(BaseModel):
    """Schema for rebalance summary."""
    
    total_value: float
    max_drift: float
    drift_threshold: float
    rebalance_amount: float
    trade_count: int
    allocations: Dict[str, AssetAllocation]
    trades: List[RebalanceTrade]

class RebalanceLogBase(BaseModel):
    """Base schema for rebalance log."""
    
    user_id: UUID
    trigger_type: RebalanceTriggerType
    status: RebalanceStatus
    before_allocations: Dict[str, float]
    after_allocations: Optional[Dict[str, float]] = None
    suggested_trades: Optional[Dict[str, RebalanceTrade]] = None
    executed_trades: Optional[Dict[str, RebalanceTrade]] = None
    drift_threshold: float = Field(default=0.05, ge=0, le=1)
    max_drift: float = Field(default=0.0, ge=0)
    total_value: float = Field(default=0.0, ge=0)
    rebalance_amount: float = Field(default=0.0, ge=0)
    error: Optional[str] = None

class RebalanceLogCreate(RebalanceLogBase):
    """Schema for creating a rebalance log."""
    
    pass

class RebalanceLogResponse(RebalanceLogBase):
    """Schema for rebalance log response."""
    
    id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RebalanceTrigger(BaseModel):
    """Schema for triggering rebalance."""
    
    trigger_type: RebalanceTriggerType
    drift_threshold: Optional[float] = Field(default=None, ge=0, le=1)
    force: bool = Field(default=False)

class RebalanceStatusResponse(BaseModel):
    """Schema for rebalance status response."""
    
    status: RebalanceStatus
    message: str
    log_id: Optional[UUID] = None
    summary: Optional[RebalanceSummary] = None 