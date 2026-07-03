# WhatsApp Jota Parity Commands

> Sprint 13 — Jota Feature Parity Blueprint
> Mapeia comandos de WhatsApp necessários para paridade com o Jota.

---

## Comandos Mapeados

### 1. "quais contas vencem hoje?"

| Aspecto | Detalhe |
|---|---|
| Intent | `list_bills_due_today` |
| Provider necessário | DDAProvider (real) ou dados internos (se boleto cadastrado manualmente) |
| Risco | Baixo (apenas leitura) |
| Confirmação necessária | Nenhuma |
| Status no PayFlow | ❌ Não implementado (depende de DDA ou cadastro manual de contas) |
| Resposta esperada | Lista de boletos com vencimento no dia, com valor e beneficiário |
| Sandbox ou real | Sandbox com fake DDA provider; real com Celcoin/DDA provider |

---

### 2. "pague essa conta"

| Aspecto | Detalhe |
|---|---|
| Intent | `pay_bill` |
| Provider necessário | BillPaymentProvider + BankingProvider (para débito) |
| Risco | Alto — liquidação financeira real |
| Confirmação necessária | Sim — senha de 6 dígitos + confirmação explícita |
| Status no PayFlow | ❌ Não implementado |
| Resposta esperada | PayFlow valida boleto, mostra detalhes, solicita confirmação e senha, executa pagamento, envia comprovante |
| Sandbox ou real | Sandbox com fake provider (sem liquidação); real com Celcoin/QI Tech |

---

### 3. "quanto tenho disponível?"

| Aspecto | Detalhe |
|---|---|
| Intent | `get_balance` |
| Provider necessário | BankingProvider (conta PayFlow) ou OpenFinanceProvider (contas conectadas) |
| Risco | Baixo (apenas leitura) |
| Confirmação necessária | Nenhuma |
| Status no PayFlow | ❌ Não implementado |
| Resposta esperada | Saldo disponível na conta PayFlow + saldos de contas conectadas via Open Finance |
| Sandbox ou real | Sandbox com fake provider; real com Celcoin + Pluggy/Belvo |

---

### 4. "qual foi meu gasto com mercado?"

| Aspecto | Detalhe |
|---|---|
| Intent | `categorize_spending` |
| Provider necessário | OpenFinanceProvider (transações) + IA (categorização) |
| Risco | Baixo (apenas leitura) |
| Confirmação necessária | Nenhuma |
| Status no PayFlow | ❌ Não implementado (IA existe, mas não tem acesso a transações reais) |
| Resposta esperada | Total gasto na categoria "mercado" no período, com breakdown de transações |
| Sandbox ou real | Sandbox com transações fake; real com Pluggy/Belvo |

---

### 5. "mostrar boletos pendentes"

| Aspecto | Detalhe |
|---|---|
| Intent | `list_pending_bills` |
| Provider necessário | DDAProvider ou dados internos |
| Risco | Baixo (apenas leitura) |
| Confirmação necessária | Nenhuma |
| Status no PayFlow | ❌ Não implementado |
| Resposta esperada | Lista de boletos pendentes com valor, vencimento e beneficiário |
| Sandbox ou real | Sandbox com fake DDA; real com Celcoin/DDA |

---

### 6. "me avise antes do vencimento"

| Aspecto | Detalhe |
|---|---|
| Intent | `create_reminder` |
| Provider necessário | Nenhum (interno) |
| Risco | Nenhum |
| Confirmação necessária | Nenhuma |
| Status no PayFlow | ✅ Implementado (recurring tasks + lembretes) |
| Resposta esperada | Confirmação de lembrete criado com data e horário |
| Sandbox ou real | Interno (já funciona) |

---

### 7. "agendar este pagamento"

| Aspecto | Detalhe |
|---|---|
| Intent | `schedule_payment` |
| Provider necessário | BillPaymentProvider + BankingProvider |
| Risco | Alto — pagamento agendado executa automaticamente |
| Confirmação necessária | Sim — senha de 6 dígitos no momento do agendamento + confirmação no dia |
| Status no PayFlow | ❌ Não implementado |
| Resposta esperada | PayFlow confirma agendamento com data, valor e detalhes do boleto |
| Sandbox ou real | Sandbox com fake provider; real com Celcoin/QI Tech |

---

### 8. "enviar comprovante"

| Aspecto | Detalhe |
|---|---|
| Intent | `send_receipt` |
| Provider necessário | ReceiptProvider |
| Risco | Baixo (apenas leitura/envio) |
| Confirmação necessária | Nenhuma |
| Status no PayFlow | ❌ Não implementado (PayFlow tem charge com status, mas não comprovante formal) |
| Resposta esperada | PDF ou imagem do comprovante da transação solicitada |
| Sandbox ou real | Sandbox com fake receipt; real integrado com charge provider |

---

### 9. "resumir meus gastos do mês"

| Aspecto | Detalhe |
|---|---|
| Intent | `summarize_spending` |
| Provider necessário | OpenFinanceProvider (transações) + IA (resumo) |
| Risco | Baixo (apenas leitura) |
| Confirmação necessária | Nenhuma |
| Status no PayFlow | ❌ Não implementado (IA existe, mas não tem acesso a transações) |
| Resposta esperada | Resumo com total gasto, principais categorias, comparação com mês anterior |
| Sandbox ou real | Sandbox com transações fake; real com Pluggy/Belvo |

---

### 10. "qual cliente está devendo?"

| Aspecto | Detalhe |
|---|---|
| Intent | `list_overdue_charges` |
| Provider necessário | Nenhum (interno — dados de cobranças do PayFlow) |
| Risco | Nenhum |
| Confirmação necessária | Nenhuma |
| Status no PayFlow | ✅ Parcialmente implementado (charges com status overdue, mas não via WhatsApp) |
| Resposta esperada | Lista de cobranças vencidas com cliente, valor e dias de atraso |
| Sandbox ou real | Interno (já funciona no dashboard; falta comando WhatsApp) |

---

### 11. "gerar cobrança para João"

| Aspecto | Detalhe |
|---|---|
| Intent | `create_charge` |
| Provider necessário | PixProvider (real) ou interno (sandbox) |
| Risco | Médio — gera cobrança em nome da organização |
| Confirmação necessária | Sim — confirmação de dados do cliente e valor |
| Status no PayFlow | ✅ Implementado (sandbox) — cria charge com QR Code simulado |
| Resposta esperada | PayFlow cria cobrança, gera QR Code Pix, envia link para o cliente |
| Sandbox ou real | Sandbox atual; real com Asaas/Celcoin |

---

### 12. "conectar minha conta"

| Aspecto | Detalhe |
|---|---|
| Intent | `connect_bank_account` |
| Provider necessário | OpenFinanceProvider |
| Risco | Médio — consentimento de dados bancários |
| Confirmação necessária | Sim — autorização no app do banco (link de consentimento) |
| Status no PayFlow | ❌ Não implementado |
| Resposta esperada | PayFlow gera link de consentimento, usuário autoriza no app do banco |
| Sandbox ou real | Sandbox com fake Open Finance; real com Pluggy/Belvo |

---

### 13. "trocar organização"

| Aspecto | Detalhe |
|---|---|
| Intent | `switch_organization` |
| Provider necessário | Nenhum (interno) |
| Risco | Nenhum |
| Confirmação necessária | Nenhuma |
| Status no PayFlow | ❌ Não implementado via WhatsApp (existe no dashboard) |
| Resposta esperada | PayFlow lista organizações do usuário, usuário escolhe qual usar |
| Sandbox ou real | Interno |

---

## Resumo de Status

| Status | Quantidade | Comandos |
|---|---|---|
| ✅ Implementado | 3 | "me avise antes do vencimento", "gerar cobrança para João", "qual cliente está devendo?" (parcial) |
| ❌ Não implementado | 10 | "quais contas vencem hoje?", "pague essa conta", "quanto tenho disponível?", "qual foi meu gasto com mercado?", "mostrar boletos pendentes", "agendar este pagamento", "enviar comprovante", "resumir meus gastos do mês", "conectar minha conta", "trocar organização" |

---

## Comandos Adicionais Sugeridos (não presentes no Jota, mas relevantes)

| Comando | Intent | Status |
|---|---|---|
| "criar template de cobrança" | `create_template` | ✅ Implementado (dashboard) |
| "listar cobranças do mês" | `list_charges` | ✅ Implementado (dashboard) |
| "analisar documento" | `analyze_document` | ✅ Implementado (OCR sandbox) |
| "configurar regra de cobrança" | `create_collection_rule` | ✅ Implementado (dashboard) |
| "relatório de inadimplência" | `report_overdue` | ✅ Implementado (analytics) |
