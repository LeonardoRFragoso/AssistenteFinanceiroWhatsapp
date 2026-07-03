"""
Open Finance router — Sprint 16.

Endpoints for Open Finance read provider (fake/demo mode only).
All endpoints are org-scoped with RBAC.
"""
import logging
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.organization import OrganizationRole
from app.models.user import User
from app.utils.dependencies import get_current_user, get_current_organization, get_current_user_role
from app.schemas.open_finance import (
    OpenFinanceStatusResponse,
    OpenFinanceConsentCreateFake,
    ConnectedAccountResponse,
    BankTransactionResponse,
    FinancialCategoryResponse,
    OpenFinanceSyncLogResponse,
    FinancialSummaryResponse,
    CategoryBreakdownResponse,
    MerchantBreakdownResponse,
    ConsentResponse,
)
from app.services.open_finance_service import OpenFinanceService
from app.services.bank_transaction_service import BankTransactionService
from app.services.financial_summary_service import FinancialSummaryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/open-finance", tags=["Open Finance"])

_FINANCE_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE}


def _require_finance_access(role: OrganizationRole) -> None:
    if role not in _FINANCE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Finance access required. Owner, admin, or finance role needed.",
        )


@router.get("/status", response_model=OpenFinanceStatusResponse)
async def get_open_finance_status(
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
):
    """Get Open Finance provider status."""
    return OpenFinanceStatusResponse(
        enabled=settings.ENABLE_OPEN_FINANCE,
        provider=settings.OPEN_FINANCE_PROVIDER,
        real_provider_configured=settings.OPEN_FINANCE_PROVIDER != "fake",
        demo_mode=settings.ENABLE_DEMO_MODE or settings.OPEN_FINANCE_PROVIDER == "fake",
        real_data_access=settings.ENABLE_OPEN_FINANCE and settings.OPEN_FINANCE_PROVIDER != "fake",
        message="Open Finance real is disabled. Fake/demo provider only.",
    )


@router.post("/consents/fake", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def create_fake_consent(
    body: OpenFinanceConsentCreateFake,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Create a fake Open Finance consent."""
    _require_finance_access(role)
    service = OpenFinanceService(db)
    try:
        consent = await service.create_fake_consent(org.id, current_user.id, body.institution_id)
        return consent
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/consents", response_model=list[ConsentResponse])
async def list_consents(
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """List Open Finance consents for the organization."""
    service = OpenFinanceService(db)
    consents = await service.list_consents(org.id)
    return consents


@router.post("/consents/{consent_id}/revoke", response_model=ConsentResponse)
async def revoke_consent(
    consent_id: int,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an Open Finance consent."""
    _require_finance_access(role)
    service = OpenFinanceService(db)
    consent = await service.revoke_consent(org.id, consent_id, current_user.id)
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    return consent


@router.get("/accounts", response_model=list[ConnectedAccountResponse])
async def list_connected_accounts(
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """List connected accounts for the organization."""
    _require_finance_access(role)
    service = OpenFinanceService(db)
    accounts = await service.list_connected_accounts(org.id)
    return accounts


@router.post("/sync/fake", status_code=status.HTTP_200_OK)
async def sync_fake_data(
    consent_id: Optional[int] = Query(None, description="Consent ID for account sync"),
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Sync fake/demo Open Finance data (accounts and transactions)."""
    _require_finance_access(role)
    service = OpenFinanceService(db)

    try:
        accounts_synced = 0
        transactions_synced = 0

        if consent_id:
            accounts = await service.sync_fake_accounts(org.id, current_user.id, consent_id)
            accounts_synced = len(accounts)

        transactions = await service.sync_fake_transactions(org.id, current_user.id)
        transactions_synced = len(transactions)

        await service.seed_default_categories(org.id)

        return {
            "status": "success",
            "accounts_synced": accounts_synced,
            "transactions_synced": transactions_synced,
            "is_demo_data": True,
            "message": "Fake/demo data synced successfully.",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/transactions", response_model=list[BankTransactionResponse])
async def list_transactions(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    connected_account_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """List bank transactions with optional filters."""
    _require_finance_access(role)
    tx_service = BankTransactionService(db)
    transactions = await tx_service.list_transactions(
        org.id, start_date, end_date, category, connected_account_id, search, limit, offset
    )
    return transactions


@router.get("/transactions/summary", response_model=FinancialSummaryResponse)
async def get_transactions_summary(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly financial summary."""
    _require_finance_access(role)
    summary_service = FinancialSummaryService(db)
    summary = await summary_service.get_monthly_summary(org.id, year, month)
    return summary


@router.get("/transactions/categories", response_model=list[CategoryBreakdownResponse])
async def get_category_breakdown(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction breakdown by category."""
    _require_finance_access(role)
    tx_service = BankTransactionService(db)
    breakdown = await tx_service.group_by_category(org.id, start_date, end_date)
    return breakdown


@router.get("/transactions/merchants", response_model=list[MerchantBreakdownResponse])
async def get_merchant_breakdown(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction breakdown by merchant."""
    _require_finance_access(role)
    tx_service = BankTransactionService(db)
    breakdown = await tx_service.group_by_merchant(org.id, start_date, end_date)
    return breakdown


@router.get("/sync-logs", response_model=list[OpenFinanceSyncLogResponse])
async def get_sync_logs(
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get Open Finance sync logs for the organization."""
    _require_finance_access(role)
    service = OpenFinanceService(db)
    logs = await service.get_sync_logs(org.id, limit)
    return logs
