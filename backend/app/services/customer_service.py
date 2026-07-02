from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from app.models.customer import Customer, CustomerStatus
from app.models.charge import Charge, ChargeStatus
from app.core.logging import logger


class CustomerService:
    """Service for managing customers and their operational relationship score.

    This is NOT a credit score. It is an operational relationship score
    based on payment behavior patterns. It must never be used for credit
    decisions or regulatory purposes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_customer(
        self,
        user_id: int,
        name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Customer:
        """Find or create a customer by normalized name/phone for the user."""
        normalized_name = name.strip().lower()

        query = select(Customer).where(
            and_(
                Customer.user_id == user_id,
                or_(
                    func.lower(Customer.name) == normalized_name,
                    and_(Customer.phone.isnot(None), Customer.phone == phone) if phone else False,
                ),
            )
        )
        result = await self.db.execute(query)
        customer = result.scalar_one_or_none()

        if customer:
            if phone and not customer.phone:
                customer.phone = phone
                await self.db.commit()
                await self.db.refresh(customer)
            if email and not customer.email:
                customer.email = email
                await self.db.commit()
                await self.db.refresh(customer)
            return customer

        customer = Customer(
            user_id=user_id,
            name=name.strip(),
            phone=phone,
            email=email,
        )
        self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)
        logger.info(f"Customer {customer.id} created for user {user_id}: {customer.name}")
        return customer

    async def get_customer(self, customer_id: int, user_id: int) -> Optional[Customer]:
        result = await self.db.execute(
            select(Customer).where(
                and_(Customer.id == customer_id, Customer.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_customers(
        self,
        user_id: int,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        has_overdue: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List customers with pagination and filters."""
        query = select(Customer).where(Customer.user_id == user_id)

        if search:
            search_lower = search.lower()
            query = query.where(
                or_(
                    func.lower(Customer.name).contains(search_lower),
                    Customer.phone.contains(search),
                )
            )

        sort_column = getattr(Customer, sort_by, Customer.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self.db.execute(query)
        customers = list(result.scalars().all())

        items = []
        for c in customers:
            summary = await self.get_customer_summary(c, user_id)
            item = {
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "email": c.email,
                "notes": c.notes,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "operational_status": summary["operational_status"],
                "total_charges_count": summary["total_charges_count"],
                "total_paid_amount": summary["total_paid_amount"],
                "total_pending_amount": summary["total_pending_amount"],
                "total_overdue_amount": summary["total_overdue_amount"],
                "last_charge_at": summary["last_charge_at"],
                "last_payment_at": summary["last_payment_at"],
                "has_overdue": summary["has_overdue"],
            }

            if status_filter and item["operational_status"] != status_filter:
                continue
            if has_overdue is True and not item["has_overdue"]:
                continue
            if has_overdue is False and item["has_overdue"]:
                continue

            items.append(item)

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_customer_charges(self, customer_id: int, user_id: int) -> List[Charge]:
        """Get all charges for a customer, matched by name/phone."""
        customer = await self.get_customer(customer_id, user_id)
        if not customer:
            return []

        query = select(Charge).where(
            and_(
                Charge.user_id == user_id,
                or_(
                    func.lower(Charge.customer_name) == customer.name.lower(),
                    and_(Charge.customer_phone.isnot(None), Charge.customer_phone == customer.phone) if customer.phone else False,
                ),
            )
        ).order_by(Charge.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_customer_summary(self, customer: Customer, user_id: int) -> Dict[str, Any]:
        """Calculate summary metrics for a customer via queries (not persisted)."""
        name_lower = customer.name.lower()
        query = select(Charge).where(
            and_(
                Charge.user_id == user_id,
                or_(
                    func.lower(Charge.customer_name) == name_lower,
                    and_(Charge.customer_phone.isnot(None), Charge.customer_phone == customer.phone) if customer.phone else False,
                ),
            )
        )
        result = await self.db.execute(query)
        charges = list(result.scalars().all())

        today = date.today()
        total_charges_count = len(charges)
        total_paid_amount = sum(
            (c.amount for c in charges if c.status == ChargeStatus.PAID),
            Decimal("0"),
        )
        total_pending_amount = sum(
            (c.amount for c in charges if c.status == ChargeStatus.PENDING and not (c.due_date and c.due_date < today)),
            Decimal("0"),
        )
        total_overdue_amount = sum(
            (c.amount for c in charges if c.status == ChargeStatus.PENDING and c.due_date and c.due_date < today),
            Decimal("0"),
        )

        paid_charges = [c for c in charges if c.status == ChargeStatus.PAID]
        overdue_charges = [c for c in charges if c.status == ChargeStatus.PENDING and c.due_date and c.due_date < today]

        last_charge_at = max((c.created_at for c in charges), default=None)
        last_payment_at = max((c.paid_at for c in paid_charges), default=None)

        operational_status = self._calculate_operational_status(
            total_charges_count=total_charges_count,
            paid_count=len(paid_charges),
            overdue_count=len(overdue_charges),
            last_charge_at=last_charge_at,
            last_payment_at=last_payment_at,
        )

        avg_delay_days = None
        if overdue_charges:
            delays = [(today - c.due_date).days for c in overdue_charges if c.due_date]
            if delays:
                avg_delay_days = sum(delays) / len(delays)

        return {
            "operational_status": operational_status,
            "total_charges_count": total_charges_count,
            "total_paid_amount": float(total_paid_amount),
            "total_pending_amount": float(total_pending_amount),
            "total_overdue_amount": float(total_overdue_amount),
            "last_charge_at": last_charge_at,
            "last_payment_at": last_payment_at,
            "has_overdue": len(overdue_charges) > 0,
            "avg_delay_days": avg_delay_days,
            "paid_count": len(paid_charges),
            "overdue_count": len(overdue_charges),
        }

    def _calculate_operational_status(
        self,
        total_charges_count: int,
        paid_count: int,
        overdue_count: int,
        last_charge_at: Optional[datetime],
        last_payment_at: Optional[datetime],
    ) -> str:
        """Calculate operational relationship status.

        This is NOT a credit score. It is an operational indicator
        based on payment behavior patterns.
        """
        if total_charges_count == 0:
            return CustomerStatus.NEW_CUSTOMER.value

        now = datetime.now(last_charge_at.tzinfo) if last_charge_at else datetime.now()

        if last_charge_at:
            days_since_last = (now - last_charge_at).days
            if days_since_last > 180:
                return CustomerStatus.INACTIVE_CUSTOMER.value

        if total_charges_count <= 2 and paid_count == 0 and overdue_count == 0:
            return CustomerStatus.NEW_CUSTOMER.value

        if overdue_count >= 3:
            return CustomerStatus.FREQUENT_LATE.value

        if overdue_count > 0:
            return CustomerStatus.LATE_PAYER.value

        if paid_count > 0 and overdue_count == 0:
            return CustomerStatus.GOOD_PAYER.value

        return CustomerStatus.NEW_CUSTOMER.value

    async def get_customer_detail(self, customer_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get full customer detail with summary."""
        customer = await self.get_customer(customer_id, user_id)
        if not customer:
            return None

        summary = await self.get_customer_summary(customer, user_id)
        charges = await self.get_customer_charges(customer_id, user_id)

        return {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "notes": customer.notes,
            "created_at": customer.created_at,
            "updated_at": customer.updated_at,
            **summary,
            "charges": [
                {
                    "id": c.id,
                    "amount": float(c.amount),
                    "description": c.description,
                    "status": c.status.value,
                    "due_date": c.due_date.isoformat() if c.due_date else None,
                    "paid_at": c.paid_at.isoformat() if c.paid_at else None,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "payment_link": c.payment_link,
                }
                for c in charges
            ],
        }

    async def update_customer_notes(self, customer_id: int, user_id: int, notes: str) -> Optional[Customer]:
        customer = await self.get_customer(customer_id, user_id)
        if not customer:
            return None
        customer.notes = notes
        await self.db.commit()
        await self.db.refresh(customer)
        return customer
