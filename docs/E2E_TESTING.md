# E2E Testing — PayFlow AI

## Playwright Setup

E2E tests use [Playwright](https://playwright.dev/) and are located in `frontend/e2e/`.

### Prerequisites

- Node.js 18+
- Frontend dependencies installed (`npm install`)
- Playwright browsers installed (`npx playwright install`)
- Docker and Docker Compose (for full demo stack)

## Running E2E — Option A: Full Demo Stack (recommended)

This starts the complete demo stack (Postgres, Redis, backend, frontend) via Docker Compose.

```bash
# 1. Start the demo stack
docker-compose -f docker-compose.demo.yml up -d --build

# 2. Wait for services to be ready
./scripts/wait-for-url.sh http://localhost:8001/health/ready 120
./scripts/wait-for-url.sh http://localhost:3001 120

# 3. Install Playwright browsers (first time only)
cd frontend && npx playwright install chromium

# 4. Run E2E tests against the demo stack
E2E_BASE_URL=http://localhost:3001 npm run test:e2e

# 5. Tear down the stack
cd .. && docker-compose -f docker-compose.demo.yml down -v
```

### Demo stack services

| Service | Port | URL |
|---|---|---|
| Frontend | 3001 | `http://localhost:3001` |
| Backend | 8001 | `http://localhost:8001` |
| Postgres | 5433 | — |
| Redis | 6380 | — |

The demo stack uses:
- `PAYFLOW_PAYMENT_PROVIDER=fake` (no real payments)
- `ENABLE_DEMO_MODE=true` (demo login enabled)
- `NEXT_PUBLIC_ENABLE_DEMO_MODE=true` (demo button visible)
- Pre-seeded demo data via `scripts/seed_demo_data.py`

## Running E2E — Option B: Frontend Dev Only

For quick local iteration without Docker:

```bash
cd frontend

# Install Playwright browsers (first time only)
npx playwright install chromium

# Run all E2E tests (auto-starts dev server)
npm run test:e2e

# Run with UI mode (interactive)
npm run test:e2e:ui
```

This mode auto-starts `npm run dev` on port 3000. Tests will use mock tokens for auth — dashboard data may not load without a running backend.

### Configuration

`frontend/playwright.config.ts`:

- **Base URL**: `http://localhost:3000` (or `E2E_BASE_URL` env var)
- **Browser**: Chromium
- **Auto-starts dev server** if `E2E_BASE_URL` is not set
- **Retries**: 2 on CI, 0 locally
- **Timeout**: 60s per test, 15s per expect
- **Workers**: 1 (sequential, avoids race conditions)

### Environment variables

```env
E2E_BASE_URL=http://localhost:3001  # Set to use external server (skip auto-start)
NEXT_PUBLIC_ENABLE_DEMO_MODE=true   # Required for demo login button
NEXT_PUBLIC_API_URL=http://localhost:8001  # Backend API URL
```

## Test Scenarios

`frontend/e2e/demo.spec.ts` covers 10 scenarios:

1. **Landing page loads** — Verifies h1 is visible
2. **Demo login button visible** — Checks "Entrar na Demo" button on landing
3. **Demo login flow works** — Clicks "Entrar como Demo" on /login, verifies redirect to /dashboard
4. **Dashboard renders** — Verifies `<main>` element is visible after login
5. **Charge summary cards** — Verifies "Pendentes" and "Vencidas" cards appear
6. **Charges table** — Verifies charges heading and `<table>` are visible
7. **Filter by Vencidas** — Clicks the "Vencidas" filter button
8. **Search by customer** — Fills search input and clicks "Buscar"
9. **Export CSV** — Clicks CSV export button
10. **Export PDF** — Clicks PDF export button

### Test strategy

- Tests use the **real demo login flow** (`/auth/demo-login` endpoint)
- Tests do **not** depend on Twilio, OpenAI, or Mercado Pago
- Tests work with the **fake provider** and demo environment
- Tests use **role-based selectors** (`getByRole`, `getByPlaceholder`) for stability
- Tests run **sequentially** (1 worker) to avoid race conditions
- Tests have **generous timeouts** (30s for navigation, 20s for dashboard elements)

## CI Integration

E2E tests run in CI as a **manual job** via `workflow_dispatch`:

```yaml
e2e-tests:
  if: github.event_name == 'workflow_dispatch'
```

### CI E2E workflow

1. Go to GitHub Actions → CI workflow
2. Click "Run workflow"
3. Select the branch
4. The E2E job will:
   - Install frontend dependencies
   - Install Playwright browsers
   - Start `docker-compose.demo.yml` (builds all services)
   - Wait for backend at `http://localhost:8001/health/ready` (120s timeout)
   - Wait for frontend at `http://localhost:3001` (120s timeout)
   - Run Playwright tests with `E2E_BASE_URL=http://localhost:3001`
   - Upload Playwright HTML report as artifact
   - Tear down the demo stack (even on failure)

### Wait script

`scripts/wait-for-url.sh` polls a URL every 2 seconds until it returns HTTP 2xx or times out:

```bash
./scripts/wait-for-url.sh <url> <timeout_seconds>
```

## Limitations

- Full stack E2E requires Docker and Docker Compose
- Frontend dev-only mode uses mock tokens — dashboard data won't load without backend
- Tests depend on demo seed data being present (auto-seeded by demo compose)
- Tests are designed for the demo UI in Portuguese — selectors match Portuguese labels
