from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from decimal import Decimal
from datetime import date, timedelta, datetime, timezone
from typing import Dict, Any
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.models.charge import Charge, ChargeStatus
from app.models.transaction import Transaction
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.core.logging import logger


class DemoService:
    """Service for managing demo user data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_demo_user(self) -> User:
        """Get or create the demo user."""
        result = await self.db.execute(
            select(User).where(User.email == settings.DEMO_USER_EMAIL)
        )
        user = result.scalar_one_or_none()

        if user:
            return user

        user = User(
            name="Demo User",
            email=settings.DEMO_USER_EMAIL,
            hashed_password=get_password_hash(settings.DEMO_USER_PASSWORD),
            phone_number="+15555555555",
        )
        self.db.add(user)
        await self.db.flush()

        sub = Subscription(
            user_id=user.id,
            plan="pro",
            status="active",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(sub)

        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"Demo user created: {user.email}")
        return user

    async def seed_demo_charges(self, user_id: int) -> int:
        """Create varied demo charges. Returns count created."""
        today = date.today()

        demo_charges = [
            Charge(
                user_id=user_id,
                customer_name="João Silva",
                customer_phone="+5511999999999",
                amount=Decimal("150.00"),
                description="Serviço de design gráfico",
                provider="fake",
                provider_charge_id="demo_1",
                payment_link="http://example.com/pay/demo_1",
                status=ChargeStatus.PENDING,
                due_date=today + timedelta(days=7),
            ),
            Charge(
                user_id=user_id,
                customer_name="Maria Santos",
                customer_phone="+5511888888888",
                amount=Decimal("350.00"),
                description="Consultoria de marketing",
                provider="fake",
                provider_charge_id="demo_2",
                payment_link="http://example.com/pay/demo_2",
                status=ChargeStatus.PENDING,
                due_date=today + timedelta(days=3),
            ),
            Charge(
                user_id=user_id,
                customer_name="Pedro Oliveira",
                amount=Decimal("89.90"),
                description="Manutenção de computador",
                provider="fake",
                provider_charge_id="demo_3",
                payment_link="http://example.com/pay/demo_3",
                status=ChargeStatus.PENDING,
                due_date=None,
            ),
            Charge(
                user_id=user_id,
                customer_name="Ana Costa",
                customer_phone="+5511777777777",
                amount=Decimal("1200.00"),
                description="Desenvolvimento de site",
                provider="fake",
                provider_charge_id="demo_4",
                payment_link="http://example.com/pay/demo_4",
                status=ChargeStatus.PENDING,
                due_date=today - timedelta(days=5),
            ),
            Charge(
                user_id=user_id,
                customer_name="Carlos Ferreira",
                amount=Decimal("450.00"),
                description="Aula de inglês - pacote mensal",
                provider="fake",
                provider_charge_id="demo_5",
                payment_link="http://example.com/pay/demo_5",
                status=ChargeStatus.PENDING,
                due_date=today - timedelta(days=15),
            ),
            Charge(
                user_id=user_id,
                customer_name="Beatriz Lima",
                customer_phone="+5511666666666",
                amount=Decimal("200.00"),
                description="Fotografia de evento",
                provider="fake",
                provider_charge_id="demo_6",
                payment_link="http://example.com/pay/demo_6",
                status=ChargeStatus.PAID,
                due_date=today - timedelta(days=10),
                paid_at=datetime.now(timezone.utc) - timedelta(days=8),
            ),
            Charge(
                user_id=user_id,
                customer_name="Roberto Alves",
                amount=Decimal("75.00"),
                description="Reparo de encanamento",
                provider="fake",
                provider_charge_id="demo_7",
                payment_link="http://example.com/pay/demo_7",
                status=ChargeStatus.PAID,
                due_date=today - timedelta(days=20),
                paid_at=datetime.now(timezone.utc) - timedelta(days=18),
            ),
            Charge(
                user_id=user_id,
                customer_name="Juliana Reis",
                customer_phone="+5511555555555",
                amount=Decimal("600.00"),
                description="Planejamento tributário",
                provider="fake",
                provider_charge_id="demo_8",
                payment_link="http://example.com/pay/demo_8",
                status=ChargeStatus.CANCELLED,
                due_date=today - timedelta(days=2),
            ),
            Charge(
                user_id=user_id,
                customer_name="Fernando Souza",
                amount=Decimal("180.00"),
                description="Instalação elétrica",
                provider="fake",
                provider_charge_id="demo_9",
                payment_link="http://example.com/pay/demo_9",
                status=ChargeStatus.PENDING,
                due_date=today + timedelta(days=1),
            ),
            Charge(
                user_id=user_id,
                customer_name="Patricia Gomes",
                customer_phone="+5511444444444",
                amount=Decimal("950.00"),
                description="Campanha de publicidade digital",
                provider="fake",
                provider_charge_id="demo_10",
                payment_link="http://example.com/pay/demo_10",
                status=ChargeStatus.PENDING,
                due_date=today - timedelta(days=30),
            ),
        ]

        for charge in demo_charges:
            self.db.add(charge)
        await self.db.commit()
        return len(demo_charges)

    async def seed_demo_transactions(self, user_id: int) -> int:
        """Create demo transactions (income/expense). Returns count created."""
        today = date.today()

        demo_transactions = [
            Transaction(
                user_id=user_id,
                type="income",
                category="Serviços",
                description="Pagamento de Beatriz Lima - Fotografia",
                amount=Decimal("200.00"),
                date=today - timedelta(days=8),
            ),
            Transaction(
                user_id=user_id,
                type="income",
                category="Serviços",
                description="Pagamento de Roberto Alves - Encanamento",
                amount=Decimal("75.00"),
                date=today - timedelta(days=18),
            ),
            Transaction(
                user_id=user_id,
                type="expense",
                category="Software",
                description="Assinatura Adobe Creative Cloud",
                amount=Decimal("89.90"),
                date=today - timedelta(days=5),
            ),
            Transaction(
                user_id=user_id,
                type="expense",
                category="Marketing",
                description="Anúncios Facebook Ads",
                amount=Decimal("150.00"),
                date=today - timedelta(days=3),
            ),
            Transaction(
                user_id=user_id,
                type="income",
                category="Consultoria",
                description="Consultoria - Maria Santos",
                amount=Decimal("350.00"),
                date=today - timedelta(days=2),
            ),
            Transaction(
                user_id=user_id,
                type="expense",
                category="Transporte",
                description="Combustível",
                amount=Decimal("120.00"),
                date=today - timedelta(days=1),
            ),
        ]

        for tx in demo_transactions:
            self.db.add(tx)
        await self.db.commit()
        return len(demo_transactions)

    async def reset_demo_user(self) -> Dict[str, Any]:
        """Delete all demo user data and recreate from scratch."""
        result = await self.db.execute(
            select(User).where(User.email == settings.DEMO_USER_EMAIL)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = await self.get_or_create_demo_user()
        else:
            await self.db.execute(
                delete(Charge).where(Charge.user_id == user.id)
            )
            await self.db.execute(
                delete(Transaction).where(Transaction.user_id == user.id)
            )
            await self.db.commit()
            logger.info(f"Demo data cleared for user {user.id}")

        charges_count = await self.seed_demo_charges(user.id)
        transactions_count = await self.seed_demo_transactions(user.id)

        return {
            "status": "ok",
            "message": "Demo data reset successfully",
            "user_email": user.email,
            "charges_created": charges_count,
            "transactions_created": transactions_count,
        }

    async def seed_all(self) -> Dict[str, Any]:
        """Create demo user and seed data if not exists. Idempotent."""
        user = await self.get_or_create_demo_user()

        existing_charges = await self.db.execute(
            select(Charge).where(Charge.user_id == user.id)
        )
        charges = existing_charges.scalars().all()

        existing_tx = await self.db.execute(
            select(Transaction).where(Transaction.user_id == user.id)
        )
        transactions = existing_tx.scalars().all()

        if charges or transactions:
            return {
                "status": "ok",
                "message": "Demo data already exists",
                "user_email": user.email,
                "charges_count": len(charges),
                "transactions_count": len(transactions),
            }

        charges_count = await self.seed_demo_charges(user.id)
        transactions_count = await self.seed_demo_transactions(user.id)

        return {
            "status": "ok",
            "message": "Demo data seeded successfully",
            "user_email": user.email,
            "charges_created": charges_count,
            "transactions_created": transactions_count,
        }
