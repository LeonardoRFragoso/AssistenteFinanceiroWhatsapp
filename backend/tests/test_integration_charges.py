import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models import User, Charge, ChargeReminderLog, ChargeDeliveryLog
from app.models.charge import ChargeStatus
from app.models.transaction import Transaction
from app.models.reminder import Reminder
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.conversation_log import ConversationLog
from app.models.provider_event import ProviderEvent
from app.models.pending_action import PendingAction
from app.main import app
from app.providers.provider_factory import get_payment_provider
from decimal import Decimal
from datetime import date, timedelta
import app.providers.provider_factory as factory_module


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
    await test_session.commit()

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
    await test_session.commit()

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


@pytest.fixture
def fake_provider():
    factory_module._PAYMENT_PROVIDER = None
    return get_payment_provider("fake")


class TestChargesAuth:
    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, client):
        resp = await client.get("/charges")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, client):
        resp = await client.get("/charges", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401


class TestChargesList:
    @pytest.mark.asyncio
    async def test_list_charges_empty(self, client, auth_headers):
        resp = await client.get("/charges", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 0

    @pytest.mark.asyncio
    async def test_list_charges_with_data(self, client, auth_headers, authed_user, test_session):
        charge = Charge(
            user_id=authed_user.id,
            customer_name="Cliente Test",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_123",
            payment_link="http://example.com/pay",
            status=ChargeStatus.PENDING
        )
        test_session.add(charge)
        await test_session.commit()

        resp = await client.get("/charges", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["customer_name"] == "Cliente Test"

    @pytest.mark.asyncio
    async def test_pagination(self, client, auth_headers, authed_user, test_session):
        for i in range(25):
            test_session.add(Charge(
                user_id=authed_user.id,
                customer_name=f"Cliente {i}",
                amount=Decimal("50.00"),
                provider="fake",
                provider_charge_id=f"fake_{i}",
                payment_link=f"http://example.com/pay/{i}",
                status=ChargeStatus.PENDING
            ))
        await test_session.commit()

        resp = await client.get("/charges?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 10
        assert data["total"] == 25
        assert data["total_pages"] == 3

        resp2 = await client.get("/charges?page=2&page_size=10", headers=auth_headers)
        data2 = resp2.json()
        assert len(data2["items"]) == 10
        assert data2["page"] == 2

        resp3 = await client.get("/charges?page=3&page_size=10", headers=auth_headers)
        data3 = resp3.json()
        assert len(data3["items"]) == 5

    @pytest.mark.asyncio
    async def test_search(self, client, auth_headers, authed_user, test_session):
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="João Silva",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_a",
            payment_link="http://a",
            status=ChargeStatus.PENDING,
            description="Serviço de design"
        ))
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="Maria Santos",
            amount=Decimal("200.00"),
            provider="fake",
            provider_charge_id="fake_b",
            payment_link="http://b",
            status=ChargeStatus.PENDING,
            description="Consultoria"
        ))
        await test_session.commit()

        resp = await client.get("/charges?search=João", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["customer_name"] == "João Silva"

        resp2 = await client.get("/charges?search=design", headers=auth_headers)
        data2 = resp2.json()
        assert data2["total"] == 1
        assert data2["items"][0]["description"] == "Serviço de design"

    @pytest.mark.asyncio
    async def test_status_filter(self, client, auth_headers, authed_user, test_session):
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="Pendente",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_p",
            payment_link="http://p",
            status=ChargeStatus.PENDING
        ))
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="Paga",
            amount=Decimal("200.00"),
            provider="fake",
            provider_charge_id="fake_paid",
            payment_link="http://paid",
            status=ChargeStatus.PAID
        ))
        await test_session.commit()

        resp = await client.get("/charges?status=paid", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["customer_name"] == "Paga"

    @pytest.mark.asyncio
    async def test_user_isolation(self, client, auth_headers, other_headers, authed_user, other_user, test_session):
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="My Charge",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_mine",
            payment_link="http://mine",
            status=ChargeStatus.PENDING
        ))
        test_session.add(Charge(
            user_id=other_user.id,
            customer_name="Other Charge",
            amount=Decimal("200.00"),
            provider="fake",
            provider_charge_id="fake_other",
            payment_link="http://other",
            status=ChargeStatus.PENDING
        ))
        await test_session.commit()

        resp = await client.get("/charges", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["customer_name"] == "My Charge"

        resp2 = await client.get("/charges", headers=other_headers)
        data2 = resp2.json()
        assert data2["total"] == 1
        assert data2["items"][0]["customer_name"] == "Other Charge"


class TestChargesSummary:
    @pytest.mark.asyncio
    async def test_summary(self, client, auth_headers, authed_user, test_session):
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="Paga",
            amount=Decimal("200.00"),
            provider="fake",
            provider_charge_id="fake_s1",
            payment_link="http://s1",
            status=ChargeStatus.PAID
        ))
        await test_session.commit()

        resp = await client.get("/charges/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["total_paid"]) == 200.0
        assert data["count_paid"] == 1


class TestChargesAnalytics:
    @pytest.mark.asyncio
    async def test_analytics_empty(self, client, auth_headers):
        resp = await client.get("/charges/analytics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_created"] == 0
        assert data["conversion_rate"] == 0
        assert data["average_payment_time_hours"] == 0

    @pytest.mark.asyncio
    async def test_analytics_with_data(self, client, auth_headers, authed_user, test_session):
        from datetime import datetime, timezone, timedelta as td
        created = datetime.now(timezone.utc) - td(days=2)
        paid = datetime.now(timezone.utc)

        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="Paid Charge",
            amount=Decimal("150.00"),
            provider="fake",
            provider_charge_id="fake_an1",
            payment_link="http://an1",
            status=ChargeStatus.PAID,
            created_at=created,
            paid_at=paid
        ))
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="Pending Charge",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_an2",
            payment_link="http://an2",
            status=ChargeStatus.PENDING
        ))
        await test_session.commit()

        resp = await client.get("/charges/analytics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_created"] == 2
        assert data["total_paid"] == 1
        assert data["conversion_rate"] == 50.0
        assert data["average_payment_time_hours"] > 0
        assert float(data["total_amount_paid"]) == 150.0


class TestChargesExport:
    @pytest.mark.asyncio
    async def test_export_csv(self, client, auth_headers, authed_user, test_session):
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="CSV Test",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_csv",
            payment_link="http://csv",
            status=ChargeStatus.PENDING
        ))
        await test_session.commit()

        resp = await client.get("/charges/export.csv", headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        content = resp.text
        assert "customer_name" in content
        assert "CSV Test" in content

    @pytest.mark.asyncio
    async def test_export_csv_no_auth(self, client):
        resp = await client.get("/charges/export.csv")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_export_pdf(self, client, auth_headers, authed_user, test_session):
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="PDF Test",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_pdf",
            payment_link="http://pdf",
            status=ChargeStatus.PENDING
        ))
        await test_session.commit()

        resp = await client.get("/charges/export.pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        assert resp.headers.get("content-disposition", "").startswith("attachment; filename=")

    @pytest.mark.asyncio
    async def test_export_pdf_no_auth(self, client):
        resp = await client.get("/charges/export.pdf")
        assert resp.status_code in (401, 403)


class TestChargesCreate:
    @pytest.mark.asyncio
    async def test_create_charge(self, client, auth_headers):
        resp = await client.post("/charges", headers=auth_headers, json={
            "customer_name": "Novo Cliente",
            "amount": "99.90",
            "description": "Test charge",
            "provider": "fake"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["customer_name"] == "Novo Cliente"
        assert float(data["amount"]) == 99.90
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_charge_no_auth(self, client):
        resp = await client.post("/charges", json={
            "customer_name": "Novo Cliente",
            "amount": "99.90"
        })
        assert resp.status_code in (401, 403)


class TestChargesCancel:
    @pytest.mark.asyncio
    async def test_cancel_pending(self, client, auth_headers, authed_user, test_session):
        charge = Charge(
            user_id=authed_user.id,
            customer_name="Cancel Me",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_cancel",
            payment_link="http://cancel",
            status=ChargeStatus.PENDING
        )
        test_session.add(charge)
        await test_session.commit()
        await test_session.refresh(charge)

        resp = await client.post(f"/charges/{charge.id}/cancel", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_paid_fails(self, client, auth_headers, authed_user, test_session):
        charge = Charge(
            user_id=authed_user.id,
            customer_name="Already Paid",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_paid_cancel",
            payment_link="http://paid_cancel",
            status=ChargeStatus.PAID
        )
        test_session.add(charge)
        await test_session.commit()
        await test_session.refresh(charge)

        resp = await client.post(f"/charges/{charge.id}/cancel", headers=auth_headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cancel_other_user_charge(self, client, auth_headers, other_user, test_session):
        charge = Charge(
            user_id=other_user.id,
            customer_name="Other User Charge",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_other_cancel",
            payment_link="http://other_cancel",
            status=ChargeStatus.PENDING
        )
        test_session.add(charge)
        await test_session.commit()
        await test_session.refresh(charge)

        resp = await client.post(f"/charges/{charge.id}/cancel", headers=auth_headers)
        assert resp.status_code == 400


class TestFakeWebhook:
    @pytest.mark.asyncio
    async def test_simulate_payment(self, client, authed_user, test_session):
        charge = Charge(
            user_id=authed_user.id,
            customer_name="Pay Me",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_wh_123",
            payment_link="http://wh",
            status=ChargeStatus.PENDING
        )
        test_session.add(charge)
        await test_session.commit()

        resp = await client.post("/provider-webhooks/fake/pay/fake_wh_123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "simulated"

        await test_session.refresh(charge)
        assert charge.status == ChargeStatus.PAID

    @pytest.mark.asyncio
    async def test_simulate_payment_not_found(self, client):
        resp = await client.post("/provider-webhooks/fake/pay/nonexistent")
        assert resp.status_code == 404
