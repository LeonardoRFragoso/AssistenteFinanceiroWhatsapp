"""
Provider foundation models — Sprint 14.

5 tables:
- provider_connections
- provider_webhook_events
- open_finance_consents
- organization_audit_logs
- transaction_authorizations

All tables are organization-scoped. No secrets stored in plaintext.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey,
    Enum, Text, JSON, Numeric, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProviderConnectionStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    EXPIRED = "expired"
    NOT_CONFIGURED = "not_configured"


class WebhookEventStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    IGNORED = "ignored"


class ConsentStatus(str, enum.Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    EXPIRED = "expired"
    REVOKED = "revoked"
    FAILED = "failed"


class AuthorizationStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ChallengeType(str, enum.Enum):
    PASSWORD_6 = "password_6"
    BIOMETRIC = "biometric"
    PRE_AUTHORIZED = "pre_authorized"


class ProviderConnection(Base):
    __tablename__ = "provider_connections"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider_type = Column(String(50), nullable=False, index=True)
    provider_name = Column(String(50), nullable=False, default="fake")
    status = Column(
        Enum(ProviderConnectionStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=ProviderConnectionStatus.ACTIVE,
    )
    environment = Column(String(20), nullable=False, default="sandbox")
    display_name = Column(String(200), nullable=True)
    external_connection_id = Column(String(255), nullable=True)
    institution_name = Column(String(100), nullable=True)
    institution_code = Column(String(20), nullable=True)
    scopes = Column(JSON, nullable=True)
    extra_data = Column(JSON, nullable=True)
    secret_ref = Column(String(255), nullable=True)
    consent_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_provider_connections_org_type", "organization_id", "provider_type"),
    )


class ProviderWebhookEvent(Base):
    __tablename__ = "provider_webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider_type = Column(String(50), nullable=False)
    provider_name = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)
    provider_event_id = Column(String(255), nullable=False)
    idempotency_key = Column(String(255), nullable=True)
    status = Column(
        Enum(WebhookEventStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=WebhookEventStatus.RECEIVED,
    )
    payload = Column(JSON, nullable=True)
    headers_sanitized = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "provider_type", "provider_name", "provider_event_id",
            name="uq_webhook_idempotency",
        ),
        Index("ix_webhook_org_type", "organization_id", "provider_type"),
    )


class OpenFinanceConsent(Base):
    __tablename__ = "open_finance_consents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    provider_connection_id = Column(
        Integer, ForeignKey("provider_connections.id", ondelete="SET NULL"), nullable=True,
    )
    provider_name = Column(String(50), nullable=False, default="fake")
    external_consent_id = Column(String(255), nullable=True)
    status = Column(
        Enum(ConsentStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=ConsentStatus.PENDING,
    )
    scopes = Column(JSON, nullable=True)
    institution_name = Column(String(100), nullable=True)
    institution_code = Column(String(20), nullable=True)
    authorization_url = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_of_consents_org_status", "organization_id", "status"),
    )


class OrganizationAuditLog(Base):
    __tablename__ = "organization_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    actor_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    actor_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    provider_type = Column(String(50), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    user_agent_hash = Column(String(64), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_audit_org_action", "organization_id", "action"),
        Index("ix_audit_org_provider", "organization_id", "provider_type"),
    )


class TransactionAuthorization(Base):
    __tablename__ = "transaction_authorizations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    action_type = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=False, default="BRL")
    status = Column(
        Enum(AuthorizationStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=AuthorizationStatus.PENDING,
    )
    challenge_type = Column(
        Enum(ChallengeType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=ChallengeType.PASSWORD_6,
    )
    code_hash = Column(String(255), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    failed_attempts = Column(Integer, nullable=False, default=0)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_txauth_org_status", "organization_id", "status"),
    )
