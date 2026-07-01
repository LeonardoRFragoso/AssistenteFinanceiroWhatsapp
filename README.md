# 💰 PayFlow AI - Assistente Financeiro Transacional via WhatsApp

Sistema SaaS de gestão financeira e cobranças via WhatsApp com dashboard web. Utiliza inteligência artificial para processamento de linguagem natural, permitindo registrar despesas, receitas e criar cobranças com links de pagamento de forma segura.

## � Como Testar o WhatsApp

**Número para iniciar conversa**: `+1 415 523 8886` (Twilio Sandbox)

**Passos para começar:**
1. Adicione o número `+1 415 523 8886` nos seus contatos
2. Envie uma mensagem no WhatsApp com o código: `join <seu-codigo-sandbox>`
3. Aguarde a confirmação do Twilio
4. Comece a usar! Exemplos:
   - "Gastei R$ 50 com almoço"
   - "Qual meu saldo?"
   - "Mostre minhas transações"
   - "Gere uma cobrança de R$ 150 para João referente ao serviço do site"

> **Nota**: Este é o número do Twilio WhatsApp Sandbox para desenvolvimento. Em produção, você terá seu próprio número aprovado.

## � Tecnologias

### Backend
- **Python 3.11+** com FastAPI
- **PostgreSQL** para banco de dados
- **Redis** para cache
- **SQLAlchemy 2.0** (async)
- **Alembic** para migrações
- **OpenAI GPT-4o** para NLP e classificação de intenções
- **Twilio** para integração WhatsApp
- **JWT** para autenticação
- **Pydantic** para validação

### Frontend
- **Next.js 14** com TypeScript
- **TailwindCSS** para estilização
- **Lucide React** para ícones
- **Axios** para requisições HTTP

### Infraestrutura
- **Docker** e **Docker Compose**
- Preparado para deploy em AWS/Cloud

## 📋 Funcionalidades

### Via WhatsApp
- ✅ Registro de despesas com linguagem natural
- ✅ Registro de receitas
- ✅ Criação de lembretes/compromissos
- ✅ Consulta de saldo e relatórios
- ✅ Listagem de transações recentes
- ✅ Criação de cobranças com confirmação explícita do usuário
- ✅ Criação de cobranças com vencimento ("com vencimento amanhã", "vence dia 15")
- ✅ Listagem de cobranças com resumo e totais
- ✅ Filtro de cobranças por status (pendentes, pagas)
- ✅ Cancelamento de cobranças via WhatsApp ("cancela a cobrança do João")
- ✅ Notificação automática quando um pagamento é confirmado
- ✅ Lembretes automáticos de vencimento e cobranças vencidas
- ✅ Worker automático de lembretes via RQ (configurável, desativado por padrão)
- ✅ Exportação de cobranças em CSV (com filtros por status e data)
- ✅ Exportação de cobranças em PDF (com filtros, resumo e tabela detalhada)
- ✅ Analytics de cobranças (taxa de conversão, tempo médio de pagamento, taxa de vencimento)
- ✅ Paginação server-side de cobranças com busca e ordenação
- ✅ Envio de link de pagamento para o cliente via WhatsApp (com confirmação)
- ✅ Provider Mercado Pago sandbox (opcional, padrão continua fake)
- ✅ IA que entende português informal

### Dashboard Web
- ✅ Autenticação segura (JWT)
- ✅ Visualização de receitas, despesas e saldo
- ✅ Gráficos por categoria
- ✅ Lista de transações recentes
- ✅ Gerenciamento de lembretes
- ✅ Relatórios mensais
- ✅ Cards de resumo de cobranças (a receber, recebido, pendentes, vencidas)
- ✅ Tabela de cobranças com filtros por status (todas, pendentes, pagas, vencidas, canceladas)
- ✅ Copiar link de pagamento e cancelar cobranças pendentes diretamente do dashboard
- ✅ Botão de exportação CSV de cobranças (respeita filtro atual)
- ✅ Botão de exportação PDF de cobranças (com resumo e tabela detalhada)
- ✅ Cards de analytics (taxa de conversão, tempo médio de pagamento, total criado/pago, taxa de vencimento, canceladas)
- ✅ Paginação de cobranças com busca por cliente/descrição
- ✅ Estados de loading, erro e vazio na tabela de cobranças
- ✅ Interface moderna e responsiva

## 🏗️ Arquitetura

```
backend/
├── app/
│   ├── core/           # Configurações, database, segurança
│   ├── models/         # Modelos SQLAlchemy (User, Charge, PendingAction, ProviderEvent, ChargeReminderLog, ChargeDeliveryLog, etc.)
│   ├── schemas/        # Schemas Pydantic
│   ├── repositories/   # Camada de acesso a dados
│   ├── services/       # Lógica de negócio (AIService, ChargeService, PendingActionService, ChargeReminderService)
│   ├── routers/        # Endpoints da API
│   ├── providers/      # Camada desacoplada de provedores de pagamento (fake, mercado_pago)
│   ├── integrations/   # Twilio, OpenAI, Mercado Pago
│   ├── utils/          # Utilitários
│   └── main.py         # Aplicação FastAPI
├── migrations/         # Migrações Alembic
├── Dockerfile
└── requirements.txt

frontend/
├── pages/              # Páginas Next.js
├── components/         # Componentes React
├── services/           # API client
├── styles/             # CSS global
└── package.json
```

## 🔧 Instalação e Configuração

### 1. Pré-requisitos
- Docker e Docker Compose instalados
- Conta Twilio com WhatsApp API
- Chave API OpenAI
- (Opcional) Conta Stripe para pagamentos

### 2. Configurar Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

**Gerar SECRET_KEY segura** (IMPORTANTE):

```bash
# Use o script fornecido
python scripts/generate_secret_key.py

# Ou gere manualmente
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Edite o arquivo `.env` com suas credenciais:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/financial_assistant
REDIS_URL=redis://redis:6379/0

# Security - IMPORTANTE: Use uma chave de 64+ caracteres
SECRET_KEY=sua-secret-key-gerada-com-64-ou-mais-caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=seu_twilio_account_sid
TWILIO_AUTH_TOKEN=seu_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# OpenAI
OPENAI_API_KEY=sua_openai_api_key
OPENAI_MODEL=gpt-4o

# Ngrok (para desenvolvimento local)
NGROK_AUTHTOKEN=seu_ngrok_authtoken

# Stripe (opcional)
STRIPE_SECRET_KEY=sua_stripe_secret_key
STRIPE_WEBHOOK_SECRET=seu_stripe_webhook_secret

# Mercado Pago (opcional, sandbox por padrão)
MERCADO_PAGO_ACCESS_TOKEN=seu_mercado_pago_access_token
MERCADO_PAGO_PUBLIC_KEY=seu_mercado_pago_public_key

# PayFlow AI - provedor de pagamento: fake | mercado_pago
# Padrão é fake (sandbox/seguro). Use mercado_pago apenas com credenciais sandbox.
PAYFLOW_PAYMENT_PROVIDER=fake

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**Validar configuração** (recomendado):

```bash
python scripts/validate_environment.py
```

### 3. Iniciar o Projeto

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down
```

Os serviços estarão disponíveis em:
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **Ngrok Dashboard**: http://localhost:4040
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

**Verificar saúde dos serviços:**

```bash
# Backend
curl http://localhost:8000/health

# Ver URL pública do Ngrok
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'

# PostgreSQL
docker-compose exec postgres pg_isready -U postgres

# Redis
docker-compose exec redis redis-cli ping
```

### 4. Documentação da API

Acesse a documentação interativa:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints de Cobrança (PayFlow AI)

- `GET /charges` - Lista cobranças paginadas (page, page_size, status, search, start_date, end_date, sort_by, sort_order)
- `GET /charges/summary` - Resumo estatístico (totais a receber, recebido, vencido, contagens)
- `GET /charges/analytics` - Analytics de cobranças (taxa de conversão, tempo médio de pagamento, taxa de vencimento, totais por status)
- `POST /charges` - Cria uma nova cobrança (gera link de pagamento no provedor configurado)
- `GET /charges/{id}` - Detalhes de uma cobrança
- `POST /charges/{id}/cancel` - Cancela uma cobrança pendente
- `POST /charges/reminders/run` - Dispara lembretes de vencimento manualmente (dev apenas)
- `GET /charges/export.csv` - Exporta cobranças do usuário em CSV (filtros por status, data, busca)
- `GET /charges/export.pdf` - Exporta cobranças em PDF com resumo e tabela detalhada (filtros por status, data, busca)

#### Campos do `GET /charges/summary`

| Campo | Descrição |
| --- | --- |
| `total_pending` | Soma de cobranças `pending` **não vencidas** (due_date null ou due_date >= hoje) |
| `total_overdue` | Soma de cobranças `pending` **vencidas** (due_date < hoje) |
| `total_receivable` | Soma de `total_pending + total_overdue` (tudo a receber) |
| `total_paid` | Soma de cobranças `paid` |
| `count_pending` | Quantidade de pendentes não vencidas |
| `count_overdue` | Quantidade de pendentes vencidas |
| `count_paid` | Quantidade de pagas |
| `count_cancelled` | Quantidade de canceladas |

> **Regra:** cobranças vencidas não entram em `total_pending` ou `count_pending`. O card "A Receber" do dashboard usa `total_receivable` para mostrar o total completo (pendentes + vencidas).

#### Filtros de Status (Listagem, CSV e PDF)

O parâmetro `status` aceita os seguintes valores:

| Valor | Descrição | Regra de Filtro |
| --- | --- | --- |
| `pending` | Pendentes não vencidas | `status = PENDING AND (due_date IS NULL OR due_date >= today)` |
| `overdue` | Vencidas (status derivado) | `status = PENDING AND due_date IS NOT NULL AND due_date < today` |
| `paid` | Pagas | `status = PAID` |
| `cancelled` | Canceladas | `status = CANCELLED` |
| `expired` | Expiradas | `status = EXPIRED` |
| `failed` | Falhadas | `status = FAILED` |

> **Importante:**
> - `overdue` não é um valor real do enum `ChargeStatus` — é um **status derivado**. Uma cobrança vencida permanece como `pending` no banco, mas com `due_date < hoje`.
> - `pending` **não inclui** cobranças vencidas. Para ver todas as pendentes (incluindo vencidas), não use filtro de status.
> - `receivable = pending + overdue` (total a receber).
> - Status inválido retorna **HTTP 400** com mensagem de erro.
> - Os endpoints `GET /charges/export.csv` e `GET /charges/export.pdf` usam **a mesma lógica de filtros** da listagem.
> - Filtros de data (`start_date`, `end_date`) são **inclusivos** — `start_date` começa às 00:00:00 e `end_date` vai até 23:59:59.999999.
> - `GET /charges/analytics` é uma **visão global** do usuário — não aceita filtros de status, data ou busca.

### Webhooks de Provedores

- `POST /provider-webhooks/fake` - Recebe eventos do provedor fake (sandbox)
- `POST /provider-webhooks/fake/pay/{provider_charge_id}` - Simula pagamento de uma cobrança fake (apenas development/testing)
- `POST /provider-webhooks/mercado-pago` - Recebe notificações do Mercado Pago para cobranças

## 📱 Configurar Webhook do Twilio

**Para desenvolvimento local**, o projeto já inclui Ngrok configurado no Docker Compose!

1. Após iniciar o projeto, obtenha a URL pública do Ngrok:
   ```bash
   # Ver no dashboard
   open http://localhost:4040
   
   # Ou via API
   curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'
   ```

2. Acesse o [Console Twilio](https://console.twilio.com/)

3. Vá em **Messaging** > **Settings** > **WhatsApp Sandbox**

4. Configure o webhook:
   - **URL**: `https://sua-url-ngrok.ngrok-free.app/webhook/whatsapp`
   - **Método**: POST
   - **Status Callback**: (opcional) mesma URL com `/status`

5. Salve as configurações

6. Teste enviando uma mensagem para o número do Twilio Sandbox

> **Nota**: A URL do Ngrok muda a cada reinicialização. Configure o `NGROK_AUTHTOKEN` no `.env` para URLs persistentes.

## 💬 Exemplos de Uso via WhatsApp

### Registrar Despesa
```
Gastei R$ 50 com almoço
Paguei 120 reais no uber
Comprei remédio por R$ 35,50
```

### Registrar Receita
```
Recebi R$ 3000 de salário
Ganhei 500 reais de freela
```

### Criar Lembrete
```
Lembrar de pagar conta amanhã
Me lembre de ligar pro médico segunda
```

### Consultar Saldo
```
Quanto gastei esse mês?
Qual meu saldo?
Mostre meu resumo financeiro
```

### Ver Transações
```
Mostre minhas últimas transações
Quais foram meus gastos?
```

### Criar Cobrança (PayFlow AI)
```
Gere uma cobrança de R$ 150 para João referente ao serviço do site
Crie um link de pagamento de R$ 89,90 para Maria
Quero cobrar R$ 300 do cliente Pedro
```

O assistente confirmará os dados e pedirá confirmação antes de gerar o link de pagamento. Responda `sim` ou `confirmo` para prosseguir.

### Listar e Consultar Cobranças
```
Mostre minhas cobranças
Alguma cobrança foi paga?
```

## 🗄️ Modelos de Dados

### User
- id, name, email, hashed_password, phone_number, created_at

### Subscription
- id, user_id, plan, status, stripe_customer_id

### Transaction
- id, user_id, type (income/expense), amount, category, description, date

### Reminder
- id, user_id, title, due_date, completed

### ConversationLog
- id, user_id, message, role (user/system/assistant), created_at

### Charge (PayFlow AI)
- id, user_id, customer_name, customer_phone, amount, description, provider, provider_charge_id, payment_link, status, due_date, paid_at, created_at, updated_at

### PendingAction (PayFlow AI)
- id, user_id, action_type, payload, status, expires_at, confirmed_at, executed_at, created_at

### ProviderEvent (PayFlow AI)
- id, provider, event_type, external_id, payload, processed, created_at, processed_at

## 🔐 Segurança

- ✅ Senhas hasheadas com bcrypt
- ✅ Autenticação JWT
- ✅ Validação de webhook Twilio
- ✅ Rate limiting
- ✅ CORS configurado
- ✅ Validação de dados com Pydantic
- ✅ SQL injection protection (SQLAlchemy)
- ✅ Confirmação explícita do usuário antes de criar cobranças (PayFlow AI)
- ✅ Provedor de pagamento padrão fake/sandbox (PayFlow AI)
- ✅ Nenhuma operação de Pix Out, boleto pagamento ou saque implementada (PayFlow AI)

## 🚀 Deploy em Produção

### Preparação

1. **Configurar variáveis de ambiente de produção**
2. **Usar banco PostgreSQL gerenciado** (AWS RDS, DigitalOcean, etc)
3. **Usar Redis gerenciado** (AWS ElastiCache, Redis Cloud)
4. **Configurar HTTPS** (obrigatório para webhook Twilio)
5. **Configurar domínio personalizado**

### Deploy Backend (AWS EC2 exemplo)

```bash
# Conectar ao servidor
ssh usuario@seu-servidor

# Clonar repositório
git clone seu-repositorio
cd seu-repositorio

# Configurar .env
nano .env

# Iniciar com Docker
docker-compose -f docker-compose.prod.yml up -d
```

### Deploy Frontend (Vercel/Netlify)

```bash
cd frontend
npm install
npm run build

# Deploy automático via Git
# Ou manual:
vercel deploy --prod
```

## 📊 Monitoramento

### Logs

```bash
# Ver logs do backend
docker-compose logs -f backend

# Ver logs do PostgreSQL
docker-compose logs -f postgres

# Ver logs do Redis
docker-compose logs -f redis
```

### Health Check

```bash
curl http://localhost:8000/health
```

## 🧪 Testes

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## 📈 Escalabilidade

O sistema foi projetado para escalar:

- **Async/await** em todo backend
- **Connection pooling** no PostgreSQL
- **Redis** para cache e rate limiting
- **Stateless** (pode rodar múltiplas instâncias)
- **Separação de camadas** (fácil microservices)

## � Scripts Utilitários

O projeto inclui scripts para facilitar o desenvolvimento:

### Gerar SECRET_KEY Segura
```bash
python scripts/generate_secret_key.py
```

### Validar Configuração do Ambiente
```bash
python scripts/validate_environment.py
```

## ✅ Correções Recentes Aplicadas

### Migration do PaymentMethod (Fev 2026)
- ✅ Corrigido erro: `invalid input value for enum paymentmethod`
- ✅ Migration agora é idempotente (pode ser executada múltiplas vezes)
- ✅ Usa blocos `DO $$ BEGIN ... EXCEPTION` do PostgreSQL

### Segurança
- ✅ SECRET_KEY agora requer 64+ caracteres
- ✅ Validação aprimorada na inicialização
- ✅ Scripts utilitários para geração de chaves seguras

**Documentação completa das correções**: Ver `MIGRATION_FIX.md` e `QUICK_START.md`

## �🛠️ Desenvolvimento

### Adicionar nova funcionalidade

1. Criar modelo em `backend/app/models/`
2. Criar schema em `backend/app/schemas/`
3. Criar repository em `backend/app/repositories/`
4. Criar service em `backend/app/services/`
5. Criar router em `backend/app/routers/`
6. Registrar router em `backend/app/main.py`

### Criar migração

```bash
docker-compose exec backend alembic revision --autogenerate -m "descrição"
docker-compose exec backend alembic upgrade head
```

### Troubleshooting

**Backend não inicia:**
```bash
# Ver logs completos
docker-compose logs backend --tail=100

# Verificar conectividade com PostgreSQL
docker-compose exec postgres pg_isready

# Verificar variáveis de ambiente
docker-compose exec backend env | grep -E "(DATABASE|SECRET|REDIS)"
```

**Erro na Migration:**
```bash
# Ver status atual
docker-compose exec backend alembic current

# Reverter e reaplicar
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head
```

**Ngrok não conecta:**
```bash
# Verificar se backend está rodando
curl http://localhost:8000/health

# Ver logs do Ngrok
docker-compose logs ngrok

# Verificar token no .env
grep NGROK_AUTHTOKEN .env
```

## 📝 Licença

Este projeto é proprietário. Todos os direitos reservados.

## 🤝 Suporte

Para suporte, entre em contato via:
- Email: suporte@seudominio.com
- WhatsApp: +55 11 99999-9999

## 🎯 Roadmap

- [ ] Integração com Stripe para pagamentos
- [ ] Exportação de relatórios em PDF
- [ ] Gráficos avançados (Recharts)
- [ ] Notificações push
- [ ] App mobile (React Native)
- [ ] Múltiplas moedas
- [ ] Categorias personalizadas
- [ ] Metas financeiras
- [ ] Análise preditiva com IA

---

**Desenvolvido com ❤️ usando Python, FastAPI, Next.js e OpenAI**
