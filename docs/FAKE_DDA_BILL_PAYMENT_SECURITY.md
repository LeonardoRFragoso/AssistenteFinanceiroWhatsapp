# Fake DDA & Bill Payment — Security Document

> **Sprint**: 17
> **Date**: 2025-07-03

## Overview

This document details the security measures implemented for the fake DDA and bill payment features in Sprint 17.

## Core Principles

1. **No real payment execution**: All payment flows are fake/sandbox only
2. **No real DDA access**: No real bank or fintech API is called
3. **Organization-scoped data**: All bills, reminders, and intents are scoped to an organization
4. **Demo data marking**: All fake data is marked `is_demo_data=True`
5. **User transparency**: All user-facing responses include demo/fake disclaimers

## Feature Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `ENABLE_DDA` | `false` | Enables DDA functionality |
| `ENABLE_BILL_PAYMENT` | `false` | Enables bill payment functionality |
| `DDA_PROVIDER_NAME` | `fake` | DDA provider name |
| `BILL_PAYMENT_PROVIDER_NAME` | `fake` | Bill payment provider name |
| `ENABLE_DEMO_MODE` | `false` | Forces all providers to fake mode |

## Data Security

### What is stored
- Bill metadata (title, beneficiary, amount, due date, category)
- Fake barcode and digitable line (not valid boletos)
- Payment intent metadata (fake reference, status, timestamps)
- Event logs (action, actor, timestamp)

### What is NOT stored
- Real bank credentials
- Real boleto data
- Real payment references
- Real transaction IDs
- Any real financial data

### Sanitization
- `raw_data_sanitized` field stores only sanitized metadata
- `metadata_sanitized` in event logs excludes sensitive information
- `beneficiary_document_masked` stores only masked document numbers

## Payment Intent Security

### What "Prepare Payment" does
- Creates a `BillPaymentIntent` record with status `draft`
- Generates a fake payment reference (e.g., `FAKE-ABC123DEF456`)
- Does NOT call any payment provider
- Does NOT move money
- Does NOT create a real transaction

### What "Authorize Fake Intent" does
- Changes intent status to `authorized_fake`
- Optionally creates a `TransactionAuthorization` record (fake)
- Does NOT execute payment
- Does NOT call any payment API
- Does NOT move money

### What "Authorize Fake Intent" does NOT do
- Does NOT pay the boleto
- Does NOT send Pix
- Does NOT initiate a bank transfer
- Does NOT create a real payment order

## RBAC

- **Owner/Admin/Finance**: Full access to all bill operations
- **Viewer**: No access to bill endpoints (403)
- **Cross-organization**: No access to other org's bills (404 or empty result)

## WhatsApp Security

- All responses include "Dados de demonstração" or "Demo" disclaimer
- "Prepare payment" messages say "Nenhum pagamento real será executado"
- "Mark paid" messages say "Nenhum pagamento real foi executado"
- No response ever says "payment made" or "payment executed"
- No response implies real money movement

## Audit Trail

Every bill action is logged in `bill_event_logs`:
- `bill_detected`, `bill_ignored`, `bill_marked_paid_manual`
- `reminder_scheduled`
- `payment_intent_created`, `payment_intent_authorized_fake`, `payment_intent_cancelled`
- `sync_fake_dda`

Additionally, organization-level audit logs are created via `OrganizationAuditService`.

## Future Considerations

When integrating real providers (Sprint 18+):
1. Real DDA access requires partnership with bank/fintech
2. Real boleto payment requires regulated payment provider
3. Real barcode validation requires provider API
4. LGPD compliance for real boleto data
5. Encryption for real financial data
6. PCI-DSS may apply if handling payment card data
