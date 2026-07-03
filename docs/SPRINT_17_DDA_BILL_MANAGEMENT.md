# Sprint 17: Fake DDA, Contas a Pagar e Bill Management

> **Date**: 2025-07-03
> **Status**: Complete
> **Commit base**: `25bbde4` (Sprint 16.1)

## Summary

Implemented a fake/sandbox layer for DDA (Débito Direto Autorizado) and accounts payable (contas a pagar), allowing PayFlow to detect simulated bills, list due dates, generate reminders, prepare fake payment intentions, and respond via WhatsApp about bills. This approximates the PayFlow experience to the Jota experience without executing real payments, real DDA, or real bank connections.

## What Was Implemented

### 1. Models (`backend/app/models/bills.py`)
- **DetectedBill**: Fake boleto/bill with beneficiary, amount, due date, barcode, digitable line, status, risk level, source, category
- **BillReminder**: Scheduled reminders for bills (WhatsApp, email, push)
- **BillPaymentIntent**: Fake payment intent (no execution) with transaction authorization link
- **BillEventLog**: Audit trail for all bill actions

### 2. Migration (`backend/migrations/versions/n3c4d5e6f7g8_fake_dda_bill_management.py`)
- Creates 4 new tables: `detected_bills`, `bill_reminders`, `bill_payment_intents`, `bill_event_logs`
- Indices on `organization_id`, `due_date`, `status`, `detected_bill_id`
- Unique constraint on `organization_id + provider_name + provider_bill_id`
- Compatible with SQLite and PostgreSQL

### 3. Fake DDA Provider (`backend/app/regulated_providers/dda_fake.py`)
- Generates 8-15 deterministic fake bills per organization
- Varied due dates (past, today, future), amounts, beneficiaries, categories, statuses
- Fake barcode and digitable line (not valid boletos)
- All data marked `is_demo_data=True`

### 4. Services
- **BillService**: Sync, list, get, ignore, mark-paid-manual, event logs
- **BillReminderService**: Schedule, list, cancel reminders
- **BillPaymentIntentService**: Create, authorize (fake), cancel, expire intents
- **BillSummaryService**: Summary, due-today, overdue, upcoming

### 5. Schemas (`backend/app/schemas/bills.py`)
- `BillStatusResponse`, `DetectedBillResponse`, `BillFilters`, `BillSummaryResponse`
- `BillReminderCreate`, `BillReminderResponse`
- `BillPaymentIntentResponse`, `BillPaymentIntentAuthorize`
- `BillMarkPaidManualRequest`, `BillIgnoreRequest`, `BillEventLogResponse`
- `SyncFakeBillsResponse`

### 6. Router (`backend/app/routers/bills.py`)
- `GET /bills/status` — provider status
- `POST /bills/sync/fake` — sync fake DDA bills
- `GET /bills` — list with filters
- `GET /bills/summary` — aggregate summary
- `GET /bills/due-today` — bills due today
- `GET /bills/overdue` — overdue bills
- `GET /bills/upcoming` — upcoming bills
- `GET /bills/{bill_id}` — get specific bill
- `POST /bills/{bill_id}/ignore` — ignore bill
- `POST /bills/{bill_id}/mark-paid-manual` — mark paid (no real payment)
- `POST /bills/{bill_id}/reminders` — create reminder
- `GET /bills/{bill_id}/reminders` — list reminders
- `POST /bills/reminders/{reminder_id}/cancel` — cancel reminder
- `POST /bills/{bill_id}/payment-intents/fake` — create fake payment intent
- `POST /bills/payment-intents/{intent_id}/authorize-fake` — authorize fake intent
- `POST /bills/payment-intents/{intent_id}/cancel` — cancel intent
- `GET /bills/{bill_id}/events` — event logs

### 7. WhatsApp Intents
- `list_due_bills`, `list_overdue_bills`, `list_bills_due_today`
- `bill_summary`, `search_bills`
- `create_bill_reminder`, `prepare_fake_bill_payment`
- `mark_bill_paid_manual`, `ignore_bill`
- All responses include demo/fake disclaimers

### 8. Frontend (`frontend/components/BillsSection.tsx`)
- Summary cards (overdue, due today, upcoming 7/30 days, total)
- Bill list with filters and search
- Action buttons: reminder, mark-paid, ignore, fake-payment-intent
- "Demo/Fake" badge on all data
- `data-testid` attributes for E2E testing

### 9. Admin Metrics
- `detected_bills_total`, `bills_overdue`, `bills_due_today`
- `fake_payment_intents_by_status`, `bill_reminders_by_status`
- `bill_event_logs_total`

### 10. Tests (70 new tests across 5 files)
- `test_bills_models.py` — model creation, enums, org isolation
- `test_bills_service.py` — sync, list, filter, search, ignore, mark-paid, summary
- `test_bills_router.py` — all endpoints, RBAC, 404 handling
- `test_bills_whatsapp.py` — all WhatsApp handlers, demo disclaimers
- `test_bill_payment_intents.py` — create, authorize, cancel, expire, org isolation

### 11. Audit Script
- Added `detected_bills`, `bill_reminders`, `bill_payment_intents`, `bill_event_logs` to `ORG_SCOPED_TABLES`

## What Was NOT Implemented

- No real DDA access (no Celcoin, Dock, QI Tech, or any real provider)
- No real boleto payment (no money movement)
- No Pix Out
- No digital account / BaaS
- No real payment initiation
- No real Open Finance integration for bill detection
- No real KYC
- No real barcode validation
- No real boleto registration

## Security

- All data is organization-scoped
- All fake data marked `is_demo_data=True`
- Feature flags `ENABLE_DDA` and `ENABLE_BILL_PAYMENT` remain `false` by default
- Provider default is `fake`
- Demo mode forces fake
- No bank credentials stored
- No sensitive data in responses
- All WhatsApp responses include demo/fake disclaimers
- "Prepare payment" does not execute payment
- Transaction authorization authorizes only fake intent, not real payment

## Test Results

- **70 new tests** across 5 files
- **0 failures, 0 errors**
- Total backend tests: 559 + 70 = 629
