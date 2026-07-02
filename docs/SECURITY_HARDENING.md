# Security Hardening — PayFlow AI

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
