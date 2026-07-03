# Jota Parity Roadmap — Fases de Integração

> Sprint 13 — Jota Feature Parity Blueprint
> Roadmap técnico para atingir paridade funcional com o Jota.
> **Nenhuma operação regulada é implementada sem parceiro.**

---

## Visão Geral

```
PayFlow atual (Sprint 12.1)
    │
    ├── Fase 1: Provider Foundation (Sprint 14)
    ├── Fase 2: Real Charge Provider (Sprint 15)
    ├── Fase 3: Open Finance Read (Sprint 16)
    ├── Fase 4: DDA e Contas a Pagar (Sprint 17)
    ├── Fase 5: Payment Initiation Sandbox (Sprint 18)
    ├── Fase 6: KYC/KYB (Sprint 19)
    └── Fase 7: BaaS/Pix Out Real (Sprint 20+)
```

---

## Fase 1 — Provider Foundation (Sprint 14)

**Objetivo**: Criar abstrações, fake providers, consent model, e auditoria.

### Entregáveis
- [ ] Interfaces base para todos os providers regulados (abstract classes)
- [ ] Fake providers para todos os tipos (OpenFinance, Banking, BillPayment, Pix, KYC, Fraud, DDA, Receipt, Consent)
- [ ] Provider factory com feature flags
- [ ] Modelo de consentimento (tabelas + service)
- [ ] Provider event logs (tabela `provider_webhook_events`)
- [ ] Audit logs organizacionais (tabela `organization_audit_logs`)
- [ ] Status page interna de providers
- [ ] Feature flags: `ENABLE_OPEN_FINANCE`, `ENABLE_BILL_PAYMENT`, `ENABLE_PIX_OUT`, `ENABLE_KYC`, `ENABLE_DDA`, `ENABLE_REAL_BANKING` (todas `false`)

### Riscos
- Nenhum risco regulatório (tudo é fake/sandbox)
- Define a arquitetura que todas as fases seguintes usarão

### Critérios de aceite
- Todas as interfaces criadas e testáveis com fake providers
- Feature flags default false em produção
- Factory rejeita provider real se feature flag desativada

---

## Fase 2 — Real Charge Provider (Sprint 15)

**Objetivo**: Integrar com gateway de recebimento real (Asaas ou Celcoin) para cobrança Pix, boleto e cartão.

### Entregáveis
- [ ] Integração com Asaas (ou equivalente) para:
  - Cobrança Pix (QR Code dinâmico)
  - Boleto de cobrança
  - Link de pagamento
  - Cartão (opcional)
- [ ] Webhooks de recebimento reais
- [ ] Reconciliação de pagamentos
- [ ] Comprovante de recebimento (PDF)
- [ ] Atualização automática de status de charge
- [ ] Notificação no WhatsApp quando pagamento recebido
- [ ] Meta Business Verified (se aplicável)

### Riscos
- Transações reais de recebimento (sem custódia)
- Webhooks devem ser idempotentes e seguros
- Conciliação deve ser precisa

### Critérios de aceite
- Cobrança Pix real gerada e recebida
- Webhook processado com idempotência
- Comprovante gerado
- Feature flag `ENABLE_REAL_CHARGES=true` apenas com provider configurado

---

## Fase 3 — Open Finance Read (Sprint 16)

**Objetivo**: Integrar com Pluggy/Belvo/Celcoin para leitura de dados bancários via Open Finance.

### Entregáveis
- [ ] Integração com Pluggy (ou Belvo) para:
  - Fluxo de consentimento Open Finance
  - Conexão de contas bancárias
  - Consulta de saldos
  - Consulta de extratos
  - Consulta de transações
- [ ] Tela de consentimento no WhatsApp (link de autorização)
- [ ] Visão consolidada de múltiplos bancos
- [ ] Categorização automática de transações com IA
- [ ] Notificação de novas transações
- [ ] Revogação de consentimento

### Riscos
- Dados financeiros sensíveis (LGPD)
- Consentimento deve ter expiração
- Tokens de consentimento devem ser seguros

### Critérios de aceite
- Consentimento criado, autorizado e revogado
- Saldo e extrato de conta conectada exibidos
- Feature flag `ENABLE_OPEN_FINANCE=true` apenas com provider configurado

---

## Fase 4 — DDA e Contas a Pagar (Sprint 17)

**Objetivo**: Detecção automática de boletos e gestão de contas a pagar.

### Entregáveis
- [ ] Integração com Celcoin (ou Dock) para DDA:
  - Ativação de DDA por CPF/CNPJ
  - Detecção automática de boletos
  - Alertas de vencimento no WhatsApp
- [ ] Listagem de boletos pendentes
- [ ] OCR de boletos (foto do código de barras) — já temos OCR base
- [ ] Validação de linha digitável
- [ ] Agendamento de pagamento de boletos
- [ ] Lembretes de vencimento configuráveis
- [ ] Status de pagamento em tempo real

### Riscos
- Boleto fraudulento detectado via DDA
- Pagamento agendado deve ser confirmado explicitamente
- Dados de CPF/CNPJ sensíveis

### Critérios de aceite
- DDA ativado e boletos detectados
- Boleto validado por foto/OCR
- Pagamento agendado com confirmação
- Feature flag `ENABLE_DDA=true` apenas com provider configurado

---

## Fase 5 — Payment Initiation Sandbox (Sprint 18)

**Objetivo**: Iniciação de pagamento via Open Finance em sandbox (sem liquidação real).

### Entregáveis
- [ ] Fluxo de iniciação de pagamento via conta conectada
- [ ] Confirmação explícita de pagamento (senha de 6 dígitos)
- [ ] Idempotência de pagamento
- [ ] Comprovante de iniciação
- [ ] Logs detalhados
- [ ] Simulação completa com fake provider
- [ ] Pré-autorização de regras (ex: até R$ X para recebedor Y)

### Riscos
- Mesmo em sandbox, o fluxo deve ser seguro
- Confirmação explícita é obrigatória
- Pré-autorização deve ter limites e expiração

### Critérios de aceite
- Pagamento iniciado em sandbox com confirmação
- Comprovante gerado
- Pré-autorização funcionando com limites
- Nenhuma liquidação real ocorre

---

## Fase 6 — KYC/KYB (Sprint 19)

**Objetivo**: Validação de identidade para onboarding de usuários e organizações.

### Entregáveis
- [ ] Integração com Unico (ou Caf) para:
  - Validação de documento (RG/CNH/passaporte)
  - Biometria facial
  - Liveness check
- [ ] Fluxo de onboarding via WhatsApp (2-3 minutos)
- [ ] KYC para PF (CPF + documento + selfie)
- [ ] KYB para PJ (CNPJ + contrato social + representante legal)
- [ ] Termos de uso e consentimento LGPD
- [ ] Status de verificação (pending, approved, rejected)
- [ ] Re-verificação periódica

### Riscos
- Dados biométricos são extremamente sensíveis
- Conformidade LGPD obrigatória
- Rejeição de KYC deve ter fluxo de recurso

### Critérios de aceite
- KYC PF completo via WhatsApp
- KYB PJ completo via WhatsApp
- Dados biométricos não armazenados (apenas resultado)
- Feature flag `ENABLE_KYC=true` apenas com provider configurado

---

## Fase 7 — BaaS/Pix Out Real (Sprint 20+)

**Objetivo**: Conta digital real, Pix Out, pagamento de contas — apenas com parceiro regulado.

### Entregáveis
- [ ] Integração com Celcoin (ou QI Tech) para BaaS:
  - Conta digital (conta de pagamento)
  - Saldo e extrato
  - Pix Out (envio de dinheiro)
  - Pagamento de boletos
  - Pagamento de contas (água, luz, etc.)
  - Cadastro de chave Pix
- [ ] Senha de 6 dígitos por transação
- [ ] Antifraude transacional
- [ ] Limites de transação
- [ ] Auditoria completa
- [ ] Rendimento automático (100% CDI) — se aplicável

### Riscos
- **Alto risco regulatório** — requer parceiro regulado
- Custódia de recursos (segregação obrigatória)
- Antifraude é crítico
- Conformidade com Banco Central

### Critérios de aceite
- Conta digital criada após KYC aprovado
- Pix Out executado com confirmação
- Pagamento de boleto executado
- Antifraude ativo
- Feature flag `ENABLE_REAL_BANKING=true` apenas com provider configurado e KYC aprovado

---

## Timeline Estimada

| Fase | Sprint | Duração estimada | Dependência |
|---|---|---|---|
| 1 — Provider Foundation | 14 | 1-2 semanas | Nenhuma |
| 2 — Real Charge Provider | 15 | 2-3 semanas | Fase 1 |
| 3 — Open Finance Read | 16 | 2-3 semanas | Fase 1 |
| 4 — DDA e Contas a Pagar | 17 | 2 semanas | Fase 1 + Fase 3 (opcional) |
| 5 — Payment Initiation Sandbox | 18 | 2 semanas | Fase 3 |
| 6 — KYC/KYB | 19 | 2-3 semanas | Fase 1 |
| 7 — BaaS/Pix Out Real | 20+ | 4-6 semanas | Fase 6 + parceiro regulado |

> **Total estimado**: 15-21 semanas (4-5 meses) para paridade completa.
> Fases 2 e 3 podem ser paralelizadas.
> Fase 7 depende de contrato com parceiro regulado.

---

## Disclaimer

Este roadmap é técnico e estratégico. **Nenhuma operação regulada deve ser implementada sem:**
1. Contrato formal com parceiro regulado pelo Banco Central.
2. Análise legal e de compliance.
3. Feature flag ativa com provider configurado.
4. KYC/KYB do usuário ou organização.
5. Auditoria e logs completos.
