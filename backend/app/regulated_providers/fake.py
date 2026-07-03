"""
Fake implementations for all regulated providers.

Sprint 13 — Provider architecture foundation

SECURITY: These are sandbox-only implementations. They simulate responses
without any real financial operation. Safe for development and testing.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
import uuid

from app.regulated_providers.base import (
    OpenFinanceProvider, BankingProvider, BillPaymentProvider, PixProvider,
    KYCProvider, FraudProvider, DDAProvider, ReceiptProvider, ConsentProvider,
    ProviderResult, ConsentResult, AccountBalance, Transaction, ConnectedAccount,
    BillValidation, BillPaymentResult, PixChargeResult, PixOutResult,
    KYCSession, KYCResult, RiskAssessment, DetectedBill, Receipt, Consent,
)


class FakeOpenFinanceProvider(OpenFinanceProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def create_consent(self, org_id: int, user_id: int, institution_id: str) -> ConsentResult:
        return ConsentResult(
            consent_id=f"fake_consent_{uuid.uuid4().hex[:8]}",
            status="authorized",
            authorization_url="https://fake.openfinance.payflow.ai/authorize",
            expires_at=datetime.utcnow() + timedelta(days=365),
        )

    async def revoke_consent(self, consent_id: str) -> bool:
        return True

    async def get_consent_status(self, consent_id: str) -> str:
        return "authorized"

    async def list_connected_accounts(self, org_id: int) -> list[ConnectedAccount]:
        return [
            ConnectedAccount(
                account_id="fake_acc_001",
                institution_name="Nubank (Fake)",
                account_type="checking",
                account_number_masked="****1234",
            ),
        ]

    async def get_account_balance(self, account_id: str) -> AccountBalance:
        return AccountBalance(
            account_id=account_id,
            balance=Decimal("5000.00"),
            updated_at=datetime.utcnow(),
        )

    async def get_account_transactions(self, account_id: str, start_date: date, end_date: date) -> list[Transaction]:
        return [
            Transaction(
                transaction_id="fake_tx_001",
                amount=Decimal("-50.00"),
                type="debit",
                description="Supermercado Fake",
                transaction_date=datetime.utcnow(),
                category="mercado",
                merchant_name="Supermercado Fake",
            ),
        ]

    async def initiate_payment(self, account_id: str, payment_data: dict) -> ProviderResult:
        return ProviderResult(
            success=True,
            provider_id=f"fake_payment_{uuid.uuid4().hex[:8]}",
            metadata={"status": "initiated", "sandbox": True},
        )


class FakeBankingProvider(BankingProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def create_account(self, org_id: int, user_data: dict) -> ProviderResult:
        return ProviderResult(
            success=True,
            provider_id=f"fake_account_{uuid.uuid4().hex[:8]}",
            metadata={"account_number": "****5678", "branch": "0001"},
        )

    async def get_balance(self, account_id: str) -> Decimal:
        return Decimal("10000.00")

    async def pix_out(self, account_id: str, pix_key: str, amount: Decimal, description: str) -> PixOutResult:
        return PixOutResult(
            success=True,
            transaction_id=f"fake_pix_{uuid.uuid4().hex[:8]}",
            status="completed",
        )

    async def pay_bill(self, account_id: str, bill_data: dict) -> BillPaymentResult:
        return BillPaymentResult(
            success=True,
            payment_id=f"fake_bill_pay_{uuid.uuid4().hex[:8]}",
            status="paid",
            receipt_url="https://fake.payflow.ai/receipt/fake",
        )

    async def register_pix_key(self, account_id: str, key_type: str, key_value: str) -> ProviderResult:
        return ProviderResult(success=True, provider_id=f"fake_pixkey_{uuid.uuid4().hex[:8]}")

    async def get_statement(self, account_id: str, start_date: date, end_date: date) -> list[Transaction]:
        return [
            Transaction(
                transaction_id="fake_stmt_001",
                amount=Decimal("1000.00"),
                type="credit",
                description="Depósito Fake",
                transaction_date=datetime.utcnow(),
            ),
        ]


class FakeBillPaymentProvider(BillPaymentProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def validate_bill(self, barcode: str) -> BillValidation:
        return BillValidation(
            valid=True,
            barcode=barcode,
            beneficiary_name="Empresa Fake Ltda",
            amount=Decimal("150.00"),
            due_date=date.today() + timedelta(days=7),
        )

    async def pay_bill(self, account_id: str, barcode: str, amount: Decimal,
                       schedule_date: date = None) -> BillPaymentResult:
        return BillPaymentResult(
            success=True,
            payment_id=f"fake_billpay_{uuid.uuid4().hex[:8]}",
            status="paid" if not schedule_date else "scheduled",
        )

    async def get_payment_status(self, payment_id: str) -> str:
        return "paid"

    async def cancel_scheduled_payment(self, payment_id: str) -> bool:
        return True


class FakePixProvider(PixProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def create_charge(self, org_id: int, amount: Decimal, description: str,
                            payer_info: dict = None) -> PixChargeResult:
        return PixChargeResult(
            charge_id=f"fake_pix_charge_{uuid.uuid4().hex[:8]}",
            qr_code="data:image/png;base64,FAKE_QR_CODE",
            qr_code_text="00020126360014BR.GOV.BCB.PIX0114fake@payflow.ai5204000053039865802BR5913PayFlow Fake6009SAO PAULO62070503***6304FAKE",
            status="pending",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

    async def create_static_qr(self, org_id: int, description: str) -> PixChargeResult:
        return PixChargeResult(
            charge_id=f"fake_static_qr_{uuid.uuid4().hex[:8]}",
            qr_code="data:image/png;base64,FAKE_STATIC_QR",
            qr_code_text="00020126360014BR.GOV.BCB.PIX0114static@payflow.ai5204000053039865802BR5913PayFlow Static6009SAO PAULO62070503***6304FAKE",
            status="active",
        )

    async def get_charge_status(self, charge_id: str) -> str:
        return "pending"

    async def process_webhook(self, payload: dict) -> ProviderResult:
        return ProviderResult(success=True, provider_id=payload.get("id", "fake_webhook"))


class FakeKYCProvider(KYCProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def start_verification(self, user_id: int, document_type: str, document_data: dict) -> KYCSession:
        return KYCSession(
            session_id=f"fake_kyc_{uuid.uuid4().hex[:8]}",
            status="pending",
            verification_url="https://fake.kyc.payflow.ai/verify",
        )

    async def submit_document(self, session_id: str, document_image: bytes) -> ProviderResult:
        return ProviderResult(success=True, provider_id=session_id, metadata={"document_valid": True})

    async def submit_selfie(self, session_id: str, selfie_image: bytes) -> ProviderResult:
        return ProviderResult(success=True, provider_id=session_id, metadata={"biometric_passed": True})

    async def get_verification_result(self, session_id: str) -> KYCResult:
        return KYCResult(status="approved", score=95.0, details={"sandbox": True})


class FakeFraudProvider(FraudProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def assess_risk(self, transaction_data: dict) -> RiskAssessment:
        return RiskAssessment(
            risk_level="low",
            risk_score=10.0,
            recommendation="approve",
            details={"sandbox": True},
        )

    async def flag_transaction(self, transaction_id: str, reason: str) -> bool:
        return True

    async def get_user_risk_score(self, user_id: int) -> float:
        return 10.0


class FakeDDAProvider(DDAProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def enable_dda(self, org_id: int, document: str) -> ProviderResult:
        return ProviderResult(
            success=True,
            provider_id=f"fake_dda_{uuid.uuid4().hex[:8]}",
            metadata={"document_masked": "***.***.***-**"},
        )

    async def disable_dda(self, enrollment_id: str) -> bool:
        return True

    async def list_detected_bills(self, org_id: int) -> list[DetectedBill]:
        return [
            DetectedBill(
                bill_id="fake_bill_001",
                beneficiary_name="Companhia Elétrica Fake",
                amount=Decimal("120.00"),
                due_date=date.today() + timedelta(days=5),
                barcode="00000000000000000000000000000000000000000000",
            ),
        ]

    async def get_bill_details(self, bill_id: str) -> DetectedBill:
        return DetectedBill(
            bill_id=bill_id,
            beneficiary_name="Companhia Elétrica Fake",
            amount=Decimal("120.00"),
            due_date=date.today() + timedelta(days=5),
            barcode="00000000000000000000000000000000000000000000",
        )


class FakeReceiptProvider(ReceiptProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def generate_receipt(self, transaction_id: str, transaction_type: str) -> Receipt:
        return Receipt(
            receipt_id=f"fake_receipt_{uuid.uuid4().hex[:8]}",
            receipt_url=f"https://fake.receipt.payflow.ai/{transaction_id}",
            transaction_data={"transaction_id": transaction_id, "type": transaction_type, "sandbox": True},
        )

    async def get_receipt(self, receipt_id: str) -> Receipt:
        return Receipt(
            receipt_id=receipt_id,
            receipt_url=f"https://fake.receipt.payflow.ai/{receipt_id}",
            transaction_data={"sandbox": True},
        )

    async def list_receipts(self, org_id: int, start_date: date, end_date: date) -> list[Receipt]:
        return [
            Receipt(
                receipt_id="fake_receipt_001",
                receipt_url="https://fake.receipt.payflow.ai/001",
                transaction_data={"sandbox": True},
            ),
        ]


class FakeConsentProvider(ConsentProvider):
    @property
    def name(self) -> str:
        return "fake"

    async def create_consent(self, org_id: int, user_id: int, scope: str, metadata: dict) -> Consent:
        return Consent(
            consent_id=f"fake_consent_{uuid.uuid4().hex[:8]}",
            scope=scope,
            status="active",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365),
            metadata=metadata,
        )

    async def verify_consent(self, org_id: int, user_id: int, scope: str) -> str:
        return "active"

    async def revoke_consent(self, consent_id: str) -> bool:
        return True

    async def list_consents(self, org_id: int) -> list[Consent]:
        return [
            Consent(
                consent_id="fake_consent_001",
                scope="open_finance",
                status="active",
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=365),
            ),
        ]
