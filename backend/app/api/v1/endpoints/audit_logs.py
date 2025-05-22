"""
Audit Logs API

This module provides endpoints for querying audit logs.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.audit.logger import get_audit_logs
from app.schemas.audit_log import AuditLogResponse

router = APIRouter()

@router.get(
    "/",
    response_model=List[AuditLogResponse],
    summary="List audit logs",
    description="Retrieve a list of audit logs with optional filtering."
)
async def list_audit_logs(
    db: AsyncSession = Depends(deps.get_db),
    current_user: UUID = Depends(deps.get_current_user),
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    target_table: Optional[str] = None,
    target_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[AuditLogResponse]:
    """
    List audit logs with optional filtering.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        user_id: Filter by user ID
        action: Filter by action
        target_table: Filter by target table
        target_id: Filter by target ID
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of audit logs matching the filters
    """
    # Get audit logs
    logs = await get_audit_logs(
        db=db,
        user_id=user_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        limit=limit,
        offset=offset
    )
    
    return logs 
