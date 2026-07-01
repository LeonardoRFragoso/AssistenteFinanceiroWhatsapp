from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
import csv
import io
from app.core.database import get_db
from app.core.config import settings
from app.schemas.charge import ChargeCreate, ChargeResponse, ChargeListResponse, ChargeSummaryResponse
from app.services.charge_service import ChargeService
from app.services.charge_reminder_service import ChargeReminderService
from app.utils.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/charges", tags=["Charges"])


@router.get("/summary", response_model=ChargeSummaryResponse)
async def get_charge_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ChargeService(db)
    return await service.get_summary(current_user.id)


@router.post("/reminders/run")
async def run_charge_reminders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manual reminder trigger is not available in production"
        )
    service = ChargeReminderService(db)
    result = await service.run_reminders()
    return result


@router.get("", response_model=ChargeListResponse)
async def list_charges(
    status: Optional[str] = Query(None, description="Filter by status: pending, paid, expired, cancelled, failed"),
    limit: int = Query(50, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ChargeService(db)
    charges = await service.get_user_charges(current_user.id, limit=limit, status=status)
    return ChargeListResponse(items=charges, total=len(charges))


@router.get("/export.csv")
async def export_charges_csv(
    status: Optional[str] = Query(None, description="Filter by status: pending, paid, cancelled, overdue"),
    start_date: Optional[date] = Query(None, description="Filter charges created after this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter charges created before this date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Export the authenticated user's charges as a CSV file."""
    service = ChargeService(db)
    charges = await service.get_user_charges(current_user.id, limit=10000, status=status)

    if start_date:
        charges = [c for c in charges if c.created_at.date() >= start_date]
    if end_date:
        charges = [c for c in charges if c.created_at.date() <= end_date]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "customer_name", "customer_phone", "amount", "description",
        "status", "derived_status", "due_date", "paid_at", "created_at",
        "payment_link"
    ])

    for c in charges:
        derived = service.get_derived_status(c)
        writer.writerow([
            c.id,
            c.customer_name,
            c.customer_phone or "",
            f"{float(c.amount):.2f}",
            c.description or "",
            c.status.value,
            derived,
            c.due_date.isoformat() if c.due_date else "",
            c.paid_at.isoformat() if c.paid_at else "",
            c.created_at.isoformat() if c.created_at else "",
            c.payment_link or ""
        ])

    output.seek(0)
    filename = f"charges_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{charge_id}", response_model=ChargeResponse)
async def get_charge(
    charge_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ChargeService(db)
    charge = await service.get_charge(charge_id, current_user.id)
    if not charge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Charge not found"
        )
    return charge


@router.post("", response_model=ChargeResponse, status_code=status.HTTP_201_CREATED)
async def create_charge(
    charge_data: ChargeCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ChargeService(db)
    return await service.create_charge(current_user.id, charge_data)


@router.post("/{charge_id}/cancel", response_model=ChargeResponse)
async def cancel_charge(
    charge_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ChargeService(db)
    charge = await service.cancel_charge(charge_id, current_user.id)
    if not charge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Charge cannot be cancelled or not found"
        )
    return charge
