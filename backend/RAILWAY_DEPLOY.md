# Deploy Backend no Railway

## Pré-requisitos

1. Conta no Railway (https://railway.app)
2. Repositório Git conectado ao Railway

## Configuração no Railway

### 1. Variáveis de Ambiente Obrigatórias

No painel do Railway, vá em **Variables** e adicione:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=<gere-uma-chave-segura-de-64-caracteres>
ENVIRONMENT=production
FRONTEND_URL=<url-do-seu-frontend-vercel>
BACKEND_URL=<url-do-seu-backend-railway>
```

**Para gerar SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 2. Variáveis de Ambiente Opcionais (Integrações)

Adicione conforme necessário:

```
# Redis (se estiver usando)
REDIS_URL=${{Redis.REDIS_URL}}

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=<seu_sid>
TWILIO_AUTH_TOKEN=<seu_token>
TWILIO_WHATSAPP_NUMBER=whatsapp:+<numero>

# OpenAI
OPENAI_API_KEY=<sua_chave>
OPENAI_MODEL=gpt-4o

# Mercado Pago
MERCADO_PAGO_ACCESS_TOKEN=<seu_token>
MERCADO_PAGO_PUBLIC_KEY=<sua_chave>

# Admin
ADMIN_EMAILS=admin@exemplo.com
```

### 3. Configuração do Serviço

O Railway deve detectar automaticamente o `Dockerfile` ou usar o `Procfile`. 

Se houver problemas, configure manualmente:
- **Root Directory**: `backend`
- **Build Command**: (deixe vazio - usa Dockerfile)
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 4. Banco de Dados PostgreSQL

1. Adicione um serviço PostgreSQL no Railway
2. O Railway criará automaticamente a variável `DATABASE_URL`
3. Use `${{Postgres.DATABASE_URL}}` para referenciar

## Verificação

Após deploy, acesse:
- `https://<sua-url>/health` - Deve retornar `{"status": "healthy"}`
- `https://<sua-url>/docs` - Documentação da API (Swagger)

## Troubleshooting

### Erro "Error creating build plan with railpack"
- Verifique se o **Root Directory** está configurado como `backend`
- Confirme que `railway.json` e `Dockerfile` existem no diretório backend

### Erro de conexão com banco
- Verifique se `DATABASE_URL` está usando a referência correta: `${{Postgres.DATABASE_URL}}`
- O código converte automaticamente para formato asyncpg

### Aplicação não inicia
- Verifique os logs no Railway
- Confirme que `SECRET_KEY` está definida
- Confirme que `DATABASE_URL` está definida
