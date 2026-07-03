#!/usr/bin/env python3
"""Audit multi-tenant integrity: detect orphan records without organization_id.

Checks all org-scoped tables for:
- Records with organization_id IS NULL
- Records with organization_id pointing to a non-existent organization

Usage:
    DATABASE_URL=sqlite+aiosqlite:///./test.db python scripts/audit_multitenant_integrity.py

Exit codes:
    0 — all good, no orphan records
    1 — inconsistencies found
"""
import asyncio
import sys
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ORG_SCOPED_TABLES = [
    "charges",
    "customers",
    "message_templates",
    "collection_rules",
    "collection_message_logs",
    "recurring_tasks",
    "pending_actions",
    "organization_subscriptions",
    "usage_counters",
    "billing_events",
    "provider_connections",
    "provider_webhook_events",
    "open_finance_consents",
    "organization_audit_logs",
    "transaction_authorizations",
]


async def audit():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        return 1

    engine = create_async_engine(database_url, echo=False)

    total_orphans = 0
    total_null = 0
    total_invalid = 0
    results = []

    async with engine.begin() as conn:
        for table in ORG_SCOPED_TABLES:
            total_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            total = total_result.scalar()

            null_result = await conn.execute(text(
                f"SELECT COUNT(*) FROM {table} WHERE organization_id IS NULL"
            ))
            null_count = null_result.scalar()

            invalid_result = await conn.execute(text(
                f"SELECT COUNT(*) FROM {table} t "
                f"WHERE t.organization_id IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM organizations o WHERE o.id = t.organization_id)"
            ))
            invalid_count = invalid_result.scalar()

            total_orphans += null_count + invalid_count
            total_null += null_count
            total_invalid += invalid_count

            status = "OK" if (null_count == 0 and invalid_count == 0) else "FAIL"
            results.append({
                "table": table,
                "total": total,
                "null_org": null_count,
                "invalid_org": invalid_count,
                "status": status,
            })

    await engine.dispose()

    print("=" * 70)
    print("Multi-Tenant Integrity Audit")
    print("=" * 70)
    print(f"{'Table':<30} {'Total':>8} {'NULL org':>10} {'Invalid org':>12} {'Status':>8}")
    print("-" * 70)
    for r in results:
        print(f"{r['table']:<30} {r['total']:>8} {r['null_org']:>10} {r['invalid_org']:>12} {r['status']:>8}")
    print("-" * 70)
    print(f"{'TOTAL':<30} {'':>8} {total_null:>10} {total_invalid:>12}")
    print("=" * 70)

    if total_orphans > 0:
        print(f"\nFOUND {total_orphans} orphan record(s) across {len(ORG_SCOPED_TABLES)} tables.")
        print("\nRecommendation:")
        if total_null > 0:
            print("  - Run backfill migration h8c9d0e1f2g3 to populate organization_id on NULL records.")
        if total_invalid > 0:
            print("  - Records with invalid organization_id should be manually reviewed and reassigned.")
        return 1
    else:
        print(f"\nAll {len(ORG_SCOPED_TABLES)} tables checked. No orphan records found.")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(audit())
    sys.exit(exit_code)
