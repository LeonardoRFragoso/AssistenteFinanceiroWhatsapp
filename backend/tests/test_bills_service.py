"""
Tests for bill service — Sprint 17.
"""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from decimal import Decimal

from app.services.bill_service import BillService
from app.services.bill_summary_service import BillSummaryService
from app.models.bills import DetectedBill, BillStatus, BillSource, BillType, BillRiskLevel


@pytest_asyncio.fixture
async def bill_with_data(db_session, sample_organization, sample_user):
    today = date.today()
    bills = []
    for i, (offset, status, amount, name, category) in enumerate([
        (-10, BillStatus.OVERDUE, Decimal("500.00"), "Light Energia", "Energia"),
        (-5, BillStatus.OVERDUE, Decimal("200.00"), "Águas do Rio", "Água"),
        (0, BillStatus.DUE_TODAY, Decimal("150.00"), "Vivo Empresas", "Telecom"),
        (3, BillStatus.PENDING, Decimal("89.90"), "Claro", "Telecom"),
        (7, BillStatus.PENDING, Decimal("1200.00"), "Aluguel Escritório", "Aluguel"),
        (15, BillStatus.PENDING, Decimal("350.00"), "Contabilidade Express", "Contabilidade"),
    ]):
        bill = DetectedBill(
            organization_id=sample_organization.id,
            user_id=sample_user.id,
            provider_name="fake",
            provider_bill_id=f"fake_test_{i}",
            source=BillSource.FAKE_DDA,
            title=f"{name} — {category}",
            beneficiary_name=name,
            amount=amount,
            currency="BRL",
            due_date=today + timedelta(days=offset),
            bill_type=BillType.UTILITY if category in ("Energia", "Água") else BillType.SERVICE,
            category=category,
            status=status,
            risk_level=BillRiskLevel.HIGH if amount > 1000 else BillRiskLevel.LOW,
            is_demo_data=True,
        )
        db_session.add(bill)
        bills.append(bill)
    await db_session.commit()
    for b in bills:
        await db_session.refresh(b)
    return bills


async def test_sync_fake_bills(db_session, sample_organization, sample_user):
    service = BillService(db_session)
    result = await service.sync_fake_bills(sample_organization.id, sample_user.id)
    assert result["created"] > 0
    assert result["created"] >= 8
    assert result["created"] <= 15
    assert result["is_demo_data"] if "is_demo_data" in result else True


async def test_sync_fake_bills_idempotent(db_session, sample_organization, sample_user):
    service = BillService(db_session)
    first = await service.sync_fake_bills(sample_organization.id, sample_user.id)
    second = await service.sync_fake_bills(sample_organization.id, sample_user.id)
    assert first["created"] > 0
    assert second["created"] == 0
    assert second["skipped"] == first["created"]


async def test_list_bills(db_session, bill_with_data):
    service = BillService(db_session)
    org_id = bill_with_data[0].organization_id
    bills = await service.list_bills(org_id)
    assert len(bills) == 6


async def test_list_bills_filter_status(db_session, bill_with_data):
    service = BillService(db_session)
    org_id = bill_with_data[0].organization_id
    bills = await service.list_bills(org_id, status_filter=BillStatus.OVERDUE)
    assert len(bills) == 2
    assert all(b.status == BillStatus.OVERDUE for b in bills)


async def test_list_bills_filter_category(db_session, bill_with_data):
    service = BillService(db_session)
    org_id = bill_with_data[0].organization_id
    bills = await service.list_bills(org_id, category="Telecom")
    assert len(bills) == 2
    assert all(b.category == "Telecom" for b in bills)


async def test_list_bills_search(db_session, bill_with_data):
    service = BillService(db_session)
    org_id = bill_with_data[0].organization_id
    bills = await service.list_bills(org_id, search="Light")
    assert len(bills) == 1
    assert "Light" in bills[0].title


async def test_get_bill(db_session, bill_with_data):
    service = BillService(db_session)
    org_id = bill_with_data[0].organization_id
    bill = await service.get_bill(org_id, bill_with_data[0].id)
    assert bill is not None
    assert bill.id == bill_with_data[0].id


async def test_get_bill_wrong_org(db_session, bill_with_data, second_organization):
    service = BillService(db_session)
    bill = await service.get_bill(second_organization.id, bill_with_data[0].id)
    assert bill is None


async def test_ignore_bill(db_session, bill_with_data, sample_user):
    service = BillService(db_session)
    org_id = bill_with_data[0].organization_id
    bill = await service.ignore_bill(org_id, bill_with_data[0].id, sample_user.id)
    assert bill is not None
    assert bill.status == BillStatus.IGNORED
    assert bill.ignored_at is not None


async def test_mark_paid_manual(db_session, bill_with_data, sample_user):
    service = BillService(db_session)
    org_id = bill_with_data[0].organization_id
    bill = await service.mark_paid_manual(org_id, bill_with_data[0].id, sample_user.id)
    assert bill is not None
    assert bill.status == BillStatus.PAID_MANUAL
    assert bill.manually_marked_paid_at is not None


async def test_get_event_logs(db_session, bill_with_data, sample_user):
    service = BillService(db_session)
    org_id = bill_with_data[0].organization_id
    await service.ignore_bill(org_id, bill_with_data[0].id, sample_user.id)
    events = await service.get_event_logs(org_id, bill_with_data[0].id)
    assert len(events) >= 1


async def test_summary_overdue(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    summary = await service.get_summary(org_id)
    assert Decimal(summary["overdue_total"]) == Decimal("700.00")
    assert summary["overdue_count"] == 2


async def test_summary_due_today(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    summary = await service.get_summary(org_id)
    assert Decimal(summary["due_today_total"]) == Decimal("150.00")
    assert summary["due_today_count"] == 1


async def test_summary_upcoming_7(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    summary = await service.get_summary(org_id)
    assert Decimal(summary["upcoming_7_days_total"]) == Decimal("1289.90")


async def test_summary_upcoming_30(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    summary = await service.get_summary(org_id)
    assert Decimal(summary["upcoming_30_days_total"]) == Decimal("1639.90")


async def test_summary_open_total(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    summary = await service.get_summary(org_id)
    assert Decimal(summary["open_total"]) == Decimal("2489.90")


async def test_summary_top_categories(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    summary = await service.get_summary(org_id)
    assert len(summary["top_categories"]) > 0


async def test_summary_top_beneficiaries(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    summary = await service.get_summary(org_id)
    assert len(summary["top_beneficiaries"]) > 0


async def test_get_due_today(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    bills = await service.get_due_today(org_id)
    assert len(bills) == 1
    assert bills[0].status == BillStatus.DUE_TODAY


async def test_get_overdue(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    bills = await service.get_overdue(org_id)
    assert len(bills) == 2


async def test_get_upcoming(db_session, bill_with_data):
    service = BillSummaryService(db_session)
    org_id = bill_with_data[0].organization_id
    bills = await service.get_upcoming(org_id, days=7)
    assert len(bills) == 2
