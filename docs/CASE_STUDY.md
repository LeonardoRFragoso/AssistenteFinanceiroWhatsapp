# PayFlow AI — Case Study Técnico

## Contexto

PayFlow AI é um SaaS financeiro conversacional que combina inteligência artificial, WhatsApp e um dashboard web para gestão de cobranças. O projeto foi desenvolvido como uma evolução iterativa por sprints, partindo de um assistente financeiro básico via WhatsApp e crescendo até um sistema robusto com observabilidade, testes E2E e hardening de segurança.

Este documento posiciona o projeto para avaliação técnica, recrutadores e portfólio.

## Problema

Autônomos, MEIs e pequenos negócios precisam de uma forma simples de cobrar clientes e acompanhar pagamentos. Soluções existentes são complexas, exigem apps dedicados ou não aproveitam o canal onde o pequeno negócio já está: o WhatsApp.

Desafios específicos:
- Criar cobranças sem conhecimento técnico
- Enviar links de pagamento diretamente ao cliente
- Acompanhar status (pendente, pago, vencido) sem planilhas
- Receber lembretes automáticos de vencimento
- Exportar dados para contabilidade
- Tudo via conversa natural em português

## Solução

PayFlow AI resolve isso com três pilares:

1. **Assistente conversacional via WhatsApp** — IA (OpenAI GPT-4o) processa linguagem natural, propõe cobranças, exige confirmação explícita e envia links de pagamento ao cliente
2. **Dashboard web** — Visualização de cobranças com filtros, analytics, exportação CSV/PDF e gestão completa
3. **Workers assíncronos** — Lembretes automáticos de vencimento via Redis + RQ

## Principais fluxos

### Fluxo 1: WhatsApp → IA → Cobrança

```
Usuário envia: "Cobre R$ 150 do João pelo serviço de design"
    ↓
IA classifica intenção → PendingAction (charge_create)
    ↓
Sistema propõe: "Confirme: cobrança de R$ 150 para João — serviço de design"
    ↓
Usuário confirma: "sim"
    ↓
ChargeService cria cobrança no provider (fake/mercado_pago)
    ↓
Sistema envia link de pagamento ao cliente via WhatsApp
    ↓
Sistema confirma: "Cobrança criada! Link enviado para João."
```

### Fluxo 2: Webhook → Pagamento confirmado

```
Provider notifica webhook (fake/mercado_pago)
    ↓
Sistema valida assinatura (x-signature)
    ↓
Sistema verifica idempotência (ProviderEvent.processed)
    ↓
Charge atualizada para status=paid
    ↓
Usuário notificado via WhatsApp: "Pagamento de R$ 150 recebido de João!"
```

### Fluxo 3: Lembretes automáticos

```
Worker periódico (RQ) verifica cobranças vencidas/próximas
    ↓
Para cada cobrança elegível:
    → Registra ChargeReminderLog
    → Envia lembrete via WhatsApp ao usuário
    → Registra ChargeDeliveryLog
```

### Fluxo 4: Dashboard com filtros e exportação

```
Usuário acessa /dashboard
    ↓
Frontend carrega: summary, analytics, charges (paginado)
    ↓
Filtros: Todas | Pendentes | Pagas | Vencidas | Canceladas
    ↓
Busca por cliente/descrição
    ↓
Exportação: CSV (com filtros) ou PDF (com resumo + tabela)
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

### Camadas do backend

- **Routers** — Endpoints REST, validação de entrada, rate limiting
- **Services** — Lógica de negócio (ChargeService, AIService, PendingActionService, ChargeReminderService)
- **Repositories** — Acesso a dados via SQLAlchemy 2.0 async
- **Models** — Modelos ORM (User, Charge, PendingAction, ProviderEvent, ChargeReminderLog, ChargeDeliveryLog, Subscription, Transaction, Reminder, ConversationLog)
- **Providers** — Camada desacoplada de provedores de pagamento (fake, mercado_pago) com factory pattern
- **Integrations** — Twilio, OpenAI, Mercado Pago SDK

## Decisões técnicas

### Por que FastAPI + async?

FastAPI oferece tipagem nativa, documentação automática (Swagger/ReDoc), validação via Pydantic e suporte async nativo. O backend é totalmente async (SQLAlchemy 2.0 async, asyncpg), permitindo alto throughput com I/O bound operations (WhatsApp, OpenAI, PostgreSQL).

### Por que SQLAlchemy 2.0 async?

Permite queries não-bloqueantes com PostgreSQL, essencial para um sistema que faz múltiplas chamadas externas (OpenAI, Twilio, provider) por requisição.

### Por que Redis + RQ para workers?

Lembretes de vencimento são periódicos e não devem bloquear requisições HTTP. RQ é simples, confiável e integra naturalmente com Redis (já usado para rate limiting e cache).

### Por que provider factory pattern?

Desacopla a lógica de cobrança do provedor específico. Permite trocar entre `fake` (sandbox) e `mercado_pago` (sandbox/produção) via variável de ambiente, sem mudar código.

### Por que PendingAction com confirmação explícita?

Toda cobrança exige confirmação do usuário antes de ser executada. Isso previne cobranças indesejadas e dá transparência ao processo. O PendingAction tem TTL (expira se não confirmado).

### Por que status derivado "overdue"?

Cobranças vencidas permanecem como `pending` no banco (pois ainda podem ser pagas), mas o sistema deriva o status `overdue` quando `due_date < hoje`. Isso evita migrações de status e mantém o modelo simples.

## Segurança

### Por configuração

- **Provider padrão é `fake`** — nenhuma cobrança real é processada sem opt-in explícito
- **Mercado Pago é opt-in** — requer `PAYFLOW_PAYMENT_PROVIDER=mercado_pago` + credenciais sandbox
- **Demo mode nunca roda em produção** — app falha na inicialização se `ENVIRONMENT=production` e `ENABLE_DEMO_MODE=true`
- **Demo mode exige provider fake** — app falha se `ENABLE_DEMO_MODE=true` e provider não for `fake`
- **Mercado Pago bloqueado em demo mode** — factory rejeita `mercado_pago` quando demo ativo

### Por implementação

- JWT auth com expiração
- Rate limiting por usuário (Redis + fallback in-memory)
- Rate limiting por IP para webhooks
- Validação de assinatura Twilio (obrigatória em produção)
- Validação de assinatura Mercado Pago (x-signature + x-request-id)
- Idempotência de webhooks via ProviderEvent.processed
- Confirmação explícita para todas as cobranças
- Sanitização de logs (sem tokens, senhas, payloads completos)
- Sentry com before_send hook (redaction de dados sensíveis)
- Security headers, CORS configurado
- SECRET_KEY requer 64+ caracteres

### O que NÃO existe

- **Sem Pix Out** — nenhuma transferência out
- **Sem saque** — nenhuma retirada de fundos
- **Sem pagamento real de boleto** — boletos não são pagos pelo sistema
- **Sem conta digital** — não há contas para usuários
- **Sem BaaS** — não é Banking as a Service
- **Sem Open Finance** — nenhuma integração com Open Finance

## IA aplicada

### OpenAI GPT-4o

- **Classificação de intenção** — identifica se o usuário quer registrar transação, criar cobrança, consultar saldo, etc.
- **Extração de entidades** — nome do cliente, valor, descrição, data de vencimento
- **Processamento de linguagem natural** — português informal ("cobre 150 do João", "gera link de pagamento pra Maria")
- **Resposta contextual** — mantém contexto da conversa via ConversationLog

### Fluxo de IA

```
Mensagem do usuário
    ↓
AIService.process_message()
    ↓
OpenAI GPT-4o (com system prompt + contexto)
    ↓
Classificação: transaction | charge | query | reminder | other
    ↓
Se charge → PendingAction (aguarda confirmação)
Se transaction → registra diretamente
Se query → responde com dados do banco
```

## Workers e assincronismo

### Redis + RQ

- **Worker de lembretes** — verifica cobranças vencidas/próximas do vencimento periodicamente
- **Configurável** — `ENABLE_CHARGE_REMINDER_WORKER=false` por padrão
- **Logs** — ChargeReminderLog e ChargeDeliveryLog para auditoria

### Por que não Celery?

RQ é mais simples para o escopo do projeto. Celery adicionaria complexidade desnecessária para um único tipo de job (lembretes).

## Observabilidade

### Sentry (opcional)

- Inicialização condicional (`SENTRY_DSN` vazio = desativado)
- `before_send` hook redige tokens, senhas, API keys
- Integrações: FastApiIntegration, RedisIntegration

### Audit logging

- `audit_logger.py` — log estruturado para eventos críticos
- Eventos: charge_created, webhook_received, payment_confirmed, export, demo_login, demo_reset, reminder_job, rate_limit_hit
- Sanitização: `log_sanitizer.py` remove dados sensíveis antes do log

### Admin metrics

- `GET /admin/system-metrics` — métricas agregadas (total de usuários, cobranças por status, eventos de provider, lembretes enviados, uptime)
- Admin-only, sem dados pessoais

## Testes

### Backend

- **117 testes** com pytest + pytest-asyncio
- Testes de integração: charges, exports, filtros, demo mode, webhooks, rate limiting, admin metrics, Sentry
- Cobertura: models, services, routers, providers, security

### Frontend

- Build com Next.js (12 páginas estáticas)
- TypeScript com tipagem estrita

### E2E

- **Playwright** com 10 cenários: landing, demo login, dashboard, cards, charges table, filtros, busca, export CSV/PDF
- CI manual via `workflow_dispatch` — sobe demo stack completa, roda testes, derruba stack
- Seletores estáveis: `getByRole`, `getByPlaceholder`

## Demonstração

### Demo stack (Docker Compose)

```bash
docker-compose -f docker-compose.demo.yml up --build
```

- Frontend: `http://localhost:3001`
- Backend: `http://localhost:8001/docs`
- Login: "Entrar como Demo"
- Dados pré-populados via `seed_demo_data.py`
- Provider: `fake` (sem cobranças reais)

### E2E

```bash
docker-compose -f docker-compose.demo.yml up -d --build
./scripts/wait-for-url.sh http://localhost:8001/health/ready 120
./scripts/wait-for-url.sh http://localhost:3001 120
cd frontend && E2E_BASE_URL=http://localhost:3001 npm run test:e2e
```

## Limitações conscientes

- **Não é uma instituição financeira** — não oferece conta digital, Pix Out, saque ou pagamento de boletos
- **Provider fake é o padrão** — sandbox segura, sem cobranças reais
- **Mercado Pago é opt-in** — requer credenciais sandbox explícitas
- **Twilio WhatsApp Sandbox** — requer código de join para testes
- **OpenAI API key** — necessária para funcionalidade de IA
- **Demo mode** — desativado por padrão, nunca em produção
- **Sem multi-tenant** — cada usuário tem seus próprios dados, mas não há isolamento por organização

## Próximos passos

- Multi-tenant (organizações com múltiplos usuários)
- Integração com mais provedores de pagamento
- Dashboard de admin avançado com gráficos temporais
- App mobile (React Native)
- Webhooks para sistemas externos
- API pública documentada para integrações
