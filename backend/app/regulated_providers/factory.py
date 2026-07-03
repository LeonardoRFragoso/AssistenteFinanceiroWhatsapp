"""
Factory for regulated fintech providers.

Sprint 13 — Provider architecture foundation

SECURITY:
- All providers default to fake/sandbox.
- Real providers require: (1) feature flag enabled, (2) provider name != "fake", (3) environment != demo.
- Production rejects unknown providers.
- Demo mode forces fake for all providers.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.regulated_providers.base import (
    OpenFinanceProvider, BankingProvider, BillPaymentProvider, PixProvider,
    KYCProvider, FraudProvider, DDAProvider, ReceiptProvider, ConsentProvider,
)
from app.regulated_providers.fake import (
    FakeOpenFinanceProvider, FakeBankingProvider, FakeBillPaymentProvider,
    FakePixProvider, FakeKYCProvider, FakeFraudProvider, FakeDDAProvider,
    FakeReceiptProvider, FakeConsentProvider,
)

logger = logging.getLogger(__name__)

_FAKE_MAP = {
    "open_finance": FakeOpenFinanceProvider,
    "banking": FakeBankingProvider,
    "bill_payment": FakeBillPaymentProvider,
    "pix": FakePixProvider,
    "kyc": FakeKYCProvider,
    "fraud": FakeFraudProvider,
    "dda": FakeDDAProvider,
    "receipt": FakeReceiptProvider,
    "consent": FakeConsentProvider,
}

_FLAG_MAP = {
    "open_finance": "ENABLE_OPEN_FINANCE",
    "banking": "ENABLE_REAL_BANKING",
    "bill_payment": "ENABLE_BILL_PAYMENT",
    "pix": "ENABLE_PIX_OUT",
    "kyc": "ENABLE_KYC",
    "dda": "ENABLE_DDA",
    "fraud": None,
    "receipt": None,
    "consent": None,
}

_NAME_MAP = {
    "open_finance": "OPEN_FINANCE_PROVIDER",
    "banking": "BANKING_PROVIDER_NAME",
    "bill_payment": "BILL_PAYMENT_PROVIDER_NAME",
    "pix": "PIX_PROVIDER_NAME",
    "kyc": "KYC_PROVIDER_NAME",
    "fraud": "FRAUD_PROVIDER_NAME",
    "dda": "DDA_PROVIDER_NAME",
    "receipt": "RECEIPT_PROVIDER_NAME",
    "consent": "CONSENT_PROVIDER_NAME",
}


def _get_provider(provider_type: str):
    """Get a regulated provider instance. Always returns fake unless feature flag + real provider configured."""
    fake_cls = _FAKE_MAP[provider_type]
    flag_name = _FLAG_MAP[provider_type]
    name_attr = _NAME_MAP[provider_type]

    if getattr(settings, "ENABLE_DEMO_MODE", False):
        return fake_cls()

    provider_name = getattr(settings, name_attr, "fake")

    if provider_name == "fake":
        return fake_cls()

    flag_enabled = getattr(settings, flag_name, False) if flag_name else True

    if not flag_enabled:
        logger.warning(
            "Provider '%s' is configured as '%s' but feature flag '%s' is disabled. "
            "Falling back to fake provider.",
            provider_type, provider_name, flag_name,
        )
        return fake_cls()

    if settings.ENVIRONMENT == "production":
        raise ValueError(
            f"Real {provider_type} provider '{provider_name}' is not yet implemented. "
            f"Use fake provider or implement the integration first."
        )

    logger.warning(
        "Provider '%s' set to '%s' but real implementation not available. "
        "Falling back to fake provider.",
        provider_type, provider_name,
    )
    return fake_cls()


def get_open_finance_provider() -> OpenFinanceProvider:
    return _get_provider("open_finance")


def get_banking_provider() -> BankingProvider:
    return _get_provider("banking")


def get_bill_payment_provider() -> BillPaymentProvider:
    return _get_provider("bill_payment")


def get_pix_provider() -> PixProvider:
    return _get_provider("pix")


def get_kyc_provider() -> KYCProvider:
    return _get_provider("kyc")


def get_fraud_provider() -> FraudProvider:
    return _get_provider("fraud")


def get_dda_provider() -> DDAProvider:
    return _get_provider("dda")


def get_receipt_provider() -> ReceiptProvider:
    return _get_provider("receipt")


def get_consent_provider() -> ConsentProvider:
    return _get_provider("consent")
