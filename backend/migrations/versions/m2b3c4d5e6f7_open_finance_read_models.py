"""open finance read models

Revision ID: m2b3c4d5e6f7
Revises: l2a3b4c5d6e7
Create Date: 2025-07-03

Creates 4 new tables for Open Finance read provider:
- connected_accounts
- bank_transactions
- financial_categories
- open_finance_sync_logs

Compatible with SQLite and PostgreSQL.
"""
from alembic import op
import sqlalchemy as sa


revision = "m2b3c4d5e6f7"
down_revision = "l2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connected_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_connection_id", sa.Integer(), sa.ForeignKey("provider_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("consent_id", sa.Integer(), sa.ForeignKey("open_finance_consents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="fake"),
        sa.Column("external_account_id", sa.String(255), nullable=True),
        sa.Column("institution_name", sa.String(100), nullable=True),
        sa.Column("institution_code", sa.String(20), nullable=True),
        sa.Column("account_type", sa.String(50), nullable=True),
        sa.Column("account_subtype", sa.String(50), nullable=True),
        sa.Column("account_number_masked", sa.String(20), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("balance_available", sa.Numeric(14, 2), nullable=True),
        sa.Column("balance_current", sa.Numeric(14, 2), nullable=True),
        sa.Column("balance_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_demo_data", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_connected_accounts_org", "connected_accounts", ["organization_id"])
    op.create_index("ix_connected_accounts_org_status", "connected_accounts", ["organization_id", "status"])

    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connected_account_id", sa.Integer(), sa.ForeignKey("connected_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="fake"),
        sa.Column("external_transaction_id", sa.String(255), nullable=True),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("merchant_name", sa.String(200), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="posted"),
        sa.Column("is_demo_data", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("raw_data_sanitized", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "provider_name", "external_transaction_id", name="uq_bank_tx_org_provider_external"),
    )
    op.create_index("ix_bank_tx_org_account", "bank_transactions", ["organization_id", "connected_account_id"])
    op.create_index("ix_bank_tx_org_date", "bank_transactions", ["organization_id", "transaction_date"])
    op.create_index("ix_bank_tx_org_category", "bank_transactions", ["organization_id", "category"])

    op.create_table(
        "financial_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="expense"),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_fin_cat_org_name"),
    )
    op.create_index("ix_fin_cat_org", "financial_categories", ["organization_id"])

    op.create_table(
        "open_finance_sync_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_connection_id", sa.Integer(), nullable=True),
        sa.Column("consent_id", sa.Integer(), nullable=True),
        sa.Column("sync_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("records_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_of_sync_logs_org", "open_finance_sync_logs", ["organization_id"])
    op.create_index("ix_of_sync_logs_org_status", "open_finance_sync_logs", ["organization_id", "status"])


def downgrade() -> None:
    op.drop_table("open_finance_sync_logs")
    op.drop_table("financial_categories")
    op.drop_table("bank_transactions")
    op.drop_table("connected_accounts")
