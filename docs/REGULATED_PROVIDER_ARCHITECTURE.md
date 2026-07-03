# Regulated Provider Architecture

> Sprint 13 — Jota Feature Parity Blueprint
> Sprint 14 — Provider Foundation implemented (tables, services, endpoints)
> Define interfaces futuras para providers regulados.
> **Nenhum provider real é implementado nesta sprint.**

> **Sprint 14 Update:** 5 database tables created (`provider_connections`, `provider_webhook_events`, `open_finance_consents`, `organization_audit_logs`, `transaction_authorizations`), 5 services, 14 API endpoints with RBAC, and 35 tests. All providers remain fake/sandbox. See `docs/SPRINT_14_PROVIDER_FOUNDATION.md`.

---

## Princípios

1. **PayFlow é orquestrador**: interface, IA, UX, e camada de regras.
2. **Liquidação financeira depende de parceiros regulados**: nunca simulado como real.
3. **Provider padrão é fake/sandbox**: sempre seguro para desenvolvimento.
4. **Toda operação regulada passa por abstraction**: nenhum código de pagamento real fora de providers.
5. **Feature flags controlam ativação**: reguladas default `false`.

---

## Grupos de Risco Regulatório

### Grupo A — Pode ser interno (sem provider regulado)

| Funcionalidade | Status no PayFlow |
|---|---|
| IA conversacional | ✅ Implementado |
| Dashboard | ✅ Implementado |
| Cobranças sandbox | ✅ Implementado |
| Templates de mensagem | ✅ Implementado |
| Analytics | ✅ Implementado |
| Billing SaaS | ✅ Implementado |
| Lembretes e tarefas | ✅ Implementado |
| Organização de dados | ✅ Implementado |
| UX de WhatsApp | ✅ Implementado |
| Relatórios | ✅ Implementado |
| Categorização interna | ❌ Futuro (com Open Finance data) |

### Grupo B — Pode ser integrado com gateway de recebimento

| Funcionalidade | Provider necessário | Status |
|---|---|---|
| Cobrança Pix (recebimento) | Asaas / Celcoin / QI Tech | ❌ Não implementado |
| Boleto de cobrança (recebimento) | Asaas / Celcoin | ❌ Não implementado |
| Cartão (recebimento) | Asaas / adquirente | ❌ Não implementado |
| Link de pagamento | Asaas / Celcoin | ❌ Não implementado |
| Webhooks de recebimento | Asaas / Celcoin | ❌ Não implementado |
| Comprovante de recebimento | Asaas / Celcoin | ❌ Não implementado |

### Grupo C — Precisa de Open Finance / provider regulado

| Funcionalidade | Provider necessário | Status |
|---|---|---|
| Saldo bancário real | Pluggy / Belvo / Celcoin | ❌ Não implementado |
| Extrato real | Pluggy / Belvo | ❌ Não implementado |
| Transações reais | Pluggy / Belvo | ❌ Não implementado |
| Contas conectadas | Pluggy / Belvo | ❌ Não implementado |
| Consentimento Open Finance | Pluggy / Belvo | ❌ Não implementado |
| Iniciação de pagamento | Pluggy / Belvo / Celcoin | ❌ Não implementado |
| Pagamento via conta conectada | Pluggy + Celcoin | ❌ Não implementado |
| DDA | Celcoin / Dock | ❌ Não implementado |

### Grupo D — Precisa de BaaS / KYC / compliance

| Funcionalidade | Provider necessário | Status |
|---|---|---|
| Conta digital | Celcoin / QI Tech / Dock | ❌ Não implementado |
| Pix Out | Celcoin / QI Tech | ❌ Não implementado |
| Pagamento de boleto | Celcoin / QI Tech | ❌ Não implementado |
| Pagamento de contas | Celcoin / QI Tech | ❌ Não implementado |
| Saque | BaaS | ❌ Não implementado |
| Conta escrow | BaaS | ❌ Não implementado |
| Cadastro de chave Pix | Celcoin / QI Tech | ❌ Não implementado |
| Wallet/saldo | BaaS | ❌ Não implementado |
| KYC/KYB | Unico / Caf / Certta | ❌ Não implementado |
| Antifraude transacional | Unico / Solução própria | ❌ Não implementado |

---

## Interfaces de Providers

### 1. OpenFinanceProvider

**Responsabilidade**: Conectar contas bancárias via Open Finance, ler saldos, extratos e transações.

```python
class OpenFinanceProvider(ABC):
    @abstractmethod
    async def create_consent(self, org_id: int, user_id: int, institution_id: str) -> ConsentResult:
        """Inicia fluxo de consentimento Open Finance."""

    @abstractmethod
    async def revoke_consent(self, consent_id: str) -> bool:
        """Revoga consentimento."""

    @abstractmethod
    async def get_consent_status(self, consent_id: str) -> ConsentStatus:
        """Verifica status do consentimento."""

    @abstractmethod
    async def list_connected_accounts(self, org_id: int) -> list[ConnectedAccount]:
        """Lista contas bancárias conectadas."""

    @abstractmethod
    async def get_account_balance(self, account_id: str) -> AccountBalance:
        """Consulta saldo de conta conectada."""

    @abstractmethod
    async def get_account_transactions(self, account_id: str, start_date: date, end_date: date) -> list[Transaction]:
        """Consulta transações de conta conectada."""

    @abstractmethod
    async def initiate_payment(self, account_id: str, payment_data: PaymentInitiation) -> PaymentResult:
        """Inicia pagamento via conta conectada (Open Finance initiation)."""
```

**Eventos/Webhooks**: `consent.authorized`, `consent.revoked`, `consent.expired`, `transaction.new`, `payment.initiated`, `payment.confirmed`, `payment.failed`

**Dados sensíveis**: tokens de consentimento, credenciais bancárias (gerenciadas pelo provider), dados de transações.

**Riscos**: Vazamento de dados financeiros, consentimento expirado, falha de iniciação de pagamento.

**Provider fake**: `FakeOpenFinanceProvider` — retorna dados simulados de saldos e transações.
**Provider real futuro**: Pluggy, Belvo, ou Celcoin Open Finance.
**Status atual**: Não implementado.

---

### 2. BankingProvider (BaaS)

**Responsabilidade**: Conta digital, saldo, Pix Out, pagamento de boletos, transferências.

```python
class BankingProvider(ABC):
    @abstractmethod
    async def create_account(self, org_id: int, user_data: KYCResult) -> AccountResult:
        """Cria conta de pagamento após KYC aprovado."""

    @abstractmethod
    async def get_balance(self, account_id: str) -> Decimal:
        """Consulta saldo da conta."""

    @abstractmethod
    async def pix_out(self, account_id: str, pix_key: str, amount: Decimal, description: str) -> PixOutResult:
        """Envia Pix para chave destinatária."""

    @abstractmethod
    async def pay_bill(self, account_id: str, bill_data: BillData) -> BillPaymentResult:
        """Paga boleto ou conta via conta digital."""

    @abstractmethod
    async def register_pix_key(self, account_id: str, key_type: str, key_value: str) -> PixKeyResult:
        """Cadastra chave Pix na conta."""

    @abstractmethod
    async def get_statement(self, account_id: str, start_date: date, end_date: date) -> Statement:
        """Extrato da conta."""
```

**Eventos/Webhooks**: `account.created`, `balance.updated`, `pix.sent`, `pix.received`, `bill.paid`, `bill.failed`, `statement.available`

**Dados sensíveis**: saldo, transações, chave Pix, dados bancários.

**Riscos**: Perda financeira, fraude, erro de liquidação, falha regulatória.

**Provider fake**: `FakeBankingProvider` — simula conta com saldo fictício.
**Provider real futuro**: Celcoin, QI Tech, Dock.
**Status atual**: Não implementado.

---

### 3. BillPaymentProvider

**Responsabilidade**: Pagamento de boletos e contas (água, luz, etc.).

```python
class BillPaymentProvider(ABC):
    @abstractmethod
    async def validate_bill(self, barcode: str) -> BillValidation:
        """Valida linha digitável ou código de barras de boleto."""

    @abstractmethod
    async def pay_bill(self, account_id: str, barcode: str, amount: Decimal, schedule_date: date | None) -> BillPaymentResult:
        """Paga boleto (imediato ou agendado)."""

    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> PaymentStatus:
        """Consulta status de pagamento de boleto."""

    @abstractmethod
    async def cancel_scheduled_payment(self, payment_id: str) -> bool:
        """Cancela pagamento agendado."""
```

**Eventos/Webhooks**: `bill.validated`, `bill.paid`, `bill.scheduled`, `bill.cancelled`, `bill.failed`

**Dados sensíveis**: código de barras, valor, dados do beneficiário.

**Riscos**: Pagamento duplicado, boleto fraudulento, falha de liquidação.

**Provider fake**: `FakeBillPaymentProvider` — simula validação e pagamento.
**Provider real futuro**: Celcoin, QI Tech.
**Status atual**: Não implementado.

---

### 4. PixProvider

**Responsabilidade**: Cobrança Pix (recebimento), QR Code dinâmico/estático, webhooks de recebimento.

```python
class PixProvider(ABC):
    @abstractmethod
    async def create_charge(self, org_id: int, amount: Decimal, description: str, payer_info: dict | None) -> PixChargeResult:
        """Cria cobrança Pix (QR Code dinâmico)."""

    @abstractmethod
    async def create_static_qr(self, org_id: int, description: str) -> PixStaticQRResult:
        """Cria QR Code Pix estático (sem valor fixo)."""

    @abstractmethod
    async def get_charge_status(self, charge_id: str) -> ChargeStatus:
        """Consulta status de cobrança Pix."""

    @abstractmethod
    async def process_webhook(self, payload: dict) -> WebhookResult:
        """Processa webhook de recebimento Pix."""
```

**Eventos/Webhooks**: `pix.received`, `pix.expired`, `pix.overpaid`, `pix.underpaid`

**Dados sensíveis**: dados do pagador, valor, ID da transação.

**Riscos**: Recebimento fraudulento, QR Code expirado, conciliação incorreta.

**Provider fake**: `FakePixProvider` — simula cobrança e recebimento.
**Provider real futuro**: Asaas, Celcoin, QI Tech.
**Status atual**: Não implementado (PayFlow tem cobrança sandbox via `FakeBillingProvider`).

---

### 5. KYCProvider

**Responsabilidade**: Validação de identidade, biometria facial, verificação de documento.

```python
class KYCProvider(ABC):
    @abstractmethod
    async def start_verification(self, user_id: int, document_type: str, document_data: dict) -> KYCSession:
        """Inicia sessão de verificação KYC."""

    @abstractmethod
    async def submit_document(self, session_id: str, document_image: bytes) -> DocumentResult:
        """Submete imagem de documento para validação."""

    @abstractmethod
    async def submit_selfie(self, session_id: str, selfie_image: bytes) -> BiometricResult:
        """Submete selfie para biometria facial."""

    @abstractmethod
    async def get_verification_result(self, session_id: str) -> KYCResult:
        """Obtém resultado final da verificação."""
```

**Eventos/Webhooks**: `kyc.started`, `kyc.document_validated`, `kyc.biometric_passed`, `kyc.biometric_failed`, `kyc.approved`, `kyc.rejected`

**Dados sensíveis**: imagem de documento, selfie, dados pessoais (CPF, RG, etc.).

**Riscos**: Vazamento de dados biométricos, falsificação de identidade, erro de validação.

**Provider fake**: `FakeKYCProvider` — aprova automaticamente.
**Provider real futuro**: Unico, Caf, Certta.
**Status atual**: Não implementado.

---

### 6. FraudProvider

**Responsabilidade**: Análise de risco transacional, antifraude, scoring.

```python
class FraudProvider(ABC):
    @abstractmethod
    async def assess_risk(self, transaction_data: dict) -> RiskAssessment:
        """Avalia risco de transação em tempo real."""

    @abstractmethod
    async def flag_transaction(self, transaction_id: str, reason: str) -> bool:
        """Marca transação como suspeita."""

    @abstractmethod
    async def get_user_risk_score(self, user_id: int) -> RiskScore:
        """Obtém score de risco do usuário."""
```

**Eventos/Webhooks**: `fraud.alert`, `fraud.block`, `risk.score_updated`

**Dados sensíveis**: padrões de comportamento, dados de dispositivo, geolocalização.

**Riscos**: Falso positivo bloqueando usuário legítimo, falso negativo permitindo fraude.

**Provider fake**: `FakeFraudProvider` — retorna baixo risco sempre.
**Provider real futuro**: Unico (Risk), solução própria, ou parceiro especializado.
**Status atual**: Não implementado.

---

### 7. DDAProvider

**Responsabilidade**: Detecção automática de boletos no CPF/CNPJ.

```python
class DDAProvider(ABC):
    @abstractmethod
    async def enable_dda(self, org_id: int, document: str) -> DDAEnrollment:
        """Ativa DDA para CPF/CNPJ."""

    @abstractmethod
    async def disable_dda(self, enrollment_id: str) -> bool:
        """Desativa DDA."""

    @abstractmethod
    async def list_detected_bills(self, org_id: int) -> list[DetectedBill]:
        """Lista boletos detectados automaticamente."""

    @abstractmethod
    async def get_bill_details(self, bill_id: str) -> BillDetails:
        """Detalhes de boleto detectado."""
```

**Eventos/Webhooks**: `dda.bill_detected`, `dda.bill_expired`, `dda.enrollment_activated`, `dda.enrollment_deactivated`

**Dados sensíveis**: CPF/CNPJ, dados de boletos.

**Riscos**: Boleto fraudulento detectado, dados incorretos.

**Provider fake**: `FakeDDAProvider` — simula boletos detectados.
**Provider real futuro**: Celcoin, Dock.
**Status atual**: Não implementado.

---

### 8. ReceiptProvider

**Responsabilidade**: Geração e armazenamento de comprovantes.

```python
class ReceiptProvider(ABC):
    @abstractmethod
    async def generate_receipt(self, transaction_id: str, transaction_type: str) -> ReceiptResult:
        """Gera comprovante de transação."""

    @abstractmethod
    async def get_receipt(self, receipt_id: str) -> Receipt:
        """Obtém comprovante por ID."""

    @abstractmethod
    async def list_receipts(self, org_id: int, start_date: date, end_date: date) -> list[Receipt]:
        """Lista comprovantes por período."""
```

**Eventos/Webhooks**: `receipt.generated`, `receipt.available`

**Dados sensíveis**: dados de transação, valor, destinatário.

**Riscos**: Comprovante falsificado, dados incorretos.

**Provider fake**: `FakeReceiptProvider` — gera PDF simulado.
**Provider real futuro**: Integrado com charge provider (Asaas, Celcoin).
**Status atual**: Não implementado (PayFlow tem charge com status, mas não comprovante formal).

---

### 9. ConsentProvider

**Responsabilidade**: Gestão de consentimentos (Open Finance, LGPD, autorização de pagamento).

```python
class ConsentProvider(ABC):
    @abstractmethod
    async def create_consent(self, org_id: int, user_id: int, scope: str, metadata: dict) -> Consent:
        """Cria registro de consentimento."""

    @abstractmethod
    async def verify_consent(self, org_id: int, user_id: int, scope: str) -> ConsentStatus:
        """Verifica se consentimento está ativo."""

    @abstractmethod
    async def revoke_consent(self, consent_id: str) -> bool:
        """Revoga consentimento."""

    @abstractmethod
    async def list_consents(self, org_id: int) -> list[Consent]:
        """Lista consentimentos ativos."""
```

**Eventos/Webhooks**: `consent.created`, `consent.expired`, `consent.revoked`

**Dados sensíveis**: escopo de consentimento, dados do usuário, timestamps.

**Riscos**: Consentimento expirado sem renovação, consentimento forçado, não conformidade LGPD.

**Provider fake**: `FakeConsentProvider` — aprova todos os consentimentos.
**Provider real futuro**: Solução interna + integração com Open Finance provider.
**Status atual**: Não implementado.

---

## Tabela de Empresas Candidatas por Provider

| Provider | Empresas candidatas | Uso no PayFlow | Complexidade | Prioridade |
|---|---|---|---|---|
| PixProvider (cobrança) | Asaas, Celcoin, QI Tech | Receber Pix de clientes | Média | Obrigatório agora |
| BankingProvider (BaaS) | Celcoin, QI Tech, Dock | Conta digital, Pix Out, pagamento | Alta | Obrigatório para paridade |
| OpenFinanceProvider | Pluggy, Belvo, Celcoin | Saldo, extrato, transações, consentimento | Alta | Obrigatório para paridade |
| BillPaymentProvider | Celcoin, QI Tech | Pagamento de boletos e contas | Média | Obrigatório para paridade |
| DDAProvider | Celcoin, Dock | Detecção automática de boletos | Média | Importante |
| KYCProvider | Unico, Caf, Certta | Validação de identidade, biometria | Média | Obrigatório para paridade |
| FraudProvider | Unico, solução própria | Antifraude transacional | Alta | Importante |
| ReceiptProvider | Integrado (Asaas/Celcoin) | Comprovantes | Baixa | Obrigatório para paridade |
| ConsentProvider | Solução interna | Gestão de consentimentos LGPD/Open Finance | Média | Obrigatório agora |
| WhatsApp Business | Meta, Twilio, Zenvia | Interface conversacional | Baixa | Obrigatório agora (já usado) |
| IA | OpenAI | Processamento de linguagem natural | Baixa | Obrigatório agora (já usado) |
| Notificações email | Resend, SendGrid, Amazon SES | Notificações de sistema | Baixa | Opcional |
| Assinatura digital | Clicksign, Docusign | Contratos e termos | Baixa | Opcional |
| Monitoramento | Sentry | Error tracking | Baixa | Obrigatório agora |
| Infraestrutura | AWS, GCP, Azure | Hosting, DB, storage | Baixa | Obrigatório agora (já usado) |

---

## Classificação de Prioridade

- **Obrigatório agora**: Necessário para operação atual do PayFlow (já integrado ou a integrar imediatamente).
- **Obrigatório para paridade**: Necessário para atingir paridade funcional com o Jota.
- **Opcional**: Melhora a experiência mas não é bloqueante.
- **Futuro enterprise**: Recursos avançados para escala enterprise.
