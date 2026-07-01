import pytest
from app.providers.provider_factory import get_payment_provider
from app.providers.fake_provider import FakePaymentProvider
from app.providers.mercado_pago_provider import MercadoPagoPaymentProvider


def test_factory_returns_fake_by_default():
    """Default provider is always fake."""
    provider = get_payment_provider("fake")
    assert provider.name == "fake"
    assert isinstance(provider, FakePaymentProvider)


def test_factory_raises_without_token_for_mercado_pago(monkeypatch):
    """Factory raises a clear error when mercado_pago is requested without token."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MERCADO_PAGO_ACCESS_TOKEN", None)

    # Reset the cached provider
    import app.providers.provider_factory as factory
    factory._PAYMENT_PROVIDER = None

    with pytest.raises(RuntimeError, match="MERCADO_PAGO_ACCESS_TOKEN"):
        get_payment_provider("mercado_pago")


def test_factory_falls_back_for_unknown_provider():
    """Unknown provider name falls back to fake."""
    provider = get_payment_provider("unknown_provider")
    assert provider.name == "fake"


def test_mercado_pago_parse_webhook_event():
    """Mercado Pago provider can parse a payment webhook event."""
    from unittest.mock import patch, MagicMock

    mock_mp = MagicMock()
    mock_mp.process_webhook_notification.return_value = {
        "type": "payment",
        "data": {
            "preference_id": "pref_123",
            "external_reference": "payflow_user_1",
            "status": "approved",
            "transaction_amount": 150.0,
            "date_approved": "2026-07-01T10:00:00Z"
        }
    }

    with patch.object(MercadoPagoPaymentProvider, "__init__", lambda self: setattr(self, "mp_service", mock_mp)):
        provider = MercadoPagoPaymentProvider()
        event = provider.parse_webhook_event({"type": "payment", "data": {"id": "123"}})

    assert event is not None
    assert event["provider_charge_id"] == "pref_123"
    assert event["status"] == "paid"
    assert event["event_type"] == "payment.approved"
