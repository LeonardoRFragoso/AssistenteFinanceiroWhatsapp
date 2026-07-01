import pytest_asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base
from app.models import User, Charge, PendingAction, ProviderEvent, ChargeReminderLog
from app.models.transaction import Transaction
from app.models.reminder import Reminder
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.conversation_log import ConversationLog


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
