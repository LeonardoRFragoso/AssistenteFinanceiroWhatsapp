from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, case
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta
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

    async def get_pending_by_user(self, user_id: int) -> List[Charge]:
        result = await self.db.execute(
            select(Charge)
            .where(and_(Charge.user_id == user_id, Charge.status == ChargeStatus.PENDING))
            .order_by(desc(Charge.created_at))
        )
        return list(result.scalars().all())

    async def get_paid_by_user(self, user_id: int, limit: int = 10) -> List[Charge]:
        result = await self.db.execute(
            select(Charge)
            .where(and_(Charge.user_id == user_id, Charge.status == ChargeStatus.PAID))
            .order_by(desc(Charge.paid_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_overdue_by_user(self, user_id: int) -> List[Charge]:
        today = date.today()
        result = await self.db.execute(
            select(Charge)
            .where(
                and_(
                    Charge.user_id == user_id,
                    Charge.status == ChargeStatus.PENDING,
                    Charge.due_date.isnot(None),
                    Charge.due_date < today
                )
            )
            .order_by(Charge.due_date)
        )
        return list(result.scalars().all())

    async def get_due_soon_by_user(self, user_id: int, days_ahead: int = 1) -> List[Charge]:
        today = date.today()
        threshold = today + timedelta(days=days_ahead)
        result = await self.db.execute(
            select(Charge)
            .where(
                and_(
                    Charge.user_id == user_id,
                    Charge.status == ChargeStatus.PENDING,
                    Charge.due_date.isnot(None),
                    Charge.due_date <= threshold,
                    Charge.due_date >= today
                )
            )
            .order_by(Charge.due_date)
        )
        return list(result.scalars().all())

    async def get_all_due_soon(self, days_ahead: int = 1) -> List[Charge]:
        today = date.today()
        threshold = today + timedelta(days=days_ahead)
        result = await self.db.execute(
            select(Charge)
            .where(
                and_(
                    Charge.status == ChargeStatus.PENDING,
                    Charge.due_date.isnot(None),
                    Charge.due_date <= threshold,
                    Charge.due_date >= today
                )
            )
            .order_by(Charge.due_date)
        )
        return list(result.scalars().all())

    async def get_all_overdue(self) -> List[Charge]:
        today = date.today()
        result = await self.db.execute(
            select(Charge)
            .where(
                and_(
                    Charge.status == ChargeStatus.PENDING,
                    Charge.due_date.isnot(None),
                    Charge.due_date < today
                )
            )
            .order_by(Charge.due_date)
        )
        return list(result.scalars().all())

    async def get_summary(self, user_id: int) -> dict:
        today = date.today()

        # Conditions:
        #   pending_not_overdue: status=PENDING AND (due_date IS NULL OR due_date >= today)
        #   overdue:             status=PENDING AND due_date IS NOT NULL AND due_date < today
        #   paid:                status=PAID
        #   cancelled:           status=CANCELLED
        pending_not_overdue = and_(
            Charge.status == ChargeStatus.PENDING,
            or_(Charge.due_date.is_(None), Charge.due_date >= today)
        )
        overdue = and_(
            Charge.status == ChargeStatus.PENDING,
            Charge.due_date.isnot(None),
            Charge.due_date < today
        )

        query = select(
            func.coalesce(
                func.sum(
                    case(
                        (pending_not_overdue, Charge.amount),
                        else_=0
                    )
                ), 0
            ).label("total_pending"),
            func.coalesce(
                func.sum(
                    case(
                        (Charge.status == ChargeStatus.PAID, Charge.amount),
                        else_=0
                    )
                ), 0
            ).label("total_paid"),
            func.coalesce(
                func.sum(
                    case(
                        (overdue, Charge.amount),
                        else_=0
                    )
                ), 0
            ).label("total_overdue"),
            func.count(
                case(
                    (pending_not_overdue, 1),
                    else_=None
                )
            ).label("count_pending"),
            func.count(
                case(
                    (Charge.status == ChargeStatus.PAID, 1),
                    else_=None
                )
            ).label("count_paid"),
            func.count(
                case(
                    (overdue, 1),
                    else_=None
                )
            ).label("count_overdue"),
            func.count(
                case(
                    (Charge.status == ChargeStatus.CANCELLED, 1),
                    else_=None
                )
            ).label("count_cancelled"),
        ).where(Charge.user_id == user_id)

        result = await self.db.execute(query)
        row = result.one()
        total_pending = Decimal(str(row.total_pending))
        total_overdue = Decimal(str(row.total_overdue))
        return {
            "total_pending": total_pending,
            "total_paid": Decimal(str(row.total_paid)),
            "total_overdue": total_overdue,
            "total_receivable": total_pending + total_overdue,
            "count_pending": row.count_pending or 0,
            "count_paid": row.count_paid or 0,
            "count_overdue": row.count_overdue or 0,
            "count_cancelled": row.count_cancelled or 0,
        }

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

    async def find_by_customer_name(self, user_id: int, customer_name: str) -> List[Charge]:
        result = await self.db.execute(
            select(Charge)
            .where(
                and_(
                    Charge.user_id == user_id,
                    Charge.customer_name.ilike(f"%{customer_name}%")
                )
            )
            .order_by(desc(Charge.created_at))
        )
        return list(result.scalars().all())

    async def find_by_amount(self, user_id: int, amount: Decimal) -> List[Charge]:
        result = await self.db.execute(
            select(Charge)
            .where(
                and_(
                    Charge.user_id == user_id,
                    Charge.amount == amount
                )
            )
            .order_by(desc(Charge.created_at))
        )
        return list(result.scalars().all())
