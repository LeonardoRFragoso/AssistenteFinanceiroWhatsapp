# Production Workers Guide

This document describes how to run PayFlow AI workers in production.

## Overview

PayFlow AI uses background workers for:

- **Charge reminders** — periodically checks for due/overdue charges and sends WhatsApp reminders.
- **WhatsApp delivery** — sends payment links and notifications via Twilio.
- **Insights/notifications** — AI-generated financial insights (optional).

## Architecture

```
┌─────────────┐     ┌───────────┐     ┌──────────────┐
│  API Server │────▶│  Redis    │────▶│  RQ Worker   │
│  (uvicorn)  │     │  Queue    │     │  (worker.py) │
└─────────────┘     └───────────┘     └──────────────┘
                                            │
                            ┌───────────────┼──────────────┐
                            ▼               ▼              ▼
                      WhatsApp        Insights       Notifications
                      Queue           Queue          Queue
```

The reminder scheduler enqueues jobs into Redis queues. RQ workers process them.

## Running the Scheduler

### Option 1: Standalone CLI (recommended for Docker/K8s)

```bash
cd backend
source .venv/bin/activate

# Run in foreground (Ctrl+C to stop)
python -m app.jobs.reminder_scheduler

# Or with custom interval
CHARGE_REMINDER_INTERVAL_MINUTES=30 python -m app.jobs.reminder_scheduler
```

### Option 2: Embedded in API server (development only)

Set `ENABLE_CHARGE_REMINDER_WORKER=true` in your `.env`. The scheduler will start
automatically when the API server launches.

```bash
ENABLE_CHARGE_REMINDER_WORKER=true
CHARGE_REMINDER_INTERVAL_MINUTES=60
```

### Option 3: Docker Compose

The `docker-compose.yml` includes a `reminder-scheduler` service:

```bash
docker-compose up -d reminder-scheduler
```

## Running RQ Workers

RQ workers process queued jobs (WhatsApp messages, insights, notifications).

```bash
cd backend
source .venv/bin/activate

# Start a worker for all queues
python worker.py

# Or specify queues
python worker.py whatsapp insights notifications charge_reminders
```

### Docker Compose

```bash
docker-compose up -d worker
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENABLE_CHARGE_REMINDER_WORKER` | `false` | Enable embedded scheduler in API server |
| `CHARGE_REMINDER_INTERVAL_MINUTES` | `60` | Minutes between reminder runs |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `TWILIO_ACCOUNT_SID` | — | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | — | Twilio auth token |
| `TWILIO_WHATSAPP_NUMBER` | — | Twilio WhatsApp sender number |

## Production Checklist

- [ ] Redis is running and accessible
- [ ] RQ worker process is running (`python worker.py`)
- [ ] Reminder scheduler is running (standalone or embedded)
- [ ] Twilio credentials are set (or WhatsApp delivery will be simulated)
- [ ] `ENVIRONMENT=production` is set
- [ ] `PAYFLOW_PAYMENT_PROVIDER` is set to `fake` or `mercado_pago`
- [ ] Log monitoring is in place
- [ ] Process manager (systemd, supervisor, Docker) restarts workers on failure

## Process Management

### systemd

```ini
# /etc/systemd/system/payflow-scheduler.service
[Unit]
Description=PayFlow AI Reminder Scheduler
After=network.target redis.service

[Service]
Type=simple
User=payflow
WorkingDirectory=/opt/payflow/backend
EnvironmentFile=/opt/payflow/backend/.env
ExecStart=/opt/payflow/backend/.venv/bin/python -m app.jobs.reminder_scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/payflow-worker.service
[Unit]
Description=PayFlow AI RQ Worker
After=network.target redis.service

[Service]
Type=simple
User=payflow
WorkingDirectory=/opt/payflow/backend
EnvironmentFile=/opt/payflow/backend/.env
ExecStart=/opt/payflow/backend/.venv/bin/python worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable payflow-scheduler payflow-worker
sudo systemctl start payflow-scheduler payflow-worker
```

## Monitoring

- Check scheduler logs: `journalctl -u payflow-scheduler -f`
- Check worker logs: `journalctl -u payflow-worker -f`
- Redis queue inspection: `rq info -u redis://localhost:6379/0`
