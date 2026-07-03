# PayFlow AI — Release Notes

## Sprint 17: Fake DDA, Contas a Pagar e Bill Management

- **Fake DDA provider**: `FakeDDAProvider` generates 8-15 deterministic demo bills per organization with varied due dates, amounts, beneficiaries, categories, and statuses. No real DDA access. All data marked `is_demo_data=True`.
- **4 new models**: `DetectedBill`, `BillReminder`, `BillPaymentIntent`, `BillEventLog` — all org-scoped with proper indexes, unique constraints, and event logging.
- **Migration**: `n3c4d5e6f7g8` — creates 4 new tables. Compatible with SQLite and PostgreSQL.
- **4 services**: `BillService`, `BillReminderService`, `BillPaymentIntentService`, `BillSummaryService` — manage sync, listing, filtering, reminders, fake payment intents, and summaries.
- **17 API endpoints**: Status, sync, list, summary, due-today, overdue, upcoming, get, ignore, mark-paid-manual, reminders (create/list/cancel), payment intents (create/authorize-fake/cancel), events. All org-scoped with RBAC.
- **9 WhatsApp intents**: list_due_bills, list_overdue_bills, list_bills_due_today, bill_summary, search_bills, create_bill_reminder, prepare_fake_bill_payment, mark_bill_paid_manual, ignore_bill. All with demo disclaimers.
- **Frontend**: `BillsSection.tsx` with summary cards, bill list, filters, action buttons, and "Demo/Fake" badge.
- **Admin metrics**: Bill counts, fake payment intents by status, reminders by status, event logs total.
- **Security**: No real payment execution, no real DDA, no real bank credentials. Feature flags `ENABLE_DDA` and `ENABLE_BILL_PAYMENT` remain `false` by default.
- **Tests**: 70 new tests across 5 files (models, service, router, WhatsApp, payment intents). Total: 629 backend tests, 0 failures.
- **Audit**: 4 new tables added to multi-tenant integrity audit script.

## Sprint 16.1: Test Suite Stabilization, Count Consistency & Open Finance Readiness

- **Fixed `test_asaas_config_defaults` failure**: Root cause was shell environment variables (`ASAAS_ENVIRONMENT=production`) overriding pydantic defaults. Fix: `monkeypatch.delenv` for all Asaas env keys + `_env_file=None` to isolate test Settings instances from both `.env` file and shell env vars.
- **Full suite green**: 559 passed, 0 failed, 0 errors.
- **README test count corrected**: 516 → 559 backend tests.
- **Release notes test count corrected**: 516 → 559.
- **No new features**: stabilization sprint only.

## Sprint 16: Open Finance Read Provider Foundation

- **Fake/sandbox Open Finance provider**: `FakeOpenFinanceReadProvider` generates realistic demo data (2 accounts, 20-40 transactions, 12 categories). No real API calls to Pluggy/Belvo. All data marked `is_demo_data=True`.
- **4 new models**: `ConnectedAccount`, `BankTransaction`, `FinancialCategory`, `OpenFinanceSyncLog` — all org-scoped with proper indexes and constraints.
- **Migration**: `m2b3c4d5e6f7` — creates 4 new tables with foreign keys, unique constraints, and indexes.
- **3 new services**: `OpenFinanceService` (consent, sync, audit), `BankTransactionService` (listing, filtering, grouping), `FinancialSummaryService` (monthly summaries, balance, safe insights).
- **Router**: `/open-finance` prefix with 11 endpoints. RBAC: owner/admin/finance for write operations.
- **WhatsApp intents**: 5 new intents for fake financial data reading (balance, transactions, monthly summary, categories, search). All responses include demo disclaimer.
- **Frontend**: `OpenFinanceSection.tsx` component with demo badge, consent creation, sync, accounts, and transactions display.
- **Admin metrics**: Open Finance account/transaction/sync-log counts added to billing-metrics endpoint.
- **Research doc**: `docs/OPEN_FINANCE_PROVIDER_RESEARCH.md` — Pluggy vs Belvo comparison and recommendations.
- **Tests**: 43 new tests across 4 files (models, service, router, WhatsApp). Total: 559 backend tests, 0 failures.
- **Security**: `ENABLE_OPEN_FINANCE` defaults false, `OPEN_FINANCE_PROVIDER` defaults "fake", demo mode forced, no real tokens, no payment initiation, audit logging, org-scoped data.

## Sprint 15: Asaas Sandbox Charge Provider

- **Asaas API v3 integration**: Sandbox mode for Pix, boleto, and payment link charges. Receive-only operations (no Pix Out, no withdrawals).
- **AsaasClient** (`app/integrations/asaas_client.py`): HTTP client with 30s timeout, retry on 5xx/timeouts, sensitive data sanitization. Methods for customer creation, payment creation, Pix QR code retrieval, payment status, and cancellation.
- **AsaasPaymentProvider** (`app/providers/asaas_provider.py`): Implements `PaymentProvider` interface. Supports PIX/BOLETO/UNDEFINED billing types. Auto-generates sandbox CPF. Maps Asaas statuses to PayFlow statuses. Parses webhook events. Validates webhook tokens.
- **Provider factory updated**: Supports `asaas` provider name with validation (demo mode, feature flag, API key). Production rejects unknown providers.
- **Charge model additions**: `provider_bank_slip_url` (boleto PDF), `provider_status` (raw provider status). `billing_type` field in `ChargeCreate` schema.
- **Migration**: `l2a3b4c5d6e7` — adds `provider_bank_slip_url` and `provider_status` columns to `charges` table.
- **Webhook endpoint**: `POST /provider-webhooks/asaas` — validates `asaas-access-token` header, idempotent by `event_id`, rate limited.
- **Test-connection endpoint**: `POST /providers/asaas/test-connection` — validates config without API calls. RBAC: owner/admin.
- **Sync endpoint**: `POST /charges/{id}/sync-provider-status` — manual reconciliation via provider API. Read-only. RBAC: manage_charges.
- **WhatsApp integration**: `PendingActionService` passes `billing_type` to charge creation. Uses active provider automatically.
- **Frontend**: Provider badge per charge, sync button, boleto PDF link, provider status display.
- **Tests**: 39 new tests across 4 files (config, provider, client, webhook). Total: 473 backend tests, 0 failures.
- **Security**: API key never logged, webhook token validation, idempotency, demo mode blocks Asaas, feature flag defaults false, production rejects unknown providers.

## Sprint 14: Provider Foundation, Consent, Audit Logs & Transaction Auth

- **5 new tables**: `provider_connections`, `provider_webhook_events`, `open_finance_consents`, `organization_audit_logs`, `transaction_authorizations` — all org-scoped with proper indexes.
- **Migration**: `k1f2g3h4i5j6` — compatible with SQLite and PostgreSQL, single head.
- **5 new services**: ProviderConnectionService, ProviderWebhookService, OpenFinanceConsentService, OrganizationAuditService, TransactionAuthorizationService.
- **Provider connection registry**: Create/list/deactivate fake/sandbox connections. Real providers blocked by feature flags. Demo mode forces fake. Production rejects unimplemented real providers.
- **Webhook idempotency**: Unique constraint on `(provider_type, provider_name, provider_event_id)`. Payloads and headers sanitized (secrets/token/key/password redacted). Duplicate detection.
- **Open Finance consent (fake)**: Creates fake consent with fake authorization URL. List/revoke/expire. No real consent initiation.
- **Audit logs**: Sensitive actions logged with SHA-256 hashed IP/user-agent. Metadata sanitized. Filterable by action/resource/provider with pagination.
- **Transaction authorization**: 6-digit challenge code hashed with SHA-256 (never stored in plaintext). 5-minute expiry, max 3 attempts. Code returned only in testing/demo — never in production.
- **New router**: `/providers` with 14 endpoints — connections, consents, audit logs, transaction auth, provider status, feature flags, webhook fake.
- **RBAC**: owner/admin (create/deactivate connections, create/revoke consents, view audit logs), finance (list connections/consents, create/confirm/cancel auth), viewer (status/flags only).
- **Provider status endpoint**: `GET /providers/status` returns environment, demo_mode, and per-provider status with `real_operation_allowed` flag.
- **Feature flags endpoint**: `GET /providers/feature-flags` returns all 6 regulated flags — no secrets exposed.
- **Admin metrics updated**: `/admin/billing-metrics` now includes provider connections total/active, consents by status, webhooks by status, transaction auths by status, audit logs total.
- **Multi-tenant audit**: Script updated to include 5 new tables. All 15 tables pass with 0 orphans.
- **Tests**: 35 new tests (22 provider foundation + 13 transaction authorization). 434 backend tests pass. 0 failures.
- **Security**: No secrets in plaintext. No real regulated operations. All behind feature flags. IP/user-agent hashed. Payloads/headers/metadata sanitized.

## Sprint 13: Jota Feature Parity Blueprint & Regulated Provider Architecture

- **Competitor research**: Comprehensive research of Jota (jota.ai) with 18 sources, 10 confirmed feature categories, parceiros (Celcoin, Unico, Meta), and business model analysis.
- **Parity matrix**: 40-feature Jota vs PayFlow matrix with gaps, priorities (P0-P3), provider requirements, and suggested sprints.
- **Regulated provider architecture**: 9 abstract provider interfaces (OpenFinance, Banking, BillPayment, Pix, KYC, Fraud, DDA, Receipt, Consent) with methods, events, risks, fake providers, and real provider candidates.
- **7-phase roadmap**: Provider foundation → real charges → Open Finance → DDA → payment initiation → KYC/KYB → BaaS/Pix Out. Estimated 4-5 months to full parity.
- **Consent model**: Open Finance consent, WhatsApp consent, payment authorization (6-digit password), LGPD compliance, pre-authorization rules, revocation, audit logs.
- **WhatsApp commands**: 13 commands mapped with intent, provider, risk, confirmation, and current status.
- **Future data model**: 13 proposed tables (provider_connections, open_finance_consents, connected_accounts, bank_transactions, detected_bills, bill_payment_intents, payment_authorizations, payment_receipts, kyc_profiles, kyb_profiles, risk_events, provider_webhook_events, organization_audit_logs).
- **Feature flags**: 6 regulated feature flags added (ENABLE_OPEN_FINANCE, ENABLE_BILL_PAYMENT, ENABLE_PIX_OUT, ENABLE_KYC, ENABLE_DDA, ENABLE_REAL_BANKING) — all default `false`.
- **Provider code**: Abstract base classes, fake implementations, and factory with feature flag validation. Production rejects unimplemented real providers. Demo mode forces fake.
- **Tests**: 43 new tests (feature flags + provider factory). 396 backend tests pass. No regressions.
- **Documentation**: 8 new docs + README updated with Jota parity roadmap section.
- **Security**: No regulated operations implemented. No real providers. No secrets. All behind abstraction + feature flags.

## Sprint 12.1: Billing Hardening

- **Seed idempotency**: `seed_plans()` now updates existing plans with latest definitions instead of skipping. No duplicates on repeated calls.
- **Downgrade protection**: `change_plan()` blocks downgrades when current usage exceeds target plan limits. Returns clear error with exceeded resource details.
- **Entitlements payload**: All entitlement responses now include `feature` and `plan_name` fields. Feature-flag denials separated from usage-limit denials.
- **Usage integrity**: WhatsApp message and OCR usage increments moved to post-success (after conversation log / after document analysis). No increments on blocked or failed operations.
- **WhatsApp billing messages**: Improved PT-BR messages with plan name, limit, current usage, and clear "no action executed" statements.
- **Provider factory hardening**: Production rejects unknown providers with `ValueError`. Demo mode forces fake provider. Dev/testing falls back to fake with warning.
- **BillingEvent idempotency**: `provider_event_id` deduplication prevents duplicate events on repeated webhooks. Payload sanitization redacts secret/token/key fields.
- **List plans endpoint**: Now includes `max_whatsapp_messages_per_month` in response.
- **Frontend hardening**: `BillingSection` with `data-testid` attributes, role-based button visibility (owner/admin only), error state with retry, loading state.
- **Admin billing metrics**: New `GET /admin/billing-metrics` endpoint with subs by status, orgs by plan, usage totals, total billing events.
- **E2E tests**: 7 Playwright billing tests covering section visibility, plan cards, usage meters, change plan flow.
- **Backend tests**: 32 new tests (64 billing tests total). 353 backend tests pass. Frontend build passes. No regressions.

## Sprint 12: SaaS Billing, Plans, Usage Limits & Subscription Sandbox

- **SaaS billing layer**: Subscription plans (Free, Starter, Professional, Business), usage counters, billing events, and a sandboxed subscription management system.
- **Models**: `SubscriptionPlan`, `OrganizationSubscription`, `UsageCounter`, `BillingEvent` in `billing.py`.
- **Migration** `j0e1f2g3h4i5`: Creates 4 billing tables. Portable across SQLite and PostgreSQL.
- **SaaSBillingService**: Plan seeding, subscription management, usage tracking, entitlement checks, fake checkout, event logging.
- **EntitlementsService**: 10 entitlement checks (charges, customers, templates, recurring tasks, OCR, PDF, analytics, collection rules, team members, WhatsApp messages).
- **Billing providers**: Abstract `BillingProvider` base, `FakeBillingProvider` for sandbox, factory pattern with `PAYFLOW_BILLING_PROVIDER` env var.
- **API endpoints** (`/saas-billing`): Plans, subscription, usage, entitlements, change-plan, cancel, reactivate, fake checkout, fake webhook.
- **Entitlement enforcement**: Charges PDF export, document OCR, collection rules, analytics PDF export, team member limits — all return 403 with clear error messages when limits reached.
- **WhatsApp billing**: Message processing limit, OCR entitlement check, charge creation limit with usage increment after confirmation. Limit-reached messages sent to users.
- **Default subscriptions**: New orgs get Free plan automatically. Demo org gets Professional plan.
- **Admin metrics**: System-metrics endpoint includes subscription counts and usage data.
- **Frontend**: `BillingSection` component with plan cards, usage meters, change/cancel/reactivate, fake checkout. `saasBillingAPI` client in `api.ts`.
- **Tests**: 20+ new billing tests. All test fixtures updated with billing plan seeding. 321 backend tests pass. Frontend build passes.

## Sprint 11.2: Migration Portability & NOT NULL Enforcement

- **Problem**: Alembic migrations used PostgreSQL-specific syntax (`DO $$` blocks, `postgresql.ENUM`, `now()`) that broke SQLite. `organization_id` was nullable with no enforcement.
- **Fix**: All migrations now portable across SQLite and PostgreSQL. `organization_id` is `NOT NULL` on all org-scoped tables.
- **Migration portability**: Replaced `now()` with `CURRENT_TIMESTAMP`. Wrapped `DO $$` blocks in dialect checks. Used `sa.String(20)` instead of `postgresql.ENUM` for non-PG dialects. Used `batch_alter_table` for FK constraints in SQLite.
- **Migration** `i9d0e1f2g3h4`: Sets `organization_id` to `NOT NULL` on all 7 org-scoped tables. Deletes any remaining NULL records first (safety net after backfill).
- **Models updated**: All 7 org-scoped models now have `nullable=False` on `organization_id`.
- **Auto-resolution**: Services auto-resolve `organization_id` from user's default org when not explicitly provided (`org_resolver.py`).
- **Demo seed fix**: All demo charges now include `organization_id`.
- **Audit script**: `scripts/audit_multitenant_integrity.py` checks for NULL and invalid `organization_id` records.
- **Admin endpoint**: `GET /admin/multitenant-health` exposes multi-tenant integrity status.
- **Tests**: 289 backend tests pass. Alembic `upgrade head` works on SQLite. Single head confirmed.

## Sprint 11.1: Multi-Tenant Isolation Hardening

- **Problem**: Sprint 11 added `organization_id` columns but routers/services still filtered only by `user_id`, allowing cross-org data leakage.
- **Fix**: All org-scoped routers now inject `get_current_organization` and pass `org.id` to services. All services filter queries by `organization_id`.
- **Routers updated**: charges, analytics, customers, message_templates, collection, recurring_tasks
- **Services updated**: ChargeService, ChargeRepository, ChargeAnalyticsService, CustomerService, MessageTemplateService, CollectionService, RecurringTaskService, PendingActionService
- **Exports**: CSV/PDF exports now filter by `organization_id`. RBAC enforced (viewer cannot export).
- **WhatsApp**: Uses user's default organization. `PendingAction.organization_id` always populated.
- **Migration** `h8c9d0e1f2g3`: Backfills `organization_id` on all existing records. Creates default org for users without one. Idempotent.
- **Tests**: All test fixtures updated to create organizations and set `organization_id` on org-scoped records. 289 backend tests pass.
- **Security**: `organization_id` is the primary data boundary. No cross-org data access. Users outside org receive 403.

## Sprint 11: Multi-Tenant SaaS — Organizations, RBAC e Workspaces

- **Organization & OrganizationMember models** (`organization.py`): tabelas `organizations` e `organization_members` com roles (owner, admin, finance, viewer)
- **Migration** `g7b8c9d0e1f2`: cria tabelas de organização + adiciona `organization_id` em charges, customers, message_templates, collection_rules, collection_message_logs, recurring_tasks, pending_actions
- **OrganizationService** (`organization_service.py`): CRUD de organizações, membership, invite por email, role hierarchy, permission checking
- **RBAC** (`permissions.py`): 9 permissões mapeadas por role (view_dashboard, manage_charges, manage_customers, manage_templates, manage_collection_rules, view_analytics, export_data, manage_members, manage_settings)
- **get_current_organization dependency**: resolve organização via header `X-Organization-ID` ou fallback para org padrão do usuário
- **Organizations router** (`organizations.py`): endpoints CRUD + list/add/update/deactivate members
- **RBAC enforcement**: charges (create/cancel), analytics (export), message_templates (create/update/deactivate), collection (create/deactivate rules), recurring_tasks (create/cancel)
- **WhatsApp org context**: charges criadas via WhatsApp agora associam `organization_id` automaticamente
- **Demo mode multi-tenant**: seed cria organização padrão para demo user e associa charges
- **Frontend**: `OrganizationSection` component com switcher, info da org, lista de membros, adicionar/remover membros, criar nova org
- **Testes**: 28 novos testes backend (OrganizationService, permissions, multi-tenant isolation, cascade delete) + 2 E2E tests (org section render, members list)
- **Segurança**: isolation por organization_id, role hierarchy enforced, no sensitive financial operations

## Sprint 10: Advanced Analytics, Collection Performance e Business Insights

- **ChargeAnalyticsService** (`charge_analytics_service.py`): métricas operacionais por usuário
  - Overview: total cobrado, recebido, pendente, vencido, taxas, tempo médio de pagamento, atraso médio
  - Tendências mensais (1-12 meses)
  - Aging de vencidas em 5 faixas (1-7, 8-15, 16-30, 31-60, 60+ dias)
  - Ranking de clientes com status operacional e ações sugeridas
  - Performance da régua de cobrança (rascunhos, clientes contatados, recuperados)
  - Insights textuais em português, sem alarmismo, sem credit scoring
- **Router `/analytics`** com 8 endpoints: overview, monthly-trends, aging, customer-performance, collection-performance, insights, export.csv, export.pdf
- **WhatsApp**: 5 novos intents (analytics_overview, monthly_trends_summary, aging_summary, customer_performance_summary, collection_performance_summary)
- **Frontend**: `AdvancedAnalyticsSection.tsx` com cards, gráficos Recharts, tabela de ranking, filtros de período, exportação CSV/PDF
- **Testes**: 27 backend + 2 E2E + 1 screenshot
- **Total**: 261 backend + 27 E2E
- **Segurança**: isolamento por user_id, sem credit scoring, sem operações bancárias, QR Code sandbox

## Sprint 1: Charge Foundation

- Modelo `Charge` com campos: customer_name, customer_phone, amount, description, provider, provider_charge_id, payment_link, status, due_date
- `ChargeStatus` enum: pending, paid, cancelled, expired, failed
- `ChargeService` e `ChargeRepository` com CRUD completo
- Provider fake com geração de links de pagamento simulados
- Endpoints: `GET /charges`, `POST /charges`, `GET /charges/{id}`, `POST /charges/{id}/cancel`
- Criação de cobranças via WhatsApp com confirmação explícita (`PendingAction`)
- Envio de link de pagamento ao cliente via WhatsApp
- Notificação automática quando pagamento é confirmado via webhook

## Sprint 2: Dashboard, Reminders e Transactions

- Dashboard web com resumo financeiro (receitas, despesas, saldo)
- Gráficos por categoria com Recharts
- Lista de transações recentes
- Gerenciamento de lembretes
- Sistema de lembretes automáticos de vencimento (`ChargeReminderService`)
- `ChargeReminderLog` para auditoria de lembretes enviados
- Worker RQ para lembretes periódicos (configurável, desativado por padrão)
- `ChargeDeliveryLog` para rastrear envio de links aos clientes

## Sprint 2.1: Summary Correction

- Correção do `GET /charges/summary`: separação correta entre `pending` (não vencidas) e `overdue` (vencidas)
- `total_receivable = total_pending + total_overdue`
- `count_pending` não inclui cobranças vencidas
- Card "A Receber" do dashboard usa `total_receivable`

## Sprint 3: Mercado Pago Sandbox, CSV, Delivery

- Provider Mercado Pago sandbox com factory pattern
- `PAYFLOW_PAYMENT_PROVIDER=fake|mercado_pago` (padrão: fake)
- Webhook `POST /provider-webhooks/mercado-pago` para notificações
- Webhook `POST /provider-webhooks/fake` para provider fake
- `POST /provider-webhooks/fake/pay/{provider_charge_id}` para simular pagamento
- `ProviderEvent` model para rastrear eventos de webhook
- Exportação CSV de cobranças com filtros por status e data
- Envio de link de pagamento ao cliente via WhatsApp com confirmação

## Sprint 4: Analytics, PDF, Integration Tests

- `GET /charges/analytics` — taxa de conversão, tempo médio de pagamento, taxa de vencimento, totais por status
- Cards de analytics no dashboard (conversão, vencimento, canceladas, total pago)
- Exportação PDF com ReportLab (resumo + tabela detalhada)
- Paginação server-side de cobranças com busca e ordenação
- Testes de integração com pytest-asyncio (29 testes)
- Estados de loading, erro e vazio na tabela de cobranças

## Sprint 4.1: Filters e Date Range

- Status derivado `overdue` (cobranças vencidas permanecem `pending` no banco)
- Filtros: Todas, Pendentes, Pagas, Vencidas, Canceladas
- Date range inclusivo (`start_date` às 00:00:00, `end_date` às 23:59:59)
- Validação de status inválido retorna HTTP 400
- Exportação CSV/PDF usa mesma lógica de filtros da listagem
- `GET /charges/analytics` é visão global (não aceita filtros)

## Sprint 5: Demo Mode, Landing Page, Deploy Readiness

- Demo mode com `ENABLE_DEMO_MODE=true`
- `demo-login` endpoint para acesso sem registro
- `demo/reset` endpoint para resetar dados demo
- Seed de dados demo (`seed_demo_data.py`)
- Landing page profissional com CTAs, features, stack, roadmap
- `docker-compose.demo.yml` com stack completa (Postgres, Redis, backend, frontend, worker)
- Validação de configuração na inicialização (`security_validator.py`)
- `SECRET_KEY` requer 64+ caracteres
- Scripts: `generate_secret_key.py`, `validate_environment.py`

## Sprint 5.1: Demo Hardening

- Demo mode nunca roda em produção (app falha se `ENVIRONMENT=production` e `ENABLE_DEMO_MODE=true`)
- Demo mode exige provider fake (app falha se `ENABLE_DEMO_MODE=true` e provider != fake)
- Mercado Pago bloqueado em demo mode (factory rejeita)
- `demo-login` bloqueado em produção (HTTP 403)
- `demo/reset` com defense in depth (ambiente, flag, provider)
- Landing page com botão demo condicional (`NEXT_PUBLIC_ENABLE_DEMO_MODE`)

## Sprint 6: E2E, Observability, Rate Limiting, Webhook Hardening

- **Playwright E2E** — 10 cenários: landing, demo login, dashboard, cards, charges, filtros, busca, export
- **Sentry opcional** — `init_sentry()` com `before_send` hook para redaction
- **Audit logger** — log estruturado para eventos críticos (charge, webhook, export, demo, reminder, rate_limit)
- **User rate limiting** — Redis + fallback in-memory (charges: 20/min, exports: 10/min, demo reset: 5/hour)
- **Webhook rate limiting** — IP + provider (60/min)
- **Twilio hardening** — assinatura obrigatória em produção (403 se desativada)
- **Mercado Pago hardening** — validação de `x-signature` + `x-request-id`, idempotência via `ProviderEvent.processed`
- **Admin metrics** — `GET /admin/system-metrics` com contagens agregadas (admin-only)
- **Documentação** — `OBSERVABILITY.md`, `SECURITY_HARDENING.md`, `E2E_TESTING.md`
- **Backend tests** — 16 novos testes (rate limit, webhook, admin, Sentry)
- **CI** — job E2E manual via `workflow_dispatch`

## Sprint 6.1: E2E CI Stabilization

- **CI E2E reescrito** — sobe `docker-compose.demo.yml`, aguarda backend/frontend, roda Playwright, derruba stack
- **`scripts/wait-for-url.sh`** — script de espera por URL com timeout
- **Playwright config** — timeouts maiores, workers=1, actionTimeout/navigationTimeout
- **E2E tests reescritos** — seletores estáveis (`getByRole`, `getByPlaceholder`), login demo real, sem mock tokens
- **Dockerfile fix** — corrigidos paths de COPY (build context era `./backend` mas usava prefixo `backend/`)
- **Entrypoint fix** — respeita `command` override do docker-compose
- **Documentação** — `E2E_TESTING.md` reescrito com Option A (demo stack) e Option B (dev only)
- **README** — seções de teste atualizadas com E2E demo stack

## Sprint 8: WhatsApp Intelligence, QR Code Sandbox, OCR Assistivo e Tarefas Recorrentes

- **WhatsApp Intelligence** — 8 novos intents: list_overdue, search_charges, charge_summary, customer_charge_history, monthly_financial_summary, top_overdue_customers, create_recurring_task, list_recurring_tasks
- **FinancialQueryService** — serviço dedicado para consultas financeiras formatadas para WhatsApp
- **QR Code sandbox** — fake provider gera QR Code PNG real (base64), endpoint `GET /charges/{id}/qr-code`, modal no dashboard
- **OCR Assistivo** — `DocumentAnalysisService` com OpenAI Vision para imagens e PyPDF2 para PDFs, endpoint `POST /documents/analyze`
- **WhatsApp mídia** — webhook aceita imagens e PDFs, roteia para análise automática
- **Tarefas recorrentes** — model `RecurringTask` + `RecurringTaskLog`, service, endpoints, worker job, componente frontend
- **27 novos testes** — FinancialQueryService (10), RecurringTaskService (8), DocumentAnalysisService (7), QR Code (2)
- **Documentação** — `SPRINT_8_WHATSAPP_INTELLIGENCE.md`

## Sprint 8.1: Stabilize OCR, Twilio Media, Test Suite e Documentation Counts

- **OpenAI graceful init** — `AIService` e `DocumentAnalysisService` não crasham quando `OPENAI_API_KEY` está ausente; usam dummy key ou mock fallback
- **Twilio graceful init** — `TwilioWhatsAppService` não crasha quando `TWILIO_AUTH_TOKEN` está ausente; usa dummy token (validação de assinatura continua segura)
- **OCR mock provider** — nova config `DOCUMENT_ANALYSIS_PROVIDER` (default `mock`); imagem analysis retorna mock determinístico sem chamar OpenAI em test/demo
- **Recurring tasks admin fix** — `is_admin` inexistente substituído por checagem `ADMIN_EMAILS` (mesmo padrão do auth router)
- **30 novos testes de estabilização** — AIService init (4), Twilio init (3), OCR mock (7), QR Code sandbox (5), Recurring task isolation (5), WhatsApp media handling (6)
- **Resultado final: 174 passed, 0 failed, 0 errors**
- **Documentação** — contagens corrigidas em README, RELEASE_NOTES, SPRINT_8

## Sprint 9: Customer Intelligence, Régua de Cobrança e Templates de Mensagens

- **Customer Intelligence** — Novo modelo `Customer` com auto-criação ao gerar cobranças, score operacional dinâmico (good_payer, late_payer, frequent_late, new_customer, inactive_customer), histórico por cliente, busca e filtros
- **Message Templates** — Modelo `MessageTemplate` com tons (amigável, neutro, firme), placeholders seguros validados, bloqueio de linguagem agressiva/abusiva, templates padrão via seed, preview renderizado
- **Collection Rules** — Modelo `CollectionRule` com gatilhos (before_due, on_due, after_due), regras não enviam mensagens automaticamente, apenas preparam rascunhos
- **Collection Message Logs** — Modelo `CollectionMessageLog` rastreia todas as mensagens geradas com status (draft, pending_confirmation, sent, skipped, failed)
- **WhatsApp: 7 novas intents** — list_customers, customer_summary, generate_collection_message, prepare_overdue_followups, list_collection_rules, create_collection_rule, list_message_templates
- **Confirmação explícita** — Todas as mensagens de cobrança são rascunhos. Nenhuma é enviada sem confirmação explícita do usuário
- **Dashboard** — Nova seção "Customer Intelligence & Régua de Cobrança" com 3 abas: Clientes, Templates, Régua de Cobrança
- **PDF Export** — Seção de QR Codes (Sandbox/Demo) adicionada ao PDF de cobranças
- **60 novos testes** — CustomerService (16), MessageTemplateService (13), CollectionService (13), WhatsApp intents (11), Explicit confirmation (2), No banking operations (2), Outros (3)
- **Resultado final: 234 passed, 0 failed, 0 errors**
- **Documentação** — `SPRINT_9_CUSTOMER_INTELLIGENCE.md`

## Sprint 9.1: E2E Coverage for Customer Intelligence

- **8 novos cenários E2E** em `demo.spec.ts` cobrindo Customer Intelligence, Templates, Régua de Cobrança, QR Code sandbox, e exports
- **3 novos screenshots** em `screenshots.spec.ts`: customer-intelligence.png, message-templates.png, collection-rules.png
- **7 data-testids adicionados** — customer-intelligence-section, customers-tab, templates-tab, collection-rules-tab, customer-search-input, message-template-preview-button, qr-code-modal
- **Testes resilientes** — empty state controlado, sem seletores frágeis, fallback gracioso quando não há dados
- **Serial mode** — Sprint 9 tests (11-18) usam login compartilhado via beforeAll para reduzir carga no backend
- **Verificação de não-auto-envio** — teste E2E confirma ausência de botão "Enviar" e presença de warning de confirmação explícita
- **Total E2E: 25 testes Playwright** (18 demo + 7 screenshots)
- **Documentação** — E2E_TESTING.md e SPRINT_9 atualizados
