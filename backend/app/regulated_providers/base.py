"""
Abstract base classes for regulated fintech providers.

Sprint 13 — Jota Feature Parity Blueprint

SECURITY NOTICE:
- These are abstract interfaces only. No real financial operations are implemented.
- All implementations default to fake/sandbox.
- Real providers require: (1) feature flag enabled, (2) provider configured, (3) partnership with regulated entity.
- Never activate a regulated feature flag without a configured real provider.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional


# ============================================================
# Data classes for provider results
# ============================================================

class ProviderResult:
    def __init__(self, success: bool, provider_id: str = "", metadata: dict = None, error: str = ""):
        self.success = success
        self.provider_id = provider_id
        self.metadata = metadata or {}
        self.error = error


class ConsentResult:
    def __init__(self, consent_id: str, status: str, authorization_url: str = "", expires_at: datetime = None):
        self.consent_id = consent_id
        self.status = status
        self.authorization_url = authorization_url
        self.expires_at = expires_at


class AccountBalance:
    def __init__(self, account_id: str, balance: Decimal, currency: str = "BRL", updated_at: datetime = None):
        self.account_id = account_id
        self.balance = balance
        self.currency = currency
        self.updated_at = updated_at or datetime.utcnow()


class Transaction:
    def __init__(self, transaction_id: str, amount: Decimal, type: str, description: str,
                 transaction_date: datetime, category: str = "", merchant_name: str = ""):
        self.transaction_id = transaction_id
        self.amount = amount
        self.type = type
        self.description = description
        self.transaction_date = transaction_date
        self.category = category
        self.merchant_name = merchant_name


class ConnectedAccount:
    def __init__(self, account_id: str, institution_name: str, account_type: str,
                 account_number_masked: str, status: str = "active"):
        self.account_id = account_id
        self.institution_name = institution_name
        self.account_type = account_type
        self.account_number_masked = account_number_masked
        self.status = status


class BillValidation:
    def __init__(self, valid: bool, barcode: str, beneficiary_name: str = "",
                 amount: Decimal = None, due_date: date = None, error: str = ""):
        self.valid = valid
        self.barcode = barcode
        self.beneficiary_name = beneficiary_name
        self.amount = amount
        self.due_date = due_date
        self.error = error


class BillPaymentResult:
    def __init__(self, success: bool, payment_id: str = "", status: str = "",
                 receipt_url: str = "", error: str = ""):
        self.success = success
        self.payment_id = payment_id
        self.status = status
        self.receipt_url = receipt_url
        self.error = error


class PixChargeResult:
    def __init__(self, charge_id: str, qr_code: str, qr_code_text: str,
                 status: str = "pending", expires_at: datetime = None):
        self.charge_id = charge_id
        self.qr_code = qr_code
        self.qr_code_text = qr_code_text
        self.status = status
        self.expires_at = expires_at


class PixOutResult:
    def __init__(self, success: bool, transaction_id: str = "", status: str = "", error: str = ""):
        self.success = success
        self.transaction_id = transaction_id
        self.status = status
        self.error = error


class KYCSession:
    def __init__(self, session_id: str, status: str, verification_url: str = ""):
        self.session_id = session_id
        self.status = status
        self.verification_url = verification_url


class KYCResult:
    def __init__(self, status: str, score: float = 0.0, details: dict = None):
        self.status = status
        self.score = score
        self.details = details or {}


class RiskAssessment:
    def __init__(self, risk_level: str, risk_score: float, recommendation: str, details: dict = None):
        self.risk_level = risk_level
        self.risk_score = risk_score
        self.recommendation = recommendation
        self.details = details or {}


class DetectedBill:
    def __init__(self, bill_id: str, beneficiary_name: str, amount: Decimal,
                 due_date: date, barcode: str, status: str = "detected"):
        self.bill_id = bill_id
        self.beneficiary_name = beneficiary_name
        self.amount = amount
        self.due_date = due_date
        self.barcode = barcode
        self.status = status


class Receipt:
    def __init__(self, receipt_id: str, receipt_url: str, transaction_data: dict):
        self.receipt_id = receipt_id
        self.receipt_url = receipt_url
        self.transaction_data = transaction_data


class Consent:
    def __init__(self, consent_id: str, scope: str, status: str, created_at: datetime,
                 expires_at: datetime = None, metadata: dict = None):
        self.consent_id = consent_id
        self.scope = scope
        self.status = status
        self.created_at = created_at
        self.expires_at = expires_at
        self.metadata = metadata or {}


# ============================================================
# Abstract provider interfaces
# ============================================================

class OpenFinanceProvider(ABC):
    """Open Finance provider — connect bank accounts, read balances, transactions, initiate payments."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def create_consent(self, org_id: int, user_id: int, institution_id: str) -> ConsentResult: ...

    @abstractmethod
    async def revoke_consent(self, consent_id: str) -> bool: ...

    @abstractmethod
    async def get_consent_status(self, consent_id: str) -> str: ...

    @abstractmethod
    async def list_connected_accounts(self, org_id: int) -> list[ConnectedAccount]: ...

    @abstractmethod
    async def get_account_balance(self, account_id: str) -> AccountBalance: ...

    @abstractmethod
    async def get_account_transactions(self, account_id: str, start_date: date, end_date: date) -> list[Transaction]: ...

    @abstractmethod
    async def initiate_payment(self, account_id: str, payment_data: dict) -> ProviderResult: ...


class BankingProvider(ABC):
    """Banking-as-a-Service provider — account, balance, Pix Out, bill payment."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def create_account(self, org_id: int, user_data: dict) -> ProviderResult: ...

    @abstractmethod
    async def get_balance(self, account_id: str) -> Decimal: ...

    @abstractmethod
    async def pix_out(self, account_id: str, pix_key: str, amount: Decimal, description: str) -> PixOutResult: ...

    @abstractmethod
    async def pay_bill(self, account_id: str, bill_data: dict) -> BillPaymentResult: ...

    @abstractmethod
    async def register_pix_key(self, account_id: str, key_type: str, key_value: str) -> ProviderResult: ...

    @abstractmethod
    async def get_statement(self, account_id: str, start_date: date, end_date: date) -> list[Transaction]: ...


class BillPaymentProvider(ABC):
    """Bill payment provider — validate and pay boletos and utility bills."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def validate_bill(self, barcode: str) -> BillValidation: ...

    @abstractmethod
    async def pay_bill(self, account_id: str, barcode: str, amount: Decimal,
                       schedule_date: date = None) -> BillPaymentResult: ...

    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> str: ...

    @abstractmethod
    async def cancel_scheduled_payment(self, payment_id: str) -> bool: ...


class PixProvider(ABC):
    """Pix charge provider — create QR Code charges, process webhooks."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def create_charge(self, org_id: int, amount: Decimal, description: str,
                            payer_info: dict = None) -> PixChargeResult: ...

    @abstractmethod
    async def create_static_qr(self, org_id: int, description: str) -> PixChargeResult: ...

    @abstractmethod
    async def get_charge_status(self, charge_id: str) -> str: ...

    @abstractmethod
    async def process_webhook(self, payload: dict) -> ProviderResult: ...


class KYCProvider(ABC):
    """KYC provider — identity verification, biometric, document validation."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def start_verification(self, user_id: int, document_type: str, document_data: dict) -> KYCSession: ...

    @abstractmethod
    async def submit_document(self, session_id: str, document_image: bytes) -> ProviderResult: ...

    @abstractmethod
    async def submit_selfie(self, session_id: str, selfie_image: bytes) -> ProviderResult: ...

    @abstractmethod
    async def get_verification_result(self, session_id: str) -> KYCResult: ...


class FraudProvider(ABC):
    """Fraud detection provider — transaction risk assessment."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def assess_risk(self, transaction_data: dict) -> RiskAssessment: ...

    @abstractmethod
    async def flag_transaction(self, transaction_id: str, reason: str) -> bool: ...

    @abstractmethod
    async def get_user_risk_score(self, user_id: int) -> float: ...


class DDAProvider(ABC):
    """DDA provider — automatic bill detection by CPF/CNPJ."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def enable_dda(self, org_id: int, document: str) -> ProviderResult: ...

    @abstractmethod
    async def disable_dda(self, enrollment_id: str) -> bool: ...

    @abstractmethod
    async def list_detected_bills(self, org_id: int) -> list[DetectedBill]: ...

    @abstractmethod
    async def get_bill_details(self, bill_id: str) -> DetectedBill: ...


class ReceiptProvider(ABC):
    """Receipt provider — generate and store transaction receipts."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def generate_receipt(self, transaction_id: str, transaction_type: str) -> Receipt: ...

    @abstractmethod
    async def get_receipt(self, receipt_id: str) -> Receipt: ...

    @abstractmethod
    async def list_receipts(self, org_id: int, start_date: date, end_date: date) -> list[Receipt]: ...


class ConsentProvider(ABC):
    """Consent management provider — LGPD, Open Finance, payment authorizations."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def create_consent(self, org_id: int, user_id: int, scope: str, metadata: dict) -> Consent: ...

    @abstractmethod
    async def verify_consent(self, org_id: int, user_id: int, scope: str) -> str: ...

    @abstractmethod
    async def revoke_consent(self, consent_id: str) -> bool: ...

    @abstractmethod
    async def list_consents(self, org_id: int) -> list[Consent]: ...
