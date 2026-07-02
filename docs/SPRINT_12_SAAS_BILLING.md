# Sprint 12 — SaaS Billing, Plans, Usage Limits & Subscription Sandbox

## Overview

Implemented a complete SaaS billing layer with subscription plans, usage tracking, entitlement enforcement, and a sandboxed subscription management system. No real payments are processed — a fake billing provider is used by default for demo/development.

## Models (`backend/app/models/billing.py`)

- **SubscriptionPlan** — plan definitions (code, name, price, limits per feature)
- **OrganizationSubscription** — one-to-one with Organization, tracks current plan, status, billing provider
- **UsageCounter** — monthly usage counters per organization (charges, customers, templates, OCR, PDF, WhatsApp messages, etc.)
- **BillingEvent** — audit log of all billing events (plan changes, checkouts, cancellations)

### Plan Limits

| Feature | Free | Starter | Professional | Business |
|---|---|---|---|---|
| Charges/month | 20 | 100 | 500 | 5000 |
| Customers | 10 | 100 | 500 | 5000 |
| Team members | 1 | 2 | 5 | 20 |
| Message templates | 3 | 10 | 50 | 200 |
| Recurring tasks | 0 | 5 | 20 | 100 |
| WhatsApp messages/month | 50 | 500 | 5000 | Unlimited |
| OCR | ❌ | ❌ | ✅ | ✅ |
| PDF export | ❌ | ✅ | ✅ | ✅ |
| Advanced analytics | ❌ | ❌ | ✅ | ✅ |
| Collection rules | ❌ | ✅ | ✅ | ✅ |
| WhatsApp intelligence | ❌ | ✅ | ✅ | ✅ |

## Migration (`j0e1f2g3h4i5_add_saas_billing_tables.py`)

Creates 4 tables: `subscription_plans`, `organization_subscriptions`, `usage_counters`, `billing_events`. Portable across SQLite and PostgreSQL.

## Services

### SaaSBillingService (`backend/app/services/saas_billing_service.py`)

- `seed_plans()` — seeds 4 default plans (free, starter, professional, business)
- `ensure_free_subscription(org_id)` — creates Free subscription if none exists
- `get_subscription(org_id)` — returns current subscription
- `get_current_plan(org_id)` — returns current plan
- `change_plan(org_id, plan_code)` — changes plan (owner/admin only)
- `cancel_subscription(org_id)` — cancels, downgrades to Free at period end
- `reactivate_subscription(org_id)` — reactivates a cancelled subscription
- `fake_checkout(org_id, plan_code)` — simulates a checkout (sandbox)
- `get_usage(org_id)` — returns usage counters for current period
- `increment_usage(org_id, field)` — increments a usage counter
- `get_entitlements(org_id)` — returns plan features and limits
- `get_subscription_summary(org_id)` — full summary (subscription + plan + usage + entitlements)
- `record_event(...)` — logs a billing event

### EntitlementsService (`backend/app/services/entitlements_service.py`)

Checks whether an organization can perform an action:

- `can_create_charge(org_id)` — checks monthly charge limit
- `can_create_customer(org_id)` — checks customer limit
- `can_create_template(org_id)` — checks template limit
- `can_create_recurring_task(org_id)` — checks recurring task limit
- `can_use_ocr(org_id)` — checks if OCR is included in plan
- `can_export_pdf(org_id)` — checks if PDF export is included
- `can_use_advanced_analytics(org_id)` — checks if advanced analytics included
- `can_use_collection_rules(org_id)` — checks if collection rules included
- `can_add_team_member(org_id)` — checks team member limit
- `can_process_whatsapp_message(org_id)` — checks WhatsApp message limit

### Billing Providers (`backend/app/billing_providers/`)

- `base.py` — abstract base class `BillingProvider`
- `fake.py` — `FakeBillingProvider` for sandbox/demo mode
- `factory.py` — `get_billing_provider()` factory, controlled by `PAYFLOW_BILLING_PROVIDER` env var

## API Endpoints (`backend/app/routers/billing_saas.py`)

Prefix: `/saas-billing`

| Method | Path | Description | Role |
|---|---|---|---|
| GET | `/plans` | List all available plans | Any org member |
| GET | `/subscription` | Get current subscription summary | Any org member |
| POST | `/subscription/change-plan` | Change plan | Owner/Admin |
| POST | `/subscription/cancel` | Cancel subscription | Owner/Admin |
| POST | `/subscription/reactivate` | Reactivate subscription | Owner/Admin |
| GET | `/usage` | Get usage counters | Any org member |
| GET | `/entitlements` | Get plan entitlements | Any org member |
| POST | `/fake/checkout` | Simulate checkout (sandbox) | Owner/Admin |
| POST | `/fake/webhook` | Simulate billing webhook | Owner/Admin |

## Entitlement Enforcement

### API Endpoints

Entitlement checks added to existing endpoints with 403 errors when limits are reached:

- **Charges** (`charges.py`) — PDF export entitlement check + usage increment
- **Documents** (`documents.py`) — OCR entitlement check + usage increment
- **Collection** (`collection.py`) — Collection rules entitlement check + usage increment
- **Analytics** (`analytics.py`) — PDF export entitlement check + usage increment
- **Organizations** (`organizations.py`) — Team member limit check before adding members

### WhatsApp Webhook (`webhook.py`)

Three billing integration points:

1. **WhatsApp message processing** — checks `can_process_whatsapp_message` before processing each incoming message. Increments `whatsapp_messages_processed` counter. Sends a limit-reached message if blocked.
2. **Document analysis (OCR)** — checks `can_use_ocr` before analyzing images/PDFs sent via WhatsApp. Increments `ocr_documents_analyzed` if allowed.
3. **Charge creation** — checks `can_create_charge` before creating a pending charge action. Increments `charges_created` after successful charge confirmation.

All billing checks are wrapped in try/except to avoid breaking WhatsApp flow if billing service fails.

## Default Subscriptions

- **New organizations** — automatically get Free plan via `ensure_free_subscription` in `OrganizationService`
- **Demo organization** — seeded with Professional plan in `demo_service.py`

## Admin Metrics

`GET /admin/system-metrics` now includes billing data:
- Total subscriptions by plan
- Total active subscriptions
- Usage statistics (total charges, OCR, PDF exports, WhatsApp messages)

## Frontend

- **`saasBillingAPI`** (`frontend/services/api.ts`) — API client for all `/saas-billing` endpoints
- **`BillingSection`** (`frontend/components/BillingSection.tsx`) — dashboard section with:
  - Current plan status (name, status badge, cancel/reactivate buttons)
  - Usage meters (8 metrics with progress bars, color-coded by usage percentage)
  - Plan cards (4 plans with features, pricing, change plan / fake checkout buttons)
  - Sandbox warning notice

## Tests

- **`backend/tests/test_billing.py`** — 20+ tests covering:
  - Plans seeded correctly
  - New org gets Free subscription
  - Demo gets Professional plan
  - Get subscription, change plan, cancel, reactivate
  - Role-based access (viewer cannot change plan, finance can view usage)
  - Charge/customer/team member limits on Free
  - OCR/PDF blocked on Free, unlocked on Professional
  - Usage increments after successful creation
  - Fake checkout changes subscription
  - Billing event recorded
  - User isolation between organizations
  - Fake billing provider is default
- **Test fixtures** (`conftest.py`, `test_integration_charges.py`, `test_sprint6.py`) — updated to seed billing plans and assign Professional subscriptions to test organizations
- **321 backend tests pass**

## Files Modified

- `backend/app/models/billing.py` — added `max_whatsapp_messages_per_month` field
- `backend/app/services/entitlements_service.py` — added `can_process_whatsapp_message`
- `backend/app/services/saas_billing_service.py` — added WhatsApp limits to plan definitions and entitlements
- `backend/app/routers/webhook.py` — WhatsApp message, OCR, and charge billing checks
- `backend/app/routers/charges.py` — PDF export entitlement check
- `backend/app/routers/documents.py` — OCR entitlement check
- `backend/app/routers/collection.py` — Collection rules entitlement check
- `backend/app/routers/analytics.py` — PDF export entitlement check
- `backend/app/routers/organizations.py` — Team member limit check
- `backend/app/routers/admin.py` — Billing metrics in system-metrics
- `backend/app/routers/billing_saas.py` — Router prefix changed to `/saas-billing`
- `backend/app/services/demo_service.py` — Professional plan for demo org
- `backend/app/services/organization_service.py` — Free subscription on org creation
- `backend/migrations/versions/j0e1f2g3h4i5_add_saas_billing_tables.py` — Migration with WhatsApp column
- `backend/scripts/audit_multitenant_integrity.py` — SaaS billing tables in audit
- `backend/tests/conftest.py` — Billing plan seeding in fixtures
- `backend/tests/test_integration_charges.py` — Billing plan seeding in integration fixtures
- `backend/tests/test_sprint6.py` — Billing plan seeding in sprint6 fixtures
- `backend/tests/test_billing.py` — New billing test suite
- `frontend/services/api.ts` — `saasBillingAPI` client
- `frontend/components/BillingSection.tsx` — New billing dashboard section
- `frontend/pages/dashboard.tsx` — BillingSection added to dashboard
