"""
Provider foundation router — Sprint 14.

Endpoints for provider connections, consents, audit logs, transaction auth,
provider status, and feature flags. All behind RBAC.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.models.organization import Organization, OrganizationRole
from app.models.user import User
from app.utils.dependencies import get_current_active_user, get_current_organization, get_current_user_role
from app.schemas.provider_foundation import (
    ProviderConnectionCreate, ProviderConnectionResponse,
    ProviderWebhookEventResponse,
    OpenFinanceConsentCreate, OpenFinanceConsentResponse,
    OrganizationAuditLogResponse,
    TransactionAuthorizationCreate, TransactionAuthorizationConfirm,
    TransactionAuthorizationResponse,
    ProviderStatusResponse, ProviderStatusItem, FeatureFlagsResponse,
)
from app.services.provider_connection_service import ProviderConnectionService
from app.services.provider_webhook_service import ProviderWebhookService
from app.services.open_finance_consent_service import OpenFinanceConsentService
from app.services.organization_audit_service import OrganizationAuditService
from app.services.transaction_authorization_service import TransactionAuthorizationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["Providers"])

_PROVIDER_TYPES = ["open_finance", "banking", "bill_payment", "pix", "kyc", "fraud", "dda", "receipt", "consent"]
_FLAG_MAP = {
    "open_finance": "ENABLE_OPEN_FINANCE",
    "banking": "ENABLE_REAL_BANKING",
    "bill_payment": "ENABLE_BILL_PAYMENT",
    "pix": "ENABLE_PIX_OUT",
    "kyc": "ENABLE_KYC",
    "dda": "ENABLE_DDA",
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


def _require_owner_admin(role: OrganizationRole):
    if role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin role required")


def _require_owner_admin_finance(role: OrganizationRole):
    if role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner, admin, or finance role required")


# ============================================================
# Provider Status & Feature Flags
# ============================================================

@router.get("/status", response_model=ProviderStatusResponse)
async def get_provider_status(
    org: Organization = Depends(get_current_organization),
):
    providers = {}
    for ptype in _PROVIDER_TYPES:
        flag_name = _FLAG_MAP.get(ptype)
        name_attr = _NAME_MAP.get(ptype, "")
        configured = getattr(settings, name_attr, "fake") if name_attr else "fake"
        enabled = getattr(settings, flag_name, False) if flag_name else True
        real_allowed = enabled and configured != "fake" and not settings.ENABLE_DEMO_MODE
        providers[ptype] = ProviderStatusItem(
            enabled=enabled,
            configured_provider=configured,
            status="disabled" if not enabled else ("active" if real_allowed else "sandbox"),
            real_operation_allowed=real_allowed,
        )
    return ProviderStatusResponse(
        environment=settings.ENVIRONMENT,
        demo_mode=settings.ENABLE_DEMO_MODE,
        providers=providers,
    )


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    org: Organization = Depends(get_current_organization),
):
    return FeatureFlagsResponse(
        ENABLE_OPEN_FINANCE=settings.ENABLE_OPEN_FINANCE,
        ENABLE_BILL_PAYMENT=settings.ENABLE_BILL_PAYMENT,
        ENABLE_PIX_OUT=settings.ENABLE_PIX_OUT,
        ENABLE_KYC=settings.ENABLE_KYC,
        ENABLE_DDA=settings.ENABLE_DDA,
        ENABLE_REAL_BANKING=settings.ENABLE_REAL_BANKING,
    )


# ============================================================
# Provider Connections
# ============================================================

@router.get("/connections", response_model=list[ProviderConnectionResponse])
async def list_connections(
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin_finance(role)
    service = ProviderConnectionService(db)
    return await service.list_connections(org.id)


@router.post("/connections", response_model=ProviderConnectionResponse, status_code=201)
async def create_connection(
    body: ProviderConnectionCreate,
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin(role)
    service = ProviderConnectionService(db)
    try:
        conn = await service.create_connection(
            organization_id=org.id,
            user_id=user.id,
            provider_type=body.provider_type,
            provider_name=body.provider_name,
            display_name=body.display_name,
            institution_name=body.institution_name,
            institution_code=body.institution_code,
            scopes=body.scopes,
            metadata=body.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return conn


@router.get("/connections/{connection_id}", response_model=ProviderConnectionResponse)
async def get_connection(
    connection_id: int,
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin_finance(role)
    service = ProviderConnectionService(db)
    conn = await service.get_connection(org.id, connection_id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return conn


@router.post("/connections/{connection_id}/deactivate", response_model=ProviderConnectionResponse)
async def deactivate_connection(
    connection_id: int,
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin(role)
    service = ProviderConnectionService(db)
    conn = await service.deactivate_connection(org.id, connection_id, user.id)
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return conn


# ============================================================
# Open Finance Consents
# ============================================================

@router.post("/open-finance/consents/fake", response_model=OpenFinanceConsentResponse, status_code=201)
async def create_fake_consent(
    body: OpenFinanceConsentCreate,
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin(role)
    service = OpenFinanceConsentService(db)
    try:
        consent = await service.create_fake_consent(
            organization_id=org.id,
            user_id=user.id,
            scopes=body.scopes,
            institution_name=body.institution_name,
            institution_code=body.institution_code,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return consent


@router.get("/open-finance/consents", response_model=list[OpenFinanceConsentResponse])
async def list_consents(
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin_finance(role)
    service = OpenFinanceConsentService(db)
    return await service.list_consents(org.id)


@router.post("/open-finance/consents/{consent_id}/revoke", response_model=OpenFinanceConsentResponse)
async def revoke_consent(
    consent_id: int,
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin(role)
    service = OpenFinanceConsentService(db)
    consent = await service.revoke_consent(org.id, consent_id, user.id)
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return consent


# ============================================================
# Audit Logs
# ============================================================

@router.get("/audit-logs", response_model=list[OrganizationAuditLogResponse])
async def list_audit_logs(
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    provider_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin(role)
    service = OrganizationAuditService(db)
    logs, _ = await service.list_logs(
        organization_id=org.id,
        action=action,
        resource_type=resource_type,
        provider_type=provider_type,
        limit=limit,
        offset=offset,
    )
    return logs


# ============================================================
# Transaction Authorizations
# ============================================================

@router.post("/transaction-authorizations", response_model=TransactionAuthorizationResponse, status_code=201)
async def create_transaction_authorization(
    body: TransactionAuthorizationCreate,
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin_finance(role)
    service = TransactionAuthorizationService(db)
    auth, code = await service.create_authorization(
        organization_id=org.id,
        user_id=user.id,
        action_type=body.action_type,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        amount=body.amount,
        metadata=body.metadata,
    )
    resp = TransactionAuthorizationResponse.model_validate(auth)
    resp.code = code
    return resp


@router.post("/transaction-authorizations/{authorization_id}/confirm", response_model=TransactionAuthorizationResponse)
async def confirm_transaction_authorization(
    authorization_id: int,
    body: TransactionAuthorizationConfirm,
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin_finance(role)
    service = TransactionAuthorizationService(db)
    try:
        auth = await service.confirm_authorization(org.id, authorization_id, user.id, body.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return auth


@router.post("/transaction-authorizations/{authorization_id}/cancel", response_model=TransactionAuthorizationResponse)
async def cancel_transaction_authorization(
    authorization_id: int,
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_owner_admin_finance(role)
    service = TransactionAuthorizationService(db)
    auth = await service.cancel_authorization(org.id, authorization_id, user.id)
    if not auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authorization not found")
    return auth


# ============================================================
# Webhook fake endpoint
# ============================================================

@router.post("/webhooks/{provider_type}/{provider_name}", response_model=ProviderWebhookEventResponse)
async def receive_webhook(
    provider_type: str,
    provider_name: str,
    payload: dict,
    provider_event_id: str = Query(..., description="Unique event ID from provider"),
    event_type: str = Query("unknown"),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    service = ProviderWebhookService(db)
    event = await service.record_event(
        organization_id=org.id,
        provider_type=provider_type,
        provider_name=provider_name,
        event_type=event_type,
        provider_event_id=provider_event_id,
        payload=payload,
    )
    return event


# ============================================================
# Asaas test-connection endpoint
# ============================================================

@router.post("/asaas/test-connection")
async def asaas_test_connection(
    user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
):
    """Test Asaas provider configuration without making API calls.

    Validates that:
    - Feature flag ENABLE_ASAAS_CHARGE_PROVIDER is true
    - ASAAS_API_KEY is configured
    - Demo mode is not active
    - Environment is sandbox or production

    Does NOT expose any secrets. Does NOT make external API calls.
    RBAC: owner/admin only.
    """
    if role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner/admin can test provider connections",
        )

    result = {
        "provider": "asaas",
        "enabled": settings.ENABLE_ASAAS_CHARGE_PROVIDER,
        "environment": settings.ASAAS_ENVIRONMENT,
        "demo_mode": settings.ENABLE_DEMO_MODE,
        "api_key_configured": bool(settings.ASAAS_API_KEY),
        "webhook_token_configured": bool(settings.ASAAS_WEBHOOK_TOKEN),
        "api_base_url": settings.ASAAS_API_BASE_URL,
    }

    if settings.ENABLE_DEMO_MODE:
        result["status"] = "demo_mode_forces_fake"
        result["message"] = "Demo mode is active — Asaas provider is not available. Provider will use fake."
    elif not settings.ENABLE_ASAAS_CHARGE_PROVIDER:
        result["status"] = "disabled"
        result["message"] = "ENABLE_ASAAS_CHARGE_PROVIDER is false. Set to true to enable Asaas."
    elif not settings.ASAAS_API_KEY:
        result["status"] = "missing_api_key"
        result["message"] = "ASAAS_API_KEY is not configured. Set it to enable Asaas."
    else:
        result["status"] = "ready"
        result["message"] = f"Asaas provider is configured for {settings.ASAAS_ENVIRONMENT} environment."

    return result
