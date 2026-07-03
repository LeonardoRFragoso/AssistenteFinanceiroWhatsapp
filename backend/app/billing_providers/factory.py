from app.billing_providers.base import BaseBillingProvider
from app.billing_providers.fake_billing_provider import FakeBillingProvider
from app.core.config import settings
from app.core.logging import logger


def get_billing_provider(provider_name: str | None = None) -> BaseBillingProvider:
    """Get the billing provider instance.

    This is SEPARATE from get_payment_provider which handles charges.
    Default is 'fake' (no real payments).

    In production, an unknown provider raises ValueError.
    In development/testing/demo, an unknown provider falls back to fake with a warning.
    """
    name = provider_name or settings.PAYFLOW_BILLING_PROVIDER
    env = settings.ENVIRONMENT.lower()

    # Demo mode always forces fake
    if getattr(settings, "ENABLE_DEMO_MODE", False):
        if name != "fake":
            logger.warning(f"Demo mode active: forcing fake billing provider (requested: {name})")
        return FakeBillingProvider()

    if name == "fake":
        return FakeBillingProvider()
    elif name == "stripe_sandbox":
        logger.warning("Stripe sandbox billing provider not fully implemented, falling back to fake")
        return FakeBillingProvider()
    elif name == "mercado_pago_sandbox":
        logger.warning("Mercado Pago sandbox billing provider not fully implemented, falling back to fake")
        return FakeBillingProvider()
    else:
        if env == "production":
            raise ValueError(
                f"Unknown billing provider '{name}' in production environment. "
                f"Set PAYFLOW_BILLING_PROVIDER to a supported value (fake, stripe_sandbox, mercado_pago_sandbox)."
            )
        logger.warning(f"Unknown billing provider '{name}' in {env} environment, falling back to fake")
        return FakeBillingProvider()
