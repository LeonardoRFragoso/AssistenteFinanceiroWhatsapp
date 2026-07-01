# Deployment Guide — PayFlow AI

This guide covers deploying PayFlow AI to production or demo environments.

## Architecture Overview

```
Frontend (Vercel) ──▶ Backend (Railway/Render) ──▶ PostgreSQL (managed)
                            │
                            ├──▶ Redis (managed) ──▶ RQ Worker
                            ├──▶ OpenAI API
                            └──▶ Twilio WhatsApp API
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Twilio account (for WhatsApp)
- OpenAI API key

## Option 1: Docker Compose Demo (local/portfolio)

```bash
docker-compose -f docker-compose.demo.yml up --build
```

This starts:
- Backend on port 8001 (with demo mode enabled, fake provider)
- Frontend on port 3001 (with demo login button)
- PostgreSQL on port 5433
- Redis on port 6380
- RQ Worker

Access:
- Frontend: http://localhost:3001
- Backend: http://localhost:8001/docs
- Demo login: click "Entrar como Demo" on login page

## Option 2: Production Deploy

### Backend (Railway/Render)

1. **Connect repository** to Railway or Render
2. **Set build command**: `pip install -r requirements.txt`
3. **Set start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Add PostgreSQL** addon (Railway) or database (Render)
5. **Add Redis** addon

### Frontend (Vercel)

1. **Import repository** to Vercel
2. **Set root directory**: `frontend`
3. **Set environment variables** (see below)
4. **Deploy**

### Environment Variables

#### Backend (required)

| Variable | Example | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` | PostgreSQL connection |
| `REDIS_URL` | `redis://host:6379/0` | Redis connection |
| `SECRET_KEY` | `<random-64-chars>` | JWT signing key |
| `OPENAI_API_KEY` | `sk-...` | OpenAI API key |
| `TWILIO_ACCOUNT_SID` | `AC...` | Twilio SID |
| `TWILIO_AUTH_TOKEN` | `...` | Twilio auth token |
| `TWILIO_WHATSAPP_NUMBER` | `whatsapp:+1555...` | Twilio WhatsApp number |
| `PAYFLOW_PAYMENT_PROVIDER` | `fake` | Provider (fake or mercado_pago) |
| `ENVIRONMENT` | `production` | Environment |
| `FRONTEND_URL` | `https://your-app.vercel.app` | Frontend URL for CORS |

#### Backend (optional)

| Variable | Default | Description |
|---|---|---|
| `ENABLE_DEMO_MODE` | `false` | Enable demo login |
| `DEMO_USER_EMAIL` | `demo@payflow.ai` | Demo user email |
| `DEMO_USER_PASSWORD` | `PayFlowDemo123` | Demo user password |
| `MERCADO_PAGO_ACCESS_TOKEN` | — | Mercado Pago sandbox token |
| `ENABLE_CHARGE_REMINDER_WORKER` | `false` | Enable reminder scheduler |
| `CHARGE_REMINDER_INTERVAL_MINUTES` | `60` | Reminder interval |

#### Frontend (required)

| Variable | Example | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://your-backend.railway.app` | Backend URL |
| `NEXT_PUBLIC_ENABLE_DEMO_MODE` | `false` | Show demo login button |
| `NEXT_PUBLIC_DEMO_EMAIL` | `demo@payflow.ai` | Demo email (display only) |

## Migrations

```bash
cd backend
alembic upgrade head
```

## Seed Demo Data

```bash
cd backend
python scripts/seed_demo_data.py
```

This creates a demo user with varied charges and transactions. Idempotent.

## Running Workers

```bash
cd backend
python worker.py
```

## Running Reminder Scheduler

```bash
cd backend
python -m app.jobs.reminder_scheduler
```

## Provider Configuration

### Fake Provider (default, demo)

```env
PAYFLOW_PAYMENT_PROVIDER=fake
```

No credentials needed. Charges are simulated.

### Mercado Pago Sandbox (opt-in)

```env
PAYFLOW_PAYMENT_PROVIDER=mercado_pago
MERCADO_PAGO_ACCESS_TOKEN=sandbox_token_here
MERCADO_PAGO_PUBLIC_KEY=sandbox_key_here
```

Only sandbox credentials. Never use production tokens in demo.

## Twilio WhatsApp Sandbox

1. Go to Twilio Console → WhatsApp Sandbox
2. Join sandbox with code: `join <code>`
3. Set webhook URL: `https://your-backend/webhook/whatsapp`
4. Configure environment variables

## Pre-Deploy Checklist

- [ ] `ENVIRONMENT=production` set
- [ ] `SECRET_KEY` is a strong random value
- [ ] `PAYFLOW_PAYMENT_PROVIDER` is `fake` for demo or `mercado_pago` for sandbox
- [ ] `ENABLE_DEMO_MODE=false` for production
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Redis is accessible
- [ ] Frontend `NEXT_PUBLIC_API_URL` points to backend
- [ ] CORS origins include frontend URL
- [ ] No secrets in `.env` are committed
- [ ] Twilio webhook URL configured
- [ ] OpenAI API key is valid
- [ ] RQ worker process running
- [ ] Health check `/health` returns healthy
- [ ] Readiness check `/health/ready` returns ready

## Health Checks

- `GET /` — API info
- `GET /health` — Full health check (DB, Redis, OpenAI, Twilio, Mercado Pago)
- `GET /health/ready` — Readiness probe (DB only)
- `GET /health/live` — Liveness probe

## Security Notes

- Demo mode should **never** be enabled in production — the app will fail at startup if `ENVIRONMENT=production` and `ENABLE_DEMO_MODE=true`
- Demo mode **always** requires `PAYFLOW_PAYMENT_PROVIDER=fake` — the app will fail at startup if demo mode is active with a non-fake provider
- Mercado Pago cannot be used when demo mode is active — the provider factory raises an error
- Demo password is for local/portfolio use only — `DEMO_USER_PASSWORD` is a fallback for dev environments
- `POST /auth/demo-login` returns 403 in production even if accidentally enabled
- `POST /demo/reset` checks environment, demo mode flag, and provider before executing
- No Pix Out, saque, conta digital, or BaaS is implemented
- All charges via WhatsApp require explicit user confirmation
- Secrets must be set via environment variables, never hardcoded
