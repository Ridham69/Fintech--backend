"""
Audit Logger Module

This module provides utilities for logging audit events.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.logging import get_logger
from app.models.audit_log import AuditLog

# Initialize logger
logger = get_logger(__name__)

async def log_audit_event(
    db: AsyncSession,
    action: str,
    target_table: str,
    target_id: str,
    request: Request,
    user_id: Optional[UUID] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Log an audit event asynchronously.
    
    Args:
        db: Database session
        action: Action performed (e.g., kyc.update)
        target_table: Table where action was performed
        target_id: ID of the affected record
        request: FastAPI request object
        user_id: Optional user ID of the actor
        metadata: Optional additional event metadata
        
    Returns:
        Created AuditLog instance
        
    Raises:
        Exception: If logging fails
    """
    try:
        # Get request metadata
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Create audit log entry
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            target_table=target_table,
            target_id=str(target_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        
        # Save to database
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        
        # Log success
        logger.info(
            "Audit event logged",
            extra={
                "audit_id": audit_log.id,
                "action": action,
                "target": f"{target_table}:{target_id}",
                "user_id": user_id
            }
        )
        
        return audit_log
        
    except Exception as e:
        # Log error but don't fail the operation
        logger.error(
            "Failed to log audit event",
            exc_info=True,
            extra={
                "action": action,
                "target": f"{target_table}:{target_id}",
                "user_id": user_id,
                "error": str(e)
            }
        )
        raise

async def get_audit_logs(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    target_table: Optional[str] = None,
    target_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> list[AuditLog]:
    """
    Query audit logs with filters.
    
    Args:
        db: Database session
        user_id: Filter by user ID
        action: Filter by action
        target_table: Filter by target table
        target_id: Filter by target ID
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of matching AuditLog instances
    """
    # Build query
    query = select(AuditLog)
    
    # Apply filters
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if target_table:
        query = query.where(AuditLog.target_table == target_table)
    if target_id:
        query = query.where(AuditLog.target_id == target_id)
    
    # Order by timestamp descending
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    return result.scalars().all() 