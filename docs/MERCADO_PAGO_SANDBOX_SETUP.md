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
```

> **Nunca commitar tokens reais.** Use apenas credenciais de teste fornecidas pelo Mercado Pago.

## Como Ativar Mercado Pago

1. Acesse [developers.mercadopago.com.br](https://www.mercadopago.com.br/developers/)
2. Crie uma aplicação ou use uma existente
3. Obtenha as credenciais de **teste/sandbox** (não as de produção)
4. Configure no `.env`:
   ```env
   PAYFLOW_PAYMENT_PROVIDER=mercado_pago
   MERCADO_PAGO_ACCESS_TOKEN=APP_USR-xxxx-xxxx-xxxx
   MERCADO_PAGO_PUBLIC_KEY=APP_USR-xxxx-xxxx-xxxx
   ```
5. Reinicie o backend: `docker-compose restart backend`

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

## Padrão do Projeto

O projeto permanece com `PAYFLOW_PAYMENT_PROVIDER=fake` como padrão. Mercado Pago deve ser ativado explicitamente apenas quando necessário para testes de integração.
