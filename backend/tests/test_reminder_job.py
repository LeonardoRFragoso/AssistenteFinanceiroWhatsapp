import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.charge_service import ChargeService
from app.services.charge_reminder_service import ChargeReminderService
from app.schemas.charge import ChargeCreate


@pytest.mark.asyncio
async def test_reminder_job_runs(db_session, sample_user):
    """The reminder service runs and returns a summary dict."""
    service = ChargeService(db_session)
    past_date = date.today() - timedelta(days=3)
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Vencida Job",
        amount=Decimal("100.00"),
        due_date=past_date,
        provider="fake"
    ))

    reminder_service = ChargeReminderService(db_session)
    result = await reminder_service.run_reminders()

    assert "sent_due_soon" in result
    assert "sent_overdue" in result
    assert "skipped" in result
    assert "errors" in result
    assert "total_processed" in result
    assert result["total_processed"] >= 1


@pytest.mark.asyncio
async def test_reminder_job_no_duplicates(db_session, sample_user):
    """Running the reminder service twice in the same day skips duplicates."""
    service = ChargeService(db_session)
    past_date = date.today() - timedelta(days=2)
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Vencida Dup",
        amount=Decimal("50.00"),
        due_date=past_date,
        provider="fake"
    ))

    reminder_service = ChargeReminderService(db_session)
    first = await reminder_service.run_reminders()
    second = await reminder_service.run_reminders()

    assert second["skipped"] >= first["sent_overdue"] + first["sent_due_soon"]
