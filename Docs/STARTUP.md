# 🚀 Assistente Financeiro - Versão STARTUP

## 📊 Visão Geral do Negócio

Sistema SaaS de gestão financeira pessoal via WhatsApp com IA, focado no mercado brasileiro.

### Proposta de Valor
- **Simplicidade**: Usuário controla finanças conversando naturalmente pelo WhatsApp
- **IA Integrada**: GPT-4o classifica intenções e extrai dados automaticamente
- **Insights Automáticos**: Análises semanais sobre gastos e comportamento financeiro
- **Freemium**: Plano gratuito para aquisição + plano Pro para monetização

### Mercado Alvo
- **Público**: Brasileiros de 25-45 anos, classes B e C
- **Problema**: Dificuldade em manter controle financeiro consistente
- **Solução**: Interface familiar (WhatsApp) + automação com IA

---

## 💰 Modelo de Negócio

### Planos

#### Gratuito
- **Preço**: R$ 0/mês
- **Limite**: 20 transações/mês
- **Objetivo**: Aquisição de usuários
- **Features**: WhatsApp, Dashboard básico, Insights básicos

#### Pro
- **Preço**: R$ 29,90/mês
- **Limite**: Ilimitado
- **Objetivo**: Monetização
- **Features**: Tudo do Free + Insights avançados, Exportação PDF, Suporte prioritário

### Projeções Financeiras

**Cenário Conservador (12 meses)**
- Mês 1-3: 100 usuários (10% conversão) = R$ 299/mês
- Mês 4-6: 500 usuários (15% conversão) = R$ 2.242/mês
- Mês 7-9: 1.500 usuários (20% conversão) = R$ 8.970/mês
- Mês 10-12: 3.000 usuários (25% conversão) = R$ 22.425/mês

**MRR Projetado Ano 1**: R$ 22.425
**ARR Projetado Ano 1**: R$ 269.100

**Custos Mensais Estimados**:
- Infraestrutura AWS: R$ 500
- OpenAI API: R$ 300
- Twilio WhatsApp: R$ 200
- Mercado Pago (taxa): 4,99%
- **Total Fixo**: ~R$ 1.000/mês

**Margem Bruta**: ~85%

---

## 🏗️ Arquitetura Técnica

### Stack Tecnológico

**Backend**
- FastAPI (Python 3.11+)
- PostgreSQL (banco principal)
- Redis (cache + filas)
- SQLAlchemy 2.0 (async ORM)
- RQ (Redis Queue para workers)

**Frontend**
- Next.js 14
- TypeScript
- TailwindCSS
- Axios

**Integrações**
- OpenAI GPT-4o (NLP)
- Twilio (WhatsApp API oficial)
- Mercado Pago (pagamentos)

**Infraestrutura**
- Docker + Docker Compose
- AWS (EC2, RDS, ElastiCache)
- Nginx (reverse proxy)

### Arquitetura de Sistema

```
┌─────────────┐
│  WhatsApp   │
│   (Twilio)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│  ┌──────────┐      ┌────────────┐  │
│  │ Webhook  │─────▶│ Redis Queue│  │
│  └──────────┘      └─────┬──────┘  │
│                          │          │
│                          ▼          │
│                    ┌──────────┐    │
│                    │  Worker  │    │
│                    │  (RQ)    │    │
│                    └────┬─────┘    │
│                         │          │
│                         ▼          │
│              ┌──────────────────┐  │
│              │   OpenAI GPT-4o  │  │
│              └──────────────────┘  │
│                         │          │
│                         ▼          │
│              ┌──────────────────┐  │
│              │   PostgreSQL     │  │
│              └──────────────────┘  │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│  Next.js    │
│  Dashboard  │
└─────────────┘
```

### Escalabilidade

**Atual (MVP)**
- 1 instância backend
- 1 worker
- Suporta: ~1.000 usuários ativos

**Escala Fase 1 (3-6 meses)**
- 2-3 instâncias backend (load balancer)
- 2-3 workers
- RDS Multi-AZ
- Suporta: ~10.000 usuários ativos

**Escala Fase 2 (6-12 meses)**
- Auto-scaling (5-10 instâncias)
- Workers dedicados por fila
- Redis Cluster
- CDN para frontend
- Suporta: ~50.000 usuários ativos

---

## 🔐 Segurança

### Implementações

✅ **Autenticação**
- JWT com expiração
- Bcrypt para senhas
- Rate limiting por IP
- Proteção brute force (5 tentativas/5min)

✅ **API**
- HTTPS obrigatório
- Headers de segurança (HSTS, CSP, X-Frame-Options)
- CORS restritivo
- Validação Pydantic em todas entradas

✅ **Dados**
- Criptografia em trânsito (TLS 1.3)
- Criptografia em repouso (AWS RDS)
- Backup diário automático
- LGPD compliance ready

✅ **Webhooks**
- Validação de assinatura Twilio
- Validação de assinatura Mercado Pago
- Rate limiting específico

---

## 📈 Métricas para Investidores

### Dashboard Admin (`/admin/metrics`)

**Métricas Financeiras**
- MRR (Monthly Recurring Revenue)
- Total Revenue
- Revenue by Plan

**Métricas de Produto**
- Total Users
- Active Users (com assinatura ativa)
- Churn Rate
- Conversion Rate (Free → Pro)

**Métricas de Uso**
- Total Transactions
- Avg Transaction Value
- Users by Plan

### KPIs Principais

1. **CAC (Customer Acquisition Cost)**: Meta < R$ 50
2. **LTV (Lifetime Value)**: Meta > R$ 500
3. **Churn Rate**: Meta < 5%/mês
4. **Conversion Rate**: Meta > 20%
5. **NPS**: Meta > 50

---

## 🚀 Deploy em Produção

### Pré-requisitos

1. **AWS Account** configurada
2. **Domínio** registrado
3. **Certificado SSL** (Let's Encrypt ou AWS Certificate Manager)
4. **Credenciais**:
   - Twilio (WhatsApp API)
   - OpenAI API Key
   - Mercado Pago Access Token

### Infraestrutura AWS

**Serviços Necessários**
- EC2 (t3.medium ou superior)
- RDS PostgreSQL (db.t3.micro para início)
- ElastiCache Redis (cache.t3.micro)
- S3 (backups)
- CloudWatch (logs e monitoramento)
- Route 53 (DNS)
- Application Load Balancer

**Custos Estimados AWS**
- EC2 (2x t3.medium): ~$60/mês
- RDS (db.t3.small): ~$30/mês
- ElastiCache: ~$15/mês
- Load Balancer: ~$20/mês
- **Total**: ~$125/mês (~R$ 625)

### Passo a Passo Deploy

#### 1. Preparar Servidor EC2

```bash
# Conectar ao servidor
ssh ubuntu@seu-servidor

# Instalar dependências
sudo apt update
sudo apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx

# Clonar repositório
git clone seu-repositorio
cd "Assessor financeiro wpp"
```

#### 2. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
nano .env

# Configurar:
# - DATABASE_URL (RDS endpoint)
# - REDIS_URL (ElastiCache endpoint)
# - MERCADO_PAGO_ACCESS_TOKEN
# - TWILIO credentials
# - OPENAI_API_KEY
# - FRONTEND_URL e BACKEND_URL (seu domínio)
```

#### 3. Configurar Banco de Dados

```bash
# Rodar migrações
docker-compose run backend alembic upgrade head

# Seed dos planos
docker-compose run backend python seed_plans.py
```

#### 4. Iniciar Serviços

```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### 5. Configurar Nginx

```nginx
server {
    listen 80;
    server_name api.seudominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name seudominio.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
    }
}
```

```bash
sudo certbot --nginx -d seudominio.com -d api.seudominio.com
```

#### 6. Configurar Webhooks

**Twilio**
- URL: `https://api.seudominio.com/webhook/whatsapp`
- Método: POST

**Mercado Pago**
- URL: `https://api.seudominio.com/billing/webhook/mercado-pago`
- Método: POST

---

## 📊 Monitoramento

### Logs

```bash
# Backend logs
docker-compose logs -f backend

# Worker logs
docker-compose logs -f worker

# Todos os logs
docker-compose logs -f
```

### Métricas CloudWatch

- CPU Utilization
- Memory Usage
- Request Count
- Error Rate
- Response Time

### Alertas Configurados

- CPU > 80% por 5 minutos
- Memory > 85%
- Error rate > 5%
- Queue size > 1000

---

## 🔄 CI/CD

### GitHub Actions (Recomendado)

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to AWS
        run: |
          ssh ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }} '
            cd /app &&
            git pull &&
            docker-compose down &&
            docker-compose up -d --build
          '
```

---

## 📱 Roadmap Produto

### Q1 2026 (Atual)
- ✅ MVP funcional
- ✅ Integração WhatsApp
- ✅ Pagamentos Mercado Pago
- ✅ Dashboard web
- ✅ Insights automáticos

### Q2 2026
- [ ] App mobile (React Native)
- [ ] Integração Open Banking
- [ ] Metas financeiras
- [ ] Notificações push
- [ ] Exportação PDF avançada

### Q3 2026
- [ ] Múltiplas contas bancárias
- [ ] Categorias personalizadas
- [ ] Compartilhamento familiar
- [ ] API pública para integrações

### Q4 2026
- [ ] Investimentos tracking
- [ ] Previsão de gastos com ML
- [ ] Assistente de voz
- [ ] Expansão internacional

---

## 💼 Time Necessário

### Fase Atual (MVP)
- 1 Desenvolvedor Full-Stack

### Fase Crescimento (1k-10k usuários)
- 1 Tech Lead
- 1 Backend Developer
- 1 Frontend Developer
- 1 DevOps/SRE (part-time)
- 1 Customer Success (part-time)

### Fase Escala (10k+ usuários)
- Time completo de 8-12 pessoas
- Áreas: Eng, Product, Growth, CS, Finance

---

## 📞 Suporte

### Canais
- Email: suporte@seudominio.com
- WhatsApp: +55 11 99999-9999
- Dashboard: Chat integrado (plano Pro)

### SLA
- **Plano Gratuito**: 48h (email)
- **Plano Pro**: 12h (prioritário)
- **Crítico**: 2h (downtime)

---

## 🎯 Próximos Passos para Investidores

1. **Validação de Mercado**
   - Beta com 100 usuários
   - Coletar feedback
   - Ajustar pricing

2. **Growth**
   - Marketing digital (Google Ads, Meta Ads)
   - Parcerias com influenciadores
   - SEO e conteúdo

3. **Expansão**
   - Novas features baseadas em feedback
   - Integração com bancos
   - App mobile

4. **Escala**
   - Infraestrutura para 50k+ usuários
   - Time completo
   - Expansão LATAM

---

## 📄 Documentos Adicionais

- **Pitch Deck**: [link]
- **Modelo Financeiro**: [planilha]
- **Roadmap Detalhado**: [notion/jira]
- **Métricas em Tempo Real**: `/admin/metrics`

---

**Desenvolvido com ❤️ para revolucionar a gestão financeira pessoal no Brasil**

*Versão: 2.0.0 - Startup Ready*
*Última atualização: Fevereiro 2026*
