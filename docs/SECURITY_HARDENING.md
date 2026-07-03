# Security Hardening — PayFlow AI

## Provider Foundation Security (Sprint 14)

- **No secrets in plaintext**: `secret_ref` field in `provider_connections` stores only external references, never actual secrets, tokens, or credentials.
- **Transaction auth code hashing**: 6-digit challenge codes are hashed with SHA-256 before storage. Code is never saved in plaintext. In production, the code is not returned in API responses.
- **IP/user-agent hashing**: Audit logs store SHA-256 hashes of IP addresses and user agents, never raw values.
- **Payload sanitization**: Webhook payloads and headers are sanitized before storage. Sensitive keys (`password`, `secret`, `token`, `api_key`, `authorization`, `credential`, etc.) are replaced with `[REDACTED]`.
- **Metadata sanitization**: Audit log metadata is sanitized using the same sensitive-key redaction.
- **Webhook idempotency**: Unique constraint on `(provider_type, provider_name, provider_event_id)` prevents duplicate event processing.
- **Feature flag enforcement**: `ProviderConnectionService.validate_provider_activation()` blocks real providers when feature flags are false. Demo mode forces fake. Production rejects unimplemented real providers.
- **RBAC on all endpoints**: Provider connections (create/deactivate) restricted to owner/admin. Audit logs restricted to owner/admin. Transaction auth requires owner/admin/finance. Viewer role limited to status/flags only.
- **Organization isolation**: All 5 new tables are scoped by `organization_id` with foreign key constraints and indexes. Multi-tenant audit script includes all new tables.
- **No real regulated operations**: All providers default to fake. No Open Finance, Pix Out, bill payment, KYC, DDA, or banking operations are implemented. This sprint creates only the foundation.
- **Transaction auth limits**: 5-minute expiry, maximum 3 failed attempts, automatic expiry of pending authorizations.

## Regulated Provider Architecture (Sprint 13)

- **Feature flags**: 6 regulated feature flags (`ENABLE_OPEN_FINANCE`, `ENABLE_BILL_PAYMENT`, `ENABLE_PIX_OUT`, `ENABLE_KYC`, `ENABLE_DDA`, `ENABLE_REAL_BANKING`) — all default `false`. No regulated feature can be activated without explicit configuration.
- **Provider abstraction**: All regulated operations (Open Finance, banking, bill payment, Pix, KYC, fraud, DDA, receipts, consent) are behind abstract interfaces. No real financial operation is implemented directly.
- **Fake providers default**: All 9 provider types default to fake/sandbox implementations. Safe for development and testing.
- **Production hardening**: Factory rejects unimplemented real providers in production with `ValueError`. Prevents misconfiguration.
- **Demo mode**: Forces fake providers for all regulated types, regardless of configuration.
- **Flag validation**: If feature flag is disabled, factory falls back to fake with warning — even if provider name is set to a real provider.
- **No secrets in code**: No API keys, credentials, or secrets for regulated providers are committed. All provider names default to "fake".
- **Consent model**: Documented consent and authorization model for Open Finance, payment authorization (6-digit password), LGPD compliance, and audit logging.
- **Future data model**: 13 proposed tables with encryption requirements for sensitive fields (CPF, CNPJ, document numbers).

## SaaS Billing Hardening (Sprint 12.1)

- **Seed idempotency**: `seed_plans()` updates existing plans with latest definitions. No duplicates, always in sync with code.
- **Downgrade protection**: Plan downgrades are blocked when current usage exceeds target plan limits. Prevents data loss and inconsistent state.
- **Entitlement payload completeness**: All entitlement responses include `feature`, `plan`, `plan_name`. Feature-flag denials clearly separated from usage-limit denials.
- **Usage counter integrity**: WhatsApp message and OCR usage increments occur only after successful operations. No increments on blocked, failed, or rejected operations.
- **Provider factory hardening**: Production environment rejects unknown billing providers with `ValueError`. Demo mode forces fake provider. Prevents misconfiguration in production.
- **BillingEvent idempotency**: `provider_event_id` deduplication prevents duplicate events on repeated webhooks. Payload sanitization redacts `secret`, `token`, `key`, `password`, `api_key` fields from stored events.
- **Frontend RBAC enforcement**: BillingSection hides management buttons (change plan, checkout, cancel, reactivate) for non-owner/admin roles. Viewers and finance can see data but not modify.
- **Admin billing metrics**: New `GET /admin/billing-metrics` endpoint with aggregated subs by status, orgs by plan, usage totals. Protected by admin authentication.

## SaaS Billing Security (Sprint 12)

- **No real payments**: Fake billing provider is the default. No Stripe, Mercado Pago, or real payment processor is called for SaaS subscriptions. `PAYFLOW_BILLING_PROVIDER=fake` by default.
- **Entitlement enforcement**: All resource-creating endpoints (charges, OCR, PDF exports, collection rules, team members) check `EntitlementsService` before executing. Denied requests return 403 with reason and limit info — no silent failures.
- **RBAC on billing management**: Only `owner` and `admin` roles can change plans, cancel, reactivate, or perform fake checkouts. `viewer` and `finance` roles can view subscription and usage but cannot modify.
- **Usage tracking integrity**: Usage counters increment only after successful resource creation. Failed operations do not increment counters. Counters reset at the start of each billing period.
- **WhatsApp billing safety**: All billing checks in the WhatsApp webhook are wrapped in try/except to prevent billing failures from blocking the user's WhatsApp experience. If the billing service is unavailable, the message is still processed.
- **Billing event audit trail**: All billing actions (plan changes, checkouts, cancellations, reactivations) are logged in `BillingEvent` with timestamp, plan code, provider, and metadata.
- **Default Free subscription**: Every new organization automatically receives a Free plan subscription. No organization can exist without a subscription — `ensure_free_subscription` is called on every billing-related API call.
- **Sandbox isolation**: Fake checkout and fake webhook endpoints are clearly labeled as sandbox-only. No real payment data is processed or stored.
- **Multi-tenant billing isolation**: Subscriptions, usage counters, and billing events are all scoped by `organization_id`. No cross-org billing data access is possible.
- **Admin metrics**: Billing metrics in admin endpoint are read-only and protected by admin authentication.

## NOT NULL Enforcement & Migration Portability (Sprint 11.2)

- **`organization_id` is NOT NULL**: All 7 org-scoped tables (charges, customers, message_templates, collection_rules, collection_message_logs, recurring_tasks, pending_actions) now enforce `organization_id` as `NOT NULL` at the database level.
- **Migration `i9d0e1f2g3h4`**: Deletes any remaining NULL records (safety net after backfill), then alters column to `NOT NULL` using `batch_alter_table` for SQLite compatibility.
- **Auto-resolution**: Services auto-resolve `organization_id` from user's default organization when not explicitly provided. This prevents accidental NULL inserts from code paths that don't pass `organization_id`.
- **Migration portability**: All Alembic migrations now work on both SQLite and PostgreSQL. No PostgreSQL-specific syntax outside dialect guards.
- **Audit script**: `scripts/audit_multitenant_integrity.py` detects orphan records (NULL or invalid `organization_id`). Exit code 1 if inconsistencies found.
- **Admin health endpoint**: `GET /admin/multitenant-health` exposes orphan record counts. Protected by admin authentication.

## Multi-Tenant Isolation Hardening (Sprint 11.1)

- **Organization_id as primary data boundary**: All org-scoped routers now inject `get_current_organization` and pass `org.id` to every service call. Services filter all queries by `organization_id` in addition to `user_id`.
- **Full router coverage**: charges, analytics, customers, message_templates, collection, recurring_tasks — all endpoints enforce org filtering.
- **Export isolation**: CSV/PDF exports (charges and analytics) filter by `organization_id`. Data from org A never appears in org B's export.
- **RBAC on exports**: `viewer` role cannot export data. `finance`, `admin`, and `owner` can export.
- **WhatsApp org context**: Charges created via WhatsApp are associated with the user's default organization. `PendingAction.organization_id` is always populated.
- **Backfill migration**: `h8c9d0e1f2g3` creates default organizations for users without one and backfills `organization_id` on all existing records. Idempotent, no data deletion.
- **Test coverage**: All test fixtures create organizations and set `organization_id` on org-scoped records. 289 backend tests pass with 0 failures.
- **No cross-org data access**: Users can only access data within their current organization context. `X-Organization-ID` header is validated against membership.

## Multi-Tenant Security (Sprint 11)

- **Organization isolation**: All priority models (charges, customers, templates, collection rules, logs, recurring tasks, pending actions) have `organization_id` FK. Data is filtered by organization context.
- **RBAC enforcement**: 4 roles (owner, admin, finance, viewer) with 9 permissions. Mutating endpoints check `has_permission()` before executing.
- **Role hierarchy**: owner > admin > finance > viewer. Higher roles inherit lower role permissions.
- **Membership validation**: `get_current_organization` validates that the user is an active member of the requested organization before returning it.
- **Owner protection**: Owner role cannot be assigned via member invitation. Owner cannot be deactivated.
- **No cross-org data access**: Users can only access organizations they are members of. `X-Organization-ID` header is validated against membership.
- **WhatsApp org context**: Charges created via WhatsApp are automatically associated with the user's default organization.
- **No sensitive financial operations**: Multi-tenancy does not introduce any banking, Pix Out, or real payment operations.

## Analytics Security (Sprint 10)

- **User isolation**: All analytics endpoints filter by `user_id` from `get_current_active_user`. No cross-user data leakage.
- **No credit scoring**: Analytics are operational only. `CustomerStatus` and suggested actions are not credit scores or financial decisions.
- **No alarmism**: Insights use neutral, operational language. No crisis language, no risk warnings, no financial recommendations.
- **No banking operations**: Analytics endpoints are read-only. No Pix Out, no real payments, no Open Finance.
- **QR Code sandbox**: Analytics does not interact with QR codes or payment providers.
- **Export safety**: CSV/PDF exports contain only the authenticated user's data, filtered by `user_id`.

## Demo Mode Security (Sprint 5.1)

- **Demo mode never runs in production**: `validate_demo_mode()` fails startup if `ENVIRONMENT=production` and `ENABLE_DEMO_MODE=true`
- **Demo mode requires fake provider**: startup fails if `ENABLE_DEMO_MODE=true` and `PAYFLOW_PAYMENT_PROVIDER != fake`
- **Mercado Pago blocked in demo mode**: `get_payment_provider("mercado_pago")` raises `RuntimeError` when demo mode is active
- **demo-login blocked in production**: Returns HTTP 403 if `ENVIRONMENT=production`
- **demo/reset defense in depth**: Checks environment, demo mode flag, and provider before executing

## Rate Limiting (Sprint 6)

### User Rate Limiting

Authenticated endpoints are rate-limited per user:

| Endpoint | Limiter | Default limit |
|---|---|---|
| `POST /charges` | `charges_limiter` | 20/min |
| `POST /charges/{id}/cancel` | `charges_limiter` | 20/min |
| `POST /charges/reminders/run` | `charges_limiter` | 20/min |
| `GET /charges/export.csv` | `exports_limiter` | 10/min |
| `GET /charges/export.pdf` | `exports_limiter` | 10/min |
| `POST /demo/reset` | `demo_reset_limiter` | 5/hour |

Configuration:

```env
USER_RATE_LIMIT_ENABLED=true
USER_RATE_LIMIT_CHARGES_PER_MINUTE=20
USER_RATE_LIMIT_EXPORTS_PER_MINUTE=10
USER_RATE_LIMIT_DEMO_RESET_PER_HOUR=5
```

- Uses Redis when available
- Falls back to in-memory in development/test (when `REDIS_URL` is not set)
- Returns HTTP 429 with clear message
- Disabled entirely when `USER_RATE_LIMIT_ENABLED=false`

### Webhook Rate Limiting

All webhook endpoints are rate-limited per IP + provider:

```env
WEBHOOK_RATE_LIMIT_PER_MINUTE=60
```

- Skipped in testing environment
- Applied to: Twilio WhatsApp, Mercado Pago, fake provider

### IP Rate Limiting (existing)

Global IP-based rate limiting middleware: 100 requests/minute per IP.

## Webhook Hardening

### Twilio WhatsApp Webhook

- **Signature validation mandatory in production**: If `TWILIO_VALIDATE_SIGNATURE=false` in production, webhook returns 403
- **Bypass only in development**: `TWILIO_VALIDATE_SIGNATURE=false` is accepted only in non-production environments
- **Rate limited**: Per IP, 60 req/min (configurable)

### Mercado Pago Webhook

- **Signature validation required**: `x-signature` and `x-request-id` headers must be present and valid
- **Missing headers**: Returns 401
- **Invalid signature**: Returns 401
- **Idempotency**: Duplicate events (same `external_id` already processed) return `{"status": "duplicate"}` without re-processing
- **No sensitive payload logged**: Only `provider`, `event_type`, `external_id` are logged
- **Rate limited**: Per IP, 60 req/min

### Fake Provider Webhook

- **Rate limited**: Per IP, 60 req/min
- **Available in all environments** (for development/testing)
- **No signature required** (sandbox only)

## Admin Metrics Security

- `GET /admin/system-metrics` requires admin authentication
- Admin access controlled by `ADMIN_EMAILS` environment variable
- No personal data exposed (no emails, phones, passwords, tokens)
- Only aggregate counts and uptime

## Sentry Data Sanitization

- `before_send` hook strips tokens, passwords, API keys, auth headers
- No full webhook payloads sent to Sentry
- No phone numbers or WhatsApp message content in breadcrumbs

## Pre-Production Checklist

- [ ] `ENVIRONMENT=production`
- [ ] `ENABLE_DEMO_MODE=false`
- [ ] `PAYFLOW_PAYMENT_PROVIDER` is `fake` or `mercado_pago` (with sandbox credentials)
- [ ] `TWILIO_VALIDATE_SIGNATURE=true`
- [ ] `USER_RATE_LIMIT_ENABLED=true`
- [ ] `SENTRY_DSN` set (optional but recommended)
- [ ] `ADMIN_EMAILS` configured
- [ ] `SECRET_KEY` is a strong random value (64+ chars)
- [ ] No secrets in `.env` committed to git
- [ ] Redis available for rate limiting (or accept in-memory fallback)
- [ ] Collection rules are non-transactional (no auto-sending)
- [ ] Message templates validated against aggressive language

## OCR Assistive Security (Sprint 8/8.1)

- **OCR é apenas assistivo**: extrai dados de imagens/PDFs, NUNCA executa pagamentos ou Pix
- **Não paga boleto**: OCR apenas sugere criação de lembrete, requer confirmação explícita
- **Não cria transação automaticamente**: toda ação sugerida tem `requires_confirmation=true`
- **Provider configurável**: `DOCUMENT_ANALYSIS_PROVIDER` (default `mock`) — em test/demo usa mock determinístico
- **OpenAI Vision é opcional**: só ativado quando `DOCUMENT_ANALYSIS_PROVIDER=openai` e `OPENAI_API_KEY` configurada
- **Dados sensíveis não são logados**: logs contêm apenas metadados (tipo, tamanho, confiança), nunca conteúdo do documento
- **Limite de arquivo**: 5MB máximo, tipos aceitos: PNG, JPG, WebP, PDF
- **Arquivo não é salvo permanentemente**: processado em memória e descartado

## Collection & Customer Intelligence Security (Sprint 9)

- **Nenhuma mensagem de cobrança é enviada automaticamente**: todas as mensagens são rascunhos (DRAFT) até confirmação explícita
- **IA pode sugerir, usuário confirma**: o sistema gera sugestões de mensagem, mas o envio requer confirmação do usuário
- **Linguagem agressiva bloqueada**: templates com palavras abusivas (caloteiro, ladrão, etc.) são rejeitados na criação
- **Placeholders validados**: apenas placeholders permitidos são aceitos em templates; unknown placeholders são rejeitados
- **Score operacional não é score de crédito**: o status do cliente é um indicador de relacionamento, não deve ser usado para decisões de crédito
- **Isolamento por usuário**: clientes, templates e regras são isolados por user_id
- **Logs de mensagens**: todas as mensagens geradas são logadas com status (draft, pending_confirmation, sent, skipped, failed)
- **Regras de cobrança são não-transacionais**: apenas preparam rascunhos, nunca executam operações bancárias
- **QR Codes no PDF são sandbox**: não representam Pix QR codes reais, claramente identificados como demo
