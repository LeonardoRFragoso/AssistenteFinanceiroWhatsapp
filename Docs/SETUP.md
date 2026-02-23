# 🚀 Guia de Setup Rápido

## Passo a Passo para Rodar o Projeto

### 1. Pré-requisitos

Certifique-se de ter instalado:
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Git](https://git-scm.com/)

### 2. Clonar o Repositório

```bash
git clone seu-repositorio
cd "Assessor financeiro wpp"
```

### 3. Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env
```

Edite o arquivo `.env` e configure:

**Obrigatório:**
- `SECRET_KEY`: Gere uma chave segura (pode usar: `openssl rand -hex 32`)
- `TWILIO_ACCOUNT_SID`: Seu Account SID do Twilio
- `TWILIO_AUTH_TOKEN`: Seu Auth Token do Twilio
- `TWILIO_WHATSAPP_NUMBER`: Número WhatsApp do Twilio (formato: whatsapp:+14155238886)
- `OPENAI_API_KEY`: Sua chave API da OpenAI

**Opcional (para produção):**
- `STRIPE_SECRET_KEY`: Para pagamentos
- `STRIPE_WEBHOOK_SECRET`: Para webhooks do Stripe

### 4. Iniciar o Projeto

```bash
# Iniciar todos os containers
docker-compose up -d

# Aguardar os serviços iniciarem (30-60 segundos)
docker-compose logs -f
```

Pressione `Ctrl+C` para sair dos logs.

### 5. Verificar se está Rodando

Abra no navegador:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Documentação API**: http://localhost:8000/docs

### 6. Criar Primeira Conta

1. Acesse http://localhost:3000
2. Clique em "Cadastre-se"
3. Preencha os dados (use seu número WhatsApp com DDD)
4. Faça login

### 7. Configurar Webhook do Twilio (Para WhatsApp)

**Desenvolvimento Local:**

1. Instale o ngrok: https://ngrok.com/download
2. Execute:
   ```bash
   ngrok http 8000
   ```
3. Copie a URL gerada (ex: https://abc123.ngrok.io)
4. Acesse [Twilio Console](https://console.twilio.com/)
5. Vá em **Messaging** > **Try it out** > **Send a WhatsApp message**
6. Configure o webhook: `https://abc123.ngrok.io/webhook/whatsapp`
7. Salve

**Produção:**
Use sua URL real: `https://seudominio.com/webhook/whatsapp`

### 8. Testar via WhatsApp

1. Envie uma mensagem para o número WhatsApp do Twilio
2. Siga as instruções para conectar
3. Teste comandos:
   - "Gastei R$ 50 com almoço"
   - "Recebi R$ 3000 de salário"
   - "Quanto gastei esse mês?"

## 🔧 Comandos Úteis

### Ver logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Parar o projeto
```bash
docker-compose down
```

### Reiniciar um serviço
```bash
docker-compose restart backend
docker-compose restart frontend
```

### Acessar banco de dados
```bash
docker-compose exec postgres psql -U postgres -d financial_assistant
```

### Executar migrações
```bash
docker-compose exec backend alembic upgrade head
```

### Limpar tudo e recomeçar
```bash
docker-compose down -v
docker-compose up -d
```

## 🐛 Troubleshooting

### Porta já em uso
Se a porta 8000 ou 3000 já estiver em uso, edite `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Backend
  - "3001:3000"  # Frontend
```

### Erro de conexão com banco
```bash
# Verificar se PostgreSQL está rodando
docker-compose ps

# Reiniciar banco
docker-compose restart postgres
```

### Frontend não carrega
```bash
# Reinstalar dependências
docker-compose exec frontend npm install
docker-compose restart frontend
```

### Erro no WhatsApp
1. Verifique se o ngrok está rodando
2. Verifique se a URL do webhook está correta no Twilio
3. Verifique os logs: `docker-compose logs -f backend`

## 📞 Obtendo Credenciais

### Twilio
1. Acesse https://www.twilio.com/
2. Crie uma conta gratuita
3. Vá em **Console** > **Account Info**
4. Copie **Account SID** e **Auth Token**
5. Ative o WhatsApp Sandbox em **Messaging** > **Try it out**

### OpenAI
1. Acesse https://platform.openai.com/
2. Crie uma conta
3. Vá em **API Keys**
4. Crie uma nova chave
5. Copie a chave (só aparece uma vez!)

### Stripe (Opcional)
1. Acesse https://stripe.com/
2. Crie uma conta
3. Vá em **Developers** > **API Keys**
4. Use as chaves de teste para desenvolvimento

## ✅ Checklist de Setup

- [ ] Docker instalado e rodando
- [ ] Arquivo `.env` configurado
- [ ] `docker-compose up -d` executado com sucesso
- [ ] Frontend acessível em http://localhost:3000
- [ ] Backend acessível em http://localhost:8000
- [ ] Conta criada no sistema
- [ ] Credenciais Twilio configuradas
- [ ] Credenciais OpenAI configuradas
- [ ] Ngrok rodando (para desenvolvimento)
- [ ] Webhook configurado no Twilio
- [ ] Teste via WhatsApp funcionando

## 🎉 Pronto!

Seu sistema está rodando! Agora você pode:
- Acessar o dashboard web
- Enviar mensagens via WhatsApp
- Gerenciar suas finanças

Para mais informações, consulte o `README.md` principal.
