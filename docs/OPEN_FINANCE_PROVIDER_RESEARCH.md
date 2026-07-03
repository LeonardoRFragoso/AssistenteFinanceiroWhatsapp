# Open Finance Provider Research — Pluggy vs Belvo

> Sprint 16 — Open Finance Read Provider Foundation

## Overview

This document summarizes the technical research on Pluggy and Belvo APIs for
future Open Finance read integration in PayFlow AI. **No real provider is
implemented in Sprint 16.** All data is fake/demo only.

---

## Pluggy API

### Authentication

- API Key based: `PLUGGY_API_KEY` header
- Sandbox base URL: `https://api.pluggy.ai/sandbox`
- Production base URL: `https://api.pluggy.ai`

### Key Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/connectors` | GET | List available institutions/connectors |
| `/connect/token` | POST | Create connect token for user |
| `/accounts` | GET | List connected accounts by item_id |
| `/accounts/{id}/balances` | GET | Get account balances |
| `/transactions` | GET | List transactions by account_id |
| `/items/{id}` | GET | Get connection item status |
| `/items` | POST | Create item (connect bank) |
| `/webhooks` | POST | Register webhook for events |

### Concepts

- **Item**: A connection to a financial institution. Contains credentials status.
- **Connector**: Represents a bank/financial institution.
- **Account**: A bank account linked to an item.
- **Transaction**: A financial movement within an account.

### Webhook Events

- `item.created` — new connection initiated
- `item.updated` — connection status changed
- `item.deleted` — connection removed

### Sandbox

- Pluggy provides a sandbox connector (`pluggy_sandbox`)
- Sandbox credentials: `user` / `pass`
- No real bank data is accessed

---

## Belvo API

### Authentication

- API Key + Secret: Basic Auth header
- Sandbox base URL: `https://sandbox.belvo.com`
- Production base URL: `https://api.belvo.com`

### Key Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/connect/` | POST | Create connect session |
| `/accounts/` | GET | List accounts by link_id |
| `/balances/` | GET | List balances |
| `/transactions/` | GET | List transactions |
| `/institutions/` | GET | List available institutions |
| `/links/` | GET | Get link status |
| `/webhooks/` | POST | Register webhook |

### Concepts

- **Link**: A connection to a financial institution. Contains access status.
- **Institution**: A bank/financial entity.
- **Account**: A bank account under a link.
- **Transaction**: A financial movement.
- **Balance**: Point-in-time balance snapshot.

### Webhook Events

- `link.created` — new link established
- `link.updated` — link status changed
- `link.destroyed` — link revoked

### Sandbox

- Belvo provides sandbox environment with fake institutions
- Sandbox credentials: `sandbox-api-key` / `sandbox-api-secret`
- No real bank data is accessed

---

## Pluggy vs Belvo — Comparison

| Feature | Pluggy | Belvo |
|---|---|---|
| Auth | API Key header | Basic Auth (key + secret) |
| Sandbox | Yes (dedicated connector) | Yes (dedicated environment) |
| Institutions (BR) | 100+ | 80+ |
| Transactions | Rich metadata | Rich metadata + categories |
| Categories | Built-in | Built-in + custom |
| Webhooks | Yes | Yes |
| Pricing model | Per item/connection | Per API call |
| Documentation | Good, REST | Good, REST |
| Open Finance BR | Yes (via partners) | Yes (BACEN registered) |

---

## What Will NOT Be Implemented in Sprint 16

- **No real API calls** to Pluggy or Belvo
- **No real bank connections**
- **No real access tokens or refresh tokens stored**
- **No payment initiation** (Pix Out, boleto payment)
- **No DDA** (automatic bill detection)
- **No KYC** (identity verification)
- **No conta digital** (digital account)
- **No BaaS** (banking as a service)

---

## Recommendation for PayFlow

**Initial provider: Pluggy**

Rationale:
1. Simpler auth model (single API key vs key+secret)
2. Dedicated sandbox connector for development
3. Rich transaction metadata with categories
4. Better documentation for quick onboarding
5. Lower barrier to entry for MVP

**Secondary provider: Belvo** (future Sprint 18+)
1. BACEN-registered Open Finance participant
2. Broader institution coverage in Brazil
3. More granular balance snapshots
4. Better suited for production Open Finance compliance

---

## Risks

- **Credential storage**: Real providers require storing access/refresh tokens.
  Must use encrypted storage (e.g., AWS KMS, Vault) — never plaintext.
- **Consent expiry**: Open Finance consents expire (12 months per BACEN).
  Must handle re-authorization flow.
- **Rate limits**: Both providers enforce rate limits. Must implement
  exponential backoff and queue-based sync.
- **Data privacy**: LGPD compliance required. All financial data must be
  org-scoped, encrypted at rest, and deletable on request.
- **Webhook security**: Must validate webhook signatures to prevent spoofing.

---

## Security Requirements for Future Implementation

1. Feature flag `ENABLE_OPEN_FINANCE` must be `true`
2. Provider name must not be `fake`
3. Demo mode must be `false`
4. API credentials must be in environment variables (never committed)
5. Access tokens must be encrypted before storage
6. All API calls must be org-scoped
7. Webhook payloads must be sanitized before logging
8. Audit logs must record all consent and sync operations
9. No financial advice or investment recommendations
10. No payment initiation through Open Finance provider
