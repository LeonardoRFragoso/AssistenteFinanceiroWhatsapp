# Security Hardening — PayFlow AI

## Demo Mode Security (Sprint 5.1)

- **Demo mode never runs in production**: `validate_demo_mode()` fails startup if `ENVIRONMENT=production` and `ENABLE_DEMO_MODE=true`
- **Demo mode requires fake provider**: startup fails if `ENABLE_DEMO_MODE=true` and `PAYFLOW_PAYMENT_PROVIDER != fake`
- **Mercado Pago blocked in demo mode**: `get_payment_provider("mercado_pago")` raises `RuntimeError` when demo mode is active
- **demo-login blocked in production**: Returns HTTP 403 if `ENVIRONMENT=production`
- **demo/reset defense in depth**: Checks environment, demo mode flag, and provider before executing

## Rate Limiting (Sprint 6)

### User Rate Limiting

Authenticated endpoints are rate-limited per user:

| Endpoint | Limiter | Default limit |
|---|---|---|
| `POST /charges` | `charges_limiter` | 20/min |
| `POST /charges/{id}/cancel` | `charges_limiter` | 20/min |
| `POST /charges/reminders/run` | `charges_limiter` | 20/min |
| `GET /charges/export.csv` | `exports_limiter` | 10/min |
| `GET /charges/export.pdf` | `exports_limiter` | 10/min |
| `POST /demo/reset` | `demo_reset_limiter` | 5/hour |

Configuration:

```env
USER_RATE_LIMIT_ENABLED=true
USER_RATE_LIMIT_CHARGES_PER_MINUTE=20
USER_RATE_LIMIT_EXPORTS_PER_MINUTE=10
USER_RATE_LIMIT_DEMO_RESET_PER_HOUR=5
```

- Uses Redis when available
- Falls back to in-memory in development/test (when `REDIS_URL` is not set)
- Returns HTTP 429 with clear message
- Disabled entirely when `USER_RATE_LIMIT_ENABLED=false`

### Webhook Rate Limiting

All webhook endpoints are rate-limited per IP + provider:

```env
WEBHOOK_RATE_LIMIT_PER_MINUTE=60
```

- Skipped in testing environment
- Applied to: Twilio WhatsApp, Mercado Pago, fake provider

### IP Rate Limiting (existing)

Global IP-based rate limiting middleware: 100 requests/minute per IP.

## Webhook Hardening

### Twilio WhatsApp Webhook

- **Signature validation mandatory in production**: If `TWILIO_VALIDATE_SIGNATURE=false` in production, webhook returns 403
- **Bypass only in development**: `TWILIO_VALIDATE_SIGNATURE=false` is accepted only in non-production environments
- **Rate limited**: Per IP, 60 req/min (configurable)

### Mercado Pago Webhook

- **Signature validation required**: `x-signature` and `x-request-id` headers must be present and valid
- **Missing headers**: Returns 401
- **Invalid signature**: Returns 401
- **Idempotency**: Duplicate events (same `external_id` already processed) return `{"status": "duplicate"}` without re-processing
- **No sensitive payload logged**: Only `provider`, `event_type`, `external_id` are logged
- **Rate limited**: Per IP, 60 req/min

### Fake Provider Webhook

- **Rate limited**: Per IP, 60 req/min
- **Available in all environments** (for development/testing)
- **No signature required** (sandbox only)

## Admin Metrics Security

- `GET /admin/system-metrics` requires admin authentication
- Admin access controlled by `ADMIN_EMAILS` environment variable
- No personal data exposed (no emails, phones, passwords, tokens)
- Only aggregate counts and uptime

## Sentry Data Sanitization

- `before_send` hook strips tokens, passwords, API keys, auth headers
- No full webhook payloads sent to Sentry
- No phone numbers or WhatsApp message content in breadcrumbs

## Pre-Production Checklist

- [ ] `ENVIRONMENT=production`
- [ ] `ENABLE_DEMO_MODE=false`
- [ ] `PAYFLOW_PAYMENT_PROVIDER` is `fake` or `mercado_pago` (with sandbox credentials)
- [ ] `TWILIO_VALIDATE_SIGNATURE=true`
- [ ] `USER_RATE_LIMIT_ENABLED=true`
- [ ] `SENTRY_DSN` set (optional but recommended)
- [ ] `ADMIN_EMAILS` configured
- [ ] `SECRET_KEY` is a strong random value (64+ chars)
- [ ] No secrets in `.env` committed to git
- [ ] Redis available for rate limiting (or accept in-memory fallback)
