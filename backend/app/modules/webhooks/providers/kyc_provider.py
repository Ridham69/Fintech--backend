"""
KYC Provider Webhook Handler

This module provides webhook handling for KYC verification providers.
"""

from typing import Any, Dict

from app.core.logging import logger
from app.services.kyc import KYCService

async def handle_kyc_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle webhook from KYC provider."""
    try:
        # Extract event data
        event_type = payload.get("type")
        verification_id = payload.get("verification_id")
        status = payload.get("status")
        data = payload.get("data", {})
        
        if not all([event_type, verification_id, status]):
            raise ValueError("Missing required fields in webhook payload")
        
        # Initialize KYC service
        kyc_service = KYCService()
        
        # Handle different event types
        if event_type == "verification.completed":
            # Update verification status
            result = await kyc_service.update_verification_status(
                verification_id=verification_id,
                status=status,
                data=data
            )
            
            # Notify user if verification is complete
            if status == "approved":
                await kyc_service.notify_verification_complete(
                    verification_id=verification_id
                )
            
            return {
                "status": "success",
                "verification_id": verification_id,
                "result": result
            }
            
        elif event_type == "verification.failed":
            # Update verification status
            result = await kyc_service.update_verification_status(
                verification_id=verification_id,
                status=status,
                data=data
            )
            
            # Notify user of failure
            await kyc_service.notify_verification_failed(
                verification_id=verification_id,
                reason=data.get("reason", "Unknown error")
            )
            
            return {
                "status": "success",
                "verification_id": verification_id,
                "result": result
            }
            
        elif event_type == "document.uploaded":
            # Process uploaded document
            result = await kyc_service.process_document(
                verification_id=verification_id,
                document_data=data
            )
            
            return {
                "status": "success",
                "verification_id": verification_id,
                "result": result
            }
            
        else:
            logger.warning(f"Unhandled KYC webhook event type: {event_type}")
            return {
                "status": "ignored",
                "event_type": event_type,
                "message": "Unhandled event type"
            }
            
    except Exception as e:
        logger.exception(f"Error handling KYC webhook: {str(e)}")
        raise 