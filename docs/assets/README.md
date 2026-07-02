# Screenshots

This directory contains screenshots of the PayFlow AI application for documentation and portfolio purposes.

## Files

| File | Description |
|---|---|
| `landing.png` | Landing page with hero section and CTA |
| `login-demo.png` | Login page with demo button |
| `dashboard-overview.png` | Dashboard with summary cards and charts |
| `charges-table.png` | Charges table with filters and pagination |
| `analytics.png` | Analytics cards (conversion rate, overdue rate, etc.) |
| `export-pdf.png` | Export CSV/PDF buttons in charges section |
| `e2e-report.png` | Playwright E2E test report |

## How to generate

```bash
# Start demo stack
docker-compose -f docker-compose.demo.yml up -d --build
./scripts/wait-for-url.sh http://localhost:8001/health/ready 120
./scripts/wait-for-url.sh http://localhost:3001 120

# Generate screenshots
cd frontend
npx playwright test e2e/screenshots.spec.ts

# Screenshots are saved to ../../docs/assets/
cd ..
docker-compose -f docker-compose.demo.yml down -v
```
