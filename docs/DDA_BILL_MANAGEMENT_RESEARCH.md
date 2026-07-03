# DDA & Bill Management — Research

> **Status**: Research complete
> **Date**: 2025-07-03
> **Sprint**: 17

## 1. What is DDA?

DDA (Débito Direto Autorizado) is a Brazilian banking system that allows financial institutions to automatically detect boletos (bank payment slips) issued in the name of a CPF/CNPJ. Instead of the customer manually entering a barcode or digitable line, the bank scans for boletos and presents them in the banking app for the customer to review and authorize payment.

Key points:
- DDA is **detection only** — it identifies boletos but does NOT pay them automatically.
- The customer must explicitly authorize each payment.
- DDA is operated by CIP (Câmara Interbancária de Pagamentos) and available through banks and fintechs.
- Not all boletos participate in DDA — the issuer must register the boleto in the DDA system.

## 2. Detecting vs Paying a Boleto

| Aspect | Detection (DDA) | Payment |
|--------|-----------------|---------|
| What it does | Finds boletos issued to a CPF/CNPJ | Executes payment of a boleto |
| Real provider needed | Yes (bank or fintech with DDA access) | Yes (bank, BaaS, or payment provider) |
| Regulatory risk | Low (read-only) | High (moves money) |
| BACEN regulation | DDA is regulated by BACEN | Payment initiation is regulated by BACEN |
| PayFlow Sprint 17 | **Fake only** — no real DDA | **Fake only** — no real payment |

## 3. Boleto Bancário — Key Concepts

- **Linha digitável** (digitable line): 47-48 digit numeric string representing the boleto.
- **Código de barras** (barcode): 44-digit numeric string encoded in the barcode.
- **Vencimento** (due date): date when the boleto must be paid before penalties.
- **Beneficiário** (beneficiary): entity receiving the payment (utility company, service provider, etc.).
- **Pagador** (payer): entity responsible for paying.
- **Status**: detected, pending, paid, overdue, expired, cancelled.
- **Valor** (amount): payment amount in BRL.
- **Desconto/Abatimento**: discounts for early payment.
- **Multa/Juros**: penalties for late payment.

## 4. Candidate Providers (Future — Not Sprint 17)

### Celcoin
- DDA API for boleto detection
- Boleto payment API
- BaaS platform with Pix Out
- Sandbox available
- BACEN-regulated

### Dock
- Formerly Conductor
- DDA and boleto payment
- Card issuing and processing
- Sandbox available

### QI Tech
- BaaS platform
- Boleto payment and DDA
- Pix Out
- Sandbox available
- BACEN-regulated via banking partner

### Asaas
- Already integrated for charge creation (Sprint 15)
- Has boleto payment API
- Could be extended for bill payment in future sprints
- Sandbox available

## 5. What Can Be Fake/Sandbox in Sprint 17

- **Bill detection**: Generate fake boletos with realistic data
- **Bill listing**: Filter, sort, search fake bills
- **Bill reminders**: Schedule reminders for fake bills
- **Bill summary**: Aggregate totals, categories, due dates
- **Payment intent**: Create fake payment intent (no execution)
- **Transaction authorization**: Authorize fake intent only
- **WhatsApp responses**: Report fake bills with demo disclaimer
- **Frontend**: Display fake bills with demo badge
- **Admin metrics**: Count fake bills, intents, reminders

## 6. What Depends on Regulated Provider (NOT Sprint 17)

- **Real DDA access**: Requires bank/fintech API with DDA integration
- **Real boleto payment**: Requires payment provider with boleto payment API
- **Real boleto validation**: Requires provider API to verify barcode/digitable line
- **Real barcode parsing**: Requires validation against bank checksums
- **Pix Out for boleto payment**: Requires BaaS with Pix Out capability
- **Automatic payment scheduling**: Requires real payment execution

## 7. What Will NOT Be Implemented in Sprint 17

- DDA real (no Celcoin, Dock, QI Tech, or any real provider)
- Boleto payment real (no money movement)
- Pix Out
- Conta digital (digital account)
- BaaS
- Open Finance real
- KYC real
- Real barcode validation
- Real boleto registration
- Automatic payment execution

## 8. Regulatory Risks

1. **Payment execution without license**: PayFlow is not a financial institution. Payment must go through a regulated partner.
2. **DDA data access**: Requires partnership with bank or fintech. Direct CIP access is not available to non-banks.
3. **Boleto validation**: Parsing barcodes without provider validation can lead to incorrect payments.
4. **LGPD**: Boleto data contains beneficiary documents, amounts, and payment history. Must be encrypted and deletable.
5. **False sense of security**: Users might think fake bills are real. Must be clearly marked as demo.

## 9. Recommendation

1. **Sprint 17**: Implement fake DDA and bill management with clear demo markers.
2. **Sprint 18+**: Integrate with Celcoin or QI Tech for real DDA and bill payment.
3. **Sprint 20+**: Add Pix Out for boleto payment via BaaS partner.
4. **Always**: Mark fake data as `is_demo_data=True` and include demo disclaimers in all user-facing responses.
