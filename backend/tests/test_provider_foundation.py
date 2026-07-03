"""
Tests for provider foundation — connections, consents, webhooks, audit logs.

Sprint 14 — Provider Foundation
"""
import pytest
from app.services.provider_connection_service import ProviderConnectionService
from app.services.open_finance_consent_service import OpenFinanceConsentService
from app.services.provider_webhook_service import ProviderWebhookService
from app.services.organization_audit_service import OrganizationAuditService


@pytest.fixture
async def org_with_members(db_session):
    """Create an org with owner, admin, finance, and viewer members."""
    from app.models.organization import Organization, OrganizationMember, OrganizationRole
    from app.models.user import User
    from app.models.billing import OrganizationSubscription, SubscriptionPlan, SubscriptionStatus, BillingProvider
    from datetime import datetime, timezone, timedelta

    owner = User(name="Owner", email="owner@test.com", hashed_password="hashed", phone_number="+5511999999991")
    admin = User(name="Admin", email="admin@test.com", hashed_password="hashed", phone_number="+5511999999992")
    finance = User(name="Finance", email="finance@test.com", hashed_password="hashed", phone_number="+5511999999993")
    viewer = User(name="Viewer", email="viewer@test.com", hashed_password="hashed", phone_number="+5511999999994")
    db_session.add_all([owner, admin, finance, viewer])
    await db_session.flush()

    org = Organization(name="Test Org", slug="test-org", owner_user_id=owner.id)
    db_session.add(org)
    await db_session.flush()

    for user, role in [(owner, OrganizationRole.OWNER), (admin, OrganizationRole.ADMIN),
                       (finance, OrganizationRole.FINANCE), (viewer, OrganizationRole.VIEWER)]:
        m = OrganizationMember(organization_id=org.id, user_id=user.id, role=role)
        db_session.add(m)

    plan = SubscriptionPlan(code="free", name="Free", price_monthly=0, active=True)
    db_session.add(plan)
    await db_session.flush()

    sub = OrganizationSubscription(
        organization_id=org.id, plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE, billing_provider=BillingProvider.FAKE,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(sub)

    await db_session.commit()
    return org, owner, admin, finance, viewer


class TestProviderConnection:
    @pytest.mark.asyncio
    async def test_create_fake_connection(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = ProviderConnectionService(db_session)
        conn = await service.create_connection(
            organization_id=org.id, user_id=owner.id,
            provider_type="open_finance", provider_name="fake",
            institution_name="Fake Bank",
        )
        assert conn.id is not None
        assert conn.provider_type == "open_finance"
        assert conn.provider_name == "fake"
        assert conn.status.value == "active"
        assert conn.environment == "sandbox"

    @pytest.mark.asyncio
    async def test_list_connections(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = ProviderConnectionService(db_session)
        await service.create_connection(org.id, owner.id, "open_finance", "fake")
        await service.create_connection(org.id, owner.id, "pix", "fake")
        conns = await service.list_connections(org.id)
        assert len(conns) == 2

    @pytest.mark.asyncio
    async def test_no_cross_org(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        from app.models.organization import Organization
        from app.models.user import User
        other_user = User(name="Other", email="other@test.com", hashed_password="hashed", phone_number="+5511999999995")
        db_session.add(other_user)
        await db_session.flush()
        other_org = Organization(name="Other Org", slug="other-org", owner_user_id=other_user.id)
        db_session.add(other_org)
        await db_session.commit()

        service = ProviderConnectionService(db_session)
        await service.create_connection(org.id, owner.id, "open_finance", "fake")
        other_conns = await service.list_connections(other_org.id)
        assert len(other_conns) == 0

    @pytest.mark.asyncio
    async def test_deactivate_connection(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = ProviderConnectionService(db_session)
        conn = await service.create_connection(org.id, owner.id, "pix", "fake")
        deactivated = await service.deactivate_connection(org.id, conn.id, owner.id)
        assert deactivated.active is False
        assert deactivated.status.value == "inactive"

    @pytest.mark.asyncio
    async def test_block_real_provider_flag_false(self, db_session, org_with_members, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", False)
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")
        monkeypatch.setattr(settings, "ENABLE_OPEN_FINANCE", False)

        org, owner, *_ = org_with_members
        service = ProviderConnectionService(db_session)
        with pytest.raises(ValueError, match="feature flag"):
            await service.create_connection(org.id, owner.id, "open_finance", "pluggy")

    @pytest.mark.asyncio
    async def test_demo_mode_forces_fake(self, db_session, org_with_members, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", True)
        monkeypatch.setattr(settings, "ENABLE_OPEN_FINANCE", True)

        org, owner, *_ = org_with_members
        service = ProviderConnectionService(db_session)
        with pytest.raises(ValueError, match="Demo mode"):
            await service.create_connection(org.id, owner.id, "open_finance", "pluggy")

    @pytest.mark.asyncio
    async def test_production_rejects_real_provider(self, db_session, org_with_members, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", False)
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "ENABLE_OPEN_FINANCE", True)

        org, owner, *_ = org_with_members
        service = ProviderConnectionService(db_session)
        with pytest.raises(ValueError, match="not yet implemented"):
            await service.create_connection(org.id, owner.id, "open_finance", "pluggy")

    @pytest.mark.asyncio
    async def test_invalid_provider_type(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = ProviderConnectionService(db_session)
        with pytest.raises(ValueError, match="Invalid provider type"):
            await service.create_connection(org.id, owner.id, "invalid_type", "fake")


class TestOpenFinanceConsent:
    @pytest.mark.asyncio
    async def test_create_fake_consent(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = OpenFinanceConsentService(db_session)
        consent = await service.create_fake_consent(
            org.id, owner.id, institution_name="Fake Bank"
        )
        assert consent.id is not None
        assert consent.status.value == "authorized"
        assert consent.provider_name == "fake"
        assert consent.authorization_url is not None

    @pytest.mark.asyncio
    async def test_list_consents(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = OpenFinanceConsentService(db_session)
        await service.create_fake_consent(org.id, owner.id, institution_name="Bank A")
        await service.create_fake_consent(org.id, owner.id, institution_name="Bank B")
        consents = await service.list_consents(org.id)
        assert len(consents) == 2

    @pytest.mark.asyncio
    async def test_revoke_consent(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = OpenFinanceConsentService(db_session)
        consent = await service.create_fake_consent(org.id, owner.id)
        revoked = await service.revoke_consent(org.id, consent.id, owner.id)
        assert revoked.status.value == "revoked"
        assert revoked.revoked_at is not None

    @pytest.mark.asyncio
    async def test_consent_no_cross_org(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        from app.models.organization import Organization
        from app.models.user import User
        other_user = User(name="Other2", email="other2@test.com", hashed_password="hashed", phone_number="+5511999999996")
        db_session.add(other_user)
        await db_session.flush()
        other_org = Organization(name="Other Org 2", slug="other-org-2", owner_user_id=other_user.id)
        db_session.add(other_org)
        await db_session.commit()

        service = OpenFinanceConsentService(db_session)
        await service.create_fake_consent(org.id, owner.id)
        other_consents = await service.list_consents(other_org.id)
        assert len(other_consents) == 0

    @pytest.mark.asyncio
    async def test_audit_log_created_for_consent(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = OpenFinanceConsentService(db_session)
        await service.create_fake_consent(org.id, owner.id, institution_name="Test Bank")
        audit_service = OrganizationAuditService(db_session)
        logs, total = await audit_service.list_logs(org.id, action="consent_created")
        assert total >= 1


class TestProviderWebhook:
    @pytest.mark.asyncio
    async def test_record_event(self, db_session, org_with_members):
        org, *_ = org_with_members
        service = ProviderWebhookService(db_session)
        event = await service.record_event(
            organization_id=org.id,
            provider_type="pix", provider_name="fake",
            event_type="pix.received",
            provider_event_id="evt_001",
            payload={"amount": 100, "customer_name": "Test"},
        )
        assert event.id is not None
        assert event.status.value == "received"

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, db_session, org_with_members):
        org, *_ = org_with_members
        service = ProviderWebhookService(db_session)
        await service.record_event(
            org.id, "pix", "fake", "pix.received", "evt_dup_001",
            payload={"amount": 50},
        )
        dup = await service.record_event(
            org.id, "pix", "fake", "pix.received", "evt_dup_001",
            payload={"amount": 50},
        )
        assert dup.status.value == "duplicate"

    @pytest.mark.asyncio
    async def test_sanitize_payload(self):
        sanitized = ProviderWebhookService.sanitize_payload({
            "amount": 100,
            "api_key": "secret123",
            "token": "abc",
            "nested": {"password": "pass", "data": "ok"},
        })
        assert sanitized["amount"] == 100
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["token"] == "[REDACTED]"
        assert sanitized["nested"]["password"] == "[REDACTED]"
        assert sanitized["nested"]["data"] == "ok"

    @pytest.mark.asyncio
    async def test_sanitize_headers(self):
        sanitized = ProviderWebhookService.sanitize_headers({
            "Content-Type": "application/json",
            "Authorization": "Bearer secret",
            "X-API-Key": "key123",
        })
        assert sanitized["Content-Type"] == "application/json"
        assert sanitized["Authorization"] == "[REDACTED]"
        assert sanitized["X-API-Key"] == "[REDACTED]"

    @pytest.mark.asyncio
    async def test_mark_processed(self, db_session, org_with_members):
        org, *_ = org_with_members
        service = ProviderWebhookService(db_session)
        event = await service.record_event(
            org.id, "pix", "fake", "pix.received", "evt_proc_001",
        )
        processed = await service.mark_processed(event.id)
        assert processed.status.value == "processed"
        assert processed.processed_at is not None

    @pytest.mark.asyncio
    async def test_mark_failed(self, db_session, org_with_members):
        org, *_ = org_with_members
        service = ProviderWebhookService(db_session)
        event = await service.record_event(
            org.id, "pix", "fake", "pix.received", "evt_fail_001",
        )
        failed = await service.mark_failed(event.id, "Connection timeout")
        assert failed.status.value == "failed"
        assert failed.error_message == "Connection timeout"


class TestOrganizationAuditLog:
    @pytest.mark.asyncio
    async def test_log_event(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = OrganizationAuditService(db_session)
        log = await service.log_event(
            organization_id=org.id,
            action="test_action",
            actor_user_id=owner.id,
            metadata={"key": "value"},
        )
        assert log.id is not None
        assert log.action == "test_action"

    @pytest.mark.asyncio
    async def test_list_logs(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = OrganizationAuditService(db_session)
        await service.log_event(org.id, "action_1", actor_user_id=owner.id)
        await service.log_event(org.id, "action_2", actor_user_id=owner.id)
        logs, total = await service.list_logs(org.id)
        assert total >= 2
        assert len(logs) >= 2

    @pytest.mark.asyncio
    async def test_no_cross_org(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        from app.models.organization import Organization
        from app.models.user import User
        other_user = User(name="Other3", email="other3@test.com", hashed_password="hashed", phone_number="+5511999999997")
        db_session.add(other_user)
        await db_session.flush()
        other_org = Organization(name="Other Org 3", slug="other-org-3", owner_user_id=other_user.id)
        db_session.add(other_org)
        await db_session.commit()

        service = OrganizationAuditService(db_session)
        await service.log_event(org.id, "action", actor_user_id=owner.id)
        other_logs, other_total = await service.list_logs(other_org.id)
        assert other_total == 0

    @pytest.mark.asyncio
    async def test_metadata_sanitized(self):
        sanitized = OrganizationAuditService.sanitize_metadata({
            "data": "ok",
            "password": "secret",
            "api_key": "key",
        })
        assert sanitized["data"] == "ok"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"

    @pytest.mark.asyncio
    async def test_hash_value(self):
        h = OrganizationAuditService.hash_value("192.168.1.1")
        assert h is not None
        assert len(h) == 64
        assert h != "192.168.1.1"

    @pytest.mark.asyncio
    async def test_hash_value_none(self):
        assert OrganizationAuditService.hash_value(None) is None

    @pytest.mark.asyncio
    async def test_filter_by_action(self, db_session, org_with_members):
        org, owner, *_ = org_with_members
        service = OrganizationAuditService(db_session)
        await service.log_event(org.id, "specific_action", actor_user_id=owner.id)
        await service.log_event(org.id, "other_action", actor_user_id=owner.id)
        logs, total = await service.list_logs(org.id, action="specific_action")
        assert total == 1
        assert all(l.action == "specific_action" for l in logs)
