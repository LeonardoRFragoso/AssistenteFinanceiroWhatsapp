# Exportação CSV, Worker de Lembretes e Envio de Link para Cliente

## Exportação CSV de Cobranças

### Endpoint

```
GET /charges/export.csv
```

**Autenticação:** JWT obrigatório.

**Parâmetros de query (opcionais):**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `status` | string | Filtra por status: `pending`, `paid`, `cancelled`, `overdue` |
| `start_date` | date | Data inicial (YYYY-MM-DD) — filtra por `created_at` |
| `end_date` | date | Data final (YYYY-MM-DD) — filtra por `created_at` |

**Colunas do CSV:**

| Coluna | Descrição |
| --- | --- |
| `id` | ID interno da cobrança |
| `customer_name` | Nome do cliente |
| `customer_phone` | Telefone do cliente |
| `amount` | Valor (formato decimal) |
| `description` | Descrição |
| `status` | Status real (`pending`, `paid`, `cancelled`) |
| `derived_status` | Status derivado (`pending`, `overdue`, `paid`, `cancelled`) |
| `due_date` | Data de vencimento |
| `paid_at` | Data de pagamento |
| `created_at` | Data de criação |
| `payment_link` | Link de pagamento |

### Frontend

O botão "Exportar CSV" está disponível no dashboard de cobranças, ao lado dos filtros. Ele respeita o filtro atual (ex: se o filtro estiver em "Pagas", o CSV conterá apenas cobranças pagas).

## Worker de Lembretes

### Visão Geral

O sistema de lembretes envia notificações via WhatsApp para cobranças:
- **Due Soon:** vencimento em 1 dia
- **Overdue:** vencimento já passou

A idempotência é garantida: cada cobrança recebe no máximo 1 lembrete de cada tipo por dia.

### Configuração

Variáveis de ambiente:

```env
ENABLE_CHARGE_REMINDER_WORKER=false
CHARGE_REMINDER_INTERVAL_MINUTES=60
```

| Variável | Default | Descrição |
| --- | --- | --- |
| `ENABLE_CHARGE_REMINDER_WORKER` | `false` | Ativa o scheduler automático |
| `CHARGE_REMINDER_INTERVAL_MINUTES` | `60` | Intervalo entre execuções (em minutos) |

### Como Executar

#### Manual (endpoint)

```bash
curl -X POST http://localhost:8000/charges/reminders/run \
  -H "Authorization: Bearer <token>"
```

#### Worker RQ

O worker processa a fila `charge_reminders`:

```bash
cd backend
python worker.py
```

#### Job direto (CLI)

```python
from app.jobs.charge_reminder_jobs import run_charge_reminders_job
result = run_charge_reminders_job()
print(result)
```

#### Scheduler automático

Quando `ENABLE_CHARGE_REMINDER_WORKER=true`, o scheduler inicia junto com a aplicação e enfileira o job a cada `CHARGE_REMINDER_INTERVAL_MINUTES` minutos.

### Retorno do Job

```json
{
  "sent_due_soon": 2,
  "sent_overdue": 1,
  "skipped": 3,
  "errors": 0,
  "total_processed": 6
}
```

## Envio de Link para Cliente

### Fluxo

1. Usuário cria cobrança via WhatsApp
2. Sistema confirma a criação e exibe o link
3. Se a cobrança tiver telefone do cliente, o sistema pergunta: *"Deseja que eu envie o link de pagamento para ele pelo WhatsApp?"*
4. Usuário responde "sim" ou "não"
5. Se sim, o link é enviado para o cliente e o envio é registrado em `ChargeDeliveryLog`

### Regras

- **Não envia automaticamente** — sempre exige confirmação do usuário
- Se Twilio não estiver configurado, o envio é **simulado** e logado como `SIMULATED`
- Todos os envios (reais, simulados ou falhas) são registrados em `charge_delivery_logs`

### Modelo `ChargeDeliveryLog`

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `id` | int | ID |
| `charge_id` | int | FK para `charges.id` |
| `user_id` | int | FK para `users.id` |
| `customer_phone` | string | Telefone do cliente |
| `channel` | enum | `whatsapp`, `sms`, `email` |
| `status` | enum | `sent`, `failed`, `simulated` |
| `sent_at` | datetime | Data do envio |
| `error_message` | text | Mensagem de erro (se houver) |
| `created_at` | datetime | Data de criação do registro |

### Mensagem Enviada ao Cliente

```
Olá, João. Você recebeu uma cobrança de R$ 150,00 referente a Serviço do site.

Link de pagamento:
<url>
```

## Variáveis de Ambiente (Sprint 3)

```env
# Provider (padrão: fake)
PAYFLOW_PAYMENT_PROVIDER=fake

# Mercado Pago Sandbox (opcional)
MERCADO_PAGO_ACCESS_TOKEN=
MERCADO_PAGO_PUBLIC_KEY=
MERCADO_PAGO_WEBHOOK_SECRET=

# Worker de lembretes
ENABLE_CHARGE_REMINDER_WORKER=false
CHARGE_REMINDER_INTERVAL_MINUTES=60
```

## Limitações

- Mercado Pago funciona apenas em modo sandbox; não há Pix Out, saque ou operações bancárias reais
- O scheduler de lembretes é uma solução simples para desenvolvimento; em produção, considere usar RQ Scheduler ou cron
- A exportação CSV limita-se a 10.000 cobranças por requisição
- O envio de link para cliente requer que o telefone esteja no formato internacional (ex: `+5511...`)
