"""
Tests for AsaasPaymentProvider webhook parsing and validation.
Sprint 15 — Asaas sandbox provider.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime

from app.providers.asaas_provider import AsaasPaymentProvider, _ASAAS_STATUS_MAP, _ASAAS_EVENT_MAP, _BILLING_TYPE_MAP, _generate_sandbox_cpf


def test_asaas_status_map():
    """Asaas status mapping should cover all key statuses."""
    assert _ASAAS_STATUS_MAP["PENDING"] == "pending"
    assert _ASAAS_STATUS_MAP["RECEIVED"] == "paid"
    assert _ASAAS_STATUS_MAP["CONFIRMED"] == "paid"
    assert _ASAAS_STATUS_MAP["OVERDUE"] == "expired"
    assert _ASAAS_STATUS_MAP["DELETED"] == "cancelled"
    assert _ASAAS_STATUS_MAP["REFUNDED"] == "cancelled"
    assert _ASAAS_STATUS_MAP["RECEIVED_IN_CASH_UNDONE"] == "pending"
    assert _ASAAS_STATUS_MAP["RESTORED"] == "pending"


def test_asaas_event_map():
    """Asaas event mapping should cover all key events."""
    assert _ASAAS_EVENT_MAP["PAYMENT_CREATED"] == "payment.created"
    assert _ASAAS_EVENT_MAP["PAYMENT_RECEIVED"] == "payment.received"
    assert _ASAAS_EVENT_MAP["PAYMENT_CONFIRMED"] == "payment.confirmed"
    assert _ASAAS_EVENT_MAP["PAYMENT_OVERDUE"] == "payment.overdue"
    assert _ASAAS_EVENT_MAP["PAYMENT_DELETED"] == "payment.deleted"
    assert _ASAAS_EVENT_MAP["PAYMENT_REFUNDED"] == "payment.refunded"
    assert _ASAAS_EVENT_MAP["PAYMENT_RESTORED"] == "payment.restored"


def test_billing_type_map():
    """Billing type mapping should cover PIX, BOLETO, UNDEFINED, CREDIT_CARD."""
    assert _BILLING_TYPE_MAP["pix"] == "PIX"
    assert _BILLING_TYPE_MAP["boleto"] == "BOLETO"
    assert _BILLING_TYPE_MAP["undefined"] == "UNDEFINED"
    assert _BILLING_TYPE_MAP["credit_card"] == "CREDIT_CARD"


def test_generate_sandbox_cpf_valid_format():
    """Generated sandbox CPF should have 11 digits."""
    cpf = _generate_sandbox_cpf()
    assert len(cpf) == 11
    assert cpf.isdigit()


def test_parse_webhook_payment_received():
    """parse_webhook_event should map PAYMENT_RECEIVED to paid."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_001",
        "event": "PAYMENT_RECEIVED",
        "payment": {
            "object": "payment",
            "id": "pay_abc123",
            "value": 100.50,
        }
    }
    event = provider.parse_webhook_event(payload)
    assert event is not None
    assert event["event_type"] == "payment.received"
    assert event["provider_charge_id"] == "pay_abc123"
    assert event["status"] == "paid"
    assert event["amount"] == Decimal("100.50")
    assert event["paid_at"] is not None


def test_parse_webhook_payment_confirmed():
    """parse_webhook_event should map PAYMENT_CONFIRMED to paid."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_002",
        "event": "PAYMENT_CONFIRMED",
        "payment": {"id": "pay_def456"}
    }
    event = provider.parse_webhook_event(payload)
    assert event is not None
    assert event["status"] == "paid"


def test_parse_webhook_payment_overdue():
    """parse_webhook_event should map PAYMENT_OVERDUE to expired."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_003",
        "event": "PAYMENT_OVERDUE",
        "payment": {"id": "pay_xyz789"}
    }
    event = provider.parse_webhook_event(payload)
    assert event is not None
    assert event["status"] == "expired"


def test_parse_webhook_payment_deleted():
    """parse_webhook_event should map PAYMENT_DELETED to cancelled."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_004",
        "event": "PAYMENT_DELETED",
        "payment": {"id": "pay_del001"}
    }
    event = provider.parse_webhook_event(payload)
    assert event is not None
    assert event["status"] == "cancelled"


def test_parse_webhook_payment_refunded():
    """parse_webhook_event should map PAYMENT_REFUNDED to cancelled."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_005",
        "event": "PAYMENT_REFUNDED",
        "payment": {"id": "pay_ref001"}
    }
    event = provider.parse_webhook_event(payload)
    assert event is not None
    assert event["status"] == "cancelled"


def test_parse_webhook_payment_restored():
    """parse_webhook_event should map PAYMENT_RESTORED to pending."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_006",
        "event": "PAYMENT_RESTORED",
        "payment": {"id": "pay_res001"}
    }
    event = provider.parse_webhook_event(payload)
    assert event is not None
    assert event["status"] == "pending"


def test_parse_webhook_without_payment_id():
    """parse_webhook_event should return None if payment id is missing."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_007",
        "event": "PAYMENT_RECEIVED",
        "payment": {}
    }
    event = provider.parse_webhook_event(payload)
    assert event is None


def test_parse_webhook_unknown_event():
    """parse_webhook_event should handle unknown events gracefully."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    payload = {
        "id": "evt_008",
        "event": "UNKNOWN_EVENT",
        "payment": {"id": "pay_unk001"}
    }
    event = provider.parse_webhook_event(payload)
    assert event is not None
    assert event["event_type"] == "payment.unknown_event"
    assert event["status"] is None


def test_validate_webhook_valid_token():
    """validate_webhook should return True for matching token."""
    from app.core.config import settings
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    old_token = settings.ASAAS_WEBHOOK_TOKEN
    try:
        settings.ASAAS_WEBHOOK_TOKEN = "test-webhook-token-32chars-min!!!"
        headers = {"asaas-access-token": "test-webhook-token-32chars-min!!!"}
        assert provider.validate_webhook(headers, {}) is True
    finally:
        settings.ASAAS_WEBHOOK_TOKEN = old_token


def test_validate_webhook_invalid_token():
    """validate_webhook should return False for non-matching token."""
    from app.core.config import settings
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    old_token = settings.ASAAS_WEBHOOK_TOKEN
    try:
        settings.ASAAS_WEBHOOK_TOKEN = "correct-token-32chars-minimum!!!"
        headers = {"asaas-access-token": "wrong-token"}
        assert provider.validate_webhook(headers, {}) is False
    finally:
        settings.ASAAS_WEBHOOK_TOKEN = old_token


def test_validate_webhook_missing_token():
    """validate_webhook should return False when token header is missing."""
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    headers = {}
    assert provider.validate_webhook(headers, {}) is False


def test_validate_webhook_no_configured_token():
    """validate_webhook should return False when ASAAS_WEBHOOK_TOKEN is not set."""
    from app.core.config import settings
    provider = AsaasPaymentProvider.__new__(AsaasPaymentProvider)
    provider.name = "asaas"
    old_token = settings.ASAAS_WEBHOOK_TOKEN
    try:
        settings.ASAAS_WEBHOOK_TOKEN = None
        headers = {"asaas-access-token": "some-token"}
        assert provider.validate_webhook(headers, {}) is False
    finally:
        settings.ASAAS_WEBHOOK_TOKEN = old_token
