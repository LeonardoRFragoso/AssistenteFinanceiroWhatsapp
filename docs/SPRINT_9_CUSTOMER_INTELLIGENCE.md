# Sprint 9 — Customer Intelligence, Régua de Cobrança e Templates de Mensagens

## Objetivo

Transformar o PayFlow AI em um assistente mais inteligente para relacionamento e cobrança, com histórico por cliente, régua de cobrança configurável, templates de mensagens, sugestão de abordagem via IA e envio sempre com confirmação explícita.

## Regras Obrigatórias

- **Nenhuma mensagem de cobrança pode ser enviada automaticamente** sem confirmação explícita do usuário.
- IA pode sugerir mensagem, mas o usuário precisa confirmar antes do envio.
- Não enviar mensagens agressivas, abusivas ou constrangedoras.
- Nenhuma operação bancária regulada (Pix Out, saque, conta digital, BaaS, Open Finance, pagamento real de boleto, rendimento real, saldo bancário real).
- Provider padrão continua `fake`.
- QR Code continua sandbox/fake.
- OCR continua apenas assistivo.
- Tarefas recorrentes continuam não transacionais.

## Novos Modelos

### Customer (`customers` table)
- `id`, `user_id`, `name`, `phone`, `email`, `notes`
- `created_at`, `updated_at`
- Clientes são criados automaticamente quando uma cobrança é criada.
- Score operacional é calculado dinamicamente via queries (não persistido).

### MessageTemplate (`message_templates` table)
- `id`, `user_id`, `name`, `tone` (friendly/neutral/firm), `template_text`
- `active`, `created_at`, `updated_at`
- Placeholders permitidos: `{customer_name}`, `{amount}`, `{description}`, `{due_date}`, `{payment_link}`, `{qr_code_note}`, `{company_name}`
- Validação automática contra palavras agressivas/abusivas.
- Templates padrão são criados automaticamente (seed) para novos usuários.

### CollectionRule (`collection_rules` table)
- `id`, `user_id`, `name`, `days_offset`, `trigger_type` (before_due/on_due/after_due)
- `template_id` (opcional), `active`
- Regras **não enviam mensagens automaticamente**. Apenas preparam rascunhos.

### CollectionMessageLog (`collection_message_logs` table)
- `id`, `user_id`, `charge_id`, `customer_id`, `template_id`
- `channel`, `message_preview`, `status` (draft/pending_confirmation/sent/skipped/failed)
- `sent_at`, `created_at`
- Rastreia todas as mensagens de cobrança geradas.

## Score Operacional

O score operacional é um indicador de relacionamento baseado em padrões de pagamento:

| Status | Descrição |
|--------|-----------|
| `good_payer` | Pagou todas as cobranças, sem atrasos |
| `late_payer` | Tem 1-2 cobranças vencidas |
| `frequent_late` | Tem 3+ cobranças vencidas |
| `new_customer` | Poucas cobranças, sem histórico suficiente |
| `inactive_customer` | Sem cobranças há mais de 180 dias |

**Importante:** Este é um score operacional de relacionamento, **não** um score de crédito. Não deve ser usado para decisões de crédito ou fins regulatórios.

## Novos Endpoints

### Customers
- `GET /customers` — Lista clientes com paginação, busca e filtros
- `GET /customers/{id}` — Detalhe do cliente com histórico de cobranças
- `GET /customers/{id}/charges` — Cobranças de um cliente
- `GET /customers/{id}/summary` — Resumo operacional do cliente
- `PATCH /customers/{id}/notes` — Atualiza notas do cliente

### Message Templates
- `GET /message-templates` — Lista templates
- `POST /message-templates` — Cria template
- `PUT /message-templates/{id}` — Atualiza template
- `POST /message-templates/{id}/preview` — Prévia renderizada
- `POST /message-templates/{id}/deactivate` — Desativa template

### Collection
- `GET /collection/rules` — Lista regras de cobrança
- `POST /collection/rules` — Cria regra
- `POST /collection/rules/{id}/deactivate` — Desativa regra
- `GET /collection/followups/overdue` — Gera rascunhos para vencidas
- `GET /collection/logs` — Lista logs de mensagens

## Novas Intents do WhatsApp

- `list_customers` — "quais clientes estão devendo?"
- `customer_summary` — "me mostra o histórico do João"
- `generate_collection_message` — "gera uma mensagem educada para cobrar a Maria"
- `prepare_overdue_followups` — "cobre os clientes vencidos"
- `list_collection_rules` — "quais regras de cobrança eu tenho?"
- `create_collection_rule` — "crie uma régua para lembrar 2 dias antes do vencimento"
- `list_message_templates` — "quais templates de cobrança eu tenho?"

## Fluxo de Confirmação Explícita

1. Usuário pede: "gera uma mensagem para cobrar a Maria"
2. Sistema gera rascunho usando template apropriado
3. Rascunho é exibido com aviso: "Nenhuma mensagem foi enviada"
4. Log é criado com status `DRAFT`
5. Para enviar, usuário deve confirmar explicitamente

## Dashboard

Nova seção "Customer Intelligence & Régua de Cobrança" com 3 abas:
- **Clientes**: Lista com busca, filtros, score operacional e modal de detalhes
- **Templates**: Lista, prévia renderizada, desativar
- **Régua de Cobrança**: Cobranças vencidas com rascunhos, regras configuradas

## PDF Export

O PDF de cobranças agora inclui uma seção de QR Codes (Sandbox/Demo) para cobranças pendentes, com aviso explícito de que não representam Pix QR codes reais.

## Testes

- **60 novos testes** em `test_sprint9.py` cobrindo:
  - CustomerService: criação, isolamento, histórico, score operacional
  - MessageTemplateService: CRUD, validação, placeholders, preview, seed
  - CollectionService: regras, follow-ups, logs, isolamento
  - WhatsApp intents: todos os novos handlers
  - Confirmação explícita: rascunhos não enviam mensagens
  - No banking operations: verificação de não-transacionalidade
- **Total: 234 testes backend** (174 existentes + 60 novos)

## Migration

```bash
alembic upgrade head
```

Migration ID: `a1b2c3d4e5f6` — Cria 4 novas tabelas: `customers`, `message_templates`, `collection_rules`, `collection_message_logs`.

## E2E Coverage (Sprint 9.1)

Sprint 9.1 adicionou 8 novos cenários E2E Playwright cobrindo Customer Intelligence:

- **Customer Intelligence section aparece** — seção visível no dashboard
- **Aba Clientes ativa por padrão** — search input visível
- **Listagem de clientes ou empty state** — table ou mensagem controlada
- **Busca de clientes** — input aceita texto e Enter
- **Aba Templates** — conteúdo ou empty state
- **Preview de template** — botão funciona quando templates existem
- **Aba Régua de Cobrança + não-auto-envio** — headings visíveis, warning presente, sem botão "Enviar"
- **QR Code sandbox modal + exports** — modal abre/fecha, CSV e PDF funcionam

Testes Sprint 9 (11-18) usam **serial mode** com login compartilhado para reduzir carga no backend.

### data-testids adicionados

- `customer-intelligence-section` — container da seção
- `customers-tab` — botão aba Clientes
- `templates-tab` — botão aba Templates
- `collection-rules-tab` — botão aba Régua de Cobrança
- `customer-search-input` — input de busca de clientes
- `message-template-preview-button` — botão de prévia de template
- `qr-code-modal` — modal de QR Code sandbox

### Screenshots gerados

- `docs/assets/customer-intelligence.png`
- `docs/assets/message-templates.png`
- `docs/assets/collection-rules.png`

**Total E2E: 18 cenários demo.spec + 7 cenários screenshots.spec = 25 testes Playwright**
