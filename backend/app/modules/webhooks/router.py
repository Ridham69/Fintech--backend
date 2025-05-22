"""
Webhook Router

This module provides FastAPI routes for webhook handling.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_notification_service
from app.models.webhooks import WebhookStatus
from app.modules.webhooks.service import WebhookService
from app.schemas.webhooks import WebhookResponse, WebhookRetry
from app.services.notification import NotificationService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/{provider}", response_model=WebhookResponse)
async def receive_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service)
) -> WebhookResponse:
    """Receive and process webhook from provider."""
    service = WebhookService(db, notification_service)
    return await service.process_webhook(provider, request)

@router.post("/{webhook_id}/retry", response_model=WebhookResponse)
async def retry_webhook(
    webhook_id: UUID,
    retry_data: WebhookRetry,
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service)
) -> WebhookResponse:
    """Retry failed webhook processing."""
    service = WebhookService(db, notification_service)
    return await service.retry_webhook(
        webhook_id,
        max_attempts=retry_data.max_attempts
    )

@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service)
) -> WebhookResponse:
    """Get webhook by ID."""
    service = WebhookService(db, notification_service)
    return await service.get_webhook(webhook_id)

@router.get("/", response_model=List[WebhookResponse])
async def list_webhooks(
    provider: Optional[str] = None,
    status: Optional[WebhookStatus] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service)
) -> List[WebhookResponse]:
    """List webhooks with optional filtering."""
    service = WebhookService(db, notification_service)
    return await service.list_webhooks(
        provider=provider,
        status=status,
        limit=limit,
        offset=offset
    ) 
