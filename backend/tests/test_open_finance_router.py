"""
Tests for Open Finance router — Sprint 16.

Tests RBAC enforcement, endpoint responses, and data isolation.
Follows the same pattern as test_integration_charges.py.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime, timezone, date
from decimal import Decimal

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models import User, Charge, ChargeReminderLog, ChargeDeliveryLog
from app.models.transaction import Transaction
from app.models.reminder import Reminder
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.conversation_log import ConversationLog
from app.models.provider_event import ProviderEvent
from app.models.pending_action import PendingAction
from app.models.customer import Customer
from app.models.message_template import MessageTemplate
from app.models.collection_rule import CollectionRule
from app.models.collection_message_log import CollectionMessageLog
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.recurring_task import RecurringTask, RecurringTaskLog
from app.models.billing import SubscriptionPlan, OrganizationSubscription, UsageCounter, BillingEvent, SubscriptionStatus, BillingProvider
from app.models.provider_foundation import (
    ProviderConnection, ProviderWebhookEvent, OpenFinanceConsent,
    OrganizationAuditLog, TransactionAuthorization,
)
from app.models.open_finance import (
    ConnectedAccount, BankTransaction, FinancialCategory, OpenFinanceSyncLog,
)
from app.services.open_finance_service import OpenFinanceService


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)
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

    sub = Subscription(
        user_id=user.id,
        plan="free",
        status="active"
    )
    test_session.add(sub)

    org = Organization(
        name="Test Org",
        slug=f"test-org-{user.id}",
        owner_user_id=user.id,
    )
    test_session.add(org)
    await test_session.flush()
    test_session.add(OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=OrganizationRole.OWNER,
        active=True,
        joined_at=datetime.now(timezone.utc),
    ))
    await test_session.commit()

    from app.services.saas_billing_service import SaaSBillingService
    billing = SaaSBillingService(test_session)
    await billing.seed_plans()
    await billing.ensure_free_subscription(org.id)
    try:
        await billing.change_plan(org.id, "professional")
    except Exception:
        pass

    user._org_id = org.id
    return user


@pytest_asyncio.fixture
async def other_user(test_session):
    user = User(
        name="Other User",
        email="other@example.com",
        hashed_password="$2b$12$otherhash",
        phone_number="+5511888888888"
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    sub = Subscription(
        user_id=user.id,
        plan="free",
        status="active"
    )
    test_session.add(sub)

    org = Organization(
        name="Other Org",
        slug=f"other-org-{user.id}",
        owner_user_id=user.id,
    )
    test_session.add(org)
    await test_session.flush()
    test_session.add(OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=OrganizationRole.OWNER,
        active=True,
        joined_at=datetime.now(timezone.utc),
    ))
    await test_session.commit()

    from app.services.saas_billing_service import SaaSBillingService
    billing = SaaSBillingService(test_session)
    await billing.seed_plans()
    await billing.ensure_free_subscription(org.id)
    try:
        await billing.change_plan(org.id, "professional")
    except Exception:
        pass

    user._org_id = org.id
    return user


@pytest_asyncio.fixture
async def auth_token(authed_user):
    return create_access_token(data={"sub": str(authed_user.id)})


@pytest_asyncio.fixture
async def other_token(other_user):
    return create_access_token(data={"sub": str(other_user.id)})


@pytest_asyncio.fixture
async def client(test_session, test_engine):
    async def override_get_db():
        yield test_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def other_headers(other_token):
    return {"Authorization": f"Bearer {other_token}"}


@pytest.mark.asyncio
async def test_of_status_endpoint(client, auth_headers, authed_user):
    """Test the /open-finance/status endpoint."""
    response = await client.get(
        "/open-finance/status",
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "provider" in data
    assert "demo_mode" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_of_create_fake_consent(client, auth_headers, authed_user, test_session):
    """Test creating a fake consent via the API."""
    response = await client.post(
        "/open-finance/consents/fake",
        json={"institution_id": "fake_bank"},
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["provider_name"] == "fake"
    assert data["status"] == "authorized"


@pytest.mark.asyncio
async def test_of_list_consents(client, auth_headers, authed_user, test_session):
    """Test listing consents via the API."""
    service = OpenFinanceService(test_session)
    await service.create_fake_consent(authed_user._org_id, authed_user.id)

    response = await client.get(
        "/open-finance/consents",
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_of_sync_fake(client, auth_headers, authed_user, test_session):
    """Test the sync fake endpoint."""
    service = OpenFinanceService(test_session)
    consent = await service.create_fake_consent(authed_user._org_id, authed_user.id)

    response = await client.post(
        f"/open-finance/sync/fake?consent_id={consent.id}",
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["is_demo_data"] is True
    assert data["accounts_synced"] == 2
    assert data["transactions_synced"] > 0


@pytest.mark.asyncio
async def test_of_list_transactions(client, auth_headers, authed_user, test_session):
    """Test listing transactions via the API."""
    service = OpenFinanceService(test_session)
    consent = await service.create_fake_consent(authed_user._org_id, authed_user.id)
    await service.sync_fake_accounts(authed_user._org_id, authed_user.id, consent.id)
    await service.sync_fake_transactions(authed_user._org_id, authed_user.id)

    response = await client.get(
        "/open-finance/transactions?limit=5",
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
    for tx in data:
        assert tx["is_demo_data"] is True


@pytest.mark.asyncio
async def test_of_transactions_summary(client, auth_headers, authed_user, test_session):
    """Test the transactions summary endpoint."""
    service = OpenFinanceService(test_session)
    consent = await service.create_fake_consent(authed_user._org_id, authed_user.id)
    await service.sync_fake_accounts(authed_user._org_id, authed_user.id, consent.id)
    await service.sync_fake_transactions(authed_user._org_id, authed_user.id)

    now = date.today()
    response = await client.get(
        f"/open-finance/transactions/summary?year={now.year}&month={now.month}",
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "income_total" in data
    assert "expense_total" in data
    assert "is_demo_data" in data


@pytest.mark.asyncio
async def test_of_sync_logs(client, auth_headers, authed_user, test_session):
    """Test listing sync logs via the API."""
    service = OpenFinanceService(test_session)
    consent = await service.create_fake_consent(authed_user._org_id, authed_user.id)
    await service.sync_fake_accounts(authed_user._org_id, authed_user.id, consent.id)

    response = await client.get(
        "/open-finance/sync-logs",
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_of_data_isolation(client, auth_headers, other_headers, authed_user, other_user, test_session):
    """Test that org1 cannot see org2's data."""
    service = OpenFinanceService(test_session)
    consent = await service.create_fake_consent(authed_user._org_id, authed_user.id)
    await service.sync_fake_accounts(authed_user._org_id, authed_user.id, consent.id)
    await service.sync_fake_transactions(authed_user._org_id, authed_user.id)

    response = await client.get(
        "/open-finance/transactions",
        headers={**other_headers, "X-Organization-ID": str(other_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Org2 has no transactions


@pytest.mark.asyncio
async def test_of_category_breakdown(client, auth_headers, authed_user, test_session):
    """Test category breakdown endpoint."""
    service = OpenFinanceService(test_session)
    consent = await service.create_fake_consent(authed_user._org_id, authed_user.id)
    await service.sync_fake_accounts(authed_user._org_id, authed_user.id, consent.id)
    await service.sync_fake_transactions(authed_user._org_id, authed_user.id)

    response = await client.get(
        "/open-finance/transactions/categories",
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_of_merchant_breakdown(client, auth_headers, authed_user, test_session):
    """Test merchant breakdown endpoint."""
    service = OpenFinanceService(test_session)
    consent = await service.create_fake_consent(authed_user._org_id, authed_user.id)
    await service.sync_fake_accounts(authed_user._org_id, authed_user.id, consent.id)
    await service.sync_fake_transactions(authed_user._org_id, authed_user.id)

    response = await client.get(
        "/open-finance/transactions/merchants",
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_of_revoke_consent(client, auth_headers, authed_user, test_session):
    """Test revoking a consent via the API."""
    service = OpenFinanceService(test_session)
    consent = await service.create_fake_consent(authed_user._org_id, authed_user.id)

    response = await client.post(
        f"/open-finance/consents/{consent.id}/revoke",
        headers={**auth_headers, "X-Organization-ID": str(authed_user._org_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "revoked"
