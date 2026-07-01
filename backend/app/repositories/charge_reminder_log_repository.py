from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import date
from typing import List, Optional
from app.models.charge_reminder_log import ChargeReminderLog, ReminderType


class ChargeReminderLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        charge_id: int,
        user_id: int,
        reminder_type: ReminderType
    ) -> ChargeReminderLog:
        log = ChargeReminderLog(
            charge_id=charge_id,
            user_id=user_id,
            reminder_type=reminder_type
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def was_reminded_today(
        self,
        charge_id: int,
        reminder_type: ReminderType
    ) -> bool:
        today = date.today()
        result = await self.db.execute(
            select(ChargeReminderLog)
            .where(
                and_(
                    ChargeReminderLog.charge_id == charge_id,
                    ChargeReminderLog.reminder_type == reminder_type,
                    ChargeReminderLog.sent_at >= today
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_by_charge_id(self, charge_id: int) -> List[ChargeReminderLog]:
        result = await self.db.execute(
            select(ChargeReminderLog)
            .where(ChargeReminderLog.charge_id == charge_id)
            .order_by(ChargeReminderLog.sent_at.desc())
        )
        return list(result.scalars().all())
