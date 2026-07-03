# Sprint 12.1 — Billing Hardening

## Objective

Stabilization and security sprint focused on hardening the SaaS billing system implemented in Sprint 12. No new major features — only consistency, idempotency, security, and organizational isolation improvements.

## Changes Made

### 1. Seed Plans Idempotency
- **File**: `backend/app/services/saas_billing_service.py`
- `seed_plans()` now updates existing plans with latest definition values instead of skipping them
- Ensures plan definitions are always in sync with code
- No duplicate plans on repeated calls

### 2. Downgrade Protection
- **File**: `backend/app/services/saas_billing_service.py`
- `change_plan()` now checks if current usage exceeds target plan limits before downgrading
- Blocks downgrade with `ValueError("current_usage_exceeds_target_plan")` including details of exceeded resources
- Only applies to downgrades (price decrease); upgrades are always allowed
- Checks: charges, customers, templates, recurring tasks

### 3. Entitlements Payload Completeness
- **File**: `backend/app/services/entitlements_service.py`
- All entitlement responses now include `feature` field identifying the resource being checked
- All responses include `plan_name` (human-readable plan name)
- Feature-flag denials (OCR, PDF, analytics, collection rules) use `_feature_denied_response` without `limit`/`current_usage` (not applicable)
- Usage-limit denials use `_denied_response` with `limit`, `current_usage`, `feature`, `plan`, `plan_name`

### 4. Usage Counter Integrity
- **Files**: `backend/app/routers/webhook.py`
- WhatsApp message usage increment moved to **after** conversation log creation (post-success)
- OCR usage increment moved to **after** successful document analysis
- No usage increments on blocked or failed operations

### 5. WhatsApp Billing Messages
- **File**: `backend/app/routers/webhook.py`
- OCR blocked message now includes plan name, feature description, and clear instructions
- Charge limit message now includes plan name, limit, current usage, and clear "no action executed" statement
- All messages in clear PT-BR

### 6. Billing Provider Factory Hardening
- **File**: `backend/app/billing_providers/factory.py`
- Production environment rejects unknown providers with `ValueError`
- Demo mode (`ENABLE_DEMO_MODE=True`) always forces fake provider
- Development/testing falls back to fake with warning for unknown providers
- Sandbox providers (stripe_sandbox, mercado_pago_sandbox) log warning and fall back to fake

### 7. BillingEvent Idempotency
- **File**: `backend/app/services/saas_billing_service.py`
- `_record_event()` now accepts `provider_event_id` parameter
- If `provider_event_id` is provided, checks for duplicate before creating
- Duplicate events are skipped with log warning
- Payload sanitization: `_sanitize_payload()` redacts fields containing `secret`, `token`, `key`, `password`, `api_key`, `secret_key`

### 8. List Plans Endpoint
- **File**: `backend/app/routers/billing_saas.py`
- `GET /saas-billing/plans` now includes `max_whatsapp_messages_per_month` in response

### 9. Frontend BillingSection Hardening
- **File**: `frontend/components/BillingSection.tsx`
- Added `data-testid` attributes: `billing-section`, `current-plan-card`, `usage-meters`, `plan-card-{code}`, `change-plan-button`, `billing-sandbox-warning`
- Role-based button visibility: only `owner`/`admin` can see change plan, checkout, cancel, reactivate buttons
- Error state with retry button when fetch fails and no data is loaded
- Loading state with spinner
- Fetches user role from `organizationsAPI.list()` to determine `canManage`

### 10. Admin Billing Metrics
- **File**: `backend/app/routers/admin.py`
- New endpoint: `GET /admin/billing-metrics`
- Returns: subscriptions by status, organizations by plan, usage totals across all orgs, total billing events

### 11. E2E Billing Tests
- **File**: `frontend/e2e/billing.spec.ts`
- 7 Playwright tests covering: section visibility, plan cards, usage meters, current plan card, sandbox warning, change plan button visibility, change plan flow

### 12. Backend Test Coverage
- **File**: `backend/tests/test_billing.py`
- 32 new tests added (64 total in billing test file)
- Test classes: `TestSeedIdempotency`, `TestDowngradeProtection`, `TestEntitlementPayload`, `TestUsageIntegrity`, `TestBillingEventIdempotency`, `TestProviderFactoryHardening`, `TestRBACBilling`, `TestListPlansIncludesWhatsApp`

## Validation Results

- **Backend tests**: 353 passed, 0 failed
- **Frontend build**: Successful (12 static pages generated)
- **No regressions**: All 321 pre-existing tests still pass

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/saas_billing_service.py` | Seed idempotency, downgrade protection, event idempotency, payload sanitization |
| `backend/app/services/entitlements_service.py` | Feature field, plan_name, feature-flag denied response |
| `backend/app/billing_providers/factory.py` | Production hardening, demo mode force |
| `backend/app/routers/billing_saas.py` | WhatsApp limit in plans response |
| `backend/app/routers/webhook.py` | Post-success usage increment, improved PT-BR messages |
| `backend/app/routers/admin.py` | Billing metrics endpoint |
| `frontend/components/BillingSection.tsx` | data-testid, role-based UI, error/loading states |
| `frontend/e2e/billing.spec.ts` | New E2E billing tests |
| `backend/tests/test_billing.py` | 32 new hardening tests |
