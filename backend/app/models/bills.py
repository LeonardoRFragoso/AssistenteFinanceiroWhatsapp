"""
Bill management models — Sprint 17.

4 tables:
- detected_bills
- bill_reminders
- bill_payment_intents
- bill_event_logs

All tables are organization-scoped. No real payment execution.
All fake/demo data is marked with is_demo_data=True.
No real DDA access, no real boleto payment, no real bank credentials.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey,
    Enum, Text, JSON, Numeric, UniqueConstraint, Index,
)
from sqlalchemy.sql import func
from app.core.database import Base


class BillStatus(str, enum.Enum):
    DETECTED = "detected"
    PENDING = "pending"
    DUE_TODAY = "due_today"
    OVERDUE = "overdue"
    PAID_MANUAL = "paid_manual"
    IGNORED = "ignored"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BillSource(str, enum.Enum):
    FAKE_DDA = "fake_dda"
    OCR = "ocr"
    MANUAL = "manual"
    IMPORTED = "imported"
    FUTURE_PROVIDER = "future_provider"


class BillType(str, enum.Enum):
    BOLETO = "boleto"
    UTILITY = "utility"
    TAX = "tax"
    RENT = "rent"
    SERVICE = "service"
    SUBSCRIPTION = "subscription"
    OTHER = "other"


class BillRiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BillReminderStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BillReminderChannel(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PUSH = "push"


class PaymentIntentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_AUTHORIZATION = "pending_authorization"
    AUTHORIZED_FAKE = "authorized_fake"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


class PaymentIntentType(str, enum.Enum):
    FAKE_BOLETO = "fake_boleto"
    FAKE_PIX = "fake_pix"


class BillEventAction(str, enum.Enum):
    BILL_DETECTED = "bill_detected"
    BILL_IGNORED = "bill_ignored"
    BILL_MARKED_PAID_MANUAL = "bill_marked_paid_manual"
    REMINDER_SCHEDULED = "reminder_scheduled"
    PAYMENT_INTENT_CREATED = "payment_intent_created"
    PAYMENT_INTENT_AUTHORIZED_FAKE = "payment_intent_authorized_fake"
    PAYMENT_INTENT_CANCELLED = "payment_intent_cancelled"
    SYNC_FAKE_DDA = "sync_fake_dda"


class DetectedBill(Base):
    __tablename__ = "detected_bills"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    provider_name = Column(String(50), nullable=False, default="fake")
    provider_bill_id = Column(String(255), nullable=True)
    source = Column(
        Enum(BillSource, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=BillSource.FAKE_DDA,
    )
    title = Column(String(255), nullable=False)
    beneficiary_name = Column(String(200), nullable=False)
    beneficiary_document_masked = Column(String(50), nullable=True)
    payer_name = Column(String(200), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="BRL")
    due_date = Column(Date, nullable=False, index=True)
    issue_date = Column(Date, nullable=True)
    barcode = Column(String(64), nullable=True)
    digitable_line = Column(String(54), nullable=True)
    bill_type = Column(
        Enum(BillType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=BillType.BOLETO,
    )
    category = Column(String(100), nullable=True)
    status = Column(
        Enum(BillStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=BillStatus.DETECTED, index=True,
    )
    risk_level = Column(
        Enum(BillRiskLevel, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=BillRiskLevel.LOW,
    )
    is_demo_data = Column(Boolean, nullable=False, default=True)
    raw_data_sanitized = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    ignored_at = Column(DateTime(timezone=True), nullable=True)
    manually_marked_paid_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "provider_name", "provider_bill_id",
            name="uq_detected_bill_org_provider",
        ),
        Index("ix_detected_bills_org_status", "organization_id", "status"),
        Index("ix_detected_bills_org_due", "organization_id", "due_date"),
    )


class BillReminder(Base):
    __tablename__ = "bill_reminders"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    detected_bill_id = Column(
        Integer, ForeignKey("detected_bills.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reminder_date = Column(Date, nullable=False, index=True)
    channel = Column(
        Enum(BillReminderChannel, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=BillReminderChannel.WHATSAPP,
    )
    status = Column(
        Enum(BillReminderStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=BillReminderStatus.SCHEDULED,
    )
    message_preview = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_bill_reminders_org_status", "organization_id", "status"),
    )


class BillPaymentIntent(Base):
    __tablename__ = "bill_payment_intents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    detected_bill_id = Column(
        Integer, ForeignKey("detected_bills.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    transaction_authorization_id = Column(
        Integer, ForeignKey("transaction_authorizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_name = Column(String(50), nullable=False, default="fake")
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="BRL")
    status = Column(
        Enum(PaymentIntentStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=PaymentIntentStatus.DRAFT, index=True,
    )
    intent_type = Column(
        Enum(PaymentIntentType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=PaymentIntentType.FAKE_BOLETO,
    )
    fake_payment_reference = Column(String(100), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    metadata_sanitized = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_bill_payment_intents_org_status", "organization_id", "status"),
    )


class BillEventLog(Base):
    __tablename__ = "bill_event_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    detected_bill_id = Column(
        Integer, ForeignKey("detected_bills.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    actor_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    action = Column(
        Enum(BillEventAction, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    metadata_sanitized = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
