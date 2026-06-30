# PayFlow AI - Roadmap do Produto

> **Nota de escopo:** Este documento descreve a evolução do projeto original "Assistente Financeiro via WhatsApp" para o produto **PayFlow AI**. A transformação é incremental: cada sprint adiciona capacidades transacionais sem quebrar os fluxos existentes de registro de despesas/receitas, relatórios e lembretes.

---

## 1. Visão do Produto

**PayFlow AI** é um assistente financeiro transacional via WhatsApp para autônomos, MEIs e pequenos negócios. Além de registrar despesas e receitas, o produto permite:

- Criar **cobranças e links de pagamento** diretamente no WhatsApp.
- Receber **notificações de pagamento** quando uma cobrança é quitada.
- Acompanhar o status de cobranças no dashboard web.
- Usar **provedores de pagamento sandbox** por padrão para desenvolvimento seguro.

### Diferença para o produto original

| Aspecto | Assistente Financeiro (legado) | PayFlow AI |
| --- | --- | --- |
| Foco | Controle pessoal de gastos e receitas | Controle + cobranças a clientes |
| Interação | Registro de transações | Registro + ações pendentes com confirmação |
| Provedores | Apenas Mercado Pago para assinaturas | Provedores desacoplados (fake, Mercado Pago) para cobranças |
| Confirmação | Não aplicável | Confirmação explícita antes de gerar pagamentos |
| Dashboard | Resumo e transações | Resumo, transações **e cobranças** |

---

## 2. Arquitetura

```
┌─────────────────┐
│   WhatsApp      │
│   (Twilio)      │
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  FastAPI Backend                         │
│  - Webhook /webhook/whatsapp             │
│  - AIService (intents)                   │
│  - PendingActionService                  │
│  - ChargeService                         │
│  - Provider Abstraction Layer            │
│  - REST API /charges                     │
│  - Provider Webhooks /provider-webhooks  │
└────────┬────────────────────────────┬────┘
         │                            │
         ▼                            ▼
┌─────────────────┐        ┌──────────────────┐
│  PostgreSQL     │        │  Provedores      │
│  + Redis/RQ     │        │  - Fake          │
│                 │        │  - Mercado Pago  │
└─────────────────┘        └──────────────────┘
```

### Entidades principais

- **User**: cliente/empresa que usa o produto.
- **Charge**: cobrança gerada para um cliente.
- **PendingAction**: ação sensível aguardando confirmação explícita.
- **ProviderEvent**: evento bruto recebido de provedores de pagamento.
- **Transaction / PaymentEvent**: entidades legadas mantidas.

---

## 3. Roadmap de Fases

### Fase 1 - Fundações e "Create charge via WhatsApp" (Sprint Atual)

Objetivo: implementar o primeiro fluxo transacional completo com segurança e sandbox.

Escopo:
- Rebranding mínimo para PayFlow AI.
- Novos models: `Charge`, `PendingAction`, `ProviderEvent`.
- Camada de provedores: `PaymentProvider` base, `FakePaymentProvider`, `MercadoPagoPaymentProvider` e factory.
- Serviços: `ChargeService` e `PendingActionService`.
- Novos intents na IA: `create_pix_charge`, `confirm_pending_action`, `cancel_pending_action`, `list_charges`, `check_charge_status`.
- Webhook WhatsApp com confirmação explícita antes de gerar qualquer cobrança.
- REST API para cobranças: `GET /charges`, `POST /charges`, `GET /charges/{id}`, `POST /charges/{id}/cancel`.
- Webhooks de provedores: `POST /provider-webhooks/fake`, `POST /provider-webhooks/mercado-pago`, com endpoint de simulação de pagamento fake.
- Dashboard web com seção de cobranças recentes.
- Documentação e testes mínimos.

### Fase 2 - Aprofundamento Transacional

- Envio automático do link de pagamento para o cliente via WhatsApp.
- Vencimento e lembretes de cobranças pendentes.
- Suporte a múltiplos itens na mesma cobrança.
- Relatório de receitas a receber / recebidas.
- Filtros e paginação no dashboard de cobranças.

### Fase 3 - Provedores e Compliance

- Integração real com Mercado Pago (modo produção via configuração).
- Validação robusta de assinaturas de webhook.
- Logs de auditoria e sanetização de dados sensíveis.
- Suporte a boleto e cartão (apenas recebimento, nunca Pix Out).

### Fase 4 - Escalabilidade e Mercado

- Planos comerciais com limites de cobranças.
- Onboarding guiado para novos usuários.
- API pública/documentação para parceiros.
- White-label e multi-empresa.

---

## 4. Limites de Segurança do Sprint Atual

Para evitar operações financeiras reais acidentais:

- `PAYFLOW_PAYMENT_PROVIDER=fake` é o padrão.
- Provedores reais só são ativados por variável de ambiente com credenciais sandbox.
- Nenhuma operação de Pix Out, boleto pagamento ou saque é implementada.
- Toda cobrança via WhatsApp exige confirmação do usuário (PendingAction).
- Segredos e tokens nunca são hardcoded; usam `.env` e `settings`.

---

## 5. Próximos Passos Imediatos

1. Revisar as rotas de webhook e REST para garantir autenticação/validação corretas.
2. Testar o fluxo completo: criação de cobrança → confirmação → pagamento fake → notificação.
3. Rodar migrações Alembic no ambiente de desenvolvimento.
4. Atualizar README com novas variáveis de ambiente e fluxo de cobranças.
5. Adicionar testes de integração para os novos endpoints.
