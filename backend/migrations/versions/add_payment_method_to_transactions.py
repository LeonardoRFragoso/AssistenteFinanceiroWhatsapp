"""Add payment_method to transactions

Revision ID: a2b3c4d5e6f7
Revises: 1bd3de9c1bc8
Create Date: 2026-02-18 14:06:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a2b3c4d5e6f7'
down_revision = '1bd3de9c1bc8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == 'postgresql'

    if is_pg:
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE paymentmethod AS ENUM ('conta_corrente', 'cartao_credito', 'cartao_debito', 'pix', 'dinheiro', 'outros');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                ALTER TABLE transactions ADD COLUMN payment_method paymentmethod NOT NULL DEFAULT 'conta_corrente'::paymentmethod;
            EXCEPTION
                WHEN duplicate_column THEN null;
            END $$;
        """)
    else:
        op.add_column('transactions', sa.Column('payment_method', sa.String(20), nullable=False, server_default='conta_corrente'))


def downgrade() -> None:
    op.drop_column('transactions', 'payment_method')
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS paymentmethod")
