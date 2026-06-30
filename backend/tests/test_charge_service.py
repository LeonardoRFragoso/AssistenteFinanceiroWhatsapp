import pytest
from decimal import Decimal
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
