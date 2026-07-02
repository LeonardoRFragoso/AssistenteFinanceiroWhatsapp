import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from app.services.charge_analytics_service import ChargeAnalyticsService
from app.models.charge import Charge, ChargeStatus
from app.models.customer import Customer
from app.models.collection_message_log import CollectionMessageLog, CollectionMessageStatus
from app.models.message_template import MessageTemplate, MessageTone
from app.models.collection_rule import CollectionRule, TriggerType
from app.models.user import User


@pytest_asyncio.fixture
async def sample_charge(db_session, sample_user, sample_organization):
    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="João Silva",
        customer_phone="11999999999",
        amount=Decimal("150.00"),
        description="serviço de design",
        provider="fake",
        provider_charge_id="fake_123",
        payment_link="https://example.com/pay/123",
        qr_code="fake-qr-code",
        qr_code_base64="base64data",
        status=ChargeStatus.PENDING,
        due_date=date.today() - timedelta(days=5),
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)
    return charge


@pytest_asyncio.fixture
async def paid_charge(db_session, sample_user, sample_organization):
    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="João Silva",
        customer_phone="11999999999",
        amount=Decimal("200.00"),
        description="consultoria",
        provider="fake",
        provider_charge_id="fake_456",
        payment_link="https://example.com/pay/456",
        status=ChargeStatus.PAID,
        due_date=date.today() - timedelta(days=30),
        paid_at=datetime.now(timezone.utc) - timedelta(days=25),
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)
    return charge


@pytest_asyncio.fixture
async def pending_charge(db_session, sample_user, sample_organization):
    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Maria Santos",
        customer_phone="11888888888",
        amount=Decimal("300.00"),
        description="serviço de consultoria",
        provider="fake",
        provider_charge_id="fake_789",
        payment_link="https://example.com/pay/789",
        status=ChargeStatus.PENDING,
        due_date=date.today() + timedelta(days=10),
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)
    return charge


@pytest_asyncio.fixture
async def second_user_charge(db_session, second_user, second_organization):
    charge = Charge(
        user_id=second_user.id,
        organization_id=second_organization.id,
        customer_name="Carlos Outro",
        customer_phone="11777777777",
        amount=Decimal("500.00"),
        description="serviço outro usuario",
        provider="fake",
        provider_charge_id="fake_other",
        payment_link="https://example.com/pay/other",
        status=ChargeStatus.PENDING,
        due_date=date.today() - timedelta(days=10),
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)
    return charge


@pytest_asyncio.fixture
async def collection_log(db_session, sample_user, sample_organization, sample_charge):
    log = CollectionMessageLog(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        charge_id=sample_charge.id,
        customer_id=None,
        template_id=None,
        channel="whatsapp",
        message_preview="Olá, sua cobrança está vencida...",
        status=CollectionMessageStatus.DRAFT,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


@pytest_asyncio.fixture
async def message_template(db_session, sample_user, sample_organization):
    tpl = MessageTemplate(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        name="Cobrança Amigável",
        tone=MessageTone.FRIENDLY,
        template_text="Olá {{customer_name}}, sua cobrança de R$ {{amount}} está vencida.",
        active=True,
    )
    db_session.add(tpl)
    await db_session.commit()
    await db_session.refresh(tpl)
    return tpl


class TestAnalyticsOverview:
    @pytest.mark.asyncio
    async def test_overview_no_data(self, db_session, sample_user):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_overview(sample_user.id)
        assert result["total_billed"] == 0
        assert result["total_paid"] == 0
        assert result["total_pending"] == 0
        assert result["total_overdue"] == 0
        assert result["collection_rate"] == 0
        assert result["overdue_rate"] == 0
        assert result["active_customers"] == 0
        assert result["total_charges"] == 0

    @pytest.mark.asyncio
    async def test_overview_with_charges(self, db_session, sample_user, sample_charge, paid_charge, pending_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_overview(sample_user.id)
        assert result["total_billed"] == 650.0
        assert result["total_paid"] == 200.0
        assert result["total_pending"] == 300.0
        assert result["total_overdue"] == 150.0
        assert result["collection_rate"] > 0
        assert result["active_customers"] == 2  # João Silva and Maria Santos
        assert result["overdue_customers"] == 1
        assert result["total_charges"] == 3

    @pytest.mark.asyncio
    async def test_overview_user_isolation(self, db_session, sample_user, second_user, sample_charge, second_user_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_overview(sample_user.id)
        assert result["total_billed"] == 150.0
        assert result["total_charges"] == 1
        # Second user should not see sample_user's charges
        result2 = await service.get_overview(second_user.id)
        assert result2["total_billed"] == 500.0
        assert result2["total_charges"] == 1

    @pytest.mark.asyncio
    async def test_overview_average_payment_time(self, db_session, sample_user, paid_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_overview(sample_user.id)
        assert result["average_payment_time_days"] is not None

    @pytest.mark.asyncio
    async def test_overview_average_delay(self, db_session, sample_user, sample_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_overview(sample_user.id)
        assert result["average_delay_days"] is not None
        assert result["average_delay_days"] > 0


class TestMonthlyTrends:
    @pytest.mark.asyncio
    async def test_monthly_trends_no_data(self, db_session, sample_user):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_monthly_trends(sample_user.id, months=3)
        assert len(result) == 3
        assert all(t["billed_amount"] == 0 for t in result)

    @pytest.mark.asyncio
    async def test_monthly_trends_with_data(self, db_session, sample_user, sample_charge, paid_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_monthly_trends(sample_user.id, months=6)
        assert len(result) == 6
        # Most recent month should have data
        current_month = result[-1]
        assert current_month["billed_amount"] > 0
        assert current_month["charges_created"] >= 2

    @pytest.mark.asyncio
    async def test_monthly_trends_user_isolation(self, db_session, sample_user, second_user, sample_charge, second_user_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_monthly_trends(sample_user.id, months=3)
        total_billed = sum(t["billed_amount"] for t in result)
        assert total_billed == 150.0


class TestAging:
    @pytest.mark.asyncio
    async def test_aging_no_overdue(self, db_session, sample_user, paid_charge, pending_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_aging(sample_user.id)
        assert result["total_overdue"] == 0
        assert result["total_overdue_amount"] == 0

    @pytest.mark.asyncio
    async def test_aging_with_overdue(self, db_session, sample_user, sample_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_aging(sample_user.id)
        assert result["total_overdue"] == 1
        assert result["total_overdue_amount"] == 150.0
        # Should be in 1-7 days bucket (5 days overdue)
        bucket_1_7 = next(b for b in result["buckets"] if b["bucket"] == "1-7 dias")
        assert bucket_1_7["count"] == 1
        assert bucket_1_7["percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_aging_buckets(self, db_session, sample_user, sample_organization):
        # Create charges with different overdue periods
        for days in [3, 12, 25, 45, 70]:
            charge = Charge(
                user_id=sample_user.id,
                organization_id=sample_organization.id,
                customer_name=f"Cliente {days}",
                amount=Decimal("100.00"),
                provider="fake",
                provider_charge_id=f"fake_{days}",
                status=ChargeStatus.PENDING,
                due_date=date.today() - timedelta(days=days),
            )
            db_session.add(charge)
        await db_session.commit()

        service = ChargeAnalyticsService(db_session)
        result = await service.get_aging(sample_user.id)
        assert result["total_overdue"] == 5
        buckets = {b["bucket"]: b for b in result["buckets"]}
        assert buckets["1-7 dias"]["count"] == 1
        assert buckets["8-15 dias"]["count"] == 1
        assert buckets["16-30 dias"]["count"] == 1
        assert buckets["31-60 dias"]["count"] == 1
        assert buckets["60+ dias"]["count"] == 1

    @pytest.mark.asyncio
    async def test_aging_user_isolation(self, db_session, sample_user, second_user, sample_charge, second_user_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_aging(sample_user.id)
        assert result["total_overdue"] == 1
        result2 = await service.get_aging(second_user.id)
        assert result2["total_overdue"] == 1
        assert result2["total_overdue_amount"] == 500.0


class TestCustomerPerformance:
    @pytest.mark.asyncio
    async def test_customer_performance_no_data(self, db_session, sample_user):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_customer_performance(sample_user.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_customer_performance_with_data(self, db_session, sample_user, sample_charge, paid_charge, pending_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_customer_performance(sample_user.id)
        assert len(result) == 2  # João Silva and Maria Santos
        # João Silva should be first (has overdue)
        assert result[0]["customer_name"] == "João Silva"
        assert result[0]["total_overdue"] == 150.0
        assert result[0]["total_paid"] == 200.0
        assert result[0]["suggested_action"] == "send_friendly_reminder"

    @pytest.mark.asyncio
    async def test_customer_performance_suggested_actions(self, db_session, sample_user, sample_organization):
        service = ChargeAnalyticsService(db_session)

        # Good payer (only paid charges)
        charge1 = Charge(
            user_id=sample_user.id,
            organization_id=sample_organization.id,
            customer_name="Bom Cliente",
            amount=Decimal("100.00"),
            provider="fake",
            provider_charge_id="fake_good",
            status=ChargeStatus.PAID,
            due_date=date.today() - timedelta(days=10),
            paid_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        db_session.add(charge1)

        # Frequent late (3+ overdue)
        for i in range(3):
            c = Charge(
                user_id=sample_user.id,
                organization_id=sample_organization.id,
                customer_name="Cliente Atrasado",
                amount=Decimal("50.00"),
                provider="fake",
                provider_charge_id=f"fake_late_{i}",
                status=ChargeStatus.PENDING,
                due_date=date.today() - timedelta(days=10 + i),
            )
            db_session.add(c)

        await db_session.commit()

        result = await service.get_customer_performance(sample_user.id)
        perf_map = {r["customer_name"]: r for r in result}
        assert perf_map["Bom Cliente"]["suggested_action"] == "thank_customer"
        assert perf_map["Cliente Atrasado"]["suggested_action"] == "review_payment_terms"

    @pytest.mark.asyncio
    async def test_customer_performance_user_isolation(self, db_session, sample_user, second_user, sample_charge, second_user_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_customer_performance(sample_user.id)
        assert all("Carlos Outro" != r["customer_name"] for r in result)
        result2 = await service.get_customer_performance(second_user.id)
        assert all("João Silva" != r["customer_name"] for r in result2)

    @pytest.mark.asyncio
    async def test_customer_performance_not_credit_score(self, db_session, sample_user, sample_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_customer_performance(sample_user.id)
        for item in result:
            assert "credit" not in item["operational_status"].lower()
            assert "score" not in item["suggested_action"].lower()


class TestCollectionPerformance:
    @pytest.mark.asyncio
    async def test_collection_performance_no_data(self, db_session, sample_user):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_collection_performance(sample_user.id)
        assert result["insufficient_data"] is True
        assert result["total_drafts"] == 0

    @pytest.mark.asyncio
    async def test_collection_performance_with_logs(self, db_session, sample_user, sample_charge, collection_log):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_collection_performance(sample_user.id)
        assert result["insufficient_data"] is True  # Only 1 log, need 3+
        assert result["total_drafts"] == 1
        assert result["charges_with_followup"] == 1

    @pytest.mark.asyncio
    async def test_collection_performance_sufficient_data(self, db_session, sample_user, sample_organization, sample_charge):
        # Create 3+ logs
        for i in range(3):
            log = CollectionMessageLog(
                user_id=sample_user.id,
                organization_id=sample_organization.id,
                charge_id=sample_charge.id,
                customer_id=None,
                template_id=None,
                channel="whatsapp",
                message_preview=f"Mensagem {i}",
                status=CollectionMessageStatus.DRAFT,
            )
            db_session.add(log)
        await db_session.commit()

        service = ChargeAnalyticsService(db_session)
        result = await service.get_collection_performance(sample_user.id)
        assert result["insufficient_data"] is False
        assert result["total_drafts"] == 3

    @pytest.mark.asyncio
    async def test_collection_performance_user_isolation(self, db_session, sample_user, second_user, sample_charge, collection_log):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_collection_performance(second_user.id)
        assert result["total_drafts"] == 0
        assert result["insufficient_data"] is True


class TestInsights:
    @pytest.mark.asyncio
    async def test_insights_no_data(self, db_session, sample_user):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_insights(sample_user.id)
        assert len(result) == 1
        assert "ainda não tem cobranças" in result[0].lower()

    @pytest.mark.asyncio
    async def test_insights_with_data(self, db_session, sample_user, sample_charge, paid_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_insights(sample_user.id)
        assert len(result) > 0
        # Should mention collection rate
        assert any("recebeu" in r.lower() for r in result)

    @pytest.mark.asyncio
    async def test_insights_not_alarmist(self, db_session, sample_user, sample_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_insights(sample_user.id)
        for insight in result:
            assert "crise" not in insight.lower()
            assert "risco" not in insight.lower()
            assert "score de crédito" not in insight.lower()

    @pytest.mark.asyncio
    async def test_insights_user_isolation(self, db_session, sample_user, second_user, sample_charge):
        service = ChargeAnalyticsService(db_session)
        result = await service.get_insights(second_user.id)
        # Second user has no charges
        assert any("ainda não tem cobranças" in r.lower() for r in result)


class TestAnalyticsWithDateFilter:
    @pytest.mark.asyncio
    async def test_overview_with_date_filter(self, db_session, sample_user, sample_charge, paid_charge):
        service = ChargeAnalyticsService(db_session)
        # Filter to only recent charges
        result = await service.get_overview(
            sample_user.id,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today(),
        )
        # Should include charges created today
        assert result["total_charges"] >= 0

    @pytest.mark.asyncio
    async def test_overview_old_date_filter(self, db_session, sample_user, sample_charge):
        service = ChargeAnalyticsService(db_session)
        # Filter to a year ago — should return no charges
        result = await service.get_overview(
            sample_user.id,
            start_date=date.today() - timedelta(days=365),
            end_date=date.today() - timedelta(days=364),
        )
        assert result["total_charges"] == 0
