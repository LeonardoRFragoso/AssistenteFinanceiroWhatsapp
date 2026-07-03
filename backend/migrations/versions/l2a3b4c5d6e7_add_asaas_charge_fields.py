"""add asaas charge fields

Revision ID: l2a3b4c5d6e7
Revises: k1f2g3h4i5j6
Create Date: 2025-07-02

Adds provider_bank_slip_url and provider_status columns to charges table
for Asaas sandbox charge provider integration.
"""
from alembic import op
import sqlalchemy as sa


revision = "l2a3b4c5d6e7"
down_revision = "k1f2g3h4i5j6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("charges", sa.Column("provider_bank_slip_url", sa.Text(), nullable=True))
    op.add_column("charges", sa.Column("provider_status", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("charges", "provider_status")
    op.drop_column("charges", "provider_bank_slip_url")
