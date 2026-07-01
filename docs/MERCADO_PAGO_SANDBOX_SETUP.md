# Mercado Pago Sandbox — Configuração

Este documento explica como configurar o Mercado Pago como provider de cobranças no PayFlow AI **em ambiente sandbox**.

> **Aviso:** O provider padrão do projeto é `fake`. Nenhuma operação de pagamento real é realizada por padrão. Use Mercado Pago apenas em ambiente de teste/sandbox.

## Variáveis de Ambiente Necessárias

No arquivo `.env`:

```env
# Provider de cobrança: fake | mercado_pago
PAYFLOW_PAYMENT_PROVIDER=mercado_pago

# Credenciais do Mercado Pago (sandbox)
MERCADO_PAGO_ACCESS_TOKEN=seu_access_token_sandbox
MERCADO_PAGO_PUBLIC_KEY=sua_public_key_sandbox
MERCADO_PAGO_WEBHOOK_SECRET=seu_webhook_secret
```

> **Nunca commitar tokens reais.** Use apenas credenciais de teste fornecidas pelo Mercado Pago.

## Como Criar Credenciais Sandbox

1. Acesse [developers.mercadopago.com.br](https://www.mercadopago.com.br/developers/)
2. Crie uma aplicação ou use uma existente
3. Vá em **Credenciais** > **Teste** (não Produção)
4. Copie:
   - **Access Token** → `MERCADO_PAGO_ACCESS_TOKEN`
   - **Public Key** → `MERCADO_PAGO_PUBLIC_KEY`
5. Para o webhook secret, vá em **Notificações/Webhooks** e crie uma chave de assinatura
   - Copie o valor → `MERCADO_PAGO_WEBHOOK_SECRET`

## Como Ativar Mercado Pago

1. Configure no `.env`:
   ```env
   PAYFLOW_PAYMENT_PROVIDER=mercado_pago
   MERCADO_PAGO_ACCESS_TOKEN=APP_USR-xxxx-xxxx-xxxx
   MERCADO_PAGO_PUBLIC_KEY=APP_USR-xxxx-xxxx-xxxx
   MERCADO_PAGO_WEBHOOK_SECRET=xxxx
   ```
2. Reinicie o backend: `docker-compose restart backend`

### Validação Automática

Se `PAYFLOW_PAYMENT_PROVIDER=mercado_pago` e `MERCADO_PAGO_ACCESS_TOKEN` não estiver configurado, o sistema retorna erro claro:

```
RuntimeError: PAYFLOW_PAYMENT_PROVIDER is set to 'mercado_pago' but
MERCADO_PAGO_ACCESS_TOKEN is not configured.
Set the token in .env or switch back to PAYFLOW_PAYMENT_PROVIDER=fake.
```

### Em Produção

Em `ENVIRONMENT=production`, a configuração deve ser explícita e segura:
- Todos os tokens devem estar definidos
- `MERCADO_PAGO_WEBHOOK_SECRET` é obrigatório (não pode ser vazio)
- O webhook rejeita requisições sem assinatura válida

## Como Voltar para Fake

Basta alterar no `.env`:

```env
PAYFLOW_PAYMENT_PROVIDER=fake
```

E reiniciar o backend.

## Configurar Webhook do Mercado Pago

1. No painel do Mercado Pago Developers, vá em **Notificações/Webhooks**
2. Configure a URL do webhook:
   ```
   https://seu-dominio.com/provider-webhooks/mercado-pago
   ```
3. Selecione os eventos:
   - `payment`
   - `merchant_order`
4. Salve a configuração

O endpoint `/provider-webhooks/mercado-pago` valida a assinatura `x-signature` do Mercado Pago e processa os eventos de pagamento.

### Payload de Exemplo (Webhook)

```json
{
  "type": "payment",
  "data": {
    "id": "123456789"
  }
}
```

O sistema busca o pagamento pelo ID, identifica a cobrança via `preference_id` (usado como `provider_charge_id`) e marca como `paid` se o status for `approved`.

### Idempotência

Se a mesma cobrança já estiver `paid`, o evento é ignorado (não duplica notificação nem atualização).

## Separação do Billing de Assinatura

O webhook de cobranças (`/provider-webhooks/mercado-pago`) é **completamente separado** do webhook de billing de assinatura (`/billing/webhook`).

- **Cobranças:** `POST /provider-webhooks/mercado-pago` → `ChargeService.process_webhook_payload`
- **Assinatura:** `POST /billing/webhook` → `BillingService` (Stripe)

Não há interferência entre os dois fluxos.

## Riscos e Limitações

- **Não usar credenciais de produção** em ambiente de desenvolvimento
- O Mercado Pago sandbox pode ter latência diferente da produção
- Nem todos os métodos de pagamento estão disponíveis em sandbox
- Webhooks de sandbox podem não ser entregues se o ngrok não estiver rodando
- O cancelamento via Mercado Pago API pode não estar implementado para todos os casos
- **Não há Pix Out, saque, boleto pagamento real, conta digital, BaaS ou Open Finance**

## Checklist de Segurança

- [ ] `PAYFLOW_PAYMENT_PROVIDER` continua `fake` por padrão
- [ ] Credenciais de **teste** (não produção) são usadas em desenvolvimento
- [ ] `MERCADO_PAGO_WEBHOOK_SECRET` está configurado e validado
- [ ] Nenhum token está commitado no repositório
- [ ] `.env` está no `.gitignore`
- [ ] Webhook rejeita requisições sem assinatura válida
- [ ] Ambiente de produção exige configuração explícita

## Padrão do Projeto

O projeto permanece com `PAYFLOW_PAYMENT_PROVIDER=fake` como padrão. Mercado Pago deve ser ativado explicitamente apenas quando necessário para testes de integração.
