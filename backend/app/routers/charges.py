from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date, datetime, timezone
from decimal import Decimal
import csv
import io
import math
from app.core.database import get_db
from app.core.config import settings
from app.schemas.charge import (
    ChargeCreate, ChargeResponse, ChargeListResponse,
    PaginatedChargeListResponse, ChargeSummaryResponse, ChargeAnalyticsResponse,
)
from app.services.charge_service import ChargeService
from app.services.charge_reminder_service import ChargeReminderService
from app.utils.dependencies import get_current_active_user
from app.utils.user_rate_limiter import charges_limiter, exports_limiter
from app.core.audit_logger import log_charge_created, log_export
from app.models.user import User
from app.models.charge import ChargeStatus
from app.repositories.charge_repository import VALID_FILTER_STATUSES

router = APIRouter(prefix="/charges", tags=["Charges"])


def _validate_status(status: Optional[str]) -> Optional[str]:
    if status is not None and status not in VALID_FILTER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Valid values: {', '.join(sorted(VALID_FILTER_STATUSES))}"
        )
    return status


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
    await charges_limiter.check(current_user.id, "reminders_run")
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manual reminder trigger is not available in production"
        )
    service = ChargeReminderService(db)
    result = await service.run_reminders()
    return result


@router.get("", response_model=PaginatedChargeListResponse)
async def list_charges(
    status: Optional[str] = Query(None, description="Filter by status: pending, overdue, paid, cancelled, expired, failed"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by customer name or description"),
    start_date: Optional[date] = Query(None, description="Filter charges created from this date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter charges created up to this date (inclusive)"),
    sort_by: str = Query("created_at", description="Sort field: created_at, due_date, amount, status"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Legacy limit param (backward compat)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    status = _validate_status(status)
    service = ChargeService(db)

    # Backward compat: if limit is provided, use old non-paginated path
    if limit is not None:
        charges = await service.get_user_charges(current_user.id, limit=limit, status=status)
        return PaginatedChargeListResponse(
            items=charges, total=len(charges), page=1, page_size=limit, total_pages=1
        )

    result = await service.get_charges_paginated(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedChargeListResponse(**result)


@router.get("/export.csv")
async def export_charges_csv(
    status: Optional[str] = Query(None, description="Filter by status: pending, overdue, paid, cancelled, expired, failed"),
    start_date: Optional[date] = Query(None, description="Filter charges created from this date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter charges created up to this date (inclusive)"),
    search: Optional[str] = Query(None, description="Search by customer name or description"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await exports_limiter.check(current_user.id, "export_csv")
    """Export the authenticated user's charges as a CSV file."""
    status = _validate_status(status)
    service = ChargeService(db)
    result = await service.get_charges_paginated(
        user_id=current_user.id,
        page=1, page_size=10000,
        status=status, search=search,
        start_date=start_date, end_date=end_date,
    )
    charges = result["items"]

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


@router.get("/export.pdf")
async def export_charges_pdf(
    status: Optional[str] = Query(None, description="Filter by status: pending, overdue, paid, cancelled, expired, failed"),
    start_date: Optional[date] = Query(None, description="Filter charges created from this date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter charges created up to this date (inclusive)"),
    search: Optional[str] = Query(None, description="Search by customer name or description"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await exports_limiter.check(current_user.id, "export_pdf")
    """Export the authenticated user's charges as a PDF report."""
    status = _validate_status(status)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER

    service = ChargeService(db)
    result = await service.get_charges_paginated(
        user_id=current_user.id,
        page=1, page_size=10000,
        status=status, search=search,
        start_date=start_date, end_date=end_date,
    )
    charges = result["items"]
    summary = await service.get_summary(current_user.id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=18, alignment=TA_CENTER, spaceAfter=12)
    normal_style = styles['Normal']
    normal_style.fontSize = 10

    elements = []
    elements.append(Paragraph("Relatório de Cobranças — PayFlow AI", title_style))
    elements.append(Spacer(1, 0.5*cm))

    filter_desc = "Filtros: "
    parts = []
    if status: parts.append(f"status={status}")
    if start_date: parts.append(f"data inicial={start_date}")
    if end_date: parts.append(f"data final={end_date}")
    if search: parts.append(f"busca='{search}'")
    filter_desc += ", ".join(parts) if parts else "nenhum"
    elements.append(Paragraph(filter_desc, normal_style))
    elements.append(Paragraph(f"Data de geração: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}", normal_style))
    elements.append(Spacer(1, 0.8*cm))

    elements.append(Paragraph("<b>Resumo</b>", normal_style))
    elements.append(Spacer(1, 0.3*cm))
    summary_data = [
        ["Métrica", "Valor"],
        ["Total a receber", f"R$ {float(summary.total_receivable):.2f}"],
        ["Total recebido", f"R$ {float(summary.total_paid):.2f}"],
        ["Total vencido", f"R$ {float(summary.total_overdue):.2f}"],
        ["Qtd. pendentes", str(summary.count_pending)],
        ["Qtd. pagas", str(summary.count_paid)],
        ["Qtd. vencidas", str(summary.count_overdue)],
        ["Qtd. canceladas", str(summary.count_cancelled)],
    ]
    summary_table = Table(summary_data, colWidths=[6*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdfa')]),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 1*cm))

    elements.append(Paragraph("<b>Cobranças</b>", normal_style))
    elements.append(Spacer(1, 0.3*cm))

    table_data = [["Cliente", "Valor", "Descrição", "Status", "Vencimento", "Pagamento", "Criada"]]
    for c in charges:
        derived = service.get_derived_status(c)
        table_data.append([
            c.customer_name[:30],
            f"R$ {float(c.amount):.2f}",
            (c.description or "-")[:30],
            derived,
            c.due_date.strftime("%d/%m/%Y") if c.due_date else "-",
            c.paid_at.strftime("%d/%m/%Y") if c.paid_at else "-",
            c.created_at.strftime("%d/%m/%Y") if c.created_at else "-",
        ])

    charge_table = Table(table_data, colWidths=[3*cm, 2*cm, 3*cm, 2*cm, 2.2*cm, 2.2*cm, 2.2*cm])
    charge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdfa')]),
    ]))
    elements.append(charge_table)

    doc.build(elements)
    buffer.seek(0)
    filename = f"charges_report_{date.today().isoformat()}.pdf"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/analytics", response_model=ChargeAnalyticsResponse)
async def get_charge_analytics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Return analytics metrics for the authenticated user's charges.

    This is a global view of the user's charges — no status, date, or search
    filters are applied. All charges ever created by the user are included.

    conversion_rate = paid / (created - cancelled)
    overdue_rate = overdue / (pending + overdue)
    average_payment_time_hours = mean(paid_at - created_at) for paid charges
    """
    service = ChargeService(db)
    charges = await service.get_user_charges(current_user.id, limit=10000)

    total_created = len(charges)
    total_paid = sum(1 for c in charges if c.status == ChargeStatus.PAID)
    total_cancelled = sum(1 for c in charges if c.status == ChargeStatus.CANCELLED)

    today = date.today()
    total_overdue = sum(
        1 for c in charges
        if c.status == ChargeStatus.PENDING and c.due_date and c.due_date < today
    )
    total_pending = sum(1 for c in charges if c.status == ChargeStatus.PENDING)

    total_amount_created = sum((c.amount for c in charges), Decimal("0"))
    total_amount_paid = sum((c.amount for c in charges if c.status == ChargeStatus.PAID), Decimal("0"))

    eligible = total_created - total_cancelled
    conversion_rate = (total_paid / eligible * 100) if eligible > 0 else 0.0

    overdue_rate = (total_overdue / (total_pending + total_overdue) * 100) if (total_pending + total_overdue) > 0 else 0.0

    paid_charges = [c for c in charges if c.status == ChargeStatus.PAID and c.paid_at and c.created_at]
    if paid_charges:
        total_hours = sum(
            (c.paid_at - c.created_at).total_seconds() / 3600
            for c in paid_charges
        )
        avg_hours = total_hours / len(paid_charges)
    else:
        avg_hours = 0.0

    return ChargeAnalyticsResponse(
        conversion_rate=round(conversion_rate, 2),
        average_payment_time_hours=round(avg_hours, 2),
        total_created=total_created,
        total_paid=total_paid,
        total_cancelled=total_cancelled,
        total_overdue=total_overdue,
        total_amount_created=total_amount_created,
        total_amount_paid=total_amount_paid,
        overdue_rate=round(overdue_rate, 2),
        payment_by_status={
            "pending": total_pending - total_overdue,
            "paid": total_paid,
            "overdue": total_overdue,
            "cancelled": total_cancelled,
        },
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
    await charges_limiter.check(current_user.id, "create_charge")
    service = ChargeService(db)
    charge = await service.create_charge(current_user.id, charge_data)
    log_charge_created(current_user.id, charge.id, charge.provider, str(charge.amount))
    return charge


@router.post("/{charge_id}/cancel", response_model=ChargeResponse)
async def cancel_charge(
    charge_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await charges_limiter.check(current_user.id, "cancel_charge")
    service = ChargeService(db)
    charge = await service.cancel_charge(charge_id, current_user.id)
    if not charge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Charge cannot be cancelled or not found"
        )
    return charge
