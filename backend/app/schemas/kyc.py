"""
KYC Schema Module

This module defines Pydantic models for KYC-related data.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

class KYCStatus(str, Enum):
    """KYC verification status."""
    
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class KYCDocument(BaseModel):
    """KYC document data."""
    
    type: str = Field(..., description="Document type (e.g., PAN, Aadhaar)")
    number: str = Field(..., description="Document number")
    file_url: str = Field(..., description="URL to uploaded document")
    verified: bool = Field(default=False, description="Whether document is verified")
    verification_date: Optional[datetime] = Field(None, description="Document verification date")

class KYCSubmission(BaseModel):
    """KYC document submission data."""
    
    documents: Dict[str, KYCDocument] = Field(..., description="Submitted KYC documents")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional KYC information")

class KYCStatusUpdate(BaseModel):
    """KYC status update data."""
    
    status: KYCStatus = Field(..., description="New KYC status")
    reason: Optional[str] = Field(None, description="Reason for status update")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional status information")

class KYCResponse(BaseModel):
    """KYC status response data."""
    
    user_id: UUID = Field(..., description="User ID")
    status: KYCStatus = Field(..., description="Current KYC status")
    submitted_at: Optional[datetime] = Field(None, description="KYC submission date")
    updated_at: Optional[datetime] = Field(None, description="Last status update date")
    documents: Optional[Dict[str, KYCDocument]] = Field(None, description="KYC documents")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional KYC information") 