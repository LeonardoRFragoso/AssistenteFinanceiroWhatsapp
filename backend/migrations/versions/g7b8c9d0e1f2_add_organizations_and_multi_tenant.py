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
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
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
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.add_column('charges', sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True))
    op.add_column('customers', sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True))
    op.add_column('message_templates', sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True))
    op.add_column('collection_rules', sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True))
    op.add_column('collection_message_logs', sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True))
    op.add_column('recurring_tasks', sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True))
    op.add_column('pending_actions', sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column('pending_actions', 'organization_id')
    op.drop_column('recurring_tasks', 'organization_id')
    op.drop_column('collection_message_logs', 'organization_id')
    op.drop_column('collection_rules', 'organization_id')
    op.drop_column('message_templates', 'organization_id')
    op.drop_column('customers', 'organization_id')
    op.drop_column('charges', 'organization_id')

    op.drop_table('organization_members')
    op.drop_table('organizations')
