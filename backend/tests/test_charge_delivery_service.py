import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.charge_service import ChargeService
from app.services.charge_delivery_service import ChargeDeliveryService
from app.schemas.charge import ChargeCreate
from app.models.charge import ChargeStatus


@pytest.mark.asyncio
async def test_delivery_no_phone(db_session, sample_user):
    """Delivery fails gracefully when charge has no customer phone."""
    service = ChargeService(db_session)
    charge = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Sem Telefone",
        amount=Decimal("100.00"),
        provider="fake"
    ))

    delivery = ChargeDeliveryService(db_session)
    result = await delivery.send_charge_link_to_customer(charge, sample_user.id)
    assert result["success"] is False
    assert "telefone" in result["message"].lower()


@pytest.mark.asyncio
async def test_delivery_simulated_when_twilio_not_configured(db_session, sample_user, monkeypatch):
    """Delivery is simulated when Twilio is not configured."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", None)
    monkeypatch.setattr(settings, "TWILIO_WHATSAPP_NUMBER", None)

    service = ChargeService(db_session)
    charge = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Com Telefone",
        customer_phone="+5511888888888",
        amount=Decimal("150.00"),
        provider="fake"
    ))

    delivery = ChargeDeliveryService(db_session)
    result = await delivery.send_charge_link_to_customer(charge, sample_user.id)
    assert result["success"] is True
    assert result["simulated"] is True


@pytest.mark.asyncio
async def test_delivery_logs_created(db_session, sample_user, monkeypatch):
    """Delivery logs are persisted even for simulated sends."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", None)
    monkeypatch.setattr(settings, "TWILIO_WHATSAPP_NUMBER", None)

    from app.repositories.charge_delivery_log_repository import ChargeDeliveryLogRepository
    from app.models.charge_delivery_log import DeliveryStatus

    service = ChargeService(db_session)
    charge = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente Log",
        customer_phone="+5511777777777",
        amount=Decimal("200.00"),
        provider="fake"
    ))

    delivery = ChargeDeliveryService(db_session)
    await delivery.send_charge_link_to_customer(charge, sample_user.id)

    repo = ChargeDeliveryLogRepository(db_session)
    logs = await repo.get_by_charge_id(charge.id)
    assert len(logs) == 1
    assert logs[0].status == DeliveryStatus.SIMULATED
