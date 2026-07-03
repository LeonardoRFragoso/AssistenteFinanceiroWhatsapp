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
    'mercado_pago' or 'asaas'. This keeps the development environment safe and
    prevents accidental real financial operations.
    """
    global _PAYMENT_PROVIDER

    if provider_name is None:
        provider_name = settings.PAYFLOW_PAYMENT_PROVIDER.lower().strip()

    if _PAYMENT_PROVIDER is not None and _PAYMENT_PROVIDER.name == provider_name:
        return _PAYMENT_PROVIDER

    if provider_name == "mercado_pago":
        if settings.ENABLE_DEMO_MODE:
            raise RuntimeError(
                "Demo mode is active but PAYFLOW_PAYMENT_PROVIDER is 'mercado_pago'. "
                "Demo mode requires PAYFLOW_PAYMENT_PROVIDER=fake. "
                "Set PAYFLOW_PAYMENT_PROVIDER=fake or disable demo mode."
            )
        if not settings.MERCADO_PAGO_ACCESS_TOKEN:
            raise RuntimeError(
                "PAYFLOW_PAYMENT_PROVIDER is set to 'mercado_pago' but "
                "MERCADO_PAGO_ACCESS_TOKEN is not configured. "
                "Set the token in .env or switch back to PAYFLOW_PAYMENT_PROVIDER=fake."
            )
        logger.info("Using Mercado Pago payment provider")
        _PAYMENT_PROVIDER = MercadoPagoPaymentProvider()
    elif provider_name == "asaas":
        if settings.ENABLE_DEMO_MODE:
            raise RuntimeError(
                "Demo mode is active. Asaas provider cannot be used in demo mode. "
                "Set ENABLE_DEMO_MODE=false or use PAYFLOW_PAYMENT_PROVIDER=fake."
            )
        if not settings.ENABLE_ASAAS_CHARGE_PROVIDER:
            raise RuntimeError(
                "Asaas charge provider is not enabled. "
                "Set ENABLE_ASAAS_CHARGE_PROVIDER=true to use it."
            )
        if not settings.ASAAS_API_KEY:
            raise RuntimeError(
                "ENABLE_ASAAS_CHARGE_PROVIDER=true but ASAAS_API_KEY is not set. "
                "Configure ASAAS_API_KEY or set ENABLE_ASAAS_CHARGE_PROVIDER=false."
            )
        from app.providers.asaas_provider import AsaasPaymentProvider
        logger.info(f"Using Asaas payment provider (environment={settings.ASAAS_ENVIRONMENT})")
        _PAYMENT_PROVIDER = AsaasPaymentProvider()
    elif provider_name == "fake":
        logger.info("Using fake payment provider (sandbox)")
        _PAYMENT_PROVIDER = FakePaymentProvider()
    else:
        if settings.ENVIRONMENT.lower() == "production":
            raise RuntimeError(
                f"Unknown payment provider '{provider_name}' in production. "
                "Set PAYFLOW_PAYMENT_PROVIDER to 'fake' or a supported provider."
            )
        logger.warning(f"Unknown payment provider '{provider_name}', falling back to fake provider")
        _PAYMENT_PROVIDER = FakePaymentProvider()

    return _PAYMENT_PROVIDER
