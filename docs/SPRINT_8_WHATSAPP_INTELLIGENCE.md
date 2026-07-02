# Sprint 8 — WhatsApp Intelligence, QR Code Sandbox, OCR Assistivo e Tarefas Recorrentes

## Resumo

O Sprint 8 evolui o PayFlow AI com inteligência financeira via WhatsApp, geração de QR Codes sandbox para cobranças, análise assistiva de documentos (OCR), e tarefas recorrentes não-transacionais.

## Funcionalidades Implementadas

### 1. WhatsApp Intelligence — Consultas Financeiras

**Novos intents adicionados ao AIService:**
- `list_overdue_charges` — listar cobranças vencidas
- `search_charges` — buscar cobranças por cliente
- `charge_summary` — resumo geral de cobranças
- `customer_charge_history` — histórico de um cliente
- `monthly_financial_summary` — resumo financeiro mensal
- `top_overdue_customers` — clientes que mais atrasam
- `create_recurring_task` — criar tarefa recorrente
- `list_recurring_tasks` — listar tarefas recorrentes

**Novo serviço:** `FinancialQueryService` (`backend/app/services/financial_query_service.py`)
- Consultas dedicadas para cobranças por status, cliente, período
- Formatação de respostas em português natural para WhatsApp
- Nunca executa operações bancárias — apenas consultas

**Webhook atualizado:** `backend/app/routers/webhook.py`
- Novos handlers para todos os intents financeiros
- Help message expandida com exemplos de consultas
- Respostas formatadas com emojis e linguagem natural

### 2. QR Code Sandbox para Cobranças

**Backend:**
- `FakePaymentProvider` agora gera QR Codes reais (PNG base64) apontando para o link de pagamento fake
- Novo endpoint: `GET /charges/{charge_id}/qr-code` — retorna QR Code sandbox
- QR Code NÃO representa Pix real — é sandbox/demo apenas
- Biblioteca `qrcode[pil]` adicionada ao requirements.txt

**Frontend:**
- Botão de QR Code na tabela de cobranças do dashboard
- Modal de visualização com imagem do QR Code, valor, descrição
- Aviso de sandbox visível no modal
- Link para abrir página de pagamento fake

### 3. OCR Assistivo — Análise de Documentos

**Novo serviço:** `DocumentAnalysisService` (`backend/app/services/document_analysis_service.py`)
- Análise de imagens via OpenAI Vision API
- Extração de texto de PDFs via PyPDF2
- Pattern matching para valores, datas e tipos de documento
- Retorna draft com confiança e ação sugerida
- **Nunca executa pagamentos** — apenas extrai dados
- Requer confirmação explícita do usuário

**Novo endpoint:** `POST /documents/analyze`
- Aceita PNG, JPG, WebP, PDF (máx 5MB)
- Retorna dados extraídos com nível de confiança
- Sugere ação (criar lembrete, revisão manual)

**WhatsApp:** Webhook agora aceita imagens e PDFs
- Roteia automaticamente para `DocumentAnalysisService`
- Retorna análise formatada como mensagem WhatsApp

### 4. Tarefas Recorrentes Não-Transacionais

**Novo model:** `RecurringTask` e `RecurringTaskLog`
- Tabelas `recurring_tasks` e `recurring_task_logs`
- Tipos de recorrência: diária, semanal, mensal
- Log de execução com sucesso/erro e mensagem enviada

**Novo serviço:** `RecurringTaskService`
- Criação, listagem, cancelamento de tarefas
- Cálculo automático de próxima execução
- Execução envia apenas lembretes via WhatsApp
- **Nunca executa operações bancárias**

**Novos endpoints:** `/recurring-tasks`
- `POST /recurring-tasks` — criar tarefa
- `GET /recurring-tasks` — listar tarefas
- `POST /recurring-tasks/{id}/cancel` — cancelar tarefa
- `POST /recurring-tasks/run` — executar tarefas em atraso (admin)

**Worker:** `backend/app/jobs/recurring_task_jobs.py`
- Job assíncrono para executar tarefas em atraso
- Config: `ENABLE_RECURRING_TASK_WORKER`, `RECURRING_TASK_INTERVAL_MINUTES`

**Frontend:** Componente `RecurringTasksSection`
- Seção no dashboard para criar e visualizar tarefas recorrentes
- Formulário com tipo de recorrência (diária/semanal/mensal)
- Cancelamento de tarefas ativas
- Aviso de que apenas lembretes são enviados

**WhatsApp:** Intents `create_recurring_task` e `list_recurring_tasks` integrados

## Segurança e Constraints

- ✅ Nenhum Pix Out ou saque implementado
- ✅ QR Code é sandbox/fake — não representa Pix real
- ✅ OCR apenas extrai dados — não executa pagamentos
- ✅ Tarefas recorrentes apenas enviam lembretes
- ✅ Provider padrão permanece `fake`
- ✅ Demo mode permanece seguro e desativado por padrão
- ✅ Todas as ações do AI requerem confirmação explícita
- ✅ Nenhuma secret commitada

## Arquivos Criados

| Arquivo | Descrição |
|---------|-----------|
| `backend/app/services/financial_query_service.py` | Serviço de consultas financeiras |
| `backend/app/services/document_analysis_service.py` | Serviço de OCR assistivo |
| `backend/app/services/recurring_task_service.py` | Serviço de tarefas recorrentes |
| `backend/app/models/recurring_task.py` | Model de tarefa recorrente + log |
| `backend/app/schemas/recurring_task.py` | Schemas Pydantic |
| `backend/app/routers/documents.py` | Router de análise de documentos |
| `backend/app/routers/recurring_tasks.py` | Router de tarefas recorrentes |
| `backend/app/jobs/recurring_task_jobs.py` | Job do worker de tarefas |
| `backend/migrations/versions/f6a7b8c9d0e1_add_recurring_tasks.py` | Migration |
| `backend/tests/test_sprint8.py` | Testes do Sprint 8 (27 testes) |
| `frontend/components/RecurringTasksSection.tsx` | Componente de tarefas recorrentes |

## Arquivos Modificados

| Arquivo | Mudança |
|---------|---------|
| `backend/app/services/ai_service.py` | Novos intents e entidades |
| `backend/app/routers/webhook.py` | Handlers para novos intents + mídia |
| `backend/app/providers/fake_provider.py` | QR Code real (PNG base64) |
| `backend/app/routers/charges.py` | Endpoint QR Code |
| `backend/app/main.py` | Routers de documents e recurring_tasks |
| `backend/app/core/config.py` | Config de recurring task worker |
| `backend/app/models/__init__.py` | Imports de novos models |
| `backend/requirements.txt` | qrcode, Pillow, PyPDF2 |
| `backend/tests/test_providers.py` | Assert atualizado para QR Code |
| `frontend/pages/dashboard.tsx` | QR Code modal + RecurringTasksSection |
| `frontend/services/api.ts` | APIs de recurring tasks e documents |
| `docker-compose.demo.yml` | Env de recurring task worker |

## Testes

- **27 novos testes** em `test_sprint8.py` cobrindo:
  - FinancialQueryService (10 testes)
  - RecurringTaskService (8 testes)
  - DocumentAnalysisService (7 testes)
  - FakePaymentProvider QR Code (2 testes)
- **30 testes de estabilização** em `test_sprint8_stabilize.py` (Sprint 8.1):
  - AIService graceful init (4 testes)
  - TwilioWhatsAppService graceful init (3 testes)
  - OCR mock provider (7 testes)
  - QR Code sandbox isolation (5 testes)
  - Recurring task isolation (5 testes)
  - WhatsApp media handling (6 testes)
- **Resultado final: 174 passed, 0 failed, 0 errors**

## Sprint 8.1 — Estabilização

### Correções aplicadas:

- **AIService**: construtor usa `api_key or "dummy-key-for-init"` para não crashar sem `OPENAI_API_KEY`
- **TwilioWhatsAppService**: construtor usa `auth_token or "dummy-token-for-init"` para não crashar sem `TWILIO_AUTH_TOKEN`
- **DocumentAnalysisService**: adicionado `DOCUMENT_ANALYSIS_PROVIDER` config (default `mock`); quando mock ou sem API key, retorna resultado determinístico sem chamar OpenAI
- **RecurringTasks router**: `is_admin` inexistente substituído por checagem `ADMIN_EMAILS` (mesmo padrão do auth router)
- **OCR em modo mock**: não chama OpenAI Vision; retorna `confidence=0.0` com `requires_confirmation=True`
- **OCR em produção**: continua usando OpenAI Vision quando `DOCUMENT_ANALYSIS_PROVIDER=openai` e `OPENAI_API_KEY` configurada
