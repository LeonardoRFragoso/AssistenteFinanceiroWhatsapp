# E2E Testing — PayFlow AI

## Playwright Setup

E2E tests use [Playwright](https://playwright.dev/) and are located in `frontend/e2e/`.

### Prerequisites

- Node.js 18+
- Frontend dependencies installed (`npm install`)
- Playwright browsers installed (`npx playwright install`)

### Running E2E tests

```bash
cd frontend

# Install Playwright browsers (first time only)
npx playwright install chromium

# Run all E2E tests
npm run test:e2e

# Run with UI mode (interactive)
npm run test:e2e:ui
```

### Configuration

`frontend/playwright.config.ts`:

- **Base URL**: `http://localhost:3000` (or `E2E_BASE_URL` env var)
- **Browser**: Chromium
- **Auto-starts dev server** if `E2E_BASE_URL` is not set
- **Retries**: 2 on CI, 0 locally

### Environment variables

```env
NEXT_PUBLIC_ENABLE_DEMO_MODE=true   # Required for demo login tests
NEXT_PUBLIC_API_URL=http://localhost:8000
E2E_BASE_URL=http://localhost:3000  # Optional: skip auto-starting dev server
```

## Test Scenarios

`frontend/e2e/demo.spec.ts` covers:

1. **Landing page loads** — Verifies h1 is visible
2. **Demo login button visible** — Checks "Entrar como Demo" button when demo mode enabled
3. **Demo login works** — Clicks demo button, verifies redirect to dashboard
4. **Dashboard loads** — Sets mock token, verifies dashboard page structure
5. **Main cards appear** — Verifies summary cards are visible
6. **Charges list appears** — Verifies charges section is present
7. **Overdue filter works** — Clicks "Vencidas" filter
8. **Search by customer** — Fills search input
9. **Export CSV** — Triggers CSV download
10. **Export PDF** — Triggers PDF download

### Test strategy

- Tests use a **mock token** in localStorage to simulate authentication
- Tests are **resilient** — they check for element visibility before interacting
- Tests do **not** depend on Mercado Pago, Twilio, or OpenAI
- Tests work with the **fake provider** and demo environment

## CI Integration

E2E tests run in CI as a **manual job** via `workflow_dispatch`:

```yaml
e2e-tests:
  if: github.event_name == 'workflow_dispatch'
```

This prevents E2E from blocking regular PRs while allowing manual execution.

### Running E2E in CI

1. Go to GitHub Actions → CI workflow
2. Click "Run workflow"
3. Select the branch
4. The E2E job will:
   - Install dependencies
   - Install Playwright browsers
   - Build frontend with demo mode enabled
   - Run Playwright tests

## Limitations

- E2E tests require the frontend dev server (auto-started or via `E2E_BASE_URL`)
- Full stack E2E (with backend) requires Docker Compose or manual backend startup
- Tests are designed to be resilient but may need adjustment if UI changes significantly
