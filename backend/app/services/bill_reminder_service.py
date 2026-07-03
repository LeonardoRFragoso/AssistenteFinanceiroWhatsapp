"""
Bill reminder service — Sprint 17.

Manages reminders for bills. Does NOT send reminders automatically.
All data is org-scoped.
"""
import logging
from datetime import date
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bills import (
    DetectedBill, BillReminder, BillEventLog,
    BillReminderStatus, BillReminderChannel, BillEventAction,
)

logger = logging.getLogger(__name__)


class BillReminderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def schedule_reminder(
        self,
        organization_id: int,
        bill_id: int,
        reminder_date: date,
        channel: BillReminderChannel = BillReminderChannel.WHATSAPP,
    ) -> Optional[BillReminder]:
        """Schedule a reminder for a bill."""
        bill_result = await self.db.execute(
            select(DetectedBill).where(
                and_(
                    DetectedBill.organization_id == organization_id,
                    DetectedBill.id == bill_id,
                )
            )
        )
        bill = bill_result.scalar_one_or_none()
        if not bill:
            return None

        message_preview = (
            f"Lembrete: {bill.title} vence em {bill.due_date.strftime('%d/%m/%Y')}. "
            f"Valor: R$ {bill.amount:.2f}. (Dados de demonstração)"
        )

        reminder = BillReminder(
            organization_id=organization_id,
            detected_bill_id=bill_id,
            reminder_date=reminder_date,
            channel=channel,
            status=BillReminderStatus.SCHEDULED,
            message_preview=message_preview,
        )
        self.db.add(reminder)
        await self.db.flush()

        event = BillEventLog(
            organization_id=organization_id,
            detected_bill_id=bill_id,
            actor_user_id=None,
            action=BillEventAction.REMINDER_SCHEDULED,
            metadata_sanitized={"reminder_id": str(reminder.id), "date": reminder_date.isoformat()},
        )
        self.db.add(event)
        await self.db.commit()
        return reminder

    async def list_reminders(
        self,
        organization_id: int,
        bill_id: Optional[int] = None,
    ) -> list[BillReminder]:
        """List reminders for an organization, optionally filtered by bill."""
        query = select(BillReminder).where(
            BillReminder.organization_id == organization_id
        )
        if bill_id:
            query = query.where(BillReminder.detected_bill_id == bill_id)
        query = query.order_by(BillReminder.reminder_date.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def cancel_reminder(
        self,
        organization_id: int,
        reminder_id: int,
    ) -> Optional[BillReminder]:
        """Cancel a scheduled reminder."""
        result = await self.db.execute(
            select(BillReminder).where(
                and_(
                    BillReminder.organization_id == organization_id,
                    BillReminder.id == reminder_id,
                )
            )
        )
        reminder = result.scalar_one_or_none()
        if not reminder:
            return None

        reminder.status = BillReminderStatus.CANCELLED
        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder
