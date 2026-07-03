"""
Tests for regulated feature flags — ensure all regulated features default to False.

Sprint 13 — Jota Feature Parity Blueprint
"""

from app.core.config import settings


class TestRegulatedFlagsDefaultFalse:
    def test_open_finance_flag_default_false(self):
        assert settings.ENABLE_OPEN_FINANCE is False

    def test_bill_payment_flag_default_false(self):
        assert settings.ENABLE_BILL_PAYMENT is False

    def test_pix_out_flag_default_false(self):
        assert settings.ENABLE_PIX_OUT is False

    def test_kyc_flag_default_false(self):
        assert settings.ENABLE_KYC is False

    def test_dda_flag_default_false(self):
        assert settings.ENABLE_DDA is False

    def test_real_banking_flag_default_false(self):
        assert settings.ENABLE_REAL_BANKING is False


class TestProviderNamesDefaultFake:
    def test_open_finance_provider_default_fake(self):
        assert settings.OPEN_FINANCE_PROVIDER == "fake"

    def test_banking_provider_default_fake(self):
        assert settings.BANKING_PROVIDER_NAME == "fake"

    def test_bill_payment_provider_default_fake(self):
        assert settings.BILL_PAYMENT_PROVIDER_NAME == "fake"

    def test_pix_provider_default_fake(self):
        assert settings.PIX_PROVIDER_NAME == "fake"

    def test_kyc_provider_default_fake(self):
        assert settings.KYC_PROVIDER_NAME == "fake"

    def test_fraud_provider_default_fake(self):
        assert settings.FRAUD_PROVIDER_NAME == "fake"

    def test_dda_provider_default_fake(self):
        assert settings.DDA_PROVIDER_NAME == "fake"

    def test_receipt_provider_default_fake(self):
        assert settings.RECEIPT_PROVIDER_NAME == "fake"

    def test_consent_provider_default_fake(self):
        assert settings.CONSENT_PROVIDER_NAME == "fake"
