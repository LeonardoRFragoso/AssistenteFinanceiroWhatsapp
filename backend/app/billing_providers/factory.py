from app.billing_providers.base import BaseBillingProvider
from app.billing_providers.fake_billing_provider import FakeBillingProvider
from app.core.config import settings
from app.core.logging import logger


def get_billing_provider(provider_name: str | None = None) -> BaseBillingProvider:
    """Get the billing provider instance.

    This is SEPARATE from get_payment_provider which handles charges.
    Default is 'fake' (no real payments).
    """
    name = provider_name or settings.PAYFLOW_BILLING_PROVIDER

    if name == "fake":
        return FakeBillingProvider()
    elif name == "stripe_sandbox":
        logger.warning("Stripe sandbox billing provider not fully implemented, falling back to fake")
        return FakeBillingProvider()
    elif name == "mercado_pago_sandbox":
        logger.warning("Mercado Pago sandbox billing provider not fully implemented, falling back to fake")
        return FakeBillingProvider()
    else:
        logger.warning(f"Unknown billing provider '{name}', falling back to fake")
        return FakeBillingProvider()
