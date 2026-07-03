"""
Tests for Asaas webhook endpoint and charge sync.
Sprint 15 — Asaas sandbox provider.
"""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from app.models.charge import Charge, ChargeStatus
from app.models.provider_event import ProviderEvent


def test_asaas_webhook_invalid_token_rejected():
    """Asaas webhook validation should reject invalid token."""
    from app.core.config import settings
    from app.providers.asaas_provider import AsaasPaymentProvider

    old_token = settings.ASAAS_WEBHOOK_TOKEN
    try:
        settings.ASAAS_WEBHOOK_TOKEN = "correct-token-32chars-minimum!!!"
        provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
        provider.name = "asaas"
        headers = {"asaas-access-token": "wrong-token"}
        assert provider.validate_webhook(headers, {}) is False
    finally:
        settings.ASAAS_WEBHOOK_TOKEN = old_token


def test_asaas_webhook_missing_token_rejected():
    """Asaas webhook validation should reject missing token."""
    from app.providers.asaas_provider import AsaasPaymentProvider

    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    headers = {}
    assert provider.validate_webhook(headers, {}) is False


@pytest.mark.asyncio
async def test_charge_model_has_asaas_fields(db_session, sample_user, sample_organization):
    """Charge model should have provider_bank_slip_url and provider_status fields."""
    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test Customer",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_test123",
        payment_link="https://sandbox.asaas.com/i/test",
        status=ChargeStatus.PENDING,
        provider_bank_slip_url="https://sandbox.asaas.com/b/test.pdf",
        provider_status="PENDING",
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    assert charge.provider_bank_slip_url == "https://sandbox.asaas.com/b/test.pdf"
    assert charge.provider_status == "PENDING"
    assert charge.provider == "asaas"


@pytest.mark.asyncio
async def test_charge_create_with_billing_type(db_session, sample_user, sample_organization):
    """ChargeCreate schema should accept billing_type."""
    from app.schemas.charge import ChargeCreate

    charge_data = ChargeCreate(
        customer_name="Test Customer",
        amount=Decimal("50.00"),
        billing_type="pix",
        description="Test charge",
    )
    assert charge_data.billing_type == "pix"


@pytest.mark.asyncio
async def test_charge_response_includes_asaas_fields(db_session, sample_user, sample_organization):
    """ChargeResponse schema should include provider_bank_slip_url and provider_status."""
    from app.schemas.charge import ChargeResponse

    charge = Charge(
        id=1,
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_001",
        status=ChargeStatus.PENDING,
        provider_bank_slip_url="https://example.com/boleto.pdf",
        provider_status="PENDING",
        created_at=datetime.now(timezone.utc),
    )
    charge.updated_at = datetime.now(timezone.utc)
    resp = ChargeResponse.model_validate(charge, from_attributes=True)
    assert resp.provider_bank_slip_url == "https://example.com/boleto.pdf"
    assert resp.provider_status == "PENDING"
    assert resp.provider == "asaas"


@pytest.mark.asyncio
async def test_sync_provider_status_already_paid(db_session, sample_user, sample_organization):
    """sync_provider_status should skip if charge is already paid."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="fake",
        provider_charge_id="fake_001",
        status=ChargeStatus.PAID,
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    service = ChargeService(db_session)
    result = await service.sync_provider_status(charge.id, sample_user.id, organization_id=sample_organization.id)
    assert result is not None
    assert result.status == ChargeStatus.PAID


@pytest.mark.asyncio
async def test_sync_provider_status_no_provider_charge_id(db_session, sample_user, sample_organization):
    """sync_provider_status should return charge if no provider_charge_id."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="fake",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    service = ChargeService(db_session)
    result = await service.sync_provider_status(charge.id, sample_user.id, organization_id=sample_organization.id)
    assert result is not None
    assert result.status == ChargeStatus.PENDING


@pytest.mark.asyncio
async def test_process_webhook_payload_asaas_payment_received(db_session, sample_user, sample_organization):
    """process_webhook_payload should process Asaas PAYMENT_RECEIVED event."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_test001",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    payload = {
        "id": "evt_test001",
        "event": "PAYMENT_RECEIVED",
        "payment": {
            "id": "pay_test001",
            "value": 100.00,
        }
    }

    service = ChargeService(db_session)
    result = await service.process_webhook_payload("asaas", payload)
    assert result is not None
    assert result.status == ChargeStatus.PAID
