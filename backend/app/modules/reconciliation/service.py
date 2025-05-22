"""
Reconciliation Service

This module provides reconciliation functionality between internal and external data.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.reconciliation import ReconciliationReport, ReconciliationStatus
from app.modules.reconciliation.external import get_provider_api
from app.schemas.reconciliation import MismatchDetail, ReconciliationReportCreate
from app.services.notification import NotificationService

class ReconciliationService:
    """Service for reconciliation operations."""
    
    def __init__(
        self,
        db: AsyncSession,
        notification_service: NotificationService
    ):
        """Initialize service."""
        self.db = db
        self.notification_service = notification_service
    
    async def reconcile_provider(
        self,
        provider: str,
        threshold: Optional[float] = None
    ) -> ReconciliationReport:
        """Reconcile data for a specific provider."""
        # Create report
        report = ReconciliationReport(
            provider=provider,
            status=ReconciliationStatus.IN_PROGRESS
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        
        try:
            # Get internal balances
            internal_balances = await self._get_internal_balances(provider)
            if not internal_balances:
                raise ValueError(f"No internal balances found for provider: {provider}")
            
            # Get external balances
            provider_api = get_provider_api(provider)
            external_balances = await provider_api.get_balances(list(internal_balances.keys()))
            last_updated = await provider_api.get_last_updated(list(internal_balances.keys()))
            
            # Compare balances
            mismatches = {}
            matched = 0
            total = len(internal_balances)
            
            for account_id, internal_balance in internal_balances.items():
                if account_id not in external_balances:
                    logger.warning(f"Account {account_id} not found in external system")
                    continue
                
                external_balance = external_balances[account_id]
                difference = abs(internal_balance - external_balance)
                
                # Check if difference exceeds threshold
                if threshold and difference > threshold:
                    mismatches[account_id] = MismatchDetail(
                        account_id=account_id,
                        internal_balance=internal_balance,
                        external_balance=external_balance,
                        difference=difference,
                        last_updated=last_updated.get(account_id, datetime.utcnow()),
                        details={
                            "threshold": threshold,
                            "percentage_diff": (difference / internal_balance) * 100
                        }
                    )
                else:
                    matched += 1
            
            # Update report
            report.status = (
                ReconciliationStatus.COMPLETED
                if not mismatches
                else ReconciliationStatus.PARTIAL
            )
            report.end_time = datetime.utcnow()
            report.mismatches = {
                k: v.model_dump()
                for k, v in mismatches.items()
            }
            report.total_accounts = total
            report.matched_accounts = matched
            report.mismatch_count = len(mismatches)
            report.threshold_exceeded = bool(mismatches)
            
            await self.db.commit()
            await self.db.refresh(report)
            
            # Send notification if threshold exceeded
            if report.threshold_exceeded:
                await self.notification_service.send_reconciliation_alert(
                    provider=provider,
                    mismatch_count=len(mismatches),
                    total_accounts=total,
                    threshold=threshold
                )
            
            return report
            
        except Exception as e:
            logger.exception(f"Error reconciling provider {provider}: {str(e)}")
            
            # Update report with error
            report.status = ReconciliationStatus.FAILED
            report.end_time = datetime.utcnow()
            report.error = str(e)
            
            await self.db.commit()
            await self.db.refresh(report)
            
            # Send error notification
            await self.notification_service.send_reconciliation_error(
                provider=provider,
                error=str(e)
            )
            
            raise
    
    async def get_report(self, report_id: UUID) -> ReconciliationReport:
        """Get reconciliation report by ID."""
        report = await self.db.get(ReconciliationReport, report_id)
        if not report:
            raise ValueError(f"Report not found: {report_id}")
        return report
    
    async def list_reports(
        self,
        provider: Optional[str] = None,
        status: Optional[ReconciliationStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ReconciliationReport]:
        """List reconciliation reports with optional filtering."""
        query = select(ReconciliationReport)
        
        if provider:
            query = query.where(ReconciliationReport.provider == provider)
        
        if status:
            query = query.where(ReconciliationReport.status == status)
        
        query = query.order_by(
            ReconciliationReport.created_at.desc()
        ).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _get_internal_balances(self, provider: str) -> Dict[str, float]:
        """Get internal balances for provider."""
        # This is a placeholder - implement actual balance fetching logic
        # based on your internal data structure
        if provider == "bank":
            return {
                "BANK001": 10000.00,
                "BANK002": 25000.50,
                "BANK003": 5000.75
            }
        elif provider == "payment":
            return {
                "PAY001": 5000.00,
                "PAY002": 15000.25,
                "PAY003": 3000.50
            }
        elif provider == "investment":
            return {
                "INV001": 25000.00,
                "INV002": 50000.75,
                "INV003": 10000.25
            }
        else:
            raise ValueError(f"Unsupported provider: {provider}") 
