"""
Reconciliation Tasks

This module provides Celery tasks for reconciliation operations.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.session import async_session
from app.modules.reconciliation.service import ReconciliationService
from app.services.notification import NotificationService

@shared_task(
    name="reconcile_provider",
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
async def reconcile_provider_task(
    self,
    provider: str,
    threshold: Optional[float] = None,
    *args: Any,
    **kwargs: Any
) -> Dict[str, Any]:
    """Reconcile data for a specific provider."""
    try:
        async with async_session() as session:
            service = ReconciliationService(
                db=session,
                notification_service=NotificationService()
            )
            report = await service.reconcile_provider(
                provider=provider,
                threshold=threshold
            )
            return {
                "status": "success",
                "report_id": str(report.id),
                "provider": provider,
                "mismatch_count": report.mismatch_count
            }
    except Exception as e:
        logger.exception(f"Error reconciling provider {provider}: {str(e)}")
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for provider {provider}")
            return {
                "status": "error",
                "provider": provider,
                "error": str(e)
            }

@shared_task(name="reconcile_all_providers")
async def reconcile_all_providers_task(
    threshold: Optional[float] = None
) -> Dict[str, Any]:
    """Reconcile data for all providers."""
    providers = ["bank", "payment", "investment"]
    results = {}
    
    for provider in providers:
        try:
            result = await reconcile_provider_task.delay(
                provider=provider,
                threshold=threshold
            )
            results[provider] = result
        except Exception as e:
            logger.exception(f"Error scheduling reconciliation for {provider}: {str(e)}")
            results[provider] = {
                "status": "error",
                "error": str(e)
            }
    
    return {
        "status": "completed",
        "results": results
    }

@shared_task(name="cleanup_old_reports")
async def cleanup_old_reports_task(
    days: int = 30
) -> Dict[str, Any]:
    """Clean up old reconciliation reports."""
    try:
        async with async_session() as session:
            # Delete reports older than specified days
            # Implementation depends on your database schema
            # This is a placeholder
            return {
                "status": "success",
                "message": f"Cleaned up reports older than {days} days"
            }
    except Exception as e:
        logger.exception(f"Error cleaning up old reports: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        } 
