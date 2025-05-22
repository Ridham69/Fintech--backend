"""
Webhook Service

This module provides webhook processing and management functionality.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.webhooks import WebhookEvent, WebhookStatus
from app.modules.webhooks.validators import get_validator
from app.schemas.webhooks import WebhookCreate, WebhookResponse
from app.services.notification import NotificationService
from app.tasks.webhooks import process_webhook_task

class WebhookService:
    """Service for webhook processing and management."""
    
    def __init__(
        self,
        db: AsyncSession,
        notification_service: NotificationService
    ):
        """Initialize service."""
        self.db = db
        self.notification_service = notification_service
    
    async def process_webhook(
        self,
        provider: str,
        request: Request
    ) -> WebhookResponse:
        """Process incoming webhook."""
        # Get validator for provider
        try:
            validator = get_validator(provider)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        
        # Verify signature
        verification = await validator.verify(request)
        if not verification.is_valid:
            raise HTTPException(
                status_code=401,
                detail=verification.error
            )
        
        # Parse request body
        try:
            body = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON payload"
            )
        
        # Create webhook event
        webhook = WebhookEvent(
            provider=provider,
            event_type=body.get("type", "unknown"),
            payload=body,
            headers=dict(request.headers),
            signature=request.headers.get("x-webhook-signature", ""),
            signature_type=settings.webhook.PROVIDERS[provider].signature_type,
            is_verified=True
        )
        
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        
        # Enqueue processing task
        process_webhook_task.delay(str(webhook.id))
        
        return WebhookResponse.model_validate(webhook)
    
    async def retry_webhook(
        self,
        webhook_id: UUID,
        max_attempts: Optional[int] = None
    ) -> WebhookResponse:
        """Retry failed webhook processing."""
        webhook = await self.db.get(WebhookEvent, webhook_id)
        if not webhook:
            raise HTTPException(
                status_code=404,
                detail="Webhook not found"
            )
        
        if webhook.status == WebhookStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="Webhook already completed"
            )
        
        if max_attempts:
            webhook.max_attempts = max_attempts
        
        webhook.status = WebhookStatus.RETRYING
        webhook.attempts = 0
        webhook.error = None
        
        await self.db.commit()
        await self.db.refresh(webhook)
        
        # Enqueue retry task
        process_webhook_task.delay(str(webhook.id))
        
        return WebhookResponse.model_validate(webhook)
    
    async def get_webhook(self, webhook_id: UUID) -> WebhookResponse:
        """Get webhook by ID."""
        webhook = await self.db.get(WebhookEvent, webhook_id)
        if not webhook:
            raise HTTPException(
                status_code=404,
                detail="Webhook not found"
            )
        
        return WebhookResponse.model_validate(webhook)
    
    async def list_webhooks(
        self,
        provider: Optional[str] = None,
        status: Optional[WebhookStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[WebhookResponse]:
        """List webhooks with optional filtering."""
        query = self.db.query(WebhookEvent)
        
        if provider:
            query = query.filter(WebhookEvent.provider == provider)
        
        if status:
            query = query.filter(WebhookEvent.status == status)
        
        webhooks = await query.order_by(
            WebhookEvent.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [WebhookResponse.model_validate(w) for w in webhooks]
    
    async def process_webhook_internal(self, webhook_id: UUID) -> None:
        """Internal method for processing webhook (called by Celery task)."""
        webhook = await self.db.get(WebhookEvent, webhook_id)
        if not webhook:
            logger.error(f"Webhook not found: {webhook_id}")
            return
        
        try:
            # Update status
            webhook.status = WebhookStatus.PROCESSING
            webhook.attempts += 1
            await self.db.commit()
            
            # Get handler for provider
            handler = self._get_handler(webhook.provider)
            if not handler:
                raise ValueError(f"No handler found for provider: {webhook.provider}")
            
            # Process webhook
            result = await handler(webhook.payload)
            
            # Update status
            webhook.status = WebhookStatus.COMPLETED
            webhook.processed_at = datetime.utcnow()
            webhook.result = result
            
            await self.db.commit()
            
            # Send notification
            await self.notification_service.send_webhook_notification(
                webhook.provider,
                webhook.event_type,
                "success",
                result
            )
            
        except Exception as e:
            logger.exception(f"Error processing webhook {webhook_id}: {str(e)}")
            
            # Update status
            webhook.status = (
                WebhookStatus.FAILED
                if webhook.attempts >= webhook.max_attempts
                else WebhookStatus.PENDING
            )
            webhook.error = str(e)
            await self.db.commit()
            
            # Send notification
            await self.notification_service.send_webhook_notification(
                webhook.provider,
                webhook.event_type,
                "error",
                {"error": str(e)}
            )
    
    def _get_handler(self, provider: str) -> Optional[callable]:
        """Get handler function for provider."""
        return settings.webhook.PROVIDERS[provider].handler 
