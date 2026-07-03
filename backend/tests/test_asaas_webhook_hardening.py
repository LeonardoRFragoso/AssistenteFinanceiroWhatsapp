"""
Tests for Asaas webhook hardening — Sprint 15.1.
Covers: token validation, idempotency, duplicate events, unknown events,
charge not found, provider_event_id fallback, payload sanitization.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from app.models.charge import Charge, ChargeStatus
from app.models.provider_event import ProviderEvent


def test_asaas_webhook_valid_token():
    """Valid token should pass validation."""
    from app.core.config import settings
    from app.providers.asaas_provider import AsaasPaymentProvider

    old_token = settings.ASAAS_WEBHOOK_TOKEN
    try:
        settings.ASAAS_WEBHOOK_TOKEN = "valid-token-32chars-minimum-length!!!"
        provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
        provider.name = "asaas"
        headers = {"asaas-access-token": "valid-token-32chars-minimum-length!!!"}
        assert provider.validate_webhook(headers, {}) is True
    finally:
        settings.ASAAS_WEBHOOK_TOKEN = old_token


def test_asaas_webhook_invalid_token():
    """Invalid token should fail validation."""
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


def test_asaas_webhook_missing_token():
    """Missing token header should fail validation."""
    from app.providers.asaas_provider import AsaasPaymentProvider

    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    assert provider.validate_webhook({}, {}) is False


def test_asaas_webhook_no_configured_token_rejects():
    """Missing ASAAS_WEBHOOK_TOKEN should reject all webhooks."""
    from app.core.config import settings
    from app.providers.asaas_provider import AsaasPaymentProvider

    old_token = settings.ASAAS_WEBHOOK_TOKEN
    try:
        settings.ASAAS_WEBHOOK_TOKEN = None
        provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
        provider.name = "asaas"
        headers = {"asaas-access-token": "some-token"}
        assert provider.validate_webhook(headers, {}) is False
    finally:
        settings.ASAAS_WEBHOOK_TOKEN = old_token


def test_asaas_webhook_unknown_event_returns_safe():
    """Unknown event should return event with status=None (safe)."""
    from app.providers.asaas_provider import AsaasPaymentProvider

    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_unknown",
        "event": "SOME_RANDOM_EVENT",
        "payment": {"id": "pay_001"}
    }
    event = provider.parse_webhook_event(payload)
    assert event is not None
    assert event["status"] is None
    assert "some_random_event" in event["event_type"]


def test_asaas_webhook_sanitizes_raw_data():
    """parse_webhook_event should sanitize sensitive keys in raw_data."""
    from app.providers.asaas_provider import AsaasPaymentProvider

    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_001",
        "event": "PAYMENT_RECEIVED",
        "payment": {"id": "pay_001", "value": 100.0},
        "access_token": "secret-should-be-redacted",
        "api_key": "key-should-be-redacted",
    }
    event = provider.parse_webhook_event(payload)
    assert event is not None
    assert event["raw_data"]["access_token"] == "[REDACTED]"
    assert event["raw_data"]["api_key"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_duplicate_webhook_does_not_reprocess(db_session, sample_user, sample_organization):
    """Duplicate webhook event should not re-process or double-update charge."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_dup001",
        status=ChargeStatus.PAID,
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    payload = {
        "id": "evt_dup001",
        "event": "PAYMENT_RECEIVED",
        "payment": {"id": "pay_dup001", "value": 100.0}
    }

    service = ChargeService(db_session)
    result = await service.process_webhook_payload("asaas", payload)
    assert result is not None
    assert result.status == ChargeStatus.PAID
    assert result.paid_at == charge.paid_at


@pytest.mark.asyncio
async def test_webhook_charge_not_found_returns_none(db_session, sample_user, sample_organization):
    """Webhook for non-existent charge should return None without exploding."""
    from app.services.charge_service import ChargeService

    payload = {
        "id": "evt_notfound",
        "event": "PAYMENT_RECEIVED",
        "payment": {"id": "pay_nonexistent", "value": 50.0}
    }

    service = ChargeService(db_session)
    result = await service.process_webhook_payload("asaas", payload)
    assert result is None


@pytest.mark.asyncio
async def test_webhook_payment_overdue_updates_expired(db_session, sample_user, sample_organization):
    """PAYMENT_OVERDUE should update charge to expired."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_overdue001",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    payload = {
        "id": "evt_overdue001",
        "event": "PAYMENT_OVERDUE",
        "payment": {"id": "pay_overdue001"}
    }

    service = ChargeService(db_session)
    result = await service.process_webhook_payload("asaas", payload)
    assert result is not None
    assert result.status == ChargeStatus.EXPIRED


@pytest.mark.asyncio
async def test_webhook_payment_deleted_updates_cancelled(db_session, sample_user, sample_organization):
    """PAYMENT_DELETED should update charge to cancelled."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_del001",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    payload = {
        "id": "evt_del001",
        "event": "PAYMENT_DELETED",
        "payment": {"id": "pay_del001"}
    }

    service = ChargeService(db_session)
    result = await service.process_webhook_payload("asaas", payload)
    assert result is not None
    assert result.status == ChargeStatus.CANCELLED


@pytest.mark.asyncio
async def test_webhook_cancelled_charge_ignores_event(db_session, sample_user, sample_organization):
    """Already cancelled charge should ignore further webhook events."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_cancelled001",
        status=ChargeStatus.CANCELLED,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    payload = {
        "id": "evt_after_cancel",
        "event": "PAYMENT_RECEIVED",
        "payment": {"id": "pay_cancelled001", "value": 100.0}
    }

    service = ChargeService(db_session)
    result = await service.process_webhook_payload("asaas", payload)
    assert result is not None
    assert result.status == ChargeStatus.CANCELLED


@pytest.mark.asyncio
async def test_webhook_without_event_id_uses_fallback(db_session, sample_user, sample_organization):
    """Webhook without event_id should still be processable via fallback idempotency."""
    from app.services.charge_service import ChargeService

    charge = Charge(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        customer_name="Test",
        amount=Decimal("100.00"),
        provider="asaas",
        provider_charge_id="pay_noeventid",
        status=ChargeStatus.PENDING,
    )
    db_session.add(charge)
    await db_session.commit()
    await db_session.refresh(charge)

    payload = {
        "event": "PAYMENT_RECEIVED",
        "payment": {"id": "pay_noeventid", "value": 100.0}
    }

    service = ChargeService(db_session)
    result = await service.process_webhook_payload("asaas", payload)
    assert result is not None
    assert result.status == ChargeStatus.PAID
