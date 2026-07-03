"""provider foundation consent audit and transaction auth

Revision ID: k1f2g3h4i5j6
Revises: j0e1f2g3h4i5
Create Date: 2025-07-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'k1f2g3h4i5j6'
down_revision = 'j0e1f2g3h4i5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # provider_connections
    op.create_table(
        'provider_connections',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('organization_id', sa.Integer(),
                   sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                   nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=False, server_default='fake'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('environment', sa.String(20), nullable=False, server_default='sandbox'),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('external_connection_id', sa.String(255), nullable=True),
        sa.Column('institution_name', sa.String(100), nullable=True),
        sa.Column('institution_code', sa.String(20), nullable=True),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('secret_ref', sa.String(255), nullable=True),
        sa.Column('consent_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(),
                   sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_provider_connections_organization_id',
                     'provider_connections', ['organization_id'])
    op.create_index('ix_provider_connections_provider_type',
                     'provider_connections', ['provider_type'])
    op.create_index('ix_provider_connections_org_type',
                     'provider_connections', ['organization_id', 'provider_type'])

    # provider_webhook_events
    op.create_table(
        'provider_webhook_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('organization_id', sa.Integer(),
                   sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                   nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('provider_event_id', sa.String(255), nullable=False),
        sa.Column('idempotency_key', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='received'),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('headers_sanitized', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('provider_type', 'provider_name', 'provider_event_id',
                            name='uq_webhook_idempotency'),
    )
    op.create_index('ix_provider_webhook_events_organization_id',
                     'provider_webhook_events', ['organization_id'])
    op.create_index('ix_webhook_org_type',
                     'provider_webhook_events', ['organization_id', 'provider_type'])

    # open_finance_consents
    op.create_table(
        'open_finance_consents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('organization_id', sa.Integer(),
                   sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                   nullable=False),
        sa.Column('user_id', sa.Integer(),
                   sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider_connection_id', sa.Integer(),
                   sa.ForeignKey('provider_connections.id', ondelete='SET NULL'),
                   nullable=True),
        sa.Column('provider_name', sa.String(50), nullable=False, server_default='fake'),
        sa.Column('external_consent_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('institution_name', sa.String(100), nullable=True),
        sa.Column('institution_code', sa.String(20), nullable=True),
        sa.Column('authorization_url', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_open_finance_consents_organization_id',
                     'open_finance_consents', ['organization_id'])
    op.create_index('ix_of_consents_org_status',
                     'open_finance_consents', ['organization_id', 'status'])

    # organization_audit_logs
    op.create_table(
        'organization_audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('organization_id', sa.Integer(),
                   sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                   nullable=False),
        sa.Column('actor_user_id', sa.Integer(),
                   sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_role', sa.String(50), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('provider_type', sa.String(50), nullable=True),
        sa.Column('ip_hash', sa.String(64), nullable=True),
        sa.Column('user_agent_hash', sa.String(64), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_organization_audit_logs_organization_id',
                     'organization_audit_logs', ['organization_id'])
    op.create_index('ix_audit_org_action',
                     'organization_audit_logs', ['organization_id', 'action'])
    op.create_index('ix_audit_org_provider',
                     'organization_audit_logs', ['organization_id', 'provider_type'])

    # transaction_authorizations
    op.create_table(
        'transaction_authorizations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('organization_id', sa.Integer(),
                   sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                   nullable=False),
        sa.Column('user_id', sa.Integer(),
                   sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='BRL'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('challenge_type', sa.String(20), nullable=False, server_default='password_6'),
        sa.Column('code_hash', sa.String(255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_transaction_authorizations_organization_id',
                     'transaction_authorizations', ['organization_id'])
    op.create_index('ix_txauth_org_status',
                     'transaction_authorizations', ['organization_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_txauth_org_status', table_name='transaction_authorizations')
    op.drop_index('ix_transaction_authorizations_organization_id', table_name='transaction_authorizations')
    op.drop_table('transaction_authorizations')

    op.drop_index('ix_audit_org_provider', table_name='organization_audit_logs')
    op.drop_index('ix_audit_org_action', table_name='organization_audit_logs')
    op.drop_index('ix_organization_audit_logs_organization_id', table_name='organization_audit_logs')
    op.drop_table('organization_audit_logs')

    op.drop_index('ix_of_consents_org_status', table_name='open_finance_consents')
    op.drop_index('ix_open_finance_consents_organization_id', table_name='open_finance_consents')
    op.drop_table('open_finance_consents')

    op.drop_index('ix_webhook_org_type', table_name='provider_webhook_events')
    op.drop_index('ix_provider_webhook_events_organization_id', table_name='provider_webhook_events')
    op.drop_table('provider_webhook_events')

    op.drop_index('ix_provider_connections_org_type', table_name='provider_connections')
    op.drop_index('ix_provider_connections_provider_type', table_name='provider_connections')
    op.drop_index('ix_provider_connections_organization_id', table_name='provider_connections')
    op.drop_table('provider_connections')
