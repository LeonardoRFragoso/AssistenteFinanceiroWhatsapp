# Asaas Provider Security — PayFlow AI

> Sprint 15.1 — Asaas Provider Hardening

## Receive-Only Operations

The Asaas integration is **receive-only**. The following operations are **NOT implemented** and will never be called:

- **Pix Out** — no money movement out of the platform
- **Saque** — no withdrawals
- **Pagamento de boleto** — no bill payment
- **Conta digital** — no banking operations
- **Open Finance** — not implemented
- **DDA** — not implemented
- **KYC** — not implemented
- **BaaS** — not implemented

Only these operations are supported:
- Create customer (sandbox CPF generated)
- Create payment (PIX/BOLETO/UNDEFINED)
- Get payment status
- Get Pix QR code
- Cancel payment (DELETE)
- Parse webhook events

## API Key Handling

- `ASAAS_API_KEY` is loaded from environment variables only
- Never hardcoded, never committed to git
- Sent via `access_token` HTTP header to Asaas API
- **Never logged** — `_sanitize_for_log` redacts `access_token`, `api_key`, `token`, `secret`, `password`, `authorization`, `credential`, `client_secret` from all log output
- Not returned in any API response or error message

## Webhook Token Validation

- `ASAAS_WEBHOOK_TOKEN` env var required for webhook acceptance
- Validated via `asaas-access-token` header on every webhook request
- Missing or mismatched token → 401 Unauthorized
- Missing token in production → rejected (no silent acceptance)
- Missing token in sandbox/dev → rejected with warning log

## Webhook Idempotency

- Every webhook event is checked by `idempotency_key`:
  - Uses `event_id` from Asaas payload if present
  - Falls back to composite key: `asaas_{payment_id}_{event_name}`
- Duplicate events return `{"status": "duplicate"}` without re-processing
- Provider events are stored in `provider_events` table with `processed=True`
- Duplicate paid events do not trigger double notifications or double usage increments

## Payload Sanitization

- Webhook payloads are sanitized via `sanitize_webhook_data` before storage
- Sensitive keys (`token`, `secret`, `password`, `api_key`, etc.) are replaced with `[REDACTED]`
- `AsaasPaymentProvider.parse_webhook_event` sanitizes `raw_data` via `_sanitize_webhook_payload`
- Headers are lowercased and only used for token validation, never stored

## Audit Logging

- `log_webhook_received` called for every webhook event
- `log_payment_confirmed` called when a charge transitions to paid
- `log_charge_created` called on charge creation
- Sync endpoint logs user ID, charge ID, and resulting status
- All audit logs use sanitized metadata

## Multi-Tenant Isolation

- All charges are scoped by `organization_id`
- `ChargeService.create_charge` resolves org via `resolve_organization_id`
- `ChargeService.sync_provider_status` filters by `organization_id`
- `ChargeService.process_payment_event` finds charge by `provider_charge_id` — the charge belongs to exactly one org
- Webhook processing does not cross org boundaries
- Provider factory is global (env-based), but charge records are org-scoped

## Feature Flag Enforcement

- `ENABLE_ASAAS_CHARGE_PROVIDER` defaults to `false`
- `AsaasPaymentProvider.__init__` raises `RuntimeError` if flag is false
- `AsaasPaymentProvider.__init__` raises `RuntimeError` if demo mode is active
- `AsaasPaymentProvider.__init__` raises `RuntimeError` if `ASAAS_API_KEY` is missing
- Provider factory raises `RuntimeError` for unknown providers in production (no silent fallback)
- `AsaasClient.__init__` raises `AsaasApiError` if API key is missing
- `AsaasClient.__init__` raises `AsaasApiError` if sandbox URL detected in production environment

## Billing Usage Safety

- `SaaSBillingService.increment_usage` is only called **after** successful charge creation
- If `ChargeService.create_charge` raises `RuntimeError`, usage is NOT incremented
- Webhook duplicate events do NOT increment usage (usage is only for creation, not status updates)
- Sync endpoint does NOT increment usage

## Timeout and Retry

- All Asaas API calls have 30-second timeout
- Retries only on 5xx and timeout errors (safe retries)
- No retries on 4xx errors (client errors are not retried)
- Invalid JSON responses raise `AsaasApiError` with status code
- Maximum 2 retries with exponential backoff (1s, 2s)

## Error Handling

- `AsaasApiError` includes `status_code` and optional `detail`
- Provider errors in `create_charge` raise `RuntimeError` → 502 to client
- Provider errors in `sync_provider_status` raise `RuntimeError` → 502 to client
- Provider errors in `get_charge` return `None` for 404, raise for other errors
- Partial API responses (missing `id`) raise `RuntimeError` with clear message
- Webhook processing errors return 500 without exposing internal details
