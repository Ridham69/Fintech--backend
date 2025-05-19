"""
Reconciliation Router

This module provides FastAPI routes for reconciliation operations.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_notification_service
from app.models.reconciliation import ReconciliationStatus
from app.modules.reconciliation.service import ReconciliationService
from app.schemas.reconciliation import (
    ReconciliationReportResponse,
    ReconciliationSummary,
    ReconciliationTrigger
)
from app.services.notification import NotificationService
from app.tasks.reconciliation import reconcile_provider_task

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])

@router.post("/trigger", response_model=ReconciliationSummary)
async def trigger_reconciliation(
    trigger: ReconciliationTrigger,
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service)
) -> ReconciliationSummary:
    """Trigger reconciliation for a provider or all providers."""
    try:
        if trigger.provider:
            # Trigger single provider reconciliation
            service = ReconciliationService(db, notification_service)
            report = await service.reconcile_provider(
                provider=trigger.provider,
                threshold=trigger.threshold
            )
            return ReconciliationSummary(
                provider=report.provider,
                status=report.status,
                total_accounts=report.total_accounts,
                matched_accounts=report.matched_accounts,
                mismatch_count=report.mismatch_count,
                threshold_exceeded=report.threshold_exceeded,
                last_run=report.end_time or report.start_time,
                error=report.error
            )
        else:
            # Trigger all providers reconciliation
            task = reconcile_provider_task.delay(
                threshold=trigger.threshold
            )
            return ReconciliationSummary(
                provider="all",
                status=ReconciliationStatus.IN_PROGRESS,
                total_accounts=0,
                matched_accounts=0,
                mismatch_count=0,
                threshold_exceeded=False,
                last_run=datetime.utcnow()
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/reports/{report_id}", response_model=ReconciliationReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service)
) -> ReconciliationReportResponse:
    """Get reconciliation report by ID."""
    try:
        service = ReconciliationService(db, notification_service)
        report = await service.get_report(report_id)
        return ReconciliationReportResponse.model_validate(report)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/reports", response_model=List[ReconciliationReportResponse])
async def list_reports(
    provider: Optional[str] = None,
    status: Optional[ReconciliationStatus] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service)
) -> List[ReconciliationReportResponse]:
    """List reconciliation reports with optional filtering."""
    try:
        service = ReconciliationService(db, notification_service)
        reports = await service.list_reports(
            provider=provider,
            status=status,
            limit=limit,
            offset=offset
        )
        return [ReconciliationReportResponse.model_validate(r) for r in reports]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 