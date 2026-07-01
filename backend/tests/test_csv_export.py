import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.charge_service import ChargeService
from app.schemas.charge import ChargeCreate
from app.models.charge import ChargeStatus


@pytest.mark.asyncio
async def test_csv_export_contains_all_columns(db_session, sample_user):
    """CSV export includes all expected columns."""
    import csv
    import io
    from app.routers.charges import export_charges_csv
    from unittest.mock import AsyncMock

    service = ChargeService(db_session)
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Cliente CSV",
        customer_phone="+5511123456789",
        amount=Decimal("100.00"),
        description="Test export",
        provider="fake"
    ))

    charges = await service.get_user_charges(sample_user.id, limit=10000)
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
            c.id, c.customer_name, c.customer_phone or "",
            f"{float(c.amount):.2f}", c.description or "",
            c.status.value, derived,
            c.due_date.isoformat() if c.due_date else "",
            c.paid_at.isoformat() if c.paid_at else "",
            c.created_at.isoformat() if c.created_at else "",
            c.payment_link or ""
        ])

    output.seek(0)
    reader = csv.DictReader(output)
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["customer_name"] == "Cliente CSV"
    assert rows[0]["status"] == "pending"
    assert rows[0]["derived_status"] == "pending"
    assert rows[0]["amount"] == "100.00"


@pytest.mark.asyncio
async def test_csv_export_respects_status_filter(db_session, sample_user):
    """CSV export with status filter only includes matching charges."""
    import csv
    import io

    service = ChargeService(db_session)

    # Create pending charge
    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Pendente",
        amount=Decimal("100.00"),
        provider="fake"
    ))

    # Create and pay a charge
    paid = await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Paga",
        amount=Decimal("200.00"),
        provider="fake"
    ))
    payload = {
        "event_type": "payment.approved",
        "provider_charge_id": paid.provider_charge_id,
        "amount": 200.0
    }
    await service.process_webhook_payload("fake", payload)

    # Filter by paid only
    paid_charges = await service.get_user_charges(sample_user.id, limit=10000, status="paid")
    assert len(paid_charges) == 1
    assert paid_charges[0].customer_name == "Paga"

    # Filter by pending only
    pending_charges = await service.get_user_charges(sample_user.id, limit=10000, status="pending")
    assert len(pending_charges) == 1
    assert pending_charges[0].customer_name == "Pendente"


@pytest.mark.asyncio
async def test_csv_export_includes_derived_status_overdue(db_session, sample_user):
    """CSV export shows derived_status as overdue for past-due pending charges."""
    import csv
    import io

    service = ChargeService(db_session)
    past_date = date.today() - timedelta(days=5)

    await service.create_charge(sample_user.id, ChargeCreate(
        customer_name="Vencida CSV",
        amount=Decimal("300.00"),
        due_date=past_date,
        provider="fake"
    ))

    charges = await service.get_user_charges(sample_user.id, limit=10000)
    assert len(charges) == 1
    derived = service.get_derived_status(charges[0])
    assert derived == "overdue"
