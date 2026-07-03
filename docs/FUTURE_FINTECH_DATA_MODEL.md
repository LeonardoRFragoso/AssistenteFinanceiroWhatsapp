# Future Fintech Data Model

> Sprint 13 — Jota Feature Parity Blueprint
> Sprint 14 — 5 of 13 proposed tables implemented
> Proposta de modelagem para funcionalidades fintech futuras.

> **Sprint 14 Update:** 5 of the 13 proposed tables have been implemented: `provider_connections`, `provider_webhook_events`, `open_finance_consents`, `organization_audit_logs`, and `transaction_authorizations` (named `transaction_authorizations` instead of `payment_authorizations`). Migration `k1f2g3h4i5j6`. The remaining 8 tables (connected_accounts, bank_transactions, detected_bills, bill_payment_intents, payment_receipts, kyc_profiles, kyb_profiles, risk_events) are planned for future sprints. See `docs/SPRINT_14_PROVIDER_FOUNDATION.md`.

---

## Visão Geral

As tabelas abaixo suportarão as funcionalidades necessárias para paridade com o Jota. Elas serão implementadas em fases conforme o roadmap (Sprint 14+).

```
provider_connections
    ├── open_finance_consents
    │   └── connected_accounts
    │       └── bank_transactions
    ├── detected_bills
    │   └── bill_payment_intents
    │       └── payment_authorizations
    │           └── payment_receipts
    ├── kyc_profiles
    │   └── kyb_profiles
    ├── risk_events
    ├── provider_webhook_events
    └── organization_audit_logs
```

---

## Tabelas Propostas

### 1. `provider_connections`

Registra conexões ativas com providers regulados.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização (NOT NULL) |
| `user_id` | Integer FK | Usuário que criou a conexão |
| `provider_type` | String(50) | `open_finance`, `banking`, `bill_payment`, `pix`, `kyc`, `dda`, `fraud`, `receipt`, `consent` |
| `provider_name` | String(50) | `fake`, `pluggy`, `belvo`, `celcoin`, `asaas`, `unico`, etc. |
| `external_id` | String(255) | ID no provider (nullable) |
| `status` | String(20) | `active`, `inactive`, `error`, `expired` |
| `metadata` | JSON | Dados específicos do provider |
| `created_at` | DateTime | Timestamp de criação |
| `updated_at` | DateTime | Timestamp de atualização |
| `expires_at` | DateTime | Expiração (nullable) |

**Índices**: `(organization_id, provider_type)`, `(organization_id, status)`

---

### 2. `open_finance_consents`

Consentimentos Open Finance por organização.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `user_id` | Integer FK | Usuário que autorizou |
| `provider_connection_id` | Integer FK | Conexão com provider |
| `institution_id` | String(20) | Instituição financeira (ex: `nubank`, `itau`) |
| `institution_name` | String(100) | Nome do banco |
| `consent_id` | String(255) | ID de consentimento no provider |
| `status` | String(20) | `pending`, `authorized`, `revoked`, `expired` |
| `scope` | JSON | Escopos autorizados (accounts, transactions, payments) |
| `authorized_at` | DateTime | Quando autorizado |
| `expires_at` | DateTime | Expiração (12 meses) |
| `revoked_at` | DateTime | Quando revogado (nullable) |
| `created_at` | DateTime | Timestamp |

**Índices**: `(organization_id, status)`, `(consent_id)`, `(expires_at)`

---

### 3. `connected_accounts`

Contas bancárias conectadas via Open Finance.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `consent_id` | Integer FK | Consentimento Open Finance |
| `external_account_id` | String(255) | ID da conta no provider |
| `institution_name` | String(100) | Nome do banco |
| `account_type` | String(20) | `checking`, `savings`, `credit_card` |
| `account_number_masked` | String(20) | Número mascarado (últimos 4 dígitos) |
| `branch_masked` | String(10) | Agência mascarada |
| `status` | String(20) | `active`, `inactive`, `error` |
| `last_synced_at` | DateTime | Última sincronização |
| `created_at` | DateTime | Timestamp |

**Índices**: `(organization_id, status)`, `(consent_id)`

---

### 4. `bank_transactions`

Transações importadas de contas conectadas.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `connected_account_id` | Integer FK | Conta conectada |
| `external_transaction_id` | String(255) | ID no provider |
| `amount` | Decimal(12,2) | Valor |
| `type` | String(20) | `credit`, `debit` |
| `description` | Text | Descrição da transação |
| `category` | String(50) | Categoria (IA) — nullable |
| `merchant_name` | String(200) | Nome do estabelecimento — nullable |
| `transaction_date` | DateTime | Data da transação |
| `posted_date` | DateTime | Data de efetivação |
| `metadata` | JSON | Dados adicionais do provider |
| `created_at` | DateTime | Timestamp |

**Índices**: `(organization_id, transaction_date)`, `(connected_account_id, transaction_date)`, `(category)`

---

### 5. `detected_bills`

Boletos detectados via DDA ou cadastrados manualmente.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `source` | String(20) | `dda`, `manual`, `ocr` |
| `document_number` | String(20) | CPF/CNPJ do beneficiário |
| `barcode` | String(255) | Código de barras ou linha digitável |
| `beneficiary_name` | String(200) | Nome do beneficiário |
| `amount` | Decimal(12,2) | Valor |
| `due_date` | Date | Data de vencimento |
| `status` | String(20) | `detected`, `pending_payment`, `paid`, `expired`, `cancelled` |
| `detected_at` | DateTime | Quando detectado |
| `paid_at` | DateTime | Quando pago (nullable) |
| `metadata` | JSON | Dados adicionais |
| `created_at` | DateTime | Timestamp |

**Índices**: `(organization_id, status)`, `(organization_id, due_date)`, `(document_number)`

---

### 6. `bill_payment_intents`

Intenções de pagamento de boletos/contas.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `detected_bill_id` | Integer FK | Boleto detectado (nullable) |
| `user_id` | Integer FK | Usuário que solicitou |
| `amount` | Decimal(12,2) | Valor a pagar |
| `schedule_date` | Date | Data agendada (nullable = imediato) |
| `source_account_id` | Integer FK | Conta de débito (connected_account ou banking account) |
| `status` | String(20) | `pending`, `authorized`, `executing`, `completed`, `failed`, `cancelled` |
| `provider_transaction_id` | String(255) | ID no provider |
| `metadata` | JSON | Dados do pagamento |
| `created_at` | DateTime | Timestamp |
| `executed_at` | DateTime | Quando executado (nullable) |

**Índices**: `(organization_id, status)`, `(organization_id, schedule_date)`

---

### 7. `payment_authorizations`

Autorizações de pagamento (senha de 6 dígitos).

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `user_id` | Integer FK | Usuário que autorizou |
| `bill_payment_intent_id` | Integer FK | Intenção de pagamento (nullable) |
| `pix_out_id` | Integer FK | Pix Out (nullable) |
| `authorization_type` | String(20) | `password`, `biometric`, `pre_authorized` |
| `status` | String(20) | `pending`, `approved`, `denied`, `expired` |
| `attempts` | Integer | Tentativas (máx 3) |
| `expires_at` | DateTime | Expiração da autorização (5 minutos) |
| `authorized_at` | DateTime | Quando autorizado (nullable) |
| `created_at` | DateTime | Timestamp |

**Índices**: `(organization_id, status)`, `(user_id, status)`

---

### 8. `payment_receipts`

Comprovantes de pagamento/transação.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `transaction_type` | String(20) | `pix_out`, `bill_payment`, `pix_received`, `charge` |
| `transaction_id` | String(255) | ID da transação no provider |
| `receipt_url` | String(500) | URL do comprovante (PDF/imagem) |
| `receipt_data` | JSON | Dados estruturados do comprovante |
| `amount` | Decimal(12,2) | Valor |
| `recipient_name` | String(200) | Nome do destinatário |
| `recipient_document` | String(20) | CPF/CNPJ do destinatário (mascarado) |
| `transaction_date` | DateTime | Data da transação |
| `created_at` | DateTime | Timestamp |

**Índices**: `(organization_id, transaction_date)`, `(transaction_type, transaction_id)`

---

### 9. `kyc_profiles`

Perfis KYC de pessoas físicas.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização (nullable para PF individual) |
| `user_id` | Integer FK | Usuário |
| `cpf` | String(11) | CPF (criptografado) |
| `full_name` | String(200) | Nome completo |
| `birth_date` | Date | Data de nascimento |
| `document_type` | String(10) | `rg`, `cnh`, `passport` |
| `document_number` | String(20) | Número do documento (criptografado) |
| `kyc_provider` | String(50) | `fake`, `unico`, `caf` |
| `kyc_session_id` | String(255) | ID da sessão no provider |
| `status` | String(20) | `pending`, `approved`, `rejected`, `expired` |
| `biometric_result` | String(20) | `passed`, `failed`, `not_performed` |
| `document_result` | String(20) | `valid`, `invalid`, `not_performed` |
| `verified_at` | DateTime | Quando verificado (nullable) |
| `expires_at` | DateTime | Expiração da verificação |
| `metadata` | JSON | Dados adicionais (não sensíveis) |
| `created_at` | DateTime | Timestamp |

**Índices**: `(user_id, status)`, `(organization_id, status)`, `(cpf)` (criptografado)

> **Nota**: Imagens de documento e selfie **não são armazenadas** — apenas o resultado da verificação.

---

### 10. `kyb_profiles`

Perfis KYB de pessoas jurídicas.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `user_id` | Integer FK | Usuário que solicitou |
| `cnpj` | String(14) | CNPJ (criptografado) |
| `company_name` | String(200) | Razão social |
| `company_type` | String(20) | `mei`, `lt`, `sa`, `individual` |
| `representative_name` | String(200) | Nome do representante legal |
| `representative_cpf` | String(11) | CPF do representante (criptografado) |
| `representative_kyc_id` | Integer FK | KYC do representante |
| `kyc_provider` | String(50) | Provider usado |
| `status` | String(20) | `pending`, `approved`, `rejected`, `expired` |
| `verified_at` | DateTime | Quando verificado |
| `expires_at` | DateTime | Expiração |
| `metadata` | JSON | Dados adicionais |
| `created_at` | DateTime | Timestamp |

**Índices**: `(organization_id, status)`, `(cnpj)` (criptografado)

---

### 11. `risk_events`

Eventos de risco e antifraude.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `user_id` | Integer FK | Usuário relacionado (nullable) |
| `event_type` | String(50) | `high_value_transaction`, `unusual_location`, `velocity_check`, `kyc_mismatch` |
| `risk_level` | String(20) | `low`, `medium`, `high`, `critical` |
| `risk_score` | Decimal(5,2) | Score de risco (0-100) |
| `description` | Text | Descrição do evento |
| `action_taken` | String(20) | `none`, `flagged`, `blocked`, `manual_review` |
| `resolved` | Boolean | Se foi resolvido |
| `resolved_by` | Integer FK | Usuário que resolveu (nullable) |
| `resolved_at` | DateTime | Quando resolvido |
| `metadata` | JSON | Dados adicionais |
| `created_at` | DateTime | Timestamp |

**Índices**: `(organization_id, risk_level)`, `(organization_id, event_type)`, `(created_at)`

---

### 12. `provider_webhook_events`

Eventos recebidos de providers regulados (webhooks).

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização (nullable se não resolvido ainda) |
| `provider_name` | String(50) | Nome do provider |
| `provider_event_id` | String(255) | ID único do evento no provider |
| `event_type` | String(50) | Tipo do evento |
| `payload` | JSON | Payload recebido (sanitizado) |
| `status` | String(20) | `received`, `processed`, `failed`, `duplicate` |
| `processed_at` | DateTime | Quando processado |
| `error_message` | Text | Erro (se falhou) |
| `created_at` | DateTime | Timestamp |

**Índices**: `(provider_name, provider_event_id)` (unique), `(organization_id, event_type)`, `(status)`

> **Idempotência**: `provider_event_id` é único por provider — eventos duplicados são marcados como `duplicate`.

---

### 13. `organization_audit_logs`

Logs de auditoria organizacionais.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | ID único |
| `organization_id` | Integer FK | Organização |
| `user_id` | Integer FK | Usuário (nullable para eventos de sistema) |
| `action` | String(100) | `consent.created`, `consent.revoked`, `payment.authorized`, `payment.denied`, `kyc.approved`, `kyc.rejected`, `provider.connected`, `provider.disconnected`, `bill.paid`, `bill.scheduled` |
| `scope` | String(50) | `open_finance`, `payment`, `kyc`, `lgpd`, `whatsapp`, `billing` |
| `metadata` | JSON | Detalhes do evento |
| `ip_address` | String(45) | IP de origem (nullable) |
| `user_agent` | String(255) | User agent (nullable) |
| `created_at` | DateTime | Timestamp |

**Índices**: `(organization_id, action)`, `(organization_id, scope)`, `(created_at)`

---

## Relacionamentos

```
organization
    ├── provider_connections
    │   ├── open_finance_consents
    │   │   └── connected_accounts
    │   │       └── bank_transactions
    │   └── (outros providers)
    ├── detected_bills
    │   └── bill_payment_intents
    │       └── payment_authorizations
    │           └── payment_receipts
    ├── kyc_profiles
    ├── kyb_profiles
    ├── risk_events
    ├── provider_webhook_events
    └── organization_audit_logs
```

---

## Notas de Implementação

1. **Criptografia**: Campos sensíveis (CPF, CNPJ, número de documento) devem ser criptografados em repouso.
2. **Multi-tenant**: Todas as tabelas têm `organization_id` NOT NULL (exceto `kyc_profiles` que pode ser PF individual).
3. **Retenção**: Dados de transações e pagamentos devem ser retidos por 5 anos (requerimento regulatório).
4. **LGPD**: Dados pessoais devem ter política de retenção e exclusão conforme LGPD.
5. **Idempotência**: `provider_webhook_events` garante idempotência via `provider_event_id`.
6. **Migrações**: Cada tabela será criada em sua respectiva fase do roadmap, não todas de uma vez.
