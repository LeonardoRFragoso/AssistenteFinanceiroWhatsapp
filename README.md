# 💰 Payflow-AI - SaaS

Sistema completo de gestão financeira pessoal via WhatsApp com dashboard web, utilizando inteligência artificial para processamento de linguagem natural.

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
- ✅ IA que entende português informal

### Dashboard Web
- ✅ Autenticação segura (JWT)
- ✅ Visualização de receitas, despesas e saldo
- ✅ Gráficos por categoria
- ✅ Lista de transações recentes
- ✅ Gerenciamento de lembretes
- ✅ Relatórios mensais
- ✅ Interface moderna e responsiva

## 🏗️ Arquitetura

```
backend/
├── app/
│   ├── core/           # Configurações, database, segurança
│   ├── models/         # Modelos SQLAlchemy
│   ├── schemas/        # Schemas Pydantic
│   ├── repositories/   # Camada de acesso a dados
│   ├── services/       # Lógica de negócio
│   ├── routers/        # Endpoints da API
│   ├── integrations/   # Twilio, OpenAI
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

## 🔐 Segurança

- ✅ Senhas hasheadas com bcrypt
- ✅ Autenticação JWT
- ✅ Validação de webhook Twilio
- ✅ Rate limiting
- ✅ CORS configurado
- ✅ Validação de dados com Pydantic
- ✅ SQL injection protection (SQLAlchemy)

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
