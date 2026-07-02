from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date, datetime, timezone
import csv
import io
from app.core.database import get_db
from app.utils.dependencies import get_current_active_user, get_current_organization, get_current_user_role
from app.services.charge_analytics_service import ChargeAnalyticsService
from app.core.permissions import has_permission
from app.models.user import User
from app.models.organization import Organization, OrganizationRole

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def get_analytics_overview(
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter up to this date"),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get advanced analytics overview for the authenticated user."""
    if not has_permission(role, "view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow viewing analytics",
        )
    service = ChargeAnalyticsService(db)
    return await service.get_overview(current_user.id, org.id, start_date, end_date)


@router.get("/monthly-trends")
async def get_monthly_trends(
    months: int = Query(6, ge=1, le=12, description="Number of months to include"),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly trends for the authenticated user."""
    if not has_permission(role, "view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow viewing analytics",
        )
    service = ChargeAnalyticsService(db)
    return await service.get_monthly_trends(current_user.id, org.id, months)


@router.get("/aging")
async def get_aging(
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get aging buckets for overdue charges."""
    if not has_permission(role, "view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow viewing analytics",
        )
    service = ChargeAnalyticsService(db)
    return await service.get_aging(current_user.id, org.id)


@router.get("/customer-performance")
async def get_customer_performance(
    limit: int = Query(10, ge=1, le=50, description="Max customers to return"),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get customer performance ranking."""
    if not has_permission(role, "view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow viewing analytics",
        )
    service = ChargeAnalyticsService(db)
    return await service.get_customer_performance(current_user.id, org.id, limit)


@router.get("/collection-performance")
async def get_collection_performance(
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get collection rule performance metrics."""
    if not has_permission(role, "view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow viewing analytics",
        )
    service = ChargeAnalyticsService(db)
    return await service.get_collection_performance(current_user.id, org.id)


@router.get("/insights")
async def get_insights(
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter up to this date"),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Get textual insights in Portuguese based on analytics data."""
    if not has_permission(role, "view_analytics"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow viewing analytics",
        )
    service = ChargeAnalyticsService(db)
    return {"insights": await service.get_insights(current_user.id, org.id, start_date, end_date)}


@router.get("/export.csv")
async def export_analytics_csv(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Export analytics data as CSV."""
    if not has_permission(role, "export_data"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow exporting data",
        )
    service = ChargeAnalyticsService(db)
    overview = await service.get_overview(current_user.id, org.id, start_date, end_date)
    trends = await service.get_monthly_trends(current_user.id, org.id, months=6)
    aging = await service.get_aging(current_user.id, org.id)
    customer_perf = await service.get_customer_performance(current_user.id, org.id, limit=10)
    insights = await service.get_insights(current_user.id, org.id, start_date, end_date)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["=== OVERVIEW ==="])
    for key, val in overview.items():
        writer.writerow([key, val])

    writer.writerow([])
    writer.writerow(["=== MONTHLY TRENDS ==="])
    writer.writerow(["month", "billed_amount", "paid_amount", "pending_amount", "overdue_amount", "charges_created", "charges_paid", "collection_rate"])
    for t in trends:
        writer.writerow([t["month"], t["billed_amount"], t["paid_amount"], t["pending_amount"], t["overdue_amount"], t["charges_created"], t["charges_paid"], t["collection_rate"]])

    writer.writerow([])
    writer.writerow(["=== AGING ==="])
    writer.writerow(["bucket", "count", "amount", "percentage"])
    for b in aging["buckets"]:
        writer.writerow([b["bucket"], b["count"], b["amount"], b["percentage"]])

    writer.writerow([])
    writer.writerow(["=== CUSTOMER PERFORMANCE ==="])
    writer.writerow(["customer_name", "operational_status", "total_billed", "total_paid", "total_pending", "total_overdue", "average_payment_delay_days", "charges_count", "last_payment_at", "suggested_action"])
    for c in customer_perf:
        writer.writerow([c["customer_name"], c["operational_status"], c["total_billed"], c["total_paid"], c["total_pending"], c["total_overdue"], c["average_payment_delay_days"], c["charges_count"], c["last_payment_at"] or "", c["suggested_action"]])

    writer.writerow([])
    writer.writerow(["=== INSIGHTS ==="])
    for insight in insights:
        writer.writerow([insight])

    output.seek(0)
    filename = f"analytics_export_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export.pdf")
async def export_analytics_pdf(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Export analytics data as PDF report."""
    if not has_permission(role, "export_data"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow exporting data",
        )
    service = ChargeAnalyticsService(db)
    overview = await service.get_overview(current_user.id, org.id, start_date, end_date)
    trends = await service.get_monthly_trends(current_user.id, org.id, months=6)
    aging = await service.get_aging(current_user.id, org.id)
    customer_perf = await service.get_customer_performance(current_user.id, org.id, limit=10)
    insights = await service.get_insights(current_user.id, org.id, start_date, end_date)

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=18, alignment=TA_CENTER, spaceAfter=12)
    normal_style = styles['Normal']
    normal_style.fontSize = 10

    elements = []
    elements.append(Paragraph("Relatório de Analytics — PayFlow AI", title_style))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"Data de geração: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}", normal_style))
    elements.append(Spacer(1, 0.8*cm))

    # Overview
    elements.append(Paragraph("<b>Visão Geral</b>", normal_style))
    elements.append(Spacer(1, 0.3*cm))
    overview_data = [
        ["Métrica", "Valor"],
        ["Total cobrado", f"R$ {overview['total_billed']:.2f}"],
        ["Total recebido", f"R$ {overview['total_paid']:.2f}"],
        ["Total pendente", f"R$ {overview['total_pending']:.2f}"],
        ["Total vencido", f"R$ {overview['total_overdue']:.2f}"],
        ["Taxa de recebimento", f"{overview['collection_rate']:.1f}%"],
        ["Taxa de vencimento", f"{overview['overdue_rate']:.1f}%"],
        ["Tempo médio de pagamento", f"{overview['average_payment_time_days'] or 'N/A'} dias"],
        ["Atraso médio", f"{overview['average_delay_days'] or 'N/A'} dias"],
        ["Clientes ativos", str(overview['active_customers'])],
        ["Clientes com vencido", str(overview['overdue_customers'])],
        ["Rascunhos de follow-up", str(overview['followups_drafted'])],
    ]
    t = Table(overview_data, colWidths=[7*cm, 5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdfa')]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 1*cm))

    # Monthly trends
    elements.append(Paragraph("<b>Tendências Mensais</b>", normal_style))
    elements.append(Spacer(1, 0.3*cm))
    trend_data = [["Mês", "Cobrado", "Recebido", "Pendente", "Vencido", "Taxa"]]
    for tr in trends:
        trend_data.append([
            tr["month"],
            f"R$ {tr['billed_amount']:.2f}",
            f"R$ {tr['paid_amount']:.2f}",
            f"R$ {tr['pending_amount']:.2f}",
            f"R$ {tr['overdue_amount']:.2f}",
            f"{tr['collection_rate']:.1f}%",
        ])
    t2 = Table(trend_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdfa')]),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 1*cm))

    # Aging
    elements.append(Paragraph("<b>Aging de Cobranças Vencidas</b>", normal_style))
    elements.append(Spacer(1, 0.3*cm))
    aging_data = [["Faixa", "Qtd", "Valor", "%"]]
    for b in aging["buckets"]:
        aging_data.append([b["bucket"], str(b["count"]), f"R$ {b['amount']:.2f}", f"{b['percentage']:.1f}%"])
    t3 = Table(aging_data, colWidths=[4*cm, 2*cm, 4*cm, 2*cm])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fef3c7')]),
    ]))
    elements.append(t3)
    elements.append(Spacer(1, 1*cm))

    # Customer performance
    elements.append(Paragraph("<b>Top Clientes — Performance</b>", normal_style))
    elements.append(Spacer(1, 0.3*cm))
    cust_data = [["Cliente", "Cobrado", "Pago", "Vencido", "Atraso méd.", "Ação"]]
    for c in customer_perf:
        cust_data.append([
            c["customer_name"][:20],
            f"R$ {c['total_billed']:.2f}",
            f"R$ {c['total_paid']:.2f}",
            f"R$ {c['total_overdue']:.2f}",
            f"{c['average_payment_delay_days']:.0f}d",
            c["suggested_action"],
        ])
    t4 = Table(cust_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm, 3*cm])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdfa')]),
    ]))
    elements.append(t4)
    elements.append(Spacer(1, 1*cm))

    # Insights
    elements.append(Paragraph("<b>Insights</b>", normal_style))
    elements.append(Spacer(1, 0.3*cm))
    for insight in insights:
        elements.append(Paragraph(f"• {insight}", normal_style))
        elements.append(Spacer(1, 0.2*cm))

    doc.build(elements)
    buffer.seek(0)
    filename = f"analytics_report_{date.today().isoformat()}.pdf"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
