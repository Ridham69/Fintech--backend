"""
Portfolio Rebalancing Service

This module provides portfolio rebalancing functionality.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.portfolio_rebalance import RebalanceLog, RebalanceStatus, RebalanceTriggerType
from app.schemas.portfolio_rebalance import (
    AssetAllocation,
    RebalanceSummary,
    RebalanceTrade
)
from app.services.investment import InvestmentService
from app.services.notification import NotificationService

class PortfolioRebalanceService:
    """Service for portfolio rebalancing operations."""
    
    def __init__(
        self,
        db: AsyncSession,
        investment_service: InvestmentService,
        notification_service: NotificationService
    ):
        """Initialize service."""
        self.db = db
        self.investment_service = investment_service
        self.notification_service = notification_service
    
    async def compute_rebalance(
        self,
        user_id: UUID,
        trigger_type: RebalanceTriggerType,
        drift_threshold: Optional[float] = None,
        force: bool = False
    ) -> Tuple[RebalanceLog, Optional[RebalanceSummary]]:
        """Compute rebalance for user portfolio."""
        # Create rebalance log
        log = RebalanceLog(
            user_id=user_id,
            trigger_type=trigger_type,
            status=RebalanceStatus.COMPUTING,
            drift_threshold=drift_threshold or 0.05
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        
        try:
            # Get current portfolio
            portfolio = await self.investment_service.get_portfolio(user_id)
            if not portfolio:
                raise ValueError(f"No portfolio found for user: {user_id}")
            
            # Get target allocations from risk profile
            risk_profile = await self.investment_service.get_risk_profile(user_id)
            if not risk_profile:
                raise ValueError(f"No risk profile found for user: {user_id}")
            
            # Calculate current allocations
            total_value = sum(holding.value for holding in portfolio.holdings)
            current_allocations = {
                holding.asset_id: holding.value / total_value
                for holding in portfolio.holdings
            }
            
            # Store before allocations
            log.before_allocations = current_allocations
            log.total_value = total_value
            await self.db.commit()
            
            # Calculate drift and check if rebalance needed
            allocations = {}
            max_drift = 0.0
            needs_rebalance = False
            
            for asset_id, target_allocation in risk_profile.allocations.items():
                current_allocation = current_allocations.get(asset_id, 0.0)
                drift = abs(current_allocation - target_allocation)
                max_drift = max(max_drift, drift)
                
                # Get holding details
                holding = next(
                    (h for h in portfolio.holdings if h.asset_id == asset_id),
                    None
                )
                
                allocations[asset_id] = AssetAllocation(
                    asset_id=asset_id,
                    current_allocation=current_allocation,
                    target_allocation=target_allocation,
                    drift=drift,
                    value=holding.value if holding else 0.0,
                    units=holding.units if holding else 0.0
                )
                
                if drift > (drift_threshold or 0.05):
                    needs_rebalance = True
            
            # Update log with drift info
            log.max_drift = max_drift
            
            # If no rebalance needed and not forced, return early
            if not needs_rebalance and not force:
                log.status = RebalanceStatus.COMPLETED
                log.completed_at = datetime.utcnow()
                await self.db.commit()
                return log, None
            
            # Calculate required trades
            trades = []
            rebalance_amount = 0.0
            
            for asset_id, allocation in allocations.items():
                current_value = allocation.value
                target_value = total_value * allocation.target_allocation
                value_diff = target_value - current_value
                
                if abs(value_diff) > 0.01:  # Minimum trade size
                    trade = RebalanceTrade(
                        asset_id=asset_id,
                        action="buy" if value_diff > 0 else "sell",
                        units=abs(value_diff / allocation.value) if allocation.value > 0 else 0.0,
                        value=abs(value_diff),
                        current_allocation=allocation.current_allocation,
                        target_allocation=allocation.target_allocation
                    )
                    trades.append(trade)
                    rebalance_amount += abs(value_diff)
            
            # Create summary
            summary = RebalanceSummary(
                total_value=total_value,
                max_drift=max_drift,
                drift_threshold=drift_threshold or 0.05,
                rebalance_amount=rebalance_amount,
                trade_count=len(trades),
                allocations=allocations,
                trades=trades
            )
            
            # Update log with trades
            log.suggested_trades = {
                trade.asset_id: trade.model_dump()
                for trade in trades
            }
            log.rebalance_amount = rebalance_amount
            await self.db.commit()
            
            return log, summary
            
        except Exception as e:
            logger.exception(f"Error computing rebalance for user {user_id}: {str(e)}")
            
            # Update log with error
            log.status = RebalanceStatus.FAILED
            log.error = str(e)
            log.completed_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(log)
            
            # Send error notification
            await self.notification_service.send_rebalance_error(
                user_id=user_id,
                error=str(e)
            )
            
            raise
    
    async def execute_rebalance(
        self,
        log_id: UUID
    ) -> RebalanceLog:
        """Execute rebalance trades."""
        log = await self.db.get(RebalanceLog, log_id)
        if not log:
            raise ValueError(f"Rebalance log not found: {log_id}")
        
        if log.status != RebalanceStatus.COMPUTING:
            raise ValueError(f"Invalid rebalance status: {log.status}")
        
        try:
            # Update status
            log.status = RebalanceStatus.EXECUTING
            await self.db.commit()
            
            # Execute trades
            executed_trades = {}
            for asset_id, trade_data in log.suggested_trades.items():
                trade = RebalanceTrade(**trade_data)
                
                # Execute trade through investment service
                result = await self.investment_service.execute_trade(
                    user_id=log.user_id,
                    asset_id=trade.asset_id,
                    action=trade.action,
                    units=trade.units,
                    value=trade.value
                )
                
                executed_trades[asset_id] = result
            
            # Update portfolio allocations
            portfolio = await self.investment_service.get_portfolio(log.user_id)
            total_value = sum(holding.value for holding in portfolio.holdings)
            after_allocations = {
                holding.asset_id: holding.value / total_value
                for holding in portfolio.holdings
            }
            
            # Update log
            log.status = RebalanceStatus.COMPLETED
            log.completed_at = datetime.utcnow()
            log.after_allocations = after_allocations
            log.executed_trades = executed_trades
            
            await self.db.commit()
            await self.db.refresh(log)
            
            # Send success notification
            await self.notification_service.send_rebalance_complete(
                user_id=log.user_id,
                rebalance_amount=log.rebalance_amount,
                trade_count=len(executed_trades)
            )
            
            return log
            
        except Exception as e:
            logger.exception(f"Error executing rebalance {log_id}: {str(e)}")
            
            # Update log with error
            log.status = RebalanceStatus.FAILED
            log.error = str(e)
            log.completed_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(log)
            
            # Send error notification
            await self.notification_service.send_rebalance_error(
                user_id=log.user_id,
                error=str(e)
            )
            
            raise
    
    async def get_rebalance_log(self, log_id: UUID) -> RebalanceLog:
        """Get rebalance log by ID."""
        log = await self.db.get(RebalanceLog, log_id)
        if not log:
            raise ValueError(f"Rebalance log not found: {log_id}")
        return log
    
    async def list_rebalance_logs(
        self,
        user_id: Optional[UUID] = None,
        status: Optional[RebalanceStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[RebalanceLog]:
        """List rebalance logs with optional filtering."""
        query = select(RebalanceLog)
        
        if user_id:
            query = query.where(RebalanceLog.user_id == user_id)
        
        if status:
            query = query.where(RebalanceLog.status == status)
        
        query = query.order_by(
            RebalanceLog.created_at.desc()
        ).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all() 
