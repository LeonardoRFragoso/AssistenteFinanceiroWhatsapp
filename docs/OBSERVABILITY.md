# Observability — PayFlow AI

## Sentry (Backend)

Sentry integration is **optional**. The app starts normally without it.

### Configuration

```env
SENTRY_DSN=                          # Leave empty to disable
SENTRY_ENVIRONMENT=development       # or production, staging
SENTRY_TRACES_SAMPLE_RATE=0.0        # 0.0 = no traces, 1.0 = all
```

### How it works

- `init_sentry()` is called at startup in `main.py` lifespan
- If `SENTRY_DSN` is empty, Sentry is **not initialized** — no errors, no crash
- A `before_send` hook (`_sanitize_event`) strips sensitive data:
  - Tokens, passwords, API keys, auth headers are redacted
  - No full webhook payloads, phone numbers, or WhatsApp messages are sent
- Integrations: `FastApiIntegration`, `RedisIntegration`

### Sentry (Frontend — optional)

To enable Sentry on the frontend, set:

```env
NEXT_PUBLIC_SENTRY_DSN=
```

Frontend Sentry is optional and not required for the app to function.

## Structured Audit Logging

The backend uses `backend/app/core/audit_logger.py` for structured logging of critical events.

### Logged events

| Event | Function | Safe fields |
|---|---|---|
| Charge created | `log_charge_created` | `user_id`, `charge_id`, `provider`, `amount` |
| PendingAction confirmed | `log_pending_action_confirmed` | `user_id`, `pending_action_id`, `action_type` |
| Webhook received | `log_webhook_received` | `provider`, `event_type`, `external_id` |
| Payment confirmed | `log_payment_confirmed` | `user_id`, `charge_id`, `provider` |
| Provider failure | `log_provider_failure` | `provider`, `charge_id`, `error` |
| Export CSV/PDF | `log_export` | `user_id`, `format`, `status`, `count` |
| Demo login | `log_demo_login` | `user_id`, `email` |
| Demo reset | `log_demo_reset` | `user_id`, `charges_created`, `transactions_created` |
| Reminder job | `log_reminder_job` | `run_count`, `reminders_sent` |
| Rate limit hit | `log_rate_limit_hit` | `user_id`, `endpoint`, `limit` |

### What is NEVER logged

- Tokens, API keys, passwords
- Full webhook payloads
- Complete phone numbers (only masked)
- WhatsApp message content
- Financial values per user (only aggregate counts in admin metrics)

## Log Sanitizer

`backend/app/utils/log_sanitizer.py` provides utilities to sanitize dicts before logging:

- `sanitize_webhook_data()` — keeps only `id`, `type`, `action`, `status`, `event_type`
- `sanitize_payment_data()` — keeps only `id`, `status`, `amount`, `currency`, `payment_method_type`
- `sanitize_user_data()` — keeps only `id`, `created_at`, `plan`

## Admin System Metrics

`GET /admin/system-metrics` — admin-only endpoint returning:

- `total_users`, `total_charges`, `paid_charges`, `pending_charges`, `overdue_charges`
- `total_provider_events`, `processed_provider_events`
- `total_reminders_sent`, `total_delivery_logs`
- `uptime_seconds`

No personal data, no per-user financial values, no tokens.
