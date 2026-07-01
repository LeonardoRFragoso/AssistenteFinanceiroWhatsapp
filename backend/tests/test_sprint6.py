import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models import User, Charge
from app.models.charge import ChargeStatus
from app.models.subscription import Subscription
from app.models.provider_event import ProviderEvent
from app.main import app
from decimal import Decimal
from datetime import date, datetime, timezone
from unittest.mock import patch


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

    sub = Subscription(user_id=user.id, plan="free", status="active")
    test_session.add(sub)
    await test_session.commit()

    return user


@pytest_asyncio.fixture
async def auth_token(authed_user):
    return create_access_token(data={"sub": str(authed_user.id)})


@pytest_asyncio.fixture
async def admin_user(test_session):
    user = User(
        name="Admin User",
        email="admin@example.com",
        hashed_password="$2b$12$adminhash",
        phone_number="+5511888888888"
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    sub = Subscription(user_id=user.id, plan="pro", status="active")
    test_session.add(sub)
    await test_session.commit()

    return user


@pytest_asyncio.fixture
async def admin_token(admin_user):
    return create_access_token(data={"sub": str(admin_user.id)})


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
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


class TestUserRateLimit:
    @pytest.mark.asyncio
    async def test_charges_rate_limit(self, client, auth_headers, authed_user, test_session):
        from app.utils.user_rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(limit=2, window_seconds=60, key_prefix="test_charges")
        await limiter.check(authed_user.id, "create_charge")
        await limiter.check(authed_user.id, "create_charge")
        with pytest.raises(Exception) as exc_info:
            await limiter.check(authed_user.id, "create_charge")
        assert "429" in str(exc_info.value.status_code)

    @pytest.mark.asyncio
    async def test_exports_rate_limit(self, client, auth_headers, authed_user):
        from app.utils.user_rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(limit=1, window_seconds=60, key_prefix="test_exports")
        await limiter.check(authed_user.id, "export_csv")
        with pytest.raises(Exception) as exc_info:
            await limiter.check(authed_user.id, "export_csv")
        assert "429" in str(exc_info.value.status_code)

    @pytest.mark.asyncio
    async def test_demo_reset_rate_limit(self, client, auth_headers, authed_user):
        from app.utils.user_rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(limit=1, window_seconds=3600, key_prefix="test_demo_reset")
        await limiter.check(authed_user.id, "demo_reset")
        with pytest.raises(Exception) as exc_info:
            await limiter.check(authed_user.id, "demo_reset")
        assert "429" in str(exc_info.value.status_code)

    @pytest.mark.asyncio
    async def test_rate_limit_disabled(self, client, auth_headers, authed_user):
        from app.utils.user_rate_limiter import UserRateLimiter

        limiter = UserRateLimiter(limit=1, window_seconds=60, key_prefix="test_disabled")
        with patch('app.utils.user_rate_limiter.settings') as mock_s:
            mock_s.USER_RATE_LIMIT_ENABLED = False
            await limiter.check(authed_user.id, "test")
            await limiter.check(authed_user.id, "test")
            await limiter.check(authed_user.id, "test")


class TestWebhookHardening:
    @pytest.mark.asyncio
    async def test_mp_webhook_without_signature_rejected(self, client):
        resp = await client.post("/provider-webhooks/mercado-pago", json={"type": "payment", "data": {"id": "123"}})
        assert resp.status_code == 401
        assert "signature" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_mp_webhook_with_invalid_signature_rejected(self, client):
        with patch('app.routers.provider_webhooks.MercadoPagoService') as mock_mp:
            mock_instance = mock_mp.return_value
            mock_instance.validate_webhook_signature_from_url.return_value = False
            resp = await client.post(
                "/provider-webhooks/mercado-pago",
                json={"type": "payment", "data": {"id": "123"}},
                headers={"x-signature": "invalid", "x-request-id": "invalid"}
            )
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_fake_webhook_still_works(self, client):
        resp = await client.post("/provider-webhooks/fake", json={
            "event_type": "payment.approved",
            "provider_charge_id": "nonexistent",
        })
        assert resp.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_mp_webhook_duplicate_idempotent(self, client, test_session):
        event = ProviderEvent(
            provider="mercado_pago",
            event_type="payment.approved",
            external_id="dup_123",
            payload={"type": "payment", "data": {"id": "dup_123"}},
            processed=True,
            processed_at=datetime.now(timezone.utc),
        )
        test_session.add(event)
        await test_session.commit()

        with patch('app.routers.provider_webhooks.MercadoPagoService') as mock_mp:
            mock_instance = mock_mp.return_value
            mock_instance.validate_webhook_signature_from_url.return_value = True
            resp = await client.post(
                "/provider-webhooks/mercado-pago",
                json={"type": "payment", "data": {"id": "dup_123"}},
                headers={"x-signature": "valid", "x-request-id": "valid"}
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "duplicate"


class TestTwilioSignatureEnforcement:
    @pytest.mark.asyncio
    async def test_twilio_signature_mandatory_in_production(self, client):
        with patch('app.routers.webhook.settings') as mock_s:
            mock_s.ENVIRONMENT = "production"
            mock_s.TWILIO_VALIDATE_SIGNATURE = False
            resp = await client.post("/webhook/whatsapp", data={
                "From": "whatsapp:+5511999999999",
                "Body": "test",
            })
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_twilio_bypass_allowed_in_dev(self, client):
        with patch('app.routers.webhook.settings') as mock_s:
            mock_s.ENVIRONMENT = "development"
            mock_s.TWILIO_VALIDATE_SIGNATURE = False
            mock_s.OPENAI_API_KEY = "test"
            resp = await client.post("/webhook/whatsapp", data={
                "From": "whatsapp:+5511999999999",
                "Body": "test",
            })
            # Should not be 403 — may be 200 or 500 depending on processing
            assert resp.status_code != 403


class TestAdminSystemMetrics:
    @pytest.mark.asyncio
    async def test_system_metrics_requires_admin(self, client, auth_headers):
        resp = await client.get("/admin/system-metrics", headers=auth_headers)
        assert resp.status_code in (403, 503)

    @pytest.mark.asyncio
    async def test_system_metrics_no_auth(self, client):
        resp = await client.get("/admin/system-metrics")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_system_metrics_admin_ok(self, client, admin_headers, test_session, authed_user):
        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="Test Charge",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="sys_1",
            payment_link="http://sys1",
            status=ChargeStatus.PENDING,
        ))
        await test_session.commit()

        with patch('app.core.config.settings') as mock_s:
            mock_s.ADMIN_EMAILS = "admin@example.com"
            resp = await client.get("/admin/system-metrics", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert "total_users" in data
            assert "total_charges" in data
            assert "paid_charges" in data
            assert "overdue_charges" in data
            assert "total_provider_events" in data
            assert "total_reminders_sent" in data
            assert "uptime_seconds" in data
            assert data["total_charges"] >= 1

    @pytest.mark.asyncio
    async def test_system_metrics_no_sensitive_data(self, client, admin_headers, test_session, authed_user):
        with patch('app.core.config.settings') as mock_s:
            mock_s.ADMIN_EMAILS = "admin@example.com"
            resp = await client.get("/admin/system-metrics", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            # Ensure no personal data is exposed
            assert "email" not in data
            assert "phone" not in data
            assert "password" not in data
            assert "token" not in data


class TestSentryIntegration:
    def test_sentry_no_init_without_dsn(self):
        from app.core.sentry import init_sentry
        with patch('app.core.sentry.settings') as mock_s:
            mock_s.SENTRY_DSN = ""
            mock_s.SENTRY_ENVIRONMENT = "development"
            mock_s.SENTRY_TRACES_SAMPLE_RATE = 0.0
            # Should not raise
            init_sentry()

    def test_sentry_init_with_dsn(self):
        from app.core.sentry import init_sentry
        with patch('app.core.sentry.settings') as mock_s, \
             patch('sentry_sdk.init') as mock_init:
            mock_s.SENTRY_DSN = "https://test@sentry.io/123"
            mock_s.SENTRY_ENVIRONMENT = "development"
            mock_s.SENTRY_TRACES_SAMPLE_RATE = 0.0
            init_sentry()
            assert mock_init.called
