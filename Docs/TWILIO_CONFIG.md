# Configuração do Twilio WhatsApp

## 📋 Credenciais do Twilio

Com base nas suas credenciais do console Twilio, configure o arquivo `.env` na raiz do projeto:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=SEU_ACCOUNT_SID_AQUI
TWILIO_AUTH_TOKEN=SEU_AUTH_TOKEN_AQUI
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

## 🔧 Passos para Configuração

### 1. Atualizar o arquivo .env

Edite o arquivo `.env` na raiz do projeto e adicione suas credenciais:

```bash
# No diretório raiz do projeto
nano .env  # ou use seu editor preferido
```

Cole as credenciais acima.

### 2. Obter um Número WhatsApp do Twilio

1. Acesse: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
2. Siga as instruções para ativar o Twilio Sandbox for WhatsApp
3. Envie a mensagem de ativação do seu WhatsApp pessoal
4. Anote o número do sandbox (geralmente `whatsapp:+14155238886`)

### 3. Configurar Webhook para Receber Mensagens

No console do Twilio:
1. Vá em **Messaging** > **Settings** > **WhatsApp Sandbox Settings**
2. Configure o webhook:
   - **When a message comes in**: `https://seu-dominio.com/webhook/whatsapp`
   - **Method**: POST

Para desenvolvimento local, use ngrok:
```bash
ngrok http 8000
```

Depois configure o webhook com a URL do ngrok:
```
https://abc123.ngrok.io/webhook/whatsapp
```

### 4. Reiniciar o Backend

```bash
docker-compose restart backend
```

## 📱 Como Usar

### Enviar Mensagem de Teste

Use o endpoint de teste:

```bash
curl -X POST http://localhost:8000/test/send-whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+5521999999999",
    "message": "Olá! Esta é uma mensagem de teste do Assistente Financeiro."
  }'
```

### Fluxo de Uso no Sistema

1. **Usuário envia mensagem via WhatsApp** para o número Twilio
2. **Twilio recebe** e envia para o webhook do backend
3. **Backend processa** com IA (OpenAI GPT-4)
4. **Backend responde** via Twilio
5. **Usuário recebe** a resposta no WhatsApp

## 🧪 Testar Integração

### 1. Verificar Conexão

```bash
# Verificar se as credenciais estão corretas
docker-compose logs backend | grep -i twilio
```

### 2. Enviar Mensagem de Teste

Do seu WhatsApp pessoal, envie para o número sandbox:
```
join <código-do-sandbox>
```

Depois envie:
```
Gastei R$ 50 com almoço
```

### 3. Verificar Logs

```bash
docker-compose logs -f backend
```

## 📊 Exemplos de Mensagens

### Registrar Despesa
```
Gastei R$ 50.00 com almoço
Paguei R$ 100 de conta de luz
Despesa de R$ 30 com uber
```

### Registrar Receita
```
Recebi R$ 3500 de salário
Entrada de R$ 500 freelance
```

### Criar Lembrete
```
Lembrar de pagar conta amanhã
Lembrete: reunião dia 20
```

### Consultar Saldo
```
Qual meu saldo?
Quanto gastei este mês?
Resumo financeiro
```

## ⚠️ Limitações do Sandbox

O Twilio Sandbox tem algumas limitações:
- Apenas números que enviaram "join" podem receber mensagens
- Mensagens expiram após 24h de inatividade
- Para produção, você precisa de um número Twilio aprovado

## 🚀 Produção

Para usar em produção:
1. Compre um número Twilio com WhatsApp habilitado
2. Solicite aprovação do template de mensagens
3. Configure domínio com SSL (HTTPS obrigatório)
4. Atualize o webhook com a URL de produção

## 🔐 Segurança

- **Nunca commite** o arquivo `.env` no Git
- Use variáveis de ambiente em produção
- Valide todas as mensagens recebidas
- Implemente rate limiting

## 📞 Suporte

- Documentação Twilio: https://www.twilio.com/docs/whatsapp
- Console Twilio: https://console.twilio.com
- Logs de mensagens: https://console.twilio.com/us1/monitor/logs/sms
