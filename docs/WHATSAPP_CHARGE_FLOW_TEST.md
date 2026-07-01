# Fluxo de Cobrança via WhatsApp — Teste Prático

Este documento descreve o fluxo completo de criação, confirmação, pagamento e consulta de cobranças via WhatsApp usando o provider **fake** (padrão do projeto).

## Pré-requisitos

- Projeto rodando com `docker-compose up -d`
- Twilio Sandbox configurado e webhook apontando para `/webhook/whatsapp`
- `PAYFLOW_PAYMENT_PROVIDER=fake` no `.env`
- Usuário cadastrado e com assinatura ativa
- `TWILIO_VALIDATE_SIGNATURE=false` em desenvolvimento (opcional)

## Fluxo Completo

### 1. Criar cobrança (com confirmação explícita)

```
Usuário: Gere uma cobrança de R$ 150 para João referente ao serviço do site

Bot: 💰 *Cobrança de R$ 150.00*
👤 Cliente: João
📝 Referente a: serviço do site

Deseja confirmar e gerar o link de pagamento?
Responda *sim* ou *confirmo*.
```

### 2. Confirmar cobrança

```
Usuário: confirmo

Bot: ✅ *Cobrança criada com sucesso!*

👤 Cliente: João
💰 Valor: R$ 150.00
📝 Referente a: serviço do site
🔗 Link de pagamento: https://fake.payflow.ai/pay/fake_abc123

Vou te avisar assim que o pagamento for confirmado. 🔔
```

### 3. Simular pagamento (provider fake)

Via terminal:

```bash
curl -X POST http://localhost:8000/provider-webhooks/fake/pay/fake_abc123
```

Ou via webhook genérico:

```bash
curl -X POST http://localhost:8000/provider-webhooks/fake \
  -H "Content-Type: application/json" \
  -d '{"event_type": "payment.approved", "provider_charge_id": "fake_abc123", "amount": 150.00}'
```

### 4. Notificação automática de pagamento

```
Bot: ✅ *Pagamento recebido!*

João pagou *R$ 150.00* referente a *serviço do site*.

Obrigado por usar o PayFlow AI! 🎉
```

### 5. Dashboard

A cobrança agora aparece como **paga** no dashboard web, na seção de cobranças.

---

## Exemplos de Mensagens Suportadas

### Criar cobrança

```
Gere uma cobrança de R$ 150 para João referente ao serviço do site
Crie um link de pagamento de R$ 89,90 para Maria
Cobra R$ 300 do Pedro pelo projeto
Gere uma cobrança de R$ 200 para João com vencimento amanhã
Cobra R$ 500 da Maria para sexta-feira
Cria uma cobrança de R$ 1000 para Pedro com vencimento dia 10
```

### Listar cobranças

```
Mostre minhas cobranças
Quais cobranças estão pendentes?
Alguma cobrança foi paga?
```

### Cancelar cobrança

```
Cancela a cobrança do João
Cancela a última cobrança
Cancela a cobrança de R$ 150
```

### Confirmar ação pendente

```
confirmo
sim
pode gerar
pode criar
```

### Cancelar ação pendente

```
cancela
não
deixa pra lá
desiste
```

---

## Resposta de Listagem

Quando o usuário pede "Mostre minhas cobranças":

```
📋 *Suas últimas cobranças:*

1. João — R$ 150.00 — pendente
2. Maria — R$ 89.90 — pago
3. Pedro — R$ 300.00 — vencida

Resumo:
A receber: R$ 450.00
Recebido: R$ 89.90
```

Quando pede "Quais cobranças estão pendentes?":

```
⏳ *Cobranças pendentes:*

1. João — R$ 150.00 — vence amanhã
2. Pedro — R$ 300.00 — vencida
```

Quando pede "Alguma cobrança foi paga?":

```
✅ *Cobranças pagas:*

1. Maria — R$ 89.90 — paga em 01/07/2026
```

---

## Cancelamento via WhatsApp

O sistema entende referências como nome do cliente, valor ou "última cobrança":

```
Usuário: Cancela a cobrança do João
Bot: 🚫 Cobrança de R$ 150.00 para João cancelada com sucesso.
```

Se houver ambiguidade:

```
Usuário: Cancela a cobrança de R$ 150
Bot: Encontrei mais de uma cobrança de R$ 150.00:
1. João — R$ 150.00 — pendente
2. Pedro — R$ 150.00 — pendente
Qual você deseja cancelar? Responda com o número.
```

Não é possível cancelar cobranças já pagas:

```
Usuário: Cancela a cobrança da Maria
Bot: ❌ A cobrança de R$ 89.90 para Maria já foi paga e não pode ser cancelada.
```

---

## Vencimento

O sistema extrai datas de vencimento de mensagens como:

- "com vencimento amanhã"
- "para sexta-feira"
- "com vencimento dia 10"
- "vence dia 15/07"

Se `due_date` passou e o status ainda é `pending`, a cobrança é considerada **vencida** no resumo e na listagem.

---

## Lembretes Automáticos

O serviço de lembretes (`ChargeReminderService`) pode ser acionado manualmente:

```bash
curl -X POST http://localhost:8000/charges/reminders/run \
  -H "Authorization: Bearer <token>"
```

Mensagens enviadas:

- **Próximo ao vencimento:** `Lembrete: a cobrança de R$ 150,00 para João vence amanhã.`
- **Vencida:** `Atenção: a cobrança de R$ 150,00 para João está vencida desde 10/07/2026.`

O sistema evita enviar lembretes duplicados no mesmo dia.
