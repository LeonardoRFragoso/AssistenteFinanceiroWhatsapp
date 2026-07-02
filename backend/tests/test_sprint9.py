"""Sprint 9 tests: Customer Intelligence, Collection Rules, Message Templates.

Tests cover:
- CustomerService create/associate
- User isolation
- Customer history
- Operational score
- Default templates + validation
- Placeholder validation
- Template preview
- Template CRUD + deactivation
- Collection rule CRUD
- Follow-up generation for overdue
- No duplicate follow-up same day
- Explicit confirmation via WhatsApp
- OpenAI fallback for templates
- Aggressive language blocked
- Collection logs created
- No banking operations
"""
import pytest
import pytest_asyncio
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.customer_service import CustomerService
from app.services.message_template_service import MessageTemplateService
from app.services.collection_service import CollectionService
from app.services.charge_service import ChargeService
from app.models.customer import Customer, CustomerStatus
from app.models.charge import Charge, ChargeStatus
from app.models.message_template import MessageTemplate, MessageTone
from app.models.collection_rule import CollectionRule, TriggerType
from app.models.collection_message_log import CollectionMessageLog, CollectionMessageStatus
from app.schemas.charge import ChargeCreate
from app.schemas.message_template import MessageTemplateCreate, ALLOWED_PLACEHOLDERS
from app.schemas.collection_rule import CollectionRuleCreate
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


class TestCustomerService:
    """Tests for CustomerService."""

    @pytest.mark.asyncio
    async def test_get_or_create_customer_new(self, db_session, sample_user):
        service = CustomerService(db_session)
        customer = await service.get_or_create_customer(
            user_id=sample_user.id, name="João Silva", phone="11999999999"
        )
        assert customer.id is not None
        assert customer.name == "João Silva"
        assert customer.phone == "11999999999"
        assert customer.user_id == sample_user.id

    @pytest.mark.asyncio
    async def test_get_or_create_customer_existing_by_name(self, db_session, sample_user):
        service = CustomerService(db_session)
        c1 = await service.get_or_create_customer(sample_user.id, "João Silva", "11999999999")
        c2 = await service.get_or_create_customer(sample_user.id, "João Silva", None)
        assert c1.id == c2.id

    @pytest.mark.asyncio
    async def test_get_or_create_customer_existing_by_phone(self, db_session, sample_user):
        service = CustomerService(db_session)
        c1 = await service.get_or_create_customer(sample_user.id, "João Silva", "11999999999")
        c2 = await service.get_or_create_customer(sample_user.id, "João Different", "11999999999")
        assert c1.id == c2.id

    @pytest.mark.asyncio
    async def test_get_or_create_customer_updates_phone(self, db_session, sample_user):
        service = CustomerService(db_session)
        c1 = await service.get_or_create_customer(sample_user.id, "João Silva", None)
        assert c1.phone is None
        c2 = await service.get_or_create_customer(sample_user.id, "João Silva", "11999999999")
        assert c2.id == c1.id
        assert c2.phone == "11999999999"

    @pytest.mark.asyncio
    async def test_user_isolation(self, db_session, sample_user, second_user):
        service = CustomerService(db_session)
        c1 = await service.get_or_create_customer(sample_user.id, "João Silva", "111")
        c2 = await service.get_or_create_customer(second_user.id, "João Silva", "111")
        assert c1.id != c2.id
        assert c1.user_id == sample_user.id
        assert c2.user_id == second_user.id

    @pytest.mark.asyncio
    async def test_list_customers(self, db_session, sample_user):
        service = CustomerService(db_session)
        await service.get_or_create_customer(sample_user.id, "João Silva", "111")
        await service.get_or_create_customer(sample_user.id, "Maria Santos", "222")
        result = await service.list_customers(sample_user.id)
        assert result["total"] == 2
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_customers_search(self, db_session, sample_user):
        service = CustomerService(db_session)
        await service.get_or_create_customer(sample_user.id, "João Silva", "111")
        await service.get_or_create_customer(sample_user.id, "Maria Santos", "222")
        result = await service.list_customers(sample_user.id, search="joão")
        assert result["total"] >= 1
        assert any("João" in i["name"] for i in result["items"])

    @pytest.mark.asyncio
    async def test_list_customers_user_isolation(self, db_session, sample_user, second_user):
        service = CustomerService(db_session)
        await service.get_or_create_customer(sample_user.id, "João Silva", "111")
        await service.get_or_create_customer(second_user.id, "Maria Santos", "222")
        result = await service.list_customers(sample_user.id)
        assert all(i["name"] != "Maria Santos" for i in result["items"])

    @pytest.mark.asyncio
    async def test_get_customer_charges(self, db_session, sample_user, sample_charge, paid_charge):
        service = CustomerService(db_session)
        customer = await service.get_or_create_customer(
            sample_user.id, sample_charge.customer_name, sample_charge.customer_phone
        )
        charges = await service.get_customer_charges(customer.id, sample_user.id)
        assert len(charges) == 2

    @pytest.mark.asyncio
    async def test_get_customer_charges_user_isolation(self, db_session, sample_user, second_user, sample_charge):
        service = CustomerService(db_session)
        customer = await service.get_or_create_customer(
            sample_user.id, sample_charge.customer_name, sample_charge.customer_phone
        )
        charges = await service.get_customer_charges(customer.id, second_user.id)
        assert len(charges) == 0

    @pytest.mark.asyncio
    async def test_customer_summary_with_overdue(self, db_session, sample_user, sample_charge):
        service = CustomerService(db_session)
        customer = await service.get_or_create_customer(
            sample_user.id, sample_charge.customer_name, sample_charge.customer_phone
        )
        summary = await service.get_customer_summary(customer, sample_user.id)
        assert summary["has_overdue"] is True
        assert summary["total_overdue_amount"] == 150.0
        assert summary["operational_status"] == CustomerStatus.LATE_PAYER.value

    @pytest.mark.asyncio
    async def test_customer_summary_good_payer(self, db_session, sample_user, paid_charge):
        service = CustomerService(db_session)
        customer = await service.get_or_create_customer(
            sample_user.id, paid_charge.customer_name, paid_charge.customer_phone
        )
        summary = await service.get_customer_summary(customer, sample_user.id)
        assert summary["operational_status"] == CustomerStatus.GOOD_PAYER.value
        assert summary["total_paid_amount"] == 200.0

    @pytest.mark.asyncio
    async def test_customer_summary_new_customer(self, db_session, sample_user):
        service = CustomerService(db_session)
        customer = await service.get_or_create_customer(sample_user.id, "Novo Cliente", "123")
        summary = await service.get_customer_summary(customer, sample_user.id)
        assert summary["operational_status"] == CustomerStatus.NEW_CUSTOMER.value
        assert summary["total_charges_count"] == 0

    @pytest.mark.asyncio
    async def test_customer_summary_frequent_late(self, db_session, sample_user, sample_organization):
        service = CustomerService(db_session)
        customer = await service.get_or_create_customer(sample_user.id, "Atrasado", "999")
        for i in range(3):
            charge = Charge(
                user_id=sample_user.id,
                organization_id=sample_organization.id,
                customer_name="Atrasado",
                customer_phone="999",
                amount=Decimal(f"{100 + i}.00"),
                provider="fake",
                status=ChargeStatus.PENDING,
                due_date=date.today() - timedelta(days=10 + i),
            )
            db_session.add(charge)
        await db_session.commit()
        summary = await service.get_customer_summary(customer, sample_user.id)
        assert summary["operational_status"] == CustomerStatus.FREQUENT_LATE.value
        assert summary["overdue_count"] == 3

    @pytest.mark.asyncio
    async def test_customer_detail(self, db_session, sample_user, sample_charge):
        service = CustomerService(db_session)
        customer = await service.get_or_create_customer(
            sample_user.id, sample_charge.customer_name, sample_charge.customer_phone
        )
        detail = await service.get_customer_detail(customer.id, sample_user.id)
        assert detail is not None
        assert detail["name"] == "João Silva"
        assert len(detail["charges"]) == 1

    @pytest.mark.asyncio
    async def test_customer_detail_not_found(self, db_session, sample_user):
        service = CustomerService(db_session)
        detail = await service.get_customer_detail(99999, sample_user.id)
        assert detail is None

    @pytest.mark.asyncio
    async def test_update_customer_notes(self, db_session, sample_user):
        service = CustomerService(db_session)
        customer = await service.get_or_create_customer(sample_user.id, "João", "111")
        updated = await service.update_customer_notes(customer.id, sample_user.id, "Cliente VIP")
        assert updated.notes == "Cliente VIP"

    @pytest.mark.asyncio
    async def test_auto_create_customer_on_charge(self, db_session, sample_user):
        service = ChargeService(db_session)
        charge_data = ChargeCreate(
            customer_name="Auto Cliente",
            customer_phone="555555555",
            amount=Decimal("50.00"),
            description="teste auto create",
        )
        charge = await service.create_charge(sample_user.id, charge_data)
        assert charge.id is not None

        customer_service = CustomerService(db_session)
        result = await customer_service.list_customers(sample_user.id, search="Auto Cliente")
        assert result["total"] == 1
        assert result["items"][0]["name"] == "Auto Cliente"


class TestMessageTemplateService:
    """Tests for MessageTemplateService."""

    @pytest.mark.asyncio
    async def test_create_template(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        data = MessageTemplateCreate(
            name="Test Template",
            tone=MessageTone.FRIENDLY,
            template_text="Olá, {customer_name}! R$ {amount}",
        )
        template = await service.create_template(sample_user.id, data)
        assert template.id is not None
        assert template.name == "Test Template"
        assert template.active is True

    @pytest.mark.asyncio
    async def test_create_template_invalid_placeholder(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        data = MessageTemplateCreate(
            name="Bad Template",
            template_text="Olá, {customer_name}! {forbidden_placeholder}",
        )
        with pytest.raises(ValueError, match="Unknown placeholders"):
            await service.create_template(sample_user.id, data)

    @pytest.mark.asyncio
    async def test_create_template_aggressive_language_blocked(self, db_session, sample_user):
        from pydantic import ValidationError
        service = MessageTemplateService(db_session)
        with pytest.raises(ValidationError, match="inappropriate language"):
            data = MessageTemplateCreate(
                name="Aggressive",
                template_text="Olá, {customer_name}, seu caloteiro! Pague R$ {amount}!",
            )
            await service.create_template(sample_user.id, data)

    @pytest.mark.asyncio
    async def test_render_template(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        data = MessageTemplateCreate(
            name="Render Test",
            template_text="Olá, {customer_name}! R$ {amount} - {description}",
        )
        template = await service.create_template(sample_user.id, data)
        rendered = service.render_template(template.template_text, {
            "customer_name": "João",
            "amount": "150.00",
            "description": "serviço",
            "due_date": "",
            "payment_link": "",
            "qr_code_note": "",
            "company_name": "",
        })
        assert "João" in rendered
        assert "150.00" in rendered
        assert "serviço" in rendered

    @pytest.mark.asyncio
    async def test_preview_template(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        data = MessageTemplateCreate(
            name="Preview Test",
            template_text="Olá, {customer_name}! Cobrança: R$ {amount}",
        )
        template = await service.create_template(sample_user.id, data)
        rendered = service.preview_template(template, {
            "customer_name": "Maria",
            "amount": "200.00",
            "description": "consultoria",
            "due_date": "2026-07-15",
            "payment_link": "https://example.com",
            "qr_code_note": "sandbox",
            "company_name": "PayFlow",
        })
        assert "Maria" in rendered
        assert "200.00" in rendered

    @pytest.mark.asyncio
    async def test_list_templates(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        data = MessageTemplateCreate(name="T1", template_text="Test {customer_name}")
        await service.create_template(sample_user.id, data)
        templates = await service.list_templates(sample_user.id)
        assert len(templates) == 1

    @pytest.mark.asyncio
    async def test_list_templates_active_only(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        t1 = await service.create_template(sample_user.id, MessageTemplateCreate(name="T1", template_text="Test {customer_name}"))
        t2 = await service.create_template(sample_user.id, MessageTemplateCreate(name="T2", template_text="Test2 {customer_name}"))
        await service.deactivate_template(t2.id, sample_user.id)
        active = await service.list_templates(sample_user.id, active_only=True)
        assert len(active) == 1
        assert active[0].name == "T1"

    @pytest.mark.asyncio
    async def test_deactivate_template(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        template = await service.create_template(sample_user.id, MessageTemplateCreate(name="T1", template_text="Test {customer_name}"))
        deactivated = await service.deactivate_template(template.id, sample_user.id)
        assert deactivated.active is False

    @pytest.mark.asyncio
    async def test_update_template(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        template = await service.create_template(sample_user.id, MessageTemplateCreate(name="T1", template_text="Test {customer_name}"))
        from app.schemas.message_template import MessageTemplateUpdate
        updated = await service.update_template(template.id, sample_user.id, MessageTemplateUpdate(name="Updated"))
        assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_seed_default_templates(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        await service.seed_default_templates(sample_user.id)
        templates = await service.list_templates(sample_user.id)
        assert len(templates) == 4
        tones = {t.tone for t in templates}
        assert MessageTone.FRIENDLY in tones
        assert MessageTone.NEUTRAL in tones
        assert MessageTone.FIRM in tones

    @pytest.mark.asyncio
    async def test_seed_default_templates_idempotent(self, db_session, sample_user):
        service = MessageTemplateService(db_session)
        await service.seed_default_templates(sample_user.id)
        await service.seed_default_templates(sample_user.id)
        templates = await service.list_templates(sample_user.id)
        assert len(templates) == 4

    @pytest.mark.asyncio
    async def test_template_user_isolation(self, db_session, sample_user, second_user):
        service = MessageTemplateService(db_session)
        await service.create_template(sample_user.id, MessageTemplateCreate(name="T1", template_text="Test {customer_name}"))
        templates = await service.list_templates(second_user.id)
        assert len(templates) == 0

    @pytest.mark.asyncio
    async def test_allowed_placeholders_complete(self):
        expected = {
            "{customer_name}", "{amount}", "{description}",
            "{due_date}", "{payment_link}", "{qr_code_note}", "{company_name}",
        }
        assert ALLOWED_PLACEHOLDERS == expected


class TestCollectionService:
    """Tests for CollectionService."""

    @pytest.mark.asyncio
    async def test_create_rule(self, db_session, sample_user):
        service = CollectionService(db_session)
        data = CollectionRuleCreate(
            name="2 dias antes",
            days_offset=2,
            trigger_type=TriggerType.BEFORE_DUE,
        )
        rule = await service.create_rule(sample_user.id, data)
        assert rule.id is not None
        assert rule.days_offset == 2

    @pytest.mark.asyncio
    async def test_list_rules(self, db_session, sample_user):
        service = CollectionService(db_session)
        await service.create_rule(sample_user.id, CollectionRuleCreate(name="R1", days_offset=2, trigger_type=TriggerType.BEFORE_DUE))
        await service.create_rule(sample_user.id, CollectionRuleCreate(name="R2", days_offset=3, trigger_type=TriggerType.AFTER_DUE))
        rules = await service.list_rules(sample_user.id)
        assert len(rules) == 2

    @pytest.mark.asyncio
    async def test_deactivate_rule(self, db_session, sample_user):
        service = CollectionService(db_session)
        rule = await service.create_rule(sample_user.id, CollectionRuleCreate(name="R1", days_offset=2, trigger_type=TriggerType.BEFORE_DUE))
        deactivated = await service.deactivate_rule(rule.id, sample_user.id)
        assert deactivated.active is False

    @pytest.mark.asyncio
    async def test_rule_user_isolation(self, db_session, sample_user, second_user):
        service = CollectionService(db_session)
        await service.create_rule(sample_user.id, CollectionRuleCreate(name="R1", days_offset=2, trigger_type=TriggerType.BEFORE_DUE))
        rules = await service.list_rules(second_user.id)
        assert len(rules) == 0

    @pytest.mark.asyncio
    async def test_get_overdue_charges(self, db_session, sample_user, sample_charge):
        service = CollectionService(db_session)
        overdue = await service.get_overdue_charges(sample_user.id)
        assert len(overdue) == 1
        assert overdue[0].customer_name == "João Silva"

    @pytest.mark.asyncio
    async def test_generate_followup_previews(self, db_session, sample_user, sample_charge):
        service = CollectionService(db_session)
        result = await service.generate_followup_previews(sample_user.id)
        assert result["total"] == 1
        assert result["items"][0]["customer_name"] == "João Silva"
        assert result["items"][0]["days_overdue"] == 5
        assert "João Silva" in result["items"][0]["rendered_message"]

    @pytest.mark.asyncio
    async def test_generate_followup_previews_empty(self, db_session, sample_user):
        service = CollectionService(db_session)
        result = await service.generate_followup_previews(sample_user.id)
        assert result["total"] == 0
        assert "Nenhuma" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_followup_previews_with_template(self, db_session, sample_user, sample_charge):
        mt_service = MessageTemplateService(db_session)
        await mt_service.create_template(sample_user.id, MessageTemplateCreate(
            name="Firm Template",
            tone=MessageTone.FIRM,
            template_text="Olá, {customer_name}! R$ {amount} vencido em {due_date}. Link: {payment_link}",
        ))
        service = CollectionService(db_session)
        result = await service.generate_followup_previews(sample_user.id)
        assert result["total"] == 1
        assert result["items"][0]["template_name"] == "Firm Template"

    @pytest.mark.asyncio
    async def test_log_message(self, db_session, sample_user, sample_charge):
        service = CollectionService(db_session)
        log = await service.log_message(
            user_id=sample_user.id,
            charge_id=sample_charge.id,
            customer_id=1,
            template_id=None,
            message_preview="Test message preview",
            status=CollectionMessageStatus.DRAFT,
        )
        assert log.id is not None
        assert log.status == CollectionMessageStatus.DRAFT.value

    @pytest.mark.asyncio
    async def test_already_sent_today(self, db_session, sample_user, sample_charge):
        service = CollectionService(db_session)
        assert await service.already_sent_today(sample_user.id, sample_charge.id) is False
        await service.log_message(
            user_id=sample_user.id,
            charge_id=sample_charge.id,
            customer_id=None,
            template_id=None,
            message_preview="test",
            status=CollectionMessageStatus.DRAFT,
        )
        assert await service.already_sent_today(sample_user.id, sample_charge.id) is True

    @pytest.mark.asyncio
    async def test_no_duplicate_followup_same_day(self, db_session, sample_user, sample_charge):
        service = CollectionService(db_session)
        await service.log_message(
            user_id=sample_user.id,
            charge_id=sample_charge.id,
            customer_id=None,
            template_id=None,
            message_preview="first",
            status=CollectionMessageStatus.DRAFT,
        )
        assert await service.already_sent_today(sample_user.id, sample_charge.id) is True

    @pytest.mark.asyncio
    async def test_list_logs(self, db_session, sample_user, sample_charge):
        service = CollectionService(db_session)
        await service.log_message(
            user_id=sample_user.id,
            charge_id=sample_charge.id,
            customer_id=None,
            template_id=None,
            message_preview="test log",
        )
        logs = await service.list_logs(sample_user.id)
        assert len(logs) == 1
        assert logs[0].message_preview == "test log"

    @pytest.mark.asyncio
    async def test_create_rule_with_invalid_template(self, db_session, sample_user):
        service = CollectionService(db_session)
        data = CollectionRuleCreate(
            name="Bad Rule",
            days_offset=2,
            trigger_type=TriggerType.BEFORE_DUE,
            template_id=99999,
        )
        with pytest.raises(ValueError, match="Template not found"):
            await service.create_rule(sample_user.id, data)


class TestWhatsAppCollectionIntents:
    """Tests for WhatsApp collection intent handlers."""

    @pytest.mark.asyncio
    async def test_handle_list_customers(self, db_session, sample_user):
        from app.routers.webhook import handle_list_customers
        from app.services.ai_service import AIService

        customer_service = CustomerService(db_session)
        await customer_service.get_or_create_customer(sample_user.id, "João Silva", "111")

        ai = AIService()
        result = await handle_list_customers(sample_user.id, {}, db_session, ai, "")
        assert "João Silva" in result

    @pytest.mark.asyncio
    async def test_handle_list_customers_empty(self, db_session, sample_user):
        from app.routers.webhook import handle_list_customers
        from app.services.ai_service import AIService

        ai = AIService()
        result = await handle_list_customers(sample_user.id, {}, db_session, ai, "")
        assert "nenhum cliente" in result.lower() or "não tem" in result.lower()

    @pytest.mark.asyncio
    async def test_handle_customer_summary(self, db_session, sample_user, sample_charge):
        from app.routers.webhook import handle_customer_summary
        from app.services.ai_service import AIService

        customer_service = CustomerService(db_session)
        await customer_service.get_or_create_customer(
            sample_user.id, sample_charge.customer_name, sample_charge.customer_phone
        )

        ai = AIService()
        result = await handle_customer_summary(
            sample_user.id, {"customer_name": "João Silva"}, db_session, ai, ""
        )
        assert "João Silva" in result

    @pytest.mark.asyncio
    async def test_handle_customer_summary_not_found(self, db_session, sample_user):
        from app.routers.webhook import handle_customer_summary
        from app.services.ai_service import AIService

        ai = AIService()
        result = await handle_customer_summary(
            sample_user.id, {"customer_name": "Inexistente"}, db_session, ai, ""
        )
        assert "Não encontrei" in result

    @pytest.mark.asyncio
    async def test_handle_generate_collection_message(self, db_session, sample_user, sample_charge):
        from app.routers.webhook import handle_generate_collection_message
        from app.services.ai_service import AIService

        customer_service = CustomerService(db_session)
        await customer_service.get_or_create_customer(
            sample_user.id, sample_charge.customer_name, sample_charge.customer_phone
        )

        ai = AIService()
        result = await handle_generate_collection_message(
            sample_user.id, {"customer_name": "João Silva", "tone": "neutral"}, db_session, ai, ""
        )
        assert "Rascunho" in result
        assert "João Silva" in result
        assert "Nenhuma mensagem foi enviada" in result

    @pytest.mark.asyncio
    async def test_handle_generate_collection_message_no_overdue(self, db_session, sample_user, paid_charge):
        from app.routers.webhook import handle_generate_collection_message
        from app.services.ai_service import AIService

        customer_service = CustomerService(db_session)
        await customer_service.get_or_create_customer(
            sample_user.id, paid_charge.customer_name, paid_charge.customer_phone
        )

        ai = AIService()
        result = await handle_generate_collection_message(
            sample_user.id, {"customer_name": "João Silva"}, db_session, ai, ""
        )
        assert "não tem cobranças vencidas" in result

    @pytest.mark.asyncio
    async def test_handle_prepare_overdue_followups(self, db_session, sample_user, sample_charge):
        from app.routers.webhook import handle_prepare_overdue_followups
        from app.services.ai_service import AIService

        ai = AIService()
        result = await handle_prepare_overdue_followups(sample_user.id, {}, db_session, ai, "")
        assert "1 cobrança" in result
        assert "João Silva" in result
        assert "Nenhuma mensagem será enviada" in result

    @pytest.mark.asyncio
    async def test_handle_prepare_overdue_followups_empty(self, db_session, sample_user):
        from app.routers.webhook import handle_prepare_overdue_followups
        from app.services.ai_service import AIService

        ai = AIService()
        result = await handle_prepare_overdue_followups(sample_user.id, {}, db_session, ai, "")
        assert "Nenhuma cobrança vencida" in result

    @pytest.mark.asyncio
    async def test_handle_list_collection_rules_empty(self, db_session, sample_user):
        from app.routers.webhook import handle_list_collection_rules
        from app.services.ai_service import AIService

        ai = AIService()
        result = await handle_list_collection_rules(sample_user.id, {}, db_session, ai, "")
        assert "não tem regras" in result

    @pytest.mark.asyncio
    async def test_handle_create_collection_rule(self, db_session, sample_user):
        from app.routers.webhook import handle_create_collection_rule
        from app.services.ai_service import AIService

        ai = AIService()
        result = await handle_create_collection_rule(
            sample_user.id,
            {"name": "Lembrete 2 dias antes", "days_offset": 2, "trigger_type": "before_due"},
            db_session, ai, "",
        )
        assert "Regra de cobrança criada" in result
        assert "não envia mensagens automaticamente" in result

    @pytest.mark.asyncio
    async def test_handle_list_message_templates_empty(self, db_session, sample_user):
        from app.routers.webhook import handle_list_message_templates
        from app.services.ai_service import AIService

        ai = AIService()
        result = await handle_list_message_templates(sample_user.id, {}, db_session, ai, "")
        assert "não tem templates" in result

    @pytest.mark.asyncio
    async def test_handle_list_message_templates_with_data(self, db_session, sample_user):
        from app.routers.webhook import handle_list_message_templates
        from app.services.ai_service import AIService

        mt_service = MessageTemplateService(db_session)
        await mt_service.create_template(sample_user.id, MessageTemplateCreate(
            name="Test Template", tone=MessageTone.FRIENDLY, template_text="Olá, {customer_name}!"
        ))

        ai = AIService()
        result = await handle_list_message_templates(sample_user.id, {}, db_session, ai, "")
        assert "Test Template" in result
        assert "amigável" in result


class TestExplicitConfirmation:
    """Tests for explicit confirmation flow — no auto-sending."""

    @pytest.mark.asyncio
    async def test_followup_preview_does_not_send(self, db_session, sample_user, sample_charge):
        """Generate followup previews should NOT send any message."""
        service = CollectionService(db_session)
        result = await service.generate_followup_previews(sample_user.id)
        assert result["total"] == 1
        assert "Deseja gerar" in result["message"] or "Nenhuma" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_message_creates_draft_log(self, db_session, sample_user, sample_charge):
        """Generating a collection message should create a DRAFT log, not SENT."""
        from app.routers.webhook import handle_generate_collection_message
        from app.services.ai_service import AIService

        customer_service = CustomerService(db_session)
        await customer_service.get_or_create_customer(
            sample_user.id, sample_charge.customer_name, sample_charge.customer_phone
        )

        ai = AIService()
        await handle_generate_collection_message(
            sample_user.id, {"customer_name": "João Silva", "tone": "firm"}, db_session, ai, ""
        )

        collection_service = CollectionService(db_session)
        logs = await collection_service.list_logs(sample_user.id)
        assert len(logs) == 1
        assert logs[0].status == CollectionMessageStatus.DRAFT.value


class TestNoBankingOperations:
    """Verify no banking operations are executed in any Sprint 9 flow."""

    @pytest.mark.asyncio
    async def test_followup_does_not_execute_payment(self, db_session, sample_user, sample_charge):
        service = CollectionService(db_session)
        result = await service.generate_followup_previews(sample_user.id)
        for item in result["items"]:
            assert "rendered_message" in item
            assert "charge_id" in item
        assert all("payment_link" not in item for item in result["items"])

    @pytest.mark.asyncio
    async def test_collection_rule_is_non_transactional(self, db_session, sample_user):
        service = CollectionService(db_session)
        rule = await service.create_rule(sample_user.id, CollectionRuleCreate(
            name="Test Rule", days_offset=3, trigger_type=TriggerType.AFTER_DUE,
        ))
        assert rule.active is True
        assert rule.template_id is None
