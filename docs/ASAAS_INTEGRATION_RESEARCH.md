# Asaas API Integration Research

> Sprint 15 — Real Charge Provider Integration
> Pesquisa da API pública do Asaas para integração de cobranças recebíveis em sandbox.

---

## Links Consultados

| Recurso | URL | Status |
|---|---|---|
| Sandbox | https://docs.asaas.com/docs/sandbox-1 | Confirmado |
| Initial Settings | https://docs.asaas.com/docs/initial-settings | Confirmado |
| Creating Customers | https://docs.asaas.com/docs/creating-customers | Confirmado |
| Create New Payment (Reference) | https://docs.asaas.com/reference/create-new-payment | Confirmado |
| Payments via Pix | https://docs.asaas.com/docs/payments-via-pix-or-dynamic-qr-code | Confirmado |
| Bank Slip Charges | https://docs.asaas.com/docs/payments-via-bank-slip | Confirmado |
| Payment Events (Webhooks) | https://docs.asaas.com/docs/payment-events | Confirmado |
| Webhook Events | https://docs.asaas.com/docs/webhooks-events | Confirmado |
| Receive Webhook Events | https://docs.asaas.com/docs/receive-asaas-events-at-your-webhook-endpoint | Confirmado |
| Create Webhook via API | https://docs.asaas.com/docs/create-new-webhook-via-api | Confirmado |
| Postman Collection | https://www.postman.com/gfjgabrielesparta/apis-de-pagamento/documentation/7mah0dx/api-asaas-v3 | Confirmado |

---

## Ambientes

| Ambiente | URL Base | Uso |
|---|---|---|
| Sandbox | `https://sandbox.asaas.com/api/v3` | Testes |
| Produção | `https://api.asaas.com/api/v3` | Operações reais |

> **Confirmado**: API Keys são distintas entre sandbox e produção. Deve-se alterar a key ao mudar de ambiente.

---

## Autenticação

- **Header**: `access_token: <API_KEY>`
- **Sandbox**: API key obtida em https://sandbox.asaas.com
- **Produção**: API key obtida em https://www.asaas.com
- **Erro 401**: API key inválida ou não informada
- **Segurança**: API key nunca deve ser logada, commitada, ou exposta em endpoints.

> **Confirmado**: A API key é enviada no header `access_token` em todas as requisições.

---

## 1. Criar Cliente (Customer)

### Endpoint
```
POST /v3/customers
```

### Body (mínimo)
```json
{
  "name": "John Doe",
  "cpfCnpj": "19540550000121",
  "mobilePhone": "4799376637"
}
```

### Response
```json
{
  "id": "cus_000005219613",
  "name": "John Doe",
  ...
}
```

### Campos
| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `name` | string | Sim | Nome do cliente |
| `cpfCnpj` | string | Sim* | CPF ou CNPJ (apenas para cobrança real) |
| `mobilePhone` | string | Não | Telefone |
| `email` | string | Não | Email |
| `externalReference` | string | Não | ID no nosso sistema |

> **Confirmado**: Criação de clientes duplicados é permitida. Para evitar, buscar antes de criar.
> **Inferido**: Em sandbox, `cpfCnpj` pode ser fictício mas deve ter formato válido.

### Regras para PayFlow
- **Não inventar CPF/CNPJ**: Se não tiver documento, usar valor sandbox válido ou bloquear.
- Em sandbox, Asaas aceita CPFs fictícios formatados corretamente.
- **Estratégia**: Para sandbox, gerar CPF válido aleatório se não fornecido. Para produção, exigir CPF/CNPJ.

---

## 2. Criar Cobrança (Payment)

### Endpoint
```
POST /v3/payments
```

### Body
```json
{
  "customer": "cus_000005219613",
  "billingType": "PIX",
  "value": 100.90,
  "dueDate": "2023-07-21",
  "description": "Pedido 056984",
  "externalReference": "payflow_charge_123"
}
```

### billingType (Confirmado)
| Valor | Descrição |
|---|---|
| `BOLETO` | Boleto bancário |
| `PIX` | Pix QR Code |
| `CREDIT_CARD` | Cartão de crédito |
| `UNDEFINED` | Payer escolhe método (link de pagamento) |

### Campos
| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `customer` | string | Sim | ID do customer (cus_xxx) |
| `billingType` | enum | Sim | BOLETO, PIX, CREDIT_CARD, UNDEFINED |
| `value` | number | Sim | Valor da cobrança (parcela única) |
| `dueDate` | date | Sim | Data de vencimento (YYYY-MM-DD) |
| `description` | string | Não | Max 500 caracteres |
| `externalReference` | string | Não | ID no nosso sistema |

### Response
```json
{
  "id": "pay_xxxxx",
  "status": "PENDING",
  "value": 100.90,
  "billingType": "PIX",
  "invoiceUrl": "https://sandbox.asaas.com/i/xxxxx",
  "bankSlipUrl": null,
  ...
}
```

### Campos de Retorno Importantes
| Campo | Descrição |
|---|---|
| `id` | ID do pagamento (pay_xxx) |
| `status` | Status do pagamento |
| `invoiceUrl` | URL da fatura/link de pagamento |
| `bankSlipUrl` | URL do boleto em PDF (apenas BOLETO) |

> **Confirmado**: Para PIX, é necessário uma chamada adicional para obter o QR Code.

---

## 3. Obter QR Code Pix

### Endpoint
```
GET /v3/payments/{id}/pixQrCode
```

### Response
```json
{
  "encodedImage": "data:image/png;base64,...",
  "payload": "00020126580014br.gov.bcb.pix...",
  "expirationDate": "2023-07-21T23:59:59"
}
```

### Campos
| Campo | Descrição |
|---|---|
| `encodedImage` | Imagem do QR Code em base64 |
| `payload` | Código copia e cola (Pix) |
| `expirationDate` | Data de expiração do QR Code |

> **Confirmado**: Disponível apenas para pagamentos com `billingType: PIX`.

---

## 4. Obter Status de Pagamento

### Endpoint
```
GET /v3/payments/{id}
```

### Response
```json
{
  "id": "pay_xxxxx",
  "status": "RECEIVED",
  "value": 100.90,
  ...
}
```

---

## 5. Cancelar Pagamento

### Endpoint
```
DELETE /v3/payments/{id}
```

> **Confirmado**: Cancela a cobrança. Status muda para `DELETED`.

---

## 6. Status de Pagamento (Confirmado)

| Status | Descrição | Mapeamento PayFlow |
|---|---|---|
| `PENDING` | Aguardando pagamento | `pending` |
| `RECEIVED` | Pagamento recebido (saldo disponível) | `paid` |
| `CONFIRMED` | Pagamento confirmado (saldo ainda não disponível) | `paid` |
| `OVERDUE` | Vencido | `expired` |
| `REFUNDED` | Reembolsado | `cancelled` |
| `RECEIVED_IN_CASH_UNDONE` | Recebimento em dinheiro desfeito | `pending` |
| `DELETED` | Cancelado/deletado | `cancelled` |

> **Confirmado**: `RECEIVED` e `CONFIRMED` ambos indicam pagamento. `RECEIVED` = saldo disponível. `CONFIRMED` = pago mas saldo ainda não liberado.

---

## 7. Webhooks

### Estrutura do Evento
```json
{
  "id": "evt_05b708f961d739ea7eba7e4db318f621",
  "event": "PAYMENT_RECEIVED",
  "dateCreated": "2024-06-12 16:45:03",
  "payment": {
    "object": "payment",
    "id": "pay_080225913252"
  }
}
```

### Eventos de Pagamento (Confirmado)
| Evento | Descrição | Ação PayFlow |
|---|---|---|
| `PAYMENT_CREATED` | Cobrança criada | Log apenas |
| `PAYMENT_CONFIRMED` | Pagamento confirmado | Marcar como `paid` |
| `PAYMENT_RECEIVED` | Pagamento recebido | Marcar como `paid` |
| `PAYMENT_OVERDUE` | Pagamento vencido | Marcar como `expired` |
| `PAYMENT_DELETED` | Cobrança cancelada | Marcar como `cancelled` |
| `PAYMENT_RESTORED` | Cobrança restaurada | Marcar como `pending` |
| `PAYMENT_REFUNDED` | Reembolsado | Marcar como `cancelled` |
| `PAYMENT_UPDATED` | Cobrança atualizada | Sync status |
| `PAYMENT_AUTHORIZED` | Cartão autorizado | Log apenas |

### Autenticação de Webhook
- **Header**: `asaas-access-token: <token>`
- Token configurado ao criar webhook via API ou painel
- Se token não corresponder, rejeitar com 401

> **Confirmado**: O token é enviado no header `asaas-access-token`.

### Comportamentos Importantes
- **Delivery**: "At least once" — mesmo evento pode ser entregue múltiplas vezes
- **Idempotência**: Aplicação deve implementar
- **Retry**: Se não responder 2xx, novas tentativas são feitas
- **Queue interruption**: Após 15 falhas consecutivas, fila pode ser interrompida
- **Eventos disponíveis por 14 dias**

---

## 8. Configurar Webhook via API

### Endpoint
```
POST /v3/webhooks
```

### Body
```json
{
  "name": "PayFlow Webhook",
  "url": "https://api.payflow.ai/provider-webhooks/asaas",
  "email": "integration@payflow.ai",
  "enabled": true,
  "interrupted": false,
  "apiVersion": 3,
  "authToken": "secure-token-with-more-than-32-characters",
  "sendType": "SEQUENTIALLY",
  "events": [
    "PAYMENT_CREATED",
    "PAYMENT_CONFIRMED",
    "PAYMENT_RECEIVED",
    "PAYMENT_OVERDUE",
    "PAYMENT_DELETED",
    "PAYMENT_RESTORED",
    "PAYMENT_REFUNDED"
  ]
}
```

> **Confirmado**: `authToken` deve ter mais de 32 caracteres. `sendType` pode ser `SEQUENTIALLY` ou `NON_SEQUENTIALLY`.

---

## 9. Erros Comuns

| HTTP | Causa | Tratamento |
|---|---|---|
| 400 | Body inválido, campos obrigatórios ausentes | Logar erro (sem API key), retornar erro claro |
| 401 | API key inválida ou ausente | Não logar API key, retornar erro de config |
| 404 | Recurso não encontrado | Tratar como não existe |
| 500 | Erro interno do Asaas | Retry com backoff |

---

## Mapeamento PayFlow → Asaas

### Charge → Asaas Payment
| PayFlow | Asaas |
|---|---|
| `customer_name` | `customer.name` (via create customer) |
| `customer_phone` | `customer.mobilePhone` |
| `amount` | `value` |
| `description` | `description` |
| `due_date` | `dueDate` |
| `provider` | `asaas` |
| `billing_type` | `billingType` (PIX, BOLETO, UNDEFINED) |

### Asaas → PayFlow Status
| Asaas | PayFlow ChargeStatus |
|---|---|
| `PENDING` | `pending` |
| `RECEIVED` | `paid` |
| `CONFIRMED` | `paid` |
| `OVERDUE` | `expired` |
| `DELETED` | `cancelled` |
| `REFUNDED` | `cancelled` |
| `RECEIVED_IN_CASH_UNDONE` | `pending` |
| `RESTORED` | `pending` |

---

## O Que NÃO Implementar

- **Pix Out** (envio de dinheiro)
- **Saque** (withdrawal)
- **Pagamento de boleto** (bill payment)
- **Conta digital** (banking)
- **BaaS**
- **Open Finance real**
- **DDA real**
- **KYC real**
- **Transferências**

---

## Inferido (não confirmado diretamente)

- Sandbox aceita CPFs fictícios com formato válido (11 dígitos para CPF, 14 para CNPJ)
- `externalReference` é retornado no webhook para correlação
- Webhook pode enviar o objeto `payment` completo ou apenas `{ id }` dependendo da configuração
- Timeout recomendado: 30 segundos para chamadas API
- Retry seguro: apenas para erros 5xx e timeouts (não para 4xx)
