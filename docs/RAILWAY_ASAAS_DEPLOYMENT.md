# Railway Asaas Deployment Guide

## Overview

This document describes how to deploy PayFlow AI to Railway with Asaas sandbox provider enabled or disabled.

## Environment Variables

### Required (always)

| Variable | Example | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` | Async PostgreSQL URL |
| `SECRET_KEY` | 64+ random chars | Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `REDIS_URL` | `redis://host:6379/0` | Redis for rate limiting and queues |
| `PAYFLOW_PAYMENT_PROVIDER` | `fake` | Default provider. Set to `asaas` to use Asaas |

### Asaas (opt-in)

| Variable | Default | Notes |
|---|---|---|
| `ENABLE_ASAAS_CHARGE_PROVIDER` | `false` | Must be `true` to use Asaas |
| `ASAAS_ENVIRONMENT` | `sandbox` | `sandbox` or `production` |
| `ASAAS_API_BASE_URL` | `https://sandbox.asaas.com/api/v3` | Sandbox default. Production: `https://api.asaas.com/api/v3` |
| `ASAAS_API_KEY` | (empty) | Required if `ENABLE_ASAAS_CHARGE_PROVIDER=true` |
| `ASAAS_WEBHOOK_TOKEN` | (empty) | Required for webhook validation. 32+ characters |

### Deploy with Asaas DISABLED (default)

No Asaas env vars needed. The app runs with the fake provider:

```env
PAYFLOW_PAYMENT_PROVIDER=fake
ENABLE_ASAAS_CHARGE_PROVIDER=false
```

The app will NOT attempt to connect to Asaas. All charges use the sandbox fake provider.

### Deploy with Asaas ENABLED (sandbox)

```env
PAYFLOW_PAYMENT_PROVIDER=asaas
ENABLE_DEMO_MODE=false
ENABLE_ASAAS_CHARGE_PROVIDER=true
ASAAS_ENVIRONMENT=sandbox
ASAAS_API_BASE_URL=https://sandbox.asaas.com/api/v3
ASAAS_API_KEY=<your-sandbox-api-key>
ASAAS_WEBHOOK_TOKEN=<your-webhook-token-32+chars>
```

If `ASAAS_API_KEY` is missing while `ENABLE_ASAAS_CHARGE_PROVIDER=true`, the app will raise a `RuntimeError` when trying to create a charge. The healthcheck will still pass — only charge creation fails with a clear error.

### Webhook Configuration

In the Asaas sandbox dashboard, configure the webhook:

```
URL: https://<your-railway-domain>/provider-webhooks/asaas
Auth Token: <same value as ASAAS_WEBHOOK_TOKEN>
Events: PAYMENT_CREATED, PAYMENT_CONFIRMED, PAYMENT_RECEIVED, PAYMENT_OVERDUE, PAYMENT_DELETED, PAYMENT_RESTORED, PAYMENT_REFUNDED
```

### Healthcheck

The healthcheck endpoint (`/health/ready`) does NOT require Asaas to be configured. It checks database and Redis connectivity only.

### Migration

The migration `l2a3b4c5d6e7` (add Asaas charge fields) runs automatically via `entrypoint.sh`. No manual intervention needed.

### Rollback to Fake Provider

To disable Asaas and revert to fake provider:

1. Set `PAYFLOW_PAYMENT_PROVIDER=fake` in Railway env vars
2. Set `ENABLE_ASAAS_CHARGE_PROVIDER=false`
3. Redeploy

Existing charges created with Asaas will remain in the database with their `provider` field set to `asaas`. The sync endpoint will return a warning for those charges since the Asaas provider won't be available.

### Dockerfile

The `backend/Dockerfile` expects the build context to be the repository root (Railway default). It copies `backend/` into the container. No changes needed for Asaas — all Asaas code is in the backend Python package.
