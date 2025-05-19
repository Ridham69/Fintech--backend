"""
Portfolio Rebalancing Router

This module defines API endpoints for portfolio rebalancing operations.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.logging import logger
from app.models.portfolio_rebalance import RebalanceLog, RebalanceStatus
from app.modules.portfolio_rebalance.service import PortfolioRebalanceService
from app.modules.portfolio_rebalance.triggers import PortfolioRebalanceTriggers
from app.schemas.portfolio_rebalance import (
    RebalanceLogResponse,
    RebalanceStatusResponse,
    RebalanceTrigger
)

router = APIRouter()

@router.post(
    "/me/rebalance",
    response_model=RebalanceStatusResponse,
    summary="Trigger portfolio rebalance"
)
async def trigger_rebalance(
    trigger: RebalanceTrigger,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db)
) -> RebalanceStatusResponse:
    """Trigger portfolio rebalance for current user."""
    try:
        # Initialize service
        investment_service = deps.get_investment_service(db)
        notification_service = deps.get_notification_service(db)
        rebalance_service = PortfolioRebalanceService(
            db,
            investment_service,
            notification_service
        )
        
        # Compute rebalance
        log, summary = await rebalance_service.compute_rebalance(
            user_id=current_user.id,
            trigger_type=trigger.trigger_type,
            drift_threshold=trigger.drift_threshold,
            force=trigger.force
        )
        
        if not summary:
            return RebalanceStatusResponse(
                status=RebalanceStatus.COMPLETED,
                message="No rebalance needed",
                log_id=log.id
            )
        
        # Execute rebalance
        log = await rebalance_service.execute_rebalance(log.id)
        
        return RebalanceStatusResponse(
            status=log.status,
            message="Rebalance completed successfully",
            log_id=log.id,
            summary=summary
        )
        
    except Exception as e:
        logger.exception(f"Error triggering rebalance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get(
    "/me/rebalance/logs",
    response_model=List[RebalanceLogResponse],
    summary="Get rebalance logs"
)
async def get_rebalance_logs(
    status: Optional[RebalanceStatus] = None,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db)
) -> List[RebalanceLogResponse]:
    """Get rebalance logs for current user."""
    try:
        # Initialize service
        investment_service = deps.get_investment_service(db)
        notification_service = deps.get_notification_service(db)
        rebalance_service = PortfolioRebalanceService(
            db,
            investment_service,
            notification_service
        )
        
        # Get logs
        logs = await rebalance_service.list_rebalance_logs(
            user_id=current_user.id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return logs
        
    except Exception as e:
        logger.exception(f"Error getting rebalance logs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get(
    "/me/rebalance/logs/{log_id}",
    response_model=RebalanceLogResponse,
    summary="Get rebalance log"
)
async def get_rebalance_log(
    log_id: UUID,
    current_user = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db)
) -> RebalanceLogResponse:
    """Get rebalance log by ID."""
    try:
        # Initialize service
        investment_service = deps.get_investment_service(db)
        notification_service = deps.get_notification_service(db)
        rebalance_service = PortfolioRebalanceService(
            db,
            investment_service,
            notification_service
        )
        
        # Get log
        log = await rebalance_service.get_rebalance_log(log_id)
        
        # Check ownership
        if log.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this log"
            )
        
        return log
        
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error getting rebalance log: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# Admin endpoints
@router.post(
    "/admin/users/{user_id}/rebalance",
    response_model=RebalanceStatusResponse,
    summary="Trigger portfolio rebalance for user (admin)"
)
async def admin_trigger_rebalance(
    user_id: UUID,
    trigger: RebalanceTrigger,
    current_user = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(deps.get_db)
) -> RebalanceStatusResponse:
    """Trigger portfolio rebalance for user (admin only)."""
    try:
        # Initialize service
        investment_service = deps.get_investment_service(db)
        notification_service = deps.get_notification_service(db)
        rebalance_service = PortfolioRebalanceService(
            db,
            investment_service,
            notification_service
        )
        
        # Compute rebalance
        log, summary = await rebalance_service.compute_rebalance(
            user_id=user_id,
            trigger_type=trigger.trigger_type,
            drift_threshold=trigger.drift_threshold,
            force=trigger.force
        )
        
        if not summary:
            return RebalanceStatusResponse(
                status=RebalanceStatus.COMPLETED,
                message="No rebalance needed",
                log_id=log.id
            )
        
        # Execute rebalance
        log = await rebalance_service.execute_rebalance(log.id)
        
        return RebalanceStatusResponse(
            status=log.status,
            message="Rebalance completed successfully",
            log_id=log.id,
            summary=summary
        )
        
    except Exception as e:
        logger.exception(f"Error triggering rebalance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get(
    "/admin/rebalance/logs",
    response_model=List[RebalanceLogResponse],
    summary="Get all rebalance logs (admin)"
)
async def admin_get_rebalance_logs(
    user_id: Optional[UUID] = None,
    status: Optional[RebalanceStatus] = None,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(deps.get_db)
) -> List[RebalanceLogResponse]:
    """Get all rebalance logs (admin only)."""
    try:
        # Initialize service
        investment_service = deps.get_investment_service(db)
        notification_service = deps.get_notification_service(db)
        rebalance_service = PortfolioRebalanceService(
            db,
            investment_service,
            notification_service
        )
        
        # Get logs
        logs = await rebalance_service.list_rebalance_logs(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return logs
        
    except Exception as e:
        logger.exception(f"Error getting rebalance logs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 