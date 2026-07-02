# PayFlow AI — Release Notes

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
