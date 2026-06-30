from typing import Optional
from app.providers.base import PaymentProvider
from app.providers.fake_provider import FakePaymentProvider
from app.providers.mercado_pago_provider import MercadoPagoPaymentProvider
from app.core.config import settings
from app.core.logging import logger


_PAYMENT_PROVIDER: Optional[PaymentProvider] = None


def get_payment_provider(provider_name: Optional[str] = None) -> PaymentProvider:
    """Return a configured PaymentProvider instance.

    Defaults to the fake provider unless PAYFLOW_PAYMENT_PROVIDER is set to
    'mercado_pago'. This keeps the development environment safe and prevents
    accidental real financial operations.
    """
    global _PAYMENT_PROVIDER

    if provider_name is None:
        provider_name = settings.PAYFLOW_PAYMENT_PROVIDER.lower().strip()

    if _PAYMENT_PROVIDER is not None and _PAYMENT_PROVIDER.name == provider_name:
        return _PAYMENT_PROVIDER

    if provider_name == "mercado_pago":
        logger.info("Using Mercado Pago payment provider")
        _PAYMENT_PROVIDER = MercadoPagoPaymentProvider()
    elif provider_name == "fake":
        logger.info("Using fake payment provider (sandbox)")
        _PAYMENT_PROVIDER = FakePaymentProvider()
    else:
        logger.warning(f"Unknown payment provider '{provider_name}', falling back to fake provider")
        _PAYMENT_PROVIDER = FakePaymentProvider()

    return _PAYMENT_PROVIDER
