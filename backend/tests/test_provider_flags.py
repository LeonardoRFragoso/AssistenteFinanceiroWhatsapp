"""
Tests for regulated provider factory — ensure factory returns fake by default,
demo mode forces fake, production rejects unimplemented real providers,
and fake providers work correctly.

Sprint 13 — Jota Feature Parity Blueprint
"""

import pytest
from decimal import Decimal
from app.core.config import settings
from app.regulated_providers.factory import (
    get_open_finance_provider, get_banking_provider,
    get_bill_payment_provider, get_pix_provider, get_kyc_provider,
    get_fraud_provider, get_dda_provider, get_receipt_provider,
    get_consent_provider,
)


class TestFactoryReturnsFake:
    def test_open_finance_returns_fake(self):
        assert get_open_finance_provider().name == "fake"

    def test_banking_returns_fake(self):
        assert get_banking_provider().name == "fake"

    def test_bill_payment_returns_fake(self):
        assert get_bill_payment_provider().name == "fake"

    def test_pix_returns_fake(self):
        assert get_pix_provider().name == "fake"

    def test_kyc_returns_fake(self):
        assert get_kyc_provider().name == "fake"

    def test_fraud_returns_fake(self):
        assert get_fraud_provider().name == "fake"

    def test_dda_returns_fake(self):
        assert get_dda_provider().name == "fake"

    def test_receipt_returns_fake(self):
        assert get_receipt_provider().name == "fake"

    def test_consent_returns_fake(self):
        assert get_consent_provider().name == "fake"


class TestDemoModeForcesFake:
    def test_demo_mode_forces_fake_banking(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", True)
        monkeypatch.setattr(settings, "BANKING_PROVIDER_NAME", "celcoin")
        monkeypatch.setattr(settings, "ENABLE_REAL_BANKING", True)
        assert get_banking_provider().name == "fake"

    def test_demo_mode_forces_fake_kyc(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", True)
        monkeypatch.setattr(settings, "KYC_PROVIDER_NAME", "unico")
        monkeypatch.setattr(settings, "ENABLE_KYC", True)
        assert get_kyc_provider().name == "fake"

    def test_demo_mode_forces_fake_open_finance(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", True)
        monkeypatch.setattr(settings, "OPEN_FINANCE_PROVIDER", "pluggy")
        monkeypatch.setattr(settings, "ENABLE_OPEN_FINANCE", True)
        assert get_open_finance_provider().name == "fake"


class TestFlagDisabledFallsBackToFake:
    def test_banking_flag_disabled_falls_back(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", False)
        monkeypatch.setattr(settings, "BANKING_PROVIDER_NAME", "celcoin")
        monkeypatch.setattr(settings, "ENABLE_REAL_BANKING", False)
        assert get_banking_provider().name == "fake"

    def test_kyc_flag_disabled_falls_back(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", False)
        monkeypatch.setattr(settings, "KYC_PROVIDER_NAME", "unico")
        monkeypatch.setattr(settings, "ENABLE_KYC", False)
        assert get_kyc_provider().name == "fake"

    def test_open_finance_flag_disabled_falls_back(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", False)
        monkeypatch.setattr(settings, "OPEN_FINANCE_PROVIDER", "belvo")
        monkeypatch.setattr(settings, "ENABLE_OPEN_FINANCE", False)
        assert get_open_finance_provider().name == "fake"


class TestProductionRejectsRealProvider:
    def test_production_rejects_real_banking(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", False)
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "BANKING_PROVIDER_NAME", "celcoin")
        monkeypatch.setattr(settings, "ENABLE_REAL_BANKING", True)
        with pytest.raises(ValueError, match="not yet implemented"):
            get_banking_provider()

    def test_production_rejects_real_kyc(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", False)
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "KYC_PROVIDER_NAME", "unico")
        monkeypatch.setattr(settings, "ENABLE_KYC", True)
        with pytest.raises(ValueError, match="not yet implemented"):
            get_kyc_provider()

    def test_production_rejects_real_open_finance(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_DEMO_MODE", False)
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "OPEN_FINANCE_PROVIDER", "pluggy")
        monkeypatch.setattr(settings, "ENABLE_OPEN_FINANCE", True)
        with pytest.raises(ValueError, match="not yet implemented"):
            get_open_finance_provider()

    def test_production_accepts_fake_banking(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "BANKING_PROVIDER_NAME", "fake")
        assert get_banking_provider().name == "fake"


class TestFakeProviderFunctionality:
    @pytest.mark.asyncio
    async def test_fake_open_finance_create_consent(self):
        result = await get_open_finance_provider().create_consent(
            org_id=1, user_id=1, institution_id="nubank"
        )
        assert result.status == "authorized"
        assert result.consent_id.startswith("fake_consent_")

    @pytest.mark.asyncio
    async def test_fake_banking_get_balance(self):
        balance = await get_banking_provider().get_balance("fake_acc")
        assert balance > 0

    @pytest.mark.asyncio
    async def test_fake_pix_create_charge(self):
        result = await get_pix_provider().create_charge(
            org_id=1, amount=Decimal("50.00"), description="Test"
        )
        assert result.status == "pending"
        assert result.charge_id.startswith("fake_pix_charge_")

    @pytest.mark.asyncio
    async def test_fake_kyc_start_verification(self):
        result = await get_kyc_provider().start_verification(
            user_id=1, document_type="rg", document_data={}
        )
        assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_fake_dda_list_detected_bills(self):
        bills = await get_dda_provider().list_detected_bills(org_id=1)
        assert len(bills) >= 1
        assert bills[0].beneficiary_name

    @pytest.mark.asyncio
    async def test_fake_consent_create(self):
        result = await get_consent_provider().create_consent(
            org_id=1, user_id=1, scope="open_finance", metadata={}
        )
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_fake_fraud_assess_risk(self):
        result = await get_fraud_provider().assess_risk({})
        assert result.risk_level == "low"

    @pytest.mark.asyncio
    async def test_fake_bill_payment_validate(self):
        result = await get_bill_payment_provider().validate_bill("00000000000000000000000000000000000000000000")
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_fake_receipt_generate(self):
        result = await get_receipt_provider().generate_receipt("tx_001", "pix_out")
        assert result.receipt_id.startswith("fake_receipt_")
