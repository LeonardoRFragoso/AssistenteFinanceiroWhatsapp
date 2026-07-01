"""Add charge_delivery_logs table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-01 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deliverystatus') THEN
                CREATE TYPE deliverystatus AS ENUM ('sent', 'failed', 'simulated');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deliverychannel') THEN
                CREATE TYPE deliverychannel AS ENUM ('whatsapp', 'sms', 'email');
            END IF;
        END $$;
        """,
        execution_options={"autocommit": True}
    )

    op.create_table(
        'charge_delivery_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('charge_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=True),
        sa.Column('channel', postgresql.ENUM('whatsapp', 'sms', 'email', name='deliverychannel', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('sent', 'failed', 'simulated', name='deliverystatus', create_type=False), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['charge_id'], ['charges.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_charge_delivery_logs_id'), 'charge_delivery_logs', ['id'], unique=False)
    op.create_index(op.f('ix_charge_delivery_logs_charge_id'), 'charge_delivery_logs', ['charge_id'], unique=False)
    op.create_index(op.f('ix_charge_delivery_logs_user_id'), 'charge_delivery_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_charge_delivery_logs_user_id'), table_name='charge_delivery_logs')
    op.drop_index(op.f('ix_charge_delivery_logs_charge_id'), table_name='charge_delivery_logs')
    op.drop_index(op.f('ix_charge_delivery_logs_id'), table_name='charge_delivery_logs')
    op.drop_table('charge_delivery_logs')
    op.execute("DROP TYPE IF EXISTS deliverystatus")
    op.execute("DROP TYPE IF EXISTS deliverychannel")
