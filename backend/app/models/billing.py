import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Enum, Text, JSON, Numeric
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.core.database import Base


class SubscriptionStatus(str, enum.Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BillingProvider(str, enum.Enum):
    FAKE = "fake"
    STRIPE_SANDBOX = "stripe_sandbox"
    MERCADO_PAGO_SANDBOX = "mercado_pago_sandbox"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price_monthly = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="BRL")
    max_charges_per_month = Column(Integer, nullable=False, default=20)
    max_customers = Column(Integer, nullable=False, default=10)
    max_team_members = Column(Integer, nullable=False, default=1)
    max_message_templates = Column(Integer, nullable=False, default=3)
    max_recurring_tasks = Column(Integer, nullable=False, default=0)
    max_whatsapp_messages_per_month = Column(Integer, nullable=True, default=None)
    allow_advanced_analytics = Column(Boolean, nullable=False, default=False)
    allow_pdf_export = Column(Boolean, nullable=False, default=False)
    allow_ocr = Column(Boolean, nullable=False, default=False)
    allow_collection_rules = Column(Boolean, nullable=False, default=False)
    allow_whatsapp_intelligence = Column(Boolean, nullable=False, default=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscriptions = relationship("OrganizationSubscription", back_populates="plan")


class OrganizationSubscription(Base):
    __tablename__ = "organization_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    status = Column(
        Enum(SubscriptionStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    billing_provider = Column(
        Enum(BillingProvider, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=BillingProvider.FAKE,
    )
    provider_subscription_id = Column(String(255), nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    organization = relationship("Organization", backref=backref("billing_subscription", cascade="all, delete-orphan"))


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    charges_created = Column(Integer, nullable=False, default=0)
    customers_created = Column(Integer, nullable=False, default=0)
    templates_created = Column(Integer, nullable=False, default=0)
    recurring_tasks_created = Column(Integer, nullable=False, default=0)
    ocr_documents_analyzed = Column(Integer, nullable=False, default=0)
    pdf_exports_generated = Column(Integer, nullable=False, default=0)
    whatsapp_messages_processed = Column(Integer, nullable=False, default=0)
    collection_followups_generated = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("organization_subscriptions.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False, default="fake")
    provider_event_id = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
