# Sprint 11.1 — Multi-Tenant Isolation Hardening

## Problem Found

After Sprint 11 introduced `organization_id` columns and basic RBAC, several routers and services were still filtering data only by `user_id`. This meant:

- Endpoints like `GET /charges`, `GET /customers`, `GET /message-templates`, `GET /collection/rules`, `GET /recurring-tasks` did NOT filter by `organization_id`.
- Analytics endpoints passed only `user_id` to `ChargeAnalyticsService`.
- Export endpoints (CSV/PDF) did not filter by organization.
- Tests created org-scoped records with `organization_id=NULL`, causing empty results after org filtering was enforced.

## Root Cause

Sprint 11 added the `organization_id` column and dependency injection (`get_current_organization`) but did not propagate `organization_id` through all service methods, repository queries, and router calls. The `organization_id` was optional (`nullable=True`) and not enforced as the primary data boundary.

## Fix Applied

### Routers Updated

All org-scoped routers now inject `org: Organization = Depends(get_current_organization)` and pass `org.id` to service calls:

- `charges.py` — list, create, get, cancel, summary, analytics, export CSV/PDF, QR code
- `analytics.py` — overview, monthly-trends, aging, customer-performance, collection-performance, insights, export CSV/PDF
- `customers.py` — list, detail, charges, summary, notes update
- `message_templates.py` — list, create, update, preview, deactivate
- `collection.py` — list rules, create rule, deactivate rule, followups, logs
- `recurring_tasks.py` — create, list, cancel

### Services Updated

All org-scoped services now accept `organization_id` and filter queries:

- `ChargeService` — all methods propagate `organization_id` to repository
- `ChargeRepository` — `get_by_user`, `get_by_id`, `get_summary`, `get_analytics` filter by `organization_id`
- `ChargeAnalyticsService` — all methods filter by `organization_id`
- `CustomerService` — `list_customers`, `get_customer`, `get_customer_charges`, `get_customer_summary`, `get_customer_detail`, `update_customer_notes`, `get_or_create_customer`
- `MessageTemplateService` — `list_templates`, `create_template`, `update_template`, `deactivate_template`, `get_template`, `_get_template`, `seed_default_templates`
- `CollectionService` — `create_rule`, `list_rules`, `deactivate_rule`, `get_overdue_charges`, `generate_followup_previews`, `log_message`, `already_sent_today`, `list_logs`
- `RecurringTaskService` — `create_task`, `get_user_tasks`, `cancel_task`
- `PendingActionService` — `create_charge_action` accepts and propagates `organization_id`

### Exports

`GET /charges/export.csv`, `GET /charges/export.pdf`, `GET /analytics/export.csv`, `GET /analytics/export.pdf` all filter by `organization_id`. RBAC enforced: `viewer` cannot export, `finance`/`admin`/`owner` can.

### WhatsApp & PendingAction

- WhatsApp handler `handle_create_pix_charge` resolves user's default organization via `ensure_default_organization` and passes `organization_id` to `PendingActionService.create_charge_action`.
- `PendingAction.confirm_and_execute` uses `organization_id` from payload when creating charges.
- **Limitation**: WhatsApp always uses the user's default organization. Multi-org switching via WhatsApp is not supported in this sprint.

### Migration

**`h8c9d0e1f2g3_harden_organization_id_backfill.py`**:

1. Creates a default organization for every user without one.
2. Adds user as `owner` member of the new org.
3. Backfills `organization_id` on all org-scoped records (`charges`, `customers`, `message_templates`, `collection_rules`, `collection_message_logs`, `recurring_tasks`, `pending_actions`) by looking up the user's first organization.
4. Idempotent: only updates records where `organization_id IS NULL`.
5. Does not delete data.

### Tests Updated

- `test_integration_charges.py` — `authed_user` and `other_user` fixtures now create organizations. All `Charge()` instances include `organization_id`.
- `test_demo_mode.py` — Demo isolation test creates organizations for both users and associates charges with `organization_id`.
- `conftest.py` — Added `sample_organization` fixture for reuse across test files.
- **Result**: 289 backend tests pass, 0 failures, 0 errors.

## Isolation Rules Enforced

- `user_id` remains for ownership/audit.
- `organization_id` is the primary data boundary for workspace isolation.
- Data from org A never appears in org B.
- Users outside the organization receive 403.
- `viewer` role cannot export data.
- `finance`/`admin`/`owner` roles can export.
- Demo mode continues working with org-aware seed.

## Remaining Limitations

1. WhatsApp uses only the user's default organization (no multi-org switching via chat).
2. `organization_id` columns are still `nullable=True` at the DB level for backward compatibility. The backfill migration populates existing records.
3. `alembic upgrade head` fails on SQLite due to pre-existing `now()` default in the initial migration (not related to Sprint 11.1). Works correctly on PostgreSQL.
4. Reminders and reports (`ReportService`, `ReminderService`) remain user-scoped (not org-scoped) as they operate on non-org models (transactions, reminders).
