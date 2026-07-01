"""Add charge_reminder_logs table

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-07-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'd4e5f6a7b8c9'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'remindertype') THEN
                CREATE TYPE remindertype AS ENUM ('due_soon', 'overdue');
            END IF;
        END $$;
        """,
        execution_options={"autocommit": True}
    )

    op.create_table(
        'charge_reminder_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('charge_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reminder_type', postgresql.ENUM('due_soon', 'overdue', name='remindertype', create_type=False), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['charge_id'], ['charges.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_charge_reminder_logs_id'), 'charge_reminder_logs', ['id'], unique=False)
    op.create_index(op.f('ix_charge_reminder_logs_charge_id'), 'charge_reminder_logs', ['charge_id'], unique=False)
    op.create_index(op.f('ix_charge_reminder_logs_user_id'), 'charge_reminder_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_charge_reminder_logs_user_id'), table_name='charge_reminder_logs')
    op.drop_index(op.f('ix_charge_reminder_logs_charge_id'), table_name='charge_reminder_logs')
    op.drop_index(op.f('ix_charge_reminder_logs_id'), table_name='charge_reminder_logs')
    op.drop_table('charge_reminder_logs')
    op.execute("DROP TYPE IF EXISTS remindertype")
