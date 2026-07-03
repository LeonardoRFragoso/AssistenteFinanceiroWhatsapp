"""
Tests for bill router — Sprint 17.
"""
import pytest
import pytest_asyncio
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models.user import User
from app.models.subscription import Subscription
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.bills import DetectedBill, BillStatus, BillSource, BillType, BillRiskLevel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


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
        name="Bill Test User",
        email="billtest@example.com",
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
        name="Bill Test Org",
        slug=f"bill-test-org-{user.id}",
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
async def test_bills(test_session, authed_user):
    today = date.today()
    bills = []
    for i, (offset, status, amount, name) in enumerate([
        (-5, BillStatus.OVERDUE, Decimal("200.00"), "Light Energia"),
        (0, BillStatus.DUE_TODAY, Decimal("150.00"), "Vivo Empresas"),
        (7, BillStatus.PENDING, Decimal("89.90"), "Claro"),
    ]):
        bill = DetectedBill(
            organization_id=authed_user._org_id,
            user_id=authed_user.id,
            provider_name="fake",
            provider_bill_id=f"router_test_{i}",
            source=BillSource.FAKE_DDA,
            title=f"{name} — Test",
            beneficiary_name=name,
            amount=amount,
            currency="BRL",
            due_date=today + timedelta(days=offset),
            bill_type=BillType.UTILITY,
            category="Test",
            status=status,
            risk_level=BillRiskLevel.LOW,
            is_demo_data=True,
        )
        test_session.add(bill)
        bills.append(bill)
    await test_session.commit()
    for b in bills:
        await test_session.refresh(b)
    return bills


@pytest_asyncio.fixture
async def client(test_session, auth_token, authed_user):
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {auth_token}"
        c.headers["X-Organization-ID"] = str(authed_user._org_id)
        yield c
    app.dependency_overrides.clear()


async def test_bills_status(client):
    res = await client.get("/bills/status")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "fake"
    assert data["demo_mode"] is True
    assert "fake" in data["message"].lower() or "demo" in data["message"].lower()


async def test_list_bills(client, test_bills):
    res = await client.get("/bills")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3


async def test_list_bills_filter_status(client, test_bills):
    res = await client.get("/bills?status=overdue")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["status"] == "overdue"


async def test_get_bill(client, test_bills):
    res = await client.get(f"/bills/{test_bills[0].id}")
    assert res.status_code == 200
    assert res.json()["id"] == test_bills[0].id


async def test_get_bill_not_found(client):
    res = await client.get("/bills/9999")
    assert res.status_code == 404


async def test_bills_summary(client, test_bills):
    res = await client.get("/bills/summary")
    assert res.status_code == 200
    data = res.json()
    assert "overdue_total" in data
    assert "open_total" in data
    assert data["is_demo_data"] is True


async def test_due_today(client, test_bills):
    res = await client.get("/bills/due-today")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1


async def test_overdue(client, test_bills):
    res = await client.get("/bills/overdue")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1


async def test_upcoming(client, test_bills):
    res = await client.get("/bills/upcoming?days=7")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1


async def test_ignore_bill(client, test_bills):
    res = await client.post(f"/bills/{test_bills[2].id}/ignore")
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"


async def test_mark_paid_manual(client, test_bills):
    res = await client.post(f"/bills/{test_bills[2].id}/mark-paid-manual")
    assert res.status_code == 200
    assert res.json()["status"] == "paid_manual"


async def test_create_reminder(client, test_bills):
    res = await client.post(
        f"/bills/{test_bills[0].id}/reminders",
        json={"reminder_date": "2025-12-31", "channel": "whatsapp"},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "scheduled"


async def test_list_reminders(client, test_bills):
    await client.post(
        f"/bills/{test_bills[0].id}/reminders",
        json={"reminder_date": "2025-12-31", "channel": "whatsapp"},
    )
    res = await client.get(f"/bills/{test_bills[0].id}/reminders")
    assert res.status_code == 200
    assert len(res.json()) >= 1


async def test_cancel_reminder(client, test_bills):
    create_res = await client.post(
        f"/bills/{test_bills[0].id}/reminders",
        json={"reminder_date": "2025-12-31", "channel": "whatsapp"},
    )
    reminder_id = create_res.json()["id"]
    res = await client.post(f"/bills/reminders/{reminder_id}/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


async def test_create_fake_payment_intent(client, test_bills):
    res = await client.post(f"/bills/{test_bills[0].id}/payment-intents/fake")
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "draft"
    assert data["fake_payment_reference"] is not None
    assert "FAKE" in data["fake_payment_reference"]


async def test_authorize_fake_intent(client, test_bills):
    create_res = await client.post(f"/bills/{test_bills[0].id}/payment-intents/fake")
    intent_id = create_res.json()["id"]
    res = await client.post(
        f"/bills/payment-intents/{intent_id}/authorize-fake",
        json={"authorization_code": "123456"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "authorized_fake"


async def test_cancel_payment_intent(client, test_bills):
    create_res = await client.post(f"/bills/{test_bills[0].id}/payment-intents/fake")
    intent_id = create_res.json()["id"]
    res = await client.post(f"/bills/payment-intents/{intent_id}/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


async def test_get_bill_events(client, test_bills):
    await client.post(f"/bills/{test_bills[0].id}/ignore")
    res = await client.get(f"/bills/{test_bills[0].id}/events")
    assert res.status_code == 200
    assert len(res.json()) >= 1


async def test_sync_fake_bills(client):
    res = await client.post("/bills/sync/fake")
    assert res.status_code == 200
    data = res.json()
    assert data["created"] >= 8
    assert data["created"] <= 15
