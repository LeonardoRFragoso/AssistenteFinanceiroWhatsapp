import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.charge_service import ChargeService
from app.services.charge_reminder_service import ChargeReminderService
from app.schemas.charge import ChargeCreate
from app.models.charge import ChargeStatus
from app.models.charge_reminder_log import ReminderType


@pytest.mark.asyncio
async def test_reminder_due_soon(db_session, sample_user):
    charge_service = ChargeService(db_session)
    tomorrow = date.today() + timedelta(days=1)
    await charge_service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Vencimento Próximo",
        amount=Decimal("150.00"),
        due_date=tomorrow,
        provider="fake"
    ))

    reminder_service = ChargeReminderService(db_session)
    result = await reminder_service.run_reminders()

    assert result["sent_due_soon"] == 1
    assert result["errors"] == 0


@pytest.mark.asyncio
async def test_reminder_overdue(db_session, sample_user):
    charge_service = ChargeService(db_session)
    past_date = date.today() - timedelta(days=5)
    await charge_service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Vencido",
        amount=Decimal("200.00"),
        due_date=past_date,
        provider="fake"
    ))

    reminder_service = ChargeReminderService(db_session)
    result = await reminder_service.run_reminders()

    assert result["sent_overdue"] == 1
    assert result["errors"] == 0


@pytest.mark.asyncio
async def test_reminder_no_duplicates(db_session, sample_user):
    charge_service = ChargeService(db_session)
    tomorrow = date.today() + timedelta(days=1)
    await charge_service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Sem Duplicata",
        amount=Decimal("100.00"),
        due_date=tomorrow,
        provider="fake"
    ))

    reminder_service = ChargeReminderService(db_session)
    first_run = await reminder_service.run_reminders()
    assert first_run["sent_due_soon"] == 1

    second_run = await reminder_service.run_reminders()
    assert second_run["sent_due_soon"] == 0
    assert second_run["skipped"] == 1


@pytest.mark.asyncio
async def test_reminder_no_pending_charges(db_session, sample_user):
    reminder_service = ChargeReminderService(db_session)
    result = await reminder_service.run_reminders()

    assert result["sent_due_soon"] == 0
    assert result["sent_overdue"] == 0
    assert result["total_processed"] == 0


@pytest.mark.asyncio
async def test_reminder_skips_paid_charges(db_session, sample_user):
    charge_service = ChargeService(db_session)
    tomorrow = date.today() + timedelta(days=1)
    charge = await charge_service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Pago",
        amount=Decimal("100.00"),
        due_date=tomorrow,
        provider="fake"
    ))
    payload = {
        "event_type": "payment.approved",
        "provider_charge_id": charge.provider_charge_id,
        "amount": 100.0
    }
    await charge_service.process_webhook_payload("fake", payload)

    reminder_service = ChargeReminderService(db_session)
    result = await reminder_service.run_reminders()

    assert result["sent_due_soon"] == 0
    assert result["sent_overdue"] == 0
