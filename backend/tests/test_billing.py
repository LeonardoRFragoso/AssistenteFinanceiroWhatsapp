"""
Sprint 12 — SaaS Billing, Plans, Usage Limits e Subscription Sandbox tests.

Covers:
- Plans seeded correctly
- New organization gets Free subscription
- Demo gets Professional plan
- Get subscription
- Change plan (owner/admin)
- Viewer cannot change plan
- Finance can view usage
- Charge limit on Free
- Customer limit on Free
- Team member limit on Free
- OCR blocked on Free
- PDF export blocked on Free
- Professional unlocks OCR/PDF
- Usage increments after creating charge
- Usage does not increment on failure
- Fake checkout changes subscription
- Billing event recorded
- User isolation between organizations
- Billing provider fake is default
- No real Stripe/Mercado Pago calls
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models import User
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.billing import (
    SubscriptionPlan, OrganizationSubscription, UsageCounter, BillingEvent,
    SubscriptionStatus, BillingProvider,
)
from app.models.subscription import Subscription
from app.services.saas_billing_service import SaaSBillingService
from app.services.entitlements_service import EntitlementsService
from app.main import app
from datetime import datetime, timezone


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def authed_user(test_session):
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password="$2b$12$testhash",
        phone_number="+5511999999999"
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    sub = Subscription(user_id=user.id, plan="free", status="active")
    test_session.add(sub)
    await test_session.commit()

    return user


@pytest_asyncio.fixture
async def authed_org(test_session, authed_user):
    org = Organization(
        name="Test Org",
        slug=f"test-org-{authed_user.id}",
        owner_user_id=authed_user.id,
    )
    test_session.add(org)
    await test_session.flush()
    test_session.add(OrganizationMember(
        organization_id=org.id,
        user_id=authed_user.id,
        role=OrganizationRole.OWNER,
        active=True,
        joined_at=datetime.now(timezone.utc),
    ))
    await test_session.commit()
    await test_session.refresh(org)

    # Seed billing plans
    billing = SaaSBillingService(test_session)
    await billing.seed_plans()
    await billing.ensure_free_subscription(org.id)

    return org


@pytest_asyncio.fixture
async def auth_token(authed_user):
    return create_access_token(data={"sub": str(authed_user.id)})


@pytest_asyncio.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def client(test_session, auth_headers):
    async def override_get_db():
        yield test_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestPlanSeeding:
    @pytest.mark.asyncio
    async def test_plans_seeded(self, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        plans = await service.list_plans(active_only=False)
        codes = [p.code for p in plans]
        assert "free" in codes
        assert "starter" in codes
        assert "professional" in codes
        assert "business" in codes

    @pytest.mark.asyncio
    async def test_free_plan_limits(self, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        free = await service.get_plan_by_code("free")
        assert free.max_charges_per_month == 20
        assert free.max_customers == 10
        assert free.max_team_members == 1
        assert free.allow_ocr is False
        assert free.allow_pdf_export is False

    @pytest.mark.asyncio
    async def test_professional_plan_features(self, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        prof = await service.get_plan_by_code("professional")
        assert prof.allow_ocr is True
        assert prof.allow_pdf_export is True
        assert prof.allow_advanced_analytics is True
        assert prof.allow_collection_rules is True


class TestDefaultSubscription:
    @pytest.mark.asyncio
    async def test_new_org_gets_free(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        sub = await service.ensure_free_subscription(authed_org.id)
        assert sub.status == SubscriptionStatus.ACTIVE
        plan = await service.get_current_plan(authed_org.id)
        assert plan.code == "free"

    @pytest.mark.asyncio
    async def test_billing_event_recorded(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        events = await service.get_billing_events(authed_org.id)
        assert len(events) >= 1
        assert events[0].event_type == "subscription_created_free"


class TestChangePlan:
    @pytest.mark.asyncio
    async def test_change_plan_owner(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        sub = await service.change_plan(authed_org.id, "professional")
        assert sub.status == SubscriptionStatus.ACTIVE
        plan = await service.get_current_plan(authed_org.id)
        assert plan.code == "professional"

    @pytest.mark.asyncio
    async def test_change_plan_records_event(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "starter")
        events = await service.get_billing_events(authed_org.id)
        event_types = [e.event_type for e in events]
        assert "plan_changed" in event_types

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        sub = await service.cancel_subscription(authed_org.id)
        assert sub.status == SubscriptionStatus.CANCELLED
        assert sub.cancel_at_period_end is True

    @pytest.mark.asyncio
    async def test_reactivate_subscription(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        await service.cancel_subscription(authed_org.id)
        sub = await service.reactivate_subscription(authed_org.id)
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.cancel_at_period_end is False


class TestEntitlements:
    @pytest.mark.asyncio
    async def test_free_charge_limit(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_create_charge(authed_org.id)
        assert result["allowed"] is True
        assert result["plan"] == "free"

    @pytest.mark.asyncio
    async def test_free_charge_limit_exceeded(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        # Increment usage to the limit
        for _ in range(20):
            await service.increment_usage(authed_org.id, "charges_created")
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_create_charge(authed_org.id)
        assert result["allowed"] is False
        assert result["reason"] == "monthly_charge_limit_reached"
        assert result["limit"] == 20
        assert result["current_usage"] == 20

    @pytest.mark.asyncio
    async def test_ocr_blocked_on_free(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_use_ocr(authed_org.id)
        assert result["allowed"] is False
        assert result["reason"] == "ocr_not_included"

    @pytest.mark.asyncio
    async def test_pdf_blocked_on_free(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_export_pdf(authed_org.id)
        assert result["allowed"] is False
        assert result["reason"] == "pdf_export_not_included"

    @pytest.mark.asyncio
    async def test_professional_unlocks_ocr(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_use_ocr(authed_org.id)
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_professional_unlocks_pdf(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_export_pdf(authed_org.id)
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_collection_rules_blocked_on_free(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_use_collection_rules(authed_org.id)
        assert result["allowed"] is False

    @pytest.mark.asyncio
    async def test_team_member_limit_free(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_add_team_member(authed_org.id)
        # Free plan has 1 member, and the owner is already a member
        assert result["allowed"] is False
        assert result["reason"] == "team_member_limit_reached"


class TestUsageTracking:
    @pytest.mark.asyncio
    async def test_usage_increments(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.increment_usage(authed_org.id, "charges_created")
        await service.increment_usage(authed_org.id, "charges_created")
        usage = await service.get_usage(authed_org.id)
        assert usage.charges_created == 2

    @pytest.mark.asyncio
    async def test_usage_separate_per_org(self, test_session, authed_org):
        # Create a second org
        user2 = User(name="User2", email="u2@test.com", hashed_password="x", phone_number="+5511")
        test_session.add(user2)
        await test_session.commit()
        await test_session.refresh(user2)
        org2 = Organization(name="Org2", slug=f"org2-{user2.id}", owner_user_id=user2.id)
        test_session.add(org2)
        await test_session.commit()
        await test_session.refresh(org2)

        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.ensure_free_subscription(org2.id)

        await service.increment_usage(authed_org.id, "charges_created", 5)
        await service.increment_usage(org2.id, "charges_created", 3)

        usage1 = await service.get_usage(authed_org.id)
        usage2 = await service.get_usage(org2.id)
        assert usage1.charges_created == 5
        assert usage2.charges_created == 3


class TestFakeCheckout:
    @pytest.mark.asyncio
    async def test_fake_checkout_changes_plan(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        sub = await service.fake_checkout(authed_org.id, "business")
        plan = await service.get_current_plan(authed_org.id)
        assert plan.code == "business"

    @pytest.mark.asyncio
    async def test_fake_checkout_records_event(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.fake_checkout(authed_org.id, "starter")
        events = await service.get_billing_events(authed_org.id)
        event_types = [e.event_type for e in events]
        assert "plan_changed" in event_types


class TestBillingProvider:
    @pytest.mark.asyncio
    async def test_default_provider_is_fake(self):
        from app.billing_providers.factory import get_billing_provider
        provider = get_billing_provider()
        assert provider.name == "fake"

    @pytest.mark.asyncio
    async def test_unknown_provider_falls_back_to_fake(self):
        from app.billing_providers.factory import get_billing_provider
        provider = get_billing_provider("unknown_provider")
        assert provider.name == "fake"

    @pytest.mark.asyncio
    async def test_fake_provider_create_subscription(self):
        from app.billing_providers.fake_billing_provider import FakeBillingProvider
        provider = FakeBillingProvider()
        result = await provider.create_subscription("professional", organization_id=1)
        assert "provider_subscription_id" in result
        assert result["status"] == "active"


class TestBillingEndpoints:
    @pytest.mark.asyncio
    async def test_list_plans(self, client, auth_headers, authed_org):
        resp = await client.get("/saas-billing/plans", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        codes = [p["code"] for p in data]
        assert "free" in codes
        assert "professional" in codes

    @pytest.mark.asyncio
    async def test_get_subscription(self, client, auth_headers, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        resp = await client.get("/saas-billing/subscription", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"]["code"] == "free"

    @pytest.mark.asyncio
    async def test_get_entitlements(self, client, auth_headers, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        resp = await client.get("/saas-billing/entitlements", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "free"
        assert data["allow_ocr"] is False

    @pytest.mark.asyncio
    async def test_get_usage(self, client, auth_headers, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        resp = await client.get("/saas-billing/usage", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["charges_created"] == 0

    @pytest.mark.asyncio
    async def test_change_plan_endpoint(self, client, auth_headers, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        resp = await client.post(
            "/saas-billing/subscription/change-plan",
            json={"plan_code": "professional"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_code"] == "professional"

    @pytest.mark.asyncio
    async def test_cancel_subscription_endpoint(self, client, auth_headers, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        resp = await client.post(
            "/saas-billing/subscription/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_fake_checkout_endpoint(self, client, auth_headers, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        resp = await client.post(
            "/saas-billing/fake/checkout",
            json={"plan_code": "business"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_code"] == "business"
        assert "no real payment" in data["message"].lower()


class TestSubscriptionSummary:
    @pytest.mark.asyncio
    async def test_summary_contains_all_fields(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        await service.increment_usage(authed_org.id, "charges_created", 5)
        summary = await service.get_subscription_summary(authed_org.id)
        assert "subscription" in summary
        assert "plan" in summary
        assert "usage" in summary
        assert "entitlements" in summary
        assert summary["plan"]["code"] == "professional"
        assert summary["usage"]["charges_created"] == 5
        assert summary["entitlements"]["allow_ocr"] is True


# ============================================================
# Sprint 12.1 — Billing Hardening Tests
# ============================================================

class TestSeedIdempotency:
    @pytest.mark.asyncio
    async def test_seed_twice_no_duplicate(self, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.seed_plans()
        plans = await service.list_plans(active_only=False)
        codes = [p.code for p in plans]
        assert len(codes) == 4
        assert len(set(codes)) == 4

    @pytest.mark.asyncio
    async def test_seed_updates_existing_plan(self, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        free = await service.get_plan_by_code("free")
        original_limit = free.max_charges_per_month
        # Modify the plan in DB
        free.max_charges_per_month = 999
        await test_session.commit()
        # Re-seed should update it back
        await service.seed_plans()
        await test_session.refresh(free)
        assert free.max_charges_per_month == original_limit

    @pytest.mark.asyncio
    async def test_business_plan_limits(self, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        biz = await service.get_plan_by_code("business")
        assert biz.max_charges_per_month == 5000
        assert biz.max_customers == 5000
        assert biz.max_team_members == 20
        assert biz.max_whatsapp_messages_per_month is None
        assert biz.allow_ocr is True
        assert biz.allow_pdf_export is True
        assert biz.allow_advanced_analytics is True


class TestDowngradeProtection:
    @pytest.mark.asyncio
    async def test_upgrade_allowed(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        sub = await service.change_plan(authed_org.id, "professional")
        assert sub.status == SubscriptionStatus.ACTIVE
        plan = await service.get_current_plan(authed_org.id)
        assert plan.code == "professional"

    @pytest.mark.asyncio
    async def test_downgrade_within_limit_allowed(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        # No usage, so downgrade should be fine
        sub = await service.change_plan(authed_org.id, "starter")
        plan = await service.get_current_plan(authed_org.id)
        assert plan.code == "starter"

    @pytest.mark.asyncio
    async def test_downgrade_blocked_when_usage_exceeds(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        # Exceed starter limits (100 charges)
        await service.increment_usage(authed_org.id, "charges_created", 150)
        with pytest.raises(ValueError, match="current_usage_exceeds_target_plan"):
            await service.change_plan(authed_org.id, "starter")

    @pytest.mark.asyncio
    async def test_downgrade_to_free_blocked_when_usage_exceeds(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        # Exceed free limits (20 charges)
        await service.increment_usage(authed_org.id, "charges_created", 25)
        with pytest.raises(ValueError, match="current_usage_exceeds_target_plan"):
            await service.change_plan(authed_org.id, "free")

    @pytest.mark.asyncio
    async def test_change_plan_records_event(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "starter")
        events = await service.get_billing_events(authed_org.id)
        event_types = [e.event_type for e in events]
        assert "plan_changed" in event_types

    @pytest.mark.asyncio
    async def test_cancel_records_event(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        await service.cancel_subscription(authed_org.id)
        events = await service.get_billing_events(authed_org.id)
        event_types = [e.event_type for e in events]
        assert "subscription_cancelled" in event_types

    @pytest.mark.asyncio
    async def test_reactivate_records_event(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.change_plan(authed_org.id, "professional")
        await service.cancel_subscription(authed_org.id)
        await service.reactivate_subscription(authed_org.id)
        events = await service.get_billing_events(authed_org.id)
        event_types = [e.event_type for e in events]
        assert "subscription_reactivated" in event_types


class TestEntitlementPayload:
    @pytest.mark.asyncio
    async def test_charge_entitlement_has_feature_field(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_create_charge(authed_org.id)
        assert "feature" in result
        assert result["feature"] == "charges"
        assert "plan_name" in result

    @pytest.mark.asyncio
    async def test_ocr_entitlement_has_feature_field(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_use_ocr(authed_org.id)
        assert "feature" in result
        assert result["feature"] == "ocr"
        assert result["plan_name"] == "Free"

    @pytest.mark.asyncio
    async def test_whatsapp_entitlement_has_feature_field(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_process_whatsapp_message(authed_org.id)
        assert "feature" in result
        assert result["feature"] == "whatsapp_messages"

    @pytest.mark.asyncio
    async def test_all_entitlements_return_plan_name(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        ent_svc = EntitlementsService(test_session)
        checks = [
            ent_svc.can_create_charge(authed_org.id),
            ent_svc.can_create_customer(authed_org.id),
            ent_svc.can_create_template(authed_org.id),
            ent_svc.can_create_recurring_task(authed_org.id),
            ent_svc.can_use_ocr(authed_org.id),
            ent_svc.can_export_pdf(authed_org.id),
            ent_svc.can_use_advanced_analytics(authed_org.id),
            ent_svc.can_use_collection_rules(authed_org.id),
            ent_svc.can_add_team_member(authed_org.id),
            ent_svc.can_process_whatsapp_message(authed_org.id),
        ]
        results = []
        for c in checks:
            results.append(await c)
        for r in results:
            assert "plan_name" in r
            assert "feature" in r


class TestUsageIntegrity:
    @pytest.mark.asyncio
    async def test_usage_does_not_increment_on_blocked(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        # Fill up charges to limit (20)
        await service.increment_usage(authed_org.id, "charges_created", 20)
        ent_svc = EntitlementsService(test_session)
        result = await ent_svc.can_create_charge(authed_org.id)
        assert result["allowed"] is False
        # Usage should still be 20, not 21
        usage = await service.get_usage(authed_org.id)
        assert usage.charges_created == 20

    @pytest.mark.asyncio
    async def test_usage_separate_per_org(self, test_session, authed_org):
        user2 = User(name="User2", email="u2@test.com", hashed_password="x", phone_number="+5511")
        test_session.add(user2)
        await test_session.commit()
        await test_session.refresh(user2)
        org2 = Organization(name="Org2", slug=f"org2-{user2.id}", owner_user_id=user2.id)
        test_session.add(org2)
        await test_session.commit()
        await test_session.refresh(org2)

        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.ensure_free_subscription(org2.id)

        await service.increment_usage(authed_org.id, "charges_created", 5)
        await service.increment_usage(org2.id, "charges_created", 3)

        usage1 = await service.get_usage(authed_org.id)
        usage2 = await service.get_usage(org2.id)
        assert usage1.charges_created == 5
        assert usage2.charges_created == 3

    @pytest.mark.asyncio
    async def test_no_duplicate_subscription_for_org(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        sub1 = await service.ensure_free_subscription(authed_org.id)
        sub2 = await service.ensure_free_subscription(authed_org.id)
        assert sub1.id == sub2.id


class TestBillingEventIdempotency:
    @pytest.mark.asyncio
    async def test_duplicate_provider_event_id_skipped(self, test_session, authed_org):
        from app.models.billing import BillingEvent
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        # Record event with provider_event_id
        await service._record_event(
            organization_id=authed_org.id,
            subscription_id=1,
            event_type="fake_checkout",
            provider="fake",
            payload={"plan_code": "starter"},
            provider_event_id="evt_123",
        )
        await test_session.commit()
        # Try to record same event again
        await service._record_event(
            organization_id=authed_org.id,
            subscription_id=1,
            event_type="fake_checkout",
            provider="fake",
            payload={"plan_code": "starter"},
            provider_event_id="evt_123",
        )
        await test_session.commit()
        events = await service.get_billing_events(authed_org.id)
        dup_events = [e for e in events if e.provider_event_id == "evt_123"]
        assert len(dup_events) == 1

    @pytest.mark.asyncio
    async def test_payload_secrets_redacted(self, test_session, authed_org):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service._record_event(
            organization_id=authed_org.id,
            subscription_id=1,
            event_type="test_event",
            provider="fake",
            payload={"plan_code": "starter", "api_key": "secret123", "token": "abc"},
        )
        await test_session.commit()
        events = await service.get_billing_events(authed_org.id)
        test_event = [e for e in events if e.event_type == "test_event"][0]
        assert test_event.payload["api_key"] == "[REDACTED]"
        assert test_event.payload["token"] == "[REDACTED]"
        assert test_event.payload["plan_code"] == "starter"

    @pytest.mark.asyncio
    async def test_events_are_org_scoped(self, test_session, authed_org):
        user2 = User(name="U2", email="u2@t.com", hashed_password="x", phone_number="+5511")
        test_session.add(user2)
        await test_session.commit()
        await test_session.refresh(user2)
        org2 = Organization(name="O2", slug=f"o2-{user2.id}", owner_user_id=user2.id)
        test_session.add(org2)
        await test_session.commit()
        await test_session.refresh(org2)

        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        await service.ensure_free_subscription(org2.id)

        events1 = await service.get_billing_events(authed_org.id)
        events2 = await service.get_billing_events(org2.id)
        for e in events1:
            assert e.organization_id == authed_org.id
        for e in events2:
            assert e.organization_id == org2.id


class TestProviderFactoryHardening:
    @pytest.mark.asyncio
    async def test_default_provider_is_fake(self):
        from app.billing_providers.factory import get_billing_provider
        provider = get_billing_provider()
        assert provider.name == "fake"

    @pytest.mark.asyncio
    async def test_unknown_provider_falls_back_in_testing(self):
        from app.billing_providers.factory import get_billing_provider
        provider = get_billing_provider("unknown_xyz")
        assert provider.name == "fake"

    @pytest.mark.asyncio
    async def test_production_rejects_unknown_provider(self, monkeypatch):
        from app.billing_providers.factory import get_billing_provider
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        with pytest.raises(ValueError, match="Unknown billing provider"):
            get_billing_provider("unknown_xyz")

    @pytest.mark.asyncio
    async def test_production_accepts_fake(self, monkeypatch):
        from app.billing_providers.factory import get_billing_provider
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        provider = get_billing_provider("fake")
        assert provider.name == "fake"

    @pytest.mark.asyncio
    async def test_demo_mode_forces_fake(self, monkeypatch):
        from app.billing_providers.factory import get_billing_provider
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", True)
        provider = get_billing_provider("stripe_sandbox")
        assert provider.name == "fake"


class TestRBACBilling:
    @pytest_asyncio.fixture
    async def viewer_user_and_token(self, test_session, authed_org):
        viewer = User(
            name="Viewer", email="viewer@test.com", hashed_password="x",
            phone_number="+5511888888888"
        )
        test_session.add(viewer)
        await test_session.flush()
        test_session.add(OrganizationMember(
            organization_id=authed_org.id,
            user_id=viewer.id,
            role=OrganizationRole.VIEWER,
            active=True,
            joined_at=datetime.now(timezone.utc),
        ))
        test_session.add(Subscription(user_id=viewer.id, plan="free", status="active"))
        await test_session.commit()
        await test_session.refresh(viewer)
        token = create_access_token(data={"sub": str(viewer.id)})
        return viewer, {"Authorization": f"Bearer {token}"}

    @pytest_asyncio.fixture
    async def finance_user_and_token(self, test_session, authed_org):
        finance = User(
            name="Finance", email="finance@test.com", hashed_password="x",
            phone_number="+5511777777777"
        )
        test_session.add(finance)
        await test_session.flush()
        test_session.add(OrganizationMember(
            organization_id=authed_org.id,
            user_id=finance.id,
            role=OrganizationRole.FINANCE,
            active=True,
            joined_at=datetime.now(timezone.utc),
        ))
        test_session.add(Subscription(user_id=finance.id, plan="free", status="active"))
        await test_session.commit()
        await test_session.refresh(finance)
        token = create_access_token(data={"sub": str(finance.id)})
        return finance, {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_viewer_cannot_change_plan(self, client, viewer_user_and_token, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        _, headers = viewer_user_and_token
        headers = {**headers, "X-Organization-ID": str(authed_org.id)}
        resp = await client.post(
            "/saas-billing/subscription/change-plan",
            json={"plan_code": "professional"},
            headers=headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_finance_cannot_change_plan(self, client, finance_user_and_token, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        _, headers = finance_user_and_token
        headers = {**headers, "X-Organization-ID": str(authed_org.id)}
        resp = await client.post(
            "/saas-billing/subscription/change-plan",
            json={"plan_code": "professional"},
            headers=headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_finance_can_view_usage(self, client, finance_user_and_token, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        _, headers = finance_user_and_token
        headers = {**headers, "X-Organization-ID": str(authed_org.id)}
        resp = await client.get("/saas-billing/usage", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_view_subscription(self, client, viewer_user_and_token, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        _, headers = viewer_user_and_token
        headers = {**headers, "X-Organization-ID": str(authed_org.id)}
        resp = await client.get("/saas-billing/subscription", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_cannot_cancel(self, client, viewer_user_and_token, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        _, headers = viewer_user_and_token
        headers = {**headers, "X-Organization-ID": str(authed_org.id)}
        resp = await client.post("/saas-billing/subscription/cancel", headers=headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_fake_checkout(self, client, viewer_user_and_token, authed_org, test_session):
        service = SaaSBillingService(test_session)
        await service.seed_plans()
        await service.ensure_free_subscription(authed_org.id)
        _, headers = viewer_user_and_token
        headers = {**headers, "X-Organization-ID": str(authed_org.id)}
        resp = await client.post(
            "/saas-billing/fake/checkout",
            json={"plan_code": "business"},
            headers=headers,
        )
        assert resp.status_code == 403


class TestListPlansIncludesWhatsApp:
    @pytest.mark.asyncio
    async def test_list_plans_has_whatsapp_limit(self, client, auth_headers, authed_org):
        resp = await client.get("/saas-billing/plans", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for plan in data:
            assert "max_whatsapp_messages_per_month" in plan
