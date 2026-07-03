"""fake dda and bill management

Revision ID: n3c4d5e6f7g8
Revises: m2b3c4d5e6f7
Create Date: 2025-07-03

Creates 4 new tables for fake DDA and bill management:
- detected_bills
- bill_reminders
- bill_payment_intents
- bill_event_logs

Compatible with SQLite and PostgreSQL.
"""
from alembic import op
import sqlalchemy as sa


revision = "n3c4d5e6f7g8"
down_revision = "m2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "detected_bills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="fake"),
        sa.Column("provider_bill_id", sa.String(255), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="fake_dda"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("beneficiary_name", sa.String(200), nullable=False),
        sa.Column("beneficiary_document_masked", sa.String(50), nullable=True),
        sa.Column("payer_name", sa.String(200), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("digitable_line", sa.String(54), nullable=True),
        sa.Column("bill_type", sa.String(20), nullable=False, server_default="boleto"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="detected"),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="low"),
        sa.Column("is_demo_data", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("raw_data_sanitized", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ignored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manually_marked_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "provider_name", "provider_bill_id", name="uq_detected_bill_org_provider"),
    )
    op.create_index("ix_detected_bills_org", "detected_bills", ["organization_id"])
    op.create_index("ix_detected_bills_due_date", "detected_bills", ["due_date"])
    op.create_index("ix_detected_bills_status", "detected_bills", ["status"])
    op.create_index("ix_detected_bills_org_status", "detected_bills", ["organization_id", "status"])
    op.create_index("ix_detected_bills_org_due", "detected_bills", ["organization_id", "due_date"])

    op.create_table(
        "bill_reminders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("detected_bill_id", sa.Integer(), sa.ForeignKey("detected_bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reminder_date", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="whatsapp"),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("message_preview", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bill_reminders_org", "bill_reminders", ["organization_id"])
    op.create_index("ix_bill_reminders_bill", "bill_reminders", ["detected_bill_id"])
    op.create_index("ix_bill_reminders_reminder_date", "bill_reminders", ["reminder_date"])
    op.create_index("ix_bill_reminders_org_status", "bill_reminders", ["organization_id", "status"])

    op.create_table(
        "bill_payment_intents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("detected_bill_id", sa.Integer(), sa.ForeignKey("detected_bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("transaction_authorization_id", sa.Integer(), sa.ForeignKey("transaction_authorizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_name", sa.String(50), nullable=False, server_default="fake"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("intent_type", sa.String(20), nullable=False, server_default="fake_boleto"),
        sa.Column("fake_payment_reference", sa.String(100), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_sanitized", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bill_payment_intents_org", "bill_payment_intents", ["organization_id"])
    op.create_index("ix_bill_payment_intents_bill", "bill_payment_intents", ["detected_bill_id"])
    op.create_index("ix_bill_payment_intents_status", "bill_payment_intents", ["status"])
    op.create_index("ix_bill_payment_intents_org_status", "bill_payment_intents", ["organization_id", "status"])

    op.create_table(
        "bill_event_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("detected_bill_id", sa.Integer(), sa.ForeignKey("detected_bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("metadata_sanitized", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bill_event_logs_org", "bill_event_logs", ["organization_id"])
    op.create_index("ix_bill_event_logs_bill", "bill_event_logs", ["detected_bill_id"])


def downgrade() -> None:
    op.drop_table("bill_event_logs")
    op.drop_table("bill_payment_intents")
    op.drop_table("bill_reminders")
    op.drop_table("detected_bills")
