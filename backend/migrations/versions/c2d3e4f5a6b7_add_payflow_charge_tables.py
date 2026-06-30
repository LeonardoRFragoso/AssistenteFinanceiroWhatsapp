"""Add PayFlow charge tables

Revision ID: c2d3e4f5a6b7
Revises: b3c4d5e6f7g8
Create Date: 2026-06-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'c2d3e4f5a6b7'
down_revision = 'b3c4d5e6f7g8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Criar enums de forma idempotente consultando o catálogo do PostgreSQL
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chargestatus') THEN
                CREATE TYPE chargestatus AS ENUM ('pending', 'paid', 'expired', 'cancelled', 'failed');
            END IF;
        END $$;
        """,
        execution_options={"autocommit": True}
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'pendingactionstatus') THEN
                CREATE TYPE pendingactionstatus AS ENUM ('pending', 'confirmed', 'cancelled', 'expired', 'executed', 'failed');
            END IF;
        END $$;
        """,
        execution_options={"autocommit": True}
    )

    # Tabela charges
    op.create_table(
        'charges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('customer_name', sa.String(length=255), nullable=False),
        sa.Column('customer_phone', sa.String(length=20), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_charge_id', sa.String(length=255), nullable=True),
        sa.Column('payment_link', sa.Text(), nullable=True),
        sa.Column('qr_code', sa.Text(), nullable=True),
        sa.Column('qr_code_base64', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'paid', 'expired', 'cancelled', 'failed', name='chargestatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_charges_id'), 'charges', ['id'], unique=False)
    op.create_index(op.f('ix_charges_user_id'), 'charges', ['user_id'], unique=False)
    op.create_index(op.f('ix_charges_provider_charge_id'), 'charges', ['provider_charge_id'], unique=False)
    op.create_index(op.f('ix_charges_status'), 'charges', ['status'], unique=False)

    # Tabela pending_actions
    op.create_table(
        'pending_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('status', postgresql.ENUM('pending', 'confirmed', 'cancelled', 'expired', 'executed', 'failed', name='pendingactionstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_actions_id'), 'pending_actions', ['id'], unique=False)
    op.create_index(op.f('ix_pending_actions_user_id'), 'pending_actions', ['user_id'], unique=False)
    op.create_index(op.f('ix_pending_actions_action_type'), 'pending_actions', ['action_type'], unique=False)
    op.create_index(op.f('ix_pending_actions_status'), 'pending_actions', ['status'], unique=False)

    # Tabela provider_events
    op.create_table(
        'provider_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_provider_events_id'), 'provider_events', ['id'], unique=False)
    op.create_index(op.f('ix_provider_events_provider'), 'provider_events', ['provider'], unique=False)
    op.create_index(op.f('ix_provider_events_event_type'), 'provider_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_provider_events_external_id'), 'provider_events', ['external_id'], unique=False)
    op.create_index(op.f('ix_provider_events_processed'), 'provider_events', ['processed'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_provider_events_processed'), table_name='provider_events')
    op.drop_index(op.f('ix_provider_events_external_id'), table_name='provider_events')
    op.drop_index(op.f('ix_provider_events_event_type'), table_name='provider_events')
    op.drop_index(op.f('ix_provider_events_provider'), table_name='provider_events')
    op.drop_index(op.f('ix_provider_events_id'), table_name='provider_events')
    op.drop_table('provider_events')

    op.drop_index(op.f('ix_pending_actions_status'), table_name='pending_actions')
    op.drop_index(op.f('ix_pending_actions_action_type'), table_name='pending_actions')
    op.drop_index(op.f('ix_pending_actions_user_id'), table_name='pending_actions')
    op.drop_index(op.f('ix_pending_actions_id'), table_name='pending_actions')
    op.drop_table('pending_actions')

    op.drop_index(op.f('ix_charges_status'), table_name='charges')
    op.drop_index(op.f('ix_charges_provider_charge_id'), table_name='charges')
    op.drop_index(op.f('ix_charges_user_id'), table_name='charges')
    op.drop_index(op.f('ix_charges_id'), table_name='charges')
    op.drop_table('charges')

    op.execute("DROP TYPE IF EXISTS pendingactionstatus")
    op.execute("DROP TYPE IF EXISTS chargestatus")
