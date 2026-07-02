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
│   ├── models/         # SQLAlchemy models (User, Charge, Transaction, etc.)
│   ├── schemas/        # Pydantic schemas
│   ├── repositories/   # Data access layer
│   ├── services/       # Business logic (AIService, ChargeService, etc.)
│   ├── routers/        # FastAPI endpoints
│   ├── providers/      # Payment providers (fake, mercado_pago)
│   ├── integrations/   # External integrations (Twilio)
│   ├── jobs/           # Background jobs (reminder_scheduler)
│   └── utils/          # Dependencies, middleware
├── scripts/            # Utility scripts (seed_demo_data.py)
├── tests/              # Integration tests
└── alembic/            # Database migrations

frontend/
├── pages/              # Next.js pages (index, login, dashboard, etc.)
├── services/           # API client
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
ChargeService.get_charges_paginated()
    │
    ├── Applies same filters as dashboard (derived statuses, date range)
    ├── CSV: generates CSV with derived_status column
    └── PDF: generates PDF report with summary table + charge table
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
