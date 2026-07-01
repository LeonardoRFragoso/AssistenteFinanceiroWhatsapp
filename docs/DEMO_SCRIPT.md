# Demo Script — PayFlow AI

Step-by-step presentation flow for demonstrating PayFlow AI features.

## Prerequisites

- Backend running (`uvicorn app.main:app --reload`)
- Frontend running (`npm run dev`)
- Redis running (for workers)
- WhatsApp connected (or simulated)
- Fake payment provider (default)

## Step 1: Login & Dashboard (2 min)

1. Navigate to `http://localhost:3000/login`
2. Login with demo credentials
3. Show the dashboard:
   - Summary cards (income, expenses, balance, transactions)
   - Plan usage bar
   - Recent transactions
   - Upcoming reminders

## Step 2: Charge Analytics (2 min)

1. Scroll to the analytics cards section
2. Show:
   - **Conversion rate** — percentage of charges that got paid
   - **Average payment time** — hours from creation to payment
   - **Total created** — total amount and count of charges
   - **Total paid** — total amount received
   - **Overdue rate** — percentage of pending charges that are overdue
   - **Cancelled count** — number of cancelled charges

## Step 3: Charges List & Pagination (3 min)

1. Scroll to the charges table
2. Demonstrate filters: All / Pending / Paid / Overdue / Cancelled
3. Use the search bar to find charges by customer name or description
4. Show pagination controls (if more than 10 charges)
5. Click "Copy link" on a charge — show the checkmark feedback
6. Click "Cancel" on a pending charge — show the spinner and status change

## Step 4: Export CSV & PDF (2 min)

1. Click "CSV" button — file downloads
2. Open the CSV file — show columns: id, customer_name, amount, status, etc.
3. Click "PDF" button — file downloads
4. Open the PDF — show:
   - Title and generation date
   - Applied filters
   - Summary table (totals, counts)
   - Detailed charges table

## Step 5: WhatsApp Integration (3 min)

1. Show the WhatsApp connection section
2. If connected, send a message like:
   - "Cobrar João Silva 150 reais pelo serviço de design"
3. Show the AI parsing the message and creating a charge
4. Show the new charge appearing in the dashboard
5. Demonstrate the payment link being sent via WhatsApp

## Step 6: Simulate Payment (2 min)

1. Copy the `provider_charge_id` from a pending charge
2. Call the simulation endpoint:
   ```
   POST /provider-webhooks/fake/pay/{provider_charge_id}
   ```
3. Show the charge status changing to "Paid" in the dashboard
4. Show analytics updating (conversion rate, total paid)

## Step 7: Charge Reminders (2 min)

1. Show a charge with a due date approaching
2. Trigger reminders manually (dev only):
   ```
   POST /charges/reminders/run
   ```
3. Show the reminder log entries

## Summary

- **Dashboard** with analytics, pagination, search, and export
- **WhatsApp** integration with AI-powered charge creation
- **Payment simulation** for testing the full flow
- **Automated reminders** for due/overdue charges
- **CSV and PDF exports** with filters and summary
