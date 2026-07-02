import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from app.models.charge import Charge, ChargeStatus
from app.models.recurring_task import RecurringTask, RecurrenceType
from app.services.financial_query_service import FinancialQueryService
from app.services.recurring_task_service import RecurringTaskService
from app.services.document_analysis_service import DocumentAnalysisService
from app.schemas.recurring_task import RecurringTaskCreate
from app.providers.fake_provider import FakePaymentProvider


class TestFinancialQueryService:
    @pytest_asyncio.fixture
    async def charges_for_user(self, db_session, sample_user):
        charges = [
            Charge(
                user_id=sample_user.id,
                customer_name="João Silva",
                customer_phone="11999999999",
                amount=Decimal("150.00"),
                description="Serviço de design",
                provider="fake",
                provider_charge_id="fake_001",
                payment_link="http://localhost:8000/pay/fake_001",
                qr_code="http://localhost:8000/pay/fake_001",
                qr_code_base64="data:image/png;base64,abc123",
                status=ChargeStatus.PENDING,
                due_date=date.today() + timedelta(days=7),
            ),
            Charge(
                user_id=sample_user.id,
                customer_name="Maria Santos",
                amount=Decimal("300.00"),
                description="Consultoria",
                provider="fake",
                provider_charge_id="fake_002",
                payment_link="http://localhost:8000/pay/fake_002",
                qr_code="http://localhost:8000/pay/fake_002",
                qr_code_base64="data:image/png;base64,def456",
                status=ChargeStatus.PAID,
                paid_at=datetime.now(timezone.utc),
            ),
            Charge(
                user_id=sample_user.id,
                customer_name="João Silva",
                amount=Decimal("200.00"),
                description="Manutenção",
                provider="fake",
                provider_charge_id="fake_003",
                payment_link="http://localhost:8000/pay/fake_003",
                qr_code="http://localhost:8000/pay/fake_003",
                qr_code_base64="data:image/png;base64,ghi789",
                status=ChargeStatus.PENDING,
                due_date=date.today() - timedelta(days=5),
            ),
        ]
        for c in charges:
            db_session.add(c)
        await db_session.commit()
        return charges

    async def test_list_overdue_charges(self, db_session, sample_user, charges_for_user):
        service = FinancialQueryService(db_session)
        result = await service.list_overdue_charges(sample_user.id)
        assert "vencida" in result.lower()
        assert "João Silva" in result
        assert "200.00" in result

    async def test_list_overdue_empty(self, db_session, sample_user):
        service = FinancialQueryService(db_session)
        result = await service.list_overdue_charges(sample_user.id)
        assert "não tem cobranças vencidas" in result.lower()

    async def test_list_pending_charges(self, db_session, sample_user, charges_for_user):
        service = FinancialQueryService(db_session)
        result = await service.list_pending_charges(sample_user.id)
        assert "pendente" in result.lower()
        assert "150.00" in result

    async def test_list_paid_charges(self, db_session, sample_user, charges_for_user):
        service = FinancialQueryService(db_session)
        result = await service.list_paid_charges(sample_user.id)
        assert "paga" in result.lower()
        assert "300.00" in result
        assert "Maria Santos" in result

    async def test_search_charges_by_customer(self, db_session, sample_user, charges_for_user):
        service = FinancialQueryService(db_session)
        result = await service.search_charges_by_customer(sample_user.id, "João")
        assert "João" in result
        assert "150.00" in result or "200.00" in result

    async def test_search_charges_not_found(self, db_session, sample_user, charges_for_user):
        service = FinancialQueryService(db_session)
        result = await service.search_charges_by_customer(sample_user.id, "Carlos")
        assert "não encontrei" in result.lower()

    async def test_charge_summary(self, db_session, sample_user, charges_for_user):
        service = FinancialQueryService(db_session)
        result = await service.charge_summary(sample_user.id)
        assert "Resumo" in result
        assert "Pendentes" in result
        assert "Pagas" in result
        assert "Vencidas" in result

    async def test_customer_charge_history(self, db_session, sample_user, charges_for_user):
        service = FinancialQueryService(db_session)
        result = await service.customer_charge_history(sample_user.id, "João Silva")
        assert "João Silva" in result
        assert "Histórico" in result

    async def test_top_overdue_customers(self, db_session, sample_user, charges_for_user):
        service = FinancialQueryService(db_session)
        result = await service.top_overdue_customers(sample_user.id)
        assert "João Silva" in result
        assert "200.00" in result

    async def test_top_overdue_empty(self, db_session, sample_user):
        service = FinancialQueryService(db_session)
        result = await service.top_overdue_customers(sample_user.id)
        assert "nenhum cliente" in result.lower()


class TestRecurringTaskService:
    async def test_create_daily_task(self, db_session, sample_user):
        service = RecurringTaskService(db_session)
        data = RecurringTaskCreate(
            title="Lembrar de cobrar clientes",
            recurrence_type=RecurrenceType.DAILY,
        )
        task = await service.create_task(sample_user.id, data)
        assert task.id is not None
        assert task.title == "Lembrar de cobrar clientes"
        assert task.recurrence_type == RecurrenceType.DAILY
        assert task.active is True
        assert task.next_run_at is not None

    async def test_create_weekly_task(self, db_session, sample_user):
        service = RecurringTaskService(db_session)
        data = RecurringTaskCreate(
            title="Revisar cobranças toda sexta",
            recurrence_type=RecurrenceType.WEEKLY,
            day_of_week=5,
        )
        task = await service.create_task(sample_user.id, data)
        assert task.recurrence_type == RecurrenceType.WEEKLY
        assert task.day_of_week == 5

    async def test_create_monthly_task(self, db_session, sample_user):
        service = RecurringTaskService(db_session)
        data = RecurringTaskCreate(
            title="Cobrar no dia 10",
            recurrence_type=RecurrenceType.MONTHLY,
            day_of_month=10,
        )
        task = await service.create_task(sample_user.id, data)
        assert task.recurrence_type == RecurrenceType.MONTHLY
        assert task.day_of_month == 10

    async def test_cancel_task(self, db_session, sample_user):
        service = RecurringTaskService(db_session)
        data = RecurringTaskCreate(
            title="Tarefa para cancelar",
            recurrence_type=RecurrenceType.DAILY,
        )
        task = await service.create_task(sample_user.id, data)
        cancelled = await service.cancel_task(task.id, sample_user.id)
        assert cancelled is not None
        assert cancelled.active is False

    async def test_cancel_nonexistent_task(self, db_session, sample_user):
        service = RecurringTaskService(db_session)
        result = await service.cancel_task(99999, sample_user.id)
        assert result is None

    async def test_get_user_tasks(self, db_session, sample_user):
        service = RecurringTaskService(db_session)
        data1 = RecurringTaskCreate(title="Task 1", recurrence_type=RecurrenceType.DAILY)
        data2 = RecurringTaskCreate(title="Task 2", recurrence_type=RecurrenceType.WEEKLY, day_of_week=3)
        await service.create_task(sample_user.id, data1)
        await service.create_task(sample_user.id, data2)
        tasks = await service.get_user_tasks(sample_user.id)
        assert len(tasks) == 2

    async def test_get_due_tasks_empty(self, db_session, sample_user):
        service = RecurringTaskService(db_session)
        data = RecurringTaskCreate(title="Future task", recurrence_type=RecurrenceType.DAILY)
        await service.create_task(sample_user.id, data)
        due = await service.get_due_tasks()
        assert len(due) == 0

    async def test_get_due_tasks_with_past_date(self, db_session, sample_user):
        task = RecurringTask(
            user_id=sample_user.id,
            title="Overdue task",
            recurrence_type=RecurrenceType.DAILY,
            next_run_at=datetime.now(timezone.utc) - timedelta(hours=2),
            active=True,
        )
        db_session.add(task)
        await db_session.commit()
        service = RecurringTaskService(db_session)
        due = await service.get_due_tasks()
        assert len(due) >= 1
        assert any(t.title == "Overdue task" for t in due)


class TestDocumentAnalysisService:
    def test_format_whatsapp_response_with_data(self):
        service = DocumentAnalysisService()
        analysis = {
            "document_type": "boleto",
            "amount": "150.00",
            "due_date": "2026-07-15",
            "description": "Conta de luz",
            "recipient_name": "Empresa XYZ",
            "confidence": 0.85,
            "suggested_action": "create_reminder",
            "requires_confirmation": True,
        }
        result = service.format_whatsapp_response(analysis)
        assert "Boleto" in result
        assert "150.00" in result
        assert "15/07/2026" in result
        assert "Empresa XYZ" in result
        assert "85%" in result
        assert "sim" in result.lower()

    def test_format_whatsapp_response_error(self):
        service = DocumentAnalysisService()
        analysis = {"error": "File too large"}
        result = service.format_whatsapp_response(analysis)
        assert "File too large" in result

    def test_format_whatsapp_response_low_confidence(self):
        service = DocumentAnalysisService()
        analysis = {
            "document_type": "unknown",
            "confidence": 0.1,
            "suggested_action": "manual_review",
            "requires_confirmation": False,
        }
        result = service.format_whatsapp_response(analysis)
        assert "não consegui identificar" in result.lower()

    def test_extract_from_text_with_amount_and_date(self):
        service = DocumentAnalysisService()
        text = "Boleto - Valor: R$ 250,50 - Vencimento: 15/07/2026"
        result = service._extract_from_text(text)
        assert result["document_type"] == "boleto"
        assert result["amount"] == "250.50"
        assert result["due_date"] == "2026-07-15"
        assert result["confidence"] >= 0.7

    def test_extract_from_text_empty(self):
        service = DocumentAnalysisService()
        result = service._extract_from_text("texto sem dados financeiros")
        assert result["confidence"] == 0.0
        assert result["document_type"] == "unknown"

    async def test_analyze_content_unsupported_type(self):
        service = DocumentAnalysisService()
        result = await service.analyze_content(b"test", "text/plain")
        assert result["confidence"] == 0.0
        assert "Unsupported" in result.get("error", "")

    async def test_analyze_content_too_large(self):
        service = DocumentAnalysisService()
        large_content = b"x" * (6 * 1024 * 1024)
        result = await service.analyze_content(large_content, "image/png")
        assert result["confidence"] == 0.0
        assert "too large" in result.get("error", "").lower()


class TestFakePaymentProviderQRCode:
    def test_generate_qr_code_base64(self):
        provider = FakePaymentProvider()
        qr_b64 = provider._generate_qr_code_base64("http://localhost:8000/pay/test123")
        assert qr_b64.startswith("data:image/png;base64,")
        assert len(qr_b64) > 100

    async def test_create_charge_returns_qr_code(self):
        provider = FakePaymentProvider()
        result = await provider.create_charge(
            amount=Decimal("150.00"),
            description="Test charge",
            customer_name="João",
        )
        assert result["qr_code"] is not None
        assert result["qr_code_base64"] is not None
        assert result["qr_code_base64"].startswith("data:image/png;base64,")
        assert result["payment_link"] is not None
