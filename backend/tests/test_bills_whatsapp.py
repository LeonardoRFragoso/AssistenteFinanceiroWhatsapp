"""
Tests for bill WhatsApp intents — Sprint 17.
"""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.routers.webhook import (
    handle_list_due_bills,
    handle_list_overdue_bills,
    handle_list_bills_due_today,
    handle_bill_summary,
    handle_search_bills,
    handle_create_bill_reminder,
    handle_prepare_fake_bill_payment,
    handle_mark_bill_paid_manual,
    handle_ignore_bill,
)
from app.models.bills import DetectedBill, BillStatus, BillSource, BillType, BillRiskLevel


@pytest_asyncio.fixture
async def bills_for_whatsapp(db_session, sample_organization, sample_user):
    today = date.today()
    bills = []
    for i, (offset, status, amount, name, category) in enumerate([
        (-5, BillStatus.OVERDUE, Decimal("200.00"), "Light Energia", "Energia"),
        (0, BillStatus.DUE_TODAY, Decimal("150.00"), "Vivo Empresas", "Telecom"),
        (7, BillStatus.PENDING, Decimal("89.90"), "Claro", "Telecom"),
    ]):
        bill = DetectedBill(
            organization_id=sample_organization.id,
            user_id=sample_user.id,
            provider_name="fake",
            provider_bill_id=f"wa_test_{i}",
            source=BillSource.FAKE_DDA,
            title=f"{name} — {category}",
            beneficiary_name=name,
            amount=amount,
            currency="BRL",
            due_date=today + timedelta(days=offset),
            bill_type=BillType.UTILITY,
            category=category,
            status=status,
            risk_level=BillRiskLevel.LOW,
            is_demo_data=True,
        )
        db_session.add(bill)
        bills.append(bill)
    await db_session.commit()
    for b in bills:
        await db_session.refresh(b)
    return bills


def _mock_ai():
    ai = MagicMock()
    ai.generate_response = AsyncMock(return_value="OK")
    ai.classify_intent = AsyncMock(return_value={"intent": "test", "entities": {}})
    return ai


async def test_handle_list_due_bills(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_list_due_bills(sample_user.id, {}, db_session, _mock_ai(), "")
    assert "demonstração" in msg.lower() or "demo" in msg.lower()


async def test_handle_list_overdue_bills(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_list_overdue_bills(sample_user.id, {}, db_session, _mock_ai(), "")
    assert "demonstração" in msg.lower() or "demo" in msg.lower()
    assert "Light" in msg


async def test_handle_list_bills_due_today(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_list_bills_due_today(sample_user.id, {"days": 7}, db_session, _mock_ai(), "")
    assert "demonstração" in msg.lower() or "demo" in msg.lower()


async def test_handle_bill_summary(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_bill_summary(sample_user.id, {}, db_session, _mock_ai(), "")
    assert "demonstração" in msg.lower() or "demo" in msg.lower()
    assert "Resumo" in msg or "resumo" in msg


async def test_handle_search_bills(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_search_bills(
        sample_user.id, {"search_term": "Light"}, db_session, _mock_ai(), ""
    )
    assert "Light" in msg
    assert "demonstração" in msg.lower() or "demo" in msg.lower()


async def test_handle_search_bills_no_term(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_search_bills(sample_user.id, {}, db_session, _mock_ai(), "")
    assert "buscar" in msg.lower() or "termo" in msg.lower()


async def test_handle_create_bill_reminder(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_create_bill_reminder(
        sample_user.id, {"beneficiary": "Light", "days_ahead": 1}, db_session, _mock_ai(), ""
    )
    assert "Lembrete" in msg
    assert "demonstração" in msg.lower() or "demo" in msg.lower()


async def test_handle_prepare_fake_bill_payment(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_prepare_fake_bill_payment(
        sample_user.id, {"beneficiary": "Vivo"}, db_session, _mock_ai(), ""
    )
    assert "fake" in msg.lower() or "demonstração" in msg.lower()
    assert "intenção" in msg.lower()
    assert "pagamento real" in msg.lower()
    assert "nenhum" in msg.lower() or "não" in msg.lower()


async def test_handle_mark_bill_paid_manual(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_mark_bill_paid_manual(
        sample_user.id, {"beneficiary": "Claro"}, db_session, _mock_ai(), ""
    )
    assert "paga" in msg.lower()
    assert "demonstração" in msg.lower() or "demo" in msg.lower()
    assert "pagamento real" in msg.lower() or "nenhum pagamento" in msg.lower()


async def test_handle_ignore_bill(db_session, bills_for_whatsapp, sample_user):
    msg = await handle_ignore_bill(
        sample_user.id, {"beneficiary": "Claro"}, db_session, _mock_ai(), ""
    )
    assert "ignorada" in msg.lower()
    assert "demonstração" in msg.lower() or "demo" in msg.lower()
