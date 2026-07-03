# 💰 PayFlow AI — Assistente Financeiro Conversacional via WhatsApp

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7+-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-559%20backend%20%2B%2036%20E2E-success)
![E2E](https://img.shields.io/badge/E2E-Playwright-orange?logo=playwright&logoColor=white)

SaaS financeiro conversacional para gestão de cobranças via WhatsApp com dashboard web. IA processa linguagem natural, cria cobranças, envia links de pagamento e acompanha recebimentos — com confirmação explícita do usuário em cada operação.

---

## O que é

PayFlow AI é um assistente de cobranças que opera via WhatsApp, permitindo que autônomos, MEIs e pequenos negócios criem cobranças, enviem links de pagamento e acompanhem recebimentos sem precisar de um app financeiro complexo.

## Problema

Autônomos e MEIs precisam de uma forma simples de cobrar clientes. Soluções existentes são complexas, exigem apps dedicados e não aproveitam o canal onde o pequeno negócio já está: o WhatsApp.

## Solução

- **WhatsApp → IA → Cobrança**: usuário envia mensagem natural, IA propõe cobrança, usuário confirma, sistema cria cobrança e envia link ao cliente
- **Consultas financeiras via WhatsApp**: listar vencidas, buscar por cliente, resumo mensal, top devedores
- **QR Code sandbox**: cada cobrança gera QR Code fake para demonstração (não é Pix real)
- **OCR assistivo**: envie foto de boleto/recibo, IA extrai dados e sugere lembrete
- **Tarefas recorrentes**: lembretes automáticos diários/semanais/mensais via WhatsApp
- **Dashboard web**: listagem paginada com filtros, analytics, QR Code modal, exportação CSV/PDF
- **Lembretes automáticos**: scheduler periódico identifica cobranças vencidas e envia lembretes via WhatsApp
- **Webhooks**: provider notifica pagamento, sistema atualiza status e notifica usuário

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.11+, FastAPI (async), SQLAlchemy 2.0, Pydantic |
| Frontend | Next.js 16, TypeScript, TailwindCSS, Lucide React |
| Database | PostgreSQL 17, Alembic (migrations) |
| Cache/Queue | Redis 7+, RQ (workers assíncronos) |
| IA | OpenAI GPT-4o (NLP, classificação de intenção) |
| Mensageria | Twilio WhatsApp Business API |
| Pagamentos | Provider fake (padrão) / Mercado Pago sandbox (opt-in) |
| PDF | ReportLab |
| Infra | Docker Compose |
| Testes | pytest (117 testes), Playwright E2E (10 cenários) |

## Como rodar demo

```bash
# Docker Compose demo (recomendado)
docker-compose -f docker-compose.demo.yml up --build

# Acesse:
# Frontend: http://localhost:3001
# Backend:  http://localhost:8001/docs
# Login:    Clique em "Entrar como Demo"
```

## Como rodar testes

```bash
# Backend
cd backend
source .venv/bin/activate
pytest -v tests

# Frontend build
cd frontend
npm run build

# E2E (full demo stack)
docker-compose -f docker-compose.demo.yml up -d --build
./scripts/wait-for-url.sh http://localhost:8001/health/ready 120
./scripts/wait-for-url.sh http://localhost:3001 120
cd frontend && E2E_BASE_URL=http://localhost:3001 npm run test:e2e
cd .. && docker-compose -f docker-compose.demo.yml down -v

# E2E (frontend dev only — sem backend)
cd frontend
npm run test:e2e
```

## Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  WhatsApp   │────→│   Twilio     │────→│   FastAPI     │
│  (Cliente)  │     │   Webhook    │     │   Backend     │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                 │
                    ┌──────────────┐     ┌───────┴───────┐
                    │   OpenAI     │←───→│   AI Service  │
                    │   GPT-4o     │     └───────┬───────┘
                    └──────────────┘             │
                    ┌──────────────┐     ┌───────┴───────┐
                    │  PostgreSQL  │←───→│  SQLAlchemy   │
                    │              │     │  (async)      │
                    └──────────────┘     └───────┬───────┘
                                                 │
                    ┌──────────────┐     ┌───────┴───────┐
                    │    Redis     │←───→│  RQ Workers   │
                    │  (cache/rl)  │     │  (reminders)  │
                    └──────────────┘     └───────────────┘
                                                 │
                    ┌──────────────┐     ┌───────┴───────┐
                    │  Next.js     │←───→│   Frontend    │
                    │  TypeScript  │     │   Dashboard   │
                    └──────────────┘     └───────────────┘
```

**Camadas do backend**: Routers → Services → Repositories → Models

- **Providers**: camada desacoplada de provedores de pagamento (fake, mercado_pago) com factory pattern
- **Integrations**: Twilio, OpenAI, Mercado Pago SDK
- Ver `docs/ARCHITECTURE.md` e `docs/CASE_STUDY.md` para detalhes

## Segurança

- **Provider padrão é `fake`** — nenhuma cobrança real é processada sem opt-in explícito
- **Mercado Pago sandbox** apenas com credenciais explícitas
- **Confirmação explícita** do usuário antes de qualquer cobrança
- **JWT auth**, rate limiting (Redis + fallback), security headers
- **Demo mode nunca roda em produção** — app falha na inicialização se `ENVIRONMENT=production` e `ENABLE_DEMO_MODE=true`
- **Demo mode exige provider fake** — app falha se `ENABLE_DEMO_MODE=true` e provider != fake
- **Mercado Pago bloqueado em demo mode** — factory rejeita
- **Webhook hardening** — validação de assinatura Twilio (obrigatória em prod), Mercado Pago `x-signature` + idempotência
- **Audit logging** estruturado com sanitização de dados sensíveis
- **Sentry opcional** com `before_send` hook para redaction
- **Sem Pix Out, sem saque, sem conta digital, sem BaaS, sem Open Finance**
- Segredos via `.env`, nunca commitados

## Screenshots

![Landing](docs/assets/landing.png)
![Login Demo](docs/assets/login-demo.png)
![Dashboard](docs/assets/dashboard-overview.png)
![Charges Table](docs/assets/charges-table.png)
![Analytics](docs/assets/analytics.png)
![Export](docs/assets/export-pdf.png)

### E2E Report

![E2E Report](docs/assets/e2e-report.png)

> Screenshots gerados via `npx playwright test e2e/screenshots.spec.ts` contra a demo stack.

## Documentação

| Documento | Descrição |
|---|---|
| [Case Study](docs/CASE_STUDY.md) | Case study técnico completo |
| [Release Notes](docs/RELEASE_NOTES.md) | Release notes por sprint |
| [Release Candidate Checklist](docs/RELEASE_CANDIDATE_CHECKLIST.md) | Checklist de release candidate |
| [Publication Checklist](docs/PUBLICATION_CHECKLIST.md) | Checklist final de publicação |
| [Architecture](docs/ARCHITECTURE.md) | Arquitetura detalhada |
| [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) | Guia de deploy |
| [E2E Testing](docs/E2E_TESTING.md) | Guia de testes E2E |
| [Observability](docs/OBSERVABILITY.md) | Sentry, audit logging, admin metrics |
| [Security Hardening](docs/SECURITY_HARDENING.md) | Demo mode, rate limiting, webhook hardening |
| [LinkedIn Launch Post](docs/LINKEDIN_LAUNCH_POST.md) | Post LinkedIn para lançamento |
| [Demo Video Script](docs/DEMO_VIDEO_SCRIPT.md) | Roteiro de vídeo demo |
| [Sprint 8 — WhatsApp Intelligence](docs/SPRINT_8_WHATSAPP_INTELLIGENCE.md) | QR Code sandbox, OCR assistivo, tarefas recorrentes |

## Limitações conscientes

- **Não é uma instituição financeira** — não oferece conta digital, Pix Out, saque ou pagamento de boletos
- **Provider fake é o padrão** — sandbox segura, sem cobranças reais
- **Mercado Pago é opt-in** — requer credenciais sandbox explícitas
- **Twilio WhatsApp Sandbox** — requer código de join para testes
- **OpenAI API key** — necessária para funcionalidade de IA
- **Demo mode** — desativado por padrão, nunca em produção

## Roadmap

- [x] Sprint 1-2: Transações, cobranças, dashboard, lembretes
- [x] Sprint 3-4: Mercado Pago sandbox, analytics, PDF, testes de integração
- [x] Sprint 5-5.1: Demo mode, landing page, hardening de segurança
- [x] Sprint 6-6.1: E2E, observabilidade, rate limiting, webhook hardening, CI stabilization
- [x] Sprint 7: Portfolio polish, case study, screenshots, release candidate
- [x] Sprint 8: WhatsApp Intelligence, QR Code sandbox, OCR assistivo, tarefas recorrentes
- [x] Sprint 9-9.1: Customer intelligence, collection playbooks, E2E coverage
- [x] Sprint 11-11.2: Multi-tenant workspaces, RBAC, migration portability
- [x] Sprint 12-12.1: SaaS billing, plans, usage limits, billing hardening
- [x] Sprint 13: Jota parity blueprint & regulated provider architecture
- [x] Sprint 14: Provider foundation, consent, audit logs & transaction auth
- [x] Sprint 15: Asaas sandbox charge provider (Pix, boleto, payment links, webhooks)
- [x] Sprint 16: Open Finance read provider foundation (fake/sandbox — saldo, extrato, transações, categorias)
- [ ] Sprint 17: DDA e contas a pagar
- [ ] Sprint 18: Payment initiation sandbox
- [ ] Sprint 19: KYC/KYB (Unico — biometria, onboarding)
- [ ] Sprint 20+: BaaS/Pix Out real (parceiro regulado)

## Roadmap to Jota-level Parity

O PayFlow AI não será lançado publicamente até atingir paridade funcional percebida com o [Jota](https://jota.ai). Veja a documentação completa em:

- [`docs/COMPETITOR_JOTA_RESEARCH.md`](docs/COMPETITOR_JOTA_RESEARCH.md) — Pesquisa funcional do Jota
- [`docs/JOTA_PARITY_MATRIX.md`](docs/JOTA_PARITY_MATRIX.md) — Matriz Jota vs PayFlow (40 funcionalidades)
- [`docs/REGULATED_PROVIDER_ARCHITECTURE.md`](docs/REGULATED_PROVIDER_ARCHITECTURE.md) — Arquitetura de providers regulados
- [`docs/JOTA_PARITY_ROADMAP.md`](docs/JOTA_PARITY_ROADMAP.md) — Roadmap de 7 fases (4-5 meses)
- [`docs/CONSENT_AND_AUTHORIZATION_MODEL.md`](docs/CONSENT_AND_AUTHORIZATION_MODEL.md) — Modelo de consentimento
- [`docs/WHATSAPP_JOTA_PARITY_COMMANDS.md`](docs/WHATSAPP_JOTA_PARITY_COMMANDS.md) — Comandos WhatsApp mapeados
- [`docs/FUTURE_FINTECH_DATA_MODEL.md`](docs/FUTURE_FINTECH_DATA_MODEL.md) — Modelo de dados fintech futuro

### Funcionalidades prontas
- IA conversacional no WhatsApp (texto, áudio, imagem)
- Cobranças sandbox com QR Code fake
- Asaas sandbox: Pix, boleto e link de pagamento (opt-in)
- Webhooks Asaas com idempotência e validação de token
- Reconciliação manual de status de cobrança
- Dashboard web com analytics
- Multi-tenant com RBAC (owner/admin/finance/viewer)
- SaaS billing com planos e limites
- Templates de mensagem, regras de cobrança, collection intelligence
- Lembretes e tarefas recorrentes
- OCR de documentos
- 559 testes backend + 36 E2E

### Funcionalidades sandbox (prontas, aguardando provider real)
- Cobrança Pix (QR Code simulado)
- Webhook de recebimento (simulado)
- Provider factory com feature flags
- Provider connection registry (fake/sandbox)
- Open Finance consent (fake)
- Open Finance read: saldo, extrato, transações, categorias (fake/demo)
- Transaction authorization (6-digit challenge, hashed)
- Audit logs com IP/user-agent hasheados
- Webhook idempotency com sanitização

### Funcionalidades futuras com parceiros regulados
- **Conta digital** (BaaS — Celcoin/QI Tech)
- **Pix Out** (envio de dinheiro — Celcoin/QI Tech)
- **Pagamento de boletos** (Celcoin/QI Tech)
- **Open Finance** (saldo, extrato — Pluggy/Belvo)
- **DDA** (detecção automática de boletos — Celcoin/Dock)
- **KYC/KYB** (biometria facial — Unico)
- **Rendimento automático** (100% CDI — BaaS)

### Disclaimer de segurança
- O PayFlow AI é um **orquestrador, interface e camada de IA**.
- Liquidação financeira, Open Finance real, Pix Out, conta digital e KYC **dependem de parceiros regulados**.
- Nenhuma operação regulada é implementada diretamente no código.
- Todos os providers regulados têm feature flags (`false` por padrão).
- Provider padrão é sempre fake/sandbox.
- Demo mode força fake providers.

## � Como Testar o WhatsApp

**Número para iniciar conversa**: `+1 415 523 8886` (Twilio Sandbox)

**Passos para começar:**
1. Adicione o número `+1 415 523 8886` nos seus contatos
2. Envie uma mensagem no WhatsApp com o código: `join <seu-codigo-sandbox>`
3. Aguarde a confirmação do Twilio
4. Comece a usar! Exemplos:
   - "Gastei R$ 50 com almoço"
   - "Qual meu saldo?"
   - "Mostre minhas transações"
   - "Gere uma cobrança de R$ 150 para João referente ao serviço do site"

> **Nota**: Este é o número do Twilio WhatsApp Sandbox para desenvolvimento. Em produção, você terá seu próprio número aprovado.

## � Tecnologias

### Backend
- **Python 3.11+** com FastAPI
- **PostgreSQL** para banco de dados
- **Redis** para cache
- **SQLAlchemy 2.0** (async)
- **Alembic** para migrações
- **OpenAI GPT-4o** para NLP e classificação de intenções
- **Twilio** para integração WhatsApp
- **JWT** para autenticação
- **Pydantic** para validação

### Frontend
- **Next.js 14** com TypeScript
- **TailwindCSS** para estilização
- **Lucide React** para ícones
- **Axios** para requisições HTTP

### Infraestrutura
- **Docker** e **Docker Compose**
- Preparado para deploy em AWS/Cloud

## 📋 Funcionalidades

### Via WhatsApp
- ✅ Registro de despesas com linguagem natural
- ✅ Registro de receitas
- ✅ Criação de lembretes/compromissos
- ✅ Consulta de saldo e relatórios
- ✅ Listagem de transações recentes
- ✅ Criação de cobranças com confirmação explícita do usuário
- ✅ Criação de cobranças com vencimento ("com vencimento amanhã", "vence dia 15")
- ✅ Listagem de cobranças com resumo e totais
- ✅ Filtro de cobranças por status (pendentes, pagas)
- ✅ Cancelamento de cobranças via WhatsApp ("cancela a cobrança do João")
- ✅ Notificação automática quando um pagamento é confirmado
- ✅ Lembretes automáticos de vencimento e cobranças vencidas
- ✅ Worker automático de lembretes via RQ (configurável, desativado por padrão)
- ✅ Exportação de cobranças em CSV (com filtros por status e data)
- ✅ Exportação de cobranças em PDF (com filtros, resumo e tabela detalhada)
- ✅ Analytics de cobranças (taxa de conversão, tempo médio de pagamento, taxa de vencimento)
- ✅ Paginação server-side de cobranças com busca e ordenação
- ✅ Envio de link de pagamento para o cliente via WhatsApp (com confirmação)
- ✅ Provider Mercado Pago sandbox (opcional, padrão continua fake)
- ✅ IA que entende português informal

### Dashboard Web
- ✅ Autenticação segura (JWT)
- ✅ Visualização de receitas, despesas e saldo
- ✅ Gráficos por categoria
- ✅ Lista de transações recentes
- ✅ Gerenciamento de lembretes
- ✅ Relatórios mensais
- ✅ Cards de resumo de cobranças (a receber, recebido, pendentes, vencidas)
- ✅ Tabela de cobranças com filtros por status (todas, pendentes, pagas, vencidas, canceladas)
- ✅ Copiar link de pagamento e cancelar cobranças pendentes diretamente do dashboard
- ✅ Botão de exportação CSV de cobranças (respeita filtro atual)
- ✅ Botão de exportação PDF de cobranças (com resumo e tabela detalhada)
- ✅ Cards de analytics (taxa de conversão, tempo médio de pagamento, total criado/pago, taxa de vencimento, canceladas)
- ✅ Paginação de cobranças com busca por cliente/descrição
- ✅ Estados de loading, erro e vazio na tabela de cobranças
- ✅ Interface moderna e responsiva

## 🏗️ Arquitetura

```
backend/
├── app/
│   ├── core/           # Configurações, database, segurança
│   ├── models/         # Modelos SQLAlchemy (User, Charge, PendingAction, ProviderEvent, ChargeReminderLog, ChargeDeliveryLog, etc.)
│   ├── schemas/        # Schemas Pydantic
│   ├── repositories/   # Camada de acesso a dados
│   ├── services/       # Lógica de negócio (AIService, ChargeService, PendingActionService, ChargeReminderService)
│   ├── routers/        # Endpoints da API
│   ├── providers/      # Camada desacoplada de provedores de pagamento (fake, mercado_pago)
│   ├── integrations/   # Twilio, OpenAI, Mercado Pago
│   ├── utils/          # Utilitários
│   └── main.py         # Aplicação FastAPI
├── migrations/         # Migrações Alembic
├── Dockerfile
└── requirements.txt

frontend/
├── pages/              # Páginas Next.js
├── components/         # Componentes React
├── services/           # API client
├── styles/             # CSS global
└── package.json
```

## 🔧 Instalação e Configuração

### 1. Pré-requisitos
- Docker e Docker Compose instalados
- Conta Twilio com WhatsApp API
- Chave API OpenAI
- (Opcional) Conta Stripe para pagamentos

### 2. Configurar Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

**Gerar SECRET_KEY segura** (IMPORTANTE):

```bash
# Use o script fornecido
python scripts/generate_secret_key.py

# Ou gere manualmente
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Edite o arquivo `.env` com suas credenciais:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/financial_assistant
REDIS_URL=redis://redis:6379/0

# Security - IMPORTANTE: Use uma chave de 64+ caracteres
SECRET_KEY=sua-secret-key-gerada-com-64-ou-mais-caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=seu_twilio_account_sid
TWILIO_AUTH_TOKEN=seu_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# OpenAI
OPENAI_API_KEY=sua_openai_api_key
OPENAI_MODEL=gpt-4o

# Ngrok (para desenvolvimento local)
NGROK_AUTHTOKEN=seu_ngrok_authtoken

# Stripe (opcional)
STRIPE_SECRET_KEY=sua_stripe_secret_key
STRIPE_WEBHOOK_SECRET=seu_stripe_webhook_secret

# Mercado Pago (opcional, sandbox por padrão)
MERCADO_PAGO_ACCESS_TOKEN=seu_mercado_pago_access_token
MERCADO_PAGO_PUBLIC_KEY=seu_mercado_pago_public_key

# PayFlow AI - provedor de pagamento: fake | mercado_pago
# Padrão é fake (sandbox/seguro). Use mercado_pago apenas com credenciais sandbox.
PAYFLOW_PAYMENT_PROVIDER=fake

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**Validar configuração** (recomendado):

```bash
python scripts/validate_environment.py
```

### 3. Iniciar o Projeto

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down
```

Os serviços estarão disponíveis em:
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **Ngrok Dashboard**: http://localhost:4040
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

**Verificar saúde dos serviços:**

```bash
# Backend
curl http://localhost:8000/health

# Ver URL pública do Ngrok
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'

# PostgreSQL
docker-compose exec postgres pg_isready -U postgres

# Redis
docker-compose exec redis redis-cli ping
```

### 4. Documentação da API

Acesse a documentação interativa:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints de Cobrança (PayFlow AI)

- `GET /charges` - Lista cobranças paginadas (page, page_size, status, search, start_date, end_date, sort_by, sort_order)
- `GET /charges/summary` - Resumo estatístico (totais a receber, recebido, vencido, contagens)
- `GET /charges/analytics` - Analytics de cobranças (taxa de conversão, tempo médio de pagamento, taxa de vencimento, totais por status)
- `POST /charges` - Cria uma nova cobrança (gera link de pagamento no provedor configurado)
- `GET /charges/{id}` - Detalhes de uma cobrança
- `POST /charges/{id}/cancel` - Cancela uma cobrança pendente
- `POST /charges/reminders/run` - Dispara lembretes de vencimento manualmente (dev apenas)
- `GET /charges/export.csv` - Exporta cobranças do usuário em CSV (filtros por status, data, busca)
- `GET /charges/export.pdf` - Exporta cobranças em PDF com resumo e tabela detalhada (filtros por status, data, busca)

#### Campos do `GET /charges/summary`

| Campo | Descrição |
| --- | --- |
| `total_pending` | Soma de cobranças `pending` **não vencidas** (due_date null ou due_date >= hoje) |
| `total_overdue` | Soma de cobranças `pending` **vencidas** (due_date < hoje) |
| `total_receivable` | Soma de `total_pending + total_overdue` (tudo a receber) |
| `total_paid` | Soma de cobranças `paid` |
| `count_pending` | Quantidade de pendentes não vencidas |
| `count_overdue` | Quantidade de pendentes vencidas |
| `count_paid` | Quantidade de pagas |
| `count_cancelled` | Quantidade de canceladas |

> **Regra:** cobranças vencidas não entram em `total_pending` ou `count_pending`. O card "A Receber" do dashboard usa `total_receivable` para mostrar o total completo (pendentes + vencidas).

#### Filtros de Status (Listagem, CSV e PDF)

O parâmetro `status` aceita os seguintes valores:

| Valor | Descrição | Regra de Filtro |
| --- | --- | --- |
| `pending` | Pendentes não vencidas | `status = PENDING AND (due_date IS NULL OR due_date >= today)` |
| `overdue` | Vencidas (status derivado) | `status = PENDING AND due_date IS NOT NULL AND due_date < today` |
| `paid` | Pagas | `status = PAID` |
| `cancelled` | Canceladas | `status = CANCELLED` |
| `expired` | Expiradas | `status = EXPIRED` |
| `failed` | Falhadas | `status = FAILED` |

> **Importante:**
> - `overdue` não é um valor real do enum `ChargeStatus` — é um **status derivado**. Uma cobrança vencida permanece como `pending` no banco, mas com `due_date < hoje`.
> - `pending` **não inclui** cobranças vencidas. Para ver todas as pendentes (incluindo vencidas), não use filtro de status.
> - `receivable = pending + overdue` (total a receber).
> - Status inválido retorna **HTTP 400** com mensagem de erro.
> - Os endpoints `GET /charges/export.csv` e `GET /charges/export.pdf` usam **a mesma lógica de filtros** da listagem.
> - Filtros de data (`start_date`, `end_date`) são **inclusivos** — `start_date` começa às 00:00:00 e `end_date` vai até 23:59:59.999999.
> - `GET /charges/analytics` é uma **visão global** do usuário — não aceita filtros de status, data ou busca.

### Webhooks de Provedores

- `POST /provider-webhooks/fake` - Recebe eventos do provedor fake (sandbox)
- `POST /provider-webhooks/fake/pay/{provider_charge_id}` - Simula pagamento de uma cobrança fake (apenas development/testing)
- `POST /provider-webhooks/mercado-pago` - Recebe notificações do Mercado Pago para cobranças

## 📱 Configurar Webhook do Twilio

**Para desenvolvimento local**, o projeto já inclui Ngrok configurado no Docker Compose!

1. Após iniciar o projeto, obtenha a URL pública do Ngrok:
   ```bash
   # Ver no dashboard
   open http://localhost:4040
   
   # Ou via API
   curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'
   ```

2. Acesse o [Console Twilio](https://console.twilio.com/)

3. Vá em **Messaging** > **Settings** > **WhatsApp Sandbox**

4. Configure o webhook:
   - **URL**: `https://sua-url-ngrok.ngrok-free.app/webhook/whatsapp`
   - **Método**: POST
   - **Status Callback**: (opcional) mesma URL com `/status`

5. Salve as configurações

6. Teste enviando uma mensagem para o número do Twilio Sandbox

> **Nota**: A URL do Ngrok muda a cada reinicialização. Configure o `NGROK_AUTHTOKEN` no `.env` para URLs persistentes.

## 💬 Exemplos de Uso via WhatsApp

### Registrar Despesa
```
Gastei R$ 50 com almoço
Paguei 120 reais no uber
Comprei remédio por R$ 35,50
```

### Registrar Receita
```
Recebi R$ 3000 de salário
Ganhei 500 reais de freela
```

### Criar Lembrete
```
Lembrar de pagar conta amanhã
Me lembre de ligar pro médico segunda
```

### Consultar Saldo
```
Quanto gastei esse mês?
Qual meu saldo?
Mostre meu resumo financeiro
```

### Ver Transações
```
Mostre minhas últimas transações
Quais foram meus gastos?
```

### Criar Cobrança (PayFlow AI)
```
Gere uma cobrança de R$ 150 para João referente ao serviço do site
Crie um link de pagamento de R$ 89,90 para Maria
Quero cobrar R$ 300 do cliente Pedro
```

O assistente confirmará os dados e pedirá confirmação antes de gerar o link de pagamento. Responda `sim` ou `confirmo` para prosseguir.

### Listar e Consultar Cobranças
```
Mostre minhas cobranças
Alguma cobrança foi paga?
```

## 🗄️ Modelos de Dados

### User
- id, name, email, hashed_password, phone_number, created_at

### Subscription
- id, user_id, plan, status, stripe_customer_id

### Transaction
- id, user_id, type (income/expense), amount, category, description, date

### Reminder
- id, user_id, title, due_date, completed

### ConversationLog
- id, user_id, message, role (user/system/assistant), created_at

### Charge (PayFlow AI)
- id, user_id, customer_name, customer_phone, amount, description, provider, provider_charge_id, payment_link, status, due_date, paid_at, created_at, updated_at

### PendingAction (PayFlow AI)
- id, user_id, action_type, payload, status, expires_at, confirmed_at, executed_at, created_at

### ProviderEvent (PayFlow AI)
- id, provider, event_type, external_id, payload, processed, created_at, processed_at

## 🔐 Segurança

- ✅ Senhas hasheadas com bcrypt
- ✅ Autenticação JWT
- ✅ Validação de webhook Twilio
- ✅ Rate limiting
- ✅ CORS configurado
- ✅ Validação de dados com Pydantic
- ✅ SQL injection protection (SQLAlchemy)
- ✅ Confirmação explícita do usuário antes de criar cobranças (PayFlow AI)
- ✅ Provedor de pagamento padrão fake/sandbox (PayFlow AI)
- ✅ Nenhuma operação de Pix Out, boleto pagamento ou saque implementada (PayFlow AI)

## 🚀 Deploy em Produção

### Preparação

1. **Configurar variáveis de ambiente de produção**
2. **Usar banco PostgreSQL gerenciado** (AWS RDS, DigitalOcean, etc)
3. **Usar Redis gerenciado** (AWS ElastiCache, Redis Cloud)
4. **Configurar HTTPS** (obrigatório para webhook Twilio)
5. **Configurar domínio personalizado**

### Deploy Backend (AWS EC2 exemplo)

```bash
# Conectar ao servidor
ssh usuario@seu-servidor

# Clonar repositório
git clone seu-repositorio
cd seu-repositorio

# Configurar .env
nano .env

# Iniciar com Docker
docker-compose -f docker-compose.prod.yml up -d
```

### Deploy Frontend (Vercel/Netlify)

```bash
cd frontend
npm install
npm run build

# Deploy automático via Git
# Ou manual:
vercel deploy --prod
```

## 📊 Monitoramento

### Logs

```bash
# Ver logs do backend
docker-compose logs -f backend

# Ver logs do PostgreSQL
docker-compose logs -f postgres

# Ver logs do Redis
docker-compose logs -f redis
```

### Health Check

```bash
curl http://localhost:8000/health
```

## 🧪 Testes

```bash
# Backend
cd backend
source .venv/bin/activate
pytest -v tests

# Frontend build
cd frontend
npm run build

# E2E com demo stack (recomendado)
docker-compose -f docker-compose.demo.yml up -d --build
./scripts/wait-for-url.sh http://localhost:8001/health/ready 120
./scripts/wait-for-url.sh http://localhost:3001 120
cd frontend && E2E_BASE_URL=http://localhost:3001 npm run test:e2e
cd .. && docker-compose -f docker-compose.demo.yml down -v

# E2E frontend dev only (sem backend, mock tokens)
cd frontend && npm run test:e2e
```

Veja `docs/E2E_TESTING.md` para detalhes completos.

## 📈 Escalabilidade

O sistema foi projetado para escalar:

- **Async/await** em todo backend
- **Connection pooling** no PostgreSQL
- **Redis** para cache e rate limiting
- **Stateless** (pode rodar múltiplas instâncias)
- **Separação de camadas** (fácil microservices)

## � Scripts Utilitários

O projeto inclui scripts para facilitar o desenvolvimento:

### Gerar SECRET_KEY Segura
```bash
python scripts/generate_secret_key.py
```

### Validar Configuração do Ambiente
```bash
python scripts/validate_environment.py
```

## ✅ Correções Recentes Aplicadas

### Migration do PaymentMethod (Fev 2026)
- ✅ Corrigido erro: `invalid input value for enum paymentmethod`
- ✅ Migration agora é idempotente (pode ser executada múltiplas vezes)
- ✅ Usa blocos `DO $$ BEGIN ... EXCEPTION` do PostgreSQL

### Segurança
- ✅ SECRET_KEY agora requer 64+ caracteres
- ✅ Validação aprimorada na inicialização
- ✅ Scripts utilitários para geração de chaves seguras

**Documentação completa das correções**: Ver `MIGRATION_FIX.md` e `QUICK_START.md`

## �🛠️ Desenvolvimento

### Adicionar nova funcionalidade

1. Criar modelo em `backend/app/models/`
2. Criar schema em `backend/app/schemas/`
3. Criar repository em `backend/app/repositories/`
4. Criar service em `backend/app/services/`
5. Criar router em `backend/app/routers/`
6. Registrar router em `backend/app/main.py`

### Criar migração

```bash
docker-compose exec backend alembic revision --autogenerate -m "descrição"
docker-compose exec backend alembic upgrade head
```

### Troubleshooting

**Backend não inicia:**
```bash
# Ver logs completos
docker-compose logs backend --tail=100

# Verificar conectividade com PostgreSQL
docker-compose exec postgres pg_isready

# Verificar variáveis de ambiente
docker-compose exec backend env | grep -E "(DATABASE|SECRET|REDIS)"
```

**Erro na Migration:**
```bash
# Ver status atual
docker-compose exec backend alembic current

# Reverter e reaplicar
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head
```

**Ngrok não conecta:**
```bash
# Verificar se backend está rodando
curl http://localhost:8000/health

# Ver logs do Ngrok
docker-compose logs ngrok

# Verificar token no .env
grep NGROK_AUTHTOKEN .env
```

## 📝 Licença

Este projeto é proprietário. Todos os direitos reservados.

## 🤝 Suporte

Para suporte, entre em contato via:
- Email: suporte@seudominio.com
- WhatsApp: +55 11 99999-9999

---

**Desenvolvido com ❤️ usando Python, FastAPI, Next.js e OpenAI**
