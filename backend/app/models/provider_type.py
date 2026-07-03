from enum import Enum


class ProviderType(str, Enum):
    OPEN_FINANCE = "open_finance"
    BANKING = "banking"
    BILL_PAYMENT = "bill_payment"
    PIX = "pix"
    KYC = "kyc"
    FRAUD = "fraud"
    DDA = "dda"
    RECEIPT = "receipt"
    CONSENT = "consent"


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    EXPIRED = "expired"
    NOT_CONFIGURED = "not_configured"
