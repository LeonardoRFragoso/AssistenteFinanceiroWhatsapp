"""
Bills router — Sprint 17.

Endpoints for fake DDA and bill management. All endpoints are org-scoped with RBAC.
No real DDA access, no real payment execution.
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.organization import OrganizationRole
from app.models.user import User
from app.models.bills import BillStatus, BillReminderChannel, PaymentIntentType
from app.utils.dependencies import get_current_user, get_current_organization, get_current_user_role
from app.schemas.bills import (
    BillStatusResponse,
    DetectedBillResponse,
    BillSummaryResponse,
    BillReminderCreate,
    BillReminderResponse,
    BillPaymentIntentResponse,
    BillPaymentIntentAuthorize,
    BillEventLogResponse,
    SyncFakeBillsResponse,
)
from app.services.bill_service import BillService
from app.services.bill_reminder_service import BillReminderService
from app.services.bill_payment_intent_service import BillPaymentIntentService
from app.services.bill_summary_service import BillSummaryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bills", tags=["Bills"])

_FINANCE_ROLES = {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE}


def _require_finance_access(role: OrganizationRole) -> None:
    if role not in _FINANCE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Finance access required. Owner, admin, or finance role needed.",
        )


@router.get("/status", response_model=BillStatusResponse)
async def get_bills_status(
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
):
    """Get bills/DDA provider status."""
    return BillStatusResponse(
        dda_enabled=settings.ENABLE_DDA,
        bill_payment_enabled=settings.ENABLE_BILL_PAYMENT,
        provider="fake",
        real_dda_access=settings.ENABLE_DDA and settings.DDA_PROVIDER_NAME != "fake",
        real_bill_payment_allowed=settings.ENABLE_BILL_PAYMENT and settings.BILL_PAYMENT_PROVIDER_NAME != "fake",
        demo_mode=settings.ENABLE_DEMO_MODE or settings.DDA_PROVIDER_NAME == "fake",
        message="DDA and bill payment are fake/demo only. No real payment is executed.",
    )


@router.post("/sync/fake", response_model=SyncFakeBillsResponse)
async def sync_fake_bills(
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Sync fake DDA bills (demo data only)."""
    _require_finance_access(role)
    service = BillService(db)
    try:
        result = await service.sync_fake_bills(org.id, current_user.id)
        return SyncFakeBillsResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("", response_model=list[DetectedBillResponse])
async def list_bills(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """List bills with optional filters."""
    _require_finance_access(role)
    service = BillService(db)
    bill_status = BillStatus(status_filter) if status_filter else None
    bills = await service.list_bills(
        org.id, status_filter=bill_status, category=category,
        start_date=start_date, end_date=end_date, search=search,
        limit=limit, offset=offset,
    )
    return [DetectedBillResponse.model_validate(b) for b in bills]


@router.get("/summary", response_model=BillSummaryResponse)
async def get_bills_summary(
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get bill summary (totals, categories, beneficiaries)."""
    _require_finance_access(role)
    service = BillSummaryService(db)
    summary = await service.get_summary(org.id)
    return BillSummaryResponse(**summary)


@router.get("/due-today", response_model=list[DetectedBillResponse])
async def get_due_today_bills(
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get bills due today."""
    _require_finance_access(role)
    service = BillSummaryService(db)
    bills = await service.get_due_today(org.id)
    return [DetectedBillResponse.model_validate(b) for b in bills]


@router.get("/overdue", response_model=list[DetectedBillResponse])
async def get_overdue_bills(
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get overdue bills."""
    _require_finance_access(role)
    service = BillSummaryService(db)
    bills = await service.get_overdue(org.id)
    return [DetectedBillResponse.model_validate(b) for b in bills]


@router.get("/upcoming", response_model=list[DetectedBillResponse])
async def get_upcoming_bills(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming bills within N days."""
    _require_finance_access(role)
    service = BillSummaryService(db)
    bills = await service.get_upcoming(org.id, days)
    return [DetectedBillResponse.model_validate(b) for b in bills]


@router.get("/{bill_id}", response_model=DetectedBillResponse)
async def get_bill(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific bill by ID."""
    _require_finance_access(role)
    service = BillService(db)
    bill = await service.get_bill(org.id, bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return DetectedBillResponse.model_validate(bill)


@router.post("/{bill_id}/ignore", response_model=DetectedBillResponse)
async def ignore_bill(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Mark a bill as ignored."""
    _require_finance_access(role)
    service = BillService(db)
    bill = await service.ignore_bill(org.id, bill_id, current_user.id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return DetectedBillResponse.model_validate(bill)


@router.post("/{bill_id}/mark-paid-manual", response_model=DetectedBillResponse)
async def mark_paid_manual(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Mark a bill as paid manually (no real payment)."""
    _require_finance_access(role)
    service = BillService(db)
    bill = await service.mark_paid_manual(org.id, bill_id, current_user.id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return DetectedBillResponse.model_validate(bill)


@router.post("/{bill_id}/reminders", response_model=BillReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    bill_id: int,
    body: BillReminderCreate,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a reminder for a bill."""
    _require_finance_access(role)
    service = BillReminderService(db)
    channel = BillReminderChannel(body.channel)
    reminder = await service.schedule_reminder(org.id, bill_id, body.reminder_date, channel)
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return BillReminderResponse.model_validate(reminder)


@router.get("/{bill_id}/reminders", response_model=list[BillReminderResponse])
async def list_reminders(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """List reminders for a bill."""
    _require_finance_access(role)
    service = BillReminderService(db)
    reminders = await service.list_reminders(org.id, bill_id)
    return [BillReminderResponse.model_validate(r) for r in reminders]


@router.post("/reminders/{reminder_id}/cancel", response_model=BillReminderResponse)
async def cancel_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a scheduled reminder."""
    _require_finance_access(role)
    service = BillReminderService(db)
    reminder = await service.cancel_reminder(org.id, reminder_id)
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return BillReminderResponse.model_validate(reminder)


@router.post("/{bill_id}/payment-intents/fake", response_model=BillPaymentIntentResponse, status_code=status.HTTP_201_CREATED)
async def create_fake_payment_intent(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Create a fake payment intent for a bill. Does NOT execute payment."""
    _require_finance_access(role)
    service = BillPaymentIntentService(db)
    intent = await service.create_fake_payment_intent(org.id, bill_id, current_user.id)
    if not intent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return BillPaymentIntentResponse.model_validate(intent)


@router.post("/payment-intents/{intent_id}/authorize-fake", response_model=BillPaymentIntentResponse)
async def authorize_fake_intent(
    intent_id: int,
    body: BillPaymentIntentAuthorize,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Authorize a fake payment intent. Does NOT execute payment."""
    _require_finance_access(role)
    service = BillPaymentIntentService(db)
    intent = await service.authorize_fake_intent(org.id, intent_id, current_user.id, body.authorization_code)
    if not intent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intent not found or not authorizable")
    return BillPaymentIntentResponse.model_validate(intent)


@router.post("/payment-intents/{intent_id}/cancel", response_model=BillPaymentIntentResponse)
async def cancel_payment_intent(
    intent_id: int,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a payment intent."""
    _require_finance_access(role)
    service = BillPaymentIntentService(db)
    intent = await service.cancel_intent(org.id, intent_id, current_user.id)
    if not intent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intent not found")
    return BillPaymentIntentResponse.model_validate(intent)


@router.get("/{bill_id}/events", response_model=list[BillEventLogResponse])
async def get_bill_events(
    bill_id: int,
    current_user: User = Depends(get_current_user),
    org=Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get event logs for a bill."""
    _require_finance_access(role)
    service = BillService(db)
    events = await service.get_event_logs(org.id, bill_id)
    return [BillEventLogResponse.model_validate(e) for e in events]
