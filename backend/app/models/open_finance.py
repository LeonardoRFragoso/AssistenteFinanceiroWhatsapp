"""
Open Finance read models — Sprint 16.

4 tables:
- connected_accounts
- bank_transactions
- financial_categories
- open_finance_sync_logs

All tables are organization-scoped. No real access/refresh tokens stored.
All fake/demo data is marked with is_demo_data=True.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey,
    Enum, Text, JSON, Numeric, UniqueConstraint, Index,
)
from sqlalchemy.sql import func
from app.core.database import Base


class ConnectedAccountStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    EXPIRED = "expired"


class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionStatus(str, enum.Enum):
    POSTED = "posted"
    PENDING = "pending"


class SyncType(str, enum.Enum):
    ACCOUNTS = "accounts"
    TRANSACTIONS = "transactions"
    BALANCES = "balances"
    FULL = "full"


class SyncStatus(str, enum.Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

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
    consent_id = Column(
        Integer, ForeignKey("open_finance_consents.id", ondelete="SET NULL"), nullable=True,
    )
    provider_name = Column(String(50), nullable=False, default="fake")
    external_account_id = Column(String(255), nullable=True)
    institution_name = Column(String(100), nullable=True)
    institution_code = Column(String(20), nullable=True)
    account_type = Column(String(50), nullable=True)
    account_subtype = Column(String(50), nullable=True)
    account_number_masked = Column(String(20), nullable=True)
    currency = Column(String(3), nullable=False, default="BRL")
    balance_available = Column(Numeric(14, 2), nullable=True)
    balance_current = Column(Numeric(14, 2), nullable=True)
    balance_updated_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(ConnectedAccountStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=ConnectedAccountStatus.ACTIVE,
    )
    is_demo_data = Column(Boolean, nullable=False, default=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_connected_accounts_org", "organization_id"),
        Index("ix_connected_accounts_org_status", "organization_id", "status"),
    )


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    connected_account_id = Column(
        Integer, ForeignKey("connected_accounts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider_name = Column(String(50), nullable=False, default="fake")
    external_transaction_id = Column(String(255), nullable=True)
    transaction_type = Column(
        Enum(TransactionType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="BRL")
    description = Column(Text, nullable=True)
    merchant_name = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)
    transaction_date = Column(Date, nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(TransactionStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=TransactionStatus.POSTED,
    )
    is_demo_data = Column(Boolean, nullable=False, default=True)
    raw_data_sanitized = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "provider_name", "external_transaction_id",
            name="uq_bank_tx_org_provider_external",
        ),
        Index("ix_bank_tx_org_account", "organization_id", "connected_account_id"),
        Index("ix_bank_tx_org_date", "organization_id", "transaction_date"),
        Index("ix_bank_tx_org_category", "organization_id", "category"),
    )


class FinancialCategory(Base):
    __tablename__ = "financial_categories"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name = Column(String(100), nullable=False)
    type = Column(
        Enum(CategoryType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=CategoryType.EXPENSE,
    )
    color = Column(String(7), nullable=True)
    icon = Column(String(50), nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_fin_cat_org_name"),
        Index("ix_fin_cat_org", "organization_id"),
    )


class OpenFinanceSyncLog(Base):
    __tablename__ = "open_finance_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider_connection_id = Column(Integer, nullable=True)
    consent_id = Column(Integer, nullable=True)
    sync_type = Column(
        Enum(SyncType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status = Column(
        Enum(SyncStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    records_found = Column(Integer, nullable=False, default=0)
    records_created = Column(Integer, nullable=False, default=0)
    records_updated = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_of_sync_logs_org", "organization_id"),
        Index("ix_of_sync_logs_org_status", "organization_id", "status"),
    )
