# Jota vs PayFlow — Matriz de Paridade

> Sprint 13 — Jota Feature Parity Blueprint
> Base: commit `9cf7392` (Sprint 12.1)

---

## Matriz de Funcionalidades

| # | Funcionalidade | Jota | PayFlow atual | Gap | Tipo | Provider necessário | Prioridade | Sprint sugerida |
|---|---|---|---|---|---|---|---|---|
| 1 | IA conversacional no WhatsApp | ✅ Confirmado | ✅ Implementado (texto, áudio, imagem) | Nenhum | internal | Nenhum | — | — |
| 2 | Cobrança via Pix (QR Code) | ✅ Confirmado | ✅ Sandbox (fake provider) | Real charge provider | sandbox | Asaas / Celcoin / QI Tech | P0 | Sprint 14 |
| 3 | Cobrança por texto/áudio/imagem | ✅ Confirmado | ✅ Implementado (texto/áudio/imagem) | Nenhum (sandbox) | internal | Nenhum | — | — |
| 4 | Confirmação de recebimento no chat | ✅ Confirmado | ✅ Webhook simulado | Real webhook | sandbox | Asaas / Celcoin | P0 | Sprint 14 |
| 5 | Extrato de cobranças filtrável | ✅ Confirmado | ✅ Dashboard + analytics | Nenhum | internal | Nenhum | — | — |
| 6 | Conta digital (conta de pagamento) | ✅ Confirmado (Celcoin) | ❌ Não implementado | Conta + BaaS | regulated_provider | Celcoin / QI Tech / Dock | P0 | Sprint 18+ |
| 7 | Pix Out (envio de dinheiro) | ✅ Confirmado | ❌ Não implementado | Pix provider + BaaS | regulated_provider | Celcoin / QI Tech | P0 | Sprint 18+ |
| 8 | Pix por áudio | ✅ Confirmado | ✅ IA processa áudio (sandbox) | Real Pix provider | regulated_provider | Celcoin / QI Tech | P0 | Sprint 18+ |
| 9 | Pagamento de boleto | ✅ Confirmado | ❌ Não implementado | Bill payment provider | regulated_provider | Celcoin / QI Tech | P0 | Sprint 17+ |
| 10 | Pagamento de boleto por foto (OCR) | ✅ Confirmado | ✅ OCR implementado (sandbox) | Real bill payment | regulated_provider | Celcoin + OCR | P0 | Sprint 17+ |
| 11 | DDA (detecção automática de boletos) | ✅ Confirmado | ❌ Não implementado | DDA provider | regulated_provider | Celcoin / Dock | P1 | Sprint 17+ |
| 12 | Open Finance (saldo, extrato, transações) | ✅ Confirmado (20+ bancos) | ❌ Não implementado | Open Finance provider | regulated_provider | Pluggy / Belvo / Celcoin | P0 | Sprint 16 |
| 13 | Consentimento Open Finance | ✅ Confirmado | ❌ Não implementado | Consent model + provider | regulated_provider | Pluggy / Belvo | P0 | Sprint 16 |
| 14 | Escolha de conta para débito | ✅ Confirmado | ❌ Não implementado | Open Finance + payment init | regulated_provider | Pluggy / Belvo / Celcoin | P1 | Sprint 17+ |
| 15 | Rendimento automático (100% CDI) | ✅ Confirmado | ❌ Não implementado | BaaS + investimento | regulated_provider | Celcoin / QI Tech | P2 | Sprint 19+ |
| 16 | Lembretes inteligentes | ✅ Confirmado | ✅ Implementado (recurring tasks) | Nenhum | internal | Nenhum | — | — |
| 17 | Tarefas recorrentes | ✅ Confirmado | ✅ Implementado | Nenhum | internal | Nenhum | — | — |
| 18 | Agendamento de pagamento | ✅ Confirmado | ❌ Não implementado | Bill payment + scheduler | regulated_provider | Celcoin / QI Tech | P1 | Sprint 17+ |
| 19 | Pré-autorização de regras | ✅ Confirmado | ❌ Não implementado | Consent + rules engine | compliance | Nenhum (interno) | P1 | Sprint 15 |
| 20 | Senha de 6 dígitos por transação | ✅ Confirmado | ❌ Não implementado | Transaction auth | security | Nenhum (interno) | P0 | Sprint 15 |
| 21 | KYC (biometria facial, documento) | ✅ Confirmado (Unico) | ❌ Não implementado | KYC provider | compliance | Unico / Caf / Certta | P0 | Sprint 16 |
| 22 | Meta Business Verified | ✅ Confirmado | ❌ Não confirmado | Verificação Meta | compliance | Meta | P1 | Sprint 14 |
| 23 | Fala Tap (maquininha por voz/NFC) | ✅ Confirmado | ❌ Não implementado | Tap to Phone + app | regulated_provider | Celcoin + NFC SDK | P3 | Sprint 20+ |
| 24 | "Meu Time" (vendedores com acessos) | ✅ Confirmado | ✅ Multi-tenant + RBAC | Nenhum (estrutura existe) | internal | Nenhum | — | — |
| 25 | Multi-banco (visão consolidada) | ✅ Confirmado | ❌ Não implementado | Open Finance | regulated_provider | Pluggy / Belvo | P0 | Sprint 16 |
| 26 | Categorização de gastos | [Inferido] | ❌ Não implementado | IA + Open Finance data | data | Pluggy / Belvo + IA | P1 | Sprint 16 |
| 27 | Comprovante de pagamento | ✅ Confirmado | ✅ Charge com status (sandbox) | Real comprovante | sandbox | Asaas / Celcoin | P0 | Sprint 14 |
| 28 | Carteira compartilhada | [Não confirmado] | ❌ Não implementado | Multi-user wallet | regulated_provider | BaaS | P3 | Futuro |
| 29 | Cartão de crédito (crédito parcelado) | ✅ Confirmado (Fala Tap) | ❌ Não implementado | Card acquiring | regulated_provider | Celcoin / adquirente | P3 | Sprint 20+ |
| 30 | Link de pagamento | [Inferido] | ❌ Não implementado | Payment link provider | sandbox | Asaas / Celcoin | P1 | Sprint 14 |
| 31 | Webhooks de recebimento | ✅ Confirmado | ✅ Webhook simulado | Real webhook | sandbox | Asaas / Celcoin | P0 | Sprint 14 |
| 32 | Relatórios de vendas | ✅ Confirmado | ✅ Analytics implementado | Nenhum | internal | Nenhum | — | — |
| 33 | Suporte dentro do WhatsApp | ✅ Confirmado | ✅ WhatsApp interface | Nenhum | internal | Nenhum | — | — |
| 34 | Onboarding via WhatsApp (2 min) | ✅ Confirmado | ❌ Não implementado | KYC + onboarding flow | compliance | Unico + Celcoin | P0 | Sprint 16 |
| 35 | Antifraude transacional | ✅ Confirmado | ❌ Não implementado | Fraud provider | compliance | Unico / Solução própria | P1 | Sprint 16 |
| 36 | LGPD compliance | ✅ Confirmado | ✅ Parcial (logs, RBAC) | Consent management | compliance | Nenhum (interno) | P0 | Sprint 15 |
| 37 | SaaS Billing (planos, limites) | ❌ Não confirmado | ✅ Implementado (Sprint 12) | Nenhum (diferencial PayFlow) | internal | Nenhum | — | — |
| 38 | Multi-organização (SaaS) | ❌ Não confirmado | ✅ Implementado (Sprint 11) | Nenhum (diferencial PayFlow) | internal | Nenhum | — | — |
| 39 | Collection intelligence (cobrança IA) | ❌ Não confirmado | ✅ Implementado (Sprint 9) | Nenhum (diferencial PayFlow) | internal | Nenhum | — | — |
| 40 | Templates de mensagem | ❌ Não confirmado | ✅ Implementado | Nenhum (diferencial PayFlow) | internal | Nenhum | — | — |

---

## Resumo de Gaps por Prioridade

### P0 — Obrigatório para paridade
1. Real charge provider (Pix cobrança, boleto, webhook, comprovante)
2. Conta digital (BaaS)
3. Pix Out
4. Pagamento de boleto
5. Open Finance (saldo, extrato, transações)
6. Consentimento Open Finance
7. KYC (biometria facial, documento)
8. Senha de 6 dígitos por transação
9. LGPD compliance (consent management)
10. Onboarding via WhatsApp

### P1 — Importante
1. DDA (detecção automática de boletos)
2. Escolha de conta para débito
3. Agendamento de pagamento
4. Pré-autorização de regras
5. Meta Business Verified
6. Categorização de gastos
7. Link de pagamento
8. Antifraude transacional

### P2 — Desejável
1. Rendimento automático (100% CDI)

### P3 — Futuro
1. Fala Tap (maquininha por voz/NFC)
2. Carteira compartilhada
3. Cartão de crédito (crédito parcelado)

---

## Diferenciais do PayFlow (não presentes no Jota)

| Funcionalidade | PayFlow | Jota |
|---|---|---|
| SaaS Billing com planos e limites | ✅ | ❌ Não confirmado |
| Multi-organização (SaaS B2B) | ✅ | ❌ Não confirmado |
| Collection intelligence com IA | ✅ | ❌ Não confirmado |
| Templates de mensagem personalizáveis | ✅ | ❌ Não confirmado |
| Analytics avançado de cobrança | ✅ | ❌ Não confirmado |
| RBAC granular (owner/admin/finance/viewer) | ✅ | ❌ Não confirmado |
| Regras de cobrança automatizadas | ✅ | ❌ Não confirmado |

> O PayFlow tem foco **B2B SaaS** (gestão de cobranças para negócios), enquanto o Jota tem foco **B2C/PF + PJ** (conta digital pessoal). A paridade não significa replicar 1:1, mas sim cobrir as funcionalidades que um usuário esperaria de um assistente financeiro no WhatsApp.
