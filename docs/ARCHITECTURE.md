# Architecture — PayFlow AI

## Overview

PayFlow AI is a WhatsApp-based financial assistant for autônomos, MEIs, and small businesses in Brazil. It enables users to create charges, send payment links, track payments, and receive automated reminders — all through a conversational interface powered by AI.

The system operates in **sandbox mode** by default (fake provider). No real financial transactions are processed.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), Pydantic |
| Frontend | Next.js 12, TypeScript, TailwindCSS |
| Database | PostgreSQL 15 |
| Cache/Queue | Redis 7, RQ |
| AI | OpenAI GPT-4o |
| Messaging | Twilio WhatsApp Business API |
| Payments | Fake provider (default), Mercado Pago sandbox (opt-in) |
| PDF | ReportLab |
| Infra | Docker Compose |

## Module Structure

```
backend/
├── app/
│   ├── core/           # Config, database, security, logging, redis
│   ├── models/         # SQLAlchemy models (User, Charge, Transaction, billing, etc.)
│   ├── schemas/        # Pydantic schemas
│   ├── repositories/   # Data access layer
│   ├── services/       # Business logic (AIService, ChargeService, SaaSBillingService, EntitlementsService, ProviderConnectionService, etc.)
│   ├── routers/        # FastAPI endpoints (charges, billing_saas, webhook, admin, providers, etc.)
│   ├── providers/      # Payment providers (fake, mercado_pago, asaas) — Sprint 15
│   ├── billing_providers/  # SaaS billing providers (base, fake, factory)
│   ├── regulated_providers/  # Regulated fintech providers (base, fake, factory, open_finance_fake, dda_fake) — Sprint 13/16/17
│   ├── integrations/   # External integrations (Twilio, AsaasClient) — Sprint 15
│   ├── jobs/           # Background jobs (reminder_scheduler)
│   └── utils/          # Dependencies, middleware
├── scripts/            # Utility scripts (seed_demo_data.py, audit_multitenant_integrity.py)
├── tests/              # Integration tests
└── alembic/            # Database migrations

frontend/
├── pages/              # Next.js pages (index, login, dashboard, etc.)
├── components/         # React components (BillingSection, OrganizationSection, etc.)
├── services/           # API client (api.ts, adminAPI.ts)
├── utils/              # Error handling
└── styles/             # TailwindCSS
```

## Key Flows

### 1. WhatsApp → AI → PendingAction → Charge → Provider

```
User sends WhatsApp message
    │
    ▼
Twilio webhook → /webhook/whatsapp
    │
    ▼
AIService.process_message()
    │
    ├── Parses intent via OpenAI GPT-4o
    ├── If charge creation intent:
    │   ├── Creates PendingAction (awaiting confirmation)
    │   └── Sends confirmation request to user
    │
    ▼
User confirms (yes/sim)
    │
    ▼
PendingAction confirmed → ChargeService.create_charge()
    │
    ├── Calls provider.create_charge() (fake or mercado_pago)
    ├── Persists Charge with status=PENDING
    ├── Sends payment link to customer via WhatsApp
    └── Returns charge to user
```

### 2. Webhook Provider → ProviderEvent → Charge Paid → Notification

```
Payment provider sends webhook
    │
    ▼
/provider-webhooks/{provider}
    │
    ▼
ChargeService.process_webhook_payload()
    │
    ├── Parses event from provider
    ├── Creates ProviderEvent record
    ├── If status=paid:
    │   ├── Updates Charge.status = PAID
    │   ├── Sets Charge.paid_at
    │   └── Sends WhatsApp notification to user
    └── Returns updated charge
```

### 3. Reminders Flow

```
ReminderScheduler (background thread)
    │
    ├── Runs every N minutes (configurable)
    │
    ▼
ChargeReminderService.run_reminders()
    │
    ├── Finds PENDING charges with due_date approaching
    ├── Creates ChargeReminderLog entries
    ├── Sends WhatsApp reminders to users
    └── Tracks delivery via ChargeDeliveryLog
```

### 4. Export Flow

```
User clicks "Export CSV" or "Export PDF" in dashboard
    │
    ▼
GET /charges/export.csv?status=overdue&start_date=...
GET /charges/export.pdf?status=pending&end_date=...
    │
    ▼
EntitlementsService.can_export_pdf(org_id)
    │
    ├── If not allowed → 403 Forbidden
    │
    ▼
ChargeService.get_charges_paginated()
    │
    ├── Applies same filters as dashboard (derived statuses, date range)
    ├── SaaSBillingService.increment_usage(org_id, "pdf_exports_generated")
    ├── CSV: generates CSV with derived_status column
    └── PDF: generates PDF report with summary table + charge table
```

### 5. SaaS Billing & Entitlements Flow

```
Organization created
    │
    ▼
OrganizationService.ensure_default_organization()
    │
    ├── SaaSBillingService.ensure_free_subscription(org_id)
    └── Organization gets Free plan automatically

User action (create charge, OCR, export, etc.)
    │
    ▼
EntitlementsService.can_<action>(org_id)
    │
    ├── Checks plan limits and feature flags
    ├── If denied → 403 with reason + limit info
    │
    ▼
Action executes successfully
    │
    ▼
SaaSBillingService.increment_usage(org_id, field)
    │
    └── UsageCounter incremented for current billing period

User changes plan via dashboard
    │
    ▼
POST /saas-billing/subscription/change-plan
    │
    ├── RBAC: owner/admin only
    ├── SaaSBillingService.change_plan(org_id, plan_code)
    ├── Downgrade protection: check if usage exceeds target plan limits
    ├── BillingEvent recorded (idempotent via provider_event_id)
    └── New plan active immediately (sandbox)
```

### 6. WhatsApp Billing Flow

```
Incoming WhatsApp message
    │
    ▼
EntitlementsService.can_process_whatsapp_message(org_id)
    │
    ├── If limit reached → send limit message (PT-BR), return
    │
    ▼
Message accepted → conversation log created
    │
    └── Increment whatsapp_messages_processed (post-success)

If document/image attached:
    │
    ├── EntitlementsService.can_use_ocr(org_id)
    ├── If not included → send upgrade message (PT-BR), return
    ├── Document analyzed successfully
    └── Increment ocr_documents_analyzed (post-success)

If charge creation intent:
    │
    ├── EntitlementsService.can_create_charge(org_id)
    ├── If limit reached → send limit message (PT-BR), return (no pending action created)
    │
    ▼
Charge confirmed → increment charges_created (post-success)
```

## Data Models

### Core Models

- **User**: email, phone, hashed_password, subscription
- **Organization**: name, slug, owner_user_id; multi-tenant workspace boundary
- **OrganizationMember**: organization_id, user_id, role (owner/admin/finance/viewer)
- **Charge**: customer_name, amount, status, due_date, provider, organization_id
- **Customer**: name, phone, notes, organization_id
- **MessageTemplate**: name, tone, template_text, organization_id
- **CollectionRule**: days_offset, trigger_type, template_id, organization_id
- **CollectionMessageLog**: charge_id, message_preview, status, organization_id
- **RecurringTask**: title, recurrence_type, next_run_at, organization_id
- **Transaction**: type (income/expense), category, amount, date
- **Subscription**: plan (free/pro), status, started_at
- **PendingAction**: AI-proposed action awaiting user confirmation, organization_id
- **ProviderEvent**: webhook event log from payment provider
- **ChargeReminderLog**: reminder sent log
- **ChargeDeliveryLog**: delivery confirmation log

### SaaS Billing Models (Sprint 12)

- **SubscriptionPlan**: code, name, price_monthly, limits (charges, customers, team members, templates, recurring tasks, WhatsApp messages), feature flags (OCR, PDF, analytics, collection rules, WhatsApp intelligence)
- **OrganizationSubscription**: organization_id (unique), plan_id, status (trialing/active/past_due/cancelled/expired), billing_provider, provider_subscription_id, current_period_start/end, cancel_at_period_end
- **UsageCounter**: organization_id, period_start/end, counters for charges_created, customers_created, templates_created, recurring_tasks_created, ocr_documents_analyzed, pdf_exports_generated, whatsapp_messages_processed, collection_followups_generated
- **BillingEvent**: organization_id, event_type, plan_code, amount, provider, metadata (JSON), timestamp

### Derived Status

`overdue` is not a database enum value — it's derived:
- `overdue` = `status=PENDING AND due_date < today`
- `pending` (filtered) = `status=PENDING AND (due_date IS NULL OR due_date >= today)`

This derived status is used consistently across:
- Dashboard listing (`GET /charges?status=overdue`)
- CSV export (`GET /charges/export.csv?status=overdue`)
- PDF export (`GET /charges/export.pdf?status=overdue`)
- Summary metrics

## Multi-Tenant Architecture (Sprint 11 + 11.1)

### Organization as Data Boundary

All org-scoped models have `organization_id` FK. Data access is filtered by `organization_id` as the primary boundary:

- **Routers** inject `get_current_organization` (resolves via `X-Organization-ID` header or user's default org)
- **Services** accept `organization_id` parameter and filter all queries
- **Repositories** apply `.where(Model.organization_id == organization_id)` when provided
- **Exports** (CSV/PDF) filter by `organization_id`; RBAC restricts export to finance/admin/owner
- **WhatsApp** uses user's default organization for all operations

### RBAC Roles & Permissions

| Role | Permissions |
|---|---|
| owner | All 9 permissions |
| admin | All except manage_settings |
| finance | view_dashboard, manage_charges, manage_customers, manage_templates, view_analytics, export_data |
| viewer | view_dashboard, view_analytics only |

### Backfill Migration

`h8c9d0e1f2g3` creates default organizations for users without one and backfills `organization_id` on all existing records. Idempotent.

## Security Decisions

1. **Fake provider by default**: No real charges are processed unless explicitly configured
2. **Explicit confirmation**: All charges via WhatsApp require user confirmation
3. **JWT authentication**: All endpoints (except health and webhooks) require auth
4. **Rate limiting**: IP-based rate limiting middleware (100 req/min)
5. **Security headers**: X-Content-Type-Options, X-Frame-Options, etc.
6. **Secrets via env**: No secrets hardcoded; `.env` is gitignored
7. **Demo mode opt-in**: `ENABLE_DEMO_MODE=false` by default
8. **No sensitive operations**: No Pix Out, saque, conta digital, or BaaS

## Sandbox Limitations

- No real payment processing (fake provider)
- Mercado Pago sandbox only (opt-in)
- No bank account integration
- No Pix Out or withdrawal
- No boleto payment
- No Open Finance integration
- Twilio WhatsApp Sandbox requires join code
- OpenAI API key required for AI features

## Demo Mode

When `ENABLE_DEMO_MODE=true`:
- `POST /auth/demo-login` — Login as demo user without password (blocked in production)
- `POST /demo/reset` — Reset demo data (non-production only, requires fake provider)
- Demo user has pre-seeded charges and transactions
- Frontend shows "Entrar como Demo" button

### Demo Mode Security

- **Never enable demo mode in production**: The app fails at startup if `ENVIRONMENT=production` and `ENABLE_DEMO_MODE=true`
- **Demo always uses fake provider**: The app fails at startup if `ENABLE_DEMO_MODE=true` and `PAYFLOW_PAYMENT_PROVIDER != fake`
- **Provider factory blocks Mercado Pago**: `get_payment_provider("mercado_pago")` raises `RuntimeError` when demo mode is active
- **demo-login blocked in production**: Returns HTTP 403 if `ENVIRONMENT=production`
- **demo/reset defense in depth**: Checks environment, demo mode, and provider before resetting
- **Credentials are local-only**: `DEMO_USER_PASSWORD` is a fallback for local/dev environments, not for public exposure

## Health & Readiness

- `GET /health` — Full health check (DB, Redis, OpenAI, Twilio, Mercado Pago)
- `GET /health/ready` — Readiness probe (DB only, for load balancer)
- `GET /health/live` — Liveness probe (process alive)

## Regulated Provider Architecture (Sprint 13)

The PayFlow AI is an **orchestrator, interface, and AI layer**. All regulated financial operations are behind provider abstractions.

### Provider Types

| Provider | Responsibility | Fake | Real (future) |
|---|---|---|---|
| OpenFinanceProvider | Bank account connection, balances, transactions | ✅ | Pluggy / Belvo / Celcoin |
| BankingProvider | Account, Pix Out, bill payment | ✅ | Celcoin / QI Tech / Dock |
| BillPaymentProvider | Boleto validation and payment | ✅ | Celcoin / QI Tech |
| PixProvider | Pix charges, QR Code, webhooks | ✅ | Asaas / Celcoin / QI Tech |
| KYCProvider | Identity verification, biometrics | ✅ | Unico / Caf / Certta |
| FraudProvider | Transaction risk assessment | ✅ | Unico / proprietary |
| DDAProvider | Automatic bill detection | ✅ | Celcoin / Dock |
| ReceiptProvider | Transaction receipts | ✅ | Integrated with charge provider |
| ConsentProvider | Consent management (LGPD, Open Finance) | ✅ | Internal |

### Feature Flags

All regulated features are controlled by feature flags (default `false`):

```
ENABLE_OPEN_FINANCE=false
ENABLE_BILL_PAYMENT=false
ENABLE_PIX_OUT=false
ENABLE_KYC=false
ENABLE_DDA=false
ENABLE_REAL_BANKING=false
```

### Factory Behavior

- **Default**: Returns fake provider
- **Demo mode**: Forces fake for all providers
- **Flag disabled**: Falls back to fake with warning
- **Production + real provider**: Raises `ValueError` (not yet implemented)
- **Production + fake**: Works normally

See: `docs/REGULATED_PROVIDER_ARCHITECTURE.md`, `docs/JOTA_PARITY_ROADMAP.md`

### Provider Foundation (Sprint 14)

5 new tables provide the data layer for regulated provider integration:

```
provider_connections        — Registry of org-provider connections (fake/sandbox)
provider_webhook_events     — Idempotent webhook event log (sanitized)
open_finance_consents       — Open Finance consent records (fake only)
organization_audit_logs     — Audit trail with hashed IP/user-agent
transaction_authorizations  — 6-digit challenge auth (hashed code, 5min expiry)
```

**Services:**
- `ProviderConnectionService` — CRUD + feature flag validation + audit logging
- `ProviderWebhookService` — Event recording + sanitization + idempotency
- `OpenFinanceConsentService` — Fake consent creation + revocation + expiry
- `OrganizationAuditService` — Audit logging + metadata sanitization + IP/UA hashing
- `TransactionAuthorizationService` — Challenge creation + confirmation + expiry

**Router:** `/providers` with 14 endpoints, RBAC-enforced.

**Security:**
- No secrets stored in plaintext (`secret_ref` = external reference only)
- Transaction auth codes hashed with SHA-256
- IP/user-agent hashed with SHA-256 in audit logs
- Webhook payloads/headers sanitized (secrets redacted)
- All providers default to fake; real providers blocked by feature flags

See: `docs/SPRINT_14_PROVIDER_FOUNDATION.md`

## Asaas Sandbox Charge Provider (Sprint 15)

Integrates Asaas API v3 in sandbox mode for receive-only charge creation (Pix, boleto, payment links).

**Components:**
- `app/integrations/asaas_client.py` — HTTP client with retry, timeout, sanitization
- `app/providers/asaas_provider.py` — `PaymentProvider` implementation for Asaas
- `app/providers/provider_factory.py` — updated to support `asaas` provider name
- `app/routers/provider_webhooks.py` — `POST /provider-webhooks/asaas` endpoint
- `app/routers/providers.py` — `POST /providers/asaas/test-connection` endpoint
- `app/routers/charges.py` — `POST /charges/{id}/sync-provider-status` endpoint

**Charge model additions:**
- `provider_bank_slip_url` — boleto PDF URL (Asaas)
- `provider_status` — raw provider status string
- `billing_type` in `ChargeCreate` schema (pix/boleto/undefined)

**Security:**
- API key never logged; `_sanitize_for_log` redacts sensitive keys
- Webhook token validation via `asaas-access-token` header
- Idempotent webhook processing by `event_id`
- Demo mode blocks Asaas; feature flag defaults to false
- Production rejects unknown providers (no silent fallback)
- Only receive-only operations (no Pix Out, no withdrawals)

See: `docs/SPRINT_15_ASAAS_SANDBOX_PROVIDER.md`

## Sprint 16: Open Finance Read Provider Foundation

**Fake/sandbox Open Finance read provider** for demo and development. No real bank connections.

**New models** (`app/models/open_finance.py`):
- `ConnectedAccount` — bank accounts linked via Open Finance consent
- `BankTransaction` — financial movements with category, merchant, amount
- `FinancialCategory` — income/expense/transfer categories
- `OpenFinanceSyncLog` — sync operation audit trail

**Fake provider** (`app/regulated_providers/open_finance_fake.py`):
- `FakeOpenFinanceReadProvider` — generates realistic demo data
- 2 fake accounts, 20-40 transactions, 12 categories
- All data marked `is_demo_data=True`

**Services:**
- `app/services/open_finance_service.py` — consent, sync, audit logging
- `app/services/bank_transaction_service.py` — listing, filtering, grouping
- `app/services/financial_summary_service.py` — monthly summaries, safe insights

**Router** (`app/routers/open_finance.py`):
- `/open-finance/status` — provider status
- `/open-finance/consents/*` — consent CRUD
- `/open-finance/accounts` — list connected accounts
- `/open-finance/sync/fake` — sync demo data
- `/open-finance/transactions/*` — list, summary, categories, merchants
- `/open-finance/sync-logs` — sync operation logs

**WhatsApp intents:**
- `open_finance_balance_summary`, `open_finance_recent_transactions`
- `open_finance_monthly_summary`, `open_finance_category_summary`
- `open_finance_search_transactions`

**Frontend:** `frontend/components/OpenFinanceSection.tsx`

**Security:**
- `ENABLE_OPEN_FINANCE` defaults false
- `OPEN_FINANCE_PROVIDER` defaults "fake"
- No real API calls, no real tokens, no payment initiation
- All data org-scoped with RBAC
- Audit logging for all operations

See: `docs/SPRINT_16_OPEN_FINANCE_FOUNDATION.md`

## Sprint 17: Fake DDA & Bill Management

**Models:** `backend/app/models/bills.py`
- `DetectedBill` — fake boleto/bill with beneficiary, amount, due date, barcode, status
- `BillReminder` — scheduled reminders (WhatsApp, email, push)
- `BillPaymentIntent` — fake payment intent (no execution)
- `BillEventLog` — audit trail for all bill actions

**Migration:** `n3c4d5e6f7g8` — creates 4 new tables

**Provider:** `backend/app/regulated_providers/dda_fake.py`
- `FakeDDAProvider` — generates 8-15 deterministic demo bills per org

**Services:**
- `BillService` — sync, list, get, ignore, mark-paid-manual, event logs
- `BillReminderService` — schedule, list, cancel reminders
- `BillPaymentIntentService` — create, authorize (fake), cancel, expire intents
- `BillSummaryService` — summary, due-today, overdue, upcoming

**Router:** `backend/app/routers/bills.py` — 17 endpoints with RBAC

**WhatsApp intents:**
- `list_due_bills`, `list_overdue_bills`, `list_bills_due_today`
- `bill_summary`, `search_bills`
- `create_bill_reminder`, `prepare_fake_bill_payment`
- `mark_bill_paid_manual`, `ignore_bill`

**Frontend:** `frontend/components/BillsSection.tsx`

**Security:**
- `ENABLE_DDA` defaults false
- `ENABLE_BILL_PAYMENT` defaults false
- `DDA_PROVIDER_NAME` defaults "fake"
- No real payment execution, no real DDA access
- All data org-scoped with RBAC
- All responses include demo/fake disclaimers
- Audit logging for all operations

See: `docs/SPRINT_17_DDA_BILL_MANAGEMENT.md`, `docs/FAKE_DDA_BILL_PAYMENT_SECURITY.md`
