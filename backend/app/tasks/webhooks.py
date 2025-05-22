"""
Webhook Tasks

This module provides Celery tasks for webhook processing.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.session import async_session
from app.modules.webhooks.service import WebhookService
from app.services.notification import NotificationService

@shared_task(
    name="process_webhook",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
async def process_webhook_task(
    self,
    webhook_id: str,
    *args: Any,
    **kwargs: Any
) -> Optional[Dict[str, Any]]:
    """Process webhook asynchronously."""
    try:
        async with async_session() as session:
            service = WebhookService(
                db=session,
                notification_service=NotificationService()
            )
            await service.process_webhook_internal(UUID(webhook_id))
    except Exception as e:
        logger.exception(f"Error processing webhook {webhook_id}: {str(e)}")
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for webhook {webhook_id}")
            return {
                "status": "error",
                "error": str(e),
                "webhook_id": webhook_id
            }
    
    return {
        "status": "success",
        "webhook_id": webhook_id
    } 
