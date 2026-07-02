"""add saas billing tables

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2025-07-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'j0e1f2g3h4i5'
down_revision = 'i9d0e1f2g3h4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # subscription_plans
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price_monthly', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='BRL'),
        sa.Column('max_charges_per_month', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('max_customers', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_team_members', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('max_message_templates', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('max_recurring_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_whatsapp_messages_per_month', sa.Integer(), nullable=True),
        sa.Column('allow_advanced_analytics', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allow_pdf_export', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allow_ocr', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allow_collection_rules', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allow_whatsapp_intelligence', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    # organization_subscriptions
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        subscription_status_enum = sa.Enum(
            'trialing', 'active', 'past_due', 'cancelled', 'expired',
            name='subscriptionstatus',
        )
        billing_provider_enum = sa.Enum(
            'fake', 'stripe_sandbox', 'mercado_pago_sandbox',
            name='billingprovider',
        )
        subscription_status_enum.create(bind, checkfirst=True)
        billing_provider_enum.create(bind, checkfirst=True)

    op.create_table(
        'organization_subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('subscription_plans.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('billing_provider', sa.String(50), nullable=False, server_default='fake'),
        sa.Column('provider_subscription_id', sa.String(255), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    # usage_counters
    op.create_table(
        'usage_counters',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('charges_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('customers_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('templates_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recurring_tasks_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ocr_documents_analyzed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pdf_exports_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('whatsapp_messages_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('collection_followups_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    # billing_events
    op.create_table(
        'billing_events',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('subscription_id', sa.Integer(), sa.ForeignKey('organization_subscriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False, server_default='fake'),
        sa.Column('provider_event_id', sa.String(255), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('billing_events')
    op.drop_table('usage_counters')
    op.drop_table('organization_subscriptions')
    op.drop_table('subscription_plans')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='subscriptionstatus').drop(bind, checkfirst=True)
        sa.Enum(name='billingprovider').drop(bind, checkfirst=True)
