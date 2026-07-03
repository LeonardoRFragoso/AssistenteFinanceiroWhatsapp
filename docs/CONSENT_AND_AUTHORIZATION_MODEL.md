# Consent and Authorization Model

> Sprint 13 — Jota Feature Parity Blueprint
> Define o modelo de consentimento, autorização e confirmação para o PayFlow AI.

---

## Princípios

1. **Consentimento explícito**: Nenhuma operação financeira é executada sem consentimento explícito do usuário.
2. **Senha de transação**: Operações financeiras exigem senha de 6 dígitos (tela exclusiva, nunca no histórico do WhatsApp).
3. **Revogação a qualquer momento**: Usuário pode revogar consentimento quando quiser.
4. **Expiração automática**: Consentimentos têm prazo de validade.
5. **LGPD**: Todos os consentimentos seguem a Lei Geral de Proteção de Dados.
6. **Auditoria**: Todo consentimento, autorização e revogação é logado.
7. **Princípio mínimo**: Apenas dados necessários são compartilhados.

---

## Tipos de Consentimento

### 1. Consentimento Open Finance

**Escopo**: Compartilhamento de dados bancários via Open Finance.

| Aspecto | Detalhe |
|---|---|
| Quem autoriza | Owner ou Admin da organização |
| Duração | 12 meses (renovável) |
| Revogação | A qualquer momento via WhatsApp ou dashboard |
| Dados compartilhados | Saldos, extratos, transações (conforme escopo autorizado) |
| Provider | Pluggy / Belvo / Celcoin |
| Armazenamento | Token de consentimento (não credenciais bancárias) |
| Expiração | Automática após 12 meses ou revogação |
| Notificação | Usuário é notificado 30 dias antes da expiração |

**Fluxo**:
```
Usuário: "Jota, quero conectar meu Nubank"
    │
    ▼
PayFlow gera link de consentimento (via provider)
    │
    ▼
Usuário autoriza no app do banco
    │
    ▼
Provider notifica PayFlow (webhook)
    │
    ▼
PayFlow registra consentimento (tabela open_finance_consents)
    │
    ▼
Dados disponíveis para consulta
```

### 2. Consentimento WhatsApp

**Escopo**: Autorização para processar mensagens e comandos via WhatsApp.

| Aspecto | Detalhe |
|---|---|
| Quem autoriza | Usuário individual (PF ou PJ) |
| Duração | Indefinida (até revogação ou desativação da conta) |
| Revogação | A qualquer momento (parar de usar o WhatsApp do PayFlow) |
| Dados processados | Mensagens, áudios, imagens, dados de conversa |
| Base legal | Legítimo interesse + consentimento |
| LGPD | Art. 7º, IX e Art. 8º |

### 3. Confirmação Explícita de Pagamento

**Escopo**: Autorização para executar pagamento (Pix Out, boleto, conta).

| Aspecto | Detalhe |
|---|---|
| Quem autoriza | Owner, Admin, ou Finance (conforme configuração) |
| Método | Senha de 6 dígitos (tela exclusiva) |
| Validade da autorização | Única (uma transação) |
| Tentativas máximas | 3 (após isso, bloqueio por 30 minutos) |
| Log | Sim (payment_authorizations) |
| Reversibilidade | Não (após execução) |

**Fluxo**:
```
Usuário: "Pague R$ 150 de energia"
    │
    ▼
PayFlow valida boleto/conta
    │
    ▼
PayFlow apresenta detalhes: beneficiário, valor, vencimento
    │
    ▼
Usuário confirma: "Pode pagar"
    │
    ▼
PayFlow solicita senha (tela exclusiva)
    │
    ▼
Senha validada → Pagamento executado
    │
    ▼
Comprovante enviado no WhatsApp
```

### 4. Confirmação de Cobrança

**Escopo**: Autorização para gerar cobrança (Pix, boleto) em nome da organização.

| Aspecto | Detalhe |
|---|---|
| Quem autoriza | Owner, Admin, ou Finance |
| Método | Confirmação simples no WhatsApp ("Pode gerar") |
| Validade | Única |
| Log | Sim (billing_events) |

### 5. Consentimento LGPD

**Escopo**: Autorização para processamento de dados pessoais.

| Aspecto | Detalhe |
|---|---|
| Quem autoriza | Usuário individual |
| Duração | Enquanto a conta estiver ativa |
| Revogação | A qualquer momento (exclusão de conta) |
| Dados | Nome, CPF/CNPJ, telefone, dados financeiros |
| Documento | Termos de uso + Política de privacidade |
| Log | Sim (organization_audit_logs) |

---

## Roles e Autorização

| Role | Ver dados | Criar cobrança | Autorizar pagamento | Gerenciar consentimento | Gerenciar billing |
|---|---|---|---|---|---|
| Owner | ✅ | ✅ | ✅ | ✅ | ✅ |
| Admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| Finance | ✅ | ✅ | ✅ (configurável) | ❌ | ❌ |
| Viewer | ✅ (limitado) | ❌ | ❌ | ❌ | ❌ |

> **Configurável**: Owner pode definir se Finance tem autorização de pagamento ou não.

---

## Pré-autorização de Regras

O sistema deve suportar regras de pré-autorização para automatizar pagamentos recorrentes:

```json
{
  "rule": {
    "max_amount": 100.00,
    "recipient": "Empresa de Energia XYZ",
    "frequency": "monthly",
    "expires_at": "2026-12-31",
    "requires_password": true
  }
}
```

**Limites da pré-autorização**:
- Valor máximo por transação
- Recebedor específico (ou lista de recebedores aprovados)
- Frequência (mensal, semanal, única)
- Data de expiração
- Sempre exige senha (mesmo em pré-autorização)
- Owner pode revogar a qualquer momento
- Log de cada execução

---

## Expiração e Renovação

| Tipo de consentimento | Prazo | Renovação | Notificação prévia |
|---|---|---|---|
| Open Finance | 12 meses | Manual (reautorização) | 30 dias antes |
| WhatsApp | Indefinido | Automático (uso contínuo) | N/A |
| Pagamento | Único | N/A | N/A |
| LGPD | Indefinido (enquanto ativo) | Automático | N/A |
| Pré-autorização | Configurável (máx 12 meses) | Manual | 7 dias antes |

---

## Revogação

Todo consentimento pode ser revogado a qualquer momento:

1. **Via WhatsApp**: "Quero revogar o consentimento do banco X"
2. **Via Dashboard**: Menu de consentimentos → Revogar
3. **Via API**: `DELETE /consents/{id}`

**Efeitos da revogação**:
- Open Finance: Dados não são mais atualizados (dados já coletados são mantidos conforme LGPD)
- Pré-autorização: Regras canceladas, pagamentos agendados cancelados
- LGPD: Inicia processo de exclusão de dados (conforme prazo legal)

---

## Logs e Auditoria

Todo evento de consentimento é registrado em `organization_audit_logs`:

| Campo | Descrição |
|---|---|
| `organization_id` | Organização |
| `user_id` | Usuário que autorizou/revogou |
| `action` | `consent.created`, `consent.revoked`, `consent.expired`, `payment.authorized`, `payment.denied` |
| `scope` | `open_finance`, `payment`, `lgpd`, `whatsapp` |
| `metadata` | Detalhes (provider, banco, valor, etc.) |
| `timestamp` | Data e hora |
| `ip_address` | IP de origem (se aplicável) |

---

## Dados Sensíveis

| Dado | Armazenamento | Criptografia | Retenção |
|---|---|---|---|
| Senha de 6 dígitos | Hash (bcrypt) | Sim | Indefinida (até exclusão) |
| Token de consentimento Open Finance | Tabela `open_finance_consents` | Sim | 12 meses + 6 meses (LGPD) |
| Dados biométricos (KYC) | **Não armazenados** — apenas resultado | N/A | N/A |
| Dados de transações | Tabela `bank_transactions` | Sim | 5 anos (requerimento regulatório) |
| Dados de pagamento | Tabela `bill_payment_intents` | Sim | 5 anos |

---

## Segurança

1. **Senha nunca no histórico do WhatsApp**: Tela exclusiva para entrada de senha.
2. **Criptografia em trânsito**: TLS 1.2+ para todas as comunicações.
3. **Criptografia em repouso**: Dados sensíveis criptografados no banco.
4. **Rate limiting**: Máximo 3 tentativas de senha, bloqueio de 30 minutos.
5. **2FA opcional**: Para operações acima de R$ 1.000 (configurável).
6. **Notificação de atividade**: Usuário é notificado de novas conexões, consentimentos e transações.
