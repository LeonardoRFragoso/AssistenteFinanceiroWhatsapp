"""
Bill summary service — Sprint 17.

Provides aggregate views of bills: totals, due dates, categories, beneficiaries.
All data is org-scoped. Read-only.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bills import DetectedBill, BillStatus

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = [
    BillStatus.DETECTED, BillStatus.PENDING, BillStatus.DUE_TODAY, BillStatus.OVERDUE,
]


class BillSummaryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self, organization_id: int) -> dict:
        """Get full bill summary for an organization."""
        today = date.today()
        overdue_total = Decimal("0.00")
        due_today_total = Decimal("0.00")
        upcoming_7_total = Decimal("0.00")
        upcoming_30_total = Decimal("0.00")
        open_total = Decimal("0.00")

        bills_result = await self.db.execute(
            select(DetectedBill).where(
                and_(
                    DetectedBill.organization_id == organization_id,
                    DetectedBill.status.in_(_ACTIVE_STATUSES),
                )
            )
        )
        bills = list(bills_result.scalars().all())

        category_totals = {}
        beneficiary_totals = {}

        for bill in bills:
            open_total += bill.amount

            if bill.status == BillStatus.OVERDUE:
                overdue_total += bill.amount
            elif bill.status == BillStatus.DUE_TODAY:
                due_today_total += bill.amount

            days_until = (bill.due_date - today).days
            if 0 < days_until <= 7:
                upcoming_7_total += bill.amount
            if 0 < days_until <= 30:
                upcoming_30_total += bill.amount

            cat = bill.category or "Outros"
            category_totals[cat] = category_totals.get(cat, Decimal("0.00")) + bill.amount

            bene = bill.beneficiary_name
            beneficiary_totals[bene] = beneficiary_totals.get(bene, Decimal("0.00")) + bill.amount

        top_categories = sorted(
            [{"category": k, "total": str(v)} for k, v in category_totals.items()],
            key=lambda x: Decimal(x["total"]), reverse=True,
        )[:5]

        top_beneficiaries = sorted(
            [{"beneficiary": k, "total": str(v)} for k, v in beneficiary_totals.items()],
            key=lambda x: Decimal(x["total"]), reverse=True,
        )[:5]

        largest_bill = None
        if bills:
            largest = max(bills, key=lambda b: b.amount)
            largest_bill = {
                "id": largest.id,
                "title": largest.title,
                "amount": str(largest.amount),
                "due_date": largest.due_date.isoformat(),
                "beneficiary": largest.beneficiary_name,
            }

        return {
            "overdue_total": str(overdue_total),
            "due_today_total": str(due_today_total),
            "upcoming_7_days_total": str(upcoming_7_total),
            "upcoming_30_days_total": str(upcoming_30_total),
            "open_total": str(open_total),
            "overdue_count": sum(1 for b in bills if b.status == BillStatus.OVERDUE),
            "due_today_count": sum(1 for b in bills if b.status == BillStatus.DUE_TODAY),
            "upcoming_7_days_count": sum(1 for b in bills if 0 < (b.due_date - today).days <= 7),
            "upcoming_30_days_count": sum(1 for b in bills if 0 < (b.due_date - today).days <= 30),
            "open_count": len(bills),
            "top_categories": top_categories,
            "top_beneficiaries": top_beneficiaries,
            "largest_bill": largest_bill,
            "is_demo_data": True,
        }

    async def get_due_today(self, organization_id: int) -> list[DetectedBill]:
        """Get bills due today."""
        result = await self.db.execute(
            select(DetectedBill).where(
                and_(
                    DetectedBill.organization_id == organization_id,
                    DetectedBill.status == BillStatus.DUE_TODAY,
                )
            ).order_by(DetectedBill.amount.desc())
        )
        return list(result.scalars().all())

    async def get_overdue(self, organization_id: int) -> list[DetectedBill]:
        """Get overdue bills."""
        result = await self.db.execute(
            select(DetectedBill).where(
                and_(
                    DetectedBill.organization_id == organization_id,
                    DetectedBill.status == BillStatus.OVERDUE,
                )
            ).order_by(DetectedBill.due_date.asc())
        )
        return list(result.scalars().all())

    async def get_upcoming(self, organization_id: int, days: int = 7) -> list[DetectedBill]:
        """Get upcoming bills within N days."""
        today = date.today()
        end_date = today + timedelta(days=days)
        result = await self.db.execute(
            select(DetectedBill).where(
                and_(
                    DetectedBill.organization_id == organization_id,
                    DetectedBill.due_date > today,
                    DetectedBill.due_date <= end_date,
                    DetectedBill.status.in_([BillStatus.PENDING, BillStatus.DETECTED]),
                )
            ).order_by(DetectedBill.due_date.asc())
        )
        return list(result.scalars().all())
