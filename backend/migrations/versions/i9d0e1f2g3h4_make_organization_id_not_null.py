"""make organization_id not null

Turn organization_id from nullable to NOT NULL on all org-scoped tables.
Requires backfill migration h8c9d0e1f2g3 to have been run first.

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2025-07-04

"""
from alembic import op
import sqlalchemy as sa


revision = 'i9d0e1f2g3h4'
down_revision = 'h8c9d0e1f2g3'
branch_labels = None
depends_on = None

ORG_SCOPED_TABLES = [
    "charges",
    "customers",
    "message_templates",
    "collection_rules",
    "collection_message_logs",
    "recurring_tasks",
    "pending_actions",
]


def upgrade() -> None:
    # First, delete any remaining records with NULL organization_id
    # (backfill should have populated them, but safety net)
    bind = op.get_bind()
    for table in ORG_SCOPED_TABLES:
        bind.execute(sa.text(
            f"DELETE FROM {table} WHERE organization_id IS NULL"
        ))

    # Now make the column NOT NULL using batch_alter_table for SQLite compatibility
    for table in ORG_SCOPED_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "organization_id",
                existing_type=sa.Integer(),
                nullable=False,
            )


def downgrade() -> None:
    for table in ORG_SCOPED_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "organization_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
