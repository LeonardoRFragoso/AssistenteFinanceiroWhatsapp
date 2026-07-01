from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone
from app.models.charge_delivery_log import ChargeDeliveryLog, DeliveryStatus, DeliveryChannel


class ChargeDeliveryLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        charge_id: int,
        user_id: int,
        customer_phone: Optional[str],
        channel: DeliveryChannel,
        status: DeliveryStatus,
        error_message: Optional[str] = None
    ) -> ChargeDeliveryLog:
        log = ChargeDeliveryLog(
            charge_id=charge_id,
            user_id=user_id,
            customer_phone=customer_phone,
            channel=channel,
            status=status,
            error_message=error_message,
            sent_at=datetime.now(timezone.utc) if status == DeliveryStatus.SENT else None
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_by_charge_id(self, charge_id: int) -> List[ChargeDeliveryLog]:
        result = await self.db.execute(
            select(ChargeDeliveryLog)
            .where(ChargeDeliveryLog.charge_id == charge_id)
            .order_by(ChargeDeliveryLog.created_at.desc())
        )
        return list(result.scalars().all())
