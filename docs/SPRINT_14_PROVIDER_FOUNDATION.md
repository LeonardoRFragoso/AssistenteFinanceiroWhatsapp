# Sprint 14 — Provider Foundation, Consent, Audit Logs e Transaction Auth

**Data:** 02 Julho 2025  
**Commit base:** `8dbf2bb`  
**Branch:** `main`

---

## Objetivo

Criar a fundação técnica para futuras integrações reguladas **sem implementar operações financeiras reais**. Esta sprint adiciona tabelas, services, endpoints internos, logs de auditoria, consentimento básico, provider connection registry e autenticação transacional — tudo em modo fake/sandbox e protegido por feature flags.

---

## Tabelas Criadas (5)

### 1. `provider_connections`
Registro de conexões entre organizações e providers regulados.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK → organizations | Obrigatório, indexado |
| `provider_type` | String(50) | open_finance, banking, bill_payment, pix, kyc, fraud, dda, receipt, consent |
| `provider_name` | String(50) | Default: `fake` |
| `status` | Enum | active, inactive, error, expired, not_configured |
| `environment` | String(20) | sandbox ou production |
| `display_name` | String(200) | |
| `external_connection_id` | String(255) | ID externo do provider |
| `institution_name` | String(100) | |
| `institution_code` | String(20) | |
| `scopes` | JSON | |
| `extra_data` | JSON | Sanitizado |
| `secret_ref` | String(255) | **Apenas referência externa, nunca segredo real** |
| `consent_expires_at` | DateTime | |
| `last_synced_at` | DateTime | |
| `created_by_user_id` | FK → users | |
| `active` | Boolean | Default: true |
| `created_at` / `updated_at` | DateTime | |

**Índices:** `organization_id`, `provider_type`, `(organization_id, provider_type)`

### 2. `provider_webhook_events`
Eventos recebidos de providers com idempotência.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK → organizations | |
| `provider_type` | String(50) | |
| `provider_name` | String(50) | |
| `event_type` | String(100) | |
| `provider_event_id` | String(255) | |
| `idempotency_key` | String(255) | |
| `status` | Enum | received, processed, duplicate, failed, ignored |
| `payload` | JSON | **Sanitizado** |
| `headers_sanitized` | JSON | **Sanitizado** |
| `error_message` | Text | |
| `received_at` / `processed_at` / `created_at` | DateTime | |

**Unique constraint:** `(provider_type, provider_name, provider_event_id)` — idempotência

### 3. `open_finance_consents`
Consentimentos Open Finance (fake apenas nesta sprint).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK → organizations | |
| `user_id` | FK → users | |
| `provider_connection_id` | FK → provider_connections | |
| `provider_name` | String(50) | Default: `fake` |
| `external_consent_id` | String(255) | |
| `status` | Enum | pending, authorized, expired, revoked, failed |
| `scopes` | JSON | |
| `institution_name` / `institution_code` | String | |
| `authorization_url` | Text | URL fake gerada pelo provider fake |
| `expires_at` / `revoked_at` | DateTime | |
| `created_at` / `updated_at` | DateTime | |

### 4. `organization_audit_logs`
Logs de auditoria por organização.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK → organizations | |
| `actor_user_id` | FK → users | |
| `actor_role` | String(50) | |
| `action` | String(100) | provider_connection_created, consent_created, consent_revoked, webhook_received, transaction_auth_created/confirmed/expired/failed, etc. |
| `resource_type` / `resource_id` | String | |
| `provider_type` | String(50) | |
| `ip_hash` | String(64) | **SHA-256 hash, nunca IP cru** |
| `user_agent_hash` | String(64) | **SHA-256 hash, nunca user-agent cru** |
| `extra_data` | JSON | **Sanitizado** |
| `created_at` | DateTime | |

### 5. `transaction_authorizations`
Autenticação de transações sensíveis (fundação apenas).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `organization_id` | FK → organizations | |
| `user_id` | FK → users | |
| `action_type` | String(50) | |
| `resource_type` / `resource_id` | String | |
| `amount` | Numeric(12,2) | |
| `currency` | String(3) | Default: BRL |
| `status` | Enum | pending, confirmed, expired, cancelled, failed |
| `challenge_type` | Enum | password_6, biometric, pre_authorized |
| `code_hash` | String(255) | **SHA-256 hash do código de 6 dígitos, nunca texto puro** |
| `expires_at` | DateTime | Expiração curta (5 minutos) |
| `confirmed_at` | DateTime | |
| `failed_attempts` | Integer | Máximo: 3 |
| `extra_data` | JSON | |
| `created_at` / `updated_at` | DateTime | |

---

## Migration

**Arquivo:** `migrations/versions/k1f2g3h4i5j6_provider_foundation_consent_audit.py`  
**Revision:** `k1f2g3h4i5j6`  
**Revises:** `j0e1f2g3h4i5`  
**Compatível com:** SQLite e PostgreSQL

---

## Services Criados (5)

### ProviderConnectionService
`backend/app/services/provider_connection_service.py`

- `list_connections(organization_id)` — lista connections da org
- `create_connection(...)` — cria connection fake/sandbox
- `get_connection(organization_id, connection_id)` — busca por ID
- `get_active_connection(organization_id, provider_type)` — busca connection ativa por tipo
- `deactivate_connection(...)` — desativa connection
- `validate_provider_activation(provider_type, provider_name)` — valida feature flags

**Regras:**
- Provider real bloqueado se feature flag false
- Demo mode força fake
- Produção rejeita provider real não implementado
- Audit log registrado em cada operação

### ProviderWebhookService
`backend/app/services/provider_webhook_service.py`

- `record_event(...)` — registra webhook com sanitização
- `is_duplicate(...)` — verifica idempotência
- `mark_processed(event_id)` — marca como processado
- `mark_failed(event_id, error_message)` — marca como falho
- `sanitize_payload(payload)` — remove secrets/token/key/password
- `sanitize_headers(headers)` — remove Authorization/token/key

### OpenFinanceConsentService
`backend/app/services/open_finance_consent_service.py`

- `create_fake_consent(...)` — cria consentimento fake com URL fake
- `list_consents(organization_id)` — lista por org
- `revoke_consent(...)` — revoga consentimento
- `expire_old_consents()` — expira consentimentos vencidos

### OrganizationAuditService
`backend/app/services/organization_audit_service.py`

- `log_event(...)` — grava audit log com IP/user-agent hasheados
- `list_logs(organization_id, filters, pagination)` — busca com filtros
- `sanitize_metadata(metadata)` — remove chaves sensíveis
- `hash_value(value)` — SHA-256 hash

### TransactionAuthorizationService
`backend/app/services/transaction_authorization_service.py`

- `create_authorization(...)` — cria desafio de 6 dígitos, retorna código apenas em testing/demo
- `confirm_authorization(...)` — valida código contra hash
- `cancel_authorization(...)` — cancela autorização
- `expire_old_authorizations()` — expira autorizações vencidas

**Segurança:**
- Código de 6 dígitos hasheado com SHA-256
- Máximo de 3 tentativas
- Expiração de 5 minutos
- Em produção, código não é retornado na API
- Audit log registrado em cada operação

---

## Schemas Criados

`backend/app/schemas/provider_foundation.py`

- `ProviderConnectionCreate` / `ProviderConnectionResponse`
- `ProviderWebhookEventResponse`
- `OpenFinanceConsentCreate` / `OpenFinanceConsentResponse`
- `OrganizationAuditLogResponse`
- `TransactionAuthorizationCreate` / `TransactionAuthorizationConfirm` / `TransactionAuthorizationResponse`
- `ProviderStatusResponse` / `ProviderStatusItem`
- `FeatureFlagsResponse`

---

## Router e Endpoints

`backend/app/routers/providers.py` — Prefix: `/providers`

### Provider Status & Feature Flags
| Método | Endpoint | RBAC |
|---|---|---|
| GET | `/providers/status` | Qualquer membro |
| GET | `/providers/feature-flags` | Qualquer membro |

### Provider Connections
| Método | Endpoint | RBAC |
|---|---|---|
| GET | `/providers/connections` | owner/admin/finance |
| POST | `/providers/connections` | owner/admin |
| GET | `/providers/connections/{id}` | owner/admin/finance |
| POST | `/providers/connections/{id}/deactivate` | owner/admin |

### Open Finance Consents
| Método | Endpoint | RBAC |
|---|---|---|
| POST | `/providers/open-finance/consents/fake` | owner/admin |
| GET | `/providers/open-finance/consents` | owner/admin/finance |
| POST | `/providers/open-finance/consents/{id}/revoke` | owner/admin |

### Audit Logs
| Método | Endpoint | RBAC |
|---|---|---|
| GET | `/providers/audit-logs` | owner/admin |

### Transaction Authorizations
| Método | Endpoint | RBAC |
|---|---|---|
| POST | `/providers/transaction-authorizations` | owner/admin/finance |
| POST | `/providers/transaction-authorizations/{id}/confirm` | owner/admin/finance |
| POST | `/providers/transaction-authorizations/{id}/cancel` | owner/admin/finance |

### Webhook Fake (opcional)
| Método | Endpoint | Auth |
|---|---|---|
| POST | `/providers/webhooks/{provider_type}/{provider_name}` | Org header |

---

## RBAC Aplicado

- **owner/admin:** criar/desativar provider connection, criar/revogar consent, ver audit logs, criar/cancelar/confirmar transaction auth
- **finance:** listar connections, listar consents, criar/confirmar/cancelar transaction auth, ver status
- **viewer:** apenas provider status e feature flags

---

## Sanitização

### Payloads
Chaves sensíveis redacted: `password`, `secret`, `token`, `api_key`, `apikey`, `access_token`, `refresh_token`, `client_secret`, `code`, `authorization`, `credential`

### Headers
Headers sensíveis redacted: `authorization`, `token`, `secret`, `key`, `password`, `api_key`, `apikey`, `x-api-key`, `x-auth-token`

### IP / User-Agent
Hasheados com SHA-256 antes de armazenar.

---

## Admin Metrics

Endpoint `/admin/billing-metrics` atualizado com:
- `provider_connections_total`
- `provider_connections_active`
- `open_finance_consents_by_status`
- `webhook_events_by_status`
- `transaction_authorizations_by_status`
- `audit_logs_total`

---

## Testes

### Arquivos criados:
- `tests/test_provider_foundation.py` — 22 testes
- `tests/test_transaction_authorization.py` — 13 testes

### Cobertura:
- **ProviderConnection:** cria fake, lista, não mistura orgs, desativa, bloqueia real com flag false, demo mode força fake, produção rejeita real
- **OpenFinanceConsent:** cria fake, lista, revoga, não mistura orgs, audit log criado
- **ProviderWebhookEvent:** registra, sanitiza secrets, detecta duplicado, marca processed/failed
- **OrganizationAuditLog:** registra, lista, não mistura orgs, metadata sanitizado, IP/user-agent hasheados, filtra por action
- **TransactionAuthorization:** cria desafio, código não em texto puro, confirma correto, rejeita errado, limita tentativas, expira, não mistura orgs, audit log criado, produção não retorna código

### Resultado:
```
434 passed, 0 failed, 0 errors
```

---

## Validações Executadas

| Validação | Resultado |
|---|---|
| pytest (full suite) | ✅ 434 passed |
| alembic upgrade head | ✅ Passou |
| alembic heads | ✅ Single head: `k1f2g3h4i5j6` |
| audit_multitenant_integrity.py | ✅ 15 tables, 0 orphans |
| frontend build | ✅ Passou |
| docker-compose config | ✅ Válido |
| docker-compose.demo.yml config | ✅ Válido |

---

## Segurança

- Nenhum segredo commitado
- `secret_ref` armazena apenas referência externa, nunca segredo
- Código de transação hasheado com SHA-256
- IP e user-agent hasheados em audit logs
- Payloads e headers sanitizados em webhooks
- Metadata sanitizado em audit logs
- Feature flags reguladas continuam `false` por padrão
- Demo mode força providers fake
- Produção rejeita providers reais não implementados
- Produção não retorna código de transação

---

## Limitações

- **Nenhuma operação regulada real implementada**
- Open Finance consent é fake (gera URL fake)
- Transaction authorization não executa pagamento
- Webhook endpoint apenas registra evento, não processa
- Frontend não implementado nesta sprint (opcional)

---

## O Que Continua Fake/Sandbox

- Todos os providers (default: `fake`)
- Open Finance consents (URL fake, status authorized imediato)
- Transaction authorizations (código retornado em testing/demo)
- Webhook events (apenas registrados, não processados)

---

## Pendências

- **Frontend:** `ProviderStatusSection.tsx` não implementado (opcional nesta sprint)
- **Docker build:** Não executado (Docker daemon pode não estar disponível)
- **E2E:** Não executado (depende de Docker)

---

## Riscos Restantes

- Providers reais ainda não implementados (planejados para sprints futuras)
- Transaction authorization é fundação apenas — não conectada a operações reais
- Webhook processing real não implementado

---

## Recomendação para Sprint 15

1. **Implementar provider real de Open Finance** (ex: Pluggy/Belvo) com feature flag
2. **Conectar transaction authorization a operações reais** (Pix Out, pagamento de boletos)
3. **Implementar processamento de webhooks** com handlers por event_type
4. **Criar frontend `ProviderStatusSection`** com visualização de status e feature flags
5. **Adicionar KYC provider** (ex: Sumsub/Jumio) com feature flag
6. **Implementar DDA** (detecção de boletos) com provider real
