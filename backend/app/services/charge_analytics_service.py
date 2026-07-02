from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, extract
from typing import Dict, Optional, List, Any
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from app.models.charge import Charge, ChargeStatus
from app.models.customer import Customer, CustomerStatus
from app.models.collection_message_log import CollectionMessageLog, CollectionMessageStatus
from app.models.message_template import MessageTemplate, MessageTone
from app.models.collection_rule import CollectionRule
from app.core.logging import logger


class ChargeAnalyticsService:
    """User-level analytics for charge performance, aging, and insights.

    This is NOT a credit score system. All metrics are operational
    indicators based on payment behavior patterns. They must never
    be used for credit decisions or regulatory purposes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_user_charges(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
    ) -> List[Charge]:
        query = select(Charge).where(Charge.user_id == user_id)
        if organization_id is not None:
            query = query.where(Charge.organization_id == organization_id)
        if start_date:
            query = query.where(Charge.created_at >= start_date)
        if end_date:
            query = query.where(Charge.created_at <= end_date)
        if status:
            if status == "overdue":
                today = date.today()
                query = query.where(
                    and_(
                        Charge.status == ChargeStatus.PENDING,
                        Charge.due_date < today,
                    )
                )
            else:
                query = query.where(Charge.status == ChargeStatus(status))
        result = await self.db.execute(query.order_by(Charge.created_at.desc()))
        return list(result.scalars().all())

    def _classify_charge(self, charge: Charge) -> str:
        """Return derived status: pending, overdue, paid, cancelled, etc."""
        if charge.status == ChargeStatus.PENDING and charge.due_date:
            if charge.due_date < date.today():
                return "overdue"
        return charge.status.value

    @staticmethod
    def _to_aware(dt: datetime) -> datetime:
        """Ensure a datetime is timezone-aware (assume UTC if naive)."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    async def get_overview(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        charges = await self._get_user_charges(user_id, organization_id, start_date, end_date)
        today = date.today()

        total_billed = sum((c.amount for c in charges), Decimal("0"))
        paid_charges = [c for c in charges if c.status == ChargeStatus.PAID]
        pending_charges = [
            c for c in charges
            if c.status == ChargeStatus.PENDING
            and not (c.due_date and c.due_date < today)
        ]
        overdue_charges = [
            c for c in charges
            if c.status == ChargeStatus.PENDING
            and c.due_date
            and c.due_date < today
        ]

        total_paid = sum((c.amount for c in paid_charges), Decimal("0"))
        total_pending = sum((c.amount for c in pending_charges), Decimal("0"))
        total_overdue = sum((c.amount for c in overdue_charges), Decimal("0"))

        collection_rate = float(total_paid) / float(total_billed) * 100 if total_billed > 0 else 0
        overdue_rate = float(total_overdue) / float(total_billed) * 100 if total_billed > 0 else 0

        # Average payment time (days between due_date and paid_at)
        payment_times = []
        for c in paid_charges:
            if c.due_date and c.paid_at:
                paid_date = c.paid_at.date() if hasattr(c.paid_at, 'date') else c.paid_at
                delta = (paid_date - c.due_date).days
                payment_times.append(delta)
        avg_payment_time = sum(payment_times) / len(payment_times) if payment_times else None

        # Average delay (only for overdue)
        delays = []
        for c in overdue_charges:
            if c.due_date:
                delays.append((today - c.due_date).days)
        avg_delay = sum(delays) / len(delays) if delays else None

        # Active customers (unique customer_name with at least one charge)
        active_customers = set(c.customer_name for c in charges)
        overdue_customers = set(c.customer_name for c in overdue_charges)

        # Followup stats
        followup_query = select(
            func.count().label("total"),
            func.sum(
                case(
                    (CollectionMessageLog.status == CollectionMessageStatus.DRAFT, 1),
                    else_=0,
                )
            ).label("drafts"),
            func.sum(
                case(
                    (CollectionMessageLog.status == CollectionMessageStatus.SENT, 1),
                    else_=0,
                )
            ).label("sent"),
        ).where(CollectionMessageLog.user_id == user_id)
        if organization_id is not None:
            followup_query = followup_query.where(CollectionMessageLog.organization_id == organization_id)
        followup_result = await self.db.execute(followup_query)
        followup_row = followup_result.one()

        return {
            "total_billed": float(total_billed),
            "total_paid": float(total_paid),
            "total_pending": float(total_pending),
            "total_overdue": float(total_overdue),
            "collection_rate": round(collection_rate, 2),
            "overdue_rate": round(overdue_rate, 2),
            "average_payment_time_days": round(avg_payment_time, 1) if avg_payment_time is not None else None,
            "average_delay_days": round(avg_delay, 1) if avg_delay is not None else None,
            "active_customers": len(active_customers),
            "overdue_customers": len(overdue_customers),
            "followups_drafted": int(followup_row.drafts or 0),
            "followups_sent": int(followup_row.sent or 0),
            "estimated_recovered_after_followup": None,
            "total_charges": len(charges),
            "paid_count": len(paid_charges),
            "pending_count": len(pending_charges),
            "overdue_count": len(overdue_charges),
        }

    async def get_monthly_trends(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        months: int = 6,
    ) -> List[Dict[str, Any]]:
        today = date.today()
        start = today.replace(day=1) - timedelta(days=months * 30)

        charges = await self._get_user_charges(user_id, organization_id, start_date=start)

        trends = []
        for i in range(months):
            month_start = today.replace(day=1) - timedelta(days=i * 30)
            month_end = month_start + timedelta(days=30)

            month_charges = [
                c for c in charges
                if c.created_at and month_start <= c.created_at.date() < month_end
            ]
            paid = [c for c in month_charges if c.status == ChargeStatus.PAID]
            pending = [
                c for c in month_charges
                if c.status == ChargeStatus.PENDING
                and not (c.due_date and c.due_date < today)
            ]
            overdue = [
                c for c in month_charges
                if c.status == ChargeStatus.PENDING
                and c.due_date
                and c.due_date < today
            ]

            billed = sum((c.amount for c in month_charges), Decimal("0"))
            paid_amt = sum((c.amount for c in paid), Decimal("0"))
            pending_amt = sum((c.amount for c in pending), Decimal("0"))
            overdue_amt = sum((c.amount for c in overdue), Decimal("0"))

            coll_rate = float(paid_amt) / float(billed) * 100 if billed > 0 else 0

            trends.append({
                "month": month_start.strftime("%Y-%m"),
                "billed_amount": float(billed),
                "paid_amount": float(paid_amt),
                "pending_amount": float(pending_amt),
                "overdue_amount": float(overdue_amt),
                "charges_created": len(month_charges),
                "charges_paid": len(paid),
                "collection_rate": round(coll_rate, 2),
            })

        trends.reverse()
        return trends

    async def get_aging(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        today = date.today()
        charges = await self._get_user_charges(user_id, organization_id, status="overdue")

        buckets = {
            "1-7 dias": [],
            "8-15 dias": [],
            "16-30 dias": [],
            "31-60 dias": [],
            "60+ dias": [],
        }

        for c in charges:
            if not c.due_date:
                continue
            days_overdue = (today - c.due_date).days
            if days_overdue <= 7:
                buckets["1-7 dias"].append(c)
            elif days_overdue <= 15:
                buckets["8-15 dias"].append(c)
            elif days_overdue <= 30:
                buckets["16-30 dias"].append(c)
            elif days_overdue <= 60:
                buckets["31-60 dias"].append(c)
            else:
                buckets["60+ dias"].append(c)

        total_overdue = len(charges)
        result = []
        for label, items in buckets.items():
            amount = sum((c.amount for c in items), Decimal("0"))
            count = len(items)
            percentage = (count / total_overdue * 100) if total_overdue > 0 else 0
            result.append({
                "bucket": label,
                "count": count,
                "amount": float(amount),
                "percentage": round(percentage, 2),
            })

        return {
            "total_overdue": total_overdue,
            "total_overdue_amount": float(sum((c.amount for c in charges), Decimal("0"))),
            "buckets": result,
        }

    async def get_customer_performance(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        charges = await self._get_user_charges(user_id, organization_id)
        today = date.today()

        # Group by customer_name
        customer_map: Dict[str, List[Charge]] = {}
        for c in charges:
            name = c.customer_name
            if name not in customer_map:
                customer_map[name] = []
            customer_map[name].append(c)

        rankings = []
        for name, cust_charges in customer_map.items():
            paid = [c for c in cust_charges if c.status == ChargeStatus.PAID]
            pending = [
                c for c in cust_charges
                if c.status == ChargeStatus.PENDING
                and not (c.due_date and c.due_date < today)
            ]
            overdue = [
                c for c in cust_charges
                if c.status == ChargeStatus.PENDING
                and c.due_date
                and c.due_date < today
            ]

            total_billed = sum((c.amount for c in cust_charges), Decimal("0"))
            total_paid = sum((c.amount for c in paid), Decimal("0"))
            total_pending = sum((c.amount for c in pending), Decimal("0"))
            total_overdue = sum((c.amount for c in overdue), Decimal("0"))

            # Average payment delay
            delays = []
            for c in overdue:
                if c.due_date:
                    delays.append((today - c.due_date).days)
            avg_delay = round(sum(delays) / len(delays), 1) if delays else 0

            last_payment = max(
                (c.paid_at for c in paid if c.paid_at),
                default=None,
            )

            # Suggested action (operational, not credit-related)
            if not overdue and not pending:
                suggested = "thank_customer"
            elif len(overdue) >= 3:
                suggested = "review_payment_terms"
            elif len(overdue) > 0:
                suggested = "send_friendly_reminder"
            elif len(pending) > 0 and not overdue:
                suggested = "monitor"
            else:
                suggested = "no_action"

            rankings.append({
                "customer_name": name,
                "operational_status": self._derive_operational_status(len(cust_charges), len(paid), len(overdue)),
                "total_billed": float(total_billed),
                "total_paid": float(total_paid),
                "total_pending": float(total_pending),
                "total_overdue": float(total_overdue),
                "average_payment_delay_days": avg_delay,
                "charges_count": len(cust_charges),
                "last_payment_at": last_payment.isoformat() if last_payment else None,
                "suggested_action": suggested,
            })

        # Sort by total_overdue descending, then total_billed descending
        rankings.sort(key=lambda x: (-x["total_overdue"], -x["total_billed"]))
        return rankings[:limit]

    def _derive_operational_status(self, total: int, paid: int, overdue: int) -> str:
        if total == 0:
            return CustomerStatus.NEW_CUSTOMER.value
        if overdue >= 3:
            return CustomerStatus.FREQUENT_LATE.value
        if overdue > 0:
            return CustomerStatus.LATE_PAYER.value
        if paid > 0 and overdue == 0:
            return CustomerStatus.GOOD_PAYER.value
        return CustomerStatus.NEW_CUSTOMER.value

    async def get_collection_performance(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        # Total logs
        logs_query = select(CollectionMessageLog).where(
            CollectionMessageLog.user_id == user_id
        )
        if organization_id is not None:
            logs_query = logs_query.where(CollectionMessageLog.organization_id == organization_id)
        logs_result = await self.db.execute(
            logs_query.order_by(CollectionMessageLog.created_at.desc())
        )
        logs = list(logs_result.scalars().all())

        if not logs:
            return {
                "total_drafts": 0,
                "drafts_by_tone": {},
                "drafts_by_status": {},
                "customers_contacted": 0,
                "followups_this_month": 0,
                "charges_with_followup": 0,
                "charges_paid_after_followup": 0,
                "estimated_recovered_amount": 0,
                "insufficient_data": True,
            }

        # Drafts by status
        status_counts: Dict[str, int] = {}
        for log in logs:
            key = log.status.value
            status_counts[key] = status_counts.get(key, 0) + 1

        # Drafts by tone (need to join with template)
        tone_counts: Dict[str, int] = {}
        for log in logs:
            if log.template_id:
                tpl_result = await self.db.execute(
                    select(MessageTemplate).where(MessageTemplate.id == log.template_id)
                )
                tpl = tpl_result.scalar_one_or_none()
                if tpl:
                    key = tpl.tone.value
                    tone_counts[key] = tone_counts.get(key, 0) + 1
            else:
                tone_counts["fallback"] = tone_counts.get("fallback", 0) + 1

        # Customers contacted (unique customer_ids)
        customer_ids = set(log.customer_id for log in logs if log.customer_id)

        # Followups this month
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        followups_this_month = sum(
            1 for log in logs
            if log.created_at and self._to_aware(log.created_at) >= month_start
        )

        # Charges with followup
        charge_ids_with_followup = set(log.charge_id for log in logs)

        # Charges paid after followup
        paid_after = 0
        estimated_recovered = Decimal("0")
        for log in logs:
            if log.charge_id:
                charge_result = await self.db.execute(
                    select(Charge).where(
                        and_(
                            Charge.id == log.charge_id,
                            Charge.status == ChargeStatus.PAID,
                        )
                    )
                )
                charge = charge_result.scalar_one_or_none()
                if charge and charge.paid_at and log.created_at:
                    log_created = self._to_aware(log.created_at)
                    charge_paid = self._to_aware(charge.paid_at)
                    if charge_paid > log_created:
                        paid_after += 1
                        estimated_recovered += charge.amount

        return {
            "total_drafts": len(logs),
            "drafts_by_tone": tone_counts,
            "drafts_by_status": status_counts,
            "customers_contacted": len(customer_ids),
            "followups_this_month": followups_this_month,
            "charges_with_followup": len(charge_ids_with_followup),
            "charges_paid_after_followup": paid_after,
            "estimated_recovered_amount": float(estimated_recovered),
            "insufficient_data": len(logs) < 3,
        }

    async def get_insights(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[str]:
        overview = await self.get_overview(user_id, organization_id, start_date, end_date)
        aging = await self.get_aging(user_id, organization_id)
        customer_perf = await self.get_customer_performance(user_id, organization_id, limit=5)

        insights: List[str] = []

        if overview["total_charges"] == 0:
            insights.append("Você ainda não tem cobranças suficientes para gerar insights. Crie algumas cobranças para começar a acompanhar sua performance.")
            return insights

        # Collection rate insight
        rate = overview["collection_rate"]
        if rate >= 80:
            insights.append(f"Você recebeu {rate:.0f}% do valor cobrado. Excelente taxa de recebimento!")
        elif rate >= 50:
            insights.append(f"Você recebeu {rate:.0f}% do valor cobrado. Há espaço para melhorar a taxa de recebimento.")
        else:
            insights.append(f"Você recebeu {rate:.0f}% do valor cobrado. Considere revisar sua estratégia de cobrança.")

        # Overdue concentration
        overdue_customers = [c for c in customer_perf if c["total_overdue"] > 0]
        if len(overdue_customers) <= 2 and len(overdue_customers) > 0:
            names = " e ".join(c["customer_name"] for c in overdue_customers)
            insights.append(f"As cobranças vencidas estão concentradas em {len(overdue_customers)} cliente(s): {names}.")

        # Aging insight
        if aging["total_overdue"] > 0:
            biggest_bucket = max(aging["buckets"], key=lambda x: x["count"])
            if biggest_bucket["count"] > 0:
                insights.append(f"A maior parte dos atrasos está na faixa de {biggest_bucket['bucket']} ({biggest_bucket['count']} cobrança(s)).")

        # Average payment time
        if overview["average_payment_time_days"] is not None:
            avg_days = overview["average_payment_time_days"]
            if avg_days <= 0:
                insights.append("Em média, seus clientes pagam antes do vencimento. Bom sinal!")
            elif avg_days <= 5:
                insights.append(f"Em média, seus clientes pagam {avg_days:.0f} dia(s) após o vencimento.")
            else:
                insights.append(f"Em média, seus clientes levam {avg_days:.0f} dia(s) para pagar após o vencimento. Considere enviar lembretes antes do vencimento.")

        # Pending amount
        if overview["total_pending"] > 0:
            insights.append(f"Você tem R$ {overview['total_pending']:.2f} em cobranças pendentes (não vencidas).")

        return insights
