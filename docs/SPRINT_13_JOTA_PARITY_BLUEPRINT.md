# Sprint 13 — Jota Feature Parity Blueprint & Regulated Provider Architecture

> **Data**: Julho 2026
> **Commit base**: `9cf7392` (Sprint 12.1: Billing Hardening)
> **Commit resultante**: (a ser definido)
> **Tipo**: Sprint de documentação, arquitetura e preparação

---

## Objetivo

Criar um blueprint técnico e estratégico completo para levar o PayFlow AI à paridade funcional com o Jota, sem implementar operações reguladas de forma indevida.

---

## Entregáveis

### Documentação criada (8 arquivos)

| Arquivo | Conteúdo |
|---|---|
| `docs/COMPETITOR_JOTA_RESEARCH.md` | Pesquisa funcional do Jota com fontes, funcionalidades confirmadas e inferidas |
| `docs/JOTA_PARITY_MATRIX.md` | Matriz Jota vs PayFlow com 40 funcionalidades, gaps, prioridades e sprints sugeridas |
| `docs/REGULATED_PROVIDER_ARCHITECTURE.md` | 9 interfaces de providers regulados com métodos, eventos, riscos e empresas candidatas |
| `docs/JOTA_PARITY_ROADMAP.md` | 7 fases de integração com timeline estimada de 4-5 meses |
| `docs/CONSENT_AND_AUTHORIZATION_MODEL.md` | Modelo de consentimento (Open Finance, WhatsApp, pagamento, LGPD) com roles e segurança |
| `docs/WHATSAPP_JOTA_PARITY_COMMANDS.md` | 13 comandos WhatsApp mapeados com intent, provider, risco e status |
| `docs/FUTURE_FINTECH_DATA_MODEL.md` | 13 tabelas futuras propostas com campos, índices e relacionamentos |
| `docs/SPRINT_13_JOTA_PARITY_BLUEPRINT.md` | Este documento — resumo da sprint |

### Ajustes de código (preparação arquitetural)

| Arquivo | Alteração |
|---|---|
| `backend/app/core/config.py` | Feature flags reguladas (todas `false` por padrão) |
| `backend/app/models/provider_type.py` | Enum de tipos de provider regulado |
| `backend/app/providers/__init__.py` | Package de providers regulados |
| `backend/app/providers/base.py` | Classes abstratas base para 9 providers |
| `backend/app/providers/fake.py` | Fake implementations para todos os providers |
| `backend/app/providers/factory.py` | Factory com feature flag validation |
| `backend/tests/test_provider_flags.py` | Testes de feature flags e provider factory |

---

## Resumo da Pesquisa do Jota

### Funcionalidades confirmadas (fonte: jota.ai + blog.jota.ai)

- Conta digital (conta de pagamento via Celcoin)
- Pix no WhatsApp (texto, áudio, imagem)
- Cobranças via QR Code Pix (gratuito)
- Fala Tap (maquininha por voz/NFC)
- Radar de Boletos (DDA automático)
- Open Finance (20+ bancos conectados)
- Rendimento automático (100% CDI)
- Lembretes e tarefas recorrentes
- KYC (Unico — biometria facial)
- Meta Business Verified
- Onboarding via WhatsApp (2-3 minutos)
- Senha de 6 dígitos por transação

### Parceiros do Jota
- **Celcoin**: BaaS (conta, Pix, boleto)
- **Unico**: KYC (biometria)
- **Meta**: WhatsApp Business

### Modelo de negócio
- Gratuito para serviços essenciais
- Receita: Fala Tap (maquininha) + crédito futuro

---

## Matriz de Gaps (resumo)

| Prioridade | Quantidade | Principais gaps |
|---|---|---|
| P0 | 10 | Real charge, conta digital, Pix Out, boleto, Open Finance, KYC, senha transação, LGPD |
| P1 | 8 | DDA, agendamento, pré-autorização, Meta Verified, categorização, antifraude |
| P2 | 1 | Rendimento CDI |
| P3 | 3 | Fala Tap, carteira compartilhada, cartão |

---

## Arquitetura de Providers (resumo)

9 interfaces propostas:
1. `OpenFinanceProvider` — Pluggy/Belvo/Celcoin
2. `BankingProvider` — Celcoin/QI Tech/Dock
3. `BillPaymentProvider` — Celcoin/QI Tech
4. `PixProvider` — Asaas/Celcoin/QI Tech
5. `KYCProvider` — Unico/Caf/Certta
6. `FraudProvider` — Unico/próprio
7. `DDAProvider` — Celcoin/Dock
8. `ReceiptProvider` — Integrado
9. `ConsentProvider` — Interno

---

## Roadmap (resumo)

| Fase | Sprint | Foco |
|---|---|---|
| 1 | 14 | Provider foundation (abstrações, fakes, consent, audit) |
| 2 | 15 | Real charge (Asaas/Celcoin — Pix cobrança, boleto, webhook) |
| 3 | 16 | Open Finance read (Pluggy/Belvo — saldo, extrato, transações) |
| 4 | 17 | DDA e contas a pagar (Celcoin — detecção, agendamento) |
| 5 | 18 | Payment initiation sandbox (Open Finance init, confirmação) |
| 6 | 19 | KYC/KYB (Unico — biometria, onboarding) |
| 7 | 20+ | BaaS/Pix Out real (Celcoin/QI Tech — conta, Pix Out, pagamento) |

**Timeline estimada**: 15-21 semanas (4-5 meses) para paridade completa.

---

## Feature Flags Adicionadas

```env
ENABLE_OPEN_FINANCE=false
ENABLE_BILL_PAYMENT=false
ENABLE_PIX_OUT=false
ENABLE_KYC=false
ENABLE_DDA=false
ENABLE_REAL_BANKING=false
```

**Todas default `false` em produção.** Ativação requer:
1. Provider configurado
2. Ambiente não-demo
3. Validação de segurança

---

## Recomendação para Sprint 14

A Sprint 14 deve implementar a **Fase 1 — Provider Foundation**:

1. Criar tabelas: `provider_connections`, `provider_webhook_events`, `organization_audit_logs`, `open_finance_consents`
2. Implementar fake providers funcionais com testes
3. Implementar consent service básico
4. Criar provider factory com feature flag validation
5. Adicionar endpoint interno de status de providers
6. Garantir que nenhuma feature flag regulada pode ser ativada sem provider configurado

---

## Regras Cumpridas

- ✅ Nenhuma operação regulada implementada diretamente
- ✅ Nenhum provider real integrado
- ✅ Nenhum Pix Out real
- ✅ Nenhum Open Finance real
- ✅ Nenhum BaaS real
- ✅ Nenhum pagamento real de boletos
- ✅ Nenhum segredo commitado
- ✅ Provider padrão continua fake/sandbox
- ✅ Feature flags reguladas default false
- ✅ Todas as features reguladas atrás de provider abstraction
