# Sprint 15 — Asaas Sandbox Provider Integration

> **Status**: ✅ Complete
> **Data**: 2025-07-02
> **Testes**: 473 backend (0 falhas), 39 novos testes Asaas
> **Migration**: `l2a3b4c5d6e7` — single head

---

## Objetivo

Integrar o gateway de pagamento Asaas em modo sandbox para criar cobranças Pix, boleto e link de pagamento, processar webhooks, e permitir reconciliação manual de status.

---

## O que foi implementado

### 1. Pesquisa e Documentação
- `docs/ASAAS_INTEGRATION_RESEARCH.md` — pesquisa completa da API Asaas v3
- Endpoints, autenticação, status mapping, webhook events, mapeamento PayFlow

### 2. Configuração (`backend/app/core/config.py`)
- `ASAAS_ENVIRONMENT` — sandbox/production (default: sandbox)
- `ASAAS_API_BASE_URL` — URL base da API
- `ASAAS_API_KEY` — API key (never logged)
- `ASAAS_WEBHOOK_TOKEN` — token para validar webhooks
- `ENABLE_ASAAS_CHARGE_PROVIDER` — feature flag (default: false)

### 3. AsaasClient (`backend/app/integrations/asaas_client.py`)
- HTTP client com httpx
- Timeout de 30s em todas as requisições
- Retry em 5xx e timeouts (2 tentativas com backoff)
- Sanitização de dados sensíveis antes de logar
- Métodos: create_customer, create_payment, get_payment, get_pix_qr_code, cancel_payment, list_customers

### 4. AsaasProvider (`backend/app/providers/asaas_provider.py`)
- Implementa interface `PaymentProvider`
- Suporta billing types: PIX, BOLETO, UNDEFINED (link), CREDIT_CARD
- Cria customer + payment em sandbox
- Recupera QR Code Pix automaticamente
- Mapeia status Asaas → PayFlow (PENDING→pending, RECEIVED→paid, etc.)
- `parse_webhook_event` normaliza eventos Asaas
- `validate_webhook` valida token `asaas-access-token`
- `cancel_charge` cancela cobrança no Asaas
- Gera CPF sandbox válido quando em sandbox

### 5. Provider Factory (`backend/app/providers/provider_factory.py`)
- Suporte para `asaas` como provider name
- Validação: demo mode, feature flag, API key
- Produção: rejeita provider desconhecido (não faz fallback silencioso)

### 6. Charge Model e Schema
- `Charge` model: novos campos `provider_bank_slip_url`, `provider_status`
- `ChargeCreate` schema: novo campo `billing_type` (pix/boleto/undefined)
- `ChargeResponse` schema: inclui `provider_bank_slip_url`, `provider_status`
- Migration: `l2a3b4c5d6e7_add_asaas_charge_fields.py`

### 7. Charge Service (`backend/app/services/charge_service.py`)
- `create_charge` passa `billing_type` ao provider
- Salva `provider_bank_slip_url` e `provider_status` após criação
- `process_webhook_payload` suporta Asaas sem requerer init completo
- `sync_provider_status` — reconciliação manual via API do provider
- `process_payment_event` agora trata expired e cancelled

### 8. Webhook Endpoint (`backend/app/routers/provider_webhooks.py`)
- `POST /provider-webhooks/asaas`
- Valida token `asaas-access-token` contra `ASAAS_WEBHOOK_TOKEN`
- Idempotência: rejeita eventos duplicados via `event_id`
- Rate limited
- Sanitização de payload

### 9. Endpoints de Gerenciamento
- `POST /providers/asaas/test-connection` — valida config sem chamar API
- `POST /charges/{charge_id}/sync-provider-status` — reconciliação manual

### 10. WhatsApp Integration
- `PendingActionService` passa `billing_type` ao criar cobranças
- Usa provider ativo automaticamente (fake ou asaas)

### 11. Frontend (`frontend/pages/dashboard.tsx`)
- Badge de provider (Asaas Sandbox / fake) em cada cobrança
- Botão de sync (RefreshCw) para reconciliação manual
- Link para boleto PDF (FileBadge) quando disponível
- Status do provider exibido abaixo do status PayFlow
- `chargesAPI.syncProviderStatus` adicionado ao service

### 12. Testes (4 arquivos, 39 testes)
- `test_asaas_config.py` — 7 testes (config defaults, factory validation)
- `test_asaas_provider.py` — 16 testes (status map, event parsing, webhook validation)
- `test_asaas_client.py` — 8 testes (HTTP client, sanitization, error handling)
- `test_asaas_webhook.py` — 8 testes (model fields, sync, webhook processing)

---

## Validações

| Validação | Resultado |
|---|---|
| pytest (full suite) | 473 passed, 0 failed |
| alembic upgrade head | Single head: `l2a3b4c5d6e7` |
| Multi-tenant audit | 15 tables, 0 orphans |
| Frontend build | ✅ Success |
| docker compose config | ✅ Valid |

---

## Segurança

- API key nunca é logada ou exposta
- Webhook token validado em todas as requisições
- Demo mode bloqueia Asaas provider
- Feature flag `ENABLE_ASAAS_CHARGE_PROVIDER` default false
- Produção rejeita provider desconhecido sem fallback
- Sanitização de dados sensíveis em logs
- Idempotência em webhooks

---

## O que NÃO foi implementado

- Pix Out (envio de dinheiro)
- Pagamento de boletos
- Conta digital / BaaS
- Open Finance real
- DDA real
- KYC real
- Transferências
- Cartão de crédito (apenas estrutura, não testado)

---

## Como ativar

```env
# .env
ENABLE_DEMO_MODE=false
PAYFLOW_PAYMENT_PROVIDER=asaas
ENABLE_ASAAS_CHARGE_PROVIDER=true
ASAAS_ENVIRONMENT=sandbox
ASAAS_API_KEY=<sua-api-key-sandbox>
ASAAS_WEBHOOK_TOKEN=<token-32+-chars>
```

## Configurar webhook no Asaas

```
POST https://sandbox.asaas.com/api/v3/webhooks
{
  "name": "PayFlow Webhook",
  "url": "https://api.payflow.ai/provider-webhooks/asaas",
  "enabled": true,
  "authToken": "<mesmo-token-do-env>",
  "sendType": "SEQUENTIALLY",
  "events": [
    "PAYMENT_CREATED", "PAYMENT_CONFIRMED", "PAYMENT_RECEIVED",
    "PAYMENT_OVERDUE", "PAYMENT_DELETED", "PAYMENT_RESTORED", "PAYMENT_REFUNDED"
  ]
}
```
