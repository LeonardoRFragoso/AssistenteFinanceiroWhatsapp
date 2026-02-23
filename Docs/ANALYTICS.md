# 📊 Sistema de Analytics e Validação de Mercado

## Visão Geral

Sistema completo de analytics para medir e validar Product-Market Fit, preparado para demonstrar tração real para investidores.

---

## 🎯 Métricas Implementadas

### 1. **Funil de Conversão** (`/admin/funnel`)

Acompanha o usuário desde o registro até a conversão em cliente pagante:

```
Registro → WhatsApp Conectado → Primeira Transação → Upgrade Clicado → Checkout Iniciado → Pagamento Aprovado
```

**Métricas retornadas:**
- Total de registros
- WhatsApp conectados
- Primeiras transações
- Upgrades clicados
- Checkouts iniciados
- Pagamentos aprovados
- **Taxas de conversão** em cada etapa

**Exemplo de resposta:**
```json
{
  "total_registrations": 1000,
  "whatsapp_connected": 850,
  "first_transaction": 600,
  "upgrade_clicked": 200,
  "checkout_started": 150,
  "payment_success": 120,
  "conversion_rates": {
    "registration_to_whatsapp": 85.0,
    "whatsapp_to_transaction": 70.59,
    "upgrade_to_checkout": 75.0,
    "checkout_to_payment": 80.0,
    "overall_free_to_pro": 12.0
  }
}
```

### 2. **Coorte de Retenção** (`/admin/retention-cohort`)

Analisa retenção de usuários agrupados por semana de cadastro:

**Métricas por coorte:**
- Tamanho da coorte
- Usuários ativos após 7 dias
- Usuários ativos após 30 dias
- % de retenção em 7 dias
- % de retenção em 30 dias

**Exemplo de resposta:**
```json
{
  "cohorts": [
    {
      "week_start": "2026-02-10",
      "cohort_size": 50,
      "active_7_days": 35,
      "active_30_days": 25,
      "retention_7_days": 70.0,
      "retention_30_days": 50.0
    }
  ]
}
```

### 3. **Taxa de Conversão** (`/admin/conversion`)

Mede conversão de usuários gratuitos para pagantes:

```json
{
  "total_users": 1000,
  "pro_users": 120,
  "free_users": 880,
  "conversion_rate": 12.0
}
```

### 4. **Taxa de Churn** (`/admin/churn`)

Mede quantos usuários cancelaram a assinatura:

```json
{
  "active_last_month": 100,
  "churned_this_month": 5,
  "churn_rate": 5.0
}
```

### 5. **LTV (Lifetime Value)** (`/admin/ltv`)

Estima o valor de vida do cliente:

```json
{
  "monthly_price": 29.90,
  "avg_lifetime_months": 20.0,
  "estimated_ltv": 598.0,
  "churn_rate_used": 5.0
}
```

### 6. **Dashboard Admin Completo** (`/admin/dashboard`)

Visão consolidada de todas as métricas principais:

```json
{
  "mrr": 3588.0,
  "total_revenue": 15000.0,
  "new_users_today": 5,
  "new_users_this_week": 35,
  "new_users_this_month": 150,
  "conversion_rate": 12.0,
  "churn_rate": 5.0,
  "estimated_ltv": 598.0,
  "cac_estimate": 50.0,
  "active_subscriptions": 120,
  "total_transactions": 5000
}
```

---

## 📈 Eventos Rastreados

### Eventos Automáticos

Todos os eventos são disparados automaticamente pelo sistema:

| Evento | Quando é disparado | Dados capturados |
|--------|-------------------|------------------|
| `user_registered` | Novo usuário se cadastra | email, plano inicial |
| `whatsapp_connected` | Primeira mensagem no WhatsApp | - |
| `first_transaction` | Primeira transação registrada | tipo, valor, categoria |
| `upgrade_clicked` | Usuário clica em upgrade | - |
| `checkout_started` | Inicia processo de pagamento | plan_id, plan_name, price |
| `payment_success` | Pagamento aprovado | amount, payment_id |
| `payment_failed` | Pagamento rejeitado | status, payment_id |
| `subscription_cancelled` | Assinatura cancelada | plan |
| `limit_reached` | Limite de transações atingido | plan, limit, current |
| `insight_viewed` | Usuário visualiza insight | - |
| `reactivation_message_sent` | Mensagem de reativação enviada | reason |
| `renewal_reminder_sent` | Lembrete de renovação enviado | days_left |
| `cancellation_feedback_sent` | Feedback pós-cancelamento | - |

### Como os Eventos São Rastreados

```python
# Exemplo: Registro de usuário
from app.repositories.user_event_repository import UserEventRepository

event_repo = UserEventRepository(db)
await event_repo.create(
    user_id=user.id,
    event_type="user_registered",
    metadata={"email": user.email, "plan": "free"}
)
```

---

## 🔄 Sistema Anti-Churn

### RetentionService

Detecta automaticamente usuários em risco e envia mensagens de reativação:

#### 1. **Usuários Inativos (7 dias)**

Detecta usuários que não usam o sistema há 7 dias e envia:

```
👋 Olá {nome}!

Sentimos sua falta! 😊

Notamos que você não usa o Assistente Financeiro há alguns dias.

💡 Lembre-se que você pode:
✅ Registrar despesas e receitas
📊 Ver relatórios financeiros
📅 Criar lembretes
💰 Controlar seu dinheiro facilmente

Volte quando quiser! Estamos aqui para ajudar. 💚
```

#### 2. **Renovação Próxima (3 dias antes)**

Lembra usuários Pro sobre renovação:

```
⏰ Lembrete de Renovação

Olá {nome}!

Sua assinatura Pro vence em 3 dias (17/02/2026).

💎 Continue aproveitando:
✅ Transações ilimitadas
📊 Insights avançados
🎯 Suporte prioritário

Sua renovação será automática.
```

#### 3. **Pós-Cancelamento**

Coleta feedback e mantém porta aberta:

```
😢 Sentimos muito ver você partir, {nome}

Sua assinatura foi cancelada com sucesso.

Gostaríamos muito de saber:
❓ O que poderíamos ter feito melhor?

Você ainda pode usar o plano gratuito:
✅ 20 transações por mês
📊 Dashboard básico
💬 WhatsApp integrado

Volte sempre que quiser! 💚
```

#### 4. **Limite Atingido**

Incentiva upgrade quando usuário atinge limite:

```
⚠️ Limite Atingido!

Você atingiu 20 de 20 transações do plano gratuito este mês.

💎 Faça upgrade para o Plano Pro:
✅ Transações ILIMITADAS
📊 Insights avançados com IA
🎯 Suporte prioritário
💰 Apenas R$ 29,90/mês

Continue controlando suas finanças sem limites! 🚀
```

### Executar Campanhas de Retenção

```python
from app.services.retention_service import RetentionService

retention_service = RetentionService(db)
results = await retention_service.process_retention_campaigns()

# Retorna:
# {
#   "inactive_users_contacted": 5,
#   "renewal_reminders_sent": 3,
#   "errors": 0
# }
```

---

## 📊 Tracking no Frontend

### Google Analytics 4

Configurado automaticamente em todas as páginas.

**Eventos customizados:**

```typescript
import { trackCTAClick, trackCheckoutStart, trackPurchase } from '@/utils/analytics';

// Clique em CTA
trackCTAClick('hero_button');

// Início de checkout
trackCheckoutStart('Plano Pro', 29.90);

// Compra concluída
trackPurchase('Plano Pro', 29.90, 'txn_123');
```

### Meta Pixel (Facebook)

Rastreia conversões para campanhas de Facebook Ads.

**Eventos automáticos:**
- `PageView` - Todas as páginas
- `Lead` - Clique em CTA
- `InitiateCheckout` - Início de checkout
- `Purchase` - Compra concluída
- `CompleteRegistration` - Cadastro concluído

### Configuração

Adicione no `.env`:

```env
GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX
META_PIXEL_ID=000000000000000
```

---

## 🎯 KPIs para Investidores

### Métricas Essenciais

| Métrica | Endpoint | Meta | Atual (exemplo) |
|---------|----------|------|-----------------|
| **MRR** | `/admin/dashboard` | R$ 10.000 | R$ 3.588 |
| **Conversão Free→Pro** | `/admin/conversion` | >15% | 12% |
| **Churn Rate** | `/admin/churn` | <5% | 5% |
| **LTV** | `/admin/ltv` | >R$ 500 | R$ 598 |
| **CAC** | Manual | <R$ 100 | R$ 50 |
| **LTV/CAC Ratio** | Calculado | >3:1 | 11.96:1 ✅ |
| **Retenção 30 dias** | `/admin/retention-cohort` | >40% | 50% ✅ |

### Fórmulas

```
MRR = Assinaturas Ativas × R$ 29,90

LTV = Preço Mensal × (1 / Churn Rate Mensal)

LTV/CAC Ratio = LTV ÷ CAC

Payback Period = CAC ÷ MRR por Cliente
```

---

## 🚀 Como Usar

### 1. Acessar Métricas

```bash
# Dashboard completo
curl http://localhost:8000/admin/dashboard?cac_estimate=50

# Funil de conversão
curl http://localhost:8000/admin/funnel

# Coorte de retenção
curl http://localhost:8000/admin/retention-cohort

# Taxa de conversão
curl http://localhost:8000/admin/conversion

# Churn rate
curl http://localhost:8000/admin/churn

# LTV
curl http://localhost:8000/admin/ltv
```

### 2. Executar Campanhas Anti-Churn

Criar um cron job ou scheduled task:

```python
# retention_cron.py
import asyncio
from app.core.database import AsyncSessionLocal
from app.services.retention_service import RetentionService

async def run_retention():
    async with AsyncSessionLocal() as db:
        service = RetentionService(db)
        results = await service.process_retention_campaigns()
        print(f"Retention campaigns executed: {results}")

if __name__ == "__main__":
    asyncio.run(run_retention())
```

Agendar para rodar diariamente:

```bash
# Linux/Mac (crontab)
0 9 * * * cd /path/to/project && python retention_cron.py

# Windows (Task Scheduler)
# Criar tarefa agendada para executar diariamente às 9h
```

### 3. Visualizar Eventos de um Usuário

```python
from app.repositories.user_event_repository import UserEventRepository

event_repo = UserEventRepository(db)
events = await event_repo.get_by_user(user_id=1, limit=50)

for event in events:
    print(f"{event.created_at}: {event.event_type} - {event.metadata}")
```

---

## 📈 Demonstração para Investidores

### Pitch Deck - Slide de Tração

**Métricas Reais (Exemplo após 3 meses):**

- 📊 **MRR**: R$ 3.588 (+45% MoM)
- 👥 **Usuários Ativos**: 1.000 (+60% MoM)
- 💰 **Conversão Free→Pro**: 12%
- 📉 **Churn Rate**: 5% (abaixo da média SaaS de 7%)
- 💎 **LTV**: R$ 598
- 💵 **CAC**: R$ 50
- 🎯 **LTV/CAC**: 11.96:1 (excelente!)
- 🔄 **Retenção 30 dias**: 50%
- 💸 **Receita Total**: R$ 15.000

### Unit Economics

```
Receita por Cliente: R$ 29,90/mês
Custo de Aquisição: R$ 50
Payback Period: 1,67 meses
Margem Bruta: 85%
```

### Projeção 12 Meses

```
Mês 1-3:   1.000 usuários → 120 Pro → R$ 3.588 MRR
Mês 4-6:   3.000 usuários → 450 Pro → R$ 13.455 MRR
Mês 7-9:   7.000 usuários → 1.050 Pro → R$ 31.395 MRR
Mês 10-12: 15.000 usuários → 2.250 Pro → R$ 67.275 MRR

ARR Ano 1: R$ 807.300
```

---

## 🔧 Manutenção

### Limpar Eventos Antigos

```sql
-- Manter apenas últimos 90 dias
DELETE FROM user_events 
WHERE created_at < NOW() - INTERVAL '90 days';
```

### Índices Importantes

```sql
CREATE INDEX idx_user_events_user_created ON user_events(user_id, created_at DESC);
CREATE INDEX idx_user_events_type_created ON user_events(event_type, created_at DESC);
```

---

## 📝 Próximos Passos

1. **Integrar com ferramentas de BI**
   - Metabase
   - Google Data Studio
   - Tableau

2. **A/B Testing**
   - Testar diferentes CTAs
   - Testar preços
   - Testar mensagens de retenção

3. **Cohort Analysis Avançado**
   - Segmentação por canal de aquisição
   - Análise por categoria de gasto
   - Comportamento por região

4. **Predictive Analytics**
   - ML para prever churn
   - Recomendação de momento ideal para upgrade
   - Previsão de LTV individual

---

**Sistema pronto para validação de mercado e demonstração de tração real! 🚀**

*Última atualização: Fevereiro 2026*
