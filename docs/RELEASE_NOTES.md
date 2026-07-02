# PayFlow AI — Release Notes

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
