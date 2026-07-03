"""
Tests for bill payment intents — Sprint 17.
"""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from decimal import Decimal

from app.services.bill_payment_intent_service import BillPaymentIntentService
from app.services.bill_service import BillService
from app.models.bills import (
    DetectedBill, BillPaymentIntent, BillEventLog,
    BillStatus, BillSource, BillType, BillRiskLevel,
    PaymentIntentStatus, PaymentIntentType, BillEventAction,
)


@pytest_asyncio.fixture
async def sample_bill_for_intent(db_session, sample_organization, sample_user):
    bill = DetectedBill(
        organization_id=sample_organization.id,
        user_id=sample_user.id,
        provider_name="fake",
        provider_bill_id="intent_test_001",
        source=BillSource.FAKE_DDA,
        title="Vivo Empresas — Telecom",
        beneficiary_name="Vivo Empresas",
        amount=Decimal("150.00"),
        currency="BRL",
        due_date=date.today() + timedelta(days=5),
        bill_type=BillType.SERVICE,
        category="Telecom",
        status=BillStatus.PENDING,
        risk_level=BillRiskLevel.LOW,
        is_demo_data=True,
    )
    db_session.add(bill)
    await db_session.commit()
    await db_session.refresh(bill)
    return bill


async def test_create_fake_payment_intent(db_session, sample_bill_for_intent, sample_user):
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        sample_bill_for_intent.organization_id,
        sample_bill_for_intent.id,
        sample_user.id,
    )
    assert intent is not None
    assert intent.status == PaymentIntentStatus.DRAFT
    assert intent.fake_payment_reference is not None
    assert "FAKE" in intent.fake_payment_reference
    assert intent.amount == Decimal("150.00")


async def test_create_intent_wrong_org(db_session, sample_bill_for_intent, second_organization, second_user):
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        second_organization.id,
        sample_bill_for_intent.id,
        second_user.id,
    )
    assert intent is None


async def test_authorize_fake_intent(db_session, sample_bill_for_intent, sample_user):
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        sample_bill_for_intent.organization_id,
        sample_bill_for_intent.id,
        sample_user.id,
    )
    authorized = await service.authorize_fake_intent(
        sample_bill_for_intent.organization_id,
        intent.id,
        sample_user.id,
        authorization_code="123456",
    )
    assert authorized is not None
    assert authorized.status == PaymentIntentStatus.AUTHORIZED_FAKE
    assert authorized.confirmed_at is not None
    assert authorized.transaction_authorization_id is not None


async def test_authorize_intent_wrong_org(db_session, sample_bill_for_intent, sample_user, second_organization, second_user):
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        sample_bill_for_intent.organization_id,
        sample_bill_for_intent.id,
        sample_user.id,
    )
    result = await service.authorize_fake_intent(
        second_organization.id,
        intent.id,
        second_user.id,
    )
    assert result is None


async def test_cancel_intent(db_session, sample_bill_for_intent, sample_user):
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        sample_bill_for_intent.organization_id,
        sample_bill_for_intent.id,
        sample_user.id,
    )
    cancelled = await service.cancel_intent(
        sample_bill_for_intent.organization_id,
        intent.id,
        sample_user.id,
    )
    assert cancelled is not None
    assert cancelled.status == PaymentIntentStatus.CANCELLED
    assert cancelled.cancelled_at is not None


async def test_cancel_intent_wrong_org(db_session, sample_bill_for_intent, sample_user, second_organization, second_user):
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        sample_bill_for_intent.organization_id,
        sample_bill_for_intent.id,
        sample_user.id,
    )
    result = await service.cancel_intent(
        second_organization.id,
        intent.id,
        second_user.id,
    )
    assert result is None


async def test_intent_event_log_created(db_session, sample_bill_for_intent, sample_user):
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        sample_bill_for_intent.organization_id,
        sample_bill_for_intent.id,
        sample_user.id,
    )
    from sqlalchemy import select, and_
    result = await db_session.execute(
        select(BillEventLog).where(
            and_(
                BillEventLog.detected_bill_id == sample_bill_for_intent.id,
                BillEventLog.action == BillEventAction.PAYMENT_INTENT_CREATED,
            )
        )
    )
    events = list(result.scalars().all())
    assert len(events) >= 1


async def test_authorize_creates_event_log(db_session, sample_bill_for_intent, sample_user):
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        sample_bill_for_intent.organization_id,
        sample_bill_for_intent.id,
        sample_user.id,
    )
    await service.authorize_fake_intent(
        sample_bill_for_intent.organization_id,
        intent.id,
        sample_user.id,
        authorization_code="123456",
    )
    from sqlalchemy import select, and_
    result = await db_session.execute(
        select(BillEventLog).where(
            and_(
                BillEventLog.detected_bill_id == sample_bill_for_intent.id,
                BillEventLog.action == BillEventAction.PAYMENT_INTENT_AUTHORIZED_FAKE,
            )
        )
    )
    events = list(result.scalars().all())
    assert len(events) >= 1


async def test_intent_does_not_execute_payment(db_session, sample_bill_for_intent, sample_user):
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        sample_bill_for_intent.organization_id,
        sample_bill_for_intent.id,
        sample_user.id,
    )
    assert intent.status == PaymentIntentStatus.DRAFT
    assert intent.metadata_sanitized["demo"] is True
    assert "fake" in intent.metadata_sanitized["note"].lower() or "no real" in intent.metadata_sanitized["note"].lower()


async def test_expire_old_intents(db_session, sample_bill_for_intent, sample_user):
    from datetime import datetime, timezone, timedelta as td
    service = BillPaymentIntentService(db_session)
    intent = await service.create_fake_payment_intent(
        sample_bill_for_intent.organization_id,
        sample_bill_for_intent.id,
        sample_user.id,
    )
    intent.expires_at = datetime.now(timezone.utc) - td(hours=1)
    await db_session.commit()

    count = await service.expire_old_intents()
    assert count >= 1

    await db_session.refresh(intent)
    assert intent.status == PaymentIntentStatus.EXPIRED
