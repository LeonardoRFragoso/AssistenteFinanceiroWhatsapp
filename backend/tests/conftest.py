import pytest_asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base
from app.models import User, Charge, PendingAction, ProviderEvent, ChargeReminderLog, ChargeDeliveryLog
from app.models.transaction import Transaction
from app.models.reminder import Reminder
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.conversation_log import ConversationLog
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
from app.models.bills import (
    DetectedBill, BillReminder, BillPaymentIntent, BillEventLog,
)
from datetime import datetime, timezone


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def sample_user(db_session):
    user = User(
        name="João Empresário",
        email="joao@example.com",
        hashed_password="hashed",
        phone_number="+5511999999999"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_user(db_session):
    user = User(
        name="Maria Teste",
        email="maria@example.com",
        hashed_password="hashed",
        phone_number="+5511888888888"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_organization(db_session, sample_user):
    """Create a default organization for the sample user."""
    org = Organization(
        name="Test Org",
        slug=f"test-org-{sample_user.id}",
        owner_user_id=sample_user.id,
    )
    db_session.add(org)
    await db_session.flush()
    member = OrganizationMember(
        organization_id=org.id,
        user_id=sample_user.id,
        role=OrganizationRole.OWNER,
        active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(org)

    # Seed billing plans and create Professional subscription
    from app.services.saas_billing_service import SaaSBillingService
    billing = SaaSBillingService(db_session)
    await billing.seed_plans()
    await billing.ensure_free_subscription(org.id)
    try:
        await billing.change_plan(org.id, "professional")
    except Exception:
        pass

    return org


@pytest_asyncio.fixture
async def second_organization(db_session, second_user):
    """Create a default organization for the second user."""
    from app.models.organization import Organization, OrganizationMember, OrganizationRole
    org = Organization(
        name="Second Test Org",
        slug=f"second-test-org-{second_user.id}",
        owner_user_id=second_user.id,
    )
    db_session.add(org)
    await db_session.flush()
    member = OrganizationMember(
        organization_id=org.id,
        user_id=second_user.id,
        role=OrganizationRole.OWNER,
        active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(org)

    # Seed billing plans and create Professional subscription
    from app.services.saas_billing_service import SaaSBillingService
    billing = SaaSBillingService(db_session)
    await billing.seed_plans()
    await billing.ensure_free_subscription(org.id)
    try:
        await billing.change_plan(org.id, "professional")
    except Exception:
        pass

    return org
