"""
API Router

This module configures the FastAPI router with all endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    kyc,
    transactions,
    audit_logs
)

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(kyc.router, prefix="/kyc", tags=["kyc"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit"]) 
