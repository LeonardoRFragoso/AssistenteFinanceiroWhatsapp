"""
Bill service — Sprint 17.

Manages fake DDA sync, bill listing, filtering, and status changes.
All data is org-scoped. No real DDA access, no real payment.
"""
import logging
from datetime import datetime, timezone, date
from typing import Optional
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.bills import (
    DetectedBill, BillEventLog,
    BillStatus, BillSource, BillEventAction,
)
from app.regulated_providers.dda_fake import FakeDDAProvider
from app.services.organization_audit_service import OrganizationAuditService

logger = logging.getLogger(__name__)


class BillService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = OrganizationAuditService(db)
        self.fake_provider = FakeDDAProvider()

    def _check_flags(self):
        """Ensure we only operate in fake mode unless explicitly enabled."""
        if settings.ENABLE_DEMO_MODE:
            return
        if not settings.ENABLE_DDA and settings.ENVIRONMENT == "production":
            raise ValueError(
                "DDA requires ENABLE_DDA=true or demo mode"
            )

    async def sync_fake_bills(self, organization_id: int, user_id: int) -> dict:
        """Sync fake DDA bills for an organization. Idempotent."""
        self._check_flags()

        fake_bills = self.fake_provider.generate_demo_bills(organization_id, user_id)
        created_count = 0
        skipped_count = 0

        for bill_data in fake_bills:
            existing = await self.db.execute(
                select(DetectedBill).where(
                    and_(
                        DetectedBill.organization_id == organization_id,
                        DetectedBill.provider_name == bill_data["provider_name"],
                        DetectedBill.provider_bill_id == bill_data["provider_bill_id"],
                    )
                )
            )
            if existing.scalar_one_or_none():
                skipped_count += 1
                continue

            bill = DetectedBill(
                organization_id=bill_data["organization_id"],
                user_id=bill_data["user_id"],
                provider_name=bill_data["provider_name"],
                provider_bill_id=bill_data["provider_bill_id"],
                source=BillSource(bill_data["source"]),
                title=bill_data["title"],
                beneficiary_name=bill_data["beneficiary_name"],
                beneficiary_document_masked=bill_data.get("beneficiary_document_masked"),
                payer_name=bill_data.get("payer_name"),
                amount=Decimal(bill_data["amount"]),
                currency=bill_data["currency"],
                due_date=date.fromisoformat(bill_data["due_date"]),
                issue_date=date.fromisoformat(bill_data["issue_date"]) if bill_data.get("issue_date") else None,
                barcode=bill_data.get("barcode"),
                digitable_line=bill_data.get("digitable_line"),
                bill_type=bill_data["bill_type"],
                category=bill_data.get("category"),
                status=BillStatus(bill_data["status"]),
                risk_level=bill_data["risk_level"],
                is_demo_data=True,
                raw_data_sanitized=bill_data.get("raw_data_sanitized"),
            )
            self.db.add(bill)
            await self.db.flush()
            created_count += 1

            event = BillEventLog(
                organization_id=organization_id,
                detected_bill_id=bill.id,
                actor_user_id=user_id,
                action=BillEventAction.BILL_DETECTED,
                metadata_sanitized={"provider": "fake_dda", "amount": str(bill.amount)},
            )
            self.db.add(event)

        await self.audit.log_event(
            organization_id=organization_id,
            action="dda_sync_fake",
            actor_user_id=user_id,
            resource_type="bills",
            provider_type="dda",
            metadata={"created": created_count, "skipped": skipped_count, "is_demo": True},
        )

        await self.db.commit()
        return {"created": created_count, "skipped": skipped_count, "total": len(fake_bills)}

    async def list_bills(
        self,
        organization_id: int,
        status_filter: Optional[BillStatus] = None,
        category: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DetectedBill]:
        """List bills for an organization with optional filters."""
        query = select(DetectedBill).where(
            DetectedBill.organization_id == organization_id
        )

        if status_filter:
            query = query.where(DetectedBill.status == status_filter)
        if category:
            query = query.where(DetectedBill.category == category)
        if start_date:
            query = query.where(DetectedBill.due_date >= start_date)
        if end_date:
            query = query.where(DetectedBill.due_date <= end_date)
        if search:
            query = query.where(
                DetectedBill.title.ilike(f"%{search}%") |
                DetectedBill.beneficiary_name.ilike(f"%{search}%") |
                DetectedBill.category.ilike(f"%{search}%")
            )

        query = query.order_by(DetectedBill.due_date.asc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_bill(self, organization_id: int, bill_id: int) -> Optional[DetectedBill]:
        """Get a specific bill by ID, org-scoped."""
        result = await self.db.execute(
            select(DetectedBill).where(
                and_(
                    DetectedBill.organization_id == organization_id,
                    DetectedBill.id == bill_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def ignore_bill(self, organization_id: int, bill_id: int, user_id: int) -> Optional[DetectedBill]:
        """Mark a bill as ignored."""
        bill = await self.get_bill(organization_id, bill_id)
        if not bill:
            return None

        bill.status = BillStatus.IGNORED
        bill.ignored_at = datetime.now(timezone.utc)

        event = BillEventLog(
            organization_id=organization_id,
            detected_bill_id=bill.id,
            actor_user_id=user_id,
            action=BillEventAction.BILL_IGNORED,
            metadata_sanitized={"bill_id": str(bill.id)},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(bill)
        return bill

    async def mark_paid_manual(self, organization_id: int, bill_id: int, user_id: int) -> Optional[DetectedBill]:
        """Mark a bill as paid manually (no real payment)."""
        bill = await self.get_bill(organization_id, bill_id)
        if not bill:
            return None

        bill.status = BillStatus.PAID_MANUAL
        bill.manually_marked_paid_at = datetime.now(timezone.utc)

        event = BillEventLog(
            organization_id=organization_id,
            detected_bill_id=bill.id,
            actor_user_id=user_id,
            action=BillEventAction.BILL_MARKED_PAID_MANUAL,
            metadata_sanitized={"bill_id": str(bill.id), "note": "Manual marking, no real payment"},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(bill)
        return bill

    async def get_event_logs(self, organization_id: int, bill_id: int) -> list[BillEventLog]:
        """Get event logs for a specific bill."""
        result = await self.db.execute(
            select(BillEventLog).where(
                and_(
                    BillEventLog.organization_id == organization_id,
                    BillEventLog.detected_bill_id == bill_id,
                )
            ).order_by(BillEventLog.created_at.desc())
        )
        return list(result.scalars().all())
