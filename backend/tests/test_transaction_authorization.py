"""
Tests for transaction authorization service — Sprint 14.

Validates:
- Code is hashed (not stored in plaintext)
- Correct code confirms
- Wrong code is rejected
- Max attempts enforced
- Expiry enforced
- No cross-org access
- Audit log created
- Production does not return code
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.transaction_authorization_service import TransactionAuthorizationService
from app.services.organization_audit_service import OrganizationAuditService
from app.models.provider_foundation import TransactionAuthorization, AuthorizationStatus


@pytest.fixture
async def org_with_users(db_session):
    from app.models.organization import Organization, OrganizationMember, OrganizationRole
    from app.models.user import User
    from app.models.billing import OrganizationSubscription, SubscriptionPlan, SubscriptionStatus, BillingProvider

    owner = User(name="Owner", email="txauth_owner@test.com", hashed_password="hashed", phone_number="+5511999999911")
    db_session.add(owner)
    await db_session.flush()

    org = Organization(name="TxAuth Org", slug="txauth-org", owner_user_id=owner.id)
    db_session.add(org)
    await db_session.flush()

    db_session.add(OrganizationMember(organization_id=org.id, user_id=owner.id, role=OrganizationRole.OWNER))

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
    return org, owner


class TestTransactionAuthorization:
    @pytest.mark.asyncio
    async def test_create_authorization(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, code = await service.create_authorization(
            organization_id=org.id, user_id=owner.id,
            action_type="bill_payment", amount=150.00,
        )
        assert auth.id is not None
        assert auth.status.value == "pending"
        assert auth.code_hash is not None
        assert code is not None  # testing env returns code
        assert len(code) == 6

    @pytest.mark.asyncio
    async def test_code_not_stored_plaintext(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, code = await service.create_authorization(
            org.id, owner.id, "bill_payment"
        )
        assert auth.code_hash != code
        assert len(auth.code_hash) == 64  # sha256 hex

    @pytest.mark.asyncio
    async def test_confirm_with_correct_code(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, code = await service.create_authorization(org.id, owner.id, "pix_out")
        confirmed = await service.confirm_authorization(org.id, auth.id, owner.id, code)
        assert confirmed.status.value == "confirmed"
        assert confirmed.confirmed_at is not None

    @pytest.mark.asyncio
    async def test_reject_wrong_code(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, _ = await service.create_authorization(org.id, owner.id, "pix_out")
        with pytest.raises(ValueError, match="Invalid authorization code"):
            await service.confirm_authorization(org.id, auth.id, owner.id, "000000")

    @pytest.mark.asyncio
    async def test_max_attempts(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, _ = await service.create_authorization(org.id, owner.id, "pix_out")
        for i in range(3):
            try:
                await service.confirm_authorization(org.id, auth.id, owner.id, "000000")
            except ValueError:
                pass
        with pytest.raises(ValueError, match="Maximum attempts"):
            await service.confirm_authorization(org.id, auth.id, owner.id, "000000")

    @pytest.mark.asyncio
    async def test_expired_authorization(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, code = await service.create_authorization(org.id, owner.id, "bill_payment")
        auth.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db_session.commit()
        with pytest.raises(ValueError, match="expired"):
            await service.confirm_authorization(org.id, auth.id, owner.id, code)

    @pytest.mark.asyncio
    async def test_cancel_authorization(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, _ = await service.create_authorization(org.id, owner.id, "pix_out")
        cancelled = await service.cancel_authorization(org.id, auth.id, owner.id)
        assert cancelled.status.value == "cancelled"

    @pytest.mark.asyncio
    async def test_no_cross_org(self, db_session, org_with_users):
        org, owner = org_with_users
        from app.models.organization import Organization
        from app.models.user import User
        other_user = User(name="Other", email="txauth_other@test.com", hashed_password="hashed", phone_number="+5511999999912")
        db_session.add(other_user)
        await db_session.flush()
        other_org = Organization(name="Other TxAuth", slug="other-txauth", owner_user_id=other_user.id)
        db_session.add(other_org)
        await db_session.commit()

        service = TransactionAuthorizationService(db_session)
        auth, code = await service.create_authorization(org.id, owner.id, "pix_out")
        with pytest.raises(ValueError, match="not found"):
            await service.confirm_authorization(other_org.id, auth.id, other_user.id, code)

    @pytest.mark.asyncio
    async def test_audit_log_created(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        await service.create_authorization(org.id, owner.id, "bill_payment")
        audit_service = OrganizationAuditService(db_session)
        logs, total = await audit_service.list_logs(org.id, action="transaction_auth_created")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_audit_log_confirmed(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, code = await service.create_authorization(org.id, owner.id, "bill_payment")
        await service.confirm_authorization(org.id, auth.id, owner.id, code)
        audit_service = OrganizationAuditService(db_session)
        logs, total = await audit_service.list_logs(org.id, action="transaction_auth_confirmed")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_production_no_code_returned(self, db_session, org_with_users, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, code = await service.create_authorization(org.id, owner.id, "bill_payment")
        assert code is None  # production does not return code

    @pytest.mark.asyncio
    async def test_expire_old_authorizations(self, db_session, org_with_users):
        org, owner = org_with_users
        service = TransactionAuthorizationService(db_session)
        auth, _ = await service.create_authorization(org.id, owner.id, "bill_payment")
        auth.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db_session.commit()
        count = await service.expire_old_authorizations()
        assert count >= 1
