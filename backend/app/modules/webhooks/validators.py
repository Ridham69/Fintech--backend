"""
Webhook Validators

This module provides signature validation for incoming webhooks.
"""

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException, Request

from app.core.config import settings
from app.schemas.webhooks import WebhookVerification

class WebhookValidator:
    """Base class for webhook signature validation."""
    
    def __init__(self, provider: str):
        """Initialize validator."""
        self.provider = provider
        self.config = settings.webhook.PROVIDERS.get(provider)
        if not self.config:
            raise ValueError(f"No configuration found for provider: {provider}")
    
    async def verify(self, request: Request) -> WebhookVerification:
        """Verify webhook signature."""
        raise NotImplementedError
    
    def _get_timestamp(self, headers: Dict[str, str]) -> Optional[datetime]:
        """Extract and validate timestamp from headers."""
        timestamp_str = headers.get("x-webhook-timestamp")
        if not timestamp_str:
            return None
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            # Check if timestamp is within allowed window
            if abs(datetime.utcnow() - timestamp) > timedelta(minutes=5):
                return None
            return timestamp
        except (ValueError, TypeError):
            return None

class HMACValidator(WebhookValidator):
    """HMAC signature validator."""
    
    async def verify(self, request: Request) -> WebhookVerification:
        """Verify HMAC signature."""
        # Get request body
        body = await request.body()
        headers = dict(request.headers)
        
        # Get signature from headers
        signature = headers.get("x-webhook-signature")
        if not signature:
            return WebhookVerification(
                is_valid=False,
                error="Missing signature header"
            )
        
        # Get timestamp
        timestamp = self._get_timestamp(headers)
        if not timestamp:
            return WebhookVerification(
                is_valid=False,
                error="Invalid or missing timestamp"
            )
        
        # Calculate HMAC
        secret = self.config.secret_key.encode()
        expected = hmac.new(
            secret,
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        is_valid = hmac.compare_digest(signature, expected)
        
        return WebhookVerification(
            is_valid=is_valid,
            error=None if is_valid else "Invalid signature",
            timestamp=timestamp
        )

class RSAValidator(WebhookValidator):
    """RSA signature validator."""
    
    def __init__(self, provider: str):
        """Initialize RSA validator."""
        super().__init__(provider)
        self.public_key = self._load_public_key()
    
    def _load_public_key(self) -> rsa.RSAPublicKey:
        """Load RSA public key."""
        try:
            key_data = self.config.public_key.encode()
            return serialization.load_pem_public_key(key_data)
        except Exception as e:
            raise ValueError(f"Failed to load public key: {str(e)}")
    
    async def verify(self, request: Request) -> WebhookVerification:
        """Verify RSA signature."""
        # Get request body
        body = await request.body()
        headers = dict(request.headers)
        
        # Get signature from headers
        signature = headers.get("x-webhook-signature")
        if not signature:
            return WebhookVerification(
                is_valid=False,
                error="Missing signature header"
            )
        
        # Get timestamp
        timestamp = self._get_timestamp(headers)
        if not timestamp:
            return WebhookVerification(
                is_valid=False,
                error="Invalid or missing timestamp"
            )
        
        try:
            # Verify signature
            signature_bytes = bytes.fromhex(signature)
            self.public_key.verify(
                signature_bytes,
                body,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return WebhookVerification(
                is_valid=True,
                timestamp=timestamp
            )
        except Exception as e:
            return WebhookVerification(
                is_valid=False,
                error=f"Invalid signature: {str(e)}",
                timestamp=timestamp
            )

def get_validator(provider: str) -> WebhookValidator:
    """Get appropriate validator for provider."""
    config = settings.webhook.PROVIDERS.get(provider)
    if not config:
        raise ValueError(f"No configuration found for provider: {provider}")
    
    if config.signature_type == "hmac":
        return HMACValidator(provider)
    elif config.signature_type == "rsa":
        return RSAValidator(provider)
    else:
        raise ValueError(f"Unsupported signature type: {config.signature_type}") 