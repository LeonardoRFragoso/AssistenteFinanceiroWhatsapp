# Sprint 10 — Advanced Analytics, Collection Performance e Business Insights

## Objetivo

Implementar analytics avançado para cobranças, com métricas operacionais, insights textuais em português, ranking de clientes, aging de vencidas, performance da régua de cobrança, e exportação CSV/PDF.

## Regras e Restrições

- **NÃO** é um sistema de credit scoring. Todas as métricas são operacionais.
- **NÃO** usa linguagem alarmista ou recomendações financeiras.
- **NÃO** realiza operações bancárias, Pix Out, ou Open Finance.
- QR Code permanece sandbox/fake.
- Isolamento rigoroso por `user_id` — nenhum dado de outro usuário é exposto.

## Backend

### ChargeAnalyticsService (`backend/app/services/charge_analytics_service.py`)

Serviço dedicado para analytics de cobranças por usuário. Métodos:

- `get_overview(user_id, start_date?, end_date?)` — métricas globais: total cobrado, recebido, pendente, vencido, taxa de recebimento, taxa de vencimento, tempo médio de pagamento, atraso médio, clientes ativos, rascunhos de follow-up.
- `get_monthly_trends(user_id, months=6)` — tendências mensais com valores cobrados, recebidos, pendentes, vencidos e taxa de recebimento.
- `get_aging(user_id)` — buckets de aging para cobranças vencidas: 1-7, 8-15, 16-30, 31-60, 60+ dias.
- `get_customer_performance(user_id, limit=10)` — ranking de clientes com status operacional, valores, atraso médio e ação sugerida (operacional, não credit scoring).
- `get_collection_performance(user_id)` — métricas da régua de cobrança: total de rascunhos, por tom, por status, clientes contatados, rascunhos no mês, cobranças pagas após follow-up, valor recuperado estimado.
- `get_insights(user_id, start_date?, end_date?)` — insights textuais em português, sem alarmismo, sem recomendações financeiras.

### Router (`backend/app/routers/analytics.py`)

Endpoints sob `/analytics`:

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/analytics/overview` | Visão geral com filtros de data |
| GET | `/analytics/monthly-trends` | Tendências mensais (1-12 meses) |
| GET | `/analytics/aging` | Aging de cobranças vencidas |
| GET | `/analytics/customer-performance` | Ranking de clientes |
| GET | `/analytics/collection-performance` | Performance da régua de cobrança |
| GET | `/analytics/insights` | Insights textuais |
| GET | `/analytics/export.csv` | Exportação CSV com todos os dados |
| GET | `/analytics/export.pdf` | Exportação PDF com relatório completo |

Todos os endpoints exigem autenticação (`get_current_active_user`) e filtram por `user_id`.

### WhatsApp Intents

Novos intents adicionados ao `AIService.classify_intent` e `process_intent`:

- `analytics_overview` — "como estão minhas cobranças?", "resumo das minhas cobranças"
- `monthly_trends_summary` — "tendência mensal", "comparativo mensal"
- `aging_summary` — "faixas de atraso", "aging das cobranças"
- `customer_performance_summary` — "performance dos clientes", "ranking de clientes"
- `collection_performance_summary` — "performance de cobrança", "como está minha régua?"

Todas as respostas usam linguagem operacional segura, sem alarmismo.

## Frontend

### AdvancedAnalyticsSection (`frontend/components/AdvancedAnalyticsSection.tsx`)

Componente integrado ao dashboard com:

- **Cards de overview**: total cobrado, recebido, pendente, vencido
- **Badges de taxas**: taxa de recebimento, vencimento, tempo médio, atraso médio, clientes ativos
- **Gráfico de tendências mensais** (Recharts LineChart)
- **Gráfico de aging** (Recharts BarChart)
- **Tabela de ranking de clientes** com status operacional e ações sugeridas
- **Cards de performance da régua de cobrança**
- **Seção de insights** textuais
- **Filtro de período**: 30, 90, 180, 365 dias
- **Exportação CSV e PDF**

### Data-testids

| data-testid | Elemento |
|-------------|----------|
| `advanced-analytics-section` | Container principal |
| `analytics-overview-cards` | Grid de cards de overview |
| `analytics-period-filter` | Select de filtro de período |
| `analytics-export-csv` | Botão exportar CSV |
| `analytics-export-pdf` | Botão exportar PDF |
| `analytics-monthly-trends` | Seção de gráfico de tendências |
| `analytics-aging` | Seção de gráfico de aging |
| `analytics-customer-performance` | Tabela de ranking de clientes |
| `analytics-collection-performance` | Cards de performance da régua |
| `analytics-insights` | Seção de insights |

## Testes

### Backend (`backend/tests/test_sprint10.py`)

27 testes cobrindo:

- Overview com e sem dados
- Isolamento por usuário (overview, trends, aging, customer performance, collection performance, insights)
- Tendências mensais
- Buckets de aging (1-7, 8-15, 16-30, 31-60, 60+)
- Ações sugeridas (thank_customer, send_friendly_reminder, review_payment_terms)
- Verificação de que NÃO é credit scoring
- Performance da régua com dados insuficientes e suficientes
- Insights sem alarmismo
- Filtros de data

### E2E (`frontend/e2e/demo.spec.ts`)

- Test 19: Advanced Analytics section renders with cards and charts
- Test 20: Analytics period filter changes data

### Screenshots (`frontend/e2e/screenshots.spec.ts`)

- Sprint 10 - Advanced Analytics screenshot

## Total de Testes

- Backend: 261 (234 anteriores + 27 novos)
- E2E: 27 (25 anteriores + 2 novos)
