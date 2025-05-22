"""
Portfolio Rebalancing Tasks

This module defines Celery tasks for portfolio rebalancing operations.
"""

from typing import List, Optional
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import logger
from app.db.session import async_session
from app.models.portfolio_rebalance import RebalanceLog, RebalanceStatus, RebalanceTriggerType
from app.models.user import User
from app.services.investment import InvestmentService
from app.services.notification import NotificationService
from app.modules.portfolio_rebalance.service import PortfolioRebalanceService

@celery_app.task(name="rebalance_due_users")
def rebalance_due_users() -> None:
    """Check and rebalance portfolios for all users."""
    logger.info("Starting scheduled portfolio rebalancing")
    
    async def _rebalance_due_users():
        async with async_session() as session:
            # Get all active users
            query = select(User).where(User.is_active == True)
            result = await session.execute(query)
            users = result.scalars().all()
            
            # Initialize services
            investment_service = InvestmentService(session)
            notification_service = NotificationService(session)
            rebalance_service = PortfolioRebalanceService(
                session,
                investment_service,
                notification_service
            )
            
            # Process each user
            for user in users:
                try:
                    # Compute rebalance
                    log, summary = await rebalance_service.compute_rebalance(
                        user_id=user.id,
                        trigger_type=RebalanceTriggerType.SCHEDULED,
                        drift_threshold=settings.REBALANCE_DRIFT_THRESHOLD
                    )
                    
                    # If rebalance needed, execute it
                    if summary:
                        await rebalance_service.execute_rebalance(log.id)
                        logger.info(
                            f"Rebalanced portfolio for user {user.id}: "
                            f"amount={summary.rebalance_amount}, "
                            f"trades={summary.trade_count}"
                        )
                    else:
                        logger.info(f"No rebalance needed for user {user.id}")
                        
                except Exception as e:
                    logger.exception(
                        f"Error rebalancing portfolio for user {user.id}: {str(e)}"
                    )
    
    # Run async function
    import asyncio
    asyncio.run(_rebalance_due_users())

@celery_app.task(name="rebalance_user_portfolio")
def rebalance_user_portfolio(
    user_id: UUID,
    trigger_type: str,
    drift_threshold: Optional[float] = None,
    force: bool = False
) -> None:
    """Rebalance portfolio for a specific user."""
    logger.info(
        f"Starting portfolio rebalance for user {user_id} "
        f"(trigger={trigger_type}, force={force})"
    )
    
    async def _rebalance_user_portfolio():
        async with async_session() as session:
            # Initialize services
            investment_service = InvestmentService(session)
            notification_service = NotificationService(session)
            rebalance_service = PortfolioRebalanceService(
                session,
                investment_service,
                notification_service
            )
            
            try:
                # Compute rebalance
                log, summary = await rebalance_service.compute_rebalance(
                    user_id=user_id,
                    trigger_type=RebalanceTriggerType(trigger_type),
                    drift_threshold=drift_threshold,
                    force=force
                )
                
                # If rebalance needed, execute it
                if summary:
                    await rebalance_service.execute_rebalance(log.id)
                    logger.info(
                        f"Rebalanced portfolio for user {user_id}: "
                        f"amount={summary.rebalance_amount}, "
                        f"trades={summary.trade_count}"
                    )
                else:
                    logger.info(f"No rebalance needed for user {user_id}")
                    
            except Exception as e:
                logger.exception(
                    f"Error rebalancing portfolio for user {user_id}: {str(e)}"
                )
    
    # Run async function
    import asyncio
    asyncio.run(_rebalance_user_portfolio())

@celery_app.task(name="cleanup_rebalance_logs")
def cleanup_rebalance_logs(days: int = 30) -> None:
    """Clean up old rebalance logs."""
    logger.info(f"Cleaning up rebalance logs older than {days} days")
    
    async def _cleanup_rebalance_logs():
        async with async_session() as session:
            # Delete old logs
            query = select(RebalanceLog).where(
                RebalanceLog.created_at < (
                    datetime.utcnow() - timedelta(days=days)
                )
            )
            result = await session.execute(query)
            old_logs = result.scalars().all()
            
            for log in old_logs:
                await session.delete(log)
            
            await session.commit()
            logger.info(f"Deleted {len(old_logs)} old rebalance logs")
    
    # Run async function
    import asyncio
    asyncio.run(_cleanup_rebalance_logs()) 
