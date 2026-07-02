"""add organizations and multi-tenant columns

Revision ID: g7b8c9d0e1f2
Revises: a1b2c3d4e5f6
Create Date: 2025-07-02

"""
from alembic import op
import sqlalchemy as sa


revision = 'g7b8c9d0e1f2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def _add_org_column(table_name: str) -> None:
    """Add organization_id column using batch_alter_table for SQLite compatibility."""
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(f'ix_{table_name}_organization_id', table_name, ['organization_id'], unique=False)


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('document', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        'organization_members',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('role', sa.Enum('owner', 'admin', 'finance', 'viewer', name='organizationrole'), nullable=False, server_default='viewer'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('invited_email', sa.String(255), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    _add_org_column('charges')
    _add_org_column('customers')
    _add_org_column('message_templates')
    _add_org_column('collection_rules')
    _add_org_column('collection_message_logs')
    _add_org_column('recurring_tasks')
    _add_org_column('pending_actions')


def downgrade() -> None:
    for table in ['pending_actions', 'recurring_tasks', 'collection_message_logs', 'collection_rules', 'message_templates', 'customers', 'charges']:
        op.drop_index(f'ix_{table}_organization_id', table_name=table)
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column('organization_id')

    op.drop_table('organization_members')
    op.drop_table('organizations')
