"""harden organization_id backfill

Create default organizations for users without one and backfill
organization_id on all multi-tenant records that have NULL.

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2025-07-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'h8c9d0e1f2g3'
down_revision = 'g7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Create a default organization for every user that doesn't have one.
    #    We use a raw INSERT ... SELECT so it works on all DB engines.
    users_without_org = conn.execute(sa.text("""
        SELECT u.id, u.name, u.email
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM organization_members om
            WHERE om.user_id = u.id AND om.active = 1
        )
    """)).fetchall()

    for user_id, user_name, user_email in users_without_org:
        # Generate a unique slug
        slug = f"default-{user_id}"
        conn.execute(sa.text("""
            INSERT INTO organizations (name, slug, owner_user_id, active, created_at, updated_at)
            VALUES (:name, :slug, :owner_id, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """), {"name": f"{user_name or 'My'} Organization", "slug": slug, "owner_id": user_id})

        org_id = conn.execute(sa.text(
            "SELECT id FROM organizations WHERE slug = :slug"
        ), {"slug": slug}).scalar()

        # Add user as owner member
        conn.execute(sa.text("""
            INSERT INTO organization_members (organization_id, user_id, role, active, joined_at, created_at, updated_at)
            VALUES (:org_id, :user_id, 'owner', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """), {"org_id": org_id, "user_id": user_id})

    # 2. Backfill organization_id on all multi-tenant tables.
    #    For each table, set organization_id to the user's default org.
    tables = [
        "charges",
        "customers",
        "message_templates",
        "collection_rules",
        "collection_message_logs",
        "recurring_tasks",
        "pending_actions",
    ]

    for table in tables:
        conn.execute(sa.text(f"""
            UPDATE {table}
            SET organization_id = (
                SELECT o.id
                FROM organizations o
                JOIN organization_members om ON om.organization_id = o.id
                WHERE om.user_id = {table}.user_id
                  AND om.active = 1
                ORDER BY om.joined_at ASC
                LIMIT 1
            )
            WHERE {table}.organization_id IS NULL
              AND {table}.user_id IS NOT NULL
        """))


def downgrade() -> None:
    # Cannot un-backfill reliably; set organization_id back to NULL
    # and remove auto-created default organizations.
    conn = op.get_bind()

    tables = [
        "charges",
        "customers",
        "message_templates",
        "collection_rules",
        "collection_message_logs",
        "recurring_tasks",
        "pending_actions",
    ]

    for table in tables:
        conn.execute(sa.text(f"""
            UPDATE {table} SET organization_id = NULL
            WHERE organization_id IS NOT NULL
        """))

    # Remove auto-created default organizations (slug starts with 'default-')
    conn.execute(sa.text("""
        DELETE FROM organization_members
        WHERE organization_id IN (
            SELECT id FROM organizations WHERE slug LIKE 'default-%'
        )
    """))
    conn.execute(sa.text("""
        DELETE FROM organizations WHERE slug LIKE 'default-%'
    """))
