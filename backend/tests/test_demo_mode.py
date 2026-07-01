import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models import User, Charge
from app.models.charge import ChargeStatus
from app.models.subscription import Subscription
from app.main import app
from decimal import Decimal
from datetime import date, timedelta
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


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]

    @pytest.mark.asyncio
    async def test_ready(self, client):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_live(self, client):
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "PayFlow AI API"
        assert "health" in data
        assert "ready" in data


class TestDemoLogin:
    @pytest.mark.asyncio
    async def test_demo_login_disabled_by_default(self, client):
        resp = await client.post("/auth/demo-login")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_demo_login_when_enabled(self, client, test_session):
        from app.core.config import settings
        from app.core.security import get_password_hash

        demo_user = User(
            name="Demo User",
            email=settings.DEMO_USER_EMAIL,
            hashed_password=get_password_hash(settings.DEMO_USER_PASSWORD),
            phone_number="+15555555555",
        )
        test_session.add(demo_user)
        await test_session.flush()

        sub = Subscription(
            user_id=demo_user.id,
            plan="pro",
            status="active",
        )
        test_session.add(sub)
        await test_session.commit()

        with patch('app.core.config.settings') as mock_settings:
            mock_settings.ENABLE_DEMO_MODE = True
            mock_settings.DEMO_USER_EMAIL = settings.DEMO_USER_EMAIL
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.DEMO_USER_PASSWORD = settings.DEMO_USER_PASSWORD
            resp = await client.post("/auth/demo-login")
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data

    @pytest.mark.asyncio
    async def test_demo_login_no_user_when_enabled(self, client):
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.ENABLE_DEMO_MODE = True
            mock_settings.DEMO_USER_EMAIL = "nonexistent@payflow.ai"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            resp = await client.post("/auth/demo-login")
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"].lower()


class TestDemoReset:
    @pytest.mark.asyncio
    async def test_demo_reset_blocked_in_production(self, client, auth_headers):
        with patch('app.routers.demo.settings') as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.ENABLE_DEMO_MODE = True
            resp = await client.post("/demo/reset", headers=auth_headers)
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_demo_reset_blocked_when_demo_disabled(self, client, auth_headers):
        with patch('app.routers.demo.settings') as mock_settings:
            mock_settings.ENVIRONMENT = "development"
            mock_settings.ENABLE_DEMO_MODE = False
            resp = await client.post("/demo/reset", headers=auth_headers)
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_demo_reset_no_auth(self, client):
        resp = await client.post("/demo/reset")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_demo_reset_creates_data(self, client, auth_headers, test_session):
        from app.core.config import settings
        from app.core.security import get_password_hash

        demo_user = User(
            name="Demo User",
            email=settings.DEMO_USER_EMAIL,
            hashed_password=get_password_hash(settings.DEMO_USER_PASSWORD),
            phone_number="+15555555555",
        )
        test_session.add(demo_user)
        await test_session.flush()
        sub = Subscription(user_id=demo_user.id, plan="pro", status="active")
        test_session.add(sub)
        await test_session.commit()

        with patch('app.routers.demo.settings') as mock_settings, \
             patch('app.services.demo_service.settings') as mock_svc_settings:
            mock_settings.ENVIRONMENT = 'development'
            mock_settings.ENABLE_DEMO_MODE = True
            mock_settings.DEMO_USER_EMAIL = settings.DEMO_USER_EMAIL
            mock_settings.DEMO_USER_PASSWORD = settings.DEMO_USER_PASSWORD
            mock_svc_settings.ENVIRONMENT = 'development'
            mock_svc_settings.ENABLE_DEMO_MODE = True
            mock_svc_settings.DEMO_USER_EMAIL = settings.DEMO_USER_EMAIL
            mock_svc_settings.DEMO_USER_PASSWORD = settings.DEMO_USER_PASSWORD
            resp = await client.post("/demo/reset", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["charges_created"] > 0
            assert data["transactions_created"] > 0


class TestDemoUserIsolation:
    @pytest.mark.asyncio
    async def test_demo_user_cannot_access_other_user_charges(
        self, client, test_session, authed_user, auth_headers
    ):
        from app.core.config import settings
        from app.core.security import get_password_hash

        demo_user = User(
            name="Demo User",
            email=settings.DEMO_USER_EMAIL,
            hashed_password=get_password_hash(settings.DEMO_USER_PASSWORD),
            phone_number="+15555555555",
        )
        test_session.add(demo_user)
        await test_session.flush()
        sub = Subscription(user_id=demo_user.id, plan="pro", status="active")
        test_session.add(sub)

        test_session.add(Charge(
            user_id=authed_user.id,
            customer_name="My Private Charge",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="iso_1",
            payment_link="http://iso1",
            status=ChargeStatus.PENDING,
        ))
        test_session.add(Charge(
            user_id=demo_user.id,
            customer_name="Demo Charge",
            amount=Decimal("50.00"),
            provider="fake",
            provider_charge_id="iso_2",
            payment_link="http://iso2",
            status=ChargeStatus.PENDING,
        ))
        await test_session.commit()

        demo_token = create_access_token(data={"sub": str(demo_user.id)})
        demo_headers = {"Authorization": f"Bearer {demo_token}"}

        resp = await client.get("/charges", headers=demo_headers)
        assert resp.status_code == 200
        data = resp.json()
        names = {item["customer_name"] for item in data["items"]}
        assert "Demo Charge" in names
        assert "My Private Charge" not in names
