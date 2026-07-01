import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.charge_service import ChargeService
from app.schemas.charge import ChargeCreate
from app.models.charge import ChargeStatus


@pytest.mark.asyncio
async def test_create_charge_with_fake_provider(db_session, sample_user):
    service = ChargeService(db_session)
    data = ChargeCreate(
        customer_name="Maria Cliente",
        customer_phone="11988888888",
        amount=Decimal("89.90"),
        description="Consultoria",
        provider="fake"
    )

    charge = await service.create_charge(sample_user.id, data)

    assert charge.id is not None
    assert charge.user_id == sample_user.id
    assert charge.customer_name == "Maria Cliente"
    assert charge.amount == Decimal("89.90")
    assert charge.status == ChargeStatus.PENDING
    assert charge.provider == "fake"
    assert charge.provider_charge_id.startswith("fake_")
    assert charge.payment_link is not None


@pytest.mark.asyncio
async def test_list_user_charges(db_session, sample_user):
    service = ChargeService(db_session)
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente A",
        amount=Decimal("100.00")
    ))
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente B",
        amount=Decimal("200.00")
    ))

    charges = await service.get_user_charges(sample_user.id)
    assert len(charges) == 2


@pytest.mark.asyncio
async def test_cancel_charge(db_session, sample_user):
    service = ChargeService(db_session)
    charge = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente C",
        amount=Decimal("50.00")
    ))

    cancelled = await service.cancel_charge(charge.id, sample_user.id)
    assert cancelled is not None
    assert cancelled.status == ChargeStatus.CANCELLED


@pytest.mark.asyncio
async def test_process_fake_payment_webhook(db_session, sample_user):
    service = ChargeService(db_session)
    charge = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente D",
        amount=Decimal("150.00")
    ))

    payload = {
        "event_type": "payment.approved",
        "provider_charge_id": charge.provider_charge_id,
        "amount": 150.0
    }

    updated = await service.process_webhook_payload("fake", payload)
    assert updated is not None
    assert updated.id == charge.id
    assert updated.status == ChargeStatus.PAID
    assert updated.paid_at is not None


@pytest.mark.asyncio
async def test_create_charge_with_due_date(db_session, sample_user):
    service = ChargeService(db_session)
    tomorrow = date.today() + timedelta(days=1)
    data = ChargeCreate(
        customer_name="Cliente Vencimento",
        amount=Decimal("200.00"),
        due_date=tomorrow,
        provider="fake"
    )

    charge = await service.create_charge(sample_user.id, data)
    assert charge.due_date == tomorrow
    assert charge.status == ChargeStatus.PENDING


@pytest.mark.asyncio
async def test_get_summary(db_session, sample_user):
    service = ChargeService(db_session)

    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Pendente",
        amount=Decimal("100.00")
    ))
    paid_charge = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Pago",
        amount=Decimal("200.00")
    ))
    payload = {
        "event_type": "payment.approved",
        "provider_charge_id": paid_charge.provider_charge_id,
        "amount": 200.0
    }
    await service.process_webhook_payload("fake", payload)

    summary = await service.get_summary(sample_user.id)
    assert summary.count_pending == 1
    assert summary.count_paid == 1
    assert summary.total_paid == Decimal("200.00")
    assert summary.total_pending == Decimal("100.00")


@pytest.mark.asyncio
async def test_summary_with_overdue(db_session, sample_user):
    service = ChargeService(db_session)
    past_date = date.today() - timedelta(days=5)
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Vencido",
        amount=Decimal("300.00"),
        due_date=past_date,
        provider="fake"
    ))

    summary = await service.get_summary(sample_user.id)
    assert summary.count_overdue == 1
    assert summary.total_overdue == Decimal("300.00")


@pytest.mark.asyncio
async def test_derived_status_overdue(db_session, sample_user):
    service = ChargeService(db_session)
    past_date = date.today() - timedelta(days=1)
    charge = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Vencido",
        amount=Decimal("50.00"),
        due_date=past_date,
        provider="fake"
    ))

    derived = service.get_derived_status(charge)
    assert derived == "overdue"


@pytest.mark.asyncio
async def test_derived_status_pending(db_session, sample_user):
    service = ChargeService(db_session)
    charge = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Pendente",
        amount=Decimal("50.00"),
        provider="fake"
    ))

    derived = service.get_derived_status(charge)
    assert derived == "pending"


@pytest.mark.asyncio
async def test_cancel_paid_charge_fails(db_session, sample_user):
    service = ChargeService(db_session)
    charge = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Pago",
        amount=Decimal("100.00"),
        provider="fake"
    ))
    payload = {
        "event_type": "payment.approved",
        "provider_charge_id": charge.provider_charge_id,
        "amount": 100.0
    }
    await service.process_webhook_payload("fake", payload)

    result = await service.cancel_charge(charge.id, sample_user.id)
    assert result is None


@pytest.mark.asyncio
async def test_filter_charges_by_status(db_session, sample_user):
    service = ChargeService(db_session)
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Pendente 1",
        amount=Decimal("100.00"),
        provider="fake"
    ))
    paid = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Pago 1",
        amount=Decimal("200.00"),
        provider="fake"
    ))
    payload = {
        "event_type": "payment.approved",
        "provider_charge_id": paid.provider_charge_id,
        "amount": 200.0
    }
    await service.process_webhook_payload("fake", payload)

    pending_charges = await service.get_user_charges(sample_user.id, status="pending")
    assert len(pending_charges) == 1
    assert pending_charges[0].customer_name == "Pendente 1"

    paid_charges = await service.get_user_charges(sample_user.id, status="paid")
    assert len(paid_charges) == 1
    assert paid_charges[0].customer_name == "Pago 1"


@pytest.mark.asyncio
async def test_find_by_customer_name(db_session, sample_user):
    service = ChargeService(db_session)
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="João Silva",
        amount=Decimal("100.00"),
        provider="fake"
    ))
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Maria Santos",
        amount=Decimal("200.00"),
        provider="fake"
    ))

    results = await service.find_charges_by_customer_name(sample_user.id, "João")
    assert len(results) == 1
    assert results[0].customer_name == "João Silva"


@pytest.mark.asyncio
async def test_get_pending_charges(db_session, sample_user):
    service = ChargeService(db_session)
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Pendente",
        amount=Decimal("100.00"),
        provider="fake"
    ))
    paid = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Pago",
        amount=Decimal("200.00"),
        provider="fake"
    ))
    payload = {
        "event_type": "payment.approved",
        "provider_charge_id": paid.provider_charge_id,
        "amount": 200.0
    }
    await service.process_webhook_payload("fake", payload)

    pending = await service.get_pending_charges(sample_user.id)
    assert len(pending) == 1
    assert pending[0].customer_name == "Pendente"


@pytest.mark.asyncio
async def test_get_paid_charges(db_session, sample_user):
    service = ChargeService(db_session)
    paid = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Pago",
        amount=Decimal("200.00"),
        provider="fake"
    ))
    payload = {
        "event_type": "payment.approved",
        "provider_charge_id": paid.provider_charge_id,
        "amount": 200.0
    }
    await service.process_webhook_payload("fake", payload)

    paid_charges = await service.get_paid_charges(sample_user.id)
    assert len(paid_charges) == 1
    assert paid_charges[0].status == ChargeStatus.PAID

