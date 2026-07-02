from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from app.models.billing import (
    SubscriptionPlan, OrganizationSubscription, UsageCounter, BillingEvent,
    SubscriptionStatus, BillingProvider,
)
from app.billing_providers.factory import get_billing_provider
from app.core.config import settings
from app.core.logging import logger


PLAN_DEFINITIONS = [
    {
        "code": "free",
        "name": "Free",
        "description": "Plano gratuito para começar",
        "price_monthly": Decimal("0.00"),
        "max_charges_per_month": 20,
        "max_customers": 10,
        "max_team_members": 1,
        "max_message_templates": 3,
        "max_recurring_tasks": 0,
        "max_whatsapp_messages_per_month": 50,
        "allow_advanced_analytics": False,
        "allow_pdf_export": False,
        "allow_ocr": False,
        "allow_collection_rules": False,
        "allow_whatsapp_intelligence": False,
    },
    {
        "code": "starter",
        "name": "Starter",
        "description": "Para pequenos negócios",
        "price_monthly": Decimal("29.90"),
        "max_charges_per_month": 100,
        "max_customers": 100,
        "max_team_members": 2,
        "max_message_templates": 10,
        "max_recurring_tasks": 5,
        "max_whatsapp_messages_per_month": 500,
        "allow_advanced_analytics": False,
        "allow_pdf_export": True,
        "allow_ocr": False,
        "allow_collection_rules": True,
        "allow_whatsapp_intelligence": True,
    },
    {
        "code": "professional",
        "name": "Professional",
        "description": "Para profissionais e empresas em crescimento",
        "price_monthly": Decimal("79.90"),
        "max_charges_per_month": 500,
        "max_customers": 500,
        "max_team_members": 5,
        "max_message_templates": 50,
        "max_recurring_tasks": 20,
        "max_whatsapp_messages_per_month": 5000,
        "allow_advanced_analytics": True,
        "allow_pdf_export": True,
        "allow_ocr": True,
        "allow_collection_rules": True,
        "allow_whatsapp_intelligence": True,
    },
    {
        "code": "business",
        "name": "Business",
        "description": "Para empresas estabelecidas",
        "price_monthly": Decimal("199.90"),
        "max_charges_per_month": 5000,
        "max_customers": 5000,
        "max_team_members": 20,
        "max_message_templates": 200,
        "max_recurring_tasks": 100,
        "max_whatsapp_messages_per_month": None,
        "allow_advanced_analytics": True,
        "allow_pdf_export": True,
        "allow_ocr": True,
        "allow_collection_rules": True,
        "allow_whatsapp_intelligence": True,
    },
]


class SaaSBillingService:
    """SaaS billing service for organization-level subscriptions.

    This is SEPARATE from the legacy BillingService which handles
    user-level Mercado Pago subscriptions. This service handles
    organization-level plan management with fake/sandbox providers.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = get_billing_provider()

    async def seed_plans(self) -> None:
        """Seed default subscription plans if they don't exist."""
        for plan_def in PLAN_DEFINITIONS:
            existing = await self.db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.code == plan_def["code"])
            )
            if existing.scalar_one_or_none():
                continue
            plan = SubscriptionPlan(**plan_def, active=True)
            self.db.add(plan)
        await self.db.commit()
        logger.info("Subscription plans seeded")

    async def list_plans(self, active_only: bool = True) -> List[SubscriptionPlan]:
        query = select(SubscriptionPlan)
        if active_only:
            query = query.where(SubscriptionPlan.active == True)
        query = query.order_by(SubscriptionPlan.price_monthly.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_plan_by_code(self, code: str) -> Optional[SubscriptionPlan]:
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.code == code)
        )
        return result.scalar_one_or_none()

    async def get_plan_by_id(self, plan_id: int) -> Optional[SubscriptionPlan]:
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_subscription(self, organization_id: int) -> Optional[OrganizationSubscription]:
        result = await self.db.execute(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def get_current_plan(self, organization_id: int) -> Optional[SubscriptionPlan]:
        sub = await self.get_subscription(organization_id)
        if not sub:
            return await self.get_plan_by_code("free")
        return await self.get_plan_by_id(sub.plan_id)

    async def ensure_free_subscription(self, organization_id: int) -> OrganizationSubscription:
        """Ensure organization has at least a Free subscription."""
        existing = await self.get_subscription(organization_id)
        if existing:
            return existing

        free_plan = await self.get_plan_by_code("free")
        if not free_plan:
            await self.seed_plans()
            free_plan = await self.get_plan_by_code("free")

        now = datetime.now(timezone.utc)
        sub = OrganizationSubscription(
            organization_id=organization_id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_provider=BillingProvider.FAKE,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=False,
        )
        self.db.add(sub)
        await self.db.flush()

        await self._record_event(
            organization_id=organization_id,
            subscription_id=sub.id,
            event_type="subscription_created_free",
            provider="fake",
            payload={"plan_code": "free"},
        )

        await self._ensure_usage_counter(organization_id)
        await self.db.commit()
        await self.db.refresh(sub)
        logger.info(f"Free subscription created for org {organization_id}")
        return sub

    async def create_subscription(
        self, organization_id: int, plan_code: str
    ) -> OrganizationSubscription:
        """Create a new subscription (fake provider by default)."""
        plan = await self.get_plan_by_code(plan_code)
        if not plan:
            raise ValueError(f"Plan '{plan_code}' not found")

        existing = await self.get_subscription(organization_id)
        if existing:
            raise ValueError("Organization already has a subscription. Use change_plan instead.")

        provider_result = await self.provider.create_subscription(plan_code, organization_id)
        now = datetime.now(timezone.utc)

        sub = OrganizationSubscription(
            organization_id=organization_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_provider=BillingProvider.FAKE,
            provider_subscription_id=provider_result.get("provider_subscription_id"),
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=False,
        )
        self.db.add(sub)
        await self.db.flush()

        await self._record_event(
            organization_id=organization_id,
            subscription_id=sub.id,
            event_type="subscription_created",
            provider=self.provider.name,
            payload={"plan_code": plan_code, **provider_result},
        )

        await self._ensure_usage_counter(organization_id)
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def change_plan(
        self, organization_id: int, new_plan_code: str
    ) -> OrganizationSubscription:
        """Change the plan of an existing subscription."""
        sub = await self.get_subscription(organization_id)
        if not sub:
            raise ValueError("No subscription found for organization")

        new_plan = await self.get_plan_by_code(new_plan_code)
        if not new_plan:
            raise ValueError(f"Plan '{new_plan_code}' not found")

        old_plan_id = sub.plan_id

        if sub.provider_subscription_id:
            provider_result = await self.provider.change_plan(
                sub.provider_subscription_id, new_plan_code
            )
        else:
            provider_result = {"status": "active", "plan_code": new_plan_code}

        sub.plan_id = new_plan.id
        sub.status = SubscriptionStatus.ACTIVE
        sub.cancel_at_period_end = False
        now = datetime.now(timezone.utc)
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=30)

        await self._record_event(
            organization_id=organization_id,
            subscription_id=sub.id,
            event_type="plan_changed",
            provider=self.provider.name,
            payload={"old_plan_id": old_plan_id, "new_plan_code": new_plan_code, **provider_result},
        )

        await self.db.commit()
        await self.db.refresh(sub)
        logger.info(f"Plan changed for org {organization_id} to {new_plan_code}")
        return sub

    async def cancel_subscription(self, organization_id: int) -> OrganizationSubscription:
        """Cancel subscription (downgrade to free at period end)."""
        sub = await self.get_subscription(organization_id)
        if not sub:
            raise ValueError("No subscription found for organization")

        if sub.provider_subscription_id:
            provider_result = await self.provider.cancel_subscription(
                sub.provider_subscription_id
            )
        else:
            provider_result = {"status": "cancelled", "cancel_at_period_end": True}

        sub.cancel_at_period_end = True
        sub.status = SubscriptionStatus.CANCELLED

        free_plan = await self.get_plan_by_code("free")
        if free_plan:
            sub.plan_id = free_plan.id

        await self._record_event(
            organization_id=organization_id,
            subscription_id=sub.id,
            event_type="subscription_cancelled",
            provider=self.provider.name,
            payload=provider_result,
        )

        await self.db.commit()
        await self.db.refresh(sub)
        logger.info(f"Subscription cancelled for org {organization_id}")
        return sub

    async def reactivate_subscription(self, organization_id: int) -> OrganizationSubscription:
        """Reactivate a cancelled subscription."""
        sub = await self.get_subscription(organization_id)
        if not sub:
            raise ValueError("No subscription found for organization")

        if sub.provider_subscription_id:
            provider_result = await self.provider.reactivate_subscription(
                sub.provider_subscription_id
            )
        else:
            provider_result = {"status": "active", "cancel_at_period_end": False}

        sub.cancel_at_period_end = False
        sub.status = SubscriptionStatus.ACTIVE
        now = datetime.now(timezone.utc)
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=30)

        await self._record_event(
            organization_id=organization_id,
            subscription_id=sub.id,
            event_type="subscription_reactivated",
            provider=self.provider.name,
            payload=provider_result,
        )

        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def fake_checkout(
        self, organization_id: int, plan_code: str
    ) -> OrganizationSubscription:
        """Simulate a checkout flow (fake provider). Always succeeds."""
        sub = await self.get_subscription(organization_id)
        if sub:
            return await self.change_plan(organization_id, plan_code)
        return await self.create_subscription(organization_id, plan_code)

    async def get_usage(self, organization_id: int) -> Optional[UsageCounter]:
        """Get the current period usage counter for an organization."""
        now = datetime.now(timezone.utc)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await self.db.execute(
            select(UsageCounter).where(
                and_(
                    UsageCounter.organization_id == organization_id,
                    UsageCounter.period_start == period_start,
                )
            )
        )
        return result.scalar_one_or_none()

    async def increment_usage(
        self, organization_id: int, field: str, amount: int = 1
    ) -> UsageCounter:
        """Increment a usage counter field for the current period."""
        counter = await self._ensure_usage_counter(organization_id)
        current_value = getattr(counter, field, 0) or 0
        setattr(counter, field, current_value + amount)
        await self.db.commit()
        await self.db.refresh(counter)
        return counter

    async def get_entitlements(self, organization_id: int) -> Dict[str, Any]:
        """Get the current entitlements for an organization."""
        plan = await self.get_current_plan(organization_id)
        if not plan:
            return {
                "plan": "none",
                "allowed": False,
                "reason": "no_plan_found",
            }
        return {
            "plan": plan.code,
            "plan_name": plan.name,
            "max_charges_per_month": plan.max_charges_per_month,
            "max_customers": plan.max_customers,
            "max_team_members": plan.max_team_members,
            "max_message_templates": plan.max_message_templates,
            "max_recurring_tasks": plan.max_recurring_tasks,
            "max_whatsapp_messages_per_month": plan.max_whatsapp_messages_per_month,
            "allow_advanced_analytics": plan.allow_advanced_analytics,
            "allow_pdf_export": plan.allow_pdf_export,
            "allow_ocr": plan.allow_ocr,
            "allow_collection_rules": plan.allow_collection_rules,
            "allow_whatsapp_intelligence": plan.allow_whatsapp_intelligence,
        }

    async def _ensure_usage_counter(self, organization_id: int) -> UsageCounter:
        """Get or create the usage counter for the current period."""
        now = datetime.now(timezone.utc)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_start.month == 12:
            next_month = period_start.replace(year=period_start.year + 1, month=1)
        else:
            next_month = period_start.replace(month=period_start.month + 1)
        period_end = next_month - timedelta(seconds=1)

        result = await self.db.execute(
            select(UsageCounter).where(
                and_(
                    UsageCounter.organization_id == organization_id,
                    UsageCounter.period_start == period_start,
                )
            )
        )
        counter = result.scalar_one_or_none()
        if counter:
            return counter

        counter = UsageCounter(
            organization_id=organization_id,
            period_start=period_start,
            period_end=period_end,
        )
        self.db.add(counter)
        await self.db.flush()
        return counter

    async def _record_event(
        self,
        organization_id: int,
        subscription_id: Optional[int],
        event_type: str,
        provider: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = BillingEvent(
            organization_id=organization_id,
            subscription_id=subscription_id,
            event_type=event_type,
            provider=provider,
            payload=payload or {},
        )
        self.db.add(event)

    async def get_billing_events(
        self, organization_id: int, limit: int = 50
    ) -> List[BillingEvent]:
        result = await self.db.execute(
            select(BillingEvent)
            .where(BillingEvent.organization_id == organization_id)
            .order_by(BillingEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_subscription_summary(self, organization_id: int) -> Dict[str, Any]:
        """Get a full subscription summary including plan, usage, and entitlements."""
        sub = await self.get_subscription(organization_id)
        plan = await self.get_current_plan(organization_id)
        usage = await self.get_usage(organization_id)
        entitlements = await self.get_entitlements(organization_id)

        return {
            "subscription": {
                "id": sub.id if sub else None,
                "status": sub.status.value if sub else "none",
                "billing_provider": sub.billing_provider.value if sub else "fake",
                "current_period_start": sub.current_period_start.isoformat() if sub and sub.current_period_start else None,
                "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
                "cancel_at_period_end": sub.cancel_at_period_end if sub else False,
            },
            "plan": {
                "code": plan.code if plan else "none",
                "name": plan.name if plan else "None",
                "price_monthly": str(plan.price_monthly) if plan else "0",
                "currency": plan.currency if plan else "BRL",
            },
            "usage": {
                "charges_created": usage.charges_created if usage else 0,
                "customers_created": usage.customers_created if usage else 0,
                "templates_created": usage.templates_created if usage else 0,
                "recurring_tasks_created": usage.recurring_tasks_created if usage else 0,
                "ocr_documents_analyzed": usage.ocr_documents_analyzed if usage else 0,
                "pdf_exports_generated": usage.pdf_exports_generated if usage else 0,
                "whatsapp_messages_processed": usage.whatsapp_messages_processed if usage else 0,
                "collection_followups_generated": usage.collection_followups_generated if usage else 0,
            },
            "entitlements": entitlements,
        }
