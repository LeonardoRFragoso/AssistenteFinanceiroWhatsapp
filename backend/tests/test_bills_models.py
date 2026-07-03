"""
Tests for bill management models — Sprint 17.
"""
import pytest
import pytest_asyncio
from datetime import date
from decimal import Decimal

from app.models.bills import (
    DetectedBill, BillReminder, BillPaymentIntent, BillEventLog,
    BillStatus, BillSource, BillType, BillRiskLevel,
    BillReminderStatus, BillReminderChannel,
    PaymentIntentStatus, PaymentIntentType, BillEventAction,
)


def test_bill_status_enum_values():
    assert BillStatus.DETECTED.value == "detected"
    assert BillStatus.PENDING.value == "pending"
    assert BillStatus.DUE_TODAY.value == "due_today"
    assert BillStatus.OVERDUE.value == "overdue"
    assert BillStatus.PAID_MANUAL.value == "paid_manual"
    assert BillStatus.IGNORED.value == "ignored"
    assert BillStatus.CANCELLED.value == "cancelled"
    assert BillStatus.EXPIRED.value == "expired"


def test_bill_source_enum_values():
    assert BillSource.FAKE_DDA.value == "fake_dda"
    assert BillSource.OCR.value == "ocr"
    assert BillSource.MANUAL.value == "manual"
    assert BillSource.IMPORTED.value == "imported"
    assert BillSource.FUTURE_PROVIDER.value == "future_provider"


def test_bill_type_enum_values():
    assert BillType.BOLETO.value == "boleto"
    assert BillType.UTILITY.value == "utility"
    assert BillType.TAX.value == "tax"
    assert BillType.RENT.value == "rent"
    assert BillType.SERVICE.value == "service"
    assert BillType.SUBSCRIPTION.value == "subscription"
    assert BillType.OTHER.value == "other"


def test_payment_intent_status_enum_values():
    assert PaymentIntentStatus.DRAFT.value == "draft"
    assert PaymentIntentStatus.PENDING_AUTHORIZATION.value == "pending_authorization"
    assert PaymentIntentStatus.AUTHORIZED_FAKE.value == "authorized_fake"
    assert PaymentIntentStatus.CANCELLED.value == "cancelled"
    assert PaymentIntentStatus.EXPIRED.value == "expired"
    assert PaymentIntentStatus.FAILED.value == "failed"


def test_bill_event_action_enum_values():
    assert BillEventAction.BILL_DETECTED.value == "bill_detected"
    assert BillEventAction.BILL_IGNORED.value == "bill_ignored"
    assert BillEventAction.BILL_MARKED_PAID_MANUAL.value == "bill_marked_paid_manual"
    assert BillEventAction.REMINDER_SCHEDULED.value == "reminder_scheduled"
    assert BillEventAction.PAYMENT_INTENT_CREATED.value == "payment_intent_created"
    assert BillEventAction.PAYMENT_INTENT_AUTHORIZED_FAKE.value == "payment_intent_authorized_fake"
    assert BillEventAction.PAYMENT_INTENT_CANCELLED.value == "payment_intent_cancelled"
    assert BillEventAction.SYNC_FAKE_DDA.value == "sync_fake_dda"


@pytest_asyncio.fixture
async def sample_bill(db_session, sample_organization, sample_user):
    bill = DetectedBill(
        organization_id=sample_organization.id,
        user_id=sample_user.id,
        provider_name="fake",
        provider_bill_id="fake_dda_test123",
        source=BillSource.FAKE_DDA,
        title="Light Energia — Energia",
        beneficiary_name="Light Energia",
        beneficiary_document_masked="***.***.123-**",
        payer_name="Empresa Demo LTDA",
        amount=Decimal("150.50"),
        currency="BRL",
        due_date=date(2025, 7, 10),
        issue_date=date(2025, 6, 20),
        barcode="00000000000000000000000000000000000000000000",
        digitable_line="00000000000.00000000000 00000000000.00000000000",
        bill_type=BillType.UTILITY,
        category="Energia",
        status=BillStatus.PENDING,
        risk_level=BillRiskLevel.LOW,
        is_demo_data=True,
    )
    db_session.add(bill)
    await db_session.commit()
    await db_session.refresh(bill)
    return bill


async def test_detected_bill_creation(db_session, sample_bill):
    assert sample_bill.id is not None
    assert sample_bill.organization_id is not None
    assert sample_bill.amount == Decimal("150.50")
    assert sample_bill.is_demo_data is True
    assert sample_bill.status == BillStatus.PENDING


async def test_bill_reminder_creation(db_session, sample_bill):
    reminder = BillReminder(
        organization_id=sample_bill.organization_id,
        detected_bill_id=sample_bill.id,
        reminder_date=date(2025, 7, 9),
        channel=BillReminderChannel.WHATSAPP,
        status=BillReminderStatus.SCHEDULED,
        message_preview="Lembrete: Light Energia vence em 10/07/2025",
    )
    db_session.add(reminder)
    await db_session.commit()
    await db_session.refresh(reminder)
    assert reminder.id is not None
    assert reminder.detected_bill_id == sample_bill.id
    assert reminder.status == BillReminderStatus.SCHEDULED


async def test_bill_payment_intent_creation(db_session, sample_bill, sample_user):
    intent = BillPaymentIntent(
        organization_id=sample_bill.organization_id,
        detected_bill_id=sample_bill.id,
        user_id=sample_user.id,
        provider_name="fake",
        amount=Decimal("150.50"),
        currency="BRL",
        status=PaymentIntentStatus.DRAFT,
        intent_type=PaymentIntentType.FAKE_BOLETO,
        fake_payment_reference="FAKE-TEST123456",
        metadata_sanitized={"demo": True, "note": "Fake intent"},
    )
    db_session.add(intent)
    await db_session.commit()
    await db_session.refresh(intent)
    assert intent.id is not None
    assert intent.status == PaymentIntentStatus.DRAFT
    assert intent.fake_payment_reference == "FAKE-TEST123456"


async def test_bill_event_log_creation(db_session, sample_bill, sample_user):
    event = BillEventLog(
        organization_id=sample_bill.organization_id,
        detected_bill_id=sample_bill.id,
        actor_user_id=sample_user.id,
        action=BillEventAction.BILL_DETECTED,
        metadata_sanitized={"provider": "fake_dda"},
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    assert event.id is not None
    assert event.action == BillEventAction.BILL_DETECTED


async def test_bill_org_isolation(db_session, sample_bill, second_organization, second_user):
    bill2 = DetectedBill(
        organization_id=second_organization.id,
        user_id=second_user.id,
        provider_name="fake",
        provider_bill_id="fake_dda_other456",
        source=BillSource.FAKE_DDA,
        title="Vivo Empresas — Telecom",
        beneficiary_name="Vivo Empresas",
        amount=Decimal("89.90"),
        currency="BRL",
        due_date=date(2025, 7, 15),
        bill_type=BillType.SERVICE,
        category="Telecom",
        status=BillStatus.PENDING,
        risk_level=BillRiskLevel.LOW,
        is_demo_data=True,
    )
    db_session.add(bill2)
    await db_session.commit()
    await db_session.refresh(bill2)
    assert bill2.organization_id != sample_bill.organization_id
