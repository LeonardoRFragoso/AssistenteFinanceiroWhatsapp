"""
Pydantic schemas for provider foundation — Sprint 14.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, Field


# ============================================================
# Provider Connection
# ============================================================

class ProviderConnectionCreate(BaseModel):
    provider_type: str = Field(..., description="open_finance, banking, bill_payment, pix, kyc, fraud, dda, receipt, consent")
    provider_name: str = Field(default="fake", description="Provider name (default: fake)")
    display_name: Optional[str] = None
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    scopes: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None


class ProviderConnectionResponse(BaseModel):
    id: int
    organization_id: int
    provider_type: str
    provider_name: str
    status: str
    environment: str
    display_name: Optional[str] = None
    external_connection_id: Optional[str] = None
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    scopes: Optional[list[str]] = None
    active: bool
    consent_expires_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Provider Webhook Event
# ============================================================

class ProviderWebhookEventResponse(BaseModel):
    id: int
    organization_id: int
    provider_type: str
    provider_name: str
    event_type: str
    provider_event_id: str
    status: str
    error_message: Optional[str] = None
    received_at: datetime
    processed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Open Finance Consent
# ============================================================

class OpenFinanceConsentCreate(BaseModel):
    institution_name: str = Field(..., description="Institution name (fake)")
    institution_code: Optional[str] = None
    scopes: Optional[list[str]] = Field(default=["accounts", "transactions"])


class OpenFinanceConsentResponse(BaseModel):
    id: int
    organization_id: int
    user_id: Optional[int] = None
    provider_name: str
    external_consent_id: Optional[str] = None
    status: str
    scopes: Optional[list[str]] = None
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    authorization_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Organization Audit Log
# ============================================================

class OrganizationAuditLogResponse(BaseModel):
    id: int
    organization_id: int
    actor_user_id: Optional[int] = None
    actor_role: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    provider_type: Optional[str] = None
    ip_hash: Optional[str] = None
    user_agent_hash: Optional[str] = None
    extra_data: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Transaction Authorization
# ============================================================

class TransactionAuthorizationCreate(BaseModel):
    action_type: str = Field(..., description="Type of action requiring authorization")
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "BRL"
    metadata: Optional[dict[str, Any]] = None


class TransactionAuthorizationConfirm(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, description="6-digit authorization code")


class TransactionAuthorizationResponse(BaseModel):
    id: int
    organization_id: int
    user_id: Optional[int] = None
    action_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str
    status: str
    challenge_type: str
    expires_at: datetime
    confirmed_at: Optional[datetime] = None
    failed_attempts: int
    created_at: datetime
    updated_at: datetime
    code: Optional[str] = Field(None, description="6-digit code (only in testing/demo)")

    class Config:
        from_attributes = True


# ============================================================
# Provider Status
# ============================================================

class ProviderStatusItem(BaseModel):
    enabled: bool
    configured_provider: str
    status: str
    real_operation_allowed: bool


class ProviderStatusResponse(BaseModel):
    environment: str
    demo_mode: bool
    providers: dict[str, ProviderStatusItem]


class FeatureFlagsResponse(BaseModel):
    ENABLE_OPEN_FINANCE: bool
    ENABLE_BILL_PAYMENT: bool
    ENABLE_PIX_OUT: bool
    ENABLE_KYC: bool
    ENABLE_DDA: bool
    ENABLE_REAL_BANKING: bool
