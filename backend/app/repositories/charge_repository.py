from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
from app.models.charge import Charge, ChargeStatus


class ChargeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        customer_name: str,
        amount: Decimal,
        provider: str,
        provider_charge_id: Optional[str] = None,
        payment_link: Optional[str] = None,
        qr_code: Optional[str] = None,
        qr_code_base64: Optional[str] = None,
        description: Optional[str] = None,
        customer_phone: Optional[str] = None,
        due_date: Optional[date] = None,
        status: ChargeStatus = ChargeStatus.PENDING
    ) -> Charge:
        charge = Charge(
            user_id=user_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            amount=amount,
            description=description,
            provider=provider,
            provider_charge_id=provider_charge_id,
            payment_link=payment_link,
            qr_code=qr_code,
            qr_code_base64=qr_code_base64,
            status=status,
            due_date=due_date
        )
        self.db.add(charge)
        await self.db.commit()
        await self.db.refresh(charge)
        return charge

    async def get_by_id(self, charge_id: int, user_id: Optional[int] = None) -> Optional[Charge]:
        query = select(Charge).where(Charge.id == charge_id)
        if user_id is not None:
            query = query.where(Charge.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_provider_charge_id(self, provider_charge_id: str) -> Optional[Charge]:
        result = await self.db.execute(
            select(Charge).where(Charge.provider_charge_id == provider_charge_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int, limit: int = 50, status: Optional[str] = None) -> List[Charge]:
        query = select(Charge).where(Charge.user_id == user_id)
        if status:
            query = query.where(Charge.status == status)
        query = query.order_by(desc(Charge.created_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        charge_id: int,
        status: ChargeStatus,
        paid_at: Optional[datetime] = None
    ) -> Optional[Charge]:
        charge = await self.get_by_id(charge_id)
        if not charge:
            return None
        charge.status = status
        if paid_at:
            charge.paid_at = paid_at
        await self.db.commit()
        await self.db.refresh(charge)
        return charge

    async def cancel(self, charge_id: int, user_id: int) -> Optional[Charge]:
        charge = await self.get_by_id(charge_id, user_id)
        if not charge or charge.status != ChargeStatus.PENDING:
            return None
        charge.status = ChargeStatus.CANCELLED
        await self.db.commit()
        await self.db.refresh(charge)
        return charge
