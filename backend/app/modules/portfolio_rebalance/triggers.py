"""
Portfolio Rebalancing Triggers

This module defines triggers for portfolio rebalancing operations.
"""

from typing import Optional
from uuid import UUID

from app.core.logging import logger
from app.tasks.portfolio_rebalance import rebalance_user_portfolio
from app.models.portfolio_rebalance import RebalanceTriggerType

class PortfolioRebalanceTriggers:
    """Triggers for portfolio rebalancing."""
    
    @staticmethod
    def on_deposit(
        user_id: UUID,
        amount: float,
        threshold: Optional[float] = None
    ) -> None:
        """Trigger rebalance on large deposit."""
        if threshold and amount >= threshold:
            logger.info(
                f"Large deposit detected for user {user_id}: "
                f"amount={amount}, threshold={threshold}"
            )
            
            rebalance_user_portfolio.delay(
                user_id=str(user_id),
                trigger_type=RebalanceTriggerType.DEPOSIT,
                force=True
            )
    
    @staticmethod
    def on_manual_trigger(
        user_id: UUID,
        force: bool = False
    ) -> None:
        """Trigger rebalance manually."""
        logger.info(f"Manual rebalance triggered for user {user_id}")
        
        rebalance_user_portfolio.delay(
            user_id=str(user_id),
            trigger_type=RebalanceTriggerType.MANUAL,
            force=force
        )
    
    @staticmethod
    def on_threshold_breach(
        user_id: UUID,
        max_drift: float,
        threshold: float
    ) -> None:
        """Trigger rebalance on threshold breach."""
        if max_drift >= threshold:
            logger.info(
                f"Threshold breach detected for user {user_id}: "
                f"max_drift={max_drift}, threshold={threshold}"
            )
            
            rebalance_user_portfolio.delay(
                user_id=str(user_id),
                trigger_type=RebalanceTriggerType.THRESHOLD
            ) 